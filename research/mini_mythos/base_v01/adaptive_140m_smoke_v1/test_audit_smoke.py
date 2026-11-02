"""Synthetic, standard-library-only audit checks. Never evidence about a model."""
import importlib.util
import json
import math
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location("smoke_independent_audit", Path(__file__).with_name("audit_smoke.py"))
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def save(root, name, value):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, allow_nan=False), encoding="utf-8")


def raw(root, name, shape, dtype="torch.float32"):
    data = b"\0" * (math.prod(shape) * (4 if dtype == "torch.float32" else 1))
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return {"path": name, "bytes": len(data), "sha256": audit.digest(data), "shape": shape, "dtype": dtype, "byteorder": "little"}


def reseal(root):
    excluded = {"FULL_MANIFEST.json", "public/GIT_BUNDLE_MANIFEST.json"}
    entries = {str(p.relative_to(root)).replace("\\", "/"): audit.file_info(p) for p in root.rglob("*") if p.is_file()
               and str(p.relative_to(root)).replace("\\", "/") not in excluded}
    save(root, "FULL_MANIFEST.json", {"entries": entries, "excluded": sorted(excluded)})
    save(root, "public/GIT_BUNDLE_MANIFEST.json", {"entries": {k: v for k, v in entries.items() if k.startswith("public/")}})


def fixture(root):
    """Mock metadata plus synthetic zeros exercises audit plumbing, never forward math."""
    entries = {str(i): {"dtype": "torch.float32", "shape": [1], "bytes": 4, "sha256": "0" * 64} for i in range(63)}
    state = {"entries": entries, "state_count": 63, "aggregate_sha256": audit.digest(audit.canonical(entries))}
    for name, value in (("state", state), ("config", {"synthetic": True}), ("packages", [])):
        for side in ("before", "after"):
            save(root, f"public/{name}_{side}.json", value)
    input_path = root.parent / "synthetic_inputs.json"
    input_path.write_text(json.dumps({"samples": [{"index": i, "tokens": list(range(257))} for i in range(32)]}), encoding="utf-8")
    files = {str(input_path): audit.file_info(input_path)}
    save(root, "public/spec.json", {"inputs_path": str(input_path)})
    save(root, "public/protected_before.json", {"files": files, "git": {}})
    save(root, "public/protected_after.json", {"files": files})
    save(root, "public/git_after.json", {})
    save(root, "public/preservation.json", {"Status": "PASS"})
    save(root, "public/environment.json", {"torch": "2.11.0+cpu", "executable": "/workspaces/mythos-base-v01-cpu312/bin/python",
        "library_sha256": "daa6b5b014f9d5f77cc47e2ba14a7027065c135b2cac7f6bcda58d0e6d6457b8",
        "upstream": "69284c13746e849104f738d6d1a347b1f457df76"})
    save(root, "public/checks.jsonl", {"Status": "PASS"})
    original = list(range(64))
    mutated = original[:32] + [x + 1 for x in original[32:]]
    save(root, "private/prefix_tokens.json", {"original64": original, "causal_mutated64": mutated})
    mapping = {"embedding": "embedding_calls", "prelude": "prelude_block_calls", "prelude_norm": "prelude_norm_calls",
        "adapter": "adapter_calls", "core": "core_block_calls", "projection": "projection_calls", "coda": "coda_block_calls",
        "final_norm": "final_norm_calls", "head": "head_calls", "value_embedding": "value_embedding_calls"}
    rows = []
    modes = [("native", d) for d in (8, 16, 32)] + [("fixed", d) for d in (8, 16, 32)] + [("diagnostic", None), ("adaptive", None), ("adaptive_repeat", None)]
    plan = [(length, seed, mode, depth) for length in (1, 16, 64) for seed in (3101, 3202) for mode, depth in modes] + [(64, 3101, "causal_mutated", None)]
    for number, (length, seed, mode, depth) in enumerate(plan, 1):
        adaptive = mode in ("adaptive", "adaptive_repeat")
        selected = depth if depth else 16 if adaptive else 32
        keys = [depth] if depth else [8, 16] if adaptive else [8, 16, 32]
        readouts = len(keys)
        counts = {"embedding": 1, "prelude": 2, "prelude_norm": 1, "adapter": selected, "core": 2 * selected,
            "projection": readouts, "coda": 2 * readouts, "final_norm": readouts, "head": readouts, "value_embedding": 1 + selected + readouts}
        prefix = f"private/{number}"
        h0 = raw(root, prefix + "_h0.bin", [1, length, 768])
        rng = raw(root, prefix + "_rng.bin", [8], "torch.uint8")
        h0["rng_after_init_sha256"] = rng["sha256"]
        observed = {"h0": [h0], "readout_states": [{"sha256": str(d), "shape": [1, length, 768]} for d in keys],
            "head_outputs": [{"shape": [1, length, 32768], "dtype": "torch.float32"} for d in keys], "head_prefixes": [], "head_suffixes": []}
        if number in (43, 55):
            observed["head_prefixes"] = [raw(root, prefix + f"_prefix{d}.bin", [1, 32, 32768]) for d in keys]
            observed["head_suffixes"] = [{"sha256": str(number)} for d in keys]
        ids = mutated if number == 55 else original[:length]
        row = {"call": number, "context": {"prefix_length": length, "seed": seed}, "mode": mode, "requested_depth": depth,
            "selected_depth": selected, "status": "PASS", "error": None, "cleanup_errors": [], "input_shape": [1, length],
            "input_sha256": audit.digest(struct.pack("<" + "q" * length, *ids)), "input_ids_json_sha256": audit.digest(audit.canonical([ids])),
            "rng_before": rng, "rng_after": rng, "rng_before_sha256": rng["sha256"], "rng_after_sha256": rng["sha256"],
            "observed": observed, "actual_counts": counts, "outputs": {str(d): raw(root, prefix + f"_out{d}.bin", [1, 32768]) for d in keys},
            "api_observed_seconds": 0.01, "call_total_seconds": 0.02}
        if mode != "native":
            library_counts = {mapping[k]: v for k, v in counts.items()}
            library_counts.update(policy_evaluations=int(adaptive), policy_softmax_calls=2 * int(adaptive))
            row.update(library_counts=library_counts, library_h0_sha256=h0["sha256"], library_rng_before_sha256=rng["sha256"],
                       library_rng_after_sha256=rng["sha256"], library_state_sha256={str(d): str(d) for d in keys}, tv_8_16=0.0 if adaptive else None)
        rows.append(row)
        save(root, f"public/call_{number:03d}.json", row)
    (root / "public/calls.jsonl").write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    save(root, "public/completion.json", {"Status": "PASS", "complete_coverage": True, "Actual": {
        "calls_started": 55, "calls_completed": 55, "groups_completed": 6, "loader_attempts": 1, "loader_returns": 1,
        "preservation": "PASS", "error": None, "save_errors": [], "checks": {"PASS": 1, "FAIL": 0, "BLOCKED": 0}}})
    reseal(root)
    return rows


class AuditFixtures(unittest.TestCase):
    def test_tv_known_values_and_extreme_logits(self):
        self.assertEqual(audit.scalar_tv([0, 0], [0, 0]), 0)
        self.assertAlmostEqual(audit.scalar_tv([math.log(3), 0], [0, math.log(3)]), .5, places=15)
        self.assertEqual(audit.scalar_tv([10000, -10000], [-10000, 10000]), 1)

    def test_invalid_fp32_and_nonfinite_rejected(self):
        for data in (b"", b"abc", struct.pack("<f", float("nan")), struct.pack("<f", float("inf"))):
            with self.assertRaises(audit.Rejected):
                audit.fp32_values(data)
        self.assertNotEqual(struct.pack("<f", 0.0), struct.pack("<f", -0.0))

    def test_path_escape_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(audit.Rejected):
                audit.safe_path(Path(tmp), "../escape")

    def test_full_synthetic_pass_then_resigned_signed_zero_tamper_and_coverage_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "worker"
            root.mkdir()
            rows = fixture(root)
            fake_pin = audit.file_info(root.parent / "synthetic_inputs.json")["sha256"]
            with mock.patch.object(audit, "INPUTS_SHA", fake_pin):
                report = audit.Audit(root).run()
            self.assertEqual(report["mechanism_results"]["natural_exit_counts"], {"16": 6, "32": 0})
            self.assertEqual(report["mechanism_results"]["natural_branch_coverage"]["32"], "NOT TESTED")
            # Re-sign every manifest: detection must come from native identity, not an old hash.
            meta = rows[3]["outputs"]["8"]
            path = root / meta["path"]
            path.write_bytes(struct.pack("<f", -0.0) + path.read_bytes()[4:])
            meta["sha256"] = audit.file_info(path)["sha256"]
            save(root, "public/call_004.json", rows[3])
            (root / "public/calls.jsonl").write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
            reseal(root)
            with mock.patch.object(audit, "INPUTS_SHA", fake_pin), self.assertRaisesRegex(audit.Rejected, "independently match native bytes 4"):
                audit.Audit(root).run()
            # Complete-looking worker PASS cannot bypass missing condition coverage.
            (root / "public/calls.jsonl").write_text("\n".join(json.dumps(row) for row in rows[:-1]), encoding="utf-8")
            reseal(root)
            with mock.patch.object(audit, "INPUTS_SHA", fake_pin), self.assertRaisesRegex(audit.Rejected, "exact55"):
                audit.Audit(root).run()

    def test_incomplete_worker_is_not_implementation_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            save(root, "public/completion.json", {"Status": "BLOCKED"})
            with self.assertRaises(audit.Incomplete):
                audit.Audit(root).run()


if __name__ == "__main__":
    unittest.main(verbosity=2, failfast=True)
