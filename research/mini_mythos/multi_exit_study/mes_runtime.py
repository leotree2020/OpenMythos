"""Reuse pinned native models and existing A; no replacement Transformer."""
from __future__ import annotations
import copy
import importlib.util
import json
from pathlib import Path
import sys
import time
from mes_policy import INHERITED, DEPTH, REFERENCE_STEPS, require, digest, object_sha

HERE = Path(__file__).resolve().parent
AB = HERE.parent/'mech_ab'
sys.path.insert(0, str(AB))
spec = importlib.util.spec_from_file_location('mes_existing_ab', AB/'run_cpu.py')
ab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ab)


class NumericalFailure(RuntimeError):
    """Valid model/inputs but numerical training failure: FAIL, not hidden as BLOCKED."""


def numeric(ok, message):
    if not ok:
        raise NumericalFailure(message)


def identity():
    own = {p.name: ab.file_sha(p) for p in HERE.iterdir() if p.suffix in ('.py','.sh') or p.name=='PROTOCOL.md'}
    inherited = {name: ab.file_sha(HERE.parent/name) for name in INHERITED}
    require(inherited == INHERITED, 'inherited source changed')
    return {'own':own,'inherited':inherited,'sha256':object_sha({'own':own,'inherited':inherited})}


def context(upstream):
    torch, env = ab.runtime()
    root = Path(ab.git(HERE,'rev-parse','--show-toplevel'))
    require(not ab.git(root,'status','--porcelain','--untracked-files=no'),'dirty research sources')
    ident = identity()
    m2 = ab.load_module('mes_original_factory', HERE.parent/'m2_matched/experiment.py')
    m2.setup(upstream)
    task = ab.load_module('mes_original_task', HERE.parent/'r1b_calibration/task.py')
    return torch, env, root, m2, task, ident


def initial(m2, seed, arm):
    gpt, parcae = m2.make('gpt',60,seed), m2.make('parcae',64,seed)
    io = m2.pair_io(gpt,parcae)
    base = gpt if arm=='GPT' else parcae
    return base, io, m2.weights_sha(base)


def wrap(base, arm):
    from mechanisms import Mechanism
    if arm != 'GPT':
        return Mechanism(base, auxiliary=.25 if arm=='A' else 0.)
    import torch
    class GPTPath(torch.nn.Module):
        def __init__(self):
            super().__init__(); self.base=base
        def forward(self,tokens,labels=None,depth=4):
            require(depth==4,'GPT label denotes four native blocks, not recursion')
            out=self.base(tokens,labels=labels,return_logits=True)
            return dict(logits=out['logits'],loss=out['loss'],final_loss=out['loss'],aux_loss=None)
    return GPTPath()


def probe(model,x,y,depth,torch,m2):
    from torch.nn.attention import SDPBackend,sdpa_kernel
    from torch.utils.flop_counter import FlopCounterMode
    before=m2.weights_sha(model.base); model.train(); model.zero_grad(set_to_none=True)
    with torch.random.fork_rng(devices=[]),sdpa_kernel(SDPBackend.MATH):
        torch.manual_seed(9001)
        with FlopCounterMode(display=False) as fc:
            out=model(x,y,depth=depth); forward=fc.get_total_flops()
            numeric(bool(torch.isfinite(out['loss'])),'nonfinite probe loss')
            out['loss'].backward(); total=fc.get_total_flops()
    numeric(all(bool(torch.isfinite(p.grad).all()) for p in model.parameters() if p.grad is not None),
            'nonfinite probe gradient')
    row=dict(parameters=sum(p.numel() for p in model.parameters()),
             gradient_participating_parameters_probe=sum(p.numel() for p in model.parameters() if p.grad is not None),
             forward_flops=forward,backward_flops=total-forward,step_flops=total)
    model.zero_grad(set_to_none=True)
    require(before==m2.weights_sha(model.base),'probe changed registered state')
    return row


def encoded(task,rows,torch):
    pairs=[task.training_tokens(r) for r in rows]
    return torch.tensor([p[0] for p in pairs],dtype=torch.long),torch.tensor([p[1] for p in pairs],dtype=torch.long)


def state(path,base,opt,rng,indices,metadata,torch,m2):
    require(not path.exists(),'snapshot already exists')
    payload=dict(model=base.state_dict(),optimizer=opt.state_dict(),cpu_rng=rng,
                 batch_indices=indices,metadata=metadata)
    numeric(all(bool(torch.isfinite(t).all()) for t in payload['model'].values()), 'nonfinite saved model')
    torch.save(payload,path)
    # Actual CPU safe-load consistency; NOT an interrupt-resume replay.
    loaded=torch.load(path,map_location='cpu',weights_only=True)
    require(set(loaded)==set(payload) and loaded['metadata']==metadata,'snapshot metadata reload')
    require(all(torch.equal(v,loaded['model'][k]) for k,v in payload['model'].items()),'snapshot tensor reload')
    require(torch.equal(rng,loaded['cpu_rng']) and torch.equal(indices,loaded['batch_indices']),'snapshot RNG/indices reload')
    def equal(a,b):
        if isinstance(a,torch.Tensor): return isinstance(b,torch.Tensor) and torch.equal(a,b)
        if isinstance(a,dict): return isinstance(b,dict) and a.keys()==b.keys() and all(equal(a[k],b[k]) for k in a)
        if isinstance(a,(list,tuple)): return type(a)==type(b) and len(a)==len(b) and all(equal(x,y) for x,y in zip(a,b))
        return a==b
    require(equal(payload['optimizer'],loaded['optimizer']),'optimizer safe-load differs')
    return dict(file=str(path.name),sha256=ab.file_sha(path),model_sha256=m2.weights_sha(base),
                step=metadata['step'],safe_reload_status='PASS',resume_replay_status='NOT TESTED')


def train_one(args,prepared):
    from torch.nn.attention import SDPBackend,sdpa_kernel
    torch,env,root,m2,task,ident=context(args.parcae_dir)
    require(ident==prepared['source_identity'],'source changed since prepare')
    job=args.out/'jobs'/f'{args.arm}_{args.seed}'; job.mkdir(parents=True,exist_ok=False)
    raw=(args.out/'train.json').read_bytes()
    require(digest(raw)==prepared['train_file_sha256'],'training input changed')
    data=json.loads(raw); x,y=encoded(task,data,torch)
    base,io,start=initial(m2,args.seed,args.arm); model=wrap(base,args.arm)
    require(start==prepared['starts'][str(args.seed)][args.arm]['model_sha256'],'start changed')
    allocation=prepared['budget']['arms']; steps=allocation[args.arm]['steps']
    max_steps=max(a['steps'] for a in allocation.values())
    indices=torch.randint(len(x),(max_steps,32),generator=torch.Generator().manual_seed(args.seed+12000))[:steps].clone()
    opt=torch.optim.AdamW(base.parameters(),lr=.002,betas=(.9,.999),eps=1e-8,weight_decay=0.)
    row=dict(arm=args.arm,seed=args.seed,status='PARTIAL',steps=0,planned_steps=steps,
             initial_model_sha256=start,shared_io=io,environment=env,source_identity=ident['sha256'],
             batch_prefix3000_sha256=m2.tensor_sha(indices[:REFERENCE_STEPS]),batch_indices_sha256=m2.tensor_sha(indices),
             counted_training_flops=steps*allocation[args.arm]['step_flops'],problem_exposures=steps*32,
             supervised_target_tokens=steps*32*4,input_token_positions=steps*32*9,
             loss_trace=[],final_loss_trace=[],aux_loss_trace=[],gradient_norm_trace=[],
             rng_before_forward_sha256=[],snapshots={})
    ab.write(job/'row.json',row); started=time.perf_counter(); model.train()
    with torch.random.fork_rng(devices=[]),sdpa_kernel(SDPBackend.MATH):
        torch.manual_seed(args.seed+2000)
        for step,ix in enumerate(indices,1):
            row['rng_before_forward_sha256'].append(m2.tensor_sha(torch.get_rng_state()))
            opt.zero_grad(set_to_none=True); out=model(x[ix],y[ix],depth=DEPTH[args.arm])
            numeric(bool(torch.isfinite(out['loss'])),'nonfinite training objective')
            out['loss'].backward()
            numeric(all(bool(torch.isfinite(p.grad).all()) for p in base.parameters() if p.grad is not None),'nonfinite gradient')
            norm=float(torch.nn.utils.clip_grad_norm_(base.parameters(),1.)); numeric(__import__('math').isfinite(norm),'nonfinite norm')
            opt.step(); row['steps']=step
            row['loss_trace'].append(float(out['loss'].detach()))
            row['final_loss_trace'].append(float(out['final_loss'].detach()))
            row['aux_loss_trace'].append(None if out['aux_loss'] is None else float(out['aux_loss'].detach()))
            row['gradient_norm_trace'].append(norm)
            if step in (REFERENCE_STEPS,steps):
                meta=dict(arm=args.arm,seed=args.seed,step=step,source_identity=ident['sha256'],
                          initial_sha256=start,train_sha256=prepared['train_file_sha256'])
                saved=state(job/f'step{step}.pt',base,opt,torch.get_rng_state().clone(),indices,meta,torch,m2)
                saved['file']=str((job/saved['file']).relative_to(args.out))
                row['snapshots'][str(step)]=saved
            if step%500==0:
                ab.write(job/'row.json',row)
                print(json.dumps(dict(arm=args.arm,seed=args.seed,step=step,objective=row['loss_trace'][-1])),flush=True)
    row.update(status='PASS',training_seconds_descriptive=time.perf_counter()-started,
               final_model_sha256=m2.weights_sha(base),
               process_high_water_rss_kib=__import__('resource').getrusage(__import__('resource').RUSAGE_SELF).ru_maxrss,
               rss_scope='worker lifetime incl imports; not isolated training memory')
    m2.upstream_check(args.parcae_dir); require(identity()==ident,'source changed during training')
    ab.write(job/'row.json',row)
    return row


def evaluate_one(args,prepared,row,truth):
    torch,env,root,m2,task,ident=context(args.parcae_dir)
    require(ident==prepared['source_identity'],'source changed before H1 inference')
    base,_,_=initial(m2,args.seed,args.arm); model=wrap(base,args.arm)
    points=[('final',row['steps'])]+([('step3000',REFERENCE_STEPS)] if args.arm=='P4' else [])
    result=[]
    for label,step in points:
        snap=row['snapshots'][str(step)]; path=args.out/snap['file']
        require(path.resolve().is_relative_to(args.out.resolve()) and ab.file_sha(path)==snap['sha256'],'snapshot identity')
        loaded=torch.load(path,map_location='cpu',weights_only=True)
        meta=loaded['metadata']
        require(meta==dict(arm=args.arm,seed=args.seed,step=step,source_identity=ident['sha256'],
                          initial_sha256=row['initial_model_sha256'],train_sha256=prepared['train_file_sha256']),
                'snapshot metadata identity')
        base.load_state_dict(loaded['model'],strict=True)
        require(m2.weights_sha(base)==snap['model_sha256'],'loaded model digest')
        depths=(4,) if args.arm=='GPT' else (2,) if args.arm=='P2' else (2,4)
        for d in depths:
            value=ab.evaluate(model,truth,args.seed,d,torch,task)
            value.update(arm=args.arm,seed=args.seed,checkpoint=label,step=step,depth=d,
                         scope='H1 frozen confirmation; free generation and teacher-forced CE separate')
            result.append(value)
        require(m2.weights_sha(base)==snap['model_sha256'],'evaluation mutated weights')
    m2.upstream_check(args.parcae_dir)
    return result
