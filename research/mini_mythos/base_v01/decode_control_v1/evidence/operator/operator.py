import json,pathlib,subprocess,datetime,os
root=pathlib.Path(__file__).parent
r=json.loads((root/'launch.json').read_text())
with (root/'stdout.log').open('xb') as out,(root/'stderr.log').open('xb') as err:
 p=subprocess.run(r['command'],cwd=r['cwd'],stdout=out,stderr=err)
result={'returncode':p.returncode,'finished':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pid':os.getpid()}
with (root/'completion.json').open('x') as f:json.dump(result,f,indent=2)
