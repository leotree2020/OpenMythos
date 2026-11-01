# CPU inference and reload PASS; fixed-prompt language quality FAIL

The original Parcae 140M checkpoint now has a reproducible CPU inference baseline.
Native forward, official generation, same-process repeat and fresh-process reload
all passed. The generated text is heavily repetitive: all 12 first-pass outputs
failed the frozen automatic repetition screen. The combined language-quality gate
is **0/12, FAIL** against the required 9/12. This is not a factual-accuracy score.

| Field | Record |
|---|---|
| Purpose | Verify CPU forward, fixed text generation and original-artifact reload consistency, then apply the frozen separate quality screen. |
| Environment | Designated Codespace; frozen Python 3.12.3, torch 2.11.0+cpu and full B1 dependency inventory; CPU FP32, single-thread, deterministic, SDPA MATH, no cache/autocast/GPU/gradient. |
| Input | Base checkpoint 2fec45b01b7cb09ee7d4e3a3f00426549f0d1eb1; original local config/weights/tokenizer; pinned upstream 69284c13746e849104f738d6d1a347b1f457df76; exact 12 prompts and 32 tokenizer probes. |
| Expected | F0–F5 PASS with exact byte comparisons; 12 first-pass samples, at least 9 simultaneously pass automatic rules and AI-assisted coherence. |
| Actual | F0–F5 PASS; 32,610 engineering check records PASS; complete repeated/reloaded output agreement; 0 automatic passes, 7 coherent labels, 0 joint passes. |
| Status | Engineering PASS. Language-quality FAIL. No further model execution after this result. |

## Measured coverage

- Three full-logit probes (prompts 1,4,7): native versus generation forward exact
  bytes in each worker; fresh-process full-probe bytes also match the first worker.
- Two sequential independent interpreters: PID 97305 and 106440. Each called the
  exact official loader once and compared every original state entry before and
  after inference: 4 × 63 = 252 successful state rows, with tied aliases verified.
- 12 prompts × (first + same-process repeat + fresh-process reload) = 36 complete
  generations, exactly 64 raw new tokens each, depth8, seeds 731001–731012.
- All 2,304 generation-forward outputs were checked for finite CPU FP32 full
  logits. Full-logit hashes repeated exactly. All 1,536 repeated last-position
  vectors were compared using actual bytes, not hash equality alone.
- 32/32 tokenizer probes round-tripped exactly. No prompt truncation/padding or
  special-token insertion. No generated EOS: all quality slices contain 64 tokens.
- 1,093 protected files and prior evidence membership remained unchanged; protected
  Git worktrees remained unchanged during the formal run. F5 PASS includes both
  workers' completed post-inference state checks, not just filesystem hashes.

The run was invoked once, 2026-11-01 06:22:56–06:37:47 UTC (15:22:56–15:37:47 JST).
Planned repetition conditions are not retries. These timings include expensive
diagnostic observations, byte writes and integrity audits; no efficiency claim.

## Quality result and interpretation

All 12 outputs contain a token 4-gram at least three times (maximum counts by ID:
3,5,3,4,3,5,3,3,5,6,6,18). Other automatic rules passed: all decode, contain no
U+FFFD, have 64 effective tokens and no six-identical-token run. The latter does
not prevent repeating multi-token phrases, as the counting example demonstrates.

Root and a delegated text reviewer independently read the fixed first-pass text
and agreed on all 12 coherence labels: 7 true, 5 false. This is AI-assisted review,
not human evaluation or statistical confirmation. Coherent labels do not mean
factual correctness, useful reasoning or accepted quality. Detailed reasons,
factual/code concerns and all original samples are in AI_QUALITY_REVIEW.json and
GENERATIONS.md. No samples were regenerated, cleaned or replaced.

For example, the France prompt begins with "Paris" but then repeats unsupported
superlatives; the Moon prompt begins with "Apollo 11" and loops the Armstrong
sentence; the code prompt produces prose instead of a function; the counting
prompt eventually repeats "thirty". Initial plausible tokens are not enough to
pass the frozen continuation-quality gate.

This result establishes the engineering pipeline. It does not establish that
this checkpoint under the fixed greedy settings is an acceptable text-quality
baseline. It also does not identify the cause of repetition: checkpoint capability,
decoding policy and other factors remain competing explanations. No causal claim
about RoPE or architecture is made, and no settings were changed after results.

## Evidence and versions

- Branch: mythos-base-v01-cpu-inference-v1.
- Implementation A: 3e43c6e674c62a58844c54a0d7642f808c6278c3.
- Execution checkpoint B: 5adfa34883d17e6e468eb48392406635d0c12346.
- Run: inference-v1-20261101T062256Z under
  /workspaces/mythos-evidence/base_v01/cpu_inference/.
- Summary: 267486 bytes, SHA256
  c4f604aa893d4df85141c69336f1bdfe90e5350f1a32d238708b15b36f2a7822.
- FULL_MANIFEST.json: 542970 bytes, SHA256
  920d4c4b2fd8b6cc154f37c95d83b22a108ae5bc36787b28da8bf0cee62cbbd2.
- Public manifest: 40962 bytes, SHA256
  0877693be6d9cc0edb88117436f288a43a3cc712c61e687d65835f21cee1625f.

After terminal execution, the separate standard-library audit re-hashed all 2,526
manifest-listed files, verified all 2,528 actual files (two manifests excluded
from self-reference), and independently re-compared 1,536 last-logit raw pairs
and 9 full-probe raw pairs. Token suffixes, EOS slicing and automatic rule counts
were independently recomputed from saved IDs/text. No discrepancy was found.
Finite logits and tokenizer decoding are execution observations; the audit did
not re-run logits or tokenization. Full original artifacts and raw logits remain
private on the target, covered by FULL_MANIFEST. All 204 listed public files plus
the public manifest, full manifest and operator evidence are committed under
evidence/. The 217-file export was transferred and whole-package hash verified.

## Preserved limits and next action

Historical B1 A5 remains BLOCKED at 1e-6; old B1 A3 overall/A8–A11 are not relabeled.
Historical RoPE construction origin remains UNRESOLVED. This experiment reused
the original stored buffer through the official loader; no buffer replacement or
threshold relaxation occurred. Training, optimizer/interrupt recovery, saving a
new model and reloading that newly saved model are NOT TESTED. Fresh-process reload
here reads the same original artifact. Formal Oracle remains BLOCKED/NOT_READY;
FORMAL_ACCEPTANCE_READY=False. No B1 rerun, B2, D2-A, GPU or PR #24 action.

Next unique instruction: using the saved 12 outputs and pinned generation source,
plan a minimal separate decoding-quality control to distinguish checkpoint/greedy
decoding explanations; review before any new execution. Do not rerun this frozen
experiment or enter B2/D2-A automatically. This stage is stopped after checkpoint.
