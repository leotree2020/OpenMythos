#!/usr/bin/env python3
"""
E2-c training, conditions C0 / C1 / C2 (E2C_PREREG_DRAFT 2, 3.1-3.5).

The loop is E1's train_k.py --task k2 statement for statement in the same
order (lr from budget_a/schedule.extended_lr, batch of 64 from
Random(60000 + seed) with held-out bodies redrawn, loss at the answer
position, zero_grad, backward, clip_grad_norm_(model parameters, 1.0),
AdamW step, the same light log, the same dev log, checkpoints at step 0 and
--save-at). C1 / C2 add lam * L_aux before the backward pass; nothing else of
the update changes. The logging helpers are train_k.py's own (imported).

Records (all read-only, outside the update; switched off by --no-records for
R1''): batch hash chain (value every 100 updates), ACT statistics (OpenMythos;
every 10 updates up to 1000, then every 100; loops executed at every
update), parameter-level ||d L_aux / d theta|| by autograd.grad at the same
updates (C1 / C2). Always recorded for C1 / C2 (they are part of the update
or of the balance check): r_u and kappa_u at every update, the auxiliary loss.
A progress record (all logs so far) is written atomically with every
checkpoint, so an interrupted attempt keeps its records for the restart
consistency check (3.5).

    python experiments/gate_e/e2c/train_e2c.py --cond C1 --lam 0.1 --arm openmythos --seed 91 \\
        --steps 3000 --save-at 25,50,... --ckpt-dir DIR --out RUN.json
--detach-aux: R1' negative control (C1 head on detached states).
--stop-after N: V1 only; exit 9 right after update N (a simulated
interruption: no final record is written).
"""

import argparse
import hashlib
import json
import os
import sys
import time

import torch
import torch.nn.functional as F

HERE = os.path.dirname(os.path.abspath(__file__))
GE = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, GE)

import e2c_common as C  # noqa: E402
from e_common import Geom, atomic_torch_save, atomic_write_json, family_tensors, load_set, param_hash  # noqa: E402
from e_task import train_rng_k2, train_sample_k2  # noqa: E402
from train_k import batch_terms, dev_probe_k2, log_due  # noqa: E402  E1, read-only
from data import encode_rows  # noqa: E402  gen_gate_a
from models import build  # noqa: E402  basic_learn
from schedule import extended_lr  # noqa: E402  budget_a


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cond", required=True, choices=C.CONDS)
    ap.add_argument("--arm", required=True, choices=["openmythos", "transformer"])
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--lam", type=float, default=None, help="C1: lambda; C2: lambda2")
    ap.add_argument("--steps", type=int, default=12000)
    ap.add_argument("--batch-size", type=int, default=64)
    ap.add_argument("--save-at", default="")
    ap.add_argument("--ckpt-dir", required=True)
    ap.add_argument("--dev", default="dev_heldout")
    ap.add_argument("--threads", type=int, default=1)
    ap.add_argument("--no-records", action="store_true")
    ap.add_argument("--detach-aux", action="store_true")
    ap.add_argument("--stop-after", type=int, default=None)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    aux = args.cond != "C0"
    if aux and not (args.lam is not None and args.lam > 0):
        raise SystemExit("C1 / C2 need --lam > 0")
    if not aux and (args.lam is not None or args.detach_aux):
        raise SystemExit("C0 takes no --lam / --detach-aux")
    if args.detach_aux and args.cond != "C1":
        raise SystemExit("--detach-aux is the C1 negative control (R1')")
    records = not args.no_records
    g = Geom(2)

    torch.set_num_threads(args.threads)
    torch.manual_seed(args.seed)
    rng = train_rng_k2(args.seed)
    draw = lambda: train_sample_k2(rng)  # noqa: E731
    dev = family_tensors(load_set(args.dev), g)
    probe = lambda m: dev_probe_k2(m, dev)  # noqa: E731
    model = build(args.arm, 2)
    opt = torch.optim.AdamW(model.parameters(), lr=2e-3, weight_decay=0.1)
    save_at = {int(s) for s in args.save_at.split(",") if s}
    os.makedirs(args.ckpt_dir, exist_ok=True)

    params = list(model.parameters())
    rec = None
    run = {"cond": args.cond, "arm": args.arm, "seed": args.seed, "lam": args.lam, "steps": args.steps,
           "batch_size": args.batch_size, "schedule": "budget_a/schedule.extended_lr", "records": records,
           "detach_aux": args.detach_aux, "clip": C.CLIP,
           "optimizer": {"type": "AdamW", "lr": 2e-3, "weight_decay": 0.1, "betas": [0.9, 0.999], "eps": 1e-8},
           "lr_schedule_sha256": hashlib.sha256(json.dumps([extended_lr(s) for s in range(args.steps)]).encode()).hexdigest(),
           "init_param_sha256": param_hash(model)}
    if aux:
        heads = C.make_heads(args.arm, args.seed, model.cfg.dim)
        run["heads_sha256"] = dict(zip(C.RECORD_POINTS[args.arm], C.heads_sha(heads)))
        run["record_points"] = list(C.RECORD_POINTS[args.arm])
        run["positions"] = list(C.DIGIT_POS)
        run["mask"] = "all ones: 64 x 2 x R supervised entries per update"
        code = None
        if args.cond == "C2":
            code = C.digit_code(args.seed)
            run["digit_code"], run["digit_code_sha256"] = code, C.code_sha(code)
    if aux or records:
        rec = C.Recorder(model, args.arm, want_states=aux, want_act=records)
    chain = C.HashChain() if records else None

    def save(step):
        path = os.path.join(args.ckpt_dir, f"{args.cond}_{args.arm}_s{args.seed}_step{step}.pt")
        atomic_torch_save({"K": 2, "task": "k2", "cond": args.cond, "lam": args.lam, "arm": args.arm,
                           "seed": args.seed, "step": step, "model": model.state_dict()}, path)

    losses, light, devlog = [], [], []
    aux_loss, r_u, kap, chain_log, act_log, loops, pnorm = [], [], [], {}, [], [], []
    first_batch_sha = None

    def progress(final=False):
        out = dict(run, first_batch_sha256=first_batch_sha, loss_every_step=losses, light_log=light, dev_log=devlog,
                   aux_loss_every_step=aux_loss, r_u=r_u, kappa_u=kap, batch_chain=chain_log, act_log=act_log,
                   loops_every_step=loops, param_aux_grad_norm=pnorm, save_at=sorted(save_at | {0}))
        if aux and r_u:
            w = r_u[:C.W_UPDATES]
            out["E_W"] = sum(v * v for v in w) if len(w) == C.W_UPDATES else None
            out["E_W_after_clip"] = sum((v * k) ** 2 for v, k in zip(w, kap)) if len(w) == C.W_UPDATES else None
            out["clip_share_W"] = sum(k < 1.0 for k in kap[:C.W_UPDATES]) / C.W_UPDATES if len(w) == C.W_UPDATES else None
        out["clip_share_all"] = sum(k < 1.0 for k in kap) / len(kap) if kap else None
        out["complete"] = final
        return out

    prog_path = args.out + ".progress.json"
    save(0)
    t0 = time.perf_counter()
    model.train()
    for step in range(args.steps):
        for gr in opt.param_groups:
            gr["lr"] = extended_lr(step)
        rows = [draw() for _ in range(args.batch_size)]
        x, y = encode_rows(rows)
        if step == 0:
            first_batch_sha = hashlib.sha256(x.numpy().tobytes()).hexdigest()
        step1 = step + 1
        if chain is not None:
            cv = chain.update(x)
            if step1 % 100 == 0 or step1 == args.steps:
                chain_log[str(step1)] = cv
        if rec is not None:
            rec.reset()
        logits = model(x[:, :-1])[:, -1]
        loss = F.cross_entropy(logits, y)
        task_loss = loss
        if aux:
            labels = C.aux_labels(rows, args.cond, code)
            L_aux, zs = C.aux_terms(rec.ordered(), heads, labels, detach=args.detach_aux)
            loss = task_loss + args.lam * L_aux
            r_u.append(C.direct_signal_norm(zs, heads, labels, args.lam))
            aux_loss.append(L_aux.item())
            if records and log_due(step1, 1000, 10, 100):
                pnorm.append({"step": step1, "norm": None if args.detach_aux else C.param_grad_norm(L_aux, params)})
        opt.zero_grad(set_to_none=True)
        loss.backward()
        gnorm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        losses.append(task_loss.item())
        kap.append(C.kappa(gnorm))
        if records and args.arm == "openmythos":
            loops.append(len(rec.act_p))
        if log_due(step1, 1000, 10, 100):
            light.append({"step": step1, "loss": losses[-1], "grad_norm_preclip": float(gnorm),
                          **batch_terms(logits.detach(), rows)})
            if records and args.arm == "openmythos":
                act_log.append({"step": step1, **rec.act_stats(g.READ_POS)})
        for v in (task_loss.item(), float(gnorm)) + ((aux_loss[-1], r_u[-1]) if aux else ()):
            if v != v or v in (float("inf"), float("-inf")):
                atomic_write_json(prog_path, dict(progress(), nonfinite_at=step1))
                print(f"NON-FINITE loss or gradient at update {step1} (F7)", file=sys.stderr)
                sys.exit(3)
        if step1 in save_at:
            save(step1)
            atomic_write_json(prog_path, progress())
        if log_due(step1, 1000, 25, 250):
            devlog.append({"step": step1, **probe(model)})
        if args.stop_after is not None and step1 == args.stop_after:
            atomic_write_json(prog_path, progress())
            print(f"simulated interruption after update {step1}", file=sys.stderr)
            sys.exit(9)
    out = progress(final=True)
    out["wall_seconds"] = time.perf_counter() - t0
    out["final_param_sha256"] = param_hash(model)
    atomic_write_json(args.out, out)
    if os.path.exists(prog_path):
        os.remove(prog_path)
    print(f"saved {args.out} ({out['wall_seconds']:.0f}s)")


if __name__ == "__main__":
    main()
