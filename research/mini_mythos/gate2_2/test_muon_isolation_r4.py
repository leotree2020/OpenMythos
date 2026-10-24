"""S2-4R4 storage isolation diagnostic. CPU only. Not Gate 2.2-C PASS."""
import copy
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


def storages(opt):
    out = []
    for i, st in opt.state.items():
        for k, v in st.items():
            if torch.is_tensor(v):
                out.append((k, v.data_ptr(), tuple(v.shape), str(v.dtype)))
    return out


def shared(a, b):
    sa = {p for _, p, _, _ in storages(a)}
    sb = {p for _, p, _, _ in storages(b)}
    return sorted(sa & sb)


def first_step(seed=7):
    torch.manual_seed(seed)
    m = Parcae(cfg())
    opt = MuonAdamW(get_muon_param_groups(m.named_parameters()))
    x = torch.randint(0, 128, (1, 4))
    opt.zero_grad(set_to_none=True)
    y = m(x, labels=x, return_logits=False, num_steps_pair=(torch.tensor(1), torch.tensor(1)))
    y["loss"].backward()
    opt.step()
    return m, opt


def restore_from_file(model_sd, opt_sd):
    m = Parcae(cfg())
    m.load_state_dict(model_sd)
    opt = MuonAdamW(get_muon_param_groups(m.named_parameters()))
    opt.load_state_dict(opt_sd)
    return m, opt


def main():
    report = {"checks": []}
    a, oa = first_step()
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        path = td / "ckpt.pt"
        torch.save({"model": a.state_dict(), "opt": oa.state_dict()}, path)
        raw = torch.load(path, map_location="cpu", weights_only=False)
    b, ob = restore_from_file(raw["model"], raw["opt"])
    share = shared(oa, ob)
    report["checks"].append({"name": "shared_storage_after_file_restore", "shared_ptrs": share, "ok": len(share) == 0})

    # deepcopy control
    b2 = Parcae(cfg())
    b2.load_state_dict(copy.deepcopy(a.state_dict()))
    ob2 = MuonAdamW(get_muon_param_groups(b2.named_parameters()))
    ob2.load_state_dict(copy.deepcopy(oa.state_dict()))
    share2 = shared(oa, ob2)
    report["checks"].append({"name": "shared_storage_after_deepcopy", "shared_ptrs": share2, "ok": len(share2) == 0})

    # A.step should not move B if isolated
    before_b = {n: p.detach().clone() for n, p in b.named_parameters()}
    before_ob = copy.deepcopy(ob.state_dict())
    x = torch.randint(0, 128, (1, 4))
    oa.zero_grad(set_to_none=True)
    ya = a(x, labels=x, return_logits=False, num_steps_pair=(torch.tensor(1), torch.tensor(1)))
    ya["loss"].backward()
    oa.step()
    moved = any(not torch.equal(before_b[n], p.detach()) for n, p in b.named_parameters())
    report["checks"].append({"name": "a_step_moves_b_params", "moved": moved})
    def sd_moved(a, b):
        if isinstance(a, dict) and isinstance(b, dict):
            return a.keys() != b.keys() or any(sd_moved(a[k], b[k]) for k in a)
        if torch.is_tensor(a) and torch.is_tensor(b):
            return not torch.equal(a, b)
        return a != b
    report["checks"].append({"name": "a_step_moves_b_opt", "moved": sd_moved(ob.state_dict(), before_ob)})

    # fresh independent pair for AB vs BA
    def pair():
        m, o = first_step()
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "c.pt"
            torch.save({"model": m.state_dict(), "opt": o.state_dict()}, p)
            raw = torch.load(p, map_location="cpu", weights_only=False)
        n, on = restore_from_file(raw["model"], raw["opt"])
        return m, o, n, on

    def one_step(m, o, seed):
        torch.manual_seed(seed)
        x = torch.randint(0, 128, (1, 4))
        o.zero_grad(set_to_none=True)
        y = m(x, labels=x, return_logits=False, num_steps_pair=(torch.tensor(1), torch.tensor(1)))
        y["loss"].backward()
        o.step()
        return {n: p.detach().clone() for n, p in m.named_parameters()}

    a1, oa1, b1, ob1 = pair()
    ra = one_step(a1, oa1, 11)
    rb = one_step(b1, ob1, 11)
    a2, oa2, b2m, ob2m = pair()
    rb2 = one_step(b2m, ob2m, 11)
    ra2 = one_step(a2, oa2, 11)
    ab_ba = all(torch.equal(ra[n], rb2[n]) and torch.equal(rb[n], ra2[n]) for n in ra)
    report["checks"].append({"name": "ab_vs_ba_order", "consistent": ab_ba})

    isolated = len(share) == 0 and not moved
    report["classification"] = "TEST HARNESS ISSUE" if not isolated else ("ORDER EFFECT" if not ab_ba else "ISOLATED; prior diff not explained by shared storage")
    report["status"] = report["classification"]
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
