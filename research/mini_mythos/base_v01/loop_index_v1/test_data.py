"""Pure data/audit fixtures only; no real corpus or model evaluation."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
import copy
import struct

ROOT = Path(__file__).resolve().parent
def load(name):
    s = importlib.util.spec_from_file_location(name, ROOT / (name + ".py"))
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m
D, A = load("data_loop"), load("audit_loop")


def paragraph(word="alpha"):
    return (word + " scientific narrative explains the history and many interesting findings. ") * 30


def tokenizer(text):
    start = int(hashlib.sha256(text.encode()).hexdigest()[:6],16) % 16000
    return [(start+i)%32768 for i in range(len(text.split()))]


def sample(i, split="train"):
    start = i*200 + (10000 if split == "validation" else 0)
    return {"id": f"{split}-{i}", "normalized_title": f"{split} article {i}", "text_sha256": f"text-{split}-{i}",
            "window_sha256": f"window-{split}-{i}", "tokens": list(range(start,start+129))}


def records(delta_depth=-.02, delta_shared=-.005, loss_correct=0):
    out=[]
    for arm,seed in [("fixed32",None)]+[(a,s) for a in ("shared","depth") for s in (4101,4202)]:
        for es in (5101,5202):
            for i in range(16):
                delta = delta_depth if arm=="depth" else delta_shared if arm=="shared" else 0
                out.append({"arm":arm,"train_seed":seed,"eval_seed":es,"article_id":str(i),
                            "nll_mean":2+i*.01+delta,"correct":32-(loss_correct if arm=="depth" else 0)})
    return out


def adapter_fixture():
    coverage = {"gain": [[True] + [False] * 95]}
    before = {"gain": [[A.sha(struct.pack("<f", 0.0))] * 96]}
    after = copy.deepcopy(before)
    after["gain"][0][0] = A.sha(struct.pack("<f", .1))
    adapter = {"arm": "depth", "train_seed": 4101, "trainable_parameters": 96, "steps": 32,
               "gradient_coverage": coverage, "depth_gradient_coverage": [True] * 32,
               "bank_hashes_before": before, "bank_hashes_after": after,
               "bank_parameter_changes": coverage}
    training = [{"arm": "depth", "train_seed": 4101, "step": i,
                 "nonzero_gradient_banks": copy.deepcopy(coverage),
                 "gradient_norm_before_clip": 1.0, "gain_update_norm": .01,
                 "gain_coordinate_updates": [True] + [False] * 95,
                 "depth_gradient_coverage": [True] * 32,
                 "depth_gain_gradient_norms": [1.0] * 32} for i in range(32)]
    return adapter, training


class DataTests(unittest.TestCase):
    def test_valid_intro_is_one_row(self):
        rows=["", " = Alpha History = \n", "", paragraph(), "", paragraph("later")]
        samples,candidates=D.collect(rows,"train","f"*64,tokenizer)
        self.assertEqual(len(samples),1)
        self.assertEqual(samples[0]["body_row"],3)
        self.assertEqual(samples[0]["tokens"],tokenizer(rows[3])[:129])
        self.assertEqual(candidates[0]["decision"],"ELIGIBLE")
    def test_short_first_row_never_concatenates(self):
        rows=["", " = Alpha History = ", "", "A short sentence.",paragraph()]
        samples,c=D.collect(rows,"train","f"*64,tokenizer)
        self.assertEqual(samples,[])
    def test_formula_candidate_excluded(self):
        rows=["", " = x + y = ", "", paragraph()]
        self.assertEqual(D.collect(rows,"train","f"*64,tokenizer)[0],[])
    def test_nested_section_is_not_article(self):
        rows=["", " = = History = = ", "", paragraph()]
        self.assertEqual(D.collect(rows,"train","f"*64,tokenizer)[0],[])
    def test_title_requires_blank_neighbours(self):
        rows=["previous prose", " = Alpha History = ", "", paragraph()]
        self.assertEqual(D.collect(rows,"train","f"*64,tokenizer)[0],[])
    def test_no_skip_over_subheading(self):
        rows=["", " = Alpha History = ", "", " = = Introduction = = ","",paragraph()]
        self.assertEqual(D.collect(rows,"train","f"*64,tokenizer)[0],[])
    def test_prose_excludes_equals(self):
        self.assertFalse(D.prose_like(paragraph()+" x=y "))
    def test_bad_token_ids_fail(self):
        rows=["", " = Alpha History = ", "", paragraph()]
        with self.assertRaises(D.Stop):
            D.collect(rows,"train","f"*64,lambda _: [32768]*200)
    def test_cross_split_exact_ngram_rejected(self):
        a=[sample(0)]; b=[sample(0,"validation")]
        b[0]["tokens"]=a[0]["tokens"][:]
        with self.assertRaisesRegex(D.Stop,"exact32-token"):
            D.choose(a,b,1)
    def test_duplicate_identity_rejected(self):
        a=[sample(0),sample(0)]; b=[sample(0,"validation"),sample(1,"validation")]
        with self.assertRaisesRegex(D.Stop,"Duplicate"):
            D.choose(a,b,2)
    def test_eligible_title_overlap_excluded_before_selection(self):
        a=[sample(0),sample(1)];b=[sample(0,"validation"),sample(1,"validation")]
        a[0]["normalized_title"]=b[0]["normalized_title"]="same title"
        ta,vb,shared=D.choose(a,b,1)
        self.assertEqual(ta[0]["id"],a[1]["id"])
        self.assertEqual(vb[0]["id"],b[1]["id"])
        self.assertEqual(shared,["same title"])
    def test_insufficient_data_blocks(self):
        with self.assertRaises(D.Stop) as c:
            D.choose([],[],16)
        self.assertEqual(c.exception.status,"BLOCKED")
    def test_identity_changes_with_source(self):
        rows=["", " = Alpha History = ", "", paragraph()]
        a=D.collect(rows,"train","a"*64,tokenizer)[0][0]
        b=D.collect(rows,"train","b"*64,tokenizer)[0][0]
        self.assertNotEqual(a["id"],b["id"])
    def test_collection_hash_order_deterministic(self):
        rows=["", " = Zebra History = ", "", paragraph("zebra"),""," = Alpha History = ","",paragraph()]
        a=D.collect(rows,"train","a"*64,tokenizer)[0]
        self.assertEqual([x["id"] for x in a],sorted(x["id"] for x in a))
        self.assertEqual(a,D.collect(rows,"train","a"*64,tokenizer)[0])


class AuditTests(unittest.TestCase):
    def test_comparison_margin_boundaries(self):
        self.assertEqual(A.comparison_label(-.01, -.01), "IMPROVEMENT")
        self.assertEqual(A.comparison_label(.01, 0.0), "WORSE")
        self.assertEqual(A.comparison_label(-1.0, -.01000001), "WORSE")
        self.assertEqual(A.comparison_label(-.009999, -.01), "NO_QUALIFIED_IMPROVEMENT")
        self.assertEqual(A.comparison_label(.009999, 0.0), "NO_QUALIFIED_IMPROVEMENT")
        with self.assertRaisesRegex(ValueError, "Finite"):
            A.comparison_label(float("nan"), 0.0)
    def test_mixed_seed_interpretation_never_averaged_away(self):
        r = records(delta_depth=-.02)
        for row in r:
            if row["arm"] == "depth" and row["train_seed"] == 4202:
                row["nll_mean"] += .04
        summary = A.summarize(r, [str(i) for i in range(16)])
        result = summary["result_interpretations"]["depth_vs_fixed32"]
        self.assertEqual(result["combined"], "MIXED")
        self.assertEqual(result["per_seed"], {"4101": "IMPROVEMENT", "4202": "WORSE"})
        self.assertEqual(summary["scientific_screens"]["depth_vs_fixed32"]["Status"], "FAIL")
    def test_equal_parameter_gradient_update_coverage(self):
        adapter, training = adapter_fixture()
        report = A.validate_adapter_record(adapter, training)
        self.assertEqual(report, {"gradient_coordinates": 1, "updated_coordinates": 1,
                                  "active_depths": 32, "trainable_parameters": 96})
    def test_coverage_discrepancy_or_missing_depth_rejected(self):
        adapter, training = adapter_fixture()
        adapter["gradient_coverage"]["gain"][0][1] = True
        with self.assertRaisesRegex(ValueError, "aggregate"):
            A.validate_adapter_record(adapter, training)
        adapter, training = adapter_fixture()
        for row in training:
            row["depth_gradient_coverage"][31] = False
            row["depth_gain_gradient_norms"][31] = 0.0
        adapter["depth_gradient_coverage"][31] = False
        with self.assertRaisesRegex(ValueError, "All32"):
            A.validate_adapter_record(adapter, training)
    def test_depth_gradient_norm_consistency(self):
        for replacement in (0.0, -1.0, float("nan"), float("inf")):
            adapter, training = adapter_fixture()
            training[0]["depth_gain_gradient_norms"][0] = replacement
            with self.assertRaisesRegex(ValueError, "norms/flags"):
                A.validate_adapter_record(adapter, training)
    def test_each_step_requires_real_finite_gain_update(self):
        for name in ("gradient_norm_before_clip", "gain_update_norm"):
            for replacement in (0.0, -1.0, float("nan"), float("inf")):
                adapter, training = adapter_fixture()
                training[0][name] = replacement
                with self.assertRaisesRegex(ValueError, "positive"):
                    A.validate_adapter_record(adapter, training)
        for flags in ([False] * 96, [True] * 95, [1] * 96):
            adapter, training = adapter_fixture()
            training[0]["gain_coordinate_updates"] = flags
            with self.assertRaisesRegex(ValueError, "update flags"):
                A.validate_adapter_record(adapter, training)
    def test_parameter_budget_and_zero_vector_update_rejected(self):
        adapter, training = adapter_fixture()
        adapter["trainable_parameters"] = 24576
        with self.assertRaisesRegex(ValueError, "96"):
            A.validate_adapter_record(adapter, training)
        adapter, training = adapter_fixture()
        adapter["bank_hashes_after"] = copy.deepcopy(adapter["bank_hashes_before"])
        adapter["bank_parameter_changes"] = {"gain": [[False] * 96]}
        with self.assertRaisesRegex(ValueError, "update vector"):
            A.validate_adapter_record(adapter, training)
    def test_gain_schema_requires96_boolean_coordinates(self):
        for record in ({"gain": [[False] * 95]}, {"A": [[True] * 96]}, {"gain": [[1] * 96]}):
            with self.assertRaises(ValueError):
                A.gain_row(record)
    def test_uniform_logits_known_nll_and_argmax(self):
        import numpy as np
        import math
        out=A.score_logits(np,np.zeros((64,32768),dtype=np.float32),[0]*64)
        self.assertAlmostEqual(out["nll_mean"],math.log(32768),places=12)
        self.assertEqual(out["correct"],64)
    def test_stable_metric_invariant_to_large_exact_shift(self):
        import numpy as np
        x=np.zeros((64,32768),dtype=np.float32)
        x[:,7]=2
        first=A.score_logits(np,x,[7]*64)
        second=A.score_logits(np,x+np.float32(1000000),[7]*64)
        self.assertAlmostEqual(first["nll_mean"],second["nll_mean"],places=12)
    def test_nonfinite_logits_rejected(self):
        import numpy as np
        x=np.zeros((64,32768),dtype=np.float32);x[0,0]=np.nan
        with self.assertRaisesRegex(ValueError,"finiteness"):
            A.score_logits(np,x,[0]*64)
    def test_wrong_target_alignment_length_rejected(self):
        import numpy as np
        with self.assertRaisesRegex(ValueError,"shape"):
            A.score_logits(np,np.zeros((64,32768),dtype=np.float32),[0]*63)
    def test_all_seeds_required(self):
        r=records()
        for x in r:
            if x["arm"]=="depth" and x["train_seed"]==4202:x["nll_mean"]+=.03
        s=A.summarize(r,[str(i) for i in range(16)])
        self.assertEqual(s["scientific_screens"]["depth_vs_fixed32"]["Status"],"FAIL")
    def test_quality_improvement_and_shared_control_separate(self):
        s=A.summarize(records(),[str(i) for i in range(16)])
        self.assertEqual(s["scientific_screens"]["depth_vs_fixed32"]["Status"],"PASS")
        self.assertEqual(s["scientific_screens"]["shared_vs_fixed32"]["Status"],"FAIL")
        self.assertAlmostEqual(s["comparisons"]["depth_vs_shared_4101"]["delta_nll"],-.015)
    def test_accuracy_guard_blocks_nll_only_win(self):
        s=A.summarize(records(loss_correct=1),[str(i) for i in range(16)])
        self.assertEqual(s["scientific_screens"]["depth_vs_fixed32"]["Status"],"FAIL")
    def test_exact_coverage_missing_row_fails(self):
        with self.assertRaisesRegex(ValueError,"coverage"):
            A.summarize(records()[:-1],[str(i) for i in range(16)])
    def test_duplicate_key_fails(self):
        r=records()
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            A.summarize(r+[r[0]],[str(i) for i in range(16)])
    def test_article_equal_mean_and_correct_denominator(self):
        s=A.summarize(records(),[str(i) for i in range(16)])
        self.assertAlmostEqual(s["means"]["fixed32"]["mean_nll"],2.075)
        self.assertEqual(s["means"]["fixed32"]["correct"],1024)
        self.assertEqual(s["means"]["fixed32"]["scored_observations"],2048)
    def test_zero_gain_is_negative_result_not_error(self):
        s=A.summarize(records(delta_depth=0),[str(i) for i in range(16)])
        self.assertEqual(s["scientific_screens"]["depth_vs_fixed32"]["Status"],"FAIL")


def main():
    p=argparse.ArgumentParser();p.add_argument("--report",type=Path,required=True);args=p.parse_args()
    suite=unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    def flatten(s):
        return [i for t in s for i in (flatten(t) if isinstance(t,unittest.TestSuite) else [t.id()])]
    ids=flatten(suite)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    report={"Purpose":"Pure data split and independent metric/screen fixtures", "Environment":sys.version,
        "Input":"Synthetic rows and metric records only; no real data/weights", "Expected":"All planned tests pass without skips",
        "Actual":{"test_ids":ids,"planned":len(ids),"run":result.testsRun,"failures":len(result.failures),"errors":len(result.errors),
                  "skipped":len(result.skipped),"expected_failures":len(result.expectedFailures),"unexpected_successes":len(result.unexpectedSuccesses)},
        "Status":"PASS" if result.wasSuccessful() and not result.skipped else "FAIL"}
    D.save(args.report,report)
    return 0 if report["Status"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
