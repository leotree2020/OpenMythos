#!/usr/bin/env python3
"""One bounded P4/S16/C4 CPU experiment; no upstream/old-result modifications."""
from __future__ import annotations
import argparse
import copy
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import resource
import subprocess
import sys
import time
import traceback

os.environ['CUDA_VISIBLE_DEVICES']=''
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
AB=HERE.parent/'mech_ab'
REUSED_SHA={'run_cpu.py':'fef3bcaac0b3b58f6660ba52529df85175187f5f8fa02b680b64c3d3bca15955',
 'mechanisms.py':'a7da3cafda5e0e9c45881f6ed68f1c192e78a04a41c2e89251ec255a88bb5c37',
 'metrics.py':'54249a6edce2c3dcc534b180c047a3539f358ff2f21a55a287d75fd623422c6a'}
for name,digest in REUSED_SHA.items():
    if hashlib.sha256((AB/name).read_bytes()).hexdigest()!=digest:
        raise RuntimeError('inherited helper changed: '+name)
sys.path.insert(0,str(AB))
spec=importlib.util.spec_from_file_location('mech_c_reused_ab',AB/'run_cpu.py')
common=importlib.util.module_from_spec(spec)
spec.loader.exec_module(common)
from c_metrics import ARMS,SEEDS,EXPERIMENT,summarize

require,write,file_sha,git=common.require,common.write,common.file_sha,common.git
runtime,sources,initial=common.runtime,common.sources,common.initial
STEPS,BATCH=3000,32


def no_hooks(wrapper):
    core=wrapper.base.transformer.core_block[0]
    return not core._forward_pre_hooks and not core.attn.c_proj._forward_hooks and not core.mlp.proj._forward_hooks


def native_preflight(base,seed,torch,m2):
    from c_adapters import LoopLoRA
    from torch.nn.attention import SDPBackend,sdpa_kernel
    initial_sha=m2.weights_sha(base);cases=[]
    with torch.random.fork_rng(devices=[]),sdpa_kernel(SDPBackend.MATH):
        for length in (6,9):
            x=torch.arange(2*length).reshape(2,length)%10
            y=(x+1)%10;y[:,:5]=-100
            for depth in (2,4):
                native=copy.deepcopy(base).train()
                torch.manual_seed(9001)
                ref=native(x,labels=y,return_logits=True,num_steps_pair=[0,depth])
                ref['loss'].backward();ref_rng=torch.get_rng_state().clone()
                for arm in ARMS:
                    rng=torch.get_rng_state().clone()
                    wrapper=LoopLoRA(copy.deepcopy(base),arm,seed).train()
                    require(torch.equal(rng,torch.get_rng_state()),'adapter constructor consumed caller RNG')
                    require(wrapper.added_parameters()==(0 if arm=='P4' else 2560),'unexpected added capacity')
                    torch.manual_seed(9001)
                    out=wrapper(x,y,depth,trace=True);out['loss'].backward()
                    torch.testing.assert_close(ref['logits'],out['logits'],rtol=1e-5,atol=1e-6)
                    require(abs(float((ref['loss']-out['loss']).detach()))<=1e-6,'zero-init loss mismatch')
                    require(torch.equal(ref_rng,torch.get_rng_state()),'zero-init caller RNG mismatch')
                    errors=[]
                    for (n,p),(n2,q) in zip(native.named_parameters(),wrapper.base.named_parameters()):
                        require(n==n2 and (p.grad is None)==(q.grad is None),'base gradient identity/None mismatch')
                        if p.grad is not None:
                            torch.testing.assert_close(p.grad,q.grad,rtol=1e-5,atol=1e-6)
                            errors.append(float((p.grad-q.grad).abs().max()))
                    if arm!='P4':
                        expected=[(name,i,i if arm=='C4' else 0) for i in range(depth)
                                  for name in ('attn_out','ffn_out')]
                        require(out['route']==expected,'wrong depth/projection routing')
                        for bank in wrapper.adapters.values():
                            require(bank.up.grad is not None and bank.down.grad is not None,'adapter gradient disconnected')
                            require(bool(torch.isfinite(bank.up.grad).all()) and bool(torch.isfinite(bank.down.grad).all()),'bad adapter gradient')
                            if depth==4:
                                require(bool((bank.up.grad!=0).any()),'up factor has no usable gradient')
                            require(bool((bank.down.grad==0).all()),'zero-up down gradient is not zero')
                    require(m2.weights_sha(wrapper.base)==initial_sha and no_hooks(wrapper),'gate mutated base/leaked hook')
                    wrapper.eval();native.eval()
                    with torch.no_grad():
                        torch.manual_seed(9002)
                        a=native(x,return_logits=True,num_steps_pair=[0,depth])['logits']
                        torch.manual_seed(9002)
                        b=wrapper(x,depth=depth)['logits']
                    torch.testing.assert_close(a,b,rtol=1e-5,atol=1e-6)
                    cases.append(dict(arm=arm,seed=seed,length=length,depth=depth,status='PASS',
                                      max_base_gradient_abs_error=max(errors,default=0.)))
    require(m2.weights_sha(base)==initial_sha,'gate changed original model')
    return dict(status='PASS',zero_init_identity_cases=cases,scope='native copies, no optimizer update')


def probe(wrapper,x,y,torch,m2):
    before=m2.weights_sha(wrapper)
    counts=common.probe(wrapper,x,y,torch,m2)
    counts.update(base_parameters=sum(p.numel() for p in wrapper.base.parameters()),
                  added_parameters=wrapper.added_parameters(),
                  scope='supported ops including adapter matmuls; excludes optimizer/unsupported elementwise')
    require(m2.weights_sha(wrapper)==before,'probe mutated full model/adapter')
    return counts


def worker(args):
    torch,env=runtime()
    from c_adapters import LoopLoRA
    from torch.nn.attention import SDPBackend,sdpa_kernel
    root,m2,task,history=sources(args.parcae_dir)
    data=json.loads((args.out/'data.json').read_text());manifest=task.manifest(data)
    require(all(manifest[k]['sha256']==v for k,v in common.DATA_SHA.items()),'data drift')
    job=args.out/'jobs'/f'{args.arm}_{args.seed}';job.mkdir(parents=True,exist_ok=False)
    base,io,base_sha=initial(m2,history,args.seed)
    wrapper=LoopLoRA(base,args.arm,args.seed);full_start=m2.weights_sha(wrapper)
    added_start=m2.weights_sha(wrapper.adapters)
    encoded=[task.training_tokens(r) for r in data['train']]
    x=torch.tensor([a for a,b in encoded],dtype=torch.long)
    y=torch.tensor([b for a,b in encoded],dtype=torch.long)
    indices=torch.randint(len(x),(STEPS,BATCH),generator=torch.Generator().manual_seed(args.seed+12000))
    probe_ix=[j for c in range(4) for j in [i for i,r in enumerate(data['train']) if r['carry']==c][:8]]
    counts=probe(wrapper,x[probe_ix],y[probe_ix],torch,m2)
    require(counts['parameters']==(60224 if args.arm=='P4' else 62784),'unexpected registered capacity')
    require(m2.weights_sha(base)==base_sha and m2.weights_sha(wrapper)==full_start,'start drift')
    row=dict(arm=args.arm,seed=args.seed,status='NOT TESTED',environment=env,source_head=git(root,'rev-parse','HEAD'),
        initial_model_sha256=base_sha,initial_full_state_sha256=full_start,initial_adapter_sha256=added_start,
        shared_io=io,settings=dict(mode=args.arm,unroll=4,objective='exit4_only',scale=1.,
            adapter_rank=0 if args.arm=='P4' else 16 if args.arm=='S16' else 4,
            adapter_groups=0 if args.arm=='P4' else 1 if args.arm=='S16' else 4,
            backbone_trainable=True),counts=counts,batch_indices_sha256=m2.tensor_sha(indices),steps=0,
        planned_steps=STEPS,supervised_target_tokens=STEPS*BATCH*4,input_token_positions=STEPS*BATCH*9,
        problem_exposures=STEPS*BATCH)
    write(job/'row.json',row)
    opt=torch.optim.AdamW(wrapper.parameters(),lr=.002,betas=(.9,.999),eps=1e-8,weight_decay=0.)
    require({id(p) for g in opt.param_groups for p in g['params']}=={id(p) for p in wrapper.parameters()},'optimizer omission')
    losses=[];norms=[];rng_hashes=[];wrapper.train();start=time.perf_counter()
    with torch.random.fork_rng(devices=[]),sdpa_kernel(SDPBackend.MATH):
        torch.manual_seed(args.seed+2000)
        for step,ix in enumerate(indices,1):
            rng_hashes.append(m2.tensor_sha(torch.get_rng_state()))
            opt.zero_grad(set_to_none=True);loss=wrapper(x[ix],y[ix],depth=4)['loss']
            require(bool(torch.isfinite(loss)),'nonfinite objective');loss.backward()
            require(all(bool(torch.isfinite(p.grad).all()) for p in wrapper.parameters() if p.grad is not None),'nonfinite gradient')
            norm=float(torch.nn.utils.clip_grad_norm_(wrapper.parameters(),1.))
            require(math.isfinite(norm),'nonfinite norm');opt.step()
            losses.append(float(loss.detach()));norms.append(norm)
            if step%500==0:
                row.update(status='PARTIAL',steps=step,loss_trace=losses,gradient_norm_trace=norms,rng_before_forward_sha256=rng_hashes)
                write(job/'row.json',row)
                print(json.dumps(dict(arm=args.arm,seed=args.seed,step=step,objective=losses[-1])),flush=True)
        rng=torch.get_rng_state().clone()
    row.update(steps=STEPS,training_seconds_descriptive=time.perf_counter()-start,
        loss_trace=losses,gradient_norm_trace=norms,rng_before_forward_sha256=rng_hashes,
        counted_training_flops=counts['step_flops']*STEPS,final_base_sha256=m2.weights_sha(base),
        final_full_state_sha256=m2.weights_sha(wrapper),final_adapter_sha256=m2.weights_sha(wrapper.adapters))
    require(row['final_full_state_sha256']!=full_start,'weights did not update')
    path=job/'step3000.pt'
    # Full wrapper state includes both native backbone and ALL adapter tensors.
    torch.save(dict(model=wrapper.state_dict(),optimizer=opt.state_dict(),cpu_rng=rng,batch_indices=indices,
        arm=args.arm,seed=args.seed,step=STEPS,settings=row['settings'],source_head=row['source_head'],
        initial_base_sha256=base_sha,data=manifest),path)
    row.update(checkpoint_file=str(path.relative_to(args.out)),checkpoint_sha256=file_sha(path))
    row['development']={str(d):common.evaluate(wrapper,data['development'],args.seed,d,torch,task) for d in (2,4)}
    row['transitions']=common.transitions([r['target'] for r in data['development']],
                        row['development']['2']['predictions'],row['development']['4']['predictions'])
    require(m2.weights_sha(wrapper)==row['final_full_state_sha256'] and no_hooks(wrapper),'evaluation mutation/hook leak')
    m2.upstream_check(args.parcae_dir)
    require(not git(root,'status','--porcelain','--untracked-files=no'),'source changed')
    row.update(status='PASS',process_high_water_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
               rss_scope='Linux worker lifetime incl imports/probes/training/evaluation, not training-only')
    write(job/'row.json',row)
    print(json.dumps(dict(arm=args.arm,seed=args.seed,execution='PASS',development_accuracy={
        d:row['development'][d]['metrics']['all']['accuracy'] for d in ('2','4')})),flush=True)
    return 0


def execute(args,report):
    torch,env=runtime();report['environment']=env
    root,m2,task,history=sources(args.parcae_dir)
    report.update(code_head=git(root,'rev-parse','HEAD'),source_pin=common.PIN,
        source_sha256={p.name:file_sha(p) for p in HERE.iterdir() if p.suffix in ('.py','.md','.sh')},
        reused_helpers_sha256=REUSED_SHA,factory_sha256=common.FACTORY_SHA,task_sha256=common.TASK_SHA)
    data,manifest=common.check_data(task);report.update(data=manifest,data_status='PASS')
    write(args.out/'data.json',data)
    (args.out/'pip-freeze.txt').write_text(subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True))
    report['native_preflight']=[]
    for seed in SEEDS:
        base,_,_=initial(m2,history,seed)
        report['native_preflight'].append(native_preflight(base,seed,torch,m2))
        print(json.dumps(dict(seed=seed,native_zero_init_gate='PASS')),flush=True)
    report['native_compatibility_status']='PASS';write(args.out/'result.json',report)
    for seed in SEEDS:
        for arm in ARMS:
            run=subprocess.run([sys.executable,'-B',str(HERE/'run_cpu.py'),'--worker','--arm',arm,'--seed',str(seed),
                '--parcae-dir',str(args.parcae_dir),'--out',str(args.out)],check=False)
            require(run.returncode==0,f'worker {arm}/{seed} blocked; preserve partial outputs')
            row=json.loads((args.out/'jobs'/f'{arm}_{seed}'/'row.json').read_text())
            require(row['status']=='PASS' and row['steps']==STEPS,'incomplete worker')
            report['rows'].append(row);write(args.out/'result.json',report)
    for seed in SEEDS:
        group=[next(r for r in report['rows'] if r['seed']==seed and r['arm']==a) for a in ARMS]
        for key in ('initial_model_sha256','batch_indices_sha256','rng_before_forward_sha256'):
            require(all(r[key]==group[0][key] for r in group),f'pairing mismatch {seed}/{key}')
        require(group[1]['counts']['parameters']==group[2]['counts']['parameters']==62784,'capacity control mismatch')
    m2.upstream_check(args.parcae_dir)
    require(not git(root,'status','--porcelain','--untracked-files=no'),'research source changed')
    outcome=summarize(report['rows'])
    report.update(execution_status='PASS',pairing_status='PASS',capacity_control_status='PASS',outcome=outcome,
        execution_scope='nine completed3000-step arms; eighteen development conditions; primary C4-S16',
        upstream_unchanged=True,exit_code=outcome['exit_code'])


def show(report):
    for key in ('experiment','execution_status','native_compatibility_status','pairing_status','capacity_control_status','outcome','error'):
        if key in report:
            print(key,json.dumps(report[key],ensure_ascii=False),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parcae-dir',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--worker',action='store_true',help=argparse.SUPPRESS)
    parser.add_argument('--arm',choices=ARMS,help=argparse.SUPPRESS)
    parser.add_argument('--seed',type=int,choices=SEEDS,help=argparse.SUPPRESS)
    args=parser.parse_args();args.out=args.out.resolve();args.parcae_dir=args.parcae_dir.resolve()
    if args.worker:
        require(args.arm and args.seed is not None and (args.out/'data.json').is_file(),'invalid worker')
        try:
            return worker(args)
        except Exception:
            job=args.out/'jobs'/f'{args.arm}_{args.seed}'
            if job.is_dir():(job/'error.log').write_text(traceback.format_exc())
            traceback.print_exc();return 2
    target=args.out/'result.json'
    if target.exists():
        try:
            old=json.loads(target.read_text());require(old.get('experiment')==EXPERIMENT,'wrong existing experiment')
            show(old);code=old.get('exit_code',2)
            return code if type(code) is int and code in (0,1,2) else 2
        except Exception as exc:
            print('BLOCKED: existing result retained:',exc);return 2
    if args.out.exists():
        print('BLOCKED: existing partial directory retained');return 2
    args.out.mkdir(parents=True,exist_ok=False)
    report=dict(experiment=EXPERIMENT,execution_status='NOT TESTED',native_compatibility_status='NOT TESTED',
        pairing_status='NOT TESTED',capacity_control_status='NOT TESTED',data_status='NOT TESTED',rows=[],
        review_status='NOT TESTED / DEFERRED',held_out_test_status='NOT TESTED',exit_code=2)
    write(target,report)
    try:execute(args,report)
    except Exception as exc:
        report.update(execution_status='BLOCKED',error=f'{type(exc).__name__}: {exc}',exit_code=2)
        (args.out/'error.log').write_text(traceback.format_exc());traceback.print_exc()
    write(target,report);show(report);print(file_sha(target),target,flush=True)
    return report['exit_code']


if __name__=='__main__':
    raise SystemExit(main())
