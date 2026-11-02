"""Authorized new preparation attempt; preserve v1; never retry or run a model."""
from __future__ import annotations
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
import traceback

REPO=Path('/workspaces/mythos-moda-fresh-cpu-v1')
ROOT=REPO/'research/mini_mythos/base_v01/moda_fresh_v1'
BASE='3a7f8b3ac15d4354800360961018de7c66d26be6'
OUT=Path('/workspaces/mythos-evidence/base_v01/moda_fresh/preparation-v2')
OLD_OUT=OUT.parent/'preparation-v1'
SPEC=OUT.parent/'specification-v1/DATA_SPEC.json'
SPEC_SHA='6185f5dee8c9f95e35a967c3f8abd5754221ed02207c68244ce3d2bdc4dcb8e9'
PYTHON='/workspaces/mythos-depth-data-cpu312/bin/python'
SPACE='bookish-pancake-vwqx7rr9x5w3wxjr'
BRANCH='mythos-moda-fresh-cpu-v1'
FROZEN_DATA_SOURCES=('data_prepare.py','freeze_data_spec.py','DATA_PROTOCOL.md')
LAUNCH_METHODS=(
    'test_data_and_operator_help_isolated',
    'test_data_success_requires_exact_preparation_contract',
    'test_exclusive_logs_and_new_output_binding_preserve_old_attempt',
    'test_malformed_report_and_wrong_test_coverage_stop',
    'test_nonzero_import_error_is_not_masked_by_missing_report',
    'test_report_fail_and_blocked_status_preserved',
    'test_specification_help_isolated',
    'test_specification_suite_isolated_reports_all_ten',
    'test_success_without_report_is_fail',
    'test_timeout_terminates_child_tree_and_reaps_parent',
)
LAUNCH_IDS=['__main__.LaunchTests.'+name for name in LAUNCH_METHODS]
ENV={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','TOKENIZERS_PARALLELISM':'false','RAYON_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','CUDA_VISIBLE_DEVICES':''}


class Stop(Exception):
    def __init__(self,status,reason,detail=None):super().__init__(reason);self.status=status;self.detail=detail or {}
def require(condition,reason,status='FAIL'):
    if not condition:raise Stop(status,reason)
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def pin(path):
    h=hashlib.sha256();size=0
    with Path(path).open('rb') as stream:
        for raw in iter(lambda:stream.read(1024*1024),b''):h.update(raw);size+=len(raw)
    return {'bytes':size,'sha256':h.hexdigest()}
def save(path,value):
    with Path(path).open('x',encoding='utf-8',newline='\n') as stream:json.dump(value,stream,sort_keys=True,indent=2,allow_nan=False);stream.write('\n')
def tree_pins(root):
    require(root.is_dir() and not root.is_symlink(),'Required preserved directory unavailable: '+str(root),'BLOCKED')
    paths=sorted(root.rglob('*'));require(not any(p.is_symlink() for p in paths),'Preserved directory contains symlink','BLOCKED')
    return {str(p):pin(p) for p in paths if p.is_file()}
def live_group(pgid):
    if os.name!='posix':return None
    alive=[]
    for path in Path('/proc').iterdir():
        if not path.name.isdigit():continue
        try:
            stat=(path/'stat').read_text();fields=stat[stat.rfind(')')+2:].split()
            if int(fields[2])==pgid and fields[0] not in ('Z','X'):alive.append(int(path.name))
        except (OSError,ValueError,IndexError):continue
    return sorted(alive)
def stop_child(proc,record):
    record['cleanup']=[]
    if os.name=='posix':
        for sig,seconds in ((signal.SIGTERM,30),(signal.SIGKILL,5)):
            try:os.killpg(proc.pid,sig);record['cleanup'].append({'signal':sig.name})
            except ProcessLookupError:pass
            except OSError as exc:record['cleanup'].append({'error':repr(exc)})
            try:proc.wait(timeout=seconds)
            except subprocess.TimeoutExpired:pass
            deadline=time.monotonic()+seconds
            while live_group(proc.pid) and time.monotonic()<deadline:time.sleep(.02)
            if not live_group(proc.pid) and proc.poll() is not None:break
        record['remaining_process_group']=live_group(proc.pid)
    else:
        # Development-only Windows fixture path. Formal execution requires Linux.
        result=subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),timeout=10)
        record['cleanup'].append({'taskkill_exit':result.returncode,'stdout':result.stdout.decode(errors='replace'),'stderr':result.stderr.decode(errors='replace')})
        try:proc.wait(timeout=5)
        except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=5)
        record['remaining_process_group']=None
        record['windows_development_cleanup']='taskkill /T; descendant PID verified by separate fixture'
    record['child_reaped']=proc.poll() is not None


def run_child(label,argv,out,cwd,timeout,env=None):
    record={'label':label,'argv':list(map(str,argv)),'started':utc(),'pid':None,'returncode':None,'child_reaped':False,'cleanup':[],'remaining_process_group':None}
    proc=None
    stdout=Path(out)/(label+'.stdout');stderr=Path(out)/(label+'.stderr')
    require(not stdout.exists() and not stderr.exists(),'Refuse existing subprocess evidence: '+label,'BLOCKED')
    try:
        with stdout.open('xb') as sout,stderr.open('xb') as serr:
            kwargs={'cwd':cwd,'env':ENV if env is None else env,'stdout':sout,'stderr':serr}
            if os.name=='posix':kwargs['start_new_session']=True
            else:kwargs['creationflags']=getattr(subprocess,'CREATE_NEW_PROCESS_GROUP',0)|getattr(subprocess,'CREATE_NO_WINDOW',0)
            try:
                proc=subprocess.Popen(record['argv'],**kwargs);record['pid']=proc.pid
                record['returncode']=proc.wait(timeout=timeout)
                if os.name=='posix' and live_group(proc.pid):
                    record['interruption']={'type':'LingeringDescendants','message':'Child returned with live process group'};stop_child(proc,record)
            except BaseException as exc:
                record['interruption']={'type':type(exc).__name__,'message':str(exc)}
                if proc is not None:stop_child(proc,record)
    except BaseException as exc:
        record.setdefault('interruption',{'type':type(exc).__name__,'message':str(exc)})
    finally:
        record['finished']=utc()
        if proc is not None:record['returncode']=proc.poll();record['child_reaped']=proc.poll() is not None
        for key,path in (('stdout',stdout),('stderr',stderr)):
            if path.is_file():record[key]={'path':str(path),**pin(path)}
        if stderr.is_file():
            with stderr.open('rb') as stream:stream.seek(max(0,stderr.stat().st_size-8192));record['stderr_tail']=stream.read().decode('utf-8',errors='replace')
    return record


def read_result(command,report_path):
    """Primary subprocess failure remains visible when no report was produced."""
    report_path=Path(report_path);detail={'command':command,'report_path':str(report_path),'report_exists':report_path.is_file()};value=None
    if report_path.is_file():
        detail['report_pin']=pin(report_path)
        try:value=json.loads(report_path.read_bytes())
        except (OSError,ValueError) as exc:detail['report_parse_error']=repr(exc)
    if command.get('interruption') or not command.get('child_reaped') or command.get('remaining_process_group'):
        raise Stop('BLOCKED','Subprocess launch/timeout/cleanup did not complete',detail)
    if command.get('returncode')!=0:
        state=value.get('Status') if isinstance(value,dict) else None
        raise Stop(state if state in ('FAIL','BLOCKED') else 'FAIL','Subprocess exited nonzero; inspect preserved stderr and optional report',detail)
    if not isinstance(value,dict):raise Stop('FAIL','Successful subprocess did not produce a readable JSON report',detail)
    if value.get('Status')!='PASS':raise Stop(value.get('Status') if value.get('Status') in ('FAIL','BLOCKED') else 'BLOCKED','Subprocess report did not PASS',detail)
    return value


def validate_tests(value,kind,expected_ids):
    count=len(expected_ids);actual=value.get('Actual',{})
    require(count>0 and len(set(expected_ids))==count,'Frozen expected test IDs required')
    if kind=='spec':
        require(actual.get('tests_run')==count and value.get('Input',{}).get('tests')==expected_ids,'Specification fixture coverage differs')
        require(all(actual.get(k)==[] for k in ('failures','errors','skipped')),'Specification fixture failure/error/skip')
    else:
        require(actual.get('planned')==actual.get('run')==count and actual.get('test_ids')==expected_ids,'Helper fixture coverage differs')
        require(all(actual.get(k)==0 for k in ('failures','errors','skipped')),'Helper fixture failure/error/skip')
        if kind=='launch':require(actual.get('expected_failures')==actual.get('unexpected_successes')==0,'Launch fixture expected/unexpected failure')
    return True


def validate_data(value):
    actual=value.get('Actual',{})
    require(actual.get('source_rows')==7600 and actual.get('selected')==20 and actual.get('historical_files')==32244 and actual.get('model_calls')==0,'Preparation selected/source/history/model coverage differs')
    require(value.get('source_after_status')=='PASS' and value.get('forbidden_imports')==[],'Preparation custody/import verification not PASS')
    require(isinstance(actual.get('input_pin'),dict) and set(actual['input_pin'])=={'bytes','sha256'},'Prepared input pin missing')
    artifacts=value.get('artifacts',{})
    require(artifacts.get('inputs.json')==actual['input_pin'],'Prepared input manifest differs')
    for name in ('history_ledger.json.gz','candidates.json.gz'):
        require(set(artifacts.get(name,{}))=={'physical','canonical'},'Missing physical/canonical ledger receipt: '+name)
    return True


def main():
    cli=argparse.ArgumentParser();cli.add_argument('--expected-head',required=True);args=cli.parse_args()
    require(re.fullmatch('[0-9a-f]{40}',args.expected_head),'Full freeze commit required','BLOCKED')
    if OUT.exists():print('BLOCKED: existing preparation-v2 retained; no retry');return 2
    if os.name!='posix' or not Path('/workspaces').is_dir():print('BLOCKED: target Linux Codespace required');return 2
    OUT.mkdir(parents=True,exist_ok=False)
    report={'Purpose':'Correct isolated helper launch, then one unchanged model-blind fresh-data preparation','Environment':{'python':sys.executable,'codespace':os.environ.get('CODESPACE_NAME')},'Input':{'base':BASE,'freeze':args.expected_head,'spec_sha256':SPEC_SHA,'preserved_attempt':str(OLD_OUT)},'Expected':{'data_tests':28,'spec_tests':10,'launch_tests':len(LAUNCH_IDS),'data_worker_launches':1,'source_attempts':1,'model_calls':0},'Actual':{'commands':[],'data_worker_launches':0,'model_calls':0},'Status':'NOT TESTED'}
    before={};spec_pin=None;git=None
    def interrupted(signum,frame):
        signal.signal(signal.SIGTERM,signal.SIG_IGN);signal.signal(signal.SIGINT,signal.SIG_IGN)
        raise KeyboardInterrupt('Operator interrupted by signal '+str(signum))
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    def command(label,argv,timeout):
        c=run_child(label,argv,OUT,REPO,timeout);report['Actual']['commands'].append(c);save(OUT/(label+'.execution.json'),c);return c
    try:
        require(sys.executable==PYTHON and sys.flags.isolated and sys.dont_write_bytecode and not sys.flags.optimize,'Exact isolated nonoptimized data interpreter required','BLOCKED')
        require(os.environ.get('CODESPACE_NAME')==SPACE,'Designated Codespace required','BLOCKED')
        git=lambda *v:subprocess.check_output(['git','-C',str(REPO),*v],text=True).strip()
        require(git('rev-parse','HEAD')==args.expected_head and not git('status','--porcelain'),'Frozen clean source checkout required','BLOCKED')
        require(git('branch','--show-current')==BRANCH and git('merge-base',BASE,args.expected_head)==BASE,'Frozen continuation branch/base required','BLOCKED')
        for name in FROZEN_DATA_SOURCES:
            historical=subprocess.check_output(['git','-C',str(REPO),'show',BASE+':research/mini_mythos/base_v01/moda_fresh_v1/'+name])
            require(pin(ROOT/name)['sha256']==hashlib.sha256(historical).hexdigest(),'Protected preparation source changed: '+name)
        spec_pin=pin(SPEC);require(spec_pin['sha256']==SPEC_SHA,'Frozen specification changed')
        before=tree_pins(OLD_OUT);report['Actual']['old_attempt_before']=before
        expected_data=json.loads((ROOT/'DEVELOPMENT_DATA_ATTEMPT4.json').read_bytes())['Actual']['test_ids']
        expected_spec=json.loads((ROOT/'DEVELOPMENT_SPECIFICATION_ATTEMPT1.json').read_bytes())['Input']['tests']
        require(len(expected_data)==28 and len(expected_spec)==10,'Frozen original helper counts')
        for name,kind,ids in (('test_data.py','data',expected_data),('test_freeze_data_spec.py','spec',expected_spec),('test_launch_contract.py','launch',LAUNCH_IDS)):
            path=OUT/(name+'.json');c=command(name,[PYTHON,'-I','-B',str(ROOT/name),'--report',str(path)],300)
            value=read_result(c,path);validate_tests(value,kind,ids)
        report['Actual']['data_worker_launches']+=1
        c=command('data_prepare',[PYTHON,'-I','-B',str(ROOT/'data_prepare.py'),'--spec',str(SPEC),'--expected-spec-sha',SPEC_SHA,'--out',str(OUT/'data')],3600)
        value=read_result(c,OUT/'data/manifest.json');validate_data(value)
        report['Actual']['data_status']=value['Status'];report['Actual']['data_actual']=value['Actual'];report['Status']='PASS'
    except BaseException as exc:
        report['Status']=getattr(exc,'status','BLOCKED' if isinstance(exc,(OSError,subprocess.SubprocessError,KeyboardInterrupt)) else 'FAIL')
        report['error']={'type':type(exc).__name__,'reason':str(exc),'detail':getattr(exc,'detail',{}),'traceback':traceback.format_exc()}
    finally:
        try:
            if before:require(tree_pins(OLD_OUT)==before,'Prior preparation-v1 changed');report['Actual']['old_attempt_after_status']='PASS'
            if spec_pin:require(pin(SPEC)==spec_pin,'Frozen specification changed during preparation');report['Actual']['specification_after_status']='PASS'
            if git:require(git('rev-parse','HEAD')==args.expected_head and not git('status','--porcelain'),'Frozen source changed during preparation');report['Actual']['source_after_status']='PASS'
        except BaseException as exc:report['Status']='FAIL';report['custody_error']={'type':type(exc).__name__,'reason':str(exc)}
        report['Actual']['model_modules_loaded']=sorted(set(sys.modules)&{'torch','parcae_lm','receval','transformers'})
        if report['Actual']['model_modules_loaded']:report['Status']='FAIL'
        report['Actual']['source_attempts']='See data/acquisition.json if created; no operator retry'
        save(OUT/'preparation_control.json',report)
    print(json.dumps(report,allow_nan=False),flush=True)
    return 0 if report['Status']=='PASS' else 2


if __name__=='__main__':raise SystemExit(main())
