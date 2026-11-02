"""Single target data-preparation launch; no model calls or automatic retries."""
import argparse,datetime,hashlib,json,os,signal,subprocess,sys,traceback
from pathlib import Path

REPO=Path('/workspaces/mythos-moda-fresh-cpu-v1')
ROOT=REPO/'research/mini_mythos/base_v01/moda_fresh_v1'
OUT=Path('/workspaces/mythos-evidence/base_v01/moda_fresh/preparation-v1')
SPEC=OUT.parent/'specification-v1/DATA_SPEC.json'
SPEC_SHA='6185f5dee8c9f95e35a967c3f8abd5754221ed02207c68244ce3d2bdc4dcb8e9'
PYTHON='/workspaces/mythos-depth-data-cpu312/bin/python'

def main():
    p=argparse.ArgumentParser();p.add_argument('--expected-head',required=True);a=p.parse_args()
    if OUT.exists():print('BLOCKED: existing preparation preserved; no retry');return 2
    OUT.mkdir(parents=True,exist_ok=False)
    r=dict(Purpose='One model-blind target preparation after source/spec freeze',Environment=dict(executable=sys.executable,codespace=os.environ.get('CODESPACE_NAME')),Input=dict(freeze=a.expected_head,spec_sha256=SPEC_SHA),Expected=dict(data_tests=28,spec_tests=10,source_attempts=1,model_calls=0),Actual=dict(commands=[],model_calls=0),Status='NOT TESTED')
    def interrupted(signum,frame):
        signal.signal(signal.SIGTERM,signal.SIG_IGN);signal.signal(signal.SIGINT,signal.SIG_IGN)
        raise KeyboardInterrupt('Operator interrupted by signal '+str(signum))
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    def command(label,args,timeout):
        proc=None
        c=dict(label=label,argv=args,started=datetime.datetime.now(datetime.timezone.utc).isoformat())
        r['Actual']['commands'].append(c)
        with (OUT/(label+'.stdout')).open('x') as out,(OUT/(label+'.stderr')).open('x') as err:
            try:
                proc=subprocess.Popen(args,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','TOKENIZERS_PARALLELISM':'false','RAYON_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','CUDA_VISIBLE_DEVICES':''},cwd=REPO,stdout=out,stderr=err,start_new_session=True)
                c['pid']=proc.pid;c['returncode']=proc.wait(timeout=timeout)
            except BaseException as exc:
                c['error']=repr(exc)
                if proc is not None:
                    try:os.killpg(proc.pid,signal.SIGTERM);proc.wait(timeout=30)
                    except ProcessLookupError:pass
                    except BaseException:
                        try:os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=5)
                        except ProcessLookupError:pass
                raise
            finally:
                c['finished']=datetime.datetime.now(datetime.timezone.utc).isoformat();c['child_reaped']=proc is not None and proc.poll() is not None;c['returncode']=proc.returncode if proc else None
        return c['returncode']
    try:
        if sys.flags.optimize:raise RuntimeError('Optimization flags are not permitted')
        assert sys.executable==PYTHON and sys.flags.isolated and sys.dont_write_bytecode
        assert os.environ.get('CODESPACE_NAME')=='bookish-pancake-vwqx7rr9x5w3wxjr'
        git=lambda *args:subprocess.check_output(['git','-C',str(REPO),*args],text=True).strip()
        assert git('rev-parse','HEAD')==a.expected_head and not git('status','--porcelain')
        assert git('branch','--show-current')=='mythos-moda-fresh-cpu-v1'
        assert hashlib.sha256(SPEC.read_bytes()).hexdigest()==SPEC_SHA
        for name,count in [('test_data.py',28),('test_freeze_data_spec.py',10)]:
            report=OUT/(name+'.json');code=command(name,[PYTHON,'-I','-B',str(ROOT/name),'--report',str(report)],300)
            v=json.loads(report.read_text());assert code==0 and v['Status']=='PASS'
            if name=='test_data.py':
                expected=json.loads((ROOT/'DEVELOPMENT_DATA_ATTEMPT4.json').read_text())['Actual']['test_ids']
                actual=v['Actual'];assert actual['planned']==actual['run']==count and actual['test_ids']==expected
                assert actual['failures']==actual['errors']==actual['skipped']==0
            else:
                expected=json.loads((ROOT/'DEVELOPMENT_SPECIFICATION_ATTEMPT1.json').read_text())['Input']['tests']
                actual=v['Actual'];assert actual['tests_run']==count and v['Input']['tests']==expected
                assert actual['failures']==actual['errors']==actual['skipped']==[]
        code=command('data_prepare',[PYTHON,'-I','-B',str(ROOT/'data_prepare.py'),'--spec',str(SPEC),'--expected-spec-sha',SPEC_SHA,'--out',str(OUT/'data')],3600)
        v=json.loads((OUT/'data/manifest.json').read_text());r['Actual']['data_status']=v['Status'];r['Actual']['data_actual']=v['Actual']
        r['Status']=v['Status'] if v['Status'] in ('PASS','FAIL','BLOCKED') else 'BLOCKED'
        if code!=0 and r['Status']=='PASS':r['Status']='FAIL'
    except BaseException as exc:
        r['Status']='BLOCKED' if isinstance(exc,(OSError,subprocess.SubprocessError,KeyboardInterrupt)) else 'FAIL'
        r['error']=dict(type=type(exc).__name__,reason=str(exc),traceback=traceback.format_exc())
    with (OUT/'preparation_control.json').open('x') as f:json.dump(r,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps(r,allow_nan=False),flush=True)
    return 0 if r['Status']=='PASS' else 2

if __name__=='__main__':raise SystemExit(main())
