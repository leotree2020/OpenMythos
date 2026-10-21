"""
Shared pieces of Gate D: paths, the 30 model states, diagnostic sets, the
parameter groups of D5 (tied embed=head counted once) and grouped bootstrap.
Nothing here trains or modifies a model.
"""

import hashlib
import json
import math
import os
import sys

import numpy as np
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.join(HERE, "..")
ROOT = os.path.join(EXP, "..")
for p in (ROOT, os.path.join(EXP, "basic_learn"), os.path.join(EXP, "gen_gate_a")):
    if p not in sys.path:
        sys.path.append(p)

from models import build  # noqa: E402

ARMS = ("openmythos", "transformer")
SEEDS = (1, 2, 3)
STEPS = (0, 3000, 6000, 9000, 12000)
BUDGET = os.path.join(EXP, "budget_a", "runs")
SETS = os.path.join(HERE, "sets")
L_PROMPT = 19  # level-A input length; '?' (readout) at index 18
Q_POS, READ_POS = 17, 18
DIGIT_POS = (2, 6, 10, 14)
VAR_POS = (0, 4, 8, 12)
LETTERS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


def state_name(arm, seed, step):
    return f"{arm}_s{seed}_step{step}"


def all_states():
    return [(a, s, t) for a in ARMS for s in SEEDS for t in STEPS]


def load_state(arm, seed, step, path=None):
    """Model in eval mode. Step 0 is the deterministic reconstruction of the
    initialization (torch.manual_seed(seed); build(arm, 4)), as in
    gen_gate_a/train_level.py; it is not independently verified against the
    original initialization (none was saved)."""
    if path is None and step == 0:
        torch.manual_seed(seed)
        model = build(arm, 4)
    else:
        if path is None:
            path = os.path.join(
                BUDGET,
                f"A_{arm}_s{seed}.pt" if step == 12000 else f"A_{arm}_s{seed}_step{step}.pt",
            )
        ck = torch.load(path, map_location="cpu", weights_only=False)
        assert ck["arm"] == arm and ck["seed"] == seed, (path, ck["arm"], ck["seed"])
        if "step" in ck:
            assert ck["step"] == step, (path, ck["step"])
        model = build(arm, 4)
        model.load_state_dict(ck["model"])
    model.eval()
    return model


def param_hash(model):
    h = hashlib.sha256()
    for k, v in model.state_dict().items():
        h.update(k.encode())
        h.update(v.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


# ---------------------------------------------------------------- data sets


def load_diag(name):
    """Rows of a frozen diagnostic set, checked against sets/manifest.json."""
    text = open(os.path.join(SETS, f"{name}.jsonl")).read()
    want = json.load(open(os.path.join(SETS, "manifest.json")))[name]["sha256"]
    if hashlib.sha256(text.encode()).hexdigest() != want:
        raise RuntimeError(f"{name} does not match its manifest hash")
    return [json.loads(l) for l in text.splitlines()]


def encode(prompts):
    x = torch.tensor([list(p.encode()) for p in prompts], dtype=torch.long)
    assert x.shape[1] == L_PROMPT and bool((x[:, READ_POS] == ord("?")).all())
    return x


def family_tensors(rows):
    """rows: one per body with 'body', 'queries' (4 letters in statement-slot
    order), 'answers' (4 digits). Returns x (4N, 19) ordered body-major,
    y (4N,), slot (4N,), body index (4N,), roots (N, 4) digit bytes."""
    prompts, ys, slots, bid, roots = [], [], [], [], []
    for i, r in enumerate(rows):
        for k in range(4):
            prompts.append(r["body"] + "|" + r["queries"][k] + "?")
            ys.append(ord(r["answers"][k]))
            slots.append(k)
            bid.append(i)
        roots.append([ord(d) for d in r["answers"]])
    return (
        encode(prompts),
        torch.tensor(ys),
        torch.tensor(slots),
        torch.tensor(bid),
        torch.tensor(roots),
    )


# ---------------------------------------------------------------- D5 groups


def param_groups(model):
    """name -> list of (param_name, param). named_parameters() yields the tied
    embed/head weight once (as embed.weight), so it is counted once."""
    groups = {}
    arm = "transformer" if hasattr(model, "layers") else "openmythos"
    for n, p in model.named_parameters():
        assert not n.startswith("head."), n  # tied: never listed separately
        if n == "embed.weight":
            g = "embed=head"
        elif n.startswith("norm."):
            g = "final_norm"
        else:
            if arm == "transformer":
                blk, rest = ".".join(n.split(".")[:2]), ".".join(n.split(".")[2:])
                blk = blk.replace("layers.", "L")
            elif n.startswith("prelude."):
                blk, rest = "pre" + n.split(".")[1], ".".join(n.split(".")[2:])
            elif n.startswith("coda."):
                blk, rest = "coda" + n.split(".")[1], ".".join(n.split(".")[2:])
            elif n.startswith("recurrent.block."):
                blk, rest = "loop", n[len("recurrent.block.") :]
            else:
                groups.setdefault("loop_only", []).append((n, p))
                continue
            if rest.startswith("attn."):
                g = f"{blk}.attn.{rest.split('.')[1]}"
            elif rest.startswith("ffn."):
                g = f"{blk}.ffn"
            else:
                g = f"{blk}.norms"
        groups.setdefault(g, []).append((n, p))
    return groups


def group_index(model):
    """Flat-vector slices per group (and aggregates attn_all, total)."""
    groups = param_groups(model)
    names = [n for n, _ in model.named_parameters()]
    sizes = {n: p.numel() for n, p in model.named_parameters()}
    offset, start = 0, {}
    for n in names:
        start[n] = offset
        offset += sizes[n]
    idx = {}
    for g, items in groups.items():
        idx[g] = torch.cat([torch.arange(start[n], start[n] + sizes[n]) for n, _ in items])
    idx["attn_all"] = torch.cat([v for g, v in idx.items() if ".attn." in g])
    idx["total"] = torch.arange(offset)
    return idx, offset


def flat_grad(model):
    return torch.cat(
        [
            (p.grad if p.grad is not None else torch.zeros_like(p)).reshape(-1)
            for _, p in model.named_parameters()
        ]
    )


def flat_params(model):
    return torch.cat([p.detach().reshape(-1) for _, p in model.named_parameters()])


# ---------------------------------------------------------------- statistics


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [c - h, c + h]


def grouped_bootstrap(values, groups, stat=np.mean, n_boot=2000, seed=0):
    """95% CI of stat(values) resampling whole groups (bodies) with
    replacement. values: (n,) or (n, k) array; groups: (n,) int ids."""
    values = np.asarray(values, dtype=np.float64)
    groups = np.asarray(groups)
    uniq, inv = np.unique(groups, return_inverse=True)
    members = [np.flatnonzero(inv == g) for g in range(len(uniq))]
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n_boot):
        pick = rng.integers(0, len(uniq), len(uniq))
        sel = np.concatenate([members[g] for g in pick])
        out.append(stat(values[sel]))
    out = np.asarray(out)
    return [float(np.percentile(out, 2.5, axis=0)), float(np.percentile(out, 97.5, axis=0))]


def summary(values, groups, n_boot=2000):
    v = np.asarray(values, dtype=np.float64)
    return {"mean": float(v.mean()), "ci95": grouped_bootstrap(v, groups, n_boot=n_boot)}


def complete_family_mask(valid_q):
    """Question-level loop validity (4N,) body-major -> mask keeping only the
    questions of bodies for which the loop ran for all 4 queries (revision 4).
    The rule is symmetric in the slot labels, so the selection cannot depend
    on which statement is the queried one."""
    v = valid_q.view(-1, 4).all(1)
    return v.repeat_interleave(4)
