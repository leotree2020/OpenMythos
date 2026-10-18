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
    # causal mask: replacing token j leaves every record at positions < j unchanged
    tensors = lambda r: {k: v for k, v in r.items() if v.dim() >= 2 and v.shape[1] == L_PROMPT}  # noqa: E731
    fn = lambda ids: tensors(run.run(ids, record=True)[1]) | {"logits": run.run(ids)[0]}  # noqa: E731
    sub = x[:64]
    diffs = {}
    for j, tok in ((Q_POS, ord("Z")), (10, ord("0")), (3, ord("z"))):
        repl = torch.full((sub.shape[0],), tok)
        diffs[str(j)] = causal_diff(fn, sub, j, repl)
    res["causal_mask"] = {"max_diff_by_position": diffs, "pass": max(diffs.values()) == 0.0}
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
