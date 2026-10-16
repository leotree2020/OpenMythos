#!/usr/bin/env python3
"""Tiny CPU-friendly *training pipeline sanity check*, not OpenMythos reproduction."""
import argparse
import json
import math
import time
import torch
import torch.nn.functional as F
from common import get_repo, load_upstream, tiny_config, commit_id, toy_batch, atomic_json


def evaluate(model, depth, seeds, device):
    model.eval()
    losses = []
    with torch.no_grad():
        for seed in seeds:
            x,y = toy_batch(torch, seed, device=device)
            logits = model(x, n_loops=depth)
            losses.append(float(F.cross_entropy(logits.reshape(-1, logits.shape[-1]), y.reshape(-1))))
    return sum(losses)/len(losses)


def train_run(module, seed, depth, steps, device, lr):
    torch.manual_seed(seed)
    cfg = tiny_config(module)
    model = module.OpenMythos(cfg).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=lr)
    log = []
    start = time.perf_counter()
    for step in range(steps):
        model.train()
        x, y = toy_batch(torch, 1000 + seed*101 + step, device=device)
        opt.zero_grad(set_to_none=True)
        logits = model(x, n_loops=depth)
        loss = F.cross_entropy(logits.reshape(-1, logits.shape[-1]), y.reshape(-1))
        if not torch.isfinite(loss):
            raise RuntimeError(f'nonfinite loss at step {step} for depth={depth}')
        loss.backward()
        norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.)
        opt.step()
        log.append({'step': step+1, 'loss': float(loss.detach()), 'grad_norm': float(norm)})
    elapsed = time.perf_counter()-start
    sweep = {str(n): evaluate(model, n, range(99_000, 99_003), device) for n in (1,2,4,8)}
    return {'train_depth': depth, 'train_steps': steps, 'seconds': round(elapsed,2),
            'params': sum(p.numel() for p in model.parameters()),
            'final_train_loss': log[-1]['loss'],
            'heldout_loss_by_inference_depth': sweep,
            'heldout_ppl_by_inference_depth': {k: math.exp(v) for k,v in sweep.items()},
            'train_trace': log}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--repo',default='.')
    p.add_argument('--device',default='cpu')
    p.add_argument('--seed',type=int,default=123)
    p.add_argument('--steps',type=int,default=3)
    p.add_argument('--train-depths',type=int,nargs='+',default=[1,4])
    p.add_argument('--lr',type=float,default=3e-3)
    p.add_argument('--out',default='research/mini_mythos/results/pilot.json')
    a=p.parse_args()
    if a.steps < 1 or any(d < 1 or d > 8 for d in a.train_depths):
        p.error('steps >= 1 and each depth must be between 1 and 8')
    root=get_repo(a.repo)
    module=load_upstream(root)
    torch.set_num_threads(min(4, torch.get_num_threads()))
    results={'upstream_commit':commit_id(root),'device':a.device,'seed':a.seed,
             'caveat':'Synthetic toy grammar; comparisons are NOT compute-matched and NOT independent proof of reasoning ability.',
             'runs':[]}
    for depth in a.train_depths:
        print('Training depth',depth, 'for',a.steps,'optimizer steps', flush=True)
        r=train_run(module,a.seed,depth,a.steps,a.device,a.lr)
        results['runs'].append(r)
        print('End train loss',round(r['final_train_loss'],4), 'eval',r['heldout_loss_by_inference_depth'], flush=True)
    atomic_json(a.out,results)
    print('Saved to:', a.out)

if __name__=='__main__':
    main()
