"""F2-D D7 B1 S1-S6 CPU probe.

PENDING CHATGPT REVIEW. Does not modify Parcae. Does not call _sample_batch_depths.
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
RANK = {"FAIL": 0, "BLOCKED": 1, "INCONCLUSIVE": 2, "PASS": 3, "NOT APPLICABLE": 4}


def git_out(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True)


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def rng_sha(state=None):
    s = torch.get_rng_state() if state is None else state
    return sha_bytes(s.numpy().tobytes())


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
    return Parcae(cfg, gradient_checkpointing=flag).float().cpu()


def reference_nk(step):
    seed_n = (514229 + step) % (2**31 - 1)
    g = torch.Generator(device="cpu")
    g.manual_seed(seed_n)
    t = torch.clamp(torch.poisson(torch.tensor([2.0]), generator=g), min=1)
    n = int(t)
    k = min(n, 2)
    return {"seed_n": seed_n, "T": n, "n": n, "k": k, "steps": n + k}


def close(a, b, abs_tol, rel_tol):
    diff = (a - b).abs()
    bound = abs_tol + rel_tol * torch.maximum(a.abs(), b.abs())
    return bool(torch.all(diff <= bound)), float(diff.max())


def worst(statuses):
    return min(statuses, key=lambda s: RANK[s])


def evaluate(row, base, enabled):
    reasons = []
    if row["sampler_fwd"] != 1 or row["sampler_bwd"] != 0:
        return "FAIL", {"reasons": ["sampler count"], "fwd": row["sampler_fwd"], "bwd": row["sampler_bwd"]}
    if row["n"] != base["n"] or row["k"] != base["k"] or row["logical"] != row["n"] + row["k"]:
        return "FAIL", {"reasons": ["n/k"], "n": row["n"], "k": row["k"], "base_n": base["n"], "base_k": base["k"]}
    if enabled and row["k"] > 0 and row["replay"] < 1:
        return "BLOCKED", {"reasons": ["no backward replay"]}
    missing = sorted(set(base["grads"]) - set(row["grads"]))
    if missing or len(row["grads"]) != 74:
        return "FAIL", {"reasons": ["gradient names"], "missing": missing, "count": len(row["grads"])}
    logit_ok, logit_diff = close(row["logits"], base["logits"], 1e-6, 0.0)
    loss_ok = abs(row["loss"] - base["loss"]) <= 1e-6 + 1e-6 * max(abs(row["loss"]), abs(base["loss"]))
    grad_ok = True
    max_grad = 0.0
    zero = []
    for name, g in base["grads"].items():
        gm = row["grads"].get(name)
        if gm is None or not torch.isfinite(gm).all() or torch.count_nonzero(gm) == 0:
            zero.append(name)
            grad_ok = False
            continue
        ok, diff = close(gm, g, 1e-6, 1e-5)
        grad_ok = grad_ok and ok
        max_grad = max(max_grad, diff)
    rng_ok = row["rng"]["after_forward"] == base["rng"]["after_forward"] and row["rng"]["after_backward"] == row["rng"]["after_forward"]
    if not all([logit_ok, loss_ok, grad_ok, rng_ok]) or zero:
        reasons.extend(["values" if not all([logit_ok, loss_ok, grad_ok]) else "", "rng" if not rng_ok else "", "zero" if zero else ""])
        reasons = [r for r in reasons if r]
    return ("PASS" if not reasons else "FAIL"), {"reasons": reasons, "logit_max_abs": logit_diff, "grad_max_abs": max_grad, "rng": row["rng"]}


def synthetic(sample):
    bad_nk = copy.deepcopy(sample)
    bad_nk["n"] = sample["n"] + 1
    rng = copy.deepcopy(sample)
    rng["rng"]["after_forward"] = "changed"
    missing_sampler = copy.deepcopy(sample)
    missing_sampler["sampler_fwd"] = 0
    extra_bwd = copy.deepcopy(sample)
    extra_bwd["sampler_bwd"] = 1
    missing_replay = copy.deepcopy(sample)
    missing_replay["replay"] = 0
    bad_grad = copy.deepcopy(sample)
    name = next(iter(bad_grad["grads"]))
    bad_grad["grads"][name] = bad_grad["grads"][name] + 1
    out = {
        "bad_nk": evaluate(bad_nk, sample, False)[0],
        "bad_rng": evaluate(rng, sample, False)[0],
        "missing_sampler": evaluate(missing_sampler, sample, False)[0],
        "extra_backward_sampler": evaluate(extra_bwd, sample, False)[0],
        "missing_replay": evaluate(missing_replay, sample, True)[0],
        "bad_grad": evaluate(bad_grad, sample, False)[0],
    }
    ok = out["bad_nk"] == "FAIL" and out["bad_rng"] == "FAIL" and out["missing_sampler"] == "FAIL" and out["extra_backward_sampler"] == "FAIL" and out["missing_replay"] == "BLOCKED" and out["bad_grad"] == "FAIL"
    return ok, out


def run_once(model, ids, labels, step, train, backward):
    model.step = step
    model.train(train)
    phase = {"v": "forward"}
    events = []
    orig_sampler = model.randomized_iteration_sampler
    orig_update = model.update_recurrent_state

    def sampler():
        entry = torch.get_rng_state().clone()
        n, k = orig_sampler()
        exit_state = torch.get_rng_state().clone()
        events.append({"fn": "sampler", "phase": phase["v"], "n": int(n), "k": int(k), "entry": rng_sha(entry), "exit": rng_sha(exit_state), "entry_state": entry, "exit_state": exit_state})
        return n, k

    def update(*args, **kwargs):
        events.append({"fn": "update", "phase": phase["v"], "grad": torch.is_grad_enabled()})
        return orig_update(*args, **kwargs)

    model.randomized_iteration_sampler = sampler
    model.update_recurrent_state = update
    block_orig = []
    for i, block in enumerate(model.transformer.core_block):
        orig = block.forward

        def make(orig):
            def hook(*args, **kwargs):
                events.append({"fn": "block", "phase": phase["v"]})
                return orig(*args, **kwargs)
            return hook

        block.forward = make(orig)
        block_orig.append(orig)
    try:
        torch.manual_seed(SEED)
        before = rng_sha()
        out = model(ids, labels=labels, return_logits=True, num_steps_pair=None)
        after_fwd = rng_sha()
        grads = {}
        after_bwd = None
        if backward:
            phase["v"] = "backward"
            model.zero_grad(set_to_none=True)
            out["loss"].backward()
            after_bwd = rng_sha()
            grads = {n: p.grad.detach().clone() for n, p in model.named_parameters() if p.grad is not None}
        after_weights = weight_sha(model.state_dict())
    finally:
        model.randomized_iteration_sampler = orig_sampler
        model.update_recurrent_state = orig_update
        for block, orig in zip(model.transformer.core_block, block_orig):
            block.forward = orig
    samp = [e for e in events if e["fn"] == "sampler"]
    fwd = samp[0] if samp else None
    shadow_ok = None
    if fwd:
        g = torch.Generator(device="cpu")
        g.set_state(fwd["entry_state"])
        torch.rand((1,), generator=g)
        shadow_ok = rng_sha(g.get_state()) == fwd["exit"]
    updates = [e for e in events if e["fn"] == "update" and e["phase"] == "forward"]
    return {
        "n": None if not fwd else fwd["n"],
        "k": None if not fwd else fwd["k"],
        "logical": len(updates),
        "flags": [e["grad"] for e in updates],
        "sampler_fwd": sum(e["phase"] == "forward" for e in samp),
        "sampler_bwd": sum(e["phase"] == "backward" for e in samp),
        "replay": sum(e["fn"] == "update" and e["phase"] == "backward" for e in events) if "per-iteration" in model.config.activation_checkpoint_impl and model.gradient_checkpointing else sum(e["fn"] == "block" and e["phase"] == "backward" for e in events),
        "loss": float(out["loss"].detach()),
        "logits": out["logits"].detach().clone(),
        "grads": grads,
        "rng": {"before": before, "sampler_entry": None if not fwd else fwd["entry"], "sampler_exit": None if not fwd else fwd["exit"], "after_forward": after_fwd, "after_backward": after_bwd},
        "shadow_ok": shadow_ok,
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
    model0 = make_model(root, False, "per-iteration")
    import parcae_lm.models.parcae.parcae as mod
    imported = str(Path(mod.__file__).resolve())
    if root not in Path(imported).parents:
        add("import", "BLOCKED", imported=imported)
        finish(out, items)
        return 2
    weights = copy.deepcopy(model0.state_dict())
    wsha = weight_sha(weights)
    torch.manual_seed(1000)
    ids = torch.randint(0, 128, (1, 8))
    labels = ids.clone()
    add("precheck", "PASS", import_path=imported, params=sum(p.numel() for p in model0.parameters()), weight_sha256=wsha, input_sha256=checksum(ids), threads=torch.get_num_threads(), open_question="_sample_batch_depths uses n=T-k; scalar sampler uses n=T")

    def cell(flag, impl, step, train, backward):
        m = make_model(root, flag, impl)
        m.load_state_dict(weights)
        return run_once(m, ids, labels, step, train, backward)

    s1a, s1b = cell(False, "per-iteration", 0, True, True), cell(False, "per-iteration", 0, True, True)
    s2a, s2b = cell(True, "per-iteration", 0, True, True), cell(True, "per-iteration", 0, True, True)
    s3a, s3b = cell(True, "per-block", 0, True, True), cell(True, "per-block", 0, True, True)
    s4 = cell(False, "per-iteration", 0, True, True)
    s5 = cell(False, "per-iteration", 1, True, True)
    s6 = cell(False, "per-iteration", 0, False, False)

    ref0 = reference_nk(0)
    ref1 = reference_nk(1)
    for name, row in [("S1", s1a), ("S2", s2a), ("S3", s3a), ("S4", s4)]:
        ok = row["n"] == ref0["n"] and row["k"] == ref0["k"] and row["logical"] == ref0["steps"] and row["shadow_ok"] and row["sampler_bwd"] == 0
        add(f"{name} formula", "PASS" if ok else "FAIL", observed={"n": row["n"], "k": row["k"], "logical": row["logical"]}, reference=ref0, shadow_ok=row["shadow_ok"])
    add("S5 formula", "PASS" if s5["n"] == ref1["n"] and s5["k"] == ref1["k"] else "FAIL", observed={"n": s5["n"], "k": s5["k"]}, reference=ref1)
    add("S6 eval", "PASS" if s6["n"] == 2 and s6["k"] == 0 and s6["logical"] == 2 else "FAIL", observed={"n": s6["n"], "k": s6["k"], "logical": s6["logical"]})
    add("S6 gradients", "NOT APPLICABLE")

    ok, neg = synthetic(s1a)
    add("synthetic", "PASS" if ok else "FAIL", results=neg)
    add("S1 repeat", evaluate(s1a, s1b, False)[0])
    add("S2 vs S1", evaluate(s2a, s1a, True)[0])
    add("S3 vs S1", evaluate(s3a, s1a, True)[0])
    add("S2 repeat", evaluate(s2a, s2b, True)[0])
    add("S3 repeat", evaluate(s3a, s3b, True)[0])
    add("S4 vs S1", evaluate(s4, s1a, False)[0])
    finish(out, items)
    return exit_code(items)


def exit_code(items):
    statuses = [i["status"] for i in items if i["status"] != "NOT APPLICABLE"]
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
        "stage": "F2-D D7 B1 S1-S6",
        "local_status": worst([i["status"] for i in items if i["status"] != "NOT APPLICABLE"]) if items else "BLOCKED",
        "env": {"python": sys.version.split()[0], "pytorch": torch.__version__, "cpu": platform.machine()},
        "items": items,
    }
    out.write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    raise SystemExit(main())
