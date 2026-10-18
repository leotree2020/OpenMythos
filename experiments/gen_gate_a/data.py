"""Load the fixed dev/test sets (verifying the manifest hash) and encode rows."""

import hashlib
import json
import os

import torch

from levels import STMT

HERE = os.path.dirname(os.path.abspath(__file__))
SETS = os.path.join(HERE, "sets")


def encode_rows(rows):
    """[(prompt, answer)] -> x (B, L) bytes of prompt+answer, y (B,) answer byte."""
    x = torch.tensor([list((p + a).encode()) for p, a in rows], dtype=torch.long)
    return x, x[:, -1].clone()


def roots_of(prompt):
    return {ord(v) for _, v in STMT.findall(prompt.split("|")[0]) if v.isdigit()}


def load_set(level, split):
    name = f"{level}_{split}"
    text = open(os.path.join(SETS, f"{name}.jsonl")).read()
    manifest = json.load(open(os.path.join(SETS, "manifest.json")))
    if hashlib.sha256(text.encode()).hexdigest() != manifest[name]["sha256"]:
        raise RuntimeError(f"{name}: fixed set does not match its manifest hash")
    rows = [json.loads(line) for line in text.splitlines()]
    x, y = encode_rows([(r["prompt"], r["answer"]) for r in rows])
    x_rs, y_rs = encode_rows([tuple(r["root_swap"]) for r in rows])
    qs_idx = [i for i, r in enumerate(rows) if r["query_swap"]]
    if qs_idx:
        x_qs, y_qs = encode_rows([tuple(rows[i]["query_swap"]) for i in qs_idx])
    else:
        x_qs = y_qs = None
    return {
        "rows": rows,
        "x": x,
        "y": y,
        "x_rs": x_rs,
        "y_rs": y_rs,
        "qs_idx": torch.tensor(qs_idx, dtype=torch.long),
        "x_qs": x_qs,
        "y_qs": y_qs,
        "roots": [roots_of(r["prompt"]) for r in rows],
        "sha256": manifest[name]["sha256"],
    }
