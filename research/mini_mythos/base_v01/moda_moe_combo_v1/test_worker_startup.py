"""Development/target helper checks for the exact worker/operator launch contract."""
from __future__ import annotations
import argparse
import ast
import gzip
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent


def load(name, filename):
    sp = importlib.util.spec_from_file_location(name, ROOT/filename)
    m = importlib.util.module_from_spec(sp)
    sys.modules[name] = m
    sp.loader.exec_module(m)
    return m


worker = load("combo_startup_worker", "run_combo.py")
operator = load("combo_startup_operator", "execute_combo.py")


class StartupTests(unittest.TestCase):
    def test_batch1_all_three_actual_call_sites(self):
        import torch
        sample = dict(tokens=list(range(129)))
        ids = worker.input_tensor(torch, sample)
        self.assertEqual(tuple(ids.shape), (1,128))
        self.assertEqual(ids.dtype, torch.long)
        self.assertEqual(ids.tolist(), [list(range(128))])
        # The three implementation call sites must use this checked interface.
        tree = ast.parse((ROOT/"run_combo.py").read_text(encoding="utf-8"))
        for name in ("identities", "training", "eval_endpoint"):
            node = next(x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name == name)
            calls = [x for x in ast.walk(node) if isinstance(x,ast.Call) and isinstance(x.func,ast.Name) and x.func.id == "input_tensor"]
            self.assertEqual(len(calls),1)
        with self.assertRaises(worker.Stop): worker.input_tensor(torch, dict(tokens=[0]*128))

    def test_actual_inherited_loader_returns_list_bridge(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sample = dict(id="s", tokens=list(range(129)))
            wiki = dict(train=[sample]*16, eval=[sample]*16)
            news = dict(eval=[sample]*20)
            a,b = root/"wiki.json",root/"news.json"
            a.write_text(json.dumps(wiki));b.write_text(json.dumps(news))
            spec = dict(wiki_data=dict(path=str(a),pin=worker.pin(a)),news_data=dict(path=str(b),pin=worker.pin(b)),data_path=str(b))
            self.assertEqual(worker.restored_data(spec, news["eval"]),(wiki,news))
            with self.assertRaises(worker.Stop):worker.restored_data(spec,news)
            with self.assertRaises(worker.Stop):worker.restored_data(spec,[])
            b.write_text("{}")
            with self.assertRaises(worker.Stop):worker.restored_data(spec,news["eval"])

    def test_adam_used_unused_steps_and_nonfinite_detection(self):
        import torch
        from torch import nn
        bank=nn.Module()
        bank.a=nn.Parameter(torch.ones(2))
        bank.unused=nn.Parameter(torch.ones(3))
        optimizer=torch.optim.AdamW(bank.parameters(),lr=.001,weight_decay=0.,foreach=False)
        for _ in range(2):
            optimizer.zero_grad(set_to_none=True);bank.a.sum().backward();optimizer.step()
        result=worker.optimizer_receipt(torch,optimizer,bank,dict(a=2,unused=0))
        self.assertEqual(result["a"]["step"],2)
        self.assertFalse(result["unused"]["state_present"])
        with self.assertRaises(worker.Stop):worker.optimizer_receipt(torch,optimizer,bank,dict(a=32,unused=0))
        optimizer.state[bank.a]["exp_avg"][0]=float("nan")
        with self.assertRaises(worker.Stop):worker.optimizer_receipt(torch,optimizer,bank,dict(a=2,unused=0))

    def test_complete_counter_inventory_cannot_accept_exit0_partial(self):
        good=dict(Status="PASS",preservation="PASS",Actual=dict(operator.MAIN_EXPECTED))
        self.assertTrue(operator.validate_count_report(good,operator.MAIN_EXPECTED))
        good["Actual"]["train_steps"]-=1
        self.assertFalse(operator.validate_count_report(good,operator.MAIN_EXPECTED))
        self.assertEqual(operator.MAIN_EXPECTED["calls_completed"]+operator.RELOAD_EXPECTED["calls_completed"],792)
        self.assertEqual(operator.MAIN_EXPECTED["quality_rows"],648)
        self.assertEqual(operator.RELOAD_EXPECTED["reload_rows"],9)

    def test_actual_helper_failure_list_and_numeric_schemas(self):
        for original in ("DEVELOPMENT_COMBO_MODEL_ATTEMPT2.json", "DEVELOPMENT_AUDIT_COMBO_ATTEMPT2.json"):
            observed=json.loads((ROOT/original).read_bytes())
            inventory=dict(test_ids=observed["Actual"]["test_ids"])
            self.assertTrue(operator.valid_helper_report(observed,inventory))
            observed["Actual"]["skipped"]=["unexpected skip"]
            self.assertFalse(operator.valid_helper_report(observed,inventory))
            observed["Actual"]["skipped"]=False
            self.assertFalse(operator.valid_helper_report(observed,inventory))

    def test_case_order_and_balanced_nine_configuration_schedule(self):
        wiki=dict(eval=[dict(id="w"+str(i)) for i in range(16)])
        news=dict(eval=[dict(id="n"+str(i)) for i in range(20)])
        cases=worker.cases(wiki,news)
        self.assertEqual(len(cases),72)
        self.assertEqual(cases[31][:2],("wiki",15))
        self.assertEqual(cases[32][:2],("news",0))
        for arm in range(9):
            for slot in range(9):self.assertEqual(sum((case+slot)%9==arm for case in range(72)),8)
        self.assertEqual(worker.CONFIGS[-1],("EjointHoff",4202))

    def test_publication_never_exports_private_arrays_or_corpus(self):
        for name in ("worker/private/Esolo_4101.pt","reload/private/final_sentinel.bin","../outside.json","/absolute.json"):
            self.assertFalse(operator.public_path(name))
        self.assertTrue(operator.public_path("worker/public/evaluation.json.gz"))
        self.assertTrue(operator.public_path("reload/public/reload.json"))
        private="[1,2,3]"
        observed=operator.public_argv(["python","audit_combo.py","--targets-json",private])
        self.assertNotIn(private,observed)
        self.assertTrue(observed[-1].startswith("REDACTED_SHA256:"))

    def test_actual_raw_vs_nonraw_accounting(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/"worker/private";p.mkdir(parents=True)
            (p/"final_sentinel.bin").write_bytes(b"raw")
            (root/"summary.json").write_bytes(b"{}")
            observed=operator.publication_budget(root)
            self.assertEqual(observed["raw_bytes"],3)
            self.assertEqual(observed["projected_nonraw_bytes"],2+2+operator.GIT_ALLOWANCE)

    def test_source_manifest_and_path_tampering(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/"a.py";p.write_bytes(b"x=1\n")
            (root/"SOURCE_MANIFEST.json").write_text(json.dumps({"a.py":operator.info(p)}))
            operator.validate_source_manifest(root)
            p.write_bytes(b"x=2\n")
            with self.assertRaises(operator.Stop):operator.validate_source_manifest(root)
            (root/"SOURCE_MANIFEST.json").write_text(json.dumps({"../outside":dict(bytes=0,sha256="x")}))
            with self.assertRaises(operator.Stop):operator.validate_source_manifest(root)

    def test_no_silent_prior_scope_reduction_or_changed_external_input(self):
        p="/tmp/immutable_old_evidence"
        value=dict(bytes=1,sha256="a")
        self.assertTrue(operator.prior_scope_closure({p:value},{p:value})["all_paths_retained"])
        with self.assertRaises(operator.Stop):operator.prior_scope_closure({}, {p:value})
        with self.assertRaises(operator.Stop):operator.prior_scope_closure({p:dict(bytes=2,sha256="b")},{p:value})

    def test_source_advance_requires_two_exact_committed_byte_anchors(self):
        path=str(operator.OLD)+"/LATEST"
        before=dict(bytes=1,sha256=operator.sha(b"a"));now=dict(bytes=1,sha256=operator.sha(b"b"))
        with patch.object(operator.subprocess,"check_output",side_effect=[b"a",b"b"]):
            receipt=operator.prior_scope_closure({path:now},{path:before})
            self.assertEqual(len(receipt["exact_published_source_advances"]),1)
        with patch.object(operator.subprocess,"check_output",side_effect=[b"c",b"b"]):
            with self.assertRaises(operator.Stop):operator.prior_scope_closure({path:now},{path:before})

    def test_salvage_can_close_without_reserving_cancelled_future_training(self):
        with tempfile.TemporaryDirectory() as d:
            run=worker.Run(dict(run_root=d),Path(d)/"worker",False)
            try:
                with patch.object(worker,"shutil_free",return_value=worker.RESERVE+1024):
                    with self.assertRaises(worker.Stop):run.guard(10)
                    run.salvage=True
                    run.save("terminal.json",dict(Status="BLOCKED"))
                self.assertEqual(worker.read(run.public/"terminal.json")["Status"],"BLOCKED")
            finally:run.event.close()

    def test_cgroup_memory_limits_override_host_available(self):
        mem="MemAvailable: 8388608 kB\n"
        self.assertEqual(operator.effective_memory(mem,"3221225472","2147483648"),1073741824)
        self.assertEqual(operator.effective_memory(mem,"max","2147483648"),8589934592)
        self.assertEqual(operator.effective_memory(mem,"3221225472","4294967296"),0)

    def test_protected_manifest_canonical_count_and_duplicate_detection(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);p=root/"mapping.json.gz"
            def fixture(raw,records):
                p.write_bytes(gzip.compress(raw,mtime=0))
                return dict(physical=operator.info(p),canonical=dict(bytes=len(raw),sha256=operator.sha(raw)),records=records)
            good=fixture(b'{"/a":{"bytes":1,"sha256":"x"}}',1)
            self.assertEqual(len(operator.bounded_protected_map(p,good)),1)
            wrong={**good,"records":2}
            with self.assertRaises(operator.Stop):operator.bounded_protected_map(p,wrong)
            duplicate=fixture(b'{"/a":1,"/a":2}',2)
            with self.assertRaises(operator.Stop):operator.bounded_protected_map(p,duplicate)
            p.write_bytes(b"changed")
            with self.assertRaises(operator.Stop):operator.bounded_protected_map(p,good)

    def test_child_interruption_installs_operator_stop_handler(self):
        tree=ast.parse((ROOT/"execute_combo.py").read_text(encoding="utf-8"))
        main=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=="main")
        handlers=[x for x in ast.walk(main) if isinstance(x,ast.Call) and isinstance(x.func,ast.Attribute) and x.func.attr=="signal"]
        signals={ast.unparse(x.args[0]) for x in handlers}
        self.assertEqual(signals,{"signal.SIGTERM","signal.SIGINT"})
        command=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=="command")
        self.assertTrue(any(isinstance(x,ast.Call) and isinstance(x.func,ast.Attribute) and x.func.attr=="killpg" for x in ast.walk(command)))


def main():
    cli=argparse.ArgumentParser();cli.add_argument("--report",type=Path,required=True);args=cli.parse_args()
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(StartupTests)
    ids=sorted(test.id() for test in suite)
    result=unittest.TextTestRunner(verbosity=2,failfast=True).run(suite)
    value=dict(Purpose="Exact combo worker launch, old-loader interface and evidence closure controls",
               Environment=dict(development_helpers_only=True,python=sys.version),Input=dict(model_weights_loaded=False),
               Expected=dict(test_ids=ids,planned=len(ids)),Actual=dict(planned=len(ids),run=result.testsRun,test_ids=ids,
                   failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),expected_failures=len(result.expectedFailures),unexpected_successes=len(result.unexpectedSuccesses)),
               Status="PASS" if result.wasSuccessful() and result.testsRun==len(ids) and not result.skipped else "FAIL")
    with args.report.open("x",encoding="utf-8") as stream:json.dump(value,stream,indent=2)
    return 0 if value["Status"]=="PASS" else 2


if __name__=="__main__":raise SystemExit(main())
