#!/usr/bin/env python3
"""Inspect OpenMythos ACT probability mass at various inference depths.

Uses actual upstream model forward and ACT forward hooks. NO model modifications.
The `force_final_remainder` values are counterfactual weight bookkeeping only.
"""
import argparse
import time
import torch
from common import atomic_json, commit_id, get_repo, load_upstream, tiny_config, toy_batch
from act_math import act_accounting


def run():
    p = argparse.ArgumentParser()
    p.add_argument('--repo', default='.')
    p.add_argument('--device', default='cpu')
    p.add_argument('--attention', choices=['gqa','mla'], default='gqa')
    p.add_argument('--depths', nargs='+', type=int, default=[1,2,4,8])
    p.add_argument('--seed', type=int, default=1003)
    p.add_argument('--out', default='research/mini_mythos/results/act_diagnostics.json')
    a = p.parse_args()
    if not a.depths or min(a.depths) < 1 or max(a.depths) > 32:
        p.error('depths must be 1..32')
    root = get_repo(a.repo)
    torch.set_num_threads(min(4,torch.get_num_threads()))
    module = load_upstream(root)
    torch.manual_seed(a.seed)
    cfg = tiny_config(module, a.attention)
    model = module.OpenMythos(cfg).to(a.device).eval()
    x, _ = toy_batch(torch, a.seed + 17, batch_size=1, device=a.device)
    summary = {'upstream_commit': commit_id(root), 'seed': a.seed,
               'device': a.device, 'attention': a.attention,
               'random_untrained_model': True,
               'warning': 'Only ACT weight bookkeeping; no accuracy or trained-model inference claims.',
               'depth_results': []}
    for depth in a.depths:
        observed = []
        def on_act(_module, _inputs, output):
            observed.append(output.detach().float().cpu())
        hook = model.recurrent.act.register_forward_hook(on_act)
        t0 = time.perf_counter()
        try:
            with torch.no_grad():
                logits = model(x, n_loops=depth)
        finally:
            hook.remove()
        probs = torch.stack(observed)
        current = act_accounting(probs, threshold=cfg.act_threshold)
        proposed = act_accounting(probs, threshold=cfg.act_threshold, force_final_remainder=True)
        row = {'requested_depth': depth, 'actual_depth': len(observed),
               'original_mass_min': float(current.probability_mass.min()),
               'original_mass_mean': float(current.probability_mass.mean()),
               'original_mass_max': float(current.probability_mass.max()),
               'forced_final_mass_mean': float(proposed.probability_mass.mean()),
               'original_mass_below_0_99_fraction': float((current.probability_mass < .99).float().mean()),
               'max_counterfactual_mass_difference': float((current.probability_mass-proposed.probability_mass).abs().max()),
               'logits_finite': bool(torch.isfinite(logits).all()),
               'seconds': round(time.perf_counter()-t0,3)}
        summary['depth_results'].append(row)
        print('depth=',depth,'actual=',row['actual_depth'], 'mean_mass=',round(row['original_mass_mean'],4))
    atomic_json(a.out,summary)
    print('Saved:',a.out)


if __name__=='__main__':
    run()
