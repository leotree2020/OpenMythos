"""Synthetic/parser-only v4 fixtures; no target, model or corpus acquisition."""
import argparse
import ast
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


def leaves(source):return list(D.byte_leaves(source.encode(),"python","fixture.py"))
def values(rows,kind):return [v for t,v,_ in rows if t==kind]


class HistoryPythonV4Tests(unittest.TestCase):
    def test_actual_pinned_blocker_retains_raw_and_late_literals(self):
        p=ROOT/"fixtures/history_invalid_inventory.txt";raw=p.read_bytes()
        self.assertEqual(D.pin(p),{"bytes":2345,"sha256":"403eee09aec392aa00eb24b46633e64c1333377f13b80e503e4ebf3f7a834bb8"})
        with self.assertRaises(SyntaxError):ast.parse(raw)
        result=list(D.byte_leaves(raw,"python",str(p)))
        self.assertEqual(result[0],("text",raw.decode("utf-8-sig"),"python_raw_source"))
        self.assertIn("inventory_bytes",values(result,"text"));self.assertIn("PASS",values(result,"text"))
        note=values(result,"python_recovery")[0]
        self.assertTrue(note["raw_source_covered"]);self.assertFalse(note["semantic_reconstruction"])
        self.assertEqual(note["files"],1);self.assertEqual(note["raw_utf8_bytes"],2345)

    def test_valid_ast_leaf_behavior_is_unchanged(self):
        source='a="alpha"; b="beta"\nids='+repr(list(range(32)))+'\nx=f"prefix {1} suffix"\n'
        tree=ast.parse(source);expected=[]
        for node in ast.walk(tree):
            if isinstance(node,ast.Constant) and isinstance(node.value,str):expected.append(("text",node.value,"line:"+str(node.lineno)))
            elif isinstance(node,(ast.List,ast.Tuple)) and len(node.elts)>=32 and all(isinstance(n,ast.Constant) and type(n.value)is int and 0<=n.value<32768 for n in node.elts):expected.append(("tokens",[n.value for n in node.elts],"line:"+str(node.lineno)))
        self.assertEqual(leaves(source),expected)

    def test_unterminated_single_quote_does_not_hide_later_string(self):
        source='broken="first\nnext="later complete words"\n'
        result=leaves(source);self.assertEqual(values(result,"text")[0],source)
        self.assertIn("later complete words",values(result,"text"))

    def test_unterminated_triple_quote_does_not_hide_later_string(self):
        source="broken='''never closed\nnext=\"later complete words\"\n"
        self.assertIn("later complete words",values(leaves(source),"text"))

    def test_escaped_raw_unicode_and_multiline_literals_recovered(self):
        source='broken="x\nplain="one\\nline\\tword\\u4e2d"\nraw=r"literal\\nbackslash"\nmulti="""first\nsecond"""\n'
        strings=values(leaves(source),"text")
        self.assertIn("one\nline\tword中",strings);self.assertIn(r"literal\nbackslash",strings)
        self.assertIn("first\nsecond",strings)

    def test_adjacent_literals_across_comment_are_conservatively_joined(self):
        source='broken="x\nvalue=("first " # retained comment\n "second")\n'
        result=leaves(source);self.assertIn("first second",values(result,"text"))
        self.assertGreater(values(result,"python_recovery")[0]["adjacent_string_groups"],0)

    def test_token_arrays_after_unmatched_quotes_and_brackets_recovered(self):
        ids=list(range(40));source="bad='''unclosed\nopen=[\nids="+repr(ids)+"\npair="+repr(tuple(ids))+"\n"
        self.assertGreaterEqual(values(leaves(source),"tokens").count(ids),2)

    def test_bool_negative_and_short_arrays_not_token_witnesses(self):
        source='bad="x\n'+'\n'.join('x='+repr(v) for v in ([True]*32,[-1]*32,list(range(31))))
        self.assertEqual(values(leaves(source),"tokens"),[])

    def test_expression_source_never_executes_and_remains_raw_covered(self):
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/"must_not_exist"
            source='bad="x\n__import__("pathlib").Path('+repr(str(output))+').write_text("executed")\n'
            result=leaves(source);self.assertFalse(output.exists());self.assertEqual(result[0][1],source)

    def test_recovery_resource_bound_blocks_instead_of_skipping(self):
        with patch.object(D,"PYTHON_RECOVERY_CHAR_BUDGET",1):
            with self.assertRaises(D.Stop) as error:leaves('bad="x\nlater="longer text"')
            self.assertEqual(error.exception.status,"BLOCKED")

    def test_adjacent_literal_quadratic_work_is_charged_to_same_bound(self):
        source='bad=)\nx=('+('"x" '*100)+')\n'
        with patch.object(D,"PYTHON_RECOVERY_CHAR_BUDGET",800):
            with self.assertRaisesRegex(D.Stop,"adjacent recovery resource bound") as error:leaves(source)
            self.assertEqual(error.exception.status,"BLOCKED")

    def test_unmatched_bracket_tail_scans_are_charged_to_same_bound(self):
        source='bad=\n'+('['*50)
        with patch.object(D,"PYTHON_RECOVERY_CHAR_BUDGET",100):
            with self.assertRaisesRegex(D.Stop,"lexical recovery resource bound") as error:leaves(source)
            self.assertEqual(error.exception.status,"BLOCKED")

    def test_preflight_parser_counts_match_full_ledger_projection_without_tokenizer(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);p=root/"old.py";p.write_text('bad="x\nlater="retained"\nids='+repr(list(range(32))))
            entries=[{"path":str(p),**D.pin(p),"kind":"python"}]
            pre=D.ParseOnlyIndex();full=D.ExclusionIndex([])
            with redirect_stdout(io.StringIO()):
                before=D.scan_history(entries,pre,lambda _:self.fail("preflight tokenizer called"))
                after=D.scan_history(entries,full,lambda s:list(range(len(s.split()))))
            self.assertEqual(D.preflight_projection(before),D.preflight_projection(after))
            self.assertEqual(pre.python_recovery,full.python_recovery)
            self.assertEqual(pre.string_count,full.string_count);self.assertEqual(pre.token_array_count,full.token_array_count)
            self.assertEqual(pre.python_recovery["files"],1)

    def test_unknown_and_malformed_other_formats_still_block(self):
        with self.assertRaises(D.Stop):list(D.byte_leaves(b"anything","opaque","file.opaque"))
        with self.assertRaises(json.JSONDecodeError):list(D.byte_leaves(b'{"broken":',"json","file.json"))

    def source_fixture(self,root):
        retained=root/"retained";retained.mkdir();source=retained/"corpus.parquet";source.write_bytes(b"frozen fixture corpus")
        pin=D.pin(source);old={"Status":"PASS","url":D.URL,"http_status":200,"actual_response":pin,"pin":pin,"response_file":"corpus.parquet"}
        (retained/"acquisition.json").write_bytes(D.canonical(old));out=root/"new";out.mkdir()
        return source,pin,out

    def test_local_source_reuse_is_byte_exact_no_network_and_no_duplicate(self):
        with tempfile.TemporaryDirectory() as directory:
            source,pin,out=self.source_fixture(Path(directory))
            with patch.object(D,"RETAINED_CORPUS",str(source)),patch.object(D,"CORPUS_PIN",pin),patch.object(D.urllib.request,"urlopen",side_effect=AssertionError("Network forbidden")):
                data,receipt,before=D.retained_source(D.BudgetWriter(out),source)
            self.assertEqual(data,source.read_bytes());self.assertFalse((out/"corpus.parquet").exists())
            self.assertEqual(set(p.name for p in out.iterdir()),{"acquisition.json","source_reference.json"})
            ref=json.loads((out/"source_reference.json").read_bytes());self.assertEqual(ref["source_pin"],pin)
            self.assertEqual(receipt["network_requests"],0);self.assertEqual(receipt["copied_corpus_bytes"],0)
            self.assertEqual(receipt["source_reference_pin"],D.pin(out/"source_reference.json"));self.assertEqual(before[str(source)],pin)

    def test_local_source_requires_exact_original_receipt_and_path(self):
        with tempfile.TemporaryDirectory() as directory:
            source,pin,out=self.source_fixture(Path(directory))
            with patch.object(D,"RETAINED_CORPUS",str(source)),patch.object(D,"CORPUS_PIN",pin):
                with self.assertRaises(D.Stop):D.retained_source(D.BudgetWriter(out),source.with_name("other.parquet"))
                receipt=source.parent/"acquisition.json";old=json.loads(receipt.read_bytes());old["http_status"]=403;receipt.write_bytes(D.canonical(old))
                with self.assertRaises(D.Stop):D.retained_source(D.BudgetWriter(out),source)
                self.assertFalse(list(out.iterdir()))

    def test_real_isolated_cli_and_no_numerical_imports(self):
        result=subprocess.run([sys.executable,"-I","-B",str(ROOT/"data_prepare.py"),"--help"],capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr);self.assertIn("--source-file",result.stdout);self.assertIn("--history-preflight-only",result.stdout)
        self.assertFalse({"numpy","pyarrow","tokenizers","torch","parcae_lm"}&{n.split(".")[0] for n in sys.modules})

    def test_shared_preflight_and_data_envelope_cannot_double_spend_budget(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);pre=root/"history-preflight";out=root/"data";pre.mkdir();out.mkdir()
            (pre/"manifest.json").write_bytes(b"x"*20);writer=D.BudgetWriter(out,shared_paths=(pre,))
            self.assertEqual(writer.used(),20)
            with patch.object(D,"PREP_BUDGET",D.SEAL_ALLOWANCE+25):
                writer.write("within",b"12345")
                with self.assertRaises(D.Stop):writer.write("over",b"1")


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--report",required=True,type=Path);args=p.parse_args()
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(HistoryPythonV4Tests);ids=sorted(t.id() for t in suite)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    report={"Purpose":"Malformed retained Python, parser preflight and exact local-corpus reuse fixtures","Environment":{"python":sys.version,"development_only":True},"Input":"Synthetic files plus pinned actual invalid-source text; no corpus/tokenizer/model access","Expected":{"test_ids":ids,"tests":len(ids)},"Actual":{"test_ids":ids,"planned":len(ids),"run":result.testsRun,"failures":len(result.failures),"errors":len(result.errors),"skipped":len(result.skipped),"expected_failures":len(result.expectedFailures),"unexpected_successes":len(result.unexpectedSuccesses),"failure_details":[[t.id(),s] for t,s in result.failures+result.errors]},"Status":"PASS" if result.wasSuccessful() and result.testsRun==len(ids) and not result.skipped else "FAIL"}
    with args.report.open("x",encoding="utf-8") as f:json.dump(report,f,indent=2,ensure_ascii=False);f.write("\n")
    raise SystemExit(0 if report["Status"]=="PASS" else 1)
