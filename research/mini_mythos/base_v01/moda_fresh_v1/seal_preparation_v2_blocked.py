"""Read-only closure after preparation-v2 BLOCKED. No repair, retry or model."""
import argparse,collections,datetime,gzip,hashlib,json,os,subprocess,sys
from pathlib import Path
REPO=Path('/workspaces/mythos-moda-fresh-cpu-v1')
ROOT=REPO/'research/mini_mythos/base_v01/moda_fresh_v1'
EXT=Path('/workspaces/mythos-evidence/base_v01/moda_fresh')
PREP=EXT/'preparation-v2'
OLD=Path('/workspaces/mythos-moda-residual-cpu-v2')
BASE='3a7f8b3ac15d4354800360961018de7c66d26be6'
FREEZE='682e5469e3353eaddc2bff3789bc0b93e599e725'
def read(p):return json.loads(Path(p).read_bytes())
def pin(p):
    h=hashlib.sha256();size=0
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b);size+=len(b)
    return dict(bytes=size,sha256=h.hexdigest())
def git(p,*a):return subprocess.check_output(['git','-C',str(p),*a],text=True).strip()
def save(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,sort_keys=True,indent=2,allow_nan=False);f.write('\n')
def main():
    p=argparse.ArgumentParser();p.add_argument('--expected-head',required=True);a=p.parse_args()
    if sys.flags.optimize or not sys.flags.isolated or not sys.dont_write_bytecode or os.environ.get('CODESPACE_NAME')!='bookish-pancake-vwqx7rr9x5w3wxjr':raise RuntimeError('Use target -I -B')
    if git(REPO,'rev-parse','HEAD')!=a.expected_head or git(REPO,'status','--porcelain'):raise RuntimeError('Frozen clean sealing source required')
    out=EXT/'stop-v2';out.mkdir(exist_ok=False)
    control=read(PREP/'preparation_control.json');manifest=read(PREP/'data/manifest.json')
    history=json.loads(gzip.decompress((PREP/'data/history_ledger.json.gz').read_bytes()))
    candidates=json.loads(gzip.decompress((PREP/'data/candidates.json.gz').read_bytes()))
    acq=read(PREP/'data/acquisition.json');checks=[]
    def check(name,ok,actual=None):checks.append(dict(Purpose=name,Expected=True,Actual=actual,Status='PASS' if ok else 'FAIL'))
    check('Preparation and parent stopped BLOCKED',control['Status']==manifest['Status']=='BLOCKED')
    commands=control['Actual']['commands']
    check('Exact helpers and one data worker only',[x['label'] for x in commands]==['test_data.py','test_freeze_data_spec.py','test_launch_contract.py','data_prepare'])
    check('All children exited and reaped',all(x['child_reaped'] and not x.get('remaining_process_group') for x in commands),[{k:x.get(k) for k in ('label','pid','returncode','child_reaped')} for x in commands])
    for c in commands:check('Child no longer active '+str(c['pid']),not Path('/proc',str(c['pid'])).exists())
    helper=[]
    for n,count in [('test_data.py',28),('test_freeze_data_spec.py',10),('test_launch_contract.py',10)]:
        r=read(PREP/(n+'.json'));actual=r['Actual']
        done=actual.get('run',actual.get('tests_run'));bad=[actual[k] for k in ('failures','errors','skipped') if actual[k] not in (0,[])]
        check('Target helper complete '+n,r['Status']=='PASS' and done==count and not bad);helper.append(dict(file=n,passed=done,Status=r['Status']))
    for name,receipt in manifest['artifacts'].items():
        check('Artifact physical pin '+name,pin(PREP/'data'/name)==receipt.get('physical',receipt))
        if name.endswith('.gz'):
            b=gzip.decompress((PREP/'data'/name).read_bytes());check('Artifact canonical pin '+name,dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())==receipt['canonical'])
    check('Exact acquired source bytes',acq['Status']=='PASS' and acq['http_status']==200 and pin(PREP/'data/corpus.parquet')==dict(bytes=1234829,sha256='71de87ec66bc5737752a2502204dfa6d7fe9856ade3ea444dc6317789a4f13fb'))
    check('7600 candidate receipts retained',len(candidates)==7600)
    check('Historical parse stops on recorded invalid source',len(history)==8042 and history[-1]['Status']=='BLOCKED' and 'SyntaxError' in history[-1].get('error',''),history[-1])
    check('Historical source after-check recorded',manifest['source_after_status']=='PASS' and not manifest['forbidden_imports'])
    check('No selection, audit or model attempt',not (PREP/'data/inputs.json').exists() and not (PREP/'DATA_AUDIT.json').exists() and not (EXT/'attempt-v1').exists())
    prior_fresh=read(EXT/'stop-v1/EXTERNAL_MANIFEST.json')
    previous_exports=read(ROOT/'BLOCKED_EXPORT_MANIFEST.json')
    check('Earlier fresh attempt and seal unchanged',pin(EXT/'stop-v1/EXTERNAL_MANIFEST.json')==pin(ROOT/'blocked_evidence/stop-v1/EXTERNAL_MANIFEST.json') and all(pin(n)==v for n,v in prior_fresh.items()) and all(pin(ROOT/n)==v for n,v in previous_exports.items()))
    before=read(ROOT/'TARGET_DISCOVERY.json')['Actual']
    check('Accepted model baseline clean and unchanged',dict(head=git(OLD,'rev-parse','HEAD'),status=git(OLD,'status','--porcelain'))==before['old_repo'])
    u=Path('/workspaces/mythos-parcae-pinned');check('Upstream unchanged',dict(head=git(u,'rev-parse','HEAD'),status=git(u,'status','--porcelain'))==before['upstream'])
    m=Path('/workspaces/OpenMythos');check('Main preexisting status unchanged',git(m,'rev-parse','HEAD')==before['main_head'] and git(m,'status','--porcelain=v1','--untracked-files=all')==before['main_status'])
    prior=Path('/workspaces/mythos-evidence/base_v01/moda_residual/attempt-v2/protected_before.json.gz')
    check('Original complete manifest identity',pin(prior)==dict(bytes=1181241,sha256='6358e3bc273953d4a48f0a233ed2aa32cb118aedb4b3cfc76bf6e89dc9549a02'))
    mapping=json.loads(gzip.decompress(prior.read_bytes()));recent=read(OLD/'research/mini_mythos/base_v01/moda_residual_v2/EXTERNAL_EVIDENCE_MANIFEST.json')
    check('Old scope overlaps agree',all(mapping[n]==recent[n] for n in mapping.keys()&recent.keys()));mapping.update(recent);changed=[]
    for i,(name,value) in enumerate(sorted(mapping.items())):
        try:
            if pin(name)!=value:changed.append(name)
        except OSError:changed.append(name)
        if i%4000==0:print(json.dumps(dict(phase='read-only v2 stop custody',checked=i,total=len(mapping))),flush=True)
    check('25986 original protected/accepted-run files unchanged',len(mapping)==25986 and not changed,dict(rehashed=len(mapping),changed=changed))
    check('No numerical/model imports',not any(n.split('.')[0] in ('torch','numpy','parcae_lm','pyarrow','tokenizers') for n in sys.modules))
    custody=dict(Purpose='Preserve actual preparation-v2 BLOCKED evidence and prior results',Environment=dict(python=sys.version,codespace=os.environ['CODESPACE_NAME']),Input=dict(base=BASE,preparation_freeze=FREEZE,seal_source=a.expected_head),Expected='No retries/models; old bytes unchanged; exact partial data evidence',Actual=dict(checks=checks,rehashed=len(mapping)),Status='PASS' if all(c['Status']=='PASS' for c in checks) else 'FAIL',utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    save(out/'custody.json',custody)
    external={str(p):pin(p) for p in sorted(PREP.rglob('*')) if p.is_file()}
    for p in (EXT/'preparation-launch-v2.log',EXT/'continuation-v2-restore.json',out/'custody.json'):external[str(p)]=pin(p)
    save(out/'EXTERNAL_MANIFEST.json',external)
    dest=ROOT/'continuation_v2_evidence';dest.mkdir(exist_ok=False);exports={}
    for src in sorted(PREP.rglob('*')):
        if not src.is_file() or src.name in ('corpus.parquet','inputs.json','acquisition.json'):continue
        rel=Path('preparation-v2')/src.relative_to(PREP);target=dest/rel;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as f:f.write(src.read_bytes())
        if pin(target)!=pin(src):raise RuntimeError('Copied evidence differs: '+str(rel))
        exports[str(rel)]=pin(target)
    for src,rel in [(out/'custody.json','custody.json'),(out/'EXTERNAL_MANIFEST.json','EXTERNAL_MANIFEST.json'),(EXT/'preparation-launch-v2.log','preparation-launch-v2.log'),(EXT/'continuation-v2-restore.json','restore.json')]:
        with (dest/rel).open('xb') as f:f.write(src.read_bytes())
        if pin(dest/rel)!=pin(src):raise RuntimeError('Copy differs')
        exports[rel]=pin(dest/rel)
    public_acq={k:v for k,v in acq.items() if k!='final_url'}
    public_acq['final_url_disclosure']='Redirect query omitted from public copy; full original receipt retained and hash-bound externally.'
    save(dest/'acquisition_summary.json',public_acq);exports['acquisition_summary.json']=pin(dest/'acquisition_summary.json');save(ROOT/'CONTINUATION_V2_EXPORT_MANIFEST.json',exports)
    summary=dict(Purpose='Frozen-weight F32/shared-control/MoDA fresh-text CPU validation',Environment=dict(target=os.environ['CODESPACE_NAME'],data_python=control['Environment']['python'],model_runtime='not loaded'),Input=dict(base=BASE,launch_freeze=FREEZE,seal_source=a.expected_head),Expected=dict(selected=20,model_calls=405,quality_rows=200,repeat_rows=200,training_steps=0),Actual=dict(helper_tests=helper,helper_pass=48,source_acquisition=acq['Status'],source_rows=len(candidates),candidate_decisions=dict(collections.Counter(r['decision'] for r in candidates)),history_rows_recorded=len(history),history_statuses=dict(collections.Counter(r['Status'] for r in history)),blocked_file=history[-1],selected=0,model_calls=0,quality_rows=0,repeat_rows=0,training_steps=0,custody=custody['Status']),Status='BLOCKED',launch_repair='PASS',quality='NOT TESTED',complete_cpu_timing='NOT TESTED',scientific_conclusion='UNRESOLVED',Formal_Oracle='BLOCKED/NOT_READY',FORMAL_ACCEPTANCE_READY=False)
    save(ROOT/'CONTINUATION_V2_RESULTS.json',summary)
    text=f'''# Fresh-text continuation v2 checkpoint\n\nOverall **BLOCKED during historical-input parsing**. Original isolated startup repair **PASS** on target. Fresh-text model quality and complete CPU timing remain **NOT TESTED**; scientific conclusion **UNRESOLVED**.\n\nGit branch `mythos-moda-fresh-cpu-v1`; accepted model baseline `bc6d267cdd8cf9306c1bf08b369cf2b791723d3d`; continuation base `{BASE}`; preparation freeze `{FREEZE}`; read-only stop-seal code `{a.expected_head}`. Result commit is the commit containing this checkpoint. No formal model-execution freeze exists. Previous preparation-v1 and checkpoint remain unchanged.\n\nPurpose: compare frozen native fixed32, same-parameter shared control and MoDA on new, history-deduplicated text at zero training, reporting quality and complete CPU time. Expected:20 records,405 calls including5 historical bridges,200 unique quality rows and200 repeat calls. Actual:48/48 target helper checks PASS, one successful exact-byte source acquisition,7600 candidate receipts,8042 historical rows retained (including the stopping row),0 selected texts,0 model calls,0 updates. Do not call this a model failure or a completed novelty test.\n\nEnvironment: designated Codespace, existing data Python3.12.3/pyarrow19.0.1/NumPy1.26.4/tokenizers0.23.2. CPU only. Model Torch2.11.0+cpu environment unchanged and not loaded. No dependency install.\n\nOriginal error fixed: specification test now imports its sibling explicitly under `-I -B`; real target28 data +10 specification +10 launch tests pass. Original stderr is now preserved as the primary failure when a child produces no report. Old failed attempt is not overwritten.\n\nNew blocker: `{history[-1]['path']}` has an unterminated string at line25. Its SHA256 is `{history[-1]['sha256']}`. The unchanged history reader uses Python AST for Python source and stops on this malformed retained script. No historical file was excluded, repaired or changed; no thresholds, source filters or sample counts were relaxed. Full data-worker post-input check reports PASS. The remaining historical scan and independent data audit are incomplete, so model work was not started.\n\nEvidence: `continuation_v2_evidence/` contains target reports, original stdout/stderr, candidate and partial history ledgers, source acquisition summary and custody report. Full source parquet and acquisition receipt remain external in `/workspaces/mythos-evidence/base_v01/moda_fresh/preparation-v2/data/`, bound by `continuation_v2_evidence/EXTERNAL_MANIFEST.json`. `CONTINUATION_V2_EXPORT_MANIFEST.json` binds public copies. Raw source text is not exported. Read-only custody **{custody['Status']}**:25986 prior-protected/accepted-run files rehashed without changes, earlier fresh attempt/seal unchanged, upstream and main preexisting state unchanged.\n\nUnexecuted implementation: independent data-audit21 local fixtures PASS; updated model/storage helpers62 local fixtures PASS; peer reviews preserved. These are development results only. No target independent data audit, storage admission, model test, CPU speed comparison or scientific acceptance. All historical source and retained partial evidence remain intact.\n\nNext unique instruction: design and test lossless historical-text coverage for syntactically malformed retained Python files, preserving raw source and recoverable text/token literals rather than skipping files; freeze that parser-only continuation and a new preparation attempt. Keep source selection, weights and scientific thresholds unchanged, and preserve preparation-v1/v2. No retry is executed by this checkpoint.\n\nNo upstream, weight, A5/early-stop threshold, B1, B2/D2-A, stacking or PR24 changes. Formal Oracle **BLOCKED/NOT_READY**; `FORMAL_ACCEPTANCE_READY=False`.\n'''
    with (ROOT/'CONTINUATION_V2_CHECKPOINT.md').open('x',encoding='utf-8') as f:f.write(text)
    save(ROOT/'LATEST_CHECKPOINT.json',dict(path='research/mini_mythos/base_v01/moda_fresh_v1/CONTINUATION_V2_CHECKPOINT.md',Status='BLOCKED',launch_repair='PASS',model_calls=0,commit_resolution='Same result commit as this marker; prior CHECKPOINT.md deliberately preserved'))
    print(json.dumps(dict(Status='BLOCKED',launch_repair='PASS',custody=custody['Status'],source_rows=7600,history_rows=len(history),model_calls=0,exports=len(exports))),flush=True)
    return 0 if custody['Status']=='PASS' else 2
if __name__=='__main__':raise SystemExit(main())
