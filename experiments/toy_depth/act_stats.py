#!/usr/bin/env python3
"""
ACT / hidden-state diagnostics for the depth-extrapolation study.

Hooks the unmodified model (no patching) and, per checkpoint, reports:
    - halting step distribution and the mass ACT actually assigns per position
      at each depth T (original rule: positions that never cross act_threshold
      keep weights summing to < 1)
    - per-loop hidden-state RMS and relative step size ||h_t - h_{t-1}|| / ||h_{t-1}||
      out to --max-loops, to see whether the recurrence diverges past the
      trained depth

    python experiments/toy_depth/act_stats.py --ckpt ckpts/seed*.pt \\
        --data experiments/toy_depth/data/test.txt
"""

import argparse
import json

import torch

from open_mythos import OpenMythos


@torch.no_grad()
def collect(model, x, n_loops):
    """Run one forward at n_loops with ACT never halting early; return p and h per loop."""
    ps, hs = [], []
    h1 = model.recurrent.act.register_forward_hook(lambda m, i, o: ps.append(o))
    h2 = model.recurrent.injection.register_forward_hook(lambda m, i, o: hs.append(o))
    thr = model.recurrent.cfg.act_threshold
    model.recurrent.cfg.act_threshold = float("inf")  # observe every loop
    try:
        model(x, n_loops=n_loops)
    finally:
        model.recurrent.cfg.act_threshold = thr
        h1.remove()
        h2.remove()
    return torch.stack(ps), torch.stack(hs)  # (L, B, T), (L, B, T, D)


def assigned_mass(p: torch.Tensor, thr: float, T: int) -> torch.Tensor:
    """Total ACT weight per position after T loops under the original rule."""
    cum = torch.zeros_like(p[0])
    mass = torch.zeros_like(p[0])
    halted = torch.zeros_like(p[0], dtype=torch.bool)
    for t in range(T):
        run = (~halted).float()
        w = torch.where(cum + p[t] >= thr, (1 - cum).clamp(min=0), p[t]) * run
        mass += w
        cum += p[t] * run
        halted |= cum >= thr
    return mass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", nargs="+", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--seq-len", type=int, default=128)
    ap.add_argument("--n-windows", type=int, default=64)
    ap.add_argument("--max-loops", type=int, default=16)
    ap.add_argument("--depths", default="4,8,16")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    with open(args.data, encoding="utf-8") as f:
        ids = torch.tensor(list(f.read().encode("utf-8")), dtype=torch.long)
    n = args.n_windows * args.seq_len
    x = ids[:n].view(args.n_windows, args.seq_len)
    depths = [int(d) for d in args.depths.split(",")]

    rows = []
    for path in args.ckpt:
        ckpt = torch.load(path, map_location="cpu", weights_only=False)
        model = OpenMythos(ckpt["cfg"])
        model.load_state_dict(ckpt["model"])
        model.eval()
        thr = model.cfg.act_threshold
        p, h = collect(model, x, args.max_loops)

        cum = p.cumsum(0)
        crossed = cum >= thr
        halt_step = torch.where(
            crossed.any(0), crossed.float().argmax(0) + 1, torch.full_like(cum[0], -1)
        )
        row = {
            "ckpt": path,
            "trained_loops": model.cfg.max_loop_iters,
            "mean_p_per_loop": p.mean((1, 2)).tolist(),
            "frac_halted_by": {
                T: (crossed[:T].any(0)).float().mean().item() for T in depths
            },
            "assigned_mass_mean": {
                T: assigned_mass(p, thr, T).mean().item() for T in depths
            },
            "assigned_mass_frac_below_0.9": {
                T: (assigned_mass(p, thr, T) < 0.9).float().mean().item()
                for T in depths
            },
            "median_halt_step": (
                halt_step[halt_step > 0].median().item()
                if (halt_step > 0).any()
                else None
            ),
            "h_rms_per_loop": h.pow(2).mean((1, 2, 3)).sqrt().tolist(),
            "rel_step_per_loop": [None]
            + (
                (h[1:] - h[:-1]).flatten(1).norm(dim=1) / h[:-1].flatten(1).norm(dim=1)
            ).tolist(),
        }
        rows.append(row)
        print(f"\n== {path} (trained T={row['trained_loops']}, thr={thr})")
        print(
            "mean p per loop     :",
            " ".join(f"{v:.3f}" for v in row["mean_p_per_loop"]),
        )
        for T in depths:
            print(
                f"T={T:<3d} halted {row['frac_halted_by'][T]:.3f} | "
                f"mean assigned mass {row['assigned_mass_mean'][T]:.3f} | "
                f"frac mass<0.9 {row['assigned_mass_frac_below_0.9'][T]:.3f}"
            )
        print(
            "h RMS per loop      :", " ".join(f"{v:.2f}" for v in row["h_rms_per_loop"])
        )
        print(
            "rel step per loop   :",
            " ".join(f"{v:.3f}" for v in row["rel_step_per_loop"][1:]),
        )

    if args.out:
        with open(args.out, "w") as f:
            json.dump(rows, f, indent=1)


if __name__ == "__main__":
    main()
