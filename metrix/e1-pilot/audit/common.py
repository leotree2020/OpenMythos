"""Data Auditor helpers (independent; no Executor code)."""
import hashlib, json, random

FACTS_SHA_PROTOCOL = "406c8801c5b69ed235cbe516658ad9ee3e3a8cfe8e4e348a0c1fd7952f2e6b97"
RELATIONS = ["capital", "currency", "founder", "river"]
STRATA = ["natural", "random"]
TRAIN_T = {"capital": "The capital of {E} is {A}.",
           "currency": "The currency used in {E} is the {A}.",
           "founder": "{E} was founded by {A}.",
           "river": "The river that flows through {E} is the {A}."}


def canon(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha(b):
    return hashlib.sha256(b).hexdigest()


def rng_rule(seed, purpose):
    return random.Random(int.from_bytes(hashlib.sha256(f"{seed}:{purpose}".encode("utf-8")).digest()[:8], "big"))


def load_tok(d):
    from transformers import AutoTokenizer
    return AutoTokenizer.from_pretrained(d, local_files_only=True)


def enc(tok, s):
    return tok.encode(s, add_special_tokens=False)
