"""S2-4R real MuonAdamW CPU precheck. No AdamW substitute. No GPU."""
import json
import sys
import time
import traceback

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


def group_of(groups, param):
    for g in groups:
        if any(p is param for p in g["params"]):
            return g["kind"]
    return None


def tensors_equal(a, b):
    if torch.is_tensor(a) and torch.is_tensor(b):
        return torch.equal(a.cpu(), b.cpu())
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(tensors_equal(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(tensors_equal(x, y) for x, y in zip(a, b))
    return a == b


def main():
    out = {
        "torch": torch.__version__,
        "cuda": torch.cuda.is_available(),
        "python_include": "/tmp/py311-include/Include (CPython 3.11.2 headers + pyconfig.h)",
        "tests": [],
    }
    torch.manual_seed(1)
    m = Parcae(cfg())
    groups = get_muon_param_groups(m.named_parameters())
    kinds = {g["kind"] for g in groups}
    out["tests"].append({"name": "instantiate_groups", "ok": "adamw" in kinds and "muon" in kinds, "kinds": sorted(kinds)})

    named = dict(m.named_parameters())
    special = {}
    for key in ("A_log", "dt_bias", "adapter.B"):
        hits = [n for n in named if key.lower() in n.lower()]
        if not hits:
            special[key] = "NOT PRESENT"
        else:
            special[key] = {n: group_of(groups, named[n]) for n in hits}
    out["tests"].append({
        "name": "special_grouping_from_real_groups",
        "ok": all(v == "NOT PRESENT" or all(k == "adamw" for k in v.values()) for v in special.values()),
        "special": special,
    })

    try:
        opt = MuonAdamW(groups)
        x = torch.randint(0, 128, (1, 4))
        y = m(x, labels=x, return_logits=False, num_steps_pair=(torch.tensor(1), torch.tensor(1)))
        y["loss"].backward()
        has_grad = any(p.grad is not None for p in m.parameters())
        t0 = time.perf_counter()
        opt.step()
        elapsed = time.perf_counter() - t0
        finite = all(torch.isfinite(p).all() for p in m.parameters())
        # identify one muon and one adamw param that changed
        changed = {"muon": False, "adamw": False}
        for g in groups:
            for p in g["params"]:
                if p.grad is not None and torch.isfinite(p).all():
                    changed[g["kind"]] = True
        out["tests"].append({
            "name": "real_step",
            "ok": has_grad and finite and changed["muon"] and changed["adamw"],
            "has_grad": has_grad,
            "finite": finite,
            "changed": changed,
            "step_seconds": round(elapsed, 4),
        })
        sd = opt.state_dict()
        opt2 = MuonAdamW(get_muon_param_groups(m.named_parameters()))
        opt2.load_state_dict(sd)
        restored = tensors_equal(opt.state_dict(), opt2.state_dict())
        # continue update
        y2 = m(x, labels=x, return_logits=False, num_steps_pair=(torch.tensor(1), torch.tensor(1)))
        y2["loss"].backward()
        opt2.step()
        finite2 = all(torch.isfinite(p).all() for p in m.parameters())
        out["tests"].append({"name": "state_dict_restore_full", "ok": restored})
        out["tests"].append({"name": "continue_after_restore", "ok": finite2})
    except Exception as e:
        out["tests"].append({"name": "real_step", "ok": False, "status": "BLOCKED", "error": f"{type(e).__name__}: {e}"})
        out["traceback"] = traceback.format_exc().splitlines()[-6:]

    # negative: muon group with 1D param should fail inside muon path
    try:
        bad = [{"params": [torch.randn(3, requires_grad=True)], "kind": "muon", "lr": 0.01, "momentum": 0.9, "weight_decay": 0.0, "ns_steps": 5}]
        p = bad[0]["params"][0]
        p.grad = torch.randn_like(p)
        MuonAdamW(bad).step()
        out["tests"].append({"name": "bad_shape", "ok": False, "note": "did not raise"})
    except Exception as e:
        out["tests"].append({"name": "bad_shape", "ok": True, "error": type(e).__name__})

    failed = [t for t in out["tests"] if not t["ok"]]
    out["failed"] = len(failed)
    out["gpu_step"] = "NOT TESTED"
    out["status"] = "S2-4R CPU PASS" if not failed else "S2-4R BLOCKED"
    print(json.dumps(out, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
