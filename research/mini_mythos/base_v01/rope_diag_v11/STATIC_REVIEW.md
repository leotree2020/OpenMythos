# Static review — MYTHOS-B1-ROPE-DIAG-V1

Verdict: APPROVE for source freezing only. Runtime validation and G0–G5 remain NOT TESTED at this review. No Torch import, fixture, candidate calculation or model execution was used to obtain this verdict.

## Reviewed source identities

| Source | SHA-256 | Reviewer |
|---|---|---|
| paths.py | 56af3ecd5869d07fff32b0d4c93da85d40cbe28c90808003d2e889d7ef03e85b | separate metrics author; root integration review |
| metrics.py | 3844858c3366ba7b634dceb54150eddb734828148e4f624130284924b4de206e | separate paths author; root integration review |
| run_rope_diag.py | 0a837fc8f5099ca061bab8268495074f3f8e5091ed83c171342c3a842249ca62 | b1_gate_review agent, separate from root author |

All are AI-assisted static reviews, not independent empirical confirmation. The line map and target AST results are in implementation_evidence/STATIC_AUDIT.json; hashes there must match these reviewed bytes.

## Protocol mapping

| Requirement | Implementation location / static finding |
|---|---|
| Exclusive single formal claim before Torch | runner main: experiment evidence root mkdir(exist_ok=False), CLAIM.json, then Run/experiment |
| G0 exact source, original files, complete metadata | runner preflight; frozen implementation Git blobs, pinned upstream hashes, original B1 manifest plus summary and lock, full installed distributions |
| Source-derived D/L/theta/layout | runner derive_parameters; never reads S to select a parameter |
| C2 before/after runtime/import actual state | initialize_runtime/runtime_state; CPU FP32, 1/1 threads, deterministic, both autocasts disabled, source origins, private warning/stdout/stderr |
| Native N | direct frozen precompute_freqs_cis(dim,end,theta,condense_ratio) |
| G1 controls / fresh N3 | experiment/native_child; same frozen interpreter -B, new PID, no S or other candidates in child; IEEE bytes incl signed zero |
| I32 / five paths / Q rounding | paths.build_path; exact source expression 1.0/(theta**...), outer.float(), [None,:,None,:] and stack dim=4 |
| C3 independent repetitions | T1/T2 then P1/P2 then R1/R2 then Q1/Q2; fresh capture dictionaries; compare every kept intermediate and final tensor |
| T/P independent reconstruction | freshly calculated t32/omega32 and T phi32 compared against already-validated I32 |
| G2 historical scalar and immediate stop | preflight checks historical copies; experiment uses original FP32 difference then scalar exact comparison; no T/P/R/Q before successful G2 |
| C1 final-FP32 operands | metrics._scope promotes final FP32 to FP64 before descriptive subtraction; pre-cast FP64 tensors remain secondary private evidence |
| Threshold / nearest rank | FP32 A5 errors promoted before 1e-6 comparison; integer ceil rank for median/p95/p99 |
| Pair geometry / N/A | metrics._geometry and masked summaries; X-minus-reference angle; chord/radius/residual distinct; zero phase/zero radii produce explicit null/reasons/counts |
| Coverage | full 2048 positions primary and 112 secondary, per-position/per-frequency and worst ties private; public is aggregates only |
| Stop / partial tensors / exceptions | build_and_preserve and saved native output before validation; explicit numeric FAIL, unclassified/infrastructure BLOCKED; outer finally seals without new diagnostics |
| G5 no false PASS on partial baseline | complete protection flag; unknown audit BLOCKED vs confirmed changed bytes FAIL; original stop reason retained |
| Final summary / manifests | summary bytes and hash prepared in memory, both manifests written first, final summary last; emergency file/terminal fallback on failure |
| No protected mutations | no B1 runner/model construction/dependency installer/optimizer/GPU/download/writeback call path |

## Static derivation from pinned upstream

- modules/blocks.py: TransformerPreNormBlock.expanded=False.
- models/config.py: outer head_size uses n_embd // num_attention_heads; require mup_model_scaling_factor=1 so later scaling cannot alter the premise.
- models/parcae/config.py: recurrent_num_attention_heads=None falls back to num_attention_heads; recurrent embedding dimension divided by that count gives the independent core dimension.
- models/parcae/parcae.py: _precompute_freqs_cis uses expanded-dependent dimension, configured block_size unless randomize_positions_from is set, and rope_settings.
- Original hash-identified config: outer 768/6=128; core 768/6=128; block_size=2048; int theta=50000; int ratio=1; randomize_positions_from=None.
- modules/utils.py: native reciprocal, FP32 arange/outer.float, trig and stack order retained; no rewriting or patching the upstream helper.
- B1 run_base.py actually sets OPENBLAS/RAYON/TOKENIZERS values as recorded; env_before is earlier and not proof those values were used during execution.

## Resolved findings before freezing

Earlier drafts could lose failed candidate tensors, overstate G5 after partial preflight, classify infrastructure errors as numerical failures, or publish summary PASS before manifests. These were corrected before any numerical execution and re-reviewed. Native outputs and stored S layout are now preserved/checked at arrival. Historical CPU source_preflight and both A5 scalar copies are protected/read. No result-dependent adjustment was made.

## Acceptance record

Purpose: freeze a faithful implementation of the already-approved diagnostic.
Environment: standard-library text/AST review; final source installed and parsed on the named Codespace; no numerical environment exercised.
Input: adac90ae repository recovery, frozen protocol/upstream/B1 evidence and the reviewed source hashes above.
Expected: complete protocol-to-code mapping, no unresolved static blockers, no execution or protected modification before freezing.
Actual: separate path/metrics reviews APPROVE; runner reviewer APPROVE after recorded corrections; AST parsing performed without importing reviewed modules. Target AST/hash output is recorded separately before commit.
Status: PASS for static source review only; all empirical/numerical claims NOT TESTED.

No fixture suite was run. A first-run program defect remains possible; it must stop and be recorded under the frozen protocol rather than be repaired and rerun.
