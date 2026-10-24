"""
Gate 2.2-A.2 CPU probe with native step semantics.

Native train_step:
    state["microbatch_step"] += 1
    model.step = state["microbatch_step"]

Groups:
  A   continuous
  B   full restore including microbatch_step
  C1  omit model.step restore, keep correct microbatch_step
      (native logic resets model.step before forward)
  C2  wrong microbatch_step
  D   extra data skip, same update count

AdamW here is a model-level probe only. NOT MuonAdamW verification.
Official scripts/train.py remains BLOCKED on CPU.
"""

import hashlib
import json
import sys
from pathlib import Path

import torch
from parcae_lm.models.parcae.parcae import Parcae, ParcaeConfig

TOL_ABS = 1e-5
STEPS = 6
RESUME_AT = 3
SEED = 42


def make_config():
    return ParcaeConfig(
        n_embd=32, intermediate_size=64, num_attention_heads=2, num_key_value_heads=2,
        vocab_size=128, padded_vocab_size=128, block_size=8,
        n_layers_in_prelude=1, n_layers_in_recurrent_block=1, n_layers_in_coda=1,
        mean_recurrence=2, mean_backprop_depth=1, recurrent_embedding_dimension=32,
        recurrent_intermediation_embedding_dimension=64, prelude_norm=True,
        injection_type="diagonal", state_init="normal", tie_embeddings=True,
        use_fused_head="pytorch", sampling_scheme="poisson-unbounded",
    )


def bhash(t):
    return hashlib.sha256(t.detach().contiguous().view(torch.uint8).cpu().numpy().tobytes()).hexdigest()


def make_data():
    g = torch.Generator().manual_seed(SEED)
    return torch.randint(0, 128, (40, 4), generator=g)


def fresh():
    torch.manual_seed(SEED)
    return Parcae(make_config())


def native_step(model, opt, sched, x, microbatch_step):
    """Mirror train_step: increment already applied by caller; set model.step then forward."""
    model.step = microbatch_step
    out = model(x, labels=x, return_logits=False)
    loss = float(out["loss"].detach())
    out["loss"].backward()
    opt.step()
    opt.zero_grad()
    sched.step()
    return loss, int(model.step)


def snap(model, opt, sched, mb, data_idx):
    import copy
    return {
        "model": {k: v.detach().cpu().clone() for k, v in model.state_dict().items()},
        "opt": copy.deepcopy(opt.state_dict()),
        "sched": sched.state_dict(),
        "microbatch_step": mb,
        "data_idx": data_idx,
        "torch_rng": torch.get_rng_state().clone(),
    }


def restore(s, wrong_mb=None, restore_model_step=True):
    m = fresh()
    m.load_state_dict(s["model"])
    opt = torch.optim.AdamW(m.parameters(), lr=1e-3)
    opt.load_state_dict(s["opt"])
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda st: 1.0)
    sched.load_state_dict(s["sched"])
    torch.set_rng_state(s["torch_rng"])
    if restore_model_step:
        m.step = s["microbatch_step"]
    else:
        m.step = 0
    mb = s["microbatch_step"] if wrong_mb is None else wrong_mb
    return m, opt, sched, mb, s["data_idx"]


def run(mode):
    model = fresh()
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3)
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda st: 1.0)
    data = make_data()
    hashes, losses, steps_used = [], [], []
    mb = 0
    data_idx = 0
    if mode in ("B", "C1", "C2", "D"):
        for _ in range(RESUME_AT):
            mb += 1
            hashes.append(bhash(data[data_idx:data_idx + 1]))
            loss, st = native_step(model, opt, sched, data[data_idx:data_idx + 1], mb)
            losses.append(loss)
            steps_used.append(st)
            data_idx += 1
        s = snap(model, opt, sched, mb, data_idx)
        if mode == "C1":
            model, opt, sched, mb, data_idx = restore(s, restore_model_step=False)
        elif mode == "C2":
            model, opt, sched, mb, data_idx = restore(s, wrong_mb=0, restore_model_step=False)
        else:
            model, opt, sched, mb, data_idx = restore(s)
        if mode == "D":
            data_idx += 1  # extra skip; update count still STEPS
    while len(losses) < STEPS:
        mb += 1
        hashes.append(bhash(data[data_idx:data_idx + 1]))
        loss, st = native_step(model, opt, sched, data[data_idx:data_idx + 1], mb)
        losses.append(loss)
        steps_used.append(st)
        data_idx += 1
    final = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
    opt_view = {}
    for i, stt in enumerate(opt.state.values()):
        for k, v in stt.items():
            if torch.is_tensor(v):
                opt_view[f"{i}.{k}"] = v.detach().cpu().clone()
    return {
        "hashes": hashes, "losses": losses, "steps_used": steps_used,
        "final": final, "opt": opt_view, "sched": sched.state_dict(),
        "updates": len(losses), "final_mb": mb,
    }


def diffs(a, b):
    abs_d, rel_d, n = 0.0, 0.0, 0
    for k in a:
        if k not in b:
            n += 1
            continue
        d = (a[k].float() - b[k].float()).abs()
        m = d.max().item()
        denom = b[k].float().abs().clamp(min=1e-8)
        r = (d / denom).max().item()
        if m > TOL_ABS:
            n += 1
        abs_d = max(abs_d, m)
        rel_d = max(rel_d, r)
    return abs_d, rel_d, n


def main():
    A = run("A")
    B = run("B")
    C1 = run("C1")
    C2 = run("C2")
    D = run("D")

    def pack(X, name):
        wa, wr, wn = diffs(A["final"], X["final"])
        oa, orr, on = diffs(A["opt"], X["opt"])
        return {
            "hashes": X["hashes"], "losses": X["losses"], "steps_used": X["steps_used"],
            "updates": X["updates"], "final_mb": X["final_mb"],
            "weight_max_abs": wa, "weight_max_rel": wr, "weight_n_diff": wn,
            "opt_max_abs": oa, "opt_n_diff": on,
            "sched_eq": X["sched"] == A["sched"],
            "hash_eq_A": X["hashes"] == A["hashes"],
            "loss_max_abs": max(abs(a - b) for a, b in zip(A["losses"], X["losses"])) if len(X["losses"]) == len(A["losses"]) else None,
        }

    results = {
        "tolerance_abs": TOL_ABS,
        "cuda_rng": "NOT APPLICABLE",
        "muonadamw": "NOT TESTED",
        "official_train_py": "BLOCKED",
        "A": {"hashes": A["hashes"], "losses": A["losses"], "steps_used": A["steps_used"], "updates": A["updates"]},
        "B": pack(B, "B"),
        "C1": pack(C1, "C1"),
        "C2": pack(C2, "C2"),
        "D": pack(D, "D"),
    }
    results["D"]["hash_D_differs_from_A"] = D["hashes"] != A["hashes"]
    results["D"]["updates_eq_A"] = D["updates"] == A["updates"]

    # expectations
    status = {
        "A": "PASS",
        "B": "PASS" if (results["B"]["hash_eq_A"] and results["B"]["weight_n_diff"] == 0) else "FAIL",
        "C1": "PASS" if (results["C1"]["hash_eq_A"] and results["C1"]["weight_n_diff"] == 0) else "FAIL",
        "C2": "PASS" if results["C2"]["weight_n_diff"] > 0 else "FAIL",
        "D": "PASS" if (results["D"]["hash_D_differs_from_A"] and results["D"]["updates_eq_A"]) else "FAIL",
    }
    results["status"] = status
    results["interpretation"] = {
        "C1": "Omitting model.step alone is not a defect if microbatch_step is restored; native logic resets model.step before forward.",
        "C2": "Wrong microbatch_step changes recurrence seed and weights.",
    }
    out = Path(__file__).resolve().parent / "CPU_PROBE_RESULTS.json"
    out.write_text(json.dumps(results, indent=2))
    print(json.dumps({"status": status, "B_n": results["B"]["weight_n_diff"], "C1_n": results["C1"]["weight_n_diff"], "C2_n": results["C2"]["weight_n_diff"], "D_differs": results["D"]["hash_D_differs_from_A"], "D_updates": results["D"]["updates"]}, indent=2))
    return 0 if all(v == "PASS" for v in status.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
