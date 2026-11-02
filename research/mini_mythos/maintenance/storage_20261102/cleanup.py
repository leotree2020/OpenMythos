"""Authorized cache-only maintenance; no model/data experiment or automatic retry."""
import datetime, gzip, hashlib, json, os, pathlib, shutil, subprocess, sys, traceback
P = pathlib.Path
CACHE = P('/home/codespace/.cache/pip')
REPO = P('/workspaces/mythos-moda-fresh-cpu-v1')
FRESH = P('/workspaces/mythos-evidence/base_v01/moda_fresh')
OUT = P('/workspaces/mythos-maintenance/storage-20261102-v1')
BASE = 'da3f1df3d0df83310fe10eadcb357ee5dccd4e2f'
FLOOR = 289406976
PYTHONS = [P('/workspaces')/n/'bin/python' for n in ('mythos-base-v01-cpu312','mythos-depth-data-cpu312','mythos-parcae-official-eval-cpu312')]
def pin(p):
    h=hashlib.sha256(); n=0
    with P(p).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''): h.update(b); n+=len(b)
    return dict(bytes=n,sha256=h.hexdigest())
def read(p):return json.loads(P(p).read_bytes())
def save(n,v):
    with (OUT/n).open('x',encoding='utf-8') as f:json.dump(v,f,sort_keys=True,indent=2,allow_nan=False);f.write('\n')
def run(argv):
    q=subprocess.run([str(x) for x in argv],capture_output=True,text=True,timeout=120,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PIP_DISABLE_PIP_VERSION_CHECK='1'))
    return dict(argv=[str(x) for x in argv],returncode=q.returncode,stdout=q.stdout,stderr=q.stderr)
def git(p,*args):
    q=run(['git','-C',p,*args]);assert q['returncode']==0,q;return q['stdout'].strip()
def caches():
    assert CACHE.resolve()==CACHE and not CACHE.is_symlink()
    rows={}
    for p in sorted(CACHE.rglob('*')):
        assert not p.is_symlink(),'Unexpected cache symlink'
        if p.is_file():
            assert p.stat().st_nlink==1,'Unexpected hard-linked cache file'
            assert p.resolve().is_relative_to(CACHE)
            rows[str(p.relative_to(CACHE))]=pin(p)
    return rows
def package_state():
    return {str(p):dict(freeze=run([p,'-I','-B','-m','pip','--isolated','--disable-pip-version-check','freeze','--all']),check=run([p,'-I','-B','-m','pip','--isolated','--disable-pip-version-check','check'])) for p in PYTHONS}
def git_state():
    return {str(p):dict(head=git(p,'rev-parse','HEAD'),status=git(p,'status','--porcelain=v1','--untracked-files=all')) for p in sorted(P('/workspaces').iterdir()) if p.is_dir() and (p/'.git').exists()}
def no_installers():
    active=[]
    for p in P('/proc').glob('[0-9]*/cmdline'):
        try:a=p.read_bytes().decode(errors='replace').split('\x00')
        except OSError:continue
        if p.parent.name==str(os.getpid()):continue
        if any(P(x).name in ('pip','pip3','uv','conda','mamba') for x in a[:2]) or any(a[i:i+2]==['-m','pip'] for i in range(len(a)-1)):active.append(p.parent.name)
    assert not active,dict(active_installers=active)
def verify(mapping):
    changed=[]
    for i,(name,value) in enumerate(sorted(mapping.items())):
        try:
            if pin(name)!=value:changed.append(name)
        except OSError:changed.append(name)
        if i%6000==0:print('protected',i,'/',len(mapping),flush=True)
    return dict(count=len(mapping),changed=changed,Status='FAIL' if changed else 'PASS')

def main():
    assert sys.flags.isolated and sys.dont_write_bytecode and not sys.flags.optimize
    assert os.environ.get('CODESPACE_NAME')=='bookish-pancake-vwqx7rr9x5w3wxjr'
    assert not git(REPO,'status','--porcelain')
    OUT.mkdir(parents=True,exist_ok=False)
    report=dict(Purpose='Recover Codespace disk using only the reinstallable pip cache',Environment=dict(codespace=os.environ['CODESPACE_NAME'],python=sys.version),Input=dict(base=BASE,maintenance_source=git(REPO,'rev-parse','HEAD'),cache=str(CACHE)),Expected=dict(unchanged_protected_files=True,unchanged_package_manifests=True,unchanged_git_states=True,free_bytes_at_least=FLOOR,no_model_calls=True),Actual={},Status='BLOCKED')
    try:
        before_free=shutil.disk_usage(REPO).free
        report['Actual']['before_free_bytes']=before_free
        cmd=[PYTHONS[0],'-I','-B','-m','pip','--isolated','--disable-pip-version-check','--cache-dir',CACHE,'cache']
        cache_dir=run(cmd+['dir']);assert cache_dir['returncode']==0 and P(cache_dir['stdout'].strip())==CACHE
        no_installers(); cache_before=caches();assert cache_before
        prior=P('/workspaces/mythos-evidence/base_v01/moda_residual/attempt-v2/protected_before.json.gz')
        assert pin(prior)==dict(bytes=1181241,sha256='6358e3bc273953d4a48f0a233ed2aa32cb118aedb4b3cfc76bf6e89dc9549a02')
        protected=json.loads(gzip.decompress(prior.read_bytes()))
        recent=read('/workspaces/mythos-moda-residual-cpu-v2/research/mini_mythos/base_v01/moda_residual_v2/EXTERNAL_EVIDENCE_MANIFEST.json')
        assert all(protected[k]==recent[k] for k in protected.keys()&recent.keys());protected.update(recent)
        assert len(protected)==25986
        for p in sorted(FRESH.rglob('*')):
            if p.is_file():
                v=pin(p);assert str(p) not in protected or protected[str(p)]==v;protected[str(p)]=v
        assert not any(P(n).resolve().is_relative_to(CACHE) for n in protected)
        protected_before=verify(protected);assert protected_before['Status']=='PASS'
        packages_before=package_state();assert all(v['freeze']['returncode']==0 for v in packages_before.values())
        git_before=git_state()
        save('before.json',dict(free_bytes=before_free,cache=cache_before,cache_dir=cache_dir,protected=protected_before,packages=packages_before,git=git_before,cache_device=CACHE.stat().st_dev,workspace_device=REPO.stat().st_dev,cache_free_bytes=shutil.disk_usage(CACHE).free))
        no_installers();assert caches()==cache_before,'Cache changed before purge'
        purge=run(cmd+['purge']);save('purge.json',purge);assert purge['returncode']==0,purge
        cache_after=caches();packages_after=package_state();git_after=git_state();protected_after=verify(protected)
        removed=sorted(cache_before.keys()-cache_after.keys());new=sorted(cache_after.keys()-cache_before.keys())
        same_remaining=all(cache_before[k]==v for k,v in cache_after.items() if k in cache_before)
        after_free=shutil.disk_usage(REPO).free
        after=dict(free_bytes=after_free,cache=cache_after,removed_entries=removed,new_entries=new,removed_bytes=sum(cache_before[k]['bytes'] for k in removed),protected=protected_after,packages=packages_after,git=git_after)
        save('after.json',after)
        checks=dict(cache_files_removed=bool(removed),remaining_cache_unchanged=same_remaining and not new,protected_unchanged=protected_after['Status']=='PASS',package_manifests_unchanged=packages_after==packages_before,git_states_unchanged=git_after==git_before,workspace_space_increased=after_free>before_free,admission_floor_available=after_free>=FLOOR,no_numerical_imports=not any(n.split('.')[0] in ('torch','numpy','parcae_lm','tokenizers','pyarrow') for n in sys.modules))
        report['Actual'].update(after_free_bytes=after_free,net_free_increase_bytes=after_free-before_free,removed_files=len(removed),removed_payload_bytes=after['removed_bytes'],remaining_cache_files=len(cache_after),remaining_cache_bytes=sum(x['bytes'] for x in cache_after.values()),protected_files_verified=len(protected),checks=checks,model_calls=0,compression='NOT NEEDED: cache purge restored sufficient capacity',scientific_experiment='NOT RUN')
        report['Status']='PASS' if all(checks.values()) else 'FAIL'
    except Exception:
        report['error']=traceback.format_exc()
    report['utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();save('RESULT.json',report)
    save('MANIFEST.json',{p.name:pin(p) for p in sorted(OUT.iterdir()) if p.is_file()})
    print(json.dumps(report),flush=True)
    return 0 if report['Status']=='PASS' else 2
if __name__=='__main__':raise SystemExit(main())
