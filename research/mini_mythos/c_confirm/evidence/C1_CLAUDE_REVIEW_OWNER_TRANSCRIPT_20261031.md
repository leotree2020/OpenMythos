# C1 Claude Code review — owner-supplied transcript and addendum

Registered by ChatGPT, 2026-10-31. Reviewed executable commit: `8a646eb56a9bcffb9767ad9f50843f85670b2fa1`.

Provenance: the two sections below transcribe the owner's two pasted Claude Code messages. The original scratchpad Markdown files, diagnostic scripts and raw logs were NOT fetched. HTML whitespace markers have been removed for readability. This is not a byte-identical copy of the original scratchpad file, cryptographic authentication of the reviewer, or a new independent test run. Claude's code APPROVE is scope-limited; its prepared.json byte audit remains NOT TESTED. Registration does not start training.

## First supplied report

The review of commit `8a646eb` is done and the conclusion is **APPROVE**: I found no blocker for entering the 15 CPU training runs. That only means the code can go to training. It is not a model-quality result, and it doesn't start training.

I could not read `prepared.json`. `/workspaces/.../mech_c_confirm_v1/prepared.json` does not exist here, and no C1 output was uploaded. I verified no prepared bytes or hash and make no inference about them. I recomputed values from the source for you to compare against your file:

- **C1T allocation digest:** `14003d130a3257e5c26d669fe79f6c7b6bed3bf8ce87c1f7c9096605fec595d0`, matching the checkpoint claim.
- **Legacy digests:** `92cf3818…`, `18ec9725…` and `e6256d5f…` re-created exactly.
- **Budget:** ceiling 355663872000, steps GPT/P4/C4 of 4843/3116/3000, unused fraction under 0.1% for every arm.

### What I reviewed

- **Commits:** 8a646eb against base `b16f7971`. It adds only the six files under `research/mini_mythos/c_confirm/`, 1124 lines, nothing outside that directory. The latest docs commit `92d61d85` changes only `CHECKPOINT.md` and `CLAUDE_REVIEW_REQUEST.md`.
- **Files read in full:** the six new files, the latest `CHECKPOINT.md`, `mech_c/c_adapters.py`, the MECH-AB interfaces, the R1-B task, the M2 factory, and the pinned upstream.
- **Inherited files:** the SHA-256 of all six inherited files equals the constants in `c1_policy.py`.

### Findings: six INFO, none blocking

| ID | Where | Observation |
| --- | --- | --- |
| R01 | `c1_policy.py:234`, `run_cpu.py:182,293` | Exit code 2 covers both "selection BLOCKED" (for example a ceiling) and "instrument BLOCKED". The printed `status`/`candidate_selection_status` tell them apart. A GPT-safeguard failure now gives exit 1 and cannot hide behind exit 0. |
| R02 | `run_cpu.py:75-105` | `verify_training` does not bind each arm's full batch-index hash or the snapshot metadata. Metadata is checked per snapshot at evaluation (`c1_runtime.py:279-282`), so nothing is missed. |
| R03 | `run_cpu.py:196-211` | Hand-started workers are blocked only by state gates. A manual worker could pre-claim a job and make the parent end BLOCKED, but evidence is kept and nothing is rewritten. Don't start workers by hand. |
| R04 | `test_c1.py:24-34` | The unit tests use fixtures. Native behaviour is covered by my diagnostics. |
| R05 | `PROTOCOL.md:16` | "All parameters trained" means they are in the optimizer. The 8,320 inactive parameters still get no gradient. C4 has 54,464 of 62,784 with gradient. The same paragraph discloses this. |
| R06 | scope | C4 vs P4 is not parameter-matched (+2,560). Equal counted FLOPs are not equal exposure. The 40,960 answers are repeated measures on 2,048 questions. Five seeds, depth 4 only, bootstrap diagnostic. All declared. |

### The six requested checks

1. **C4 parameters, saving, pairing, GPT: PASS.**
   - The optimizer covers all C4 parameters. The saved state includes `adapters.*`. The full-state digest changes when an adapter is perturbed and the base digest does not.
   - P4 and C4 base weights are bit-equal. Adapter construction doesn't touch the global RNG. P4 and C4 RNG hashes match over 3 steps.
   - With zero correction, C4 matches native loss, logits, RNG and base gradients on real models (error 0.0). With non-zero up-factors, all four loop slots of both banks get gradient.
   - GPT makes one native labelled call with `return_logits=False`, and its loss, RNG and gradients equal `m2.call`.
2. **Groups, seeds, budget: PASS.** Native probes give 73433088, 114130944 and 118554624 FLOPs per step, and 65344, 60224 and 62784 parameters. `budgets()` hard-fails on any count drift. 20 snapshots are saved.
3. **C1T holdout: PASS.** C1T has 2048 canonical keys, 512 per stratum, with 0 overlap with the 5120 legacy keys and with train/development. Labels are created only after `verify_training`. HC/H2 never get labels.
4. **Evaluation workers: PASS.**
   - The worker hashes and parses the same bytes once, and the parent re-checks them afterwards.
   - Duplicate workers cannot rewrite old rows or logs.
   - Snapshot hash, metadata and full-state digest are checked before scoring.
   - Generation uses prompts only, and teacher-forced NLL is separate.
   - Tampered metrics are rejected with "saved answer/score mismatch".
5. **Decisions: PASS.** Selection is FAIL if either primary or the GPT safeguard fails, else BLOCKED if either is blocked. The exit code follows selection, not the primary alone. On synthetic rows:
   - All three screens pass: PASS, exit 0.
   - Primary passes but the GPT safeguard fails: FAIL, exit 1.
   - Ceiling: BLOCKED, exit 2.
6. **Scope: PASS.** 20 depth-4 conditions only, bootstrap diagnostic, the inactive-parameter and five-seed limits retained.

### What I ran

- **Unit tests:** `unittest test_c1`: 29/29 PASS (fixtures, not native acceptance).
- **Native diagnostics:** seed 1101 only, real pinned models, forward/backward without any `optimizer.step`: counts, parameters, gradient coverage, zero-path equivalence, RNG pairing, GPT route, a generation check on 4 development prompts of untrained models, and a non-zero adapter check.
- **Data and policy checks:** recomputed allocation and overlap, plus `summarize`/selection on synthetic rows.
- **Environment:** my torch is `2.11.0+cu130`, not the required `2.11.0+cpu`. I bypassed the version gate and ran components directly, so this is not a production reproduction (FLOP counts matched anyway). Pinned upstream stayed clean, and nothing was modified or committed.

### Not run or not verifiable

- `prepared.json` content and hash.
- `prepare`, `train`, `evaluate`, any optimizer step, and the 15 trajectories.
- C1T scoring, and HC/H2.
- The launcher script (read statically only), and resume replay.
- Native probes for seeds 1202–1505, and hardware cost.

Formal Oracle stays BLOCKED/NOT_READY with `FORMAL_ACCEPTANCE_READY=False`, and there is no G2 REAL. Training still needs your own `--review-report`, `--reviewer` and `--review-approved`. I've stopped here.

The full report is at `/tmp/claude-0/-home-user/2c7c9a9c-fc7c-5adb-90a5-e297bc6c2a17/scratchpad/tools/C1_CLAUDE_REVIEW_20261031.md`.

## Second supplied message — missing-file clarification/addendum

**APPROVE for the code at `8a646eb`, but I could not verify `prepared.json`, because the package never arrived.** The only new upload is `69b69c27-…Review_Request_20261031.md` (3,829 bytes), identical in content to the earlier request. It contains no zip and no `prepared.json`, and a filesystem search found none. I did not read or hash-verify it, so that check is NOT TESTED.

My earlier report on this commit therefore stands. There were no blockers and six INFO items, none requiring a change. They cover:

- C4 optimization and saving
- three-group budgets and pairing
- C1T isolation
- the completion barrier
- the primary and GPT-protection decision rule

APPROVE means the code can go to training and says nothing about model quality.

### What I could check without the file

- **Newer branch commit:** `679d9fd` is docs-only against `8a646eb`. It records an earlier ChatGPT audit of `prepared.json` as 22,745 bytes with SHA-256 `2f3e1251eaf474d3a49f2de826b6ba6c9711a16a15a9d74c09f8386b5db85829`. I did not verify those bytes or that audit.
- **Source identity:** I recomputed the source-identity aggregate from the `8a646eb` bytes using the code's own `identity()` formula. It is `750d827c88244dfd4d26dc2be6d2fedf88868c399665c882110fbbde9c86a4e0`, equal to the value `679d9fd` quotes.
- **Budget:** the allocated totals are GPT 355,636,445,184, P4 355,632,021,504 and C4 355,663,872,000, matching the table in `679d9fd`.
- **Native probes:** earlier runs gave the same step counts, and gradient-bearing parameter counts of 65,344, 51,904 and 54,464.
- **Holdout:** the C1T digest `14003d13…` also matches.

These show the claimed values are what this code produces. They do not authenticate your file.

### Does the missing file block training?

Each training worker re-checks the source identity, start hashes and train-file hash against `prepared.json` (`c1_runtime.py:202,205,211`). A mismatched file would stop the run instead of passing silently. If you want the `prepared.json` check done before approval, treat the review as pending until you re-upload it. I'll then check its bytes, hash and fields in one step, without rerunning anything.

Nothing was rerun or changed, and no training was started. The report with this addendum is at `/tmp/claude-0/-home-user/2c7c9a9c-fc7c-5adb-90a5-e297bc6c2a17/scratchpad/tools/C1_CLAUDE_REVIEW_20261031_v2.md`.
