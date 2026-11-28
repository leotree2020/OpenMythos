# data-auditor, E1-V1 freeze audit (D2 of tasks/E1V1_FREEZE_OWNER_MESSAGE.md): helper library.
# Written by the data-auditor from the text of metrix/e1-v1/METRIX_E1V1_PROTOCOL.md, its four JSON
# manifests and the Pilot protocol v1.1; adapted from the auditor's own earlier audit/audit_lib.py.
# No Executor code (reports/authoring/*.py, reports/freeze/*) is imported, called or copied.
import hashlib
import json
import os
import random
import re
import subprocess

REPO = "/home/user/OpenMythos"
V1 = REPO + "/metrix/e1-v1"
AUDIT = V1 + "/audit"
TMP = AUDIT + "/tmp_freeze"
INPUTS = TMP + "/inputs"
DATA = TMP + "/data"
FREEZE = "9a19e70e1bc16130368caa00bd1bf6fbc126bc8c"
BASE = "bc03348ad8b2390ac3df452631d63b8bfe66ad67"
FIVE = ["metrix/e1-v1/METRIX_E1V1_PROTOCOL.md", "metrix/e1-v1/DATA_MANIFEST.json",
        "metrix/e1-v1/SPLIT_MANIFEST.json", "metrix/e1-v1/DOSE_SPACE.json",
        "metrix/e1-v1/DAMAGE_MANIFEST.json"]
EVAL_SETS_REL = "research/mini_mythos/stage1/results/r1/eval_sets.jsonl"
# protocol section 0, byte regex for the row prefix of eval_sets.jsonl
ROW_PREFIX = re.compile(rb'^\{"domain": "([^"\\]*)", "split": "([^"\\]*)", ')

RELATIONS = ["capital", "currency", "founder", "river"]
STRATA = ["natural", "random"]
STRAT_SHORT = {"natural": "nat", "random": "rnd"}

HEX64 = re.compile(r"(?<![0-9A-Fa-f])[0-9A-Fa-f]{64}(?![0-9A-Fa-f])")
HEX40 = re.compile(r"(?<![0-9A-Fa-f])[0-9A-Fa-f]{40}(?![0-9A-Fa-f])")


# ---------------------------------------------------------------- git
def git(*args):
    r = subprocess.run(["git", "-C", REPO] + list(args), capture_output=True)
    if r.returncode != 0:
        raise RuntimeError("git %s failed: %s" % (" ".join(args), r.stderr.decode()))
    return r.stdout


def git_blob(commit, path):
    return git("cat-file", "blob", f"{commit}:{path}")


def git_json(commit, path):
    return json.loads(git_blob(commit, path).decode("utf-8"))


# ---------------------------------------------------------------- hashing
def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def git_blob_sha1(b):
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()


def canon(obj):
    # DATA_MANIFEST.json: hashing.serialization
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def sha_text(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def canon_sha(obj):
    return sha_text(canon(obj))


def jsonl_text(rows):
    # hashing.jsonl: one canonical object per line, joined by '\n', one final '\n'
    return "".join(canon(r) + "\n" for r in rows)


def jsonl_sha(rows):
    return sha_text(jsonl_text(rows))


def write_jsonl(path, rows):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(jsonl_text(rows))


def read_jsonl(path):
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def file_canonical_sha256_jsonl(path):
    """canonical_sha256 of a JSONL file: parse every line, re-serialize canonically."""
    return jsonl_sha(read_jsonl(path))


def file_canonical_sha256_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return canon_sha(json.load(f))


def rng_rule(seed, purpose):
    d = hashlib.sha256(f"{seed}:{purpose}".encode("utf-8")).digest()
    return random.Random(int.from_bytes(d[:8], "big"))


# ---------------------------------------------------------------- inputs
def local_input(repo, path):
    return os.path.join(INPUTS, repo.replace("/", "__"), path)


QWEN_REPO = "Qwen/Qwen3-1.7B"


def qwen_dir():
    return os.path.join(INPUTS, QWEN_REPO.replace("/", "__"))


def setup_env():
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_HOME"] = TMP + "/hf_home"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"


def load_qwen_tokenizer(files_sha256):
    """Check the 4 tokenizer files against the manifest, then load the tokenizer only (no weights)."""
    setup_env()
    for name, exp in files_sha256.items():
        got = file_sha256(os.path.join(qwen_dir(), name))
        print(f"  tokenizer file {name}: sha256 {got} | manifest {exp} | equal {got == exp}")
        if got != exp:
            raise SystemExit("ABORT tokenizer file hash mismatch")
    from transformers import AutoTokenizer
    return AutoTokenizer.from_pretrained(qwen_dir())


# ---------------------------------------------------------------- name generation (Pilot 2.2, V1 2.2)
def within_edit1(a, b):
    la, lb = len(a), len(b)
    if abs(la - lb) > 1:
        return False
    if la == lb:
        return sum(1 for x, y in zip(a, b) if x != y) <= 1
    if la > lb:
        a, b, la, lb = b, a, lb, la
    i = 0
    while i < la and a[i] == b[i]:
        i += 1
    return a[i:] == b[i + 1:]


def hamming_le1(a, b):
    return len(a) == len(b) and sum(1 for x, y in zip(a, b) if x != y) <= 1


def letter_block(s):
    return s.split("-", 1)[0] if "-" in s else s


def reject(s, stratum, accepted):
    if stratum == "natural":
        ls = s.lower()
        for a in accepted:
            la = a.lower()
            if ls == la or s[:4] == a[:4] or within_edit1(ls, la):
                return True
        return False
    lb = letter_block(s)
    for a in accepted:
        if s == a or lb == letter_block(a) or hamming_le1(s, a):
            return True
    return False


class Names:
    def __init__(self, tok, ng, anchor_lower_joined, seed, per_role, preseed=()):
        self.tok = tok
        self.ng = ng  # DATA_MANIFEST name_generation
        self.anchor = anchor_lower_joined
        self.seed = seed
        self.per_role = per_role
        self.accepted = list(preseed)
        self.log = []

    def n_ids(self, s):
        return len(self.tok.encode(s, add_special_tokens=False))

    def draw(self, r, stratum):
        if stratum == "natural":
            nat = self.ng["natural"]
            n = 2 if r.random() < 0.5 else 3
            s = "".join(r.choice(nat["onsets"]) + r.choice(nat["nuclei"]) + r.choice(nat["codas"]) for _ in range(n))
            return s[0].upper() + s[1:]
        rnd = self.ng["random"]
        u = r.random()
        L = 3 if u < 0.25 else 4 if u < 0.75 else 5
        s = "".join(r.choice(rnd["letters"]) for _ in range(L))
        return s + "-" + "".join(r.choice(rnd["digits"]) for _ in range(2))

    def form_ok(self, s, stratum):
        lo, hi = self.ng[stratum]["length_chars"]
        if not (lo <= len(s) <= hi):
            return False
        if stratum == "natural":
            return self.n_ids(" " + s) > 1
        return True

    def ok(self, s, stratum):
        return not reject(s, stratum, self.accepted) and s.lower() not in self.anchor

    def cell(self, rel, st):
        r = rng_rule(self.seed, f"names:{rel}:{st}:entity")
        ents, ed = [], 0
        while len(ents) < self.per_role:
            ed += 1
            if ed > 20000:
                raise RuntimeError("IMPLEMENTATION_FAIL entity stream")
            s = self.draw(r, st)
            if self.form_ok(s, st) and self.ok(s, st):
                ents.append(s)
                self.accepted.append(s)
        r = rng_rule(self.seed, f"names:{rel}:{st}:answer")
        counts, k = {}, 0
        while k < 400:
            s = self.draw(r, st)
            if not self.form_ok(s, st):
                continue
            k += 1
            p = (self.n_ids(" " + s), self.n_ids(s))
            counts[p] = counts.get(p, 0) + 1
        best = max(counts.values())
        target = min(p for p, c in counts.items() if c == best)
        r = rng_rule(self.seed, f"names:{rel}:{st}:answer")
        ans, ad = [], 0
        while len(ans) < self.per_role:
            ad += 1
            if ad > 20000:
                raise RuntimeError("IMPLEMENTATION_FAIL answer stream")
            s = self.draw(r, st)
            if not self.form_ok(s, st):
                continue
            if (self.n_ids(" " + s), self.n_ids(s)) != target:
                continue
            if self.ok(s, st):
                ans.append(s)
                self.accepted.append(s)
        self.log.append((rel, st, ed, ad, target))
        return ents, ans


def build_facts(tok, ng, anchor_joined, seed, n_learned, n_unread, prefix, preseed=()):
    g = Names(tok, ng, anchor_joined, seed, n_learned + n_unread, preseed)
    facts = []
    for rel in RELATIONS:
        for st in STRATA:
            ents, ans = g.cell(rel, st)
            for i in range(n_learned + n_unread):
                if i < n_learned:
                    fid, exp = f"{prefix}-L-{rel}-{STRAT_SHORT[st]}-{i + 1:02d}", "learned"
                else:
                    fid, exp = f"{prefix}-U-{rel}-{STRAT_SHORT[st]}-{i - n_learned + 1:02d}", "unread"
                facts.append({"fact_id": fid, "exposure": exp, "relation": rel, "stratum": st,
                              "entity": ents[i], "answer": ans[i]})
    return facts, g


# ---------------------------------------------------------------- templates and corpora
def normalize_template(text):
    s = text.replace("{E}", "<ENTITY>").replace("{A}", "<ANSWER>").lower()
    s = "".join(ch if (("a" <= ch <= "z") or ("0" <= ch <= "9") or ch in "<> ") else " " for ch in s)
    return " ".join(s.split())


def tmpl_index(templates):
    out = {}
    for t in templates:
        out.setdefault((t["relation"], t["kind"]), []).append(t)
    for k in out:
        out[k].sort(key=lambda t: t["template_id"])
    return out


def fill(text, e=None, a=None):
    if e is not None:
        text = text.replace("{E}", e)
    if a is not None:
        text = text.replace("{A}", a)
    return text


def build_corpora(facts, templates, data_seed, cand_seed, n_learned):
    tb = tmpl_index(templates)
    learned = [f for f in facts if f["exposure"] == "learned"]
    F = [{"fact_id": f["fact_id"], "template_id": tb[(f["relation"], "TRAIN")][0]["template_id"],
          "text": fill(tb[(f["relation"], "TRAIN")][0]["text"], f["entity"], f["answer"])} for f in learned]
    Y = []
    for f in learned:
        te, ta = tb[(f["relation"], "Y_ENTITY")][0], tb[(f["relation"], "Y_ANSWER")][0]
        Y.append({"fact_id": f["fact_id"], "template_id": te["template_id"], "kind": "Y_ENTITY",
                  "text": fill(te["text"], e=f["entity"])})
        Y.append({"fact_id": f["fact_id"], "template_id": ta["template_id"], "kind": "Y_ANSWER",
                  "text": fill(ta["text"], a=f["answer"])})
    Q = [{"fact_id": f["fact_id"], "template_id": t["template_id"], "question": fill(t["text"], e=f["entity"])}
         for f in facts for t in tb[(f["relation"], "DEV")]]
    S, att = [], {}
    for rel in RELATIONS:
        for st in STRATA:
            cell = [f for f in learned if f["relation"] == rel and f["stratum"] == st]
            assert len(cell) == n_learned
            r = rng_rule(data_seed, f"s-permutation:{rel}:{st}")
            n = 0
            while True:
                n += 1
                p = list(range(n_learned))
                r.shuffle(p)
                if all(p[i] != i for i in range(n_learned)):
                    break
            att[f"{rel}/{st}"] = n
            t = tb[(rel, "TRAIN")][0]
            for i in range(n_learned):
                S.append({"fact_id": cell[i]["fact_id"], "answer_fact_id": cell[p[i]]["fact_id"],
                          "text": fill(t["text"], cell[i]["entity"], cell[p[i]]["answer"])})
    C, pools = {}, {}
    for f in facts:
        pool = [g["answer"] for g in facts if g["relation"] == f["relation"] and g["stratum"] == f["stratum"]
                and g["exposure"] == f["exposure"] and g["fact_id"] != f["fact_id"]]
        pools[f["fact_id"]] = len(pool)
        if len(pool) < 4:
            raise RuntimeError("IMPLEMENTATION_FAIL pool < 4")
        r = rng_rule(cand_seed, f"cand:{f['fact_id']}")
        c = [f["answer"]] + r.sample(pool, 3)
        r.shuffle(c)
        C[f["fact_id"]] = c
    return F, S, Y, Q, C, pools, att


# ---------------------------------------------------------------- leakage helpers (L6, L8)
def _alnum(ch):
    return ("a" <= ch <= "z") or ("A" <= ch <= "Z") or ("0" <= ch <= "9")


def l8_hit(text, strings_lower):
    t = text.lower()
    for s in strings_lower:
        start = 0
        while True:
            i = t.find(s, start)
            if i < 0:
                break
            j = i + len(s)
            if (i == 0 or not _alnum(t[i - 1])) and (j == len(t) or not _alnum(t[j])):
                return True
            start = i + 1
    return False


def word13(text):
    w = text.split()
    return {tuple(w[i:i + 13]) for i in range(len(w) - 12)}


# ---------------------------------------------------------------- hex scanning
def hexes(s):
    return HEX64.findall(s), HEX40.findall(s)


def walk_json(obj, path=""):
    """Yield (path, kind, value) for every key and string value; kind 'key' or 'value'."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}.{k}" if path else k
            yield (p, "key", k)
            yield from walk_json(v, p)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_json(v, f"{path}[{i}]")
    elif isinstance(obj, str):
        yield (path, "value", obj)
