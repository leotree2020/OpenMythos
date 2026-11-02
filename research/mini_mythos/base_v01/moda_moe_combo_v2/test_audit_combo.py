"""Synthetic development checks only; no original data, model or target access."""
from __future__ import annotations
import argparse
import copy
import gzip
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import struct
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("independent_combo_audit", HERE / "audit_combo.py")
A = importlib.util.module_from_spec(spec)
spec.loader.exec_module(A)


def population():
    rows = []
    values = {"F": (2.0, 32), "H": (2.2, 30), "Esolo": (1.9, 34), "HE": (1.7, 36), "EjointHoff": (1.95, 33)}
    for domain, count in A.DOMAIN_COUNTS.items():
        for config, seed in A.CONFIGS:
            nll, correct = values[config]
            for article in range(count):
                for h0 in A.EVAL_SEEDS:
                    rows.append({"domain": domain, "config": config, "train_seed": seed, "eval_seed": h0,
                        "article_id": domain + "_%02d" % article, "targets": [0] * 64,
                        "worker_per_token": {"nll": [nll] * 64, "predictions": [0] * correct + [1] * (64 - correct)},
                        "nll_sum": 64 * nll, "nll_mean": nll, "correct": correct, "target_count": 64,
                        "logits_sha256": "a" * 64, "endpoint_wall_ns": 1000000000 + article * 1000000,
                        "endpoint_cpu_ns": 1500000000 + article * 1000000})
    return rows


class AuditTests(unittest.TestCase):
    def test_uniform_matrix_exact_counts_and_stable_nll(self):
        import numpy as np
        raw = np.zeros(A.SHAPE, dtype="<f4").tobytes()
        result = A.compute(raw, [0] * 64)
        self.assertEqual(result["raw"], {"bytes": A.RAW_BYTES, "sha256": hashlib.sha256(raw).hexdigest()})
        self.assertEqual(result["metrics"]["correct"], 64)
        self.assertAlmostEqual(result["metrics"]["nll_mean"], __import__("math").log(32768), places=12)
        self.assertEqual(result["columns"]["predictions"], [0] * 64)
        self.assertEqual(result["columns"]["top2_indices"], [1] * 64)
        self.assertEqual(result["finite_components"], 2097152)
        self.assertEqual([x["offset"] for x in result["chunks"]], [i * 1048576 for i in range(8)])
        self.assertTrue(all(x["sum64"] == x["sum_squares64"] == 0 and x["bytes"] == 1048576 for x in result["chunks"]))

    def test_large_logits_top2_ties_and_gold_are_independent(self):
        import numpy as np
        matrix = np.full(A.SHAPE, -1000, dtype="<f4")
        matrix[:, 7] = 1000; matrix[:, 11] = 1000
        result = A.compute(matrix.tobytes(), [11] * 64)
        self.assertEqual(result["columns"]["predictions"], [7] * 64)
        self.assertEqual(result["columns"]["top2_indices"], [11] * 64)
        self.assertEqual(result["metrics"]["correct"], 0)
        self.assertAlmostEqual(result["metrics"]["nll_mean"], __import__("math").log(2), places=12)
        self.assertEqual(result["columns"]["margin"], [0.0] * 64)

    def test_last_component_nonfinite_rejected(self):
        import numpy as np
        matrix = np.zeros(A.SHAPE, dtype="<f4")
        for invalid in (np.nan, np.inf, -np.inf):
            matrix[-1, -1] = invalid
            with self.subTest(value=str(invalid)), self.assertRaisesRegex(ValueError, "finite"):
                A.compute(matrix.tobytes(), [0] * 64)

    def test_wrong_raw_length_or_target_type_rejected(self):
        raw = bytes(A.RAW_BYTES)
        for value in (raw[:-1], raw + b"x"):
            with self.assertRaisesRegex(ValueError, "8388608"):
                A.compute(value, [0] * 64)
        for targets in ([0] * 63, [True] * 64, [32768] * 64, [-1] * 64, [0.0] * 64):
            with self.subTest(target=targets[0]), self.assertRaises(ValueError):
                A.compute(raw, targets)

    def test_compact_columns_tamper_detected(self):
        result = A.compute(bytes(A.RAW_BYTES), [0] * 64)
        changed = copy.deepcopy(result["columns"]); changed["nll"][3] += 0.01
        with self.assertRaisesRegex(ValueError, "NLL identity"):
            A.metrics_from_columns(changed, [0] * 64)
        changed = copy.deepcopy(result["columns"]); changed["top2_indices"][0] = 0
        with self.assertRaisesRegex(ValueError, "Top-two"):
            A.metrics_from_columns(changed, [0] * 64)

    def test_complete_domain_denominators_and_interaction(self):
        result = A.aggregate(population())
        self.assertEqual(result["total_quality_rows"], 648)
        self.assertEqual(result["reload_rows_added_to_quality"], 0)
        for domain, denominator, rows in (("wiki", 2048, 288), ("news", 2560, 360)):
            values = result["domains"][domain]
            self.assertEqual(values["quality_rows"], rows)
            self.assertEqual(values["means"]["F"]["scored_observations"], denominator)
            self.assertEqual(values["means"]["F"]["accuracy"], 0.5)
            self.assertAlmostEqual(values["comparisons"]["HE_vs_F_4101"]["delta_nll"], -0.3)
            self.assertAlmostEqual(values["comparisons"]["joint_E_inference_interaction_4101"]["delta_nll"], -0.45)
            self.assertEqual(values["comparisons"]["joint_E_inference_interaction_4101"]["delta_accuracy"], 5 / 64)
            self.assertEqual(values["scientific_screens"]["HE_vs_F"], "PASS")
            self.assertEqual(values["secondary_screens"]["H_vs_F"], "FAIL")
            self.assertEqual(set(values["scientific_screens"]), {"HE_vs_F", "HE_vs_H", "HE_vs_Esolo"})
            self.assertEqual(values["comparisons"]["joint_E_inference_interaction_4101"]["screen"], "NOT ASSESSED")
            self.assertEqual(values["timing"]["screen"], "NOT ASSESSED")

    def test_mixed_training_seeds_cannot_be_hidden_by_pooling(self):
        rows = population()
        for row in rows:
            if row["config"] == "HE" and row["train_seed"] == 4202:
                row["worker_per_token"]["nll"] = [2.1] * 64; row["nll_sum"] = 2.1 * 64; row["nll_mean"] = 2.1
        result = A.aggregate(rows)
        for domain in A.DOMAIN_COUNTS:
            self.assertEqual(result["domains"][domain]["scientific_screens"]["HE_vs_F"], "FAIL")
            self.assertEqual(result["domains"][domain]["result_interpretations"]["HE_vs_F"]["combined"], "MIXED")

    def test_duplicate_missing_or_reload_rows_rejected(self):
        rows = population()
        for changed in (rows[:-1], rows + [copy.deepcopy(rows[0])], [copy.deepcopy(rows[0])] + rows[1:-1] + [copy.deepcopy(rows[0])]):
            with self.assertRaises(ValueError):
                A.aggregate(changed)

    def test_changed_targets_or_reported_metrics_rejected(self):
        rows = population(); rows[0]["targets"][0] = 1
        with self.assertRaisesRegex(ValueError, "correct"):
            A.aggregate(rows)

    def test_public_rows_use_external_target_mapping_without_echo(self):
        rows = population(); mapping = {}
        for row in rows:
            targets = row.pop("targets")
            mapping[row["domain"], row["article_id"]] = targets
            row["targets_sha256"] = hashlib.sha256(struct.pack("<64q", *targets)).hexdigest()
        result = A.aggregate(rows, mapping)
        self.assertEqual(result["total_quality_rows"], 648)
        self.assertNotIn('"targets"', json.dumps(result))
        wrong = copy.deepcopy(mapping); wrong["wiki", "wiki_00"][0] = 1
        with self.assertRaisesRegex(ValueError, "target-vector binding"):
            A.aggregate(rows, wrong)
        rows = population(); rows[0]["nll_mean"] += 0.1
        with self.assertRaisesRegex(ValueError, "nll_mean"):
            A.aggregate(rows)

    def test_same_article_initial_state_grid_required(self):
        rows = population(); rows[0]["article_id"] = "unpaired"
        with self.assertRaises(ValueError):
            A.aggregate(rows)
        rows = population(); rows[0]["eval_seed"] = 999
        with self.assertRaisesRegex(ValueError, "h0"):
            A.aggregate(rows)

    def test_joint_inference_counterfactual_not_esolo_substitution(self):
        rows = population()
        for row in rows:
            if row["config"] == "EjointHoff":
                row["worker_per_token"]["nll"] = [1.0] * 64; row["nll_sum"] = 64.0; row["nll_mean"] = 1.0
        result = A.aggregate(rows)
        value = result["domains"]["wiki"]["comparisons"]["joint_E_inference_interaction_4101"]
        self.assertAlmostEqual(value["delta_nll"], 0.5)
        self.assertEqual(value["kind"], "FIXED_JOINT_E_INFERENCE_NONADDITIVITY")

    def test_frozen_screen_boundaries(self):
        self.assertEqual(A.label(-0.01, -0.01), "IMPROVEMENT")
        self.assertEqual(A.label(-0.009999, 0.0), "NO_QUALIFIED_IMPROVEMENT")
        self.assertEqual(A.label(0.01, 0.0), "WORSE")
        self.assertEqual(A.label(-0.1, -0.010001), "WORSE")

    def test_exact_isolated_stream_cli_and_no_private_target_echo(self):
        with tempfile.TemporaryDirectory() as directory:
            targets = Path(directory).resolve() / "targets.json"; targets.write_text(json.dumps([0] * 64))
            command = [sys.executable, "-I", "-B", str(HERE / "audit_combo.py"), "--stream", "--targets", str(targets), "--development-only"]
            result = subprocess.run(command, input=bytes(A.RAW_BYTES), capture_output=True, timeout=30)
            report = json.loads(result.stdout)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertEqual(report["Status"], "PASS")
            self.assertEqual(report["Actual"]["metrics"]["correct"], 64)
            self.assertNotIn("targets", report["Input"])
            self.assertEqual(report["Environment"]["model_imports"], [])
            result = subprocess.run(command, input=bytes(A.RAW_BYTES) + b"x", capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout)["Status"], "FAIL")
            direct = [sys.executable, "-I", "-B", str(HERE / "audit_combo.py"), "--stream", "--targets-json", json.dumps([0] * 64), "--development-only"]
            result = subprocess.run(direct, input=bytes(A.RAW_BYTES), capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(json.loads(result.stdout)["Actual"]["metrics"]["correct"], 64)

    def test_duplicate_nonfinite_json_and_missing_final_inputs_rejected(self):
        for raw in ('{"a":1,"a":2}', '[NaN]'):
            with self.assertRaises(ValueError): A.loads(raw)
        result = subprocess.run([sys.executable, "-I", "-B", str(HERE / "audit_combo.py"), "--final", "--development-only"], capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["Status"], "FAIL")

    @staticmethod
    def final_fixture(root):
        root = root.resolve(); run = root / "run"; public = run / "worker/public"; public.mkdir(parents=True)
        def save(path, value):
            path.parent.mkdir(parents=True, exist_ok=True)
            raw = (json.dumps(value, sort_keys=True) + "\n").encode()
            path.write_bytes(gzip.compress(raw, mtime=0) if path.name.endswith(".gz") else raw)
        spec = {"freeze_commit": "a" * 40}
        for domain, count in A.DOMAIN_COUNTS.items():
            path = root / (domain + ".json")
            save(path, {"context_tokens": 128, "scored_positions": [64, 128], "eval_seeds": [5101, 5202],
                "eval": [{"id": domain + "_%02d" % i, "tokens": [0] * 129} for i in range(count)]})
            spec[domain + "_data"] = {"path": str(path), "pin": A.file_pin(path)}
        spec_path = root / "spec.json"; save(spec_path, spec)
        computed = A.compute(bytes(A.RAW_BYTES), [0] * 64)
        receipt = {"Status": "PASS", "Input": {"targets_sha256": computed["targets_sha256"]},
            "Environment": {"development_only": True, "python": "3.12.3", "numpy": "1.26.4", "model_imports": []}, "Actual": computed}
        unordered = population()
        by = {(r["domain"], r["config"], r["train_seed"], r["eval_seed"], r["article_id"]): r for r in unordered}
        rows = []
        for number in range(648):
            case, slot = divmod(number, 9)
            domain = "wiki" if case < 32 else "news"
            local = case if domain == "wiki" else case - 32
            config, seed = A.CONFIGS[(case + slot) % 9]
            article = domain + "_%02d" % (local // 2)
            row = by[domain, config, seed, A.EVAL_SEEDS[local % 2], article]
            row.update(row_index=number, case_index=case, slot=slot,
                observer={"h0_sha256": "a" * 64, "rng_before_sha256": "b" * 64, "rng_after_sha256": "c" * 64, "seed": A.EVAL_SEEDS[local % 2]})
            rows.append(row)
        for number, row in enumerate(rows):
            row.pop("targets"); row["article_index"] = int(row["article_id"].split("_")[1])
            row["worker_per_token"] = {k: computed["columns"][k] for k in ("nll", "predictions")}
            row.update(computed["metrics"])
            row["logits_sha256"] = computed["raw"]["sha256"]
            row["targets_sha256"] = computed["targets_sha256"]
            row["audit_receipt"] = "audits/row_%03d.json.gz" % number
            save(public / row["audit_receipt"], receipt)
        save(public / "evaluation.json.gz", {"rows": rows})
        independent = {"domains": {}}
        for domain, count in A.DOMAIN_COUNTS.items():
            independent["domains"][domain] = {"means": {
                A.config_name(c, s): {"mean_nll": math.log(32768), "correct": count * 128,
                    "scored_observations": count * 128, "accuracy": 1.0} for c, s in A.CONFIGS},
                "primary_comparisons": {title + "_" + str(seed): {"delta_nll": 0.0, "delta_accuracy": 0.0, "screen": False}
                    for title in ("HE_vs_F", "HE_vs_H", "HE_vs_Esolo") for seed in A.SEEDS},
                "scientific_screens": {title: "FAIL" for title in ("HE_vs_F", "HE_vs_H", "HE_vs_Esolo")}}
        save(public / "results.json", independent)
        for directory, mode, expected in (("worker", "main", A.MAIN_COUNTS), ("reload", "reload", A.RELOAD_COUNTS)):
            save(run / directory / "public/completion.json", {"Status": "PASS", "preservation": "PASS",
                "Input": {"mode": mode, "freeze": spec["freeze_commit"]}, "Expected": expected, "Actual": expected})
        reload_rows = []
        for index, (config, seed) in enumerate(A.CONFIGS):
            reference = next(r for r in rows if r["domain"] == "news" and r["article_index"] == 0 and r["eval_seed"] == 5101
                and (r["config"], r["train_seed"]) == (config, seed))
            reload_rows.append({"config": config, "train_seed": seed, "eval_seed": 5101, "article_id": reference["article_id"],
                "observer": reference["observer"], "logits_sha256": reference["logits_sha256"], "reference_row_index": reference["row_index"],
                "worker_per_token": reference["worker_per_token"], **computed["metrics"]})
            save(run / "reload/public" / ("audits/reload_%d.json.gz" % index), receipt)
        save(run / "reload/public/reload.json", {"Status": "PASS", "rows": reload_rows, "quality_rows_added": 0, "new_interpreter": True})
        raw_path = run / "reload/private/final_sentinel.bin"; raw_path.parent.mkdir(parents=True); raw_path.write_bytes(bytes(A.RAW_BYTES))
        save(run / "reload/public/sentinel.json", {"identity": {"phase": "reload", "config": "EjointHoff", "train_seed": 4202,
            "eval_seed": 5101, "article_id": "news_00"}, "raw": computed["raw"], "audit": "audits/reload_8.json.gz"})
        return run, spec_path, rows, receipt, save

    def test_final_mode_independent_sources_receipts_and_worker_summary(self):
        with tempfile.TemporaryDirectory() as directory:
            run, spec_path, rows, receipt, save = self.final_fixture(Path(directory))
            command = [sys.executable, "-I", "-B", str(HERE / "audit_combo.py"), "--final", "--run-dir", str(run), "--spec", str(spec_path), "--development-only"]
            completed = subprocess.run(command, capture_output=True, timeout=60)
            report = json.loads(completed.stdout)
            self.assertEqual(completed.returncode, 0, report.get("error"))
            self.assertEqual(report["Status"], "PASS")
            self.assertEqual(report["Actual"]["independent_stream_rows"], 648)
            self.assertEqual(report["Actual"]["paired_actual_states"], 72)
            self.assertEqual(report["Actual"]["reload"]["exact_rows"], 9)
            self.assertEqual(report["Actual"]["reload"]["new_quality_rows"], 0)
            self.assertEqual(report["Actual"]["reload"]["retrospective_full_matrices_recomputed"], 1)
            self.assertEqual(report["Actual"]["domains"]["news"]["scientific_screens"]["HE_vs_F"], "FAIL")
            self.assertEqual(report["Actual"]["model_calls"], 0)
            self.assertNotIn('"targets"', json.dumps(report))
            bad = copy.deepcopy(receipt); bad["Actual"]["columns"]["nll"][0] += 0.1
            save(run / "worker/public/audits/row_005.json.gz", bad)
            with self.assertRaisesRegex(ValueError, "NLL identity"):
                A.audit_final(run, spec_path, True)

    def test_final_rejects_public_targets_traversal_source_pin_and_false_screen(self):
        with tempfile.TemporaryDirectory() as directory:
            run, spec_path, rows, receipt, save = self.final_fixture(Path(directory))
            original = copy.deepcopy(rows)
            rows[0]["targets"] = [0] * 64; save(run / "worker/public/evaluation.json.gz", {"rows": rows})
            with self.assertRaisesRegex(ValueError, "No raw target"):
                A.audit_final(run, spec_path, True)
            rows = copy.deepcopy(original); rows[0]["audit_receipt"] = "../../untrusted.json.gz"
            save(run / "worker/public/evaluation.json.gz", {"rows": rows})
            with self.assertRaisesRegex(ValueError, "confined row audit"):
                A.audit_final(run, spec_path, True)
            save(run / "worker/public/evaluation.json.gz", {"rows": original})
            unpaired = copy.deepcopy(original); unpaired[1]["observer"]["h0_sha256"] = "f" * 64
            save(run / "worker/public/evaluation.json.gz", {"rows": unpaired})
            with self.assertRaisesRegex(ValueError, "share actual h0"):
                A.audit_final(run, spec_path, True)
            save(run / "worker/public/evaluation.json.gz", {"rows": original})
            saved = A.read_json(run / "worker/public/results.json")
            saved["domains"]["wiki"]["primary_comparisons"]["HE_vs_F_4101"]["screen"] = True
            save(run / "worker/public/results.json", saved)
            with self.assertRaisesRegex(ValueError, "boolean screen"):
                A.audit_final(run, spec_path, True)
            source = A.read_json(spec_path); source["wiki_data"]["pin"]["sha256"] = "0" * 64; save(spec_path, source)
            with self.assertRaisesRegex(ValueError, "source pin"):
                A.audit_final(run, spec_path, True)

    def test_reload_reference_full_sentinel_and_recorded_counts_are_verified(self):
        with tempfile.TemporaryDirectory() as directory:
            run, spec_path, rows, receipt, save = self.final_fixture(Path(directory))
            path = run / "reload/public/reload.json"; original = A.read_json(path)
            changed = copy.deepcopy(original); changed["rows"][3]["observer"]["h0_sha256"] = "f" * 64; save(path, changed)
            with self.assertRaisesRegex(ValueError, "New-process exact"):
                A.audit_final(run, spec_path, True)
            changed = copy.deepcopy(original); changed["rows"][0], changed["rows"][1] = changed["rows"][1], changed["rows"][0]; save(path, changed)
            with self.assertRaisesRegex(ValueError, "configuration order"):
                A.audit_final(run, spec_path, True)
            save(path, original)
            raw = run / "reload/private/final_sentinel.bin"
            with raw.open("r+b") as stream:
                stream.seek(A.RAW_BYTES - 1); stream.write(b"\x01")
            with self.assertRaisesRegex(ValueError, "exact bytes"):
                A.audit_final(run, spec_path, True)
            raw.write_bytes(bytes(A.RAW_BYTES))
            changed_receipt = copy.deepcopy(receipt); changed_receipt["Actual"]["chunks"][0]["sum64"] = 1.0
            save(run / "reload/public/audits/reload_8.json.gz", changed_receipt)
            with self.assertRaisesRegex(ValueError, "final-sentinel reconstruction"):
                A.audit_final(run, spec_path, True)
            save(run / "reload/public/audits/reload_8.json.gz", receipt)
            completion_path = run / "reload/public/completion.json"
            completion = A.read_json(completion_path); completion["Actual"]["calls_completed"] = 8; save(completion_path, completion)
            with self.assertRaisesRegex(ValueError, "exact counters"):
                A.audit_final(run, spec_path, True)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--report", type=Path, required=True); args = parser.parse_args()
    require_new = not args.report.exists()
    if not require_new:
        raise RuntimeError("Development report exists; preserve prior attempt")
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(AuditTests)
    identifiers = sorted(t.id() for t in suite)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    import numpy as np
    files = {p.name: {"bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in (HERE / "audit_combo.py", Path(__file__))}
    report = {"Purpose": "Development-only independent matrix and paired aggregate checks", "Environment": {"python": sys.version, "numpy": np.__version__},
        "Input": {"source_pins": files, "data": "synthetic only", "real_model_calls": 0},
        "Expected": {"planned": len(identifiers), "failures": 0, "errors": 0, "skipped": 0},
        "Actual": {"planned": len(identifiers), "run": result.testsRun, "test_ids": identifiers, "failures": len(result.failures), "errors": len(result.errors),
            "skipped": len(result.skipped), "expected_failures": len(result.expectedFailures), "unexpected_successes": len(result.unexpectedSuccesses),
            "failure_details": [{"id": t.id(), "traceback": detail} for t, detail in result.failures + result.errors]},
        "Status": "PASS" if result.wasSuccessful() and result.testsRun == len(identifiers) and not result.skipped else "FAIL"}
    with args.report.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, sort_keys=True, indent=2); stream.write("\n")
    return 0 if report["Status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
