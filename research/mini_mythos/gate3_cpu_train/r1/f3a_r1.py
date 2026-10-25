"""F3-A-R1 resume state probe.

PENDING CHATGPT REVIEW. Does not modify Parcae.
AdamW only. MuonAdamW and train.py are NOT TESTED.
"""
import argparse
import copy
import hashlib
import json
import random
import sys
from pathlib import Path

import numpy as np
import torch

SEED = 42


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def checksum(t):
    return sha_bytes(t.detach().cpu().contiguous().numpy().tobytes())


def weight_sha(state):
    h = hashlib.sha256()
    for name in sorted(state):
        t = state[name].detach().cpu().contiguous()
        h.update(name.encode())
        h.update(str(tuple(t.shape)).encode())
        h.update(str(t.dtype).encode())
        h.update(t.numpy().tobytes())
    return h.hexdigest()


def state_sha(obj):
    raw = json.dumps(obj, default=lambda x: checksum(x) if torch.is_tensor(x) else str(x), sort_keys=True)
    return sha_bytes(raw.encode())


def make_model(root):
    sys.path.insert(0, str(root))
    from parcae_lm.models.parcae.config import ParcaeConfig
    from parcae_lm.models.parcae.parcae import Parcae

    torch.manual_seed(SEED)
    from parcae_lm.models.parcae.config import ParcaeConfig
    cfg = ParcaeConfig(
        n_embd=64, intermediate_size=128, num_attention_heads=4, num_key_value_heads=4,
        vocab_size=128, padded_vocab_size=128, block_size=32,
        n_layers_in_prelude=2, n_layers_in_recurrent_block=2, n_layers_in_coda=2,
        mean_recurrence=2, mean_backprop_depth=2,
        recurrent_embedding_dimension=64, recurrent_intermediation_embedding_dimension=128,
        attn_impl="sdpa",
    )
    return Parcae(cfg).float().cpu()


def make_opt(model):
    import recpre.optim as optim

    groups = [{"params": [p for p in model.parameters() if p.requires_grad], "lr": 1e-3, "weight_decay": 0.01}]
    return optim.get_optimizer("AdamW", use_apex_adamw=False, allow_fusion=False)(
        groups, lr=1e-3, weight_decay=0.01, betas=(0.9, 0.95)
    )


def make_sched():
    from recpre.schedulers import get_lr_scheduler

    return get_lr_scheduler("linear", base_lr=1e-3, min_lr=1e-4, warmup_steps=1, cooldown_steps=0, max_steps=6)


def rng_state():
    return {
        "torch": sha_bytes(torch.get_rng_state().numpy().tobytes()),
        "python": sha_bytes(repr(random.getstate()).encode()),
        "numpy": sha_bytes(repr(np.random.get_state()).encode()),
    }


def seed_once():
    torch.manual_seed(SEED)
    random.seed(SEED)
    np.random.seed(SEED)


def step(model, opt, sched, ids, labels, n):
    lr = sched.get_lr(n)
    for group in opt.param_groups:
        group["lr"] = lr
    before = weight_sha(model.state_dict())
    model.train()
    out = model(ids, labels=labels, return_logits=True, num_steps_pair=(torch.tensor(0), torch.tensor(2)))
    loss = out["loss"]
    opt.zero_grad(set_to_none=True)
    loss.backward()
    grads = {name: p.grad.detach().clone() for name, p in model.named_parameters() if p.grad is not None}
    opt.step()
    after = weight_sha(model.state_dict())
    expected_change = lr > 0
    return {
        "loss": float(loss.detach()),
        "lr": lr,
        "before": before,
        "after": after,
        "changed": before != after,
        "change_ok": (before != after) == expected_change,
        "finite": bool(torch.isfinite(loss)) and all(torch.isfinite(g).all() for g in grads.values()),
        "grad_count": len(grads),
        "opt_sha": state_sha(opt.state_dict()),
        "sched": {"base_lr": sched.base_lr, "min_lr": sched.min_lr, "warmup": sched.warmup_steps, "max": sched.max_steps},
        "rng": rng_state(),
    }


def save_ckpt(path, model, opt, sched, step_n):
    torch.save({
        "model": model.state_dict(),
        "optimizer": opt.state_dict(),
        "scheduler": {"base_lr": sched.base_lr, "min_lr": sched.min_lr, "warmup_steps": sched.warmup_steps, "max_steps": sched.max_steps},
        "step": step_n,
        "torch_rng": torch.get_rng_state(),
        "python_rng": random.getstate(),
        "numpy_rng": np.random.get_state(),
    }, path)


def load_ckpt(path, root):
    blob = torch.load(path, map_location="cpu", weights_only=False)
    for key in ("model", "optimizer", "scheduler", "step", "torch_rng", "python_rng", "numpy_rng"):
        if key not in blob:
            raise ValueError(f"missing {key}")
    if blob["step"] != 3:
        raise ValueError("wrong step")
    model = make_model(root)
    opt = make_opt(model)
    sched = make_sched()
    model.load_state_dict(blob["model"])
    opt.load_state_dict(blob["optimizer"])
    torch.set_rng_state(blob["torch_rng"])
    random.setstate(blob["python_rng"])
    np.random.set_state(blob["numpy_rng"])
    return model, opt, sched, blob


def corrupt(src, dest, mutator):
    blob = torch.load(src, map_location="cpu", weights_only=False)
    mutator(blob)
    torch.save(blob, dest)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--parcae-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(args.parcae_root).resolve()
    out = Path(args.output).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    seed_once()
    torch.manual_seed(1000)
    ids = torch.randint(0, 128, (2, 8))
    labels = ids.clone()
    base = make_model(root)
    if sum(p.numel() for p in base.parameters()) != 247936:
        raise SystemExit(2)
    weights = copy.deepcopy(base.state_dict())

    def run(start, count, model, opt, sched):
        return [step(model, opt, sched, ids, labels, n) for n in range(start, start + count)]

    seed_once()
    a_model = make_model(root)
    a_model.load_state_dict(weights)
    a_opt, a_sched = make_opt(a_model), make_sched()
    a_rows = run(0, 6, a_model, a_opt, a_sched)

    seed_once()
    b_model = make_model(root)
    b_model.load_state_dict(weights)
    b_opt, b_sched = make_opt(b_model), make_sched()
    b_rows = run(0, 3, b_model, b_opt, b_sched)
    ckpt = out.parent / "f3a_r1_step3.pt"
    save_ckpt(ckpt, b_model, b_opt, b_sched, 3)
    b2_model, b2_opt, b2_sched, blob = load_ckpt(ckpt, root)
    b_rows += run(3, 3, b2_model, b2_opt, b2_sched)

    pair = []
    ok = all(r["change_ok"] and r["finite"] and r["grad_count"] == 74 for r in a_rows)
    for i in range(3, 6):
        loss_ok = abs(a_rows[i]["loss"] - b_rows[i]["loss"]) <= 1e-6 + 1e-6 * max(abs(a_rows[i]["loss"]), abs(b_rows[i]["loss"]))
        item = {
            "step": i + 1,
            "loss_ok": loss_ok,
            "lr_ok": a_rows[i]["lr"] == b_rows[i]["lr"],
            "weight_ok": a_rows[i]["after"] == b_rows[i]["after"],
            "opt_ok": a_rows[i]["opt_sha"] == b_rows[i]["opt_sha"],
            "sched_ok": a_rows[i]["sched"] == b_rows[i]["sched"],
            "rng_ok": a_rows[i]["rng"] == b_rows[i]["rng"],
        }
        pair.append(item)
        ok = ok and all(item.values())

    neg = {}
    cases = {
        "missing_optimizer": lambda b: b.pop("optimizer"),
        "missing_rng": lambda b: b.pop("torch_rng"),
        "wrong_step": lambda b: b.update(step=9),
        "missing_scheduler": lambda b: b.pop("scheduler"),
        "bad_shape": lambda b: b["model"].pop(next(iter(b["model"]))),
    }
    for name, mut in cases.items():
        path = out.parent / f"bad_{name}.pt"
        corrupt(ckpt, path, mut)
        try:
            load_ckpt(path, root)
            neg[name] = "PASS"
        except Exception as exc:
            neg[name] = f"REJECTED:{type(exc).__name__}"
    ok = ok and all(v.startswith("REJECTED") for v in neg.values())

    payload = {
        "review": "PENDING CHATGPT REVIEW",
        "stage": "F3-A-R1 LOCAL RESULT",
        "optimizer": "AdamW",
        "muonadamw": "NOT TESTED",
        "train_py": "NOT TESTED",
        "dataloader_resume": "NOT TESTED",
        "seed_policy": "once per path, not per step",
        "input_sha256": checksum(ids),
        "weight_sha256": weight_sha(weights),
        "checkpoint_sha256": sha_bytes(ckpt.read_bytes()),
        "path_a": a_rows,
        "path_b": b_rows,
        "pair": pair,
        "negatives": neg,
        "local_status": "PASS" if ok else "FAIL",
    }
    out.write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))
    return 0 if payload["local_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
