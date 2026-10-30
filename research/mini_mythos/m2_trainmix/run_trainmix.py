#!/usr/bin/env python3
"""M2-T: paired fixed2 vs mixed1/3 native Parcae continuation, CPU only.

This is a new training-distribution experiment, not a patch of upstream or a
repeat of M2-D. It restores separate copies of model/AdamW/RNG per arm and
requires matched data, RNG streams and measured counted-op budgets.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import traceback

os.environ['CUDA_VISIBLE_DEVICES'] = ''
os.environ['TORCHDYNAMO_DISABLE'] = '1'
sys.dont_write_bytecode = True
PIN = '69284c13746e849104f738d6d1a347b1f457df76'
PILOT_SHA = 'c5be0f6da8eab77ab499ad97a3aaf318633d2d44f234083165ffcacc3b26d7bb'
REF_SHA = '74f00c64448ddbc224a48ef83dc031a90c33448ccb92647666707f6b8f988967'
DEPTH_HARNESS_SHA = '64a168b5b1dd94179171606ba74a4939febedc8fd857a80d730ed3f66eb78a88'
TEXT_SHA = '86c4e6aa9db7c042ec79f339dcb96d42b0075e16b8fc2e86bf0ca57e2dc565ed'
SEEDS = (42, 20261029, 20261030)
ARMS = ('fixed2', 'mixed13')
CUT, EXTRA, SEQ, BATCH = 1920, 480, 32, 8


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    return sha(path.read_bytes())


def tensor_sha(tensor):
    return sha(tensor.detach().cpu().contiguous().numpy().tobytes())


def git(path, *args):
    return subprocess.check_output(['git', '-C', str(path), *args], text=True).strip()


def write(path, obj):
    temp = path.with_name(path.name + '.tmp')
    temp.write_text(json.dumps(obj, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    os.replace(temp, path)


def save(path, obj, torch):
    temp = path.with_name(path.name + '.tmp')
    torch.save(obj, temp)
    os.replace(temp, path)


def import_reference(name, path, expected):
    require(file_sha(path) == expected, 'reference source identity mismatch: ' + str(path))
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, 'reference import failed')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def object_sha(obj, torch):
    """Stable typed digest, not a claim of authenticated evidence custody."""
    h = hashlib.sha256()
    def visit(value):
        if torch.is_tensor(value):
            h.update(b'tensor:')
            h.update(str(value.dtype).encode())
            h.update(str(tuple(value.shape)).encode())
            h.update(value.detach().cpu().contiguous().numpy().tobytes())
        elif isinstance(value, dict):
            h.update(b'dict:')
            for key in sorted(value, key=lambda k: (type(k).__name__, str(k))):
                visit(key)
                visit(value[key])
        elif isinstance(value, (tuple, list)):
            h.update((type(value).__name__ + ':').encode())
            for item in value:
                visit(item)
        else:
            h.update((type(value).__name__ + ':').encode())
            h.update(json.dumps(value, sort_keys=True, allow_nan=False).encode())
        h.update(b'\0')
    visit(obj)
    return h.hexdigest()


def schedules(torch, seed):
    """Each pair totals four core calls, identically budgeted to two depth2 steps."""
    generator = torch.Generator().manual_seed(seed + 37000)
    order = torch.randint(0, 2, (EXTRA // 2,), generator=generator).tolist()
    mixed = [depth for bit in order for depth in ((1, 3) if bit == 0 else (3, 1))]
    return {'fixed2': [2] * EXTRA, 'mixed13': mixed}


def verdict(rows):
    expected = {(seed, arm) for seed in SEEDS for arm in ARMS}
    keys = [(r['seed'], r['arm']) for r in rows]
    require(len(keys) == len(expected) and set(keys) == expected, 'incomplete/duplicate result rows')
    index = {(r['seed'], r['arm']): r for r in rows}
    p, s, e, interactions = [], [], [], []
    for seed in SEEDS:
        a, b = index[seed, 'fixed2'], index[seed, 'mixed13']
        values = [r['validation'][str(depth)]['nll'] for r in (a, b) for depth in (2, 4)]
        require(all(math.isfinite(x) for x in values), 'nonfinite endpoint')
        a2, a4, b2, b4 = values
        p.append(b4 - a4)
        s.append(b2 - a2)
        e.append(b4 - b2)
        interactions.append((b4 - b2) - (a4 - a2))
    primary = sum(p)/3 <= -.01 and max(p) < 0
    safeguard = sum(s)/3 <= .02 and max(s) <= .05
    depth_benefit = sum(e)/3 <= -.01 and max(e) < 0
    return {'primary_status': 'PASS' if primary else 'FAIL',
            'depth2_safeguard_status': 'PASS' if safeguard else 'FAIL',
            'intervention_status': 'PASS' if primary and safeguard else 'FAIL',
            'extra_inference_benefit_status': 'PASS' if depth_benefit else 'FAIL',
            'mixed_minus_fixed_at_depth4': p,
            'mean_mixed_minus_fixed_at_depth4': sum(p)/3,
            'mixed_minus_fixed_at_depth2': s,
            'mixed_depth4_minus_depth2': e,
            'gap_difference_in_differences': interactions,
            'scope': 'exploratory validation-only schedule intervention; no general efficiency/ACT claim'}


def load_start(torch, model, row, evidence, depth_module):
    info = row['checkpoints']['1920']
    name = f"parcae_{row['seed']}_step1920.pt"
    require(info['checkpoint_file'] == name, 'invalid snapshot name')
    path = evidence / name
    require(path.is_file() and not path.is_symlink(), 'missing/symlink start snapshot')
    require(file_sha(path) == info['checkpoint_sha256'], 'input snapshot SHA mismatch')
    state = torch.load(path, map_location='cpu', weights_only=True)
    require((state['arm'], state['seed'], state['step']) == ('parcae', row['seed'], CUT),
            'input snapshot metadata mismatch')
    require(depth_module.state_hash(state['model']) == info['weight_sha256'] == row['final_weights_sha256'],
            'input semantic weight hash mismatch')
    model.load_state_dict(state['model'], strict=True)
    params = list(model.named_parameters())
    state_parameter_names = [name for name in state['model'] if name in dict(params)]
    require(state_parameter_names == [name for name, _ in params], 'parameter order differs from saved model')
    saved_opt = state['optimizer']
    require(len(saved_opt['param_groups']) == 1, 'unexpected optimizer grouping')
    group = saved_opt['param_groups'][0]
    require(group['params'] == list(range(len(params))), 'optimizer IDs not in original order')
    require((group['lr'], group['betas'], group['eps'], group['weight_decay']) ==
            (.002, (.9, .999), 1e-8, 0.), 'optimizer hyperparameter mismatch')
    for idx, moments in saved_opt['state'].items():
        require(0 <= idx < len(params), 'optimizer state ID outside parameters')
        shape = params[idx][1].shape
        require(moments['exp_avg'].shape == moments['exp_avg_sq'].shape == shape,
                'optimizer moment shape mismatch')
        require(int(moments['step']) == CUT, 'start optimizer counter mismatch')
    optimizer = torch.optim.AdamW(model.parameters(), lr=.002, betas=(.9,.999), eps=1e-8, weight_decay=0.)
    optimizer.load_state_dict(saved_opt)
    require(object_sha(optimizer.state_dict(), torch) == object_sha(saved_opt, torch),
            'loaded optimizer does not reproduce saved state')
    require(torch.is_tensor(state['rng']) and state['rng'].dtype == torch.uint8, 'bad CPU RNG state')
    torch.Generator().set_state(state['rng'])
    identity = {'snapshot_sha256': file_sha(path), 'model_sha256': depth_module.state_hash(model.state_dict()),
                'optimizer_sha256': object_sha(optimizer.state_dict(), torch),
                'rng_sha256': tensor_sha(state['rng'])}
    return optimizer, state['rng'].clone(), identity


def measured_training_cost(torch, model, depth):
    from torch.nn.attention import SDPBackend, sdpa_kernel
    from torch.utils.flop_counter import FlopCounterMode
    x = torch.arange(BATCH*SEQ).reshape(BATCH, SEQ) % 256
    y = (x + 1) % 256
    model.train()
    model.zero_grad(set_to_none=True)
    with torch.random.fork_rng(devices=[]), sdpa_kernel(SDPBackend.MATH):
        torch.manual_seed(9001)
        with FlopCounterMode(display=False) as counter:
            value = model(x, labels=y, return_logits=False, num_steps_pair=[0, depth])['loss']
            forward = int(counter.get_total_flops())
            value.backward()
            total = int(counter.get_total_flops())
    model.zero_grad(set_to_none=True)
    require(total > forward > 0, 'invalid counted training cost')
    return {'forward': forward, 'backward': total-forward, 'step': total}


def execute(args, out, report):
    import torch
    import numpy
    import einops
    from torch.nn.attention import SDPBackend, sdpa_kernel
    env = {'python': platform.python_version(), 'torch': torch.__version__,
           'numpy': numpy.__version__, 'einops': einops.__version__, 'platform': platform.platform()}
    report['environment'] = env
    require(platform.system() == 'Linux' and platform.python_version() == '3.12.3', 'pinned Linux Python 3.12.3 required')
    require((torch.__version__, numpy.__version__, einops.__version__) ==
            ('2.11.0+cpu', '1.26.4', '0.8.0'), 'pinned CPU dependency versions required')
    root = Path(git(Path(__file__).parent, 'rev-parse', '--show-toplevel'))
    require(not git(root, 'status', '--porcelain', '--untracked-files=no'), 'modified tracked research source')
    require(git(args.parcae_dir, 'rev-parse', 'HEAD') == PIN, 'wrong native source pin')
    require(not git(args.parcae_dir, 'status', '--porcelain', '--untracked-files=no'), 'modified native source')
    m2 = import_reference('m2t_reference', root/'research/mini_mythos/m2_matched/experiment.py', REF_SHA)
    dmod = import_reference('m2t_depth_reference', root/'research/mini_mythos/m2_depth/run_depth.py', DEPTH_HARNESS_SHA)
    m2.setup(args.parcae_dir)
    require(file_sha(args.evidence/'pilot.json') == PILOT_SHA, 'input pilot hash mismatch')
    pilot = json.loads((args.evidence/'pilot.json').read_text())
    require(pilot['original_parcae_pin'] == PIN, 'input pilot source pin mismatch')
    raw = args.text.read_bytes()
    require(sha(raw) == TEXT_SHA, 'input text identity mismatch')
    train_bytes, val_bytes = raw[:int(len(raw)*.8)], raw[int(len(raw)*.8):int(len(raw)*.9)]
    require(sha(train_bytes) == pilot['data']['train_sha256'] and
            sha(val_bytes) == pilot['data']['val_sha256'], 'train/validation intervals mismatch')
    train, val = [torch.tensor(list(b), dtype=torch.long) for b in (train_bytes, val_bytes)]
    reference_rows = {seed: dmod.select_row(pilot, seed) for seed in SEEDS}
    report.update(code_head=git(root, 'rev-parse', 'HEAD'), source_pin=PIN,
                  script_sha256=file_sha(Path(__file__)), protocol_sha256=file_sha(Path(__file__).with_name('PROTOCOL.md')),
                  source_pilot_sha256=PILOT_SHA, reference_sha256=REF_SHA, depth_reference_sha256=DEPTH_HARNESS_SHA,
                  train_sha256=sha(train_bytes), val_sha256=sha(val_bytes), rows=[], baselines=[])
    (out/'pip-freeze.txt').write_text(subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'], text=True))
    costs = None
    # Verify ALL originals before any new optimizer update is permitted.
    for seed in SEEDS:
        model = m2.make('parcae', 64, seed)
        _, _, identity = load_start(torch, model, reference_rows[seed], args.evidence, dmod)
        baseline, _ = dmod.evaluate(torch, model, val, 2)
        require(baseline == reference_rows[seed]['checkpoints']['1920']['val'], 'baseline reevaluation mismatch')
        report['baselines'].append({'seed': seed, 'status': 'PASS', 'metrics': baseline, 'start': identity})
        if costs is None:
            costs = {str(d): measured_training_cost(torch, model, d) for d in (1, 2, 3)}
            require(costs['1']['step'] + costs['3']['step'] == 2 * costs['2']['step'],
                    'BLOCKED_BUDGET: mixed counted cost is not exactly matched')
            require(costs['2']['step'] == reference_rows[seed]['counts']['step_flops'], 'old depth2 cost drift')
            require(m2.weights_sha(model) == identity['model_sha256'], 'counting mutated model state')
        del model
    report.update(baseline_status='PASS', measured_costs=costs,
                  planned_counted_training_flops=EXTRA*costs['2']['step'], baseline_claim='exact saved depth2 validation only')
    write(out/'result.json', report)
    print(json.dumps({'preflight': 'PASS', 'equal_counted_training_flops': report['planned_counted_training_flops']}), flush=True)

    for seed in SEEDS:
        old = reference_rows[seed]
        generator = torch.Generator().manual_seed(seed+11)
        all_starts = torch.randint(len(train)-SEQ, (CUT+EXTRA, BATCH), generator=generator)
        require(tensor_sha(all_starts[:CUT]) == old['batch_starts_sha256_all'], 'historical data prefix mismatch')
        starts = all_starts[CUT:]
        plan = schedules(torch, seed)
        for arm in ARMS:
            # Always reload the original file: optimizer tensors must NOT alias the prior arm.
            model = m2.make('parcae', 64, seed)
            optimizer, rng, start_identity = load_start(torch, model, old, args.evidence, dmod)
            require(start_identity == next(x['start'] for x in report['baselines'] if x['seed'] == seed),
                    'paired starting state mismatch')
            losses, gradients, rng_hashes = [], [], []
            wall = 0.0
            with torch.random.fork_rng(devices=[]), sdpa_kernel(SDPBackend.MATH):
                torch.set_rng_state(rng)
                for ix, (ids, depth) in enumerate(zip(starts, plan[arm]), 1):
                    rng_hashes.append(tensor_sha(torch.get_rng_state()))
                    t0 = time.perf_counter()
                    model.train()
                    optimizer.zero_grad(set_to_none=True)
                    x, y = m2.window(train, ids)
                    value = model(x, labels=y, return_logits=False,
                                  num_steps_pair=[0, depth])['loss']
                    if not bool(torch.isfinite(value)):
                        raise FloatingPointError('nonfinite training loss')
                    value.backward()
                    if not all(bool(torch.isfinite(p.grad).all()) for p in model.parameters() if p.grad is not None):
                        raise FloatingPointError('nonfinite gradient')
                    gn = float(torch.nn.utils.clip_grad_norm_(model.parameters(), 1.))
                    if not math.isfinite(gn):
                        raise FloatingPointError('nonfinite gradient norm')
                    optimizer.step()
                    wall += time.perf_counter()-t0
                    losses.append(float(value.detach()))
                    gradients.append(gn)
                    if ix % 120 == 0:
                        print(json.dumps({'seed': seed, 'arm': arm, 'new_steps': ix, 'train_nll': losses[-1]}), flush=True)
                saved_rng = torch.get_rng_state().clone()
            model_hash = m2.weights_sha(model)
            require(model_hash != start_identity['model_sha256'], 'no model update')
            for state in optimizer.state.values():
                require(int(state['step']) == CUT+EXTRA, 'final optimizer counter mismatch')
            validation, inference_cost = {}, {}
            for depth in (2, 4):
                validation[str(depth)], _ = dmod.evaluate(torch, model, val, depth)
                inference_cost[str(depth)] = dmod.forward_cost(torch, model, val, depth, validation[str(depth)]['windows'])
            require(m2.weights_sha(model) == model_hash, 'evaluation mutated weights')
            checkpoint = out/f'{arm}_{seed}_step2400.pt'
            save(checkpoint, {'model': model.state_dict(), 'optimizer': optimizer.state_dict(), 'rng': saved_rng,
                              'seed': seed, 'arm': arm, 'step': CUT+EXTRA, 'model_sha256': model_hash,
                              'loss_trace': losses, 'gradient_norm_trace': gradients,
                              'depth_schedule': plan[arm], 'code_head': report['code_head']}, torch)
            row = {'seed': seed, 'arm': arm, 'status': 'PASS', 'start': start_identity,
                   'train_batch_sha256': tensor_sha(starts), 'new_steps': EXTRA,
                   'new_target_tokens': EXTRA*BATCH*SEQ, 'depth_schedule': plan[arm],
                   'sum_core_calls': sum(plan[arm]), 'counted_training_flops': sum(costs[str(d)]['step'] for d in plan[arm]),
                   'training_seconds_descriptive': wall, 'rng_before_forward_sha256': rng_hashes,
                   'loss_trace': losses, 'gradient_norm_trace': gradients, 'validation': validation,
                   'inference_counts': inference_cost, 'final_model_sha256': model_hash,
                   'checkpoint_file': checkpoint.name, 'checkpoint_sha256': file_sha(checkpoint)}
            report['rows'].append(row)
            write(out/f'{arm}_{seed}.json', row)
            write(out/'result.json', report)
            del model, optimizer
        a, b = report['rows'][-2:]
        for key in ('start', 'train_batch_sha256', 'new_steps', 'new_target_tokens',
                    'sum_core_calls', 'counted_training_flops', 'rng_before_forward_sha256', 'inference_counts'):
            require(a[key] == b[key], 'paired controlled comparison mismatch: ' + key)
        print(json.dumps({'seed': seed, 'paired_controls': 'PASS',
                          'mixed_minus_fixed_depth4': b['validation']['4']['nll']-a['validation']['4']['nll']}), flush=True)
    for seed in SEEDS:
        info = reference_rows[seed]['checkpoints']['1920']
        require(file_sha(args.evidence/info['checkpoint_file']) == info['checkpoint_sha256'], 'original evidence changed')
    require(not git(args.parcae_dir, 'status', '--porcelain', '--untracked-files=no'), 'upstream source changed')
    report.update(execution_status='PASS', budget_status='PASS', outcome=verdict(report['rows']),
                  independent_review='NOT TESTED', initializer_issue='A-M2L-02 OPEN; complete stored state used',
                  inference_superiority='NOT ESTABLISHED', original_results='M2-L/M2-D negative results retained')
    write(out/'result.json', report)
    print(json.dumps({'execution': 'PASS', 'budget': 'PASS', 'outcome': report['outcome']}), flush=True)
    return 0 if report['outcome']['intervention_status'] == 'PASS' else 1


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--parcae-dir', type=Path, required=True)
    p.add_argument('--evidence', type=Path, required=True)
    p.add_argument('--text', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    out = args.out.resolve()
    require(not out.is_relative_to(args.evidence.resolve()), 'output must be outside original evidence')
    out.mkdir(parents=True, exist_ok=False)
    report = {'experiment': 'MYTHOS-M2T-PAIRED-TRAINING-DEPTH-V1', 'execution_status': 'NOT TESTED',
              'budget_status': 'NOT TESTED', 'outcome': None,
              'limitations': ['within-Parcae training schedule only', 'already explored validation interval',
                              'no test or Alice evaluation', 'native inactive parameters unchanged',
                              'not general ACT, inference efficiency or reasoning evidence']}
    try:
        return execute(args, out, report)
    except Exception as exc:
        report.update(execution_status='FAIL' if isinstance(exc, FloatingPointError) else 'BLOCKED',
                      error=traceback.format_exc())
        write(out/'result.json', report)
        traceback.print_exc()
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
