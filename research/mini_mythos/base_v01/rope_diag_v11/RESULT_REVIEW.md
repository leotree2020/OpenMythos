# RoPE diagnostic result review — 2026-11-01

The frozen CPU diagnostic completed successfully. All five predefined paths failed the compatibility screen. These are separate conclusions: execution PASS; source explanation UNRESOLVED. B1 A5 remains BLOCKED.

## Purpose, environment, input and acceptance

- Purpose: determine whether the stored RoPE buffer is compatible with one of five predefined numerical constructions; establish controls and reproduce the historical A5 scalar first.
- Environment: Codespace `bookish-pancake-vwqx7rr9x5w3wxjr`; `/workspaces/mythos-base-v01-cpu312/bin/python`; Python 3.12.3, torch 2.11.0+cpu, numpy 1.26.4, einops 0.8.0, tokenizers 0.23.2, huggingface-hub 1.33.0; frozen dependency inventory and runtime controls passed G0. CPU only, one intra-op and inter-op thread, deterministic algorithms enabled.
- Input: original B1 run `b1-20261101T021657Z`, original weight/config bytes, upstream `69284c13746e849104f738d6d1a347b1f457df76`, and frozen diagnostic protocol/source.
- Expected: G0–G5 pass; N1/N2/N3/I32 agree bytewise; exact historical scalar reproduction; two independent evaluations per T/P/R/Q; full-range metrics; protected inputs unchanged. Compatibility is evaluated separately against the unchanged Python scalar `1e-6`.
- Actual: G0–G5 PASS; 165 recorded checks PASS, zero FAIL/BLOCKED; no stop or emergency artifacts; all five compatibility screens false; all five bitwise-match flags false.
- Status: execution **PASS**, numerical-path source explanation **UNRESOLVED**, original B1 A5 **BLOCKED**.

## Version and run identity

- Branch: `mythos-base-v01-rope-diag-v11`.
- Frozen implementation A: `d51cd388cde2e202a044ca148c29fd441acc440d`.
- Execution/checkpoint HEAD B: `f008592ae547513e3d51131b33735d6d748e6e01`.
- Run: `rope-v11-20261101T051150Z`; launch 2026-11-01 05:11:50 UTC; process completion 05:12:59.706467 UTC.
- One formal invocation; the N3 interpreter is an internal control, not a second run. No fixtures, helper rehearsals, model construction, forward, generation, training or GPU work occurred.
- The formal claim remains present. No source fix or repeat run occurred after results.

## Primary results

Each comparison covers 262,144 FP32 components / 131,072 cos-sin pairs over positions `[0,2048)`. Errors below use the original FP32 subtract/abs/max definition.

| Path | Maximum absolute error versus stored S | Components above 1e-6 | Bit-identical components | diagnostic_match | bitwise_match |
|---|---:|---:|---:|---|---|
| N — native helper | 0.00012207025429233909 | 7,160 | 204,723 | false | false |
| T — FP64 trig from FP32 phase, final FP32 | 0.00012207025429233909 | 7,159 | 209,672 | false | false |
| P — FP64 phase/trig from FP32 frequency, final FP32 | 0.0001735686673782766 | 49,384 | 106,796 | false | false |
| R — FP64 frequency/phase/trig, final FP32 | 0.00015680474461987615 | 57,328 | 97,972 | false | false |
| Q — FP64 frequency rounded to FP32 before FP32 phase/trig | 0.00012207025429233909 | 22,732 | 175,297 | false | false |

G2 observed `0.00012207025429233909`, exactly equal to the hash-verified historical value. This reproduces one scalar, not the historical N tensor. Current N repeats and I32 agree bytewise. N3 PID 38824 differs from parent PID 38345; its process controls passed.

The secondary `[0,112)` maxima also exceed `1e-6`: N/T/Q `7.625669240951538e-6`, P `9.294599294662476e-6`, R `8.355826139450073e-6`. Short context is not a demonstrated resolution.

## Evidence review and custody

- All 230 entries in the original full manifest were re-hashed on the target: PASS. The run contains 232 files and three directories; the two extra files are the explicitly excluded manifests themselves. No missing or unexplained files.
- Full manifest: 42,773 bytes; SHA-256 `1e8c2ac5a35e52ce71a633ffaab8636de0e90eacb3ea6f1323e63d3e01ac04f5`.
- Public bundle: 179 listed files, plus its own manifest; all 179 re-hashed both on the target and by a separate reviewing agent from copied public bytes. Public manifest: 33,143 bytes; SHA-256 `01ff575ae2607ced09bf89a9be54578c7393ef6364121ddf943eed6a24d86a80`.
- Summary: 80,676 bytes; SHA-256 `e6cd27a4e8625bc59c2f382cb447e1c717554295eacef75f122e23e6741327d6`.
- G5 records 132 protected files unchanged and both protected checkouts clean at their original pins. No save errors or unavailable checks.
- Public export preserves the `public/` path prefix used by the original manifest. Raw S, path/repeat tensors, detailed reports and logs remain on the target under `/workspaces/mythos-evidence/base_v01/rope_diag/rope-v11-20261101T051150Z/private/`; they are not published. The full manifest remains alongside them. Operator records are outside the immutable run directory.
- Separate agent review: APPROVE for evidence custody, execution acceptance and bounded conclusions. It verified public hashes, stage order, process identity, controls and G5 records; it did not recompute tensor metrics or independently reread private tensors. AI review is not additional experimental evidence.
- A second result-interpretation review agreed with these limits. That reviewer authored the metrics module and is not independent of its implementation; this review only read saved JSON and did not recompute numerical checks.

## Interpretation and unresolved issues

The five fixed constructions do not match S under the frozen criterion. Changing only the trigonometric evaluation path (T) did not resolve the discrepancy in this environment. The saved T-N maximum is `5.960464477539063e-8`; its compatibility flag compares two constructed candidates, not either one to S. No tested path establishes the buffer's actual creation history. Untested precision combinations, historical versions, devices and conversion/export histories remain open.

Equal N/T/Q maxima do not imply equal tensors. Higher arithmetic precision does not imply greater compatibility with a stored FP32 artifact. Neither the error magnitude nor scalar reproduction proves a GPU, CPU, version, frequency or kernel cause. The diagnostic does not establish whether the difference affects logits or language quality, or whether it is harmless. No threshold was relaxed and no buffer was replaced.

B1 A5 remains BLOCKED; A3 overall, A8–A11 and language quality remain NOT TESTED. Formal Oracle is BLOCKED / NOT_READY and `FORMAL_ACCEPTANCE_READY=False`. D1 and its conclusions are unchanged. PR #24 head remains `4308099bfc90d9398f54a47f9272b6bd4582f7b9`; no PR operation occurred.

## Next single instruction

Read-only audit the pinned official model constructor, checkpoint save/load and evaluation loader to establish whether the official loading path restores `freqs_cis` from the checkpoint or regenerates it, and which creation-history facts are actually documented. Record exact source references and unknowns. Use that evidence to choose the smallest separately specified compatibility check needed to reach a usable baseline. Do not add numerical paths, rerun this diagnostic/B1, substitute buffers, change thresholds, edit upstream, enter B2/D2-A or operate PR #24.
