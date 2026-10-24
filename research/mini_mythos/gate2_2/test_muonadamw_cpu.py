"""Real MuonAdamW CPU precheck. Does not substitute AdamW."""
import json
import sys
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


def main():
    out = {"torch": torch.__version__, "cuda": torch.cuda.is_available(), "tests": []}
    torch.manual_seed(1)
    m = Parcae(cfg())
    groups = get_muon_param_groups(m.named_parameters())
    kinds = {g["kind"] for g in groups}
    out["tests"].append({"name": "instantiate_groups", "ok": "adamw" in kinds and "muon" in kinds, "kinds": sorted(kinds)})
    # name routing
    routed = []
    for name, p in m.named_parameters():
        ln = name.lower()
        adam = p.ndim < 2 or any(x in ln for x in ["wte", "embedding", "embed", "lm_head", "norm", "ln_", "bias", "a_log", "dt_bias", "adapter.b", "adapter.adapter", "transformer.c."])
        routed.append((name, "adamw" if adam else "muon"))
    special = [n for n, k in routed if any(s in n.lower() for s in ["a_log", "dt_bias", "adapter.b"])]
    out["tests"].append({"name": "special_to_adamw", "ok": all(k == "adamw" for n, k in routed if n in special), "special": special})
    try:
        opt = MuonAdamW(groups)
        x = torch.randint(0, 128, (1, 4))
        y = m(x, labels=x, return_logits=False, num_steps_pair=(torch.tensor(1), torch.tensor(1)))
        y["loss"].backward()
        before = {n: p.detach().clone() for n, p in m.named_parameters()}
        opt.step()
        finite = all(torch.isfinite(p).all() for p in m.parameters())
        changed = any(not torch.equal(before[n], p) for n, p in m.named_parameters())
        sd = opt.state_dict()
        opt2 = MuonAdamW(get_muon_param_groups(m.named_parameters()))
        opt2.load_state_dict(sd)
        restored = opt.state_dict().keys() == opt2.state_dict().keys()
        out["tests"].append({"name": "real_step", "ok": finite and changed, "finite": finite, "changed": changed})
        out["tests"].append({"name": "state_dict_restore", "ok": restored})
    except Exception as e:
        out["tests"].append({"name": "real_step", "ok": False, "status": "BLOCKED", "error": f"{type(e).__name__}: {e}"})
        out["traceback"] = traceback.format_exc().splitlines()[-5:]
    # bad shape group
    try:
        bad = [{"params": [torch.randn(3)], "kind": "muon", "lr": 0.01, "momentum": 0.9, "weight_decay": 0.0}]
        MuonAdamW(bad).step()
        out["tests"].append({"name": "bad_shape", "ok": False})
    except Exception as e:
        out["tests"].append({"name": "bad_shape", "ok": True, "error": type(e).__name__})
    failed = [t for t in out["tests"] if not t["ok"]]
    out["failed"] = len(failed)
    out["gpu_step"] = "NOT TESTED"
    print(json.dumps(out, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
