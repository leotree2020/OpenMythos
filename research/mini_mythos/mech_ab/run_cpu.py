#!/usr/bin/env python3
"""Bounded nine-arm CPU mechanism experiment. No upstream or old-result writes."""
from __future__ import annotations
import argparse
import copy
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import resource
import subprocess
import sys
import time
import traceback

os.environ['CUDA_VISIBLE_DEVICES'] = ''
sys.dont_write_bytecode = True
from metrics import ARMS, SEEDS, EXPERIMENT, summarize, transitions

HERE = Path(__file__).resolve().parent
PIN = '69284c13746e849104f738d6d1a347b1f457df76'
FACTORY_SHA = '74f00c64448ddbc224a48ef83dc031a90c33448ccb92647666707f6b8f988967'
TASK_SHA = '1baebb6e47f39de63e894e7d8379bdcd8403e8cd79ead1e33fa6e525278940af'
HISTORY_SHA = '4960841f1f685326cf8a4c7d1198718346ef38b8ce0a3d0fb8d48d70daa0637d'
DATA_SHA = {'train':'d2603d85dca18da104b6138e4513fd47be7c8f2063f447534807f86d68e3c458',
            'development':'f232a8bc703e5aea07d89637f67110442a5d3882f560b05487c4462d31cd02cd'}
STEPS, BATCH, EVAL_BATCH = 3000, 32, 64


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git(root, *args):
    return subprocess.check_output(['git','-C',str(root),*args],text=True).strip()


def write(path, value):
    path = Path(path)
    tmp = path.with_name(path.name+'.tmp')
    tmp.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    os.replace(tmp,path)


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name,path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def runtime():
    import torch, numpy, einops
    env = dict(python=platform.python_version(),torch=str(torch.__version__),
               numpy=numpy.__version__,einops=einops.__version__,platform=platform.platform(),
               device='cpu',threads=1,torch_build=torch.__config__.show())
    require(platform.system() == 'Linux' and env['python'] == '3.12.3',
            'requires original Linux Python3.12.3; no auto-install or waiver')
    require((env['torch'],env['numpy'],env['einops']) == ('2.11.0+cpu','1.26.4','0.8.0'),
            'requires pinned original CPU packages')
    require(torch.get_default_dtype() == torch.float32,'FP32 default required')
    return torch,env


def sources(parcae):
    root = Path(git(HERE,'rev-parse','--show-toplevel'))
    require(not git(root,'status','--porcelain','--untracked-files=no'),'dirty tracked research sources')
    factory = HERE.parent/'m2_matched/experiment.py'
    task_path = HERE.parent/'r1b_calibration/task.py'
    require(file_sha(factory)==FACTORY_SHA and file_sha(task_path)==TASK_SHA,'factory/task drift')
    m2 = load_module('mech_ab_factory',factory)
    m2.setup(parcae)
    require(m2.PIN == PIN,'upstream pin mismatch')
    task = load_module('mech_ab_existing_task',task_path)
    history_path = factory.parent/'evidence/linux_e533fbe/pilot.json'
    require(file_sha(history_path)==HISTORY_SHA,'initial identity reference drift')
    history = json.loads(history_path.read_text())
    return root,m2,task,history


def initial(m2, history, seed):
    gpt,base = m2.make('gpt',60,seed),m2.make('parcae',64,seed)
    io = m2.pair_io(gpt,base)
    expected = next(r['initial_weights_sha256'] for r in history['rows']
                    if r['seed']==seed and r['arm']=='parcae')
    require(m2.weights_sha(base)==expected,'original paired initial identity mismatch')
    del gpt
    return base,io,expected


def check_data(task):
    data = task.make_data()
    manifest = task.manifest(data)
    require(all(manifest[k]['sha256']==v for k,v in DATA_SHA.items()),'data drift')
    return data,manifest


def native_preflight(base, seed, torch, m2):
    from mechanisms import Mechanism,readout
    from torch.nn.attention import SDPBackend,sdpa_kernel
    before = m2.weights_sha(base)
    checks = []
    with torch.random.fork_rng(devices=[]),sdpa_kernel(SDPBackend.MATH):
        for length in (6,9):
            x = torch.arange(2*length).reshape(2,length) % 10
            y = (x+1) % 10
            y[:,:5] = -100
            for depth in (2,4):
                native = copy.deepcopy(base).train()
                wrapped = Mechanism(copy.deepcopy(base)).train()
                torch.manual_seed(9001)
                a = native(x,labels=y,return_logits=True,num_steps_pair=[0,depth])
                a['loss'].backward()
                rng_a = torch.get_rng_state().clone()
                torch.manual_seed(9001)
                b = wrapped(x,y,depth=depth,trace=True)
                b['loss'].backward()
                rng_b = torch.get_rng_state().clone()
                torch.testing.assert_close(a['logits'],b['logits'],rtol=1e-5,atol=1e-6)
                require(abs(float((a['loss']-b['loss']).detach()))<=1e-6,'identity loss mismatch')
                require(torch.equal(rng_a,rng_b),'identity RNG mismatch')
                max_error = 0.
                for (n,p),(n2,q) in zip(native.named_parameters(),wrapped.base.named_parameters()):
                    require(n==n2 and (p.grad is None)==(q.grad is None),'gradient name/None mismatch')
                    if p.grad is not None:
                        torch.testing.assert_close(p.grad,q.grad,rtol=1e-5,atol=1e-6)
                        max_error=max(max_error,float((p.grad-q.grad).abs().max()))
                with torch.no_grad():
                    suffix=readout(wrapped.base,b['states'][-1],x)
                torch.testing.assert_close(suffix,b['logits'],rtol=1e-5,atol=1e-6)
                require(m2.weights_sha(native)==before and m2.weights_sha(wrapped.base)==before,
                        'identity preflight mutated registered state')
                require(not wrapped.base.transformer.adapter._forward_pre_hooks and
                        not wrapped.base.transformer.core_block[-1]._forward_hooks,'hook leak')
                # Independent no-label native forward exercises evaluation path too.
                native.eval(); wrapped.eval()
                with torch.no_grad():
                    torch.manual_seed(9002)
                    la=native(x,return_logits=True,num_steps_pair=[0,depth])['logits']
                    torch.manual_seed(9002)
                    lb=wrapped(x,depth=depth)['logits']
                torch.testing.assert_close(la,lb,rtol=1e-5,atol=1e-6)
                checks.append(dict(seed=seed,length=length,depth=depth,status='PASS',
                                   max_gradient_abs_error=max_error))
        aux=Mechanism(copy.deepcopy(base),auxiliary=.25).train()
        torch.manual_seed(9001)
        result=aux(x,y,depth=4)
        result['aux_loss'].backward()  # auxiliary branch ALONE must reach shared core
        grads=[p.grad for n,p in aux.base.named_parameters() if 'core_block' in n and p.grad is not None]
        require(grads and all(bool(torch.isfinite(g).all()) for g in grads)
                and any(bool((g!=0).any()) for g in grads),'auxiliary core gradient detached/invalid')
        require(sum(p.numel() for p in base.parameters())==sum(p.numel() for p in aux.parameters()),
                'wrapper added trainable parameters')
    require(m2.weights_sha(base)==before,'preflight changed original start')
    return {'status':'PASS','identity_cases':checks,'auxiliary_core_gradient':'PASS'}


def probe(wrapper,x,y,torch,m2):
    from torch.nn.attention import SDPBackend,sdpa_kernel
    from torch.utils.flop_counter import FlopCounterMode
    before=m2.weights_sha(wrapper.base)
    wrapper.train();wrapper.zero_grad(set_to_none=True)
    with torch.random.fork_rng(devices=[]),sdpa_kernel(SDPBackend.MATH):
        torch.manual_seed(9001)
        with FlopCounterMode(display=False) as counter:
            out=wrapper(x,y,depth=4)
            forward=counter.get_total_flops()
            out['loss'].backward()
            total=counter.get_total_flops()
    require(total>forward>0 and bool(torch.isfinite(out['loss'])),'invalid count/objective')
    require(all(bool(torch.isfinite(p.grad).all()) for p in wrapper.parameters() if p.grad is not None),
            'nonfinite probe gradients')
    counts={'parameters':sum(p.numel() for p in wrapper.parameters()),
            'gradient_participating_parameters_probe':sum(p.numel() for p in wrapper.parameters() if p.grad is not None),
            'none_grad_names_probe':[n for n,p in wrapper.base.named_parameters() if p.grad is None],
            'forward_flops':forward,'backward_flops':total-forward,'step_flops':total,
            'scope':'supported operators; auxiliary readout included; elementwise/optimizer may be omitted'}
    wrapper.zero_grad(set_to_none=True)
    require(m2.weights_sha(wrapper.base)==before,'count probe changed weights')
    return counts


def generate(wrapper,prompts,seed,depth,torch):
    from torch.nn.attention import SDPBackend,sdpa_kernel
    from torch.utils.flop_counter import FlopCounterMode
    wrapper.eval();predictions=[]
    with torch.no_grad(),torch.random.fork_rng(devices=[]),sdpa_kernel(SDPBackend.MATH):
        with FlopCounterMode(display=False) as counter:
            for offset in range(0,len(prompts),EVAL_BATCH):
                x=torch.tensor(prompts[offset:offset+EVAL_BATCH],dtype=torch.long)
                require(x.ndim==2 and x.shape[1]==6,'only six prompt digits are allowed')
                torch.manual_seed(seed+80000+offset)
                for _ in range(4):
                    logits=wrapper(x,depth=depth)['logits']
                    require(logits.shape==(*x.shape,256) and bool(torch.isfinite(logits).all()),'invalid logits')
                    x=torch.cat((x,logits[:,-1,:].argmax(-1,keepdim=True)),dim=1)
                predictions.extend(x[:,6:].tolist())
            count=counter.get_total_flops()
    return predictions,count


def evaluate(wrapper,rows,seed,depth,torch,task):
    from mechanisms import answer_ce
    from torch.nn.attention import SDPBackend,sdpa_kernel
    start=time.perf_counter()
    predictions,count=generate(wrapper,[r['prompt'] for r in rows],seed,depth,torch)
    seconds=time.perf_counter()-start
    nll=0.;targets=0
    with torch.no_grad(),torch.random.fork_rng(devices=[]),sdpa_kernel(SDPBackend.MATH):
        for offset in range(0,len(rows),EVAL_BATCH):
            items=[task.training_tokens(r) for r in rows[offset:offset+EVAL_BATCH]]
            x=torch.tensor([a for a,b in items],dtype=torch.long)
            y=torch.tensor([b for a,b in items],dtype=torch.long)
            torch.manual_seed(seed+90000+offset)
            # Teacher-forced CE is separate; it never supplies prefixes to greedy generation.
            logits=wrapper(x,depth=depth)['logits']
            loss=float(answer_ce(logits,y));n=int((y!=-100).sum())
            require(math.isfinite(loss),'nonfinite development CE')
            nll+=loss*n;targets+=n
    return dict(metrics=task.score(rows,predictions),predictions=predictions,
                answer_nll=nll/targets,answer_target_tokens=targets,
                counted_full_generation_flops=count,generation_seconds_descriptive=seconds,
                scope='existing development; four free full-prefix generation steps; CE separate')


def worker(args):
    torch,env=runtime()
    from mechanisms import ARMS as SETTINGS,Mechanism
    from torch.nn.attention import SDPBackend,sdpa_kernel
    root,m2,task,history=sources(args.parcae_dir)
    data_path=args.out/'data.json'
    data=json.loads(data_path.read_text());manifest=task.manifest(data)
    require(all(manifest[k]['sha256']==v for k,v in DATA_SHA.items()),'worker data drift')
    job=args.out/'jobs'/f'{args.arm}_{args.seed}'
    job.mkdir(parents=True,exist_ok=False)
    base,io,initial_sha=initial(m2,history,args.seed)
    wrapper=Mechanism(base,*SETTINGS[args.arm])
    encoded=[task.training_tokens(r) for r in data['train']]
    x=torch.tensor([a for a,b in encoded],dtype=torch.long)
    y=torch.tensor([b for a,b in encoded],dtype=torch.long)
    indices=torch.randint(len(x),(STEPS,BATCH),generator=torch.Generator().manual_seed(args.seed+12000))
    probe_indices=[i for c in range(4) for i in
                   [j for j,r in enumerate(data['train']) if r['carry']==c][:8]]
    # Native gate already covered full shapes; probe uses fixed actual-shape batch.
    counts=probe(wrapper,x[probe_indices],y[probe_indices],torch,m2)
    require(m2.weights_sha(base)==initial_sha,'initial state changed before learning')
    row=dict(arm=args.arm,seed=args.seed,status='NOT TESTED',environment=env,
             source_head=git(root,'rev-parse','HEAD'),initial_model_sha256=initial_sha,shared_io=io,
             settings=dict(alpha=SETTINGS[args.arm][0],auxiliary=SETTINGS[args.arm][1],unroll=4),
             counts=counts,batch_indices_sha256=m2.tensor_sha(indices),
             steps=0,planned_steps=STEPS,supervised_target_tokens=STEPS*BATCH*4,
             input_token_positions=STEPS*BATCH*9,problem_exposures=STEPS*BATCH)
    write(job/'row.json',row)
    opt=torch.optim.AdamW(base.parameters(),lr=.002,betas=(.9,.999),eps=1e-8,weight_decay=0.)
    losses=[];final_losses=[];aux_losses=[];norms=[];rng_hashes=[]
    wrapper.train();started=time.perf_counter()
    with torch.random.fork_rng(devices=[]),sdpa_kernel(SDPBackend.MATH):
        torch.manual_seed(args.seed+2000)
        for step,ix in enumerate(indices,1):
            rng_hashes.append(m2.tensor_sha(torch.get_rng_state()))
            opt.zero_grad(set_to_none=True)
            output=wrapper(x[ix],y[ix],depth=4)
            loss=output['loss'];require(bool(torch.isfinite(loss)),'nonfinite objective')
            loss.backward()
            require(all(bool(torch.isfinite(p.grad).all()) for p in base.parameters() if p.grad is not None),
                    'nonfinite gradient')
            norm=float(torch.nn.utils.clip_grad_norm_(base.parameters(),1.))
            require(math.isfinite(norm),'nonfinite norm')
            opt.step()
            losses.append(float(loss.detach()));final_losses.append(float(output['final_loss'].detach()))
            aux_losses.append(None if output['aux_loss'] is None else float(output['aux_loss'].detach()))
            norms.append(norm)
            if step%500==0:
                row.update(status='PARTIAL',steps=step,loss_trace=losses,final_loss_trace=final_losses,
                           aux_loss_trace=aux_losses,gradient_norm_trace=norms,rng_before_forward_sha256=rng_hashes)
                write(job/'row.json',row)
                print(json.dumps(dict(arm=args.arm,seed=args.seed,step=step,objective=losses[-1])),flush=True)
        rng=torch.get_rng_state().clone()
    row.update(training_seconds_descriptive=time.perf_counter()-started,steps=STEPS,
               loss_trace=losses,final_loss_trace=final_losses,aux_loss_trace=aux_losses,
               gradient_norm_trace=norms,rng_before_forward_sha256=rng_hashes,
               counted_training_flops=counts['step_flops']*STEPS,final_model_sha256=m2.weights_sha(base))
    require(row['final_model_sha256']!=initial_sha,'weights did not change')
    path=job/'step3000.pt'
    torch.save(dict(model=base.state_dict(),optimizer=opt.state_dict(),cpu_rng=rng,batch_indices=indices,
                    arm=args.arm,seed=args.seed,step=STEPS,settings=row['settings'],
                    initial_sha256=initial_sha,data=manifest,source_head=row['source_head']),path)
    row.update(checkpoint_file=str(path.relative_to(args.out)),checkpoint_sha256=file_sha(path))
    row['development']={str(d):evaluate(wrapper,data['development'],args.seed,d,torch,task) for d in (2,4)}
    row['transitions']=transitions([r['target'] for r in data['development']],
                         row['development']['2']['predictions'],row['development']['4']['predictions'])
    require(m2.weights_sha(base)==row['final_model_sha256'],'evaluation changed weights')
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
    report.update(code_head=git(root,'rev-parse','HEAD'),source_pin=PIN,
          source_sha256={p.name:file_sha(p) for p in HERE.iterdir() if p.suffix in ('.py','.md','.sh')},
          factory_sha256=FACTORY_SHA,task_sha256=TASK_SHA)
    data,manifest=check_data(task);report.update(data=manifest,data_status='PASS')
    write(args.out/'data.json',data)
    (args.out/'pip-freeze.txt').write_text(subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True))
    report['native_preflight']=[]
    for seed in SEEDS:
        base,_,_=initial(m2,history,seed)
        report['native_preflight'].append(native_preflight(base,seed,torch,m2))
        print(json.dumps(dict(seed=seed,native_identity_preflight='PASS')),flush=True)
    report['native_compatibility_status']='PASS';write(args.out/'result.json',report)
    # Exactly nine isolated child processes; a scientific FAIL never cancels another arm.
    for seed in SEEDS:
        for arm in ARMS:
            cmd=[sys.executable,'-B',str(HERE/'run_cpu.py'),'--worker','--arm',arm,'--seed',str(seed),
                 '--parcae-dir',str(args.parcae_dir),'--out',str(args.out)]
            completed=subprocess.run(cmd,check=False)
            require(completed.returncode==0,f'worker {arm}/{seed} blocked; partial output retained')
            row=json.loads((args.out/'jobs'/f'{arm}_{seed}'/'row.json').read_text())
            require(row['status']=='PASS' and row['steps']==STEPS,'incomplete worker')
            report['rows'].append(row);write(args.out/'result.json',report)
    for seed in SEEDS:
        triple=[next(r for r in report['rows'] if r['seed']==seed and r['arm']==a) for a in ARMS]
        for key in ('initial_model_sha256','batch_indices_sha256','rng_before_forward_sha256'):
            require(triple[0][key]==triple[1][key]==triple[2][key],f'pairing mismatch: {key}/{seed}')
    report.update(pairing_status='PASS',outcome=summarize(report['rows']),execution_status='PASS',
                  execution_scope='nine completed3000-step arms and eighteen development conditions')
    report['exit_code']=report['outcome']['exit_code']
    m2.upstream_check(args.parcae_dir)
    require(not git(root,'status','--porcelain','--untracked-files=no'),'tracked source changed')
    report['upstream_unchanged']=True


def show(report):
    for key in ('experiment','execution_status','native_compatibility_status','pairing_status','outcome','error'):
        if key in report:
            print(key,json.dumps(report[key],ensure_ascii=False),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parcae-dir',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--worker',action='store_true',help=argparse.SUPPRESS)
    parser.add_argument('--arm',choices=ARMS,help=argparse.SUPPRESS)
    parser.add_argument('--seed',type=int,choices=SEEDS,help=argparse.SUPPRESS)
    args=parser.parse_args();args.out=args.out.resolve();args.parcae_dir=args.parcae_dir.resolve()
    if args.worker:
        require(args.arm and args.seed is not None and (args.out/'data.json').is_file(),'invalid worker invocation')
        try:
            return worker(args)
        except Exception:
            job=args.out/'jobs'/f'{args.arm}_{args.seed}'
            if job.is_dir():
                (job/'error.log').write_text(traceback.format_exc())
            traceback.print_exc()
            return 2
    result=args.out/'result.json'
    if result.exists():
        try:
            existing=json.loads(result.read_text())
            require(existing.get('experiment')==EXPERIMENT,'wrong existing experiment; no overwrite')
            show(existing);print('Existing evidence: READ ONLY; no rerun.')
            return int(existing.get('exit_code',2))
        except (ValueError,TypeError,RuntimeError) as exc:
            print(f'BLOCKED: invalid existing result retained: {exc}',file=sys.stderr);return 2
    if args.out.exists():
        print('BLOCKED: incomplete/existing output retained; no rerun.',file=sys.stderr);return 2
    args.out.mkdir(parents=True,exist_ok=False)
    report=dict(experiment=EXPERIMENT,execution_status='BLOCKED',native_compatibility_status='NOT TESTED',
                pairing_status='NOT TESTED',data_status='NOT TESTED',rows=[],outcome=None,
                review_status='NOT TESTED / DEFERRED',held_out_test_status='NOT TESTED',exit_code=2)
    write(result,report)
    try:
        execute(args,report)
    except Exception as exc:
        report.update(execution_status='BLOCKED',error=f'{type(exc).__name__}: {exc}',exit_code=2)
        (args.out/'error.log').write_text(traceback.format_exc())
        traceback.print_exc()
    write(result,report);show(report)
    print(file_sha(result),result,flush=True)
    return report['exit_code']


if __name__=='__main__':
    raise SystemExit(main())
