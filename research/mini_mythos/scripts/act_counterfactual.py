#!/usr/bin/env python3
"""ACT-002: four-cell same-weight counterfactual training dynamics.

At each optimizer step evaluate:
  OO = original ACT on original-trained weights
  FO = forced ACT on original-trained weights (same-weight direct policy effect)
  OF = original ACT on forced-trained weights (parameter history effect)
  FF = forced ACT on forced-trained weights (deployed A/B counterpart)

FF - OO = (FO - OO) + (OF - OO) + (FF - OF - FO + OO).

The third term is a policy-by-parameter interaction; sizes of component norms
must NOT be interpreted as percentages of total effect. No upstream modifications.
CPU-friendly random tiny model and synthetic tokens, NOT a quality benchmark.
"""
import argparse
import copy
import inspect
import math
import time

import torch
import torch.nn.functional as F

from act_counterfactual_math import factorial_effects
from act_dynamics import summarize_act_pair
from act_remainder import act_probability_hook
from common import atomic_json, commit_id, get_repo, load_upstream, tiny_config, toy_batch


def _forward(model, x, depth, *, fixed=False, observed=None):
    with act_probability_hook(model, depth, force_final=fixed, observed=observed):
        return model(x, n_loops=depth)


def _parameter_difference(original, fixed):
    with torch.no_grad():
        squared = sum(
            ((p.detach().float() - q.detach().float()) ** 2).sum()
            for p, q in zip(original.parameters(), fixed.parameters())
        )
        return float(torch.sqrt(squared))


def _gradient_difference(original, fixed):
    with torch.no_grad():
        squared = sum(
            ((p.grad.detach().float() - q.grad.detach().float()) ** 2).sum()
            for p, q in zip(original.parameters(), fixed.parameters())
            if p.grad is not None and q.grad is not None
        )
        return float(torch.sqrt(squared))


def _evaluate_four_cells(original, fixed, depth, device, seeds):
    original.eval()
    fixed.eval()
    rows = []
    with torch.no_grad():
        for seed in seeds:
            x, y = toy_batch(torch, seed, device=device)
            oo = _forward(original, x, depth)
            fo = _forward(original, x, depth, fixed=True)
            of = _forward(fixed, x, depth)
            ff = _forward(fixed, x, depth, fixed=True)
            rows.append(factorial_effects(oo, fo, of, ff, y)['loss'])
    columns = ('original_weights_original_act', 'original_weights_forced_act',
               'forced_weights_original_act', 'forced_weights_forced_act',
               'total_deployed_delta', 'direct_mechanism_same_original_weights_delta',
               'parameter_history_under_original_act_delta',
               'policy_parameter_interaction_delta')
    return {'heldout_batches': len(rows),
            **{key: sum(row[key] for row in rows) / len(rows) for key in columns}}


def _first_event(trace, key, tolerance):
    return next((row['step'] for row in trace if abs(row[key]) > tolerance), None)


def run_experiment(module, attention, depth, seed, steps, lr, device):
    torch.manual_seed(seed)
    cfg = tiny_config(module, attention)
    original = module.OpenMythos(cfg).to(device)
    fixed = copy.deepcopy(original)
    if _parameter_difference(original, fixed) != 0:
        raise RuntimeError('The two models must share identical initial parameters')

    opt_original = torch.optim.AdamW(original.parameters(), lr=lr)
    opt_fixed = torch.optim.AdamW(fixed.parameters(), lr=lr)
    trace = []

    for idx in range(steps):
        original.train()
        fixed.train()
        x, y = toy_batch(torch, seed + 1000 + idx, device=device)
        opt_original.zero_grad(set_to_none=True)
        opt_fixed.zero_grad(set_to_none=True)
        param_diff_pre = _parameter_difference(original, fixed)

        obs_oo, obs_fo, obs_of, obs_ff = [], [], [], []
        # Counterfactual forwards have no gradient and never update parameters.
        with torch.no_grad():
            fo = _forward(original, x, depth, fixed=True, observed=obs_fo)
            of = _forward(fixed, x, depth, observed=obs_of)

        # These are the two ACT strategies actually used for optimizer updates.
        oo = _forward(original, x, depth, observed=obs_oo)
        ff = _forward(fixed, x, depth, fixed=True, observed=obs_ff)

        effects = factorial_effects(oo, fo, of, ff, y)
        masses_original = summarize_act_pair(obs_oo, obs_fo, cfg.act_threshold)
        masses_fixed = summarize_act_pair(obs_of, obs_ff, cfg.act_threshold)

        loss_original = F.cross_entropy(oo.reshape(-1, oo.shape[-1]), y.reshape(-1))
        loss_fixed = F.cross_entropy(ff.reshape(-1, ff.shape[-1]), y.reshape(-1))
        loss_original.backward()
        loss_fixed.backward()
        grad_delta = _gradient_difference(original, fixed)
        norm_original = torch.nn.utils.clip_grad_norm_(original.parameters(), 1.0)
        norm_fixed = torch.nn.utils.clip_grad_norm_(fixed.parameters(), 1.0)
        if not bool(torch.isfinite(norm_original) and torch.isfinite(norm_fixed)):
            raise RuntimeError('Nonfinite gradient norm')

        opt_original.step()
        opt_fixed.step()

        trace.append({
            'step': idx + 1,
            'parameter_l2_difference_pre_update': param_diff_pre,
            'parameter_l2_difference_post_update': _parameter_difference(original, fixed),
            'original_act_mass_mean_original_weights': masses_original['original_act_mass_mean'],
            'original_act_mass_min_original_weights': masses_original['original_act_mass_min'],
            'original_act_deficit_fraction_original_weights': masses_original['original_act_deficit_fraction'],
            'original_act_mass_mean_forced_weights': masses_fixed['original_act_mass_mean'],
            'original_act_deficit_fraction_forced_weights': masses_fixed['original_act_deficit_fraction'],
            'actual_loops_original_weights': masses_original['original_actual_loops'],
            'actual_loops_forced_weights': masses_fixed['forced_actual_loops'],
            'deployed_gradient_l2_difference_preclip': grad_delta,
            'grad_norm_original_preclip': float(norm_original),
            'grad_norm_fixed_preclip': float(norm_fixed),
            'effects': effects,
        })

    # Evaluate after identical numbers of updates, using four combinations.
    heldout = _evaluate_four_cells(original, fixed, depth, device, (99001, 99002, 99003))
    events = {
        'first_original_mass_deficit_step': next((
            r['step'] for r in trace
            if r['original_act_deficit_fraction_original_weights'] > 0
        ), None),
        'first_direct_mechanism_logits_difference_step': _first_event(
            [{'step': r['step'], 'metric': r['effects']['logits']['direct_mechanism_same_original_weights']['max_abs']}
             for r in trace], 'metric', 1e-7),
        'first_parameter_divergence_pre_update_step': _first_event(
            [{'step': r['step'], 'metric': r['parameter_l2_difference_pre_update']} for r in trace],
            'metric', 1e-9),
        'first_policy_parameter_interaction_logits_step': _first_event(
            [{'step': r['step'], 'metric': r['effects']['logits']['policy_parameter_interaction']['max_abs']}
             for r in trace], 'metric', 1e-7),
    }
    return {'attention': attention, 'requested_depth': depth,
            'parameters': sum(p.numel() for p in original.parameters()),
            'events': events, 'train_trace': trace, 'heldout': heldout,
            'final_parameter_l2_difference': _parameter_difference(original, fixed)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', default='.')
    parser.add_argument('--device', default='cpu')
    parser.add_argument('--attentions', choices=['gqa', 'mla'], nargs='+', default=['gqa'])
    parser.add_argument('--depths', type=int, nargs='+', default=[2])
    parser.add_argument('--seed', type=int, default=22)
    parser.add_argument('--steps', type=int, default=30)
    parser.add_argument('--lr', type=float, default=0.003)
    parser.add_argument('--out', default='research/mini_mythos/results/act_counterfactual.json')
    args = parser.parse_args()
    if args.steps < 1 or not args.depths or min(args.depths) < 1 or max(args.depths) > 8:
        parser.error('steps must be positive; depths must be from 1 to 8')
    if not math.isfinite(args.lr) or args.lr <= 0:
        parser.error('lr must be finite and positive')

    torch.set_num_threads(min(torch.get_num_threads(), 4))
    root = get_repo(args.repo)
    module = load_upstream(root)
    # This opt-in hook is only valid for the already-audited upstream ACT loop.
    forward_source = inspect.getsource(module.RecurrentBlock.forward)
    if not all(part in forward_source for part in (
        'remainder = (1.0 - cumulative_p).clamp(min=0)',
        'cumulative_p + p >= self.cfg.act_threshold',
        'weight = weight * still_running.float()',
    )):
        raise RuntimeError('Upstream ACT loop changed; audit hook before running ACT-002')

    report = {'experiment': 'ACT-002_same_weight_counterfactual',
              'upstream_commit': commit_id(root), 'device': args.device,
              'torch': torch.__version__, 'seed': args.seed,
              'steps': args.steps, 'lr': args.lr,
              'limitations': 'Randomly initialized tiny model and synthetic tokens. Four-cell effects are observational contrasts at paired parameter snapshots; do not equate effect norms to additive shares or infer real-world model quality.',
              'formula': 'FF-OO=(FO-OO)+(OF-OO)+(FF-OF-FO+OO)',
              'results': []}
    for attention in args.attentions:
        for depth in args.depths:
            started = time.perf_counter()
            row = run_experiment(module, attention, depth, args.seed,
                                 args.steps, args.lr, args.device)
            row['seconds'] = round(time.perf_counter() - started, 3)
            report['results'].append(row)
            print(f"{attention} depth={depth} first_mass_deficit="
                  f"{row['events']['first_original_mass_deficit_step']} "
                  f"first_direct_effect="
                  f"{row['events']['first_direct_mechanism_logits_difference_step']} "
                  f"first_parameter_divergence="
                  f"{row['events']['first_parameter_divergence_pre_update_step']}",
                  flush=True)
    atomic_json(args.out, report)
    print('Saved:', args.out)


if __name__ == '__main__':
    main()
