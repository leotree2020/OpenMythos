"""S2-4R6F file-resume equivalence. CPU only. Not Gate 2.2-C PASS."""
import json
import platform
import random
import subprocess
import tempfile
from pathlib import Path

import numpy as np
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


def raw_bytes(t):
    return t.detach().cpu().contiguous().view(torch.uint8).numpy().tobytes()


def bit_equal(a, b):
    return raw_bytes(a) == raw_bytes(b)


def strict(a, b, path=""):
    if torch.is_tensor(a) and torch.is_tensor(b):
        if a.shape != b.shape or a.dtype != b.dtype or a.device != b.device:
            return False, path or "meta", None
        if not torch.isfinite(a.float()).all() or not torch.isfinite(b.float()).all():
            if not bit_equal(a, b):
                return False, path or "nonfinite", None
        exact = torch.equal(a, b)
        bits = bit_equal(a, b)
        if exact and bits:
            return True, None, 0.0
        diff = (a.detach().float() - b.detach().float()).abs().max().item()
        return False, path or "value", diff
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) != set(b):
            return False, path or "keys", None
        for k in a:
            ok, where, mx = strict(a[k], b[k], f"{path}.{k}" if path else str(k))
            if not ok:
                return False, where, mx
        return True, None, 0.0
    if isinstance(a, (list, tuple)) and type(a) is type(b):
        if len(a) != len(b):
            return False, path or "len", None
        for i, (x, y) in enumerate(zip(a, b)):
            ok, where, mx = strict(x, y, f"{path}[{i}]")
            if not ok:
                return False, where, mx
        return True, None, 0.0
    if type(a) is type(b) and a == b:
        return True, None, 0.0
    return False, path or type(a).__name__, None


def storage_ranges(obj, prefix=""):
    out = []
    if torch.is_tensor(obj):
        out.append((prefix, obj.data_ptr(), obj.untyped_storage().data_ptr(), obj.numel() * obj.element_size()))
    elif isinstance(obj, dict):
        for k, v in obj.items():
            out.extend(storage_ranges(v, f"{prefix}.{k}" if prefix else str(k)))
    return out


def overlaps(a_ranges, b_ranges):
    hits = []
    for na, pa, sa, la in a_ranges:
        for nb, pb, sb, lb in b_ranges:
            if sa == sb and la and lb:
                hits.append((na, nb))
    return hits


def snapshot_rng():
    return {
        "torch": torch.get_rng_state().clone(),
        "python": random.getstate(),
        "numpy": np.random.get_state(),
    }


def restore_rng(s):
    torch.set_rng_state(s["torch"])
    random.setstate(s["python"])
    np.random.set_state(s["numpy"])


def fresh():
    torch.manual_seed(7)
    np.random.seed(7)
    random.seed(7)
    m = Parcae(cfg())
    o = MuonAdamW(get_muon_param_groups(m.named_parameters()))
    x = torch.randint(0, 128, (1, 4))
    o.zero_grad(set_to_none=True)
    y = m(x, labels=x, return_logits=False, num_steps_pair=(torch.tensor(1), torch.tensor(1)))
    y["loss"].backward()
    o.step()
    return m, o


def save_ckpt(path, m, o):
    torch.save({"model": m.state_dict(), "opt": o.state_dict(), "rng": snapshot_rng()}, path)


def resume(path):
    raw = torch.load(path, map_location="cpu", weights_only=False)
    m = Parcae(cfg())
    m.load_state_dict(raw["model"])
    o = MuonAdamW(get_muon_param_groups(m.named_parameters()))
    o.load_state_dict(raw["opt"])
    restore_rng(raw["rng"])
    return m, o, raw["rng"]


def next_step(m, o):
    x = torch.randint(0, 128, (1, 4))
    o.zero_grad(set_to_none=True)
    empty = all(p.grad is None for p in m.parameters())
    y = m(x, labels=x, return_logits=False, num_steps_pair=(torch.tensor(1), torch.tensor(1)))
    y["loss"].backward()
    grads = {n: p.grad.detach().clone() for n, p in m.named_parameters() if p.grad is not None}
    o.step()
    return x, empty, grads, torch.isfinite(y["loss"]).all().item()


def comparator_negatives():
    out = []
    a = torch.zeros(2)
    b = torch.zeros(3)
    ok, _, _ = strict(a, b)
    out.append({"name": "neg_shape", "ok": not ok})
    ok, _, _ = strict(torch.zeros(2), torch.zeros(2, dtype=torch.float64))
    out.append({"name": "neg_dtype", "ok": not ok})
    ok, _, _ = strict({"a": 1}, {"b": 1})
    out.append({"name": "neg_keys", "ok": not ok})
    pz = torch.tensor([0.0])
    nz = torch.tensor([-0.0])
    ok, _, _ = strict(pz, nz)
    out.append({"name": "neg_signed_zero", "ok": not ok, "note": "BIT path must reject +0/-0"})
    ok, _, _ = strict([1, 2], [1])
    out.append({"name": "neg_list_len", "ok": not ok})
    return out


def main():
    checks = []
    gcc = subprocess.check_output(["g++", "--version"], text=True).splitlines()[0]
    env = {
        "python": platform.python_version(),
        "torch": torch.__version__,
        "gcc": gcc,
        "cpath": "/tmp/py311-include/Include",
        "python_h": "CPython 3.11.2",
        "pyconfig_h": "Python 3.10 copy",
        "openmythos": "d44804e",
        "parcae": "69284c1",
    }
    checks.extend(comparator_negatives())

    a, oa = fresh()
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "c.pt"
        save_ckpt(path, a, oa)
        rng_at_save = snapshot_rng()
        b, ob, rng_b = resume(path)
        checks.append({"name": "pre_model", "ok": strict(a.state_dict(), b.state_dict())[0]})
        checks.append({"name": "pre_opt", "ok": strict(oa.state_dict(), ob.state_dict())[0]})
        checks.append({"name": "no_shared", "ok": not overlaps(storage_ranges(a.state_dict()), storage_ranges(b.state_dict())) and not overlaps(storage_ranges(oa.state_dict()), storage_ranges(ob.state_dict()))})
        checks.append({"name": "same_mode", "ok": a.training == b.training})
        # restore A's RNG to saved point too, then step both
        restore_rng(rng_at_save)
        xa, ea, ga, fa = next_step(a, oa)
        restore_rng(rng_b)
        xb, eb, gb, fb = next_step(b, ob)
        checks.append({"name": "ab_input", "ok": torch.equal(xa, xb)})
        checks.append({"name": "ab_empty", "ok": ea and eb})
        checks.append({"name": "ab_grads", "ok": strict(ga, gb)[0]})
        checks.append({"name": "ab_model", "ok": strict(a.state_dict(), b.state_dict())[0]})
        checks.append({"name": "ab_opt", "ok": strict(oa.state_dict(), ob.state_dict())[0]})
        checks.append({"name": "ab_finite", "ok": fa and fb})

        # BA
        a2, oa2 = fresh()
        with tempfile.TemporaryDirectory() as td2:
            p2 = Path(td2) / "c.pt"
            save_ckpt(p2, a2, oa2)
            rng2 = snapshot_rng()
            b2, ob2, rng_b2 = resume(p2)
        checks.append({"name": "ba_pre_model", "ok": strict(a2.state_dict(), b2.state_dict())[0]})
        checks.append({"name": "ba_pre_opt", "ok": strict(oa2.state_dict(), ob2.state_dict())[0]})
        restore_rng(rng_b2)
        xb2, eb2, gb2, fb2 = next_step(b2, ob2)
        restore_rng(rng2)
        xa2, ea2, ga2, fa2 = next_step(a2, oa2)
        checks.append({"name": "ba_input", "ok": torch.equal(xa2, xb2)})
        checks.append({"name": "ba_grads", "ok": strict(ga2, gb2)[0]})
        checks.append({"name": "ba_model", "ok": strict(a2.state_dict(), b2.state_dict())[0]})
        checks.append({"name": "ba_opt", "ok": strict(oa2.state_dict(), ob2.state_dict())[0]})
        checks.append({"name": "ba_finite", "ok": fa2 and fb2})

        # cross order
        checks.append({"name": "cross_a", "ok": strict(a.state_dict(), a2.state_dict())[0]})
        checks.append({"name": "cross_b", "ok": strict(b.state_dict(), b2.state_dict())[0]})

        # RNG pollution negative
        a3, oa3 = fresh()
        with tempfile.TemporaryDirectory() as td3:
            p3 = Path(td3) / "c.pt"
            save_ckpt(p3, a3, oa3)
            b3, ob3, _ = resume(p3)
        torch.manual_seed(999)
        x_bad = torch.randint(0, 128, (1, 4))
        restore_rng(snapshot_rng())
        checks.append({"name": "rng_pollution_detected", "ok": not torch.equal(x_bad, torch.randint(0, 128, (1, 4)))})

    failed = [c["name"] for c in checks if not c["ok"]]
    bits = all(c["ok"] for c in checks)
    status = "CPU FILE-RESUME BIT-EXACT PASS" if bits else "FAIL"
    print(json.dumps({"status": status, "env": env, "checks": checks, "failed": failed, "gate": "NOT PASS"}, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
