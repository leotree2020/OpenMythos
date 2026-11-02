"""Read-only custody and evidence closure after the actual v4 preflight stop."""
import argparse, gzip, json, os, pathlib, subprocess, sys
P=pathlib.Path
ROOT=P(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from seal_resource_v3 import pin, read, git, save
REPO=P('/workspaces/mythos-moda-fresh-cpu-v1')
FRESH=P('/workspaces/mythos-evidence/base_v01/moda_fresh')
PREP=FRESH/'preparation-v4'
FREEZE='45cd7aac58ec1bc1dbd42e77e3022a9fe7de4ed4'
BASE='b13ab1d799cbd5d37e58d7ea7cdf2540d0093493'
def main():
    cli=argparse.ArgumentParser();cli.add_argument('--expected-head',required=True);a=cli.parse_args()
    assert sys.flags.isolated and sys.dont_write_bytecode and os.environ.get('CODESPACE_NAME')=='bookish-pancake-vwqx7rr9x5w3wxjr'
    assert git(REPO,'rev-parse','HEAD')==a.expected_head and not git(REPO,'status','--porcelain')
    c=read(PREP/'preparation_control.json');m=read(PREP/'history-preflight/manifest.json')
    rows=json.loads(gzip.decompress((PREP/'history-preflight/preflight_findings.json.gz').read_bytes()))
    assert c['Status']==m['Status']=='BLOCKED' and c['Input']['freeze']==FREEZE
    assert c['Actual']['history_preflight_launches']==1 and c['Actual']['data_worker_launches']==0
    assert not (PREP/'data').exists() and not (FRESH/'attempt-v1').exists()
    out=FRESH/'stop-v4';out.mkdir(exist_ok=False)
    checks=[]
    def check(name,ok,actual=None):checks.append(dict(Purpose=name,Expected=True,Actual=actual,Status='PASS' if ok else 'FAIL'))
    inv=read(ROOT/'PREPARATION_V4_TEST_INVENTORY.json');passed=0
    for name,definition in inv.items():
        r=read(PREP/(name+'.json'));v=r['Actual'];n=len(definition['test_ids']);actual=v.get('run',v.get('tests_run'))
        ok=r['Status']=='PASS' and actual==n and all(v.get(k,0) in (0,[]) for k in ('failures','errors','skipped','expected_failures','unexpected_successes'))
        check('Target helper '+name,ok,dict(run=actual,planned=n));passed+=actual
    check('All76 target helpers',passed==76,passed)
    commands=c['Actual']['commands'];check('All preparation children stopped',all(x['child_reaped'] and not x.get('remaining_process_group') for x in commands))
    for k in ('old_fresh_after_status','specification_after_status','retained_source_after_status','source_after_status'):check(k,c['Actual'].get(k)=='PASS')
    check('Full input after-pin check retained',m['source_after_status']=='PASS')
    check('Actual old Python blocker parsed',any(r['Status']=='PASS' and r['path'].endswith('/inventory_source.py') and r['sha256']=='403eee09aec392aa00eb24b46633e64c1333377f13b80e503e4ebf3f7a834bb8' for r in rows))
    bad=rows[-1];check('Recorded JSONL stop file unchanged',pin(bad['path'])=={k:bad[k] for k in ('bytes','sha256')},bad)
    prior=P('/workspaces/mythos-evidence/base_v01/moda_residual/attempt-v2/protected_before.json.gz')
    assert pin(prior)==dict(bytes=1181241,sha256='6358e3bc273953d4a48f0a233ed2aa32cb118aedb4b3cfc76bf6e89dc9549a02')
    mapping=json.loads(gzip.decompress(prior.read_bytes()));more=read('/workspaces/mythos-moda-residual-cpu-v2/research/mini_mythos/base_v01/moda_residual_v2/EXTERNAL_EVIDENCE_MANIFEST.json')
    assert all(mapping[k]==more[k] for k in mapping.keys()&more.keys());mapping.update(more);assert len(mapping)==25986
    old_fresh=read(PREP/'old_fresh_before.json')
    assert all(mapping[k]==old_fresh[k] for k in mapping.keys()&old_fresh.keys());mapping.update(old_fresh)
    maintenance=read(REPO/'research/mini_mythos/maintenance/storage_20261102/EXPORT_MANIFEST.json')
    for row in maintenance.values():
        p=row['source'];expected={k:row[k] for k in ('bytes','sha256')}
        assert p not in mapping or mapping[p]==expected;mapping[p]=expected
    changed=[]
    for i,(name,value) in enumerate(sorted(mapping.items())):
        try:
            if pin(name)!=value:changed.append(name)
        except OSError:changed.append(name)
        if i%6000==0:print('Stop custody',i,'/',len(mapping),flush=True)
    check('All prior protected and old fresh bytes unchanged',not changed,dict(rehashed=len(mapping),changed=changed))
    before=read(ROOT/'TARGET_DISCOVERY.json')['Actual']
    for key,path in [('upstream','/workspaces/mythos-parcae-pinned'),('old_repo','/workspaces/mythos-moda-residual-cpu-v2')]:check(key+' unchanged',dict(head=git(path,'rev-parse','HEAD'),status=git(path,'status','--porcelain'))==before[key])
    check('Main checkout unchanged',git('/workspaces/OpenMythos','rev-parse','HEAD')==before['main_head'] and git('/workspaces/OpenMythos','status','--porcelain=v1','--untracked-files=all')==before['main_status'])
    active=[]
    for p in P('/proc').glob('[0-9]*/cmdline'):
        try:args=p.read_bytes().decode(errors='replace').split(chr(0))
        except OSError:continue
        if any(P(x).name in ('prepare_once_v4.py','data_prepare.py','run_fresh.py','audit_stream.py') for x in args if x):active.append(p.parent.name)
    check('No active experiment workers',not active,active)
    custody=dict(Purpose='Read-only closure of v4 historical-parse BLOCKED',Environment=dict(python=sys.version,codespace=os.environ['CODESPACE_NAME']),Input=dict(base=BASE,preparation_freeze=FREEZE,seal_source=a.expected_head),Expected='Preserved old bytes; complete real stop evidence',Actual=dict(checks=checks),Status='PASS' if all(x['Status']=='PASS' for x in checks) else 'FAIL')
    save(out/'custody.json',custody)
    external={str(p):pin(p) for p in PREP.rglob('*') if p.is_file()}
    for p in (FRESH/'continuation-v4-restore.json',P('/workspaces/mythos-moda-fresh-preparation-v4.log'),out/'custody.json'):external[str(p)]=pin(p)
    save(out/'EXTERNAL_MANIFEST.json',external)
    dest=ROOT/'continuation_v4_evidence';dest.mkdir(exist_ok=False);exports={}
    for p in sorted(PREP.rglob('*')):
        if not p.is_file():continue
        target=dest/'preparation-v4'/p.relative_to(PREP);target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as f:f.write(p.read_bytes())
        assert pin(target)==pin(p);exports[str(target.relative_to(ROOT))]=pin(target)
    for p in (out/'custody.json',out/'EXTERNAL_MANIFEST.json',P('/workspaces/mythos-moda-fresh-preparation-v4.log')):
        target=dest/p.name
        with target.open('xb') as f:f.write(p.read_bytes())
        assert pin(target)==pin(p);exports[str(target.relative_to(ROOT))]=pin(target)
    save(ROOT/'CONTINUATION_V4_EXPORT_MANIFEST.json',exports)
    diagnosis=read(PREP/'post_stop_record_diagnosis.json')
    summary=dict(Purpose='Frozen-weight MoDA new-text quality/CPU validation',Environment=c['Environment'],Input=dict(base=BASE,preparation_freeze=FREEZE,seal_source=a.expected_head),Expected=dict(selected=20,model_calls=405),Actual=dict(target_helpers_passed=passed,history_preflight=m['Actual'],stopping_file=bad,python_blocker_repaired=True,post_stop_record_structure=diagnosis,selected=0,model_calls=0,training_steps=0,custody=custody['Status']),Status='BLOCKED',quality='NOT TESTED',complete_cpu_timing='NOT TESTED',Formal_Oracle='BLOCKED/NOT_READY',FORMAL_ACCEPTANCE_READY=False)
    save(ROOT/'CONTINUATION_V4_RESULTS.json',summary)
    text=f'''# Fresh MoDA continuation v4 checkpoint\n\n**BLOCKED at historical JSONL parsing.** Python repair and76 target helper checks PASS; new-text quality and CPU timing NOT TESTED.\n\nBase `{BASE}`; branch mythos-moda-fresh-cpu-v1; preparation freeze `{FREEZE}`; read-only closure source `{a.expected_head}`. Result commit is the commit containing this file.\n\nPurpose: complete the unchanged frozen-weight F32/S/H new-text CPU comparison. Environment: existing designated Codespace/data Python3.12.3; no install/GPU/model import. Expected:32244 historical files,20 new texts then405 model calls. Actual: preflight reached {m['Actual']['historical_files_completed']} recorded files including the stopping row; incomplete scan,0 tokenizer calls,0 new acquisitions,0 selected texts,0 model calls and0 training. All76 helper tests pass. The exact old malformed inventory_source.py now has a retained PASS recovery finding; its original bytes remain unchanged.\n\nNew stop: `{bad['path']}`, {bad['bytes']} bytes, SHA256 `{bad['sha256']}`. It raises an unterminated-string JSON decoding error. Post-stop read-only record audit (no model/selection/retry) reports {json.dumps(diagnosis)}. Raw source text was not published. Early exploratory escaped-delimiter diagnostics are preserved but are superseded by post_stop_separator_diagnosis.json (numeric character codes) and post_stop_record_diagnosis.json (physical LF record audit). No file rewrite/skip, parser fix or preparation retry followed this stop.\n\nEvidence: continuation_v4_evidence/, CONTINUATION_V4_EXPORT_MANIFEST.json and external preparation-v4/stop-v4. Custody **{custody['Status']}** with {len(mapping)} prior-protected/fresh paths rehashed; full original-input after-pin check and old fresh/specification/source-acquisition/source-code checks PASS. Upstream, accepted model baseline and main preexisting worktree state checked. No active workers at closure if custody PASS. New independent data audit, target model storage admission and model execution remain NOT TESTED.\n\nStorage maintenance remains successful; this is a parser/data-format blocker. Scientific conclusion UNRESOLVED. All original weights, thresholds, source selection and evidence retained. No MoE stacking, B1 rerun, A5 change, B2/D2-A, GPU or PR24 merge. Formal Oracle BLOCKED/NOT_READY; FORMAL_ACCEPTANCE_READY=False.\n\nNext unique instruction: freeze a minimal controlled malformed-JSONL historical-input recovery that retains the entire original tail/file plus recoverable text/token literals without dropping files or relaxing filters, and verifies ordinary LF JSONL handling. Preserve this v4 stop and diagnose the recorded invalid record using the existing byte-pinned file. Only after synthetic coverage and a separately frozen new preparation may the unchanged full-history/new-text gates continue. Do not automatically rerun v4 or the model.\n'''
    with (ROOT/'CONTINUATION_V4_CHECKPOINT.md').open('x',encoding='utf-8') as f:f.write(text)
    with (ROOT/'LATEST_CHECKPOINT.json').open('w',encoding='utf-8') as f:json.dump(dict(path='research/mini_mythos/base_v01/moda_fresh_v1/CONTINUATION_V4_CHECKPOINT.md',Status='BLOCKED',target_helpers_passed=76,python_blocker_repaired=True,model_calls=0,remaining_blocker='historical JSONL record cannot be parsed'),f,indent=2);f.write(chr(10))
    print(json.dumps(dict(Status='BLOCKED',custody=custody['Status'],target_helpers=passed,history_recorded=m['Actual']['historical_files_completed'],model_calls=0)),flush=True)
    return 0 if custody['Status']=='PASS' else 2
if __name__=='__main__':raise SystemExit(main())
