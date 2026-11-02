"""CPU-only independent cases for complete-path custody hashing and I/O cleanup."""
from __future__ import annotations
import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent
sp=importlib.util.spec_from_file_location("scope_operator_under_test",ROOT/"execute_combo.py")
operator=importlib.util.module_from_spec(sp);sys.modules[sp.name]=operator;sp.loader.exec_module(operator)


class ScopeTests(unittest.TestCase):
    def test_same_path_once_but_different_hardlink_paths_both_hashed(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);a=root/"a";b=root/"b";a.write_bytes(b"same payload");os.link(a,b)
            original=operator.info;calls=[];lock=threading.Lock()
            def counted(path):
                with lock:calls.append(str(path))
                return original(path)
            with patch.object(operator,"info",side_effect=counted):
                result=operator.hash_paths([str(a),str(a),str(b)],workers=4)
            self.assertEqual(set(result),{str(a),str(b)})
            self.assertEqual(sorted(calls),sorted([str(a),str(b)]))
            self.assertEqual(result[str(a)],result[str(b)])

    def test_changed_expected_pin_propagates_and_every_thread_joins(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"a";p.write_bytes(b"changed")
            before={t.name for t in threading.enumerate()}
            with self.assertRaises(operator.Stop) as error:
                operator.hash_paths([str(p)],{str(p):dict(bytes=3,sha256="0"*64)})
            self.assertEqual(error.exception.status,"FAIL")
            self.assertFalse({t.name for t in threading.enumerate() if t.name not in before and t.name.startswith("ThreadPoolExecutor")})

    def test_missing_input_is_never_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileNotFoundError):operator.hash_paths([str(Path(d)/"missing")])

    def test_leaf_and_ancestor_symlinks_are_rejected_before_read(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"a";p.write_bytes(b"payload")
            original=Path.is_symlink
            def leaf(path):return path==p or original(path)
            with patch.object(Path,"is_symlink",leaf),patch.object(operator,"info") as read:
                with self.assertRaises(operator.Stop):operator.hash_paths([str(p)])
                read.assert_not_called()
            def ancestor(path):return path==p.parent or original(path)
            with patch.object(Path,"is_symlink",ancestor),patch.object(operator,"info") as read:
                with self.assertRaises(operator.Stop):operator.hash_paths([str(p)])
                read.assert_not_called()

    def test_conflicting_sources_and_relative_paths_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=str(Path(d)/"a");value=dict(bytes=1,sha256="a")
            expected={};operator.merge_expected(expected,{p:value});operator.merge_expected(expected,{p:value})
            self.assertEqual(expected,{p:value})
            with self.assertRaises(operator.Stop):operator.merge_expected(expected,{p:dict(bytes=2,sha256="b")})
            with self.assertRaises(operator.Stop):operator.merge_expected(expected,{"../outside":value})


def main():
    cli=argparse.ArgumentParser();cli.add_argument("--report",type=Path,required=True);args=cli.parse_args()
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(ScopeTests);ids=sorted(t.id() for t in suite)
    result=unittest.TextTestRunner(verbosity=2,failfast=True).run(suite)
    actual=dict(planned=len(ids),run=result.testsRun,test_ids=ids,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),expected_failures=len(result.expectedFailures),unexpected_successes=len(result.unexpectedSuccesses))
    report=dict(Purpose="Unique-path complete custody, exact pin conflicts and I/O thread cleanup",Environment=dict(cpu_only=True,python=sys.version),Input=dict(real_model_calls=0),Expected=dict(tests=len(ids),omitted_required_paths=0),Actual=actual,Status="PASS" if result.wasSuccessful() and result.testsRun==len(ids) and not result.skipped else "FAIL")
    with args.report.open("x",encoding="utf-8") as s:json.dump(report,s,indent=2)
    return 0 if report["Status"]=="PASS" else 2


if __name__=="__main__":raise SystemExit(main())
