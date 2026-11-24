"""IE-1 (implementation stage B, second fix commit, task 1): a DEV-rows-only copy of eval_sets.jsonl, built by my own
method, with the meaning of tests/test_data_hashes.py::_dev_rows_only (every row whose split field is "dev", byte for
byte, in file order), and the general DEV selection of protocol 2.7 on it.
TEST rule (protocol section 3; invocation text): eval_sets.jsonl is hashed as a whole file and read in BINARY mode;
for a row only the split value in the row prefix is located and counted.  A row whose split value is not b"dev" is
never UTF-8-decoded, JSON-parsed or token-decoded; nothing else about it is computed, kept or printed (its bytes are
neither written nor compared).  Only DEV rows are parsed and decoded.
  A. eval_sets.jsonl whole-file sha256 == DATA_MANIFEST general_text.source_file_sha256 (freeze commit).
     Pass 1 (file iteration, binary): two independent locators of the split value per row:
       L1 my locator of rounds 1-3: b'"split": "' found within the first 80 bytes, value up to the next quote;
       L2 anchored, the meaning of the test's selection: the row starts with b'{"domain": "', the domain value has no
          quote or backslash and is followed by b'", "split": "', the split value has no backslash and is followed
          by b'", ' (search windows limited to the row prefix).
     every row: L1 and L2 both found and equal.  Rows with split b"dev" are written, raw bytes in file order, to
     <out_dir>/eval_sets_dev_rows.jsonl (opened "wb"); all others are only counted.
  B. (a) the DEV file holds exactly the DEV rows of eval_sets.jsonl, byte for byte and in the same order:
     pass 2 over the original by byte offsets (bytes.find(b"\\n"), not file iteration), merged with the DEV file read
     as bytes: every original row whose L1 split is b"dev" equals the next DEV-file row; every DEV-file row is
     consumed; no row of the DEV file has another split (L1 and L2); byte length == sum of the DEV rows' lengths.
     DEV rows: strict UTF-8, JSON, parsed split == "dev"; no b"\\r" byte (so a text-mode reader such as l6_check.py
     sees the same 400 rows: checked by reading the DEV file in text mode, UTF-8, and comparing line by line).
     The DEV file's sha256 is the value the test's temporary manifest carries; the test's temporary manifest ==
     the frozen DATA_MANIFEST except general_text.source_file_sha256 (built here in memory); l6_check.py (read as
     text, not run) takes only general_text.source_file_sha256 and decode_tokenizer_json_sha256 from the manifest.
     Optional: the copies left by the Executor's pytest runs (pytest tmp dirs) compared as whole files (sha256,
     bytes) with mine; their temporary manifest parsed and compared with the frozen one.
  C. (b) the general DEV selection of protocol 2.7 (per domain books, c4, fineweb, wikitext the first 25 rows with
     split == "dev", file order) made (i) from the complete file (non-dev rows skipped after L1) and (ii) from the DEV
     file: same rows, byte for byte, same order; the windows (parcae tokenizer.json decode, special tokens skipped;
     Qwen encode, add_special_tokens=False; first 256 ids; Qwen decode) from both == data_d/general_dev.jsonl
     (doc_id, domain, ids, text, row order) == my round-3 regeneration (auditor_id/out/general.json).
Data Auditor's own script; no Executor code imported, called or copied (l6_check.py and the test are read as text
only, never run).  Loads tokenizers only.
usage: python -I ie_01_devrows.py <repo_root> <parcae_tokenizer.json> <qwen_tok_dir> <data_d> <my_round3_general.json>
                                 <out_dir (new)> [<executor pytest tmp dir with eval_sets_dev_rows.jsonl> ...]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import copy, json, re
from collections import Counter, defaultdict
from ia_common import DOMAINS, FROZEN, sha, canon, file_sha, blob, frozen_json, load_qwen, enc, run

KEY = b'"split": "'
HEAD_DOMAIN = b'{"domain": "'
MID = b'", "split": "'
PER_DOMAIN = 25
DEVNAME = "eval_sets_dev_rows.jsonl"


def loc1(line):
    k = line.find(KEY, 0, 80)
    if k < 0:
        return None
    e = line.find(b'"', k + len(KEY), k + len(KEY) + 16)
    return None if e < 0 else line[k + len(KEY):e]


def loc2(line):
    if not line.startswith(HEAD_DOMAIN):
        return None
    q = line.find(b'"', len(HEAD_DOMAIN), len(HEAD_DOMAIN) + 64)
    if q < 0 or b"\\" in line[len(HEAD_DOMAIN):q] or line[q:q + len(MID)] != MID:
        return None
    s = q + len(MID)
    e = line.find(b'"', s, s + 16)
    if e < 0 or b"\\" in line[s:e] or line[e:e + 3] != b'", ':
        return None
    return line[s:e]


def diff_paths(a, b, path=()):
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append(path + (k,))
            else:
                out += diff_paths(a[k], b[k], path + (k,))
        return out
    return [] if a == b and type(a) is type(b) else [path]


def select(rows_iter):
    """rows_iter yields (row number, raw bytes) of DEV rows only; per domain the first 25, file order."""
    kept = defaultdict(list)
    for n, raw in rows_iter:
        r = json.loads(raw.decode("utf-8"))
        if r["split"] != "dev":
            raise ValueError(f"row {n}: parsed split {r['split']!r}")
        if len(kept[r["domain"]]) < PER_DOMAIN:
            kept[r["domain"]].append((n, raw, r))
    return kept


def windows(kept, ptok, qtok, maxw):
    out = []
    for d in DOMAINS:
        for n, raw, r in kept[d]:
            ids = enc(qtok, ptok.decode(r["tokens"], skip_special_tokens=True))[:maxw]
            out.append({"domain": d, "doc_id": r["doc_id"], "ids": ids, "text": qtok.decode(ids)})
    return out


def main():
    repo, ptok_path, qdir, data_d, r3_general, out_dir = sys.argv[1:7]
    executor_tmp = sys.argv[7:]
    ok = True
    if os.path.exists(out_dir):
        print("out_dir exists already; refusing to reuse:", out_dir)
        return False
    os.makedirs(out_dir)
    gt = frozen_json(repo, "DATA_MANIFEST.json")["general_text"]
    print(f"freeze-commit general_text.dev: {gt['dev']!r} | truncate_to_model_tokens {gt['truncate_to_model_tokens']}")
    m = re.fullmatch(r"first (\d+) windows per domain \(([a-z0-9, ]+)\) with split == '(\w+)', file order", gt["dev"])
    ok &= m is not None and int(m.group(1)) == PER_DOMAIN and m.group(2).split(", ") == DOMAINS and m.group(3) == "dev"
    maxw = gt["truncate_to_model_tokens"]

    print("\n== A. eval_sets.jsonl: whole-file hash; pass 1 (binary file iteration), two split locators per row")
    ev = os.path.join(repo, gt["source_file"])
    evh = file_sha(ev)
    print(f"{gt['source_file']} sha256 {evh} | frozen manifest {gt['source_file_sha256']} | MATCH {evh == gt['source_file_sha256']}")
    ok &= evh == gt["source_file_sha256"]
    devfile = os.path.join(out_dir, DEVNAME)
    counts, bad_rows, dev_numbers = Counter(), [], []
    with open(ev, "rb") as fi, open(devfile, "wb") as fo:
        for n, line in enumerate(fi, 1):
            s1, s2 = loc1(line), loc2(line)
            if s1 is None or s2 is None or s1 != s2:
                bad_rows.append(n)
            counts[s1] += 1
            if s1 == b"dev":
                fo.write(line)
                dev_numbers.append(n)
    printable = {(k.decode("ascii") if k is not None else None): v for k, v in sorted(counts.items(), key=lambda kv: str(kv[0]))}
    print(f"rows by split value (prefix only): {printable} | rows where L1 / L2 is missing or they disagree: {bad_rows}")
    ok &= printable == {"dev": 400, "test": 800} and not bad_rows
    runs, start = [], dev_numbers[0]
    for a, b in zip(dev_numbers, dev_numbers[1:] + [None]):
        if b != a + 1:
            runs.append(f"{start}-{a}")
            start = b
    print(f"DEV row numbers in eval_sets.jsonl (runs): {runs}")
    print(f"wrote {devfile} (only rows whose split value is b'dev'; raw bytes, file order)")

    print("\n== B. (a) the DEV file == the DEV rows of eval_sets.jsonl, byte for byte, same order")
    dbytes = open(devfile, "rb").read()
    dsha = sha(dbytes)
    drows = []
    p = 0
    while p < len(dbytes):
        e = dbytes.find(b"\n", p)
        e = len(dbytes) if e < 0 else e + 1
        drows.append(dbytes[p:e])
        p = e
    raw = open(ev, "rb").read()
    print(f"eval_sets.jsonl bytes {len(raw)} (whole file read as bytes; sha256 {sha(raw)} == pass-1 hash {sha(raw) == evh})")
    ok &= sha(raw) == evh
    p, k, merged_ok, dev_len, n = 0, 0, True, 0, 0
    while p < len(raw):
        e = raw.find(b"\n", p)
        e = len(raw) if e < 0 else e + 1
        row = raw[p:e]
        n += 1
        if loc1(row) == b"dev":
            dev_len += len(row)
            if k >= len(drows) or drows[k] != row:
                merged_ok = False
            k += 1
        p = e
    print(f"pass 2 (byte offsets) rows {n} | DEV rows met {k} | each equal to the next DEV-file row: {merged_ok} | DEV-file rows {len(drows)} "
          f"all consumed: {k == len(drows)}")
    ok &= merged_ok and k == len(drows) == 400 and n == 1200
    print(f"DEV file bytes {len(dbytes)} == sum of the DEV rows' lengths {dev_len}: {len(dbytes) == dev_len}")
    ok &= len(dbytes) == dev_len
    other = [i for i, r in enumerate(drows, 1) if loc1(r) != b"dev" or loc2(r) != b"dev"]
    print(f"DEV-file rows whose split (L1 or L2) is not dev: {other}")
    ok &= not other
    parsed_ok, cr, nonl = True, [], []
    for i, r in enumerate(drows, 1):
        try:
            o = json.loads(r.decode("utf-8"))
            parsed_ok &= o.get("split") == "dev"
        except (UnicodeDecodeError, ValueError):
            parsed_ok = False
        if b"\r" in r:
            cr.append(i)
        if not r.endswith(b"\n"):
            nonl.append(i)
    print(f"DEV rows: strict UTF-8 + JSON, parsed split == 'dev': {parsed_ok} | rows with a b'\\r' byte: {cr} | rows without the final b'\\n': {nonl}")
    ok &= parsed_ok and not cr and not nonl
    with open(devfile, encoding="utf-8") as fh:
        tlines = list(fh)
    same_text = tlines == [r.decode("utf-8") for r in drows]
    print(f"DEV file read in text mode (UTF-8, universal newlines, as a text-mode reader would): {len(tlines)} lines, equal to the binary rows: {same_text}")
    ok &= same_text and len(tlines) == 400
    print(f"DEV file sha256 {dsha} (the value the test's temporary manifest carries as general_text.source_file_sha256)")

    dm_rel = "metrix/e1-pilot/DATA_MANIFEST.json"
    wt = open(os.path.join(repo, dm_rel), "rb").read()
    fr = blob(repo, FROZEN, dm_rel)
    print(f"{dm_rel}: working tree == freeze-commit blob: {wt == fr}")
    ok &= wt == fr
    base = json.loads(wt)
    tmpm = copy.deepcopy(base)
    tmpm["general_text"]["source_file_sha256"] = dsha
    print(f"the test's temporary manifest (built here in memory) differs from the frozen manifest at: {diff_paths(base, tmpm)}")
    ok &= diff_paths(base, tmpm) == [("general_text", "source_file_sha256")]
    l6 = open(os.path.join(repo, "metrix/e1-pilot/reports/round5/l6_check.py"), encoding="utf-8").read()
    gt_subs = sorted(set(re.findall(r"\bgt\[([^\]]+)\]", l6)))
    loop_keys = re.findall(r'\(\("eval_sets\.jsonl", a\.eval_sets, "(\w+)"\),\s*\("parcae tokenizer\.json", a\.parcae_tokenizer, "(\w+)"\)\)', l6)
    man_loads = re.findall(r"json\.load\(open\(a\.manifest[^\n]*", l6)
    print(f"l6_check.py (read as text): manifest loads {man_loads} | gt[...] subscripts {gt_subs} | keys of the pin loop {loop_keys}")
    ok &= gt_subs == ["key"] and loop_keys == [("source_file_sha256", "decode_tokenizer_json_sha256")] and len(man_loads) == 1

    for d in executor_tmp:
        f = os.path.join(d, DEVNAME)
        mf = os.path.join(d, "DATA_MANIFEST_dev_rows.json")
        if not os.path.isfile(f):
            print(f"Executor pytest copy {f}: not present")
            continue
        st = os.stat(f)
        fb = open(f, "rb").read()
        same = fb == dbytes
        print(f"Executor pytest copy {f}: bytes {len(fb)} sha256 {sha(fb)} | == my DEV file byte for byte: {same}")
        ok &= same
        if same and os.path.isfile(mf):
            em = json.loads(open(mf, "rb").read().decode("utf-8"))
            dp = diff_paths(base, em)
            print(f"  its {os.path.basename(mf)} differs from the frozen manifest at {dp} | value == my DEV file sha256: "
                  f"{em['general_text']['source_file_sha256'] == dsha}")
            ok &= dp == [("general_text", "source_file_sha256")] and em["general_text"]["source_file_sha256"] == dsha

    print("\n== C. (b) protocol 2.7 general DEV selection: complete file vs DEV file vs data_d/general_dev.jsonl")

    def full_iter():
        with open(ev, "rb") as fh:
            for i, line in enumerate(fh, 1):
                if loc1(line) != b"dev":
                    continue                    # not dev: only the split value was located
                yield i, line

    kf = select(full_iter())
    kd = select(enumerate(drows, 1))
    print(f"kept per domain: complete file {{{', '.join(f'{d}: {len(kf[d])}' for d in DOMAINS)}}} other domains {sorted(set(kf) - set(DOMAINS))} | "
          f"DEV file {{{', '.join(f'{d}: {len(kd[d])}' for d in DOMAINS)}}} other domains {sorted(set(kd) - set(DOMAINS))}")
    ok &= all(len(kf[d]) == len(kd[d]) == PER_DOMAIN for d in DOMAINS) and set(kf) == set(kd) == set(DOMAINS)
    same_sel = all([raw for _, raw, _ in kf[d]] == [raw for _, raw, _ in kd[d]] for d in DOMAINS)
    pos_map = all(dev_numbers[nd - 1] == nf for d in DOMAINS for (nf, _, _), (nd, _, _) in zip(kf[d], kd[d]))
    print(f"selected rows byte-identical and in the same order: {same_sel} | DEV-file row k is eval_sets row dev_numbers[k] for every selected row: {pos_map}")
    for d in DOMAINS:
        print(f"  {d}: eval_sets rows {kf[d][0][0]}..{kf[d][-1][0]} | DEV-file rows {kd[d][0][0]}..{kd[d][-1][0]} | doc_id {kf[d][0][2]['doc_id']}..{kf[d][-1][2]['doc_id']}")
    ok &= same_sel and pos_map

    from tokenizers import Tokenizer
    ph = file_sha(ptok_path)
    print(f"parcae tokenizer.json sha256 {ph} | frozen manifest {gt['decode_tokenizer_json_sha256']} | MATCH {ph == gt['decode_tokenizer_json_sha256']}")
    ok &= ph == gt["decode_tokenizer_json_sha256"]
    ptok = Tokenizer.from_file(ptok_path)
    qtok = load_qwen(qdir)
    wf, wd = windows(kf, ptok, qtok, maxw), windows(kd, ptok, qtok, maxw)
    print(f"windows: complete file {len(wf)} | DEV file {len(wd)} | identical (domain, doc_id, ids, text): {wf == wd}")
    ok &= wf == wd and len(wf) == 100
    ex = [json.loads(x) for x in open(os.path.join(data_d, "general_dev.jsonl"), "rb").read().decode("utf-8").split("\n") if x]
    print(f"data_d/general_dev.jsonl: rows {len(ex)} | byte sha256 {file_sha(os.path.join(data_d, 'general_dev.jsonl'))} | keys {sorted(ex[0]) if ex else None}")
    cmp_ex = len(ex) == len(wd) and all(sorted(e) == ["doc_id", "domain", "ids", "text"] and all(e[k] == w[k] for k in ("domain", "doc_id", "ids", "text"))
                                         for e, w in zip(ex, wd))
    mism = [i for i, (e, w) in enumerate(zip(ex, wd)) if any(e.get(k) != w[k] for k in ("domain", "doc_id", "ids", "text"))]
    print(f"my windows (from the DEV file) == data_d/general_dev.jsonl row by row (domain, doc_id, ids, text): {cmp_ex} | mismatching rows {mism}")
    ok &= cmp_ex
    r3 = json.loads(open(r3_general, "rb").read().decode("utf-8"))
    cmp_r3 = len(r3) == len(wd) and all((a["domain"], a["doc_id"], a["ids"], a["text"]) == (w["domain"], w["doc_id"], w["ids"], w["text"]) for a, w in zip(r3, wd))
    print(f"== my round-3 regeneration {r3_general} (complete file, ia_06): {cmp_r3}")
    ok &= cmp_r3
    print(f"AUDIT_VALUE general_dev_ids_canonical_sha256 {sha(canon([w['ids'] for w in wd]))}")
    print(f"AUDIT_VALUE general_dev_texts_canonical_sha256 {sha(canon([w['text'] for w in wd]))}")
    return bool(ok)


run(main)
