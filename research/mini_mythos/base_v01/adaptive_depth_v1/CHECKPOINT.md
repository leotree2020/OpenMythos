# MYTHOS-ADAPTIVE-DEPTH-DEV-V1 checkpoint

CPU development acceptance: **PASS**. Original140M validation and quality/cost improvement: **NOT TESTED**.

Purpose: implement the first isolated adaptive-computation mechanism on native Parcae, toward the user's goal of developing an open Mythos model with Claude Mythos capabilities as the long-term reference. This is neither an exact reconstruction of Claude's private architecture nor evidence of capability parity. The broader direction and its public-source limits are in RESEARCH_DIRECTION.md.

## Git and frozen implementation

- Repository: leotree2020/OpenMythos.
- Base result checkpoint: c63b829a752ac57d22addfe17ff53ecbcb58e8a0.
- Branch: mythos-adaptive-depth-dev-v1.
- Execution/source freeze: **93e66ebfd8a1b6d3da07cde57fdfd97b552604af**.
- SOURCE_MANIFEST.json SHA256: a4d9d11a19eb02ad8b5ca0e67d25647e3d72a4325dfeba00408bcd02ce766d31.
- Result/checkpoint commit: the subsequent commit containing this document. It changes only evidence/documentation relative to the freeze; no executable source was changed after final acceptance.
- Upstream Parcae stays clean at 69284c13746e849104f738d6d1a347b1f457df76; before/after tracked-file byte manifests are identical.
- PR #24 head was re-observed as 4308099bfc90d9398f54a47f9272b6bd4582f7b9. No PR action or merge was performed.

All new repository paths are under research/mini_mythos/base_v01/adaptive_depth_v1/. Local working artifacts are in acceptance_review_local/adaptive_depth_v1_work; the final run is acceptance_review_local/adaptive_depth_v1_acceptance/attempt-v1. This local source directory is not a claim of a Git checkout: remote blob identity was verified separately before the frozen run, in evidence/PUBLICATION_VERIFICATION.json.

## Implemented behavior

One prefix, one h0 and one Prelude. Continue native recurrence to8 and16; compare final-position FP64 softmax distributions using TV. Exit at16 when TV<=0.01, else continue the same state to32. Intermediate readouts are isolated from the recurrent state. API outputs only next-token logits; labels, cache, masks and unsupported configurations are rejected. Native fixed8/16/32 bypasses are available. This is a fixed heuristic, not learned ACT or persistent checkpoint recovery.

The threshold is an unvalidated engineering candidate fixed before quality testing. It is not a quality guarantee. Costs include two or three full Coda/head readouts plus policy/validation work; no speedup or FLOP advantage is claimed. Fixed16/32 have36/68 block calls; planned adaptive16/32 have38/72. Native selected-path module hooks independently checked the corresponding path counters; synthetic fixture counters are not native module throughput measurements.

## Acceptance evidence

| Purpose | Environment / Input | Expected | Actual | Status |
|---|---|---|---|---|
| Controller arithmetic and execution semantics | Local CPU synthetic fixtures | Inclusive frozen TV rule, invalid inputs rejected, actual early stop/continuation and readout isolation | All10 synthetic/policy tests passed | PASS |
| Native tiny correctness | Pinned Parcae; random32-hidden,2-head,128-MLP,64-vocabulary model,2/2/2 blocks | Native vs fixed/resumed8/16/32 output bytes equal under paired h0; nontrivial states; causal control and immutability | All5 native tests passed; no skip | PASS |
| Complete frozen suite | Python3.12.14/Torch2.9.0+cpu, Windows CPU | Exactly15 frozen test IDs, including5 required native tests; no failure/skip | 15 run,0 failures,0 errors,0 skips,0 expected failures,0 unexpected successes,0 unrun | PASS |
| Environment and custody | CPU FP32 model; FP64 policy;1 intra-op/1 inter-op; deterministic; no autocast;-I -B | Frozen source identities, runtime, dependency inventory and upstream preserved | 17 driver checks passed; before/after packages and upstream equal | PASS |
| Original140M weights and official target environment | Designated Codespace, original model artifacts | Separate frozen identity/cost smoke | Not accessed or executed in this stage | NOT TESTED |
| Language quality, instruction following, cost advantage | Separate future controlled protocol | Added value relative to native fixed-depth and budget controls | No performance evidence generated here | NOT TESTED |
| Training / optimizer / training recovery | Separate future protocol | Explicit gradient and uninterrupted-vs-resumed training checks | No training performed; this interface is inference-only | NOT TESTED |

The final test suite took2.649s as reported by unittest; the complete driver took6.344s. These are development durations, not model performance benchmarks. See evidence/DEVELOPMENT_RESULTS.json and the unedited stdout/stderr. Synthetic tests include an intentionally stable but wrong prediction; passing that test proves only the controller's semantics.

Native tiny initialization uses scaled + orthogonal random weights so depth outputs/states are nondegenerate. It is not the official140M initialization or pretrained checkpoint. DEVELOPMENT_ATTEMPTS.json preserves all3 pre-freeze attempts: the first failed in fixture construction after an incompatible initialization override, then the fixture was corrected and additional identity/causality checks were added. No frozen final acceptance was retried and no performance outcome was used to tune a threshold.

## Unresolved and preserved boundaries

- Original140M/config compatibility, selected-depth identity, practical overhead and language benefit remain untested. Local Torch2.9 results do not establish Codespace Torch2.11 numerical identity.
- Stable predictions may be wrong. Adaptive computation may cost more than fixed16 and may fail to outperform random routing at comparable cost.
- Existing32 historical articles are development evidence, not a fresh test or known pretraining-clean data.
- Claude Mythos weights/full training recipe are unavailable to this project; OpenMythos is a theoretical reference. No parity claim.
- Reviews are internal agent static and saved-evidence reviews. No external Claude/Grok/human review occurred; Grok cross-review remains NOT TESTED and is not silently replaced by an external-review claim.
- No upstream edit, A5 relaxation, B1 rerun, B2/D2-A, GPU, training, dependency installation or PR #24 operation. D1's failed positive-performance screens and original B1 A5 BLOCKED remain unchanged.
- Formal Oracle remains BLOCKED/NOT_READY; FORMAL_ACCEPTANCE_READY=False.

## Next unique instruction

Prepare, internally review and freeze a bounded CPU identity/cost smoke protocol for this exact controller against the original140M weights in the designated Codespace. Verify the native configuration, all original state_dict bytes and paired h0; compare native fixed8/16/32 with the continued outputs, validate actual module calls and immutable state, and account for every extra readout. On any BLOCKED/FAIL preserve evidence and stop. Do not begin quality testing until that correctness gate passes; quality testing then needs its own frozen prefix-only data/control/decision protocol. Do not rerun this completed development acceptance or the old B1/depth experiment.
