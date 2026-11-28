# data-auditor, E1-V1 round 2, item 2: data-related content of the four modified JSON files.
#   (a) leaf-by-leaf diff HEAD (= round-1 tree 0e3dc49e) vs index (staged tree f395c476): what was removed,
#       added, changed; are all removed leaves placeholders; did any hash change.
#   (b) every 64-hex value in the four JSON files and in the protocol vs a value the auditor computed itself.
#   (c) seeds, counts and rule text (round-1 a6 checks, adapted; the auditor's own code).
#   (d) reading rules: DAMAGE_MANIFEST vs protocol section 0; the literal regex of protocol section 0 applied to
#       the row-prefix bytes of eval_sets.jsonl (no test row decoded or parsed) vs the round-1 regex.
#   (e) G-D2 bounds: protocol 7.5 vs DAMAGE_MANIFEST.
#   (f) the placeholder fields removed: is any data-related information lost.
#   (g) git provenance (read-only commands) and the deliverable diff vs the staged changes.
# No Executor code is imported, called or copied.
import json
import math
import re
import subprocess
import sys

sys.path.insert(0, "/home/user/OpenMythos/metrix/e1-v1/audit")
import audit_lib as A  # noqa: E402

D = A.TMP + "/v1data"
NAMES = ("DATA_MANIFEST.json", "SPLIT_MANIFEST.json", "DOSE_SPACE.json", "DAMAGE_MANIFEST.json")
TREE = "f395c476606603e65d336e1ba3ac34a065c40889"
HEAD = "59761ad923674d43725167a8c79f6bdf16f531ee"
DIFF_FILE = "/tmp/claude-0/-home-user/1e17bf44-a265-5c2d-b2f8-f9d45e7efe94/scratchpad/c/input_round2.diff"


def git(*args):
    return subprocess.run(["git", "-C", A.REPO] + list(args), capture_output=True, text=True).stdout


def walk(obj, path=""):
    if isinstance(obj, dict):
        if not obj:
            yield path, {}
        for k, v in obj.items():
            yield from walk(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        if not obj:
            yield path, []
        for i, v in enumerate(obj):
            yield from walk(v, f"{path}[{i}]")
    else:
        yield path, obj


def chk(label, got, exp):
    ok = got == exp
    print(f"{'OK  ' if ok else 'DIFF'} {label}: got {got} | expected {exp}")
    return ok


def short(v, n=150):
    s = json.dumps(v, ensure_ascii=False)
    return s if len(s) <= n else s[:n] + "…"


def main():
    ok = True
    proto = open(A.V1 + "/METRIX_E1V1_PROTOCOL.md", encoding="utf-8").read()
    J = {n: A.load_json(A.V1 + "/" + n) for n in NAMES}
    dm, sm, ds, gm = (J[n] for n in NAMES)

    # ======================= (a) HEAD vs index =======================
    print("=== (a) leaf diff HEAD (tree 0e3dc49e) -> index (tree f395c476)")
    removed_all, hash_changes = [], []
    for n in NAMES:
        old = json.loads(git("show", f"HEAD:metrix/e1-v1/{n}"))
        new = json.loads(git("show", f":metrix/e1-v1/{n}"))
        ok &= chk(f"{n}: working tree parses equal to index", J[n] == new, True)
        lo, ln = dict(walk(old)), dict(walk(new))
        rem = [p for p in lo if p not in ln]
        add = [p for p in ln if p not in lo]
        chg = [p for p in lo if p in ln and lo[p] != ln[p]]
        print(f"  {n}: leaves HEAD {len(lo)} index {len(ln)} | removed {len(rem)} added {len(add)} changed {len(chg)}")
        for p in rem:
            print(f"    removed {p} = {short(lo[p])}")
            removed_all.append((n, p, lo[p]))
        for p in add:
            print(f"    added   {p} = {short(ln[p])}")
        for p in chg:
            print(f"    changed {p}: {short(lo[p], 110)} -> {short(ln[p], 110)}")
        hx = lambda d: sorted((p, h) for p, v in d.items() if isinstance(v, str) for h in re.findall(r"(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])", v))  # noqa: E731
        if hx(lo) != hx(ln):
            hash_changes.append((n, sorted(set(hx(lo)) ^ set(hx(ln)))))
        # numbers (ints / floats) anywhere: must be unchanged
        nums = lambda d: sorted((p, v) for p, v in d.items() if isinstance(v, (int, float)) and not isinstance(v, bool))  # noqa: E731
        ok &= chk(f"{n}: every numeric leaf unchanged", nums(lo) == nums(ln), True)
    ok &= chk("64-hex values (path, value) changed between HEAD and index", hash_changes, [])
    bad_removed = [(n, p, v) for n, p, v in removed_all if v not in (None, "NOT_GENERATED")]
    ok &= chk("removed leaves whose value is not null / 'NOT_GENERATED'", bad_removed, [])
    kinds = {}
    for n, p, v in removed_all:
        key = (n, p.split(".")[-1] if not p.startswith("split_sha256") else "split_sha256.*", v)
        kinds[key] = kinds.get(key, 0) + 1
    print("  removed leaves by (file, field, value):", kinds)

    # ======================= (b) every 64-hex value =======================
    print("=== (b) every 64-hex value vs the auditor's own computation")
    facts = A.read_jsonl(D + "/facts.jsonl")
    pfacts = A.read_jsonl(D + "/pilot_facts.jsonl")
    anchor = A.read_jsonl(D + "/anchor_text.jsonl")
    comp = {
        "V1 facts list (canonical JSON list)": A.canon_sha(facts),
        "Pilot facts list (canonical JSON list, DATA_SEED 20261110)": A.canon_sha(pfacts),
        "facts.jsonl": A.jsonl_sha(facts),
        "train_F.jsonl": A.jsonl_sha(A.read_jsonl(D + "/train_F.jsonl")),
        "train_S.jsonl": A.jsonl_sha(A.read_jsonl(D + "/train_S.jsonl")),
        "train_Y.jsonl": A.jsonl_sha(A.read_jsonl(D + "/train_Y.jsonl")),
        "dev_qa.jsonl": A.jsonl_sha(A.read_jsonl(D + "/dev_qa.jsonl")),
        "candidates.json": A.canon_sha(A.load_json(D + "/candidates.json")),
        "anchor_text.jsonl": A.jsonl_sha(anchor),
        "anchor decoded texts (canonical JSON list)": A.canon_sha([a["text"] for a in anchor]),
        "general_dev.jsonl": A.jsonl_sha(A.read_jsonl(D + "/general_dev.jsonl")),
        "d2_dev.jsonl MMLU": A.jsonl_sha(A.read_jsonl(D + "/d2_dev.jsonl")),
        "d2_dev.jsonl ARC": A.jsonl_sha(A.read_jsonl(D + "/d2_dev_arc.jsonl")),
        "template set": A.sha_text("\n".join(sorted(A.sha_text(A.normalize_template(t["text"])) for t in sm["templates"]))),
        "file anchor parquet": A.file_sha256(A.ANCHOR_PARQUET),
        "file eval_sets.jsonl (whole file)": A.file_sha256(A.EVAL_SETS),
        "file parcae tokenizer.json": A.file_sha256(A.PARCAE_TOK),
    }
    for f in ("tokenizer.json", "tokenizer_config.json", "vocab.json", "merges.txt"):
        comp[f"file qwen/{f}"] = A.file_sha256(A.QWEN_DIR + "/" + f)
    comp["file MMLU all/validation"] = A.file_sha256(A.MMLU_DIR + "/all/validation-00000-of-00001.parquet")
    comp["file MMLU all/test (whole file)"] = A.file_sha256(A.MMLU_DIR + "/all/test-00000-of-00001.parquet")
    for f in ("ARC-Challenge/validation", "ARC-Easy/validation", "ARC-Challenge/test", "ARC-Easy/test"):
        comp[f"file ARC {f}"] = A.file_sha256(A.ARC_DIR + f"/{f}-00000-of-00001.parquet")
    for t in sm["templates"]:
        comp[f"template {t['template_id']} normalized"] = A.sha_text(A.normalize_template(t["text"]))
    byval = {}
    for k, v in comp.items():
        byval.setdefault(v, []).append(k)
    occ = []
    for n in NAMES:
        for p, v in walk(J[n]):
            if isinstance(v, str):
                for h in re.findall(r"(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])", v):
                    occ.append((n, p, h))
    unmatched = [(n, p, h) for n, p, h in occ if h not in byval]
    print(f"  64-hex occurrences in the four JSON files: {len(occ)} | distinct {len({h for _, _, h in occ})}")
    for n, p, h in occ:
        if not p.startswith("templates["):
            print(f"    {n}:{p} {h[:16]}… = auditor {byval.get(h, ['NOT COMPUTED'])}")
    print(f"    templates[*].normalized_sha256: {sum(1 for n, p, h in occ if p.startswith('templates['))} occurrences, all equal to the auditor's value: {all(h in byval for n, p, h in occ if p.startswith('templates['))}")
    ok &= chk("64-hex values in the JSON files not equal to an auditor-computed value", unmatched, [])
    # meaning check: each value sits under a field of the same meaning
    exp_paths = {
        ("DATA_MANIFEST.json", "name_generation.expected_facts_canonical_sha256"): "V1 facts list (canonical JSON list)",
        ("DATA_MANIFEST.json", "name_generation.preseed.pilot_facts_canonical_sha256"): "Pilot facts list (canonical JSON list, DATA_SEED 20261110)",
        ("DATA_MANIFEST.json", "s_permutation.expected_train_S_canonical_sha256"): "train_S.jsonl",
        ("DATA_MANIFEST.json", "anchor_text.decoded_texts_canonical_sha256"): "anchor decoded texts (canonical JSON list)",
        ("DATA_MANIFEST.json", "anchor_text.file_canonical_sha256_authoring"): "anchor_text.jsonl",
        ("DATA_MANIFEST.json", "files.d2_dev.jsonl.reference_canonical_sha256.mmlu"): "d2_dev.jsonl MMLU",
        ("DATA_MANIFEST.json", "files.d2_dev.jsonl.reference_canonical_sha256.arc"): "d2_dev.jsonl ARC",
        ("SPLIT_MANIFEST.json", "template_freeze.template_set_sha256"): "template set",
        ("SPLIT_MANIFEST.json", "candidates.candidate_mapping_sha256"): "candidates.json",
        ("DAMAGE_MANIFEST.json", "d1.source_file_sha256"): "file eval_sets.jsonl (whole file)",
        ("DAMAGE_MANIFEST.json", "d1.decode_tokenizer_json_sha256"): "file parcae tokenizer.json",
        ("DAMAGE_MANIFEST.json", "d1.dev.authoring.canonical_sha256"): "general_dev.jsonl",
        ("DAMAGE_MANIFEST.json", "d2.datasets.mmlu.dev_source.sha256"): "file MMLU all/validation",
        ("DAMAGE_MANIFEST.json", "d2.datasets.mmlu.test_source.sha256"): "file MMLU all/test (whole file)",
        ("DAMAGE_MANIFEST.json", "d2.datasets.mmlu.authoring_dev.canonical_sha256"): "d2_dev.jsonl MMLU",
        ("DAMAGE_MANIFEST.json", "d2.datasets.arc.dev_source[0].sha256"): "file ARC ARC-Challenge/validation",
        ("DAMAGE_MANIFEST.json", "d2.datasets.arc.dev_source[1].sha256"): "file ARC ARC-Easy/validation",
        ("DAMAGE_MANIFEST.json", "d2.datasets.arc.test_source[0].sha256"): "file ARC ARC-Challenge/test",
        ("DAMAGE_MANIFEST.json", "d2.datasets.arc.test_source[1].sha256"): "file ARC ARC-Easy/test",
        ("DAMAGE_MANIFEST.json", "d2.datasets.arc.authoring_dev.canonical_sha256"): "d2_dev.jsonl ARC",
    }
    for f in ("facts.jsonl", "train_F.jsonl", "train_S.jsonl", "train_Y.jsonl", "dev_qa.jsonl", "candidates.json", "anchor_text.jsonl", "general_dev.jsonl"):
        exp_paths[("DATA_MANIFEST.json", f"files.{f}.reference_canonical_sha256")] = f
    for f in ("tokenizer.json", "tokenizer_config.json", "vocab.json", "merges.txt"):
        exp_paths[("DATA_MANIFEST.json", f"model.tokenizer.files_sha256.{f}")] = f"file qwen/{f}"
    wrong = []
    for (n, p), meaning in exp_paths.items():
        v = dict(walk(J[n])).get(p)
        if v != comp[meaning]:
            wrong.append((n, p, v, comp[meaning]))
    ok &= chk(f"fields of a known meaning ({len(exp_paths)}) whose value differs from the auditor's value of that meaning", wrong, [])
    for n, p, h in occ:
        if (n, p) not in exp_paths and not p.startswith("templates["):
            print(f"    embedded in text (not a hash field): {n}:{p} {h[:16]}… = {byval.get(h)}")
    ok &= chk("TEST reference hashes (test_qa, general_test, d2_test) are null", [dm["files"][f]["reference_canonical_sha256"] for f in ("test_qa.jsonl", "general_test.jsonl", "d2_test.jsonl")], [None, None, None])
    ph = sorted(set(re.findall(r"(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])", proto)))
    ok &= chk(f"64-hex values in the protocol ({len(ph)}) not equal to an auditor-computed value", [h for h in ph if h not in byval], [])
    for h in ph:
        print(f"    protocol {h[:16]}… = auditor {byval.get(h)}")

    # ======================= (c) seeds, counts, rule text =======================
    print("=== (c) seeds, counts, rule text")
    pdm = A.load_json(A.PILOT + "/DATA_MANIFEST.json")
    psm = A.load_json(A.PILOT + "/SPLIT_MANIFEST.json")
    sec0 = [l for l in proto.splitlines() if l.startswith("**种子(PROPOSED)**")][0]
    seeds = {k: int(v) for k, v in re.findall(r"`(DATA_SEED|CANDIDATE_SEED|BOOTSTRAP_SEED) = (\d+)`", sec0)}
    for k in ("DATA_SEED", "CANDIDATE_SEED", "BOOTSTRAP_SEED"):
        ok &= chk(f"{k} protocol section 0 vs DATA_MANIFEST", seeds.get(k), dm["seeds"][k])
    occs = [(proto.count("\n", 0, m.start()) + 1, m.group(1), int(m.group(2))) for m in re.finditer(r"`(DATA_SEED|CANDIDATE_SEED|BOOTSTRAP_SEED) = (\d+)`", proto)]
    other = [o for o in occs if o[2] != dm["seeds"][o[1]]]
    ok &= chk("seed assignments in the protocol differing from DATA_MANIFEST outside the Pilot regeneration sentence",
              [o for o in other if "重新生成 Pilot" not in proto.splitlines()[o[0] - 1]], [])
    print("  seed assignments differing from DATA_MANIFEST (Pilot regeneration only):", other)
    ok &= chk("TRAIN_SEEDS protocol / DATA_MANIFEST / DOSE_SPACE / Z0 / P+", ("`TRAIN_SEEDS = [101, 202, 303]`" in proto, dm["seeds"]["TRAIN_SEEDS"], ds["seeds"]["training_seeds"], ds["controls"]["Z0"]["seeds"], ds["controls"]["P+"]["seeds"]),
              (True, [101, 202, 303], [101, 202, 303], [101, 202, 303], [101, 202, 303]))
    ok &= chk("DAMAGE_MANIFEST bootstrap seed / SPLIT_MANIFEST candidate seed text", (gm["statistics"]["seed"], sm["candidates"]["seed"]), (f"BOOTSTRAP_SEED = {dm['seeds']['BOOTSTRAP_SEED']}", f"CANDIDATE_SEED = {dm['seeds']['CANDIDATE_SEED']}"))
    pn, vn = pdm["name_generation"], dm["name_generation"]
    same_keys = ["natural", "random", "streams", "accepted_strings_scope", "anchor_rule", "token_counts", "max_draws_per_stream", "on_exhaustion", "draw"]
    ok &= chk("name_generation rule fields equal to Pilot", [k for k in same_keys if pn.get(k) != vn.get(k)], [])
    ok &= chk("s_permutation rule = Pilot with 15 -> 30", pdm["s_permutation"]["rule"].replace("15", "30"), dm["s_permutation"]["rule"])
    ok &= chk("templates identical to Pilot", sm["templates"] == psm["templates"], True)
    for k in ("way", "pool", "draw", "shared_by", "duplicates", "pool_too_small", "exposure_matching"):
        ok &= chk(f"candidates.{k} identical to Pilot", sm["candidates"][k] == psm["candidates"][k], True)
    ok &= chk("hashing rules identical to Pilot (both manifests)", (dm["hashing"], sm["hashing"]) == (pdm["hashing"], psm["hashing"]), True)
    for k in ("source", "selection", "truncate_to_model_tokens", "document_rule", "decoded_texts_canonical_sha256"):
        ok &= chk(f"anchor_text.{k} identical to Pilot", dm["anchor_text"][k] == pdm["anchor_text"][k], True)
    for k in ("source_file", "source_file_sha256", "decode_with", "decode_tokenizer_json_sha256", "window_rule"):
        ok &= chk(f"D1 {k} identical to Pilot general_text", gm["d1"][k] == pdm["general_text"][k], True)
    ok &= chk("facts counts (total, learned, unread, per cell)", (dm["facts"]["total"], dm["facts"]["learned"], dm["facts"]["unread"], dm["facts"]["per_cell"]["learned"], dm["facts"]["per_cell"]["unread"]), (len(facts), sum(f["exposure"] == "learned" for f in facts), sum(f["exposure"] == "unread" for f in facts), 30, 10))
    ok &= chk("protocol counts 320 = 240 + 80, 30 + 10, pool 29 / 9, Y 480", ("**320 facts = 240 learned + 80 unread**" in proto, "每个 cell **30 learned + 10 unread**" in proto, "learned 29 个、unread 9 个" in proto, "共 480 句" in proto), (True, True, True, True))
    ok &= chk("pool sizes SPLIT_MANIFEST", sm["candidates"]["pool_sizes"], {"learned": 29, "unread": 9})
    ok &= chk("Y/F authoring numbers protocol / DATA_MANIFEST", ("F 3,802 token,Y 4,541 token,比值 1.1944" in proto, dm["y_ratio"]["authoring"]), (True, {"F_tokens": 3802, "Y_tokens": 4541, "ratio": 1.1944}))
    ok &= chk("D1 DEV 400 / D2 DEV 800 / D1 TEST 175 per domain (protocol vs DAMAGE_MANIFEST)",
              ("撰写时 400(每领域 100,排除 0)" in proto, "| 800;撰写时排除 0" in proto, "400(每领域可用 175 行)" in proto, gm["d1"]["dev"]["authoring"]["kept"], gm["d2"]["datasets"]["mmlu"]["authoring_dev"]["items"], gm["d1"]["test"]["available_per_domain_after_skip"]),
              (True, True, True, 400, 800, 175))
    ok &= chk("MMLU / ARC source rows (protocol vs DAMAGE_MANIFEST)", ("1,531 行" in proto and "14,042 行" in proto and "299 + 570 行" in proto and "1,172 + 2,376 行" in proto,
              [gm["d2"]["datasets"]["mmlu"]["dev_source"]["rows"], gm["d2"]["datasets"]["mmlu"]["test_source"]["rows"]] + [s["rows"] for s in gm["d2"]["datasets"]["arc"]["dev_source"] + gm["d2"]["datasets"]["arc"]["test_source"]]),
              (True, [1531, 14042, 299, 570, 1172, 2376]))
    ok &= chk("ARC dev_order / test_order index ranges = rows - 1", ("indices 0..868" in gm["d2"]["datasets"]["arc"]["dev_order"], "indices 0..3547" in gm["d2"]["datasets"]["arc"]["test_order"]), (299 + 570 - 1 == 868, 1172 + 2376 - 1 == 3547))
    ok &= chk("MMLU dev_order / test_order list lengths", ("list(range(1531))" in gm["d2"]["datasets"]["mmlu"]["dev_order"], "list(range(14042))" in gm["d2"]["datasets"]["mmlu"]["test_order"]), (True, True))
    ok &= chk("letter ids / prompt instruction (protocol vs DAMAGE_MANIFEST)", ("id 362、425、356、422" in proto, gm["d2"]["letter_token_ids"], '`I = "Answer the following multiple choice question with the letter of the correct option."`' in proto,
              "I = 'Answer the following multiple choice question with the letter of the correct option.'" in gm["d2"]["prompt"]), (True, {"A": 362, "B": 425, "C": 356, "D": 422}, True, True))
    ok &= chk("dose ladder (protocol 6.3 vs DOSE_SPACE; steps = 30 x passes)", ("k ∈ {1, 2, 3, 4, 6, 8, 11, 16, 23, 32}" in proto, ds["dose"]["ladder_passes"], ds["dose"]["ladder_steps"] == [30 * k for k in ds["dose"]["ladder_passes"]], ds["dose"]["d0_passes"]),
              (True, [1, 2, 3, 4, 6, 8, 11, 16, 23, 32], True, 11))
    ok &= chk("iso parameters DOSE_SPACE (targets, tau_dev, tau_test) vs protocol 6.2 / 6.4 / 6.5", (ds["iso"]["targets"], ds["iso"]["tau_dev"], ds["iso"]["tau_test"], "t ∈ {0.70, 0.80, 0.90}" in proto, "τ_DEV = 0.10" in proto, "τ_TEST = 0.05" in proto),
              ([0.7, 0.8, 0.9], 0.1, 0.05, True, True, True))
    ok &= chk("DOSE_SPACE checkpoint_retention.rule = protocol 6.7 condition", ("not yet crossed before j has |a_j - t| <= 0.10" in ds["checkpoint_retention"]["rule"], "|a_j − t| ≤ 0.10" in proto), (True, True))
    print("  report only: DOSE_SPACE iso has no field for the exact arithmetic of protocol 6.4 item 2a:", [k for k in ds["iso"] if "arith" in k or "fraction" in k.lower()])

    # ======================= (d) reading rules =======================
    print("=== (d) reading rules")
    print("  DAMAGE d1.reading_rule:", gm["d1"]["reading_rule"])
    print("  DAMAGE d2.reading_rule:", gm["d2"]["reading_rule"])
    sec0_read = [l for l in proto.splitlines() if l.startswith("**“读取 TEST 数据”的定义**")][0]
    ok &= chk("protocol section 0 allows exactly: whole-file sha256; eval_sets row-prefix match + count; parquet footer row count",
              all(s in sec0_read for s in ("对整个文件求 sha256", "按行首字节匹配 domain 与 split 字段后计数", "test 行不解码、不做 JSON 解析", "只读文件尾的行数", "不得解码或读取任何 test 行或 TEST 题目的内容")), True)
    ok &= chk("DAMAGE d1.reading_rule matches (sha256 allowed; prefix bytes only; counted; never decoded or parsed)",
              all(s in gm["d1"]["reading_rule"] for s in ("whole-file sha256 allowed", "row-prefix bytes", "regex of protocol section 0", "counted", "never decoded or JSON-parsed")), True)
    ok &= chk("DAMAGE d2.reading_rule matches (sha256 allowed; parquet footer only; no row read or decoded)",
              all(s in gm["d2"]["reading_rule"] for s in ("whole-file sha256 of a TEST source allowed", "only the parquet footer (row count)", "no row is read or decoded")), True)
    m = re.search(r"字节正则 `([^`]+)`", sec0_read)
    regex_text = m.group(1)
    print("  protocol regex (literal):", regex_text)
    PRO = re.compile(regex_text.encode("utf-8"))
    R1 = re.compile(rb'^\{"domain": "([a-z0-9_]+)", "split": "([a-z]+)", ')
    cnt_p, cnt_1, disagree, unmatched_p, lines = {}, {}, 0, 0, 0
    with open(A.EVAL_SETS, "rb") as f:
        for raw in f:
            lines += 1
            mp, m1 = PRO.match(raw), R1.match(raw)
            gp = (mp.group(1), mp.group(2)) if mp else None
            g1 = (m1.group(1), m1.group(2)) if m1 else None
            if gp != g1:
                disagree += 1
            if gp is None:
                unmatched_p += 1
            else:
                k = (gp[0].decode(), gp[1].decode())  # the domain and split field values only
                cnt_p[k] = cnt_p.get(k, 0) + 1
            if g1:
                k = (g1[0].decode(), g1[1].decode())
                cnt_1[k] = cnt_1.get(k, 0) + 1
    print(f"  eval_sets.jsonl lines {lines} | protocol-regex counts {dict(sorted(cnt_p.items()))}")
    ok &= chk("lines where the protocol regex and the round-1 auditor regex capture different (domain, split)", disagree, 0)
    ok &= chk("lines not matched by the protocol regex", unmatched_p, 0)
    ok &= chk("per (domain, split) counts protocol regex = round-1 regex", cnt_p, cnt_1)
    ok &= chk("test rows per domain after skipping 25 (protocol regex)", {d: cnt_p[(d, "test")] - 25 for d in gm["d1"]["domains"]}, {d: gm["d1"]["test"]["available_per_domain_after_skip"] for d in gm["d1"]["domains"]})

    # ======================= (e) G-D2 bounds =======================
    print("=== (e) G-D2 bounds")
    gd2 = gm["gate_d"]["G-D2"]
    row = [l for l in proto.splitlines() if l.startswith("| G-D2 噪声基线 |")][0]
    print("  protocol G-D2 row:", row)
    print("  DAMAGE G-D2:", gd2)
    pb = re.search(r"`m\(D1-all\)`、`m\(D1-diff\)` ≤ ([0-9.]+),`m\(D1-same\)` ≤ ([0-9.]+)", row)
    jb = re.search(r"m\(D1-all\) <= ([0-9.]+), m\(D1-diff\) <= ([0-9.]+), m\(D1-same\) <= ([0-9.]+)", gd2["rule"])
    ok &= chk("bounds protocol (D1-all, D1-diff, D1-same) = DAMAGE_MANIFEST", (float(pb.group(1)), float(pb.group(1)), float(pb.group(2))), tuple(float(x) for x in jb.groups()))
    mD2 = 2 * math.sqrt(0.25 / 800)
    print(f"  2 * sqrt(0.25 / 800) = {mD2:.6f}; sqrt(0.25 / 800) = {math.sqrt(0.25 / 800):.6f}")
    ok &= chk("protocol '2 × sqrt(0.25/800) ≈ 0.035' and DAMAGE '2 * sqrt(0.25 / 800)'", ("2 × sqrt(0.25/800) ≈ 0.035" in row, "2 * sqrt(0.25 / 800)" in gd2["rule"], round(mD2, 3)), (True, True, 0.035))
    ok &= chk("G-D2 planning numbers protocol 7.5 vs DAMAGE planning", ("`m(D1-all)` 约 0.045、`m(D1-diff)` 约 0.052、`m(D1-same)` 约 0.090" in proto, "D1-all 0.045, D1-diff 0.052, D1-same 0.090" in gd2["planning"]), (True, True))
    ok &= chk("sigma_N definition: sample SD (B - 1) of 10,000 bootstrap values; m = 2 sigma_N", (gm["statistics"]["replicates"], "denominator B - 1" in gm["statistics"]["sigma_N"], gm["margin"]["multiplier"]), (10000, True, 2))
    # report only: 'by construction' for m(D2) holds for the population value; a finite bootstrap SD can exceed it slightly
    import numpy as np
    rs = np.random.default_rng(12345)
    exceed, vals = 0, []
    for rep in range(20):
        c = np.array([1] * 400 + [0] * 400)
        idx = rs.integers(0, 800, size=(10000, 800))
        sd = c[idx].mean(axis=1).std(ddof=1)
        vals.append(sd)
        exceed += sd > math.sqrt(0.25 / 800)
    print(f"  report only: Acc_D2(N) = 0.5 (worst case), 20 simulated 10,000-replicate bootstraps: sigma min {min(vals):.6f} max {max(vals):.6f}; above sqrt(0.25/800) in {exceed} of 20 (2 sigma max {2 * max(vals):.6f})")

    # ======================= (f) placeholders removed =======================
    print("=== (f) removed placeholder fields: information lost?")
    old_dm = json.loads(git("show", "HEAD:metrix/e1-v1/DATA_MANIFEST.json"))
    old_sm = json.loads(git("show", "HEAD:metrix/e1-v1/SPLIT_MANIFEST.json"))
    old_vals = {f: {k: old_dm["files"][f].get(k) for k in ("status", "byte_sha256", "canonical_sha256")} for f in old_dm["files"]}
    ok &= chk("old files.*.{status, byte_sha256, canonical_sha256} were all NOT_GENERATED / null / null", all(v == {"status": "NOT_GENERATED", "byte_sha256": None, "canonical_sha256": None} for v in old_vals.values()), True)
    ok &= chk("old SPLIT_MANIFEST.split_sha256 values", old_sm.get("split_sha256"), {"train_F.jsonl": None, "train_S.jsonl": None, "train_Y.jsonl": None, "dev_qa.jsonl": None, "test_qa.jsonl": None})
    ok &= chk("files kept (same 12 entries)", list(dm["files"]), list(old_dm["files"]))
    ok &= chk("every file entry keeps content / reference_canonical_sha256 / canonical_check, values unchanged",
              all(dm["files"][f][k] == old_dm["files"][f][k] for f in dm["files"] for k in ("content", "reference_canonical_sha256", "canonical_check")), True)
    ok &= chk("TEST entries keep generation_allowed unchanged", all(dm["files"][f]["generation_allowed"] == old_dm["files"][f]["generation_allowed"] for f in ("test_qa.jsonl", "general_test.jsonl", "d2_test.jsonl")), True)
    ok &= chk("every split_sha256 file still has a reference hash (non-TEST) or an st10_record rule (TEST) in DATA_MANIFEST files",
              [f for f in old_sm["split_sha256"] if not (dm["files"][f]["reference_canonical_sha256"] or "st10_record" in dm["files"][f]["canonical_check"])], [])
    rv = {r["file"]: r["value"] for r in dm["reported_values"]}
    ok &= chk("where actual hashes go: step1_record (9 non-TEST files) and st10_record (TEST file sha256) in reported_values; SPLIT actual_hashes",
              ("data hashes of the 9 non-TEST files" in rv["metrix/e1-v1/results/step1_record.json"], "TEST file sha256" in rv["metrix/e1-v1/results/st10_record.json"], "results/step1_record.json" in sm["actual_hashes"] and "results/st10_record.json" in sm["actual_hashes"]), (True, True, True))
    ok &= chk("protocol 2.8 lists 9 non-TEST files", len(re.findall(r"`([A-Za-z0-9_]+\.jsonl?)`", [l for l in proto.splitlines() if l.startswith("非 TEST:")][0].split("TEST(")[0])), 9)
    ok &= chk("hashing definitions of byte_sha256 / canonical_sha256 still in both manifests", ("byte_sha256" in dm["hashing"] and "canonical_sha256" in dm["hashing"], "byte_sha256" in sm["hashing"] and "canonical_sha256" in sm["hashing"]), (True, True))
    refs = [n for n in NAMES if re.search(r"split_sha256|NOT_GENERATED", open(A.V1 + "/" + n, encoding="utf-8").read())]
    refs += ["METRIX_E1V1_PROTOCOL.md"] if re.search(r"split_sha256|NOT_GENERATED", proto) else []
    ok &= chk("remaining references to split_sha256 / NOT_GENERATED in protocol and JSON files", refs, [])
    st12 = [l for l in proto.splitlines() if l.startswith("- ST12:")][0]
    ok &= chk("ST12: manifests not rewritten during execution; actual hashes go to results records", ("执行中不改写本协议与四个 JSON 中的任何字段" in st12, "results/step1_record.json" in st12), (True, True))

    # ======================= (g) provenance =======================
    print("=== (g) provenance (read-only git commands)")
    ok &= chk("HEAD", git("rev-parse", "HEAD").strip(), HEAD)
    ok &= chk("HEAD tree = round-1 staged tree", git("rev-parse", "HEAD^{tree}").strip(), "0e3dc49eaca9b07254e61301bc2602f8d8a39eea")
    ok &= chk("branch", git("branch", "--show-current").strip(), "metrix-e1-v1-protocol-v1")
    idx = sorted((l.split()[0], l.split()[1], l.split("\t", 1)[1]) for l in git("ls-files", "-s").splitlines())
    tre = sorted((l.split()[0], l.split()[2], l.split("\t", 1)[1]) for l in git("ls-tree", "-r", TREE).splitlines())
    ok &= chk(f"index entries equal tree {TREE[:8]}… (git ls-files -s vs git ls-tree -r)", idx == tre and len(idx) > 0, True)
    ok &= chk("unstaged changes to tracked files (git diff --name-only)", git("diff", "--name-only").split(), [])
    outside = [l for l in git("diff", "--cached", "--name-only", "HEAD").splitlines() if not l.startswith("metrix/e1-v1/")]
    ok &= chk("staged changes outside metrix/e1-v1/", outside, [])
    raw = open(DIFF_FILE, encoding="utf-8").read()
    parts = re.split(r"(?m)^(?=diff --git )", raw)[1:]
    same = []
    for p in parts:
        path = re.match(r"diff --git a/(\S+) ", p).group(1)
        same.append((path, git("diff", "--cached", "HEAD", "--", path) == p))
    ok &= chk(f"deliverable diff: per-file hunks equal to 'git diff --cached HEAD -- <file>' ({len(parts)} files)", [s for s in same if not s[1]], [])
    print("ITEM2 round 2:", "ALL MATCH" if ok else "MISMATCH PRESENT")


if __name__ == "__main__":
    main()
