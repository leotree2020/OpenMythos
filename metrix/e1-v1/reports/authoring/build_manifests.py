#!/usr/bin/env python3
"""E1-V1 protocol authoring: writes the four JSON companions of METRIX_E1V1_PROTOCOL.md (DATA_MANIFEST.json,
SPLIT_MANIFEST.json, DOSE_SPACE.json, DAMAGE_MANIFEST.json). The 32 templates and the Pilot model / name-generation /
anchor blocks are copied from the frozen Pilot manifests (read from the repository, not retyped); every V1 hash is the
value printed in reports/authoring/v1_data_check.txt and d2_dataset_metadata.txt. Run from the repository root:

  python3 metrix/e1-v1/reports/authoring/build_manifests.py

Freeze (Review Gate ruling 2026-11-28 A1-A5, Owner approval 2026-11-28 12:13:25 UTC C1-C4, recorded in
metrix/e1-v1/tasks/E1V1_FREEZE_OWNER_MESSAGE.md): version v1, status PROTOCOL_FROZEN; protocol section 17 lists the
changes made to the four JSON files at the freeze.
"""
import copy
import json
from pathlib import Path

PILOT = Path("metrix/e1-pilot")
V1 = Path("metrix/e1-v1")
pdm = json.loads((PILOT / "DATA_MANIFEST.json").read_text(encoding="utf-8"))
psm = json.loads((PILOT / "SPLIT_MANIFEST.json").read_text(encoding="utf-8"))

OWNER_APPROVAL = "Owner approval 2026-11-28 12:13:25 UTC (metrix/e1-v1/tasks/E1V1_FREEZE_OWNER_MESSAGE.md)"
HEAD = {"protocol": "METRIX-E1-V1", "version": "v1", "status": "PROTOCOL_FROZEN",
        "frozen": {"approved_by": "Owner", "approval_utc": "2026-11-28T12:13:25Z",
                   "approval_record": "metrix/e1-v1/tasks/E1V1_FREEZE_OWNER_MESSAGE.md (C1-C4)",
                   "review_gate_ruling": "2026-11-28, items A1-A6 of the same record (protocol section 17)",
                   "condition": "A and C done and no BLOCKER in the review of the freeze commit (C4)",
                   "freeze_record": "metrix/e1-v1/PROTOCOL_FROZEN (full hash of the freeze commit; sha256 of the protocol and the four JSON files at that commit)"},
        "origin": {"repository": "leotree2020/OpenMythos", "start_branch": "metrix-e1-pilot-protocol-v1",
                   "start_commit": "6e03468956208c422d0d41c08edaaf116166338c",
                   "authoring_branch": "metrix-e1-v1-protocol-v1",
                   "pilot_protocol": "metrix/e1-pilot/METRIX_E1_PROTOCOL.md v1.1, frozen commit 87a244db28a901f9e89282b50df76778ab5c2887"}}
HASHING = copy.deepcopy(pdm["hashing"])


def dump(name, obj):
    (V1 / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print("wrote", V1 / name)


# --------------------------------------------------------------------------------------------- DATA_MANIFEST
model = copy.deepcopy(pdm["model"])
model["input_convention"]["d2_scoring"] = (
    "chat(p) + 'The answer is' + ' ' + letter, letter in A, B, C, D; chat as for qa; ' A', ' B', ' C', ' D' are single "
    "tokens 362, 425, 356, 422; only that token is scored (log-probability of the next token after the context); "
    "protocol sections 0 and 7.1")
model["libraries"]["lock"] = "versions of metrix/e1-pilot/requirements.lock (protocol section 0)"
model["specified_by"] = pdm["model"]["specified_by"] + "; unchanged for E1-V1 (Task Order section 0)"

name_gen = copy.deepcopy(pdm["name_generation"])
name_gen["order"] = name_gen["order"].replace("the first 15 accepted strings are learned, the next 5 unread",
                                              "the first 30 accepted strings are learned, the next 10 unread")
name_gen["entity_procedure"] = name_gen["entity_procedure"].replace("until 20 are accepted", "until 40 are accepted")
name_gen["answer_token_length_rule"]["accept"] = name_gen["answer_token_length_rule"]["accept"].replace(
    "until 20", "until 40")
name_gen["preseed"] = {
    "rule": "before the first draw the accepted set holds the 320 entity and answer strings of the E1-PILOT facts, so "
            "reject_if also rejects strings equal or close to a Pilot string (protocol 2.2 change 3, 2.7)",
    "pilot_facts": "regenerated with the Pilot rules of metrix/e1-pilot/METRIX_E1_PROTOCOL.md 2.2 and DATA_SEED 20261110",
    "pilot_facts_canonical_sha256": "406c8801c5b69ed235cbe516658ad9ee3e3a8cfe8e4e348a0c1fd7952f2e6b97",
    "on_mismatch": "ST12"}
name_gen["changes_from_pilot"] = ["DATA_SEED 20261128", "40 accepted per role and cell (30 learned + 10 unread)",
                                  "accepted set pre-seeded with the 320 Pilot strings"]
name_gen["reference_implementation"] = "metrix/e1-v1/reports/authoring/v1_data_check.py (Names.build)"
name_gen["expected_facts_canonical_sha256"] = "0fc5ad819500e8a9f56771405af67d0fa71bafabba25bf8f4c3e5b6d684e01f4"
name_gen["authoring_draws"] = "reports/authoring/v1_data_check.txt (entity 40-83, answer 80-270 draws per cell)"

name_gen["answer_token_length_rule"]["purpose"] = name_gen["answer_token_length_rule"]["purpose"].replace(
    "all 20 answers of a cell", "all 40 answers of a cell")

s_perm = copy.deepcopy(pdm["s_permutation"])
s_perm["rule"] = s_perm["rule"].replace("the 15 learned answers", "the 30 learned answers")
co = s_perm["call_order"]
for a, b in (("list(range(15))", "list(range(30))"), ("learned facts 01..15", "learned facts 01..30"), ("i = 0..14", "i = 0..29")):
    assert a in co, a
    co = co.replace(a, b)
s_perm["call_order"] = co
s_perm["expected_train_S_canonical_sha256"] = "7ac254f6e87e017ecc6ce9945006cda1c5310c7358d69da88e5c81cfdc907bd6"
s_perm["reference_implementation"] = "metrix/e1-v1/reports/authoring/v1_data_check.py"
s_perm["fixed"] = "Pilot protocol 2.6 detail 4, unchanged; E1-V1 DATA_SEED"

anchor = copy.deepcopy(pdm["anchor_text"])
anchor["schedule"] = ("step s uses documents (4*s + i) mod 512, i = 0..3; optimizer steps are numbered s = 1..960; "
                      "documents numbered 0..511 in anchor_text.jsonl order (interpretation B1)")
anchor["same_as_pilot"] = "the same 512 documents as E1-PILOT (protocol 2.6)"
anchor["file_canonical_sha256_authoring"] = "2089e656819d1fe0f6ececcc26e5cade09ee80a92c50e7c8f607fa4e0ef46da5"


def f(content, ref, record, test=False):
    d = {"content": content, "record": record}
    if test:
        d["generation_allowed"] = ("only in protocol section 10 step 10: after results/selection_freeze_record.json "
                                   "is committed and pushed and the Owner approvals of TEST generation are committed")
        d["reference_canonical_sha256"] = None
    else:
        d["reference_canonical_sha256"] = ref
    return d


files = {
    "facts.jsonl": f("all 320 facts", "4eeee6d198dede289886b9cd7941f362f3b9fba611aea551223289781de307a9",
                     "{fact_id, exposure ('learned' or 'unread'), relation, stratum ('natural' or 'random'), entity, answer}, generation order"),
    "train_F.jsonl": f("240 TRAIN statements (arms F, L, A, Z0, P+)", "fb1d80064c4c779609ef40a29151bbf1fd1f5f1e1c768c6c5360412f38819511",
                       "{fact_id, template_id, text}, fact order"),
    "train_S.jsonl": f("240 statements with permuted answers (arm S)", "7ac254f6e87e017ecc6ce9945006cda1c5310c7358d69da88e5c81cfdc907bd6",
                       "{fact_id, answer_fact_id, text} (Pilot 2.6)"),
    "train_Y.jsonl": f("480 style-only sentences (arm Y)", "82314e6b4a5917d0d4e62e3f34f4ab80e330c8dc5b5c7395e1183809c4daf96b",
                       "{fact_id, template_id, kind, text}; fact order, Y_ENTITY before Y_ANSWER"),
    "dev_qa.jsonl": f("DEV questions: 320 facts x 2 templates", "39ea5ea1ff730cbc73d12542e10173baee83759aa4477cc930574ce93ce5c7ce",
                      "{fact_id, template_id, question}; fact order, then template order"),
    "candidates.json": f("candidate lists of all 320 facts", "79600769eef1876b54bc3d174874880e8e05bab11290f97360559f99324235c3",
                         "one JSON object {fact_id: [4 candidates]} (Pilot 2.5)"),
    "anchor_text.jsonl": f("512 anchor documents (arm A)", "2089e656819d1fe0f6ececcc26e5cade09ee80a92c50e7c8f607fa4e0ef46da5",
                           "{doc: 0-based document number (anchor order), source_row: 0-based row index in the parquet file order, ids: the first at most 128 ids of encode(text, add_special_tokens=False), text: tokenizer.decode(ids) with default arguments}"),
    "general_dev.jsonl": f("D1 DEV windows (DAMAGE_MANIFEST.json: d1.dev)", "e8350160464963e684e0c58826d53250dec4de366a716d3111aa8ec5089ce281",
                           "{domain, doc_id (of eval_sets.jsonl), ids: the first at most 256 ids fed to the model, text: tokenizer.decode(ids) with default arguments}"),
    "d2_dev.jsonl": f("D2 DEV items (DAMAGE_MANIFEST.json: d2.dev); dataset MMLU (" + OWNER_APPROVAL + ", C2)",
                      "f40c146a3da500f13797dcfedfb2932e8a5dc88a6b43cbd423bf8fb549a688be",
                      "{item: 0-based position in the file, source_row: 0-based row index in the source list (MMLU: parquet row; ARC, not adopted: index in Challenge then Easy), subject (MMLU subject; ARC, not adopted: item id), prompt: the D2 prompt p, answer: the correct letter}"),
    "test_qa.jsonl": f("TEST questions: 320 facts x 3 templates", None, "{fact_id, template_id, question}", test=True),
    "general_test.jsonl": f("D1 TEST windows (DAMAGE_MANIFEST.json: d1.test)", None, "as general_dev.jsonl", test=True),
    "d2_test.jsonl": f("D2 TEST items (DAMAGE_MANIFEST.json: d2.test)", None, "as d2_dev.jsonl", test=True),
}
files["d2_dev.jsonl"]["not_adopted_alternative"] = {
    "arc": {"reference_canonical_sha256": "1ea77c8adeb84b6d5f7a3aa699ab02951e4f43bd27ba14f36c3a32287e04ac32",
            "status": "not adopted alternative (C2); verification record kept, not used in E1-V1"}}
for k in files:
    files[k]["canonical_check"] = "the canonical_sha256 of the generated file must equal reference_canonical_sha256 (ST12)" \
        if not k.startswith(("test_", "general_test", "d2_test")) else "sha256 recorded in st10_record.json and the TEST marker"

RES = "metrix/e1-v1/results/"
reported = [
    {"value": "data hashes of the 9 non-TEST files; L1-L8 DEV counts", "file": RES + "step1_record.json", "field": "files, leakage"},
    {"value": "preflight step seconds (F, L, A), DEV evaluation seconds, peak memory, estimate, ST11 bound", "file": RES + "preflight_record.json", "field": "preflight"},
    {"value": "N on DEV: Acc learned / unread / per stratum, Acc_CB, per-fact Score and CB, per-window NLL, D1-all / D1-diff / D1-same levels, per-item D2 letter scores, Acc_D2", "file": RES + "n_dev_record.json", "field": "summary, units"},
    {"value": "Gate D: Z0 per-tensor numerical equality to N (torch.equal; -0.0 equals +0.0), state hashes (report only) and maximal differences per seed; P+ D1-all / D1-diff / D1-same / D2 per seed and seed-average with 95% CI, per-unit values; G-D4 differences; sigma_N for the four metrics; G-D5 pairs; G-D1..G-D4 decisions; Gate D decision and the D2 qualification status (D2_NOT_QUALIFIED or not)", "file": RES + "gate_d_record.json", "field": "z0, p_plus, reproducibility, noise, gate_d"},
    {"value": "MARGIN_RECORD: formula, sigma_N inputs, input record sha256 and commit, m(D1-all), m(D1-diff), m(D1-same), m(D2)", "file": RES + "margin_record.json", "field": "margin"},
    {"value": "every training run: per dose point Acq (learned, per stratum), Acc unread, Spill, FPR, Acc_CB, D1-all / D1-diff / D1-same / per-domain dNLL and PPL_degradation%, Acc_D2, D2; per-unit Score, CB, window NLL, D2 letter scores; compute accounting; saved checkpoint state_sha256; finite flags", "file": RES + "runs/<run>.json", "field": "dose_points, accounting, checkpoints"},
    {"value": "S own-mapping accuracy at d0; G0.1-G0.9 values (G0.9 report only); fact comparisons F-N, S-N, Y-N per seed and seed-average; Spill per arm; AllCorrect on DEV", "file": RES + "gate0_record.json", "field": "values, comparisons"},
    {"value": "S, Y and F at d0 side by side (protocol section 1 Non-claims; Review Gate ruling 2026-11-28 A4): D1-all, D1-diff, D1-same, D1-books, D1-c4, D1-fineweb, D1-wikitext and D2 (with Acc_D2) on DEV, per seed and seed-average", "file": RES + "gate0_record.json", "field": "d0_damage"},
    {"value": "iso brackets, weights and checkpoint hashes per (method, seed, t); NOT_REACHED flags; DEV per-method iso damage and DEV Gate M comparisons for all metrics and points (seed-average and per seed, CI, conclusion words marked secondary); G-D5 Spearman correlation; list of TEST checkpoints", "file": RES + "selection_freeze_record.json", "field": "iso, dev_comparisons, g_d5, test_checkpoints"},
    {"value": "TEST-part counts L3a, L3b, L4, L5, L6, L8 (Executor and data-auditor); TEST file sha256; exclusion counts of D1 / D2 TEST", "file": RES + "st10_record.json", "field": "counts, files, exclusions"},
    {"value": "TEST: per model per-fact Score, EM, AllCorrect (N also CB), per-window NLL and per-item D2 letter scores of N and every bracket checkpoint; Acc, EM, FPR, Spill on TEST; T1-T3; Acq_TEST(X, t) and match status; all Gate M TEST comparisons (seed-average and per seed, CI, conclusion words); per-method iso damage on TEST; final status", "file": RES + "test_evaluation_result.json and " + RES + "test_details/", "field": "summaries, units, values, iso_test, comparisons, final"},
    {"value": "experiment records (Pilot section 10 template), two", "file": RES + "experiment_record_*.json", "field": "template"},
    {"value": "termination check (data-auditor, protocol section 14)", "file": "metrix/e1-v1/audit/termination_check.*", "field": "result"},
]

data_manifest = dict(HEAD)
data_manifest.update({
    "model": model,
    "seeds": {"DATA_SEED": 20261128, "CANDIDATE_SEED": 20261129, "TRAIN_SEEDS": [101, 202, 303], "BOOTSTRAP_SEED": 20261130,
              "rng_rule": pdm["seeds"]["rng_rule"],
              "purposes": {
                  "names": "DATA_SEED, 'names:<relation>:<stratum>:entity' and ':answer' (Pilot 2.2)",
                  "pilot_names": "DATA_SEED of E1-PILOT (20261110), same purposes (to regenerate the Pilot strings)",
                  "s_permutation": "DATA_SEED, 's-permutation:<relation>:<stratum>' (Pilot 2.6)",
                  "candidates": "CANDIDATE_SEED, 'cand:<fact_id>' (Pilot 2.5)",
                  "order": "TRAIN_SEED, 'order:<k>', k = 1..32 (interpretation B3)",
                  "lora_A": "TRAIN_SEED, 'lora_A:<module path>' (interpretation B5)",
                  "d2_order": "DATA_SEED, 'd2:mmlu:validation:order', 'd2:mmlu:test:order' (ARC, not adopted alternative, verification record only: 'd2:arc:validation:order', 'd2:arc:test:order')",
                  "bootstrap": "BOOTSTRAP_SEED, '<X>-<Y>:<split>:<metric>:<t>:<seed or avg>', 'P+-N:DEV:<metric>:-:<seed or avg>', 'N:DEV:<metric>:level'; fact metrics '<X>-<Y>:<split>:<seed or avg>' (interpretation B12)"}},
    "facts": {"total": 320, "learned": 240, "unread": 80, "relations": pdm["facts"]["relations"], "strata": pdm["facts"]["strata"],
              "per_cell": {"cell": "relation x stratum (8 cells)", "learned": 30, "unread": 10},
              "fact_schema": pdm["facts"]["fact_schema"],
              "fact_id_format": "E1V1-<L|U>-<relation>-<nat|rnd>-<two-digit index starting at 01>",
              "max_occurrences_of_an_answer_value": 1, "all_entity_and_answer_strings_globally_unique": True,
              "same_rules_as": "Pilot protocol 2.1, counts changed"},
    "name_generation": name_gen,
    "s_permutation": s_perm,
    "y_ratio": {"rule": "Y tokens / F tokens over one pass, each sequence = text ids + 1 <|endoftext|>; must lie in [0.80, 1.25], otherwise IMPLEMENTATION_FAIL (Pilot 2.6)",
                "authoring": {"F_tokens": 3802, "Y_tokens": 4541, "ratio": 1.1944}},
    "pilot_disjointness": {"check": "L7 (SPLIT_MANIFEST.json: leakage_checks.L7_pilot_disjoint)", "authoring_result": 0},
    "templates": {"count": 32, "list": "SPLIT_MANIFEST.json: templates (copied from the Pilot manifest)"},
    "anchor_text": anchor,
    "damage_sets": "DAMAGE_MANIFEST.json",
    "files": files,
    "reported_values": reported,
    "hashing": HASHING,
})
dump("DATA_MANIFEST.json", data_manifest)

# --------------------------------------------------------------------------------------------- SPLIT_MANIFEST
lc = copy.deepcopy(psm["leakage_checks"])
leak = {
    "L1_template_hash": dict(lc["L1_template_hash"], authoring_result={"duplicate_normalized_hashes": 0}),
    "L2_template_ngram": dict(lc["L2_template_ngram"], authoring_result={"max": 0.2}),
    "L3a_unread_fact": dict(lc["L3a_unread_fact"], authoring_result=0),
    "L3b_learned_answer_in_anchor": dict(lc["L3b_learned_answer_in_anchor"], authoring_result=0),
    "L4_question_text": dict(lc["L4_question_text"], corpora="train_F, train_S, train_Y and anchor_text", authoring_result={"dev_questions": 640, "found": 0}),
    "L5_identity": {"rule": "learned and unread fact_id sets disjoint; all 640 entity / answer strings distinct", "limit": 0, "authoring_result": 0},
    "L6_anchor_ngram": {"rule": lc["L6_general_text"]["rule"].replace("general_dev / general_test", "general_dev, general_test (D1) and d2_dev, d2_test (D2, the prompt text p)"),
                        "limit": 0, "report_only": lc["L6_general_text"]["report_only"],
                        "test_part": {"pairs": ["anchor_text vs general_test.jsonl", "anchor_text vs d2_test.jsonl"],
                                      "when": "protocol section 10 step 10, after the TEST files are generated and before the TEST evaluation",
                                      "count": "for each of general_test.jsonl and d2_test.jsonl separately: the word 13-grams of the 512 anchor documents merged into one set, those of all windows (D1) or all prompts (D2) of the file merged into another, 13-grams within each document, no concatenation across documents; the number of distinct elements of the intersection; texts = the decoded ids fed to the model (anchor <= 128 ids, window <= 256 ids) or the prompt p",
                                      "computed_by": "Executor and data-auditor, each on its own; the results must be equal"},
                        "authoring_result": {"d1_dev": 0, "d1_dev_token_id_13grams_report_only": 0, "d2_dev": 0}},
    "L7_pilot_disjoint": {"rule": "(a) V1 strings equal (lowercased) to one of the 320 Pilot strings + (b) V1 strings that trigger the 2.2 reject_if against a Pilot string of the same stratum + (c) fact_ids shared with the Pilot",
                          "limit": 0, "authoring_result": {"a": 0, "b": 0, "c": 0}},
    "L8_fictional_strings_in_damage_sets": {"rule": "D1 windows and D2 items whose text contains one of the 640 V1 strings case-insensitively with no ASCII letter or digit immediately before or after (or at a text boundary); one unit counts 1",
                                            "limit": 0, "applies_to": ["general_dev", "general_test", "d2_dev", "d2_test"],
                                            "text": "D1: the text field of the window (decode of the ids fed to the model, not the whole source document); D2: the prompt p",
                                            "test_part": "as L6: counted for general_test.jsonl and d2_test.jsonl separately by Executor and data-auditor in section 10 step 10; must be equal",
                                            "authoring_result": {"d1_dev": 0, "d2_dev": 0}},
}
split_manifest = dict(HEAD)
split_manifest.update({
    "fact_ids": {"learned": "E1V1-L-*: 240 facts, each with exactly one TRAIN statement",
                 "unread": "E1V1-U-*: 80 facts, no training text in any arm",
                 "assignment": "within a cell, generated facts 01-30 are learned and 31-40 (written as U 01-10) are unread; no fact changes class"},
    "splits": {"TRAIN": "TRAIN statements of learned facts (and the S / Y corpora derived from them)",
               "DEV": "2 questions per fact (learned and unread), DEV templates",
               "TEST": "3 questions per fact (learned and unread), TEST templates; generated only in protocol section 10 step 10",
               "damage_sets": "D1 and D2 DEV / TEST: DAMAGE_MANIFEST.json"},
    "templates": copy.deepcopy(psm["templates"]),
    "template_freeze": copy.deepcopy(psm["template_freeze"]),
    "candidates": dict(copy.deepcopy(psm["candidates"]), **{
        "seed": "CANDIDATE_SEED = 20261129",
        "pool_sizes": {"learned": 29, "unread": 9},
        "call_order": psm["candidates"]["call_order"].replace("14 for learned, 4 for unread", "29 for learned, 9 for unread"),
        "file": "candidates.json: one JSON object, key fact_id, value the list of the 4 candidates in that order; 320 keys",
        "reference_implementation": "metrix/e1-v1/reports/authoring/v1_data_check.py",
        "candidate_mapping_sha256": "79600769eef1876b54bc3d174874880e8e05bab11290f97360559f99324235c3",
        "candidate_mapping_sha256_note": "canonical sha256 of candidates.json built from the 320 facts of the E1-V1 DATA_SEED"}),
    "leakage_checks": dict(leak, **{
        "command": "python -m metrix.e1_v1.check_leakage --data <DATA_DIR> --split-manifest metrix/e1-v1/SPLIT_MANIFEST.json --damage-manifest metrix/e1-v1/DAMAGE_MANIFEST.json --out <DATA_DIR>/leakage_report.json (implementation belongs to the Implementation Task Order)",
        "exit_code": "0 only if every check is within its limit",
        "test_split": "L1, L2 use templates only; L3a-L5 run on TEST questions after test_qa.jsonl is generated; the TEST parts of L6 and L8 run after general_test.jsonl and d2_test.jsonl are generated (protocol section 10 step 10)",
        "test_part_over_limit": "any TEST part over its limit, or Executor and data-auditor results of L6 / L8 differ: stop, do not evaluate TEST, BLOCKED, report to the Owner (ST10)",
        "generation_rule": "names occurring in anchor_text or equal / close to a Pilot string are rejected at generation; D1 / D2 units triggering L8 or L6 are excluded at generation (DAMAGE_MANIFEST.json); the checks still run"}),
    "hashing": HASHING,
    "actual_hashes": "the manifests are not rewritten during execution; the actual hashes of generated files go into results/step1_record.json (non-TEST) and results/st10_record.json (TEST); protocol section 13 ST12",
})
split_manifest["template_freeze"]["note"] = "the 32 Pilot templates, unchanged (protocol 2.4)"
dump("SPLIT_MANIFEST.json", split_manifest)

# --------------------------------------------------------------------------------------------- DOSE_SPACE
dose_space = dict(HEAD)
dose_space.update({
    "methods": {
        "F": {"definition": "all parameters trainable, trained on train_F", "config": {"learning_rate": 3e-05, "weight_decay": 0.0},
              "source": "E1-PILOT selected configuration F3 (metrix/e1-pilot/results/selection_freeze_record.json: selected)"},
        "L": {"definition": "base frozen; LoRA on q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj of all 28 layers; alpha = 2 * rank; dropout 0; B initialised to 0; A per interpretation B5",
              "config": {"learning_rate": 0.001, "rank": 32, "alpha": 64, "weight_decay": 0.0},
              "source": "E1-PILOT selected configuration L6"},
        "A": {"definition": "F plus lambda * KL(p_base || p_theta) on anchor text, 4 anchor documents per step, token-weighted (Pilot section 4; interpretation B6)",
              "config": {"learning_rate": 0.0001, "anchor_lambda": 1.0, "weight_decay": 0.0},
              "source": "E1-PILOT selected configuration A5"}},
    "configs_per_method": 1,
    "tuning": "none in E1-V1: each method uses the configuration E1-PILOT selected with the same budget (6 configurations each) and the same DEV-accuracy rule; no damage-based selection (protocol 6.6)",
    "controls": {
        "S": {"corpus": "train_S", "config": "F", "passes": 11},
        "Y": {"corpus": "train_Y", "batch": 16, "config": "F", "passes": 11},
        "Z0": {"purpose": "negative control (Gate D, G-D1)", "code_path": "F", "corpus": "train_F", "learning_rate": 0.0, "weight_decay": 0.0, "passes": 2, "seeds": [101, 202, 303],
               "expectation": "every reloaded parameter tensor numerically equal to N's corresponding tensor (torch.equal; -0.0 and +0.0 count as equal); whether state_sha256(Z0) equals state_sha256(N) is reported only"},
        "P+": {"purpose": "positive control (Gate D, G-D3, G-D4)", "code_path": "F", "corpus": "train_F", "learning_rate": 0.0001, "weight_decay": 0.1, "passes": 11, "seeds": [101, 202, 303],
               "source": "E1-PILOT F6 (metrix/e1-pilot/results/training_runs/F-F6-seed101.json: config, dnll 5.55021)"}},
    "dose": {"dimension": "passes over the 240 TRAIN statements (batch 8, 30 optimizer steps per pass); one run per (method, seed) trained to the largest dose, evaluated in place at every dose point",
             "ladder_passes": [1, 2, 3, 4, 6, 8, 11, 16, 23, 32],
             "ladder_steps": [30, 60, 90, 120, 180, 240, 330, 480, 690, 960],
             "points": 10, "same_for": ["F", "L", "A"], "d0_passes": 11,
             "d0_use": "Gate 0 (G0.4, G0.5, G0.8, T1) on F; S and Y are trained to d0",
             "coverage_rationale": "protocol 6.3 (Pilot DEV accuracies of F1/F3, L4/L6, A2/A5 at 20 cosine passes, about 11 constant-rate passes)"},
    "seeds": {"training_seeds": [101, 202, 303], "use": "one curve per (method, seed); data order rng_rule(TRAIN_SEED, 'order:<k>'); LoRA A rng_rule(TRAIN_SEED, 'lora_A:<module path>'); iso points per seed; comparisons on the seed-average and per seed"},
    "iso": {"targets": [0.7, 0.8, 0.9], "acquisition": "Acc(model, DEV-QA, learned), fact-level mean (Pilot section 5)",
            "bracket": "j* = smallest j >= 2 with a_{j-1} < t <= a_j; none -> NOT_REACHED for that seed",
            "tau_dev": 0.1, "tau_dev_rule": "t - a_{j*-1} <= 0.10 and a_{j*} - t <= 0.10, otherwise NOT_REACHED for that seed",
            "interpolation": "w = (t - a_{j*-1}) / (a_{j*} - a_{j*-1}); per-unit value v_t = (1 - w) * v(lo) + w * v(hi); the same w on TEST",
            "method_rule": "a method is comparable at t only if all 3 seeds are bracketed; otherwise NOT_REACHED; no extrapolation",
            "dev_only": True,
            "tau_test": 0.05, "tau_test_rule": "|Acq_TEST(X, t) - Acq_TEST(F, t)| > 0.05 (seed-average of interpolated TEST accuracies) -> MATCH_FAILED"},
    "checkpoint_retention": {
        "rule": "after the DEV evaluation of dose point j: save (with state_sha256) if some target t not yet crossed before j has |a_j - t| <= 0.10; never delete",
        "always_saved": ["F at d0 (3 seeds)", "S and Y final (3 seeds each)", "P+ final (3 seeds)", "Z0 final (3 seeds)"],
        "format": "full float32 state_dict for F, A, S, Y, P+, Z0; adapter parameters plus the base state_sha256 for L",
        "disk": "about 310 GB expected, 516 GB worst case; rent >= 600 GB (protocol section 12); ST18"},
    "training_contract": {
        "optimizer": "AdamW, betas (0.9, 0.999), eps 1e-8",
        "batch_size_statements": 8, "batch_size_Y": 16, "steps_per_pass": 30,
        "passes": {"F": 32, "L": 32, "A": 32, "S": 11, "Y": 11, "P+": 11, "Z0": 2},
        "example_order": "one permutation of the corpus per pass from rng_rule(TRAIN_SEED, 'order:<k>'), k = 1..; batches are consecutive slices (interpretation B3)",
        "sequence": "one statement per sequence followed by <|endoftext|>; pad on the right to the longest sequence in the batch; padding excluded from the loss",
        "loss": "token-weighted CE over all non-padding target positions (interpretation B4); A adds the anchor KL term of Pilot section 4",
        "gradient_accumulation": 1,
        "warmup": "linear from 0 over the first 30 steps (pass 1)",
        "scheduler": "constant after warmup (no decay)",
        "weight_decay": "per method / control config; applied to 2-D weight matrices only, tied embedding included (interpretation B7)",
        "gradient_clipping": "global norm 1.0",
        "precision": "bfloat16 autocast with float32 master weights and optimizer state; evaluation float32 without autocast",
        "evaluation": "DEV evaluation in place after step 30 * k of every dose point, under model.eval() and torch.no_grad(); it changes no parameter, gradient, optimizer state or random stream",
        "early_stopping": "not allowed",
        "hardware": {"gpu": "NVIDIA A100 80GB", "count": 1, "device_name_rule": "Pilot section 7 (ST9)"},
        "gpu_hours_limit": 9,
        "gpu_hours_limit_source": OWNER_APPROVAL + ", C1; ST7 = 9 hours (protocol sections 12, 13, 15 item 1)",
        "st11_bound": "0.875 * gpu_hours_limit = 7.875 hours; estimate E by the formula of protocol section 12 (replaces interpretation B17)"},
    "compute_matching": {"same": ["1 configuration per method", "the same 10 dose points", "the same fact tokens at every dose point (k passes over train_F; 3,802 tokens per pass with <|endoftext|>)"],
                         "different": ["L trains adapters only (about 34.86M parameters at rank 32); forward parameters base plus adapters",
                                       "A adds per step the forward of 4 anchor documents through the frozen base and the trained model and the backward of the latter"],
                         "rationale": "acquisition is driven by the fact text read, identical token by token across methods; the extra compute of A and L is part of the method and is reported separately (Pilot section 10, interpretation B18), not converted into fact passes"},
    "counts": {"curve_runs": 9, "S_runs": 3, "Y_runs": 3, "Z0_runs": 3, "P_plus_runs": 3, "total_training_runs": 21,
               "dev_evaluations": 107, "test_evaluations": "N, F@d0 x3, S x3, Y x3 and the bracket checkpoints of the selection freeze record"},
    "owner_decisions": {"dose_points_and_configs": "main plan: 1 configuration per method, 10 dose points, 3 seeds (" + OWNER_APPROVAL + ", C3; protocol section 15 item 3); the reduction plans R1-R4 of protocol section 12 are for reference only, not part of the frozen protocol; adopting one requires a new protocol version"},
})
dump("DOSE_SPACE.json", dose_space)

# --------------------------------------------------------------------------------------------- DAMAGE_MANIFEST
gt = pdm["general_text"]
d2_prompt = ("I + '\\n\\n' + question.strip() + '\\n' + 'A. ' + c0 + '\\n' + 'B. ' + c1 + '\\n' + 'C. ' + c2 + '\\n' + 'D. ' + c3; "
             "I = 'Answer the following multiple choice question with the letter of the correct option.'; ci = str(option i).strip(), dataset order")
excl_dev = ["not exactly 4 options or answer outside A-D", "L8 hit (a V1 string as a whole word)", "L6 hit (shares a word 13-gram with anchor_text)"]
damage = dict(HEAD)
damage.update({
    "d1": {"metric": "per-window d(w) = NLL_theta(w) - NLL_N(w) (Pilot section 5 general damage); D1-all = mean over 4 domains of the domain means; D1-diff = over books, c4, wikitext; D1-same = fineweb",
           "source_file": gt["source_file"], "source_file_sha256": gt["source_file_sha256"],
           "decode_with": gt["decode_with"], "decode_tokenizer_json_sha256": gt["decode_tokenizer_json_sha256"],
           "domains": ["books", "c4", "fineweb", "wikitext"],
           "anchor_source_groups": {"same": ["fineweb"], "different": ["books", "c4", "wikitext"],
                                    "basis": "the Stage 1 fineweb windows come from the held-out FineWeb-Edu validation shard of SandyResearch/fineweb-edu-shuffled, the anchor source (research/mini_mythos/stage1/README.md evaluation-set table)"},
           "window_rule": gt["window_rule"],
           "dev": {"file": "general_dev.jsonl", "rule": "per domain all 100 rows with split == 'dev', file order; exclude units triggering L8, then L6",
                   "per_domain": 100, "authoring": {"kept": 400, "excluded": 0, "canonical_sha256": "e8350160464963e684e0c58826d53250dec4de366a716d3111aa8ec5089ce281", "ids_per_window_mean": 248.893}},
           "test": {"file": "general_test.jsonl", "rule": "per domain the rows with split == 'test' in file order, skipping the first 25 test rows of the domain (the E1-PILOT TEST windows); exclude units triggering L8, then L6, then windows whose ids equal those of a DEV window; take the first 100 per domain; fewer than 100 -> ST10",
                    "per_domain": 100, "available_per_domain_after_skip": 175},
           "reading_rule": "before section 10 step 10: whole-file sha256 allowed; test rows are only matched on the row-prefix bytes (the regex of protocol section 0) and counted, never decoded or JSON-parsed"},
    "d2": {
        "status": "FROZEN: mmlu (" + OWNER_APPROVAL + ", C2; protocol section 15 item 2)", "selected": "mmlu", "alternative_not_adopted": "arc",
        "metric": "c_theta(i) = 1[s(i, correct letter) > max over other letters] (ties wrong); Acc_D2 = mean; damage e_theta(i) = c_N(i) - c_theta(i), D2 = mean e = -dAcc",
        "prompt": d2_prompt, "scoring": model["input_convention"]["d2_scoring"], "letter_token_ids": {"A": 362, "B": 425, "C": 356, "D": 422},
        "unrelated_to_facts": "the V1 entities and answers are randomly generated fictional strings; D2 items are existing real-world questions; L8 excludes any item containing a V1 string",
        "datasets": {
            "mmlu": {"adoption": "selected (C2)", "repo": "cais/mmlu", "revision": "c30699e8356da336a370243923dbaf21066bb9fe", "license": "mit", "research_use": "allowed (MIT)",
                     "dev_source": {"file": "all/validation-00000-of-00001.parquet", "sha256": "66cdf0b090ccb657d18d13cd81e31fdc55c3467da9642ffb178653268a97c8ef", "rows": 1531},
                     "test_source": {"file": "all/test-00000-of-00001.parquet", "sha256": "74a41822ce7d3def56e1682f958469c04642a5336a5ce912fa375fdb90fb25d7", "rows": 14042},
                     "fields": "question, subject, choices (list of 4), answer (0-3)",
                     "dev_order": "rng_rule(DATA_SEED, 'd2:mmlu:validation:order').shuffle(list(range(1531)))",
                     "test_order": "rng_rule(DATA_SEED, 'd2:mmlu:test:order').shuffle(list(range(14042)))",
                     "authoring_dev": {"items": 800, "excluded": 0, "rows_visited": 800, "canonical_sha256": "f40c146a3da500f13797dcfedfb2932e8a5dc88a6b43cbd423bf8fb549a688be", "context_ids_mean": 134.221, "subjects": 57}},
            "arc": {"adoption": "not adopted alternative (C2): verification record kept, not used in E1-V1", "repo": "allenai/ai2_arc", "revision": "210d026faf9955653af8916fad021475a3f00453", "license": "cc-by-sa-4.0", "research_use": "allowed (CC-BY-SA-4.0: attribution, share-alike)",
                    "dev_source": [{"file": "ARC-Challenge/validation-00000-of-00001.parquet", "sha256": "395a5c88d1580d69855fbaee9450270578df1ad5af6259771cd0a42c20e99f05", "rows": 299},
                                   {"file": "ARC-Easy/validation-00000-of-00001.parquet", "sha256": "ed890ff1e4cef7a7140d3a30dcea3ed2c9d467c6458f447ad9ef0176d8dcbb74", "rows": 570}],
                    "test_source": [{"file": "ARC-Challenge/test-00000-of-00001.parquet", "sha256": "62f03257e737aed263f55c6abf87c7bb0028a44a6bdd2a26eb1279eb42c1d1e9", "rows": 1172},
                                    {"file": "ARC-Easy/test-00000-of-00001.parquet", "sha256": "4160597d618ae851c7eb04e281574f3f654776216ac6b6641588d64527b47177", "rows": 2376}],
                    "fields": "id, question, choices {text, label}, answerKey; only items with exactly 4 labels; labels in the given order map to A-D; subject field holds the item id",
                    "dev_order": "rows of Challenge validation then Easy validation (indices 0..868), rng_rule(DATA_SEED, 'd2:arc:validation:order').shuffle",
                    "test_order": "rows of Challenge test then Easy test (indices 0..3547), rng_rule(DATA_SEED, 'd2:arc:test:order').shuffle",
                    "authoring_dev": {"items": 800, "excluded": {"not_4_choices": 6}, "canonical_sha256": "1ea77c8adeb84b6d5f7a3aa699ab02951e4f43bd27ba14f36c3a32287e04ac32", "context_ids_mean": 82.989}}},
        "verification": "reports/authoring/d2_dataset_metadata.txt (Hub API revision, license, LFS oids; sha256 of the downloaded files equal the oids)",
        "dev": {"file": "d2_dev.jsonl", "rule": "in dev_order, exclude: " + "; ".join(excl_dev) + "; take the first 800", "items": 800},
        "test": {"file": "d2_test.jsonl", "rule": "in test_order, exclude the same and items whose prompt equals a DEV prompt; take the first 800; fewer -> ST10", "items": 800},
        "reading_rule": "before section 10 step 10: whole-file sha256 of a TEST source allowed; only the parquet footer (row count) is read; no row is read or decoded (protocol section 0)"},
    "leakage": {"L6": "SPLIT_MANIFEST.json: leakage_checks.L6_anchor_ngram", "L8": "SPLIT_MANIFEST.json: leakage_checks.L8_fictional_strings_in_damage_sets"},
    "statistics": {
        "unit": {"D1": "window", "D2": "item"}, "replicates": 10000, "seed": "BOOTSTRAP_SEED = 20261130",
        "d1_resampling": "within domains, in the order books, c4, fineweb, wikitext (only the domains of the metric); r.choices(windows, k=n_domain); statistic = mean of the domain means; both models use the same drawn windows",
        "d2_resampling": "unstratified, r.choices(items, k=800)",
        "percentile": "interpretation B11 (linear interpolation at (B - 1) * p / 100)",
        "seed_average": "average the 3 seeds' values per unit, then bootstrap; per-seed bootstraps reported; seed min, max and sample SD of the point estimates reported",
        "sigma_N": "sample SD (denominator B - 1) of the 10,000 bootstrap values of N's level statistic on the DEV set: D1 metrics: mean of domain means of NLL_N(w); D2: Acc_D2(N)"},
    "gate_d": {
        "G-D1": {"control": "Z0", "rule": "per seed: every reloaded parameter tensor numerically equal to N's corresponding tensor (torch.equal; -0.0 and +0.0 count as equal); whether state_sha256 equals N's is reported only; per-unit differences to N: candidate scores <= 1e-4, D1 window NLL <= 1e-5, D2 letter scores <= 1e-4; predictions identical except near-ties (top-2 gap <= 1e-4 in either evaluation, Pilot G0.8)"},
        "G-D2": {"rule": "sigma_N(D1-all), sigma_N(D1-diff), sigma_N(D1-same), sigma_N(D2) finite and > 0; m(D1-all) <= 0.10, m(D1-diff) <= 0.10, m(D1-same) <= 0.20 (m(D2) <= 2 * sqrt(0.25 / 800) by construction, no bound); P+ seed SD of D1-diff and D2 reported",
                 "planning": "reports/authoring/sigma_planning.txt (expected m: D1-all 0.045, D1-diff 0.052, D1-same 0.090)"},
        "G-D3": {"control": "P+", "D1-diff": {"seed_average_min": 1.0, "ci95_lower_gt": 0.0, "per_seed_min": 0.5},
                 "D2": {"seed_average_min": 0.05, "ci95_lower_gt": 0.0, "per_seed_gt": 0.0}},
        "G-D4": {"rule": "P+ seed 101: evaluation at the end of training and after save / reload (state_sha256 equal); tolerances as G-D1"},
        "G-D5": {"rule": "report only: P+ (D1-diff, D2) per seed; after the DEV curves, Spearman correlation of D1-diff and D2 over all trained-model DEV evaluations"},
        "pass": "G-D1 and G-D4 hold, and the D1 conditions of G-D2 and G-D3 hold (sigma_N of D1-all, D1-diff, D1-same finite and > 0; the three margin upper bounds; the P+ D1-diff condition); otherwise ST14. If a D2 condition of G-D2 or G-D3 fails (sigma_N(D2) finite and > 0; the P+ D2 condition), Gate D can still pass and D2 is D2_NOT_QUALIFIED (protocol 7.5)",
        "D2_NOT_QUALIFIED": "Gate D passed but a D2 condition of G-D2 or G-D3 failed: all D2 values are computed, committed and reported as usual; D2 comparisons in Gate M get no conclusion word and no interpretation; not a final status (protocol 7.5, 9.6)"},
    "margin": {"formula": "m(M) = 2 * sigma_N(M), M in D1-all, D1-diff, D1-same, D2", "multiplier": 2,
               "input_record": "metrix/e1-v1/results/gate_d_record.json (noise)", "output_record": "metrix/e1-v1/results/margin_record.json (MARGIN_RECORD)",
               "timing": "after Gate D passes; committed and pushed before any training of section 10 step 6 (ST15)"},
    "comparison": {"primary": "TEST, t = 0.80, D1-diff, Delta(L-F) and Delta(A-F); Bonferroni over the 2: 97.5% CI",
                   "secondary": "all other points, metrics, DEV comparisons, per-domain metrics D1-books, D1-c4, D1-wikitext and per-method damages: 95% CI; words only for method comparisons on D1-all, D1-diff, D1-same, D2, marked secondary",
                   "words": "for a comparison on metric M with m = m(M): superior: hi < 0 and all 3 seed estimates < 0; non-inferior: not superior, hi < m and all 3 seed estimates < m; inferior: lo > m and all 3 seed estimates > m; inconclusive otherwise; per-method damages (X vs N) and per-domain metrics get no word; when D2 is D2_NOT_QUALIFIED, D2 method comparisons get no word (protocol 7.5, 9.4)"},
})
dump("DAMAGE_MANIFEST.json", damage)
