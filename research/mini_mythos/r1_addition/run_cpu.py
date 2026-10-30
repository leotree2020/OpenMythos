#!/usr/bin/env python3
"""R1-A: native-model arithmetic learning and prespecified extra-compute screen."""
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
from task import (SEEDS, STEPS, BATCH, EVAL_BATCH, digest, object_digest,
                  make_splits, manifest, training_tokens, score, learning_gate, benefit)

HERE = Path(__file__).resolve().parent
PIN = '69284c13746e849104f738d6d1a347b1f457df76'
FACTORY_SHA = '74f00c64448ddbc224a48ef83dc031a90c33448ccb92647666707f6b8f988967'
EXPECTED_DATA = {'train': 'cd51f326fa3ad15a1c4c0408c57993167e1265403f48563f709b3f3a267d6274',
                 'validation': '3f442db5d57985b83101affff9b74a2a957cfb72027be87b5a282ea4f1d05d79',
                 'test': '814ca3a401e480b0e92fe12354dd40ea56d92d8a5c34743032946ef7df178790'}


def require(value, message):
    if not value:
        raise RuntimeError(message)


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()


def file_sha(path):
    return digest(Path(path).read_bytes())


def write(path, value):
    temp = path.with_name(path.name+'.tmp')
    temp.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    os.replace(temp, path)


def native(model, arm, x, y=None, depth=2):
    kwargs = {'labels': y, 'return_logits': y is None}
    if arm == 'parcae':
        kwargs['num_steps_pair'] = [0, depth]
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
    require(before == m2.weights_sha(model), 'budget probe changed weights')
    require(total > forward > 0, 'empty supported-op budget')
    return {'parameters': sum(p.numel() for p in model.parameters()),
            'gradient_participating_parameters_probe': active, 'none_grad_names_probe': inactive,
            'forward_flops': forward, 'backward_flops': total-forward, 'step_flops': total,
            'masked_ce_abs_error': error, 'batch': BATCH, 'input_length': 6,
            'scope': 'supported operators, excludes optimizer/hardware effects; no active-capacity equivalence'}


def evaluate(model, arm, rows, seed, depth, torch):
    from torch.nn.attention import SDPBackend, sdpa_kernel
    from torch.utils.flop_counter import FlopCounterMode
    model.eval()
    predictions = []
    with torch.no_grad(), torch.random.fork_rng(devices=[]), sdpa_kernel(SDPBackend.MATH):
        with FlopCounterMode(display=False) as fc:
            for offset in range(0, len(rows), EVAL_BATCH):
                batch = rows[offset:offset+EVAL_BATCH]
                # ONLY operand digits reach the model; target digits are used by score() later.
                x = torch.tensor([r['prompt'] for r in batch], dtype=torch.long)
                require(x.shape[1] == 4, 'prompt contains target prefix')
                torch.manual_seed(seed+70000+offset)
                for _ in range(3):
                    logits = native(model, arm, x, depth=depth)
                    require(bool(torch.isfinite(logits).all()), 'nonfinite generation')
                    token = logits[:, -1, :].argmax(-1, keepdim=True)
                    x = torch.cat((x, token), dim=1)
                predictions.extend(x[:,4:].tolist())
            count = fc.get_total_flops()
    return {'metrics': score(rows, predictions), 'predictions': predictions,
            'counted_full_generation_flops': count, 'problems': len(rows),
            'rng_policy': 'seed+70000+batch_offset, reset for each depth; greedy full256-way output',
            'cost_scope': 'all three greedy full-prefix forwards incl final partial batch; no cache'}


def execute(args, out, report):
    import torch
    import numpy
    import einops
    from torch.nn.attention import SDPBackend, sdpa_kernel
    env = {'python': platform.python_version(), 'torch': str(torch.__version__),
           'numpy': numpy.__version__, 'einops': einops.__version__, 'platform': platform.platform(),
           'device': 'cpu', 'threads': 1, 'torch_build': torch.__config__.show()}
    report['environment'] = env
    require(platform.system() == 'Linux' and env['python'] == '3.12.3', 'requires original Linux Python3.12.3')
    require((env['torch'], env['numpy'], env['einops']) == ('2.11.0+cpu','1.26.4','0.8.0'),
            'requires pinned CPU dependencies; no automatic installation/waiver')
    require(torch.get_default_dtype() == torch.float32, 'requires FP32 default')
    root = Path(git(HERE, 'rev-parse', '--show-toplevel'))
    require(not git(root,'status','--porcelain','--untracked-files=no'), 'dirty research sources')
    factory = root/'research/mini_mythos/m2_matched/experiment.py'
    require(file_sha(factory) == FACTORY_SHA, 'historical model factory changed')
    spec = importlib.util.spec_from_file_location('r1a_native_factory', factory)
    m2 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m2)
    m2.setup(args.parcae_dir)
    require(m2.PIN == PIN, 'wrong native pin')
    splits = make_splits()
    report.update(code_head=git(root,'rev-parse','HEAD'), source_pin=PIN,
                  source_sha256={n:file_sha(HERE/n) for n in ('PROTOCOL.md','task.py','run_cpu.py')},
                  factory_sha256=FACTORY_SHA, data=manifest(splits))
    require(all(report['data'][s]['sha256'] == h for s,h in EXPECTED_DATA.items()), 'task data drift')
    report['data_status'] = 'PASS'
    write(out/'data.json', splits)
    (out/'pip-freeze.txt').write_text(subprocess.check_output([sys.executable,'-m','pip','freeze'], text=True))
    encoded = [training_tokens(e) for e in splits['train']]
    train_x = torch.tensor([e[0] for e in encoded], dtype=torch.long)
    train_y = torch.tensor([e[1] for e in encoded], dtype=torch.long)
    require(train_x.shape[1] == 6 and bool(((train_y != -100).sum(1) == 3).all()), 'wrong task mask')
    # These are initial models, not old language-model trained checkpoints.
    pairs, rows_by_key, indices = {}, {}, {}
    history_path = factory.parent/'evidence/linux_e533fbe/pilot.json'
    require(file_sha(history_path) == '4960841f1f685326cf8a4c7d1198718346ef38b8ce0a3d0fb8d48d70daa0637d',
            'historical identity file drift')
    history = json.loads(history_path.read_text())
    for seed in SEEDS:
        pair = {'gpt':m2.make('gpt',60,seed), 'parcae':m2.make('parcae',64,seed)}
        shared = m2.pair_io(pair['gpt'], pair['parcae'])
        pairs[seed] = pair
        indices[seed] = torch.randint(len(train_x), (STEPS,BATCH),
                                     generator=torch.Generator().manual_seed(seed+11000))
        for arm, model in pair.items():
            initial = m2.weights_sha(model)
            old = next(r for r in history['rows'] if r['seed']==seed and r['arm']==arm)
            require(initial == old['initial_weights_sha256'], 'unexpected starting recipe')
            probe = task_probe(model,arm,train_x[:BATCH],train_y[:BATCH],torch,m2)
            row = {'seed':seed,'arm':arm,'status':'NOT TESTED','initial_model_sha256':initial,
                   'shared_io':shared,'budget_probe':probe,'batch_indices_sha256':m2.tensor_sha(indices[seed]),
                   'steps':STEPS,'supervised_target_tokens':STEPS*BATCH*3,
                   'input_token_positions':STEPS*BATCH*6,'problem_exposures':STEPS*BATCH}
            rows_by_key[seed,arm] = row
            report['rows'].append(row)
    report['paired_budgets'] = []
    for seed in SEEDS:
        a,b = (rows_by_key[seed,arm]['budget_probe'] for arm in ('gpt','parcae'))
        pr, cr = m2.ratio(a['parameters'],b['parameters']), m2.ratio(a['step_flops'],b['step_flops'])
        report['paired_budgets'].append({'seed':seed,'registered_parameter_ratio':pr,'counted_compute_ratio':cr})
        require(max(pr,cr) <= 1.10, 'task-shape budgets outside frozen tolerance; no auto-calibration')
    report['budget_status'] = 'PASS'
    write(out/'result.json',report)

    def train(arm, seed):
        model, row = pairs[seed][arm], rows_by_key[seed,arm]
        require(m2.weights_sha(model) == row['initial_model_sha256'], 'model changed before training')
        model.train()
        opt = torch.optim.AdamW(model.parameters(),lr=.002,betas=(.9,.999),eps=1e-8,weight_decay=0.)
        losses, norms = [], []
        started = time.perf_counter()
        with torch.random.fork_rng(devices=[]), sdpa_kernel(SDPBackend.MATH):
            torch.manual_seed(seed+2000)
            for step, ix in enumerate(indices[seed],1):
                opt.zero_grad(set_to_none=True)
                loss = native(model,arm,train_x[ix],train_y[ix])
                require(bool(torch.isfinite(loss)), 'nonfinite training loss')
                loss.backward()
                require(all(bool(torch.isfinite(p.grad).all()) for p in model.parameters() if p.grad is not None),
                        'nonfinite gradient')
                norm = float(torch.nn.utils.clip_grad_norm_(model.parameters(),1.))
                require(math.isfinite(norm), 'nonfinite gradient norm')
                opt.step()
                losses.append(float(loss.detach()))
                norms.append(norm)
                if step % 500 == 0:
                    print(json.dumps({'seed':seed,'arm':arm,'step':step,'training_loss':losses[-1]}),flush=True)
            rng = torch.get_rng_state().clone()
        row.update(training_seconds_descriptive=time.perf_counter()-started,loss_trace=losses,
                   gradient_norm_trace=norms,final_model_sha256=m2.weights_sha(model),
                   counted_training_flops=STEPS*row['budget_probe']['step_flops'])
        require(row['initial_model_sha256'] != row['final_model_sha256'], 'weights never changed')
        path = out/f'{arm}_{seed}_step{STEPS}.pt'
        torch.save({'model':model.state_dict(),'optimizer':opt.state_dict(),'cpu_rng':rng,
                    'seed':seed,'arm':arm,'step':STEPS,'batch_indices':indices[seed],
                    'data':report['data'],'source_head':report['code_head']},path)
        row.update(checkpoint_file=path.name,checkpoint_sha256=file_sha(path),status='PASS')
        row['validation_d2'] = evaluate(model,arm,splits['validation'],seed,2,torch)
        require(row['final_model_sha256'] == m2.weights_sha(model), 'validation mutated weights')
        write(out/'result.json',report)
        print(json.dumps({'seed':seed,'arm':arm,'validation_accuracy':
                          {k:v['accuracy'] for k,v in row['validation_d2']['metrics'].items()}}),flush=True)

    for seed in SEEDS:
        train('gpt',seed)
    report['baseline_learning_status'] = learning_gate(
        [rows_by_key[s,'gpt']['validation_d2']['metrics'] for s in SEEDS],'gpt')
    if report['baseline_learning_status'] != 'PASS':
        report.update(execution_status='PASS',execution_scope='three GPT controls only; planned learning-gate stop',
                      primary={'status':'BLOCKED','reason':'GPT_TASK_NOT_LEARNED'},exit_code=1)
        return finish(report,out,args,root,m2)
    for seed in SEEDS:
        train('parcae',seed)
    report['parcae_learning_status'] = learning_gate(
        [rows_by_key[s,'parcae']['validation_d2']['metrics'] for s in SEEDS],'parcae')
    if report['parcae_learning_status'] != 'PASS':
        report.update(execution_status='PASS',execution_scope='six training arms; test unexamined by learning-gate rule',
                      primary={'status':'BLOCKED','reason':'PARCAE_TASK_NOT_LEARNED'},exit_code=1)
        return finish(report,out,args,root,m2)
    # Only now measure held-out test once per prespecified model/depth condition.
    for seed in SEEDS:
        for arm, depths in (('gpt',(2,)),('parcae',(2,4))):
            row, model = rows_by_key[seed,arm], pairs[seed][arm]
            row['test'] = {str(d):evaluate(model,arm,splits['test'],seed,d,torch) for d in depths}
            require(row['final_model_sha256'] == m2.weights_sha(model), 'test mutated weights')
            write(out/'result.json',report)
            print(json.dumps({'seed':seed,'arm':arm,'test_accuracy':
                {d:{k:v['accuracy'] for k,v in e['metrics'].items()} for d,e in row['test'].items()}}),flush=True)
    report['primary'] = benefit([rows_by_key[s,'parcae']['test']['2']['metrics'] for s in SEEDS],
                                [rows_by_key[s,'parcae']['test']['4']['metrics'] for s in SEEDS])
    report['extra_inference_counted_cost_ratio'] = [rows_by_key[s,'parcae']['test']['4']['counted_full_generation_flops']/
           rows_by_key[s,'parcae']['test']['2']['counted_full_generation_flops'] for s in SEEDS]
    report.update(execution_status='PASS',execution_scope='all six training arms and nine final test conditions',
                  test_status='PASS',exit_code={'PASS':0,'FAIL':1,'BLOCKED':2}[report['primary']['status']])
    return finish(report,out,args,root,m2)


def finish(report,out,args,root,m2):
    m2.upstream_check(args.parcae_dir)
    require(not git(root,'status','--porcelain','--untracked-files=no'),'research sources changed')
    report['upstream_unchanged'] = True
    write(out/'result.json',report)
    print(json.dumps({k:report[k] for k in ('execution_status','execution_scope','baseline_learning_status',
                     'parcae_learning_status','test_status','primary')}),flush=True)
    print(file_sha(out/'result.json'), str(out/'result.json'),flush=True)
    return report['exit_code']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parcae-dir',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True,exist_ok=False)
    report = {'experiment':'MYTHOS-R1A-CARRY-ADDITION-CPU-V1','execution_status':'NOT TESTED',
              'execution_scope':'not started','data_status':'NOT TESTED','budget_status':'NOT TESTED',
              'baseline_learning_status':'NOT TESTED','parcae_learning_status':'NOT TESTED',
              'test_status':'NOT TESTED','primary':{'status':'NOT TESTED'},'rows':[],
              'review_status':'NOT TESTED / DEFERRED','exit_code':2,
              'limitations':['elementary in-distribution two-digit addition, not general reasoning',
                             'reversed answer representation, no length-generalization claim',
                             'known inactive native parameters preserved; not equal active capacity',
                             'counts exclude optimizer/hardware cost; no statistical superiority claim',
                             'no formal Oracle acceptance or automatic merge']}
    write(out/'result.json',report)
    try:
        return execute(args,out,report)
    except Exception:
        report.update(execution_status='BLOCKED',error=traceback.format_exc(),exit_code=2)
        write(out/'result.json',report)
        traceback.print_exc()
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
