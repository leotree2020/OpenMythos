"""
M0: implementation checks on one model state (PREREGISTRATION 4 M0: Gate D
revision 3 D0 checks with the positions of the task geometry). The checkers
are gate_d d0's where they are position-free (later_position_grad,
rope_relative_error, tied_decomposition, moe_row_rounding); the others are
the same code with the prompt length taken from the geometry. Hard checks:
any "pass": False stops the state (exit 3). causal_value_monitor fails only
on a difference that does not start at an MoE block output (as in Gate D).
"""

import e_common  # noqa: F401,E402  (first: puts the archived modules on sys.path)
import torch

from d0 import (TOL_ATTN, TOL_ROPE, TOL_TIED, _moe_modules, later_position_grad,  # gate_d
                moe_points, moe_row_rounding, rope_relative_error, tied_decomposition)
from e_common import family_tensors
from open_mythos.main import GQAttention, apply_rope
from runner import Runner  # gate_d


def causal_positions(g):
    """Gate D used (17, 'Z'), (10, '0'), (3, 'z'): the query, an inner digit
    position and an early ';'."""
    return ((g.Q_POS, ord("Z")), (g.DIGIT_POS[-1], ord("0")), (3, ord("z")))


def _float_records(rec, logits, g):
    out = {k: v for k, v in rec.items()
           if v.dim() >= 2 and v.shape[1] == g.L and v.is_floating_point() and v.requires_grad}
    out["logits"] = logits
    return out


def structural_causal_check(run, x, g):
    detail, worst = {}, 0.0
    for j, _ in causal_positions(g):
        lg, rec, _ = run.run(x, record=True, grad=True)
        gr = later_position_grad(_float_records(rec, lg, g), rec["emb"], j)
        worst = max(worst, max(v[0] for v in gr.values()))
        detail[str(j)] = {"n_record_points": len(gr), "max_grad_from_later": max(v[0] for v in gr.values()),
                          "nonzero_points": [k for k, v in gr.items() if v[0] != 0.0]}
    return {"by_position": detail, "pass": worst == 0.0}


def causal_value_monitor(run, x, g):
    detail, ok = {}, True
    for j, tok in causal_positions(g):
        x2 = x.clone()
        x2[:, j] = tok
        la, a, _ = run.run(x, record=True)
        lb, b, _ = run.run(x2, record=True)
        a["logits"], b["logits"] = la, lb
        first, max_abs = None, 0.0
        for k in a:
            if not (a[k].dim() >= 2 and a[k].shape[1] == g.L):
                continue
            d = (a[k][:, :j].float() - b[k][:, :j].float()).abs().max().item()
            if d > 0:
                first = first or k
            max_abs = max(max_abs, d)
        from_moe = first is None or first in moe_points(run.arm)
        ok &= from_moe
        detail[str(j)] = {"max_abs_diff": max_abs, "first_differing_point": first, "first_is_moe_output": from_moe}
    return {"by_position": detail, "pass": ok}


def attention_future_zero(run, x, g):
    _, _, att = run.run(x, want_attn=True)
    upper = torch.triu(torch.ones(g.L, g.L, dtype=torch.bool), 1)
    worst = {k: w[..., upper].abs().max().item() for k, w in att.items()}
    return {"max_future_weight": worst, "pass": max(worst.values()) == 0.0}


def moe_token_independence(model, x, g):
    res, ok = {}, True
    for name, moe in _moe_modules(model):
        cap = []
        h = moe.register_forward_pre_hook(lambda m, a: cap.append(a[0].detach()))
        with torch.no_grad():
            model(x)
        h.remove()
        inp = cap[0].clone().requires_grad_(True)
        out = moe(inp)
        gen = torch.Generator().manual_seed(0)
        cross = 0.0
        for i in range(g.L):
            for _ in range(2):
                v = torch.randn(out[:, i].shape, generator=gen)
                (gr,) = torch.autograd.grad((out[:, i] * v).sum(), inp, retain_graph=True)
                mask = torch.ones(g.L, dtype=torch.bool)
                mask[i] = False
                cross = max(cross, gr[:, mask].abs().max().item())
        with torch.no_grad():
            flat = inp.detach().reshape(-1, inp.shape[-1])
            idx_batch = (moe.router(flat) + moe.router_bias).topk(moe.topk, dim=-1).indices
            idx_alone = torch.cat([(moe.router(flat[r : r + 1]) + moe.router_bias).topk(moe.topk, dim=-1).indices
                                   for r in range(flat.shape[0])])
        mism = int((idx_batch != idx_alone).any(dim=-1).sum())
        res[name] = {"max_cross_token_grad": cross, "routing_mismatches": mism, "n_tokens": int(flat.shape[0])}
        ok &= cross == 0.0 and mism == 0
    return {"layers": res, "pass": ok}


def model_checks(model, rows, g):
    K = g.K
    x, y, slot, bid, roots = family_tensors(rows, g)
    run = Runner(model)
    res = {}
    res["encoding"] = {
        "length": int(x.shape[1]),
        "readout_is_question_mark": bool((x[:, g.READ_POS] == ord("?")).all()),
        "query_token_is_queried_letter": all(x[K * i + k, g.Q_POS].item() == ord(r["queries"][k])
                                             for i, r in enumerate(rows) for k in range(K)),
        "digit_positions_hold_answers": all(x[K * i + k, g.DIGIT_POS[k]].item() == y[K * i + k].item()
                                            for i in range(len(rows)) for k in range(K)),
        "answers_match_body": all(r["body"][4 * k + 2] == r["answers"][k] and r["body"][4 * k] == r["queries"][k]
                                  for r in rows for k in range(K)),
    }
    res["encoding"]["pass"] = res["encoding"]["length"] == g.L and all(
        v for k, v in res["encoding"].items() if k != "length")
    run.check_attn, run.attn_diff = True, 0.0
    with torch.no_grad():
        ref = model(x)
    lg, rec, _ = run.run(x, record=True, want_attn=True)
    run.check_attn = False
    res["runner_bitwise"] = {"pass": bool(torch.equal(ref, lg))}
    res["attention_reconstruction"] = {"max_diff": run.attn_diff, "pass": run.attn_diff <= TOL_ATTN}
    with torch.no_grad():
        if run.arm == "transformer":
            fin = model.head(model.norm(rec["out2"]))
        else:
            h = rec["h_out"]
            freqs = model.freqs_cis[: g.L]
            mask = model._causal_mask(g.L, h.device, h.dtype)
            for i, layer in enumerate(model.coda):
                h = layer(h, freqs, mask, None, f"coda_{i}")
            fin = model.head(model.norm(h))
    res["record_point_consistency"] = {"pass": bool(torch.equal(fin, lg))}
    res["causal_structural"] = structural_causal_check(run, x[:32], g)
    res["causal_value_monitor"] = causal_value_monitor(run, x[:64], g)
    res["attention_future_zero"] = attention_future_zero(run, x, g)
    res["moe_token_independence"] = moe_token_independence(model, x[:32], g)
    res["moe_row_rounding_evidence"] = moe_row_rounding(model, x[:32])
    hd = model.cfg.dim // model.cfg.n_heads
    err = rope_relative_error(apply_rope, model.freqs_cis[: g.L], hd)
    calls = []
    hooks = [mod.register_forward_pre_hook(lambda m, a: calls.append(a[1]))
             for mod in model.modules() if isinstance(mod, GQAttention)]
    with torch.no_grad():
        model(x[:8])
    for hk in hooks:
        hk.remove()
    freqs_ok = all(tuple(c.shape) == (g.L, hd // 2) and torch.equal(c, model.freqs_cis[: g.L]) for c in calls)
    res["rope"] = {"relative_err": err, "n_attention_calls": len(calls), "freqs_shape_and_start_ok": freqs_ok,
                   "pass": err <= TOL_ROPE and freqs_ok}
    model.train()
    with torch.no_grad():
        tr = model(x)
    model.eval()
    res["train_eval_mode"] = {"identical": bool(torch.equal(tr, ref)), "max_diff": (tr - ref).abs().max().item()}
    res["train_eval_mode"]["pass"] = res["train_eval_mode"]["identical"]
    store = {}

    def keep(mod, inp, out):
        out.retain_grad()
        store["e"] = out

    hk = model.embed.register_forward_hook(keep)
    model.zero_grad(set_to_none=True)
    out = model(x[:16])
    out[:, g.READ_POS].gather(1, y[:16, None]).sum().backward()
    hk.remove()
    gq = store["e"].grad[:, g.Q_POS].norm(dim=-1)
    res["query_path"] = {"min_grad_norm_query_pos": gq.min().item(), "pass": bool((gq > 0).all())}
    inp, outp, total = tied_decomposition(model, x[:32], y[:32], read_pos=g.READ_POS)
    dd = (inp + outp - total).abs().max().item()
    res["tied_decomposition"] = {"max_diff": dd, "pass": dd <= TOL_TIED}
    model.zero_grad(set_to_none=True)
    res["pass"] = all(v["pass"] for v in res.values() if isinstance(v, dict) and "pass" in v)
    return res
