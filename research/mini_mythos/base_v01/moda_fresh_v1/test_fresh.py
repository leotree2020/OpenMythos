"""Development-only frozen-evaluation contract tests; no140M model or real data."""
import argparse
import ast
import importlib.util
import json
import math
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parent))
import run_fresh as f


def fake_data():
    return dict(eval=[dict(id=f.sha(("article%02d"%i).encode()),tokens=[(j+i)%32768 for j in range(129)]) for i in range(20)],context_tokens=128,scored_positions=[64,128],eval_seeds=[5101,5202])


def fake_records(nll_offsets=None,correct_offsets=None):
    nll_offsets=nll_offsets or {};correct_offsets=correct_offsets or {};rows=[];timings=[]
    for x in f.schedule():
        key=f.name(x["arm"],x["train_seed"]);row={**x,"article_id":f.sha(("article%02d"%x["article_index"]).encode()),
            "nll_mean":3.+nll_offsets.get(key,0.),"correct":20+correct_offsets.get(key,0),"target_count":64}
        if x["pass_index"]==0:rows.append(row)
        timings.append({**x,"article_id":row["article_id"],"endpoint_wall_ns":1000000*(x["arm_index"]+1),"endpoint_cpu_ns":2000000*(x["arm_index"]+1)})
    return rows,timings


class FreshTests(unittest.TestCase):
    def test_latin_schedule_exact_counts_reverse_pairs_and_last_sentinel(self):
        plan=f.schedule();self.assertEqual(len(plan),400)
        self.assertEqual([x["call_index"] for x in plan],list(range(400)))
        for case in range(40):
            a=[r["arm_index"] for r in plan if r["case"]==case and r["pass_index"]==0]
            b=[r["arm_index"] for r in plan if r["case"]==case and r["pass_index"]==1]
            self.assertEqual(a,b[::-1]);self.assertEqual(set(a),set(range(5)))
        for p in range(2):
            for a in range(5):
                for s in range(5):self.assertEqual(sum(r["pass_index"]==p and r["arm_index"]==a and r["slot"]==s for r in plan),8)
        self.assertEqual({k:plan[-1][k] for k in ("call_index","article_index","eval_seed","arm","train_seed")},dict(call_index=399,article_index=19,eval_seed=5202,arm="depth",train_seed=4202))

    def test_data_layout_id_type_length_and_duplicate_rejection(self):
        d=fake_data();self.assertEqual(len(f.validate_data(d)),20)
        for change in (lambda x:x["eval"][0].update(tokens=[1]*128),lambda x:x["eval"][0]["tokens"].__setitem__(0,True),
                       lambda x:x["eval"][0].update(id="article01"),lambda x:x.update(scored_positions=[0,128]),lambda x:x.update(eval_seeds=[5101])):
            d=fake_data();change(d)
            with self.assertRaises(f.Stop):f.validate_data(d)

    def test_threshold_edges_and_worse_direction(self):
        self.assertEqual(f.label(-.01,-.01),"IMPROVEMENT")
        self.assertEqual(f.label(-.009999,0),"NO_QUALIFIED_IMPROVEMENT")
        self.assertEqual(f.label(.01,0),"WORSE")
        self.assertEqual(f.label(-1,-.010001),"WORSE")

    def test_aggregate_two_seed_screens_do_not_hide_opposite_result(self):
        rows,times=fake_records(dict(depth_4101=-.2,depth_4202=.03))
        a=f.aggregate(rows,times)
        self.assertEqual(a["scientific_screens"]["depth_vs_fixed32"],"FAIL")
        self.assertEqual(a["result_interpretations"]["depth_vs_fixed32"]["combined"],"MIXED")
        self.assertAlmostEqual(a["comparisons"]["depth_vs_fixed32_4101"]["delta_nll"],-.2)
        self.assertEqual(a["comparisons"]["depth_vs_fixed32_4101"]["articles_improved"],20)

    def test_aggregate_accuracy_guard_and_article_denominator(self):
        rows,times=fake_records(dict(depth_4101=-.1,depth_4202=-.1),dict(depth_4101=-1))
        a=f.aggregate(rows,times)
        self.assertEqual(a["means"]["fixed32"]["scored_observations"],2560)
        self.assertEqual(a["means"]["fixed32"]["correct"],800)
        self.assertEqual(a["comparisons"]["depth_vs_fixed32_4101"]["delta_accuracy"],-1/64)
        self.assertEqual(a["scientific_screens"]["depth_vs_fixed32"],"FAIL")

    def test_timing_reports_whole_endpoint_sum_and_cpu_not_bounded_by_wall(self):
        rows,times=fake_records();a=f.aggregate(rows,times)["timing"]
        self.assertEqual(a["models"]["fixed32"]["endpoint_total_seconds"],.08)
        self.assertEqual(a["models"]["fixed32"]["process_cpu_total_seconds"],.16)
        self.assertEqual(a["models"]["fixed32"]["endpoint_p95_seconds"],.001)
        self.assertEqual(a["ratios"]["depth_4101_vs_fixed32"],3.)
        self.assertEqual(a["screen"],"NOT ASSESSED")

    def test_missing_rows_and_timing_are_rejected(self):
        rows,times=fake_records()
        with self.assertRaises(f.Stop):f.aggregate(rows[:-1],times)
        with self.assertRaises(f.Stop):f.aggregate(rows,times[:-1])
        rows[0]=rows[1]
        with self.assertRaises(f.Stop):f.aggregate(rows,times)

    def test_endpoint_timer_encloses_input_forward_score_and_excludes_audit(self):
        events=[];w=iter([100,900]);c=iter([200,600])
        def wall():events.append("wall");return next(w)
        def cpu():events.append("cpu");return next(c)
        def tensor(value,**kw):events.append("tensor");return value
        def forward(ids,seed,banks,training):
            events.append("forward");self.assertEqual(len(ids[0]),128);self.assertFalse(training);self.assertEqual(seed,5101);return "logits",{"h0":"x"}
        def score(logits,targets):events.append("score");self.assertEqual(targets,list(range(1,129)));return {"nll_mean":3.}
        out=f.timed_endpoint(types.SimpleNamespace(tensor=tensor,long="long"),types.SimpleNamespace(forward=forward),types.SimpleNamespace(score=score),dict(tokens=list(range(129))),5101,None,wall,cpu)
        self.assertEqual(events,["wall","cpu","tensor","tensor","forward","score","cpu","wall"])
        self.assertEqual(out[-2:],(800,400))

    def test_exclusive_gzip_roundtrip_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"x.json.gz";v={"metrics":[1.,2.,3.]};a=f.save(p,v)
            self.assertEqual(f.read(p),v);self.assertEqual(f.pin(p),a)
            self.assertEqual(f.encoded(v,True),p.read_bytes())
            with self.assertRaises(FileExistsError):f.save(p,{})

    def test_unchanged_reserve_and_new_streamed_budget_boundaries(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve();p=root/"row.json"
            b=dict(raw=0,metadata=0,free=f.RESERVE+f.RAW_BUDGET+f.META_BUDGET)
            with patch.object(f,"budget_snapshot",return_value=b):f.guard(root,p,100)
            b["free"]-=1
            with patch.object(f,"budget_snapshot",return_value=b),self.assertRaises(f.Stop):f.guard(root,p,100)
            with self.assertRaises(f.Stop):f.guard(root,root.parent/"escape",0)

    def test_single_full_raw_allocation_keeps_existing_sentinel(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve();b=dict(raw=f.RAW_BYTES,metadata=100,free=999999999)
            with patch.object(f,"budget_snapshot",return_value=b),self.assertRaises(f.Stop):f.guard(root,root/"failed_logits.bin",f.RAW_BYTES,True)

    def test_state_prefix_normalization_collision_rejected(self):
        self.assertEqual(f.normalize({"module.model.x":1}),{"x":1})
        with self.assertRaises(f.Stop):f.normalize({"x":1,"model.x":2})

    def test_incremental_gzip_checklog_lossless_and_exclusive(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"checks.jsonl.gz";log=f.CheckLog(path)
            rows=[dict(Purpose="complete record "+str(i),Status="PASS",Actual=[i,"中文",None]) for i in range(50)]
            for row in rows:log.write(f.encoded(row))
            log.close();self.assertEqual(f.read_checks(path),rows)
            with self.assertRaises(FileExistsError):f.CheckLog(path)

    def test_worker_has_no_optimizer_backward_or_training_call(self):
        tree=ast.parse(Path(f.__file__).read_text())
        for node in ast.walk(tree):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute):
                self.assertNotIn(node.func.attr,("backward","step","AdamW","Adam","SGD"))
                if node.func.attr=="forward":
                    self.assertTrue(any(k.arg=="training" and isinstance(k.value,ast.Constant) and k.value.value is False for k in node.keywords))


def main():
    p=argparse.ArgumentParser();p.add_argument("--report",type=Path);args=p.parse_args()
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(FreshTests);ids=sorted(t.id() for t in suite)
    result=unittest.TextTestRunner(verbosity=2,failfast=True).run(suite)
    report=dict(Purpose="Development-only fresh-evaluation contract checks",Environment=dict(python=sys.version,development_only=True),Input=dict(real_model=False,real_data=False),Expected=dict(tests=len(ids)),
        Actual=dict(planned=len(ids),run=result.testsRun,test_ids=ids,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),expected_failures=len(result.expectedFailures),unexpected_successes=len(result.unexpectedSuccesses)),
        Status="PASS" if result.wasSuccessful() and result.testsRun==len(ids) and not result.skipped else "FAIL")
    if args.report:
        with args.report.open("x",encoding="utf-8") as stream:json.dump(report,stream,indent=2);stream.write("\n")
    return 0 if result.wasSuccessful() else 1


if __name__=="__main__":raise SystemExit(main())
