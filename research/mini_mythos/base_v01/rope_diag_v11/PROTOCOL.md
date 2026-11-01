# MYTHOS-B1-ROPE-DIAG-V1 — protocol v1.1 + C1–C3 + final clarifications (frozen text)

Status: NOT TESTED. This file records the protocol as authorized by the owner in the messages of 2026-11-01
(v1.1 review package, C1–C3 supplement, implementation/execution authorization). It is a condensed, faithful
transcription of the definitions; where a wording difference ever matters, the owner's original messages govern.
It authorizes nothing by itself.

## Fixed basis
- Repository `leotree2020/OpenMythos`; B1 branch `mythos-base-v01-b1`; B1 result checkpoint `d88be474ebb2529c5b095e3732b1f25509f9b824`;
  B1 execution HEAD `f0541330868267af25c4d2d04f549bf3e4d77e2f`; frozen implementation origin `d39eabb0f1ec33230bfdd00337877c647dfa42db`.
- Read-only upstream `sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76`.
- Original B1 run `b1-20261101T021657Z`; model `SandyResearch/parcae-140m@236739ce93ba1afc1b3f172fb4a509f4500d2852`.
- Target: Codespace `bookish-pancake-vwqx7rr9x5w3wxjr`; env `/workspaces/mythos-base-v01-cpu312`; upstream `/workspaces/mythos-parcae-pinned`;
  original evidence `/workspaces/mythos-evidence/base_v01/b1/b1-20261101T021657Z`; new evidence `/workspaces/mythos-evidence/base_v01/rope_diag/<run-id>/`.
- Inputs (no re-download): `downloads/model/pytorch_model.bin` 578361537 B sha256 `ed6eb306464dd0d694e9eacd58f7e06ac3e44b43cb7c5c79dbcb1543059c6621`;
  `downloads/model/config.json` 1741 B sha256 `5c8fc785c2f6dba67d0370ad715034860e3b22bfce850da825c06baa03923c13`.
- Historical comparison value is read from the verified `verify_load.json` (A5 max abs diff `0.00012207025429233909`, threshold `1e-6`, shape `[1,2048,1,64,2]`).

## Purpose and hypotheses
Check input / derivation / layout / reference-construction consistency; determine with which pre-fixed numerical paths the stored difference is compatible;
decide whether a further independent diagnostic is warranted. Not a goal: making B1 pass, judging language quality, showing harmlessness.
H1 input/reference construction inconsistent; H2 numerical-path difference; H3 formula/layout difference; H4 historical version/device/conversion origin.
They may co-exist; none is pre-selected. N is a new helper output, not B1's historical N (B1 stored no N tensor/hash); G2 can only test the historical scalar.

## Boundaries
No full model construction, no strict load, forward, generate, reload, backward, optimizer, GPU, KV cache, new seeds/prompts, re-download, parameter search,
upstream/B1/original-evidence modification, buffer replacement, dependency install/upgrade. `torch.load(weights_only=True, map_location='cpu')`, extract `freqs_cis`,
copy to an independent S. One formal protocol run only; no code change, retry or re-run after observing results.

## G0 derivations (from original config + source branches, not from the target shape)
`expanded=False`; `mup_model_scaling_factor==1`; `randomize_positions_from=None`; D=128 (outer and core-block head dim, core heads per the
`recurrent_num_attention_heads` fallback rule); L=2048; theta=50000; condense_ratio=1; positions 0…2047; frequency indices 0,2,…126; last-axis order [cos,sin];
helper signature `(dim, end, theta, condense_ratio)`. Any failed premise → BLOCKED, no parameter adjustment.

## C2 runtime
Before importing torch: `OMP_NUM_THREADS=MKL_NUM_THREADS=OPENBLAS_NUM_THREADS=RAYON_NUM_THREADS=1`, `TOKENIZERS_PARALLELISM=false`,
`CUDA_VISIBLE_DEVICES=""`, `PYTHONDONTWRITEBYTECODE=1`, Python `-B`, `sys.dont_write_bytecode=True`, pycache redirected into the diagnostic directory.
Required actual state: intra-op 1, inter-op 1, deterministic algorithms on, FP32/CPU defaults (each path still names its dtype), no enabled autocast,
no compile; the helper's own `torch.autocast("cuda", enabled=False)` is allowed. Record before/after and before/after `import parcae_lm`; do not trust return values;
unverifiable/unsatisfied → G0 BLOCKED. Keep warnings/stdout/stderr. Record CPU model/family/model/stepping/flags, CPU capability, torch build config.
Record historical pre-setting values (`env_before`), source-declared values and current actual values separately; missing history = UNKNOWN. Do not call the B1 runner.

## Paths (all tensors: freq `[64]`, phase `[2048,64]`, same element strides, contiguous, same call order; keep `theta ** tensor` form and theta's Python type)
- I32 (control): explicit expansion in FP32 of ω32 = 1/θ^(arange(0,D,2,FP32)/D), t32 = arange(L,FP32)/condense, φ32 = outer(t32,ω32), cos/sin stacked on a new last dim. No helper call, no S input, no patching. Output must equal N bytewise.
- N: frozen native helper.
- T: rebuild t32, ω32, φ32 independently (verify equal to I32); φ32→FP64; FP64 cos/sin; stack; convert to FP32.
- P: rebuild t32, ω32 (verify equal to I32); both →FP64; FP64 outer, cos/sin; stack; →FP32. (No ω64, no direct φ32 promotion.)
- R: ω64 = full frequency expression in FP64; FP64 outer with same positions; FP64 cos/sin; stack; →FP32.
- Q: same ω64 as R; round ω64 to FP32 (single rounding of the full expression; not pow→FP32→reciprocal; not final-only conversion); then native FP32 outer, cos/sin, layout.
- T/P/R pre-conversion FP64 data are secondary numerical evidence only.
Comparisons: S vs N,T,P,R,Q; T−N, P−T, R−P, Q−N, N−R (descriptive). No nine-path set; uncovered mixed paths are reported as not excluded.

## Order and guards
G0 → G1 → G2 → T₁/T₂ → P₁/P₂ → R₁/R₂ → Q₁/Q₂ → metrics and sealing. Structure/finiteness checked as tensors appear.
- G0 identity/source/deps/runtime/derivations → BLOCKED.
- G1 N1, same-process N2, fresh-interpreter N3 (re-imports, calls helper; no S, no other candidates), I32: shape/dtype/canonical bytes equal → else control FAIL.
- G2a record historical vs current environment (UNKNOWN where absent). G2b: original A5 definition (FP32 subtract, abs, max, then Python scalar) must exactly equal the verified historical scalar; else BLOCKED
  "historical A5 max-diff scalar reproduction not established": save S identity, N/I32, process controls, environment, old/new scalars; no T/P/R/Q; no "current-host observation mode".
- G3 path definitions correct; each of T,P,R,Q evaluated twice independently (no reuse/clone/cache of the first output); final FP32 outputs and kept intermediates/pre-conversion data bytewise equal incl. ±0; finiteness; full 262144-element coverage; all prescribed metrics present. Any mismatch → FAIL, stop, no third computation.
- G4 candidate shape/axes/order; position 0 cos=1, sin=0. G5 inputs, upstream, B1 code, original evidence unchanged; new evidence sealed with size/hash.
Bit comparison uses IEEE bit patterns/bytes (distinguish +0/−0). On any stop: only sealing (serialize, re-hash inputs, Git state, manifests, summary/checkpoint, commit); unreached items NOT TESTED.

## C1 metrics (operands fixed)
S32 = file buffer; X32 = candidate's final FP32 output; S64, X64 = exact FP64 extensions. All primary FP64 descriptive metrics use S64, X64 only.
- A5-compatible: FP32 subtract, abs, max (original definition); other summaries may extend those FP32 errors to FP64. Threshold is the Python scalar 1e-6 compared against the float32-as-double value (do not round the threshold to FP32).
- FP64 descriptive: extend S32, X32, then subtract.
- Report per comparison: max, mean, median, p95, p99 (nearest-rank: k=ceil(p·n), 1-based, ascending; median p=0.5), count/fraction > 1e-6, count/fraction of bit-identical components,
  location/frequency/component/both values of the max (ties by index order, first 10 + total), per-position and per-frequency summaries.
- Per cos/sin pair: d_chord = sqrt((c_X−c_S)²+(s_X−s_S)²); Δθ = atan2(c_S·s_X − s_S·c_X, c_S·c_X + s_S·s_X) (direction X−S, wrapped); r_X, r_S, Δr = r_X − r_S; unit-circle residual c²+s²−1 for each.
  Chord includes radial error and is not an angle; zero radius/invalid angle → N/A with reason and count (no zero fill); non-finite input → guard stop; finite zero-radius S is a reported structural finding.
- |Δθ|/|φ32| and |Δθ|/ulp32(φ32) with φ32 from I32; ulp32 = FP64(nextafter_FP32(φ32,+inf)) − FP64(φ32); φ32 = 0 → N/A (no epsilon). N/A as null+reason, not NaN/Inf.
- Scope: full [0,2048) (131072 pairs, 262144 components) primary; [0,112) slice reported alongside, never substituting.
- diagnostic_match(X): full-range A5-compatible max ≤ 1e-6. bitwise_match(X): all elements byte-identical. Reported separately. Candidate mismatch is not a FAIL and does not stop the run.

## Interpretation limits
One candidate matches → compatible with that fixed path only. Several match → insufficient discrimination. Mean-only improvement / local worsening → mixed. None match → UNRESOLVED, untested paths not excluded.
Forbidden claims: frequency construction is the only environment able to produce this magnitude; Q has a single rounding in the whole computation; R−P changes only one pow kernel; ~6e-8 is a verified trig error bound; closer to R means more correct;
G2 failure proves a host cause; 1e-6 equals bitwise identity. Whatever happens: B1 A5 stays BLOCKED; A3 overall and A8–A11 gain no PASS; language quality NOT TESTED; Formal Oracle BLOCKED/NOT_READY; FORMAL_ACCEPTANCE_READY=False.

## Evidence
Each record: Purpose / Environment / Input / Expected / Actual / PASS|FAIL|BLOCKED|NOT TESTED. Full private evidence stays on the target (S, path outputs, repeats, pre-conversion FP64, per-element data, logs); nothing that can reconstruct S or the weights is published.
Two manifests: full evidence (private + committable, size/sha256/class) and Git bundle. Explicit staging only (no `git add -A`). CHECKPOINT.md in this directory for any outcome; normal push, no force, no PR, no PR #24 action.
