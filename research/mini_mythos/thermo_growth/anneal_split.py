#!/usr/bin/env python3
"""Autonomous growth by cooling: deterministic annealing (Rose 1998) on Parcae's own representations.

Nothing is trained and nothing new is fed in. All the "knowledge points" start as ONE point (the mean).
The temperature T is lowered step by step. At each T the soft assignments and centres settle to their
free-energy minimum (F = D - T H). When T falls below a critical temperature, a centre becomes unstable
and splits BY ITSELF along the strongest direction of the points it holds: point -> line -> plane -> space.
Nobody schedules a split; theory predicts when it happens: T_c = 2 * lambda_max of the covariance of
the points a centre holds (squared-distance distortion). The script records, at every temperature,
the number of distinct centres K, the dimension they span (affine rank and participation ratio), and
the predicted vs the observed split temperatures.

  python -B anneal_split.py --points FILE.npz --out OUT        # points from any source (key "X", optional "label")
  python -B anneal_split.py --parcae --sets EVAL_SETS --upstream P --model-dir M --tokenizer T --out OUT
                                                                # Parcae final hidden states of the dev windows

Writes OUT/anneal.jsonl (one row per temperature), OUT/summary.json and prints a table.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent


def covariance_top(torch, X, w=None, iters=200, tol=1e-10):
    """Largest eigenvalue and its eigenvector of the (weighted) covariance of rows of X (power
    iteration on the weighted, centred data; deterministic start)."""
    if w is None:
        w = torch.full((X.shape[0],), 1.0 / X.shape[0], dtype=X.dtype)
    w = w / w.sum()
    mu = (w[:, None] * X).sum(0)
    Xc = (X - mu) * w.sqrt()[:, None]
    v = Xc.abs().sum(0) + 1.0
    v = v / v.norm()
    lam = 0.0
    for _ in range(iters):
        z = Xc.t() @ (Xc @ v)
        new = float(z.norm())
        if new == 0.0:
            return 0.0, v
        v = z / new
        if abs(new - lam) <= tol * new:
            lam = new
            break
        lam = new
    return lam, v


def participation_ratio(torch, Y, p):
    """Effective dimension of the centres, weighted by their mass."""
    p = p / p.sum()
    mu = (p[:, None] * Y).sum(0)
    Yc = (Y - mu) * p.sqrt()[:, None]
    s2 = torch.linalg.svdvals(Yc) ** 2
    tot = float(s2.sum())
    return 0.0 if tot <= 0 else tot ** 2 / float((s2 ** 2).sum())


def affine_rank(torch, Y, rel=1e-6):
    if Y.shape[0] < 2:
        return 0
    s = torch.linalg.svdvals(Y - Y.mean(0))
    return int((s > rel * max(float(s[0]), 1e-300)).sum())


def settle(torch, X, Y, p, T, iters=300, tol=1e-9):
    """Fixed point of the free energy at temperature T (mass-constrained DA updates). Stops when no
    centre moves more than sqrt(tol) times the rms radius of the data."""
    n = X.shape[0]
    tol = tol * float((X - X.mean(0)).pow(2).sum(1).mean())
    x2 = (X * X).sum(1, keepdim=True)
    for _ in range(iters):
        d2 = (x2 + (Y * Y).sum(1)[None, :] - 2.0 * X @ Y.t()).clamp_(min=0.0)
        logits = torch.log(p)[None, :] - d2 / T
        post = torch.softmax(logits, dim=1)                       # p(y | x)
        p_new = post.mean(0).clamp_(min=1e-300)
        Y_new = (post.t() @ X) / (n * p_new[:, None])
        shift = float((Y_new - Y).pow(2).sum(1).max())
        Y, p = Y_new, p_new
        if shift < tol:
            break
    return Y, p, post, d2


def merge(torch, Y, p, post, radius):
    """Group centres closer than `radius` (copies that did not separate) into effective clusters."""
    groups = []
    for j in range(Y.shape[0]):
        for g in groups:
            if float((Y[j] - Y[g[0]]).norm()) < radius:
                g.append(j)
                break
        else:
            groups.append([j])
    pg = torch.stack([p[g].sum() for g in groups])
    Yg = torch.stack([(p[g, None] * Y[g]).sum(0) / p[g].sum() for g in groups])
    postg = torch.stack([post[:, g].sum(1) for g in groups], 1)
    return Yg, pg, postg


def anneal(torch, X, alpha=0.95, t_min_ratio=1e-3, k_max=64, seed=0, perturb=1e-3, split_radius=1e-2):
    """Deterministic annealing from one point. Returns a list of records (one per temperature)."""
    gen = torch.Generator().manual_seed(seed)
    X = X.double()
    n, dim = X.shape
    scale = math.sqrt(float((X - X.mean(0)).pow(2).sum(1).mean()))       # rms distance to the mean
    lam1, _ = covariance_top(torch, X)
    t_c1 = 2.0 * lam1
    T = 1.5 * t_c1
    Y = X.mean(0, keepdim=True)
    p = torch.ones(1, dtype=X.dtype)
    records = []
    prev_k = 1
    while True:
        # every effective centre is held as two slightly perturbed copies: if the copies drift apart
        # while settling, the centre has split by itself at this temperature
        d = torch.randn(Y.shape, generator=gen, dtype=X.dtype)
        d = d / d.norm(dim=1, keepdim=True) * perturb * scale
        Y2 = torch.cat([Y + d, Y - d], 0)
        p2 = torch.cat([p / 2, p / 2], 0)
        Y2, p2, post2, d2 = settle(torch, X, Y2, p2, T)
        Y, p, post = merge(torch, Y2, p2, post2, split_radius * scale)
        k = Y.shape[0]
        # predicted critical temperature of every effective centre: 2 * lambda_max of the points it holds
        tc = [2.0 * covariance_top(torch, X, post[:, j])[0] for j in range(k)]
        hard = post.argmax(1)
        distortion = float((post2 * d2).sum(1).mean())
        entropy = float(-(post2 * torch.log(post2.clamp(min=1e-300))).sum(1).mean())
        rec = {"T": T, "T_over_Tc1": T / t_c1, "K": k, "split_now": k > prev_k,
               "span_dim": affine_rank(torch, Y), "pr_dim": participation_ratio(torch, Y, p),
               "next_Tc_predicted": max(tc), "distortion": distortion, "entropy": entropy,
               "free_energy": distortion - T * entropy, "masses": sorted((float(v) for v in p), reverse=True),
               "hard_sizes": sorted(torch.bincount(hard, minlength=k).tolist(), reverse=True)}
        records.append(rec)
        prev_k = k
        if k >= k_max or T < t_min_ratio * t_c1:
            break
        T *= alpha
    return records, {"points": n, "dim": dim, "rms_radius": scale, "lambda_1": lam1, "Tc1_predicted": t_c1,
                     "first_split_observed_T": next((r["T"] for r in records if r["split_now"]), None),
                     "final_assignment": hard.tolist()}


def parcae_points(args, torch):
    """Final hidden states of the dev windows (window means), native Parcae, FP32, no training."""
    sys.path.insert(0, str(HERE.parent / "stage2"))
    sys.path.insert(0, str(HERE.parent / "thermo_b"))
    import importlib.util
    import gpu_common as G
    spec = importlib.util.spec_from_file_location("thermo_train", HERE.parent / "thermo_b" / "train.py")
    TR = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(TR)
    model, _ = G.load_model(torch, args.upstream, args.model_dir, args.tokenizer, args.device, pin_check=True)
    for prm in model.parameters():
        prm.requires_grad_(False)
    dev = G.load_windows(args.sets, "dev")
    windows = TR.probe_windows(dev, args.per_domain)
    feats, _ = TR.features(torch, model, windows, args.device, args.tokens_per_window)
    level = "windows" if args.level == "windows" else "tokens"
    doms = sorted(feats)
    X = torch.cat([feats[d][level] for d in doms], 0).cpu()
    labels = sum(([d] * feats[d][level].shape[0] for d in doms), [])
    return X, labels


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--points", help="npz with X [N, D] (and optional label [N])")
    src.add_argument("--parcae", action="store_true")
    p.add_argument("--sets")
    p.add_argument("--upstream")
    p.add_argument("--model-dir")
    p.add_argument("--tokenizer")
    p.add_argument("--device", default="cpu")
    p.add_argument("--threads", type=int, default=4)
    p.add_argument("--per-domain", type=int, default=100)
    p.add_argument("--level", choices=["windows", "tokens"], default="windows")
    p.add_argument("--tokens-per-window", type=int, default=10)
    p.add_argument("--alpha", type=float, default=0.95, help="cooling factor per step")
    p.add_argument("--k-max", type=int, default=64)
    p.add_argument("--t-min-ratio", type=float, default=1e-3)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--out", required=True)
    args = p.parse_args()
    import torch
    torch.set_num_threads(args.threads)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    cache = out / "points.npz"
    if args.parcae and cache.exists():
        z = np.load(cache, allow_pickle=False)
        X, labels = torch.from_numpy(z["X"]).double(), [str(v) for v in z["label"]]
    elif args.parcae:
        X, labels = parcae_points(args, torch)
        np.savez(cache, X=X.numpy(), label=np.asarray(labels))
    else:
        z = np.load(args.points, allow_pickle=False)
        X = torch.from_numpy(z["X"]).double()
        labels = [str(v) for v in z["label"]] if "label" in z else None
    records, info = anneal(torch, X, alpha=args.alpha, t_min_ratio=args.t_min_ratio, k_max=args.k_max, seed=args.seed)
    with open(out / "anneal.jsonl", "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    assign = info.pop("final_assignment")
    if labels is not None:                                   # which texts end up together in each final centre
        info["labels"] = sorted(set(labels))
        comp = {}
        for a, lab in zip(assign, labels):
            comp.setdefault(int(a), {}).setdefault(lab, 0)
            comp[int(a)][lab] += 1
        info["final_composition"] = [comp[c] for c in sorted(comp, key=lambda c: -sum(comp[c].values()))]
    info["source"] = "parcae dev windows (%s level)" % args.level if args.parcae else args.points
    (out / "summary.json").write_text(json.dumps(info, indent=1) + "\n")
    print(json.dumps(info, indent=1))
    print("T/Tc1    K  span  PR    next Tc (pred)/Tc1  split")
    for r in records:
        if r["split_now"] or r is records[0] or r is records[-1]:
            print("%7.4f %3d %5d %5.2f   %7.4f            %s" % (r["T_over_Tc1"], r["K"], r["span_dim"], r["pr_dim"],
                                                            r["next_Tc_predicted"] / info["Tc1_predicted"],
                                                            "SPLIT" if r["split_now"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
