"""Pure launch/preservation fixtures; no model, Torch or real target inputs."""
import argparse
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest import mock
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("fresh_operator_fixture",ROOT/"execute_once.py")
O=importlib.util.module_from_spec(spec);spec.loader.exec_module(O)

class StartupTests(unittest.TestCase):
    def test_new_base_branch_and_attempt_binding(self):
        self.assertEqual(O.BASE,"bc6d267cdd8cf9306c1bf08b369cf2b791723d3d")
        self.assertEqual(O.BRANCH,"mythos-moda-fresh-cpu-v1")
        self.assertEqual(O.EXPECTED_REPO.as_posix(),"/workspaces/mythos-moda-fresh-cpu-v1")
        self.assertEqual(O.RUN.as_posix(),"/workspaces/mythos-evidence/base_v01/moda_fresh/attempt-v1")
        self.assertFalse(O.INPUTS.is_relative_to(O.RUN))
        self.assertEqual(O.PREPARATION.name,"preparation-v5")
        self.assertEqual(O.CONTINUATION,"b32b63e43ca0ad5c35aeb26904979f769e31bfbe")
        self.assertEqual(O.SOURCE_CORPUS,O.RUN.parent/"preparation-v2/data/corpus.parquet")
        self.assertEqual(O.DATA_AUDIT,O.PREPARATION/"DATA_AUDIT.json")
        self.assertEqual([p.name for p in O.FRESH_PRIOR_DIRS],["preparation-v1","specification-v1","stop-v1","storage-20261102-v1"])
    def test_exact_isolated_entrypoint_imports_before_help(self):
        for name in ("execute_once.py","measure_storage.py","test_startup.py","test_measure_storage.py"):
            result=subprocess.run([sys.executable,"-I","-B",str(ROOT/name),"--help"],capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,(name,result.stdout,result.stderr))
            self.assertIn("usage:",result.stdout)
    def test_publication_uses_new_checkpoint_and_preserves_prior_stop_documents(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/"CHECKPOINT.md").write_text("old blocked checkpoint");(root/"RESULTS_SUMMARY.json").write_text("old blocked summary")
            with mock.patch.object(O,"ROOT",root):
                targets=O.publication_targets()
                self.assertEqual([p.name for p in targets],["evidence","PUBLIC_EXPORT.json","EXTERNAL_EVIDENCE_MANIFEST.json","MODEL_CHECKPOINT.md"])
                self.assertTrue(all(not p.exists() for p in targets))
                (root/"MODEL_CHECKPOINT.md").write_text("existing result")
                self.assertFalse(all(not p.exists() for p in targets))
            self.assertEqual((root/"CHECKPOINT.md").read_text(),"old blocked checkpoint")
    def test_postclosure_budget_counts_new_reports_and_exact_limits(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);private=root/"worker/private";private.mkdir(parents=True)
            (private/"final_sentinel.bin").write_bytes(b"raw"*10)
            (root/"summary.json").write_bytes(b"s"*20);(root/"custody.json").write_bytes(b"c"*40)
            budget=O.publication_budget(root)
            self.assertEqual(budget["run_bytes"],90);self.assertEqual(budget["raw_bytes"],30);self.assertEqual(budget["public_copy_bytes"],60)
            self.assertEqual(budget["projected_total_nonraw_bytes"],120+O.FINALIZATION_ALLOWANCE)
            (root/"publication_quiescence.json").write_bytes(b"q"*10)
            final=O.publication_budget(root);self.assertEqual(final["projected_total_nonraw_bytes"],budget["projected_total_nonraw_bytes"]+20)
            with mock.patch.object(O,"METADATA_BUDGET",final["projected_total_nonraw_bytes"]):self.assertEqual(O.validate_publication_budget(final),final)
            with mock.patch.object(O,"METADATA_BUDGET",final["projected_total_nonraw_bytes"]-1):
                with self.assertRaisesRegex(O.Stop,"exceed12MiB"):O.validate_publication_budget(final)
            low={**final,"free_bytes":O.DISK_RESERVE+final["public_copy_bytes"]+O.FINALIZATION_ALLOWANCE-1}
            with self.assertRaisesRegex(O.Stop,"capacity unavailable"):O.validate_publication_budget(low)
    def test_old_checkouts_do_not_inherit_new_base(self):
        self.assertEqual(O.CHECKOUTS["/workspaces/mythos-moda-residual-cpu-v1"],"d5d6e74888b65b757ecef075f1bd6838f712cc77")
        self.assertEqual(O.CHECKOUTS[str(O.OLD_REPO)],O.BASE)
        self.assertEqual(O.CHECKOUTS["/workspaces/mythos-moda-moe-math-cpu-v1"],"5d9df2733f2b04cab9515db8c51c6b37a7443bda")
        self.assertIn(O.OLD_RUN,O.OLD_RUNS)
        self.assertIn(O.OLD_RUN.parent/"preparation-v2",O.OLD_RUNS)
        for name in ("launch-v2.json","acceptance-v2.json","acceptance-v2.stdout"):
            self.assertIn(O.OLD_RUN.parent/name,O.OLD_PARENT_FILES)
    def test_new_zero_training_budget_does_not_touch_old_reserve(self):
        self.assertEqual(O.RAW_LOGITS_BUDGET,8388608)
        self.assertEqual(O.METADATA_BUDGET,12582912)
        self.assertEqual(O.DISK_RESERVE,268435456)
        self.assertEqual(O.REQUIRED_DISK_BYTES,289406976)
        self.assertEqual(O.FINALIZATION_ALLOWANCE,4194304)
    def test_worker_and_audit_cli_are_new_entrypoints(self):
        c=O.worker_command(Path("/spec"),Path("/out"))
        self.assertEqual(c[:3],[O.PYTHON,"-I","-B"]);self.assertEqual(Path(c[3]).name,"run_fresh.py")
        self.assertEqual(c[-4:],["--spec",str(Path("/spec")),"--out",str(Path("/out"))])
        a=O.audit_command(Path("/spec"),Path("/out"),Path("/audit"))
        self.assertEqual(a[:3],[O.DATA_PYTHON,"-I","-B"]);self.assertEqual(Path(a[3]).name,"audit_stream.py")
        self.assertIn("--final",a);self.assertEqual(a[-6:],["--spec",str(Path("/spec")),"--worker",str(Path("/out")),"--output",str(Path("/audit"))])
    def test_complete_worker_coverage_and_zero_update_contract(self):
        expected=dict(model_loads=1,calls_started=405,calls_completed=405,bridge_calls=5,quality_rows=200,repeat_rows=200,train_steps=0,backward_calls=0,optimizer_steps=0)
        self.assertTrue(O.validate_worker_coverage({"Status":"PASS","Actual":expected}))
        for key,value in expected.items():
            self.assertFalse(O.validate_worker_coverage({"Status":"PASS","Actual":{**expected,key:value+1}}))
        self.assertFalse(O.validate_worker_coverage({"Status":"BLOCKED","Actual":expected}))
        self.assertFalse(O.validate_worker_coverage({"Status":"PASS","Actual":{**expected,"unexpected":1}}))
    def test_spec_binds_new_data_and_all_old_model_references(self):
        pins={str(O.INPUTS):{"bytes":100,"sha256":"a"*64}}
        s=O.make_spec("b"*40,pins)
        self.assertEqual(s["data_sha256"],"a"*64);self.assertEqual(s["freeze_commit"],"b"*40)
        self.assertEqual(s["old_spec_path"],str(O.OLD_RUN/"spec.json"))
        self.assertEqual(s["old_adapter_rows_path"],str(O.OLD_RUN/"worker/public/adapters.json"))
        self.assertEqual(s["old_evaluation_path"],str(O.OLD_RUN/"worker/public/evaluation.json"))
        self.assertEqual(s["run_root"],str(O.RUN));self.assertEqual(s["input_pins"],pins)
    def test_exact_test_inventory_rejects_skips_and_hidden_errors(self):
        actual={"test_ids":["a"],"planned":1,"run":1,"failures":0,"errors":0,"skipped":0,"expected_failures":0,"unexpected_successes":0}
        self.assertTrue(O.validate_test_report({"Status":"PASS","Actual":actual},["a"]))
        for key in ("failures","errors","skipped","expected_failures","unexpected_successes","planned","run"):
            self.assertFalse(O.validate_test_report({"Status":"PASS","Actual":{**actual,key:9}},["a"]))
        self.assertFalse(O.validate_test_report({"Status":"PASS","Actual":actual},["a","a"]))
    def test_exclusive_save_and_confined_source_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for name in ("../escape",str(root.parent/"absolute"),""):
                with self.assertRaises(O.Stop):O.package_path(name,root)
            p=root/"checkpoint.json";O.save(p,{"Status":"BLOCKED"})
            with self.assertRaises(FileExistsError):O.save(p,{"Status":"PASS"})
            self.assertEqual(json.loads(p.read_text())["Status"],"BLOCKED")
    def test_public_policy_keeps_gzip_records_but_excludes_raw_and_data(self):
        for name in ("summary.json","protected_before.json.gz","audit.json.gz","worker/public/evaluation.json.gz","worker/public/rows/row_000.json.gz","worker/public/checks.jsonl","worker/public/checks.jsonl.gz"):
            self.assertTrue(O.public_path(name),name)
        for name in ("../secret.json","other.json.gz","worker/private/final_sentinel.bin","worker/private/failed_logits.bin","worker/private/adapter.pt","data/inputs.json","worker/public/arbitrary.gz"):
            self.assertFalse(O.public_path(name),name)
    def test_scope_collector_keeps_parent_records_preparation_and_untracked(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);main=root/"main";oldtree=root/"oldtree";oldrun=root/"oldrun";prep=root/"prep"
            for p in (main,oldtree,oldrun,prep):p.mkdir()
            files=(main/"tracked.py",main/"untracked.txt",oldtree/"tracked.py",oldrun/"raw.bin",root/"closure.json",prep/"inputs.json")
            for p in files:p.write_bytes(b"same")
            preflight=prep/"STORAGE_PREFLIGHT.json";preflight.write_bytes(b"self")
            def fake_git(path,*args):return "untracked.txt\0" if "--others" in args else "tracked.py\0"
            with mock.patch.object(O,"MAIN_TREE",main),mock.patch.object(O,"OLD_RUNS",[oldrun]),mock.patch.object(O,"PREPARATION",prep),mock.patch.object(O,"FRESH_PRIOR_DIRS",()),mock.patch.object(O,"RUN",root/"unused_namespace"/"attempt-v1"),mock.patch.object(O,"DISCOVERY_FILES",[]),mock.patch.object(O,"history_inputs",return_value={str(main/"untracked.txt"):O.info(main/"untracked.txt")}),mock.patch.object(O,"STORAGE_PREFLIGHT",preflight),mock.patch.object(O,"OLD_PARENT_FILES",[root/"closure.json"]),mock.patch.object(O,"git",side_effect=fake_git):
                actual=O.collect_protected({str(main):{},str(oldtree):{}})
            self.assertEqual(set(actual),{str(p) for p in files});self.assertEqual(len(actual),6)
            self.assertEqual(len({x["sha256"] for x in actual.values()}),1)
    def test_full_old_fresh_namespace_retained_and_current_attempt_excluded(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);prep=root/"preparation-v2";oldprep=root/"preparation-v1";spec=root/"specification-v1";stop=root/"stop-v1";run=root/"attempt-v1"
            for p in (prep,oldprep,spec,stop,run):p.mkdir()
            retained=[oldprep/"trace.stderr",spec/"policy.json.gz",stop/"custody.json",prep/"DATA_AUDIT.json",root/"continuation-v2-restore.json"]
            for p in retained:p.write_bytes(b"same old/new metadata")
            excluded=[run/"live.stdout",prep/"STORAGE_PREFLIGHT.json"]
            for p in excluded:p.write_bytes(b"self/new output")
            with mock.patch.object(O,"OLD_RUNS",[]),mock.patch.object(O,"PREPARATION",prep),mock.patch.object(O,"FRESH_PRIOR_DIRS",(oldprep,spec,stop)),mock.patch.object(O,"RUN",run),mock.patch.object(O,"STORAGE_PREFLIGHT",excluded[1]),mock.patch.object(O,"OLD_PARENT_FILES",[]),mock.patch.object(O,"DISCOVERY_FILES",[]),mock.patch.object(O,"history_inputs",return_value={}):
                actual=O.collect_protected({})
            self.assertEqual(set(actual),set(map(str,retained)));self.assertEqual(len(actual),5)
    def test_collector_never_overwrites_conflicting_frozen_pin(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);p=root/"source.txt";p.write_bytes(b"new bytes")
            with mock.patch.object(O,"MAIN_TREE",root),mock.patch.object(O,"history_inputs",return_value={str(p):{"bytes":1,"sha256":"a"*64}}),mock.patch.object(O,"git",return_value="source.txt\0"):
                with self.assertRaisesRegex(O.Stop,"changed during collection"):O.collect_protected({str(root):{}})

    def test_independent_data_gate_requires_pinned_actual_complete_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);prep=root/"preparation-v2";data=prep/"data";spec=root/"specification-v1"
            data.mkdir(parents=True);spec.mkdir()
            ids=[("%064x"%i) for i in range(20)]
            paths={"DATA_AUDIT":prep/"DATA_AUDIT.json","INPUTS":data/"inputs.json","PREPARATION_MANIFEST":data/"manifest.json","SPECIFICATION":spec,"PREPARATION":prep,"ROOT":root,"TOKENIZER":root/"tokenizer.json","SOURCE_CORPUS":root/"retained-v2-corpus.parquet"}
            O.save(paths["INPUTS"],{"eval":[{"id":i} for i in ids]});O.save(paths["PREPARATION_MANIFEST"],{"Status":"PASS"});O.save(spec/"DATA_SPEC.json",{"schema":"fixture"})
            report={"Status":"PASS","Environment":{"development_only":False,"executable":O.DATA_PYTHON},"Input":{"spec":str(spec/"DATA_SPEC.json"),"spec_sha256":O.info(spec/"DATA_SPEC.json")["sha256"],"prep":str(data)},"Actual":{"input_pin":O.info(paths["INPUTS"]),"preparation_manifest":O.info(paths["PREPARATION_MANIFEST"]),"source_rows":7600,"selected":20,"per_class":{str(i):5 for i in range(4)},"history":{"files":32244},"new_model_calls":0,"new_source_acquisitions":0,"historical_absence_independently_rescanned":False,"selected_ids":ids},"checks":[{"Status":"PASS"}],"check_counts":{"PASS":1,"FAIL":0}}
            for key,path in (("audit_source_pin",root/"audit_data.py"),("shared_parser_pin",root/"data_prepare.py"),("tokenizer_pin",paths["TOKENIZER"]),("source_pin",paths["SOURCE_CORPUS"])):
                path.write_bytes(b"fixture metadata bytes");report["Input"][key]=O.info(path)
            report["Input"]["tokenizer_path"]=str(paths["TOKENIZER"]);report["Actual"]["source_pin"]=report["Input"]["source_pin"]
            report["Actual"]["source_custody"]={"source_file":str(paths["SOURCE_CORPUS"]),"source_pin":O.info(paths["SOURCE_CORPUS"]),"network_requests":0,"copied_corpus_bytes":0}
            O.save(paths["DATA_AUDIT"],report);pins={str(p):O.info(p) for p in (paths["DATA_AUDIT"],paths["INPUTS"],paths["PREPARATION_MANIFEST"],spec/"DATA_SPEC.json")}
            with mock.patch.multiple(O,**paths):
                self.assertEqual(O.validate_data_audit(pins)["selected"],20)
                original_source=report["Actual"]["source_custody"]["source_file"]
                report["Actual"]["source_custody"]["source_file"]=str(data/"unapproved-copy.parquet")
                paths["DATA_AUDIT"].write_text(json.dumps(report));changed={**pins,str(paths["DATA_AUDIT"]):O.info(paths["DATA_AUDIT"])}
                with self.assertRaisesRegex(O.Stop,"retained-source reuse"):O.validate_data_audit(changed)
                report["Actual"]["source_custody"]["source_file"]=original_source
                paths["DATA_AUDIT"].write_text(json.dumps(report));pins[str(paths["DATA_AUDIT"])]=O.info(paths["DATA_AUDIT"])
                without=dict(pins);without.pop(str(paths["DATA_AUDIT"]))
                with self.assertRaisesRegex(O.Stop,"missing/changed pin"):O.validate_data_audit(without)
                for key,value in (("selected",19),("new_model_calls",1),("historical_absence_independently_rescanned",True)):
                    original=report["Actual"][key];report["Actual"][key]=value
                    paths["DATA_AUDIT"].write_text(json.dumps(report));changed={**pins,str(paths["DATA_AUDIT"]):O.info(paths["DATA_AUDIT"])}
                    with self.assertRaises(O.Stop):O.validate_data_audit(changed)
                    report["Actual"][key]=original
                report["Status"]="BLOCKED";paths["DATA_AUDIT"].write_text(json.dumps(report));changed={**pins,str(paths["DATA_AUDIT"]):O.info(paths["DATA_AUDIT"])}
                with self.assertRaisesRegex(O.Stop,"has not passed"):O.validate_data_audit(changed)
    def test_both_original_manifests_must_be_exact_subsets(self):
        a={"/workspaces/old/a":{"bytes":1,"sha256":"a"*64}}
        b=a|{"/workspaces/old/b":{"bytes":1,"sha256":"a"*64}}
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);v1=root/"old.json";O.save(v1,a)
            v2=root/"old.json.gz";receipt=O.storage_codec.write_manifest(v2,b);rp=root/"receipt.json";O.save(rp,receipt)
            with mock.patch.object(O,"PRIOR_V1",v1),mock.patch.object(O,"PRIOR_V1_PIN",O.info(v1)),mock.patch.object(O,"PRIOR_V1_COUNT",1),mock.patch.object(O,"PRIOR_PROTECTED",v2),mock.patch.object(O,"PRIOR_PROTECTED_PIN",O.info(v2)),mock.patch.object(O,"PRIOR_RECEIPT",rp),mock.patch.object(O,"PRIOR_PROTECTED_COUNT",2):
                self.assertTrue(O.prior_scope_preserved(b)["all_original_paths_and_pins_preserved"])
                with self.assertRaisesRegex(O.Stop,"reduced or changed"):O.prior_scope_preserved(a)
                with self.assertRaisesRegex(O.Stop,"reduced or changed"):O.prior_scope_preserved(b|{"/workspaces/old/b":{"bytes":2,"sha256":"a"*64}})
    def test_complete_history_ledger_added_without_dropping_registered_nontext(self):
        self.assertEqual(O.HISTORY_COUNT,32244)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/"original.bin";source.write_bytes(b"historical")
            ledger=root/"history.json.gz";manifest=root/"manifest.json"
            rows=[{"path":str(source),**O.info(source),"Status":"EXCLUDED_REGISTERED_NONTEXT"}]
            raw=json.dumps(rows).encode();ledger.write_bytes(gzip.compress(raw))
            receipt={"physical":O.info(ledger),"canonical":{"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()}}
            report={"Status":"PASS","source_after_status":"PASS","Actual":{"historical_files":1},"artifacts":{"history_ledger.json.gz":receipt}}
            O.save(manifest,report)
            with mock.patch.object(O,"HISTORY_COUNT",1),mock.patch.object(O,"HISTORY_LEDGER",ledger),mock.patch.object(O,"PREPARATION_MANIFEST",manifest):
                self.assertEqual(O.history_inputs(),{str(source):O.info(source)})
                source.write_bytes(b"changed")
                with self.assertRaisesRegex(O.Stop,"changed after preparation"):O.history_inputs()
            with mock.patch.object(O,"HISTORY_LEDGER",ledger),mock.patch.object(O,"PREPARATION_MANIFEST",manifest):
                with self.assertRaisesRegex(O.Stop,"Complete32244"):O.history_inputs()
    def test_premeasured_existing_scope_is_exact_and_freeze_delta_bounded(self):
        entry={"bytes":1,"sha256":"a"*64};existing={"/workspaces/old/a":entry};current={"/workspaces/fresh/a.py":entry}
        _,er=O.storage_codec.pack(existing);proof={"Status":"PASS","Actual":{"existing_inventory_receipt":er,"current_repository_entries":current}}
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);outside=root/"outside.json";O.save(outside,proof);O.save(root/"STORAGE_PREFLIGHT.json",proof)
            with mock.patch.object(O,"ROOT",root),mock.patch.object(O,"REPO",Path("/workspaces/fresh")),mock.patch.object(O,"STORAGE_PREFLIGHT",outside):
                updated=existing|current|{"/workspaces/fresh/new.py":entry};_,receipt=O.storage_codec.pack(updated)
                self.assertEqual(O.validate_storage_preflight(updated,receipt)["changed_entries"],1)
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
    report={"Purpose":"Fresh zero-training CPU launch, evidence-scope and budget interfaces","Environment":sys.version,
        "Input":"Synthetic reports and temporary files only; no real model/data","Expected":"Exact planned checks without skips/errors",
        "Actual":{"test_ids":ids,"planned":len(ids),"run":result.testsRun,"failures":len(result.failures),"errors":len(result.errors),"skipped":len(result.skipped),"expected_failures":len(result.expectedFailures),"unexpected_successes":len(result.unexpectedSuccesses)},
        "Status":"PASS" if result.wasSuccessful() and result.testsRun==len(ids) and not result.skipped else "FAIL"}
    O.save(args.report,report);return 0 if report["Status"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
