# Mini-Mythos F2-C B2 — ChatGPT Independent Evidence Review

Date: 2026-10-24 (Asia/Tokyo)  
Reviewed Grok B2 commit: `3ddbef0a5fd5fe048430b1f1ee56f04aed224391`  
Parent (frozen B2 gate): `d875d601117ea044ef366a58cd183fe1b956890c`  
Decision: **RECORDED NUMERICAL CHECKS PASS; B2 FINAL PROCESS ACCEPTANCE PENDING R1 GUARD HARDENING; F2-C OVERALL NOT CLOSED.**

## Scope and provenance

Repo `leotree2020/OpenMythos`, branch `mini-mythos-p1c-gate22c-readiness`; pinned upstream Parcae HEAD `69284c13746e849104f738d6d1a347b1f457df76`. B2 commit adds exactly seven files, 967 additions, zero deletions, all under isolated B2/docs paths. The prior B1 manifest remains at GitHub blob SHA `918e49ef06c31083245259feb4fa2d13eab96cad`.

Reviewed exact B2 script `research/mini_mythos/tests/test_parcae_gradient_math_b2.py`, results, raw stdout/stderr, recorded process exit, run metadata, and frozen B1 manifest. Independently recomputed recorded FD values, relative/absolute thresholds, 16-ULP signal gates, and stability conditions from the B2 JSON. Independently recomputed SHA-256 of all four archived evidence files.

This is a static independent code review and artifact/arithmetic/hash review; **not** a fresh native Parcae run by ChatGPT.

## B2 experimental results

- Three locked Core weight scalars: `transformer.core_block.1.attn.c_proj.weight[1424]`, `transformer.core_block.0.attn.c_proj.weight[1440]`, `transformer.core_block.0.mlp.proj.weight[2934]`.
- Fixed seed 42, CPU float32, Python 3.11.2, torch 2.14.1+cpu; recorded clean Parcae worktree and `EXIT:0`.
- FULL `(0,2)`: six finite-difference points (3 scalars × h=1e-3,1e-2) satisfied the predeclared error envelope, actual step symmetry and 16-ULP loss-signal gate.
- TBPTT `(1,1)`: native vs frozen-`x1` suffix logits max difference 0, loss difference 0, selected Core scalar AD differences 0; then six suffix FD points satisfied predeclared gates.
- Negative full-vs-TBPTT Core scalar gradient gaps: 0.29848015308380127, 0.24144262075424194, 0.16473227739334106, all >0.01.
- FD values computed independently from `(Lplus-Lminus)/(theta_plus-theta_minus)` match recorded values; finite-difference error bound, both-h stability and 16-ULP gates recompute true for all twelve points.
- Max FULL abs errors by scalar: 0.0004269954274145338, 0.00008456293683639649, 0.00005487212500898675.
- Max TBPTT abs errors by scalar: 0.000029982629238700653, 0.0001599232245952653, 0.0001686126533463339.

## Evidence integrity

Independent SHA-256 checks of GitHub-hosted assets match `RUN_META.json` for all four:

- `F2C_B2_RESULTS.json`: `f04a7b984bf491edca546019320a494c6ed142a517cc4bea80fb41132fbc9fe1`
- `stdout.txt`: `4901d6a289819bd4060f09fef768e3b248b9edea43c298445b744480b4d4bc93`
- `stderr.txt` (empty): `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- `exit_code.txt` (`EXIT:0`): `194ff5bca66278888f0f00be5c7ca523d15098ece958b14952533811089f6106`

## Blocking gaps in code's predeclared acceptance gates

1. **G2: The runtime manifest itself is not hash-verified.** The script obtains the historic manifest blob with `git -C /tmp/om rev-parse ${MANIFEST_COMMIT}:...` and compares the historic blob to a constant, then reads `--manifest` from disk without computing/comparing the **actual bytes** to the frozen blob. It checks names, indices, input hash and three base values, but metadata/threshold fields can be silently changed. Before closing B2, verify the exact disk manifest blob against `918e49...`; fail BLOCKED upon mutation, prove it with a negative test. Preserve original B1 manifest unmodified.
2. **G1: Failure precedence is not guaranteed.** Code sets `overall="INCONCLUSIVE" if unstable else aggregate(rows)`; if a row is FAIL and the two FD estimates are also unstable, that would downgrade FAIL to INCONCLUSIVE. Hard failures must outrank numerical inconclusiveness. Prove via synthetic test without editing upstream code.
3. **G2/G3: Some required provenance/guards not checked at runtime.** The code hardcodes `/tmp/om` for history lookup, rather than locating the research repository from `__file__` or CLI. It does not explicitly check actual imported Parcae module path, expected parameter count 247936, selected tensor ownership/no-alias, nor verify parameter tensor equality after all perturbations. These were explicitly part of the frozen B2 gate. Add small fail-closed checks; do not change the mathematical test, fixed selection, h grid, or thresholds.
4. The recorded B2 values are bit-identical to B1 exploratory values for the matching FULL checks, expected under the same deterministic seed and inputs. This is a locked-parameter controlled replay, not an independent held-out data/seed study. This distinction limits the scientific conclusion, without invalidating the reported B2 checks.

## Decision / required action

- **B2 committed numeric evidence:** PASS (within the declared 3-scalar CPU scope, based on reviewed Grok execution artifacts).
- **B2 formal acceptance tooling:** **PENDING** until safeguards G1/G2/G3 are enforced, with explicit synthetic negative tests.
- **F2-C as a whole:** **PENDING REVIEW, not final PASS**, and never a blanket whole-model derivative correctness claim.
- **Native pure fp64**: BLOCKED by upstream float32 operations.
- **GPU, MuonAdamW, native train.py, Gate 2.2-C**: NOT TESTED.

Next Grok directive: **B2-R1 MINIMAL GUARDS ONLY**. Preserve manifest and prior B2 artifacts, correct manifest-on-disk check, failure precedence, import and parameter-source checks and restoration assertions, and remove hardcoded `/tmp/om`; provide synthetic negative guards and a new CPU evidence run using same three frozen scalars/h/seed/inputs and unmodified upstream. No new experiment designs, no new selection, no tolerance changes, no CUDA/GPU, no training, no dependency changes, no base-branch merge. Store isolated R1 code/evidence, Git diff/status, stdout/stderr/exit/SHA256, and stop for ChatGPT review.
