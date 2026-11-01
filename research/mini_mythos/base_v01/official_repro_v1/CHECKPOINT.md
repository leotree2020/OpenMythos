# MYTHOS-PARCAE-OFFICIAL-CORE-CPU-V1 — final checkpoint

Updated 2026-11-01 UTC. **STOPPED / BLOCKED / PARTIAL. No evaluation is running.**

## Outcome

The unchanged official Parcae CORE evaluation was actually executed on the designated Codespace using the original released140M weights, depth8 and the official CPU path. The limited calibration completed784/792 planned example instances and65/66 task returns, then the frozen6000-second launcher budget expired at2026-11-01T11:18:01.893325Z. Parent statusBLOCKED; child received the launcher's SIGTERM, exited-15, and its process group was gone. No numerical retry or continuation occurred.

This is a budget/coverage blocker, not evidence of a model failure. The missing examples are exactly seed3456, `bigbench_language_identification`, indices4–11. No child completion record or original `eval/core.json` was produced. Do not fill either in retrospectively.

| Purpose / acceptance | Expected | Actual | Status |
|---|---|---|---|
| Official limited coverage |22 tasks×12 examples×3 seeds=792;66 task returns |784 and65;264/264/256 examples by seed |BLOCKED|
| Recorded decisions and summaries |Original item identities and scoring decisions agree |784/784 item identities/decisions and65/65 task means independently checked without model execution |PASS for saved evidence|
| Source/input preservation |Original bytes and frozen environment unchanged |183 source/data inputs,3 original weight/config/tokenizer files and4 tools matched; upstream/B1 checkouts at original clean HEADs; original26-package inventory unchanged |PASS|
| Evidence custody |Raw evidence unchanged by review and exact copies |79/79 raw files and20/20 compact copies match;67 RNG files retained externally and in a verified local backup |PASS|
| Full official CORE / paper-score reproduction |273111 task-example instances and comparable settings |Not started |NOT TESTED|
| New free text generation / training |Separate authorized protocol |None performed |NOT TESTED here|

The frozen main audit has10 PASS checks,4 BLOCKED checks,0 FAIL checks, plus6 blocker entries covering missing coverage/terminal outputs/aggregate. Independent review APPROVE means evidence and classification are valid; it does not mean the planned full calibration passed.

## Actual limited-mode scores

| Seed | Coverage | Descriptive CORE percentage points |
|---|---|---:|
|1234|264 examples /22 tasks|10.590110546142334|
|2345|264 examples /22 tasks|11.46202887832643|
|3456|256 examples /21 complete tasks|Not reported; incomplete|

These are chance-centered,22-task macro scores, not raw accuracy percentages. The first two match official stdout's rounded scores. No two-seed mean replaces the planned three-seed result. `max_per_task=12` also restricts the few-shot pool; these figures cannot establish agreement or disagreement with the paper's14.04±0.20. Questions repeat across seed settings;792 is a count of evaluation instances, not independent held-out questions.

The official exam scores candidate answers and teacher-forced answer tokens. Our old12-prompt exam scores64-token free continuations for repetition and coherence. Old joint quality passes0/12 do not mean every factual opening was wrong. See `EXAM_COMPARISON.md` and `TASK_RESULTS.md`.

## Git / frozen versions

- Repository `leotree2020/OpenMythos`; branch `mythos-parcae-official-repro-cpu-v1`.
- Isolated checkout `/workspaces/mythos-base-v01-rope-diag-v11`.
- Base recovery result `6b52321746f393fa36711ff3896a5a9c5484c7c0`.
- Numerical observer/protocol freeze `22b415118a6482d8957bff29126ef56e3e9a71b4`; execution reservation `57f5c891de83ef06ccce46b64509cf2121fcdb0b`.
- Read-only main audit `920d615276f434512cdae6fd877a1e53f8cfc9a1`; descriptive reporter `1ae9b58ebbbb07157cd4d18703ed16b815f9194d`; custody helper `6cb22fb63d370dd75efe665cca9758d2b220f5a3`.
- Final results/evidence commit **`289d5c5996ba1853f21c580697e87421653700cc`**. Its worktree was clean after commit; this checkpoint is a subsequent documentation-only commit.
- Original read-only upstream `69284c13746e849104f738d6d1a347b1f457df76`; B1 checkout `d88be474ebb2529c5b095e3732b1f25509f9b824`, both preserved.
- All changes relative to the recovered base are confined to `research/mini_mythos/base_v01/official_repro_v1/`. No PR was created or merged; PR24 was not operated on.

The audit/custody tools were prepared after model launch, before their own execution; their timing is disclosed, not represented as part of the pre-launch numerical freeze. The observer, official implementation, scoring, input set and running configuration were not changed after launch.

## Environment and evidence

Designated machine `bookish-pancake-vwqx7rr9x5w3wxjr`, AMD EPYC7763,2 vCPU/~8GiB RAM. New isolated eval venv `/workspaces/mythos-parcae-official-eval-cpu312`; original `/workspaces/mythos-base-v01-cpu312` remains unchanged. Python3.12.3, torch2.11.0+cpu, NumPy1.26.4, tokenizers0.23.2, Transformers5.22.1, lm_eval0.4.12, jsonargparse4.53.0. Full installed inventory, exact URL/hash dependency lock, resolver/install logs and provenance are committed. The new overlay uses fsspec2026.7.0; the original baseline still has2026.9.0.

Model observed as `ModelingParcae`,144323136 parameters, mean_recurrence8, FP32. CPU2 intra-op/1 inter-op threads, no autocast or forced attention backend. The official metadata-free tokenizer wrapper reported BOS/EOS/PAD=None; original CORE fallback BOS1/PAD0 was preserved. Torch h0 RNG was not manually seeded; original RNG states were saved without restoration or alteration.

Run root `/workspaces/mythos-evidence/base_v01/official_repro/official-core-limited-v1-20261101T093733Z`; sibling `-operator` and `-review` directories. Preparation assets are under `/workspaces/mythos-evidence/base_v01/official_repro/preparation-v1-20261101`.

Raw `observations.jsonl`:343231 bytes, SHA256 `bcd8946b0016b8fa52f0dc1ed15c0a3e8d43ef35dc8ed19cf5dbca62738eb0a2`. Parent completion SHA256 `fcfdd0f9d4e501deba00d7f80acc5bd5f09f61ae07859dd9dd6a349caa4e8ec0`.

Compact evidence and original stdout/stderr are committed with exact-byte checks against the Git index. The unfinished stdout line's original trailing space was retained; its formatting warning is recorded in `FINAL_PACKAGING.json`, not repaired. Model weights, tokenizer, original benchmark corpus, environments and binary RNG files are not in Git. Manifests bind their external evidence; the67 RNG files also have a hash-verified local backup under `acceptance_review_local/official_reproduction_work/download/external_rng/` in the user project workspace.

Review artifacts: `RESULTS.md`, `TASK_RESULTS.md`, `EXAM_COMPARISON.md`, `FINAL_INDEPENDENT_REVIEW.md`, `evidence/review/audit_official.json`, `summarize_partial.json`, `POSTFLIGHT.json`, `CUSTODY.json`, raw/copy manifests and sealing records. Independent review reran no model and checked original bundle hashes/item identities; it is automated review, not an external human or Grok audit.

## Resources and unresolved issues

- Peak observed process RSS2.829GiB. Complete-seed task times2007.45s and2115.05s exclude model load; load event114.39s. The original6000s calibration budget was insufficient.
- Per-task extrapolation gives approximately33.56–36.53 days for all273111 instances on this two-core CPU. This is an observed-workload projection with instrumentation overhead and changed full-pool example lengths, not an uncertainty interval or a claim of CPU impossibility.
- Full reproduction needs sustainably available compute. No NVIDIA GPU is present on the examined target or local machine, and no usable GPU machine/spending ceiling has been supplied. No paid resource was provisioned.
- CPU/FP32 versus publication conditions, dependency-version differences, exact paper-table-to-released-weight mapping, and unseeded Torch h0 remain limits. Original logits and internal activations were not independently regenerated.
- Earlier free-continuation quality FAIL remains; no production usability, training/recovery readiness, architecture gain or full author-score replication is established here.

## Preserved project state

B1 A5 remains BLOCKED. Prior exact CPU loading/forward/reload engineering evidence and12-prompt quality findings are unchanged. D1/D2-A and all prior checkpoints are unchanged. No upstream edits, A5 relaxation, B1 rerun, B2/D2-A, training, optimizer, GPU or PR24 operation. Formal Oracle BLOCKED/NOT_READY; `FORMAL_ACCEPTANCE_READY=False`.

## Next unique action

**Resolve a continuously available GPU machine and spending ceiling, then freeze a full official CORE execution protocol retaining all22 tasks, original seeds and273111 instances. Do not resume or repair this partial run, replace missing scores, or declare paper reproduction from its subset.** Until compute is resolved, retain this stopped checkpoint and do not launch another experiment.
