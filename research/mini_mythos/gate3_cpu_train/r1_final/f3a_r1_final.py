"""F3-A final exception checks.

Uses the committed R1 checkpoint. Does not rerun six-step training.
PENDING CHATGPT REVIEW.
"""
import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

import numpy as np
import torch

FROZEN = {"base_lr": 0.001, "min_lr": 0.0001, "warmup_steps": 1, "max_steps": 6}
SEED = 42


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


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


def load_checked(path, root, trusted_rng):
    blob = torch.load(path, map_location="cpu", weights_only=False)
    for key in ("model", "optimizer", "scheduler", "step", "torch_rng"):
        if key not in blob:
            raise ValueError(f"missing {key}")
    sched = blob["scheduler"]
    for key, expected in FROZEN.items():
        if sched.get(key) != expected:
            raise ValueError(f"scheduler {key}")
    model = make_model(root)
    opt = make_opt(model)
    model.load_state_dict(blob["model"])
    opt.load_state_dict(blob["optimizer"])
    torch.set_rng_state(blob["torch_rng"])
    if sha_bytes(torch.get_rng_state().numpy().tobytes()) != trusted_rng:
        raise ValueError("rng mismatch")
    return model, opt, blob


def copy_mut(src, dest, mut):
    blob = torch.load(src, map_location="cpu", weights_only=False)
    mut(blob)
    torch.save(blob, dest)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--parcae-root", required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(args.parcae_root).resolve()
    src = Path(args.checkpoint).resolve()
    out = Path(args.output).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    trusted = torch.load(src, map_location="cpu", weights_only=False)
    trusted_rng = sha_bytes(trusted["torch_rng"].numpy().tobytes())
    results = {}

    sched_path = out.parent / "bad_scheduler_config.pt"
    copy_mut(src, sched_path, lambda b: b["scheduler"].update(base_lr=0.5))
    try:
        load_checked(sched_path, root, trusted_rng)
        results["bad_scheduler_config"] = "PASS"
    except Exception as exc:
        results["bad_scheduler_config"] = f"REJECTED:{type(exc).__name__}:{exc}"

    rng_path = out.parent / "bad_torch_rng.pt"
    def bad_rng(blob):
        state = blob["torch_rng"].clone()
        state[0] = (int(state[0]) + 1) % 256
        blob["torch_rng"] = state
    copy_mut(src, rng_path, bad_rng)
    try:
        model, opt, blob = load_checked(rng_path, root, trusted_rng)
        results["bad_torch_rng"] = "PASS"
    except ValueError as exc:
        if "rng mismatch" not in str(exc):
            raise
        # Format is valid. Load model, do not reseed, run one step, then fail the check.
        blob = torch.load(rng_path, map_location="cpu", weights_only=False)
        model = make_model(root)
        opt = make_opt(model)
        model.load_state_dict(blob["model"])
        opt.load_state_dict(blob["optimizer"])
        torch.set_rng_state(blob["torch_rng"])
        restored = sha_bytes(torch.get_rng_state().numpy().tobytes())
        ids = torch.randint(0, 128, (2, 8))
        model.train()
        loss = model(ids, labels=ids.clone(), return_logits=True, num_steps_pair=(torch.tensor(0), torch.tensor(2)))["loss"]
        opt.zero_grad(set_to_none=True)
        loss.backward()
        opt.step()
        results["bad_torch_rng"] = "FAIL:rng mismatch" if restored != trusted_rng else "PASS"

    shape_path = out.parent / "bad_tensor_shape.pt"
    def bad_shape(blob):
        key = next(k for k, v in blob["model"].items() if v.ndim > 0)
        blob["model"][key] = blob["model"][key].reshape(-1)
    copy_mut(src, shape_path, bad_shape)
    try:
        load_checked(shape_path, root, trusted_rng)
        results["bad_tensor_shape"] = "PASS"
    except Exception as exc:
        results["bad_tensor_shape"] = f"REJECTED:{type(exc).__name__}:{exc}"

    ok = results["bad_scheduler_config"].startswith("REJECTED") and results["bad_torch_rng"].startswith("FAIL") and results["bad_tensor_shape"].startswith("REJECTED")
    payload = {
        "review": "PENDING CHATGPT REVIEW",
        "stage": "F3-A FINAL EXCEPTION DELTA",
        "source_checkpoint": str(src),
        "source_checkpoint_sha256": sha_bytes(src.read_bytes()),
        "old_bad_shape_reclass": "missing_model_key",
        "results": results,
        "local_status": "PASS" if ok else "FAIL",
        "note": "No six-step rerun. One controlled load path only. MuonAdamW and train.py NOT TESTED.",
    }
    out.write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
