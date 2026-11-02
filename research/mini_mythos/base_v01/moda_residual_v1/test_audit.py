"""Synthetic independent-metric, retention, and compact evidence budget checks."""
import argparse
import copy
import json
import math
from pathlib import Path
import struct
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import audit_row as R
import audit_moda as A
ROOT=Path(__file__).resolve().parent


def rows():
    result=[]
    for arm,seed in [("fixed32",None)]+[(a,s) for a in ("shared","depth") for s in (4101,4202)]:
        for es in (5101,5202):
            for i in range(16):
                result.append({"arm":arm,"train_seed":seed,"eval_seed":es,"article_id":str(i),
                    "article_index":i,"nll_mean":2-(.02 if arm=="depth" else .005 if arm=="shared" else 0),"correct":32})
    return result


def train_fixture(arm="depth"):
    report={"arm":arm,"train_seed":4101,"steps":32,"trainable_parameters":12288,
        "gradient_coverage":True,"depth_gradient_coverage":[True]*32,"parameter_changes":{"o_proj":True},
        "features_before":{"w":{"sha256":"a"*64}},"features_after":{"w":{"sha256":"a"*64}},
        "history_gradient_active":{"key":arm=="depth","value":arm=="depth"}}
    records=[]
    for t in range(32):
        present=[True]*31+[False] if arm=="depth" else [False]*32
        norms=([0.0 if t==0 else .1]*31+[None]) if arm=="depth" else [None]*32
        records.append({"arm":arm,"train_seed":4101,"step":t,"nonzero_o_proj_gradient":True,
            "gradient_norm_before_clip":1.0,"output_update_norm":.01,"depth_gradient_coverage":[True]*32,
            "depth_o_proj_gradient_norms":[.1]*32,"branch_trace":{"arm":arm,"writer_calls":32,
            "read_lengths":list(range(32)) if arm=="depth" else [0]*32},
            "history_gradients":{k:{"present":present[:],"norms":norms[:]} for k in ("key","value")}})
    return report,records


def evidence_budget():
    # Sizes come from the actual full-width adapter/AdamW/RNG serialization
    # fixture, never from real pretrained weights or an assumed parameter count.
    measurements=[]
    for p in sorted(ROOT.glob("DEVELOPMENT_ADAPTER_ATTEMPT*.json")):
        value=R.read(p)
        sizes=value.get("Actual",{}).get("four_adapter_checkpoint_sizes",[])
        if value.get("Status")=="PASS" and len(sizes)==4 and all(type(n)is int and n>0 for n in sizes):
            measurements.append((p,sizes))
    if not measurements:raise ValueError("Complete four-checkpoint serialization fixture required")
    checkpoint_report,checkpoint_sizes=measurements[-1]
    number=-1.2345678901234567e+200  # Long finite JSON float spelling, sizing only.
    columns={k:[32767]*64 if k in ("predictions","top2_indices") else [number]*64
             for k in ("nll","predictions","gold","max","shifted_logsumexp","logsumexp","top1","top2","top2_indices","margin")}
    receipt={"Purpose":"x"*160,"Environment":{"python":"x"*512,"executable":"x"*256,"development_only":False},
        "Input":{"row_path":"x"*256,"row_input":{"bytes":65536,"sha256":"a"*64},"spec_sha256":"a"*64,
                 "identity":{"arm":"shared","train_seed":4202,"eval_seed":5202,"article_id":"a"*64,"article_index":15}},
        "Expected":"x"*200,"Status":"PASS","utc":"x"*40,
        "Actual":{"raw":{"bytes":8388608,"sha256":"a"*64},"metrics":{"nll_mean":number,"nll_sum":number,"correct":64,"target_count":64},
                  "columns":columns,"finite_components":2097152,
                  "chunks":[{"index":i,"offset":i*1048576,"bytes":1048576,"sha256":"a"*64,
                    "sum64":number,"sum_squares64":number,"min64":number,"max64":number} for i in range(8)],
                  "baseline_reference":{"path":"x"*256,"pin":{"bytes":8388608,"sha256":"a"*64},
                     "evaluation_pin":{"bytes":999999,"sha256":"a"*64},"observer_stable":{k:"a"*64 for k in R.STABLE_OBSERVER}}}}
    per_receipt=len(json.dumps(receipt,separators=(",",":"),allow_nan=False).encode())+1
    # Row metadata includes per-token worker values; bound at 8KiB in each copy.
    # 160 individual row files plus a duplicated evaluation.json and both public
    # copies are budgeted. Other public reports have a separate explicit envelope.
    receipt_copies=2*160*per_receipt
    row_metadata_copies=2*160*(6144+8192)
    # Target read-only measurement: prior math protected_before.json=961111B.
    # New stage reserves 2MiB per protected manifest copy and enforces that
    # envelope before training. 128 training/history rows reserve8KiB each.
    protected_manifest_copies=2*2*1024**2
    training_history_copies=2*128*8192
    other_public_copies=protected_manifest_copies+training_history_copies+6*1024**2
    git_and_finalization=4*1024**2
    training_example=train_fixture("depth")[1][-1]
    training_example.update(article_id="a"*64,h0_seed=1420231,observer={k:"a"*64 for k in R.STABLE_OBSERVER},
                            loss=number,seconds=number,optimizer_step=32,targets=128,epoch=1)
    def worst_floats(value):
        if isinstance(value,float):return number
        if isinstance(value,list):return [worst_floats(x) for x in value]
        if isinstance(value,dict):return {k:worst_floats(v) for k,v in value.items()}
        return value
    measured_training_bytes=len(json.dumps(worst_floats(training_example),allow_nan=False).encode())+1
    if measured_training_bytes>8192:raise ValueError("Training/history serialization exceeds preregistered envelope")
    actual={"measured_receipt_bytes":per_receipt,"live_receipt_copies_bytes":receipt_copies,
        "row_metadata_copies_bytes":row_metadata_copies,"four_checkpoint_sizes":checkpoint_sizes,
        "four_checkpoint_total_bytes":sum(checkpoint_sizes),"other_public_copies_allowance":other_public_copies,
        "git_and_finalization_allowance":git_and_finalization,
        "protected_manifest_copies_allowance":protected_manifest_copies,"training_history_copies_allowance":training_history_copies,
        "measured_training_history_row_bytes":measured_training_bytes,
        "misc_checks_audit_process_summary_public_copies_allowance":6*1024**2}
    actual["projected_total_nonraw_bytes"]=receipt_copies+row_metadata_copies+sum(checkpoint_sizes)+other_public_copies+git_and_finalization
    return {"Purpose":"Pre-freeze compact evidence serialization budget","Environment":"Local CPU synthetic serialization only",
        "Input":{"checkpoint_report":checkpoint_report.name,"checkpoint_report_pin":R.info(checkpoint_report),
                 "receipt_fixture":"Longest finite float spellings, bounded256-character paths;160 rows and public copies",
                 "prior_protected_manifest_measurement":{"bytes":961111,"source":"root target read-only /workspaces/mythos-evidence/base_v01/moda_moe_math/attempt-v1/protected_before.json"},
                 "resource_revision":"Attempt1 nominal16MiB proof was incomplete for custody/history/publiccopy overhead; corrected before execution freeze to32MiB with explicit measured fixtures and envelopes; no old protocol changed",
                 "limits":{"individual_row_metadata_bytes":6144,"evaluation_row_metadata_bytes":8192,
                           "other_public_copies_bytes":other_public_copies,"git_finalization_bytes":git_and_finalization}},
        "Expected":{"nonraw_bytes_max":32*1024**2},"Actual":actual,
        "Status":"PASS" if actual["projected_total_nonraw_bytes"]<=32*1024**2 else "FAIL"}


class AuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import numpy as np
        cls.np=np;cls.raw=np.zeros((64,32768),dtype="<f4").tobytes()
        cls.result=R.compute(np,cls.raw,[0]*64)
    def test_uniform_nll_tie_rule_and_complete_chunks(self):
        r=self.result
        self.assertAlmostEqual(r["metrics"]["nll_mean"],math.log(32768),places=12)
        self.assertEqual(r["columns"]["predictions"],[0]*64)
        self.assertEqual(r["columns"]["top2_indices"],[1]*64)
        self.assertEqual(r["columns"]["margin"],[0.0]*64)
        self.assertEqual(len(r["chunks"]),8)
        self.assertEqual(sum(c["bytes"] for c in r["chunks"]),8388608)
    def test_nonfinite_and_shape_rejected(self):
        raw=bytearray(self.raw);raw[:4]=struct.pack("<f",float("nan"))
        with self.assertRaisesRegex(ValueError,"finite"):R.compute(self.np,raw,[0]*64)
        with self.assertRaisesRegex(ValueError,"byte"):R.compute(self.np,self.raw[:-4],[0]*64)
    def test_constant_shift_and_gold_alignment(self):
        x=self.np.zeros((64,32768),dtype="<f4");x[:,7]=2
        a=R.compute(self.np,x.tobytes(),[7]*64)
        b=R.compute(self.np,(x+self.np.float32(1000000)).tobytes(),[7]*64)
        self.assertEqual(a["columns"]["nll"],b["columns"]["nll"])
        self.assertEqual(a["metrics"]["correct"],64)
    def test_per_token_mismatch_cannot_cancel_in_mean(self):
        r=copy.deepcopy(self.result)
        row={**r["metrics"],"worker_per_token":{"nll":r["columns"]["nll"][:],"predictions":[0]*64}}
        R.compare_worker(row,r)
        row["worker_per_token"]["nll"][0]+=.01;row["worker_per_token"]["nll"][1]-=.01
        with self.assertRaisesRegex(ValueError,"token NLL"):R.compare_worker(row,r)
    def test_compact_columns_reconstruct_metrics_and_reject_tamper(self):
        self.assertEqual(R.validate_columns(self.result["columns"],[0]*64)["correct"],64)
        c=copy.deepcopy(self.result["columns"]);c["gold"][0]=1
        with self.assertRaisesRegex(ValueError,"NLL"):R.validate_columns(c,[0]*64)
    def test_retention_selection_is_frozen_not_result_dependent(self):
        data={"eval":[{"id":"first"}]}
        self.assertEqual(R.expected_retention({"arm":"fixed32"},data),"historical_bridge")
        self.assertEqual(R.expected_retention({"arm":"depth","article_id":"first","eval_seed":5101},data),"sentinel")
        self.assertEqual(R.expected_retention({"arm":"shared","article_id":"first","eval_seed":5202},data),"audited_then_discarded")
    def test_identity_includes_frozen_article_index(self):
        row={"arm":"depth","train_seed":4101,"eval_seed":5101,"article_id":"a","article_index":3,"extra":False}
        self.assertEqual(len(R.identity(row)),5)
        self.assertEqual(R.identity(row)["article_index"],3)
    def test_baseline_bridge_requires_raw_h0_rng_and_targets(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/"public").mkdir();(root/"private").mkdir()
            path=root/"private/old.bin";path.write_bytes(self.raw)
            old={"arm":"fixed32","train_seed":None,"eval_seed":5101,"article_id":"a","article_index":0,
                "shape":[64,32768],"dtype":"float32-le","logits_sha256":R.sha(self.raw),"targets_sha256":"b"*64,
                "h0_sha256":"c"*64,"observer":{"h0_sha256":"c"*64,"rng_before_sha256":"d"*64,
                "rng_after_sha256":"e"*64,"seed":5101},"logits_file":"private/old.bin"}
            ev=root/"public/evaluation.json";R.save(ev,{"rows":[old]})
            spec={"baseline_evaluation_path":str(ev),"baseline_evaluation_pin":R.info(ev)}
            self.assertEqual(R.historical_bridge(spec,old,self.result)["path"],str(path.resolve()))
            bad=copy.deepcopy(old);bad["observer"]["rng_after_sha256"]="0"*64
            with self.assertRaisesRegex(ValueError,"RNG"):R.historical_bridge(spec,bad,self.result)
    def test_parameter_history_and_depth_gradient_controls(self):
        for arm in ("shared","depth"):
            adapter,records=train_fixture(arm)
            self.assertEqual(A.validate_training(adapter,records)["active_depths"],32)
            records[0]["output_update_norm"]=0
            with self.assertRaisesRegex(ValueError,"positive"):A.validate_training(adapter,records)
    def test_fake_history_and_feature_changes_rejected(self):
        adapter,records=train_fixture()
        records[0]["history_gradients"]["key"]["norms"][0]=.1
        with self.assertRaisesRegex(ValueError,"Initial zero"):A.validate_training(adapter,records)
        adapter,records=train_fixture();adapter["features_after"]={"changed":True}
        with self.assertRaisesRegex(ValueError,"feature"):A.validate_training(adapter,records)
    def test_screens_and_mixed_seeds_not_averaged_away(self):
        records=rows();s=A.summarize(records,[str(i) for i in range(16)])
        self.assertEqual(s["scientific_screens"]["depth_vs_fixed32"]["Status"],"PASS")
        for row in records:
            if row["arm"]=="depth" and row["train_seed"]==4202:row["nll_mean"]+=.04
        self.assertEqual(A.summarize(records,[str(i) for i in range(16)])["result_interpretations"]["depth_vs_fixed32"]["combined"],"MIXED")
        with self.assertRaisesRegex(ValueError,"coverage"):A.summarize(records[:-1],[str(i) for i in range(16)])
    def test_exact_margin_boundaries_and_accuracy_guard(self):
        self.assertEqual(A.comparison_label(-.01,-.01),"IMPROVEMENT")
        self.assertEqual(A.comparison_label(.01,0),"WORSE")
        self.assertEqual(A.comparison_label(-1,-.01000001),"WORSE")
        self.assertEqual(A.comparison_label(0,0),"NO_QUALIFIED_IMPROVEMENT")
    def test_no_torch_import_and_evidence_budget(self):
        self.assertNotIn("torch",sys.modules)
        proof=evidence_budget()
        self.assertEqual(proof["Status"],"PASS",proof)


def main():
    p=argparse.ArgumentParser();p.add_argument("--report",type=Path,required=True);p.add_argument("--budget-report",type=Path);args=p.parse_args()
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(AuditTests);ids=sorted(t.id() for t in suite)
    result=unittest.TextTestRunner(verbosity=2,failfast=True).run(suite)
    report={"Purpose":"Independent compact-evidence audit fixtures","Environment":sys.version,
        "Input":"Synthetic8MiB logits, fabricated training records, measured toy adapter serialization; no real model/data",
        "Expected":"All planned fixtures pass,32MiB nonraw budget",
        "Actual":{"test_ids":ids,"planned":len(ids),"run":result.testsRun,"failures":len(result.failures),"errors":len(result.errors),
                  "skipped":len(result.skipped),"expected_failures":len(result.expectedFailures),"unexpected_successes":len(result.unexpectedSuccesses)},
        "Status":"PASS" if result.wasSuccessful() and result.testsRun==len(ids) and not result.skipped else "FAIL"}
    R.save(args.report,report)
    if args.budget_report:R.save(args.budget_report,evidence_budget())
    return 0 if report["Status"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
