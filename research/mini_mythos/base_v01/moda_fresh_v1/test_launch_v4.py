"""Synthetic isolated-startup and retained-source controller fixtures; no target data."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import prepare_once_v4 as operator


class LaunchV4Tests(unittest.TestCase):
    def good_preflight(self):
        return {'Status':'PASS','Actual':{'historical_files':32244,'historical_files_completed':32244,'parse_completed':True,'model_calls':0,'tokenizer_calls':0,'new_source_acquisitions':0,'history_ledger_projection':{'schema':'mythos-history-format-projection-v1','records':32244,'canonical':{'bytes':100,'sha256':'a'*64}}},'source_after_status':'PASS','forbidden_imports':[]}
    def inventory(self):
        data=json.loads((HERE/'DEVELOPMENT_DATA_ATTEMPT4.json').read_bytes())['Actual']['test_ids']
        spec=json.loads((HERE/'DEVELOPMENT_SPECIFICATION_ATTEMPT1.json').read_bytes())['Input']['tests']
        return {'test_data.py':{'kind':'data','test_ids':data},'test_freeze_data_spec.py':{'kind':'spec','test_ids':spec},'test_launch_contract.py':{'kind':'launch','test_ids':operator.launch.LAUNCH_IDS},'test_history_python_v4.py':{'kind':'data','test_ids':['__main__.HistoryPythonTests.test_fixture']},'test_launch_v4.py':{'kind':'launch','test_ids':operator.LAUNCH_IDS}}
    def test_frozen_base_new_namespace_and_helpers(self):
        self.assertEqual(operator.BASE,'b13ab1d799cbd5d37e58d7ea7cdf2540d0093493')
        self.assertEqual(operator.OUT.name,'preparation-v4');self.assertEqual(operator.SOURCE.parent.parent.name,'preparation-v2')
        self.assertEqual(operator.pin(HERE/'prepare_once_v2.py')['sha256'],operator.LAUNCH_HELPER_SHA)
        self.assertEqual(operator.SOURCE_PIN,{'bytes':1234829,'sha256':'71de87ec66bc5737752a2502204dfa6d7fe9856ade3ea444dc6317789a4f13fb'})
    def test_exact_isolated_cli_help(self):
        with tempfile.TemporaryDirectory() as folder:
            for name in ('prepare_once_v4.py','test_launch_v4.py','data_prepare.py'):
                completed=subprocess.run([sys.executable,'-I','-B',str(HERE/name),'--help'],cwd=folder,capture_output=True,text=True,timeout=30)
                self.assertEqual(completed.returncode,0,(name,completed.stdout,completed.stderr));self.assertIn('usage:',completed.stdout)
                if name=='data_prepare.py':
                    self.assertIn('--history-preflight-only',completed.stdout);self.assertIn('--source-file',completed.stdout)
    def test_worker_commands_separate_preflight_and_reused_source(self):
        preflight=operator.worker_command(True);actual=operator.worker_command(False)
        for command in (preflight,actual):
            self.assertEqual(command[:3],[operator.PYTHON,'-I','-B']);self.assertEqual(Path(command[3]).name,'data_prepare.py')
            self.assertEqual(command[command.index('--expected-spec-sha')+1],operator.SPEC_SHA)
        self.assertIn('--history-preflight-only',preflight);self.assertNotIn('--source-file',preflight)
        self.assertNotIn('--history-preflight-only',actual);self.assertEqual(actual[actual.index('--source-file')+1],str(operator.SOURCE))
        self.assertEqual(preflight[preflight.index('--out')+1],str(operator.PREFLIGHT));self.assertEqual(actual[actual.index('--out')+1],str(operator.DATA))
    def test_retained_source_hash_and_successful_original_receipt(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'corpus.parquet';source.write_bytes(b'retained original bytes');expected=operator.pin(source)
            acquisition=root/'acquisition.json';receipt={'Status':'PASS','http_status':200,'url':operator.SOURCE_URL,'actual_response':expected,'pin':expected,'response_file':'corpus.parquet'};operator.save(acquisition,receipt)
            with mock.patch.object(operator,'SOURCE_PIN',expected):
                reference=operator.retained_source(source);self.assertEqual(reference,{'schema':'mythos-local-corpus-reference-v1','mode':'LOCAL_PINNED_REUSE','Status':'PASS','source_file':str(source),'source_pin':expected,'original_acquisition_file':str(acquisition),'original_acquisition_pin':operator.pin(acquisition),'network_requests':0,'copied_corpus_bytes':0})
                receipt['http_status']=206;acquisition.write_text(json.dumps(receipt))
                with self.assertRaises(operator.Stop):operator.retained_source(source)
                source.write_bytes(b'changed')
                with self.assertRaises(operator.Stop):operator.retained_source(source)
    def test_preflight_contract_rejects_partial_parse_or_tokenization(self):
        good=self.good_preflight();self.assertTrue(operator.validate_preflight(good))
        for key,value in [('historical_files',32243),('historical_files_completed',8042),('parse_completed',False),('model_calls',1),('tokenizer_calls',1),('new_source_acquisitions',1)]:
            bad={**good,'Actual':{**good['Actual'],key:value}}
            with self.subTest(key=key),self.assertRaises(operator.Stop):operator.validate_preflight(bad)
        bad={**good,'Actual':{**good['Actual'],'history_ledger_projection':{}}}
        with self.assertRaises(operator.Stop):operator.validate_preflight(bad)
    def test_data_contract_rejects_source_copy_and_missing_reuse(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);reference={'schema':'mythos-local-corpus-reference-v1','mode':'LOCAL_PINNED_REUSE','Status':'PASS','source_file':'/retained/corpus.parquet','source_pin':operator.SOURCE_PIN,'original_acquisition_file':'/retained/acquisition.json','original_acquisition_pin':{'bytes':7,'sha256':'a'*64},'network_requests':0,'copied_corpus_bytes':0}
            operator.save(root/'source_reference.json',reference)
            pin={'bytes':7,'sha256':'b'*64};compressed={'physical':pin,'canonical':pin}
            report={'Status':'PASS','Actual':{'source_rows':7600,'selected':20,'historical_files':32244,'model_calls':0,'input_pin':pin,'new_source_acquisitions':0,'copied_corpus_bytes':0},'source_after_status':'PASS','forbidden_imports':[],'artifacts':{'inputs.json':pin,'history_ledger.json.gz':compressed,'candidates.json.gz':compressed,'source_reference.json':operator.pin(root/'source_reference.json')}}
            self.assertTrue(operator.validate_data(report,root,reference))
            report['Actual']['new_source_acquisitions']=1
            with self.assertRaises(operator.Stop):operator.validate_data(report,root,reference)
            report['Actual']['new_source_acquisitions']=0;(root/'corpus.parquet').write_bytes(b'duplicated')
            with self.assertRaises(operator.Stop):operator.validate_data(report,root,reference)
    def test_old_namespace_snapshot_excludes_only_current_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);current=root/'preparation-v4';current.mkdir();old=root/'preparation-v2';old.mkdir()
            oldfile=old/'partial.json';oldfile.write_bytes(b'preserve malformed bytes');resource=root/'resource-v3.json';resource.write_bytes(b'preserve blocked record');(current/'live.stdout').write_bytes(b'new')
            before=operator.old_namespace_pins(root,current)
            self.assertEqual(set(before),{str(oldfile),str(resource)})
            (current/'live.stdout').write_bytes(b'more new bytes');self.assertEqual(before,operator.old_namespace_pins(root,current))
            oldfile.write_bytes(b'changed');self.assertNotEqual(before,operator.old_namespace_pins(root,current))
            preflight=current/'history-preflight';data=current/'data';preflight.mkdir();data.mkdir()
            (preflight/'manifest.json').write_bytes(b'p'*3);(data/'manifest.json').write_bytes(b'd'*4)
            with mock.patch.object(operator,'PREPARATION_BUDGET',7):self.assertEqual(operator.output_usage(current,preflight,data)['combined_preparation_bytes'],7)
            with mock.patch.object(operator,'PREPARATION_BUDGET',6),self.assertRaises(operator.Stop):operator.output_usage(current,preflight,data)
    def test_source_manifest_is_confined_and_requires_all_sources(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for name in operator.SOURCE_REQUIRED:
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'frozen')
            manifest={name:operator.pin(root/name) for name in operator.SOURCE_REQUIRED};operator.source_manifest(root,manifest)
            reduced=dict(manifest);reduced.pop('test_history_python_v4.py')
            with self.assertRaises(operator.Stop):operator.source_manifest(root,reduced)
            with self.assertRaises(operator.Stop):operator.source_manifest(root,{**manifest,'../escape':{'bytes':0,'sha256':'0'*64}})
            (root/'data_prepare.py').write_bytes(b'changed')
            with self.assertRaises(operator.Stop):operator.source_manifest(root,manifest)
    def test_test_inventory_cannot_omit_or_shrink_original_helpers(self):
        good=self.inventory();self.assertEqual(operator.test_inventory(good),good)
        bad=dict(good);bad.pop('test_history_python_v4.py')
        with self.assertRaises(operator.Stop):operator.test_inventory(bad)
        bad={**good,'test_data.py':{**good['test_data.py'],'test_ids':good['test_data.py']['test_ids'][:-1]}}
        with self.assertRaises(operator.Stop):operator.test_inventory(bad)
        bad={**good,'test_launch_v4.py':{**good['test_launch_v4.py'],'test_ids':good['test_launch_v4.py']['test_ids'][:-1]}}
        with self.assertRaises(operator.Stop):operator.test_inventory(bad)
    def test_nonzero_failure_is_not_masked_by_missing_report(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);script=root/'bad.py';script.write_text('import mythos_fixture_module_that_does_not_exist\n')
            result=operator.launch.run_child('bad',[sys.executable,'-I','-B',str(script)],root,root,30)
            with self.assertRaises(operator.Stop) as caught:operator.launch.read_result(result,root/'missing.json')
            self.assertEqual(caught.exception.status,'FAIL');self.assertIn('ModuleNotFoundError',caught.exception.detail['command']['stderr_tail']);self.assertTrue(result['child_reaped'])


if __name__=='__main__':
    cli=argparse.ArgumentParser();cli.add_argument('--report',required=True,type=Path);args=cli.parse_args()
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(LaunchV4Tests);ids=[test.id() for test in suite]
    operator.require(ids==operator.LAUNCH_IDS,'Frozen v4 launch inventory differs')
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    report={'Purpose':'Development-only v4 isolated startup, retained corpus binding and complete-preflight gates','Environment':{'executable':sys.executable,'version':sys.version,'isolated':bool(sys.flags.isolated),'no_bytecode':sys.dont_write_bytecode},'Input':{'synthetic_only':True,'new_source_acquisitions':0,'model_calls':0},'Expected':{'tests':10,'failures':0,'errors':0,'skipped':0},'Actual':{'test_ids':ids,'planned':len(ids),'run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'expected_failures':len(result.expectedFailures),'unexpected_successes':len(result.unexpectedSuccesses),'failure_details':[[t.id(),e] for t,e in result.failures+result.errors]},'Status':'PASS' if result.wasSuccessful() and result.testsRun==len(ids) and not result.skipped else 'FAIL'}
    operator.save(args.report,report);raise SystemExit(0 if report['Status']=='PASS' else 1)
