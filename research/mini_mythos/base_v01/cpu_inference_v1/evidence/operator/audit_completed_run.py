"""Post-stop stdlib evidence audit only; never import or execute model code."""
import collections
import hashlib
import json
from pathlib import Path
import sys

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return {'size':path.stat().st_size,'sha256':h.hexdigest()}
def equal_files(a,b):
    if a.stat().st_size!=b.stat().st_size:return False
    with a.open('rb') as x,b.open('rb') as y:
        while True:
            bx,by=x.read(1024*1024),y.read(1024*1024)
            if bx!=by:return False
            if not bx:return True
def read(p):return json.loads(p.read_text())
def main():
    root=Path(sys.argv[1]).resolve();op=Path(sys.argv[2]).resolve()
    if op.is_relative_to(root):raise ValueError('Operator output cannot be inside immutable run')
    if not (op/'completion.json').exists():raise ValueError('Cannot audit an active run')
    launch=read(op/'launch.json')
    if launch['run_id']!=root.name or launch['command'][-1]!=root.name:raise ValueError('Operator run identity differs')
    result={'Purpose':'Read-only evidence/byte audit after terminal run','Environment':'stdlib only; no torch/model imports',
            'Input':str(root),'Expected':'Complete manifests and internally consistent evidence; engineering verdict based on gates',
            'Actual':{},'Status':'NOT TESTED'}
    failures=[]
    def check(ok,why):
        if not ok:failures.append(why)
    full=read(root/'FULL_MANIFEST.json');public=read(root/'public/GIT_BUNDLE_MANIFEST.json')
    check(len({e['path'] for e in full['files']})==len(full['files']),'Duplicate full manifest paths')
    for item in full['files']:
        p=(root/item['path']).resolve();p.relative_to(root)
        check(digest(p)=={'size':item['size'],'sha256':item['sha256']},'Manifest mismatch '+item['path'])
    actual={str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}
    expected={e['path'] for e in full['files']}|set(full['excluded'])
    check(actual==expected,'Run file membership differs')
    public_expected=[e for e in full['files'] if e['class']=='public']
    check(public['files']==public_expected,'Public and full manifest differ')
    statuses=collections.Counter();check_records=0
    for p in root.rglob('*.json'):
        if p.name.startswith(('check_','worker_check_')):
            row=read(p);statuses[row['Status']]+=1;check_records+=1
    for p in root.rglob('checks.jsonl'):
        for line in p.read_text().splitlines():
            row=json.loads(line);statuses[row['Status']]+=1;check_records+=1
    summary=read(root/'public/summary.json')
    pair_count=0;probe_pairs=0;generation_count=0;trace_steps=0;state_rows=0;first_outputs=[]
    if summary['engineering_status']=='PASS':
        check(all(v=='PASS' for v in summary['gates'].values()),'PASS with incomplete gates')
        check(statuses=={'PASS':check_records},'Non-PASS check in engineering PASS')
        for worker,passes in (('first',(1,2)),('reload',(1,))):
            w=root/worker;ws=read(w/'public/summary.json')
            check(ws['status']=='PASS' and ws['official_loader_calls']==ws['official_loader_returned']==1,'Worker load counts/status '+worker)
            for phase in ('before','after'):
                state=read(w/'public'/('state_'+phase+'.json'))
                check(state['report']['status']=='PASS' and len(state['rows'])==63,'State comparison '+worker+phase)
                state_rows+=len(state['rows'])
                names=[r['name'] for r in state['rows']]
                check(len(set(names))==63 and set(names)==set(read(w/'public/normalization.json').values()),'State key coverage '+worker+phase)
                check(all(r['bytewise_equal'] and r['hash_complete'] and r['bytes_hashed']==r['expected_bytes'] for r in state['rows']),'Incomplete state bytes')
            infer=w/'inference'
            for pid in (1,4,7):
                a=infer/'private'/f'forward_{pid:02d}.bin';b=infer/'private'/f'forward_generation_{pid:02d}.bin'
                length=len(read(infer/'public'/f'forward_{pid:02d}.json')['input_ids'])
                check(a.stat().st_size==b.stat().st_size==length*32768*4,'Full probe byte coverage '+worker+str(pid))
                check(equal_files(a,b),'Native/generation raw bytes '+worker+str(pid));probe_pairs+=1
                if worker=='reload':
                    check(equal_files(a,root/'first/inference/private'/a.name),'Reload full probe bytes '+str(pid));probe_pairs+=1
            for passno in passes:
                for pid in range(1,13):
                    stem=f'pass{passno}_prompt{pid:02d}'
                    gen=read(infer/'public'/(stem+'_generation.json'));q=gen['quality'];generation_count+=1
                    check(len(q['raw_new_ids'])==64 and len(q['full_generated_ids'])==len(q['input_ids'])+64,'Generation length '+worker+stem)
                    check(q['full_generated_ids'][:len(q['input_ids'])]==q['input_ids'],'Prompt prefix '+worker+stem)
                    raw=q['full_generated_ids'][len(q['input_ids']):]
                    check(q['raw_new_ids']==raw,'Raw suffix '+worker+stem)
                    eos=raw.index(1) if 1 in raw else None
                    effective=raw[:eos] if eos is not None else raw
                    check(q['eos_position']==eos and q['continuation_ids']==effective,'EOS slicing '+worker+stem)
                    grams=collections.Counter(tuple(effective[i:i+4]) for i in range(max(0,len(effective)-3)))
                    longest=0;runlen=0;previous=None
                    for token in effective:
                        runlen=runlen+1 if token==previous else 1;previous=token;longest=max(longest,runlen)
                    rules={'min_16_new_tokens':len(effective)>=16,'no_4gram_3x':max(grams.values(),default=0)<3,
                           'no_token_run_6':longest<6,'decodes_without_error':q['auto']['decode_error'] is None,
                           'no_u_fffd':q['text_continuation'] is not None and '\ufffd' not in q['text_continuation']}
                    check(q['auto']['rules']==rules and q['auto']['passed']==all(rules.values()),'Automatic screen arithmetic '+worker+stem)
                    check(all(type(i)==int and 0<=i<32768 for i in q['full_generated_ids']),'Token range '+worker+stem)
                    trace=[json.loads(s) for s in (infer/'public'/(stem+'_trace.jsonl')).read_text().splitlines()]
                    check([r['step'] for r in trace]==list(range(64)),'Trace coverage '+worker+stem);trace_steps+=len(trace)
                    check(all(r['all_logits_finite'] and r['full_logits_shape']==[1,len(q['input_ids'])+i,32768] for i,r in enumerate(trace)),'Trace logits metadata '+worker+stem)
                    if worker=='first' and passno==1:first_outputs.append(q)
                    else:
                        baseline=root/'first/inference';basegen=read(baseline/'public'/f'pass1_prompt{pid:02d}_generation.json')
                        check(q==basegen['quality'],'Complete generation repeated '+worker+stem)
                        bt=[json.loads(s) for s in (baseline/'public'/f'pass1_prompt{pid:02d}_trace.jsonl').read_text().splitlines()]
                        for i,row in enumerate(trace):
                            check(row['full_logits']==bt[i]['full_logits'],'Full-logit hash repeat '+worker+stem+str(i))
                            a=infer/'private'/f'{stem}_step{i:02d}_last.bin';b=baseline/'private'/f'pass1_prompt{pid:02d}_step{i:02d}_last.bin'
                            check(a.stat().st_size==32768*4 and equal_files(a,b),'Last logits raw repeat '+worker+stem+str(i));pair_count+=1
        check((generation_count,trace_steps,pair_count,probe_pairs,state_rows)==(36,2304,1536,9,252),'Final coverage counts')
    result['Actual']={'engineering_status':summary['engineering_status'],'gates':summary['gates'],
                      'manifest_files_verified':len(full['files']),'actual_run_files':len(actual),'public_files_listed':len(public['files']),
                      'checks':check_records,'check_statuses':dict(statuses),'generation_rows':generation_count,'observed_steps':trace_steps,
                      'raw_last_logit_pairs_rechecked':pair_count,'raw_full_probe_pairs_rechecked':probe_pairs,'state_rows':state_rows,
                      'failures':failures,'full_manifest':digest(root/'FULL_MANIFEST.json'),
                      'public_manifest':digest(root/'public/GIT_BUNDLE_MANIFEST.json'),'summary':digest(root/'public/summary.json')}
    result['Status']='PASS' if not failures else 'FAIL'
    with (op/'read_only_audit.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print('FINAL_AUDIT_BEGIN');print(json.dumps({'audit':result,'summary':{k:v for k,v in summary.items() if k!='workers'},'first_outputs':first_outputs},ensure_ascii=False));print('FINAL_AUDIT_END')
if __name__=='__main__':
    try:main()
    except Exception as exc:
        import traceback
        error={'Status':'BLOCKED','Purpose':'Post-run evidence audit','Actual':{'error':repr(exc),'traceback':traceback.format_exc()}}
        root=Path(sys.argv[1]).resolve();op=Path(sys.argv[2]).resolve()
        if not op.is_relative_to(root):
            try:
                with (op/'audit_exception.json').open('x') as f:json.dump(error,f,indent=2)
            except Exception:pass
        print(json.dumps(error));sys.exit(2)
