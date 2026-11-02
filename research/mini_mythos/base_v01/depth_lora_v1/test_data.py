"""Pure data/audit fixtures only; no real corpus or model evaluation."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent
def load(name):
    s = importlib.util.spec_from_file_location(name, ROOT / (name + ".py"))
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m
D, A = load("data_lora"), load("audit_lora")


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
