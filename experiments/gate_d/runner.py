"""
Diagnostic re-implementation of the two forward passes with named record
points (PREREGISTRATION.md 8.1), activation patching (8.6, 9.3) and
reconstructed attention weights (8.2). It calls the models' own submodules
(norms, projections, FFN/MoE, LoRA, LTI, ACT head) in the same order as
open_mythos/main.py and basic_learn/models.py; D0 checks that its logits are
bitwise equal to model(x). The native code is not modified.

Record points
    transformer  emb, in{k}, mid{k}, out{k}            k = 0, 1, 2
    openmythos   emb, pre0.mid, e, h_before{t}, blk_in{t}, loop{t}.mid,
                 blk_out{t}, h{t+1}, act_w{t}, still{t}, cum_before{t},
                 halted_before{t}, hout_before{t}, h_out, coda0.mid, coda_out
Attention (query rows of every head): L{k} / pre0, loop{t}, coda0.

The recurrent loop always runs all n_loops iterations. The original breaks
early only when every position of the batch has halted; after that every ACT
weight is 0, so h_out (and the logits) are unchanged. Per-sample validity of
loop t (sample not fully halted before t) is recorded as valid{t}.

Patches: dict name -> (pos, src). pos is an int / list of positions or None
(all positions); src is a tensor of the full shape of that record point
(taken from another run's records). Special names for the full-state
replacement of OpenMythos loop interfaces:
    carry{t}       at the start of loop t: h, e, cum, halted, h_out
    carry_post{t}  after the LTI update of loop t: e, cum, halted, h_out
                   (src: dict of tensors from the source run's records)
"""

import torch
import torch.nn.functional as F

from open_mythos.main import apply_rope, loop_index_embedding


class Runner:
    def __init__(self, model):
        self.m = model
        self.arm = "transformer" if hasattr(model, "layers") else "openmythos"
        self.check_attn = False
        self.attn_diff = 0.0

    # --------------------------------------------------------------- pieces
    def _attn(self, mod, x, freqs, mask, want):
        B, T, _ = x.shape
        q = mod.wq(x).view(B, T, mod.n_heads, mod.head_dim)
        k = mod.wk(x).view(B, T, mod.n_kv_heads, mod.head_dim)
        v = mod.wv(x).view(B, T, mod.n_kv_heads, mod.head_dim)
        q = apply_rope(q, freqs)
        k = apply_rope(k, freqs)
        k = k.repeat_interleave(mod.groups, dim=2)
        v = v.repeat_interleave(mod.groups, dim=2)
        q, k, v = q.transpose(1, 2), k.transpose(1, 2), v.transpose(1, 2)
        att = torch.matmul(q, k.transpose(-2, -1)) * mod.head_dim**-0.5
        if mask is not None:
            att = att + mask
        w = F.dropout(F.softmax(att, dim=-1), p=mod.dropout_p, training=mod.training)
        out = torch.matmul(w, v).transpose(1, 2).contiguous().view(B, T, -1)
        out = mod.wo(out)
        if self.check_attn:
            ref = mod(x, freqs, mask, None, "check")
            self.attn_diff = max(self.attn_diff, (ref - out).abs().max().item())
        return out, (w if want else None)

    def _block(self, blk, x, freqs, mask, tag, ctx):
        a = blk.attn_norm(x)
        ao, w = self._attn(blk.attn, a, freqs, mask, ctx["want_attn"])
        if w is not None:
            ctx["attn"][tag] = w
        h = self._tap(f"{tag}.mid", x + blk.resid_drop(ao), ctx)
        return h + blk.resid_drop(blk.ffn(blk.ffn_norm(h)))

    def _tap(self, name, t, ctx):
        if name in ctx["patch"]:
            pos, src = ctx["patch"][name]
            t = t.clone()
            if pos is None:
                t[...] = src
            else:
                t[:, pos] = src[:, pos]
        if ctx["record"] is True or (ctx["record"] and name in ctx["record"]):
            ctx["rec"][name] = t
        return t

    # -------------------------------------------------------------- forward
    def run(self, ids, patch=None, record=False, want_attn=False, n_loops=None, grad=False):
        """Returns (logits at every position, records dict, attention dict).
        grad=True keeps the autograd graph (D0 structural checks only)."""
        ctx = {"patch": patch or {}, "record": record, "rec": {}, "attn": {},
               "want_attn": want_attn}
        with torch.set_grad_enabled(grad):
            if self.arm == "transformer":
                logits = self._run_transformer(ids, ctx)
            else:
                logits = self._run_openmythos(ids, ctx, n_loops)
        return logits, ctx["rec"], ctx["attn"]

    def _run_transformer(self, ids, ctx):
        m = self.m
        T = ids.shape[1]
        x = self._tap("emb", m.embed(ids), ctx)
        freqs = m.freqs_cis[:T]
        mask = torch.triu(
            torch.full((1, 1, T, T), float("-inf"), device=x.device, dtype=x.dtype), 1
        )
        for i, layer in enumerate(m.layers):
            x = self._tap(f"in{i}", x, ctx)
            x = self._block(layer, x, freqs, mask, f"L{i}", ctx)
            x = self._tap(f"out{i}", x, ctx)
        return m.head(m.norm(x))

    def _run_openmythos(self, ids, ctx, n_loops):
        m, rb = self.m, self.m.recurrent
        T = ids.shape[1]
        x = self._tap("emb", m.embed(ids), ctx)
        freqs = m.freqs_cis[0:T]
        mask = m._causal_mask(T, x.device, x.dtype) if T > 1 else None
        for i, layer in enumerate(m.prelude):
            x = self._block(layer, x, freqs, mask, f"pre{i}", ctx)
        e = self._tap("e", x, ctx)
        h = e
        n_loops = n_loops or rb.cfg.max_loop_iters
        B = ids.shape[0]
        halted = torch.zeros(B, T, dtype=torch.bool)
        cum = torch.zeros(B, T)
        h_out = torch.zeros_like(h)
        thr = rb.cfg.act_threshold
        rec = ctx["rec"]
        for t in range(n_loops):
            if f"carry{t}" in ctx["patch"]:
                c = ctx["patch"][f"carry{t}"][1]
                h, e = c[f"h_before{t}"].clone(), c["e"].clone()
                cum, halted = c[f"cum_before{t}"].clone(), c[f"halted_before{t}"].clone()
                h_out = c[f"hout_before{t}"].clone()
            if ctx["record"]:
                rec[f"h_before{t}"], rec[f"cum_before{t}"] = h, cum
                rec[f"halted_before{t}"], rec[f"hout_before{t}"] = halted, h_out
                rec[f"valid{t}"] = ~halted.all(dim=1)
            combined = rb.norm(loop_index_embedding(h, t, rb.loop_dim) + e)
            combined = self._tap(f"blk_in{t}", combined, ctx)
            trans_out = self._block(rb.block, combined, freqs, mask, f"loop{t}", ctx)
            trans_out = trans_out + rb.lora(trans_out, t)
            trans_out = self._tap(f"blk_out{t}", trans_out, ctx)
            h = rb.injection(h, e, trans_out)
            if f"carry_post{t}" in ctx["patch"]:
                c = ctx["patch"][f"carry_post{t}"][1]
                e = c["e"].clone()
                cum, halted = c[f"cum_before{t}"].clone(), c[f"halted_before{t}"].clone()
                h_out = c[f"hout_before{t}"].clone()
            h = self._tap(f"h{t + 1}", h, ctx)
            p = rb.act(h)
            still = ~halted
            remainder = (1.0 - cum).clamp(min=0)
            weight = torch.where(cum + p >= thr, remainder, p)
            weight = weight * still.float()
            h_out = h_out + weight.unsqueeze(-1) * h
            cum = cum + p * still.float()
            halted = halted | (cum >= thr)
            if ctx["record"]:
                rec[f"act_w{t}"], rec[f"still{t}"] = weight, still
        if ctx["record"]:
            rec["cum_final"], rec["halted_final"] = cum, halted
        x = self._tap("h_out", h_out, ctx)
        for i, layer in enumerate(m.coda):
            x = self._block(layer, x, freqs, mask, f"coda{i}", ctx)
        x = self._tap("coda_out", x, ctx)
        return m.head(m.norm(x))


def probe_points(arm, n_loops=4):
    """Record points read by the D2 probes (block outputs, PREREGISTRATION 3/8.1)."""
    if arm == "transformer":
        return ["emb", "out0", "out1", "out2"]
    return ["emb", "e"] + [f"h{t + 1}" for t in range(n_loops)] + ["h_out", "coda_out"]


def attn_layers(arm, n_loops=4):
    if arm == "transformer":
        return ["L0", "L1", "L2"]
    return ["pre0"] + [f"loop{t}" for t in range(n_loops)] + ["coda0"]
