"""F2-E B1-R1 CPU probe.

PENDING CHATGPT REVIEW. Does not modify Parcae.
Returned means come from the real iterate_forward return.
E6 is CONTROLLED and exploratory.
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
RANK = {"FAIL": 0, "BLOCKED": 1, "INCONCLUSIVE": 2, "PASS": 3, "NOT DETECTED": 4, "DETECTED": 5, "NOT APPLICABLE": 6}


def git_out(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True)


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


def make_model(root, method, flag=False, impl="per-iteration"):
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
        recurrent_iteration_method=method,
    )
    return Parcae(cfg, gradient_checkpointing=flag).float().cpu()


def reference(method, step, shape):
    seed = (514229 + step) % (2**31 - 1)
    g = torch.Generator(device="cpu")
    g.manual_seed(seed)
    if method == "per-batch":
        t = torch.clamp(torch.poisson(torch.tensor([2.0]), generator=g), min=1)
        n = t.to(torch.long)
        k = torch.clamp(n, max=2)
        total = n
    else:
        total = torch.clamp(torch.poisson(torch.full(shape, 2.0), generator=g), min=1).to(torch.long)
        k = torch.clamp(total, max=2)
        n = total - k
    return {"seed": seed, "n": n, "k": k, "T": total}


def close(a, b, abs_tol, rel_tol):
    diff = (a - b).abs()
    bound = abs_tol + rel_tol * torch.maximum(a.abs(), b.abs())
    return bool(torch.all(diff <= bound)), float(diff.max())


def worst(statuses):
    return min(statuses, key=lambda s: RANK.get(s, 0))


def accept_sample(row, ref, method):
    reasons = []
    if method == "per-batch":
        if row["scalar_calls"] != 1 or row["element_calls"] != 0 or row["sampler_bwd"] != 0:
            reasons.append("sampler route")
    else:
        if row["element_calls"] != 1 or row["scalar_calls"] != 0 or row["sampler_bwd"] != 0:
            reasons.append("sampler route")
    if not torch.equal(row["n"], ref["n"]) or not torch.equal(row["k"], ref["k"]):
        reasons.append("n/k")
    outer = int(ref["n"].max()) + int(ref["k"].max())
    if row["outer"] != outer:
        reasons.append("outer")
    if method != "per-batch":
        exp_n = int(ref["n"].float().mean().to(torch.long))
        exp_k = int(ref["k"].float().mean().to(torch.long))
        if int(row["returned_n"]) != exp_n or int(row["returned_k"]) != exp_k:
            reasons.append("native returned mean")
        expected_shape = [row["n"].shape[0], 1, 1] if method == "per-sequence" else [row["n"].shape[0], row["n"].shape[1], 1]
        nmax, kmax = int(ref["n"].max()), int(ref["k"].max())
        if len(row["recurrent_masks"]) != nmax + kmax:
            reasons.append("mask count")
        for i, m in enumerate(row["recurrent_masks"]):
            expected_phase = "no_grad" if i < nmax else "grad"
            expected_step = i if i < nmax else i - nmax
            if m.get("phase") != expected_phase or m.get("step") != expected_step:
                reasons.append("phase/step")
                break
            if m.get("callsite") != "iterate_forward_write" or not m.get("operand_ok") or not m.get("select_ok"):
                reasons.append("write")
                break
            expected = (expected_step < ref["n"]) if expected_phase == "no_grad" else (expected_step < ref["k"])
            expanded = expected[..., None] if expected.ndim == 2 else expected[:, None, None]
            raw = m.get("mask")
            if raw is None or list(raw.shape) != expected_shape or not torch.equal(raw, expanded):
                reasons.append("mask bits")
                break
        if row["start_weights"] != row["after_weights"]:
            reasons.append("weights changed")
    return ("PASS" if not reasons else "FAIL"), {
        "reasons": reasons,
        "outer": row["outer"],
        "returned": [int(row["returned_n"]), int(row["returned_k"])],
        "masks": row["recurrent_masks"],
    }


def evaluate_pair(row, base, enabled):
    reasons = []
    if row["n"].shape != base["n"].shape or not torch.equal(row["n"], base["n"]) or not torch.equal(row["k"], base["k"]):
        reasons.append("sample")
    if row["rng_before"] != base["rng_before"] or row["rng_after"] != base["rng_after"] or row["input_sha"] != base["input_sha"] or row["start_weights"] != base["start_weights"] or row["after_weights"] != base["after_weights"]:
        reasons.append("identity")
    if row["sampler_bwd"] != 0 or base["sampler_bwd"] != 0:
        reasons.append("backward sampler")
    if len(row["grads"]) != 74 or len(base["grads"]) != 74 or set(row["grads"]) != set(base["grads"]):
        reasons.append("gradient names")
    logit_ok, logit_diff = close(row["logits"], base["logits"], 1e-6, 0.0)
    loss_delta = abs(row["loss"] - base["loss"])
    loss_ok = loss_delta <= 1e-6 + 1e-6 * max(abs(row["loss"]), abs(base["loss"]))
    max_grad = 0.0
    bad = []
    for name in base["grads"]:
        g, gm = base["grads"][name], row["grads"].get(name)
        if gm is None or not torch.isfinite(g).all() or not torch.isfinite(gm).all() or torch.count_nonzero(g) == 0 or torch.count_nonzero(gm) == 0:
            bad.append(name)
            continue
        ok, diff = close(gm, g, 1e-6, 1e-5)
        max_grad = max(max_grad, diff)
        if not ok:
            bad.append(name)
    scalars = []
    for name, idx in FROZEN:
        if name in row["grads"] and name in base["grads"]:
            scalars.append({"name": name, "index": idx, "row": float(row["grads"][name].view(-1)[idx]), "base": float(base["grads"][name].view(-1)[idx])})
    if enabled and (row["replay"] != 2 or base["replay"] != 0):
        return "FAIL", {"reasons": ["replay"], "replay": row["replay"], "base_replay": base["replay"]}
    if row["start_weights"] != row["after_weights"] or base["start_weights"] != base["after_weights"]:
        reasons.append("weights")
    if row.get("rng_after_bwd") != base.get("rng_after_bwd") or row.get("rng_sampler_exit") != base.get("rng_sampler_exit"):
        reasons.append("rng boundary")
    shapes = row.get("grad_shapes") or {}
    if len(shapes) != 74 or set(shapes) != set(row["grads"]) or any(tuple(row["grads"][n].shape) != tuple(shapes[n]) for n in shapes):
        reasons.append("grad shapes")
    if reasons or bad or not logit_ok or not loss_ok:
        return "FAIL", {"reasons": reasons or bad[:5], "logit_max_abs": logit_diff, "loss_delta": loss_delta, "grad_max_abs": max_grad, "scalars": scalars}
    return "PASS", {"logit_max_abs": logit_diff, "loss_delta": loss_delta, "grad_max_abs": max_grad, "grad_count": 74, "replay": row["replay"], "scalars": scalars, "rng_before": row["rng_before"]}


def synthetic(sample, ref):
    cases = {}
    bad = copy.deepcopy(sample)
    bad["n"] = sample["n"] + 1
    cases["bad_nk"] = accept_sample(bad, ref, "per-sequence")[0]
    bad = copy.deepcopy(sample)
    bad["outer"] = sample["outer"] + 1
    cases["bad_outer"] = accept_sample(bad, ref, "per-sequence")[0]
    bad = copy.deepcopy(sample)
    bad["returned_n"] = int(sample["returned_n"]) + 1
    cases["bad_mean"] = accept_sample(bad, ref, "per-sequence")[0]
    bad = copy.deepcopy(sample)
    bad["sampler_bwd"] = 1
    cases["bad_bwd"] = accept_sample(bad, ref, "per-sequence")[0]
    bad = copy.deepcopy(sample)
    bad["recurrent_masks"] = sample["recurrent_masks"][:-1]
    cases["drop_last"] = accept_sample(bad, ref, "per-sequence")[0]
    bad = copy.deepcopy(sample)
    bad["recurrent_masks"] = sample["recurrent_masks"] + [dict(sample["recurrent_masks"][-1])]
    cases["extra_mask"] = accept_sample(bad, ref, "per-sequence")[0]
    bad = copy.deepcopy(sample)
    bad["recurrent_masks"] = [dict(m) for m in sample["recurrent_masks"]]
    bad["recurrent_masks"][0]["step"] = 999
    cases["step_999"] = accept_sample(bad, ref, "per-sequence")[0]
    bad = copy.deepcopy(sample)
    bad["recurrent_masks"] = [dict(m, phase="grad" if m["phase"] == "no_grad" else "no_grad") for m in sample["recurrent_masks"]]
    cases["bad_phase"] = accept_sample(bad, ref, "per-sequence")[0]
    bad = copy.deepcopy(sample)
    flipped = sample["recurrent_masks"][0]["mask"].clone()
    flipped.view(-1)[0] = ~flipped.view(-1)[0]
    bad["recurrent_masks"] = [dict(sample["recurrent_masks"][0], mask=flipped)] + sample["recurrent_masks"][1:]
    cases["flip_bits"] = accept_sample(bad, ref, "per-sequence")[0]
    bad = copy.deepcopy(sample)
    bad["recurrent_masks"] = [dict(m, callsite="other") for m in sample["recurrent_masks"]]
    cases["bad_callsite"] = accept_sample(bad, ref, "per-sequence")[0]
    bad = copy.deepcopy(sample)
    bad["rng_before"] = "changed"
    cases["bad_rng"] = evaluate_pair(bad, sample, False)[0]
    bad = copy.deepcopy(sample)
    bad["replay"] = 0
    cases["missing_replay"] = evaluate_pair(bad, sample, True)[0]
    bad = copy.deepcopy(sample)
    bad["replay"] = 1
    cases["replay_one"] = evaluate_pair(bad, sample, True)[0]
    bad = copy.deepcopy(sample)
    bad["rng_after_bwd"] = "changed"
    cases["bad_rng_bwd"] = evaluate_pair(bad, sample, False)[0]
    bad = copy.deepcopy(sample)
    bad["start_weights"] = "changed"
    cases["bad_weight"] = evaluate_pair(bad, sample, False)[0]
    name = next(iter(sample["grads"]))
    bad = copy.deepcopy(sample)
    bad["grads"][name] = torch.full_like(bad["grads"][name], float("nan"))
    cases["nan_grad"] = evaluate_pair(bad, sample, False)[0]
    bad = copy.deepcopy(sample)
    bad["grads"][name] = torch.zeros_like(bad["grads"][name])
    cases["zero_grad"] = evaluate_pair(bad, sample, False)[0]
    bad = copy.deepcopy(sample)
    bad["grads"] = dict(sample["grads"])
    bad["grads"].pop(name)
    cases["missing_grad"] = evaluate_pair(bad, sample, False)[0]
    bad = copy.deepcopy(sample)
    bad["grads"] = dict(sample["grads"])
    bad["grads"]["extra"] = torch.zeros(1)
    cases["extra_grad"] = evaluate_pair(bad, sample, False)[0]
    return all(v in {"FAIL", "BLOCKED"} for v in cases.values()), cases


def run_once(model, ids, labels, step, controlled=None):
    method = model.config.recurrent_iteration_method
    phase = {"v": "no_grad"}
    events = {"scalar": 0, "element": 0, "bwd": 0, "updates": [], "n": None, "k": None, "returned_n": None, "returned_k": None, "masks": []}
    orig_scalar = model.randomized_iteration_sampler
    orig_element = model._sample_batch_depths
    orig_update = model.update_recurrent_state
    orig_iter = model.iterate_forward
    orig_where = torch.where

    def scalar():
        events["bwd" if phase["v"] == "backward" else "scalar"] += 1
        events["rng_sampler_entry"] = sha_bytes(torch.get_rng_state().numpy().tobytes())
        n, k = orig_scalar()
        events["rng_sampler_exit"] = sha_bytes(torch.get_rng_state().numpy().tobytes())
        events["n"], events["k"] = n.detach().clone(), k.detach().clone()
        return n, k

    def element(*args, **kwargs):
        events["bwd" if phase["v"] == "backward" else "element"] += 1
        if controlled is not None:
            n, k = controlled
            events["n"], events["k"] = n.clone(), k.clone()
            return n, k
        events["rng_sampler_entry"] = sha_bytes(torch.get_rng_state().numpy().tobytes())
        n, k = orig_element(*args, **kwargs)
        events["rng_sampler_exit"] = sha_bytes(torch.get_rng_state().numpy().tobytes())
        events["n"], events["k"] = n.detach().clone(), k.detach().clone()
        return n, k

    def iterate(*args, **kwargs):
        x, n, k, xk = orig_iter(*args, **kwargs)
        events["returned_n"] = n.detach().clone() if torch.is_tensor(n) else torch.tensor(n)
        events["returned_k"] = k.detach().clone() if torch.is_tensor(k) else torch.tensor(k)
        return x, n, k, xk

    write = {"expect": False, "xk": None, "x_new": None, "phase": None, "step": -1, "last": None}
    def update(*args, **kwargs):
        if phase["v"] == "backward":
            events["updates"].append("backward")
            return orig_update(*args, **kwargs)
        write["xk"] = args[0]
        write["phase"] = "grad" if torch.is_grad_enabled() else "no_grad"
        write["expect"] = True
        if write["phase"] != write["last"]:
            write["step"] = 0
            write["last"] = write["phase"]
        else:
            write["step"] += 1
        out = orig_update(*args, **kwargs)
        write["x_new"] = out
        events["updates"].append(write["phase"])
        return out
    def where(mask, a, b, *rest, **kwargs):
        out = orig_where(mask, a, b, *rest, **kwargs)
        if write["expect"] and isinstance(mask, torch.Tensor) and mask.dtype == torch.bool and mask.ndim == 3 and mask.shape[-1] == 1:
            n = events["n"]
            expected = (write["step"] < n) if write["phase"] == "no_grad" else (write["step"] < events["k"])
            expanded = expected[..., None] if expected.ndim == 2 else expected[:, None, None]
            m_exp = mask.expand_as(out)
            events["masks"].append({
                "phase": write["phase"],
                "step": write["step"],
                "shape": list(mask.shape),
                "true": int(mask.sum()),
                "mask": mask.detach().clone(),
                "mask_sha256": checksum(mask),
                "content_ok": bool(torch.equal(mask, expanded)),
                "select_ok": bool(torch.all(torch.where(m_exp, out == a, out == b))),
                "operand_ok": bool(torch.equal(a, write["x_new"]) and torch.equal(b, write["xk"])),
                "callsite": "iterate_forward_write",
            })
            write["expect"] = False
        return out

    model.randomized_iteration_sampler = scalar
    model._sample_batch_depths = element
    model.update_recurrent_state = update
    model.iterate_forward = iterate
    torch.where = where
    try:
        start_weights = weight_sha(model.state_dict())
        torch.manual_seed(SEED)
        before = sha_bytes(torch.get_rng_state().numpy().tobytes())
        model.step = step
        model.train()
        # phase tracking is approximate: no_grad updates happen first
        out = model(ids, labels=labels, return_logits=True, num_steps_pair=None)
        after = sha_bytes(torch.get_rng_state().numpy().tobytes())
        phase["v"] = "backward"
        model.zero_grad(set_to_none=True)
        out["loss"].backward()
        grads = {n: p.grad.detach().clone() for n, p in model.named_parameters() if p.grad is not None}
        grad_shapes = {n: list(p.shape) for n, p in model.named_parameters() if p.requires_grad}
        rng_after_bwd = sha_bytes(torch.get_rng_state().numpy().tobytes())
    finally:
        torch.where = orig_where
        model.randomized_iteration_sampler = orig_scalar
        model._sample_batch_depths = orig_element
        model.update_recurrent_state = orig_update
        model.iterate_forward = orig_iter
    n, k = events["n"], events["k"]
    n_int = int(n.max()) if n is not None else 0
    # mark first n_int forward updates as no_grad by source schedule
    forward_updates = [p for p in events["updates"] if p != "backward"]
    return {
        "method": method,
        "n": n,
        "k": k,
        "scalar_calls": events["scalar"],
        "element_calls": events["element"],
        "sampler_bwd": events["bwd"],
        "outer": len(forward_updates),
        "replay": sum(p == "backward" for p in events["updates"]),
        "returned_n": events["returned_n"],
        "returned_k": events["returned_k"],
        "recurrent_masks": events["masks"],
        "loss": float(out["loss"].detach()),
        "logits": out["logits"].detach().clone(),
        "grads": grads,
        "rng_before": before,
        "rng_after": after,
        "rng_after_bwd": rng_after_bwd,
        "rng_sampler_entry": events.get("rng_sampler_entry"),
        "rng_sampler_exit": events.get("rng_sampler_exit"),
        "grad_shapes": grad_shapes,
        "input_sha": checksum(ids),
        "start_weights": start_weights,
        "after_weights": weight_sha(model.state_dict()),
    }


def e6(root, weights):
    model = make_model(root, "per-token")
    model.load_state_dict(weights)
    t = torch.ones(2, 8, dtype=torch.long)
    t[0, 0] = 1
    t[0, 1] = 4
    n = t - torch.clamp(t, max=2)
    k = torch.clamp(t, max=2)
    # algebraic where only
    x = torch.ones(2, 8, 4)
    x_new = x + 1
    mask = (torch.tensor(0) < n)
    got = torch.where(mask[..., None], x_new, x)
    where_ok = torch.equal(got[0, 0], x[0, 0]) and torch.equal(got[0, 1], x_new[0, 1])
    # target-token measurement inside the real per-token loop
    captured = {}
    orig_update = model.update_recurrent_state
    calls = {"i": 0}

    def update(x, *rest):
        if calls["i"] == 0:
            captured["x"] = x.detach().clone()
            captured["rest"] = rest
        calls["i"] += 1
        return orig_update(x, *rest)

    model.update_recurrent_state = update
    model._sample_batch_depths = lambda *a, **kw: (n, k)
    ids = torch.arange(16).view(2, 8)
    model.train()
    model.step = 0
    torch.manual_seed(SEED)
    model(ids, labels=ids.clone(), return_logits=True, num_steps_pair=None)
    model.update_recurrent_state = orig_update
    if "x" not in captured:
        return "INCONCLUSIVE", {"reason": "no captured state", "controlled": True, "where_ok": where_ok}
    base_x = captured["x"]
    inactive = base_x.clone()
    inactive[0, 0, 0] += 0.1
    active = base_x.clone()
    active[0, 1, 0] += 0.1
    y0 = orig_update(base_x, *captured["rest"])
    yi = orig_update(inactive, *captured["rest"])
    ya = orig_update(active, *captured["rest"])
    target = (yi - y0)[0, 1].abs().max().item()
    control = (ya - y0)[0, 1].abs().max().item()
    return "INCONCLUSIVE", {
        "controlled": True,
        "where_ok": where_ok,
        "target_token_max_abs": target,
        "positive_control_max_abs": control,
        "reason": "numbers come from a direct update replay, not the live masked-loop output",
        "planned_T": t.tolist(),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--parcae-root", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--fail-demo", action="store_true")
    args = parser.parse_args()
    if args.fail_demo:
        Path(args.output).write_text("FAIL demo\n")
        raise SystemExit(exit_code([{"status": "FAIL"}]))
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
    base = make_model(root, "per-batch")
    import parcae_lm.models.parcae.parcae as mod
    if root not in Path(mod.__file__).resolve().parents or sum(p.numel() for p in base.parameters()) != 247936:
        add("precheck", "BLOCKED")
        finish(out, items)
        return 2
    weights = copy.deepcopy(base.state_dict())
    wsha = weight_sha(weights)
    torch.manual_seed(1000)
    ids1 = torch.randint(0, 128, (1, 8))
    ids2 = torch.randint(0, 128, (2, 8))
    add("precheck", "PASS", weight_sha256=wsha, input1=checksum(ids1), input2=checksum(ids2))

    def cell(method, ids, flag=False):
        m = make_model(root, method, flag)
        m.load_state_dict(weights)
        return run_once(m, ids, ids.clone(), 0)

    e1 = cell("per-batch", ids1)
    e2 = cell("per-sequence", ids2)
    e3 = cell("per-token", ids2)
    e4s = cell("per-sequence", ids2)
    e4t = cell("per-token", ids2)
    e5s_off, e5s_on = cell("per-sequence", ids2, False), cell("per-sequence", ids2, True)
    e5t_off, e5t_on = cell("per-token", ids2, False), cell("per-token", ids2, True)
    for name, row, method, shape in [("E1", e1, "per-batch", (1,)), ("E2", e2, "per-sequence", (2,)), ("E3", e3, "per-token", (2, 8))]:
        status, detail = accept_sample(row, reference(method, 0, shape), method)
        add(name, status, n=row["n"].tolist(), k=row["k"].tolist(), **detail)
    for name, pair in [
        ("E4 sequence", evaluate_pair(e4s, e2, False)),
        ("E4 token", evaluate_pair(e4t, e3, False)),
        ("E5 sequence", evaluate_pair(e5s_on, e5s_off, True)),
        ("E5 token", evaluate_pair(e5t_on, e5t_off, True)),
    ]:
        status, detail = pair
        add(name, status, **detail)
    add("cross mode logits", "NOT APPLICABLE")
    ok, cases = synthetic(e2, reference("per-sequence", 0, (2,)))
    add("synthetic", "PASS" if ok else "FAIL", results=cases)
    add("E6 controlled", "INCONCLUSIVE", controlled=True, prior_target_token_max_abs=0.0049576908349990845, prior_positive_control_max_abs=0.04084044694900513, reason="kept from R1; direct update replay is not live masked-loop evidence")
    finish(out, items)
    return exit_code(items)


def exit_code(items):
    statuses = [i["status"] for i in items if i["status"] not in {"NOT APPLICABLE", "DETECTED", "NOT DETECTED"}]
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
        "stage": "F2-E B1-R3 FINAL ACCEPTANCE DELTA",
        "local_status": worst([i["status"] for i in items if i["status"] not in {"NOT APPLICABLE", "DETECTED", "NOT DETECTED"}]) if items else "BLOCKED",
        "env": {"python": sys.version.split()[0], "pytorch": torch.__version__, "cpu": platform.machine()},
        "intent": "INTENT UNKNOWN",
        "items": items,
    }
    for item in payload["items"]:
        for m in item.get("masks") or []:
            if "mask" in m and "mask_sha256" not in m:
                m["mask_sha256"] = checksum(m["mask"])
            m.pop("mask", None)
    out.write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    raise SystemExit(main())
