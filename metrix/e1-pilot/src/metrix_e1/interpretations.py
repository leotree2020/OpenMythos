"""Points where protocol v1.1 leaves a choice that the code has to make (Implementation stage B).

Each entry names the protocol text it reads, the choice the code makes and where. None of them changes a threshold,
an arm, a metric or a step; each is a reading of a sentence that admits more than one implementation. They were
listed for Review Gate in reports/IMPL_B_REPORT.md (B1-B24) and reports/IMPL_C_REPORT.md (B25) ("待 Review Gate
决定") and are written into every experiment record (record.py), so that a ruling can be checked against the code
that ran.

Review Gate accepted all of B1-B24 on 2026-11-24 (scope: this stage). The ruling is recorded in RULING_REF (no
separate decision file: Owner's stage-C message, tasks/IMPL_C_OWNER_MESSAGE.md); those entries carry the status
ACCEPTED and that reference. B3 and B14 carry the ruling's notes. Review Gate accepted B25 on 2026-11-25 (ruling on
C1, item 3, tasks/IMPL_C1_RULING.md): status ACCEPTED_C1, reference RULING_REF_C1. Review Gate revised B17 on
2026-11-27 (tasks/IMPL_C4_RULING.md item 1: ST11 reads B17's estimate plus the checkpoint overhead): status
ACCEPTED_C4, reference RULING_REF_C4. pending() returns the entries not yet ruled (the TEST generator and every TEST
path refuse while it is not empty: pending_problem()); it is empty.
"""
PENDING = "PENDING_REVIEW_GATE"
ACCEPTED = "ACCEPTED（Review Gate 2026-11-24）"
RULING_REF = "reports/IMPL_C_REPORT.md「Review Gate 对阶段 B 的裁决」第 1 项"
ACCEPTED_C1 = "ACCEPTED（Review Gate 2026-11-25）"
RULING_REF_C1 = "tasks/IMPL_C1_RULING.md 第 3 项(reports/IMPL_C_REPORT.md「Review Gate 对 C1 的裁决」)"
ACCEPTED_C4 = "ACCEPTED（Review Gate 2026-11-27 修订）"
RULING_REF_C4 = "tasks/IMPL_C4_RULING.md 第 1 项"

ENTRIES = (
    {"id": "B1", "status": ACCEPTED, "where": "train.step_numbers (used by train.batch_schedule), train.anchor_docs", "protocol": "2.7, 4, 7",
     "text": "Optimizer steps are numbered s = 1..300 (the protocol's '第 300 步' is the last step). Step s of arm A uses "
             "anchor documents (4s + i) mod 512, i = 0..3, documents numbered 0..511 in anchor_text.jsonl order (step "
             "1: documents 4-7; with s = 0..299 the first step would use 0-3 and every step's documents would differ)."},
    {"id": "B2", "status": ACCEPTED, "where": "train.lr_at", "protocol": "7 (warmup, scheduler)",
     "text": "lr(s) = peak * s / 15 for s <= 15 (rises linearly from 0; step 1 already has peak/15); for s >= 15, "
             "lr(s) = peak * (0.1 + 0.9 * 0.5 * (1 + cos(pi * (s - 15) / (300 - 15)))), so lr(15) = peak and "
             "lr(300) = 0.1 * peak. Set on every parameter group before optimizer step s."},
    {"id": "B3", "status": ACCEPTED, "where": "train.epoch_batches, train.batch_schedule", "protocol": "7 (order)",
     "text": "Epochs are numbered e = 1..20 and the purpose is 'order:<e>' with TRAIN_SEED = the run's seed; "
             "permutation p = list(range(N)); r.shuffle(p) (the same call as protocol 2.6 detail 4); the batches of "
             "epoch e are p[0:B], p[B:2B], ... (B = 8 for F, L, A, S; B = 16 for Y), rows indexed in the file order of "
             "the corpus. The row order of train_Y.jsonl (fact order, the Y_ENTITY sentence before the Y_ANSWER one) is "
             "a stage A choice without a frozen hash (DEFERRED_MINORS AA11), so Y's batches depend on it.",
     "ruling_note": "Review Gate 2026-11-24: in the formal run, section 8 step 1 writes the canonical hash of "
                    "train_Y.jsonl into the manifest (DATA_MANIFEST.json files, the field written by step 1)."},
    {"id": "B4", "status": ACCEPTED, "where": "train.token_ce", "protocol": "4 (CE), 7 (sequence)",
     "text": "CE(batch) = sum of -log p(x_t | x_<t) over every non-padding target position (t = 2..n of each "
             "sequence, the final <|endoftext|> included) divided by the number of those positions (token-weighted "
             "over the batch, like the anchor KL); sequences are not averaged first."},
    {"id": "B5", "status": ACCEPTED, "where": "train.lora_a_init, train.apply_lora", "protocol": "4 (arm L), 0 (rng_rule)",
     "text": "LoRA A is initialised uniformly in [-1/sqrt(in_features), 1/sqrt(in_features)] (the Kaiming-uniform "
             "default of torch.nn.Linear and peft): every value is r.uniform(-b, b) of r = rng_rule(TRAIN_SEED, "
             "'lora_A:<module path>'), row by row, stored as float32; B = 0; scaling alpha / rank = 2; the adapter "
             "output B(A x) * scaling is added to the frozen base output; LoRA parameters are float32. The distribution "
             "and the purpose string are not in the protocol."},
    {"id": "B6", "status": ACCEPTED, "where": "train.anchor_kl, train.train_run", "protocol": "4 (arm A), 7 (precision)",
     "text": "The base copy's forward and the trained model's forward on the anchor documents both run under the "
             "same bf16 autocast as the rest of training; their logits are cast to float32 before log_softmax and the "
             "KL is computed in float32."},
    {"id": "B7", "status": ACCEPTED, "where": "train.make_optimizer", "protocol": "7 (weight decay)",
     "text": "'2-D weight matrices' = every trainable parameter with ndim == 2, including the tied embedding / "
             "lm_head matrix for F, S, Y; 1-D parameters (RMSNorm weights) get no weight decay."},
    {"id": "B8", "status": ACCEPTED, "where": "evaluate.em_normalize", "protocol": "5 (EM)",
     "text": "'去结尾的 . , ; : ! ?' removes every trailing character of that set (str.rstrip('.,;:!?'), as in the "
             "data-auditor's audit/r4_scoring_em.py and r5_em_stop.py); a leading 'the ' is removed once; a <think> "
             "without a later </think> is left as it is."},
    {"id": "B9", "status": ACCEPTED, "where": "evaluate.score_cb", "protocol": "5 (TRAIN closed book)",
     "text": "The candidates c of CB(f) are the 4 candidates C_f of candidates.json (protocol 2.5: one candidate list "
             "for all templates, splits and arms)."},
    {"id": "B10", "status": ACCEPTED, "where": "stats.stratified_draws, stats.paired_bootstrap", "protocol": "6",
     "text": "One generator r = rng_rule(BOOTSTRAP_SEED, purpose) per comparison; for each of the 10,000 replicates, "
             "for each stratum in the order natural, random: r.choices(d_stratum, k=len(d_stratum)) with the facts "
             "of the stratum in facts.jsonl order; Delta* = mean of the 120 drawn values."},
    {"id": "B11", "status": ACCEPTED, "where": "stats.percentile", "protocol": "6",
     "text": "Percentile = linear interpolation between order statistics at position (B - 1) * p / 100 of the sorted "
             "replicates (numpy's default 'linear' method)."},
    {"id": "B12", "status": ACCEPTED, "where": "stats.purpose", "protocol": "6",
     "text": "Purpose '<比较>:<split>:<seed 或 avg>' is written '<X>-<Y>:<split>:<seed>' with ASCII '-', split 'DEV' "
             "or 'TEST', seed the integer or 'avg' (e.g. 'F-N:DEV:101', 'F-N:DEV:avg'); the Spill of an arm, compared "
             "with N on the unread facts, is written 'Spill-<arm>:<split>:<seed>'."},
    {"id": "B13", "status": ACCEPTED, "where": "stats.size_estimate, stats.halfwidth_check, gate.judge (G0.10)", "protocol": "8 (G0.10)",
     "text": "sigma_d = sample standard deviation (ddof 1) of the 120 seed-average d_f; its bootstrap 2.5 / 97.5 "
             "percentiles from the stratified resampling of B10 with purpose 'sigma:<X>-<Y>:DEV:avg'; n = ceil(((1.96 + "
             "0.84) * sigma / delta)^2); planning n = the largest n over the three sigma values, the three deltas and "
             "both comparisons; the CI half-width check resamples n facts (stratified, n/2 per stratum rounded up) with "
             "purpose 'halfwidth:<X>-<Y>:DEV:avg:<n>' and reports the half-width of the 95% CI of the mean (report "
             "only; skipped and noted when n = 0, i.e. sigma_d = 0). G0.10 holds iff sigma_d, both percentiles and "
             "every n are finite."},
    {"id": "B14", "status": ACCEPTED, "where": "gate.judge", "protocol": "8, 9",
     "text": "Gate 0 status words: all G0 satisfied -> gate0 'PASS' (the pilot's final status still needs T1-T3); any "
             "G0 not satisfied -> 'PIPELINE_NOT_QUALIFIED' with the reasons of section 9 (G0.1, G0.2, G0.6, G0.7, G0.8 "
             "-> IMPLEMENTATION_FAIL; G0.4 -> OPTIMIZATION_FAIL; G0.5 with G0.4 satisfied -> "
             "OPTIMIZATION_OR_CAPACITY_UNRESOLVED for any of its three parts, not only the accuracy; G0.5 with G0.4 not "
             "satisfied -> OPTIMIZATION_FAIL, although section 8 calls [0.40, 0.70) UNRESOLVED without naming G0.4; "
             "seed-average Acc(F) < 0.40 adds the section 8 note '对该模型与该训练量过难'). Section 9 lists no reason for G0.3, "
             "G0.9 (section 8: benchmark recalibration, noted) and G0.10: their reason is null, although section 9 says "
             "one reason is given. Several unsatisfied conditions give several reasons (section 9 says 'a reason').",
     "ruling_note": "Review Gate 2026-11-24: G0.3 and G0.9 have reason null with the note '需重新校准' "
                    "(gate.RECALIBRATION_NOTE), consistent with Task Order V1.2 section 15.8."},
    {"id": "B15", "status": ACCEPTED, "where": "gate.repro_compare", "protocol": "8 (G0.8)",
     "text": "'候选分数' = every candidate score of the evaluation (s_QA on DEV-QA and s_ST of the TRAIN closed book); "
             "'预测' = the index of the highest candidate, or 'tie' when the top score is shared (tie = wrong)."},
    {"id": "B16", "status": ACCEPTED, "where": "stops", "protocol": "11",
     "text": "Statuses section 11 does not state: ST3 -> PIPELINE_NOT_QUALIFIED with reason OPTIMIZATION_FAIL "
             "(Acc_CB < 0.90) or OPTIMIZATION_OR_CAPACITY_UNRESOLVED (otherwise); ST4, ST5 -> PIPELINE_NOT_QUALIFIED "
             "with reason IMPLEMENTATION_FAIL (section 9 for G0.6, G0.7); ST6 outside the selected configurations and "
             "the controls -> that configuration is excluded from selection (section 7), no pilot status; ST7, ST11 "
             "-> BLOCKED (resources)."},
    {"id": "B17", "status": ACCEPTED_C4, "ruling": RULING_REF_C4,
     "where": "compute.estimate_total_hours, compute.evaluation_units, pilot.evaluation_plan, "
              "pilot.checkpoint_overhead_seconds, pilot.st11_estimate_hours, pilot.preflight, pilot.step2",
     "protocol": "8 step 2 (preflight), 11 ST11",
     "text": "Preflight estimate (the value ST11 compares with 3.5 hours; Review Gate 2026-11-27 revision) = B17's "
             "estimate + the checkpoint overhead. B17's estimate = (measured mean seconds per step of the first "
             "configuration's first 20 steps, the first step excluded as warm-up, CUDA synchronised before each "
             "timestamp) x sum over the 30 runs of 300 steps x the run's FLOP factor (F, S, Y, L: 1; A: 1 + (2 + 6) * "
             "anchor tokens / (6 * fact tokens) per step, section 10 coefficients) + (measured seconds of one float32 "
             "DEV evaluation, timed in the preflight) x evaluation units (N, 30 runs and the 3 G0.8 re-evaluations on "
             "DEV; N and the 15 final checkpoints of the 5 arms x 3 seeds on TEST, at test / dev questions per fact = "
             "1.5) + the GPU time already used. Checkpoint overhead = load x 32 base-model loads (N, the 30 runs, N at "
             "TEST) + 30 checkpoints x (2 x hash + save + reload + file hash) + reload x 18 further checkpoint reloads "
             "(the 3 G0.8 re-evaluations, the 15 TEST checkpoints) + hash x 17 TEST state hashes (the 16 TEST models "
             "and N once more at the TEST begin) + file hash x 15 TEST checkpoint files, with load, hash (state_sha256, "
             "B25), save (torch.save), reload (torch.load into a fresh model) and file hash (SHA-256 of the checkpoint "
             "file) each measured once in the preflight on the first configuration's model. Both parts and their sum "
             "are written into the step 2 record. The ST7 look-ahead is not changed by this revision; the look-ahead "
             "before the TEST evaluation adds no margin."},
    {"id": "B18", "status": ACCEPTED, "where": "compute.flops", "protocol": "10 (compute accounting)",
     "text": "P = parameters taking part in the forward pass (for L: base plus adapters); T = non-padding tokens fed "
             "(training: fact tokens of the batch; anchor: anchor tokens). Arm A's anchor compute is listed "
             "separately: base forward 2 * P * T_anchor + trained-model forward and backward 6 * P * T_anchor."},
    {"id": "B19", "status": ACCEPTED, "where": "leakage.run_test_part", "protocol": "8 step 8 ('对 TEST 运行 L3–L5'), 3",
     "text": "Announced in reports/IMPL_A_REPORT.md for this stage: the protocol does not say what L3 and L5 count "
             "on TEST. Implemented: L4 on every instantiated TEST question (verbatim in train_F, train_S, train_Y, "
             "anchor_text); L3a, L3b and L5 re-run as at Gate 0 (they read no TEST content, so the TEST part cannot "
             "change them); L6 TEST part as protocol section 3."},
    {"id": "B20", "status": ACCEPTED, "where": "evaluate.score_s_mapping", "protocol": "8 (report only: S on its own permuted mapping)",
     "text": "S's accuracy on its own mapping: for each learned fact f with S answer a' = answer of answer_fact_id, the "
             "DEV-QA questions of f and the TRAIN-statement prefix of f are scored with the candidate list of the "
             "fact a' belongs to (it contains a' and has 4 equal-length candidates); correct iff a' scores strictly "
             "highest. Report only."},
    {"id": "B21", "status": ACCEPTED, "where": "train.load_model", "protocol": "0 (determinism), 8 (G0.8)",
     "text": "The model is loaded with attn_implementation='eager' (not the default 'sdpa') so that attention uses "
             "plain matmul and softmax under torch.use_deterministic_algorithms(True); this changes numbers at the 1e-6 "
             "level, not the definitions."},
    {"id": "B22", "status": ACCEPTED, "where": "gate._g3_ranges", "protocol": "8 (G0.3, T3)",
     "text": "'每个 stratum ∈ [0.10, 0.40]' is read as Acc(N, DEV-QA, learned) of each stratum (the clause follows the "
             "learned accuracy); the unread accuracy is checked overall only."},
    {"id": "B23", "status": ACCEPTED, "where": "evaluate.em_normalize", "protocol": "5 (EM)",
     "text": "'取第一行' splits at the first '\\n' only ('\\r' is not a line break here)."},
    {"id": "B24", "status": ACCEPTED, "where": "gate.judge_test", "protocol": "8 (T1-T3), 9",
     "text": "Final status: PASS iff Gate 0 is PASS and T1-T3 hold; otherwise PIPELINE_NOT_QUALIFIED with reasons T1 -> "
             "OPTIMIZATION_OR_CAPACITY_UNRESOLVED (section 9 names T1's accuracy; the CI part is given the same "
             "reason), T2 -> IMPLEMENTATION_FAIL (the G0.6 / G0.7 numbers), T3 -> null with the recalibration note (as "
             "G0.3). T3's 'G0.3 的同样范围' is read as all four G0.3 ranges, Acc_CB(N) included (a TRAIN closed-book "
             "value that does not depend on TEST). TEST comparisons use the purpose split 'TEST'."},
    {"id": "B25", "status": ACCEPTED_C1, "ruling": RULING_REF_C1,
     "where": "record.selection_freeze_record, testgate.require_test_session, train.state_sha256",
     "protocol": "8 step 8 ('提交冻结记录(选定配置、数据哈希、checkpoint 哈希)')",
     "text": "A run's checkpoint hash is train.state_sha256 of the trained model (for arm L the LoRA-wrapped model, "
             "base weights and adapters; N's is the loaded base model's). It is not a file-byte hash. Computation: "
             "h = SHA-256(); for each key k of module.state_dict() in sorted order (Python string order), with t = "
             "the tensor detached, moved to the CPU and made contiguous: h.update(UTF-8 bytes of k + b'\\0' + "
             "str(t.dtype) + b'\\0' + str(tuple(t.shape)) + b'\\0'), then h.update(the raw bytes of t, flattened "
             "and viewed as uint8, in the host's byte order); the hash is h.hexdigest() (64 lowercase hex). TEST "
             "evaluation recomputes it on the model loaded from the saved checkpoint and requires equality with the "
             "freeze record (through the TEST marker) before the model is evaluated."},
)


def pending():
    return [e["id"] for e in ENTRIES if e.get("status", PENDING) == PENDING]


def pending_problem():
    """None when every entry is ruled, else the reason naming the open ids. The one check used by the TEST generator
    (test_data.check_interpretations_ruled) and by every TEST path (leakage.verify_authorization)."""
    open_ids = pending()
    if open_ids:
        return "interpretations not yet ruled by Review Gate: %s" % ", ".join(open_ids)
    return None


def as_records():
    """The entries as written into every experiment record: status (PENDING_REVIEW_GATE when absent) and, for a
    ruled entry, the reference of the ruling (the entry's own, else RULING_REF)."""
    out = []
    for e in ENTRIES:
        r = dict(e, status=e.get("status", PENDING))
        if r["status"] != PENDING:
            r["ruling"] = e.get("ruling", RULING_REF)
        out.append(r)
    return out
