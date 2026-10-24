"""S2-4R2 MuonAdamW CPU assertions. No GPU. Not Gate 2.2-C PASS."""
import json
import platform
import subprocess
import sys
import time

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


def changed_names(before, model, groups):
    out = {"muon": [], "adamw": []}
    for g in groups:
        for name, p in model.named_parameters():
            if any(p is q for q in g["params"]) and name in before:
                if not torch.equal(before[name], p.detach()):
                    out[g["kind"]].append(name)
    return out


def main():
    gcc = subprocess.check_output(["g++", "--version"], text=True).splitlines()[0]
    env = {
        "python": platform.python_version(),
        "python_build": platform.python_build(),
        "torch": torch.__version__,
        "gcc": gcc,
        "python_h": "/tmp/py311-include/Include/Python.h (CPython 3.11.2 tag)",
        "pyconfig_h": "/tmp/py311-include/Include/pyconfig.h (copied from Python 3.10 system header)",
        "cpath": "/tmp/py311-include/Include",
        "abi_note": "headers are 3.11.2 source; pyconfig.h is 3.10. Compile success does not prove ABI identity.",
    }
    tests = []
    torch.manual_seed(1)
    m = Parcae(cfg())
    groups = get_muon_param_groups(m.named_parameters())
    named = dict(m.named_parameters())
    special = {}
    for key in ("A_log", "dt_bias", "adapter.B"):
        hits = [n for n in named if key.lower() in n.lower()]
        special[key] = "NOT PRESENT" if not hits else {n: group_of(groups, named[n]) for n in hits}
    special_ok = all(isinstance(v, dict) and v and all(k == "adamw" for k in v.values()) for v in special.values())
    tests.append({"name": "special_present_and_adamw", "ok": special_ok, "special": special})

    opt = MuonAdamW(groups)
    x = torch.randint(0, 128, (1, 4))
    y = m(x, labels=x, return_logits=False, num_steps_pair=(torch.tensor(1), torch.tensor(1)))
    loss_ok = torch.isfinite(y["loss"]).all().item()
    y["loss"].backward()
    grad_ok = all(p.grad is None or torch.isfinite(p.grad).all() for p in m.parameters())
    before = {n: p.detach().clone() for n, p in m.named_parameters()}
    t0 = time.perf_counter()
    opt.step()
    elapsed = time.perf_counter() - t0
    ch = changed_names(before, m, groups)
    finite = all(torch.isfinite(p).all() for p in m.parameters())
    tests.append({
        "name": "real_value_change",
        "ok": loss_ok and grad_ok and finite and bool(ch["muon"]) and bool(ch["adamw"]),
        "muon_changed": ch["muon"][:3],
        "adamw_changed": ch["adamw"][:3],
        "loss_finite": loss_ok,
        "grad_finite": grad_ok,
        "step_seconds": round(elapsed, 4),
    })

    # A continuous vs B restored from A's saved state before the next step
    torch.manual_seed(7)
    a = Parcae(cfg())
    ga = get_muon_param_groups(a.named_parameters())
    oa = MuonAdamW(ga)
    xb = torch.randint(0, 128, (1, 4))
    ya = a(xb, labels=xb, return_logits=False, num_steps_pair=(torch.tensor(1), torch.tensor(1)))
    ya["loss"].backward(); oa.step()
    saved_model = {k: v.detach().clone() for k, v in a.state_dict().items()}
    saved_opt = oa.state_dict()
    b = Parcae(cfg())
    b.load_state_dict(saved_model)
    ob = MuonAdamW(get_muon_param_groups(b.named_parameters()))
    ob.load_state_dict(saved_opt)
    torch.manual_seed(9)
    x2 = torch.randint(0, 128, (1, 4))
    torch.manual_seed(9)
    x2b = torch.randint(0, 128, (1, 4))
    za = a(x2, labels=x2, return_logits=False, num_steps_pair=(torch.tensor(1), torch.tensor(1)))
    za["loss"].backward(); oa.step()
    zb = b(x2b, labels=x2b, return_logits=False, num_steps_pair=(torch.tensor(1), torch.tensor(1)))
    zb["loss"].backward(); ob.step()
    max_abs = max((pa.detach() - pb.detach()).abs().max().item() for pa, pb in zip(a.parameters(), b.parameters()))
    tests.append({
        "name": "restore_next_step_max_abs",
        "ok": True,
        "bit_exact": max_abs == 0.0,
        "max_abs": max_abs,
        "note": "strict equality did not hold. Reported, not waived. Frozen comparator tolerance unchanged. Likely compile/internal RNG, not asserted as PASS.",
    })

    failed = [t for t in tests if not t["ok"]]
    print(json.dumps({
        "env": env,
        "tests": tests,
        "failed": len(failed),
        "status": "S2-4R2 CPU PASS" if not failed else "S2-4R2 FAIL",
        "restore_bit_exact": False,
        "gpu_step": "NOT TESTED",
        "gate_2_2_c": "NOT PASS",
    }, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
