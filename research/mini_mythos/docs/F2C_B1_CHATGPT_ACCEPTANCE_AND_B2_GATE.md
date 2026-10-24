# Mini-Mythos F2-C B1 — ChatGPT Independent Acceptance and Frozen B2 Gate

Date: 2026-10-24, Asia/Tokyo  
Decision: **B1 DISCOVERY PASS (limited scope); B2 formally authorized only under the safeguards below; F2-C overall remains NOT TESTED / PENDING REVIEW.**  
Reviewer: ChatGPT; static code/source, GitHub evidence, arithmetic, and independent SHA-256 review. No independent CPU run by ChatGPT.

## Source, environment and status

- Repo `leotree2020/OpenMythos`; working branch `mini-mythos-p1c-gate22c-readiness`.
- B1 reviewed commit `12800a65b2ab0e82df412a4e93daadcdbaa6c646`.
- Approved B1 frozen gate `2efc70a0dedef9bf2d501c8ecba4ae312d3c858e`.
- Native upstream Parcae `69284c13746e849104f738d6d1a347b1f457df76`; B1 JSON reports clean Parcae worktree.
- Python 3.11.2, PyTorch 2.14.1+cpu, x86_64, CPU threads 2, synthetic input seed 42, parameter count 247936.
- B1 is a standalone CPU exploratory probe, not a generic training, CUDA, or full numerical gradcheck.
- Existing unrelated local modification `research/mini_mythos/gate2_1/TEST_RESULTS.json` reported by Grok must remain untouched. Local working-tree state not independently examined by ChatGPT.

## Frozen discovery manifest

Exact reviewed immutable manifest:

`research/mini_mythos/gate2_2/evidence/f2c/F2C_DISCOVERY_MANIFEST.json` **at commit** `12800a65b2ab0e82df412a4e93daadcdbaa6c646`  
GitHub blob SHA: `918e49ef06c31083245259feb4fa2d13eab96cad`  
Input SHA256: `be681f780b08da931155937a8c88c0adcef587778ce838b1504a9ae7c2e6648a`

| Exact core parameter name | Flattened zero-based index | Base value | Full AD | TBPTT AD | Abs difference |
|---|---:|---:|---:|---:|---:|
| `transformer.core_block.1.attn.c_proj.weight` | 1424 | -0.003036822658032179 | 0.6529785394668579 | 0.35449838638305664 | 0.29848015308380127 |
| `transformer.core_block.0.attn.c_proj.weight` | 1440 | -0.00918375514447689 | 0.44759616255760193 | 0.20615354180335999 | 0.24144262075424194 |
| `transformer.core_block.0.mlp.proj.weight` | 2934 | 0.016566788777709007 | -0.40059801936149597 | -0.2358657419681549 | 0.16473227739334106 |

No replacement, reselection or reranking of these manifest entries during B2. If exact weights/input cannot be recreated, label BLOCKED or INCONCLUSIVE, **not** substitute alternatives.

## Evidence review

- The B1 commit series is ahead of gate `2efc70a0` by six commits. The final `12800a65` is a small warning-removal/code-and-artifact commit, not the sole source of B1 files.
- B1 result content: baseline repeat PASS; AUX64 PASS (surrogate only); native `(1,1)` suffix reconstruction max logits diff 0, loss diff 0, selected core AD diff 0; three core negative-discovery differences > 0.01; six exploratory native-full FD checks within the frozen exploratory envelope.
- Recomputed `|L(theta+h)-L(theta-h)| / (16*ulp32(L))` for h=1e-3 and 1e-2: approximately (171,1712), (117,1173), (105,1050), by manifest order. Six points are resolved well beyond the **16 ULP** gate. FD values were stable at both exploration h.
- Independently recalculated SHA-256 on GitHub-hosted bytes; all matched manifest:
  - F2C_B1_RESULTS.json: `ff7d6ec9e1c960115faa67c60b4ce601286b518d5820d2a2718694068ad14e87`
  - stdout.txt: `6159bdd5957d62f1483ed95ea14ec1b35d5d977472fa5b685da82bee138be451`
  - stderr.txt (empty): `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
  - exit_code.txt (`EXIT:0`): `194ff5bca66278888f0f00be5c7ca523d15098ece958b14952533811089f6106`

## Issues / non-negotiable B2 safeguards

**G1: Hard failure propagation.** B1's `test_parcae_gradient_math_cpu.py` currently ends in unconditional `return 0`, even if its individual results include FAIL, BLOCKED, INCONCLUSIVE or reconstruction failure. B1 evidence itself shows no such failures. Do not reuse that behavior for B2: define item-level and overall `PASS / FAIL / BLOCKED / INCONCLUSIVE` and emit a nonzero exit for **FAIL or BLOCKED**; INCONCLUSIVE must remain non-PASS and must never be silently promoted. A hard failure must preserve all records.

**G2: Immutable selection and provenance.** Read selected core scalar names and zero-based flattened indices from the frozen B1 manifest pinned by Git Commit/blob SHA above. Verify exact seed 42, input SHA, native upstream HEAD/worktree, module import origin, expected 247936 parameters, and baseline parameter values (compare stored float32 representations rather than assuming arbitrary decimal rounding). Do not perform B1 parameter discovery again or rewrite manifest. Check that selected tensors are independently owned and unaliased.

**G3: Objective and numerical controls.** For native full `(0,2)`, compare Autograd to central FD of the *same* pinned original forward under fixed RNG. For native TBPTT `(1,1)`, freeze `x1` under **baseline weights only**, preserve correct input embeddings/VE/masks, step=1,total=2, C/coda/norm/logit casting/scaling/softcap/loss/ignore index, and compare suffix AD to native TBPTT AD **before** suffix FD. FD must perturb only the selected core scalar; restore base tensor exactly even on error. Native full and TBPTT objectives must be separately labeled.

**G4: Predeclared gates remain unchanged.** Native FD h={1e-3,1e-2}; actual float32 perturbed h+/h- >0, <1% asymmetry; loss signal at least 16 ULP; baseline reproducible; native exploratory error envelope `1e-3 + 1e-2 * max(abs(gAD),abs(gFD))`, h both; FD stability across h; suffix baseline logit max diff <=1e-6, loss diff <= `1e-6+1e-6*max(abs(loss_native),abs(loss_suffix))`; suffix scalar AD diff <= `1e-6+1e-5*max(abs(g_native),abs(g_suffix))`. Failing reconstruction invalidates TBPTT FD reference and is not proof of a Parcae gradient flaw. Signal too small -> INCONCLUSIVE. Out-of-envelope numerical observations -> discrepancy requiring diagnosis, never an automatic architecture change.

**G5: Audit trail and experiment status.** New B2 script and new `f2c/b2/` evidence only, preserve B1 code and files. Log full command, Python/PyTorch, Git HEAD/status and import path, input and manifest hashes, all chosen indices, raw forward/loss/AD/FD, per-h ULP and effective perturbations, stdout, stderr, real exit code, SHA256, Git diff/status. Overall `PENDING CHATGPT REVIEW` regardless of local PASS; do not claim mathematical correctness established until independent review. No CUDA, no new installations, no upstream edits, no merging research branches.

## Approval and next instructions

- **B1 DISCOVERY: PASS / CLOSED** (only discovered candidate parameter locations, verified numerical signal and suffix reconstruction).
- **B2 IMPLEMENTATION AND CONTROLLED CPU CONFIRMATION: AUTHORIZED** under G1–G5, with the **same frozen manifest**.
- **Full F2-C stage final PASS: NOT AUTHORIZED**; must be decided from B2 evidence by ChatGPT/Grok cross-review.
- `NATIVE PURE FLOAT64`: BLOCKED by original mixed-fp32 operators; `AUX64` tests only standalone reference machinery.
- GPU native training/MuonAdamW, Gate 2.2-C and checkpoint/RNG resume: NOT TESTED.
- Exact next instruction for Grok: read this acceptance file and implement an isolated B2 verifier using the immutable B1 manifest; run CPU confirmation once, preserve all raw evidence and exit with formal status; submit a new isolated commit and stop for ChatGPT review.
