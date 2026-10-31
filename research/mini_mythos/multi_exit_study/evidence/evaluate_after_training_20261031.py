#!/usr/bin/env python3
"""Invoke the unchanged reviewed MES evaluate phase, with endpoint record checks.
NOT a per-worker H1 read-time fix; Claude R02 remains OPEN. No training/resume.
"""
from __future__ import annotations
import hashlib, importlib.util, json, os, subprocess, sys
from pathlib import Path

REPO=Path('/workspaces/OpenMythos')
OUT=REPO/'mythos_evidence/mes1_v1_gptfix1'
PIN='7bcb08f480d0bda2dba5b1351442190001492782'
TRAIN_SHA='318b0cfbca08f5c33f36b7514300186e63e3a404c8ee1aac7e1177e4de021f69'
PREP_SHA='d6ec93cb908d3994b6098b913c9b045d06b055a8fbade92bf62cdd0c5ae20678'
SOURCE_SHA='298cb63094c3c67e76786a387e79d302d707ecc8e959c566561281a097db56c9'
REVIEW_SHA='a6de1292561d416a721e5c8e6bc31655400017d5cfe7c071792f4f1e42c1cad7'
EXPERIMENT='MYTHOS-MES1-EQUAL-COUNT-HOLDOUT-V1'
STEPS={'GPT':5941,'P2':5433,'P4':3822,'A':3000}
SEEDS=(101,202,303,404,505)
GATES=('primary_equal_budget_A4_P4','same_updates_A4_P4','external_GPT_safeguard','intermediate_P2_safeguard','A_extra_depth')

def require(ok,msg):
    if not ok:raise RuntimeError(msg)
def digest(raw):return hashlib.sha256(raw).hexdigest()
def file_sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def object_sha(v):return digest(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode())
def read(p):
    def pairs(items):
        out={}
        for k,v in items:
            require(k not in out,'duplicate JSON key');out[k]=v
        return out
    def bad(v):raise ValueError('nonfinite JSON constant '+v)
    return json.loads(p.read_bytes(),object_pairs_hook=pairs,parse_constant=bad)
def git(root,*args):return subprocess.check_output(['git','-C',str(root),*args],text=True).strip()

def worktree():
    raw=subprocess.check_output(['git','-C',str(REPO),'worktree','list','--porcelain','-z'])
    found=[];record={}
    for field in raw.split(b'\0'):
        if not field:
            if record.get('HEAD')==PIN and 'worktree' in record:found.append(Path(record['worktree']))
            record={};continue
        key,_,value=field.decode().partition(' ');record[key]=value
    require(found,'no existing worktree at reviewed commit; do not create/reset')
    # Identical pinned trees are equivalent; choose a clean one deterministically.
    for wt in sorted(found):
        if wt.is_dir() and git(wt,'rev-parse','HEAD')==PIN and not git(wt,'status','--porcelain','--untracked-files=no'):
            return wt
    raise RuntimeError('no clean reviewed worktree')

def precheck(wt,out):
    require(file_sha(out/'training.json')==TRAIN_SHA,'training.json differs from uploaded audited bytes')
    require(file_sha(out/'prepared.json')==PREP_SHA,'prepared.json identity differs')
    require(file_sha(out/'pretraining_review.md')==REVIEW_SHA,'registered review bytes differ')
    p,t=read(out/'prepared.json'),read(out/'training.json')
    require(p.get('experiment')==t.get('experiment')==EXPERIMENT,'wrong experiment')
    require(p.get('phase')=='prepare' and t.get('phase')=='train','wrong prerequisite phase')
    require(p.get('status')==t.get('status')=='PASS' and p.get('exit_code')==t.get('exit_code')==0,'prerequisite incomplete')
    require(p.get('code_head')==PIN and t.get('pairing_status')=='PASS','wrong execution or pairing')
    ident=p['source_identity'];require(ident['sha256']==SOURCE_SHA,'prepared source identity differs')
    require(object_sha({'own':ident['own'],'inherited':ident['inherited']})==SOURCE_SHA,'malformed source identity')
    require(t['review']['source_identity_sha256']==SOURCE_SHA and t['review']['report_sha256']==REVIEW_SHA,'review bindings differ')
    require(t['review']['owner_acknowledged_approval'] is True,'owner review acknowledgement absent')
    root=wt/'research/mini_mythos';own=root/'multi_exit_study'
    actual={x.name:file_sha(x) for x in own.iterdir() if x.suffix in ('.py','.sh') or x.name=='PROTOCOL.md'}
    require(actual==ident['own'],'reviewed own sources changed')
    for name,h in ident['inherited'].items():require(file_sha(root/name)==h,'inherited sources changed: '+name)
    mapping={(r['arm'],r['seed']):r for r in t['rows']}
    require(len(t['rows'])==len(mapping)==20 and set(mapping)=={(a,s) for a in STEPS for s in SEEDS},'twenty complete trajectories required')
    snapshots={}
    for (a,s),r in mapping.items():
        require(r['status']=='PASS' and r['steps']==r['planned_steps']==STEPS[a],'incomplete training row')
        require(r['source_identity']==SOURCE_SHA and r['initial_model_sha256']==p['starts'][str(s)][a]['model_sha256'],'row source/start binding')
        require(r['counted_training_flops']==p['budget']['arms'][a]['total_flops'],'row budget binding')
        require(set(r['snapshots'])=={'3000',str(STEPS[a])},'snapshot endpoints missing')
        for step,snap in r['snapshots'].items():
            expected=f'jobs/{a}_{s}/step{step}.pt';require(snap['file']==expected,'unexpected snapshot path')
            path=(out/expected).resolve();require(path.is_relative_to(out.resolve()),'snapshot path escaped')
            require(file_sha(path)==snap['sha256'],'snapshot missing/changed: '+expected)
            snapshots[expected]=snap['sha256']
    require(len(snapshots)==35,'expected35 snapshot files')
    return p,t,snapshots

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

def postcheck(wt,out,prepared,training):
    r=read(out/'result.json')
    require(r.get('experiment')==EXPERIMENT and r.get('phase')=='evaluate' and r.get('execution_status')=='PASS','evaluation did not finish; keep all partial evidence')
    require(r['training_summary_sha256']==TRAIN_SHA,'result training binding differs')
    require(r['training_rows']==training['rows'],'result training records changed')
    require(file_sha(out/'H1.json')==r['H1_file_sha256'],'H1 endpoint bytes changed')
    truth=read(out/'H1.json');require(len(truth)==2048 and object_sha(truth)==r['H1_sha256'],'H1 content digest')
    # This runs only AFTER the reviewed parent and all workers completed.
    root=wt/'research/mini_mythos'
    policy=load('mes_handoff_policy',root/'multi_exit_study/mes_policy.py')
    task=load('mes_handoff_task',root/'r1b_calibration/task.py')
    allocation,manifest=policy.allocate(task)
    require(manifest==prepared['holdouts'],'reserved allocation changed')
    require(truth==policy.h1_examples(task,allocation),'H1 differs from frozen deterministic task')
    for row in r['rows']:
        require(task.score(truth,row['predictions'])==row['metrics'],'saved metrics inconsistent with frozen H1')
    require(policy.summarize(r['rows'],truth)==r['outcome'],'separate outcome recomputation differs')
    print('H1 endpoint identity and saved prediction rescoring: PASS')
    for key in GATES:print(key,r['outcome'][key]['status'])
    print('R02 remains OPEN: endpoint checks are NOT per-worker read-time identity proof.')
    return r

def main():
    os.environ.update(CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',MES1_OUTPUT_DIR=str(OUT))
    wt=worktree();p,t,snapshots=precheck(wt,OUT)
    print('Reviewed worktree:',wt,flush=True);print('Existing training, preparation and35 snapshot files: PASS',flush=True)
    result=OUT/'result.json'
    if result.exists():
        print('Existing evaluation retained; no rerun or automatic resume.',flush=True)
        postcheck(wt,OUT,p,t);return read(result)['exit_code']
    require(not (OUT/'evaluate.started').exists() and not (OUT/'H1.json').exists(),'partial evaluation evidence retained')
    require(not any((OUT/'jobs'/f'{a}_{s}'/'H1.json').exists() for a in STEPS for s in SEEDS),'prior worker H1 evidence retained')
    rc=subprocess.run(['bash',str(wt/'research/mini_mythos/multi_exit_study/run_codespaces_cpu.sh'),'evaluate'],cwd=wt,check=False).returncode
    require(result.is_file(),'no evaluation result; inspect console log, do not retrain')
    precheck(wt,OUT)  # Bound source and training bytes remain unchanged.
    r=postcheck(wt,OUT,p,t)
    require(type(rc)is int and rc==r['exit_code'] and rc in (0,1,2),'exit/result mismatch')
    receipt=OUT/'evaluation_handoff_integrity.json'
    require(not receipt.exists(),'existing integrity receipt retained')
    with receipt.open('x') as f:
        json.dump(dict(scope='endpoint checks only; no source/model changes',status='PASS',training_sha256=TRAIN_SHA,
            prepared_sha256=PREP_SHA,result_sha256=file_sha(result),H1_file_sha256=r['H1_file_sha256'],snapshot_files_checked=35,
            screens={k:r['outcome'][k]['status'] for k in GATES},R02='OPEN; no per-worker read-time checksum'),f,indent=2)
        f.write('\n')
    print('Result:',result);print(file_sha(result));return rc
if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as exc:print('BLOCKED (handoff):',str(exc),file=sys.stderr);raise SystemExit(2)
