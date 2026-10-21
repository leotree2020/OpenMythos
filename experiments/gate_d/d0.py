"""
D0: implementation checks (PREREGISTRATION.md 3, 8.2, 9.1).

tool_checks()  validate each checker on hand-made examples first: a checker
               that fails here is a diagnostic-tool error, not a model issue.
model_checks() the same checkers on a real model state.
Every check returns {"pass": bool, ...}; nothing is relaxed after the fact.
"""

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from common import DIGIT_POS, L_PROMPT, Q_POS, READ_POS, encode
from runner import Runner
from open_mythos.main import GQAttention, MythosConfig, apply_rope, precompute_rope_freqs

TOL_ATTN, TOL_ROPE, TOL_TIED = 1e-5, 1e-5, 1e-6


# ------------------------------------------------------------- checkers


def causal_diff(fn, x, j, replace):
    """max |difference| at positions < j of every (B, T, ...) output of fn
    when token j is replaced."""
    x2 = x.clone()
    x2[:, j] = replace
    a, b = fn(x), fn(x2)
    return max((a[k][:, :j].float() - b[k][:, :j].float()).abs().max().item() for k in a)


def rope_relative_error(rope_fn, freqs, head_dim, shifts=(1, 3, 7), seed=0):
    """q.k after rope must depend only on the position offset."""
    g = torch.Generator().manual_seed(seed)
    q = torch.randn(1, 1, 1, head_dim, generator=g)
    k = torch.randn(1, 1, 1, head_dim, generator=g)
    T = freqs.shape[0]
    rq = rope_fn(q.expand(1, T, 1, head_dim).contiguous(), freqs)[0, :, 0]
    rk = rope_fn(k.expand(1, T, 1, head_dim).contiguous(), freqs)[0, :, 0]
    dots = rq @ rk.T  # (T, T): position m of q, n of k
    err = 0.0
    for s in shifts:
        for m in range(T - s):
            for n in range(T - s):
                err = max(err, abs(dots[m, n].item() - dots[m + s, n + s].item()))
    return err


def tied_decomposition(model, ids, y, read_pos=READ_POS):
    """Input-side and output-side parts of the tied embed=head gradient of the
    mean CE at read_pos; returns (input_side, output_side, embed.weight.grad)."""
    store = {}

    def emb_hook(mod, inp, out):
        out.retain_grad()
        store["emb"] = out

    def norm_hook(mod, inp, out):
        store["fin"] = out

    h1 = model.embed.register_forward_hook(emb_hook)
    h2 = model.norm.register_forward_hook(norm_hook)
    model.zero_grad(set_to_none=True)
    logits = model(ids)
    store["logits"] = logits
    logits.retain_grad()
    loss = F.cross_entropy(logits[:, read_pos], y)
    loss.backward()
    h1.remove()
    h2.remove()
    W = model.embed.weight
    inp = torch.zeros_like(W).index_add_(
        0, ids.reshape(-1), store["emb"].grad.reshape(-1, W.shape[1])
    )
    gl = store["logits"].grad  # (B, T, V); only read_pos is non-zero
    out = torch.einsum("btv,btd->vd", gl, store["fin"].detach())
    return inp, out, W.grad.clone()


# ------------------------------------------------------------- tool checks


def tool_checks():
    res = {}
    # attention reconstruction vs an independent numpy computation
    cfg = MythosConfig(vocab_size=8, dim=8, n_heads=2, n_kv_heads=1, max_seq_len=3,
                       attn_type="gqa", dropout=0.0)
    att = GQAttention(cfg)
    g = torch.Generator().manual_seed(1)
    for lin in (att.wq, att.wk, att.wv, att.wo):
        lin.weight.data = torch.randn(lin.weight.shape, generator=g) * 0.5
    x = torch.randn(1, 3, 8, generator=g)
    freqs = precompute_rope_freqs(4, 3, 10000.0)
    mask = torch.triu(torch.full((1, 1, 3, 3), float("-inf")), 1)
    r = Runner.__new__(Runner)
    r.check_attn, r.attn_diff = False, 0.0
    with torch.no_grad():
        out, w = r._attn(att, x, freqs, mask, True)
    X = x[0].double().numpy()
    Wq, Wk, Wv, Wo = (l.weight.data.double().numpy() for l in (att.wq, att.wk, att.wv, att.wo))
    fr = freqs.numpy()

    def rope_np(v):  # v (T, 4): pairs (0,1), (2,3) as complex numbers
        c = v[:, 0::2] + 1j * v[:, 1::2]
        c = c * fr
        o = np.empty_like(v)
        o[:, 0::2], o[:, 1::2] = c.real, c.imag
        return o

    Q, K, V = X @ Wq.T, X @ Wk.T, X @ Wv.T
    heads, ws = [], []
    for hd in range(2):
        q = rope_np(Q[:, 4 * hd : 4 * hd + 4])
        k = rope_np(K[:, 0:4])  # one kv head shared by both query heads
        s = q @ k.T / 2.0
        s = s + np.triu(np.full((3, 3), -np.inf), 1)
        p = np.exp(s - s.max(1, keepdims=True))
        p /= p.sum(1, keepdims=True)
        ws.append(p)
        heads.append(p @ V[:, 0:4])
    ref = np.concatenate(heads, 1) @ Wo.T
    res["attention_reconstruction_vs_numpy"] = {
        "max_diff_out": float(np.abs(out[0].double().numpy() - ref).max()),
        "max_diff_weights": float(max(np.abs(w[0, h].double().numpy() - ws[h]).max() for h in range(2))),
    }
    res["attention_reconstruction_vs_numpy"]["pass"] = (
        max(res["attention_reconstruction_vs_numpy"].values()) <= TOL_ATTN
    )
    # causal checker: must pass a causal map and flag a non-causal one
    xt = torch.randn(2, 6, 3, generator=g)
    causal_fn = lambda v: {"o": v.cumsum(1)}  # noqa: E731
    acausal_fn = lambda v: {"o": v.flip(1).cumsum(1).flip(1)}  # noqa: E731
    d_ok = causal_diff(causal_fn, xt, 4, torch.ones(3))
    d_bad = causal_diff(acausal_fn, xt, 4, torch.ones(3))
    res["causal_checker"] = {"causal_diff": d_ok, "acausal_diff": d_bad,
                             "pass": d_ok == 0.0 and d_bad > 0}
    # rope checker: must pass true RoPE and flag an absolute-position variant
    fr32 = precompute_rope_freqs(32, L_PROMPT, 10000.0)
    e_ok = rope_relative_error(apply_rope, fr32, 32)
    bad = lambda v, f: v + torch.arange(v.shape[1]).view(1, -1, 1, 1).float() * 0.1  # noqa: E731
    e_bad = rope_relative_error(bad, fr32, 32)
    res["rope_checker"] = {"true_rope_err": e_ok, "absolute_variant_err": e_bad,
                           "pass": e_ok <= TOL_ROPE and e_bad > TOL_ROPE}
    # tied-weight decomposition on a tiny tied model with a known answer
    class Tiny(nn.Module):
        def __init__(self):
            super().__init__()
            self.embed = nn.Embedding(5, 4)
            self.norm = nn.Identity()
            self.head = nn.Linear(4, 5, bias=False)
            self.head.weight = self.embed.weight

        def forward(self, ids):
            h = self.embed(ids).cumsum(1)
            return self.head(self.norm(h))

    tiny = Tiny()
    ids = torch.tensor([[1, 2, 3], [4, 0, 2]])
    inp, out_, total = tied_decomposition(tiny, ids, torch.tensor([3, 1]), read_pos=2)
    res["tied_decomposition_tiny"] = {
        "max_diff": (inp + out_ - total).abs().max().item(),
        "missing_output_side_diff": (inp - total).abs().max().item(),
    }
    res["tied_decomposition_tiny"]["pass"] = (
        res["tied_decomposition_tiny"]["max_diff"] <= TOL_TIED
        and res["tied_decomposition_tiny"]["missing_output_side_diff"] > TOL_TIED
    )
    res["structural_checker_negative_controls"] = negative_controls()
    return res


# ------------------------------------------------------------- model checks


def model_checks(model, rows):
    """rows: diag_eval families. Returns dict of checks for one model state."""
    from common import family_tensors

    x, y, slot, bid, roots = family_tensors(rows)
    run = Runner(model)
    res = {}
    # encoding and readout position
    ans_ok = all(
        r["body"][4 * k + 2] == r["answers"][k] and r["body"][4 * k] == r["queries"][k]
        for r in rows for k in range(4)
    )
    res["encoding"] = {
        "length": int(x.shape[1]),
        "readout_is_question_mark": bool((x[:, READ_POS] == ord("?")).all()),
        "query_token_is_queried_letter": bool(
            all(x[4 * i + k, Q_POS].item() == ord(r["queries"][k]) for i, r in enumerate(rows) for k in range(4))
        ),
        "digit_positions_hold_answers": bool(
            all(x[4 * i + k, DIGIT_POS[k]].item() == y[4 * i + k].item() for i in range(len(rows)) for k in range(4))
        ),
        "answers_match_body": ans_ok,
    }
    res["encoding"]["pass"] = (
        res["encoding"]["length"] == L_PROMPT
        and all(v for k, v in res["encoding"].items() if k != "length")
    )
    # runner reproduces the model bitwise; attention reconstruction
    run.check_attn, run.attn_diff = True, 0.0
    with torch.no_grad():
        ref = model(x)
    lg, rec, _ = run.run(x, record=True, want_attn=True)
    run.check_attn = False
    res["runner_bitwise"] = {"pass": bool(torch.equal(ref, lg))}
    res["attention_reconstruction"] = {"max_diff": run.attn_diff, "pass": run.attn_diff <= TOL_ATTN}
    # record-point consistency: finish the forward from the last record point
    with torch.no_grad():
        if run.arm == "transformer":
            fin = model.head(model.norm(rec["out2"]))
        else:
            h = rec["h_out"]
            freqs = model.freqs_cis[:L_PROMPT]
            mask = model._causal_mask(L_PROMPT, h.device, h.dtype)
            for i, layer in enumerate(model.coda):
                h = layer(h, freqs, mask, None, f"coda_{i}")
            fin = model.head(model.norm(h))
    res["record_point_consistency"] = {"pass": bool(torch.equal(fin, lg))}
    # causal mask (revision 3, PREREGISTRATION 10.2): structural check per record
    # point (hard), forward value differences (monitor), attention / MoE structure
    res["causal_structural"] = structural_causal_check(run, x[:32])
    res["causal_value_monitor"] = causal_value_monitor(run, x[:64])
    res["attention_future_zero"] = attention_future_zero(run, x)
    res["moe_token_independence"] = moe_token_independence(model, x[:32])
    res["moe_row_rounding_evidence"] = moe_row_rounding(model, x[:32])
    # RoPE: relative-position property with the model's own frequencies, and the
    # frequencies every attention call of the original forward receives
    hd = model.cfg.dim // model.cfg.n_heads
    err = rope_relative_error(apply_rope, model.freqs_cis[:L_PROMPT], hd)
    calls = []
    hooks = [
        mod.register_forward_pre_hook(lambda m, a: calls.append(a[1]))
        for mod in model.modules() if isinstance(mod, GQAttention)
    ]
    with torch.no_grad():
        model(x[:8])
    for hk in hooks:
        hk.remove()
    freqs_ok = all(
        tuple(c.shape) == (L_PROMPT, hd // 2) and torch.equal(c, model.freqs_cis[:L_PROMPT])
        for c in calls
    )
    res["rope"] = {"relative_err": err, "n_attention_calls": len(calls),
                   "freqs_shape_and_start_ok": freqs_ok, "pass": err <= TOL_ROPE and freqs_ok}
    # train vs eval mode (dropout 0)
    model.train()
    with torch.no_grad():
        tr = model(x)
    model.eval()
    res["train_eval_mode"] = {"identical": bool(torch.equal(tr, ref)),
                              "max_diff": (tr - ref).abs().max().item()}
    res["train_eval_mode"]["pass"] = res["train_eval_mode"]["identical"]
    # the readout depends on the query token in the computation graph
    store = {}

    def keep(mod, inp, out):
        out.retain_grad()
        store["e"] = out

    hk = model.embed.register_forward_hook(keep)
    model.zero_grad(set_to_none=True)
    out = model(x[:16])
    out[:, READ_POS].gather(1, y[:16, None]).sum().backward()
    hk.remove()
    gq = store["e"].grad[:, Q_POS].norm(dim=-1)
    res["query_path"] = {"min_grad_norm_pos17": gq.min().item(), "pass": bool((gq > 0).all())}
    # tied embed=head gradient decomposition
    inp, outp, total = tied_decomposition(model, x[:32], y[:32])
    d = (inp + outp - total).abs().max().item()
    res["tied_decomposition"] = {"max_diff": d, "pass": d <= TOL_TIED}
    model.zero_grad(set_to_none=True)
    return res


def causal_structural(model, x, j):
    """Investigation of a causal_mask failure (not a pre-registered check):
    gradient of every record point and the logits at positions < j with
    respect to the input embeddings at positions >= j. Exactly 0 means no
    information path from position j onward to earlier positions, whatever
    floating-point rounding does to the forward values."""
    from runner import Runner

    store = {}

    def keep(mod, inp, out):
        out.retain_grad()
        store["e"] = out

    outs = []
    mods = list(model.layers) if hasattr(model, "layers") else (
        list(model.prelude) + [model.recurrent.block] + list(model.coda))
    hooks = [mm.register_forward_hook(lambda mod, i, o: outs.append(o)) for mm in mods]
    hooks.append(model.embed.register_forward_hook(keep))
    model.zero_grad(set_to_none=True)
    lg = model(x)
    tot = sum(o[:, :j].sum() for o in outs) + lg[:, :j].sum()
    tot.backward()
    for h in hooks:
        h.remove()
    g = store["e"].grad
    model.zero_grad(set_to_none=True)
    return {"max_grad_from_later_positions": g[:, j:].abs().max().item(),
            "max_grad_from_earlier_positions": g[:, :j].abs().max().item()}


# ------------------------------------------- revision 3 (PREREGISTRATION 10.2)

CAUSAL_J = ((Q_POS, ord("Z")), (10, ord("0")), (3, ord("z")))


def later_position_grad(outputs, inp, j, n_proj=2, seed=0):
    """For each output (B, T, ...) separately: gradient of <v, out[:, :j]> with
    random Gaussian v (n_proj independent draws) w.r.t. inp (B, T, D). Returns
    {name: (max |grad| at positions >= j, max |grad| at positions < j)}.
    A non-zero Jacobian from later to earlier positions gives a non-zero
    gradient with probability 1, so contributions cannot cancel."""
    g = torch.Generator().manual_seed(seed)
    res = {}
    for name, out in outputs.items():
        late, early = 0.0, 0.0
        for _ in range(n_proj):
            v = torch.randn(out[:, :j].shape, generator=g)
            (gr,) = torch.autograd.grad((out[:, :j] * v).sum(), inp, retain_graph=True,
                                        allow_unused=True)
            if gr is None:
                continue
            late = max(late, gr[:, j:].abs().max().item())
            early = max(early, gr[:, :j].abs().max().item())
        res[name] = (late, early)
    return res


def _float_records(rec, logits):
    out = {k: v for k, v in rec.items()
           if v.dim() >= 2 and v.shape[1] == L_PROMPT and v.is_floating_point() and v.requires_grad}
    out["logits"] = logits
    return out


def structural_causal_check(run, x):
    """Hard check: every float record point and the logits at positions < j
    have exactly zero gradient w.r.t. the input embeddings at positions >= j."""
    detail, worst = {}, 0.0
    for j, _ in CAUSAL_J:
        lg, rec, _ = run.run(x, record=True, grad=True)
        g = later_position_grad(_float_records(rec, lg), rec["emb"], j)
        worst = max(worst, max(v[0] for v in g.values()))
        detail[str(j)] = {"n_record_points": len(g),
                          "max_grad_from_later": max(v[0] for v in g.values()),
                          "nonzero_points": [k for k, v in g.items() if v[0] != 0.0]}
    return {"by_position": detail, "pass": worst == 0.0}


def moe_points(arm):
    return {"out1"} if arm == "transformer" else {f"blk_out{t}" for t in range(16)}


def causal_value_monitor(run, x):
    """Monitor (revision 3): forward value differences at positions < j when
    token j is replaced. Fails only if the first differing record point is not
    an MoE block output (a new kind of difference)."""
    detail, ok = {}, True
    for j, tok in CAUSAL_J:
        x2 = x.clone()
        x2[:, j] = tok
        la, a, _ = run.run(x, record=True)
        lb, b, _ = run.run(x2, record=True)
        a["logits"], b["logits"] = la, lb
        first, max_abs, max_rel = None, 0.0, 0.0
        for k in a:
            if not (a[k].dim() >= 2 and a[k].shape[1] == L_PROMPT):
                continue
            d = (a[k][:, :j].float() - b[k][:, :j].float()).abs().max().item()
            if d > 0:
                scale = a[k][:, :j].float().abs().max().item()
                max_rel = max(max_rel, d / scale if scale > 0 else float("inf"))
                first = first or k
            max_abs = max(max_abs, d)
        from_moe = first is None or first in moe_points(run.arm)
        ok &= from_moe
        detail[str(j)] = {"max_abs_diff": max_abs, "max_rel_diff": max_rel,
                          "first_differing_point": first, "first_is_moe_output": from_moe}
    return {"by_position": detail, "pass": ok}


def attention_future_zero(run, x):
    """Reconstructed attention weights above the diagonal are exactly 0."""
    _, _, att = run.run(x, want_attn=True)
    T = L_PROMPT
    upper = torch.triu(torch.ones(T, T, dtype=torch.bool), 1)
    worst = {k: w[..., upper].abs().max().item() for k, w in att.items()}
    return {"max_future_weight": worst, "pass": max(worst.values()) == 0.0}


def _moe_modules(model):
    from open_mythos.main import MoEFFN

    return [(n, m) for n, m in model.named_modules() if isinstance(m, MoEFFN)]


def moe_token_independence(model, x):
    """(b) No cross-token aggregation in MoE: per MoE layer, output at position
    i has zero gradient w.r.t. inputs at k != i; the experts chosen for a token
    are the same when it is routed alone as in the batch."""
    res, ok = {}, True
    for name, moe in _moe_modules(model):
        cap = []
        h = moe.register_forward_pre_hook(lambda m, a: cap.append(a[0].detach()))
        with torch.no_grad():
            model(x)
        h.remove()
        inp = cap[0].clone().requires_grad_(True)  # first call (loop 0 for OpenMythos)
        out = moe(inp)
        g = torch.Generator().manual_seed(0)
        cross = 0.0
        for i in range(L_PROMPT):
            for _ in range(2):
                v = torch.randn(out[:, i].shape, generator=g)
                (gr,) = torch.autograd.grad((out[:, i] * v).sum(), inp, retain_graph=True)
                mask = torch.ones(L_PROMPT, dtype=torch.bool)
                mask[i] = False
                cross = max(cross, gr[:, mask].abs().max().item())
        with torch.no_grad():
            flat = inp.detach().reshape(-1, inp.shape[-1])
            lb = moe.router(flat) + moe.router_bias
            idx_batch = lb.topk(moe.topk, dim=-1).indices
            idx_alone = torch.cat(
                [(moe.router(flat[r : r + 1]) + moe.router_bias).topk(moe.topk, dim=-1).indices
                 for r in range(flat.shape[0])]
            )
        mism = int((idx_batch != idx_alone).any(dim=-1).sum())
        res[name] = {"max_cross_token_grad": cross, "routing_mismatches": mism,
                     "n_tokens": int(flat.shape[0])}
        ok &= cross == 0.0 and mism == 0
    return {"layers": res, "pass": ok}


def moe_row_rounding(model, x):
    """(c) Evidence only (no pass/fail): one routed expert applied to the first
    5 vs the first 7 rows of a real MoE input; difference on the shared rows."""
    name, moe = _moe_modules(model)[0]
    cap = []
    h = moe.register_forward_pre_hook(lambda m, a: cap.append(a[0].detach()))
    with torch.no_grad():
        model(x)
        h.remove()
        flat = cap[0].reshape(-1, cap[0].shape[-1])
        ex = moe.routed_experts[0]
        d = (ex(flat[:5]) - ex(flat[:7])[:5]).abs().max().item()
    return {"layer": name, "expert": 0, "max_diff_shared_rows_5_vs_7": d}


def negative_controls():
    """Tool check: the structural checker reports exactly 0 for causal
    attention and a non-zero gradient for (a) attention without a mask and
    (b) a cross-token mean."""
    cfg = MythosConfig(vocab_size=8, dim=8, n_heads=2, n_kv_heads=1, max_seq_len=6,
                       attn_type="gqa", dropout=0.0)
    att = GQAttention(cfg)
    freqs = precompute_rope_freqs(4, 6, 10000.0)
    mask = torch.triu(torch.full((1, 1, 6, 6), float("-inf")), 1)
    x = torch.randn(2, 6, 8, generator=torch.Generator().manual_seed(3), requires_grad=True)
    causal = later_position_grad({"o": att(x, freqs, mask)}, x, 3)["o"][0]
    no_mask = later_position_grad({"o": att(x, freqs, None)}, x, 3)["o"][0]
    mean_leak = later_position_grad({"o": x + x.mean(1, keepdim=True)}, x, 3)["o"][0]
    return {"causal_attention": causal, "attention_without_mask": no_mask,
            "cross_token_mean": mean_leak,
            "pass": causal == 0.0 and no_mask > 0 and mean_leak > 0}
