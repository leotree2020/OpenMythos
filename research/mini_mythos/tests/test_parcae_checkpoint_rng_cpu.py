"""F2-D B1 D1-D6 CPU probe. D7 is not run.

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
    model = Parcae(cfg, gradient_checkpointing=flag).float().cpu().eval()
    return model


def close(a, b, abs_tol, rel_tol):
    diff = (a - b).abs()
    bound = abs_tol + rel_tol * torch.maximum(a.abs(), b.abs())
    return bool(torch.all(diff <= bound)), float(diff.max())


def synthetic():
    bad_grad = close(torch.tensor([1.0]), torch.tensor([2.0]), 1e-6, 1e-5)[0] is False
    no_replay = ("PASS" if False else "BLOCKED") == "BLOCKED"
    rng_bad = ("PASS" if "a" == "b" else "FAIL") == "FAIL"
    rank = min(["FAIL", "INCONCLUSIVE"], key=lambda s: RANK[s]) == "FAIL"
    return bad_grad and no_replay and rng_bad and rank


def run_once(model, ids, labels, pair, mode):
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
    finally:
        model.update_recurrent_state = orig_update
        for block, orig in zip(model.transformer.core_block, block_orig):
            block.forward = orig
    fwd_updates = [e for e in events if e["fn"] == "update" and e["phase"] == "forward"]
    bwd_updates = [e for e in events if e["fn"] == "update" and e["phase"] == "backward"]
    bwd_blocks = [e for e in events if e["fn"] == "block" and e["phase"] == "backward"]
    return {
        "loss": float(loss.detach()),
        "logits": logits,
        "grads": grads,
        "flags": [e["grad"] for e in fwd_updates],
        "logical_steps": len(fwd_updates),
        "replay_updates": len(bwd_updates),
        "replay_blocks": len(bwd_blocks),
        "rng": {"before": before, "before_reset": before_reset, "after_forward": after_fwd, "after_backward": after_bwd},
        "flag": model.gradient_checkpointing,
        "impl": model.config.activation_checkpoint_impl,
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
    if not synthetic():
        add("synthetic", "FAIL")
        finish(out, items)
        return 1
    add("synthetic", "PASS")

    base = make_model(root, False, "per-iteration")
    import parcae_lm.models.parcae.parcae as mod
    if root not in Path(mod.__file__).resolve().parents:
        add("import", "BLOCKED")
        finish(out, items)
        return 2
    nparams = sum(p.numel() for p in base.parameters())
    if nparams != 247936:
        add("params", "BLOCKED", got=nparams)
        finish(out, items)
        return 2
    weights = copy.deepcopy(base.state_dict())
    weight_sha = sha_bytes(torch.save(weights, f"{out}.weights") or b"")
    Path(f"{out}.weights").unlink()
    torch.manual_seed(1000)
    ids = torch.randint(0, 128, (1, 8))
    labels = ids.clone()
    add("precheck", "PASS", params=nparams, input_sha256=checksum(ids), threads=torch.get_num_threads())

    runs = {}
    for name, flag, impl, pair, _ref in CELLS:
        model = make_model(root, flag, impl)
        model.load_state_dict(weights)
        a = run_once(model, ids, labels, pair, name)
        b = run_once(model, ids, labels, pair, name)
        same = a["loss"] == b["loss"] and checksum(a["logits"]) == checksum(b["logits"])
        runs[name] = a
        expected_flags = [True, True] if pair == (0, 2) else [False, True]
        logical_ok = a["logical_steps"] == 2 and a["flags"] == expected_flags
        add(f"{name} repeat", "PASS" if same and logical_ok else "FAIL", logical=a["logical_steps"], flags=a["flags"])

    for name, flag, impl, pair, ref in CELLS:
        row = runs[name]
        replay = row["replay_updates"] if impl == "per-iteration" and flag else row["replay_blocks"]
        activated = (not flag) or (flag and impl in row["impl"])
        if flag and replay < 1:
            add(name, "BLOCKED", reason="no backward replay", replay_updates=row["replay_updates"], replay_blocks=row["replay_blocks"])
            continue
        if not flag:
            add(name, "PASS", role="baseline", replay_updates=row["replay_updates"], replay_blocks=row["replay_blocks"], rng=row["rng"])
            continue
        base_row = runs[ref]
        logit_ok, logit_diff = close(row["logits"], base_row["logits"], 1e-6, 0.0)
        loss_ok = abs(row["loss"] - base_row["loss"]) <= 1e-6 + 1e-6 * max(abs(row["loss"]), abs(base_row["loss"]))
        names_ok = set(row["grads"]) == set(base_row["grads"]) and len(row["grads"]) == 74
        grad_ok = True
        max_grad = 0.0
        zero = []
        for n, g in base_row["grads"].items():
            if torch.count_nonzero(g) == 0:
                zero.append(n)
            ok, diff = close(row["grads"][n], g, 1e-6, 1e-5)
            grad_ok = grad_ok and ok
            max_grad = max(max_grad, diff)
        scalars = []
        for n, idx in FROZEN:
            gb = float(base_row["grads"][n].view(-1)[idx])
            gm = float(row["grads"][n].view(-1)[idx])
            scalars.append({"name": n, "index": idx, "base": gb, "mode": gm, "abs": abs(gb - gm)})
        rng_ok = (
            row["rng"]["before_reset"] == base_row["rng"]["before_reset"]
            and row["rng"]["after_forward"] == base_row["rng"]["after_forward"]
            and row["rng"]["after_backward"] == row["rng"]["after_forward"]
            and row["rng"]["after_backward"] == base_row["rng"]["after_backward"]
        )
        finite = all(torch.isfinite(g).all() for g in row["grads"].values())
        status = "PASS" if all([logit_ok, loss_ok, names_ok, grad_ok, rng_ok, finite, not zero, activated]) else "FAIL"
        add(name, status, logit_max_abs=logit_diff, loss_abs=abs(row["loss"] - base_row["loss"]), grad_max_abs=max_grad, zero=zero, scalars=scalars, rng=row["rng"], replay_updates=row["replay_updates"], replay_blocks=row["replay_blocks"])

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
        "stage": "F2-D B1 D1-D6",
        "d7": "NOT RUN",
        "local_status": min((i["status"] for i in items), key=lambda s: RANK[s]) if items else "BLOCKED",
        "env": {"python": sys.version.split()[0], "pytorch": torch.__version__, "cpu": platform.machine(), "threads": torch.get_num_threads()},
        "items": items,
    }
    out.write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    raise SystemExit(main())
