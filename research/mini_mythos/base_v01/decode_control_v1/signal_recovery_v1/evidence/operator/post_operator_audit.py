"""Stdlib-only post-stop external audit. Never loads models or changes input evidence."""
import argparse, hashlib, json, re, sys
from pathlib import Path
from datetime import datetime, timezone

A='e2605841d7eb21c7d8ecbc07aa55ebe6c76f05b7'
L='2f6ca9f728c79e3dce51d8f459f927e9e823d87e'
O='d495ab0ed10ad46135febbd5bab27ea9f11bc5ee'
R='5837494b6c153bd818659419755f1b2450f540f5'
PY='/workspaces/mythos-base-v01-cpu312/bin/python'
STAGE=Path('/workspaces/mythos-base-v01-rope-diag-v11/research/mini_mythos/base_v01/decode_control_v1')
PINS={'mythos_launch.py':(4374,'8083b948eebdf08c2d14a79d940ccead72db5f10c6bac8d9061816b6c9ea05c3'),
      'resource_observer.py':(7019,'77a053266449fa82ab9fe287a8f145bd9a3118c322b106783f209c03a874824b'),
      'strace':(2087432,'28f957c227012de0b18d1bd7fff2d396cb693ea60ed8013be68de071e84b5001')}

def read(p):
    if p.is_symlink(): raise ValueError('Symlink evidence: '+str(p))
    return json.loads(p.read_text(encoding='utf-8'))

def digest(p):
    if p.is_symlink(): raise ValueError('Symlink evidence: '+str(p))
    before=p.stat(); h=hashlib.sha256(); size=0
    with p.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''): h.update(block); size+=len(block)
    after=p.stat()
    if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns) or size!=after.st_size:
        raise RuntimeError('File changed during audit: '+str(p))
    return {'size':size,'sha256':h.hexdigest()}

def tree(root,exclude=None):
    out={}
    for p in sorted(root.rglob('*')):
        if p.is_symlink(): raise ValueError('Symlink evidence: '+str(p))
        if p.is_file() and p!=exclude: out[p.relative_to(root).as_posix()]=digest(p)
    return out

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('run','operator','record','output'): parser.add_argument('--'+key,required=True,type=Path)
    args=parser.parse_args()
    run,op,record,out=(getattr(args,k).resolve() for k in ('run','operator','record','output'))
    q=read(record)
    if out.exists() or out.is_relative_to(run) or any(out.is_relative_to(Path(p).resolve()) for p in q['preserve_directories']):
        raise ValueError('Output must be new and outside every protected run')
    failures=[]; blockers=[]; checks=[]; actual={'formal_status':'UNAVAILABLE','historical_signal_cause':'UNRESOLVED'}
    def check(ok,reason,detail=None):
        checks.append({'Purpose':reason,'Status':'PASS' if ok else 'FAIL','Actual':detail})
        if not ok: failures.append({'reason':reason,'actual':detail})
    try:
        check(q['diagnostic_implementation_A']==A and q['launcher_commit_L']==L and q['observer_commit_O']==O and q['new_attempts_authorized']==1,'Registered A/L/O and attempt count')
        check(q['run_id']==run.name==op.name and q['operator_dir']==str(op),'Registered run/operator paths')
        command=['/usr/bin/strace','-D','-f','-ttt','-e','trace=none','-e','signal=SIGTERM,SIGINT,SIGHUP','-o',str(op/'signals.log'),'--',PY,'-B',str(STAGE/'run_decode_control.py'),'--execute','--implementation-commit',A,'--run-id',run.name]
        cfg=read(op/'config.json')
        check(q['command']==command and q['python']==PY and q['timeout_seconds']==6000 and cfg=={k:q[k] for k in ('command','cwd','timeout_seconds')},'Exact wrapper and unchanged coordinator command')
        for name in ('mythos_launch.py','resource_observer.py'):
            source=(STAGE/'launch_recovery_v1'/name) if name=='mythos_launch.py' else record.parent/name
            size,sha=PINS[name]; check(digest(op/name)==digest(source)=={'size':size,'sha256':sha},'Exact helper source/copy: '+name)
        size,sha=PINS['strace']; check(digest(Path('/usr/bin/strace'))==q['strace_binary']=={'size':size,'sha256':sha},'Pinned tracing tool')
        launch=read(op/'launch_observation.json'); claim=read(op/'claim.json'); done=read(op/'completion.json')
        check((launch['diagnostic_A'],launch['launcher_L'],launch['observer_O'],launch['execution_head'])==(A,L,O,R),'Launch A/L/O/R identities')
        check(claim['pid']==launch['pid'] and claim['source_sha256']==PINS['mythos_launch.py'][1] and claim['config']==cfg and claim['python']==PY and claim['isolated']==1 and claim['numerical_libraries_imported'] is False,'Launcher claim')
        summary=read(run/'public/summary.json'); coord=read(run/'private/CLAIM.json')
        wp=run/'first/public/summary.json'; worker=read(wp) if wp.exists() else {}
        status=summary['engineering_status']; actual.update(formal_status=status,formal_gates=summary['gates'],launcher_completion=done,worker_stop=worker.get('stop'))
        check(status in ('PASS','FAIL','BLOCKED') and summary['implementation_commit']==A and summary['execution_head']==R and summary['branch']=='mythos-base-v01-decode-control-v1' and summary['run_id']==run.name,'Formal identity and status')
        rc=0 if status=='PASS' else 2; ls='COMPLETED' if status=='PASS' else 'CHILD_FAILED'
        if done.get('status')=='BLOCKED':
            check(status=='BLOCKED','Launcher interruption and formal outcome agree'); blockers.append({'reason':'Launcher cleanup/interruption requires retained-detail inspection'})
        else: check(done.get('status')==ls and done.get('returncode')==rc and 'cleanup' not in done and 'exception' not in done,'Launcher agrees with legitimate formal PASS/FAIL/BLOCKED')
        check(coord['run_id']==run.name,'Coordinator claim')
        if worker: check(worker['ppid']==coord['pid'] and worker['implementation_commit']==A and summary.get('workers',{}).get('first')==worker,'Worker parent and copied summary')
        check((summary.get('stop_reason') is None) if status=='PASS' else bool(summary.get('stop_reason')),'Formal stop record agrees with outcome')
        obdone=read(op/'observer_completion.json'); oblaunch=read(op/'observer_launch.json')
        rows=[json.loads(line) for line in (op/'resource_samples.jsonl').read_text(encoding='utf-8').splitlines()]
        check(bool(rows) and len(rows)==obdone['samples'] and obdone['reason']=='launcher_completed' and obdone['signals_sent']==0 and obdone['model_artifacts_opened'] is False and not obdone['numerical_imports'],'Passive observer completion and actual row count')
        check(all((op/name).read_bytes()==b'' for name in ('observer.stdout','observer.stderr')),'Empty observer console')
        check(all(row['observer_pid']==oblaunch['pid'] for row in rows),'Observer PID')
        check(all(a['monotonic']<b['monotonic'] for a,b in zip(rows,rows[1:])),'Increasing observation clock')
        pins={launch['pid']:{'starttime':str(launch['pid_starttime']),'ppid':None},coord['pid']:{'starttime':None,'ppid':launch['pid']}}
        if worker: pins[worker['pid']]={'starttime':None,'ppid':coord['pid']}
        coverage={pid:{'owned_samples':0,'cgroup_samples':0} for pid in pins}; identity_ok=True; term_unblocked=True
        for row in rows:
            for item in row.get('owned_processes',[]):
                pid=item.get('pid'); raw=item.get('stat')
                if pid not in pins or not isinstance(raw,str): continue
                f=raw.rsplit(')',1)[1].split(); pin=pins[pid]
                if pin['starttime'] is None: pin['starttime']=f[19]
                identity_ok &= (pin['starttime']==f[19] and (pin['ppid'] is None or int(f[1])==pin['ppid']))
                blocked=item.get('status',{}).get('SigBlk'); term_unblocked &= isinstance(blocked,str) and not bool(int(blocked,16)&(1<<14))
                coverage[pid]['owned_samples']+=1
                for line in item.get('cgroup','').splitlines() if isinstance(item.get('cgroup'),str) else []:
                    if line.startswith('0::'):
                        path=str((Path('/sys/fs/cgroup')/line[3:].lstrip('/')).resolve()); mem=row.get('cgroup_memory',{}).get(path,{})
                        if isinstance(mem.get('memory.current'),str) and mem['memory.current'].strip().isdigit(): coverage[pid]['cgroup_samples']+=1
        check(identity_ok,'Observed PID/starttime/parent identities'); check(term_unblocked,'Observed owned-process SIGTERM unblocked')
        if any(not v['owned_samples'] or not v['cgroup_samples'] for v in coverage.values()): blockers.append({'reason':'Owned process or actual cgroup not captured','coverage':coverage})
        actual['observer']={'rows':len(rows),'coverage':coverage,'identity_pins':pins,'explicit_limits':[{'sample':i,'launch_pending':row.get('launch_record_pending'),'identity_mismatches':row.get('identity_mismatches',[])} for i,row in enumerate(rows) if row.get('launch_record_pending') or row.get('identity_mismatches')]}
        text=(op/'signals.log').read_text(encoding='utf-8'); signals=[]; unparsed=[]
        for line in text.splitlines():
            if '--- SIG' not in line: continue
            m=re.match(r'^\s*(\d+)\s+(\d+(?:\.\d+)?)\s+--- (SIG\w+) \{([^}]*)\} ---',line)
            if m: signals.append({'receiver_pid':int(m[1]),'timestamp':m[2],'signal':m[3],'siginfo':dict(re.findall(r'(si_\w+)=([A-Za-z0-9_+-]+)',m[4])),'raw':line})
            else: unparsed.append(line)
        actual['signals']=signals; actual['unparsed_signal_records']=unparsed
        if unparsed: blockers.append({'reason':'Unparsed signal records','records':unparsed})
        combined=''.join(row.get('trace_new','') for row in rows); check(all(x['raw'] in combined for x in signals),'Observer retained every signal record')
        exits={int(pid):int(code) for pid,code in re.findall(r'(?m)^\s*(\d+)\s+\d+(?:\.\d+)?\s+\+\+\+ exited with (\d+) \+\+\+',text)}
        expected={coord['pid']:done.get('returncode')}
        if worker: expected[worker['pid']]=0 if worker.get('status')=='PASS' else 2
        check(all(exits.get(pid)==code for pid,code in expected.items()),'Coordinator/worker trace exits agree',{'expected':expected,'actual':{p:exits.get(p) for p in expected}})
        actual['trace_exits']={pid:exits.get(pid) for pid in expected}
        if status=='PASS': check(not [x for x in signals if x['receiver_pid'] in expected],'Formal PASS has no selected signal to coordinator/worker')
        actual['signal_limit']='Original siginfo describes its recorded event only. Post-hoc sender /proc data can be absent or reused. No historical cause is inferred from either presence or absence of a signal.'
        before=read(op/'prior_attempts_before.json'); check(set(before)==set(q['preserve_directories']),'Registered prior-attempt directories')
        prior={}
        for name,expected_files in before.items():
            now=tree(Path(name)); same=now==expected_files; check(same,'Prior-attempt bytes and membership unchanged',name)
            prior[name]={'files':len(now),'unchanged':same,'added':sorted(set(now)-set(expected_files)),'removed':sorted(set(expected_files)-set(now)),'changed':sorted(k for k in set(now)&set(expected_files) if now[k]!=expected_files[k])}
        actual['prior_preservation']=prior
        live=[]
        for pid,pin in pins.items():
            try: f=(Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()
            except FileNotFoundError: continue
            if pin['starttime']==f[19] and f[0] not in ('Z','X'): live.append(pid)
        check(not live,'Owned launcher/coordinator/worker finished before snapshot',live)
        snapshot=tree(op,out); check(tree(op,out)==snapshot,'Operator snapshot remained byte/member stable')
        actual['operator_manifest']=[{'path':name,**value} for name,value in snapshot.items()]
    except Exception as exc: blockers.append({'type':type(exc).__name__,'error':str(exc)})
    integrity='FAIL' if failures else 'BLOCKED' if blockers else 'PASS'
    result={'Purpose':'Read-only post-stop audit of external observation and prior evidence preservation',
            'Environment':{'python':sys.version,'libraries':'stdlib only','model_execution':False},
            'Input':{'run':str(run),'operator':str(op),'record':str(record),'audit_source':digest(Path(__file__).resolve())},
            'Expected':'Fixed identities, consistent terminal/signal/resource records and unchanged prior attempts',
            'Actual':actual,'Status':integrity,'external_integrity_status':integrity,'full_run_accepted_by_this_audit':False,
            'checks':checks,'failures':failures,'blockers':blockers,'utc':datetime.now(timezone.utc).isoformat(),
            'operator_manifest_excluded':[str(out)],
            'limitations':['External integrity PASS may coexist with formal FAIL/BLOCKED; the frozen numerical auditor remains separate.',
                           'No model/weight deserialization, probability recalculation or new process signal occurred.',
                           'Git identities are cross-checked from records; Git was not independently queried.',
                           'Historical SIGTERM cause remains UNRESOLVED even when this attempt has no signals.']}
    with out.open('x',encoding='utf-8',newline='\n') as stream: json.dump(result,stream,ensure_ascii=False,indent=2,allow_nan=False); stream.write('\n')
    print(json.dumps({'external_integrity_status':integrity,'formal_status':actual['formal_status'],'failures':len(failures),'blockers':len(blockers),'output':str(out)}))
    return 0 if integrity=='PASS' else 2

if __name__=='__main__': sys.exit(main())
