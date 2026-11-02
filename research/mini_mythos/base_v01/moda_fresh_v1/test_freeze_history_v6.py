"""Synthetic coverage for expanded history scope; no project/model inputs."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("freeze_history_v6",HERE/"freeze_history_v6.py")
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class ScopeTests(unittest.TestCase):
    def test_entire_prior_fresh_corpus_and_debug_text_are_included(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);main=root/"main";fresh=root/"evidence/moda_fresh"
            main.mkdir();fresh.mkdir(parents=True)
            raw=fresh/"preparation-v2/data/corpus.parquet";raw.parent.mkdir(parents=True);raw.write_bytes(b"previously read test rows")
            debug=fresh/"stop-v5/debug.txt";debug.parent.mkdir();debug.write_bytes(b"old debug text")
            newer=fresh/"source-v6/corpus.parquet";newer.parent.mkdir();newer.write_bytes(b"current source excluded")
            hidden=main/".git";hidden.mkdir();(hidden/"objects").write_bytes(b"metadata")
            prior={str(root/("retained-"+str(i))):{} for i in range(32244)}
            old={"history_roots":[str(main),str(root/"evidence")],"expected_history_file_count":32244}
            with patch.object(module,"FRESH",fresh),patch.object(module,"EXCLUDED",{fresh/"source-v6"}):
                paths,original=module.enumerate_paths(old,prior)
            self.assertEqual(original,set(prior));self.assertEqual(set(paths),set(prior)|{str(raw),str(debug)})

    def test_isolated_repo_snapshot_inventory_covers_nested_debug_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/".git").write_text("gitdir: internal")
            source=root/"nested/test.py";source.parent.mkdir();source.write_text("old_fixture = 42")
            report=root/"nested/receipt.json";report.write_text("{}")
            cached=root/"nested/__pycache__/code.pyc";cached.parent.mkdir();cached.write_bytes(b"cache")
            with patch.object(module,"REPO",root):result=module.repo_files()
            self.assertEqual(result,sorted([source,report]))

    def test_original_history_scope_cannot_shrink_silently(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);fresh=root/"moda_fresh";fresh.mkdir()
            old={"history_roots":[str(root)],"expected_history_file_count":32244}
            with patch.object(module,"FRESH",fresh),patch.object(module,"EXCLUDED",set()):
                with self.assertRaisesRegex(AssertionError,"Original history scope changed"):
                    module.enumerate_paths(old,{})

if __name__=="__main__":
    cli=argparse.ArgumentParser();cli.add_argument("--report",type=Path,required=True);args=cli.parse_args()
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(ScopeTests)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    receipt={"Purpose":"Synthetic original-scope preservation and expanded historical text coverage","Environment":{"python":sys.version,"isolated":bool(sys.flags.isolated)},"Input":"Temporary synthetic files only","Expected":{"run":3,"failures":0,"errors":0,"skipped":0},"Actual":{"run":result.testsRun,"failures":len(result.failures),"errors":len(result.errors),"skipped":len(result.skipped)},"Status":"PASS" if result.wasSuccessful() and not result.skipped and result.testsRun==3 else "FAIL"}
    with args.report.open("x",encoding="utf-8") as stream:json.dump(receipt,stream,indent=2);stream.write("\n")
    raise SystemExit(0 if receipt["Status"]=="PASS" else 1)
