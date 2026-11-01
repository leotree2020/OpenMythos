import pathlib,subprocess,json,hashlib,datetime,os
repo=pathlib.Path('/workspaces/mythos-base-v01-rope-diag-v11');rel=pathlib.Path('research/mini_mythos/base_v01/decode_control_v1/launch_recovery_v1')
record=json.loads((repo/rel/'RUN_RECORD.json').read_text())
def git(*a):return subprocess.check_output(['git','-C',str(repo),*a],text=True).strip()
assert git('branch','--show-current')=='mythos-base-v01-decode-control-v1'
assert not git('status','--porcelain=v1','--untracked-files=all','--ignored')
assert git('merge-base','--is-ancestor',record['launcher_commit_L'],'HEAD')==''
run=pathlib.Path('/workspaces/mythos-evidence/base_v01/decode_control')/record['run_id'];assert not run.exists()
root=pathlib.Path(record['operator_dir']);root.mkdir(parents=True,exist_ok=False)
source=(repo/rel/'mythos_launch.py').read_bytes();assert hashlib.sha256(source).hexdigest()==record['launcher_sha256']
(root/'mythos_launch.py').write_bytes(source)
config={k:record[k] for k in ['command','cwd','timeout_seconds']};(root/'config.json').write_text(json.dumps(config,indent=2)+chr(10))
prior=pathlib.Path('/workspaces/mythos-evidence/base_v01/decode_operator/decode-v1-20261101T071421Z')
prior_manifest={str(p.relative_to(prior)):{'size':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(prior.rglob('*')) if p.is_file()}
(root/'prior_failed_attempt_manifest.json').write_text(json.dumps({'root':str(prior),'files':prior_manifest},indent=2)+chr(10))
cmd=['/workspaces/mythos-base-v01-cpu312/bin/python','-I','-B',str(root/'mythos_launch.py'),'--config',str(root/'config.json')]
with (root/'launcher.stdout').open('xb') as out,(root/'launcher.stderr').open('xb') as err:
 p=subprocess.Popen(cmd,cwd=repo,stdout=out,stderr=err,start_new_session=True)
launch={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pid':p.pid,'run_id':record['run_id'],'operator_dir':str(root),'launcher_command':cmd,'execution_head':git('rev-parse','HEAD'),'diagnostic_A':record['diagnostic_implementation_A'],'launcher_L':record['launcher_commit_L'],'launcher_sha256':record['launcher_sha256']}
(root/'launch_observation.json').write_text(json.dumps(launch,indent=2)+chr(10))
print(json.dumps(launch))
