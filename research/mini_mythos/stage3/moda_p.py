"""MoDA-P: depth attention for Parcae's recurrent core, added through hooks (upstream untouched).

Write: after core layer j finishes a pass, its output h is stored for every token as
    k = qknorm(W_k[j] @ norm1_{next}(h)),  v = W_v[j] @ norm1_{next}(h)
where next = (j + 1) % n_core (the layer that reads h next) and W_k[j], W_v[j] start as copies of
that layer's own c_k, c_v. Writes from recurrence steps run without gradient still build a graph
for W_k / W_v (the state itself carries no gradient there).
Read: inside core layer l's attention, each head attends with its own query (c_q + qk-norm; RoPE
cancels at equal positions) over all entries already written at the same token position, with a
separate softmax; the result is scaled per head by gate[l] (initialised to 0) and added to the
attention output before c_proj. With all gates 0 the model is bitwise the native one.
"""
import contextlib
import math

import torch
import torch.nn.functional as F


def _rms(x):
    return F.rms_norm(x, (x.size(-1),))


class MoDAP:
    def __init__(self, model, collect_stats=False):
        core = model.transformer.core_block
        cfg = model.config
        if getattr(cfg, "qk_bias", False) or getattr(cfg, "clip_qkv", None) is not None:
            raise NotImplementedError("qk_bias / clip_qkv not supported")
        a0 = core[0].attn
        self.n_core = len(core)
        self.H, self.Hk, self.d = a0.n_head, a0.n_kv_head, a0.head_dim
        self.qk_norm = bool(cfg.qk_norm)
        self.scale = 1.0 / math.sqrt(self.d)
        self.params, self.handles = {}, []
        self.write_k, self.write_v, self.gates = [], [], []
        for j in range(self.n_core):
            reader = core[(j + 1) % self.n_core]
            wk = torch.nn.Parameter(reader.attn.c_k.weight.detach().clone())
            wv = torch.nn.Parameter(reader.attn.c_v.weight.detach().clone())
            self.params["write.%d.k" % j], self.params["write.%d.v" % j] = wk, wv
            self.write_k.append(wk)
            self.write_v.append(wv)
        for l in range(self.n_core):
            g = torch.nn.Parameter(torch.zeros(self.H, device=a0.c_q.weight.device))
            self.params["gate.%d" % l] = g
            self.gates.append(g)
        self.collect_stats = collect_stats
        self.stats = {"reads": 0, "entropy_sum": 0.0, "ratio_sum": 0.0}
        self._clear()
        self.handles.append(model.register_forward_pre_hook(self._begin))
        self.handles.append(model.register_forward_hook(self._end))
        for j, block in enumerate(core):
            self.handles.append(block.register_forward_hook(self._writer(j, core[(j + 1) % self.n_core].norm_1)))
            self.handles.append(block.attn.c_q.register_forward_hook(self._query(j)))
            self.handles.append(block.attn.c_proj.register_forward_pre_hook(self._reader(j)))

    # -------------------------------------------------------------- state per forward
    def _clear(self):
        self.k, self.v, self.q = [], [], {}
        self.grad_writes = False

    def _begin(self, module, args):
        self._clear()
        self.grad_writes = torch.is_grad_enabled() and any(p.requires_grad for p in self.write_k)

    def _end(self, module, args, output):
        self._clear()

    def _writer(self, j, norm_next):
        def hook(module, args, h):
            ctx = torch.enable_grad() if self.grad_writes else contextlib.nullcontext()
            with ctx:
                B, T, _ = h.shape
                hn = norm_next(h)
                k = F.linear(hn, self.write_k[j]).view(B, T, self.Hk, self.d)
                v = F.linear(hn, self.write_v[j]).view(B, T, self.Hk, self.d)
                if self.qk_norm:
                    k = _rms(k)
            self.k.append(k)
            self.v.append(v)
        return hook

    def _query(self, l):
        def hook(module, args, out):
            self.q[l] = out
        return hook

    def _reader(self, l):
        def hook(module, args):
            if not self.k:
                return None
            y = args[0]
            B, T, C = y.shape
            q = self.q.pop(l).view(B, T, self.H, self.d)
            if self.qk_norm:
                q = _rms(q)
            K = torch.stack(self.k, dim=2)                        # [B, T, L, Hk, d]
            V = torch.stack(self.v, dim=2)
            if self.Hk != self.H:                                 # query head h uses kv head h // rep
                K = K.repeat_interleave(self.H // self.Hk, dim=3)
                V = V.repeat_interleave(self.H // self.Hk, dim=3)
            logits = torch.einsum("bthd,btlhd->bthl", q, K.to(q.dtype)) * self.scale
            w = torch.softmax(logits.float(), dim=-1)
            out = torch.einsum("bthl,btlhd->bthd", w.to(V.dtype), V)
            out = out * self.gates[l].view(1, 1, self.H, 1).to(out.dtype)
            out = out.reshape(B, T, C).to(y.dtype)
            if self.collect_stats:
                with torch.no_grad():
                    ent = -(w * torch.log(w.clamp_min(1e-30))).sum(-1).mean()
                    self.stats["reads"] += 1
                    self.stats["entropy_sum"] += float(ent)
                    self.stats["ratio_sum"] += float(out.float().norm() / y.float().norm().clamp_min(1e-30))
            return (y + out,)
        return hook

    # -------------------------------------------------------------- bookkeeping
    def parameters(self):
        return list(self.params.values())

    def count(self):
        return sum(p.numel() for p in self.params.values())

    def summary_stats(self):
        n = max(1, self.stats["reads"])
        return {"reads": self.stats["reads"], "mean_depth_attention_entropy": self.stats["entropy_sum"] / n,
                "mean_depth_to_attention_norm_ratio": self.stats["ratio_sum"] / n,
                "gate_abs_mean": {k: float(p.detach().abs().mean()) for k, p in self.params.items()
                                  if k.startswith("gate")}}

    def remove(self):
        for h in self.handles:
            h.remove()
        self._clear()
