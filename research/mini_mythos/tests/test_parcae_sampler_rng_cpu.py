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


def accept_sampler(row, ref, expect):
    reasons = []
    if row["sampler_fwd"] != 1 or row["sampler_bwd"] != 0:
        reasons.append("sampler count")
    if row["n"] != ref["n"] or row["k"] != ref["k"] or row["logical"] != row["n"] + row["k"]:
        reasons.append("formula")
    if row["flags"] != [False] * row["n"] + [True] * row["k"]:
        reasons.append("flags")
    expected_shape = [1] if expect["train"] else []
    if row.get("dtype") != "torch.int64" or row.get("shape") != expected_shape:
        reasons.append("dtype/shape")
    if not row.get("shadow_ok"):
        reasons.append("shadow")
    if row.get("train") != expect["train"] or row.get("step") != expect["step"] or row.get("scheme") != expect["scheme"]:
        reasons.append("condition")
    if row.get("input_sha") != expect["input_sha"] or row.get("start_weights") != expect["weight_sha"] or row.get("after_weights") != expect["weight_sha"]:
        reasons.append("identity")
    if expect.get("backward") and row["rng"].get("after_backward") != row["rng"].get("after_forward"):
        reasons.append("after-backward rng")
    return ("PASS" if not reasons else "FAIL"), {"reasons": reasons, "n": row["n"], "k": row["k"], "flags": row["flags"], "rng": row["rng"], "shadow_ok": row["shadow_ok"]}


def evaluate(row, base, enabled):
    reasons = []
    if row["sampler_fwd"] != 1 or row["sampler_bwd"] != 0:
        return "FAIL", {"reasons": ["sampler count"], "fwd": row["sampler_fwd"], "bwd": row["sampler_bwd"]}
    if row["n"] != base["n"] or row["k"] != base["k"] or row["logical"] != row["n"] + row["k"]:
        return "FAIL", {"reasons": ["n/k"], "n": row["n"], "k": row["k"], "base_n": base["n"], "base_k": base["k"]}
    expected_flags = [False] * row["n"] + [True] * row["k"]
    if row["flags"] != expected_flags:
        return "FAIL", {"reasons": ["grad flags"], "flags": row["flags"], "expected": expected_flags}
    if row.get("dtype") != "torch.int64" or row.get("shape") not in ([1], []):
        return "FAIL", {"reasons": ["dtype/shape"], "dtype": row.get("dtype"), "shape": row.get("shape")}
    rng_keys = ["before", "sampler_entry", "sampler_exit", "after_forward"]
    if any(row["rng"].get(k) != base["rng"].get(k) for k in rng_keys):
        return "FAIL", {"reasons": ["rng snapshot"], "row_rng": row["rng"], "base_rng": base["rng"]}
    for key in ["train", "step", "scheme", "input_sha", "start_weights", "after_weights"]:
        if row.get(key) != base.get(key):
            return "FAIL", {"reasons": ["condition"], "key": key, "row": row.get(key), "base": base.get(key)}
    if enabled and row["k"] > 0 and row["replay"] < 1:
        return "BLOCKED", {"reasons": ["no backward replay"]}
    if len(row["grads"]) != 74 or len(base["grads"]) != 74 or set(row["grads"]) != set(base["grads"]):
        return "FAIL", {"reasons": ["gradient names"], "row": len(row["grads"]), "base": len(base["grads"])}
    logit_ok, logit_diff = close(row["logits"], base["logits"], 1e-6, 0.0)
    loss_delta = abs(row["loss"] - base["loss"])
    loss_ok = loss_delta <= 1e-6 + 1e-6 * max(abs(row["loss"]), abs(base["loss"]))
    grad_ok = True
    max_grad = 0.0
    zero = []
    for name in base["grads"]:
        g = base["grads"][name]
        gm = row["grads"][name]
        if not torch.isfinite(g).all() or not torch.isfinite(gm).all() or torch.count_nonzero(g) == 0 or torch.count_nonzero(gm) == 0:
            zero.append(name)
            grad_ok = False
            continue
        ok, diff = close(gm, g, 1e-6, 1e-5)
        grad_ok = grad_ok and ok
        max_grad = max(max_grad, diff)
    rng_ok = row["rng"]["after_backward"] == row["rng"]["after_forward"] and base["rng"]["after_backward"] == base["rng"]["after_forward"]
    if not all([logit_ok, loss_ok, grad_ok, rng_ok]) or zero:
        reasons.extend(["values" if not all([logit_ok, loss_ok, grad_ok]) else "", "rng" if not rng_ok else "", "zero" if zero else ""])
        reasons = [r for r in reasons if r]
    return ("PASS" if not reasons else "FAIL"), {"reasons": reasons, "loss": row["loss"], "logit_max_abs": logit_diff, "loss_delta": loss_delta, "grad_max_abs": max_grad, "grad_count": len(row["grads"])}


def synthetic(sample, expect):
    cases = {}
    bad_nk = copy.deepcopy(sample)
    bad_nk["n"] += 1
    cases["bad_nk"] = accept_sampler(bad_nk, {"n": sample["n"], "k": sample["k"]}, expect)[0]
    bad_flags = copy.deepcopy(sample)
    bad_flags["flags"] = [True] * len(sample["flags"])
    cases["bad_flags"] = accept_sampler(bad_flags, {"n": sample["n"], "k": sample["k"]}, expect)[0]
    bad_entry = copy.deepcopy(sample)
    bad_entry["rng"]["sampler_entry"] = "changed"
    cases["bad_entry"] = evaluate(bad_entry, sample, False)[0]
    bad_step = copy.deepcopy(sample)
    bad_step["step"] = 99
    cases["bad_step"] = accept_sampler(bad_step, {"n": sample["n"], "k": sample["k"]}, expect)[0]
    bad_scheme = copy.deepcopy(sample)
    bad_scheme["scheme"] = "fixed"
    cases["bad_scheme"] = accept_sampler(bad_scheme, {"n": sample["n"], "k": sample["k"]}, expect)[0]
    bad_input = copy.deepcopy(sample)
    bad_input["input_sha"] = "changed"
    cases["bad_input"] = accept_sampler(bad_input, {"n": sample["n"], "k": sample["k"]}, expect)[0]
    bad_weight = copy.deepcopy(sample)
    bad_weight["after_weights"] = "changed"
    cases["bad_weight"] = accept_sampler(bad_weight, {"n": sample["n"], "k": sample["k"]}, expect)[0]
    missing_sampler = copy.deepcopy(sample)
    missing_sampler["sampler_fwd"] = 0
    cases["missing_sampler"] = accept_sampler(missing_sampler, {"n": sample["n"], "k": sample["k"]}, expect)[0]
    extra_bwd = copy.deepcopy(sample)
    extra_bwd["sampler_bwd"] = 1
    cases["extra_backward_sampler"] = accept_sampler(extra_bwd, {"n": sample["n"], "k": sample["k"]}, expect)[0]
    missing_replay = copy.deepcopy(sample)
    missing_replay["replay"] = 0
    cases["missing_replay"] = evaluate(missing_replay, sample, True)[0]
    name = next(iter(sample["grads"]))
    bad_grad = copy.deepcopy(sample)
    bad_grad["grads"][name] = bad_grad["grads"][name] + 1
    cases["bad_grad"] = evaluate(bad_grad, sample, False)[0]
    missing_name = copy.deepcopy(sample)
    missing_name["grads"].pop(name)
    cases["missing_name"] = evaluate(missing_name, sample, False)[0]
    ok = all(cases[k] == "FAIL" for k in cases if k != "missing_replay") and cases["missing_replay"] == "BLOCKED"
    return ok, cases


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
        events.append({"fn": "sampler", "phase": phase["v"], "n": int(n), "k": int(k), "dtype": str(n.dtype), "shape": list(n.shape), "entry": rng_sha(entry), "exit": rng_sha(exit_state), "entry_state": entry, "exit_state": exit_state})
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
        "dtype": None if not fwd else fwd["dtype"],
        "shape": None if not fwd else fwd["shape"],
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
    nparams = sum(p.numel() for p in model0.parameters())
    if nparams != 247936:
        add("params", "BLOCKED", got=nparams)
        finish(out, items)
        return 2
    add("precheck", "PASS", import_path=imported, params=nparams, weight_sha256=wsha, input_sha256=checksum(ids), sampling_scheme=model0.config.sampling_scheme, threads=torch.get_num_threads(), open_question="_sample_batch_depths uses n=T-k; scalar sampler uses n=T")

    def cell(flag, impl, step, train, backward):
        m = make_model(root, flag, impl)
        m.load_state_dict(weights)
        if weight_sha(m.state_dict()) != wsha:
            raise RuntimeError("start weight mismatch")
        row = run_once(m, ids, labels, step, train, backward)
        row["start_weights"] = wsha
        row["train"] = train
        row["step"] = step
        row["scheme"] = m.config.sampling_scheme
        row["input_sha"] = checksum(ids)
        return row

    s1a, s1b = cell(False, "per-iteration", 0, True, True), cell(False, "per-iteration", 0, True, True)
    s2a, s2b = cell(True, "per-iteration", 0, True, True), cell(True, "per-iteration", 0, True, True)
    s3a, s3b = cell(True, "per-block", 0, True, True), cell(True, "per-block", 0, True, True)
    s4 = cell(False, "per-iteration", 0, True, True)
    s5 = cell(False, "per-iteration", 1, True, True)
    s6 = cell(False, "per-iteration", 0, False, False)

    for name, row in [("S1a", s1a), ("S1b", s1b), ("S2a", s2a), ("S2b", s2b), ("S3a", s3a), ("S3b", s3b), ("S4", s4), ("S5", s5)]:
        add(f"{name} weights", "PASS" if row["start_weights"] == wsha and row["after_weights"] == wsha else "FAIL")
    add("S6 weights", "PASS" if s6["start_weights"] == wsha else "FAIL")
    ref0 = reference_nk(0)
    ref1 = reference_nk(1)
    expect0 = {"train": True, "step": 0, "scheme": model0.config.sampling_scheme, "input_sha": checksum(ids), "weight_sha": wsha, "backward": True}
    expect5 = {**expect0, "step": 1}
    expect6 = {**expect0, "train": False, "backward": False}
    for name, row, ref, expect in [
        ("S1a", s1a, ref0, expect0), ("S1b", s1b, ref0, expect0),
        ("S2a", s2a, ref0, expect0), ("S2b", s2b, ref0, expect0),
        ("S3a", s3a, ref0, expect0), ("S3b", s3b, ref0, expect0),
        ("S4", s4, ref0, expect0), ("S5", s5, ref1, expect5), ("S6", s6, {"n": 2, "k": 0}, expect6),
    ]:
        status, detail = accept_sampler(row, ref, expect)
        add(f"{name} sampler", status, **detail)
    add("S6 gradients", "NOT APPLICABLE")

    ok, neg = synthetic(s1a, expect0)
    add("synthetic", "PASS" if ok else "FAIL", results=neg)
    def record(name, row, base, enabled):
        status, detail = evaluate(row, base, enabled)
        scalars = []
        for n, idx in FROZEN:
            if n in row["grads"] and n in base["grads"]:
                scalars.append({"name": n, "index": idx, "row": float(row["grads"][n].view(-1)[idx]), "base": float(base["grads"][n].view(-1)[idx])})
        add(name, status, n=row["n"], k=row["k"], logical=row["logical"], flags=row["flags"], sampler_fwd=row["sampler_fwd"], sampler_bwd=row["sampler_bwd"], replay=row["replay"], rng=row["rng"], shadow_ok=row["shadow_ok"], scalars=scalars, **{k:v for k,v in detail.items() if k != "rng"})
    record("S1 repeat", s1a, s1b, False)
    record("S1b vs S1a", s1b, s1a, False)
    record("S2 vs S1", s2a, s1a, True)
    record("S2b vs S1", s2b, s1a, True)
    record("S3 vs S1", s3a, s1a, True)
    record("S3b vs S1", s3b, s1a, True)
    record("S2 repeat", s2a, s2b, True)
    record("S3 repeat", s3a, s3b, True)
    record("S4 vs S1", s4, s1a, False)
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
