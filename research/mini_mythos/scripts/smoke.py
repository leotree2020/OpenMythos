#!/usr/bin/env python3
"""Runtime correctness probes against OpenMythos as imported from checkout."""
import argparse
import traceback
import time
from pathlib import Path
import torch
import torch.nn.functional as F
from common import get_repo, commit_id, tiny_config, load_upstream, toy_batch, atomic_json


def run_probe(label, fn, results):
    try:
        detail = fn()
        results.append({'name': label, 'status': 'PASS', 'details': detail})
    except Exception as exc:
        results.append({'name': label, 'status': 'FAIL', 'error': repr(exc),
                        'traceback': traceback.format_exc(limit=5)})


def test_model(module, device, attention):
    torch.manual_seed(123)
    model = module.OpenMythos(tiny_config(module, attention)).to(device)
    model.train()
    x, y = toy_batch(torch, 800, device=device)
    out = model(x, n_loops=2)
    assert out.shape == (2, 16, 96), out.shape
    assert torch.isfinite(out).all(), 'nonfinite logits'
    loss = F.cross_entropy(out.reshape(-1, 96), y.reshape(-1))
    loss.backward()
    norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
    assert torch.isfinite(norm), 'nonfinite gradient norm'
    return {'params': sum(p.numel() for p in model.parameters()),
            'train_loss': float(loss), 'grad_norm_before_clip': float(norm)}


def causal_probe(module, device, attention):
    torch.manual_seed(123)
    model = module.OpenMythos(tiny_config(module, attention)).to(device).eval()
    x, _ = toy_batch(torch, 801, batch_size=1, device=device)
    changed = x.clone()
    changed[:, 9:] = (changed[:, 9:] + 23) % 96
    with torch.no_grad():
        a = model(x, n_loops=2)
        b = model(changed, n_loops=2)
    diff = float((a[:, :9] - b[:, :9]).abs().max())
    assert diff < 3e-4, f'future leaked to past logits: max_abs={diff}'
    return {'max_abs_diff_past': diff, 'tolerance': 3e-4}


def kv_cache_probe(module, device, attention):
    torch.manual_seed(123)
    model = module.OpenMythos(tiny_config(module, attention)).to(device).eval()
    x, _ = toy_batch(torch, 802, batch_size=1, device=device)
    with torch.no_grad():
        full = model(x, n_loops=2)[:, -1, :]
        cache = {}
        model(x[:, :-1], n_loops=2, kv_cache=cache, start_pos=0)
        incremental = model(x[:, -1:], n_loops=2, kv_cache=cache, start_pos=x.shape[1]-1)[:, -1, :]
    max_diff = float((full - incremental).abs().max())
    assert max_diff < 5e-4, f'cache inconsistent: max_abs={max_diff}'
    return {'max_abs_diff_full_vs_cached': max_diff, 'cache_layers': sorted(cache)}


def act_mass_probe(module, device, attention):
    torch.manual_seed(123)
    model = module.OpenMythos(tiny_config(module, attention)).to(device).eval()
    x, _ = toy_batch(torch, 803, batch_size=1, device=device)
    summary = []
    for loops in (1, 2, 4, 8):
        probabilities = []
        hook = model.recurrent.act.register_forward_hook(
            lambda _m, _inputs, output: probabilities.append(output.detach().float().cpu()))
        try:
            with torch.no_grad():
                model(x, n_loops=loops)
        finally:
            hook.remove()
        total = torch.zeros_like(probabilities[0])
        halts = torch.zeros_like(total, dtype=torch.bool)
        mass = torch.zeros_like(total)
        for p in probabilities:
            running = ~halts
            remaining = (1.0-total).clamp(min=0)
            w = torch.where(total + p >= model.cfg.act_threshold, remaining, p)
            mass += w * running.float()
            total += p * running.float()
            halts |= total >= model.cfg.act_threshold
        summary.append({'requested_loops': loops, 'actual_loops': len(probabilities),
                        'weight_mean': float(mass.mean()), 'weight_min': float(mass.min()),
                        'weight_max': float(mass.max())})
    return summary


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--repo', default='.')
    p.add_argument('--device', default='cpu')
    p.add_argument('--attention', choices=['gqa', 'mla'], default='gqa')
    p.add_argument('--out', default='research/mini_mythos/results/smoke.json')
    a = p.parse_args()
    repo = get_repo(a.repo)
    module = load_upstream(repo)
    data = {'upstream_commit': commit_id(repo), 'torch': torch.__version__,
            'device': a.device, 'attention': a.attention, 'checks': []}
    probes = [
        ('forward_backward', lambda: test_model(module, a.device, a.attention)),
        ('causal_invariance', lambda: causal_probe(module, a.device, a.attention)),
        ('kv_cache_equivalence', lambda: kv_cache_probe(module, a.device, a.attention)),
        ('act_weight_mass', lambda: act_mass_probe(module, a.device, a.attention)),
    ]
    for name, fn in probes:
        start = time.perf_counter()
        run_probe(name, fn, data['checks'])
        data['checks'][-1]['elapsed_s'] = round(time.perf_counter() - start, 3)
        print(name, data['checks'][-1]['status'])
        if data['checks'][-1]['status'] == 'FAIL':
            print('  ', data['checks'][-1]['error'])
    atomic_json(a.out, data)
    print('Saved:', a.out)
    if any(c['status'] == 'FAIL' for c in data['checks']):
        raise SystemExit(1)

if __name__ == '__main__':
    main()
