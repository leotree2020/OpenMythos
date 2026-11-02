"""Pure launch/preservation fixtures; no model, Torch or real evidence reads."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("moda_operator_fixture", ROOT / "execute_once.py")
O = importlib.util.module_from_spec(spec)
spec.loader.exec_module(O)


class StartupTests(unittest.TestCase):
    def test_new_branch_base_paths(self):
        self.assertEqual(O.BASE,"d5d6e74888b65b757ecef075f1bd6838f712cc77")
        self.assertEqual(O.BRANCH,"mythos-moda-residual-cpu-v2")
        self.assertEqual(O.EXPECTED_REPO.as_posix(),"/workspaces/mythos-moda-residual-cpu-v2")
        self.assertEqual(O.RUN.as_posix(),"/workspaces/mythos-evidence/base_v01/moda_residual/attempt-v2")
        self.assertFalse(O.INPUTS.is_relative_to(O.RUN))
    def test_worker_reload_and_independent_audit_cli(self):
        command=O.worker_command(Path("/spec"),Path("/out"),reload=True)
        self.assertEqual(command[:3],[O.PYTHON,"-I","-B"])
        self.assertEqual(Path(command[3]).name,"run_moda.py")
        self.assertEqual(command[-1],"--reload")
        audit=O.audit_command(Path("/run"),Path("/audit"))
        self.assertEqual(audit[:3],[O.DATA_PYTHON,"-I","-B"])
        self.assertEqual(Path(audit[3]).name,"audit_moda.py")
    def test_compact_budget_includes_all_raw_and_reserve(self):
        self.assertEqual(O.RAW_LOGITS_BUDGET,5*8388608)
        self.assertEqual(O.METADATA_BUDGET,32*1024**2)
        self.assertEqual(O.DISK_RESERVE,256*1024**2)
        self.assertEqual(O.REQUIRED_DISK_BYTES,343932928)
    def test_old_results_and_sparse_source_binding(self):
        self.assertEqual(O.CHECKOUTS["/workspaces/mythos-depth-lora-cpu-v1"],"d2d6ddd1ca92a1bea31c5807306abf52e0f1aa85")
        self.assertEqual(O.CHECKOUTS["/workspaces/mythos-loop-index-cpu-v1"],"76a78d1d9b3d111a832161bd7360af20383e108a")
        self.assertEqual(O.CHECKOUTS["/workspaces/mythos-moda-moe-math-cpu-v1"],"5d9df2733f2b04cab9515db8c51c6b37a7443bda")
        self.assertEqual(O.CHECKOUTS["/workspaces/mythos-moda-residual-cpu-v1"],O.BASE)
        self.assertEqual(len(O.OLD_RUNS),8)
        self.assertEqual(len(O.OLD_PARENT_FILES),5)
        self.assertIn(Path("/workspaces/mythos-moda-residual-v1.log"),O.OLD_PARENT_FILES)
        self.assertIn(Path("/workspaces/mythos-evidence/base_v01/moda_residual/attempt-v1"),O.OLD_RUNS)
        self.assertEqual(O.MODA_SOURCE_SHA,"335c76d353550cbd3bc409ecfae92141b1ab70265429e0f8e33ccdcb5cd06492")
        self.assertFalse(O.BASELINE_EVALUATION.is_relative_to(O.RUN))
    def test_exact_test_inventory_not_exit_only(self):
        actual={"test_ids":["a"],"planned":1,"run":1,"failures":0,"errors":0,"skipped":0,"expected_failures":0,"unexpected_successes":0}
        self.assertTrue(O.validate_test_report({"Status":"PASS","Actual":actual},["a"]))
        for key in ("failures","errors","skipped","expected_failures","unexpected_successes"):
            self.assertFalse(O.validate_test_report({"Status":"PASS","Actual":{**actual,key:1}},["a"]))
    def test_main_and_reload_exact_coverage(self):
        expected={"calls_started":293,"calls_completed":293,"train_steps":128,"eval_rows":160,
                  "zero_control_calls":5,"model_loads":1,"adapters_saved":4,"reload_calls":0}
        self.assertTrue(O.validate_worker_coverage({"Status":"PASS","Actual":expected}))
        for key,value in expected.items():
            self.assertFalse(O.validate_worker_coverage({"Status":"PASS","Actual":{**expected,key:value+1}}))
        self.assertFalse(O.validate_worker_coverage({"Status":"PASS","Actual":expected},reload=True))
    def test_source_paths_and_save_do_not_escape_or_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for name in ("../escape.py",str(root.parent/"absolute.py"),""):
                with self.assertRaises(O.Stop):O.package_path(name,root)
            p=root/"record.json";O.save(p,{"Status":"BLOCKED"})
            with self.assertRaises(FileExistsError):O.save(p,{"Status":"PASS"})
    def test_public_policy_excludes_raw_adapters_and_real_data(self):
        for name in ("worker/public/row_audits/row_000.json","worker/public/rows/row_000.json","summary.json","protected_before.json.gz"):
            self.assertTrue(O.public_path(name))
        for name in ("worker/private/pending_row_000.bin","worker/private/sentinel_row_032.bin","worker/private/a.pt","data/inputs.json","../secret.json","other.json.gz","worker/public/protected_before.json.gz"):
            self.assertFalse(O.public_path(name))
        with tempfile.TemporaryDirectory() as directory:
            progress=O.evidence_progress(Path(directory))
            self.assertEqual(progress["live_audits"]["PASS"],0)
            self.assertEqual(progress["remaining_live_audits"],"NOT TESTED")
            self.assertEqual(progress["retention_actions"]["audited_then_discarded"],0)


    def test_scope_collector_keeps_old_runs_parent_records_and_main_untracked(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);main=root/"main";oldtree=root/"oldtree";oldrun=root/"oldrun"
            for p in (main,oldtree,oldrun):p.mkdir()
            for p in (main/"tracked.py",main/"untracked.txt",oldtree/"tracked.py",oldrun/"raw.bin",root/"closure.json"):p.write_bytes(b"same")
            def fake_git(path,*args):
                if "--others" in args:return "untracked.txt\0"
                return "tracked.py\0"
            with mock.patch.object(O,"MAIN_TREE",main),mock.patch.object(O,"OLD_RUNS",[oldrun]),mock.patch.object(O,"OLD_PARENT_FILES",[root/"closure.json"]),mock.patch.object(O,"git",side_effect=fake_git):
                actual=O.collect_protected({str(main):{},str(oldtree):{}})
            self.assertEqual(set(actual),{str(p) for p in (main/"tracked.py",main/"untracked.txt",oldtree/"tracked.py",oldrun/"raw.bin",root/"closure.json")})
            self.assertEqual(len(actual),5)
            self.assertEqual(len({x["sha256"] for x in actual.values()}),1)

    def test_prior_scope_and_gzip_roundtrip_preserve_distinct_paths(self):
        mapping={"/workspaces/old/a":{"bytes":1,"sha256":"a"*64},"/workspaces/old/b":{"bytes":1,"sha256":"a"*64}}
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);old=root/"old.json";O.save(old,mapping)
            with mock.patch.object(O,"PRIOR_PROTECTED",old),mock.patch.object(O,"PRIOR_PROTECTED_PIN",O.info(old)),mock.patch.object(O,"PRIOR_PROTECTED_COUNT",2):
                self.assertTrue(O.prior_scope_preserved(mapping)["all_original_paths_and_pins_preserved"])
                with self.assertRaisesRegex(O.Stop,"reduced or changed"):O.prior_scope_preserved({"/workspaces/old/a":mapping["/workspaces/old/a"]})
            receipt=O.storage_codec.write_manifest(root/"protected_before.json.gz",mapping)
            O.save(root/"protected_before_receipt.json",receipt)
            self.assertEqual(O.storage_codec.read_manifest(root/"protected_before.json.gz",json.loads((root/"protected_before_receipt.json").read_text())),mapping)
            self.assertLessEqual(receipt["compressed"]["bytes"],2*1024**2)

    def test_exact_premeasured_existing_scope_and_bounded_freeze_delta(self):
        entry={"bytes":1,"sha256":"a"*64};existing={"/workspaces/old/a":entry};current={"/workspaces/v2/a.py":entry}
        _, er=O.storage_codec.pack(existing)
        proof={"Status":"PASS","Actual":{"existing_inventory_receipt":er,"current_repository_entries":current}}
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);outside=root/"outside.json";O.save(outside,proof);O.save(root/"STORAGE_PREFLIGHT.json",proof)
            with mock.patch.object(O,"ROOT",root),mock.patch.object(O,"REPO",Path("/workspaces/v2")),mock.patch.object(O,"STORAGE_PREFLIGHT",outside):
                updated=existing|current|{"/workspaces/v2/new.py":entry};_,receipt=O.storage_codec.pack(updated)
                result=O.validate_storage_preflight(updated,receipt)
                self.assertEqual(result["changed_or_added_current_entries"],1)
                with self.assertRaisesRegex(O.Stop,"path removed"):O.validate_storage_preflight(existing,receipt)
                with self.assertRaisesRegex(O.Stop,"existing protection"):O.validate_storage_preflight(updated|{"/workspaces/old/a":{"bytes":2,"sha256":"a"*64}},receipt)
                with mock.patch.object(O,"FINAL_INVENTORY_DELTA_LIMIT",1):
                    with self.assertRaisesRegex(O.Stop,"64KiB"):O.validate_storage_preflight(updated,receipt)
                outside.write_text("{}")
                with self.assertRaisesRegex(O.Stop,"receipt bytes differ"):O.validate_storage_preflight(updated,receipt)


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--report",type=Path,required=True);args=parser.parse_args()
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(StartupTests);ids=sorted(t.id() for t in suite)
    result=unittest.TextTestRunner(verbosity=2,failfast=True).run(suite)
    report={"Purpose":"MoDA v2 storage-only continuation startup/preservation interfaces","Environment":sys.version,
        "Input":"Synthetic report/path objects only","Expected":"All planned checks pass without skips",
        "Actual":{"test_ids":ids,"planned":len(ids),"run":result.testsRun,"failures":len(result.failures),"errors":len(result.errors),
                  "skipped":len(result.skipped),"expected_failures":len(result.expectedFailures),"unexpected_successes":len(result.unexpectedSuccesses)},
        "Status":"PASS" if result.wasSuccessful() and result.testsRun==len(ids) and not result.skipped else "FAIL"}
    O.save(args.report,report)
    return 0 if report["Status"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
