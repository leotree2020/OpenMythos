#!/usr/bin/env python3
"""One frozen difficulty candidate; only development predictions at native depth2."""
from __future__ import annotations
import argparse
import importlib.util
import json
import math
import os
import platform
import subprocess
import sys
import time
import traceback
from pathlib import Path

os.environ['CUDA_VISIBLE_DEVICES'] = ''
sys.dont_write_bytecode = True
from task import (SEEDS, STEPS, BATCH, EVAL_BATCH, PROMPT, ANSWER, EXPERIMENT,
                  digest, make_data, manifest, training_tokens, score, learning_gate, qualify)

HERE = Path(__file__).resolve().parent
PIN = '69284c13746e849104f738d6d1a347b1f457df76'
FACTORY_SHA = '74f00c64448ddbc224a48ef83dc031a90c33448ccb92647666707f6b8f988967'
HISTORY_SHA = '4960841f1f685326cf8a4c7d1198718346ef38b8ce0a3d0fb8d48d70daa0637d'
EXPECTED_DATA = {'train': 'd2603d85dca18da104b6138e4513fd47be7c8f2063f447534807f86d68e3c458',
                'development': 'f232a8bc703e5aea07d89637f67110442a5d3882f560b05487c4462d31cd02cd'}


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def file_sha(path):
    return digest(Path(path).read_bytes())


def git(path, *args):
    return subprocess.check_output(['git', '-C', str(path), *args], text=True).strip()


def write(path, value):
    tmp = path.with_name(path.name+'.tmp')
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    os.replace(tmp, path)


def native(model, arm, x, y=None):
    kwargs = {'labels': y, 'return_logits': y is None}
    if arm == 'parcae':
        kwargs['num_steps_pair'] = [0, 2]
    return model(x, **kwargs)['logits' if y is None else 'loss']


def task_probe(model, arm, x, y, torch, m2):
    from torch.nn.attention import SDPBackend, sdpa_kernel
    from torch.utils.flop_counter import FlopCounterMode
    before = m2.weights_sha(model)
    model.eval()
    with torch.random.fork_rng(devices=[]), sdpa_kernel(SDPBackend.MATH):
        with torch.no_grad():
            torch.manual_seed(9001)
            logits = native(model, arm, x)
            torch.manual_seed(9001)
            loss = native(model, arm, x, y)
            ce = torch.nn.functional.cross_entropy(logits.reshape(-1,256), y.reshape(-1), ignore_index=-100)
            error = abs(float(loss-ce))
            require(error <= 1e-6 and bool(torch.isfinite(loss)), 'masked native CE mismatch')
        model.train()
        model.zero_grad(set_to_none=True)
        torch.manual_seed(9001)
        with FlopCounterMode(display=False) as fc:
            loss = native(model, arm, x, y)
            forward = fc.get_total_flops()
            loss.backward()
            total = fc.get_total_flops()
        active = sum(p.numel() for p in model.parameters() if p.grad is not None)
        inactive = [n for n,p in model.named_parameters() if p.grad is None]
    model.zero_grad(set_to_none=True)
    require(before == m2.weights_sha(model), 'probe changed registered state')
    require(total > forward > 0, 'empty counts')
    return {'parameters': sum(p.numel() for p in model.parameters()),
            'gradient_participating_parameters_probe': active, 'none_grad_names_probe': inactive,
            'forward_flops': forward, 'backward_flops': total-forward, 'step_flops': total,
            'masked_ce_abs_error': error, 'batch': len(x), 'input_length': x.shape[1],
            'scope': 'supported operators only, not equal active capacity/hardware work'}


def generate(model, arm, prompts, seed, torch):
    """No targets enter this function; four free greedy tokens from six operands."""
    from torch.nn.attention import SDPBackend, sdpa_kernel
    from torch.utils.flop_counter import FlopCounterMode
    model.eval()
    predictions = []
    with torch.no_grad(), torch.random.fork_rng(devices=[]), sdpa_kernel(SDPBackend.MATH):
        with FlopCounterMode(display=False) as fc:
            for offset in range(0, len(prompts), EVAL_BATCH):
                x = torch.tensor(prompts[offset:offset+EVAL_BATCH], dtype=torch.long)
                require(x.ndim == 2 and x.shape[1] == PROMPT, 'wrong prompt length')
                torch.manual_seed(seed+80000+offset)
                for _ in range(ANSWER):
                    logits = native(model, arm, x)
                    require(logits.shape == (*x.shape, 256), 'wrong logit shape')
                    require(bool(torch.isfinite(logits).all()), 'nonfinite generation')
                    x = torch.cat((x, logits[:, -1, :].argmax(-1, keepdim=True)), dim=1)
                predictions.extend(x[:,PROMPT:].tolist())
            count = fc.get_total_flops()
    return predictions, count


def evaluate(model, arm, rows, seed, torch):
    predictions, count = generate(model, arm, [r['prompt'] for r in rows], seed, torch)
    return {'metrics': score(rows, predictions), 'predictions': predictions,
            'counted_full_generation_flops': count, 'problems': len(rows),
            'scope': 'development only; four full-prefix greedy forwards; native GPT or Parcae d2',
            'rng_policy': 'seed+80000+batch_offset; forked CPU RNG'}


def execute(args, out, report):
    import torch
    import numpy
    import einops
    from torch.nn.attention import SDPBackend, sdpa_kernel
    env = {'python': platform.python_version(), 'torch': str(torch.__version__),
           'numpy': numpy.__version__, 'einops': einops.__version__, 'platform': platform.platform(),
           'device': 'cpu', 'torch_build': torch.__config__.show()}
    report['environment'] = env
    require(platform.system() == 'Linux' and env['python'] == '3.12.3', 'requires original Linux Python3.12.3')
    require((env['torch'],env['numpy'],env['einops']) == ('2.11.0+cpu','1.26.4','0.8.0'),
            'requires pinned CPU dependencies; no automatic installation or waiver')
    require(torch.get_default_dtype() == torch.float32, 'requires float32 default')
    root = Path(git(HERE, 'rev-parse', '--show-toplevel'))
    require(not git(root,'status','--porcelain','--untracked-files=no'), 'dirty research source')
    factory = root/'research/mini_mythos/m2_matched/experiment.py'
    require(file_sha(factory) == FACTORY_SHA, 'original model factory changed')
    spec = importlib.util.spec_from_file_location('r1b_existing_factory', factory)
    require(spec is not None and spec.loader is not None, 'factory import unavailable')
    m2 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m2)
    m2.setup(args.parcae_dir)
    require(m2.PIN == PIN, 'wrong source pin')
    env['threads'] = torch.get_num_threads()
    require(env['threads'] == 1, 'requires single CPU thread')
    data = make_data()
    report.update(code_head=git(root,'rev-parse','HEAD'), source_pin=PIN,
                  source_sha256={n:file_sha(HERE/n) for n in ('PROTOCOL.md','task.py','run_cpu.py')},
                  factory_sha256=FACTORY_SHA, data=manifest(data))
    require(all(report['data'][s]['sha256'] == h for s,h in EXPECTED_DATA.items()), 'data drift')
    report['data_status'] = 'PASS'
    write(out/'data_train_development.json',data)
    (out/'pip-freeze.txt').write_text(subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True))
    encoded = [training_tokens(e) for e in data['train']]
    train_x = torch.tensor([e[0] for e in encoded], dtype=torch.long)
    train_y = torch.tensor([e[1] for e in encoded], dtype=torch.long)
    require(train_x.shape[1] == PROMPT+ANSWER-1 and
            bool(((train_y != -100).sum(1) == ANSWER).all()), 'wrong shifted answer mask')
    history_path = factory.parent/'evidence/linux_e533fbe/pilot.json'
    require(file_sha(history_path) == HISTORY_SHA, 'historical initial identity file changed')
    history = json.loads(history_path.read_text())
    pairs, rows, indices = {}, {}, {}
    for seed in SEEDS:
        pair = {'gpt': m2.make('gpt',60,seed), 'parcae': m2.make('parcae',64,seed)}
        shared = m2.pair_io(pair['gpt'],pair['parcae'])
        pairs[seed] = pair
        indices[seed] = torch.randint(len(train_x),(STEPS,BATCH),
                                     generator=torch.Generator().manual_seed(seed+12000))
        for arm, model in pair.items():
            initial = m2.weights_sha(model)
            old = next(r for r in history['rows'] if r['seed']==seed and r['arm']==arm)
            require(initial == old['initial_weights_sha256'], 'starting recipe mismatch')
            probe = task_probe(model,arm,train_x[:BATCH],train_y[:BATCH],torch,m2)
            row = {'seed':seed,'arm':arm,'status':'NOT TESTED','initial_model_sha256':initial,
                   'shared_io':shared,'budget_probe':probe,'batch_indices_sha256':m2.tensor_sha(indices[seed]),
                   'planned_steps':STEPS,'supervised_target_tokens':STEPS*BATCH*ANSWER,
                   'input_token_positions':STEPS*BATCH*(PROMPT+ANSWER-1),'problem_exposures':STEPS*BATCH}
            rows[seed,arm] = row
            report['rows'].append(row)
    report['paired_budgets'] = []
    for seed in SEEDS:
        a,b = (rows[seed,arm]['budget_probe'] for arm in ('gpt','parcae'))
        pr, cr = m2.ratio(a['parameters'],b['parameters']),m2.ratio(a['step_flops'],b['step_flops'])
        report['paired_budgets'].append({'seed':seed,'registered_parameter_ratio':pr,'counted_compute_ratio':cr})
        require(max(pr,cr) <= 1.10, 'actual task-shape budgets outside tolerance; no auto-retuning')
    report['budget_status'] = 'PASS'
    write(out/'result.json',report)

    def train(arm,seed):
        model, row = pairs[seed][arm],rows[seed,arm]
        require(m2.weights_sha(model) == row['initial_model_sha256'], 'model changed before training')
        model.train()
        opt = torch.optim.AdamW(model.parameters(),lr=.002,betas=(.9,.999),eps=1e-8,weight_decay=0.)
        losses,norms = [],[]
        started = time.perf_counter()
        with torch.random.fork_rng(devices=[]), sdpa_kernel(SDPBackend.MATH):
            torch.manual_seed(seed+2000)
            for step,ix in enumerate(indices[seed],1):
                opt.zero_grad(set_to_none=True)
                loss = native(model,arm,train_x[ix],train_y[ix])
                require(bool(torch.isfinite(loss)), 'nonfinite training loss')
                loss.backward()
                require(all(bool(torch.isfinite(p.grad).all()) for p in model.parameters() if p.grad is not None),
                        'nonfinite gradient')
                norm = float(torch.nn.utils.clip_grad_norm_(model.parameters(),1.))
                require(math.isfinite(norm), 'nonfinite norm')
                opt.step()
                losses.append(float(loss.detach()));norms.append(norm)
                if step % 500 == 0:
                    print(json.dumps({'seed':seed,'arm':arm,'step':step,'training_loss':losses[-1]}),flush=True)
            rng = torch.get_rng_state().clone()
        row.update(steps=STEPS,training_seconds_descriptive=time.perf_counter()-started,
                   loss_trace=losses,gradient_norm_trace=norms,final_model_sha256=m2.weights_sha(model),
                   counted_training_flops=STEPS*row['budget_probe']['step_flops'])
        require(row['initial_model_sha256'] != row['final_model_sha256'], 'weights never changed')
        path = out/f'{arm}_{seed}_step{STEPS}.pt'
        temp = path.with_suffix('.pt.tmp')
        torch.save({'model':model.state_dict(),'optimizer':opt.state_dict(),'cpu_rng':rng,
                    'seed':seed,'arm':arm,'step':STEPS,'batch_indices':indices[seed],
                    'data':report['data'],'source_head':report['code_head']},temp)
        os.replace(temp,path)
        row.update(checkpoint_file=path.name,checkpoint_sha256=file_sha(path),status='PASS')
        row['development_d2'] = evaluate(model,arm,data['development'],seed,torch)
        require(m2.weights_sha(model) == row['final_model_sha256'], 'evaluation changed weights')
        write(out/'result.json',report)
        print(json.dumps({'seed':seed,'arm':arm,'development_accuracy':
                         {k:v['accuracy'] for k,v in row['development_d2']['metrics'].items()}}),flush=True)

    for seed in SEEDS:
        train('gpt',seed)
    gm = [rows[s,'gpt']['development_d2']['metrics'] for s in SEEDS]
    if learning_gate(gm) == 'FAIL':
        report.update(execution_scope='three GPT controls; planned learning-floor stop',
                      qualification=qualify(gm,None))
    else:
        for seed in SEEDS:
            train('parcae',seed)
        pm = [rows[s,'parcae']['development_d2']['metrics'] for s in SEEDS]
        report.update(execution_scope='six final development endpoints; no held-out test or depth4',
                      qualification=qualify(gm,pm))
    m2.upstream_check(args.parcae_dir)
    require(not git(root,'status','--porcelain','--untracked-files=no'), 'source changed during execution')
    require(all(file_sha(HERE/n)==h for n,h in report['source_sha256'].items()), 'experiment source bytes changed')
    report.update(execution_status='PASS',upstream_unchanged=True,
                  exit_code={'PASS':0,'FAIL':1,'BLOCKED':2}[report['qualification']['task_qualification_status']],
                  completed_training_arms=sum(r['status']=='PASS' for r in report['rows']))
    write(out/'result.json',report)
    print(json.dumps({'execution':report['execution_status'],'qualification':report['qualification']}),flush=True)
    return report['exit_code']


def read_existing(path):
    value = json.loads(Path(path).read_text())
    require(value.get('experiment') == EXPERIMENT, 'existing result belongs to another task')
    require(value.get('execution_status') == 'PASS' and value.get('qualification'),
            'existing result incomplete/BLOCKED; preserve it, do not rerun')
    code = {'PASS':0,'FAIL':1,'BLOCKED':2}[value['qualification']['task_qualification_status']]
    require(value.get('exit_code') == code, 'existing result exit-code inconsistency')
    print(json.dumps({'existing_result':'READ_ONLY','execution':value['execution_status'],
                      'qualification':value['qualification'],'sha256':file_sha(path)}),flush=True)
    return code


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--parcae-dir',type=Path)
    p.add_argument('--out',type=Path)
    p.add_argument('--read-existing',type=Path)
    args=p.parse_args()
    if args.read_existing:
        try:
            return read_existing(args.read_existing)
        except Exception as e:
            print('BLOCKED: '+str(e),file=sys.stderr);return 2
    if args.out is None or args.parcae_dir is None:
        p.error('--out and --parcae-dir are required for a new run')
    out=args.out.resolve()
    try:
        out.mkdir(parents=True,exist_ok=False)
    except FileExistsError:
        print('BLOCKED: output exists; never overwrite or auto-resume',file=sys.stderr);return 2
    report={'experiment':EXPERIMENT,'execution_status':'NOT TESTED','data_status':'NOT TESTED',
            'budget_status':'NOT TESTED','qualification':None,'rows':[],
            'final_test_status':'NOT TESTED','extra_depth_benefit_status':'NOT TESTED',
            'review_status':'NOT TESTED / DEFERRED',
            'limitations':['development-only selection, not final-test evidence',
                           'one new in-distribution length, not length generalization',
                           'unchanged inactive native parameters; no equal active capacity',
                           'no architecture superiority, ACT or hardware-efficiency claim']}
    try:
        return execute(args,out,report)
    except Exception:
        report.update(execution_status='BLOCKED',error=traceback.format_exc(),exit_code=2)
        write(out/'result.json',report)
        traceback.print_exc();return 2


if __name__=='__main__':
    raise SystemExit(main())
