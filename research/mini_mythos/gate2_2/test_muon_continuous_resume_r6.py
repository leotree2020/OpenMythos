"""S2-4R6 continuous vs resume. CPU only. Not Fabric e2e. Not Gate 2.2-C PASS."""
import json
import tempfile
from pathlib import Path

import torch
from parcae_lm.models.parcae.parcae import Parcae, ParcaeConfig
from recpre.optim.muon_adamw import MuonAdamW, get_muon_param_groups


def cfg():
    return ParcaeConfig(
        n_embd=32, intermediate_size=64, num_attention_heads=2, num_key_value_heads=2,
        vocab_size=128, padded_vocab_size=128, block_size=8,
        n_layers_in_prelude=1, n_layers_in_recurrent_block=1, n_layers_in_coda=1,
        mean_recurrence=1, mean_backprop_depth=1, recurrent_embedding_dimension=32,
        recurrent_intermediation_embedding_dimension=64, prelude_norm=True,
        injection_type="diagonal", state_init="normal", tie_embeddings=True,
        use_fused_head="pytorch", sampling_scheme="fixed",
    )


def strict_equal(a, b, path=""):
    if torch.is_tensor(a) and torch.is_tensor(b):
        if a.shape != b.shape or a.dtype != b.dtype:
            return False, path or "tensor", None
        if torch.equal(a, b):
            return True, None, 0.0
        diff = (a.detach().float() - b.detach().float()).abs()
        return False, path or "tensor", diff.max().item()
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) != set(b):
            return False, path or "dict-keys", None
        worst = 0.0
        for k in a:
            ok, where, mx = strict_equal(a[k], b[k], f"{path}.{k}" if path else str(k))
            if not ok:
                return False, where, mx
            if isinstance(mx, float):
                worst = max(worst, mx)
        return True, None, worst
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)) and type(a) is type(b):
        if len(a) != len(b):
            return False, path or "len", None
        for i, (x, y) in enumerate(zip(a, b)):
            ok, where, mx = strict_equal(x, y, f"{path}[{i}]")
            if not ok:
                return False, where, mx
        return True, None, 0.0
    if type(a) is type(b) and a == b:
        return True, None, 0.0
    return False, path or type(a).__name__, None


def shared_ptrs(oa, ob):
    def ptrs(opt):
        out = set()
        for st in opt.state.values():
            for v in st.values():
                if torch.is_tensor(v):
                    out.add(v.data_ptr())
        return out
    return ptrs(oa) & ptrs(ob)


def fresh():
    torch.manual_seed(7)
    m = Parcae(cfg())
    o = MuonAdamW(get_muon_param_groups(m.named_parameters()))
    x = torch.randint(0, 128, (1, 4))
    o.zero_grad(set_to_none=True)
    y = m(x, labels=x, return_logits=False, num_steps_pair=(torch.tensor(1), torch.tensor(1)))
    y["loss"].backward()
    o.step()
    return m, o


def resume_from_file(path):
    raw = torch.load(path, map_location="cpu", weights_only=False)
    m = Parcae(cfg())
    m.load_state_dict(raw["model"])
    o = MuonAdamW(get_muon_param_groups(m.named_parameters()))
    o.load_state_dict(raw["opt"])
    return m, o


def next_step(m, o, seed):
    torch.manual_seed(seed)
    x = torch.randint(0, 128, (1, 4))
    o.zero_grad(set_to_none=True)
    empty = all(p.grad is None for p in m.parameters())
    y = m(x, labels=x, return_logits=False, num_steps_pair=(torch.tensor(1), torch.tensor(1)))
    y["loss"].backward()
    grads = {n: p.grad.detach().clone() for n, p in m.named_parameters() if p.grad is not None}
    o.step()
    return x, empty, grads, torch.isfinite(y["loss"]).all().item()


def main():
    checks = []
    a, oa = fresh()
    a_id = id(a)
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "ckpt.pt"
        torch.save({"model": a.state_dict(), "opt": oa.state_dict()}, path)
        b, ob = resume_from_file(path)
        # A was not rebuilt
        checks.append({"name": "a_not_rebuilt", "ok": id(a) == a_id})
        ok, where, mx = strict_equal(a.state_dict(), b.state_dict())
        checks.append({"name": "pre_model", "ok": ok, "where": where, "max_abs": mx})
        ok, where, mx = strict_equal(oa.state_dict(), ob.state_dict())
        checks.append({"name": "pre_opt", "ok": ok, "where": where, "max_abs": mx})
        checks.append({"name": "no_shared", "ok": not shared_ptrs(oa, ob)})
        checks.append({"name": "same_mode", "ok": a.training == b.training})

        # AB
        xa, empty_a, ga, finite_a = next_step(a, oa, 11)
        xb, empty_b, gb, finite_b = next_step(b, ob, 11)
        checks.append({"name": "grad_empty", "ok": empty_a and empty_b})
        checks.append({"name": "same_input", "ok": torch.equal(xa, xb)})
        ok, where, mx = strict_equal(ga, gb)
        checks.append({"name": "grads", "ok": ok, "where": where, "max_abs": mx})
        ok, where, mx = strict_equal(a.state_dict(), b.state_dict())
        checks.append({"name": "after_ab_model", "ok": ok, "where": where, "max_abs": mx})
        ok, where, mx = strict_equal(oa.state_dict(), ob.state_dict())
        checks.append({"name": "after_ab_opt", "ok": ok, "where": where, "max_abs": mx})
        checks.append({"name": "finite", "ok": finite_a and finite_b})

        # BA from fresh
        a2, oa2 = fresh()
        with tempfile.TemporaryDirectory() as td2:
            p2 = Path(td2) / "c.pt"
            torch.save({"model": a2.state_dict(), "opt": oa2.state_dict()}, p2)
            b2, ob2 = resume_from_file(p2)
        next_step(b2, ob2, 11)
        next_step(a2, oa2, 11)
        ok, where, mx = strict_equal(a2.state_dict(), b2.state_dict())
        checks.append({"name": "after_ba_model", "ok": ok, "where": where, "max_abs": mx})

        # negative: shared load without clone
        raw = {"model": a.state_dict(), "opt": oa.state_dict()}
        n1 = Parcae(cfg()); n1.load_state_dict(raw["model"])
        o1 = MuonAdamW(get_muon_param_groups(n1.named_parameters())); o1.load_state_dict(raw["opt"])
        n2 = Parcae(cfg()); n2.load_state_dict(raw["model"])
        o2 = MuonAdamW(get_muon_param_groups(n2.named_parameters())); o2.load_state_dict(raw["opt"])
        checks.append({"name": "negative_shared_storage", "shared": bool(shared_ptrs(o1, o2))})

    failed = [c["name"] for c in checks if c.get("ok") is False]
    status = "CPU RESTORE BIT-EXACT PASS" if not failed else "FAIL"
    print(json.dumps({
        "status": status,
        "checks": checks,
        "failed": failed,
        "note": "CPU file restore. Not Fabric e2e. GPU NOT TESTED. Gate 2.2-C NOT PASS.",
    }, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
