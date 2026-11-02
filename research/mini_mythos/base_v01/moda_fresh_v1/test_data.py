"""Synthetic standard-library fixtures only; no corpus/tokenizer/model imports."""
import argparse
from contextlib import contextmanager
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location("fresh_data",ROOT/"data_prepare.py")
D=importlib.util.module_from_spec(s);s.loader.exec_module(D)


def tokenize(text):
    return [int(hashlib.sha256(word.encode()).hexdigest()[:8],16)%32768 for word in text.split()]


def prose(i,n=150):
    def word(j):
        return "".join(chr(97+(x%26)) for x in hashlib.sha256(f"{i}:{j}".encode()).digest()[:12])
    return " ".join(word(j) for j in range(n))+"."


def collect(count=24):
    rows=[{"text":prose(i),"label":i%4} for i in range(count)]
    with patch.object(D,"TOTAL_ROWS",count):return D.collect_candidates(rows,tokenize)


class DataTests(unittest.TestCase):
    def test_prose_frozen_exclusions_and_exact_boundary(self):
        good=prose(1)
        self.assertIsNone(D.prose_reason(good))
        for raw,reason in [(good+"\\","LITERAL_BACKSLASH"),(good+"<","ANGLE_BRACKET"),(good+">","ANGLE_BRACKET"),(good+"\ufffd","REPLACEMENT_CHARACTER"),("abc","NO_SENTENCE_PUNCTUATION"),("1234567890.","ALPHABETIC_RATIO")]:
            self.assertEqual(D.prose_reason(raw),reason)
        self.assertIsNone(D.prose_reason("a"*13+"0"*6+"."))
        self.assertEqual(D.prose_reason("a"*12+"0"*7+"."),"ALPHABETIC_RATIO")

    def test_short_records_never_concatenated(self):
        rows=[{"text":prose(i,128),"label":i%4} for i in range(4)]
        with patch.object(D,"TOTAL_ROWS",4):c,l=D.collect_candidates(rows,tokenize)
        self.assertEqual(c,[]);self.assertTrue(all(x["decision"]=="EXCLUDE_SHORT" for x in l))

    def test_exact_strata_selection_order_original_tokens(self):
        c,l=collect();chosen=D.select(c,l,D.ExclusionIndex(c))
        self.assertEqual([sum(x["label"]==k for x in chosen) for k in range(4)],[5]*4)
        for k in range(4):self.assertEqual([x["id"] for x in chosen if x["label"]==k],sorted(x["id"] for x in c if x["label"]==k)[:5])
        p=D.selected_payload(chosen)
        self.assertEqual(p["optimizer_steps"],0);self.assertEqual(p["scored_target_offsets"],[65,129])
        for row in p["eval"]:
            self.assertEqual(row["tokens"],tokenize(row["text"])[:129])
            self.assertEqual(row["scored_targets_sha256"],D.digest_tokens(row["tokens"][65:129]))

    def test_insufficient_any_class_is_blocked_no_fallback(self):
        c,l=collect(20);idx=D.ExclusionIndex(c);idx.matches[c[0]["id"]]={"source":{},"reasons":["fixture"]}
        with self.assertRaises(D.Stop) as error:D.select(c,l,idx)
        self.assertEqual(error.exception.status,"BLOCKED")

    def test_normalized_exact_casefold_whitespace(self):
        a=D.fingerprint(prose(10),tokenize);b=D.fingerprint("\t"+prose(10).upper().replace(" ","  \n")+"  ",tokenize)
        self.assertIn("NORMALIZED_EXACT",D.overlaps(a,b))

    def test_exact32_token_boundary_and_not31(self):
        empty={"normalized":None,"word12":set(),"word5":set()}
        a={**empty,"token32":D.grams(list(range(129)),32)}
        b={**empty,"token32":D.grams([900]+list(range(10,42))+[901],32)}
        c={**empty,"token32":D.grams([900]+list(range(10,41))+[901],32)}
        self.assertEqual(D.overlaps(a,b),["TOKEN32"]);self.assertEqual(D.overlaps(a,c),[])

    def test_exact12_word_boundary(self):
        words=["token"+str(i) for i in range(13)];a=D.fingerprint(" ".join(words),tokenize)
        b=D.fingerprint("different "+" ".join(words[:12]),tokenize)
        self.assertIn("WORD12",D.overlaps(a,b))

    def test_word5_containment_integer_half_and_minimum(self):
        empty={"normalized":None,"token32":set(),"word12":set()}
        a={**empty,"word5":set(range(20))};b={**empty,"word5":set(range(10))|set(range(100,110))}
        self.assertEqual(D.overlaps(a,b),["WORD5_CONTAINMENT_GE_HALF"])
        b["word5"]=set(range(9))|set(range(100,111));self.assertEqual(D.overlaps(a,b),[])
        b["word5"]=set(range(19));self.assertEqual(D.overlaps(a,b),[])

    def test_index_matches_direct_rules_and_token_array(self):
        c,l=collect();idx=D.ExclusionIndex(c);witness={"path":"fixture"}
        idx.text(c[2]["text"],witness,tokenize)
        self.assertIn("NORMALIZED_EXACT",idx.matches[c[2]["id"]]["reasons"])
        idx.tokens(c[3]["fingerprint"]["ids"],witness)
        self.assertIn("TOKEN32",idx.matches[c[3]["id"]]["reasons"])
        self.assertEqual(idx.string_count,1);self.assertEqual(idx.token_array_count,1)

    def test_selected_new_duplicate_is_rejected_before_next_rank(self):
        c,l=collect(28);first=min((x for x in c if x["label"]==0),key=lambda x:x["id"])
        later=max((x for x in c if x["label"]==0),key=lambda x:x["id"])
        later["fingerprint"]=first["fingerprint"]
        selected=D.select(c,l,D.ExclusionIndex(c))
        self.assertNotIn(later["id"],{x["id"] for x in selected})
        self.assertEqual(next(r for r in l if r["id"]==later["id"])["decision"],"EXCLUDE_NEW_DUPLICATE")

    def test_json_jsonl_csv_tsv_python_xml_leaves(self):
        raw=json.dumps({"text":prose(1),"token_ids":list(range(129))}).encode()
        leaves=list(D.byte_leaves(raw,"json","fixture.json"));self.assertEqual([x[0] for x in leaves],["text","tokens"])
        self.assertEqual(len(list(D.byte_leaves(raw+b"\n"+raw+b"\n","jsonl","fixture.jsonl"))),4)
        self.assertEqual([v for _,v,_ in D.byte_leaves(b'a,b\nc,d\n',"csv","fixture.csv")],["a","b","c","d"])
        self.assertEqual([v for _,v,_ in D.byte_leaves(b'a\tb\n',"tsv","fixture.tsv")],["a","b"])
        self.assertEqual(list(D.byte_leaves(b'x="hello"\ny=[0]*129\n',"python","fixture.py"))[0][1],"hello")
        self.assertEqual([v for _,v,_ in D.byte_leaves(b'<r><x>hello</x><x>world</x></r>',"xml","fixture.xml")],["hello","world"])

    def test_duplicate_json_key_and_bad_tail_block(self):
        with self.assertRaises(D.Stop):D.strict_json('{"x":1,"x":2}')
        with self.assertRaises(json.JSONDecodeError):list(D.byte_leaves(b'{"x":1}\n{"broken":',"jsonl","fixture.jsonl"))

    def test_history_duplicate_values_and_nonfinite_metadata_preserve_all_text(self):
        raw=b'{"text":"first retained value","text":"second retained value","loss":NaN,"nested":{"a":"third retained value","n":Infinity,"m":-Infinity}}'
        leaves=list(D.byte_leaves(raw,"json","fixture.json"))
        self.assertEqual([v for typ,v,_ in leaves if typ=="text"],["first retained value","second retained value","third retained value"])
        note=next(v for typ,v,_ in leaves if typ=="format_note")
        self.assertEqual(note,{"duplicate_keys":1,"nonfinite_numeric_constants":3})
        self.assertEqual(len({where for typ,_,where in leaves if typ=="text"}),3)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"history.json";p.write_bytes(raw);idx=D.ExclusionIndex([])
            ledger=D.scan_history([{"path":str(p),**D.pin(p),"kind":"json"}],idx,tokenize)
            self.assertEqual(idx.string_count,3);self.assertEqual(idx.format_notes,note)
            self.assertEqual(ledger[0]["format_notes"][0]["duplicate_keys"],1)

    def test_expected_inventory_count_and_suffixes_are_enforced(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/"known.txt";p.write_text("known")
            spec={"history_roots":[str(root)],"discover_before_acquisition":True,"expected_history_file_count":1,"expected_history_suffixes":{".txt":1}}
            self.assertEqual(len(D.verify_inventory(spec)),1)
            spec["expected_history_file_count"]=2
            with self.assertRaises(D.Stop):D.verify_inventory(spec)
            spec["expected_history_file_count"]=1;spec["expected_history_suffixes"]={".json":1}
            with self.assertRaises(D.Stop):D.verify_inventory(spec)

    def test_archive_unknown_member_blocks_and_no_extraction(self):
        b=io.BytesIO()
        with zipfile.ZipFile(b,"w") as z:z.writestr("data.json",'{"text":"hello"}')
        self.assertEqual(list(D.byte_leaves(b.getvalue(),"zip","fixture.zip"))[0][1],"hello")
        b=io.BytesIO()
        with zipfile.ZipFile(b,"w") as z:z.writestr("unknown.opaque",b"data")
        with self.assertRaises(D.Stop) as error:list(D.byte_leaves(b.getvalue(),"zip","fixture.zip"))
        self.assertEqual(error.exception.status,"BLOCKED")

    def test_base64_gzip_tar_text_and_registered_binary_member(self):
        raw=io.BytesIO();text=b'{"text":"historical prose"}';binary=b"checkpoint"
        with tarfile.open(fileobj=raw,mode="w") as tar:
            for name,data in [("data.json",text),("model.pt",binary)]:
                info=tarfile.TarInfo(name);info.size=len(data);tar.addfile(info,io.BytesIO(data))
        encoded=D.base64.b64encode(D.gzip.compress(raw.getvalue(),mtime=0))
        member="fixture.b64!base64!decoded!model.pt"
        policy={member:{"bytes":len(binary),"sha256":D.sha(binary),"kind":"nontext","reason":"Synthetic frozen checkpoint member"}}
        values=list(D.byte_leaves(encoded,"base64","fixture.b64",member_policy=policy))
        self.assertEqual(values[0][1],"historical prose");self.assertEqual(values[1][0],"nontext")
        policy[member]["sha256"]="0"*64
        with self.assertRaises(D.Stop):list(D.byte_leaves(encoded,"base64","fixture.b64",member_policy=policy))

    def test_compressed_nontext_registry_exact_pin(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/"policy.json.gz";value={"/fixture.bin":{"bytes":4,"sha256":"f"*64,"reason":"fixture"}}
            p.write_bytes(D.gzip.compress(D.canonical(value),mtime=0))
            spec={"nontext_entries_path":str(p),"nontext_entries_pin":D.pin(p)}
            self.assertEqual(D.policy_mapping(spec,"nontext_entries"),value)
            spec["nontext_entries_pin"]["sha256"]="0"*64
            with self.assertRaises(D.Stop):D.policy_mapping(spec,"nontext_entries")

    def test_unicode_short_text_still_matches32_token_ids(self):
        c,l=collect();c=c[:1];c[0]["fingerprint"]["token32"]={tuple(range(32))};idx=D.ExclusionIndex(c)
        idx.text("\U0001f603"*8,{"path":"fixture"},lambda _:list(range(32)))
        self.assertIn("TOKEN32",idx.matches[c[0]["id"]]["reasons"])

    def test_cached_and_uncached_history_have_identical_exclusions(self):
        c,_=collect();cached=D.ExclusionIndex(c);uncached=D.ExclusionIndex(c)
        texts=[c[0]["text"],prose(88),c[0]["text"],prose(88),c[1]["text"]]
        for i,text in enumerate(texts):cached.text(text,{"path":str(i)},tokenize)
        with patch.object(D,"TEXT_CACHE_LIMIT",0):
            for i,text in enumerate(texts):uncached.text(text,{"path":str(i)},tokenize)
        self.assertEqual(cached.matches,uncached.matches)
        self.assertEqual(cached.string_count,uncached.string_count)
        self.assertEqual(cached.text_fingerprints,3);self.assertEqual(cached.text_cache_hits,2)
        self.assertEqual(uncached.text_fingerprints,5);self.assertEqual(uncached.text_cache_hits,0)

    def test_external_extra_file_list_and_inventory_retain_paths_and_pins(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);root=base/"root";root.mkdir()
            inside=root/"inside.txt";inside.write_text("inside")
            outside=base/"outside.txt";outside.write_text("outside")
            other=base/"other.txt";other.write_text("other")
            inventory=base/"old.json.gz";inventory.write_bytes(D.gzip.compress(D.canonical({str(inside):D.pin(inside),str(outside):D.pin(outside)}),mtime=0))
            extra=base/"extra.json.gz";extra.write_bytes(D.gzip.compress(D.canonical([str(other)]),mtime=0))
            spec={"history_roots":[str(root)],"discover_before_acquisition":True,
                  "extra_history_inventory_path":str(inventory),"extra_history_inventory_pin":D.pin(inventory),
                  "extra_history_files_path":str(extra),"extra_history_files_pin":D.pin(extra)}
            self.assertEqual({e["path"] for e in D.verify_inventory(spec)},{str(inside),str(outside),str(other)})
            outside.write_text("changed")
            with self.assertRaises(D.Stop):D.verify_inventory(spec)

    def test_acquisition_records_success_http_error_and_hash_failure(self):
        class Response(io.BytesIO):
            url="https://fixture.invalid/frozen";headers={"Content-Length":"4"}
            def __init__(self,data,status):super().__init__(data);self.status=status
        body=b"good";expected={"bytes":len(body),"sha256":D.sha(body)}
        for status,received,want in [(200,body,"PASS"),(403,b"deny","BLOCKED"),(200,b"bad!","FAIL")]:
            with self.subTest(status=status,received=received),tempfile.TemporaryDirectory() as tmp,patch.object(D,"CORPUS_PIN",expected),patch.object(D.urllib.request,"urlopen",return_value=Response(received,status)):
                w=D.BudgetWriter(tmp)
                if want=="PASS":self.assertEqual(D.acquire(w)[0],body)
                else:
                    with self.assertRaises(D.Stop) as error:D.acquire(w)
                    self.assertEqual(error.exception.status,want)
                receipt=json.loads((Path(tmp)/"acquisition.json").read_text())
                self.assertEqual(receipt["Status"],want);self.assertEqual(receipt["http_status"],status)
                self.assertEqual(receipt["actual_response"],{"bytes":len(received),"sha256":D.sha(received)})
                self.assertEqual((Path(tmp)/receipt["response_file"]).read_bytes(),received)

    def test_acquisition_network_error_retains_partial_body_without_retry(self):
        class Response(io.BytesIO):
            url="https://fixture.invalid/frozen";status=200;headers={}
            def __init__(self):super().__init__(b"go");self.calls=0
            def read(self,n=-1):
                self.calls+=1
                if self.calls>1:raise OSError("synthetic interrupted connection")
                return super().read(n)
        with tempfile.TemporaryDirectory() as tmp,patch.object(D,"CORPUS_PIN",{"bytes":4,"sha256":D.sha(b"good")}),patch.object(D.urllib.request,"urlopen",return_value=Response()) as opener:
            with self.assertRaises(D.Stop) as error:D.acquire(D.BudgetWriter(tmp))
            self.assertEqual(error.exception.status,"BLOCKED");self.assertEqual(opener.call_count,1)
            receipt=json.loads((Path(tmp)/"acquisition.json").read_text())
            self.assertEqual(receipt["actual_response"],{"bytes":2,"sha256":D.sha(b"go")})
            self.assertEqual((Path(tmp)/receipt["response_file"]).read_bytes(),b"go")

    def test_history_ledger_keeps_all_physical_paths_reuses_payload(self):
        c,_=collect();idx=D.ExclusionIndex(c)
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);raw=json.dumps({"text":c[0]["text"]}).encode();entries=[]
            for n in ("a.json","b.json"):
                p=base/n;p.write_bytes(raw);entries.append({"path":str(p),**D.pin(p),"kind":"json"})
            ledger=D.scan_history(entries,idx,tokenize)
            self.assertEqual(len(ledger),2);self.assertEqual(ledger[1]["Status"],"PASS_IDENTICAL_PAYLOAD")
            self.assertEqual(idx.string_count,1);self.assertEqual(ledger[1]["identical_to"],str(base/"a.json"))

    def test_partial_history_ledger_preserved_on_parse_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"bad.json";p.write_text("{");ledger=[]
            with self.assertRaises(D.Stop):D.scan_history([{"path":str(p),**D.pin(p),"kind":"json"}],D.ExclusionIndex([]),tokenize,ledger=ledger)
            self.assertEqual(len(ledger),1);self.assertEqual(ledger[0]["Status"],"BLOCKED")

    def test_discovery_blocks_unknown_file_and_requires_nontext_pin(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/"potential.bin";p.write_bytes(b"unknown")
            spec={"history_roots":[str(root)],"discover_before_acquisition":True}
            with self.assertRaises(D.Stop):D.verify_inventory(spec)
            spec["nontext_entries"]={str(p):{**D.pin(p),"reason":"Synthetic fixture only; explicit test classification"}}
            self.assertEqual(D.verify_inventory(spec)[0]["kind"],"nontext")
            p.write_bytes(b"changed")
            with self.assertRaises(D.Stop):D.verify_inventory(spec)

    def test_explicit_inventory_detects_new_missing_changed_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/"old.txt";p.write_text("known")
            spec={"history_roots":[str(root)],"history_entries":[{"path":str(p),**D.pin(p),"kind":"text"}]}
            self.assertEqual(len(D.verify_inventory(spec)),1)
            q=root/"new.txt";q.write_text("new")
            with self.assertRaises(D.Stop):D.verify_inventory(spec)
            q.unlink();p.write_text("changed")
            with self.assertRaises(D.Stop):D.verify_inventory(spec)

    def test_budget_seal_reserve_exclusive_compression_and_confinement(self):
        with tempfile.TemporaryDirectory() as tmp:
            w=D.BudgetWriter(tmp);receipt=w.compressed("ledger.json.gz",{"all":[1,2,3]})
            self.assertEqual(D.gzip.decompress((Path(tmp)/"ledger.json.gz").read_bytes()),D.canonical({"all":[1,2,3]}))
            self.assertEqual(receipt["physical"],D.pin(Path(tmp)/"ledger.json.gz"))
            with self.assertRaises(FileExistsError):w.json("ledger.json.gz",{})
            with self.assertRaises(D.Stop):w.write("../escape",b"x")
            with patch.object(D,"PREP_BUDGET",D.SEAL_ALLOWANCE+1):
                with self.assertRaises(D.Stop):w.write("over",b"ab")

    def test_no_numerical_or_corpus_imports(self):
        self.assertFalse({"numpy","pyarrow","tokenizers","torch","parcae_lm","receval","transformers"}&{n.split(".")[0] for n in sys.modules})


def main():
    p=argparse.ArgumentParser();p.add_argument("--report",type=Path,required=True);args=p.parse_args()
    suite=unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    def flatten(s):return [x for test in s for x in (flatten(test) if isinstance(test,unittest.TestSuite) else [test.id()])]
    ids=flatten(suite);result=unittest.TextTestRunner(verbosity=2).run(suite)
    report={"Purpose":"Synthetic model-blind source selection, historical exclusion and bounded storage fixtures","Environment":sys.version,
            "Input":"Synthetic text/containers only; no real source, tokenizer, numerical dependency or model","Expected":"All exact planned fixtures pass with no skips",
            "Actual":{"test_ids":ids,"planned":len(ids),"run":result.testsRun,"failures":len(result.failures),"errors":len(result.errors),"skipped":len(result.skipped)},
            "Status":"PASS" if result.wasSuccessful() and not result.skipped else "FAIL"}
    with args.report.open("x",encoding="utf-8",newline="\n") as f:json.dump(report,f,indent=2);f.write("\n")
    return 0 if report["Status"]=="PASS" else 1


if __name__=="__main__":raise SystemExit(main())
