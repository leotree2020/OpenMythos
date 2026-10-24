"""Standalone F2-B-R1 CPU probe. Not collected by unittest or pytest.

PENDING CHATGPT REVIEW. Not a final PASS.
Does not modify Parcae. No GPU. No dataset download.
"""
import argparse
import json
import platform
import subprocess
import sys
from pathlib import Path

import torch

PINNED = "69284c13746e849104f738d6d1a347b1f457df76"
PAIRS = [(0, 1), (0, 2), (1, 1), (2, 2)]
CAUSAL_TOL = 1e-5
SEED = 42


def git_head(root):
    try:
        out = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            text=True, stderr=subprocess.STDOUT,
        ).strip()
        return out, None
    except Exception as exc:
        return None, str(exc)


def env_record(parcae_root, head):
    return {
        "python": sys.version.split()[0],
        "pytorch": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "cpu": platform.processor() or platform.machine(),
        "threads": torch.get_num_threads(),
        "parcae_root": str(parcae_root),
        "parcae_head": head,
        "pinned": PINNED,
        "device": "cpu",
        "dtype": "float32",
        "seed": SEED,
    }


def make_model():
    from parcae_lm.models.parcae.config import ParcaeConfig
    from parcae_lm.models.parcae.parcae import Parcae

    torch.manual_seed(SEED)
    cfg = ParcaeConfig(
        n_embd=64,
        intermediate_size=128,
        num_attention_heads=4,
        num_key_value_heads=4,
        vocab_size=128,
        padded_vocab_size=128,
        block_size=32,
        n_layers_in_prelude=2,
        n_layers_in_recurrent_block=2,
        n_layers_in_coda=2,
        mean_recurrence=2,
        mean_backprop_depth=2,
        recurrent_embedding_dimension=64,
        recurrent_intermediation_embedding_dimension=128,
        attn_impl="sdpa",
    )
    model = Parcae(cfg).float().cpu()
    model.eval()
    return model, {
        "n_embd": 64,
        "intermediate_size": 128,
        "heads": 4,
        "vocab_size": 128,
        "padded_vocab_size": 128,
        "prelude_core_coda": [2, 2, 2],
        "mean_recurrence": 2,
        "mean_backprop_depth": 2,
        "attn_impl": "sdpa",
        "state_init": "like-init",
    }


def count_core(model, fn):
    flags = []
    orig = model.update_recurrent_state

    def wrapped(*args, **kwargs):
        flags.append(bool(torch.is_grad_enabled()))
        return orig(*args, **kwargs)

    model.update_recurrent_state = wrapped
    try:
        return fn(), flags
    finally:
        model.update_recurrent_state = orig


def run_once(model, ids, labels, pair, train_mode, seed=None):
    if seed is not None:
        torch.manual_seed(seed)
    model.train(train_mode)
    model.zero_grad(set_to_none=True)

    def go():
        return model(ids, labels=labels, return_logits=True, num_steps_pair=torch.tensor(pair))

    out, flags = count_core(model, go)
    loss = out["loss"]
    logits = out["logits"]
    finite = bool(torch.isfinite(loss).item() and torch.isfinite(logits).all().item())
    loss.backward()
    grads = {}
    missing = []
    bad = []
    zero = []
    for name, p in model.named_parameters():
        if not p.requires_grad:
            continue
        if p.grad is None:
            missing.append(name)
            continue
        if not torch.isfinite(p.grad).all():
            bad.append(name)
        if float(p.grad.abs().max()) == 0.0:
            zero.append(name)
        grads[name] = p.grad.detach().clone()
    return {
        "flags": flags,
        "loss": float(loss.detach()),
        "logits": logits.detach().clone(),
        "finite": finite and not bad,
        "grads": grads,
        "missing": missing,
        "bad": bad,
        "zero": zero,
    }


def max_abs(a, b):
    return float((a - b).abs().max().item())


def expected_flags(pair):
    return [False] * pair[0] + [True] * pair[1]


def main():
    parser = argparse.ArgumentParser(description="Standalone F2-B-R1 probe")
    parser.add_argument("--parcae-root", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--require-pinned", action="store_true")
    args = parser.parse_args()

    root = Path(args.parcae_root).resolve()
    out = Path(args.output).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    head, err = git_head(root)
    if args.require_pinned and head != PINNED:
        payload = {"status": "BLOCKED", "reason": "Parcae HEAD mismatch", "head": head, "error": err}
        out.write_text(json.dumps(payload, indent=2))
        print(json.dumps(payload, indent=2))
        return 2
    sys.path.insert(0, str(root))

    model, cfg = make_model()
    env = env_record(root, head)
    torch.manual_seed(SEED)
    ids = torch.randint(0, 128, (1, 8))
    labels = ids.clone()
    results = []

    u1 = run_once(model, ids, labels, (1, 1), False)
    u2 = run_once(model, ids, labels, (1, 1), False)
    results.append({
        "item": "unseeded (1,1)",
        "status": "RECORDED",
        "logit_max_abs": max_abs(u1["logits"], u2["logits"]),
    })

    trainable = [n for n, p in model.named_parameters() if p.requires_grad]
    for pair in PAIRS:
        a = run_once(model, ids, labels, pair, False, SEED)
        b = run_once(model, ids, labels, pair, False, SEED)
        logit_diff = max_abs(a["logits"], b["logits"])
        loss_diff = abs(a["loss"] - b["loss"])
        shared = set(a["grads"]) & set(b["grads"])
        grad_diff = max((max_abs(a["grads"][k], b["grads"][k]) for k in shared), default=None)
        flags_ok = a["flags"] == expected_flags(pair) and b["flags"] == expected_flags(pair)
        covered = len(a["grads"])
        ok = (
            logit_diff == 0.0 and loss_diff == 0.0 and grad_diff == 0.0
            and flags_ok and a["finite"] and b["finite"]
        )
        results.append({
            "item": list(pair),
            "status": "PASS" if ok else "FAIL",
            "flags": a["flags"],
            "flags_ok": flags_ok,
            "logit_max_abs": logit_diff,
            "loss_abs": loss_diff,
            "grad_max_abs": grad_diff,
            "finite": a["finite"] and b["finite"],
            "trainable": len(trainable),
            "with_grad": covered,
            "coverage": covered / len(trainable) if trainable else None,
            "missing": a["missing"],
            "zero": a["zero"],
            "nonfinite": a["bad"],
            "loss": a["loss"],
        })

    a02 = run_once(model, ids, labels, (0, 2), False, SEED)
    a11 = run_once(model, ids, labels, (1, 1), False, SEED)
    only02 = sorted(set(a02["grads"]) - set(a11["grads"]))
    only11 = sorted(set(a11["grads"]) - set(a02["grads"]))
    shared = set(a02["grads"]) & set(a11["grads"])
    results.append({
        "item": "compare (0,2) vs (1,1)",
        "status": "RECORDED",
        "logit_max_abs": max_abs(a02["logits"], a11["logits"]),
        "grad_max_abs": max((max_abs(a02["grads"][k], a11["grads"][k]) for k in shared), default=None),
        "missing_in_0_2": only11,
        "missing_in_1_1": only02,
        "zero_0_2": a02["zero"],
        "zero_1_1": a11["zero"],
        "nonfinite_0_2": a02["bad"],
        "nonfinite_1_1": a11["bad"],
    })

    causal = []
    for pos in (5, 6, 7):
        base = run_once(model, ids, labels, (1, 1), False, SEED)
        changed = ids.clone()
        changed[0, pos] = (changed[0, pos] + 1) % 128
        alt = run_once(model, changed, labels, (1, 1), False, SEED)
        diff = float((base["logits"][:, :pos] - alt["logits"][:, :pos]).abs().max().item())
        causal.append({
            "position": pos,
            "max_abs_before": diff,
            "status": "PASS" if diff < CAUSAL_TOL else "FAIL",
        })
    results.append({
        "item": "causal positions",
        "tolerance": CAUSAL_TOL,
        "positions": causal,
        "status": "PASS" if all(x["status"] == "PASS" for x in causal) else "FAIL",
    })

    modes = []
    for mode in (True, False):
        a = run_once(model, ids, labels, (1, 1), mode, SEED)
        b = run_once(model, ids, labels, (1, 1), mode, SEED)
        modes.append({
            "mode": "train" if mode else "eval",
            "repeat_logit_max_abs": max_abs(a["logits"], b["logits"]),
            "flags": a["flags"],
            "finite": a["finite"] and b["finite"],
            "status": "PASS" if max_abs(a["logits"], b["logits"]) == 0.0 and a["finite"] else "FAIL",
        })
    cross = run_once(model, ids, labels, (1, 1), True, SEED)
    cross_eval = run_once(model, ids, labels, (1, 1), False, SEED)
    results.append({
        "item": "train/eval coverage",
        "modes": modes,
        "train_vs_eval_logit_max_abs": max_abs(cross["logits"], cross_eval["logits"]),
        "status": "PASS" if all(m["status"] == "PASS" for m in modes) else "FAIL",
    })

    hard = [r for r in results if r["status"] == "FAIL"]
    payload = {
        "review": "PENDING CHATGPT REVIEW",
        "kind": "standalone probe, not unittest/pytest",
        "params": sum(p.numel() for p in model.parameters()),
        "env": env,
        "config": cfg,
        "results": results,
        "overall": "FAIL" if hard else "PENDING CHATGPT REVIEW",
    }
    out.write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))
    return 1 if hard else 0


if __name__ == "__main__":
    raise SystemExit(main())
