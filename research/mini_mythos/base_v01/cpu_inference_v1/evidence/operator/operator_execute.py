import pathlib,subprocess,json,datetime,traceback
op=pathlib.Path('/workspaces/mythos-evidence/base_v01/inference_operator/inference-v1-20261101T062256Z')
command=['/workspaces/mythos-base-v01-cpu312/bin/python', '-B', '/workspaces/mythos-base-v01-rope-diag-v11/research/mini_mythos/base_v01/cpu_inference_v1/run_forward_check.py', '--execute', '--implementation-commit', '3e43c6e674c62a58844c54a0d7642f808c6278c3', '--run-id', 'inference-v1-20261101T062256Z']
started=datetime.datetime.now(datetime.timezone.utc).isoformat()
try:
 with (op/'stdout.log').open('xb') as out,(op/'stderr.log').open('xb') as err:
  result=subprocess.run(command,stdout=out,stderr=err)
 record={"started":started,"finished":datetime.datetime.now(datetime.timezone.utc).isoformat(),"returncode":result.returncode}
except BaseException:
 record={"started":started,"finished":datetime.datetime.now(datetime.timezone.utc).isoformat(),"status":"BLOCKED","traceback":traceback.format_exc()}
with (op/"completion.json").open("x") as f:json.dump(record,f,indent=2)
