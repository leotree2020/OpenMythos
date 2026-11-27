"""ic9_01 (implementation stage C, C2 second fix commit (staged tree a6ce8a0e, parent 0cbee197), round 1; my ic8_01 rewritten for this round; task 1 / definition
item 1): hashes of the data directory the smoke test wrote (<smoke>/data), recomputed by my own code, against
PROTOCOL_FROZEN, the frozen-commit manifests and the smoke's records step1_record.json (file_hashes, content_hashes)
and step1_manifest_fields.json (the fields formal step 1 would write into the two manifests).
  A. PROTOCOL_FROZEN read by my own method (current-version section, frozen commit, table "全部数据哈希"): the four
     content rows and the template-set row, each value equal to the frozen-commit manifest location it names.
  B. the four content hashes from <smoke>/data by the protocol rules (section 0 canonical JSON / JSONL; facts: the six
     fields of every line in file order, as a JSON list; train_S: JSONL; candidates: the object; anchor texts: JSON
     list of the 512 texts in document order, also from my own decode of the stored ids with the pinned Qwen
     tokenizer -- tokenizer only).
  C. the 8 files: byte_sha256 (file bytes) and canonical_sha256 (parsed, re-serialized: JSONL one canonical object per
     line joined by \\n with a final \\n; JSON the canonical object), against step1_record.json file_hashes, my stage-B
     record (audit/stdout/impl_b/36_id_compare.txt) and the Executor's data regeneration of this round
     (<scratch>/c2c_data, c2c_03_checks.txt listing): byte-identical files.
  D. step1_manifest_fields.json against MY construction of the two fields: frozen DATA_MANIFEST.json "files" with each
     of the 8 non-TEST entries given status GENERATED, byte_sha256, canonical_sha256 (my values) and every other key
     and the two TEST entries unchanged; frozen SPLIT_MANIFEST.json "split_sha256" with each non-TEST name set to my
     canonical_sha256 (B3 ruling note: train_Y.jsonl among them) and test_qa.jsonl left null. The manifests in the
     working tree and index are the frozen ones (smoke does not write them).
  E. templates (SPLIT_MANIFEST normalization rule): normalized text and normalized_sha256 of all 32 templates,
     template_set_sha256 = sha256 of the sorted normalized_sha256 values joined by \\n (template text only; no TEST row).
  F. the data directory listing: the 8 files + LABEL.txt (SMOKE label), no TEST file.
  G. the two manifests as formal step 1 would write them, built by me: the frozen files are in the layout
     json.dumps(indent=2, ensure_ascii=False) + newline, and only the step-1 field differs.
Data Auditor's own script; no Executor code imported, called or copied.
usage: python -I -B ic9_01_hashes.py <repo_root> <qwen_tok_dir> <smoke_work_dir> <executor_c2c_data_dir>"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import copy
import json
import re
from ia_common import FROZEN, git, blob, sha, canon, jsonl_bytes, read_jsonl, load_qwen, run

PF = "metrix/e1-pilot/PROTOCOL_FROZEN"
FACT_FIELDS = ["fact_id", "exposure", "relation", "stratum", "entity", "answer"]
DATA = ["facts.jsonl", "train_F.jsonl", "train_S.jsonl", "train_Y.jsonl", "dev_qa.jsonl", "candidates.json",
        "general_dev.jsonl", "anchor_text.jsonl"]
TEST_FILES = ["test_qa.jsonl", "general_test.jsonl"]
MY_ROWS = {"facts": "fact(160 条)", "train_S": "`train_S.jsonl`", "candidates": "`candidates.json`",
           "anchor_texts": "锚文本(512 篇解码文本)", "template_set": "模板集合(32 个)"}
KEYS = ["facts", "train_S", "candidates", "anchor_texts"]
DM, SM = "metrix/e1-pilot/DATA_MANIFEST.json", "metrix/e1-pilot/SPLIT_MANIFEST.json"
SMOKE_LABEL = "SMOKE — NOT A RESULT"


def cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def normalize(text):
    s = text.replace("{E}", "<ENTITY>").replace("{A}", "<ANSWER>").lower()
    s = "".join(c if c in "abcdefghijklmnopqrstuvwxyz0123456789<> " else " " for c in s)
    return re.sub(r" {2,}", " ", s).strip(" ")


def canonical_of(path):
    raw = open(path, "rb").read()
    if path.endswith(".json"):
        return sha(canon(json.loads(raw.decode("utf-8"))))
    return sha(jsonl_bytes([json.loads(x) for x in raw.decode("utf-8").split("\n") if x != ""]))


def main():
    repo, qdir, work, c2data = sys.argv[1:5]
    dd, rec_d = os.path.join(work, "data"), os.path.join(work, "records")
    ok = True
    print("== A. PROTOCOL_FROZEN, my own reading")
    wt = open(os.path.join(repo, PF), "rb").read()
    print("%s sha256 %s | == HEAD blob %s | == index blob %s" % (PF, sha(wt), wt == blob(repo, "HEAD", PF),
                                                               wt == git(repo, "cat-file", "blob", ":" + PF).stdout))
    lines = wt.decode("utf-8").split("\n")
    ver = [ln.split("：", 1)[1].strip() for ln in lines if ln.startswith("当前有效版本：")]
    s0 = lines.index("## %s(当前有效)" % ver[0])
    s1 = next(i for i in range(s0 + 1, len(lines)) if lines[i].startswith("## "))
    crow = [cells(ln) for ln in lines[s0:s1] if ln.startswith("|") and cells(ln)[0] == "%s 冻结提交(完整 hash)" % ver[0]]
    commit = crow[0][1].strip("`")
    print("current version %s | frozen commit %s | == %s: %s" % (ver, commit, FROZEN, commit == FROZEN))
    ok &= ver == ["v1.1"] and commit == FROZEN
    th = lines.index("### 全部数据哈希")
    table, prev = {}, None
    for ln in lines[th + 1:]:
        if ln.startswith("#"):
            break
        if ln.startswith("|"):
            c = cells(ln)
            if re.fullmatch(r"`[0-9a-f]{64}`", c[1]):
                where = prev if c[3] == "同上" else c[3].strip("`")
                prev = where
                table[c[0]] = (c[1].strip("`"), where)
    print("table rows with a 64-hex value: %d" % len(table))
    ok &= len(table) == 12
    frozen_vals = {}
    for k, label in MY_ROWS.items():
        v, where = table[label]
        fname, path = where.split(": ", 1)
        x = json.loads(blob(repo, FROZEN, "metrix/e1-pilot/" + fname))
        for part in path.split("."):
            x = x[part]
        print("  %-12s row %r -> %s | frozen-commit %s: %s == value: %s" % (k, label, v, fname, path, x == v))
        ok &= x == v
        frozen_vals[k] = v

    print("\n== B. the four content hashes recomputed from %s" % dd)
    raw = read_jsonl(os.path.join(dd, "facts.jsonl"))
    six = all(sorted(r) == sorted(FACT_FIELDS) for r in raw)
    facts = [{f: r[f] for f in FACT_FIELDS} for r in raw]
    s_rows = read_jsonl(os.path.join(dd, "train_S.jsonl"))
    cands = json.load(open(os.path.join(dd, "candidates.json"), encoding="utf-8"))
    anchor = read_jsonl(os.path.join(dd, "anchor_text.jsonl"))
    order = [r["doc"] for r in anchor] == list(range(len(anchor)))
    print("facts.jsonl %d lines (each exactly the 6 fields: %s) | train_S.jsonl %d | candidates.json %d facts | "
          "anchor_text.jsonl %d (doc == line index: %s)" % (len(raw), six, len(s_rows), len(cands), len(anchor), order))
    ok &= six and order and len(raw) == 160 and len(s_rows) == 120 and len(cands) == 160 and len(anchor) == 512
    tok = load_qwen(qdir)
    dec = [tok.decode(r["ids"]) for r in anchor]
    mine = {"facts": sha(canon(facts)), "train_S": sha(jsonl_bytes(s_rows)), "candidates": sha(canon(cands)),
            "anchor_texts": sha(canon([r["text"] for r in anchor]))}
    print("anchor texts from my decode of the stored ids: %s | decoded == stored text for all 512: %s" % (
        sha(canon(dec)), dec == [r["text"] for r in anchor]))
    ok &= sha(canon(dec)) == mine["anchor_texts"] and dec == [r["text"] for r in anchor]
    s1rec = json.load(open(os.path.join(rec_d, "step1_record.json"), encoding="utf-8"))
    for k in KEYS:
        same = mine[k] == frozen_vals[k] == s1rec["content_hashes"].get(k)
        print("  %-12s mine %s | PROTOCOL_FROZEN %s | smoke step1_record content_hashes %s | ALL EQUAL %s" % (
            k, mine[k], frozen_vals[k], s1rec["content_hashes"].get(k), same))
        ok &= same
    print("  step1_record content_hashes keys %s (expected exactly the four)" % sorted(s1rec["content_hashes"]))
    ok &= sorted(s1rec["content_hashes"]) == sorted(KEYS)
    print("  step1_record mode %r label %r" % (s1rec.get("mode"), s1rec.get("label")))
    ok &= s1rec.get("mode") == "smoke" and s1rec.get("label") == SMOKE_LABEL

    print("\n== C. the 8 files: byte_sha256 and canonical_sha256")
    r3 = open(os.path.join(repo, "metrix/e1-pilot/audit/stdout/impl_b/36_id_compare.txt"), encoding="utf-8").read()
    rec3 = {m[0]: (m[1], m[2]) for m in re.findall(r"^  (\S+): rows \d+ \| byte ([0-9a-f]{64}) \| canonical ([0-9a-f]{64})", r3, re.M)}
    ex = open(os.path.join(repo, "metrix/e1-pilot/reports/impl_c/c2c_03_checks.txt"), encoding="utf-8").read()
    exl = {m[0]: (m[1], m[2]) for m in re.findall(r"^(\S+)\s+rows\s+\d+\s+byte_sha256 ([0-9a-f]{64})\s+canonical_sha256 ([0-9a-f]{64})", ex, re.M)}
    fh = s1rec["file_hashes"]
    my_files = {}
    for n in DATA:
        p = os.path.join(dd, n)
        b, c = sha(open(p, "rb").read()), canonical_of(p)
        my_files[n] = {"byte_sha256": b, "canonical_sha256": c}
        same_c2 = open(p, "rb").read() == open(os.path.join(c2data, n), "rb").read()
        eq = (fh.get(n) == my_files[n] and rec3.get(n) == (b, c) and exl.get(n) == (b, c) and same_c2)
        print("  %-18s byte %s canonical %s | step1_record %s | my stage-B %s | Executor c2c_03 listing %s | == c2c_data "
              "bytes %s" % (n, b, c, fh.get(n) == my_files[n], rec3.get(n) == (b, c), exl.get(n) == (b, c), same_c2))
        ok &= eq
    print("  step1_record file_hashes names == the 8 files: %s" % (sorted(fh) == sorted(DATA)))
    ok &= sorted(fh) == sorted(DATA)

    print("\n== D. step1_manifest_fields.json vs my construction from the frozen manifests")
    mf = json.load(open(os.path.join(rec_d, "step1_manifest_fields.json"), encoding="utf-8"))
    fdm, fsm = json.loads(blob(repo, FROZEN, DM)), json.loads(blob(repo, FROZEN, SM))
    want_files = copy.deepcopy(fdm["files"])
    for n in DATA:
        want_files[n].update(status="GENERATED", **my_files[n])
    want_split = copy.deepcopy(fsm["split_sha256"])
    for n in want_split:
        if n in DATA:
            want_split[n] = my_files[n]["canonical_sha256"]
    got = mf["fields"]
    print("record kind %r mode %r label %r | field paths %s" % (mf.get("kind"), mf.get("mode"), mf.get("label"), sorted(got)))
    ok &= mf.get("mode") == "smoke" and mf.get("label") == SMOKE_LABEL and sorted(got) == sorted([DM, SM])
    eq_f, eq_s = got.get(DM) == want_files, got.get(SM) == want_split
    print("DATA_MANIFEST.json files == mine: %s | SPLIT_MANIFEST.json split_sha256 == mine: %s" % (eq_f, eq_s))
    for n in list(DATA) + TEST_FILES:
        print("  files.%-18s %s" % (n, json.dumps({k: got[DM][n].get(k) for k in ("status", "byte_sha256", "canonical_sha256")})))
    print("  split_sha256 %s" % json.dumps(got[SM]))
    print("  TEST entries unchanged from the frozen manifests: files %s | split_sha256 test_qa.jsonl %r" % (
        all(got[DM][n] == fdm["files"][n] for n in TEST_FILES), got[SM].get("test_qa.jsonl")))
    print("  train_Y.jsonl canonical in split_sha256 (B3 ruling note): %s" % (got[SM].get("train_Y.jsonl") == my_files["train_Y.jsonl"]["canonical_sha256"]))
    ok &= eq_f and eq_s and got[SM].get("test_qa.jsonl") is None
    for rel in (DM, SM):
        frozen_b = blob(repo, FROZEN, rel)
        print("  %s: working tree == frozen %s | index == frozen %s" % (
            rel, open(os.path.join(repo, rel), "rb").read() == frozen_b, git(repo, "cat-file", "blob", ":" + rel).stdout == frozen_b))
        ok &= open(os.path.join(repo, rel), "rb").read() == frozen_b == git(repo, "cat-file", "blob", ":" + rel).stdout
    print("  step1_record manifests_changed %s (vs HEAD: the frozen manifests have null fields, so both would change) | "
          "manifests_already_written %s" % (s1rec.get("manifests_changed"), s1rec.get("manifests_already_written")))
    ok &= s1rec.get("manifests_changed") == [DM, SM] and s1rec.get("manifests_already_written") is False

    print("\n== E. templates (SPLIT_MANIFEST normalization)")
    T = fsm["templates"]
    bad = [t["template_id"] for t in T if normalize(t["text"]) != t["normalized"]
           or sha(normalize(t["text"]).encode("utf-8")) != t["normalized_sha256"]]
    tset = sha("\n".join(sorted(sha(normalize(t["text"]).encode("utf-8")) for t in T)).encode("utf-8"))
    print("templates %d | normalized text or normalized_sha256 differing from the manifest: %s | template_set_sha256 mine %s "
          "| manifest %s | PROTOCOL_FROZEN %s | equal %s" % (len(T), bad, tset, fsm["template_freeze"]["template_set_sha256"],
                                                           frozen_vals["template_set"],
                                                           tset == fsm["template_freeze"]["template_set_sha256"] == frozen_vals["template_set"]))
    ok &= len(T) == 32 and not bad and tset == fsm["template_freeze"]["template_set_sha256"] == frozen_vals["template_set"]

    print("\n== G. the bytes formal step 1 would write (my construction; repository layout)")
    for rel, field, new in ((DM, "files", want_files), (SM, "split_sha256", want_split)):
        frozen_b = blob(repo, FROZEN, rel)
        fobj = json.loads(frozen_b)
        layout = (json.dumps(fobj, indent=2, ensure_ascii=False) + "\n").encode("utf-8") == frozen_b
        nobj = copy.deepcopy(fobj)
        nobj[field] = new
        nb = (json.dumps(nobj, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
        others = {k: v for k, v in nobj.items() if k != field} == {k: v for k, v in fobj.items() if k != field}
        print("  %s: frozen bytes are json.dumps(indent=2, ensure_ascii=False) + newline: %s | new bytes %d (frozen %d), "
              "sha256 %s | everything outside %r unchanged: %s" % (rel, layout, len(nb), len(frozen_b), sha(nb), field, others))
        ok &= layout and others

    print("\n== F. data directory listing")
    listing = sorted(os.listdir(dd))
    lab = open(os.path.join(dd, "LABEL.txt"), encoding="utf-8").read() if "LABEL.txt" in listing else None
    print("listing %s | == the 8 files + LABEL.txt: %s | LABEL.txt %r | TEST file names present: %s" % (
        listing, listing == sorted(DATA + ["LABEL.txt"]), lab, [n for n in TEST_FILES if n in listing]))
    ok &= listing == sorted(DATA + ["LABEL.txt"]) and lab == SMOKE_LABEL + "\n"
    return bool(ok)


run(main)
