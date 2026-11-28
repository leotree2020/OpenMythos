#!/usr/bin/env python3
"""E1-V1 protocol authoring: reference construction of the non-TEST data rules of METRIX_E1V1_PROTOCOL.md and the
authoring-time checks (protocol sections 2, 3 and 7). CPU only; tokenizer only, no model weights (torch is not even
installed in the authoring environment). Generated data are written to --out (a session scratch directory, NOT the
repository); only hashes, counts and statistics are printed. Prints a final "RESULT: PASS" or "RESULT: FAIL".

TEST rule: no TEST row of any source is decoded or used for a computation. eval_sets.jsonl rows are matched on the
raw bytes of the row prefix (domain and split fields) and only dev rows are decoded (the Pilot stage B method); for the
TEST sources of D2 only the parquet footer (row count) is read.

  python -I v1_data_check.py --qwen DIR --anchor-parquet FILE --parcae-tokenizer FILE --eval-sets FILE \
      --pilot-split-manifest FILE --mmlu-validation FILE --mmlu-test FILE --arc-dir DIR --out DIR
"""
import argparse
import collections
import hashlib
import itertools
import json
import random
import re
import statistics
import sys
from pathlib import Path

# ------------------------------------------------------------------------------------------- frozen constants
PILOT_DATA_SEED = 20261110
PILOT_FACTS_SHA = "406c8801c5b69ed235cbe516658ad9ee3e3a8cfe8e4e348a0c1fd7952f2e6b97"
ANCHOR_TEXTS_SHA = "8828bc4fcc5a3552778839f97909f072050431dd6f74dd08ef47602da11b2408"
TEMPLATE_SET_SHA = "2b52411326c218e9c51d947b2f4e0d77b0cdd5d6237f9ce25b57a872c48ce28f"

DATA_SEED = 20261128          # E1-V1 (protocol section 0)
CANDIDATE_SEED = 20261129
RELATIONS = ["capital", "currency", "founder", "river"]
STRATA = ["natural", "random"]
SHORT = {"natural": "nat", "random": "rnd"}
NATURAL = {"onsets": ["b", "d", "f", "g", "k", "l", "m", "n", "p", "r", "s", "t", "v", "z", "br", "dr", "kr", "tr", "sh", "th"],
           "nuclei": ["a", "e", "i", "o", "u", "ae", "ia", "ou"], "codas": ["", "", "n", "r", "l", "s", "th", "nd"],
           "length": (4, 10)}
RANDOM_ = {"letters": "BCDFGHJKLMNPQRSTVWXZ", "digits": "23456789", "length": (6, 8)}
MAX_DRAWS, SURVEY = 20000, 400
ANSWER_PREFIX = "The answer is"
D1_DOMAINS = ["books", "c4", "fineweb", "wikitext"]
D1_MAX_TOKENS = 256
D1_TEST_SKIP_FIRST = 25       # the Pilot TEST windows (first 25 test rows per domain) are not reused
D1_PER_DOMAIN = 100
D2_N = 800                    # D2 items per split (DEV and TEST)
D2_INSTRUCTION = "Answer the following multiple choice question with the letter of the correct option."
LETTERS = ["A", "B", "C", "D"]
NGRAM_L6 = 13

FAIL = []


def check(name, ok, detail=""):
    print("CHECK %-58s %s %s" % (name, "ok" if ok else "FAIL", detail))
    if not ok:
        FAIL.append(name)


def rng_rule(seed, purpose):
    return random.Random(int.from_bytes(hashlib.sha256(("%s:%s" % (seed, purpose)).encode("utf-8")).digest()[:8], "big"))


def canonical(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha(b):
    return hashlib.sha256(b).hexdigest()


def jsonl_bytes(rows):
    return b"".join(canonical(r) + b"\n" for r in rows)


def write(out, name, data):
    (out / name).write_bytes(data)
    return sha(data)


# ------------------------------------------------------------------------------------------- names (section 2.2)
def lev_le1(a, b):
    if a == b:
        return True
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) <= 1
    if len(a) > len(b):
        a, b = b, a
    i = 0
    while i < len(a) and a[i] == b[i]:
        i += 1
    return a[i:] == b[i + 1:]


def clash(s, stratum, accepted):
    if stratum == "natural":
        low = s.lower()
        return any(a.lower() == low or a[:4] == s[:4] or lev_le1(a.lower(), low) for a in accepted)
    block = s.split("-")[0]
    return any(a == s or a.split("-")[0] == block or (len(a) == len(s) and sum(x != y for x, y in zip(a, s)) <= 1)
               for a in accepted)


class Names:
    def __init__(self, tok, anchor_texts):
        self.tok = tok
        self.anchor_low = [t.lower() for t in anchor_texts]

    def ids(self, text):
        return self.tok.encode(text, add_special_tokens=False)

    @staticmethod
    def draw(r, stratum):
        if stratum == "natural":
            n = 2 if r.random() < 0.5 else 3
            s = "".join(r.choice(NATURAL["onsets"]) + r.choice(NATURAL["nuclei"]) + r.choice(NATURAL["codas"]) for _ in range(n))
            return s[0].upper() + s[1:]
        u = r.random()
        L = 3 if u < 0.25 else (4 if u < 0.75 else 5)
        return "".join(r.choice(RANDOM_["letters"]) for _ in range(L)) + "-" + "".join(r.choice(RANDOM_["digits"]) for _ in range(2))

    def form_ok(self, s, stratum):
        lo, hi = NATURAL["length"] if stratum == "natural" else RANDOM_["length"]
        if not lo <= len(s) <= hi:
            return False
        return stratum != "natural" or len(self.ids(" " + s)) > 1

    def in_anchor(self, s):
        low = s.lower()
        return any(low in t for t in self.anchor_low)

    def pair(self, s):
        return (len(self.ids(" " + s)), len(self.ids(s)))

    def build(self, seed, n_learned, n_unread, prefix, preseed=()):
        """preseed: strings placed in the accepted set before the first draw (E1-V1: the 320 Pilot strings)."""
        accepted = list(preseed)
        facts, log = [], []
        per_cell = n_learned + n_unread
        for rel in RELATIONS:
            for st in STRATA:
                cell = "%s/%s" % (rel, st)

                def take(purpose, want, ok, what):
                    r, got, n = rng_rule(seed, purpose), [], 0
                    while len(got) < want:
                        if n >= MAX_DRAWS:
                            raise RuntimeError("IMPLEMENTATION_FAIL: %s stream exhausted in %s" % (what, cell))
                        s = self.draw(r, st)
                        n += 1
                        if ok(s):
                            got.append(s)
                    return got, n

                def accept(target):
                    def ok(s):
                        if (self.form_ok(s, st) and (target is None or self.pair(s) == target)
                                and not clash(s, st, accepted) and not self.in_anchor(s)):
                            accepted.append(s)
                            return True
                        return False
                    return ok

                ents, n_e = take("names:%s:%s:entity" % (rel, st), per_cell, accept(None), "entity")
                survey, _ = take("names:%s:%s:answer" % (rel, st), SURVEY, lambda s: self.form_ok(s, st), "survey")
                cnt = collections.Counter(self.pair(s) for s in survey)
                best = max(cnt.values())
                target = min(k for k, v in cnt.items() if v == best)
                ans, n_a = take("names:%s:%s:answer" % (rel, st), per_cell, accept(target), "answer")
                log.append({"cell": cell, "entity_draws": n_e, "target_pair": list(target), "answer_draws": n_a})
                for i, (e, a) in enumerate(zip(ents, ans)):
                    learned = i < n_learned
                    idx = i + 1 if learned else i - n_learned + 1
                    facts.append({"fact_id": "%s-%s-%s-%s-%02d" % (prefix, "L" if learned else "U", rel, SHORT[st], idx),
                                  "exposure": "learned" if learned else "unread", "relation": rel, "stratum": st,
                                  "entity": e, "answer": a})
        return facts, log


# ------------------------------------------------------------------------------------------- texts (sections 2.3-2.6)
def fill(text, e, a):
    return text.replace("{E}", e).replace("{A}", a)


def templates_by(templates):
    out = {}
    for t in templates:
        out.setdefault((t["relation"], t["kind"]), []).append(t)
    return out


def normalize_template(text):
    s = text.replace("{E}", "<ENTITY>").replace("{A}", "<ANSWER>").lower()
    s = re.sub(r"[^a-z0-9<> ]", " ", s)
    return re.sub(r" +", " ", s).strip()


def word_ngrams(words, n):
    return {tuple(words[i:i + n]) for i in range(len(words) - n + 1)}


def shared_ngrams(docs_a, docs_b, n):
    a = set().union(*(word_ngrams(list(d), n) for d in docs_a))
    b = set().union(*(word_ngrams(list(d), n) for d in docs_b))
    return a & b


def whole_word_hits(strings, text):
    """V1 strings that occur in text case-insensitively with no ASCII letter or digit right before or after (L8)."""
    low = text.lower()
    hits = []
    for s in strings:
        k = s.lower()
        start = 0
        while True:
            i = low.find(k, start)
            if i < 0:
                break
            before = low[i - 1] if i > 0 else ""
            after = low[i + len(k)] if i + len(k) < len(low) else ""
            if not re.match(r"[a-z0-9]", before) and not re.match(r"[a-z0-9]", after):
                hits.append(s)
                break
            start = i + 1
    return hits


def stats(xs):
    xs = sorted(xs)
    return {"n": len(xs), "sum": sum(xs), "mean": round(statistics.fmean(xs), 3), "min": xs[0],
            "median": xs[len(xs) // 2], "max": xs[-1]}


def main():
    ap = argparse.ArgumentParser()
    for a in ("qwen", "anchor-parquet", "parcae-tokenizer", "eval-sets", "pilot-split-manifest", "mmlu-validation",
              "mmlu-test", "arc-dir", "out"):
        ap.add_argument("--" + a, required=True)
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    import pyarrow.parquet as pq
    import transformers
    import tokenizers
    from transformers import AutoTokenizer
    from tokenizers import Tokenizer
    print("python", sys.version.split()[0], "| transformers", transformers.__version__, "| tokenizers", tokenizers.__version__)
    for f in ("tokenizer.json", "tokenizer_config.json", "vocab.json", "merges.txt"):
        print("input qwen/%s sha256 %s" % (f, sha((Path(args.qwen) / f).read_bytes())))
    for a in ("anchor_parquet", "parcae_tokenizer", "eval_sets", "pilot_split_manifest", "mmlu_validation", "mmlu_test"):
        print("input %s sha256 %s" % (a, sha(Path(getattr(args, a)).read_bytes())))
    tok = AutoTokenizer.from_pretrained(args.qwen)
    endoftext = tok.convert_tokens_to_ids("<|endoftext|>")
    check("tokenizer <|endoftext|> id 151643", endoftext == 151643, endoftext)

    def enc(t):
        return tok.encode(t, add_special_tokens=False)

    def chat(q):
        return tok.apply_chat_template([{"role": "user", "content": q}], tokenize=False, add_generation_prompt=True,
                                       enable_thinking=False)

    # ---- anchor text (Pilot 2.7, unchanged) ----
    anchor = []
    seen = 0
    for batch in pq.ParquetFile(args.anchor_parquet).iter_batches(columns=["text"], batch_size=256):
        for text in batch.column(0).to_pylist():
            seen += 1
            if isinstance(text, str) and len(text) >= 600:
                ids = enc(text)[:128]
                anchor.append({"doc": len(anchor), "source_row": seen - 1, "ids": ids, "text": tok.decode(ids)})
                if len(anchor) == 512:
                    break
        if len(anchor) == 512:
            break
    a_sha = sha(canonical([r["text"] for r in anchor]))
    check("anchor decoded texts canonical sha256 = Pilot frozen", a_sha == ANCHOR_TEXTS_SHA, a_sha)
    anchor_file_sha = write(out, "anchor_text.jsonl", jsonl_bytes(anchor))
    print("anchor_text.jsonl sha256", anchor_file_sha)

    names = Names(tok, [r["text"] for r in anchor])
    anchor_words13 = set().union(*(word_ngrams(r["text"].split(), NGRAM_L6) for r in anchor))

    def shares_anchor_13gram(text):
        return bool(word_ngrams(text.split(), NGRAM_L6) & anchor_words13)

    # ---- Pilot facts (to get the 320 Pilot strings) ----
    pilot, _ = names.build(PILOT_DATA_SEED, 15, 5, "E1P")
    p_sha = sha(canonical(pilot))
    check("Pilot facts canonical sha256 = 406c8801...", p_sha == PILOT_FACTS_SHA, p_sha)
    pilot_strings = [x for f in pilot for x in (f["entity"], f["answer"])]

    # ---- V1 facts ----
    facts, log = names.build(DATA_SEED, 30, 10, "E1V1", preseed=pilot_strings)
    for c in log:
        print("cell %-18s entity_draws %5d answer_draws %5d target_pair %s" % (c["cell"], c["entity_draws"], c["answer_draws"], c["target_pair"]))
    f_sha = sha(canonical(facts))
    print("V1 facts: %d (learned %d, unread %d); canonical sha256 (JSON list, protocol 2.2) %s" % (
        len(facts), sum(f["exposure"] == "learned" for f in facts), sum(f["exposure"] == "unread" for f in facts), f_sha))
    print("facts.jsonl sha256", write(out, "facts.jsonl", jsonl_bytes(facts)))
    v1_strings = [x for f in facts for x in (f["entity"], f["answer"])]

    # ---- templates (Pilot 2.4, unchanged) ----
    sm = json.loads(Path(args.pilot_split_manifest).read_text(encoding="utf-8"))
    templates = sm["templates"]
    for t in templates:
        n = normalize_template(t["text"])
        if n != t["normalized"] or sha(n.encode("utf-8")) != t["normalized_sha256"]:
            check("template %s normalization" % t["template_id"], False)
    ts_sha = sha("\n".join(sorted(t["normalized_sha256"] for t in templates)).encode("utf-8"))
    check("template_set_sha256 = Pilot frozen", ts_sha == TEMPLATE_SET_SHA and len(templates) == 32, ts_sha)
    tpl = templates_by(templates)

    learned = [f for f in facts if f["exposure"] == "learned"]
    train_F = []
    for f in learned:
        (t,) = tpl[(f["relation"], "TRAIN")]
        train_F.append({"fact_id": f["fact_id"], "template_id": t["template_id"], "text": fill(t["text"], f["entity"], f["answer"])})
    cells = collections.OrderedDict()
    for f in learned:
        cells.setdefault((f["relation"], f["stratum"]), []).append(f)
    train_S, attempts = [], {}
    for (rel, st), group in cells.items():
        r = rng_rule(DATA_SEED, "s-permutation:%s:%s" % (rel, st))
        n = 0
        while True:
            perm = list(range(len(group)))
            r.shuffle(perm)
            n += 1
            if all(perm[i] != i for i in range(len(perm))):
                break
        attempts["%s/%s" % (rel, st)] = n
        (t,) = tpl[(rel, "TRAIN")]
        for i, f in enumerate(group):
            g = group[perm[i]]
            train_S.append({"fact_id": f["fact_id"], "answer_fact_id": g["fact_id"], "text": fill(t["text"], f["entity"], g["answer"])})
    print("S derangement attempts per cell", attempts)
    train_Y = []
    for f in learned:
        for kind in ("Y_ENTITY", "Y_ANSWER"):
            (t,) = tpl[(f["relation"], kind)]
            train_Y.append({"fact_id": f["fact_id"], "template_id": t["template_id"], "kind": kind,
                            "text": fill(t["text"], f["entity"], f["answer"])})
    dev_qa = []
    check("DEV templates per relation = 2", all(len(tpl[(rel, "DEV")]) == 2 for rel in RELATIONS))
    for f in facts:
        for t in tpl[(f["relation"], "DEV")]:
            dev_qa.append({"fact_id": f["fact_id"], "template_id": t["template_id"], "question": fill(t["text"], f["entity"], f["answer"])})
    cands, pools = {}, []
    for f in facts:
        pool = [g["answer"] for g in facts if g is not f and (g["relation"], g["stratum"], g["exposure"]) == (f["relation"], f["stratum"], f["exposure"])]
        pools.append(len(pool))
        r = rng_rule(CANDIDATE_SEED, "cand:%s" % f["fact_id"])
        c = [f["answer"]] + r.sample(pool, 3)
        r.shuffle(c)
        cands[f["fact_id"]] = c
    check("distractor pool >= 4 for every fact", min(pools) >= 4, "min pool %d, max %d" % (min(pools), max(pools)))
    check("4 distinct candidates per fact", all(len(set(c)) == 4 for c in cands.values()))
    hashes = {}
    for name, rows in (("train_F.jsonl", train_F), ("train_S.jsonl", train_S), ("train_Y.jsonl", train_Y), ("dev_qa.jsonl", dev_qa)):
        hashes[name] = write(out, name, jsonl_bytes(rows))
        print("%-14s rows %4d sha256 (byte = canonical) %s" % (name, len(rows), hashes[name]))
    hashes["candidates.json"] = write(out, "candidates.json", canonical(cands))
    print("candidates.json keys %d sha256 (byte = canonical) %s" % (len(cands), hashes["candidates.json"]))

    # ---- Y ratio (Pilot 2.6) ----
    f_tok = sum(len(enc(r["text"])) + 1 for r in train_F)
    y_tok = sum(len(enc(r["text"])) + 1 for r in train_Y)
    check("Y / F token ratio in [0.80, 1.25]", 0.80 <= y_tok / f_tok <= 1.25, "F %d Y %d ratio %.4f" % (f_tok, y_tok, y_tok / f_tok))

    # ---- exposure matching (Pilot 2.5) ----
    by_id = {f["fact_id"]: f for f in facts}
    bad = 0
    for name, rows in (("train_F", train_F), ("train_S", train_S), ("train_Y", train_Y)):
        low = "\n".join(r["text"] for r in rows).lower()
        for fid, cs in cands.items():
            want = 1 if by_id[fid]["exposure"] == "learned" else 0
            bad += sum(low.count(c.lower()) != want for c in cs)
    check("exposure matching (every learned candidate once, unread 0)", bad == 0, "violations %d" % bad)

    # ---- answer token ids in the scoring context equal those in the TRAIN statement (Pilot round 3 item 7) ----
    mism = 0
    for f in learned:
        (t,) = tpl[(f["relation"], "TRAIN")]
        stmt_ids = enc(fill(t["text"], f["entity"], f["answer"]))
        a_ids = enc(" " + f["answer"])
        found = any(stmt_ids[i:i + len(a_ids)] == a_ids for i in range(len(stmt_ids)))
        for q in [r["question"] for r in dev_qa if r["fact_id"] == f["fact_id"]]:
            ctx = enc(chat(q) + ANSWER_PREFIX)
            full = enc(chat(q) + ANSWER_PREFIX + " " + f["answer"])
            mism += int(full[:len(ctx)] != ctx or full[len(ctx):] != a_ids or not found)
    check("scored answer ids = TRAIN statement answer ids (240 x 2 DEV)", mism == 0, "mismatches %d" % mism)

    # ---- leakage L1-L5 (DEV parts), L7 ----
    sets = collections.defaultdict(set)
    for t in templates:
        sets[t["set"]].add(t["normalized_sha256"])
    dup = sum(len(sets[a] & sets[b]) for a, b in itertools.combinations(sorted(sets), 2))
    check("L1 template hashes pairwise disjoint", dup == 0, dup)
    best = 0.0
    for x, y in itertools.combinations(templates, 2):
        if x["set"] != y["set"]:
            gx, gy = word_ngrams(normalize_template(x["text"]).split(), 4), word_ngrams(normalize_template(y["text"]).split(), 4)
            if gx and gy:
                best = max(best, len(gx & gy) / len(gx | gy))
    check("L2 max word 4-gram Jaccard <= 0.25", best <= 0.25, best)
    corpora = {"train_F": [r["text"] for r in train_F], "train_S": [r["text"] for r in train_S],
               "train_Y": [r["text"] for r in train_Y], "anchor_text": [r["text"] for r in anchor]}
    unread_strings = [x for f in facts if f["exposure"] == "unread" for x in (f["entity"], f["answer"])]
    l3a = sum(t.lower().count(s.lower()) for texts in corpora.values() for t in texts for s in unread_strings)
    check("L3a unread strings in training corpora and anchor", l3a == 0, l3a)
    l3b = sum(t.lower().count(f["answer"].lower()) for t in corpora["anchor_text"] for f in learned)
    check("L3b learned answers in anchor", l3b == 0, l3b)
    l4 = sum(q["question"] in t for texts in corpora.values() for t in texts for q in dev_qa)
    check("L4 DEV questions verbatim in training corpora", l4 == 0, "%d (questions %d)" % (l4, len(dev_qa)))
    ids_l = {f["fact_id"] for f in learned}
    ids_u = {f["fact_id"] for f in facts if f["exposure"] == "unread"}
    l5 = len(ids_l & ids_u) + len(v1_strings) - len(set(v1_strings))
    check("L5 identity (fact_id overlap + duplicate strings among 640)", l5 == 0 and len(v1_strings) == 640, l5)
    pl_low = {s.lower() for s in pilot_strings}
    l7a = sum(s.lower() in pl_low for s in v1_strings)
    stratum_of = {x: f["stratum"] for f in facts + pilot for x in (f["entity"], f["answer"])}
    l7b = sum(clash(s, stratum_of[s], [p for p in pilot_strings if stratum_of[p] == stratum_of[s]]) for s in v1_strings)
    l7c = len({f["fact_id"] for f in facts} & {f["fact_id"] for f in pilot})
    check("L7a V1 strings equal to a Pilot string (case-insensitive)", l7a == 0, l7a)
    check("L7b V1 strings in conflict (2.2 reject_if) with a Pilot string", l7b == 0, l7b)
    check("L7c fact_id overlap with Pilot", l7c == 0, l7c)

    # ---- D1 (section 7.2): DEV windows; TEST rule counted from row prefixes only ----
    head = re.compile(rb'\{"domain": "([^"\\]*)", "split": "([^"\\]*)", ')
    ptok = Tokenizer.from_file(args.parcae_tokenizer)
    dev_rows, counts = collections.defaultdict(list), collections.Counter()
    with open(args.eval_sets, "rb") as fh:
        for line in fh:
            m = head.match(line)
            dom, split = m.group(1).decode("ascii"), m.group(2).decode("ascii")
            counts[(dom, split)] += 1
            if split == "dev":
                dev_rows[dom].append(json.loads(line.decode("utf-8")))
    print("eval_sets rows by (domain, split) from row prefixes:", dict(sorted(counts.items())))
    general_dev, d1_excluded = [], collections.Counter()
    for d in D1_DOMAINS:
        for r in dev_rows[d]:
            ids = enc(ptok.decode(r["tokens"], skip_special_tokens=True))[:D1_MAX_TOKENS]
            text = tok.decode(ids)
            w = {"domain": d, "doc_id": r["doc_id"], "ids": ids, "text": text}
            if whole_word_hits(v1_strings, text):
                d1_excluded[(d, "L8")] += 1
                continue
            if shares_anchor_13gram(text):
                d1_excluded[(d, "L6")] += 1
                continue
            general_dev.append(w)
    print("D1 DEV windows kept per domain", dict(collections.Counter(w["domain"] for w in general_dev)), "excluded", dict(d1_excluded))
    print("D1 TEST available after skipping the first %d test rows per domain: %s" % (
        D1_TEST_SKIP_FIRST, {d: counts[(d, "test")] - D1_TEST_SKIP_FIRST for d in D1_DOMAINS}))
    hashes["general_dev.jsonl"] = write(out, "general_dev.jsonl", jsonl_bytes(general_dev))
    print("general_dev.jsonl windows %d sha256 %s" % (len(general_dev), hashes["general_dev.jsonl"]))
    l6_d1 = len(shared_ngrams([a["text"].split() for a in anchor], [w["text"].split() for w in general_dev], NGRAM_L6))
    l6_d1_ids = len(shared_ngrams([a["ids"] for a in anchor], [w["ids"] for w in general_dev], NGRAM_L6))
    check("L6 anchor vs D1 DEV word 13-grams", l6_d1 == 0, "%d (token-id 13-grams, report only: %d)" % (l6_d1, l6_d1_ids))
    l8_d1 = sum(bool(whole_word_hits(v1_strings, w["text"])) for w in general_dev)
    check("L8 D1 DEV windows containing a V1 string (whole word)", l8_d1 == 0, l8_d1)
    d1_len = [len(w["ids"]) for w in general_dev]
    print("D1 DEV ids per window", stats(d1_len))

    # ---- D2 (section 7.1): MMLU validation -> DEV; MMLU test: row count only ----
    def d2_prompt(question, choices):
        return D2_INSTRUCTION + "\n\n" + question.strip() + "\n" + "\n".join("%s. %s" % (L, str(c).strip()) for L, c in zip(LETTERS, choices))

    letter_ids = [enc(" " + L) for L in LETTERS]
    check("' A'..' D' are single tokens", all(len(x) == 1 for x in letter_ids), letter_ids)
    val = pq.read_table(args.mmlu_validation).to_pylist()
    n_test = pq.ParquetFile(args.mmlu_test).metadata.num_rows
    print("MMLU all/validation rows %d; all/test rows (parquet footer) %d; validation columns %s" % (len(val), n_test, sorted(val[0])))
    order = list(range(len(val)))
    rng_rule(DATA_SEED, "d2:mmlu:validation:order").shuffle(order)
    d2_dev, d2_excl = [], collections.Counter()
    for i in order:
        r = val[i]
        if len(r["choices"]) != 4 or r["answer"] not in (0, 1, 2, 3):
            d2_excl["not_4_choices"] += 1
            continue
        text = d2_prompt(r["question"], r["choices"])
        if whole_word_hits(v1_strings, text):
            d2_excl["L8"] += 1
            continue
        if shares_anchor_13gram(text):
            d2_excl["L6"] += 1
            continue
        d2_dev.append({"item": len(d2_dev), "source_row": i, "subject": r["subject"], "prompt": text, "answer": LETTERS[r["answer"]]})
        if len(d2_dev) == D2_N:
            break
    print("D2 DEV items %d (from %d validation rows in shuffled order, rows visited %d); excluded %s" % (
        len(d2_dev), len(val), order.index(d2_dev[-1]["source_row"]) + 1, dict(d2_excl)))
    hashes["d2_dev.jsonl"] = write(out, "d2_dev.jsonl", jsonl_bytes(d2_dev))
    print("d2_dev.jsonl sha256", hashes["d2_dev.jsonl"])
    print("D2 DEV answer letters", dict(sorted(collections.Counter(x["answer"] for x in d2_dev).items())),
          "subjects", len({x["subject"] for x in d2_dev}))
    d2_len = [len(enc(chat(x["prompt"]) + ANSWER_PREFIX)) for x in d2_dev]
    print("D2 DEV context ids per item (chat + 'The answer is')", stats(d2_len))
    check("L6 anchor vs D2 DEV word 13-grams", len(shared_ngrams([a["text"].split() for a in anchor], [x["prompt"].split() for x in d2_dev], NGRAM_L6)) == 0)
    check("L8 D2 DEV items containing a V1 string", sum(bool(whole_word_hits(v1_strings, x["prompt"])) for x in d2_dev) == 0)

    # ---- ARC (alternative D2): validation -> DEV built the same way; test: row counts only ----
    for sub in ("ARC-Challenge", "ARC-Easy"):
        for split in ("validation", "test"):
            p = Path(args.arc_dir) / sub / ("%s-00000-of-00001.parquet" % split)
            print("ARC %s/%s rows (parquet footer) %d sha256 %s" % (sub, split, pq.ParquetFile(str(p)).metadata.num_rows, sha(p.read_bytes())))
    arc_val = []
    for sub in ("ARC-Challenge", "ARC-Easy"):
        arc_val += pq.read_table(str(Path(args.arc_dir) / sub / "validation-00000-of-00001.parquet")).to_pylist()
    order = list(range(len(arc_val)))
    rng_rule(DATA_SEED, "d2:arc:validation:order").shuffle(order)
    arc_dev, arc_excl = [], collections.Counter()
    for i in order:
        r = arc_val[i]
        labels, texts = list(r["choices"]["label"]), list(r["choices"]["text"])
        if len(labels) != 4 or r["answerKey"] not in labels:
            arc_excl["not_4_choices"] += 1
            continue
        text = d2_prompt(r["question"], texts)
        if whole_word_hits(v1_strings, text):
            arc_excl["L8"] += 1
            continue
        if shares_anchor_13gram(text):
            arc_excl["L6"] += 1
            continue
        arc_dev.append({"item": len(arc_dev), "source_row": i, "subject": r["id"], "prompt": text, "answer": LETTERS[labels.index(r["answerKey"])]})
        if len(arc_dev) == D2_N:
            break
    print("ARC DEV (alternative) items %d from %d validation rows (Challenge then Easy, shuffled); excluded %s" % (
        len(arc_dev), len(arc_val), dict(arc_excl)))
    check("ARC DEV (alternative) reaches %d items" % D2_N, len(arc_dev) == D2_N)
    print("d2_dev_arc.jsonl sha256", write(out, "d2_dev_arc.jsonl", jsonl_bytes(arc_dev)))
    print("ARC DEV context ids per item", stats([len(enc(chat(x["prompt"]) + ANSWER_PREFIX)) for x in arc_dev]))

    # ---- token counts for the compute estimate (section 10) ----
    qa_len = [len(enc(chat(q["question"]) + ANSWER_PREFIX + " " + c)) for q in dev_qa for c in cands[q["fact_id"]]]
    print("fact DEV-QA scored sequences", stats(qa_len))
    cb_len = []
    for f in learned:
        (t,) = tpl[(f["relation"], "TRAIN")]
        pre = t["text"].split(" {A}")[0].replace("{E}", f["entity"])
        cb_len += [len(enc(pre + " " + c)) for c in cands[f["fact_id"]]]
    print("TRAIN closed-book sequences", stats(cb_len))
    print("train_F tokens per pass (with <|endoftext|>) %d; train_Y %d" % (f_tok, y_tok))
    print("RESULT: %s" % ("PASS" if not FAIL else "FAIL " + ", ".join(FAIL)))
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(main())
