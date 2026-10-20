#!/usr/bin/env python3
"""
V1 recomputation (E2C_PREREG_DRAFT 3.5, 6): from a saved checkpoint of step k
and the batch of update k+1 (regenerated from Random(60000 + seed)), recompute
in a fresh process what train_e2c.py logged for update u = k+1: r_u, kappa_u,
the auxiliary loss, the task loss, the parameter-level ||d L_aux / d theta||,
the loops executed and the ACT statistics. Run twice in separate processes;
s1_gate3.py compares both with each other and with the run's record (bitwise:
the float values must be identical).

    python s1_recompute.py --cond C1 --lam 0.1 --arm openmythos --seed 99 --ckpt-dir D --ks 9,99,199,299 --out OUT.json
"""

import argparse
import json
import os
import sys

import torch
import torch.nn.functional as F

HERE = os.path.dirname(os.path.abspath(__file__))
GE = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, GE)

import e2c_common as C  # noqa: E402
from e_common import Geom, atomic_write_json  # noqa: E402
from e_task import train_rng_k2, train_sample_k2  # noqa: E402
from data import encode_rows  # noqa: E402
from models import build  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cond", required=True, choices=["C1", "C2"])
    ap.add_argument("--lam", type=float, required=True)
    ap.add_argument("--arm", required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--ckpt-dir", required=True)
    ap.add_argument("--ks", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    torch.set_num_threads(1)
    g = Geom(2)
    ks = sorted(int(k) for k in args.ks.split(","))
    rng = train_rng_k2(args.seed)
    batches, drawn = {}, 0
    for k in ks:  # batch of update k+1 = the (k+1)-th batch of the stream
        while drawn < k + 1:
            rows = [train_sample_k2(rng) for _ in range(64)]
            drawn += 1
        batches[k] = rows
    out = {}
    for k in ks:
        ck = torch.load(os.path.join(args.ckpt_dir, f"{args.cond}_{args.arm}_s{args.seed}_step{k}.pt"),
                        map_location="cpu", weights_only=False)
        assert ck["step"] == k and ck["cond"] == args.cond and ck["lam"] == args.lam
        model = build(args.arm, 2)
        model.load_state_dict(ck["model"])
        model.train()
        heads = C.make_heads(args.arm, args.seed, model.cfg.dim)
        code = C.digit_code(args.seed) if args.cond == "C2" else None
        rec = C.Recorder(model, args.arm, want_states=True, want_act=True)
        rows = batches[k]
        x, y = encode_rows(rows)
        rec.reset()
        logits = model(x[:, :-1])[:, -1]
        task = F.cross_entropy(logits, y)
        labels = C.aux_labels(rows, args.cond, code)
        L_aux, zs = C.aux_terms(rec.ordered(), heads, labels)
        loss = task + args.lam * L_aux
        r = C.direct_signal_norm(zs, heads, labels, args.lam)
        pn = C.param_grad_norm(L_aux, list(model.parameters()))
        loss.backward()
        gnorm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        out[str(k + 1)] = {"r_u": r, "kappa_u": C.kappa(gnorm), "aux_loss": L_aux.item(), "task_loss": task.item(),
                           "param_aux_grad_norm": pn, "grad_norm_preclip": float(gnorm),
                           "loops": len(rec.act_p) if args.arm == "openmythos" else None,
                           "act": rec.act_stats(g.READ_POS)}
        rec.remove()
    atomic_write_json(args.out, out)
    print(json.dumps(out)[:300])


if __name__ == "__main__":
    main()
