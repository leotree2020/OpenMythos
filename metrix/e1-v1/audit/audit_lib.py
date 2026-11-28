# data-auditor, E1-V1 round 1. Independent helper library written from the text of
# metrix/e1-v1/METRIX_E1V1_PROTOCOL.md, its four JSON manifests and the Pilot protocol
# v1.1 (sections 0, 2, 3). No Executor code is imported, called or copied.
import hashlib
import json
import os
import random
import sys

REPO = "/home/user/OpenMythos"
V1 = REPO + "/metrix/e1-v1"
PILOT = REPO + "/metrix/e1-pilot"
AUDIT = V1 + "/audit"
TMP = AUDIT + "/tmpdata"
S = "/tmp/claude-0/-home-user/1e17bf44-a265-5c2d-b2f8-f9d45e7efe94/scratchpad"
INPUTS = S + "/inputs"
QWEN_DIR = INPUTS + "/qwen"
ANCHOR_PARQUET = INPUTS + "/anchor_source/data/sample-100BT/train/shard_00000.parquet"
PARCAE_TOK = INPUTS + "/parcae/tokenizer.json"
EVAL_SETS = REPO + "/research/mini_mythos/stage1/results/r1/eval_sets.jsonl"
MMLU_DIR = INPUTS + "/d2/cais__mmlu"
ARC_DIR = INPUTS + "/d2/allenai__ai2_arc"

RELATIONS = ["capital", "currency", "founder", "river"]
STRATA = ["natural", "random"]
STRAT_SHORT = {"natural": "nat", "random": "rnd"}


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def canon(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def sha_text(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def canon_sha(obj):
    return sha_text(canon(obj))


def jsonl_text(rows):
    return "".join(canon(r) + "\n" for r in rows)


def jsonl_sha(rows):
    return sha_text(jsonl_text(rows))


def rng_rule(seed, purpose):
    d = hashlib.sha256(f"{seed}:{purpose}".encode("utf-8")).digest()
    return random.Random(int.from_bytes(d[:8], "big"))


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_jsonl(path, rows):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(jsonl_text(rows))


def read_jsonl(path):
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def setup_env():
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    os.environ.setdefault("HF_HOME", TMP + "/hf_home")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")


def load_qwen_tokenizer(expected_sha):
    """Check the 4 tokenizer files against the manifest, then load the tokenizer only."""
    setup_env()
    for name, exp in expected_sha.items():
        got = file_sha256(os.path.join(QWEN_DIR, name))
        print(f"input qwen/{name} sha256 {got} manifest {exp} equal {got == exp}")
        if got != exp:
            print("ABORT tokenizer file hash mismatch")
            sys.exit(2)
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(QWEN_DIR)
    return tok


def within_edit1(a, b):
    """Levenshtein distance of a and b is <= 1."""
    la, lb = len(a), len(b)
    if abs(la - lb) > 1:
        return False
    if la == lb:
        diff = 0
        for x, y in zip(a, b):
            if x != y:
                diff += 1
                if diff > 1:
                    return False
        return True
    if la > lb:
        a, b = b, a
        la, lb = lb, la
    # b is longer by one: a must equal b with one character deleted
    i = 0
    while i < la and a[i] == b[i]:
        i += 1
    return a[i:] == b[i + 1:]


def hamming_le1(a, b):
    if len(a) != len(b):
        return False
    diff = 0
    for x, y in zip(a, b):
        if x != y:
            diff += 1
            if diff > 1:
                return False
    return True


def letter_block(s):
    return s.split("-", 1)[0] if "-" in s else s


def reject_natural(s, accepted):
    ls = s.lower()
    for a in accepted:
        la = a.lower()
        if ls == la:
            return True
        if s[:4] == a[:4]:
            return True
        if within_edit1(ls, la):
            return True
    return False


def reject_random(s, accepted):
    lb = letter_block(s)
    for a in accepted:
        if s == a:
            return True
        if lb == letter_block(a):
            return True
        if len(a) == len(s) and hamming_le1(s, a):
            return True
    return False


def reject_reason(s, stratum, accepted):
    """Which reject_if rule (if any) fires against a list of strings; used by L7b."""
    hits = []
    for a in accepted:
        if stratum == "natural":
            if s.lower() == a.lower():
                hits.append(("lower_equal", a))
            elif s[:4] == a[:4]:
                hits.append(("first4", a))
            elif within_edit1(s.lower(), a.lower()):
                hits.append(("edit1", a))
        else:
            if s == a:
                hits.append(("equal", a))
            elif letter_block(s) == letter_block(a):
                hits.append(("letter_block", a))
            elif len(a) == len(s) and hamming_le1(s, a):
                hits.append(("hamming1", a))
    return hits


class NameGen:
    """Protocol 2.2 (Pilot), with the V1 changes (seed, count 40, preseed)."""

    ONSETS = ["b", "d", "f", "g", "k", "l", "m", "n", "p", "r", "s", "t", "v", "z",
              "br", "dr", "kr", "tr", "sh", "th"]
    NUCLEI = ["a", "e", "i", "o", "u", "ae", "ia", "ou"]
    CODAS = ["", "", "n", "r", "l", "s", "th", "nd"]
    LETTERS = "BCDFGHJKLMNPQRSTVWXZ"
    DIGITS = "23456789"

    def __init__(self, tok, anchor_lower_joined, seed, per_role, preseed=()):
        self.tok = tok
        self.anchor = anchor_lower_joined
        self.seed = seed
        self.per_role = per_role
        self.accepted = list(preseed)
        self.log = []

    def enc_len(self, s):
        return len(self.tok.encode(s, add_special_tokens=False))

    def draw(self, rng, stratum):
        if stratum == "natural":
            n = 2 if rng.random() < 0.5 else 3
            s = ""
            for _ in range(n):
                s += rng.choice(self.ONSETS) + rng.choice(self.NUCLEI) + rng.choice(self.CODAS)
            return s[0].upper() + s[1:]
        u = rng.random()
        L = 3 if u < 0.25 else 4 if u < 0.75 else 5
        s = "".join(rng.choice(self.LETTERS) for _ in range(L))
        s += "-" + "".join(rng.choice(self.DIGITS) for _ in range(2))
        return s

    def form_ok(self, s, stratum):
        if stratum == "natural":
            return 4 <= len(s) <= 10 and self.enc_len(" " + s) > 1
        return 6 <= len(s) <= 8

    def conflict(self, s, stratum):
        if stratum == "natural":
            return reject_natural(s, self.accepted)
        return reject_random(s, self.accepted)

    def in_anchor(self, s):
        return s.lower() in self.anchor

    def pair(self, s):
        return (self.enc_len(" " + s), self.enc_len(s))

    def cell(self, relation, stratum):
        purpose_e = f"names:{relation}:{stratum}:entity"
        purpose_a = f"names:{relation}:{stratum}:answer"
        # entities
        r = rng_rule(self.seed, purpose_e)
        ents, ed = [], 0
        while len(ents) < self.per_role:
            ed += 1
            if ed > 20000:
                raise RuntimeError("IMPLEMENTATION_FAIL entity stream exhausted")
            s = self.draw(r, stratum)
            if not self.form_ok(s, stratum):
                continue
            if self.conflict(s, stratum) or self.in_anchor(s):
                continue
            ents.append(s)
            self.accepted.append(s)
        # answer survey
        r = rng_rule(self.seed, purpose_a)
        counts, k = {}, 0
        while k < 400:
            s = self.draw(r, stratum)
            if not self.form_ok(s, stratum):
                continue
            k += 1
            p = self.pair(s)
            counts[p] = counts.get(p, 0) + 1
        best = max(counts.values())
        target = min(p for p, c in counts.items() if c == best)
        # answer accept, restarted stream
        r = rng_rule(self.seed, purpose_a)
        ans, ad = [], 0
        while len(ans) < self.per_role:
            ad += 1
            if ad > 20000:
                raise RuntimeError("IMPLEMENTATION_FAIL answer stream exhausted")
            s = self.draw(r, stratum)
            if not self.form_ok(s, stratum):
                continue
            if self.pair(s) != target:
                continue
            if self.conflict(s, stratum) or self.in_anchor(s):
                continue
            ans.append(s)
            self.accepted.append(s)
        self.log.append((relation, stratum, ed, ad, list(target), dict(sorted(counts.items()))))
        return ents, ans


def build_facts(tok, anchor_joined, seed, n_learned, n_unread, prefix, preseed=()):
    g = NameGen(tok, anchor_joined, seed, n_learned + n_unread, preseed)
    facts = []
    for rel in RELATIONS:
        for st in STRATA:
            ents, ans = g.cell(rel, st)
            for i in range(n_learned + n_unread):
                if i < n_learned:
                    fid = f"{prefix}-L-{rel}-{STRAT_SHORT[st]}-{i + 1:02d}"
                    exp = "learned"
                else:
                    fid = f"{prefix}-U-{rel}-{STRAT_SHORT[st]}-{i - n_learned + 1:02d}"
                    exp = "unread"
                facts.append({"fact_id": fid, "exposure": exp, "relation": rel, "stratum": st,
                              "entity": ents[i], "answer": ans[i]})
    return facts, g


def templates_by(templates):
    out = {}
    for t in templates:
        out.setdefault((t["relation"], t["kind"]), []).append(t)
    for k in out:
        out[k].sort(key=lambda t: t["template_id"])
    return out


def inst(text, e=None, a=None):
    s = text
    if e is not None:
        s = s.replace("{E}", e)
    if a is not None:
        s = s.replace("{A}", a)
    return s


def build_corpora(facts, templates, data_seed, cand_seed, n_learned):
    tb = templates_by(templates)
    learned = [f for f in facts if f["exposure"] == "learned"]
    train_F = []
    for f in learned:
        t = tb[(f["relation"], "TRAIN")][0]
        train_F.append({"fact_id": f["fact_id"], "template_id": t["template_id"],
                        "text": inst(t["text"], f["entity"], f["answer"])})
    train_Y = []
    for f in learned:
        te = tb[(f["relation"], "Y_ENTITY")][0]
        ta = tb[(f["relation"], "Y_ANSWER")][0]
        train_Y.append({"fact_id": f["fact_id"], "template_id": te["template_id"], "kind": "Y_ENTITY",
                        "text": inst(te["text"], e=f["entity"])})
        train_Y.append({"fact_id": f["fact_id"], "template_id": ta["template_id"], "kind": "Y_ANSWER",
                        "text": inst(ta["text"], a=f["answer"])})
    dev_qa = []
    for f in facts:
        for t in tb[(f["relation"], "DEV")]:
            dev_qa.append({"fact_id": f["fact_id"], "template_id": t["template_id"],
                           "question": inst(t["text"], e=f["entity"])})
    train_S, s_attempts = [], {}
    for rel in RELATIONS:
        for st in STRATA:
            cell = [f for f in learned if f["relation"] == rel and f["stratum"] == st]
            assert len(cell) == n_learned
            r = rng_rule(data_seed, f"s-permutation:{rel}:{st}")
            att = 0
            while True:
                att += 1
                p = list(range(n_learned))
                r.shuffle(p)
                if all(p[i] != i for i in range(n_learned)):
                    break
            s_attempts[f"{rel}/{st}"] = att
            t = tb[(rel, "TRAIN")][0]
            for i in range(n_learned):
                train_S.append({"fact_id": cell[i]["fact_id"], "answer_fact_id": cell[p[i]]["fact_id"],
                                "text": inst(t["text"], cell[i]["entity"], cell[p[i]]["answer"])})
    cands, pools = {}, {}
    for f in facts:
        pool = [g["answer"] for g in facts if g["relation"] == f["relation"] and g["stratum"] == f["stratum"]
                and g["exposure"] == f["exposure"] and g["fact_id"] != f["fact_id"]]
        pools[f["fact_id"]] = len(pool)
        if len(pool) < 4:
            raise RuntimeError("IMPLEMENTATION_FAIL pool < 4")
        r = rng_rule(cand_seed, f"cand:{f['fact_id']}")
        d = r.sample(pool, 3)
        c = [f["answer"]] + d
        r.shuffle(c)
        cands[f["fact_id"]] = c
    return train_F, train_S, train_Y, dev_qa, cands, pools, s_attempts


def normalize_template(text):
    s = text.replace("{E}", "<ENTITY>").replace("{A}", "<ANSWER>").lower()
    s = "".join(ch if (("a" <= ch <= "z") or ("0" <= ch <= "9") or ch in "<> ") else " " for ch in s)
    return " ".join(s.split())


def ascii_alnum(ch):
    return ("a" <= ch <= "z") or ("A" <= ch <= "Z") or ("0" <= ch <= "9")


def whole_word_hits(text, strings_lower):
    """L8: strings (lowercased) occurring in text case-insensitively with no ASCII letter or digit
    immediately before or after (or at a text boundary). Returns the list of hit strings."""
    t = text.lower()
    hits = []
    for s in strings_lower:
        start = 0
        while True:
            i = t.find(s, start)
            if i < 0:
                break
            before_ok = i == 0 or not ascii_alnum(t[i - 1])
            j = i + len(s)
            after_ok = j == len(t) or not ascii_alnum(t[j])
            if before_ok and after_ok:
                hits.append(s)
                break
            start = i + 1
    return hits


def word_ngrams(text, n=13):
    w = text.split()
    return {tuple(w[i:i + n]) for i in range(len(w) - n + 1)}


def id_ngrams(ids, n=13):
    return {tuple(ids[i:i + n]) for i in range(len(ids) - n + 1)}
