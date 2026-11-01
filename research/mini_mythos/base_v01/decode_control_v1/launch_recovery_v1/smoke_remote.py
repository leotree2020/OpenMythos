import pathlib,subprocess,json,datetime,base64,hashlib,sys,os
repo=pathlib.Path('/workspaces/mythos-base-v01-rope-diag-v11')
venv='/workspaces/mythos-base-v01-cpu312/bin/python'
root=pathlib.Path('/workspaces/mythos-evidence/base_v01/decode_operator')/('launch-smoke-v1-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
root.mkdir(parents=True,exist_ok=False)
b=base64.b64decode(SOURCE_B64);launcher=root/'mythos_launch.py';launcher.write_bytes(b)
checks=[]
def save(p,x):
 with p.open('x') as f:json.dump(x,f,indent=2);f.write(chr(10))
def check(ok,purpose,actual,expected):
 checks.append({'Purpose':purpose,'Environment':'target Codespace; frozen Python3.12.3; stdlib only','Input':'harmless real child processes','Expected':expected,'Actual':actual,'Status':'PASS' if ok else 'FAIL'})
 if not ok:raise RuntimeError(purpose)
def run_case(name,code,timeout=20):
 d=root/name;d.mkdir();c={'command':[venv,'-I','-B','-c',code],'cwd':str(repo),'timeout_seconds':timeout};save(d/'config.json',c)
 q=subprocess.run([venv,'-I','-B',str(launcher),'--config',str(d/'config.json')],cwd=repo,capture_output=True,timeout=40)
 (d/'launcher.stdout').write_bytes(q.stdout);(d/'launcher.stderr').write_bytes(q.stderr)
 return d,q,json.loads((d/'completion.json').read_text()),json.loads((d/'claim.json').read_text())
status='NOT TESTED'
try:
 d,q,c,claim=run_case('success',"import sys,json,operator; print('MYTHOS_SMOKE_OUT'); print('MYTHOS_SMOKE_ERR',file=sys.stderr); assert not any(n in sys.modules for n in ('torch','numpy','tokenizers'))")
 check(q.returncode==0 and c['status']=='COMPLETED' and c['returncode']==0,'Successful child completion',{'launcher_rc':q.returncode,'completion':c},'COMPLETED, child rc0, launcher rc0')
 check((d/'stdout.log').read_bytes()==b'MYTHOS_SMOKE_OUT\n' and (d/'stderr.log').read_bytes()==b'MYTHOS_SMOKE_ERR\n','Exact stdout and stderr capture',{'stdout':(d/'stdout.log').read_text(),'stderr':(d/'stderr.log').read_text()},'two exact sentinel lines')
 check(claim['source_sha256']==hashlib.sha256(b).hexdigest() and claim['isolated']==1 and not claim['numerical_libraries_imported'] and '/workspaces/' not in claim['operator_origin'],'Correct source and isolated stdlib imports',claim,'same source, isolated, no numerical modules, genuine stdlib operator')
 before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in d.iterdir() if p.is_file()}
 duplicate=subprocess.run([venv,'-I','-B',str(launcher),'--config',str(d/'config.json')],cwd=repo,capture_output=True,timeout=40)
 after={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in d.iterdir() if p.is_file()}
 save(root/'duplicate_attempt.json',{'returncode':duplicate.returncode,'stdout':duplicate.stdout.decode(),'stderr':duplicate.stderr.decode(),'before':before,'after':after})
 check(duplicate.returncode!=0 and b'FileExistsError' in duplicate.stderr and before==after,'Duplicate claim refused without overwriting logs',{'rc':duplicate.returncode,'unchanged':before==after},'refused, original files byte unchanged')
 d,q,c,claim=run_case('exit7',"import sys; print('EXIT7_OUT'); print('EXIT7_ERR',file=sys.stderr); sys.exit(7)")
 check(q.returncode==2 and c['returncode']==7 and c['status']=='CHILD_FAILED' and (d/'stdout.log').read_bytes()==b'EXIT7_OUT\n' and (d/'stderr.log').read_bytes()==b'EXIT7_ERR\n','Nonzero child exit preserved',{'launcher_rc':q.returncode,'completion':c},'launcher2, child7, CHILD_FAILED, exact output')
 grandchild="import signal,time,os; signal.signal(signal.SIGTERM,signal.SIG_IGN); print('GRANDCHILD_PID='+str(os.getpid()),flush=True); time.sleep(30)"
 parent="import subprocess,time; p=subprocess.Popen("+repr([venv,'-I','-B','-c',grandchild])+",stdout=subprocess.PIPE,text=True); print(p.stdout.readline().strip(),flush=True); time.sleep(30)"
 d,q,c,claim=run_case('timeout',parent,1)
 pid=int((d/'stdout.log').read_text().strip().split('=')[1]);statepath=pathlib.Path('/proc')/str(pid)/'status';state=next((line for line in statepath.read_text().splitlines() if line.startswith('State:')),'unknown') if statepath.exists() else 'absent'
 save(root/'timeout_process_observation.json',{'grandchild_pid':pid,'state':state,'note':'Zombie means terminated but not yet reaped, not a running process.'})
 check(q.returncode==2 and c['status']=='BLOCKED' and c['exception_type']=='TimeoutExpired' and c['cleanup'].get('kill_sent') is True and (state=='absent' or '\tZ' in state),'Timeout kills TERM-resistant child group',{'completion':c,'grandchild_state':state},'expected negative fixture: BLOCKED TimeoutExpired, group KILL, grandchild absent/zombie')
 status='PASS'
except BaseException as exc:
 status='FAIL';checks.append({'Purpose':'Smoke harness terminal state','Expected':'all cases accepted','Actual':repr(exc),'Status':'FAIL'})
finally:
 report={'Purpose':'Validate launch orchestration with harmless real subprocesses before any model work','Environment':{'codespace':os.environ.get('CODESPACE_NAME'),'launcher_python':venv},'Input':{'launcher_sha256':hashlib.sha256(b).hexdigest(),'source_bytes':len(b),'smoke_root':str(root)},'Expected':'all6 checks PASS; no model imports/weights','Actual':{'checks':len(checks),'passed':sum(x['Status']=='PASS' for x in checks)},'Status':status,'development_only':True,'formal_run_started':False,'checks':checks};save(root/'SMOKE_REPORT.json',report)
 print(json.dumps({'root':str(root),'status':status,'checks':len(checks),'passed':sum(x['Status']=='PASS' for x in checks),'source_sha256':hashlib.sha256(b).hexdigest()}))
