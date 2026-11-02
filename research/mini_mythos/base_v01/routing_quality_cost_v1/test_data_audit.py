"""Synthetic label provenance and independent-audit fixtures; never loads a model."""
import argparse
import copy
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location("fixture_"+name, HERE/(name+".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


D, A = load("data_quality"), load("audit_quality")


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(D.canonical(value)+b"\n")


def source_fixture():
    rows, articles, samples, token_map = [], [], [], {}
    for i in range(60):
        heading = len(rows)
        title, body = f"Synthetic title{i}", f"Synthetic body{i}"
        rows.extend((title,body))
        tokens = list(range(i*400,i*400+300))
        token_map[body] = tokens
        key = D.sha(D.canonical({"corpus_sha256":D.PINS["corpus"],"heading_row":heading,"title":title}))
        article = {"source_article_key":key,"heading_row":heading,"body_rows":[heading+1],"text_sha256":D.sha(body.encode()),
                   "article_id":D.sha((title+"\n"+body).encode()),"full_token_count":len(tokens)}
        articles.append(article)
        if i < 16:
            prefix=tokens[:128]
            samples.append({**article,"index":i,"tokens":prefix,"input_ids_sha256":D.sha(D.canonical(prefix)),
                            "raw_input_sha256":D.sha(struct.pack("<128q",*prefix))})
    digest=D.sha(D.canonical(rows))
    partition={"rows_sha256":digest,"all_row_sha256":[D.sha(x.encode()) for x in rows],"articles":articles}
    ledger={"rows_sha256":digest,"accepted_heading_rows":list(range(0,120,2)),
            "decisions":[{"row":i,"decision":"ACCEPT_TITLE"} for i in range(0,120,2)]}
    return rows,partition,ledger,{"context_tokens":128,"seeds":[3101,3202],"samples":samples},token_map


def quality_cases(delta=0.0):
    return [{"case_index":i,"article_index":i//2,"seed":(3101,3202)[i%2],"adaptive_depth":32,
             "adaptive":{"nll":1+delta,"top1":0,"correct":True},"fixed32":{"nll":1.,"top1":0,"correct":True},"delta_nll":delta} for i in range(32)]


def timing_rows(ratio=.9):
    return [{"phase":p,"round":r,"case_index":c,"position":pos,"arm":arm,
             "elapsed_seconds":ratio if arm=="adaptive" else 1.,"cpu_seconds":2.*(ratio if arm=="adaptive" else 1.)}
            for p,r,c,pos,arm in A.expected_timing_order()]


class WorkerFixture:
    """Hand-authored raw outputs and metadata, not produced by worker code.

Audit data reconstruction and terminal seals are separately tested/static
reviewed; this fixture substitutes those two setup methods only. All64 call
records, counter/pair/output checks,130 timing records and scoring remain real.
"""
    def __init__(self, root):
        self.root,self.w=root,root/"worker"
        (self.w/"private").mkdir(parents=True)
        (self.w/"public").mkdir()
        self.zero=self.raw("zero.bin",struct.pack("<f",0.)*32768,[1,32768])
        self.skew=self.raw("skew.bin",struct.pack("<f",1.)*16384+struct.pack("<f",0.)*16384,[1,32768])
        self.h0=self.raw("h0.bin",struct.pack("<f",0.)*(128*768),[1,128,768])
        self.h0["rng_after_init_sha256"]="synthetic-state"
        self.rng=self.raw("rng.bin",bytes(range(16)),[16],"torch.uint8")
        self.samples,self.labels,self.records,self.references,self.pairs=[],[],[],{},[]
        for i in range(16):
            tokens=[i+1]*128
            self.samples.append({"tokens":tokens,"source_article_key":f"source{i}",
                                 "raw_input_sha256":D.sha(struct.pack("<128q",*tokens))})
            self.labels.append({"target_token":0})
        for case in range(32):
            article,seed=case//2,(3101,3202)[case%2]
            arms=("adaptive","fixed32") if case%2==0 else ("fixed32","adaptive")
            for arm in arms:
                number=len(self.records)+1
                depth=16 if arm=="adaptive" and case<2 else 32
                keys=([8,16] if depth==16 else [8,16,32]) if arm=="adaptive" else [32]
                count=len(keys)
                outputs={str(d):self.zero for d in keys}
                if arm=="adaptive" and depth==32:
                    outputs["16"]=self.skew
                variation=A.tv(A.values((self.w/self.zero["path"]).read_bytes()),A.values((self.w/outputs.get("16",self.zero)["path"]).read_bytes())) if arm=="adaptive" else None
                counts={"embedding":1,"prelude":2,"prelude_norm":1,"adapter":depth,"core":2*depth,"projection":count,"coda":2*count,"final_norm":count,"head":count,"value_embedding":1+depth+count}
                mapping={"embedding":"embedding_calls","prelude":"prelude_block_calls","prelude_norm":"prelude_norm_calls","adapter":"adapter_calls","core":"core_block_calls","projection":"projection_calls","coda":"coda_block_calls","final_norm":"final_norm_calls","head":"head_calls","value_embedding":"value_embedding_calls"}
                library={mapping[k]:v for k,v in counts.items()}
                library.update(h0_calls=1,recurrent_updates=depth,readouts=count,readout_clone_elements=count*128*768,total_block_calls=2+2*depth+2*count,
                               policy_evaluations=int(arm=="adaptive"),policy_softmax_calls=2*int(arm=="adaptive"),policy_vocabulary_elements=65536*int(arm=="adaptive"))
                sample=self.samples[article]
                row={"call":number,"status":"PASS","cleanup_errors":[],"error":None,"mode":"adaptive" if arm=="adaptive" else "fixed",
                     "requested_depth":None if arm=="adaptive" else 32,"selected_depth":depth,"tv_8_16":variation,
                     "context":{"case_index":case,"article_index":article,"seed":seed,"arm":arm,"phase":"quality","source_article_key":sample["source_article_key"]},
                     "input_shape":[1,128],"input_sha256":sample["raw_input_sha256"],"input_ids_json_sha256":D.sha(D.canonical([sample["tokens"]])),
                     "actual_counts":counts,"library_counts":library,"outputs":outputs,
                     "observed":{"h0":[self.h0],"readout_states":[{"shape":[1,128,768],"sha256":"state"+str(d)} for d in keys],
                                 "head_outputs":[{"shape":[1,128,32768],"dtype":"torch.float32","last_raw_sha256":outputs[str(d)]["sha256"]} for d in keys]},
                     "rng_before":self.rng,"rng_after":self.rng,"library_h0_sha256":self.h0["sha256"],
                     "rng_before_sha256":self.rng["sha256"],"rng_after_sha256":self.rng["sha256"],
                     "library_rng_before_sha256":self.rng["sha256"],"library_rng_after_sha256":self.rng["sha256"],
                     "library_state_sha256":{str(d):"state"+str(d) for d in keys}}
                self.records.append(row)
                self.references[(case,arm)]=row
                write(self.w/f"public/call_{number:03d}.json",row)
            a,f=self.references[(case,"adaptive")],self.references[(case,"fixed32")]
            self.pairs.append({"case_index":case,"article_index":article,"seed":seed,"source_article_key":sample["source_article_key"],"order":list(arms),
                               "adaptive_call":a["call"],"fixed32_call":f["call"],"adaptive_depth":a["selected_depth"],"tv_8_16":a["tv_8_16"],
                               "adaptive_logits":a["outputs"][str(a["selected_depth"])],"fixed32_logits":f["outputs"]["32"],
                               "paired_h0_sha256":self.h0["sha256"],"paired_rng_before_sha256":self.rng["sha256"],"paired_rng_after_sha256":self.rng["sha256"]})
        (self.w/"public/calls.jsonl").write_text("".join(json.dumps(x)+"\n" for x in self.records),encoding="utf-8")
        write(self.w/"public/quality_pairs.json",{"Status":"PASS","Actual":{"pairs":self.pairs}})
        self.timings=[]
        for ordinal,base in enumerate(timing_rows(1.1),1):
            ref=self.references[(base["case_index"],base["arm"])]
            row={**base,"ordinal":ordinal,"article_index":base["case_index"]//2,"seed":(3101,3202)[base["case_index"]%2],
                 "status":"PASS","error":None,"quality_reference_call":ref["call"],"selected_depth":ref["selected_depth"],"tv_8_16":ref["tv_8_16"],
                 "h0_sha256":ref["library_h0_sha256"],"input_sha256":ref["input_sha256"],"rng_before_sha256":ref["rng_before_sha256"],
                 "rng_after_sha256":ref["rng_after_sha256"],"library_counts":ref["library_counts"],"selected_logits":ref["outputs"][str(ref["selected_depth"]) ]}
            self.timings.append(row)
        self.save_timing()

    def raw(self,name,b,shape,dtype="torch.float32"):
        path=self.w/"private"/name
        path.write_bytes(b)
        return {"path":"private/"+name,"shape":shape,"dtype":dtype,"byteorder":"little","bytes":len(b),"sha256":D.sha(b)}

    def save_timing(self):
        (self.w/"public/timing_calls.jsonl").write_text("".join(json.dumps(x)+"\n" for x in self.timings),encoding="utf-8")
        write(self.w/"public/timing_summary.json",{"Status":"PASS","Actual":{"warmup_calls":2,"timed_calls":128,"timing_rows":self.timings}})

    def audit(self):
        audit=A.Audit(self.root)
        with mock.patch.object(audit,"audit_data",return_value=(self.samples,self.labels)),mock.patch.object(audit,"audit_seal",return_value=None):
            return audit.run()


class DataAuditTests(unittest.TestCase):
    def test_actual_next_token_not_last_prefix_token(self):
        """Labels are the129th body token while prefixes retain exact128 tokens."""
        rows,p,l,inputs,m=source_fixture()
        before=copy.deepcopy(inputs)
        labels=D.derive_labels(rows,p,l,inputs,lambda x:m[x])
        self.assertEqual([x["target_token"] for x in labels],[i*400+128 for i in range(16)])
        self.assertEqual(inputs,before)
        self.assertNotEqual(labels[0]["target_token"],inputs["samples"][0]["tokens"][-1])

    def test_changed_prefix_rejected(self):
        rows,p,l,inputs,m=source_fixture()
        inputs["samples"][0]["tokens"][1]+=1
        with self.assertRaises(D.Stop):D.derive_labels(rows,p,l,inputs,lambda x:m[x])

    def test_changed_body_boundary_rejected(self):
        rows,p,l,inputs,m=source_fixture()
        inputs["samples"][0]["body_rows"]=[3]
        with self.assertRaises(D.Stop):D.derive_labels(rows,p,l,inputs,lambda x:m[x])

    def test_changed_sample_order_rejected(self):
        rows,p,l,inputs,m=source_fixture()
        inputs["samples"][0],inputs["samples"][1]=inputs["samples"][1],inputs["samples"][0]
        with self.assertRaises(D.Stop):D.derive_labels(rows,p,l,inputs,lambda x:m[x])

    def test_invalid_token_rejected(self):
        rows,p,l,inputs,m=source_fixture()
        m["Synthetic body0"][128]=True
        with self.assertRaises(D.Stop):D.derive_labels(rows,p,l,inputs,lambda x:m[x])

    def test_nll_golden_and_first_index_tie(self):
        self.assertAlmostEqual(A.score([0.,0.],1)["nll"],math.log(2),places=15)
        self.assertEqual(A.score([0.,0.],1)["top1"],0)
        self.assertAlmostEqual(A.score([1000.,998.],0)["nll"],math.log1p(math.exp(-2)),places=12)
        self.assertAlmostEqual(A.score([1e300,1e300],0)["nll"],math.log(2),places=15)

    def test_invalid_target_and_nonfinite_score_rejected(self):
        for logits,target in (([0.,1.],2),([0.,1.],True),([float("nan"),1.],0)):
            with self.assertRaises(A.Reject):A.score(logits,target)

    def test_quality_mean_and_per_case_margins(self):
        c=quality_cases(.01)
        self.assertEqual(A.quality_summary(c)["screen"]["Status"],"PASS")
        c[0]["delta_nll"]+=1e-6
        self.assertEqual(A.quality_summary(c)["screen"]["Status"],"FAIL")
        c=quality_cases(-.1)
        c[0]["delta_nll"]=.100001
        self.assertEqual(A.quality_summary(c)["screen"]["Status"],"FAIL")

    def test_top1_decline_fails_quality_screen(self):
        c=quality_cases()
        c[0]["adaptive"]["correct"]=False
        self.assertEqual(A.quality_summary(c)["screen"]["Status"],"FAIL")

    def test_quality_missing_or_reordered_case_rejected(self):
        c=quality_cases()
        with self.assertRaises(A.Reject):A.quality_summary(c[:-1])
        c[0],c[1]=c[1],c[0]
        with self.assertRaises(A.Reject):A.quality_summary(c)

    def test_two_round_cost_margin_and_warmup_exclusion(self):
        rows=timing_rows(.95)
        rows[0]["elapsed_seconds"]=999.
        self.assertEqual(A.timing_summary(rows)["screen"]["Status"],"PASS")
        next(x for x in reversed(rows) if x["arm"]=="adaptive")["elapsed_seconds"]+=.1
        self.assertEqual(A.timing_summary(rows)["screen"]["Status"],"FAIL")

    def test_timing_order_and_nonfinite_rejected(self):
        rows=timing_rows()
        rows[2],rows[3]=rows[3],rows[2]
        with self.assertRaises(A.Reject):A.timing_summary(rows)
        rows=timing_rows()
        rows[5]["cpu_seconds"]=float("nan")
        with self.assertRaises(A.Reject):A.timing_summary(rows)

    def test_artifact_path_escape_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(A.Reject):A.safe(Path(tmp),"../outside")

    def test_full_synthetic_quality_and_timing_audit(self):
        """All64 real audit call paths and130 timing rows; negative cost is valid science."""
        with tempfile.TemporaryDirectory() as tmp:
            f=WorkerFixture(Path(tmp))
            result=f.audit()
            self.assertEqual(result["screens"]["quality"]["Status"],"PASS")
            self.assertEqual(result["screens"]["cpu_time"]["Status"],"FAIL")
            self.assertEqual(len(result["quality_results"]["early_exit_cases"]),2)
            self.assertEqual(result["describe_cost"]["quality_phase_observed_totals"]["adaptive"]["head"],94)
            self.assertEqual(result["describe_cost"]["quality_phase_observed_totals"]["fixed32"]["head"],32)

    def test_tampered_raw_hash_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=WorkerFixture(Path(tmp))
            path=f.w/f.zero["path"]
            path.write_bytes(b"x"+path.read_bytes()[1:])
            with self.assertRaises(A.Reject):f.audit()

    def test_timing_reference_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=WorkerFixture(Path(tmp))
            f.timings[2]["quality_reference_call"]+=1
            f.save_timing()
            with self.assertRaises(A.Reject):f.audit()

    def test_no_model_imports(self):
        self.assertEqual(D.forbidden(),[])


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--report",required=True,type=Path)
    args=parser.parse_args()
    if not args.report.is_absolute():parser.error("Absolute report path required")
    names=unittest.defaultTestLoader.getTestCaseNames(DataAuditTests)
    ids=["test_data_audit.DataAuditTests."+n for n in names]
    output=io.StringIO()
    result=unittest.TextTestRunner(stream=output,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(DataAuditTests))
    failed={test._testMethodName for test,_ in result.failures+result.errors}
    report={"Purpose":"Synthetic next-token provenance and independent scalar/count/timing audit checks",
            "Environment":{"python":sys.version,"model_imports":D.forbidden()},
            "Input":{"planned_test_ids":ids,"source_sha256":{n:D.info(HERE/n)["sha256"] for n in ("data_quality.py","audit_quality.py","test_data_audit.py")}},
            "Expected":"Every declared test passes; no Torch/model/real data use",
            "Actual":{"test_ids":ids,"planned":len(ids),"run":result.testsRun,"failures":len(result.failures),"errors":len(result.errors),
                      "skipped":len(result.skipped),"expected_failures":len(result.expectedFailures),"unexpected_successes":len(result.unexpectedSuccesses),
                      "tests":[{"id":"test_data_audit.DataAuditTests."+n,"Purpose":getattr(DataAuditTests,n).__doc__ or n,"Status":"FAIL" if n in failed else "PASS"} for n in names],
                      "unittest_output":output.getvalue()},"Status":"PASS" if result.wasSuccessful() and not result.skipped else "FAIL"}
    with args.report.open("x",encoding="utf-8",newline="\n") as f:
        json.dump(report,f,indent=2,ensure_ascii=False,allow_nan=False)
        f.write("\n")
    print(output.getvalue())
    return 0 if report["Status"]=="PASS" else 2


if __name__=="__main__":
    sys.exit(main())
