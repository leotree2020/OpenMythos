"""Pure inherited data-selection fixture helpers; no preparation CLI in this stage.

The operator reuses the frozen inputs.json byte-for-byte; these functions exist
only to preserve development checks for the original split rules.
"""
from __future__ import annotations
import argparse
import datetime
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import struct
import sys
import traceback

PINS = {
    "train": "49280f3dd993cbdfd322186194133d5d1935f81e1c91064c239f2a70ebb02701",
    "validation": "a10eb5a42c4264c45dd38bfef4da6a74ddef5fc22cb419e1a89d54c4cc6d748f",
    "tokenizer": "e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77",
}
SPACE = "bookish-pancake-vwqx7rr9x5w3wxjr"
SELECTION = "first16 by ascending article identity SHA; one first nonempty intro row per conservatively accepted title; >=129 tokens; no cross-row concatenation"


class Stop(Exception):
    def __init__(self, status, reason):
        super().__init__(reason)
        self.status = status


def canonical(x):
    return json.dumps(x, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()


def sha(x):
    return hashlib.sha256(x).hexdigest()


def info(path):
    b = Path(path).read_bytes()
    return {"bytes": len(b), "sha256": sha(b)}


def save(path, x):
    with Path(path).open("x", encoding="utf-8", newline="\n") as f:
        json.dump(x, f, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
        f.write("\n")


def require(okay, reason, status="FAIL"):
    if not okay:
        raise Stop(status, reason)


def normalized_title(title):
    return " ".join(re.findall(r"[a-z0-9]+", title.casefold()))


def prose_like(s):
    s = s.strip()
    nonspace = [c for c in s if not c.isspace()]
    return (len(nonspace) >= 120 and not s.startswith(("=", "*", "|", "{", "}"))
            and "=" not in s and sum(c.isalpha() for c in nonspace) / len(nonspace) >= .65
            and any(c in s for c in ".?!"))


def collect(rows, split, corpus_sha, tokenize):
    """Conservative source grammar; ambiguous regions never become sample text."""
    require(isinstance(rows, list) and all(isinstance(s, str) for s in rows), "Text rows required")
    candidates, eligible = [], []
    for i, raw in enumerate(rows):
        s = raw.strip()
        if not s or not (s.startswith("=") or s.endswith("=")):
            continue
        m = re.fullmatch(r"= ([A-Za-z0-9][A-Za-z0-9 '\"(),.:;!?&/\-]*) =", s)
        title = m.group(1).strip() if m else None
        around_blank = (i == 0 or not rows[i - 1].strip()) and (i + 1 == len(rows) or not rows[i + 1].strip())
        letters_ok = bool(title and sum(c.isalpha() for c in title) >= 3
                          and sum(c.isalpha() for c in title) / max(1, len(title.replace(" ", ""))) >= .5)
        candidate = {"row": i, "row_sha256": sha(raw.encode()), "title_candidate": s,
                     "blank_neighbours": around_blank, "decision": "EXCLUDE_AMBIGUOUS_OR_NESTED"}
        candidates.append(candidate)
        if not (m and around_blank and letters_ok):
            continue
        j = i + 1
        while j < len(rows) and not rows[j].strip():
            j += 1
        candidate.update(title=title, normalized_title=normalized_title(title), intro_row=j if j < len(rows) else None)
        if j >= len(rows) or not prose_like(rows[j]):
            candidate["decision"] = "EXCLUDE_FIRST_ROW_NOT_PROSE"
            continue
        tokens = tokenize(rows[j])
        require(isinstance(tokens, list) and all(type(t) is int and 0 <= t < 32768 for t in tokens), "Tokenizer ID contract")
        candidate.update(intro_sha256=sha(rows[j].encode()), intro_token_count=len(tokens), intro_excerpt=rows[j][:220])
        if len(tokens) < 129:
            candidate["decision"] = "EXCLUDE_FIRST_ROW_SHORT"
            continue
        candidate["decision"] = "ELIGIBLE"
        identity = {"split": split, "corpus_sha256": corpus_sha, "heading_row": i,
                    "title": title, "body_row": j, "text_sha256": sha(rows[j].encode())}
        sample = {"id": sha(canonical(identity)), **identity, "normalized_title": normalized_title(title),
                  "full_row_token_count": len(tokens), "tokens": tokens[:129],
                  "window_sha256": sha(struct.pack("<129q", *tokens[:129])),
                  "input_sha256": sha(struct.pack("<128q", *tokens[:128])),
                  "scored_targets_sha256": sha(struct.pack("<64q", *tokens[65:129]))}
        candidate["id"] = sample["id"]
        eligible.append(sample)
    return sorted(eligible, key=lambda x: x["id"]), candidates


def ngrams(tokens, n=32):
    return {tuple(tokens[i:i+n]) for i in range(len(tokens) - n + 1)}


def choose(train, validation, count=16):
    require(type(count) is int and count > 0, "Positive selection count")
    # Exclude overlapping titles in the entire eligible inventories before selection,
    # rather than searching for a favorable split after seeing model results.
    titles_a = {s["normalized_title"] for s in train}
    titles_b = {s["normalized_title"] for s in validation}
    shared_titles = titles_a & titles_b
    ta = [s for s in train if s["normalized_title"] not in shared_titles]
    va = [s for s in validation if s["normalized_title"] not in shared_titles]
    require(len(ta) >= count and len(va) >= count, "Insufficient unambiguous disjoint source rows", "BLOCKED")
    a, b = ta[:count], va[:count]
    for group in (a, b):
        for key in ("id", "normalized_title", "text_sha256", "window_sha256"):
            require(len({s[key] for s in group}) == count, "Duplicate selected identity: " + key)
    require(not ({s["text_sha256"] for s in a} & {s["text_sha256"] for s in b}), "Train/eval text overlap")
    train_ngrams = set().union(*(ngrams(s["tokens"]) for s in a))
    val_ngrams = set().union(*(ngrams(s["tokens"]) for s in b))
    require(not train_ngrams & val_ngrams, "Train/eval exact32-token overlap")
    return a, b, sorted(shared_titles)



if __name__ == "__main__":
    raise SystemExit("BLOCKED: this stage reuses frozen data; preparation is not authorized")
