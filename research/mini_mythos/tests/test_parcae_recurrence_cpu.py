"""F2-B CPU recurrence probe. Does not modify Parcae. PENDING REVIEW, not final PASS."""
import json
import sys
from pathlib import Path

import torch

sys.path.insert(0, "/tmp/parcae-src")
from parcae_lm.models.parcae.config import ParcaeConfig
from parcae_lm.models.parcae.parcae import Parcae

PAIRS = [(0, 1), (0, 2), (1, 1), (2, 2)]
CAUSAL_TOL = 1e-5
SEED = 42


def make_model():
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
    return model


def count_core(model, fn):
    calls = {"n": 0}
    orig = model.update_recurrent_state

    def wrapped(*args, **kwargs):
        calls["n"] += 1
        return orig(*args, **kwargs)

    model.update_recurrent_state = wrapped
    try:
        return fn(), calls["n"]
    finally:
        model.update_recurrent_state = orig


def run_once(model, ids, labels, pair, train_mode, seed=None):
    if seed is not None:
        torch.manual_seed(seed)
    model.train(train_mode)
    model.zero_grad(set_to_none=True)

    def go():
        return model(ids, labels=labels, return_logits=True, num_steps_pair=torch.tensor(pair))

    out, calls = count_core(model, go)
    loss = out["loss"]
    logits = out["logits"]
    finite = bool(torch.isfinite(loss).item() and torch.isfinite(logits).all().item())
    loss.backward()
    grads = {}
    bad = []
    for name, p in model.named_parameters():
        if p.grad is None:
            continue
        if not torch.isfinite(p.grad).all():
            bad.append(name)
        grads[name] = p.grad.detach().clone()
    return {
        "calls": calls,
        "loss": float(loss.detach()),
        "logits": logits.detach().clone(),
        "finite": finite and not bad,
        "grad_bad": bad,
        "grads": grads,
    }


def max_abs(a, b):
    return float((a - b).abs().max().item())


def main():
    model = make_model()
    torch.manual_seed(SEED)
    ids = torch.randint(0, 128, (1, 8))
    labels = ids.clone()
    results = []

    # Unseeded: documents that like-init draws a new state each forward.
    u1 = run_once(model, ids, labels, (1, 1), False)
    u2 = run_once(model, ids, labels, (1, 1), False)
    results.append({
        "pair": "unseeded (1,1)",
        "purpose": "show default state_init RNG is not bit-stable across forwards",
        "logit_max_abs": max_abs(u1["logits"], u2["logits"]),
        "status": "RECORDED",
    })

    for pair in PAIRS:
        a = run_once(model, ids, labels, pair, False, SEED)
        b = run_once(model, ids, labels, pair, False, SEED)
        diff = max_abs(a["logits"], b["logits"])
        expected = pair[0] + pair[1]
        ok = diff == 0.0 and a["calls"] == expected and b["calls"] == expected and a["finite"] and b["finite"]
        results.append({
            "pair": list(pair),
            "purpose": "fixed seed, fixed weights, fixed input",
            "calls": [a["calls"], b["calls"]],
            "calls_ok": a["calls"] == expected and b["calls"] == expected,
            "repeat_max_abs": diff,
            "finite": a["finite"] and b["finite"],
            "loss": a["loss"],
            "status": "PASS" if ok else "FAIL",
        })

    a02 = run_once(model, ids, labels, (0, 2), False, SEED)
    a11 = run_once(model, ids, labels, (1, 1), False, SEED)
    shared = set(a02["grads"]) & set(a11["grads"])
    grad_diff = max(max_abs(a02["grads"][k], a11["grads"][k]) for k in shared) if shared else None
    results.append({
        "pair": "compare (0,2) vs (1,1)",
        "purpose": "same total steps, different truncation; record only",
        "logit_max_abs": max_abs(a02["logits"], a11["logits"]),
        "grad_max_abs": grad_diff,
        "status": "RECORDED",
    })

    base = run_once(model, ids, labels, (1, 1), False, SEED)
    changed = ids.clone()
    changed[0, -1] = (changed[0, -1] + 1) % 128
    alt = run_once(model, changed, labels, (1, 1), False, SEED)
    causal_diff = float((base["logits"][:, :-1] - alt["logits"][:, :-1]).abs().max().item())
    results.append({
        "pair": "causal (1,1)",
        "purpose": "future token must not change earlier logits under same seed",
        "tolerance": CAUSAL_TOL,
        "max_abs": causal_diff,
        "status": "PASS" if causal_diff < CAUSAL_TOL else "FAIL",
    })

    train_run = run_once(model, ids, labels, (1, 1), True, SEED)
    eval_run = run_once(model, ids, labels, (1, 1), False, SEED)
    results.append({
        "pair": "train vs eval (1,1)",
        "purpose": "mode difference with fixed pair and fixed seed",
        "logit_max_abs": max_abs(train_run["logits"], eval_run["logits"]),
        "status": "RECORDED",
    })

    hard = [r for r in results if r["status"] == "FAIL"]
    payload = {
        "review": "PENDING REVIEW — not final PASS",
        "params": sum(p.numel() for p in model.parameters()),
        "seed": SEED,
        "state_init": "like-init",
        "causal_tolerance": CAUSAL_TOL,
        "results": results,
        "overall": "FAIL" if hard else "PENDING REVIEW",
    }
    out = Path("/tmp/om/research/mini_mythos/gate2_2/evidence/f2b/F2B_RESULTS.json")
    out.write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))
    return 1 if hard else 0


if __name__ == "__main__":
    raise SystemExit(main())
