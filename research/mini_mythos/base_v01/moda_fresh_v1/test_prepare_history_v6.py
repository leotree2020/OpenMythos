"""Synthetic full-history preparation bridge fixtures; no real corpus or model."""
import argparse
from contextlib import redirect_stdout
import copy
import gzip
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT))
import prepare_history_v6 as W
D=W.D


def fixture_rows(per_class=6):
    rows=[];tokens={}
    for label in range(4):
        for j in range(per_class):
            i=len(rows);text=" ".join("item"+str(i)+"word"+str(k) for k in range(35))+"."
            rows.append({"text":text,"label":label});tokens[text]=list(range(i*400,i*400+129))
    return rows,tokens


def gate_records(rows,tokenize):
    result=[]
    for i,row in enumerate(rows):
        text=row["text"];h=D.sha(text.encode());identity={"corpus_sha256":W.S.CORPUS_PIN["sha256"],"row":i,"text_sha256":h}
        reason=D.prose_reason(text);ids=None if reason else tokenize(text)
        result.append({"id":D.sha(D.canonical(identity)),"row":i,"label":row["label"],"text_sha256":h,"decision":"EXCLUDE_"+reason if reason else ("EXCLUDE_SHORT" if len(ids)<129 else "ELIGIBLE_PENDING_HISTORY"),"full_token_count":None if reason else len(ids),"tokenization_started":reason is None,"tokenization_performed":reason is None})
    return result


def rebuilt(rows,tokens):
    gate=gate_records(rows,tokens.__getitem__);ledger=[]
    candidates,actual=W.rebuild_candidates(iter(rows),tokens.__getitem__,gate,ledger,total_rows=len(rows),rows_per_label=len(rows)//4)
    return candidates,ledger,actual


class PrepareHistoryV6Tests(unittest.TestCase):
    def test_acquisition_A_and_current_B_have_explicit_ancestry_and_unchanged_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/"source.py";source.write_bytes(b"immutable acquisition code")
            (root/"FREEZE_RECEIPT.json").write_bytes(D.canonical({"Input":{"source_freeze":"a"*40}}))
            with patch.object(W,"SPEC_DIR",root),patch.object(W,"HERE",root),patch.object(W.S,"SOURCES",("source.py",)),patch.object(W.S,"git",return_value="a"*40),patch.object(W.subprocess,"check_output",return_value=source.read_bytes()):
                original,pins=W.acquisition_ancestry({"Input":{"freeze":"a"*40}},"b"*40)
                self.assertEqual(original,"a"*40);self.assertIn(str(source),pins)
                source.write_bytes(b"changed")
                with self.assertRaisesRegex(D.Stop,"unchanged since A"):W.acquisition_ancestry({"Input":{"freeze":"a"*40}},"b"*40)

    def test_source_gate_must_pass_before_any_artifact_is_consumed(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"manifest.json";path.write_bytes(D.canonical({"Status":"BLOCKED","Actual":{},"Input":{}}))
            with patch.object(W,"GATE",path):
                with self.assertRaisesRegex(D.Stop,"Source eligibility gate"):W.source_gate(D.pin(path)["sha256"])

    def test_full_source_gate_receipt_pins_and_reuse_reference(self):
        rows,tokens=fixture_rows();records=gate_records(rows,tokens.__getitem__)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source_dir=root/"source";spec_dir=root/"spec";source_dir.mkdir();spec_dir.mkdir()
            source=source_dir/"corpus.parquet";source.write_bytes(b"synthetic train");source_pin=D.pin(source)
            tokenizer=root/"tokenizer.json";tokenizer.write_bytes(b"synthetic tokenizer")
            for name in ("DATA_SPEC.json","FREEZE_RECEIPT.json","history_before.json.gz"):(spec_dir/name).write_bytes(b"frozen")
            acquisition={"Status":"PASS","http_status":200,"url":W.S.URL,"actual_response":source_pin,"pin":source_pin,"response_file":"corpus.parquet","request_attempts":1}
            (source_dir/"acquisition.json").write_bytes(D.canonical(acquisition));receipt=W.Writer(source_dir).compressed("candidates.json.gz",records)
            actual={"source_rows":24,"rows_per_label":{str(i):6 for i in range(4)},"eligible_per_label":{str(i):6 for i in range(4)},"source_rows_observed":24,"source_rows_completed":24,"ledger_rows_retained":24,"source_attempts":1,"model_calls":0,"optimizer_steps":0,"history_files_scanned":0,"eligibility_necessary_condition":"PASS","old_fresh_after_status":"PASS","input_after_status":"PASS","corpus_after_status":"PASS","checkout_after_status":"PASS","history_freeze":{"spec":D.pin(spec_dir/"DATA_SPEC.json"),"receipt":D.pin(spec_dir/"FREEZE_RECEIPT.json"),"inventory":D.pin(spec_dir/"history_before.json.gz")}}
            gate={"Status":"PASS","Actual":actual,"Input":{"dataset":W.S.DATASET,"revision":W.S.REVISION,"split":"train","url":W.S.URL,"corpus":source_pin,"tokenizer_sha256":D.pin(tokenizer)["sha256"]},"forbidden_imports":[],"artifacts":{"corpus.parquet":source_pin,"acquisition.json":D.pin(source_dir/"acquisition.json"),"candidates.json.gz":receipt}}
            gate_path=source_dir/"manifest.json";gate_path.write_bytes(D.canonical(gate))
            with patch.object(W,"GATE",gate_path),patch.object(W,"SPEC",spec_dir/"DATA_SPEC.json"),patch.object(W,"SPEC_DIR",spec_dir),patch.object(W.S,"OUT",source_dir),patch.object(W.S,"TOTAL_ROWS",24),patch.object(W.S,"ROWS_PER_LABEL",6),patch.object(W.S,"CORPUS_PIN",source_pin),patch.object(W.S,"TOKENIZER",tokenizer),patch.object(W.S,"TOKENIZER_SHA",D.pin(tokenizer)["sha256"]):
                _,observed,reference,before=W.source_gate(D.pin(gate_path)["sha256"])
                self.assertEqual(observed,records);self.assertEqual(reference["source_file"],str(source));self.assertEqual(reference["network_requests"],0)
                self.assertIn(str(tokenizer),before);source.write_bytes(b"changed")
                with self.assertRaisesRegex(D.Stop,"Retained train corpus"):W.source_gate(D.pin(gate_path)["sha256"])

    def test_scope_union_retains_original_old_test_external_and_snapshot_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);fresh=root/"fresh";spec_dir=fresh/"specification-v6";repo=root/"repo";snapshot=spec_dir/"repo_history_snapshot"/"old.py";snapshot.parent.mkdir(parents=True)
            snapshot.write_text('x="prior debug words"');old_before=fresh/"preparation-v4/old_fresh_before.json";old_before.parent.mkdir(parents=True);old_before.write_bytes(b"{}")
            test_source=fresh/"preparation-v2/data/corpus.parquet";test_source.parent.mkdir(parents=True);test_source.write_bytes(b"old test source")
            external=root/"old.log";external.write_text("prior external evidence")
            original={str(root/"original"/str(i)) for i in range(32244)};paths=sorted(original|{str(old_before),str(test_source)})
            mapping={p:{"bytes":0,"sha256":"a"*64} for p in original};mapping.update({str(p):D.pin(p) for p in (old_before,test_source,external,snapshot)})
            spec={"repo_snapshot_origins":{str(snapshot):{"original_path":str(repo/"old.py"),"pin":D.pin(snapshot)}},"repo_snapshot_files":1,"repo_snapshot_bytes":snapshot.stat().st_size,"added_old_fresh_files":2,"added_external_sealed_files":1,"history_file_count":32248}
            old_v4={str(old_before):D.pin(old_before),str(external):D.pin(external)}
            with patch.object(W.S,"FRESH",fresh),patch.object(W.S,"REPO",repo),patch.object(W,"SPEC_DIR",spec_dir),patch.object(W.F,"enumerate_paths",return_value=(paths,original)),patch.object(W.F,"historical_git_json",side_effect=lambda name:old_v4 if "v4" in name else {}):
                expected,_=W.scope_paths(spec,{}, {},mapping);self.assertEqual(expected,set(mapping));self.assertIn(str(test_source),expected)
                smaller=dict(mapping);smaller.pop(str(test_source))
                with self.assertRaisesRegex(D.Stop,"scope"):W.scope_paths(spec,{}, {},smaller)
                (snapshot.parent/"extra.txt").write_text("unregistered")
                with self.assertRaisesRegex(D.Stop,"snapshot files"):W.scope_paths(spec,{}, {},mapping)

    def test_source_bridge_rebuilds_every_identity_and_decision_without_legacy_mutation(self):
        rows,tokens=fixture_rows();candidates,ledger,actual=rebuilt(rows,tokens)
        self.assertEqual(ledger,gate_records(rows,tokens.__getitem__));self.assertEqual(len(candidates),24)
        self.assertEqual(actual["eligible_per_label"],{str(i):6 for i in range(4)})
        self.assertEqual(D.TOTAL_ROWS,7600);self.assertEqual(D.CORPUS_RELATIVE,"data/test-00000-of-00001.parquet")

    def test_each_source_bridge_identity_flag_count_and_decision_is_enforced(self):
        rows,tokens=fixture_rows();gate=gate_records(rows,tokens.__getitem__)
        for field,value in (("id","bad"),("text_sha256","bad"),("decision","EXCLUDE_SHORT"),("full_token_count",130),("tokenization_started",False),("tokenization_performed",False)):
            with self.subTest(field=field):
                changed=copy.deepcopy(gate);changed[1][field]=value;partial=[]
                with self.assertRaisesRegex(D.Stop,"source gate at row 1"):W.rebuild_candidates(rows,tokens.__getitem__,changed,partial,24,6)
                self.assertEqual(len(partial),2)

    def test_source_bridge_preserves_rejected_and_short_rows_in_full_ledger(self):
        rows,tokens=fixture_rows(7);rows[0]["text"]="literal\\backslash.";tokens[rows[0]["text"]]=[1]*129
        tokens[rows[1]["text"]]=[1]*128
        candidates,ledger,actual=rebuilt(rows,tokens)
        self.assertEqual(len(ledger),28);self.assertEqual(len(candidates),26)
        self.assertEqual(ledger[0]["decision"],"EXCLUDE_LITERAL_BACKSLASH");self.assertIsNone(ledger[0]["full_token_count"])
        self.assertFalse(ledger[0]["tokenization_started"]);self.assertEqual(ledger[1]["decision"],"EXCLUDE_SHORT")
        self.assertEqual(actual["eligible_per_label"]["0"],5)

    def test_source_bridge_short_missing_extra_or_wrong_label_stops(self):
        rows,tokens=fixture_rows();gate=gate_records(rows,tokens.__getitem__)
        with self.assertRaises(D.Stop):W.rebuild_candidates(rows[:-1],tokens.__getitem__,gate,[],24,6)
        with self.assertRaises(D.Stop):W.rebuild_candidates(rows+[rows[0]],tokens.__getitem__,gate,[],24,6)
        bad=copy.deepcopy(rows);bad[0]["label"]=True
        with self.assertRaises(D.Stop):W.rebuild_candidates(bad,tokens.__getitem__,gate,[],24,6)

    def test_expanded_history_old_test_corpus_excludes_all_candidates_then_fixed_quota(self):
        rows,tokens=fixture_rows();candidates,ledger,_=rebuilt(rows,tokens)
        selected_history=[rows[label*6] for label in range(4)]
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);old=root/"old_ag_test.parquet";old.write_bytes(b"synthetic prior test corpus")
            duplicate=root/"duplicate.parquet";duplicate.write_bytes(old.read_bytes())
            mapping={str(p):D.pin(p) for p in (old,duplicate)};entries=W.classify_history(mapping,{},{});index=D.ExclusionIndex(candidates)
            with redirect_stdout(io.StringIO()):
                history=D.scan_history(entries,index,tokens.__getitem__,lambda raw,kind:selected_history)
            chosen=D.select(candidates,ledger,index)
        self.assertEqual(len(history),2);self.assertEqual(sum(r["Status"]=="PASS_IDENTICAL_PAYLOAD" for r in history),1)
        self.assertEqual(len(index.matches),4);self.assertEqual(len(chosen),20)
        self.assertEqual(sum(r["decision"]=="EXCLUDE_HISTORY" for r in ledger),4)
        self.assertTrue(all("witness" in r for r in ledger if r["decision"]=="EXCLUDE_HISTORY"))

    def test_history_reduction_can_still_block_quota_and_preserves_witnesses(self):
        rows,tokens=fixture_rows();candidates,ledger,_=rebuilt(rows,tokens);index=D.ExclusionIndex(candidates)
        for c in candidates[:2]:index.text(c["text"],{"path":"old","location":"retained","sha256":"a"*64},tokens.__getitem__)
        with self.assertRaisesRegex(D.Stop,"Insufficient fixed-class"):D.select(candidates,ledger,index)
        self.assertTrue(any(r.get("witness") for r in ledger));self.assertEqual(len(ledger),24)

    def test_train_payload_keeps_token_positions_and_zero_training(self):
        rows,tokens=fixture_rows();candidates,ledger,_=rebuilt(rows,tokens);chosen=D.select(candidates,ledger,D.ExclusionIndex(candidates));result=W.payload(chosen)
        self.assertEqual(result["provenance"]["split"],"train");self.assertEqual(result["provenance"]["corpus"],W.S.CORPUS_PIN)
        self.assertEqual(result["context_tokens"],128);self.assertEqual(result["scored_positions"],[64,128]);self.assertEqual(result["scored_target_offsets"],[65,129])
        self.assertEqual(result["eval_seeds"],[5101,5202]);self.assertEqual(result["optimizer_steps"],0)
        for row in result["eval"]:
            self.assertEqual(row["tokens"],tokens[row["text"]][:129]);self.assertEqual(row["scored_targets_sha256"],D.digest_tokens(row["tokens"][65:129]))

    def test_unknown_format_blocks_and_registered_nontext_is_exact(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"unknown.bin";path.write_bytes(b"pinned bytes");mapping={str(path):D.pin(path)}
            with self.assertRaisesRegex(D.Stop,"Unknown historical"):W.classify_history(mapping,{}, {})
            policy={str(path):{**D.pin(path),"reason":"explicit known numeric state"}}
            self.assertEqual(W.classify_history(mapping,policy,{})[0]["kind"],"nontext")
            path.write_bytes(b"changed")
            with self.assertRaisesRegex(D.Stop,"bytes changed"):W.classify_history(mapping,policy,{})

    def test_snapshot_alias_requires_exact_bytes_suffix_and_unambiguous_kind(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);old=root/"old.bin";copy_path=root/"copy.bin";old.write_bytes(b"known");copy_path.write_bytes(b"known")
            mapping={str(p):D.pin(p) for p in (old,copy_path)};origins={str(copy_path):{"original_path":str(old),"pin":D.pin(old)}}
            policies={"nontext_entries":{str(old):{**D.pin(old),"reason":"known state"}},"format_entries":{},"member_entries":{}}
            nontext,formats,members,notes=W.snapshot_policies(mapping,origins,policies)
            self.assertIn(str(copy_path),nontext);self.assertEqual(len(notes),1)
            conflict=root/"conflict.bin";conflict.write_bytes(b"known")
            policies["format_entries"][str(conflict)]={**D.pin(conflict),"kind":"text","reason":"conflicting classification"}
            with self.assertRaisesRegex(D.Stop,"Conflicting identical"):W.snapshot_policies(mapping,origins,policies)

    def test_snapshot_archive_member_alias_is_bound_to_identical_physical_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);old=root/"old.tar.gz";new=root/"new.tar.gz";old.write_bytes(b"archive fixture");new.write_bytes(old.read_bytes())
            mapping={str(p):D.pin(p) for p in (old,new)};member=str(old)[:-3]+"!state.pt"
            policies={"nontext_entries":{},"format_entries":{},"member_entries":{member:{"bytes":4,"sha256":"a"*64,"kind":"nontext","reason":"explicit member"}}}
            _,_,members,notes=W.snapshot_policies(mapping,{str(new):{"pin":D.pin(new),"original_path":str(old)}},policies)
            self.assertEqual(members[str(new)[:-3]+"!state.pt"],policies["member_entries"][member]);self.assertEqual(len(notes),1)
            new.write_bytes(b"not identical");mapping[str(new)]=D.pin(new)
            _,_,members,notes=W.snapshot_policies(mapping,{str(new):{}},policies)
            self.assertNotIn(str(new)[:-3]+"!state.pt",members);self.assertEqual(notes,[])

    def test_ledger_compression_is_lossless_pinned_and_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);writer=W.Writer(root);value=[{"decision":"EXCLUDE_HISTORY","witness":{"path":"old","location":"line:2"}}]
            receipt=writer.compressed("ledger.json.gz",value);self.assertEqual(W.packed(root/"ledger.json.gz",receipt),value)
            with self.assertRaises(D.Stop):W.packed(root/"ledger.json.gz",receipt,limit=2)
            with self.assertRaises(D.Stop):writer.compressed("ledger.json.gz",value)
            bad=copy.deepcopy(receipt);bad["canonical"]["sha256"]="0"*64
            with self.assertRaises(D.Stop):W.packed(root/"ledger.json.gz",bad)

    def test_budget_reserve_and_exclusive_partial_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);writer=W.Writer(root)
            with patch.object(W,"BUDGET",W.SEAL+4):
                writer.write("within",b"1234")
                with self.assertRaises(D.Stop):writer.write("excess",b"x")
            with self.assertRaises(D.Stop):writer.write("../outside",b"x")
            writer.compressed("candidates.json.gz",[{"decision":"NOT_TESTED"}]);writer.compressed("history_ledger.json.gz",[{"Status":"BLOCKED","error":"fixture"}])
            writer.seal({"Status":"BLOCKED","Actual":{"model_calls":0}})
            self.assertEqual(json.loads((root/"manifest.json").read_bytes())["Status"],"BLOCKED")

    def test_partial_failed_history_keeps_both_physical_rows_and_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);good=root/"a.txt";bad=root/"b.json";good.write_text("kept");bad.write_bytes(b'{"broken":')
            entries=W.classify_history({str(p):D.pin(p) for p in (good,bad)}, {}, {});history=[]
            with redirect_stdout(io.StringIO()):
                with self.assertRaises(D.Stop):D.scan_history(entries,D.ExclusionIndex([]),lambda _:[],ledger=history)
            self.assertEqual(len(history),2);self.assertEqual(history[0]["Status"],"PASS");self.assertEqual(history[1]["Status"],"BLOCKED");self.assertIn("error",history[1])

    def test_exact_isolated_help_requires_three_frozen_bridge_arguments_without_model_imports(self):
        result=subprocess.run([sys.executable,"-I","-B",str(ROOT/"prepare_history_v6.py"),"--help"],capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)
        for flag in ("--expected-head","--expected-spec-sha","--expected-gate-sha"):self.assertIn(flag,result.stdout)
        self.assertFalse({"torch","numpy","pyarrow","tokenizers","parcae_lm"}&{n.split(".")[0] for n in sys.modules})


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--report",type=Path,required=True);args=parser.parse_args()
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(PrepareHistoryV6Tests);ids=sorted(t.id() for t in suite);result=unittest.TextTestRunner(verbosity=2).run(suite)
    report={"Purpose":"Synthetic source bridge, complete history scope and fixed selection preparation controls","Environment":{"python":sys.version,"development_only":True},"Input":"Synthetic corpora, rows, files and receipts only; no target/source/tokenizer/model access","Expected":{"tests":len(ids),"test_ids":ids},"Actual":{"test_ids":ids,"planned":len(ids),"run":result.testsRun,"failures":len(result.failures),"errors":len(result.errors),"skipped":len(result.skipped),"expected_failures":len(result.expectedFailures),"unexpected_successes":len(result.unexpectedSuccesses),"failure_details":[[t.id(),s] for t,s in result.failures+result.errors]},"Status":"PASS" if result.wasSuccessful() and result.testsRun==len(ids) and not result.skipped else "FAIL"}
    with args.report.open("x",encoding="utf-8") as stream:json.dump(report,stream,indent=2,ensure_ascii=False);stream.write("\n")
    raise SystemExit(0 if report["Status"]=="PASS" else 1)
