"""F2-D B1-R1 D1-D6 CPU probe. D7 is not run.

PENDING CHATGPT REVIEW. Does not modify Parcae.
"""
import argparse
import copy
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path

import torch

PINNED = "69284c13746e849104f738d6d1a347b1f457df76"
SEED = 42
FROZEN = [
    ("transformer.core_block.1.attn.c_proj.weight", 1424),
    ("transformer.core_block.0.attn.c_proj.weight", 1440),
    ("transformer.core_block.0.mlp.proj.weight", 2934),
]
CELLS = [
    ("D1", False, "per-iteration", (0, 2), "D1"),
    ("D2", True, "per-iteration", (0, 2), "D1"),
    ("D3", True, "per-block", (0, 2), "D1"),
    ("D4", False, "per-iteration", (1, 1), "D4"),
    ("D5", True, "per-iteration", (1, 1), "D4"),
    ("D6", True, "per-block", (1, 1), "D4"),
]
RANK = {"FAIL": 0, "BLOCKED": 1, "INCONCLUSIVE": 2, "PASS": 3}


def git_out(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True)


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def rng_sha():
    return sha_bytes(torch.get_rng_state().numpy().tobytes())


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


def make_model(root, flag, impl):
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
        attn_impl="sdpa", activation_checkpoint_impl=impl,
    )
    return Parcae(cfg, gradient_checkpointing=flag).float().cpu().eval()


def close(a, b, abs_tol, rel_tol):
    diff = (a - b).abs()
    bound = abs_tol + rel_tol * torch.maximum(a.abs(), b.abs())
    return bool(torch.all(diff <= bound)), float(diff.max())


def worst(statuses):
    return min(statuses, key=lambda s: RANK[s])


def evaluate(row, base, enabled, pair):
    reasons = []
    expected = [True, True] if pair == (0, 2) else [False, True]
    if row["logical_steps"] != 2 or row["flags"] != expected:
        reasons.append("logical")
    replay = row["replay_updates"] if enabled and "per-iteration" in row["impl"] else row["replay_blocks"]
    if enabled and replay < 1:
        return "BLOCKED", {"reasons": ["no backward replay"], "replay": replay}
    missing = sorted(set(base["grads"]) - set(row["grads"]))
    extra = sorted(set(row["grads"]) - set(base["grads"]))
    if missing or extra or len(row["grads"]) != 74:
        return "FAIL", {"reasons": ["gradient names"], "missing": missing, "extra": extra, "count": len(row["grads"])}
    logit_ok, logit_diff = close(row["logits"], base["logits"], 1e-6, 0.0)
    loss_ok = abs(row["loss"] - base["loss"]) <= 1e-6 + 1e-6 * max(abs(row["loss"]), abs(base["loss"]))
    grad_ok = True
    max_grad = 0.0
    zero = []
    nonfinite = []
    for name, g in base["grads"].items():
        gm = row["grads"].get(name)
        if gm is None:
            missing.append(name)
            continue
        if not torch.isfinite(gm).all() or not torch.isfinite(g).all():
            nonfinite.append(name)
        if torch.count_nonzero(gm) == 0 or torch.count_nonzero(g) == 0:
            zero.append(name)
        ok, diff = close(gm, g, 1e-6, 1e-5)
        grad_ok = grad_ok and ok
        max_grad = max(max_grad, diff)
    rng_ok = (
        row["rng"]["before_reset"] == base["rng"]["before_reset"]
        and row["rng"]["after_forward"] == base["rng"]["after_forward"]
        and row["rng"]["after_backward"] == row["rng"]["after_forward"]
        and row["rng"]["after_backward"] == base["rng"]["after_backward"]
    )
    if not logit_ok:
        reasons.append("logits")
    if not loss_ok:
        reasons.append("loss")
    if not grad_ok:
        reasons.append("gradient values")
    if zero:
        reasons.append("zero")
    if nonfinite:
        reasons.append("nonfinite")
    if not rng_ok:
        reasons.append("rng")
    if missing:
        reasons.append("missing")
    status = "PASS" if not reasons else "FAIL"
    return status, {
        "reasons": reasons,
        "logit_max_abs": logit_diff,
        "loss_abs": abs(row["loss"] - base["loss"]),
        "grad_max_abs": max_grad,
        "grad_count": len(row["grads"]),
        "zero": zero,
        "nonfinite": nonfinite,
        "missing": missing,
        "rng": row["rng"],
        "replay_updates": row["replay_updates"],
        "replay_blocks": row["replay_blocks"],
    }


def synthetic(sample):
    results = {}
    bad = copy.deepcopy(sample)
    name = next(iter(bad["grads"]))
    bad["grads"][name] = bad["grads"][name] + 1
    results["bad_grad"] = evaluate(bad, sample, False, (0, 2))[0]
    missing_replay = copy.deepcopy(sample)
    missing_replay["impl"] = "per-iteration"
    missing_replay["replay_updates"] = 0
    results["missing_replay"] = evaluate(missing_replay, sample, True, (0, 2))[0]
    bad_rng = copy.deepcopy(sample)
    bad_rng["rng"]["after_forward"] = "changed"
    results["bad_rng"] = evaluate(bad_rng, sample, False, (0, 2))[0]
    missing_name = copy.deepcopy(sample)
    missing_name["grads"].pop(name)
    results["missing_name"] = evaluate(missing_name, sample, False, (0, 2))[0]
    ok = (
        results["bad_grad"] == "FAIL"
        and results["missing_replay"] == "BLOCKED"
        and results["bad_rng"] == "FAIL"
        and results["missing_name"] == "FAIL"
        and worst(["FAIL", "INCONCLUSIVE"]) == "FAIL"
    )
    return ok, results


def run_once(model, ids, labels, pair):
    phase = {"v": "forward"}
    events = []
    orig_update = model.update_recurrent_state

    def update(*args, **kwargs):
        events.append({"fn": "update", "phase": phase["v"], "grad": torch.is_grad_enabled()})
        return orig_update(*args, **kwargs)

    model.update_recurrent_state = update
    block_orig = []
    for i, block in enumerate(model.transformer.core_block):
        orig = block.forward

        def make(orig, i):
            def hook(*args, **kwargs):
                events.append({"fn": "block", "i": i, "phase": phase["v"], "grad": torch.is_grad_enabled()})
                return orig(*args, **kwargs)
            return hook

        block.forward = make(orig, i)
        block_orig.append(orig)
    try:
        before = rng_sha()
        torch.manual_seed(SEED)
        before_reset = rng_sha()
        out = model(ids, labels=labels, return_logits=True, num_steps_pair=torch.tensor(pair))
        after_fwd = rng_sha()
        loss = out["loss"]
        logits = out["logits"].detach().clone()
        phase["v"] = "backward"
        model.zero_grad(set_to_none=True)
        loss.backward()
        after_bwd = rng_sha()
        grads = {n: p.grad.detach().clone() for n, p in model.named_parameters() if p.grad is not None}
        after_weights = weight_sha(model.state_dict())
    finally:
        model.update_recurrent_state = orig_update
        for block, orig in zip(model.transformer.core_block, block_orig):
            block.forward = orig
    fwd_updates = [e for e in events if e["fn"] == "update" and e["phase"] == "forward"]
    return {
        "loss": float(loss.detach()),
        "logits": logits,
        "grads": grads,
        "flags": [e["grad"] for e in fwd_updates],
        "logical_steps": len(fwd_updates),
        "replay_updates": sum(e["fn"] == "update" and e["phase"] == "backward" for e in events),
        "replay_blocks": sum(e["fn"] == "block" and e["phase"] == "backward" for e in events),
        "rng": {"before": before, "before_reset": before_reset, "after_forward": after_fwd, "after_backward": after_bwd},
        "flag": model.gradient_checkpointing,
        "impl": model.config.activation_checkpoint_impl,
        "after_weights": after_weights,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--parcae-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(args.parcae_root).resolve()
    out = Path(args.output).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    items = []

    def add(item, status, **extra):
        items.append({"item": item, "status": status, **extra})

    head = git_out(root, "rev-parse", "HEAD").strip()
    status = git_out(root, "status", "--porcelain")
    if head != PINNED or status.strip():
        add("precheck", "BLOCKED", head=head, status=status)
        finish(out, items)
        return 2

    base = make_model(root, False, "per-iteration")
    import parcae_lm.models.parcae.parcae as mod
    imported = str(Path(mod.__file__).resolve())
    if root not in Path(imported).parents:
        add("import", "BLOCKED", imported=imported)
        finish(out, items)
        return 2
    nparams = sum(p.numel() for p in base.parameters())
    if nparams != 247936:
        add("params", "BLOCKED", got=nparams)
        finish(out, items)
        return 2
    weights = copy.deepcopy(base.state_dict())
    wsha = weight_sha(weights)
    torch.manual_seed(1000)
    ids = torch.randint(0, 128, (1, 8))
    labels = ids.clone()
    add("precheck", "PASS", params=nparams, import_path=imported, weight_sha256=wsha, input_sha256=checksum(ids), frozen=FROZEN, threads=torch.get_num_threads())

    runs = {}
    for name, flag, impl, pair, _ref in CELLS:
        model = make_model(root, flag, impl)
        model.load_state_dict(weights)
        if weight_sha(model.state_dict()) != wsha:
            add(f"{name} weight", "FAIL")
            finish(out, items)
            return 1
        a = run_once(model, ids, labels, pair)
        b = run_once(model, ids, labels, pair)
        if a["after_weights"] != wsha or b["after_weights"] != wsha:
            add(f"{name} weight unchanged", "FAIL")
        runs[name] = (a, b)
        status_ab, detail = evaluate(a, b, flag, pair)
        add(f"{name} repeat", status_ab, **detail)

    sample = runs["D1"][0]
    ok, neg = synthetic(sample)
    add("synthetic", "PASS" if ok else "FAIL", results=neg)
    if not ok:
        finish(out, items)
        return exit_code(items)

    for name, flag, impl, pair, ref in CELLS:
        for i, row in enumerate(runs[name], start=1):
            status, detail = evaluate(row, runs[ref][0], flag, pair)
            add(f"{name} run{i}", status, **detail)

    finish(out, items)
    return exit_code(items)


def exit_code(items):
    statuses = [i["status"] for i in items]
    if "FAIL" in statuses:
        return 1
    if "BLOCKED" in statuses:
        return 2
    if "INCONCLUSIVE" in statuses:
        return 3
    return 0


def finish(out, items):
    payload = {
        "review": "PENDING CHATGPT REVIEW",
        "stage": "F2-D B1-R1 D1-D6",
        "d7": "NOT RUN",
        "local_status": worst([i["status"] for i in items]) if items else "BLOCKED",
        "env": {"python": sys.version.split()[0], "pytorch": torch.__version__, "cpu": platform.machine(), "threads": torch.get_num_threads()},
        "items": items,
    }
    out.write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    raise SystemExit(main())
