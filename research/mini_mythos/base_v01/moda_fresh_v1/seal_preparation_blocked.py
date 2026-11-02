"""Read-only custody and evidence sealing after the stopped preparation attempt."""
import argparse,datetime,gzip,hashlib,json,os,subprocess,sys
from pathlib import Path

REPO=Path('/workspaces/mythos-moda-fresh-cpu-v1')
ROOT=REPO/'research/mini_mythos/base_v01/moda_fresh_v1'
EXTERNAL=Path('/workspaces/mythos-evidence/base_v01/moda_fresh')
OLD=Path('/workspaces/mythos-moda-residual-cpu-v2')
BASE='bc6d267cdd8cf9306c1bf08b369cf2b791723d3d'
PREP_FREEZE='b8a1d0b6640028f214bb5e4ef55e7f0ae499f8b0'

def pin(p):
    h=hashlib.sha256();n=0
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b);n+=len(b)
    return dict(bytes=n,sha256=h.hexdigest())
def git(p,*a):return subprocess.check_output(['git','-C',str(p),*a],text=True).strip()
def read(p):return json.loads(Path(p).read_bytes())
def write(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,sort_keys=True,indent=2,allow_nan=False);f.write('\n')

def main():
    a=argparse.ArgumentParser();a.add_argument('--expected-head',required=True);args=a.parse_args()
    if sys.flags.optimize or not sys.flags.isolated or not sys.dont_write_bytecode:raise RuntimeError('Use -I -B without -O')
    if os.environ.get('CODESPACE_NAME')!='bookish-pancake-vwqx7rr9x5w3wxjr':raise RuntimeError('Wrong target')
    if git(REPO,'rev-parse','HEAD')!=args.expected_head or git(REPO,'status','--porcelain'):raise RuntimeError('Seal source must be frozen and clean')
    if (EXTERNAL/'stop-v1').exists():raise RuntimeError('Existing stop evidence preserved; no overwrite')
    out=EXTERNAL/'stop-v1';out.mkdir()
    control=read(EXTERNAL/'preparation-v1/preparation_control.json')
    before=read(ROOT/'TARGET_DISCOVERY.json')['Actual']
    checks=[]
    def check(name,okay,actual=None):checks.append(dict(Purpose=name,Expected=True,Actual=actual,Status='PASS' if okay else 'FAIL'))
    check('Actual attempt stopped as BLOCKED',control['Status']=='BLOCKED')
    commands=control['Actual']['commands']
    check('Only two helper commands; no source preparation invocation',len(commands)==2 and [c['label'] for c in commands]==['test_data.py','test_freeze_data_spec.py'])
    check('Both children exited and reaped',all(c['child_reaped'] for c in commands),[{k:c.get(k) for k in ('pid','returncode','child_reaped')} for c in commands])
    for c in commands:
        check('Recorded child PID no longer active '+str(c['pid']),not Path('/proc',str(c['pid'])).exists())
    check('No fresh data or model run directory',not (EXTERNAL/'preparation-v1/data').exists() and not (EXTERNAL/'attempt-v1').exists())
    helper=read(EXTERNAL/'preparation-v1/test_data.py.json')
    check('28 exact data helper tests passed',helper['Status']=='PASS' and helper['Actual']['planned']==helper['Actual']['run']==28 and helper['Actual']['failures']==helper['Actual']['errors']==helper['Actual']['skipped']==0)
    err=(EXTERNAL/'preparation-v1/test_freeze_data_spec.py.stderr').read_text()
    check('Second helper failed during sibling import before tests',commands[1]['returncode']==1 and "ModuleNotFoundError: No module named 'freeze_data_spec'" in err and not (EXTERNAL/'preparation-v1/test_freeze_data_spec.py.json').exists())
    for label,p,expected in [('accepted old MoDA',OLD,before['old_repo']),('upstream',Path('/workspaces/mythos-parcae-pinned'),before['upstream'])]:
        state=dict(head=git(p,'rev-parse','HEAD'),status=git(p,'status','--porcelain'));check(label+' Git unchanged',state==expected,state)
    main=Path('/workspaces/OpenMythos')
    check('Main preexisting tracked/untracked status unchanged',git(main,'rev-parse','HEAD')==before['main_head'] and git(main,'status','--porcelain=v1','--untracked-files=all')==before['main_status'])
    prior=Path('/workspaces/mythos-evidence/base_v01/moda_residual/attempt-v2/protected_before.json.gz')
    check('Prior complete manifest identity',pin(prior)==dict(bytes=1181241,sha256='6358e3bc273953d4a48f0a233ed2aa32cb118aedb4b3cfc76bf6e89dc9549a02'))
    protected=json.loads(gzip.decompress(prior.read_bytes()))
    recent=read(OLD/'research/mini_mythos/base_v01/moda_residual_v2/EXTERNAL_EVIDENCE_MANIFEST.json')
    overlap=[p for p in protected.keys()&recent.keys() if protected[p]!=recent[p]]
    check('Prior and accepted current run seals agree',not overlap,overlap)
    mapping={**protected,**recent};changed=[]
    for i,(name,expected) in enumerate(sorted(mapping.items())):
        try:
            actual=pin(name)
            if actual!=expected:changed.append(dict(path=name,expected=expected,actual=actual))
        except OSError as exc:changed.append(dict(path=name,error=repr(exc)))
        if i%4000==0:print(json.dumps(dict(phase='stop custody',checked=i,total=len(mapping))),flush=True)
    check('All prior protected and accepted-run bytes preserved',not changed,dict(prior_count=len(protected),accepted_run_files=len(recent),unique_rehashed=len(mapping),changed=changed))
    check('No model or numerical modules imported',not any(n.split('.')[0] in ('torch','numpy','parcae_lm','tokenizers','pyarrow') for n in sys.modules))
    custody=dict(Purpose='Post-stop preservation audit; no retry or model calculation',Environment=dict(python=sys.version,codespace=os.environ['CODESPACE_NAME']),Input=dict(base=BASE,prep_freeze=PREP_FREEZE,seal_source=args.expected_head),Expected='Stopped children and unchanged prior sealed files',Actual=dict(checks=checks,model_calls=0,source_acquisitions=0),Status='PASS' if all(c['Status']=='PASS' for c in checks) else 'FAIL',utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    write(out/'custody.json',custody)
    inventory={str(p):pin(p) for p in sorted(EXTERNAL.rglob('*')) if p.is_file()}
    write(out/'EXTERNAL_MANIFEST.json',inventory)
    export={}
    for p in sorted(EXTERNAL.rglob('*')):
        if p.is_file():
            rel=p.relative_to(EXTERNAL);dest=ROOT/'blocked_evidence'/rel;dest.parent.mkdir(parents=True,exist_ok=True)
            with dest.open('xb') as f:f.write(p.read_bytes())
            if pin(dest)!=pin(p):raise RuntimeError('Evidence copy differs: '+str(p))
            export[str(dest.relative_to(ROOT))]=pin(dest)
    write(ROOT/'BLOCKED_EXPORT_MANIFEST.json',export)
    summary=dict(Purpose='Frozen-weight native F32/control/MoDA transfer quality and complete CPU timing',Environment=dict(target='bookish-pancake-vwqx7rr9x5w3wxjr',data_python='/workspaces/mythos-depth-data-cpu312/bin/python',base_cpu_runtime='Unchanged; not imported this attempt'),Input=dict(base=BASE,branch='mythos-moda-fresh-cpu-v1',data_freeze='1f322af67bca976bf3de7b00433c1f5876c74ae3',launch_freeze=PREP_FREEZE,seal_source=args.expected_head),Expected=dict(fresh_texts=20,training_steps=0,model_calls=405,quality_rows=200,repeat_rows=200),Actual=dict(data_helper_pass=28,specification_helper_tests_executed=0,source_downloads=0,selected_fresh_texts=0,model_calls=0,training_steps=0,quality_rows=0,repeat_rows=0,custody=custody['Status']),Status='BLOCKED',scientific_conclusion='UNRESOLVED',quality='NOT TESTED',complete_cpu_timing='NOT TESTED',cause="Frozen specification helper has no sibling-module path bootstrap under python -I; ModuleNotFoundError before test execution. Parent correctly stopped, but its report foregrounds the subsequently missing helper report.",limitations=['Static reviews failed to catch the exact isolated launch interface; their PASS is not runtime acceptance.','No fresh text acquired or selected, therefore neither novelty nor fresh-test performance established.','audit_data.py remains untested draft; model executor has no final source/input/capacity freeze.'],Formal_Oracle='BLOCKED/NOT_READY',FORMAL_ACCEPTANCE_READY=False)
    write(ROOT/'RESULTS_SUMMARY.json',summary)
    cp=f'''# MYTHOS-MODA-FRESH-CPU-V1 checkpoint\n\nStatus: **BLOCKED during preparation; no new source or model execution**.\n\nBase `{BASE}`; branch `mythos-moda-fresh-cpu-v1`. Data source freeze `1f322af67bca976bf3de7b00433c1f5876c74ae3`; launch freeze `{PREP_FREEZE}`; read-only sealing source `{args.expected_head}`. This result/documentation commit is identified by Git HEAD after publication. No formal model-execution freeze exists.\n\nPurpose: compare unchanged native fixed32, equal-parameter control and MoDA on deduplicated project-new text, including complete CPU prediction time. Expected: 20 texts, 405 calls including 5 historical bridges, 200 unique quality rows, 200 repeat calls, zero training. Actual: source downloads 0, selected texts 0, model calls 0, training 0. Quality and full CPU timing **NOT TESTED**; scientific conclusion **UNRESOLVED**.\n\nThe history-format specification succeeded for 32,244 paths, including explicit binary/archive classifications. Target data helper tests passed 28/28. The second helper `test_freeze_data_spec.py` exited before running tests: `ModuleNotFoundError: No module named 'freeze_data_spec'` under the prescribed `python -I -B` launch. Its missing report subsequently raised FileNotFoundError in the parent, which recorded BLOCKED and stopped. This is our launch-interface defect, not model failure. No rerun, fallback source, threshold or model change occurred. Earlier local 10/10 helper PASS and static review PASS did not establish isolated target launch compatibility.\n\nEnvironment: designated Codespace; data Python3.12.3, existing dependencies. Model CPU runtime remains Torch2.11.0+cpu/NumPy1.26.4 but was not loaded. The stdlib history-policy tool used target system Python3.14.2, recorded separately. No installs or GPU.\n\nEvidence: `blocked_evidence/` preserves all newly produced external discovery/specification/preparation logs and stop audit, including original traceback; `BLOCKED_EXPORT_MANIFEST.json` binds copies. External originals remain under `/workspaces/mythos-evidence/base_v01/moda_fresh/`. Post-stop custody **{custody['Status']}**, rehashed {len(mapping)} prior-protected/accepted-run files; original manifest retains all25,436 paths. Upstream and accepted base Git states and main preexisting status were checked. Newly drafted model/audit/measurement code and every development report are retained, explicitly unexecuted; `audit_data.py` is untested draft. No target storage or data audit occurred.\n\nRemaining: fix the isolated sibling-import startup defect and cover the exact launch interface; complete and test independent data audit; then a separately frozen new preparation attempt and capacity gates before any model call. Preserve this attempt unchanged. Do not infer transfer or speed from old development results. A5/B1 and thresholds unchanged; no upstream changes, stacking, B2/D2-A, GPU or PR24 operation. Formal Oracle **BLOCKED/NOT_READY**; `FORMAL_ACCEPTANCE_READY=False`.\n\nNext unique instruction: from this checkpoint, repair only the isolated helper launch interface, add subprocess tests using the exact `-I -B` command, finish the pending data audit, and freeze a new continuation before a new attempt. Do not reuse or overwrite preparation-v1. This checkpoint does not execute that continuation.\n'''
    with (ROOT/'CHECKPOINT.md').open('x',encoding='utf-8') as f:f.write(cp)
    print(json.dumps(dict(experiment='BLOCKED',custody=custody['Status'],checks=len(checks),files_rehashed=len(mapping),exported_files=len(export),model_calls=0)),flush=True)
    return 0 if custody['Status']=='PASS' else 2

if __name__=='__main__':raise SystemExit(main())
