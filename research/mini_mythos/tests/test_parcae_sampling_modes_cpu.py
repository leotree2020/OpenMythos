"""F2-E B1 E1-E6 CPU probe.

PENDING CHATGPT REVIEW. Does not modify Parcae.
E6 is a test-side controlled intervention, not a native sample.
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
    else:
        total = torch.clamp(torch.poisson(torch.full(shape, 2.0), generator=g), min=1).to(torch.long)
        k = torch.clamp(total, max=2)
        n = total - k
    return {"seed": seed, "n": n, "k": k, "T": n if method == "per-batch" else n + k}


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
        mean_n = int(ref["n"].float().mean().to(torch.long))
        mean_k = int(ref["k"].float().mean().to(torch.long))
        if row["returned_n"] != mean_n or row["returned_k"] != mean_k:
            reasons.append("returned mean")
    return ("PASS" if not reasons else "FAIL"), {"reasons": reasons, "outer": row["outer"], "returned": [row["returned_n"], row["returned_k"]]}


def evaluate_pair(row, base, enabled):
    if row["n"].shape != base["n"].shape or not torch.equal(row["n"], base["n"]) or not torch.equal(row["k"], base["k"]):
        return "FAIL", {"reasons": ["sample mismatch"]}
    if len(row["grads"]) != 74 or set(row["grads"]) != set(base["grads"]):
        return "FAIL", {"reasons": ["gradient names"], "count": len(row["grads"])}
    logit_ok, logit_diff = close(row["logits"], base["logits"], 1e-6, 0.0)
    loss_delta = abs(row["loss"] - base["loss"])
    loss_ok = loss_delta <= 1e-6 + 1e-6 * max(abs(row["loss"]), abs(base["loss"]))
    max_grad = 0.0
    bad = []
    for name in base["grads"]:
        g, gm = base["grads"][name], row["grads"][name]
        if not torch.isfinite(g).all() or not torch.isfinite(gm).all() or torch.count_nonzero(g) == 0 or torch.count_nonzero(gm) == 0:
            bad.append(name)
            continue
        ok, diff = close(gm, g, 1e-6, 1e-5)
        max_grad = max(max_grad, diff)
        if not ok:
            bad.append(name)
    if enabled and row["replay"] < 1:
        return "BLOCKED", {"reasons": ["no replay"]}
    status = "PASS" if logit_ok and loss_ok and not bad else "FAIL"
    return status, {"reasons": bad[:5], "logit_max_abs": logit_diff, "loss_delta": loss_delta, "grad_max_abs": max_grad, "grad_count": len(row["grads"])}


def synthetic(sample, ref, method):
    bad = copy.deepcopy(sample)
    bad["n"] = sample["n"] + 1
    cases = {"bad_nk": accept_sample(bad, ref, method)[0]}
    bad = copy.deepcopy(sample)
    bad["outer"] = sample["outer"] + 1
    cases["bad_outer"] = accept_sample(bad, ref, method)[0]
    bad = copy.deepcopy(sample)
    bad["returned_n"] = sample["returned_n"] + 1
    cases["bad_mean"] = accept_sample(bad, ref, "per-sequence")[0]
    bad = copy.deepcopy(sample)
    bad["sampler_bwd"] = 1
    cases["bad_bwd"] = accept_sample(bad, ref, method)[0]
    return all(v == "FAIL" for v in cases.values()), cases


def run_once(model, ids, labels, step):
    method = model.config.recurrent_iteration_method
    events = {"scalar": 0, "element": 0, "bwd": 0, "updates": [], "n": None, "k": None}
    phase = {"v": "forward"}
    orig_scalar = model.randomized_iteration_sampler
    orig_element = model._sample_batch_depths
    orig_update = model.update_recurrent_state

    def scalar():
        if phase["v"] == "backward":
            events["bwd"] += 1
        else:
            events["scalar"] += 1
        n, k = orig_scalar()
        events["n"], events["k"] = n.detach().clone(), k.detach().clone()
        return n, k

    def element(*args, **kwargs):
        if phase["v"] == "backward":
            events["bwd"] += 1
        else:
            events["element"] += 1
        n, k = orig_element(*args, **kwargs)
        events["n"], events["k"] = n.detach().clone(), k.detach().clone()
        return n, k

    def update(*args, **kwargs):
        events["updates"].append(phase["v"])
        return orig_update(*args, **kwargs)

    model.randomized_iteration_sampler = scalar
    model._sample_batch_depths = element
    model.update_recurrent_state = update
    masks = []
    orig_where = torch.where
    def where(mask, a, b):
        if isinstance(mask, torch.Tensor) and mask.dtype == torch.bool:
            masks.append({"shape": list(mask.shape), "true": int(mask.sum())})
        return orig_where(mask, a, b)
    torch.where = where
    try:
        torch.manual_seed(SEED)
        before = sha_bytes(torch.get_rng_state().numpy().tobytes())
        model.step = step
        model.train()
        out = model(ids, labels=labels, return_logits=True, num_steps_pair=None)
        after = sha_bytes(torch.get_rng_state().numpy().tobytes())
        phase["v"] = "backward"
        model.zero_grad(set_to_none=True)
        out["loss"].backward()
        grads = {n: p.grad.detach().clone() for n, p in model.named_parameters() if p.grad is not None}
    finally:
        torch.where = orig_where
        model.randomized_iteration_sampler = orig_scalar
        model._sample_batch_depths = orig_element
        model.update_recurrent_state = orig_update
    n, k = events["n"], events["k"]
    returned = out.get("num_steps_no_grad") if isinstance(out, dict) else None
    # returned means are not in forward dict; recompute from captured tensors for per-element
    returned_n = int(n) if method == "per-batch" else int(n.float().mean().to(torch.long))
    returned_k = int(k) if method == "per-batch" else int(k.float().mean().to(torch.long))
    return {
        "method": method,
        "n": n,
        "k": k,
        "scalar_calls": events["scalar"],
        "element_calls": events["element"],
        "sampler_bwd": events["bwd"],
        "outer": sum(p == "forward" for p in events["updates"]),
        "replay": sum(p == "backward" for p in events["updates"]),
        "returned_n": returned_n,
        "returned_k": returned_k,
        "masks": masks,
        "loss": float(out["loss"].detach()),
        "logits": out["logits"].detach().clone(),
        "grads": grads,
        "rng_before": before,
        "rng_after": after,
        "after_weights": weight_sha(model.state_dict()),
    }


def e6(model):
    # test-side controlled intervention
    n = torch.tensor([[0, 1]], dtype=torch.long)
    k = torch.tensor([[0, 1]], dtype=torch.long)
    orig = model._sample_batch_depths
    model._sample_batch_depths = lambda *a, **kw: (n, k)
    ids = torch.tensor([[1, 2]])
    labels = ids.clone()
    model.train()
    model.step = 0
    torch.manual_seed(SEED)
    out = model(ids, labels=labels, return_logits=True, num_steps_pair=None)
    model._sample_batch_depths = orig
    # algebraic where
    x = torch.ones(1, 2, 4)
    x_new = x + 1
    mask = torch.tensor([[False, True]])
    got = torch.where(mask[..., None], x_new, x)
    where_ok = torch.equal(got[:, 0], x[:, 0]) and torch.equal(got[:, 1], x_new[:, 1])
    # coupling through one native core update
    x0 = torch.zeros(1, 2, 64)
    x1 = x0.clone()
    x1[:, 0, 0] += 0.1
    pos = torch.zeros(1, 2, 64)
    mask_attn = torch.ones(1, 1, 2, 2)
    step = torch.tensor(0)
    total = torch.tensor(1)
    y0 = model.update_recurrent_state(x0, pos, model.freqs_cis[:, :2], mask_attn, step, total)
    y1 = model.update_recurrent_state(x1, pos, model.freqs_cis[:, :2], mask_attn, step, total)
    delta = (y1 - y0).abs().max().item()
    pos_ctrl = x0.clone()
    pos_ctrl[:, 1, 0] += 0.1
    yp = model.update_recurrent_state(pos_ctrl, pos, model.freqs_cis[:, :2], mask_attn, step, total)
    pos_delta = (yp - y0).abs().max().item()
    if pos_delta <= 1e-6:
        status = "INCONCLUSIVE"
    elif delta > 1e-6:
        status = "DETECTED"
    else:
        status = "NOT DETECTED"
    return status, {"where_ok": where_ok, "inactive_to_active_max_abs": delta, "positive_control_max_abs": pos_delta, "controlled": True}


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
    add("precheck", "PASS", weight_sha256=wsha, input1=checksum(ids1), input2=checksum(ids2), distributed=torch.distributed.is_initialized())

    def cell(method, ids, flag=False):
        m = make_model(root, method, flag)
        m.load_state_dict(weights)
        return run_once(m, ids, ids.clone(), 0)

    e1 = cell("per-batch", ids1)
    e2 = cell("per-sequence", ids2)
    e3 = cell("per-token", ids2)
    e4 = cell("per-sequence", ids2)
    e5_off = cell("per-sequence", ids2, False)
    e5_on = cell("per-sequence", ids2, True)
    for name, row, method, shape in [
        ("E1", e1, "per-batch", (1,)),
        ("E2", e2, "per-sequence", (2,)),
        ("E3", e3, "per-token", (2, 8)),
    ]:
        ref = reference(method, 0, shape)
        status, detail = accept_sample(row, ref, method)
        add(name, status, n=row["n"].tolist(), k=row["k"].tolist(), masks=row.get("masks"), **detail)
    add("E4 repeat", evaluate_pair(e4, e2, False)[0])
    add("E5 checkpoint", evaluate_pair(e5_on, e5_off, True)[0])
    add("cross mode logits", "NOT APPLICABLE")
    ok, cases = synthetic(e2, reference("per-sequence", 0, (2,)), "per-sequence")
    add("synthetic", "PASS" if ok else "FAIL", results=cases)
    status, detail = e6(base)
    add("E6 controlled", status, **detail)
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
        "stage": "F2-E B1 E1-E6",
        "local_status": worst([i["status"] for i in items if i["status"] not in {"NOT APPLICABLE", "DETECTED", "NOT DETECTED"}]) if items else "BLOCKED",
        "env": {"python": sys.version.split()[0], "pytorch": torch.__version__, "cpu": platform.machine()},
        "intent": "INTENT UNKNOWN",
        "items": items,
    }
    out.write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    raise SystemExit(main())
