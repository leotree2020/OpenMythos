#!/usr/bin/env python3
"""Reproducible ACT final-remainder A/B experiment on the actual upstream model.

No upstream source edits. The candidate arm installs a temporary hook that
makes the final ACT probability 1; in the pinned upstream recurrence this
selects the remainder weight. Tiny random models and synthetic tokens only.
Neither improved reasoning nor trained-model quality is claimed.
"""
import argparse
import copy
import math
import time

import torch
import torch.nn.functional as F

from act_math import act_accounting
from act_dynamics import summarize_act_pair, first_trace_event
from act_remainder import act_probability_hook
from common import atomic_json, commit_id, get_repo, load_upstream, tiny_config, toy_batch


def gradient_vector(model):
    return torch.cat([
        p.grad.detach().float().reshape(-1).cpu() if p.grad is not None
        else torch.zeros(p.numel(), dtype=torch.float32)
        for p in model.parameters() if p.requires_grad
    ])


def parameter_vector(model):
    return torch.cat([p.detach().float().reshape(-1).cpu() for p in model.parameters()])


def loss_for(logits, targets):
    return F.cross_entropy(logits.reshape(-1, logits.shape[-1]), targets.reshape(-1))


def evaluate_pair(original, candidate, depth, device, seeds):
    original.eval()
    candidate.eval()
    baseline_losses, corrected_losses = [], []
    with torch.no_grad():
        for seed in seeds:
            x, y = toy_batch(torch, seed, device=device)
            a = original(x, n_loops=depth)
            with act_probability_hook(candidate, depth, force_final=True):
                b = candidate(x, n_loops=depth)
            baseline_losses.append(float(loss_for(a, y)))
            corrected_losses.append(float(loss_for(b, y)))
    return {'original_loss': sum(baseline_losses) / len(baseline_losses),
            'forced_final_loss': sum(corrected_losses) / len(corrected_losses),
            'heldout_batches': len(seeds)}


def run_arm(module, attention, depth, *, device, seed, steps, lr):
    torch.manual_seed(seed)
    cfg = tiny_config(module, attention)
    original = module.OpenMythos(cfg).to(device)
    candidate = copy.deepcopy(original)
    optimizer_a = torch.optim.AdamW(original.parameters(), lr=lr)
    optimizer_b = torch.optim.AdamW(candidate.parameters(), lr=lr)
    initial_parameter_delta = float(torch.linalg.vector_norm(parameter_vector(original) - parameter_vector(candidate)))
    assert initial_parameter_delta == 0.0, 'A/B weights differ at initialization'

    train_trace = []
    initial = None
    for step in range(steps):
        original.train()
        candidate.train()
        x, y = toy_batch(torch, seed + 1000 + step, device=device)
        optimizer_a.zero_grad(set_to_none=True)
        optimizer_b.zero_grad(set_to_none=True)
        observed_a, observed_b = [], []
        with act_probability_hook(original, depth, observed=observed_a):
            logits_a = original(x, n_loops=depth)
        with act_probability_hook(candidate, depth, force_final=True,
                                  observed=observed_b):
            logits_b = candidate(x, n_loops=depth)
        if not bool(torch.isfinite(logits_a).all() and torch.isfinite(logits_b).all()):
            raise RuntimeError(f'Nonfinite logits at attention={attention}, depth={depth}, step={step}')
        loss_a, loss_b = loss_for(logits_a, y), loss_for(logits_b, y)
        loss_a.backward()
        loss_b.backward()
        grad_a, grad_b = gradient_vector(original), gradient_vector(candidate)
        if not bool(torch.isfinite(grad_a).all() and torch.isfinite(grad_b).all()):
            raise RuntimeError(f'Nonfinite gradients at attention={attention}, depth={depth}, step={step}')

        mass_metrics = summarize_act_pair(observed_a, observed_b, cfg.act_threshold)
        logits_delta = float((logits_a - logits_b).detach().abs().max())
        gradient_delta = float(torch.linalg.vector_norm(grad_a - grad_b))

        if step == 0:
            original_stats = act_accounting(torch.stack(observed_a), cfg.act_threshold)
            patched_stats = act_accounting(torch.stack(observed_b), cfg.act_threshold)
            expected_stats = act_accounting(torch.stack(observed_a), cfg.act_threshold,
                                            force_final_remainder=True)
            max_mass_error = float((patched_stats.probability_mass - expected_stats.probability_mass).abs().max())
            if max_mass_error > 2e-6 or not torch.allclose(patched_stats.probability_mass,
                                                           torch.ones_like(patched_stats.probability_mass), atol=2e-6):
                raise RuntimeError(f'Counterfactual accounting mismatch (error={max_mass_error})')
            initial = {
                'original_actual_loops': len(observed_a), 'forced_actual_loops': len(observed_b),
                'original_mass_min': float(original_stats.probability_mass.min()),
                'original_mass_mean': float(original_stats.probability_mass.mean()),
                'forced_mass_mean': float(patched_stats.probability_mass.mean()),
                'oracle_mass_max_error': max_mass_error,
                'logits_max_abs_diff': float((logits_a - logits_b).detach().abs().max()),
                'logits_mean_abs_diff': float((logits_a - logits_b).detach().abs().mean()),
                'gradient_l2_original': float(torch.linalg.vector_norm(grad_a)),
                'gradient_l2_forced': float(torch.linalg.vector_norm(grad_b)),
                'gradient_l2_difference': float(torch.linalg.vector_norm(grad_a - grad_b)),
            }

        norm_a = torch.nn.utils.clip_grad_norm_(original.parameters(), 1.0)
        norm_b = torch.nn.utils.clip_grad_norm_(candidate.parameters(), 1.0)
        train_trace.append({'step': step + 1, 'original_loss': float(loss_a.detach()),
                            'forced_final_loss': float(loss_b.detach()),
                            'original_grad_norm_preclip': float(norm_a),
                            'forced_grad_norm_preclip': float(norm_b),
                            **mass_metrics,
                            'logits_max_abs_diff': logits_delta,
                            'gradient_l2_difference': gradient_delta})
        optimizer_a.step()
        optimizer_b.step()

    heldout = evaluate_pair(original, candidate, depth, device, (99001, 99002, 99003))
    dynamics = {
        'first_original_mass_deficit_step': first_trace_event(
            train_trace, 'original_act_mass_deficit_max', threshold=1e-6),
        'first_logits_difference_step': first_trace_event(
            train_trace, 'logits_max_abs_diff', threshold=1e-7),
        'first_loss_difference_step': next((
            t['step'] for t in train_trace
            if abs(t['forced_final_loss'] - t['original_loss']) > 1e-7
        ), None),
        'steps_with_original_mass_deficit': sum(
            t['original_act_deficit_fraction'] > 0 for t in train_trace),
    }
    return {'attention': attention, 'requested_depth': depth,
            'params': sum(p.numel() for p in original.parameters()),
            'initial': initial, 'train_trace': train_trace, 'heldout': heldout,
            'dynamics': dynamics,
            'trained_parameter_l2_difference': float(torch.linalg.vector_norm(
                parameter_vector(original) - parameter_vector(candidate)))}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', default='.')
    p.add_argument('--device', default='cpu')
    p.add_argument('--attentions', choices=('gqa', 'mla'), nargs='+', default=['gqa', 'mla'])
    p.add_argument('--depths', type=int, nargs='+', default=[1, 2, 4, 8])
    p.add_argument('--seed', type=int, default=42)
    p.add_argument('--steps', type=int, default=3)
    p.add_argument('--lr', type=float, default=0.003)
    p.add_argument('--out', default='research/mini_mythos/results/act_ab.json')
    a = p.parse_args()
    if a.steps < 1 or not a.depths or min(a.depths) < 1 or max(a.depths) > 8:
        p.error('steps >= 1 and depths must be in 1..8 for the tiny configuration')
    if not math.isfinite(a.lr) or a.lr <= 0:
        p.error('--lr must be finite and positive')
    torch.set_num_threads(min(4, torch.get_num_threads()))
    root = get_repo(a.repo)
    module = load_upstream(root)
    # Fail visibly if upstream ACT implementation changes: the hook assumes that
    # the upstream recurrence branches to `remainder` when p crosses threshold.
    import inspect
    source = inspect.getsource(module.RecurrentBlock.forward)
    if not all(fragment in source for fragment in (
        'remainder = (1.0 - cumulative_p).clamp(min=0)',
        'cumulative_p + p >= self.cfg.act_threshold',
        'weight = weight * still_running.float()',
    )):
        raise RuntimeError('Upstream ACT code has changed; re-audit the hook equivalence before running')

    report = {'experiment': 'act_final_remainder_ab', 'upstream_commit': commit_id(root),
              'torch': torch.__version__, 'device': a.device, 'seed': a.seed,
              'steps_per_arm': a.steps, 'lr': a.lr,
              'method': 'On the final allowed ACT call, a temporary hook replaces p with 1; no upstream source or weights are edited.',
              'limitations': 'Random untrained tiny models, deterministic toy tokens; not a reasoning benchmark. Tiny heldout batches; no statistical significance.',
              'trace_notes': 'ACT mass and logits/gradient differences are measured before each optimizer step on the same toy batch. First-event thresholds are numerical diagnostics, not statistical tests.',
              'results': []}
    for attention in a.attentions:
        for depth in a.depths:
            start = time.perf_counter()
            row = run_arm(module, attention, depth, device=a.device, seed=a.seed, steps=a.steps, lr=a.lr)
            row['seconds'] = round(time.perf_counter() - start, 3)
            report['results'].append(row)
            print(f"{attention} depth={depth} original_mass={row['initial']['original_mass_mean']:.4f} "
                  f"forced_mass={row['initial']['forced_mass_mean']:.4f} "
                  f"logits_delta={row['initial']['logits_max_abs_diff']:.6g} "
                  f"grad_delta={row['initial']['gradient_l2_difference']:.6g} "
                  f"first_mass_deficit={row['dynamics']['first_original_mass_deficit_step']} "
                  f"first_loss_split={row['dynamics']['first_loss_difference_step']}", flush=True)
    atomic_json(a.out, report)
    print('Saved:', a.out)


if __name__ == '__main__':
    main()
