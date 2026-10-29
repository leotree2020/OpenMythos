#!/usr/bin/env python3
"""Validation-only native Parcae depth diagnostic. No training/backward/optimizer.

Use a clean worktree, the existing pinned CPU Python, unmodified Parcae and the
existing M2-L evidence. Nothing is downloaded and existing outputs are not reused.
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
TEXT_SHA = '86c4e6aa9db7c042ec79f339dcb96d42b0075e16b8fc2e86bf0ca57e2dc565ed'
SEEDS = (42, 20261029, 20261030)
DEPTHS = (2, 1, 4, 8)
SEQ, EVAL_BATCH = 32, 32


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    return sha(path.read_bytes())


def git(path, *args):
    return subprocess.check_output(['git', '-C', str(path), *args], text=True).strip()


def write(path, data):
    temp = path.with_name(path.name + '.tmp')
    temp.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    os.replace(temp, path)


def state_hash(state):
    h = hashlib.sha256()
    for name, tensor in sorted(state.items()):
        h.update(name.encode())
        h.update(tensor.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


def select_row(pilot, seed):
    candidates = [r for r in pilot['rows'] if r['seed'] == seed and r['arm'] == 'parcae']
    require(len(candidates) == 1, 'missing/duplicate Parcae evidence row')
    row = candidates[0]
    require(row['status'] == 'PASS' and set(row['checkpoints']) == {'120', '480', '1920'},
            'incomplete original model trajectory')
    require(row['checkpoints']['1920']['step'] == 1920, 'wrong final step')
    return row


def load_snapshot(torch, evidence, row):
    info = row['checkpoints']['1920']
    name = info['checkpoint_file']
    require(name == f"parcae_{row['seed']}_step1920.pt", 'unexpected snapshot path')
    path = evidence / name
    require(path.is_file() and not path.is_symlink(), 'missing/symlink snapshot')
    require(file_sha(path) == info['checkpoint_sha256'], 'snapshot file SHA mismatch')
    saved = torch.load(path, map_location='cpu', weights_only=True)
    require((saved['arm'], saved['seed'], saved['step']) == ('parcae', row['seed'], 1920),
            'snapshot metadata mismatch')
    require(state_hash(saved['model']) == info['weight_sha256'] == row['final_weights_sha256'],
            'snapshot semantic weight hash mismatch')
    require(all(bool(torch.isfinite(t).all()) for t in saved['model'].values()),
            'nonfinite stored state')
    return saved['model']


def primary_verdict(rows):
    expected = {(s, d) for s in SEEDS for d in DEPTHS}
    keys = [(r['seed'], r['depth']) for r in rows]
    require(len(keys) == len(expected) and set(keys) == expected, 'incomplete or duplicate evaluation')
    index = {(r['seed'], r['depth']): r for r in rows}
    require(all(math.isfinite(r['metrics']['nll']) for r in rows), 'nonfinite NLL')
    differences = [index[s, 4]['metrics']['nll'] - index[s, 2]['metrics']['nll'] for s in SEEDS]
    mean = sum(differences) / len(differences)
    return {'status': 'PASS' if mean <= -.01 and max(differences) < 0 else 'FAIL',
            'comparison': 'depth4_minus_depth2', 'paired_nll_deltas': differences,
            'mean_nll_delta': mean, 'frozen_mean_max': -.01,
            'each_seed_requires_strict_improvement': True,
            'scope': 'exploratory validation-only fixed-weight depth extrapolation'}


def evaluate(torch, model, pool, depth):
    from torch.nn.attention import SDPBackend, sdpa_kernel
    starts = torch.arange(0, len(pool) - SEQ, SEQ)
    total = 0.0
    elapsed = time.perf_counter()
    model.eval()
    with torch.no_grad(), torch.random.fork_rng(devices=[]), sdpa_kernel(SDPBackend.MATH):
        torch.manual_seed(1212)
        for ids in starts.split(EVAL_BATCH):
            z = pool[ids[:, None] + torch.arange(SEQ + 1)]
            result = model(z[:, :-1].contiguous(), labels=z[:, 1:].contiguous(),
                           return_logits=False, num_steps_pair=[0, depth])
            value = float(result['loss'])
            require(math.isfinite(value), 'nonfinite native evaluation loss')
            total += value * len(ids) * SEQ
    tokens = len(starts) * SEQ
    nll = total / tokens
    return {'nll': nll, 'ppl': math.exp(nll), 'target_tokens': tokens,
            'windows': len(starts), 'discarded_target_tail': len(pool) - 1 - tokens,
            'window_starts_sha256': sha(starts.contiguous().numpy().tobytes())}, time.perf_counter()-elapsed


def forward_cost(torch, model, pool, depth, windows):
    from torch.nn.attention import SDPBackend, sdpa_kernel
    from torch.utils.flop_counter import FlopCounterMode
    full_batches, last_size = divmod(windows, EVAL_BATCH)
    sizes = sorted({EVAL_BATCH} | ({last_size} if last_size else set()))
    costs = {}
    with torch.no_grad(), torch.random.fork_rng(devices=[]), sdpa_kernel(SDPBackend.MATH):
        for size in sizes:
            torch.manual_seed(1212)
            ids = torch.arange(size) * SEQ
            z = pool[ids[:, None] + torch.arange(SEQ + 1)]
            with FlopCounterMode(display=False) as counter:
                model(z[:, :-1].contiguous(), labels=z[:, 1:].contiguous(),
                      return_logits=False, num_steps_pair=[0, depth])
            costs[size] = int(counter.get_total_flops())
            require(costs[size] > 0, 'no supported-op FLOP count')
    return {'full_batch_size': EVAL_BATCH, 'full_batches': full_batches,
            'last_batch_size': last_size, 'per_batch': costs,
            'total_validation_forward_flops': full_batches * costs[EVAL_BATCH] +
                (costs[last_size] if last_size else 0),
            'scope': 'supported forward operators only; no backward, optimizer or hardware FLOPs'}


def execute(args, result, out):
    import torch
    import numpy
    import einops
    env = {'python': platform.python_version(), 'torch': torch.__version__,
           'numpy': numpy.__version__, 'einops': einops.__version__,
           'platform': platform.platform()}
    result['review_runtime'] = env
    require(platform.system() == 'Linux' and platform.python_version() == '3.12.3',
            'requires original Linux Python 3.12.3; no packages installed automatically')
    require((torch.__version__, numpy.__version__, einops.__version__) ==
            ('2.11.0+cpu', '1.26.4', '0.8.0'), 'requires original CPU dependency builds')
    root = Path(git(Path(__file__).parent, 'rev-parse', '--show-toplevel'))
    require(not git(root, 'status', '--porcelain', '--untracked-files=no'), 'dirty research sources')
    require(git(args.parcae_dir, 'rev-parse', 'HEAD') == PIN, 'wrong upstream pin')
    require(not git(args.parcae_dir, 'status', '--porcelain', '--untracked-files=no'), 'dirty upstream')
    require(not out.is_relative_to(args.evidence.resolve()), 'output must not be inside evidence')
    pilot_path = args.evidence / 'pilot.json'
    require(file_sha(pilot_path) == PILOT_SHA, 'original pilot bytes changed')
    pilot = json.loads(pilot_path.read_text())
    require(pilot['code_head'] == '09d0d508fa0eef459c8b767b109b236f9490c014', 'wrong original experiment')
    require(pilot['original_parcae_pin'] == PIN, 'pilot upstream mismatch')
    raw = args.text.read_bytes()
    require(sha(raw) == TEXT_SHA, 'wrong corpus bytes')
    validation = raw[int(len(raw)*.8):int(len(raw)*.9)]
    require(sha(validation) == pilot['data']['val_sha256'], 'validation slice identity mismatch')
    reference = root / 'research/mini_mythos/m2_matched/experiment.py'
    require(file_sha(reference) == REF_SHA, 'reference model constructor changed')
    spec = importlib.util.spec_from_file_location('m2_depth_reference', reference)
    require(spec is not None and spec.loader is not None, 'reference import unavailable')
    m2 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m2)
    m2.setup(args.parcae_dir)
    pool = torch.tensor(list(validation), dtype=torch.long)
    result.update(code_head=git(root, 'rev-parse', 'HEAD'), upstream_pin=PIN,
                  script_sha256=file_sha(Path(__file__)), protocol_sha256=file_sha(Path(__file__).with_name('PROTOCOL.md')),
                  reference_sha256=REF_SHA, pilot_sha256=PILOT_SHA,
                  corpus_sha256=TEXT_SHA, validation_sha256=sha(validation),
                  baseline_status='NOT TESTED', primary_status='NOT TESTED', rows=[])
    write(out/'result.json', result)
    models, old_rows = {}, {}
    for seed in SEEDS:
        old = select_row(pilot, seed)
        model = m2.make('parcae', 64, seed)
        model.load_state_dict(load_snapshot(torch, args.evidence, old), strict=True)
        require(m2.weights_sha(model) == old['final_weights_sha256'], 'loaded full state mismatch')
        model.eval()
        models[seed], old_rows[seed] = model, old
    # All historical baselines must pass BEFORE any off-depth score is read.
    for depth in DEPTHS:
        for seed in SEEDS:
            model, old = models[seed], old_rows[seed]
            before = m2.weights_sha(model)
            metrics, seconds = evaluate(torch, model, pool, depth)
            if depth == 2:
                require(metrics == old['checkpoints']['1920']['val'],
                        f'BLOCKED_REFERENCE_REPLAY: seed {seed}; actual={metrics}')
            costs = forward_cost(torch, model, pool, depth, metrics['windows'])
            require(m2.weights_sha(model) == before == old['final_weights_sha256'], 'state mutated')
            require(all(p.grad is None for p in model.parameters()), 'unexpected gradient generated')
            row = {'seed': seed, 'depth': depth, 'metrics': metrics, 'counts': costs,
                   'elapsed_seconds_descriptive': seconds, 'weight_sha256': before,
                   'weights_unchanged': True, 'gradient_operations': 0}
            result['rows'].append(row)
            write(out/'result.json', result)
            print(json.dumps({'seed': seed, 'depth': depth, 'validation_nll': metrics['nll'],
                              'counted_forward_flops': costs['total_validation_forward_flops']}), flush=True)
        if depth == 2:
            result['baseline_status'] = 'PASS'
            write(out/'result.json', result)
    for row in result['rows']:
        baseline = next(x for x in result['rows'] if x['seed'] == row['seed'] and x['depth'] == 2)
        row['counted_compute_ratio_to_depth2'] = row['counts']['total_validation_forward_flops'] / baseline['counts']['total_validation_forward_flops']
        row['nll_delta_from_depth2'] = row['metrics']['nll'] - baseline['metrics']['nll']
    result['primary'] = primary_verdict(result['rows'])
    require(not git(args.parcae_dir, 'status', '--porcelain', '--untracked-files=no'), 'upstream changed')
    result.update(execution_status='PASS', primary_status=result['primary']['status'],
                  efficiency_superiority='NOT TESTED', grok_or_claude_review='NOT TESTED',
                  A_M2L_02='OPEN; saved complete state loaded; initialization not reconstructed')
    write(out/'result.json', result)
    print(json.dumps({'execution': result['execution_status'], 'baseline': result['baseline_status'],
                      'primary': result['primary']}), flush=True)
    return 0 if result['primary_status'] == 'PASS' else 1


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--parcae-dir', type=Path, required=True)
    p.add_argument('--evidence', type=Path, required=True)
    p.add_argument('--text', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    out = args.out.resolve()
    # Prevent replacing an old experiment or any M2-L evidence.
    require(not out.is_relative_to(args.evidence.resolve()), 'output must be outside original evidence')
    out.mkdir(parents=True, exist_ok=False)
    result = {'experiment': 'MYTHOS-M2D-FIXED-WEIGHT-DEPTH-V1',
              'execution_status': 'NOT TESTED', 'primary_status': 'NOT TESTED',
              'limitations': ['validation-only exploratory depth extrapolation of depth2-trained weights',
                             'inactive native parameter paths retained', 'no training or Alice evaluation',
                             'no model superiority or statistical inference claim']}
    try:
        return execute(args, result, out)
    except Exception:
        result.update(execution_status='BLOCKED', error=traceback.format_exc())
        write(out/'result.json', result)
        traceback.print_exc()
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
