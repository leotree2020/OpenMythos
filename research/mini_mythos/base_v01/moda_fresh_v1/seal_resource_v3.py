"""Seal only the observed v3 storage block; no parser, data, or model retry."""
import argparse, datetime, gzip, hashlib, json, os, shutil, subprocess, sys
from pathlib import Path

REPO = Path('/workspaces/mythos-moda-fresh-cpu-v1')
ROOT = REPO / 'research/mini_mythos/base_v01/moda_fresh_v1'
EXT = Path('/workspaces/mythos-evidence/base_v01/moda_fresh')
BASE = '2ea2cc39f6cf0a3ccbb482f21e960b4ce34bda3b'
FLOOR = 289406976

def read(p): return json.loads(Path(p).read_bytes())
def pin(p):
    h = hashlib.sha256(); size = 0
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''): h.update(b); size += len(b)
    return dict(bytes=size, sha256=h.hexdigest())
def git(p, *a): return subprocess.check_output(['git','-C',str(p),*a], text=True).strip()
def save(p, v):
    with p.open('x', encoding='utf-8') as f: json.dump(v, f, sort_keys=True, indent=2, allow_nan=False); f.write('\n')

def main():
    a = argparse.ArgumentParser(); a.add_argument('--expected-head', required=True); a = a.parse_args()
    if os.environ.get('CODESPACE_NAME') != 'bookish-pancake-vwqx7rr9x5w3wxjr' or not sys.flags.isolated or not sys.dont_write_bytecode:
        raise RuntimeError('Designated target and -I -B required')
    if git(REPO,'rev-parse','HEAD') != a.expected_head or git(REPO,'status','--porcelain'):
        raise RuntimeError('Clean frozen closure source required')
    restore = read(EXT/'continuation-v3-restore.json')
    observed = restore['Actual']['free_bytes']
    if restore['Input'] != BASE or observed >= FLOOR:
        raise RuntimeError('Recorded stop condition not established')
    out = EXT/'stop-v3-resource'; out.mkdir(exist_ok=False)
    checks = []
    def check(name, ok, actual=None): checks.append(dict(Purpose=name, Expected=True, Actual=actual, Status='PASS' if ok else 'FAIL'))
    for n in ('STORAGE_BUDGET.md','data_prepare.py','audit_data.py','execute_once.py','run_fresh.py','audit_stream.py','DATA_PROTOCOL.md','PROTOCOL.md','CONTINUATION_V2_CHECKPOINT.md'):
        old = subprocess.check_output(['git','-C',str(REPO),'show',BASE+':research/mini_mythos/base_v01/moda_fresh_v1/'+n])
        check('Frozen existing file unchanged: '+n, (ROOT/n).read_bytes() == old)
    check('Unchanged published capacity floor', b'289406976' in (ROOT/'STORAGE_BUDGET.md').read_bytes())
    check('No new preparation or model attempt', not (EXT/'preparation-v3').exists() and not (EXT/'attempt-v1').exists())
    names = {'prepare_once.py','prepare_once_v2.py','prepare_once_v3.py','data_prepare.py','run_fresh.py','audit_stream.py','measure_storage.py','execute_once.py'}
    active = []
    for p in Path('/proc').glob('[0-9]*/cmdline'):
        try: argv = p.read_bytes().decode(errors='replace').split('\x00')
        except OSError: continue
        if any(Path(x).name in names for x in argv if x): active.append(dict(pid=p.parent.name, argv=argv))
    check('No preparation or model workers active', not active, active)
    before = read(ROOT/'TARGET_DISCOVERY.json')['Actual']
    for key,path in [('upstream','/workspaces/mythos-parcae-pinned'),('old_repo','/workspaces/mythos-moda-residual-cpu-v2')]:
        actual = dict(head=git(path,'rev-parse','HEAD'), status=git(path,'status','--porcelain'))
        check(key+' unchanged', actual == before[key], actual)
    check('Main prior checkout unchanged', git('/workspaces/OpenMythos','rev-parse','HEAD') == before['main_head'] and git('/workspaces/OpenMythos','status','--porcelain=v1','--untracked-files=all') == before['main_status'])
    old_manifest = Path('/workspaces/mythos-evidence/base_v01/moda_residual/attempt-v2/protected_before.json.gz')
    check('Original protection inventory unchanged', pin(old_manifest) == dict(bytes=1181241,sha256='6358e3bc273953d4a48f0a233ed2aa32cb118aedb4b3cfc76bf6e89dc9549a02'))
    mapping = json.loads(gzip.decompress(old_manifest.read_bytes()))
    recent = read('/workspaces/mythos-moda-residual-cpu-v2/research/mini_mythos/base_v01/moda_residual_v2/EXTERNAL_EVIDENCE_MANIFEST.json')
    check('Overlapping protected pins agree', all(mapping[k] == recent[k] for k in mapping.keys() & recent.keys()))
    mapping.update(recent)
    protected_count = len(mapping)
    for p in (EXT/'stop-v1/EXTERNAL_MANIFEST.json', EXT/'stop-v2/EXTERNAL_MANIFEST.json'):
        more = read(p)
        check('Fresh manifest overlap agrees '+p.parent.name, all(mapping[k] == more[k] for k in mapping.keys() & more.keys()))
        mapping.update(more)
    changed = []
    for i,(name,value) in enumerate(sorted(mapping.items())):
        try:
            if pin(name) != value: changed.append(name)
        except OSError: changed.append(name)
        if i % 4000 == 0: print(json.dumps(dict(phase='read-only custody',checked=i,total=len(mapping))),flush=True)
    check('All prior protected and previous fresh manifest paths unchanged', protected_count == 25986 and not changed, dict(prior_protected=protected_count,total_rehashed=len(mapping),changed=changed))
    check('No numerical/data/model imports', not any(x.split('.')[0] in ('torch','numpy','pyarrow','tokenizers','parcae_lm') for x in sys.modules))
    custody = dict(Purpose='Preserve prior files after v3 resource stop', Environment=dict(python=sys.version,codespace=os.environ['CODESPACE_NAME']), Input=dict(base=BASE,closure_source=a.expected_head), Expected='All old bytes unchanged; no new experiment', Actual=dict(checks=checks), Status='PASS' if all(c['Status']=='PASS' for c in checks) else 'FAIL')
    save(out/'custody.json',custody)
    report = dict(Purpose='Check unchanged capacity requirement before spending more space on preparation',Environment=dict(codespace=os.environ['CODESPACE_NAME'],python=sys.version,numerical_environment='not imported'),Input=dict(base=BASE,closure_source=a.expected_head,restore=pin(EXT/'continuation-v3-restore.json'),storage_protocol=pin(ROOT/'STORAGE_BUDGET.md')),Expected=dict(required_free_bytes=FLOOR,reserve_bytes=268435456,raw_budget_bytes=8388608,nonraw_budget_bytes=12582912),Actual=dict(observed_free_bytes=observed,shortfall_bytes=FLOOR-observed,closure_free_bytes=shutil.disk_usage(REPO).free,parser_implemented=False,tests_run=0,history_files_scanned=0,source_acquisitions=0,selected_texts=0,model_calls=0,training_steps=0,custody=custody['Status']),Status='BLOCKED',gate='Early necessary-capacity guard; full post-preparation storage measurement NOT TESTED',quality='NOT TESTED',complete_cpu_timing='NOT TESTED',scientific_conclusion='UNRESOLVED',utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    save(out/'resource_gate.json',report)
    save(out/'EXTERNAL_MANIFEST.json',{str(p):pin(p) for p in (EXT/'continuation-v3-restore.json',out/'resource_gate.json',out/'custody.json')})
    dest = ROOT/'continuation_v3_evidence'; dest.mkdir(exist_ok=False)
    exports = {}
    for p in (EXT/'continuation-v3-restore.json',out/'resource_gate.json',out/'custody.json',out/'EXTERNAL_MANIFEST.json'):
        target = dest/p.name
        with target.open('xb') as f: f.write(p.read_bytes())
        if pin(target) != pin(p): raise RuntimeError('Evidence copy mismatch')
        exports[str(target.relative_to(ROOT))] = pin(target)
    save(ROOT/'CONTINUATION_V3_EXPORT_MANIFEST.json',exports)
    save(ROOT/'CONTINUATION_V3_RESULTS.json',report)
    text = f'''# Fresh MoDA continuation v3: resource BLOCKED\n\nBase `{BASE}`; branch `mythos-moda-fresh-cpu-v1`; read-only closure source `{a.expected_head}`. Result commit is the commit containing this checkpoint. The prior v1/v2 checkpoints and evidence remain unchanged.\n\nPurpose: repair historical Python parsing, then finish the frozen-weight native fixed32/shared-control/MoDA new-text CPU comparison. Expected: full retained-history coverage, unchanged data filters, weights and thresholds, then quality and complete endpoint timing. Actual: target restored; an early necessary-capacity guard found **{observed} free bytes**, below the unchanged **{FLOOR} bytes** formal admission floor by **{FLOOR-observed} bytes**. This is before additional preparation output. **BLOCKED**, stopped without parser implementation, tests, new history scan, acquisition or model calls. The formal post-preparation inventory/capacity gate remains NOT TESTED.\n\nEnvironment: designated Codespace; system Python {sys.version.split()[0]} used only for standard-library observation/sealing. Existing numerical environments were not imported or modified.\n\nNo source file was skipped or rewritten; history parsing was not attempted. The malformed historical `inventory_source.py` remains unresolved. Three ChatGPT peer agents performed partial local reading only and stopped with zero edits/tests; no review approval or repair PASS is claimed.\n\nEvidence: `continuation_v3_evidence/` and `CONTINUATION_V3_EXPORT_MANIFEST.json`; original external records in `/workspaces/mythos-evidence/base_v01/moda_fresh/stop-v3-resource/` plus `continuation-v3-restore.json`. Read-only custody **{custody['Status']}**, including {len(mapping)} rehashed prior paths (25986 old protected/accepted-run entries plus prior fresh records); no changed bytes detected if PASS. Active experiment worker check is recorded. No cleanup or storage expansion was attempted.\n\nQuality and complete CPU timing **NOT TESTED**, scientific conclusion **UNRESOLVED**. This resource stop says nothing about MoDA quality. No upstream, weights, thresholds, MoE stacking, GPU, B1, B2/D2-A or PR24 changes. Formal Oracle BLOCKED/NOT_READY; FORMAL_ACCEPTANCE_READY=False.\n\nNext unique instruction: restore sufficient target storage capacity without deleting or relocating protected evidence and without reducing the frozen budgets; allow enough for preparation/publication in addition to the 289406976-byte model admission floor. Then resume the parser-only repair with synthetic coverage tests and a new preserved preparation attempt, followed by unchanged data/capacity gates before any model calls. No automatic retry has occurred.\n'''
    with (ROOT/'CONTINUATION_V3_CHECKPOINT.md').open('x',encoding='utf-8') as f: f.write(text)
    marker = ROOT/'LATEST_CHECKPOINT.json'
    with marker.open('w',encoding='utf-8') as f: json.dump(dict(path='research/mini_mythos/base_v01/moda_fresh_v1/CONTINUATION_V3_CHECKPOINT.md',Status='BLOCKED',reason='insufficient frozen admission capacity',parser_implemented=False,model_calls=0,commit_resolution='same result commit as marker; prior checkpoints preserved'),f,indent=2); f.write('\n')
    print(json.dumps(dict(Status='BLOCKED',custody=custody['Status'],observed_free_bytes=observed,required_free_bytes=FLOOR,model_calls=0)),flush=True)
    return 0 if custody['Status']=='PASS' else 2

if __name__ == '__main__': raise SystemExit(main())
