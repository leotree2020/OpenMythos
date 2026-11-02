"""Independent stdlib-only audit fixtures; no worker, Torch, or real research data."""
import argparse
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest import mock


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("routing_auditor_under_test", HERE / "audit_routing.py")
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def describe(path):
    value = path.read_bytes()
    return {"bytes": len(value), "sha256": digest(value)}


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encoded(value) + b"\n")


def history():
    """60 eligible sources; old 0..30 plus duplicate, corrected 1..32."""
    articles = [{"article_id": f"article-{59 - i:03d}", "source_article_key": f"source-{i:03d}",
                 "eligible": True, "full_token_count": 300, "heading_row": i} for i in range(60)]
    partition = {"articles": articles,
                 "row_roles": [{"source_article_key": f"source-{i:03d}"} for i in range(60)]}
    old = {"samples": [{"heading_row": i} for i in list(range(31)) + [0]]}
    corrected = {"samples": [{"source_article_key": f"source-{i:03d}"} for i in range(1, 33)]}
    return partition, old, corrected


class SealedFixture:
    """Hand-authored byte evidence, never derived through worker/controller code.

    The mock substitutes only source re-tokenization, which requires unavailable
    pinned historical files. All worker sealing, counts, bytes, decisions and
    metadata checks in Audit.run remain real.
    """
    def __init__(self, root, all_late=False):
        self.root, self.worker = root, root / "worker"
        self.samples, self.rows = [], []
        self.zero = struct.pack("<f", 0.0) * 32768
        self.skew = struct.pack("<f", 1.0) * 16384 + struct.pack("<f", 0.0) * 16384
        self.full_head_hashes = {}
        for block in (self.zero, self.skew):
            full_hash = hashlib.sha256()
            for _ in range(128):
                full_hash.update(block)
            self.full_head_hashes[digest(block)] = full_hash.hexdigest()
        # Two equal-size groups: analytic TV(uniform, softmax([1...1,0...0])).
        self.late_tv = (math.exp(1.0) - 1.0) / (2.0 * (math.exp(1.0) + 1.0))
        for index in range(16):
            tokens = [index + 1] * 128
            self.samples.append({"index": index, "tokens": tokens,
                                 "source_article_key": f"synthetic-source-{index:02d}",
                                 "article_id": f"synthetic-article-{index:02d}",
                                 "input_ids_sha256": digest(encoded(tokens)),
                                 "raw_input_sha256": digest(struct.pack("<128q", *tokens))})
        prepared = root / "data/private/inputs.json"
        data_completion = root / "data/public/completion.json"
        save(prepared, {"context_tokens": 128, "seeds": [3101, 3202], "samples": self.samples})
        save(data_completion, {"Status": "PASS", "fixture_only": True,
                               "Actual": {"sample_count": 16, "call_budget": 32}})
        source = root / "synthetic-source/program.py"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(b"# Synthetic fixture source, never executed.\n")
        source_manifest = root / "operator/source_manifest.json"
        source_entries = {str(source): describe(source)}
        save(source_manifest, source_entries)
        self.spec = {
            "inputs_path": str(prepared.resolve()), "inputs_sha256": describe(prepared)["sha256"],
            "data_manifest_path": str(data_completion.resolve()),
            "data_manifest_sha256": describe(data_completion)["sha256"],
            "source_manifest_path": str(source_manifest),
            "source_manifest_sha256": describe(source_manifest)["sha256"]}
        save(self.worker / "public/spec.json", self.spec)
        save(root / "operator/spec.json", self.spec)
        protected = {"files": {**source_entries, str(source_manifest): describe(source_manifest)},
                     "git": {"synthetic-repo": {"head": "b" * 40, "status": ""}}}
        save(self.worker / "public/protected_before.json", protected)
        save(self.worker / "public/protected_after.json", protected)
        save(self.worker / "public/git_after.json", protected["git"])
        save(self.worker / "public/preservation.json", {"Status": "PASS"})
        entries = {f"synthetic.state.{i}": {"shape": [1], "dtype": "torch.float32",
                                           "sha256": digest(struct.pack("<f", float(i)))} for i in range(63)}
        state = {"state_count": 63, "entries": entries, "aggregate_sha256": digest(encoded(entries))}
        for side in ("before", "after"):
            save(self.worker / f"public/state_{side}.json", state)
            save(self.worker / f"public/config_{side}.json", {"fixture": "constant-config", "init_logit_scale": 1.0})
            save(self.worker / f"public/packages_{side}.json", {"fixture": "no-imported-packages"})
        save(self.worker / "public/checks.jsonl", {"Purpose": "synthetic worker fixture", "Status": "PASS"})
        for index, sample in enumerate(self.samples):
            for seed in (3101, 3202):
                number = len(self.rows) + 1
                late = all_late or seed == 3202
                depth, keys = (32, [8, 16, 32]) if late else (16, [8, 16])
                projections = len(keys)
                counts = {"embedding": 1, "prelude": 2, "prelude_norm": 1, "adapter": depth,
                          "core": 2 * depth, "projection": projections, "coda": 2 * projections,
                          "final_norm": projections, "head": projections,
                          "value_embedding": 1 + depth + projections}
                library = {"embedding_calls": 1, "prelude_block_calls": 2, "prelude_norm_calls": 1,
                           "adapter_calls": depth, "core_block_calls": 2 * depth,
                           "projection_calls": projections, "coda_block_calls": 2 * projections,
                           "final_norm_calls": projections, "head_calls": projections,
                           "value_embedding_calls": 1 + depth + projections,
                           "policy_evaluations": 1, "policy_softmax_calls": 2,
                           "h0_calls": 1, "recurrent_updates": depth, "readouts": projections,
                           "policy_vocabulary_elements": 65536,
                           "readout_clone_elements": projections * 128 * 768,
                           "total_block_calls": 2 + 2 * depth + 2 * projections}
                h0_bytes = struct.pack("<f", 0.0 if seed == 3101 else 0.125) * (128 * 768)
                rng_bytes = bytes([seed % 256]) * 16
                h0 = self.raw(number, "h0", h0_bytes, [1, 128, 768])
                h0["rng_after_init_sha256"] = digest(rng_bytes)
                rng_before = self.raw(number, "rng_before", rng_bytes, [16], "torch.uint8")
                rng_after = self.raw(number, "rng_after", rng_bytes, [16], "torch.uint8")
                outputs, heads, states = {}, [], []
                for d in keys:
                    output = self.skew if late and d >= 16 else self.zero
                    outputs[str(d)] = self.raw(number, f"depth{d}", output, [1, 32768])
                    states.append({"shape": [1, 128, 768], "sha256": digest(h0_bytes)})
                    heads.append({"shape": [1, 128, 32768], "dtype": "torch.float32",
                                  "sha256": self.full_head_hashes[digest(output)], "last_raw_sha256": digest(output)})
                row = {"call": number, "status": "PASS", "cleanup_errors": [], "error": None,
                       "mode": "adaptive", "requested_depth": None, "input_shape": [1, 128],
                       "context": {"article_index": index, "seed": seed,
                                   "source_article_key": sample["source_article_key"]},
                       "input_sha256": sample["raw_input_sha256"],
                       "input_ids_json_sha256": digest(encoded([sample["tokens"]])),
                       "selected_depth": depth, "tv_8_16": self.late_tv if late else 0.0,
                       "actual_counts": counts, "library_counts": library, "outputs": outputs,
                       "observed": {"h0": [h0], "readout_states": states, "head_outputs": heads,
                                    "head_prefixes": [], "head_suffixes": []},
                       "rng_before": rng_before, "rng_after": rng_after,
                       "library_h0_sha256": digest(h0_bytes),
                       "library_rng_before_sha256": digest(rng_bytes), "rng_before_sha256": digest(rng_bytes),
                       "library_rng_after_sha256": digest(rng_bytes), "rng_after_sha256": digest(rng_bytes),
                       "library_state_sha256": {str(d): digest(h0_bytes) for d in keys},
                       "api_observed_seconds": 0.125, "call_total_seconds": 0.25, "policy_seconds": 0.001}
                self.rows.append(row)
        self.write_rows()
        self.seal()

    def raw(self, number, kind, data, shape, dtype="torch.float32"):
        name = f"private/call{number:03d}_{kind}.bin"
        target = self.worker / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return {"path": name, "bytes": len(data), "sha256": digest(data), "shape": shape,
                "dtype": dtype, "byteorder": "little"}

    def write_rows(self):
        (self.worker / "public/calls.jsonl").write_bytes(b"".join(encoded(row) + b"\n" for row in self.rows))
        for row in self.rows:
            save(self.worker / f"public/call_{row['call']:03d}.json", row)
        early = sum(row["selected_depth"] == 16 for row in self.rows)
        routing = {"selected_depth_counts": {"16": early, "32": len(self.rows) - early}}
        records = [{"call": row["call"], "article_index": row["context"]["article_index"],
                    "seed": row["context"]["seed"], "selected_depth": row["selected_depth"],
                    "tv_8_16": row["tv_8_16"], "actual_counts": row["actual_counts"]} for row in self.rows]
        save(self.worker / "public/routing_results.json", {"Status": "PASS", "Actual": {"routing": routing, "records": records}})
        save(self.worker / "public/completion.json", {
            "Status": "PASS", "complete_coverage": True, "Input": {"spec": self.spec}, "Actual": {
                "calls_started": 32, "calls_completed": 32, "groups_completed": 16,
                "loader_attempts": 1, "loader_returns": 1, "error": None, "save_errors": [],
                "preservation": "PASS", "checks": {"PASS": 1, "FAIL": 0, "BLOCKED": 0}, "routing": routing}})

    def seal(self):
        excluded = {"FULL_MANIFEST.json", "public/GIT_BUNDLE_MANIFEST.json"}
        entries = {p.relative_to(self.worker).as_posix(): describe(p) for p in self.worker.rglob("*")
                   if p.is_file() and p.relative_to(self.worker).as_posix() not in excluded}
        save(self.worker / "FULL_MANIFEST.json", {"excluded": sorted(excluded), "entries": entries})
        save(self.worker / "public/GIT_BUNDLE_MANIFEST.json", {
            "entries": {k: v for k, v in entries.items() if k.startswith("public/")}})

    def audit(self):
        instance = AUDIT.Audit(self.root)
        with mock.patch.object(AUDIT.Audit, "audit_data", return_value=self.samples):
            return instance.run()


class AuditTests(unittest.TestCase):
    def test_source_union_excludes33_and_chooses_first16_by_article_id(self):
        selected, excluded = AUDIT.choose(*history())
        self.assertEqual(excluded, [f"source-{i:03d}" for i in range(33)])
        self.assertEqual([a["article_id"] for a in selected], [f"article-{i:03d}" for i in range(16)])
        self.assertEqual([a["source_article_key"] for a in selected], [f"source-{i:03d}" for i in range(59, 43, -1)])

    def test_wrong_historical_source_union_rejected(self):
        partition, old, corrected = history()
        corrected["samples"][-1]["source_article_key"] = "source-000"
        with self.assertRaisesRegex(AUDIT.Reject, "Historical source exclusion counts"):
            AUDIT.choose(partition, old, corrected)

    def test_tv_matches_analytic_two_category_distribution(self):
        self.assertAlmostEqual(AUDIT.tv([0.0, 0.0], [math.log(3.0), 0.0]), 0.25, places=15)
        self.assertEqual(AUDIT.tv([1000.0, -1000.0], [1000.0, -1000.0]), 0.0)
        with self.assertRaises(AUDIT.Reject):
            AUDIT.tv([0.0], [0.0, 1.0])

    def test_fp32_nonfinite_and_invalid_extent_rejected(self):
        self.assertEqual(AUDIT.values(struct.pack("<3f", 0.0, -2.0, 1.5)), [0.0, -2.0, 1.5])
        for raw in (b"", b"abc", struct.pack("<f", math.nan), struct.pack("<f", math.inf)):
            with self.subTest(raw=raw), self.assertRaises(AUDIT.Reject):
                AUDIT.values(raw)

    def test_artifact_path_escape_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.assertEqual(AUDIT.safe(root, "private/file.bin"), (root / "private/file.bin").resolve())
            for name in ("../escape.bin", str((root.parent / "escape.bin").resolve()), "."):
                with self.subTest(name=name), self.assertRaises(AUDIT.Reject):
                    AUDIT.safe(root, name)

    def test_sealed32_calls_accept_both16_and32_exits(self):
        with tempfile.TemporaryDirectory() as folder:
            fixture = SealedFixture(Path(folder))
            result = fixture.audit()
            mechanism = result["mechanism_results"]
            self.assertEqual(mechanism["early_exit_counts"], {"16": 16, "32": 16})
            self.assertEqual(mechanism["article_pair_counts"], {"discordant": 16})
            self.assertEqual(mechanism["per_seed_early_exits"], {"3101": 16, "3202": 0})
            self.assertEqual(mechanism["early_exit_screen"]["Status"], "PASS")
            self.assertEqual(mechanism["engineering_status"], "PASS")
            self.assertEqual(mechanism["quality_improvement"], "NOT TESTED")
            self.assertEqual(len(mechanism["tv_reports"]), 32)
            self.assertEqual(result["describe_cost"]["observed_totals"]["core"], 1536)
            self.assertEqual(result["describe_cost"]["observed_totals"]["head"], 80)
            self.assertTrue(all(not r["scalar_predicate_disagreement"] for r in mechanism["tv_reports"]))

    def test_all32_science_fail_preserves_engineering_pass(self):
        with tempfile.TemporaryDirectory() as folder:
            result = SealedFixture(Path(folder), all_late=True).audit()["mechanism_results"]
            self.assertEqual(result["engineering_status"], "PASS")
            self.assertEqual(result["early_exit_screen"]["Status"], "FAIL")
            self.assertEqual(result["early_exit_screen"]["meaning"], "NO_EARLY_EXIT_ON_THIS_SAMPLE")
            self.assertEqual(result["early_exit_counts"], {"16": 0, "32": 32})

    def test_resigned_wrong_tv_rejected_by_independent_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            fixture = SealedFixture(Path(folder))
            fixture.rows[0]["tv_8_16"] = 0.005
            fixture.write_rows()
            fixture.seal()
            with self.assertRaisesRegex(AUDIT.Reject, "independent scalar TV 1"):
                fixture.audit()

    def test_resigned_wrong_decision_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            fixture = SealedFixture(Path(folder))
            fixture.rows[0]["selected_depth"] = 32
            fixture.write_rows()
            fixture.seal()
            with self.assertRaisesRegex(AUDIT.Reject, "frozen branch 1"):
                fixture.audit()

    def test_resigned_missing_call_row_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            fixture = SealedFixture(Path(folder))
            fixture.rows.pop()
            fixture.write_rows()
            fixture.seal()
            with self.assertRaisesRegex(AUDIT.Reject, "32 condition rows"):
                fixture.audit()

    def test_does_not_import_torch_or_worker(self):
        self.assertFalse(any(name.split(".")[0] in {"torch", "parcae_lm", "receval", "transformers", "run_smoke", "run_routing"}
                             for name in sys.modules))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(AuditTests)
    names = [test.id().replace("__main__.", "test_audit_routing.") for test in suite]
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    text = stream.getvalue()
    print(text, end="")
    report = {"Purpose": "Independent no-model audit fixtures", "Environment": sys.version,
              "Input": "Synthetic stdlib-only sealed evidence; source-token phase mocked",
              "Expected": "All declared tests execute once, no failures/errors/skips",
              "Actual": {"planned": len(names), "run": result.testsRun, "test_ids": names,
                         "failures": len(result.failures), "errors": len(result.errors), "skipped": len(result.skipped),
                         "expected_failures": len(result.expectedFailures), "unexpected_successes": len(result.unexpectedSuccesses)},
              "Status": "PASS" if result.wasSuccessful() and result.testsRun == len(names) and not result.skipped else "FAIL",
              "stdout": text,
              "sources": {name: describe(HERE / name) for name in ("test_audit_routing.py", "audit_routing.py")},
              "formal_model_calls": 0, "real_data_reads": 0}
    if args.report:
        save(args.report, report)
    return 0 if report["Status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
