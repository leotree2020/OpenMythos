"""S2-4R5 locate A/B step divergence. CPU only. Not Gate 2.2-C PASS."""
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


def max_abs(a, b):
    if torch.is_tensor(a) and torch.is_tensor(b) and a.shape == b.shape:
        return (a.detach().float() - b.detach().float()).abs().max().item()
    return 0.0


def first_name(na, nb):
    for n in na:
        if not torch.equal(na[n].detach(), nb[n].detach()):
            return n
    return None


def base():
    torch.manual_seed(7)
    m = Parcae(cfg())
    o = MuonAdamW(get_muon_param_groups(m.named_parameters()))
    x = torch.randint(0, 128, (1, 4))
    o.zero_grad(set_to_none=True)
    y = m(x, labels=x, return_logits=False, num_steps_pair=(torch.tensor(1), torch.tensor(1)))
    y["loss"].backward()
    o.step()
    return m, o


def clone_sd(sd):
    if torch.is_tensor(sd):
        return sd.detach().clone()
    if isinstance(sd, dict):
        return {k: clone_sd(v) for k, v in sd.items()}
    if isinstance(sd, list):
        return [clone_sd(v) for v in sd]
    return sd

def load_pair(blob):
    a = Parcae(cfg())
    a.load_state_dict(clone_sd(blob["model"]))
    oa = MuonAdamW(get_muon_param_groups(a.named_parameters()))
    oa.load_state_dict(clone_sd(blob["opt"]))
    b = Parcae(cfg())
    b.load_state_dict(clone_sd(blob["model"]))
    ob = MuonAdamW(get_muon_param_groups(b.named_parameters()))
    ob.load_state_dict(clone_sd(blob["opt"]))
    return a, oa, b, ob


def shared(oa, ob):
    sa = {v.data_ptr() for st in oa.state.values() for v in st.values() if torch.is_tensor(v)}
    sb = {v.data_ptr() for st in ob.state.values() for v in st.values() if torch.is_tensor(v)}
    return bool(sa & sb)


def step_pair(a, oa, b, ob, seed, order):
    def one(m, o):
        torch.manual_seed(seed)
        x = torch.randint(0, 128, (1, 4))
        o.zero_grad(set_to_none=True)
        y = m(x, labels=x, return_logits=False, num_steps_pair=(torch.tensor(1), torch.tensor(1)))
        y["loss"].backward()
        return x, {n: p.grad.detach().clone() for n, p in m.named_parameters() if p.grad is not None}
    if order == "AB":
        xa, ga = one(a, oa)
        xb, gb = one(b, ob)
        oa.step(); ob.step()
    else:
        xb, gb = one(b, ob)
        xa, ga = one(a, oa)
        ob.step(); oa.step()
    return xa, xb, ga, gb


def kind_max(a, b, groups_a):
    kind = {}
    for g in groups_a:
        for n, p in a.named_parameters():
            if any(p is q for q in g["params"]):
                kind[n] = g["kind"]
    pa, pb = dict(a.named_parameters()), dict(b.named_parameters())
    muon = max((max_abs(pa[n], pb[n]) for n, k in kind.items() if k == "muon"), default=0.0)
    adam = max((max_abs(pa[n], pb[n]) for n, k in kind.items() if k == "adamw"), default=0.0)
    return muon, adam


def main():
    report = {"checks": [], "env_risk": "3.11.2 headers + 3.10 pyconfig.h; not RunPod 2.8"}
    m, o = base()
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "c.pt"
        torch.save({"model": m.state_dict(), "opt": o.state_dict()}, p)
        blob = torch.load(p, map_location="cpu", weights_only=False)

    a, oa, b, ob = load_pair(blob)
    pre = max(max_abs(x, y) for x, y in zip(a.state_dict().values(), b.state_dict().values()) if torch.is_tensor(x))
    report["checks"].append({"name": "pre_model", "max_abs": pre, "ok": pre == 0.0})
    report["checks"].append({"name": "no_shared_storage", "ok": not shared(oa, ob)})

    xa, xb, ga, gb = step_pair(a, oa, b, ob, 11, "AB")
    gmax = max(max_abs(ga[n], gb[n]) for n in ga)
    report["checks"].append({"name": "grad_ab", "max_abs": gmax, "ok": gmax == 0.0 and torch.equal(xa, xb)})
    pmax = max(max_abs(x, y) for x, y in zip(a.parameters(), b.parameters()))
    muon, adam = kind_max(a, b, get_muon_param_groups(a.named_parameters()))
    first = first_name(dict(a.named_parameters()), dict(b.named_parameters()))
    report["checks"].append({"name": "after_ab", "max_abs": pmax, "muon": muon, "adamw": adam, "first": first, "ok": pmax == 0.0})

    a2, oa2, b2, ob2 = load_pair(blob)
    step_pair(a2, oa2, b2, ob2, 11, "BA")
    pmax2 = max(max_abs(x, y) for x, y in zip(a2.parameters(), b2.parameters()))
    report["checks"].append({"name": "after_ba", "max_abs": pmax2, "ok": pmax2 == 0.0})

    failed = [c for c in report["checks"] if not c["ok"]]
    report["status"] = "FAIL" if failed else "BIT-EXACT PASS"
    report["failed"] = [c["name"] for c in failed]
    print(json.dumps(report, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
