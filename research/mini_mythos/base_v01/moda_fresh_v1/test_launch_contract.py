"""Exact isolated CLI launch fixtures; synthetic temporary files, no new corpus/model."""
from __future__ import annotations
import argparse
import ctypes
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import prepare_once_v2 as operator


def running(pid):
    if os.name=='posix':
        try:
            raw=Path('/proc')/str(pid)/'stat';fields=raw.read_text().split(')')[-1].split();return fields[0] not in ('Z','X')
        except FileNotFoundError:return False
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=[ctypes.c_ulong,ctypes.c_int,ctypes.c_ulong];kernel.OpenProcess.restype=ctypes.c_void_p
    kernel.GetExitCodeProcess.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_ulong)];kernel.GetExitCodeProcess.restype=ctypes.c_int
    kernel.CloseHandle.argtypes=[ctypes.c_void_p];kernel.CloseHandle.restype=ctypes.c_int
    handle=kernel.OpenProcess(0x1000,False,pid)
    if not handle:return False
    try:
        code=ctypes.c_ulong();return bool(kernel.GetExitCodeProcess(handle,ctypes.byref(code))) and code.value==259
    finally:kernel.CloseHandle(handle)


class LaunchTests(unittest.TestCase):
    def call(self,folder,name,script,args=(),timeout=30):
        return operator.run_child(name,[sys.executable,'-I','-B',str(script),*map(str,args)],folder,folder,timeout)
    def fixture(self,folder,name,source):
        path=folder/name;path.write_text(source,encoding='utf-8');return path
    def successful_command(self):return {'returncode':0,'child_reaped':True,'remaining_process_group':[]}
    def test_specification_help_isolated(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);c=self.call(root,'help',HERE/'test_freeze_data_spec.py',['--help'])
            self.assertEqual(c['returncode'],0,c);self.assertTrue(c['child_reaped']);self.assertNotIn('interruption',c)
            self.assertIn('--report',(root/'help.stdout').read_text())
    def test_specification_suite_isolated_reports_all_ten(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path=root/'specification.json';c=self.call(root,'specification',HERE/'test_freeze_data_spec.py',['--report',path])
            value=operator.read_result(c,path)
            expected=json.loads((HERE/'DEVELOPMENT_SPECIFICATION_ATTEMPT1.json').read_bytes())['Input']['tests']
            self.assertTrue(operator.validate_tests(value,'spec',expected));self.assertEqual(value['Actual']['tests_run'],10)
            self.assertFalse(any(root.rglob('*.pyc')))
    def test_data_and_operator_help_isolated(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for i,name in enumerate(('test_data.py','data_prepare.py','prepare_once_v2.py')):
                c=self.call(root,'help'+str(i),HERE/name,['--help'])
                self.assertEqual(c['returncode'],0,c);self.assertTrue(c['child_reaped']);self.assertNotIn('interruption',c)
    def test_nonzero_import_error_is_not_masked_by_missing_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);script=self.fixture(root,'bad_import.py','import mythos_fixture_module_that_does_not_exist\n')
            c=self.call(root,'bad_import',script)
            with self.assertRaises(operator.Stop) as caught:operator.read_result(c,root/'missing.json')
            self.assertEqual(caught.exception.status,'FAIL');self.assertIn('exited nonzero',str(caught.exception))
            self.assertIn('ModuleNotFoundError',caught.exception.detail['command']['stderr_tail'])
            self.assertFalse(caught.exception.detail['report_exists']);self.assertNotIn('report_parse_error',caught.exception.detail)
    def test_success_without_report_is_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);script=self.fixture(root,'no_report.py','print("No report created")\n');c=self.call(root,'no_report',script)
            with self.assertRaises(operator.Stop) as caught:operator.read_result(c,root/'absent.json')
            self.assertEqual(caught.exception.status,'FAIL');self.assertIn('readable JSON report',str(caught.exception))
    def test_report_fail_and_blocked_status_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for state in ('FAIL','BLOCKED'):
                path=root/(state+'.json');operator.save(path,{'Status':state,'Actual':{'model_calls':0}})
                c={**self.successful_command(),'returncode':2}
                with self.assertRaises(operator.Stop) as caught:operator.read_result(c,path)
                self.assertEqual(caught.exception.status,state);self.assertEqual(caught.exception.detail['report_pin'],operator.pin(path))
    def test_malformed_report_and_wrong_test_coverage_stop(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path=root/'bad.json';path.write_text('{')
            with self.assertRaises(operator.Stop) as caught:operator.read_result(self.successful_command(),path)
            self.assertEqual(caught.exception.status,'FAIL');self.assertIn('report_parse_error',caught.exception.detail)
            value=json.loads((HERE/'DEVELOPMENT_SPECIFICATION_ATTEMPT1.json').read_bytes());ids=value['Input']['tests']
            value['Actual']['tests_run']=9
            with self.assertRaises(operator.Stop):operator.validate_tests(value,'spec',ids)
            value['Actual']['tests_run']=10;value['Actual']['skipped']=[['fixture','not run']]
            with self.assertRaises(operator.Stop):operator.validate_tests(value,'spec',ids)
    def test_timeout_terminates_child_tree_and_reaps_parent(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);pidfile=root/'child.pid'
            script=self.fixture(root,'sleeper.py','import pathlib,subprocess,sys,time\nchild=subprocess.Popen([sys.executable,"-I","-B","-c","import time;time.sleep(60)"])\npathlib.Path(sys.argv[1]).write_text(str(child.pid))\ntime.sleep(60)\n')
            c=self.call(root,'timeout',script,[pidfile],timeout=2)
            self.assertTrue(pidfile.is_file(),c);child=int(pidfile.read_text())
            try:
                self.assertEqual(c.get('interruption',{}).get('type'),'TimeoutExpired',c);self.assertTrue(c['child_reaped'],c)
                deadline=time.monotonic()+3
                while running(child) and time.monotonic()<deadline:time.sleep(.05)
                self.assertFalse(running(child),'descendant still alive');self.assertFalse(running(c['pid']),'parent still alive')
                with self.assertRaises(operator.Stop) as caught:operator.read_result(c,root/'not_created.json')
                self.assertEqual(caught.exception.status,'BLOCKED')
            finally:
                if running(child):
                    if os.name=='posix':os.kill(child,9)
                    else:subprocess.run(['taskkill','/PID',str(child),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    def test_exclusive_logs_and_new_output_binding_preserve_old_attempt(self):
        self.assertEqual(operator.OUT.name,'preparation-v2');self.assertEqual(operator.OLD_OUT.name,'preparation-v1')
        self.assertEqual(operator.SPEC_SHA,'6185f5dee8c9f95e35a967c3f8abd5754221ed02207c68244ce3d2bdc4dcb8e9')
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);old=root/'same.stdout';old.write_bytes(b'preserve')
            with self.assertRaises(operator.Stop):self.call(root,'same',HERE/'test_freeze_data_spec.py',['--help'])
            self.assertEqual(old.read_bytes(),b'preserve')
    def test_data_success_requires_exact_preparation_contract(self):
        pin={'bytes':7,'sha256':'a'*64};compressed={'physical':pin,'canonical':pin}
        v={'Status':'PASS','Actual':{'source_rows':7600,'selected':20,'historical_files':32244,'model_calls':0,'input_pin':pin},'source_after_status':'PASS','forbidden_imports':[],'artifacts':{'inputs.json':pin,'history_ledger.json.gz':compressed,'candidates.json.gz':compressed}}
        self.assertTrue(operator.validate_data(v))
        for key,value in (('selected',19),('source_rows',7599),('historical_files',32243),('model_calls',1)):
            candidate={**v,'Actual':{**v['Actual'],key:value}}
            with self.assertRaises(operator.Stop):operator.validate_data(candidate)
        candidate={**v,'artifacts':{**v['artifacts'],'history_ledger.json.gz':pin}}
        with self.assertRaises(operator.Stop):operator.validate_data(candidate)


if __name__=='__main__':
    cli=argparse.ArgumentParser();cli.add_argument('--report',required=True,type=Path);args=cli.parse_args()
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(LaunchTests);ids=[t.id() for t in suite]
    operator.require(ids==operator.LAUNCH_IDS,'Frozen launch fixture inventory differs')
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    report={'Purpose':'Exact isolated CLI launch, report-contract and child-tree cleanup fixtures','Environment':{'python':sys.executable,'version':sys.version,'isolated':bool(sys.flags.isolated),'no_bytecode':sys.dont_write_bytecode,'platform':sys.platform},'Input':{'synthetic_only':True,'model_calls':0,'source_acquisitions':0,'subprocess_contract':[sys.executable,'-I','-B']},'Expected':{'tests':10,'failures':0,'errors':0,'skipped':0},'Actual':{'test_ids':ids,'planned':len(ids),'run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'expected_failures':len(result.expectedFailures),'unexpected_successes':len(result.unexpectedSuccesses),'failure_details':[[t.id(),msg] for t,msg in result.failures+result.errors]},'Status':'PASS' if result.wasSuccessful() and result.testsRun==len(ids) and not result.skipped else 'FAIL'}
    operator.save(args.report,report);raise SystemExit(0 if report['Status']=='PASS' else 1)
