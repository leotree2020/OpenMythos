"""ic9_02 (implementation stage C, C2 second fix commit (staged tree a6ce8a0e, parent 0cbee197), round 1; my ic8_02 run again; task 2 / definition
items 2-4): L1-L6 (Gate 0 part), candidate feasibility under the four constraints and the split, recomputed by my own
code on the data directory the smoke test wrote (<smoke>/data; byte-identical to the stage-A/B data per ic9_01 C), and
compared with the smoke's leakage report (records/step2_record.json "leakage") value by value and detail by detail, and
with my stage-A records for the byte-identical data (audit/stdout/impl_a/18_ia_leakage_gen4.txt,
20_ia_feasibility_gen4.txt). The rules are those of my ic6_06 (written again here, my own code).
  L1  normalized-template sha256 shared by two different sets (TRAIN / DEV / TEST / Y) of the frozen SPLIT_MANIFEST
      templates; L2 max Jaccard of word 4-gram sets over template pairs of different sets (template text only).
  L3a unread entities / answers (case-insensitive substring count) in train_F, train_S, train_Y, anchor text;
  L3b learned answers in the anchor text; L4 the 320 DEV questions verbatim in train_F/S/Y and the anchor text;
  L5 learned / unread fact_id overlap + duplicate entity / answer strings; L6 distinct word 13-grams (str.split) shared
      by the 512 anchor documents and the 100 general DEV windows (texts = Qwen decode of the stored ids, compared with
      the stored text); report only: shared token-id 13-grams.
  feasibility: cell (relation, stratum, exposure); K_st = len(encode(" " + answer)); per fact the answers of its cell
      with the same K_st (own answer included) = available, pool = available - 1; minimum, cells with available < 4 or
      pool < 4; every candidates.json list: 4 distinct strings, the true answer once, all from the fact's cell, one
      (K_st, K_qa).
  split: 160 distinct fact_ids, learned 120 / unread 40, 15 + 5 per relation x stratum, disjoint; TRAIN files only
      learned facts (F, S once each, S answer same cell not itself, once each; Y twice: Y_ENTITY + Y_ANSWER); DEV
      every fact twice, once per DEV template of its relation; candidates keys = fact_ids; general DEV 25 per domain;
      anchor 512; no TEST file in <smoke>/data (directory listing only).
Tokenizer only (pinned Qwen tokenizer files); no model, no weights. Data Auditor's own script; no Executor code imported,
called or copied.
usage: python -I -B ic9_02_data_recheck.py <repo_root> <qwen_tok_dir> <smoke_work_dir>"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json
import re
from collections import Counter
from itertools import combinations
from ia_common import RELS, STRATA, DOMAINS, sha, frozen_json, read_jsonl, load_qwen, enc, run

ID_RE = re.compile(r"E1P-(L|U)-(capital|currency|founder|river)-(nat|rnd)-(\d\d)")
STAGE_A = "metrix/e1-pilot/audit/stdout/impl_a/"
CHECKS = ("L1", "L2", "L3a", "L3b", "L4", "L5", "L6")


def normalize(text):
    s = text.replace("{E}", "<ENTITY>").replace("{A}", "<ANSWER>").lower()
    s = "".join(c if c in "abcdefghijklmnopqrstuvwxyz0123456789<> " else " " for c in s)
    return re.sub(r" {2,}", " ", s).strip(" ")


def ngrams(seq, n):
    return {tuple(seq[i:i + n]) for i in range(len(seq) - n + 1)}


def recorded(repo, fname):
    t = open(os.path.join(repo, STAGE_A + fname), encoding="utf-8").read()
    return dict(re.findall(r"^AUDIT_VALUE (\S+) (\S+)$", t, re.M)), t


def main():
    repo, qdir, work = sys.argv[1:4]
    dd = os.path.join(work, "data")
    ok = True
    sm, dm = frozen_json(repo, "SPLIT_MANIFEST.json"), frozen_json(repo, "DATA_MANIFEST.json")
    lc = sm["leakage_checks"]
    limits = {"L1": lc["L1_template_hash"]["limit"], "L2": lc["L2_template_ngram"]["limit"],
              "L3a": lc["L3a_unread_fact"]["limit"], "L3b": lc["L3b_learned_answer_in_anchor"]["limit"],
              "L4": lc["L4_question_text"]["limit"], "L5": lc["L5_identity"]["limit"], "L6": lc["L6_general_text"]["limit"]}
    print("limits (frozen-commit SPLIT_MANIFEST): %s" % limits)
    tok = load_qwen(qdir)
    facts = read_jsonl(os.path.join(dd, "facts.jsonl"))
    F = read_jsonl(os.path.join(dd, "train_F.jsonl"))
    S = read_jsonl(os.path.join(dd, "train_S.jsonl"))
    Y = read_jsonl(os.path.join(dd, "train_Y.jsonl"))
    D = read_jsonl(os.path.join(dd, "dev_qa.jsonl"))
    A = read_jsonl(os.path.join(dd, "anchor_text.jsonl"))
    GD = read_jsonl(os.path.join(dd, "general_dev.jsonl"))
    cands = json.load(open(os.path.join(dd, "candidates.json"), encoding="utf-8"))

    print("\n== L1-L6 (Gate 0 part), mine")
    T = sm["templates"]
    sets = {}
    for t in T:
        sets.setdefault(t["set"], set()).add(sha(normalize(t["text"]).encode("utf-8")))
    shared = sorted({h for a, b in combinations(sorted(sets), 2) for h in sets[a] & sets[b]})
    best, at = -1.0, []
    for a, b in combinations(T, 2):
        if a["set"] == b["set"]:
            continue
        ga, gb = ngrams(normalize(a["text"]).split(" "), 4), ngrams(normalize(b["text"]).split(" "), 4)
        j = 0.0 if not (ga or gb) else len(ga & gb) / len(ga | gb)
        if j > best + 1e-12:
            best, at = j, [(a["template_id"], b["template_id"])]
        elif abs(j - best) <= 1e-12:
            at.append((a["template_id"], b["template_id"]))
    a_dec = [tok.decode(r["ids"]) for r in A]
    g_dec = [tok.decode(r["ids"]) for r in GD]
    dec_ok = all(x == r["text"] for x, r in zip(a_dec, A)) and all(x == r["text"] for x, r in zip(g_dec, GD))
    print("anchor: decode(ids) == text for %d of %d | general DEV: decode(ids) == text for %d of %d" % (
        sum(x == r["text"] for x, r in zip(a_dec, A)), len(A), sum(x == r["text"] for x, r in zip(g_dec, GD)), len(GD)))
    ok &= dec_ok
    corp = {"train_F": [r["text"] for r in F], "train_S": [r["text"] for r in S], "train_Y": [r["text"] for r in Y],
            "anchor_text": a_dec}
    low = {k: [t.lower() for t in v] for k, v in corp.items()}
    unread = [f for f in facts if f["exposure"] == "unread"]
    learned = [f for f in facts if f["exposure"] == "learned"]
    u_strings = [f["entity"] for f in unread] + [f["answer"] for f in unread]
    l3a = sum(t.count(s.lower()) for s in u_strings for k in corp for t in low[k])
    l3b = sum(t.count(f["answer"].lower()) for f in learned for t in low["anchor_text"])
    qs = [r["question"] for r in D]
    l4 = sum(t.count(q) for q in qs for k in corp for t in corp[k])
    l4i = sum(t.count(q.lower()) for q in qs for k in corp for t in low[k])
    ids_l, ids_u = {f["fact_id"] for f in learned}, {f["fact_id"] for f in unread}
    strings = [x for f in facts for x in (f["entity"], f["answer"])]
    overlap, dup = len(ids_l & ids_u), len(strings) - len(set(strings))
    aw = set().union(*(ngrams(t.split(), 13) for t in a_dec))
    gw = set().union(*(ngrams(t.split(), 13) for t in g_dec))
    tok_shared = len(set().union(*(ngrams(r["ids"], 13) for r in A)) & set().union(*(ngrams(r["ids"], 13) for r in GD)))
    mine = {"L1": len(shared), "L2": best, "L3a": l3a, "L3b": l3b, "L4": l4, "L5": overlap + dup, "L6": len(aw & gw)}
    print("L2 maximum %s at %s | L4 case-insensitive %d | L6 token-id 13-grams shared (report only) %d | template sets %s" % (
        best, at, l4i, tok_shared, {k: len(v) for k, v in sets.items()}))

    print("\n== comparison with the smoke's step2_record.json leakage report and my stage-A record")
    s2 = json.load(open(os.path.join(work, "records", "step2_record.json"), encoding="utf-8"))
    rep = s2["leakage"]
    print("step2_record mode %r label %r | report part %r result %r" % (s2.get("mode"), s2.get("label"), rep.get("part"),
                                                                       rep.get("result")))
    ok &= s2.get("mode") == "smoke" and rep.get("part") == "gate0" and sorted(rep["checks"]) == sorted(CHECKS)
    rec18, t18 = recorded(repo, "18_ia_leakage_gen4.txt")
    for c in CHECKS:
        x = rep["checks"][c]
        r = rec18.get("leakage:" + c)
        same = float(x["value"]) == float(mine[c]) and r is not None and float(r) == float(mine[c])
        within = mine[c] <= limits[c]
        print("  %-4s mine %-6s | smoke report value %-6s limit %-5s within_limit %-5s | my stage-A %-6s | equal %s | "
              "limit (frozen) %s, within %s" % (c, mine[c], x["value"], x["limit"], x["within_limit"], r, same, limits[c], within))
        ok &= same and within and x["limit"] == limits[c] and x["within_limit"] is True
    det = {c: rep["checks"][c].get("detail", {}) for c in CHECKS}
    my_det = {
        "L1": {"shared_hashes": shared},
        "L2": {"n": 4, "pair_in_my_maxima": tuple(det["L2"].get("pair", ())) in at},
        "L3a": {"strings": len(u_strings), "found": {}, "corpora": sorted(corp)},
        "L3b": {"strings": len(learned), "found": {}},
        "L4": {"questions": len(qs), "found": {}, "corpora": sorted(corp), "part": "DEV"},
        "L5": {"duplicate_strings": dup, "fact_id_overlap": overlap, "learned": len(ids_l), "unread": len(ids_u),
               "strings": len(strings)},
        "L6": {"anchor_documents": len(A), "windows": len(GD), "n": 13, "report_only_token_id_ngrams": tok_shared,
               "examples": []},
    }
    for c in CHECKS:
        exp = my_det[c]
        got = {k: det[c].get(k) for k in exp if k != "pair_in_my_maxima"}
        if c == "L2":
            eq = det[c].get("n") == 4 and exp["pair_in_my_maxima"]
            print("  %-4s detail %s | the report's pair %s is one of my maximal pairs: %s" % (c, det[c], det[c].get("pair"), eq))
        else:
            mine_cmp = {k: v for k, v in exp.items()}
            got_cmp = {k: (sorted(v) if isinstance(v, list) and k == "corpora" else v) for k, v in got.items()}
            eq = got_cmp == mine_cmp
            print("  %-4s detail (report) %s | mine %s | equal %s" % (c, got_cmp, mine_cmp, eq))
        ok &= eq
    print("  report result PASS and every check within its limit: %s" % (rep.get("result") == "PASS"))
    ok &= rep.get("result") == "PASS"
    aut = lc["L2_template_ngram"].get("authoring_result", {})
    print("  frozen authoring_result L2 %s (max == mine: %s)" % (aut, aut.get("max") == best))

    print("\n== candidate feasibility (four constraints)")
    K = {f["answer"]: (len(enc(tok, " " + f["answer"])), len(enc(tok, f["answer"]))) for f in facts}
    low_a, low_p, mins = [], [], []
    for rel in RELS:
        for st in STRATA:
            ks = Counter(K[f["answer"]] for f in facts if (f["relation"], f["stratum"]) == (rel, st))
            for ex in ("learned", "unread"):
                cell = [f for f in facts if (f["relation"], f["stratum"], f["exposure"]) == (rel, st, ex)]
                avail = [sum(1 for g in cell if K[g["answer"]][0] == K[f["answer"]][0]) for f in cell]
                ma = min(avail)
                mins.append(ma)
                print("  %-24s n %2d (K_st, K_qa) %-14s min available %2d min pool %2d" % (
                    "%s/%s/%s" % (rel, st, ex), len(cell), dict(Counter(K[f["answer"]] for f in cell)), ma, ma - 1))
                if ma < 4:
                    low_a.append((rel, st, ex))
                if ma - 1 < 4:
                    low_p.append((rel, st, ex))
            ok &= len(ks) == 1
    rec20, _ = recorded(repo, "20_ia_feasibility_gen4.txt")
    print("minimum available %d (stage-A record %s) | minimum pool %d (stage-A record %s) | cells with available < 4: %s "
          "| cells with pool < 4: %s" % (min(mins), rec20.get("feasibility:min_available"), min(mins) - 1,
                                         rec20.get("feasibility:min_pool"), low_a, low_p))
    ok &= not low_a and not low_p and str(min(mins)) == rec20.get("feasibility:min_available") and \
        str(min(mins) - 1) == rec20.get("feasibility:min_pool")
    by_id = {f["fact_id"]: f for f in facts}
    bad = []
    for fid, c in cands.items():
        f = by_id.get(fid)
        if f is None:
            bad.append((fid, "unknown"))
            continue
        cell_ans = {g["answer"] for g in facts if (g["relation"], g["stratum"], g["exposure"]) ==
                    (f["relation"], f["stratum"], f["exposure"])}
        kc = {(len(enc(tok, " " + x)), len(enc(tok, x))) for x in c}
        if not (len(c) == 4 and len(set(c)) == 4 and c.count(f["answer"]) == 1 and set(c) <= cell_ans and len(kc) == 1):
            bad.append((fid, c))
    pos = Counter(c.index(by_id[fid]["answer"]) for fid, c in cands.items() if fid in by_id)
    print("candidates.json: %d lists | violating the four constraints: %d %s | position of the true answer %s" % (
        len(cands), len(bad), bad[:3], dict(sorted(pos.items()))))
    ok &= len(cands) == 160 and set(cands) == set(by_id) and not bad

    print("\n== split")
    ids = [f["fact_id"] for f in facts]
    L, U = set(ids_l), set(ids_u)
    fmt = all(ID_RE.fullmatch(i) for i in ids)
    lu = all((ID_RE.fullmatch(f["fact_id"]).group(1) == "L") == (f["exposure"] == "learned")
             and ID_RE.fullmatch(f["fact_id"]).group(2) == f["relation"]
             and ID_RE.fullmatch(f["fact_id"]).group(3) == {"natural": "nat", "random": "rnd"}[f["stratum"]] for f in facts)
    cells = Counter((f["relation"], f["stratum"], f["exposure"]) for f in facts)
    cell_ok = all(cells[(r, s, "learned")] == 15 and cells[(r, s, "unread")] == 5 for r in RELS for s in STRATA)
    print("facts %d distinct %d | learned %d unread %d | learned & unread %d | id format %s | letter / relation / stratum "
          "consistent %s | 8 cells x (15 + 5) %s | frozen DATA_MANIFEST facts %s" % (
              len(ids), len(set(ids)), len(L), len(U), len(L & U), fmt, lu, cell_ok,
              {k: dm["facts"][k] for k in ("total", "learned", "unread")}))
    ok &= len(ids) == len(set(ids)) == dm["facts"]["total"] == 160 and len(L) == dm["facts"]["learned"] == 120 \
        and len(U) == dm["facts"]["unread"] == 40 and not (L & U) and fmt and lu and cell_ok
    cell_of = {f["fact_id"]: (f["relation"], f["stratum"]) for f in facts}
    fF, fS, fY = Counter(r["fact_id"] for r in F), Counter(r["fact_id"] for r in S), Counter(r["fact_id"] for r in Y)
    aS = Counter(r["answer_fact_id"] for r in S)
    tr_ok = (len(F) == 120 and set(fF) == L and set(fF.values()) == {1} and len(S) == 120 and set(fS) == L
             and set(fS.values()) == {1} and set(aS) == L and set(aS.values()) == {1}
             and all(r["fact_id"] != r["answer_fact_id"] and cell_of[r["fact_id"]] == cell_of[r["answer_fact_id"]] for r in S)
             and len(Y) == 240 and set(fY) == L and set(fY.values()) == {2}
             and all(sorted(r["kind"] for r in Y if r["fact_id"] == i) == ["Y_ANSWER", "Y_ENTITY"] for i in L))
    unread_in_train = sorted((set(fF) | set(fS) | set(aS) | set(fY)) & U)
    print("TRAIN train_F %d train_S %d train_Y %d | unread fact_ids in TRAIN %s | F, S once, S answer same cell not "
          "itself once, Y twice (Y_ENTITY + Y_ANSWER): %s" % (len(F), len(S), len(Y), unread_in_train, tr_ok))
    ok &= tr_ok and not unread_in_train
    dev_t = {r: sorted(t["template_id"] for t in T if t["relation"] == r and t["kind"] == "DEV") for r in RELS}
    fD = Counter(r["fact_id"] for r in D)
    dev_ok = (len(D) == 320 and set(fD) == set(ids) and set(fD.values()) == {2}
              and all(sorted(r["template_id"] for r in D if r["fact_id"] == f["fact_id"]) == dev_t[f["relation"]]
                      for f in facts))
    gd = Counter(r["domain"] for r in GD)
    print("DEV dev_qa %d, every fact twice, once per DEV template of its relation: %s | candidates keys == fact_ids %s | "
          "general DEV %d per domain %s | anchor %d" % (len(D), dev_ok, set(cands) == set(ids), len(GD), dict(gd), len(A)))
    ok &= dev_ok and len(GD) == 100 and all(gd[d] == 25 for d in DOMAINS) and len(A) == 512
    listing = sorted(os.listdir(dd))
    print("data dir listing %s | names with 'test': %s" % (listing, [x for x in listing if "test" in x.lower()]))
    ok &= not [x for x in listing if "test" in x.lower()]
    return bool(ok)


run(main)
