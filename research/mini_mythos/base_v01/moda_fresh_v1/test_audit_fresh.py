"""Development-only independent scoring/timing audit fixtures; no real model/data."""
import argparse
import copy
import json
import math
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parent))
import audit_stream as a
import run_fresh as f
from test_fresh import fake_data,fake_records


class AuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import numpy as np
        cls.np=np
        cls.raw=bytes(f.RAW_BYTES)
        cls.uniform=a.compute(np,cls.raw,[0]*64)

    def test_uniform_matrix_exact_tie_rule_and_nll(self):
        x=self.uniform
        self.assertEqual(x["metrics"]["correct"],64)
        self.assertAlmostEqual(x["metrics"]["nll_mean"],math.log(32768),places=12)
        self.assertEqual(x["columns"]["predictions"],[0]*64)
        self.assertEqual(x["columns"]["top2_indices"],[1]*64)
        self.assertEqual(x["columns"]["margin"],[0.]*64)

    def test_all_chunks_hashes_sizes_and_finite_counts(self):
        x=self.uniform
        self.assertEqual(x["finite_components"],2097152)
        self.assertEqual(x["raw"],dict(bytes=f.RAW_BYTES,sha256=f.sha(self.raw)))
        self.assertEqual(len(x["chunks"]),8)
        for i,c in enumerate(x["chunks"]):
            self.assertEqual(c["offset"],i*1048576);self.assertEqual(c["bytes"],1048576)
            self.assertEqual(c["sha256"],f.sha(bytes(1048576)));self.assertEqual(c["sum64"],0)

    def test_shape_excess_bytes_bad_targets_and_nonfinite_rejected(self):
        for raw,targets in ((self.raw[:-1],[0]*64),(self.raw+b"x",[0]*64),(self.raw,[0]*63),(self.raw,[True]*64)):
            with self.assertRaises(ValueError):a.compute(self.np,raw,targets)
        for value in (float("nan"),float("inf"),float("-inf")):
            raw=struct.pack("<f",value)+self.raw[4:]
            with self.assertRaises(ValueError):a.compute(self.np,raw,[0]*64)

    def test_target_alignment_and_shift_invariance(self):
        np=self.np;x=np.zeros((64,32768),dtype="<f4");x[:,7]=2.
        p=a.compute(np,x.tobytes(),[7]*64);q=a.compute(np,(x+8.).tobytes(),[7]*64)
        self.assertEqual(p["metrics"]["correct"],64)
        self.assertAlmostEqual(p["metrics"]["nll_mean"],q["metrics"]["nll_mean"],places=12)
        wrong=a.compute(np,x.tobytes(),[6]*64)
        self.assertEqual(wrong["metrics"]["correct"],0)
        self.assertAlmostEqual(wrong["metrics"]["nll_mean"]-p["metrics"]["nll_mean"],2.,places=12)

    def test_worker_per_token_mismatch_cannot_cancel_in_mean(self):
        x=self.uniform;row={**x["metrics"],"worker_per_token":dict(nll=list(x["columns"]["nll"]),predictions=[0]*64)}
        a.compare_worker(row,x)
        row["worker_per_token"]["nll"][0]+=.1;row["worker_per_token"]["nll"][1]-=.1
        with self.assertRaisesRegex(ValueError,"per-token"):a.compare_worker(row,x)

    def test_worker_exact_argmax_and_aggregate_contract(self):
        x=self.uniform;row={**x["metrics"],"worker_per_token":dict(nll=list(x["columns"]["nll"]),predictions=[0]*64)}
        row["worker_per_token"]["predictions"][0]=1
        with self.assertRaisesRegex(ValueError,"argmax"):a.compare_worker(row,x)
        row["worker_per_token"]["predictions"][0]=0;row["nll_mean"]+=1e-6
        with self.assertRaisesRegex(ValueError,"aggregate"):a.compare_worker(row,x)

    def test_compact_metric_identities_and_tamper_detection(self):
        c=self.uniform["columns"];m=a.metrics_from_columns(c,[0]*64)
        self.assertTrue(a.same_recursive(m,self.uniform["metrics"]))
        for key,value in (("nll",0.),("margin",-1.),("predictions",32768),("top2_indices",0)):
            x=copy.deepcopy(c);x[key][0]=value
            with self.assertRaises(ValueError):a.metrics_from_columns(x,[0]*64)

    def _paired(self):
        rows,times=fake_records();data=fake_data()["eval"]
        for r in rows+times:
            observer=dict(h0_sha256="h"+str(r["case"]),rng_before_sha256="before"+str(r["eval_seed"]),rng_after_sha256="after"+str(r["eval_seed"]),seed=r["eval_seed"])
            r.update(observer=observer,logits_sha256="hash_"+str(r["case"])+"_"+str(r["arm_index"]))
        return rows,times,data

    def test_all400_timing_order_identities_pairing_and_balance(self):
        rows,times,data=self._paired();a.validate_timing(times,rows,data)
        times[0],times[1]=times[1],times[0]
        with self.assertRaisesRegex(ValueError,"order"):a.validate_timing(times,rows,data)

    def test_repeat_mismatch_or_changed_h0_is_not_timing_noise(self):
        rows,times,data=self._paired();times[200]["logits_sha256"]="different"
        with self.assertRaisesRegex(ValueError,"exact"):a.validate_timing(times,rows,data)
        rows,times,data=self._paired();times[200]["observer"]["h0_sha256"]="different"
        with self.assertRaisesRegex(ValueError,"exact"):a.validate_timing(times,rows,data)

    def test_wrong_article_seed_and_zero_time_rejected(self):
        for key,value in (("article_id","wrong"),("eval_seed",999),("endpoint_wall_ns",0)):
            rows,times,data=self._paired();times[12][key]=value
            with self.assertRaises(ValueError):a.validate_timing(times,rows,data)

    def test_recursive_compare_checks_structure_types_and_nan(self):
        self.assertTrue(a.same_recursive({"a":[1,2.]},{"a":[1,2.+1e-11]}))
        self.assertFalse(a.same_recursive({"a":1},{"a":True}))
        self.assertFalse(a.same_recursive({"a":1},{"a":1,"b":2}))
        self.assertFalse(a.same_recursive(float("nan"),float("nan")))

    def test_independent_order_and_aggregate_do_not_call_worker_implementations(self):
        rows,times=fake_records(dict(depth_4101=-.02,depth_4202=-.03),dict(depth_4101=1,depth_4202=2))
        expected=f.aggregate(rows,times);plan=f.schedule()
        with patch.object(f,"aggregate",side_effect=AssertionError("worker aggregate called")),patch.object(f,"schedule",side_effect=AssertionError("worker schedule called")),patch.object(f,"label",side_effect=AssertionError("worker label called")):
            actual=a.independent_aggregate(rows,times);self.assertEqual(a.independent_schedule(),plan)
        self.assertTrue(a.same_recursive(actual,expected))
        changed=copy.deepcopy(expected);changed["comparisons"]["depth_vs_fixed32_4101"]["delta_nll"]+=.1
        self.assertFalse(a.same_recursive(actual,changed))
        changed=copy.deepcopy(expected);changed["timing"]["paired_per_article"][0]["ratio"]+=.1
        self.assertFalse(a.same_recursive(actual,changed))

    def test_full200row400timing_evidence_reconciliation_and_tampered_summary(self):
        with tempfile.TemporaryDirectory() as directory:
            worker=Path(directory).resolve()/"worker";public=worker/"public";private=worker/"private"
            (public/"rows").mkdir(parents=True);(public/"row_audits").mkdir();private.mkdir()
            root=worker.parent;data=fake_data()
            for row in data["eval"]:row["tokens"]=[0]*129
            datapath=root/"data.json";f.save(datapath,data)
            spec=dict(data_path=str(datapath),data_sha256=f.pin(datapath)["sha256"],spec_path=str(root/"spec.json"),
                old_adapter_rows_path=str(root/"adapters.json"),old_evaluation_path=str(root/"oldrows.json"),baseline_evaluation_path=str(root/"baserows.json"))
            f.save(root/"spec.json",spec)
            states={"p%d"%i:{"sha256":"a"*64} for i in range(63)};adapters={f.name(arm,seed):{"o_proj":{"sha256":"b"*64}} for arm,seed in f.ARMS[1:]}
            for n,v in (("base_state_before.json",states),("base_state_after.json",states),("adapters_before.json",adapters),("adapters_after.json",adapters)):f.save(public/n,v)
            f.save(root/"adapters.json",dict(rows=[dict(arm=arm,train_seed=seed,state=adapters[f.name(arm,seed)]) for arm,seed in f.ARMS[1:]]))
            log=f.CheckLog(public/"checks.jsonl.gz");log.write(f.encoded(dict(Status="PASS",Purpose="Fixture completeness")));log.close()
            f.save(public/"completion.json",dict(Status="PASS",preservation="PASS",Actual=f.EXPECTED,checks=dict(PASS=1,FAIL=0,BLOCKED=0),seconds=1.,load_seconds=.1,audit_seconds=.2,serialization_seconds=.3,peak_rss_bytes=1234))
            rows=[];timings=[];refs={}
            for planned in f.schedule():
                sample=data["eval"][planned["article_index"]];arm=planned["arm"]
                observer=dict(h0_sha256=f.sha(str(planned["case"]).encode()),rng_before_sha256="b"*64,rng_after_sha256="c"*64,seed=planned["eval_seed"],core_block_calls=[32,32],adapter_calls=32)
                timing={**planned,"article_id":sample["id"],"observer":observer,"logits_sha256":self.uniform["raw"]["sha256"],"endpoint_wall_ns":123456789,"endpoint_cpu_ns":223456789};timings.append(timing)
                if planned["pass_index"]:continue
                n=len(rows);rowpath=public/("rows/row_%03d.json.gz"%n);auditpath=public/("row_audits/row_%03d.json.gz"%n)
                row={**planned,"article_id":sample["id"],"observer":observer,"logits_sha256":timing["logits_sha256"],**self.uniform["metrics"],
                    "worker_per_token":dict(nll=list(self.uniform["columns"]["nll"]),predictions=[0]*64),"targets_sha256":f.sha(struct.pack("<64q",*([0]*64))),
                    "shape":[64,32768],"dtype":"float32-le","row_input_file":str(rowpath.relative_to(worker)),"row_audit_file":str(auditpath.relative_to(worker)),
                    "branch_trace":dict(arm=arm,writer_calls=0 if arm=="fixed32" else 32,write_depths=[] if arm=="fixed32" else list(range(32)),read_lengths=[] if arm=="fixed32" else list(range(32)) if arm=="depth" else [0]*32)}
                f.save(rowpath,row);rows.append(row);refs[f.rowkey(row)]=row
                f.save(auditpath,dict(Status="PASS",Environment=dict(numpy="1.26.4",development_only=False,executable=f.DATA_PYTHON),Input=dict(identity=f.identity(row),row_input=f.pin(rowpath),spec_sha256=f.pin(root/"spec.json")["sha256"],data_sha256=spec["data_sha256"]),Actual=self.uniform))
                command=[f.DATA_PYTHON,"-I","-B",str(Path(a.__file__).resolve()),"--spec",spec["spec_path"],"--row",str(rowpath),"--output",str(auditpath)]
                f.save(public/("row_audits/process_%03d.json.gz"%n),dict(command=command,returncode=0,stdout="",stderr=""))
            old=[]
            for arm,seed in f.ARMS:
                r=refs[arm,seed,5101,data["eval"][0]["id"]]
                old.append(dict(arm=arm,train_seed=seed,article_id=r["article_id"],eval_seed=5101,logits_sha256=r["logits_sha256"],observer=r["observer"],Status="PASS"))
            f.save(public/"oldbridges.json",dict(Status="PASS",rows=old));f.save(root/"oldrows.json",dict(rows=old[1:]));f.save(root/"baserows.json",dict(rows=old[:1]))
            f.save(public/"evaluation.json.gz",dict(rows=rows));f.save(public/"timing.json.gz",dict(rows=timings));summary=f.aggregate(rows,timings);f.save(public/"results.json",summary)
            path=private/"final_sentinel.bin";path.write_bytes(self.raw);r=refs[f.rowkey(timings[-1])]
            f.save(public/"sentinel.json",dict(identity=f.identity(r),path="private/final_sentinel.bin",raw=f.pin(path),first_pass_row=r["row_input_file"],first_pass_audit=r["row_audit_file"]))
            checked=[]
            def check(purpose,okay,actual=None):
                checked.append(purpose)
                if not okay:raise AssertionError(purpose)
            result=a.final_audit(spec,worker,self.np,check)
            self.assertEqual(result["rows"],200);self.assertEqual(result["repeats"],200);self.assertGreater(len(checked),1600)
            self.assertEqual(result["retrospective_full_rows_unavailable"],199)
            summary["means"]["depth_4101"]["mean_nll"]+=1.
            (public/"results.json").write_bytes(f.encoded(summary))
            with self.assertRaisesRegex(AssertionError,"independently reconstructed"):a.final_audit(spec,worker,self.np,check)

    def test_auditor_imports_no_model_or_torch(self):
        self.assertFalse(any(n.split(".")[0] in ("torch","parcae_lm","receval","transformers") for n in sys.modules))


def main():
    p=argparse.ArgumentParser();p.add_argument("--report",type=Path);args=p.parse_args()
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(AuditTests);ids=sorted(t.id() for t in suite)
    result=unittest.TextTestRunner(verbosity=2,failfast=True).run(suite)
    report=dict(Purpose="Independent fresh stream scoring and timing audit fixtures",Environment=dict(python=sys.version,development_only=True),Input=dict(real_model=False,real_data=False),Expected=dict(tests=len(ids)),
        Actual=dict(planned=len(ids),run=result.testsRun,test_ids=ids,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),expected_failures=len(result.expectedFailures),unexpected_successes=len(result.unexpectedSuccesses)),
        Status="PASS" if result.wasSuccessful() and result.testsRun==len(ids) and not result.skipped else "FAIL")
    if args.report:
        with args.report.open("x",encoding="utf-8") as stream:json.dump(report,stream,indent=2);stream.write("\n")
    return 0 if result.wasSuccessful() else 1


if __name__=="__main__":raise SystemExit(main())
