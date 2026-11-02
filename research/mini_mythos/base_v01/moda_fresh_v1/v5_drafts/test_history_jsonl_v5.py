"""Synthetic historical JSONL coverage fixtures; no target or corpus access."""
import argparse
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import data_prepare as D


def leaves(raw):return list(D.byte_leaves(raw,"jsonl","synthetic.jsonl"))
def strings(rows):return [v for typ,v,_ in rows if typ=="text"]
def recovery(rows):return next(v for typ,v,_ in rows if typ=="jsonl_recovery")


class HistoryJSONLV5Tests(unittest.TestCase):
    def test_complete_valid_records_keep_exact_existing_leaves(self):
        raw='{"text":"first","text":"second","n":NaN}\n'+json.dumps({"ids":list(range(32)),"text":"third"})+'\n'
        expected=[]
        for i,line in enumerate(raw.split("\n")):
            if line:
                value,notes=D.history_json(line);where="line:"+str(i+1)
                if any(notes.values()):expected.append(("format_note",notes,where))
                expected.extend(D.json_leaves(value,where))
        self.assertEqual(leaves(raw.encode()),expected)

    def test_7536_complete_records_and_2000_character_tail_are_retained(self):
        good='{"text":"synthetic complete record"}\n';tail='{"text":"'+('x'*(2000-len('{"text":"')))
        raw=(good*7536+tail).encode();result=leaves(raw);note=recovery(result)
        self.assertEqual(strings(result).count("synthetic complete record"),7536)
        self.assertIn(tail,strings(result));self.assertIn("x"*(2000-len('{"text":"')),strings(result))
        self.assertEqual((note["complete_valid_records"],note["malformed_records"]),(7536,1))
        record=note["records"][0];self.assertEqual((record["record_index"],record["line"]),(7536,7537))
        self.assertEqual(record["raw_utf8_bytes"],2000);self.assertEqual(record["raw_sha256"],D.sha(tail.encode()))

    def test_physical_lf_only_preserves_unicode_separators_inside_strings(self):
        text="alpha\u2028beta\u2029gamma\x85delta";raw=(json.dumps({"text":text},ensure_ascii=False)+'\n').encode()
        self.assertEqual(strings(leaves(raw)),[text]);self.assertFalse(any(t=="jsonl_recovery" for t,_,_ in leaves(raw)))

    def test_ascii_blank_records_only_and_crlf_raw_preservation(self):
        raw=b' \t\r\n{"text":"valid"}\r\n{"text":"truncated\r\n'+"\u2028\n".encode()
        result=leaves(raw);note=recovery(result)
        self.assertEqual((note["complete_valid_records"],note["malformed_records"]),(1,2))
        self.assertIn('{"text":"truncated\r\n',strings(result));self.assertIn("\u2028\n",strings(result))
        self.assertEqual([r["record_index"] for r in note["records"]],[2,3])

    def test_bom_valid_behavior_and_malformed_raw_bytes_preserved(self):
        self.assertEqual(strings(leaves(b'\xef\xbb\xbf{"text":"valid"}\n')),["valid"])
        raw=b'\xef\xbb\xbf{"text":"truncated';result=leaves(raw);note=recovery(result)
        self.assertEqual(strings(result)[0].encode(),raw);self.assertEqual(note["raw_utf8_bytes"],len(raw))

    def test_complete_json_escapes_decode_exactly_as_standard_parser(self):
        value='quote" slash/ backslash\\ tab\t newline\n carriage\r back\b form\f snow雪 smile😀'
        encoded=json.dumps(value,ensure_ascii=True);raw=('bad '+encoded).encode()
        self.assertIn(value,strings(leaves(raw)))
        work=D.JSONLRecoveryWork();decoded,end,term=D.json_string_prefix(encoded,0,work)
        self.assertEqual((decoded,end,term),(json.loads(encoded),len(encoded),"COMPLETE"))

    def test_truncated_escape_units_do_not_invent_missing_bytes(self):
        for ending in ('\\','\\u','\\u1','\\u12','\\u123','\\uD83D','\\uD83D\\uDE'):
            with self.subTest(ending=ending):
                raw=('{"text":"safe'+ending).encode();result=leaves(raw);note=recovery(result)
                self.assertIn("safe",strings(result));self.assertGreater(note["truncated_escapes"],0)
                self.assertTrue(all("�" not in s for s in strings(result)))
                self.assertEqual(strings(result)[0].encode(),raw)

    def test_surrogate_pairs_combine_and_unpaired_units_stop_prefix(self):
        for source,expected in ((r'"safe\uD83D\uDE00 done"',"safe😀 done"),(r'"safe\uD83Dx"',"safe"),(r'"safe\uDE00x"',"safe")):
            with self.subTest(source=source):
                decoded,_,_=D.json_string_prefix(source,0,D.JSONLRecoveryWork());self.assertEqual(decoded,expected);decoded.encode()

    def test_invalid_escape_does_not_hide_later_complete_string(self):
        result=leaves(br'{"bad":"safe\q invalid","later":"later decoded\ntext"}')
        self.assertIn("safe",strings(result));self.assertIn("later decoded\ntext",strings(result))

    def test_invalid_control_prefix_and_later_physical_record_retained(self):
        raw=b'{"text":"safe\x01bad"}\n{"text":"after"}\n';result=leaves(raw)
        self.assertIn("safe",strings(result));self.assertIn("after",strings(result))
        self.assertEqual(recovery(result)["complete_valid_records"],1)

    def test_complete_token_arrays_recovered_after_malformed_prefix(self):
        ids=list(range(40));raw=('bad [ '+json.dumps(ids)+' more').encode();result=leaves(raw)
        self.assertIn(ids,[v for typ,v,_ in result if typ=="tokens"]);self.assertEqual(recovery(result)["token_arrays"],1)

    def test_token_array_recovery_rejects_partial_boolean_negative_and_short(self):
        for value in ([True]*32,[-1]*32,list(range(31))):
            with self.subTest(value=value):self.assertFalse(any(t=="tokens" for t,_,_ in leaves(('bad '+json.dumps(value)).encode())))
        self.assertFalse(any(t=="tokens" for t,_,_ in leaves(('bad '+json.dumps(list(range(40)))[:-1]).encode())))

    def test_no_expression_or_source_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/"must_not_exist";raw=('bad __import__("pathlib").Path('+repr(str(p))+').write_text("executed")').encode()
            result=leaves(raw);self.assertFalse(p.exists());self.assertEqual(strings(result)[0].encode(),raw)

    def test_invalid_utf8_and_ordinary_json_are_not_repaired(self):
        with self.assertRaises(UnicodeDecodeError):leaves(b'{"x":"\xff"}')
        with self.assertRaises(json.JSONDecodeError):list(D.byte_leaves(b'{"x":',"json","old.json"))
        with self.assertRaises(D.Stop):D.strict_json('{"x":1,"x":2}')

    def test_quote_recovery_work_bound_stops_instead_of_skipping(self):
        raw=('bad '+('" '+('x'*30)+' ')*20).encode()
        with patch.object(D,"JSONL_RECOVERY_CHAR_BUDGET",2000):
            with self.assertRaisesRegex(D.Stop,"JSONL recovery resource bound") as error:leaves(raw)
            self.assertEqual(error.exception.status,"BLOCKED")

    def test_failed_bracket_search_and_emitted_prefix_charge_work(self):
        with patch.object(D,"JSONL_RECOVERY_CHAR_BUDGET",300):
            with self.assertRaises(D.Stop):leaves(b'bad '+b'['*60)
        work=D.JSONLRecoveryWork()
        with patch.object(D,"JSONL_RECOVERY_CHAR_BUDGET",5):
            with self.assertRaises(D.Stop):D.json_string_prefix('"abcd"',0,work)

    def test_work_bound_is_shared_across_malformed_records(self):
        raw=b'bad "words"\n'
        with patch.object(D,"JSONL_RECOVERY_CHAR_BUDGET",100):
            self.assertTrue(leaves(raw))
            with self.assertRaises(D.Stop):leaves(raw*10)

    def test_preflight_and_full_scan_have_identical_notes_and_projection(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/"history.jsonl";p.write_bytes(b'{"text":"valid"}\nbad "retained\\ntext" '+json.dumps(list(range(32))).encode())
            entries=[{"path":str(p),**D.pin(p),"kind":"jsonl"}];pre=D.ParseOnlyIndex();full=D.ExclusionIndex([])
            with redirect_stdout(io.StringIO()):
                before=D.scan_history(entries,pre,lambda _:self.fail("Tokenizer in preflight"))
                after=D.scan_history(entries,full,lambda s:list(range(len(s.split()))))
            self.assertEqual(before,after);self.assertEqual(D.preflight_projection(before),D.preflight_projection(after))
            self.assertEqual(pre.jsonl_recovery,full.jsonl_recovery);self.assertEqual(pre.jsonl_recovery["files"],1)

    def test_raw_and_decoded_prefix_create_historical_exclusion_witness(self):
        text=" ".join("word"+str(i) for i in range(40));tokenize=lambda s:[ord(c)%100 for c in s]
        candidate={"id":"candidate","fingerprint":D.fingerprint(text,tokenize)};index=D.ExclusionIndex([candidate])
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/"old.jsonl";p.write_bytes(('{"text":"'+text.replace(' ','\\u0020')).encode())
            with redirect_stdout(io.StringIO()):D.scan_history([{"path":str(p),**D.pin(p),"kind":"jsonl"}],index,tokenize)
        self.assertIn("candidate",index.matches);self.assertTrue(index.matches["candidate"]["reasons"])

    def test_exact_isolated_cli_imports_no_numerical_packages(self):
        result=subprocess.run([sys.executable,"-I","-B",str(ROOT/"data_prepare.py"),"--help"],capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertFalse({"numpy","pyarrow","tokenizers","torch","parcae_lm"}&{n.split(".")[0] for n in sys.modules})


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--report",required=True,type=Path);args=p.parse_args()
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(HistoryJSONLV5Tests);ids=sorted(t.id() for t in suite)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    report={"Purpose":"Conservative malformed historical JSONL coverage and bounded recovery","Environment":{"python":sys.version,"development_only":True},"Input":"Synthetic JSONL only; no actual source corpus, model or target access","Expected":{"test_ids":ids,"tests":len(ids)},"Actual":{"test_ids":ids,"planned":len(ids),"run":result.testsRun,"failures":len(result.failures),"errors":len(result.errors),"skipped":len(result.skipped),"expected_failures":len(result.expectedFailures),"unexpected_successes":len(result.unexpectedSuccesses),"failure_details":[[t.id(),s] for t,s in result.failures+result.errors]},"Status":"PASS" if result.wasSuccessful() and result.testsRun==len(ids) and not result.skipped else "FAIL"}
    with args.report.open("x",encoding="utf-8") as f:json.dump(report,f,indent=2,ensure_ascii=False);f.write("\n")
    raise SystemExit(0 if report["Status"]=="PASS" else 1)
