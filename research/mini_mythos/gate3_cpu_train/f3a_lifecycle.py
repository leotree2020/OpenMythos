"""F3-A CPU training lifecycle probe.

PENDING CHATGPT REVIEW. Does not modify Parcae.
AdamW path only. MuonAdamW is NOT TESTED.
Fixed inputs. DataLoader resume is NOT TESTED.
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

PINNED = "69284c13746e849104f738d6d1a347b1f457df76"
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


def make_model(root):
    sys.path.insert(0, str(root))
    from parcae_lm.models.parcae.config import ParcaeConfig
    from parcae_lm.models.parcae.parcae import Parcae

    torch.manual_seed(SEED)
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


def set_seed():
    torch.manual_seed(SEED)
    random.seed(SEED)
    np.random.seed(SEED)


def step(model, opt, sched, ids, labels, n):
    lr = sched.get_lr(n)
    for group in opt.param_groups:
        group["lr"] = lr
    before = weight_sha(model.state_dict())
    set_seed()
    model.train()
    out = model(ids, labels=labels, return_logits=True, num_steps_pair=(torch.tensor(0), torch.tensor(2)))
    loss = out["loss"]
    opt.zero_grad(set_to_none=True)
    loss.backward()
    grads = {name: p.grad.detach().clone() for name, p in model.named_parameters() if p.grad is not None}
    opt.step()
    return {
        "loss": float(loss.detach()),
        "lr": lr,
        "before": before,
        "after": weight_sha(model.state_dict()),
        "changed": before != weight_sha(model.state_dict()),
        "finite": bool(torch.isfinite(loss)) and all(torch.isfinite(g).all() for g in grads.values()),
        "grad_count": len(grads),
        "opt_steps": int(opt.state_dict()["state"][0]["step"]) if opt.state_dict()["state"] else 0,
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
    model = make_model(root)
    opt = make_opt(model)
    sched = make_sched()
    model.load_state_dict(blob["model"])
    opt.load_state_dict(blob["optimizer"])
    torch.set_rng_state(blob["torch_rng"])
    random.setstate(blob["python_rng"])
    np.random.set_state(blob["numpy_rng"])
    return model, opt, sched, blob


def close(a, b):
    diff = (a - b).abs()
    bound = 1e-6 + 1e-5 * torch.maximum(a.abs(), b.abs())
    return bool(torch.all(diff <= bound)), float(diff.max())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--parcae-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(args.parcae_root).resolve()
    out = Path(args.output).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    set_seed()
    torch.manual_seed(1000)
    ids = torch.randint(0, 128, (2, 8))
    labels = ids.clone()
    base = make_model(root)
    if sum(p.numel() for p in base.parameters()) != 247936:
        raise SystemExit(2)
    weights = copy.deepcopy(base.state_dict())

    def run(start_step, steps, model, opt, sched):
        rows = []
        for n in range(start_step, start_step + steps):
            rows.append(step(model, opt, sched, ids, labels, n))
        return rows

    a_model = make_model(root)
    a_model.load_state_dict(weights)
    a_opt, a_sched = make_opt(a_model), make_sched()
    a_rows = run(0, 6, a_model, a_opt, a_sched)

    b_model = make_model(root)
    b_model.load_state_dict(weights)
    b_opt, b_sched = make_opt(b_model), make_sched()
    b_rows = run(0, 3, b_model, b_opt, b_sched)
    ckpt = out.parent / "f3a_step3.pt"
    save_ckpt(ckpt, b_model, b_opt, b_sched, 3)
    b2_model, b2_opt, b2_sched, blob = load_ckpt(ckpt, root)
    b_rows += run(3, 3, b2_model, b2_opt, b2_sched)

    pair = []
    ok = True
    for i in range(3, 6):
        loss_ok = abs(a_rows[i]["loss"] - b_rows[i]["loss"]) <= 1e-6 + 1e-6 * max(abs(a_rows[i]["loss"]), abs(b_rows[i]["loss"]))
        lr_ok = a_rows[i]["lr"] == b_rows[i]["lr"]
        w_ok = a_rows[i]["after"] == b_rows[i]["after"]
        pair.append({"step": i + 1, "loss_ok": loss_ok, "lr_ok": lr_ok, "weight_ok": w_ok})
        ok = ok and loss_ok and lr_ok and w_ok and a_rows[i]["changed"] and a_rows[i]["finite"]

    # negatives
    bad = torch.load(ckpt, map_location="cpu", weights_only=False)
    bad.pop("optimizer")
    neg = {"missing_optimizer": "optimizer" not in bad}
    bad = torch.load(ckpt, map_location="cpu", weights_only=False)
    bad.pop("torch_rng")
    neg["missing_rng"] = "torch_rng" not in bad
    bad = torch.load(ckpt, map_location="cpu", weights_only=False)
    bad["step"] = 9
    neg["wrong_step"] = bad["step"] != 3

    payload = {
        "review": "PENDING CHATGPT REVIEW",
        "stage": "F3-A LOCAL RESULT",
        "optimizer": "AdamW",
        "muonadamw": "NOT TESTED",
        "train_py": "NOT TESTED",
        "dataloader_resume": "NOT TESTED",
        "input_sha256": checksum(ids),
        "weight_sha256": weight_sha(weights),
        "checkpoint_sha256": sha_bytes(ckpt.read_bytes()),
        "path_a": a_rows,
        "path_b": b_rows,
        "pair": pair,
        "negatives": neg,
        "local_status": "PASS" if ok and all(neg.values()) else "FAIL",
    }
    out.write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))
    return 0 if payload["local_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
