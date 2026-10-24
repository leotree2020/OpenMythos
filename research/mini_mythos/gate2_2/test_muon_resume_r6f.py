"""S2-4R6F-FIX. CPU file-resume only. Not Gate 2.2-C PASS."""
import json
import platform
import random
import subprocess
import sys
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
    x = t.detach().cpu().contiguous()
    if x.ndim == 0:
        x = x.reshape(1)
    return x.view(torch.uint8).numpy().tobytes()


def finite_tree(obj):
    if torch.is_tensor(obj) and obj.is_floating_point():
        return bool(torch.isfinite(obj).all())
    if isinstance(obj, dict):
        return all(finite_tree(v) for v in obj.values())
    if isinstance(obj, (list, tuple)):
        return all(finite_tree(v) for v in obj)
    return True


def strict(a, b, path=""):
    if torch.is_tensor(a) and torch.is_tensor(b):
        if a.shape != b.shape or a.dtype != b.dtype or a.device != b.device:
            return False, path or "meta"
        if a.is_floating_point() and (not torch.isfinite(a).all() or not torch.isfinite(b).all()):
            return False, path or "nonfinite"
        if raw_bytes(a) != raw_bytes(b):
            return False, path or "bytes"
        return True, None
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) != set(b):
            return False, path or "keys"
        for k in a:
            ok, where = strict(a[k], b[k], f"{path}.{k}" if path else str(k))
            if not ok:
                return False, where
        return True, None
    if isinstance(a, (list, tuple)) and type(a) is type(b):
        if len(a) != len(b):
            return False, path or "len"
        for i, (x, y) in enumerate(zip(a, b)):
            ok, where = strict(x, y, f"{path}[{i}]")
            if not ok:
                return False, where
        return True, None
    if type(a) is type(b) and a == b:
        return True, None
    return False, path or type(a).__name__


def storage_ranges(obj, prefix=""):
    out = []
    if torch.is_tensor(obj):
        out.append((prefix, obj.untyped_storage().data_ptr(), obj.storage_offset(), obj.numel()))
    elif isinstance(obj, dict):
        for k, v in obj.items():
            out.extend(storage_ranges(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            out.extend(storage_ranges(v, f"{prefix}[{i}]"))
    return out


def overlaps(a, b):
    return any(sa == sb and na_n and nb_n for _, sa, _, na_n in a for _, sb, _, nb_n in b)


def snap():
    return {"torch": torch.get_rng_state().clone(), "python": random.getstate(), "numpy": np.random.get_state()}


def apply_rng(s):
    torch.set_rng_state(s["torch"])
    random.setstate(s["python"])
    np.random.set_state(s["numpy"])


def rng_equal(a, b):
    if not torch.equal(a["torch"], b["torch"]):
        return False, "torch"
    if a["python"] != b["python"]:
        return False, "python"
    na, nb = a["numpy"], b["numpy"]
    if len(na) != len(nb):
        return False, "numpy-len"
    for i, (x, y) in enumerate(zip(na, nb)):
        if hasattr(x, "shape"):
            if not np.array_equal(x, y):
                return False, f"numpy[{i}]"
        elif x != y:
            return False, f"numpy[{i}]"
    return True, None


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
    torch.save({"model": m.state_dict(), "opt": o.state_dict(), "rng": snap()}, path)


def resume(path):
    raw = torch.load(path, map_location="cpu", weights_only=False)
    m = Parcae(cfg())
    m.load_state_dict(raw["model"])
    o = MuonAdamW(get_muon_param_groups(m.named_parameters()))
    o.load_state_dict(raw["opt"])
    apply_rng(raw["rng"])
    return m, o, raw


def next_step(m, o):
    x = torch.randint(0, 128, (1, 4))
    o.zero_grad(set_to_none=True)
    empty = all(p.grad is None for p in m.parameters())
    y = m(x, labels=x, return_logits=False, num_steps_pair=(torch.tensor(1), torch.tensor(1)))
    y["loss"].backward()
    grads = {n: p.grad.detach().clone() for n, p in m.named_parameters() if p.grad is not None}
    loss_ok = finite_tree(y["loss"]) and finite_tree(grads)
    o.step()
    return x, empty, grads, loss_ok and finite_tree(m.state_dict()) and finite_tree(o.state_dict())


def main():
    checks = []
    env = {
        "python": platform.python_version(),
        "torch": torch.__version__,
        "gcc": subprocess.check_output(["g++", "--version"], text=True).splitlines()[0],
        "cpath": "/tmp/py311-include/Include",
        "include": sysconfig_include(),
        "openmythos": "4d57cb0",
        "parcae": "69284c1",
        "abi_risk": "3.11.2 headers with 3.10 pyconfig.h",
    }
    # comparator negatives
    checks.append({"name": "neg_shape", "ok": not strict(torch.zeros(2), torch.zeros(3))[0]})
    checks.append({"name": "neg_dtype", "ok": not strict(torch.zeros(2), torch.zeros(2, dtype=torch.float64))[0]})
    checks.append({"name": "neg_keys", "ok": not strict({"a": 1}, {"b": 1})[0]})
    checks.append({"name": "neg_signed_zero", "ok": not strict(torch.tensor(0.0), torch.tensor(-0.0))[0]})
    checks.append({"name": "neg_scalar", "ok": strict(torch.tensor(1.0), torch.tensor(1.0))[0]})
    checks.append({"name": "neg_nan", "ok": not strict(torch.tensor(float("nan")), torch.tensor(float("nan")))[0]})

    a, oa = fresh()
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "c.pt"
        save_ckpt(path, a, oa)
        saved = torch.load(path, map_location="cpu", weights_only=False)
        b, ob, raw = resume(path)
        now = snap()
        ok, field = rng_equal(now, raw["rng"])
        checks.append({"name": "resume_rng_immediate", "ok": ok, "field": field})
        checks.append({"name": "pre_model", "ok": strict(a.state_dict(), b.state_dict())[0]})
        checks.append({"name": "pre_opt", "ok": strict(oa.state_dict(), ob.state_dict())[0]})
        checks.append({"name": "no_shared", "ok": not overlaps(storage_ranges(a.state_dict()), storage_ranges(b.state_dict()))})
        checks.append({"name": "same_mode", "ok": a.training == b.training})
        apply_rng(saved["rng"])
        xa, ea, ga, fa = next_step(a, oa)
        apply_rng(raw["rng"])
        xb, eb, gb, fb = next_step(b, ob)
        checks.append({"name": "ab_input", "ok": torch.equal(xa, xb)})
        checks.append({"name": "ab_empty", "ok": ea and eb})
        checks.append({"name": "ab_grads", "ok": strict(ga, gb)[0]})
        checks.append({"name": "ab_model", "ok": strict(a.state_dict(), b.state_dict())[0]})
        checks.append({"name": "ab_opt", "ok": strict(oa.state_dict(), ob.state_dict())[0]})
        checks.append({"name": "ab_finite", "ok": fa and fb})

        a2, oa2 = fresh()
        with tempfile.TemporaryDirectory() as td2:
            p2 = Path(td2) / "c.pt"
            save_ckpt(p2, a2, oa2)
            saved2 = torch.load(p2, map_location="cpu", weights_only=False)
            b2, ob2, raw2 = resume(p2)
        checks.append({"name": "ba_pre", "ok": strict(a2.state_dict(), b2.state_dict())[0] and strict(oa2.state_dict(), ob2.state_dict())[0]})
        checks.append({"name": "ba_no_shared", "ok": not overlaps(storage_ranges(oa2.state_dict()), storage_ranges(ob2.state_dict()))})
        checks.append({"name": "ba_mode", "ok": a2.training == b2.training})
        apply_rng(raw2["rng"])
        xb2, eb2, gb2, fb2 = next_step(b2, ob2)
        apply_rng(saved2["rng"])
        xa2, ea2, ga2, fa2 = next_step(a2, oa2)
        checks.append({"name": "ba_empty", "ok": ea2 and eb2})
        checks.append({"name": "ba_input", "ok": torch.equal(xa2, xb2)})
        checks.append({"name": "ba_grads", "ok": strict(ga2, gb2)[0]})
        checks.append({"name": "ba_model", "ok": strict(a2.state_dict(), b2.state_dict())[0]})
        checks.append({"name": "ba_opt", "ok": strict(oa2.state_dict(), ob2.state_dict())[0]})
        checks.append({"name": "ba_finite", "ok": fa2 and fb2})
        checks.append({"name": "cross_model", "ok": strict(a.state_dict(), a2.state_dict())[0] and strict(b.state_dict(), b2.state_dict())[0]})
        checks.append({"name": "cross_opt", "ok": strict(oa.state_dict(), oa2.state_dict())[0] and strict(ob.state_dict(), ob2.state_dict())[0]})

        # independent RNG field negatives
        base = snap()
        torch.rand(1)
        checks.append({"name": "neg_torch_only", "ok": rng_equal(base, snap())[1] == "torch"})
        apply_rng(base)
        random.random()
        checks.append({"name": "neg_python_only", "ok": rng_equal(base, snap())[1] == "python"})
        apply_rng(base)
        np.random.rand()
        checks.append({"name": "neg_numpy_only", "ok": rng_equal(base, snap())[1] == "numpy[1]" or rng_equal(base, snap())[1] == "numpy[2]"})

        def pollute():
            torch.manual_seed(99); random.seed(99); np.random.seed(99)
        def resume_partial(skip):
            pollute()
            raw = torch.load(path, map_location="cpu", weights_only=False)
            m = Parcae(cfg())
            m.load_state_dict(raw["model"])
            o = MuonAdamW(get_muon_param_groups(m.named_parameters()))
            o.load_state_dict(raw["opt"])
            s = raw["rng"]
            if "torch" not in skip:
                torch.set_rng_state(s["torch"])
            if "python" not in skip:
                random.setstate(s["python"])
            if "numpy" not in skip:
                np.random.set_state(s["numpy"])
            return m, o, raw
        pollute()
        _, _, raw_good = resume(path)
        checks.append({"name": "good_rng", "ok": rng_equal(snap(), raw_good["rng"])[0]})
        for label, skip, field in (("bad_torch", {"torch"}, "torch"), ("bad_python", {"python"}, "python"), ("bad_numpy", {"numpy"}, "numpy")):
            _, _, raw_bad = resume_partial(skip)
            ok, got = rng_equal(snap(), raw_bad["rng"])
            checks.append({"name": label, "ok": (not ok) and (got == field or (field == "numpy" and str(got).startswith("numpy"))), "field": got})

        # AB/BA storage isolation already recorded; add optimizer overlap on AB
        checks.append({"name": "ab_opt_isolated", "ok": not overlaps(storage_ranges(oa.state_dict()), storage_ranges(ob.state_dict()))})

    failed = [c["name"] for c in checks if not c["ok"]]
    status = "CPU FILE-RESUME BIT-EXACT PASS" if not failed else "FAIL"
    print(json.dumps({"status": status, "env": env, "checks": checks, "failed": failed, "gate": "NOT PASS"}, indent=2))
    return 0 if not failed else 1


def sysconfig_include():
    import sysconfig
    return sysconfig.get_path("include")


if __name__ == "__main__":
    raise SystemExit(main())
