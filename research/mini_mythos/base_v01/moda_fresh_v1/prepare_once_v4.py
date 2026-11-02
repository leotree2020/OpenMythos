"""New parser-only preparation continuation with retained-source reuse and no retry."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import traceback

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import prepare_once_v2 as launch

REPO=Path('/workspaces/mythos-moda-fresh-cpu-v1')
ROOT=REPO/'research/mini_mythos/base_v01/moda_fresh_v1'
BASE='b13ab1d799cbd5d37e58d7ea7cdf2540d0093493'
FRESH=Path('/workspaces/mythos-evidence/base_v01/moda_fresh')
OUT=FRESH/'preparation-v4'
PREFLIGHT=OUT/'history-preflight'
DATA=OUT/'data'
SPEC=FRESH/'specification-v1/DATA_SPEC.json'
SPEC_SHA='6185f5dee8c9f95e35a967c3f8abd5754221ed02207c68244ce3d2bdc4dcb8e9'
SOURCE=FRESH/'preparation-v2/data/corpus.parquet'
SOURCE_PIN={'bytes':1234829,'sha256':'71de87ec66bc5737752a2502204dfa6d7fe9856ade3ea444dc6317789a4f13fb'}
SOURCE_URL='https://huggingface.co/datasets/fancyzhx/ag_news/resolve/eb185aade064a813bc0b7f42de02595523103ca4/data/test-00000-of-00001.parquet'
PYTHON='/workspaces/mythos-depth-data-cpu312/bin/python'
SPACE='bookish-pancake-vwqx7rr9x5w3wxjr'
BRANCH='mythos-moda-fresh-cpu-v1'
PREPARATION_BUDGET=4*1024**2
LAUNCH_HELPER_SHA='231c7588e01d4aba5f65375809c72663c6f7afb771c8c19b82a475f2a895f7e7'
TEST_KINDS={'test_data.py':'data','test_freeze_data_spec.py':'spec','test_launch_contract.py':'launch','test_history_python_v4.py':'data','test_launch_v4.py':'launch'}
LAUNCH_METHODS=(
    'test_data_contract_rejects_source_copy_and_missing_reuse',
    'test_exact_isolated_cli_help',
    'test_frozen_base_new_namespace_and_helpers',
    'test_nonzero_failure_is_not_masked_by_missing_report',
    'test_old_namespace_snapshot_excludes_only_current_output',
    'test_preflight_contract_rejects_partial_parse_or_tokenization',
    'test_retained_source_hash_and_successful_original_receipt',
    'test_source_manifest_is_confined_and_requires_all_sources',
    'test_test_inventory_cannot_omit_or_shrink_original_helpers',
    'test_worker_commands_separate_preflight_and_reused_source',
)
LAUNCH_IDS=['__main__.LaunchV4Tests.'+name for name in LAUNCH_METHODS]
FIXED_UNCHANGED=('prepare_once.py','prepare_once_v2.py','freeze_data_spec.py','DATA_PROTOCOL.md')
SOURCE_REQUIRED={'prepare_once_v4.py','test_launch_v4.py','prepare_once_v2.py','data_prepare.py','test_data.py','test_freeze_data_spec.py','test_launch_contract.py','test_history_python_v4.py','fixtures/history_invalid_inventory.txt','CONTINUATION_V4.md','PREPARATION_V4_TEST_INVENTORY.json'}

Stop=launch.Stop
require=launch.require
pin=launch.pin
save=launch.save


def old_namespace_pins(root,excluded):
    root,excluded=Path(root),Path(excluded)
    require(root.is_dir() and not root.is_symlink(),'Existing fresh namespace unavailable','BLOCKED')
    result={}
    for p in sorted(root.rglob('*')):
        if p==excluded or p.is_relative_to(excluded):continue
        require(not p.is_symlink(),'Historical fresh namespace symlink: '+str(p),'BLOCKED')
        if p.is_file():result[str(p)]=pin(p)
    return result


def retained_source(source):
    source=Path(source)
    require(source.is_absolute() and source.is_file() and not source.is_symlink(),'Retained source unavailable','BLOCKED')
    require(pin(source)==SOURCE_PIN,'Retained corpus differs from frozen official source')
    acquisition=source.with_name('acquisition.json')
    require(acquisition.is_file() and not acquisition.is_symlink(),'Original acquisition receipt unavailable','BLOCKED')
    receipt=json.loads(acquisition.read_bytes())
    require(receipt.get('Status')=='PASS' and receipt.get('http_status')==200 and receipt.get('url')==SOURCE_URL and receipt.get('actual_response')==SOURCE_PIN and receipt.get('pin')==SOURCE_PIN and receipt.get('response_file')=='corpus.parquet','Original exact-byte acquisition receipt not accepted')
    return {'schema':'mythos-local-corpus-reference-v1','mode':'LOCAL_PINNED_REUSE','Status':'PASS','source_file':str(source),'source_pin':SOURCE_PIN,'original_acquisition_file':str(acquisition),'original_acquisition_pin':pin(acquisition),'network_requests':0,'copied_corpus_bytes':0}


def source_manifest(root,manifest):
    root=Path(root)
    require(isinstance(manifest,dict) and SOURCE_REQUIRED<=set(manifest),'Complete preparation-v4 source manifest required')
    for name,expected in manifest.items():
        path=Path(name)
        require(name and not path.is_absolute() and (root/path).resolve().is_relative_to(root.resolve()),'Source manifest escaped package')
        require(pin(root/path)==expected,'Frozen preparation source differs: '+name)


def test_inventory(value):
    require(isinstance(value,dict) and set(value)==set(TEST_KINDS),'Exact complete helper inventory required')
    for name,kind in TEST_KINDS.items():
        item=value[name];ids=item.get('test_ids',[])
        require(item.get('kind')==kind and isinstance(ids,list) and bool(ids) and ids==sorted(set(ids)),'Frozen helper schema/unique ordered IDs: '+name)
    require(len(value['test_data.py']['test_ids'])==28 and len(value['test_freeze_data_spec.py']['test_ids'])==10 and value['test_launch_contract.py']['test_ids']==launch.LAUNCH_IDS,'Original48 helper inventory retained')
    require(value['test_launch_v4.py']['test_ids']==LAUNCH_IDS,'Exact v4 launch fixture inventory')
    return value


def worker_command(preflight=False):
    command=[PYTHON,'-I','-B',str(ROOT/'data_prepare.py'),'--spec',str(SPEC),'--expected-spec-sha',SPEC_SHA,'--out',str(PREFLIGHT if preflight else DATA)]
    return command+(['--history-preflight-only'] if preflight else ['--source-file',str(SOURCE)])


def output_usage(parent,preflight,data):
    def used(root):return sum(p.stat().st_size for p in Path(root).rglob('*') if p.is_file())
    preflight_bytes=used(preflight);data_bytes=used(data)
    result={'preflight_bytes':preflight_bytes,'data_bytes':data_bytes,'combined_preparation_bytes':preflight_bytes+data_bytes,'combined_preparation_budget':PREPARATION_BUDGET,'whole_parent_bytes':used(parent)}
    require(result['combined_preparation_bytes']<=PREPARATION_BUDGET,'Combined preflight/data outputs exceed unchanged4MiB preparation budget','BLOCKED')
    return result


def validate_preflight(value):
    actual=value.get('Actual',{})
    require(actual.get('historical_files')==actual.get('historical_files_completed')==32244 and actual.get('parse_completed')is True,'Complete historical-parser preflight required')
    require(actual.get('model_calls')==actual.get('tokenizer_calls')==actual.get('new_source_acquisitions')==0,'Preflight must not tokenize, acquire sources or call models')
    require(value.get('source_after_status')=='PASS' and value.get('forbidden_imports')==[],'Preflight custody/import verification required')
    projection=actual.get('history_ledger_projection',{});canonical=projection.get('canonical',{})
    require(projection.get('schema')=='mythos-history-format-projection-v1' and projection.get('records')==32244 and type(canonical.get('bytes'))is int and canonical['bytes']>0 and re.fullmatch('[0-9a-f]{64}',canonical.get('sha256','')),'Complete canonical history-format projection required')
    return True


def validate_data(value,data_dir,reference):
    launch.validate_data(value)
    actual=value['Actual'];artifacts=value['artifacts'];data_dir=Path(data_dir)
    require(actual.get('new_source_acquisitions')==0 and actual.get('copied_corpus_bytes')==0,'No repeated source acquisition or corpus copy permitted')
    require('source_reference.json' in artifacts and 'corpus.parquet' not in artifacts and not (data_dir/'corpus.parquet').exists(),'Retained external corpus reference required; no duplicate corpus')
    require(pin(data_dir/'source_reference.json')==artifacts['source_reference.json'],'Source reference artifact pin')
    observed=json.loads((data_dir/'source_reference.json').read_bytes())
    require(observed==reference,'Exact retained source and original acquisition binding')
    return True


def main():
    cli=argparse.ArgumentParser();cli.add_argument('--expected-head',required=True);args=cli.parse_args()
    require(re.fullmatch('[0-9a-f]{40}',args.expected_head),'Full frozen source commit required','BLOCKED')
    if OUT.exists():print('BLOCKED: preparation-v4 already exists; no retry/overwrite');return 2
    if os.name!='posix' or not Path('/workspaces').is_dir():print('BLOCKED: designated Linux Codespace required');return 2
    OUT.mkdir(parents=True,exist_ok=False)
    report={'Purpose':'Parser-only continuation: complete history preflight then frozen retained-source preparation','Environment':{'executable':sys.executable,'codespace':os.environ.get('CODESPACE_NAME')},'Input':{'base':BASE,'freeze':args.expected_head,'spec_sha256':SPEC_SHA,'retained_source':str(SOURCE)},'Expected':{'history_files':32244,'selected':20,'history_preflight_launches':1,'data_worker_launches':1,'new_source_acquisitions':0,'model_calls':0},'Actual':{'commands':[],'history_preflight_launches':0,'data_worker_launches':0,'new_source_acquisitions':0,'model_calls':0},'Status':'NOT TESTED'}
    before={};spec_pin=None;source_reference=None;git=None
    def interrupted(signum,frame):
        signal.signal(signal.SIGTERM,signal.SIG_IGN);signal.signal(signal.SIGINT,signal.SIG_IGN)
        raise KeyboardInterrupt('Operator interrupted by signal '+str(signum))
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    def command(label,argv,timeout):
        row=launch.run_child(label,argv,OUT,REPO,timeout);report['Actual']['commands'].append(row);save(OUT/(label+'.execution.json'),row);return row
    try:
        require(sys.executable==PYTHON and sys.flags.isolated and sys.dont_write_bytecode and not sys.flags.optimize,'Exact isolated data environment required','BLOCKED')
        require(os.environ.get('CODESPACE_NAME')==SPACE and HERE==ROOT,'Designated Codespace/package required','BLOCKED')
        require(pin(HERE/'prepare_once_v2.py')['sha256']==LAUNCH_HELPER_SHA,'Frozen shared launch/cleanup helper changed')
        git=lambda *v:subprocess.check_output(['git','-C',str(REPO),*v],text=True).strip()
        require(git('rev-parse','HEAD')==args.expected_head and not git('status','--porcelain'),'Frozen clean preparation checkout required','BLOCKED')
        require(git('branch','--show-current')==BRANCH and git('merge-base',BASE,args.expected_head)==BASE,'Authorized continuation ancestry/branch required','BLOCKED')
        for name in FIXED_UNCHANGED:
            old=subprocess.check_output(['git','-C',str(REPO),'show',BASE+':research/mini_mythos/base_v01/moda_fresh_v1/'+name])
            require(pin(ROOT/name)['sha256']==hashlib.sha256(old).hexdigest(),'Historical source/protocol changed: '+name)
        source_manifest(ROOT,json.loads((ROOT/'PREPARATION_V4_SOURCE_MANIFEST.json').read_bytes()))
        inventory=test_inventory(json.loads((ROOT/'PREPARATION_V4_TEST_INVENTORY.json').read_bytes()))
        spec_pin=pin(SPEC);require(spec_pin['sha256']==SPEC_SHA,'Original specification changed')
        source_reference=retained_source(SOURCE);report['Actual']['retained_source']=source_reference
        for p in (FRESH/'preparation-v1',FRESH/'preparation-v2'):require(p.is_dir(),'Prior preparation missing','BLOCKED')
        before=old_namespace_pins(FRESH,OUT);save(OUT/'old_fresh_before.json',before)
        for name,kind in TEST_KINDS.items():
            path=OUT/(name+'.json');row=command(name,[PYTHON,'-I','-B',str(ROOT/name),'--report',str(path)],300)
            result=launch.read_result(row,path);launch.validate_tests(result,kind,inventory[name]['test_ids'])
        report['Actual']['history_preflight_launches']+=1
        row=command('history_preflight',worker_command(True),3600)
        result=launch.read_result(row,PREFLIGHT/'manifest.json');validate_preflight(result)
        report['Actual']['history_preflight']=result['Actual']
        report['Actual']['budget_after_preflight']=output_usage(OUT,PREFLIGHT,DATA)
        report['Actual']['data_worker_launches']+=1
        row=command('data_prepare',worker_command(False),3600)
        result=launch.read_result(row,DATA/'manifest.json');validate_data(result,DATA,source_reference)
        report['Actual']['data_actual']=result['Actual'];report['Actual']['budget_after_data']=output_usage(OUT,PREFLIGHT,DATA);report['Status']='PASS'
    except BaseException as exc:
        report['Status']=getattr(exc,'status','BLOCKED' if isinstance(exc,(OSError,subprocess.SubprocessError,KeyboardInterrupt)) else 'FAIL')
        report['error']={'type':type(exc).__name__,'reason':str(exc),'detail':getattr(exc,'detail',{}),'traceback':traceback.format_exc()}
    finally:
        try:
            if before:require(old_namespace_pins(FRESH,OUT)==before,'Existing fresh evidence changed');report['Actual']['old_fresh_after_status']='PASS'
            if spec_pin:require(pin(SPEC)==spec_pin,'Specification changed');report['Actual']['specification_after_status']='PASS'
            if source_reference:require(retained_source(SOURCE)==source_reference,'Retained source/acquisition changed');report['Actual']['retained_source_after_status']='PASS'
            if git:require(git('rev-parse','HEAD')==args.expected_head and not git('status','--porcelain'),'Frozen source changed during preparation');report['Actual']['source_after_status']='PASS'
        except BaseException as exc:report['Status']='FAIL';report['custody_error']={'type':type(exc).__name__,'reason':str(exc)}
        try:report['Actual']['final_output_usage']=output_usage(OUT,PREFLIGHT,DATA)
        except BaseException as exc:
            if report['Status']!='FAIL':report['Status']=getattr(exc,'status','BLOCKED')
            report['budget_error']={'type':type(exc).__name__,'reason':str(exc)}
        report['Actual']['model_modules_loaded']=sorted(set(sys.modules)&{'torch','parcae_lm','receval','transformers'})
        if report['Actual']['model_modules_loaded']:report['Status']='FAIL'
        save(OUT/'preparation_control.json',report)
    print(json.dumps(report,allow_nan=False),flush=True)
    return 0 if report['Status']=='PASS' else 2


if __name__=='__main__':raise SystemExit(main())
