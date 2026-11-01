# Decode control: final static review

Date: 2026-11-01. Verdict: **APPROVE for source/protocol freeze and the authorized
single formal execution.** This verdict is not an engineering-run PASS or a
language-quality PASS. New numerical and quality results remain **NOT TESTED**.

Reviewer role: `/root/b1_gate_review`, separate from the agents implementing the
coordinator/worker, generation module and quality aggregator. This is an internal
AI static cross-review, not a Claude/Grok review or independent human validation.

| Field | Record |
|---|---|
| Purpose | Check the frozen decoding-control implementation against the approved boundaries, acceptance rules, pinned official interfaces and evidence-preservation requirements before any model execution. |
| Environment | Local read-only text inspection; standard-library AST parsing and SHA-256 of source/documents. No torch import, model/tokenizer load, generated-token experiment or numerical fixture execution by this reviewer. |
| Input | The eight reviewed files and exact byte hashes listed below; the pinned official-source observations in SOURCE_REVIEW.md; previously reviewed frozen state/tokenizer utilities. |
| Expected | Correct D0-D4 status propagation, a complete G/S/P matrix, exact historical G bridge, separate model/sampler RNG streams, explicit quality rules, immutable upstream/history and honest failure/unknown states. |
| Actual | The identified blocking stage-name and first-error preservation defects were corrected before freeze. The final interfaces, ordering, hash/byte checks, RNG controls, private/public evidence boundaries and quality aggregation agree with the protocol. All four new Python files parsed as AST without importing or executing them. |
| Status | PASS for this static review; APPROVE. No remaining blocking issue identified within the reviewed scope. |

## Reviewed versions

Hashes are SHA-256 of the actual local bytes read. This review does not hash
itself. Implementation commit A and execution checkpoint B are assigned by the
subsequent freeze process; no commit identity is inferred here.

| File | Bytes | SHA-256 |
|---|---:|---|
| run_decode_control.py | 16203 | 83264ce219514972378274dfcb2ca030a76b894f40955c47224329006c51674b |
| worker.py | 10303 | e068e39a434c289cbd59429ce366db46df19bbe82949f84038d83a82fa3e70cd |
| generation_checks.py | 30578 | 963f66894af539d17ea5a8c14463be90f00f46652a3a58c20a475f81814732bf |
| quality_summary.py | 9532 | 95226a18137109f0fea2e00722b189c8078af98776afda694b3f5026145d725c |
| PROTOCOL.md | 11877 | 5f6689e156876811fa5dc6d23143bf8c2c83af1af64b471391b985d381d7f481 |
| QUALITY_RUBRIC.md | 10941 | ee5a215f884757c30d367963e0aa8438f32e1dd8f76d8d3cb3e6f2ac6c2a18a6 |
| SOURCE_REVIEW.md | 12972 | ab02cd7673570fa25a2d039713f9ab9143ae199921c9f15ecbda828ff391710c |
| README_USAGE.md | 948 | 850f9337e0f83e1ec6c1e87565bbeaccce10ac00548648149df362aa17dc0a8d |

The reused utilities are pinned separately by the coordinator:
`load_integrity_v1/state_checks.py` at
`2f1238e8b4b17ede1cc56b6ca40ae57a89f1acd797ac881bbebb892790381ed4`
and `cpu_inference_v1/tokenizer_checks.py` at
`28437883baa50adc4996b578d55bbf2daf907d6a6c53e5e0573f18705721d8ae`.
Their prior experimental runners are not called.

## Findings corrected before freeze

1. **Stage dictionary names.** Initial coordinator/worker dictionaries retained
   F-stage names from the prior experiment. They now initialize only D0-D4 and
   D1-D3 respectively. The worker's actual stop phase propagates to the
   coordinator, preserving completed earlier gates.
2. **First failure and cleanup.** The generation module originally caught only
   Exception and could replace a first failure with a trace/RNG/check-stream
   cleanup or terminal-save exception. The final module catches BaseException,
   records the primary exception separately from condition cleanup errors,
   closes its check stream before terminal serialization and propagates a
   GenerationStop with the active D2/D3 phase. Terminal-save errors are attached
   to the original failure rather than turning a known numerical FAIL into an
   unrelated phase or a PASS.
3. **Probability normalization.** The protocol now explicitly freezes the
   `abs(sum-1)<=1e-6` check on final FP32 probabilities expanded to FP64 for the
   sum. This is a new probability-distribution guard, not a change to old A5.
4. **Resource interpretation.** The 2.5 GiB MemAvailable floor is explicitly a
   new single-worker resource estimate, with possible transient loader copies;
   it is not a guaranteed peak bound or numerical acceptance relaxation. An OOM
   or resource failure is BLOCKED and does not authorize a retry.

## Controls checked statically

- The coordinator accepts only the designated Codespace/interpreter, clean pinned
  checkouts, the new isolated branch and source bytes at implementation A. It
  verifies the pinned manifests and file bytes for the B1, RoPE, load-integrity
  and prior inference run trees, then protects their complete file membership,
  tracked upstream bytes and required research inputs through final sealing.
- A single sequential worker has a fixed 5400-second budget. The official
  evaluation loader is called once with the local directory, CPU and dtype=None;
  attempts and successful return are recorded separately. All 63 state entries
  and the tied embedding/head identity are checked before and after successful
  generation. No upstream source, model configuration, state initialization or
  stored RoPE buffer is patched.
- G runs first on all 12 prompts. Each of its 64 steps must match the prior
  inference pass's prefix/metadata/full-logit hash and retained last-logit actual
  bytes, followed by exact token/text/EOS/automatic-description equality. No S/P
  generation starts before all twelve G bridges pass.
- S and P each have three fixed 12-prompt panels, yielding 84 total continuations
  and exactly 5376 official forwards. Each call uses the complete growing prefix,
  depth 8, CPU FP32, no gradient and no cache. The unchanged official forward is
  called directly; the custom upstream generator's ignored generator keyword
  is not used as an isolation mechanism.
- The model default RNG is seeded once per continuation. Sampling uses a
  dedicated CPU Generator passed directly to multinomial. Each sampled step
  checks actual default-RNG bytes against the current G control, verifies that
  forward does not consume the sampler RNG, and verifies that selection and
  observation do not consume model RNG. Sampling starts from the same first-step
  logits as G. After prefixes diverge, logits are not required to remain equal.
- P applies temperature, descending sort, cumulative-probability mask, the
  official right shift retaining the first token, mask scattering, then softmax
  and sampling. Masking operates on a separate tensor. Raw logits must be finite;
  only explicitly masked negative infinities are accepted. Sampling distribution
  checks precede the draw, and source last-logit bytes are checked unchanged.
- Every planned output is retained, including tokens after EOS. Automatic quality
  failures do not stop or select the numerical matrix. Semantic review occurs
  afterward. The pure quality aggregator requires complete unique row identities,
  Boolean labels and both reviewers to agree on coherence. S/P need at least
  9/12 joint passes in every panel, without pooling or best-seed selection. Its
  assessment-complete PASS is explicitly distinct from policy quality PASS.
- Engineering FAIL/BLOCKED stops subsequent model calculations. Standard-library
  audits and best-effort evidence preservation may continue. D4 separates file
  invariance from a completed worker post-generation state check; an otherwise
  passing file audit does not upgrade an early-stopped run to full D4 PASS.
  The coordinator prepares the terminal summary in memory, writes the manifests,
  then writes that summary last. Operator records remain necessary for abrupt
  process/host failure or storage failures that prevent in-process sealing.
- Raw logits and G RNG bytes remain on the target; public records contain
  metadata, hashes, check results, token IDs and generated text. No weights,
  tokenizer binary or virtual environment is published by this experiment.

## Review limits and independence

The reviewer authored SOURCE_REVIEW.md. Its source findings are therefore not
independently validated merely by this reviewer's later rereading. The root
reviewer separately read the pinned source facts/report; the project must retain
that attribution rather than counting the same agent twice. The reviewer did not
author or edit the four implementation/aggregation Python files during this
review. Only this static-review record is written by this review step.

AST parsing and source inspection cannot establish that the model run will pass,
that available memory is sufficient at peak, that every failure can be sealed
under host termination/disk failure, or that sampled outputs will be coherent.
The actual run must supply its own gate records, full manifests and read-only
result audit. This reviewer has not run the model, tokenizer, numerical probes,
sampling experiments or development fixture tests for this stage. Other agents'
separately recorded development checks are not claimed as this reviewer's runs.

The later AI quality packets hide policy/panel/seed/automatic outcomes from the
reviewers. This is metadata blinding, not an unseen-task evaluation: these twelve
prompts and prior G texts have already been examined in the project. Two AI
judgments are not independent human ground truth. Preserve both labels and
reasons, disagreements and the mapping; do not negotiate a higher score after
seeing automatic outcomes.

The isolated sampler changes the full sampled sequence relative to upstream's
shared-RNG generator. P also changes temperature and top-p together. Conclusions
are limited to these fixed policies on viewed development prompts. New sampled
fresh-process replay, generalization, factual reliability, training/resume,
architecture improvement and hardware efficiency are not established here.
Historical B1 A5 and Formal Oracle remain blocked; no B1 rerun, B2, D2-A or PR #24
operation follows from this approval.
