# D1 / PR #24 — owner-supplied Claude Code review transcript

Recorded 2026-10-31. Provenance: the owner pasted the following review into the project conversation. This is a transcription with Markdown/HTML whitespace normalized, not a copy fetched from Claude's scratchpad, an authenticated reviewer identity, or a GitHub APPROVE submitted as Claude. The reviewer scripts and raw diagnostic logs were not supplied. Findings and limits are retained. Approval covers executable commit `596af7f8997ca793e880a6e1d80c25c7b2043329`, not subsequent orchestration helpers or model quality.

---

D1 / PR #24 review is done and the verdict is **APPROVE** for the code at `596af7f8997ca793e880a6e1d80c25c7b2043329`. I found no blocker for the 12 CPU training runs. That does not mean D works, and I did not start training.

## File received

I received `ccb08253-D1_prepared_20261031.json`: 21,440 bytes, SHA-256 `d7ce57ca11316d0ff892bf35b26ec9ed1ef2f04a2b8587dd4671c7eae8b5a1d1`. Both match the values in your request. This is a check of byte correspondence only; it doesn't authenticate who produced the file.

- **Field checks:** a strict parse (duplicate keys and non-finite constants rejected) succeeds, and 15 of 15 field checks pass.
  - Environment: Python 3.12.3, torch 2.11.0+cpu, numpy 1.26.4, einops 0.8.0, one CPU thread.
  - `code_head`, the upstream pin and the data digests match.
  - Counts are GPT 73,433,088 FLOPs per step and 114,130,944 for P4, D0 and D1.
  - Gradient-bearing parameters are 51,904 for each Parcae arm.
  - P4, D0 and D1 share starting hashes per seed.
  - There are 36 preflight cases, all PASS with gradient error 0.0, plus 3 GPT checks.
- **Source identity:** I recomputed all six own files and eight inherited files from the `596af7f` tree. That includes `m2_matched/experiment.py`, which the handoff package didn't contain. Every hash and the aggregate `7b7660c5…` equal the prepared values.
- **Not verifiable from the file:** the raw initial tensors, `data.json` and `pip-freeze.txt`.

## What I found

| ID | Severity | Where | Finding |
| --- | --- | --- | --- |
| R01 | LOW | `run_cpu.py:293,313,366-376` | A numerical failure in a worker is saved as FAIL in the job row, but the parent summary ends as BLOCKED with exit 2. The protocol classes a valid numerical failure as FAIL. No evidence is lost. Fix: raise `NumericalFailure` when the worker returns 1, as C1 and MES do. |
| R02 | INFO | `dual_state.py:115-125`, `measurements.py:276-287` | `zero_a` means different things in D0 and D1. In D0 it zeroes only the answer state carried forward. In D1 it also removes the feedback `a` in `e + a`. On an untrained model (seed 2101, 32 prompts) the mean last-position logit L2 is 1.429 for full D1 `zero_a`, against 0.403 when only the carried state is zeroed. A zero vector is also out-of-distribution. So don't read D0-vs-D1 `zero_a` differences as how much the answer state matters. |
| R03 | INFO | `measurements.py:237-273` | The same-prefix profile covers only the six-digit prompt. Confidence and entropy at call 2 come from a state the head was never trained to read. The relative-change fields are zero by construction at some calls. |
| R04 | INFO | `run_cpu.py:195-212`, `:314-315` | Trace lengths and the 36/27/6 profile and intervention counts aren't asserted. They hold by how the worker loops are built. |
| R05 | INFO | scope | Exit 0 means measurement finished, even if every screen FAILs. D vs P4 changes state and routing together. Compute differs: GPT 73.4M against Parcae 114.1M per step. Three seeds, already-viewed development data, and the 8,320 inactive parameters are retained. All declared. |

## The six requested checks

1. **Old-a / new-z routing: PASS.** Against the native forward (P4) and my own explicit unroll (D0, D1), at depth 2 and 4 on real pinned Parcae, seed 2101, I got:
   - bit-equal logits, loss and RNG state;
   - bit-equal gradients, max error 0.0;
   - the same two None-gradient tensors (8,320 parameters) in every arm.
   - Routes are `single×n` for P4 and `work, answer, …` for D0/D1.
   - No hooks remain after success or after a forced error, prefix causality holds on the real D1 model, and no parameters are added.
2. **Gradients and RNG pairing: PASS.** RNG hashes are equal for P4, D0 and D1 over 3 steps. The parent also compares the full 3000-step trace and the batch-index digest.
3. **Training and snapshots: PASS.**
   - **Training:** the optimizer covers all parameters. Batch indices and training seeds are shared across arms.
   - **Snapshots:** they are saved at the fixed points 300, 1500 and 3000 (36 in all) with model, optimizer, RNG and indices. The protocol quotes no extra figures here.
   - **Evidence protection:** the evaluation workers re-check snapshot metadata and weight digest. Duplicate workers cannot overwrite existing rows or logs.
4. **Measurement meaning: PASS with the R02–R03 caveats.** Same-prefix state trajectories are kept separate from full-answer generation. Depth 2→4 transitions are two generation policies, not an in-place edit. No-op is bit-identical, and state bytes are logical payload, not peak memory.
5. **Scope and evidence protection: PASS.** Only the already-viewed development data is used, with no H1, HC, H2 or C1T. There are 21 final conditions. Existing or partial output is never overwritten.
6. **Criteria: PASS.** The exploratory screens are D0-P4, D1-P4 and D1-D0 at depth 4, with mean at least +1 pp and every seed at least −1 pp. Candidate selection stays `NOT ASSESSED`.

## What I ran

- **File checks:** the size and SHA of the JSON, a strict parse, the 15 field checks, and the source-identity recomputation.
- **Unit tests:** `unittest test_d1`: 25/25 PASS. These are fixture tests.
- **Native diagnostic:** real pinned models, forward/backward only, no `optimizer.step`. It covered the equivalence runs above, RNG pairing, probes, hooks after an error, causality, and an untrained state profile and sensitivity run.
- **Environment:** my torch is `2.11.0+cu130`, not `2.11.0+cpu`, and I bypassed the version gate. This is not a reproduction of the production build. Upstream stayed clean.

Not executed: `prepare`, `train`, `evaluate`, any optimizer step, the 12 trajectories, development scoring, the launcher script (static read only), resume replay, and seeds 2202 and 2303 native diagnostics.

Formal Oracle stays BLOCKED/NOT_READY, `FORMAL_ACCEPTANCE_READY=False`, and there is no G2 REAL. I've stopped here. The full report is at `/tmp/claude-0/-home-user/2c7c9a9c-fc7c-5adb-90a5-e297bc6c2a17/scratchpad/tools/D1_CLAUDE_REVIEW_20261031.md`.
