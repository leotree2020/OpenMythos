#!/usr/bin/env python3
"""D1 bounded CPU prepare/train/profile. Frozen native sources remain read-only."""
from __future__ import annotations
import argparse
import copy
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

os.environ['CUDA_VISIBLE_DEVICES']=''
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'c_confirm'))
import c1_runtime as R
from measurements import ARMS,SEEDS,STEPS,BATCH,POINTS,EXPERIMENT
import measurements as M
ab=R.ab
require=ab.require
INHERITED={**R.P.INHERITED,
 'c_confirm/c1_runtime.py':'5da2a4102d6154894ce0ba03c6fa0463e086cb9be236e3aa01772fc1e1797158',
 'c_confirm/c1_policy.py':'44e4b4cf4ca755a262290846dd0539c902eb07f6847f0aa63bfce29c7555298c'}


def sha(raw): return hashlib.sha256(raw).hexdigest()
def object_sha(obj): return sha(json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False).encode())

def parse(raw):
    def pairs(items):
        d={}
        for k,v in items:
            require(k not in d,'duplicate JSON key');d[k]=v
        return d
    def bad(x): raise ValueError('nonfinite JSON: '+x)
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=bad)

def read(path): return parse(Path(path).read_bytes())

def identity():
    own={p.name:ab.file_sha(p) for p in HERE.iterdir() if p.suffix in ('.py','.sh') or p.name=='PROTOCOL.md'}
    inherited={p:ab.file_sha(HERE.parent/p) for p in INHERITED}
    require(inherited==INHERITED,'inherited source drift')
    return dict(own=own,inherited=inherited,sha256=object_sha(dict(own=own,inherited=inherited)))

def context(upstream):
    torch,env=ab.runtime()
    root=Path(ab.git(HERE,'rev-parse','--show-toplevel'))
    require(not ab.git(root,'status','--porcelain','--untracked-files=no'),'dirty research source')
    ident=identity()
    m2=ab.load_module('d1_native_factory',HERE.parent/'m2_matched/experiment.py');m2.setup(upstream)
    task=ab.load_module('d1_task',HERE.parent/'r1b_calibration/task.py')
    return torch,env,root,m2,task,ident

def wrap(base,arm,seed):
    if arm=='GPT': return R.wrap(base,'GPT',seed)
    from dual_state import DualState
    return DualState(base,arm)


def native_check(base,seed,torch,m2):
    from dual_state import independent_reference
    from torch.nn.attention import SDPBackend,sdpa_kernel
    original=m2.weights_sha(base); cases=[]
    with torch.random.fork_rng(devices=[]),sdpa_kernel(SDPBackend.MATH):
        for length in (6,9):
            x=torch.arange(2*length).reshape(2,length)%10;y=(x+1)%10;y[:,:5]=-100
            for depth in (2,4):
                for arm in ('P4','D0','D1'):
                    ref=copy.deepcopy(base).train(); model=wrap(copy.deepcopy(base),arm,seed).train()
                    require(sum(p.numel() for p in model.parameters())==sum(p.numel() for p in ref.parameters()),'added parameters')
                    torch.manual_seed(9001)
                    a=(ref(x,labels=y,return_logits=True,num_steps_pair=[0,depth]) if arm=='P4'
                       else independent_reference(ref,x,y,depth,arm))
                    a['loss'].backward();ra=torch.get_rng_state().clone()
                    torch.manual_seed(9001);b=model(x,y,depth=depth,trace=True)
                    b['loss'].backward();rb=torch.get_rng_state().clone()
                    torch.testing.assert_close(a['logits'],b['logits'],rtol=1e-5,atol=1e-6)
                    torch.testing.assert_close(a['loss'],b['loss'],rtol=1e-5,atol=1e-6)
                    require(torch.equal(ra,rb),'reference RNG differs')
                    error=0.
                    for (n,p),(n2,q) in zip(ref.named_parameters(),model.base.named_parameters()):
                        require(n==n2 and (p.grad is None)==(q.grad is None),'gradient route differs')
                        if p.grad is not None:
                            torch.testing.assert_close(p.grad,q.grad,rtol=1e-5,atol=1e-6)
                            error=max(error,float((p.grad-q.grad).abs().max()))
                    require(not model.base.transformer.adapter._forward_pre_hooks and not model.base.transformer.core_block[-1]._forward_hooks,'leaked hooks')
                    model.eval()
                    with torch.no_grad():
                        torch.manual_seed(9002);la=model(x,depth=depth)['logits']
                        xx=x.clone();xx[:,3:]=(xx[:,3:]+3)%10
                        torch.manual_seed(9002);lb=model(xx,depth=depth)['logits']
                        torch.testing.assert_close(la[:,:3],lb[:,:3],rtol=1e-5,atol=1e-6)
                        if arm!='P4' and depth==4:
                            torch.manual_seed(9002);ln=model(x,depth=4,intervention='noop')['logits']
                            torch.testing.assert_close(la,ln,rtol=0,atol=0)
                    require(m2.weights_sha(model.base)==original and m2.weights_sha(ref)==original,'preflight changed weights')
                    cases.append(dict(seed=seed,arm=arm,depth=depth,length=length,status='PASS',max_gradient_error=error))
    require(m2.weights_sha(base)==original,'mutated starting model')
    return dict(status='PASS',cases=cases,scope='native/reference copies; no optimizer updates')


def setup_phase(args):
    require(not args.out.exists(),'existing preparation directory retained')
    args.out.mkdir(parents=True)
    torch,env,root,m2,task,ident=context(args.parcae_dir)
    data,manifest=ab.check_data(task); ab.write(args.out/'data.json',data)
    x,y=R.encoded(task,data['train'][:BATCH],torch)
    report=dict(experiment=EXPERIMENT,phase='prepare',status='PARTIAL',exit_code=2,
                environment=env,source_identity=ident,code_head=ab.git(root,'rev-parse','HEAD'),
                source_pin=m2.PIN,data=manifest,data_file_sha256=ab.file_sha(args.out/'data.json'),
                starts={},counts={},native_preflight=[],gpt_checks=[],review_status='PENDING Claude Code',
                training_status='NOT TESTED',quality_status='NOT TESTED',scope='old train/development only; no optimizer updates')
    for seed in SEEDS:
        report['starts'][str(seed)]={};report['counts'][str(seed)]={}
        for arm in ARMS:
            base,io,base_sha=R.initial(m2,seed,arm)
            model=wrap(base,arm,seed)
            report['starts'][str(seed)][arm]=dict(base_sha256=base_sha,full_sha256=m2.weights_sha(model),shared_io=io)
            report['counts'][str(seed)][arm]=R.probe(model,x,y,torch,m2)
            if arm=='GPT':report['gpt_checks'].append(dict(seed=seed,**R.gpt_objective_check(base,x,y,torch)))
            if arm=='P4':report['native_preflight'].append(native_check(base,seed,torch,m2))
        starts=report['starts'][str(seed)]
        require(len({starts[a]['base_sha256'] for a in ('P4','D0','D1')})==1,'unpaired native starts')
        require(len({object_sha(starts[a]['shared_io']) for a in ARMS})==1,'unpaired IO')
        print(json.dumps(dict(seed=seed,native_prepare='PASS',training='NOT TESTED')),flush=True)
    require(all(report['counts'][str(s)]==report['counts'][str(SEEDS[0])] for s in SEEDS),'seed-dependent cost')
    m2.upstream_check(args.parcae_dir); require(identity()==ident,'source drift during prepare')
    report.update(status='PASS',exit_code=0);ab.write(args.out/'prepared.json',report)
    return report


def preparation(args):
    p=read(args.out/'prepared.json')
    require(p['experiment']==EXPERIMENT and p['status']=='PASS','preparation not accepted')
    require(identity()==p['source_identity'],'source/protocol changed since prepare')
    require(ab.git(HERE,'rev-parse','HEAD')==p['code_head'],'use the prepared execution commit')
    return p


def data_bytes(args,p):
    raw=(args.out/'data.json').read_bytes()
    require(sha(raw)==p['data_file_sha256'],'data bytes changed')
    return parse(raw)  # parse THE SAME bytes just checked


def train_one(args,p):
    from torch.nn.attention import SDPBackend,sdpa_kernel
    torch,env,root,m2,task,ident=context(args.parcae_dir)
    require(ident==p['source_identity'],'worker source differs')
    job=args.out/'jobs'/f'{args.arm}_{args.seed}'
    data=data_bytes(args,p);x,y=R.encoded(task,data['train'],torch)
    base,io,bs=R.initial(m2,args.seed,args.arm);model=wrap(base,args.arm,args.seed)
    full=m2.weights_sha(model); start=p['starts'][str(args.seed)][args.arm]
    require((bs,full,io)==(start['base_sha256'],start['full_sha256'],start['shared_io']),'initial state drift')
    indices=torch.randint(len(x),(STEPS,BATCH),generator=torch.Generator().manual_seed(args.seed+12000))
    opt=torch.optim.AdamW(model.parameters(),lr=.002,betas=(.9,.999),eps=1e-8,weight_decay=0.)
    row=dict(arm=args.arm,seed=args.seed,status='PARTIAL',steps=0,planned_steps=STEPS,
             environment=env,source_identity=ident['sha256'],initial_model_sha256=bs,
             initial_full_state_sha256=full,shared_io=io,batch_indices_sha256=m2.tensor_sha(indices),
             counted_training_flops=p['counts'][str(args.seed)][args.arm]['step_flops']*STEPS,
             problem_exposures=STEPS*BATCH,supervised_target_tokens=STEPS*BATCH*4,
             loss_trace=[],gradient_norm_trace=[],rng_trace=[],snapshots={})
    ab.write(job/'row.json',row);t=time.perf_counter()
    with torch.random.fork_rng(devices=[]),sdpa_kernel(SDPBackend.MATH):
        torch.manual_seed(args.seed+2000)
        for step,ix in enumerate(indices,1):
            model.train();opt.zero_grad(set_to_none=True)
            row['rng_trace'].append(m2.tensor_sha(torch.get_rng_state()))
            out=model(x[ix],y[ix],depth=4)
            R.numeric(bool(torch.isfinite(out['loss'])),'nonfinite loss');out['loss'].backward()
            R.numeric(all(bool(torch.isfinite(q.grad).all()) for q in model.parameters() if q.grad is not None),'nonfinite gradients')
            norm=float(torch.nn.utils.clip_grad_norm_(model.parameters(),1.));R.numeric(math.isfinite(norm),'nonfinite norm')
            opt.step();row['steps']=step
            row['loss_trace'].append(float(out['loss'].detach()));row['gradient_norm_trace'].append(norm)
            if step in POINTS:
                meta=dict(arm=args.arm,seed=args.seed,step=step,source_identity=ident['sha256'],
                          data_file_sha256=p['data_file_sha256'],initial_full_sha256=full)
                snap=R.state(job/f'step{step}.pt',model,opt,torch.get_rng_state().clone(),indices,meta,torch,m2)
                snap['file']=str((job/snap['file']).relative_to(args.out));row['snapshots'][str(step)]=snap
                ab.write(job/'row.json',row)
                print(json.dumps(dict(arm=args.arm,seed=args.seed,step=step,training='PARTIAL')),flush=True)
    row.update(status='PASS',final_model_sha256=m2.weights_sha(model),final_base_sha256=m2.weights_sha(base),
               training_seconds_descriptive=time.perf_counter()-t,
               process_high_water_rss_kib=__import__('resource').getrusage(__import__('resource').RUSAGE_SELF).ru_maxrss)
    m2.upstream_check(args.parcae_dir);require(identity()==ident,'source changed');ab.write(job/'row.json',row)
    return row


def verify_training(args,p,t):
    require(t['experiment']==EXPERIMENT and t['phase']=='train' and t['status']=='PASS','training incomplete')
    expected={(a,s) for a in ARMS for s in SEEDS}; seen=set()
    for r in t['rows']:
        key=(r['arm'],r['seed']);require(key in expected and key not in seen,'unknown/duplicate job');seen.add(key)
        require(r['status']=='PASS' and r['steps']==STEPS and r['source_identity']==p['source_identity']['sha256'],'incomplete/source drift')
        require(read(args.out/'jobs'/f'{key[0]}_{key[1]}'/'row.json')==r,'job row drift')
        require(set(r['snapshots'])==set(map(str,POINTS)),'snapshot steps')
        for point,snap in r['snapshots'].items():
            path=(args.out/snap['file']).resolve()
            require(path.is_relative_to(args.out) and path.name==f'step{point}.pt','snapshot path')
            require(ab.file_sha(path)==snap['sha256'],'snapshot bytes drift')
    require(seen==expected,'missing jobs')
    for seed in SEEDS:
        rr={r['arm']:r for r in t['rows'] if r['seed']==seed}
        require(len({r['batch_indices_sha256'] for r in rr.values()})==1,'data index mismatch')
        require(rr['P4']['rng_trace']==rr['D0']['rng_trace']==rr['D1']['rng_trace'],'Parcae RNG mismatch')
        require(len({rr[a]['initial_model_sha256'] for a in ('P4','D0','D1')})==1,'base start mismatch')


def gradient_coverage(model,x,y,seed,torch):
    from torch.nn.attention import SDPBackend,sdpa_kernel
    model.train();model.zero_grad(set_to_none=True)
    with torch.random.fork_rng(devices=[]),sdpa_kernel(SDPBackend.MATH):
        torch.manual_seed(seed+93000);out=model(x,y,depth=4);out['loss'].backward()
    none=[];present=nonzero=0
    for n,q in model.named_parameters():
        if q.grad is None:none.append(n)
        else:
            R.numeric(bool(torch.isfinite(q.grad).all()),'nonfinite diagnostic gradient')
            present+=q.numel();nonzero+=int((q.grad!=0).sum())
    model.zero_grad(set_to_none=True)
    return dict(registered=sum(q.numel() for q in model.parameters()),present=present,
                nonzero_elements=nonzero,none_names=none,scope='one synthetic batch; no optimizer update')


def evaluate_one(args,p,row):
    torch,env,root,m2,task,ident=context(args.parcae_dir)
    require(ident==p['source_identity'],'worker source differs')
    data=data_bytes(args,p);truth=data['development'];probes=M.probe_rows(truth)
    base,_,_=R.initial(m2,args.seed,args.arm);model=wrap(base,args.arm,args.seed)
    profiles=[];final=[]
    for step in POINTS:
        snap=row['snapshots'][str(step)];path=(args.out/snap['file']).resolve()
        require(path.is_relative_to(args.out) and ab.file_sha(path)==snap['sha256'],'snapshot file identity')
        saved=torch.load(path,map_location='cpu',weights_only=True)
        expected=dict(arm=args.arm,seed=args.seed,step=step,source_identity=ident['sha256'],
                      data_file_sha256=p['data_file_sha256'],initial_full_sha256=row['initial_full_state_sha256'])
        require(saved['metadata']==expected,'wrong snapshot metadata')
        model.load_state_dict(saved['model'],strict=True)
        require(m2.weights_sha(model)==snap['model_sha256'],'weight identity')
        prof=dict(step=step,probe_generation=ab.evaluate(model,probes,args.seed,4,torch,task))
        if args.arm!='GPT':prof['latent_profile']=M.state_profile(model,[r['prompt'] for r in probes],args.seed,torch)
        profiles.append(prof)
        if step==STEPS:
            for depth in ((4,) if args.arm=='GPT' else (2,4)):
                val=ab.evaluate(model,truth,args.seed,depth,torch,task)
                require(val['metrics']==task.score(truth,val['predictions']),'saved answer/score mismatch')
                val.update(arm=args.arm,seed=args.seed,step=step,depth=depth,checkpoint_sha256=snap['sha256'])
                final.append(val)
        require(m2.weights_sha(model)==snap['model_sha256'],'profiling changed weights')
    extra={}
    if args.arm!='GPT':extra['transitions']=M.transitions(truth,final[0]['predictions'],final[1]['predictions'])
    if args.arm in ('D0','D1'):extra['sensitivity']=M.sensitivity(model,[r['prompt'] for r in probes],args.seed,torch)
    x=torch.arange(2*9).reshape(2,9)%10;y=(x+1)%10;y[:,:5]=-100
    extra['gradient_probe']=gradient_coverage(model,x,y,args.seed,torch)
    require(m2.weights_sha(model)==row['final_model_sha256'],'diagnostic changed weights')
    m2.upstream_check(args.parcae_dir);require(identity()==ident,'source changed')
    return dict(arm=args.arm,seed=args.seed,status='PASS',profiles=profiles,final=final,diagnostics=extra,
                profile_keys=[r['key'] for r in probes],scope='viewed development only; no new heldout inference')


def dispatch(args,phase,arm,seed):
    cmd=[sys.executable,'-B',str(HERE/'run_cpu.py'),phase,'--out',str(args.out),
         '--parcae-dir',str(args.parcae_dir),'--worker','--arm',arm,'--seed',str(seed)]
    # Worker owns an exclusive directory; stdout goes to parent phase console log.
    return subprocess.run(cmd,check=False).returncode


def train_phase(args):
    p=preparation(args)
    require(args.review_approved and args.reviewer and args.review_report and args.review_report.is_file(),
            'actual Claude report and owner --review-approved acknowledgement required')
    require(not any((args.out/n).exists() for n in ('train.started','jobs','training.json','review.md','result.json')),'existing training/partial evidence retained')
    (args.out/'train.started').touch(exist_ok=False)
    raw=args.review_report.read_bytes();require(raw.strip(),'empty review report')
    (args.out/'review.md').write_bytes(raw)
    t=dict(experiment=EXPERIMENT,phase='train',status='PARTIAL',exit_code=2,rows=[],
           review=dict(reviewer_as_supplied=args.reviewer,report_sha256=sha(raw),owner_acknowledged_approval=True,
                       scope='owner-supplied report; no cryptographic author authentication'),
           quality_status='NOT TESTED',scope='no development scoring during training')
    ab.write(args.out/'training.json',t)
    for seed in SEEDS:
        for arm in ARMS:
            rc=dispatch(args,'train',arm,seed)
            path=args.out/'jobs'/f'{arm}_{seed}'/'row.json'
            if path.exists():t['rows'].append(read(path))
            ab.write(args.out/'training.json',t)
            require(rc==0,'worker stopped; partial evidence retained; no automatic retry')
    t.update(status='PASS',exit_code=0);verify_training(args,p,t);ab.write(args.out/'training.json',t)
    return t


def eval_phase(args):
    p=preparation(args);t=read(args.out/'training.json');verify_training(args,p,t)
    require(not any((args.out/n).exists() for n in ('evaluate.started','evaluations','result.json')),'existing evaluation/partial evidence retained')
    (args.out/'evaluate.started').touch(exist_ok=False)
    report=dict(experiment=EXPERIMENT,phase='evaluate',status='PARTIAL',exit_code=2,rows=[],
                source_identity=p['source_identity'],code_head=p['code_head'],environment=p['environment'],
                data=p['data'],counts=p['counts'],training_summary_sha256=ab.file_sha(args.out/'training.json'),
                training_rows=t['rows'],review=t['review'],measurement_scope='viewed development,not independent confirmation')
    ab.write(args.out/'result.json',report)
    for seed in SEEDS:
        for arm in ARMS:
            rc=dispatch(args,'evaluate',arm,seed)
            path=args.out/'evaluations'/f'{arm}_{seed}'/'row.json'
            if path.exists():report['rows'].append(read(path))
            ab.write(args.out/'result.json',report)
            require(rc==0,'evaluation stopped; partial evidence retained')
    final=[r for job in report['rows'] for r in job['final']]
    report['outcome']=M.summarize(final)
    require(ab.file_sha(args.out/'data.json')==p['data_file_sha256'],'data changed during evaluation')
    report.update(status='PASS',execution_status='PASS',exit_code=0,
                  post_result_review_status='NOT TESTED; Claude Code review pending',
                  formal_oracle='BLOCKED/NOT_READY; FORMAL_ACCEPTANCE_READY=False')
    ab.write(args.out/'result.json',report);return report


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('phase',choices=('prepare','train','evaluate'))
    parser.add_argument('--out',type=Path,required=True);parser.add_argument('--parcae-dir',type=Path,required=True)
    parser.add_argument('--worker',action='store_true');parser.add_argument('--arm',choices=ARMS)
    parser.add_argument('--seed',type=int,choices=SEEDS)
    parser.add_argument('--review-report',type=Path);parser.add_argument('--reviewer')
    parser.add_argument('--review-approved',action='store_true')
    args=parser.parse_args();args.out=args.out.resolve();owned=False;job=None
    name={'prepare':'prepared.json','train':'training.json','evaluate':'result.json'}[args.phase]
    try:
        if args.worker:
            require(args.phase!='prepare' and args.arm is not None and args.seed is not None,'invalid worker')
            p=preparation(args)
            parent=read(args.out/('training.json' if args.phase=='train' else 'result.json'))
            require(parent['phase']==args.phase and parent['status']=='PARTIAL','worker requires active parent phase')
            folder='jobs' if args.phase=='train' else 'evaluations'
            (args.out/folder).mkdir(exist_ok=True)
            job=args.out/folder/f'{args.arm}_{args.seed}';job.mkdir(exist_ok=False);owned=True
            if args.phase=='train':result=train_one(args,p)
            else:
                t=read(args.out/'training.json');verify_training(args,p,t)
                row=next(r for r in t['rows'] if (r['arm'],r['seed'])==(args.arm,args.seed))
                result=evaluate_one(args,p,row)
            ab.write(job/'row.json',result);return 0
        require(not (args.out/name).exists(),'existing phase evidence retained; do not rerun')
        if args.phase=='prepare':
            require(not args.out.exists(),'partial output retained')
            owned=True;result=setup_phase(args)
        else:
            preparation(args)
            # Precheck ownership before writing phase summaries/error state.
            names=('train.started','jobs','review.md','training.json','result.json') if args.phase=='train' else ('evaluate.started','evaluations','result.json')
            require(not any((args.out/n).exists() for n in names),'existing or partial phase retained')
            if args.phase=='train':
                require(args.review_approved and args.reviewer and args.review_report and args.review_report.is_file(),'actual review/ack required')
                require(args.review_report.read_bytes().strip(),'empty review')
                owned=True;result=train_phase(args)
            else:
                verify_training(args,read(args.out/'prepared.json'),read(args.out/'training.json'))
                owned=True;result=eval_phase(args)
        print(json.dumps({k:result[k] for k in ('experiment','phase','status','outcome','exit_code') if k in result},ensure_ascii=False),flush=True)
        print(ab.file_sha(args.out/name),str(args.out/name));return result['exit_code']
    except Exception as error:
        traceback.print_exc()
        if owned:
            status='FAIL' if isinstance(error,R.NumericalFailure) else 'BLOCKED';rc=1 if status=='FAIL' else 2
            path=job/'row.json' if job else args.out/name
            if path.parent.exists():
                previous=read(path) if path.exists() else dict(experiment=EXPERIMENT,phase=args.phase)
                previous.update(status=status,exit_code=rc,error=f'{type(error).__name__}: {error}')
                ab.write(path,previous)
                (path.parent/('error.log' if job else args.phase+'.error.log')).write_text(traceback.format_exc())
            return rc
        print('BLOCKED: existing evidence not modified');return 2

if __name__=='__main__':raise SystemExit(main())
