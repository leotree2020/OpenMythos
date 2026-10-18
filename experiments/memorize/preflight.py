#!/usr/bin/env python3
"""
Pre-training checks for the memorization diagnostic (no training).

1. Fixed data: the 32 set is the first 32 of the 512 set; regenerating gives
   identical token ids and labels (hash); no overlap with the held-out set.
2. Loss position and label mapping: the model input is x[:, :-1], whose last
   token is "?"; the loss target is y = x[:, -1], the answer digit's byte id
   (48-57); the answer never appears in the input after "?"; train and eval
   both compare argmax over the 256-byte vocabulary with that same y.
3. Gradients: one training step on the 32 set for each arm gives finite
   gradients; lists parameters whose gradient is missing or exactly zero
   (for MoE, experts not routed in that batch are expected to be zero).
"""

import json
import os
import sys

import torch
import torch.nn.functional as F

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "basic_learn"))

from fixed_sets import digest, fixed_set, heldout_set, root_candidates  # noqa: E402
from models import build  # noqa: E402


def main():
    rep, fail = {}, []
    x32, y32 = fixed_set(32)
    x512, y512 = fixed_set(512)
    xh, yh = heldout_set()
    rep["hash32"], rep["hash512"] = digest(x32, y32), digest(x512, y512)
    if digest(*fixed_set(32)) != rep["hash32"]:
        fail.append("32 set not reproducible")
    if not (torch.equal(x512[:32], x32) and torch.equal(y512[:32], y32)):
        fail.append("32 set is not the first 32 of the 512 set")
    seen = {bytes(r.tolist()) for r in x512}
    rep["heldout_overlap"] = sum(bytes(r.tolist()) in seen for r in xh)
    if rep["heldout_overlap"]:
        fail.append("held-out overlaps the fixed set")
    rep["unique_prompts_512"] = len(seen)

    inp = x512[:, :-1]
    if not torch.equal(x512[:, -1], y512):
        fail.append("label is not the last token")
    if not bool((inp[:, -1] == ord("?")).all()):
        fail.append("input does not end at '?'")
    if not bool(((y512 >= 48) & (y512 <= 57)).all()):
        fail.append("labels outside digit byte range")
    cands = root_candidates(x512)
    if not all(int(t) in c for t, c in zip(y512, cands)):
        fail.append("answer not among prompt roots")
    rep["answer_digit_hist_512"] = {
        chr(k): int(v) for k, v in zip(*torch.unique(y512, return_counts=True))
    }
    rep["roots_per_prompt_hist_512"] = {}
    for c in cands:
        rep["roots_per_prompt_hist_512"][len(c)] = (
            rep["roots_per_prompt_hist_512"].get(len(c), 0) + 1
        )

    rep["grads"] = {}
    for arm in ("openmythos", "transformer"):
        torch.manual_seed(1)
        m = build(arm, 8)
        logits = m(x32[:, :-1])
        if logits.shape[-1] != 256:
            fail.append(f"{arm}: vocab {logits.shape[-1]}")
        loss = F.cross_entropy(logits[:, -1], y32)
        loss.backward()
        missing, zero, nonfinite = [], [], []
        for n, p in m.named_parameters():
            if p.grad is None:
                missing.append(n)
            elif not torch.isfinite(p.grad).all():
                nonfinite.append(n)
            elif p.grad.abs().sum() == 0:
                zero.append(n)
        total = torch.sqrt(
            sum(p.grad.pow(2).sum() for p in m.parameters() if p.grad is not None)
        ).item()
        rep["grads"][arm] = {
            "initial_loss": loss.item(),
            "grad_norm": total,
            "missing": missing,
            "zero": zero,
            "nonfinite": nonfinite,
        }
        if nonfinite or not total > 0:
            fail.append(f"{arm}: bad gradients")
    rep["failures"] = fail
    with open(os.path.join(HERE, "preflight.json"), "w") as f:
        json.dump(rep, f, indent=1)
    print(json.dumps(rep, indent=1, ensure_ascii=False))
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
