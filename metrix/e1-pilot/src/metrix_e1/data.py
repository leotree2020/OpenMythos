"""Data of METRIX E1-PILOT, everything except TEST.

Protocol v1.1 section 2 (2.1 facts, 2.2 names, 2.3-2.4 texts and templates, 2.5 candidates, 2.6 S and Y, 2.7 general
DEV windows and anchor text, 2.8 files), section 8 step 1 (generate the non-TEST data on CPU), section 11 ST12 (the
generated data against the frozen hashes). TEST (test_qa.jsonl, general_test.jsonl) is not generated here; it belongs
to section 8 step 8 (test_data.py). No eval_sets.jsonl row with split other than the DEV split is parsed or decoded:
the split field of every row is read from the row prefix only (protocol section 3, "读取 TEST 数据").

Ported from the reference scripts already in the repository; tests/test_data_hashes.py shows that the outputs are
byte-identical to theirs:
  reports/round2/names.py + gen_facts.py   2.2 facts                (canonical list of the 160 facts)
  reports/round2/anchor_check.py           2.7 anchor texts         (list of the 512 decoded texts)
  reports/round7/gen_s_cands.py            2.5 candidates, 2.6 S    (candidates.json, train_S.jsonl)
  reports/round5/l6_check.py               2.7 general DEV windows  (ids and decoded texts)
  reports/round2/y_ratio.py                2.6 Y / F token ratio    (sequence + <|endoftext|>)

Before generating, the library versions of protocol section 0 are checked (frozen.check_library_versions, ST8).
All numbers and strings of the protocol (counts, probabilities, length limits, seeds, templates, sources, revisions)
are read from the frozen manifests through metrix_e1.frozen; where the manifest states a number inside a sentence,
the sentence is matched in full and the number taken from it (a different sentence stops the run).

Commands (each prints RESULT: PASS / RESULT: FAIL; exit 0 only on PASS):
  python -m metrix_e1.data fetch    --inputs DIR              download the pinned tokenizer files and anchor parquet
  python -m metrix_e1.data generate --inputs DIR --out DIR    write the 8 non-TEST data files of 2.8
  python -m metrix_e1.data verify   --inputs DIR --data DIR   ST12 check of an existing data directory
"""
import argparse
import collections
import json
import platform
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from . import frozen as FZ
from ._cli import run_guarded
from .errors import ImplementationFail, ST12Error

DATA_FILES = ("facts.jsonl", "train_F.jsonl", "train_S.jsonl", "train_Y.jsonl", "dev_qa.jsonl", "candidates.json",
              "general_dev.jsonl", "anchor_text.jsonl")
TEST_FILES = ("test_qa.jsonl", "general_test.jsonl")


# ------------------------------------------------------------------------------------- frozen parameters (section 2)

def _match(pattern, text, what):
    m = re.fullmatch(pattern, text)
    if m is None:
        raise ImplementationFail("the frozen text of %s is %r; the implementation expects the form %r" % (what, text, pattern))
    return m


@dataclass(frozen=True)
class Params:
    """The section 2 values the generators use, read from the frozen manifests."""
    data_seed: int
    candidate_seed: int
    relations: tuple
    strata: tuple
    stratum_short: dict          # natural -> nat, random -> rnd (fact_id format)
    exposure_letter: dict        # learned -> L, unread -> U (SPLIT_MANIFEST fact_ids)
    fact_prefix: str             # E1P (fact_id format)
    fact_fields: tuple
    n_learned: int
    n_unread: int
    names: dict                  # DATA_MANIFEST name_generation
    natural_min_tokens_exclusive: int
    natural_prefix_chars: int
    natural_max_edit: int
    random_max_hamming: int
    random_digits: int
    survey_size: int
    max_draws: int
    candidate_way: int
    pool_min: int
    endoftext_id: int
    y_ratio_bounds: tuple
    anchor_source: tuple         # (repo, revision, filename); its sha256 is checked through PROTOCOL_FROZEN
    anchor_n_docs: int
    anchor_min_chars: int
    anchor_max_tokens: int
    general_source: str          # repository path of eval_sets.jsonl
    parcae: tuple                # (repo, revision)
    general_dev_per_domain: int
    general_domains: tuple
    general_dev_split: str
    general_max_tokens: int
    qwen: tuple                  # (repo, revision)
    qwen_files: tuple
    dev_per_fact: int


def params(fz):
    dm, sm, ss = fz.data_manifest, fz.split_manifest, fz.search_space
    f, ng = dm["facts"], dm["name_generation"]
    m = _match(r"(\w+)-<(\w)\|(\w)>-<relation>-<(\w+)\|(\w+)>-<two-digit index starting at 01>", f["fact_id_format"],
               "facts.fact_id_format")
    prefix_id, short = m.group(1), m.groups()[3:]
    if len(f["strata"]) != len(short):
        raise ImplementationFail("fact_id_format names %d strata, the manifest lists %r" % (len(short), f["strata"]))
    letters = {}
    for exposure in ("learned", "unread"):
        e = _match(r"(\w+)-(\w)-\*: (\d+) facts, .*", sm["fact_ids"][exposure], "fact_ids.%s" % exposure)
        if e.group(1) != prefix_id or int(e.group(3)) != f[exposure] or e.group(2) not in m.groups()[1:3]:
            raise ImplementationFail("fact_ids.%s %r disagrees with fact_id_format / facts" % (exposure, sm["fact_ids"][exposure]))
        letters[exposure] = e.group(2)
    nat = ng["natural"]
    _match(r"length_chars", nat["form_rules"][0], "natural form rule 1")
    tok_min = int(_match(r"len\(encode\(' ' \+ s\)\) > (\d+) \(not a single token with a leading space\)",
                         nat["form_rules"][1], "natural form rule 2").group(1))
    _match(r"equals an accepted string after lowercasing both", nat["reject_if"][0], "natural reject_if 1")
    prefix = int(_match(r"same first (\d+) characters as an accepted string \(case-sensitive\)", nat["reject_if"][1],
                        "natural reject_if 2").group(1))
    edit = int(_match(r"Levenshtein distance <= (\d+) to an accepted string after lowercasing both", nat["reject_if"][2],
                      "natural reject_if 3").group(1))
    if len(nat["reject_if"]) != 3 or len(nat["form_rules"]) != 2:
        raise ImplementationFail("natural reject_if / form_rules have an unexpected number of rules")
    rnd = ng["random"]
    _match(r"equals an accepted string", rnd["reject_if"][0], "random reject_if 1")
    _match(r"same letter block as an accepted string \(letter block = the part before '-'; the whole string if it has no '-'\)",
           rnd["reject_if"][1], "random reject_if 2")
    ham = int(_match(r"Hamming distance <= (\d+) to an accepted string of the same length", rnd["reject_if"][2],
                     "random reject_if 3").group(1))
    if len(rnd["reject_if"]) != 3 or rnd["form_rules"] != ["length_chars"]:
        raise ImplementationFail("random reject_if / form_rules have an unexpected number of rules")
    if sorted(rnd["L"]) != ["3", "4", "5"] or sorted(nat["syllables"]) != ["2", "3"]:
        raise ImplementationFail("syllable or letter-count distribution has unexpected support")
    digits = int(_match(r"u = rng\.random\(\); L = 3 if u < 0\.25 else 4 if u < 0\.75 else 5; L times rng\.choice\(letters\); "
                        r"'-'; (\d+) times rng\.choice\(digits\)", ng["draw"]["random"], "draw.random").group(1))
    _match(r"n = 2 if rng\.random\(\) < 0\.5 else 3; concatenate n times rng\.choice\(onsets\) \+ rng\.choice\(nuclei\) \+ "
           r"rng\.choice\(codas\); capitalize the first letter", ng["draw"]["natural"], "draw.natural")
    survey = int(_match(r"from the start of the answer stream, the first (\d+) draws that satisfy the form rules \(reject_if "
                        r"and the anchor rule are NOT applied; repeats count\); count \(K_st, K_qa\); target = the most "
                        r"frequent pair, ties broken by the smaller pair compared as a tuple",
                        ng["answer_token_length_rule"]["survey"], "answer_token_length_rule.survey").group(1))
    cand = sm["candidates"]
    pool_min = int(_match(r"a distractor pool with fewer than (\d+) answers: IMPLEMENTATION_FAIL; no synthetic distractors "
                          r"are generated \(protocol 2\.5; supplement b, Task Order V1\.2\)", cand["pool_too_small"],
                          "candidates.pool_too_small").group(1))
    eot = int(_match(r"raw statement text followed by <\|endoftext\|> \(id (\d+)\); no chat template, no system prompt",
                     dm["model"]["input_convention"]["training"], "model.input_convention.training").group(1))
    lo, hi = _match(r".*; Y tokens / F tokens must lie in \[([0-9.]+), ([0-9.]+)\]",
                    ss["training_contract"]["primary_training_token_budget"],
                    "SEARCH_SPACE training_contract.primary_training_token_budget").groups()
    at = dm["anchor_text"]
    a_repo, a_rev, a_file = _match(r"([\w.-]+/[\w.-]+)@([0-9a-f]{40}), (\S+) \(sha256 [0-9a-f]{64}\)",
                                   at["source"], "anchor_text.source").groups()
    a_n, a_chars = (int(x) for x in _match(r"first (\d+) documents in file order with at least (\d+) characters",
                                           at["selection"], "anchor_text.selection").groups())
    gt = dm["general_text"]
    p_repo, p_rev = _match(r"([\w.-]+/[\w.-]+)@([0-9a-f]{40}), special tokens skipped", gt["decode_with"],
                           "general_text.decode_with").groups()
    g_n, g_domains, g_split = _match(r"first (\d+) windows per domain \(([a-z0-9, ]+)\) with split == '(\w+)', file order",
                                     gt["dev"], "general_text.dev").groups()
    dev_n = int(_match(r"(\d+) questions per fact \(learned and unread\), DEV templates", sm["splits"]["DEV"],
                       "splits.DEV").group(1))
    tok = dm["model"]["tokenizer"]
    return Params(
        data_seed=fz.seeds["DATA_SEED"], candidate_seed=fz.seeds["CANDIDATE_SEED"],
        relations=tuple(f["relations"]), strata=tuple(f["strata"]),
        stratum_short=dict(zip(f["strata"], short)), exposure_letter=letters,
        fact_prefix=prefix_id, fact_fields=tuple(ng["expected_facts_fields"]),
        n_learned=f["per_cell"]["learned"], n_unread=f["per_cell"]["unread"], names=ng,
        natural_min_tokens_exclusive=tok_min, natural_prefix_chars=prefix, natural_max_edit=edit,
        random_max_hamming=ham, random_digits=digits, survey_size=survey, max_draws=ng["max_draws_per_stream"],
        candidate_way=cand["way"], pool_min=pool_min, endoftext_id=eot, y_ratio_bounds=(float(lo), float(hi)),
        anchor_source=(a_repo, a_rev, a_file), anchor_n_docs=a_n, anchor_min_chars=a_chars,
        anchor_max_tokens=at["truncate_to_model_tokens"], general_source=gt["source_file"], parcae=(p_repo, p_rev),
        general_dev_per_domain=int(g_n), general_domains=tuple(d.strip() for d in g_domains.split(",")),
        general_dev_split=g_split, general_max_tokens=gt["truncate_to_model_tokens"],
        qwen=(tok["repo"], tok["revision"]), qwen_files=tuple(tok["files_sha256"]), dev_per_fact=dev_n)


# ------------------------------------------------------------------------------------------------- inputs (2.7, 0)

def input_paths(p, inputs_dir):
    """Layout of the downloaded inputs under inputs_dir (outside the repository)."""
    d = Path(inputs_dir)
    out = {"qwen:%s" % name: d / "qwen_tokenizer" / name for name in p.qwen_files}
    out["parcae_tokenizer"] = d / "parcae_tokenizer" / "tokenizer.json"
    out["anchor_parquet"] = d / "anchor_source" / p.anchor_source[2]
    return out


def fetch_inputs(fz, inputs_dir):
    """Download the pinned non-model inputs: the four tokenizer files of the model revision (no weight file is
    requested), the parcae tokenizer.json, the anchor parquet. Each file is then checked against its frozen sha256."""
    from huggingface_hub import hf_hub_download
    p = params(fz)
    paths = input_paths(p, inputs_dir)
    d = Path(inputs_dir)
    for name in p.qwen_files:
        hf_hub_download(p.qwen[0], name, revision=p.qwen[1], local_dir=d / "qwen_tokenizer")
    hf_hub_download(p.parcae[0], "tokenizer.json", revision=p.parcae[1], local_dir=d / "parcae_tokenizer")
    hf_hub_download(p.anchor_source[0], p.anchor_source[2], revision=p.anchor_source[1], repo_type="dataset",
                    local_dir=d / "anchor_source")
    return {key: fz.check_file(path, key) for key, path in paths.items()}


def check_inputs(fz, p, inputs_dir):
    """ST12 range (1) for the input files: file-byte sha256 of the tokenizer files, the anchor parquet and
    eval_sets.jsonl against PROTOCOL_FROZEN. Returns {key: path}."""
    paths = input_paths(p, inputs_dir)
    paths["eval_sets"] = fz.repo_root / p.general_source
    for key, path in paths.items():
        fz.check_file(path, key)
    return paths


def load_qwen_tokenizer(p, paths):
    """The protocol tokenizer from the four checked files only (offline)."""
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(str(paths["qwen:tokenizer.json"].parent), local_files_only=True)
    if tok.convert_tokens_to_ids("<|endoftext|>") != p.endoftext_id:
        raise ST12Error("tokenizer: <|endoftext|> has id %r, the protocol says %d" % (
            tok.convert_tokens_to_ids("<|endoftext|>"), p.endoftext_id))
    return tok


# ---------------------------------------------------------------------------------------------- anchor text (2.7)

def build_anchor(p, tok, parquet_path):
    """First anchor_n_docs documents in file order with at least anchor_min_chars characters; each cut to its first
    anchor_max_tokens ids of the protocol tokenizer; text = decode of those ids (default arguments).
    Rows: {"doc": i, "source_row": row index in the parquet file, "ids": [...], "text": "..."}."""
    import pyarrow.parquet as pq
    rows, seen = [], 0
    for batch in pq.ParquetFile(str(parquet_path)).iter_batches(columns=["text"], batch_size=256):
        for text in batch.column(0).to_pylist():
            seen += 1
            if isinstance(text, str) and len(text) >= p.anchor_min_chars:
                ids = tok.encode(text, add_special_tokens=False)[:p.anchor_max_tokens]
                rows.append({"doc": len(rows), "source_row": seen - 1, "ids": ids, "text": tok.decode(ids)})
                if len(rows) == p.anchor_n_docs:
                    return rows
    raise ImplementationFail("anchor parquet has only %d documents with at least %d characters" % (len(rows), p.anchor_min_chars))


# ---------------------------------------------------------------------------------------------------- names (2.2)

def lev_le1(a, b):
    """Levenshtein distance between a and b is at most 1 (reference: reports/round2/names.py)."""
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


class NameGenerator:
    """Protocol 2.2 (reference: reports/round2/names.py, Names)."""

    def __init__(self, p, tok, anchor_texts):
        if p.natural_max_edit != 1:
            raise ImplementationFail("the edit-distance test is implemented for distance <= 1, the manifest says %d" % p.natural_max_edit)
        self.p = p
        self.ng = p.names
        self.tok = tok
        self.anchor_low = [t.lower() for t in anchor_texts]

    def ids(self, text):
        return self.tok.encode(text, add_special_tokens=False)

    def draw(self, r, stratum):
        g = self.ng[stratum]
        if stratum == "natural":
            n = 2 if r.random() < g["syllables"]["2"] else 3
            s = "".join(r.choice(g["onsets"]) + r.choice(g["nuclei"]) + r.choice(g["codas"]) for _ in range(n))
            return s[0].upper() + s[1:]
        u = r.random()
        p3, p4 = g["L"]["3"], g["L"]["4"]
        n = 3 if u < p3 else (4 if u < p3 + p4 else 5)
        return "".join(r.choice(g["letters"]) for _ in range(n)) + "-" + "".join(
            r.choice(g["digits"]) for _ in range(self.p.random_digits))

    def form_ok(self, s, stratum):
        lo, hi = self.ng[stratum]["length_chars"]
        if not lo <= len(s) <= hi:
            return False
        return stratum != "natural" or len(self.ids(" " + s)) > self.p.natural_min_tokens_exclusive

    def clash(self, s, stratum, accepted):
        """reject_if against every string accepted so far (any cell, role, stratum)."""
        if stratum == "natural":
            low, k = s.lower(), self.p.natural_prefix_chars
            return any(a.lower() == low or a[:k] == s[:k] or lev_le1(a.lower(), low) for a in accepted)
        block, h = s.split("-")[0], self.p.random_max_hamming
        return any(a == s or a.split("-")[0] == block or (len(a) == len(s) and sum(x != y for x, y in zip(a, s)) <= h)
                   for a in accepted)

    def in_anchor(self, s):
        """Anchor rule: case-insensitive substring of any anchor text."""
        low = s.lower()
        return any(low in t for t in self.anchor_low)

    def pair(self, s):
        """(K_st, K_qa) = (len(encode(" " + s)), len(encode(s)))."""
        return (len(self.ids(" " + s)), len(self.ids(s)))

    def _stream(self, rel, st, role):
        return FZ.rng_rule(self.p.data_seed, "names:%s:%s:%s" % (rel, st, role))

    def _take(self, r, want, ok, cell, what):
        out, n = [], 0
        while len(out) < want:
            if n >= self.p.max_draws:
                raise ImplementationFail("%s stream exhausted in %s after %d draws" % (what, cell, n))
            s = self.draw(r, cell[1])
            n += 1
            if ok(s):
                out.append(s)
        return out, n

    def build(self):
        p = self.p
        per_cell = p.n_learned + p.n_unread
        accepted, facts, log = [], [], []
        for rel in p.relations:
            for st in p.strata:
                cell = (rel, st)
                ents, n_e = self._take(self._stream(rel, st, "entity"), per_cell,
                                       lambda s: self._accept(s, st, accepted), cell, "entity")
                survey, _ = self._take(self._stream(rel, st, "answer"), p.survey_size,
                                       lambda s: self.form_ok(s, st), cell, "survey")
                cnt = collections.Counter(self.pair(s) for s in survey)
                best = max(cnt.values())
                target = min(k for k, v in cnt.items() if v == best)
                ans, n_a = self._take(self._stream(rel, st, "answer"), per_cell,      # restarted stream
                                      lambda s: self._accept(s, st, accepted, target), cell, "answer")
                log.append({"cell": "%s/%s" % cell, "entity_draws": n_e, "target_pair": list(target), "answer_draws": n_a})
                for i, (e, a) in enumerate(zip(ents, ans)):
                    exposure = "learned" if i < p.n_learned else "unread"
                    idx = i + 1 if i < p.n_learned else i - p.n_learned + 1
                    fid = "%s-%s-%s-%s-%02d" % (p.fact_prefix, p.exposure_letter[exposure], rel, p.stratum_short[st], idx)
                    fact = {"fact_id": fid, "exposure": exposure, "relation": rel, "stratum": st, "entity": e, "answer": a}
                    if sorted(fact) != sorted(p.fact_fields):
                        raise ImplementationFail("fact fields %s differ from the manifest's %s" % (sorted(fact), p.fact_fields))
                    facts.append(fact)
        return facts, log

    def _accept(self, s, st, accepted, target=None):
        """Form rules, (for answers) the target (K_st, K_qa) pair, reject_if and the anchor rule, in the order of the
        reference; an accepted string joins the accepted set."""
        if (self.form_ok(s, st) and (target is None or self.pair(s) == target) and not self.clash(s, st, accepted)
                and not self.in_anchor(s)):
            accepted.append(s)
            return True
        return False


# ------------------------------------------------------------------------------------------------- texts (2.3-2.6)

def templates_by(fz):
    """{(relation, kind): [template rows in manifest order]}"""
    out = {}
    for t in fz.templates:
        out.setdefault((t["relation"], t["kind"]), []).append(t)
    return out


def fill(template, fact):
    return template["text"].replace("{E}", fact["entity"]).replace("{A}", fact["answer"])


def _one_template(tpl, rel, kind):
    rows = tpl.get((rel, kind), [])
    if len(rows) != 1:
        raise ImplementationFail("expected one %s template for %s, found %d" % (kind, rel, len(rows)))
    return rows[0]


def build_train_F(tpl, facts):
    """2.3: one TRAIN statement per learned fact, fact order. Rows {"fact_id", "template_id", "text"}."""
    out = []
    for f in facts:
        if f["exposure"] == "learned":
            t = _one_template(tpl, f["relation"], "TRAIN")
            out.append({"fact_id": f["fact_id"], "template_id": t["template_id"], "text": fill(t, f)})
    return out


def build_train_S(p, tpl, facts):
    """2.6 S, call order of detail 4 (reference: reports/round7/gen_s_cands.py, build_s)."""
    cells, out, attempts = {}, [], {}
    for f in facts:
        if f["exposure"] == "learned":
            cells.setdefault((f["relation"], f["stratum"]), []).append(f)
    for (rel, st), group in cells.items():          # insertion order = fact order = cell order of 2.2
        r = FZ.rng_rule(p.data_seed, "s-permutation:%s:%s" % (rel, st))
        n = 0
        while True:
            perm = list(range(len(group)))
            r.shuffle(perm)
            n += 1
            if all(perm[i] != i for i in range(len(perm))):
                break
        attempts["%s/%s" % (rel, st)] = n
        t = _one_template(tpl, rel, "TRAIN")
        for i, f in enumerate(group):
            g = group[perm[i]]
            out.append({"fact_id": f["fact_id"], "answer_fact_id": g["fact_id"],
                        "text": t["text"].replace("{E}", f["entity"]).replace("{A}", g["answer"])})
    return out, attempts


def build_train_Y(tpl, facts):
    """2.6 Y: per learned fact one Y_ENTITY and one Y_ANSWER sentence, separate sequences, fact order, entity first.
    Rows {"fact_id", "template_id", "kind", "text"}."""
    out = []
    for f in facts:
        if f["exposure"] == "learned":
            for kind in ("Y_ENTITY", "Y_ANSWER"):
                t = _one_template(tpl, f["relation"], kind)
                out.append({"fact_id": f["fact_id"], "template_id": t["template_id"], "kind": kind, "text": fill(t, f)})
    return out


def y_ratio(p, tok, train_F, train_Y):
    """2.6: Y tokens / F tokens over one pass, each sequence = text ids + <|endoftext|> (reference:
    reports/round2/y_ratio.py; Review Gate ruling on stage A item 3). Outside the frozen interval ->
    IMPLEMENTATION_FAIL. The ratio without the <|endoftext|> of each sequence is reported next to it (same ruling: both
    ratios are reported; only the ratio with <|endoftext|> is the protocol check)."""
    def n(rows):
        return sum(len(tok.encode(r["text"], add_special_tokens=False)) for r in rows)
    f_txt, y_txt = n(train_F), n(train_Y)
    f_tok, y_tok = f_txt + len(train_F), y_txt + len(train_Y)
    ratio = y_tok / f_tok
    lo, hi = p.y_ratio_bounds
    if not lo <= ratio <= hi:
        raise ImplementationFail("Y / F token ratio %.4f outside [%s, %s] (F %d, Y %d tokens)" % (ratio, lo, hi, f_tok, y_tok))
    return {"F_tokens": f_tok, "Y_tokens": y_tok, "ratio": ratio, "F_tokens_without_endoftext": f_txt,
            "Y_tokens_without_endoftext": y_txt, "ratio_without_endoftext": y_txt / f_txt, "bounds": [lo, hi]}


def build_dev_qa(p, tpl, facts):
    """2.3: DEV questions, every fact (learned and unread) x the DEV templates of its relation, fact order then
    template order. Rows {"fact_id", "template_id", "question"}."""
    out = []
    for f in facts:
        ts = tpl.get((f["relation"], "DEV"), [])
        if len(ts) != p.dev_per_fact:
            raise ImplementationFail("%s: %d DEV templates, the manifest says %d" % (f["relation"], len(ts), p.dev_per_fact))
        for t in ts:
            out.append({"fact_id": f["fact_id"], "template_id": t["template_id"], "question": fill(t, f)})
    return out


def build_candidates(p, facts):
    """2.5, call order of detail 5 (reference: reports/round7/gen_s_cands.py, build_candidates)."""
    out = {}
    for f in facts:
        pool = [g["answer"] for g in facts
                if g is not f and (g["relation"], g["stratum"], g["exposure"]) == (f["relation"], f["stratum"], f["exposure"])]
        if len(pool) < p.pool_min:
            raise ImplementationFail("distractor pool of %s has %d answers (< %d)" % (f["fact_id"], len(pool), p.pool_min))
        r = FZ.rng_rule(p.candidate_seed, "cand:%s" % f["fact_id"])
        c = [f["answer"]] + r.sample(pool, p.candidate_way - 1)
        r.shuffle(c)
        out[f["fact_id"]] = c
    return out


def check_exposure(facts, cands, corpora):
    """2.5 exposure matching: every candidate of a learned fact occurs exactly once (case-insensitive substring) in
    each training corpus of F (= L, A), S and Y; every candidate of an unread fact occurs zero times. A violation
    means the generated data do not have the property the protocol states -> IMPLEMENTATION_FAIL."""
    by_id = {f["fact_id"]: f for f in facts}
    bad = []
    for name, rows in corpora.items():
        low = "\n".join(r["text"] for r in rows).lower()
        for fid, cs in cands.items():
            want = 1 if by_id[fid]["exposure"] == "learned" else 0
            for c in cs:
                k = low.count(c.lower())
                if k != want:
                    bad.append("%s: candidate %r of %s occurs %d times (want %d)" % (name, c, fid, k, want))
    if bad:
        raise ImplementationFail("exposure matching (2.5) violated: %s" % "; ".join(bad[:10]))


# ------------------------------------------------------------------------------------------ general DEV (2.7, 3)

_ROW_HEAD = re.compile(rb'\{"domain": "[^"\\]*", "split": "([^"\\]*)", ')    # group 1: the split field only


def build_general_dev(p, tok, eval_sets_path, parcae_path):
    """2.7 general DEV windows (reference: reports/round5/l6_check.py). The file is read as bytes; only rows whose
    split field (matched on the raw bytes of the row prefix) is the DEV split are decoded to text and parsed (protocol
    section 3: parsing the split field and counting are not reading TEST; data-auditor stage B observation 1: no
    test row is even decoded from UTF-8). Window = the first general_max_tokens ids of the protocol
    tokenizer for the parcae-decoded text (special tokens skipped); text = decode of those ids (default arguments).
    Rows {"domain", "doc_id", "ids", "text"}, domains in manifest order, file order within a domain."""
    from tokenizers import Tokenizer
    ptok = Tokenizer.from_file(str(parcae_path))
    kept = collections.defaultdict(list)
    rows_by_split = collections.Counter()           # counted from the row prefix only (counting is not reading)
    want = p.general_dev_split.encode("ascii")
    with open(eval_sets_path, "rb") as fh:
        for lineno, line in enumerate(fh, 1):
            m = _ROW_HEAD.match(line)
            if m is None:
                raise ImplementationFail("eval_sets.jsonl line %d does not start with the domain and split fields" % lineno)
            rows_by_split[m.group(1).decode("ascii", "replace")] += 1      # the split field only
            if m.group(1) != want:
                continue
            r = json.loads(line.decode("utf-8"))
            if r["split"] != p.general_dev_split:
                raise ImplementationFail("eval_sets.jsonl line %d: parsed split differs from the row prefix" % lineno)
            if len(kept[r["domain"]]) < p.general_dev_per_domain:
                kept[r["domain"]].append(r)
    if sorted(kept) != sorted(p.general_domains) or any(len(kept[d]) != p.general_dev_per_domain for d in p.general_domains):
        raise ImplementationFail("general DEV: windows per domain %s" % {d: len(v) for d, v in kept.items()})
    out = []
    for d in p.general_domains:
        for r in kept[d]:
            ids = tok.encode(ptok.decode(r["tokens"], skip_special_tokens=True), add_special_tokens=False)[:p.general_max_tokens]
            out.append({"domain": d, "doc_id": r["doc_id"], "ids": ids, "text": tok.decode(ids)})
    return out, {"rows_by_split": dict(sorted(rows_by_split.items())), "decoded_rows": len(out)}


# ------------------------------------------------------------------------------------------------ all files (2.8)

def generate(fz, inputs_dir):
    """Build the 8 non-TEST files of 2.8 in memory. Every frozen hash is checked as soon as its content exists
    (ST12). Returns ({file name: bytes}, info). Files are in canonical form, so byte_sha256 == canonical_sha256."""
    p = params(fz)
    libraries = FZ.check_library_versions(fz.data_manifest)
    paths = check_inputs(fz, p, inputs_dir)
    tok = load_qwen_tokenizer(p, paths)
    anchor = build_anchor(p, tok, paths["anchor_parquet"])
    fz.check_content("anchor_texts", FZ.sha256_hex(FZ.canonical_bytes([r["text"] for r in anchor])))
    facts, name_log = NameGenerator(p, tok, [r["text"] for r in anchor]).build()
    fz.check_content("facts", FZ.sha256_hex(FZ.canonical_bytes(facts)))
    tpl = templates_by(fz)
    train_F = build_train_F(tpl, facts)
    train_S, s_attempts = build_train_S(p, tpl, facts)
    fz.check_content("train_S", FZ.sha256_hex(FZ.jsonl_bytes(train_S)))
    train_Y = build_train_Y(tpl, facts)
    ratio = y_ratio(p, tok, train_F, train_Y)
    dev_qa = build_dev_qa(p, tpl, facts)
    cands = build_candidates(p, facts)
    fz.check_content("candidates", FZ.sha256_hex(FZ.canonical_bytes(cands)))
    check_exposure(facts, cands, {"train_F": train_F, "train_S": train_S, "train_Y": train_Y})
    general, general_stats = build_general_dev(p, tok, paths["eval_sets"], paths["parcae_tokenizer"])
    files = {
        "facts.jsonl": FZ.jsonl_bytes(facts),
        "train_F.jsonl": FZ.jsonl_bytes(train_F),
        "train_S.jsonl": FZ.jsonl_bytes(train_S),
        "train_Y.jsonl": FZ.jsonl_bytes(train_Y),
        "dev_qa.jsonl": FZ.jsonl_bytes(dev_qa),
        "candidates.json": FZ.canonical_bytes(cands),
        "general_dev.jsonl": FZ.jsonl_bytes(general),
        "anchor_text.jsonl": FZ.jsonl_bytes(anchor),
    }
    assert tuple(files) == DATA_FILES
    info = {"python": platform.python_version(), "libraries": libraries,
            "name_log": name_log, "s_attempts": s_attempts, "y_ratio": ratio, "general_dev": general_stats,
            "rows": {"facts.jsonl": len(facts), "train_F.jsonl": len(train_F), "train_S.jsonl": len(train_S),
                     "train_Y.jsonl": len(train_Y), "dev_qa.jsonl": len(dev_qa), "candidates.json": len(cands),
                     "general_dev.jsonl": len(general), "anchor_text.jsonl": len(anchor)}}
    return files, info


def write(files, out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    present = [n for n in TEST_FILES if (out / n).exists()]
    if present:
        raise ImplementationFail("output directory %s holds TEST files %s; data generation does not touch TEST" % (out, present))
    for name, blob in files.items():
        (out / name).write_bytes(blob)


def file_hashes(data_dir):
    """byte_sha256 and canonical_sha256 (protocol section 0) of each data file, read back from disk."""
    d = Path(data_dir)
    out = {}
    for name in DATA_FILES:
        raw = (d / name).read_bytes()
        if name.endswith(".jsonl"):
            canon = FZ.jsonl_bytes(FZ.parse_jsonl(raw))
        else:
            canon = FZ.canonical_bytes(json.loads(raw))
        out[name] = {"byte_sha256": FZ.sha256_hex(raw), "canonical_sha256": FZ.sha256_hex(canon)}
    return out


def verify(fz, inputs_dir, data_dir):
    """ST12 at the start of a step (protocol section 11; Implementation Task Order V1 section 6 item 10):
    (a) the input files against their frozen file-byte hashes, (b) the four frozen content hashes of the files in
    data_dir, (c) every data file byte-identical to its regeneration from the checked inputs and the frozen
    manifests (train_F, train_Y, dev_qa, general_dev and the ids of anchor_text have no frozen hash of their own;
    they are fixed functions of frozen values). Raises ST12Error on any difference."""
    content = fz.check_data_dir(data_dir)
    files, _ = generate(fz, inputs_dir)
    d = Path(data_dir)
    for name, blob in files.items():
        try:
            on_disk = (d / name).read_bytes()
        except OSError as e:
            raise ST12Error("%s: cannot read %s: %r" % (name, d / name, e)) from e
        if on_disk != blob:
            raise ST12Error("%s in %s differs from its regeneration from the frozen inputs" % (name, d))
    return content


# --------------------------------------------------------------------------------------------------------- command

def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m metrix_e1.data")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a1 = sub.add_parser("fetch")
    a1.add_argument("--inputs", required=True)
    a2 = sub.add_parser("generate")
    a2.add_argument("--inputs", required=True)
    a2.add_argument("--out", required=True)
    a3 = sub.add_parser("verify")
    a3.add_argument("--inputs", required=True)
    a3.add_argument("--data", required=True)
    a = ap.parse_args(argv)
    fz = FZ.load()
    print("frozen: PROTOCOL_FROZEN %s, commit %s; four frozen files match by git cat-file" % (fz.record.version, fz.record.commit))
    if a.cmd == "fetch":
        for key, sha in fetch_inputs(fz, a.inputs).items():
            print("%-28s sha256 %s = frozen" % (key, sha))
    elif a.cmd == "generate":
        files, info = generate(fz, a.inputs)
        write(files, a.out)
        print("python %s; libraries %s (protocol section 0: %s)" % (
            info["python"], json.dumps(info["libraries"]), json.dumps(fz.data_manifest["model"]["libraries"])))
        print("name generation per cell:", json.dumps(info["name_log"]))
        print("S derangement attempts per cell:", json.dumps(info["s_attempts"]))
        yr = info["y_ratio"]
        print("Y / F token ratio: F %(F_tokens)d, Y %(Y_tokens)d, ratio %(ratio).4f" % yr)
        print("Y / F token ratio without <|endoftext|> (report only): F %(F_tokens_without_endoftext)d, Y "
              "%(Y_tokens_without_endoftext)d, ratio %(ratio_without_endoftext).4f" % yr)
        print("both ratios within [%s, %s]: with %s, without %s" % (
            yr["bounds"][0], yr["bounds"][1], yr["bounds"][0] <= yr["ratio"] <= yr["bounds"][1],
            yr["bounds"][0] <= yr["ratio_without_endoftext"] <= yr["bounds"][1]))
        print("eval_sets.jsonl rows by split (row prefix only): %(rows_by_split)s; rows parsed and decoded: %(decoded_rows)d"
              % info["general_dev"])
        for name, h in file_hashes(a.out).items():
            print("%-18s rows %4d  byte_sha256 %s  canonical_sha256 %s" % (name, info["rows"][name], h["byte_sha256"], h["canonical_sha256"]))
        for key, sha in fz.check_data_dir(a.out).items():
            print("frozen content hash %-12s %s = PROTOCOL_FROZEN (read back from %s)" % (key, sha, a.out))
    else:
        for key, sha in verify(fz, a.inputs, a.data).items():
            print("frozen content hash %-12s %s = PROTOCOL_FROZEN" % (key, sha))
        print("all %d data files byte-identical to their regeneration from the frozen inputs" % len(DATA_FILES))
    print("RESULT: PASS")
    sys.exit(0)


if __name__ == "__main__":
    run_guarded(main)
