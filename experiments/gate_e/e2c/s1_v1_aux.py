#!/usr/bin/env python3
"""
V1, auxiliary-supervision checks run in one process (E2C_PREREG_DRAFT 3.3-3.5, 6):

    a  record points: the tensors the Recorder takes from the native forward
       equal gate_d Runner's record points of the same names (bitwise), on a
       trained checkpoint and a training batch
    b  fixed heads: train_e2c.main() run in this process (30 updates, C1 and
       C2); the optimizer holds exactly the model's parameters and no head;
       the head tensors keep requires_grad False, get no .grad, and their
       sha256 after training equals the sha256 before and the run record
    c  gradient scope of L_aux (C1 and C2):
       - direct gradient on each record point (the state taken as a leaf):
         zero at every position other than 2 and 6; lam times its norm over
         all record points equals the logged formula r_u (rel. 1e-5)
       - gradient on the embedding output: exactly zero at positions 7-10
         (after the last supervised position), non-zero at 0-6
       - parameter gradient: none on the final norm (it acts after every
         record point) and none on any tensor outside the model
    d  labels: C1 = LETTERS index of the letters at positions 0 / 4;
       C2 = c(digit at 2 / 6) with c = Random(80000 + seed).sample(range(52), 10)
"""

import argparse
import json
import os
import sys
import tempfile

import torch
import torch.nn.functional as F

HERE = os.path.dirname(os.path.abspath(__file__))
GE = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, GE)

import e2c_common as C  # noqa: E402
from e_common import LETTERS, atomic_write_json  # noqa: E402
from e_task import train_rng_k2, train_sample_k2  # noqa: E402
from data import encode_rows  # noqa: E402
from models import build  # noqa: E402
from runner import Runner  # noqa: E402


def batch(seed, n=64):
    rng = train_rng_k2(seed)
    rows = [train_sample_k2(rng) for _ in range(n)]
    return rows, encode_rows(rows)[0]


def check_a(arm, ckpt):
    model = build(arm, 2)
    model.load_state_dict(torch.load(ckpt, map_location="cpu", weights_only=False)["model"])
    model.train()
    rows, x = batch(C.IMPL_SEED)
    rec = C.Recorder(model, arm)
    with torch.no_grad():
        model(x[:, :-1])
    ref = Runner(model).run(x[:, :-1], record=set(C.RECORD_POINTS[arm]))[1]
    out = {p: bool(torch.equal(rec.states[p], ref[p])) for p in C.RECORD_POINTS[arm]}
    rec.remove()
    return {"bitwise_equal_to_runner": out, "pass": all(out.values())}


def check_b(arm, cond):
    import train_e2c
    captured = {}
    real_heads, real_adamw = C.make_heads, torch.optim.AdamW

    def heads_spy(*a, **k):
        h = real_heads(*a, **k)
        captured["heads"] = h
        captured["sha_before"] = C.heads_sha(h)
        return h

    class AdamWSpy(real_adamw):
        def __init__(self, params, *a, **k):
            params = list(params)
            captured["opt_params"] = params
            super().__init__(params, *a, **k)

    tmp = tempfile.mkdtemp(prefix="e2c_v1b_")
    C.make_heads, torch.optim.AdamW = heads_spy, AdamWSpy
    argv = sys.argv
    sys.argv = ["train_e2c.py", "--cond", cond, "--lam", "0.1", "--arm", arm, "--seed", str(C.IMPL_SEED), "--steps", "30",
                "--save-at", "30", "--ckpt-dir", tmp, "--out", os.path.join(tmp, "run.json")]
    try:
        train_e2c.main()
    finally:
        C.make_heads, torch.optim.AdamW, sys.argv = real_heads, real_adamw, argv
    heads = captured["heads"]
    model = build(arm, 2)
    model.load_state_dict(torch.load(os.path.join(tmp, f"{cond}_{arm}_s{C.IMPL_SEED}_step30.pt"), weights_only=False)["model"])
    run = json.load(open(os.path.join(tmp, "run.json")))
    n_model = len(list(model.parameters()))
    head_ids = {id(h) for h in heads}
    out = {"optimizer_param_count": len(captured["opt_params"]), "model_param_count": n_model,
           "no_head_in_optimizer": not any(id(p) in head_ids for p in captured["opt_params"]),
           "heads_requires_grad_false": all(not h.requires_grad for h in heads),
           "heads_grad_none": all(h.grad is None for h in heads),
           "heads_sha_unchanged": C.heads_sha(heads) == captured["sha_before"],
           "heads_sha_equals_record": list(run["heads_sha256"].values()) == captured["sha_before"],
           "heads_sha_equals_recomputed": C.heads_sha(C.make_heads(arm, C.IMPL_SEED, 128)) == captured["sha_before"]}
    out["pass"] = out["optimizer_param_count"] == n_model and all(v for k, v in out.items() if isinstance(v, bool))
    return out


def check_c(arm, cond, lam=0.1):
    torch.manual_seed(C.IMPL_SEED)
    model = build(arm, 2)
    model.train()
    rows, x = batch(C.IMPL_SEED)
    heads = C.make_heads(arm, C.IMPL_SEED, model.cfg.dim)
    code = C.digit_code(C.IMPL_SEED)
    labels = C.aux_labels(rows, cond, code)
    emb = {}
    hk = model.embed.register_forward_hook(lambda m, i, o: emb.setdefault("out", o))
    rec = C.Recorder(model, arm)
    model(x[:, :-1])
    hk.remove()
    states = rec.ordered()
    L_aux, zs = C.aux_terms(states, heads, labels)
    r_formula = C.direct_signal_norm(zs, heads, labels, lam)
    # direct gradient: each state as a leaf of its own head only
    leaves = [s.detach().clone().requires_grad_(True) for s in states]
    L_leaf, _ = C.aux_terms(leaves, heads, labels)
    gl = torch.autograd.grad(lam * L_leaf, leaves)
    other = [p for p in range(x.shape[1] - 1) if p not in C.DIGIT_POS]
    direct_zero_elsewhere = all(bool((g[:, other] == 0).all()) for g in gl)
    r_autograd = float(torch.sqrt(sum((g.double() ** 2).sum() for g in gl)))
    ge = torch.autograd.grad(L_aux, emb["out"], retain_graph=True)[0]
    after = bool((ge[:, 7:] == 0).all())
    before = bool((ge[:, :7].abs().sum((0, 2)) > 0).all())
    names = [n for n, _ in model.named_parameters()]
    gp = torch.autograd.grad(L_aux, list(model.parameters()), allow_unused=True)
    norm_grad = dict(zip(names, gp))["norm.weight"]
    labels_ok = (bool(torch.equal(labels, torch.tensor([[LETTERS.index(p[0]), LETTERS.index(p[4])] for p, _ in rows])))
                 if cond == "C1" else
                 bool(torch.equal(labels, torch.tensor([[code[int(p[2])], code[int(p[6])]] for p, _ in rows]))))
    out = {"direct_gradient_zero_outside_positions_2_6": direct_zero_elsewhere,
           "r_u_formula": r_formula, "r_u_autograd_direct": r_autograd,
           "r_u_formula_matches_autograd": abs(r_formula - r_autograd) <= 1e-5 * r_autograd,
           "embedding_output_grad_zero_at_positions_7_10": after, "embedding_output_grad_nonzero_at_0_6": before,
           "final_norm_weight_grad_none_or_zero": norm_grad is None or bool((norm_grad == 0).all()),
           "params_with_aux_grad": sum(g is not None and bool((g != 0).any()) for g in gp), "labels_as_defined": labels_ok,
           "aux_loss_at_init": L_aux.item(), "ln52": float(torch.log(torch.tensor(52.0)))}
    out["pass"] = all(v for k, v in out.items() if isinstance(v, bool))
    rec.remove()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True)
    ap.add_argument("--ckpt", required=True, help="trained checkpoint for check a")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    torch.set_num_threads(1)
    out = {"a_record_points": check_a(args.arm, args.ckpt)}
    for cond in ("C1", "C2"):
        out[f"b_heads_{cond}"] = check_b(args.arm, cond)
        out[f"c_scope_{cond}"] = check_c(args.arm, cond)
    out["pass"] = all(v["pass"] for v in out.values())
    atomic_write_json(args.out, out)
    print(json.dumps({k: v["pass"] for k, v in out.items() if isinstance(v, dict)}))
    sys.exit(0 if out["pass"] else 3)


if __name__ == "__main__":
    main()
