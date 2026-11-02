"""Synthetic-only data audit fixtures, including exact isolated CLI startup."""
import argparse
from collections import Counter
from contextlib import contextmanager,redirect_stdout
import copy
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import audit_data as A
import data_prepare as D


def tokenize(text):return [int(hashlib.sha256(word.encode()).hexdigest()[:8],16)%32768 for word in text.split()]
def prose(i,n=150):
    return " ".join("".join(chr(97+(x%26)) for x in hashlib.sha256(f"{i}:{j}".encode()).digest()[:12]) for j in range(n))+"."
def strict_copy(value):return json.loads(json.dumps(value))
def checks(purpose,okay,actual=None):A.require(okay,purpose)


class Fixture:
    def __init__(self,root):
        self.root=root;self.history=root/"history";self.history.mkdir();self.prep=root/"data";self.prep.mkdir();(self.prep/"public").mkdir()
        self.source=[{"text":prose(i),"label":i%4} for i in range(32)]+[{"text":"short.","label":i%4} for i in range(32,7600)]
        # Keep repeated JSON keys and nonfinite numeric metadata in real bytes.
        old=self.history/"first.json"
        raw=('{"text":'+json.dumps(self.source[0]["text"])+',"tokens":'+json.dumps(tokenize(self.source[1]["text"])) + ',"dup":1,"dup":NaN}').encode()
        old.write_bytes(raw);(self.history/"same.json").write_bytes(raw)
        binary=self.history/"frozen.bin";binary.write_bytes(b"registered nontext fixture")
        self.members={}
        archive=self.history/"archive.zip"
        with zipfile.ZipFile(archive,"w") as stream:
            stream.writestr("state.bin",b"state zip");stream.writestr("story.txt",self.source[2]["text"])
        self.members[str(archive)+"!state.bin"]={"kind":"nontext","bytes":9,"sha256":A.sha(b"state zip"),"reason":"Synthetic tensor payload"}
        archive2=self.history/"nested.tar.gz";tar=io.BytesIO()
        with tarfile.open(fileobj=tar,mode="w") as stream:
            value=b"state tar";entry=tarfile.TarInfo("state.bin");entry.size=len(value);stream.addfile(entry,io.BytesIO(value))
            value=b"short fixture prose.";entry=tarfile.TarInfo("notes.txt");entry.size=len(value);stream.addfile(entry,io.BytesIO(value))
        archive2.write_bytes(gzip.compress(tar.getvalue(),mtime=0))
        self.members[str(archive2)[:-3]+"!state.bin"]={"kind":"nontext","bytes":9,"sha256":A.sha(b"state tar"),"reason":"Synthetic tar tensor payload"}
        allpaths=sorted(str(p) for p in self.history.iterdir())
        self.spec={"schema":"mythos-fresh-history-v1","history_roots":[str(self.history)],"excluded_roots":[],"discover_before_acquisition":True,"expected_history_file_count":len(allpaths),"expected_history_suffixes":dict(Counter(Path(p).suffix for p in allpaths)),"nontext_entries":{str(binary):{**A.pin(binary),"reason":"Registered synthetic tensor"}},"member_entries":self.members,"extra_history_inventory":{str(old):A.pin(old)}}
        self.candidates,self.ledger=D.collect_candidates(self.source,tokenize);index=D.ExclusionIndex(self.candidates)
        with redirect_stdout(io.StringIO()):self.history_ledger=D.scan_history(D.verify_inventory(self.spec),index,tokenize,member_policy=self.members)
        self.chosen=D.select(self.candidates,self.ledger,index);self.payload=D.selected_payload(self.chosen)
        self.retained=A.RETAINED_SOURCE;self.retained.parent.mkdir();self.retained.write_bytes(b"Synthetic parquet fixture bytes")
        acquisition={"url":A.URL,"Status":"PASS","http_status":200,"actual_response":A.CORPUS,"pin":A.CORPUS,"response_file":"corpus.parquet"}
        self.origin=self.retained.with_name("acquisition.json");self.origin.write_bytes(A.encoded(acquisition))
        self.reference={"schema":"mythos-local-corpus-reference-v1","mode":"LOCAL_PINNED_REUSE","source_file":str(self.retained),"source_pin":A.CORPUS,"original_acquisition_file":str(self.origin),"original_acquisition_pin":A.pin(self.origin),"network_requests":0,"copied_corpus_bytes":0,"Status":"PASS"}
        self.artifacts={};self.write("source_reference.json",self.reference)
        self.reuse={**self.reference,"mode":"LOCAL_PINNED_REUSE","source_reference_pin":self.artifacts["source_reference.json"],"url":A.URL,"expected":A.CORPUS}
        self.write("acquisition.json",self.reuse);self.write("inputs.json",self.payload)
        self.public={"samples":[{k:v for k,v in row.items() if k not in ("text","tokens")} for row in self.payload["eval"]],"input_pin":self.artifacts["inputs.json"],"labels":{str(i):5 for i in range(4)}}
        self.write("public/selection.json",self.public);self.write("candidates.json.gz",self.ledger);self.write("history_ledger.json.gz",self.history_ledger)
        self.manifest={"Purpose":"Synthetic fixture","Environment":{"development_only":True},"Input":{"spec_sha256":"a"*64,"source":A.URL},"Expected":{"records":20,"per_class":5,"tokens":129,"training_steps":0,"model_imports":[]},"Actual":{"source_rows":7600,"prose_length_eligible":len(self.candidates),"historical_files":len(allpaths),"historical_strings":index.string_count,"historical_token_arrays":index.token_array_count,"historical_format_notes":index.format_notes,"excluded_by_history":len(index.matches),"selected":20,"input_pin":self.artifacts["inputs.json"],"model_calls":0},"Status":"PASS","source_after_status":"PASS","forbidden_imports":[],"artifacts":self.artifacts}
        self.manifest["Actual"]["historical_python_recovery"]={k:0 for k in A.RECOVERY_KEYS}
        self.manifest["Actual"].update(new_source_acquisitions=0,copied_corpus_bytes=0)
        self.manifest["Input"].update(history_preflight_only=False,source_file=str(self.retained))
        self.preflight=self.root/"history-preflight";self.preflight.mkdir()
        projection=[]
        for row in self.history_ledger:
            value={key:row[key] for key in ("path","bytes","sha256","kind","Status")}
            value.update({key:row[key] for key in ("reason","identical_to") if key in row});projection.append(value)
        raw=A.encoded(projection)
        findings=[row for row in self.history_ledger if row.get("python_recovery") or row.get("format_notes") or row.get("error") or row["Status"] not in ("PASS","PASS_IDENTICAL_PAYLOAD","EXCLUDED_REGISTERED_NONTEXT")]
        findings_raw=A.encoded(findings);findings_path=self.preflight/"preflight_findings.json.gz";findings_path.write_bytes(gzip.compress(findings_raw,mtime=0))
        self.preflight_report={"Status":"PASS","source_after_status":"PASS","forbidden_imports":[],"Input":{"spec_sha256":"a"*64,"history_preflight_only":True,"source_file":None},"Expected":{"historical_files":len(allpaths),"parse_completed":True,"tokenizer_calls":0,"new_source_acquisitions":0,"model_calls":0},"Actual":{"historical_files":len(allpaths),"historical_files_completed":len(allpaths),"parse_completed":True,"tokenizer_calls":0,"new_source_acquisitions":0,"model_calls":0,"historical_strings":index.string_count,"historical_token_arrays":index.token_array_count,"historical_format_notes":index.format_notes,"historical_python_recovery":{k:0 for k in A.RECOVERY_KEYS},"history_ledger_projection":{"schema":"mythos-history-format-projection-v1","records":len(allpaths),"canonical":{"bytes":len(raw),"sha256":A.sha(raw)}}},"artifacts":{"preflight_findings.json.gz":{"physical":A.pin(findings_path),"canonical":{"bytes":len(findings_raw),"sha256":A.sha(findings_raw)}}}}
        (self.preflight/"manifest.json").write_bytes(A.encoded(self.preflight_report))
        self.seal()
    def write(self,name,value,raw=False):
        content=value if raw else A.encoded(value);path=self.prep/name
        if name.endswith(".gz"):
            path.write_bytes(gzip.compress(content,mtime=0));receipt={"physical":A.pin(path),"canonical":{"bytes":len(content),"sha256":A.sha(content)}}
        else:path.write_bytes(content);receipt=A.pin(path)
        self.artifacts[name]=receipt;return receipt
    def seal(self):(self.prep/"manifest.json").write_bytes(A.encoded(self.manifest))
    def arrow(self,raw,kind):
        A.require(raw==b"Synthetic parquet fixture bytes" and kind=="parquet","Synthetic reader exact bytes")
        return self.source
    def run(self):return A.audit(self.spec,"a"*64,self.prep,tokenize,self.arrow,checks)


@contextmanager
def fixture():
    raw=b"Synthetic parquet fixture bytes";source_pin={"bytes":len(raw),"sha256":A.sha(raw)}
    with tempfile.TemporaryDirectory() as name,patch.object(A,"CORPUS",source_pin),patch.object(D,"CORPUS_PIN",source_pin),patch.object(A,"RETAINED_SOURCE",Path(name).resolve()/"prior_v2"/"corpus.parquet"):
        yield Fixture(Path(name).resolve())


class AuditDataTests(unittest.TestCase):
    def test_exact_isolated_import_and_cli_help(self):
        with tempfile.TemporaryDirectory() as directory:
            result=subprocess.run([sys.executable,"-I","-B",str(ROOT/"audit_data.py"),"--help"],cwd=directory,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr);self.assertIn("--expected-spec-sha",result.stdout);self.assertIn("--prep",result.stdout)

    def test_exact_isolated_wrong_target_saves_blocked_without_reading_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();out=root/"audit.json";environment={**os.environ,"CODESPACE_NAME":"synthetic-wrong-target"}
            result=subprocess.run([sys.executable,"-I","-B",str(ROOT/"audit_data.py"),"--spec",str(root/"absent.json"),"--expected-spec-sha","0"*64,"--prep",str(root/"absent"),"--output",str(out)],cwd=root,env=environment,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=30)
            self.assertEqual(result.returncode,2,result.stderr);report=A.read(out)
            self.assertEqual(report["Status"],"BLOCKED");self.assertIn("environment",report["error"]["reason"]);self.assertEqual(report["Actual"],{})

    def test_frozen_source_tokenizer_parser_constants_match(self):
        self.assertEqual(A.CORPUS,D.CORPUS_PIN);self.assertEqual(A.URL,D.URL);self.assertEqual(A.TOKENIZER_SHA,D.TOKENIZER_SHA)
        self.assertEqual(A.pin(D.__file__)["sha256"],A.PARSER_SHA)

    def test_exact_isolated_invalid_output_cannot_mutate_preparation(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();prep=root/"data";prep.mkdir();original=prep/"original.json";original.write_bytes(b'{"preserve":true}')
            before={p.name:A.pin(p) for p in prep.iterdir()};out=prep/"forbidden_audit.json"
            result=subprocess.run([sys.executable,"-I","-B",str(ROOT/"audit_data.py"),"--spec",str(root/"absent.json"),"--expected-spec-sha","0"*64,"--prep",str(prep),"--output",str(out)],cwd=root,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=30)
            self.assertEqual(result.returncode,2,result.stderr);report=json.loads(result.stdout)
            self.assertEqual(report["Status"],"BLOCKED");self.assertEqual(report["error"]["type"],"UnsafeAuditOutput")
            self.assertFalse(out.exists());self.assertEqual({p.name:A.pin(p) for p in prep.iterdir()},before)

    def test_strict_json_duplicate_nonfinite_and_bounded_gzip(self):
        for raw in ('{"x":1,"x":2}','{"x":NaN}','{"x":Infinity}'):
            with self.assertRaises(A.Stop):A.loads(raw)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"large.gz";path.write_bytes(gzip.compress(b"0"*10))
            with patch.object(A,"LIMIT",9),self.assertRaises(A.Stop):A.read(path)

    def test_full_synthetic7600row_custody_selection_audit(self):
        with fixture() as f:
            with patch.object(D,"collect_candidates",side_effect=AssertionError("shared eligibility prohibited")),patch.object(D,"select",side_effect=AssertionError("shared selection prohibited")),patch.object(D,"overlaps",side_effect=AssertionError("shared overlap prohibited")),patch.object(D,"verify_inventory",side_effect=AssertionError("shared inventory prohibited")):
                result=f.run()
            self.assertEqual(result["source_rows"],7600);self.assertEqual(result["selected"],20);self.assertEqual(result["history"]["files"],5)
            self.assertFalse(result["historical_absence_independently_rescanned"]);self.assertEqual(result["new_model_calls"],0);self.assertEqual(result["new_source_acquisitions"],0)
            self.assertEqual(result["historical_witnesses"]["excluded_candidates"],3);self.assertEqual(result["input_pin"],A.pin(f.prep/"inputs.json"))

    def test_manifest_header_status_source_and_counter_tamper(self):
        with fixture() as f:
            original=copy.deepcopy(f.manifest)
            for branch,key,value in [(None,"Status","FAIL"),("Input","spec_sha256","b"*64),("Input","source","alternate"),("Expected","tokens",130),("Actual","historical_files",4),("Actual","model_calls",1)]:
                f.manifest=copy.deepcopy(original);target=f.manifest if branch is None else f.manifest[branch];target[key]=value;f.seal()
                with self.subTest(branch=branch,key=key),self.assertRaises(A.Stop):f.run()

    def test_source_bytes_and_acquisition_receipt_tamper(self):
        with fixture() as f:
            f.retained.write_bytes(b"other source bytes")
            with self.assertRaises(A.Stop):f.run()
        with fixture() as f:
            receipt=A.read(f.origin);receipt["http_status"]=206;f.origin.write_bytes(A.encoded(receipt))
            f.reference["original_acquisition_pin"]=A.pin(f.origin);f.reuse["original_acquisition_pin"]=A.pin(f.origin)
            f.write("source_reference.json",f.reference);f.write("acquisition.json",f.reuse);f.seal()
            with self.assertRaises(A.Stop):f.run()

    def test_retained_source_exact_path_pin_and_no_local_duplicate(self):
        with fixture() as f:
            source,custody=A.retained_source(f.prep);self.assertEqual(source,f.retained)
            self.assertEqual(custody["network_requests"],0);self.assertEqual(custody["copied_corpus_bytes"],0)
            alternate=f.root/"same_content.parquet";alternate.write_bytes(f.retained.read_bytes())
            bad={**f.reference,"source_file":str(alternate)};f.write("source_reference.json",bad)
            with self.assertRaises(A.Stop):A.retained_source(f.prep)
            f.write("source_reference.json",f.reference);(f.prep/"corpus.parquet").write_bytes(f.retained.read_bytes())
            with self.assertRaises(A.Stop):A.retained_source(f.prep)

    def test_retained_reference_reuse_disagreement_and_network_claim_rejected(self):
        with fixture() as f:
            for key,value in (("source_pin",{"bytes":1,"sha256":"0"*64}),("original_acquisition_pin",{"bytes":1,"sha256":"0"*64}),("network_requests",1),("copied_corpus_bytes",A.CORPUS["bytes"]),("mode","DOWNLOAD")):
                bad={**f.reuse,key:value};f.write("acquisition.json",bad)
                with self.subTest(key=key),self.assertRaises(A.Stop):A.retained_source(f.prep)

    def test_retained_source_unchanged_after_complete_synthetic_audit(self):
        with fixture() as f:
            before={str(p):A.pin(p) for p in f.retained.parent.iterdir()};result=f.run()
            self.assertEqual({str(p):A.pin(p) for p in f.retained.parent.iterdir()},before)
            self.assertEqual(result["source_custody"]["source_file"],str(f.retained))
            self.assertEqual(result["source_custody"]["original_acquisition_pin"],A.pin(f.origin))

    def test_artifact_physical_canonical_and_unlisted_tamper(self):
        with fixture() as f:
            A.verify_artifacts(f.prep,f.manifest)
            original=copy.deepcopy(f.manifest)
            for key in ("physical","canonical"):
                f.manifest=copy.deepcopy(original);f.manifest["artifacts"]["candidates.json.gz"][key]["sha256"]="0"*64
                with self.subTest(key=key),self.assertRaises(A.Stop):A.verify_artifacts(f.prep,f.manifest)
            f.manifest=original;(f.prep/"unlisted.json").write_bytes(b"{}")
            with self.assertRaises(A.Stop):A.verify_artifacts(f.prep,f.manifest)

    def test_policy_pin_dual_form_and_conflict_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory).resolve()/"policy.json.gz";path.write_bytes(gzip.compress(A.encoded({}),mtime=0))
            spec={"nontext_entries_path":str(path),"nontext_entries_pin":A.pin(path)};self.assertEqual(A.policies(spec)["nontext_entries"],{})
            spec["nontext_entries"]={}
            with self.assertRaises(A.Stop):A.policies(spec)
            del spec["nontext_entries"];spec["nontext_entries_pin"]["bytes"]+=1
            with self.assertRaises(A.Stop):A.policies(spec)
            with self.assertRaises(A.Stop):A.policies({"nontext_entries":{"same":{}},"format_entries":{"same":{}}})

    def test_source_identity_length_prose_and_token_contract_tamper(self):
        with fixture() as f:
            for key,value in (("row",1),("text_sha256","0"*64),("full_token_count",151)):
                ledger=copy.deepcopy(f.ledger);ledger[0][key]=value
                with self.subTest(key=key),self.assertRaises(A.Stop):A.independent_candidates(f.source,ledger,tokenize)
            source=copy.deepcopy(f.source);source[-1]["text"]="replacement text."
            with self.assertRaises(A.Stop):A.independent_candidates(source,f.ledger,tokenize)
            with self.assertRaises(A.Stop):A.independent_candidates(f.source,f.ledger,lambda _: [False]*150)
            ledger=copy.deepcopy(f.ledger);ledger[-1]["decision"]="SELECTED"
            with self.assertRaises(A.Stop):A.independent_candidates(f.source,ledger,tokenize)

    def test_first_five_selection_and_hidden_witness_tamper(self):
        with fixture() as f:
            eligible=A.independent_candidates(f.source,f.ledger,tokenize);A.independent_selection(eligible,f.ledger)
            ledger=copy.deepcopy(f.ledger);selected=next(r for r in ledger if r["decision"]=="SELECTED");selected["decision"]="ELIGIBLE_NOT_SELECTED"
            with self.assertRaises(A.Stop):A.independent_selection(eligible,ledger)
            ledger=copy.deepcopy(f.ledger);selected=next(r for r in ledger if r["decision"]=="SELECTED");selected["witness"]={"unexplained":True}
            with self.assertRaises(A.Stop):A.independent_selection(eligible,ledger)

    def test_independent_newnew_duplicate_before_quota(self):
        source=[{"text":prose(i),"label":i%4} for i in range(28)];source[24]["text"]=source[0]["text"]
        with patch.object(D,"TOTAL_ROWS",28):candidates,ledger=D.collect_candidates(source,tokenize)
        D.select(candidates,ledger,D.ExclusionIndex(candidates))
        eligible=A.independent_candidates(source,ledger,tokenize,28);self.assertEqual(len(A.independent_selection(eligible,ledger)),20)
        duplicates=[r for r in ledger if r["decision"]=="EXCLUDE_NEW_DUPLICATE"];self.assertTrue(duplicates)
        duplicates[0]["witness"]["reasons"]=["TOKEN32"]
        with self.assertRaises(A.Stop):A.independent_selection(eligible,ledger)

    def test_payload_exact_target_window_and_public_redaction(self):
        with fixture() as f:
            eligible=A.independent_candidates(f.source,f.ledger,tokenize);chosen=A.independent_selection(eligible,f.ledger)
            A.audit_payload(chosen,f.payload,f.public,f.artifacts["inputs.json"])
            for key,value in (("tokens",f.payload["eval"][0]["tokens"][1:]+[0]),("text",f.payload["eval"][0]["text"]+" edit"),("scored_targets_sha256","0"*64)):
                payload=copy.deepcopy(f.payload);payload["eval"][0][key]=value
                with self.subTest(key=key),self.assertRaises(A.Stop):A.audit_payload(chosen,payload,f.public,f.artifacts["inputs.json"])
            public=copy.deepcopy(f.public);public["samples"][0]["text"]=f.payload["eval"][0]["text"]
            with self.assertRaises(A.Stop):A.audit_payload(chosen,f.payload,public,f.artifacts["inputs.json"])

    def test_full_history_membership_and_extra_file_detection(self):
        with fixture() as f:
            policy=A.policies(f.spec)
            with self.assertRaises(A.Stop):A.audit_history(f.spec,policy,f.history_ledger[:-1])
            (f.history/"new.txt").write_text("new unexpected text")
            with self.assertRaises(A.Stop):A.audit_history(f.spec,policy,f.history_ledger)

    def test_history_actual_byte_and_prior_pin_tamper(self):
        with fixture() as f:
            policy=A.policies(f.spec);prior=next(iter(policy["extra_history_inventory"]));policy["extra_history_inventory"][prior]["sha256"]="0"*64
            with self.assertRaises(A.Stop):A.audit_history(f.spec,policy,f.history_ledger)
        with fixture() as f:
            (f.history/"first.json").write_bytes(b"{}")
            with self.assertRaises(A.Stop):A.audit_history(f.spec,A.policies(f.spec),f.history_ledger)

    def test_history_status_reuse_and_nontext_classification_tamper(self):
        with fixture() as f:
            for change in ("reuse","status","reason"):
                ledger=copy.deepcopy(f.history_ledger)
                if change=="reuse":next(r for r in ledger if r["Status"]=="PASS_IDENTICAL_PAYLOAD")["identical_to"]="unscanned"
                elif change=="status":next(r for r in ledger if r["Status"]=="PASS")["Status"]="NOT TESTED"
                else:next(r for r in ledger if r["kind"]=="nontext")["reason"]="different"
                with self.subTest(change=change),self.assertRaises(A.Stop):A.audit_history(f.spec,A.policies(f.spec),ledger)

    def test_nested_gzip_archive_nontext_exact_receipt(self):
        with fixture() as f:
            actual=A.audit_history(f.spec,A.policies(f.spec),f.history_ledger);self.assertEqual(actual["files"],5)
            ledger=copy.deepcopy(f.history_ledger);row=next(r for r in ledger if r["path"].endswith(".tar.gz"));row["classified_nontext_members"][0]["location"]="wrong virtual member"
            with self.assertRaises(A.Stop):A.audit_history(f.spec,A.policies(f.spec),ledger)

    def test_witness_reasons_location_and_source_tamper(self):
        with fixture() as f:
            eligible=A.independent_candidates(f.source,f.ledger,tokenize)
            for change in ("reason","location","sha"):
                ledger=copy.deepcopy(f.ledger);w=next(r for r in ledger if r["decision"]=="EXCLUDE_HISTORY")["witness"]
                if change=="reason":w["reasons"]=["invented"]
                elif change=="location":w["source"]["location"]="missing"
                else:w["source"]["sha256"]="0"*64
                with self.subTest(change=change),self.assertRaises(A.Stop):A.audit_witnesses(eligible,ledger,f.history_ledger,tokenize,f.arrow,f.members)

    def test_python_same_line_witness_chooses_actual_matching_leaf_once(self):
        source=[{"text":prose(7),"label":0}]
        with patch.object(D,"TOTAL_ROWS",1):candidates,ledger=D.collect_candidates(source,tokenize)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory).resolve()/"values.py";path.write_text("x = ('unrelated', "+repr(source[0]["text"])+")",encoding="utf-8")
            index=D.ExclusionIndex(candidates)
            with redirect_stdout(io.StringIO()):history=D.scan_history([{"path":str(path),**D.pin(path),"kind":"python"}],index,tokenize)
            ledger[0].update(decision="EXCLUDE_HISTORY",witness=index.matches[candidates[0]["id"]]);eligible=A.independent_candidates(source,ledger,tokenize,1)
            self.assertEqual(A.audit_witnesses(eligible,ledger,history,tokenize,None,{})["excluded_candidates"],1)

    def test_prose_overlap_boundaries_and_no_forbidden_imports(self):
        self.assertIsNone(A.exclusion_reason("a"*13+"0"*6+"."));self.assertEqual(A.exclusion_reason("a"*12+"0"*7+"."),"ALPHABETIC_RATIO")
        empty={"normalized":None,"t32":set(),"w12":set(),"w5":set()};left={**empty,"t32":A.ngrams(list(range(129)),32)}
        self.assertEqual(A.overlap(left,{**empty,"t32":A.ngrams(list(range(32)),32)}),["TOKEN32"])
        self.assertEqual(A.overlap(left,{**empty,"t32":A.ngrams(list(range(31)),32)}),[])
        left={**empty,"w5":set(range(20))};right={**empty,"w5":set(range(10))|set(range(100,110))}
        self.assertEqual(A.overlap(left,right),["WORD5_CONTAINMENT_GE_HALF"]);self.assertFalse(set(sys.modules)&A.FORBIDDEN)

    def test_malformed_python_raw_literal_token_coverage_and_note_tamper(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();path=root/"retained_bad.py"
            path.write_text("broken = '\ntext = "+repr(prose(9))+"\ntokens = "+repr(list(range(129)))+"\n",encoding="utf-8")
            spec={"history_roots":[str(root)],"excluded_roots":[],"expected_history_file_count":1,"expected_history_suffixes":{".py":1},"discover_before_acquisition":True}
            index=D.ExclusionIndex([])
            with redirect_stdout(io.StringIO()):ledger=D.scan_history(D.verify_inventory(spec),index,tokenize)
            value=A.audit_history(spec,A.policies(spec),ledger)
            self.assertEqual(value["python_recovery"]["files"],1);self.assertGreater(value["python_recovery"]["string_fragments"],0);self.assertGreater(value["python_recovery"]["token_arrays"],0)
            for change in ("missing","raw","semantic","count"):
                altered=copy.deepcopy(ledger)
                if change=="missing":del altered[0]["python_recovery"]
                elif change=="raw":altered[0]["python_recovery"][0]["raw_source_covered"]=False
                elif change=="semantic":altered[0]["python_recovery"][0]["semantic_reconstruction"]=True
                else:altered[0]["python_recovery"][0]["token_arrays"]+=1
                with self.subTest(change=change),self.assertRaises(A.Stop):A.audit_history(spec,A.policies(spec),altered)

    def test_recovery_aggregate_tamper_rejected(self):
        with fixture() as f:
            f.manifest["Actual"]["historical_python_recovery"]["files"]=1;f.seal()
            with self.assertRaises(A.Stop):f.run()

    def test_preflight_projection_count_hash_and_no_tokenizer_contract(self):
        with fixture() as f:
            original=copy.deepcopy(f.preflight_report)
            for change in ("count","hash","tokenizer","source"):
                report=copy.deepcopy(original)
                if change=="count":report["Actual"]["history_ledger_projection"]["records"]-=1
                elif change=="hash":report["Actual"]["history_ledger_projection"]["canonical"]["sha256"]="0"*64
                elif change=="tokenizer":report["Actual"]["tokenizer_calls"]=1
                else:report["Input"]["source_file"]=str(f.retained)
                (f.preflight/"manifest.json").write_bytes(A.encoded(report))
                with self.subTest(change=change),self.assertRaises(A.Stop):f.run()

    def test_preflight_all_findings_preserved_even_after_receipt_repin(self):
        with fixture() as f:
            path=f.preflight/"preflight_findings.json.gz";findings=A.read(path);self.assertTrue(findings)
            raw=A.encoded([]);path.write_bytes(gzip.compress(raw,mtime=0))
            f.preflight_report["artifacts"][path.name]={"physical":A.pin(path),"canonical":{"bytes":len(raw),"sha256":A.sha(raw)}}
            (f.preflight/"manifest.json").write_bytes(A.encoded(f.preflight_report))
            with self.assertRaises(A.Stop):f.run()

    def test_parse_only_and_candidate_scan_complete_finding_rows_agree(self):
        with fixture() as f:
            index=D.ParseOnlyIndex()
            def forbidden_tokenizer(_):raise AssertionError("Preflight must not tokenize")
            with redirect_stdout(io.StringIO()):rows=D.scan_history(D.verify_inventory(f.spec),index,forbidden_tokenizer,member_policy=f.members)
            self.assertEqual(rows,f.history_ledger)
            self.assertEqual(D.preflight_projection(rows),f.preflight_report["Actual"]["history_ledger_projection"])
            self.assertEqual(index.format_notes,f.manifest["Actual"]["historical_format_notes"])


def main():
    cli=argparse.ArgumentParser();cli.add_argument("--report",type=Path);cli.add_argument("--list-tests",action="store_true");args=cli.parse_args()
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(AuditDataTests);ids=sorted(t.id() for t in suite)
    if args.list_tests:print(json.dumps(ids));return 0
    result=unittest.TextTestRunner(verbosity=2,failfast=True).run(suite)
    passed=result.wasSuccessful() and result.testsRun==len(ids) and not result.skipped
    report={"Purpose":"Development-only independent data audit and exact isolated launch fixtures","Environment":{"python":sys.version,"executable":sys.executable,"isolated":bool(sys.flags.isolated),"bytecode_disabled":sys.dont_write_bytecode,"development_only":True},"Input":{"real_model":False,"real_data":False,"source_acquisitions":0},"Expected":{"tests":len(ids)},"Actual":{"planned":len(ids),"run":result.testsRun,"test_ids":ids,"failures":len(result.failures),"errors":len(result.errors),"skipped":len(result.skipped),"expected_failures":len(result.expectedFailures),"unexpected_successes":len(result.unexpectedSuccesses)},"Status":"PASS" if passed else "FAIL"}
    if args.report:
        with args.report.open("x",encoding="utf-8") as stream:json.dump(report,stream,indent=2);stream.write("\n")
    return 0 if passed else 1


if __name__=="__main__":raise SystemExit(main())
