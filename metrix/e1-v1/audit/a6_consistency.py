# data-auditor, E1-V1 round 1, item 6: data-related consistency between METRIX_E1V1_PROTOCOL.md
# and the four JSON files (seeds, counts, rule text, hashes), plus the git provenance of the
# referenced commits. Reads only protocol / manifest text, the Pilot manifests and git metadata.
import json
import re
import subprocess
import sys

sys.path.insert(0, "/home/user/OpenMythos/metrix/e1-v1/audit")
import audit_lib as A  # noqa: E402


def git(*args):
    return subprocess.run(["git", "-C", A.REPO] + list(args), capture_output=True, text=True).stdout.strip()


def walk(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk(v, f"{path}[{i}]")
    else:
        yield path, obj


def chk(label, got, exp):
    ok = got == exp
    print(f"{'OK  ' if ok else 'DIFF'} {label}: got {got} | expected {exp}")
    return ok


def main():
    ok = True
    proto = open(A.V1 + "/METRIX_E1V1_PROTOCOL.md", encoding="utf-8").read()
    J = {n: A.load_json(A.V1 + "/" + n) for n in ("DATA_MANIFEST.json", "SPLIT_MANIFEST.json", "DOSE_SPACE.json", "DAMAGE_MANIFEST.json")}
    pdm = A.load_json(A.PILOT + "/DATA_MANIFEST.json")
    psm = A.load_json(A.PILOT + "/SPLIT_MANIFEST.json")
    dm, sm, ds, gm = J["DATA_MANIFEST.json"], J["SPLIT_MANIFEST.json"], J["DOSE_SPACE.json"], J["DAMAGE_MANIFEST.json"]

    # ---- full 64-hex hashes in the protocol: where do they occur in the JSON files ----
    json_vals = {}
    for n, j in J.items():
        for p, v in walk(j):
            if isinstance(v, str):
                for h in re.findall(r"\b[0-9a-f]{64}\b", v):
                    json_vals.setdefault(h, []).append(f"{n}:{p}")
                for h in re.findall(r"\b[0-9a-f]{40}\b", v):
                    json_vals.setdefault(h, []).append(f"{n}:{p}")
    ph = sorted(set(re.findall(r"(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])", proto)))
    print("64-hex values in the protocol:", len(ph))
    for h in ph:
        loc = json_vals.get(h, [])
        print(f"  {h[:12]}… in JSON: {len(loc)} {loc[:3]}")
        if not loc:
            print("    (not in any of the four JSON files)")
    pc = sorted(set(re.findall(r"(?<![0-9a-f])[0-9a-f]{40}(?![0-9a-f])", proto)))
    print("40-hex values (commits / revisions) in the protocol:", pc)
    for h in pc:
        print(f"  {h} in JSON: {json_vals.get(h, [])[:3]} | git cat-file -t: {git('cat-file', '-t', h) or 'not a local object'}")
    # abbreviated hashes 'xxxxxxxx…yyyy' in the protocol must expand to a full value in the JSON files
    abbrev = re.findall(r"`([0-9a-f]{8})…([0-9a-f]{4})`", proto)
    for a, b in abbrev:
        full = [h for h in json_vals if h.startswith(a) and h.endswith(b)]
        ok &= chk(f"abbreviated {a}…{b} expands to exactly one JSON value", len(full), 1)
    abbrev2 = re.findall(r"`([0-9a-f]{8})…`", proto)
    for a in abbrev2:
        full = [h for h in json_vals if h.startswith(a)]
        ok &= chk(f"abbreviated {a}… matches exactly one JSON value", len(full), 1)

    # ---- seeds ----
    occ = [(proto.count("\n", 0, m.start()) + 1, m.group(1), int(m.group(2))) for m in re.finditer(r"`(DATA_SEED|CANDIDATE_SEED|BOOTSTRAP_SEED) = (\d+)`", proto)]
    print("protocol seed assignments (line, name, value):", occ)
    # the Pilot DATA_SEED 20261110 is allowed only where the protocol regenerates the Pilot facts (2.2 change 3)
    other = [o for o in occ if o[2] != dm["seeds"][o[1]]]
    for o in other:
        line = proto.splitlines()[o[0] - 1]
        print(f"  value differing from DATA_MANIFEST at line {o[0]}: {o[1]} = {o[2]} | Pilot regeneration context: {'Pilot' in line and '重新生成 Pilot' in line}")
    ok &= chk("seed assignments differing from DATA_MANIFEST outside the Pilot regeneration sentence",
              [o for o in other if "重新生成 Pilot" not in proto.splitlines()[o[0] - 1]], [])
    sec0 = [l for l in proto.splitlines() if l.startswith("**种子(PROPOSED)**")][0]
    seeds = {k: int(v) for k, v in re.findall(r"`(DATA_SEED|CANDIDATE_SEED|BOOTSTRAP_SEED) = (\d+)`", sec0)}
    print("protocol section 0 seeds", seeds)
    for k in ("DATA_SEED", "CANDIDATE_SEED", "BOOTSTRAP_SEED"):
        ok &= chk(f"{k} protocol vs DATA_MANIFEST", seeds.get(k), dm["seeds"][k])
    ok &= chk("TRAIN_SEEDS protocol vs DATA_MANIFEST", "`TRAIN_SEEDS = [101, 202, 303]`" in proto, dm["seeds"]["TRAIN_SEEDS"] == [101, 202, 303])
    ok &= chk("DOSE_SPACE training seeds", ds["seeds"]["training_seeds"], dm["seeds"]["TRAIN_SEEDS"])
    ok &= chk("DOSE_SPACE Z0 / P+ seeds", (ds["controls"]["Z0"]["seeds"], ds["controls"]["P+"]["seeds"]), (dm["seeds"]["TRAIN_SEEDS"], dm["seeds"]["TRAIN_SEEDS"]))
    ok &= chk("DAMAGE_MANIFEST bootstrap seed text", gm["statistics"]["seed"], f"BOOTSTRAP_SEED = {dm['seeds']['BOOTSTRAP_SEED']}")
    ok &= chk("seeds differ from Pilot (20261110-20261112)", {dm["seeds"][k] for k in ("DATA_SEED", "CANDIDATE_SEED", "BOOTSTRAP_SEED")} & {20261110, 20261111, 20261112}, set())
    ok &= chk("CANDIDATE_SEED text in SPLIT_MANIFEST", sm["candidates"]["seed"], f"CANDIDATE_SEED = {dm['seeds']['CANDIDATE_SEED']}")

    # ---- name generation: identical to the Pilot manifest except the listed changes ----
    pn, vn = pdm["name_generation"], dm["name_generation"]
    for k in sorted(set(pn) | set(vn)):
        if pn.get(k) != vn.get(k):
            print(f"  name_generation.{k} differs from Pilot: Pilot {json.dumps(pn.get(k), ensure_ascii=False)[:160]} | V1 {json.dumps(vn.get(k), ensure_ascii=False)[:160]}")
    same_keys = ["natural", "random", "streams", "accepted_strings_scope", "anchor_rule", "token_counts", "max_draws_per_stream", "on_exhaustion", "draw"]
    ok &= chk("name_generation rule fields equal to Pilot (natural, random, draw, streams, scope, anchor rule, token counts, max draws)",
              [k for k in same_keys if pn.get(k) != vn.get(k)], [])
    ok &= chk("s_permutation rule equal to Pilot apart from counts", pdm["s_permutation"]["rule"].replace("15", "30"), dm["s_permutation"]["rule"])
    ok &= chk("templates identical to Pilot SPLIT_MANIFEST", sm["templates"] == psm["templates"], True)
    ok &= chk("template_freeze normalization identical to Pilot", sm["template_freeze"]["normalization"], psm["template_freeze"]["normalization"])
    for k in ("way", "pool", "draw", "shared_by", "duplicates", "pool_too_small", "exposure_matching"):
        ok &= chk(f"candidates.{k} identical to Pilot", sm["candidates"][k], psm["candidates"][k])
    ok &= chk("hashing rules identical to Pilot", (dm["hashing"], sm["hashing"]), (pdm["hashing"], psm["hashing"]))
    for k in ("source", "selection", "truncate_to_model_tokens", "document_rule", "decoded_texts_canonical_sha256"):
        ok &= chk(f"anchor_text.{k} identical to Pilot", dm["anchor_text"][k], pdm["anchor_text"][k])
    for k in ("source_file", "source_file_sha256", "decode_with", "decode_tokenizer_json_sha256", "window_rule"):
        ok &= chk(f"D1 {k} identical to Pilot general_text", gm["d1"][k], pdm["general_text"][k])
    ok &= chk("model / tokenizer identical to Pilot", (dm["model"]["repo"], dm["model"]["revision"], dm["model"]["tokenizer"]["files_sha256"]),
              (pdm["model"]["repo"], pdm["model"]["revision"], pdm["model"]["tokenizer"]["files_sha256"]))

    # ---- counts in the protocol text vs JSON ----
    ok &= chk("320 = 240 + 80 in protocol 2.1", "**320 facts = 240 learned + 80 unread**" in proto, True)
    ok &= chk("per cell 30 + 10 (protocol vs DATA_MANIFEST)", "每个 cell **30 learned + 10 unread**" in proto, dm["facts"]["per_cell"] == {"cell": "relation x stratum (8 cells)", "learned": 30, "unread": 10})
    ok &= chk("pool 29 / 9 (protocol 2.5 vs SPLIT_MANIFEST)", "learned 29 个、unread 9 个" in proto, sm["candidates"]["pool_sizes"] == {"learned": 29, "unread": 9})
    ok &= chk("Y 480 sentences (protocol 2.6 vs DATA_MANIFEST files)", "共 480 句" in proto, dm["files"]["train_Y.jsonl"]["content"].startswith("480"))
    ok &= chk("Y/F authoring numbers protocol vs manifest", "F 3,802 token,Y 4,541 token,比值 1.1944" in proto, dm["y_ratio"]["authoring"] == {"F_tokens": 3802, "Y_tokens": 4541, "ratio": 1.1944})
    ok &= chk("D1 DEV 400 / D2 DEV 800 (protocol 7.2 vs DAMAGE_MANIFEST)", ("撰写时 400(每领域 100,排除 0)" in proto) and ("| 800;撰写时排除 0" in proto),
              gm["d1"]["dev"]["authoring"]["kept"] == 400 and gm["d2"]["datasets"]["mmlu"]["authoring_dev"]["items"] == 800)
    ok &= chk("D1 TEST 175 per domain (protocol vs DAMAGE_MANIFEST)", "400(每领域可用 175 行)" in proto, gm["d1"]["test"]["available_per_domain_after_skip"] == 175)
    ok &= chk("MMLU rows (protocol vs DAMAGE_MANIFEST)", ("1,531 行" in proto) and ("14,042 行" in proto),
              (gm["d2"]["datasets"]["mmlu"]["dev_source"]["rows"], gm["d2"]["datasets"]["mmlu"]["test_source"]["rows"]) == (1531, 14042))
    ok &= chk("ARC rows (protocol vs DAMAGE_MANIFEST)", ("299 + 570 行" in proto) and ("1,172 + 2,376 行" in proto),
              [s["rows"] for s in gm["d2"]["datasets"]["arc"]["dev_source"] + gm["d2"]["datasets"]["arc"]["test_source"]] == [299, 570, 1172, 2376])
    print("protocol 7.1 ARC sentence:", re.search(r"只用恰好 4 个选项的题\(撰写时[^)]*\)", proto).group(0))
    print("protocol 15 ARC sentence:", re.search(r"ARC 的 DEV 来源只有[^;|]*", proto).group(0))
    print("DAMAGE_MANIFEST arc.authoring_dev.excluded:", gm["d2"]["datasets"]["arc"]["authoring_dev"]["excluded"],
          "(see a5_damage.txt: DEV source rows by number of labels)")
    ok &= chk("D2 letter ids protocol vs DAMAGE_MANIFEST", "id 362、425、356、422" in proto, gm["d2"]["letter_token_ids"] == {"A": 362, "B": 425, "C": 356, "D": 422})
    ok &= chk("D2 prompt instruction text protocol vs DAMAGE_MANIFEST", '`I = "Answer the following multiple choice question with the letter of the correct option."`' in proto,
              "I = 'Answer the following multiple choice question with the letter of the correct option.'" in gm["d2"]["prompt"])
    ok &= chk("D2 seeds/purposes protocol vs manifest", all(p in proto for p in ("d2:mmlu:validation:order", "d2:mmlu:test:order", "d2:arc:validation:order", "d2:arc:test:order")),
              all(p in dm["seeds"]["purposes"]["d2_order"] for p in ("d2:mmlu:validation:order", "d2:mmlu:test:order", "d2:arc:validation:order", "d2:arc:test:order")))
    # dose ladder
    ok &= chk("ladder_steps = 30 * ladder_passes", ds["dose"]["ladder_steps"], [30 * k for k in ds["dose"]["ladder_passes"]])
    ok &= chk("ladder in protocol 6.3", "k ∈ {1, 2, 3, 4, 6, 8, 11, 16, 23, 32}" in proto, ds["dose"]["ladder_passes"] == [1, 2, 3, 4, 6, 8, 11, 16, 23, 32])
    ok &= chk("steps per pass: 240/8 and 480/16", (240 // ds["training_contract"]["batch_size_statements"], 480 // ds["training_contract"]["batch_size_Y"]), (30, 30))
    ok &= chk("anchor schedule covers the longest run (960 steps)", max(ds["training_contract"]["passes"].values()) * 30, 960)
    ok &= chk("d0 = 11 passes in the ladder", ds["dose"]["d0_passes"] in ds["dose"]["ladder_passes"], True)
    # reference hashes appear identically in the protocol and manifests
    pairs = [("facts list", dm["name_generation"]["expected_facts_canonical_sha256"]),
             ("pilot facts", dm["name_generation"]["preseed"]["pilot_facts_canonical_sha256"]),
             ("candidates", dm["files"]["candidates.json"]["reference_canonical_sha256"]),
             ("train_S", dm["files"]["train_S.jsonl"]["reference_canonical_sha256"]),
             ("train_Y", dm["files"]["train_Y.jsonl"]["reference_canonical_sha256"]),
             ("anchor decoded", dm["anchor_text"]["decoded_texts_canonical_sha256"]),
             ("template set", sm["template_freeze"]["template_set_sha256"]),
             ("general_dev", dm["files"]["general_dev.jsonl"]["reference_canonical_sha256"]),
             ("d2_dev mmlu", dm["files"]["d2_dev.jsonl"]["reference_canonical_sha256"]["mmlu"]),
             ("d2_dev arc", dm["files"]["d2_dev.jsonl"]["reference_canonical_sha256"]["arc"]),
             ("mmlu validation file", gm["d2"]["datasets"]["mmlu"]["dev_source"]["sha256"]),
             ("mmlu test file", gm["d2"]["datasets"]["mmlu"]["test_source"]["sha256"])]
    for name, h in pairs:
        ok &= chk(f"manifest hash '{name}' written in the protocol", h in proto, True)
    not_in_proto = ["train_F.jsonl", "dev_qa.jsonl", "facts.jsonl", "anchor_text.jsonl"]
    print("reference hashes present only in DATA_MANIFEST (protocol refers to DATA_MANIFEST.json: files):",
          {n: dm["files"][n]["reference_canonical_sha256"] in proto for n in not_in_proto})
    # SPLIT_MANIFEST / DATA_MANIFEST cross references
    ok &= chk("candidate hash DATA_MANIFEST vs SPLIT_MANIFEST", dm["files"]["candidates.json"]["reference_canonical_sha256"], sm["candidates"]["candidate_mapping_sha256"])
    ok &= chk("train_S hash DATA_MANIFEST files vs s_permutation", dm["files"]["train_S.jsonl"]["reference_canonical_sha256"], dm["s_permutation"]["expected_train_S_canonical_sha256"])
    ok &= chk("general_dev hash DATA_MANIFEST vs DAMAGE_MANIFEST", dm["files"]["general_dev.jsonl"]["reference_canonical_sha256"], gm["d1"]["dev"]["authoring"]["canonical_sha256"])
    ok &= chk("d2_dev hashes DATA_MANIFEST vs DAMAGE_MANIFEST", dm["files"]["d2_dev.jsonl"]["reference_canonical_sha256"],
              {"mmlu": gm["d2"]["datasets"]["mmlu"]["authoring_dev"]["canonical_sha256"], "arc": gm["d2"]["datasets"]["arc"]["authoring_dev"]["canonical_sha256"]})
    ok &= chk("anchor file hash DATA_MANIFEST files vs anchor_text.file_canonical_sha256_authoring", dm["files"]["anchor_text.jsonl"]["reference_canonical_sha256"], dm["anchor_text"]["file_canonical_sha256_authoring"])
    ok &= chk("L-check authoring results DATA_MANIFEST pilot_disjointness vs SPLIT L7", dm["pilot_disjointness"]["authoring_result"], sum(sm["leakage_checks"]["L7_pilot_disjoint"]["authoring_result"].values()))
    # L6 / L8 scope
    ok &= chk("L8 applies_to (SPLIT) = the four damage files", sm["leakage_checks"]["L8_fictional_strings_in_damage_sets"]["applies_to"], ["general_dev", "general_test", "d2_dev", "d2_test"])
    print("L6 test_part.count text (SPLIT_MANIFEST):", sm["leakage_checks"]["L6_anchor_ngram"]["test_part"]["count"])
    print("L6 test_part.pairs (SPLIT_MANIFEST):", sm["leakage_checks"]["L6_anchor_ngram"]["test_part"]["pairs"])

    # ---- git provenance ----
    print("git HEAD", git("rev-parse", "HEAD"), "| branch", git("branch", "--show-current"))
    print("git log -1 6e03468…:", git("log", "-1", "--format=%H %s", "6e03468956208c422d0d41c08edaaf116166338c"))
    print("git log -1 87a244d…:", git("log", "-1", "--format=%H %s", "87a244db28a901f9e89282b50df76778ab5c2887"))
    pf = open(A.PILOT + "/PROTOCOL_FROZEN", encoding="utf-8").read()
    ok &= chk("Pilot PROTOCOL_FROZEN mentions 87a244db…", "87a244db28a901f9e89282b50df76778ab5c2887" in pf, True)
    ok &= chk("Pilot protocol at HEAD equal to Pilot protocol at the v1.1 freeze commit",
              git("rev-parse", "HEAD:metrix/e1-pilot/METRIX_E1_PROTOCOL.md") == git("rev-parse", "87a244db28a901f9e89282b50df76778ab5c2887:metrix/e1-pilot/METRIX_E1_PROTOCOL.md"), True)
    ok &= chk("Pilot SPLIT_MANIFEST templates at freeze commit = V1 templates",
              json.loads(git("show", "87a244db28a901f9e89282b50df76778ab5c2887:metrix/e1-pilot/SPLIT_MANIFEST.json"))["templates"] == sm["templates"], True)
    staged_outside = [l for l in git("diff", "--cached", "--name-only", "HEAD").splitlines() if not l.startswith("metrix/e1-v1/")]
    ok &= chk("staged changes outside metrix/e1-v1/", staged_outside, [])
    # read-only: the index entries (mode, blob, path) must equal the entries of tree 0e3dc49e…
    idx = sorted((l.split()[0], l.split()[1], l.split("\t", 1)[1]) for l in git("ls-files", "-s").splitlines())
    tre = sorted((l.split()[0], l.split()[2], l.split("\t", 1)[1]) for l in git("ls-tree", "-r", "0e3dc49eaca9b07254e61301bc2602f8d8a39eea").splitlines())
    ok &= chk("index entries equal tree 0e3dc49e… (git ls-files -s vs git ls-tree -r)", idx == tre and len(idx) > 0, True)
    print("index entries", len(idx), "| tree entries", len(tre))
    print("ITEM6:", "ALL MATCH" if ok else "MISMATCH PRESENT")


if __name__ == "__main__":
    main()
