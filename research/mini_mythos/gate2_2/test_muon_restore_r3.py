"""S2-4R3 controlled restore equivalence. CPU only. Not Gate 2.2-C PASS."""
import json
import random

import numpy as np
import torch
from parcae_lm.models.parcae.parcae import Parcae, ParcaeConfig
from recpre.optim.muon_adamw import MuonAdamW, get_muon_param_groups

TOL = 1e-5  # local report tolerance only; frozen comparator is not changed


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


def max_diff(a, b):
    if torch.is_tensor(a) and torch.is_tensor(b) and a.shape == b.shape:
        return (a.detach().float() - b.detach().float()).abs().max().item()
    if isinstance(a, dict) and isinstance(b, dict) and a.keys() == b.keys():
        vals = [max_diff(a[k], b[k]) for k in a]
        return max(vals) if vals else 0.0
    return 0.0 if a == b else 1.0


def first_mismatch(named_a, named_b):
    for n in named_a:
        if n not in named_b:
            return n
        if not torch.equal(named_a[n].detach(), named_b[n].detach()):
            return n
    return None


def main():
    report = {"env_risk": "Python 3.11.2 headers with Python 3.10 pyconfig.h. Not RunPod 2.8.0+cu128.", "checks": []}
    torch.manual_seed(7)
    np.random.seed(7)
    random.seed(7)
    a = Parcae(cfg())
    oa = MuonAdamW(get_muon_param_groups(a.named_parameters()))
    x1 = torch.randint(0, 128, (1, 4))
    oa.zero_grad(set_to_none=True)
    y = a(x1, labels=x1, return_logits=False, num_steps_pair=(torch.tensor(1), torch.tensor(1)))
    y["loss"].backward()
    oa.step()

    b = Parcae(cfg())
    b.load_state_dict({k: v.detach().clone() for k, v in a.state_dict().items()})
    ob = MuonAdamW(get_muon_param_groups(b.named_parameters()))
    ob.load_state_dict(oa.state_dict())

    # restore-point checks
    model_diff = max_diff(a.state_dict(), b.state_dict())
    opt_diff = max_diff(oa.state_dict(), ob.state_dict())
    same_mode = a.training == b.training
    report["checks"].append({"name": "restore_model", "max_abs": model_diff, "ok": model_diff == 0.0})
    report["checks"].append({"name": "restore_optimizer", "max_abs": opt_diff, "ok": opt_diff == 0.0})
    report["checks"].append({"name": "same_mode", "ok": same_mode})
    if model_diff != 0.0 or opt_diff != 0.0 or not same_mode:
        report["status"] = "BLOCKED"
        report["reason"] = "restore start differs"
        print(json.dumps(report, indent=2))
        return 2

    torch.manual_seed(9)
    np.random.seed(9)
    random.seed(9)
    x2 = torch.randint(0, 128, (1, 4))
    torch.manual_seed(9)
    np.random.seed(9)
    random.seed(9)
    x2b = torch.randint(0, 128, (1, 4))
    report["checks"].append({"name": "same_input", "ok": torch.equal(x2, x2b)})

    oa.zero_grad(set_to_none=True)
    ob.zero_grad(set_to_none=True)
    empty_a = all(p.grad is None for p in a.parameters())
    empty_b = all(p.grad is None for p in b.parameters())
    report["checks"].append({"name": "grad_empty_before_backward", "ok": empty_a and empty_b})

    rng_a = torch.get_rng_state().clone()
    ya = a(x2, labels=x2, return_logits=False, num_steps_pair=(torch.tensor(1), torch.tensor(1)))
    ya["loss"].backward()
    torch.set_rng_state(rng_a)
    yb = b(x2b, labels=x2b, return_logits=False, num_steps_pair=(torch.tensor(1), torch.tensor(1)))
    yb["loss"].backward()

    ga = {n: p.grad for n, p in a.named_parameters() if p.grad is not None}
    gb = {n: p.grad for n, p in b.named_parameters() if p.grad is not None}
    g_mismatch = first_mismatch(ga, gb)
    g_max = max((max_diff(ga[n], gb[n]) for n in ga if n in gb), default=0.0)
    report["checks"].append({"name": "grad_before_step", "bit_exact": g_mismatch is None, "max_abs": g_max, "first": g_mismatch})
    if g_mismatch is not None:
        report["status"] = "BLOCKED"
        report["reason"] = "gradients differ before step; not attributed to optimizer"
        print(json.dumps(report, indent=2))
        return 2

    oa.step()
    ob.step()
    pa = dict(a.named_parameters())
    pb = dict(b.named_parameters())
    mismatch = first_mismatch(pa, pb)
    p_max = max(max_diff(pa[n], pb[n]) for n in pa)
    groups = get_muon_param_groups(a.named_parameters())
    kind = {}
    for g in groups:
        for n, p in a.named_parameters():
            if any(p is q for q in g["params"]):
                kind[n] = g["kind"]
    muon_max = max((max_diff(pa[n], pb[n]) for n, k in kind.items() if k == "muon"), default=0.0)
    adam_max = max((max_diff(pa[n], pb[n]) for n, k in kind.items() if k == "adamw"), default=0.0)
    bit = mismatch is None
    numerical = (not bit) and p_max <= TOL
    status = "BIT-EXACT PASS" if bit else ("NUMERICAL PASS" if numerical else "FAIL")
    report["checks"].append({
        "name": "after_step",
        "status": status,
        "max_abs": p_max,
        "muon_max": muon_max,
        "adamw_max": adam_max,
        "first": mismatch,
        "local_tol": TOL,
        "frozen_comparator_unchanged": True,
    })
    report["status"] = status
    print(json.dumps(report, indent=2))
    return 0 if status in ("BIT-EXACT PASS", "NUMERICAL PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
