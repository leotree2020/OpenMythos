"""Leakage checks L1-L6 of METRIX E1-PILOT.

Protocol v1.1 section 3 ("泄漏检查(6 项,全部可执行)", "执行接口") and SPLIT_MANIFEST.json leakage_checks; section 8
step 2 and G0.1; section 11 ST1. Rules, limits and n-gram orders are read from the frozen SPLIT_MANIFEST.json.

Gate 0 part (G0.1; section 8 step 2), computed by run_gate0():
  L1   normalized_sha256 values shared between the TRAIN, DEV, TEST and Y template sets         limit from manifest
  L2   max word n-gram Jaccard over template pairs from different sets                          limit from manifest
  L3a  occurrences (case-insensitive substring) of every unread entity and unread answer in train_F, train_S,
       train_Y and anchor_text
  L3b  occurrences (case-insensitive substring) of every learned answer in anchor_text
  L4   occurrences (verbatim) of every instantiated DEV question in every training corpus: train_F, train_S,
       train_Y and anchor_text (arm A trains on the anchor documents)
  L5   learned / unread fact_id overlap + duplicates among the 320 entity and answer strings
  L6   distinct word 13-grams (word = str.split(), case-sensitive; 13-grams within each document) shared between the
       512 anchor documents and the general DEV windows, each text being the decode of the ids fed to the model;
       Qwen token-id 13-grams of the same ids are reported, no limit
L1 and L2 use the 32 frozen templates only (template texts, including the TEST templates, are part of the protocol;
no TEST question is instantiated).

TEST part (section 8 step 8: L3-L5 on TEST after test_qa.jsonl exists; L6 anchor vs general_test.jsonl): not executed
by this module in Implementation stage A and not reachable from its command line; the step 8 wiring is built in a
later stage behind the TEST generator's preconditions. The counting functions below take in-memory lists and read no
file, so the same functions serve both parts.

Command (protocol section 3 interface; also reachable as python -m metrix.e1_pilot.check_leakage):
  python -m metrix_e1.leakage --data <DATA_DIR> --split-manifest metrix/e1-pilot/SPLIT_MANIFEST.json \
      --out <DATA_DIR>/leakage_report.json
Before the checks the command runs the ST12 range (1) check of the data directory (the four content hashes of
PROTOCOL_FROZEN, frozen.Frozen.check_data_dir); a difference stops it (ST12) without a report.
Exit code 0 only if every Gate 0 check is within its limit (RESULT: PASS); otherwise RESULT: FAIL and exit 1.
"""
import argparse
import itertools
import json
import re
import sys
from pathlib import Path

from . import frozen as FZ
from ._cli import run_guarded
from .errors import ImplementationFail, ST12Error

CHECKS = ("L1", "L2", "L3a", "L3b", "L4", "L5", "L6")


def _rules(split_manifest):
    """Limits and n-gram orders of the six checks, from the frozen SPLIT_MANIFEST.json."""
    lc = split_manifest["leakage_checks"]
    m2 = re.fullmatch(r"Jaccard overlap of word (\d+)-gram sets of normalized templates, every pair from different sets",
                      lc["L2_template_ngram"]["rule"])
    m6 = re.fullmatch(r"word (\d+)-grams shared between anchor_text and general_dev / general_test; word = an element of "
                      r"Python str\.split\(\) \(split on whitespace, case-sensitive\)", lc["L6_general_text"]["rule"])
    if m2 is None or m6 is None:
        raise ImplementationFail("L2 / L6 rule text of the frozen manifest is not the form the implementation expects")
    return {
        "limits": {"L1": lc["L1_template_hash"]["limit"], "L2": lc["L2_template_ngram"]["limit"],
                   "L3a": lc["L3a_unread_fact"]["limit"], "L3b": lc["L3b_learned_answer_in_anchor"]["limit"],
                   "L4": lc["L4_question_text"]["limit"], "L5": lc["L5_identity"]["limit"],
                   "L6": lc["L6_general_text"]["limit"]},
        "l2_n": int(m2.group(1)),
        "l6_n": int(m6.group(1)),
    }


# --------------------------------------------------------------------------------------------- counting functions

def l1_template_hash(templates):
    """L1: number of normalized_sha256 values that occur in more than one of the four template sets."""
    sets_of = {}
    for t in templates:
        h = FZ.sha256_hex(FZ.normalize_template(t["text"]).encode("utf-8"))
        sets_of.setdefault(h, set()).add(t["set"])
    shared = sorted(h for h, s in sets_of.items() if len(s) > 1)
    return len(shared), {"shared_hashes": shared}


def word_ngrams(words, n):
    return {tuple(words[i:i + n]) for i in range(len(words) - n + 1)}


def l2_template_ngram(templates, n):
    """L2: maximum Jaccard overlap of the word n-gram sets of two normalized templates from different sets (a
    template with fewer than n words has no n-gram; its Jaccard with any template is 0)."""
    best, pair = 0.0, None
    for x, y in itertools.combinations(templates, 2):
        if x["set"] == y["set"]:
            continue
        gx = word_ngrams(FZ.normalize_template(x["text"]).split(), n)
        gy = word_ngrams(FZ.normalize_template(y["text"]).split(), n)
        j = len(gx & gy) / len(gx | gy) if gx and gy else 0.0
        if pair is None or j > best:
            best, pair = j, [x["template_id"], y["template_id"]]
    return best, {"pair": pair}


def substring_hits(strings, corpora, case_insensitive):
    """Occurrences of every string in every corpus (a corpus = list of texts; counts are summed over texts, never
    across text boundaries). Returns (total, {corpus: {string: count}} with non-zero counts only)."""
    total, found = 0, {}
    for name, texts in corpora.items():
        texts = [t.lower() for t in texts] if case_insensitive else list(texts)
        for s in strings:
            key = s.lower() if case_insensitive else s
            k = sum(t.count(key) for t in texts)
            if k:
                found.setdefault(name, {})[s] = k
                total += k
    return total, found


def l5_identity(facts):
    """L5: |learned fact_ids & unread fact_ids| + (number of entity and answer strings - number of distinct ones)."""
    learned = {f["fact_id"] for f in facts if f["exposure"] == "learned"}
    unread = {f["fact_id"] for f in facts if f["exposure"] == "unread"}
    strings = [f["entity"] for f in facts] + [f["answer"] for f in facts]
    overlap, dup = len(learned & unread), len(strings) - len(set(strings))
    return overlap + dup, {"fact_id_overlap": overlap, "duplicate_strings": dup, "learned": len(learned),
                           "unread": len(unread), "strings": len(strings)}


def shared_ngrams(docs_a, docs_b, n):
    """Distinct n-grams shared by two document collections; n-grams are taken within each document and merged into
    one set per collection (protocol section 3, L6). A document is a sequence (words or token ids)."""
    a = set().union(*(word_ngrams(list(d), n) for d in docs_a))
    b = set().union(*(word_ngrams(list(d), n) for d in docs_b))
    return a & b


def l6_general_text(anchor_rows, window_rows, n):
    """L6: word n-grams (str.split(), case-sensitive) of the decoded texts; report only: token-id n-grams of the
    ids fed to the model."""
    words = shared_ngrams([r["text"].split() for r in anchor_rows], [r["text"].split() for r in window_rows], n)
    ids = shared_ngrams([r["ids"] for r in anchor_rows], [r["ids"] for r in window_rows], n)
    return len(words), {"report_only_token_id_ngrams": len(ids), "examples": [list(g) for g in sorted(words)[:5]]}


# ------------------------------------------------------------------------------------------------ Gate 0 part (G0.1)

def load_data(data_dir):
    """The non-TEST files the Gate 0 part needs (no TEST file is opened)."""
    d = Path(data_dir)
    return {name: FZ.read_jsonl(d / ("%s.jsonl" % name))
            for name in ("facts", "train_F", "train_S", "train_Y", "dev_qa", "anchor_text", "general_dev")}


def run_gate0(split_manifest, data):
    """All Gate 0 checks. Returns the report dict (value, limit, within_limit and details per check)."""
    rules = _rules(split_manifest)
    facts = data["facts"]
    corpora = {"train_F": [r["text"] for r in data["train_F"]], "train_S": [r["text"] for r in data["train_S"]],
               "train_Y": [r["text"] for r in data["train_Y"]], "anchor_text": [r["text"] for r in data["anchor_text"]]}
    unread = [s for f in facts if f["exposure"] == "unread" for s in (f["entity"], f["answer"])]
    learned_answers = [f["answer"] for f in facts if f["exposure"] == "learned"]
    out = {}
    out["L1"] = l1_template_hash(split_manifest["templates"])
    out["L2"] = l2_template_ngram(split_manifest["templates"], rules["l2_n"])
    out["L2"][1]["n"] = rules["l2_n"]
    total, found = substring_hits(unread, corpora, case_insensitive=True)
    out["L3a"] = (total, {"strings": len(unread), "corpora": sorted(corpora), "found": found})
    total, found = substring_hits(learned_answers, {"anchor_text": corpora["anchor_text"]}, case_insensitive=True)
    out["L3b"] = (total, {"strings": len(learned_answers), "found": found})
    questions = [r["question"] for r in data["dev_qa"]]
    total, found = substring_hits(questions, corpora, case_insensitive=False)
    out["L4"] = (total, {"part": "DEV", "questions": len(questions), "corpora": sorted(corpora), "found": found})
    out["L5"] = l5_identity(facts)
    out["L6"] = l6_general_text(data["anchor_text"], data["general_dev"], rules["l6_n"])
    out["L6"][1].update({"part": "DEV (anchor_text vs general_dev)", "n": rules["l6_n"],
                         "anchor_documents": len(data["anchor_text"]), "windows": len(data["general_dev"])})
    report = {"part": "gate0", "checks": {}}
    for c in CHECKS:
        value, detail = out[c]
        limit = rules["limits"][c]
        report["checks"][c] = {"value": value, "limit": limit, "within_limit": value <= limit, "detail": detail}
    report["result"] = "PASS" if all(v["within_limit"] for v in report["checks"].values()) else "FAIL"
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m metrix.e1_pilot.check_leakage")
    ap.add_argument("--data", required=True)
    ap.add_argument("--split-manifest", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    fz = FZ.load()
    with open(a.split_manifest, encoding="utf-8") as fh:
        given = json.load(fh)
    if FZ.strip_step1_fields(FZ.SPLIT_MANIFEST_REL, given) != FZ.strip_step1_fields(FZ.SPLIT_MANIFEST_REL, fz.split_manifest):
        raise ST12Error("--split-manifest %s differs from SPLIT_MANIFEST.json at the frozen commit" % a.split_manifest)
    for key, sha in fz.check_data_dir(a.data).items():
        print("ST12 range (1): %-12s %s = PROTOCOL_FROZEN" % (key, sha))
    report = run_gate0(fz.split_manifest, load_data(a.data))
    report["frozen_commit"] = fz.record.commit
    Path(a.out).write_text(json.dumps(report, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    for c, v in report["checks"].items():
        print("%-4s value %-22r limit %-5r %s" % (c, v["value"], v["limit"], "within limit" if v["within_limit"] else "OVER LIMIT"))
    print("L6 report only: shared Qwen token-id %d-grams %d" % (
        report["checks"]["L6"]["detail"]["n"], report["checks"]["L6"]["detail"]["report_only_token_id_ngrams"]))
    print("report written to %s" % a.out)
    print("RESULT: %s" % report["result"])
    sys.exit(0 if report["result"] == "PASS" else 1)


if __name__ == "__main__":
    run_guarded(main)
