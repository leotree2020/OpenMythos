# MYTHOS-CPU-INFERENCE-V1

Purpose: establish CPU forward correctness, fixed-prompt generation, same-process
repeatability and fresh-process reload consistency for the original Parcae 140M
artifact. This is a new isolated experiment based on checkpoint
`2fec45b01b7cb09ee7d4e3a3f00426549f0d1eb1`, not a rerun or amended acceptance of B1.

## Authorization and boundaries

The owner explicitly authorized planning, implementation, review, freezing and
one formal CPU execution in the existing Codespace. No further permission or
Claude handoff is needed. No upstream changes, weight/buffer replacement, config
overrides, tolerance changes, B1 runner invocation, training/backprop/optimizer,
GPU, cache, B2, D2-A, PR creation or PR #24 mutation. No download or package change.
Synced project sources and prior experiments are read-only. A failure stops all
subsequent model computations; only evidence preservation and read-only audits
may continue. No repair/retry after formal results. Pre-freeze AST/static review
is development work, not numerical evidence. No numerical fixture run is required.

## Frozen inputs and environment

- Target `bookish-pancake-vwqx7rr9x5w3wxjr` only.
- Reused checkout `/workspaces/mythos-base-v01-rope-diag-v11`, new branch
  `mythos-base-v01-cpu-inference-v1`, additions only under
  `research/mini_mythos/base_v01/cpu_inference_v1/`.
- Upstream `sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76`,
  `/workspaces/mythos-parcae-pinned`, read-only.
- Frozen B1 checkout `d88be474ebb2529c5b095e3732b1f25509f9b824`, B1 run
  `/workspaces/mythos-evidence/base_v01/b1/b1-20261101T021657Z`.
- Local original `pytorch_model.bin`: 578361537 bytes,
  SHA256 `ed6eb306464dd0d694e9eacd58f7e06ac3e44b43cb7c5c79dbcb1543059c6621`.
- `config.json`: 1741 bytes,
  `5c8fc785c2f6dba67d0370ad715034860e3b22bfce850da825c06baa03923c13`.
- `tokenizer.json`: 2326980 bytes,
  `e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77`.
- Existing `prompts_v1.json` at base commit: 12 exact strings, IDs 1–12;
  SHA256 `f0c36e5e8c2f65a47f72ed81cdef20d464f750cc228873780aa546876befb8ca`.
  Existing `tokenizer_probes_v1.json`: 32 strings, SHA256
  `0fc0681c4b9f8baa5012c076e5e457125d2622f6402eaccbe0a6c29efda54d15`.
  Read these JSON inputs; never reconstruct text from prose. Prompt 7 includes
  real newlines and four spaces. The old experiment field is provenance only.
- Interpreter `/workspaces/mythos-base-v01-cpu312/bin/python`: Python 3.12.3,
  torch 2.11.0+cpu, numpy 1.26.4, tokenizers 0.23.2. Full distribution inventory
  must equal the original env_check record. Lock SHA256
  `84440f8945041ed314c29b205c5244e074116ede023d5aae0b11b633b4d6a51e`.
- CPU FP32, batch=1, no padding, no gradient, eval, no checkpointing/monitoring.
  Original `attn_impl=flash` is retained; its CPU path uses SDPA. Force official
  `sdpa_kernel(SDPBackend.MATH)` context around all acceptance forward/generation
  calls. This is not testing CUDA/FA3 and is not a performance benchmark.
- Before torch import: OMP/MKL/OPENBLAS/RAYON threads=1,
  TOKENIZERS_PARALLELISM=false, CUDA_VISIBLE_DEVICES="", PYTHONDONTWRITEBYTECODE=1,
  HF_HUB_OFFLINE=1, TRANSFORMERS_OFFLINE=1; `-B`, private pycache redirect.
  Actual intra/inter-op=1, deterministic algorithms=True, default FP32/CPU,
  CPU/CUDA autocast=False, CUDA not initialized. Internal disabled autocast
  contexts are allowed. Save actual runtime before/after upstream import, CPU
  model/flags, torch build and package origins. Do not claim identical historical
  process state merely because the settings agree.
- At least 2 GiB free disk and 3 GiB MemAvailable. One sequential worker at a time;
  each has a frozen 3600-second budget. Timeout is BLOCKED; no retry.

## Loading and RNG

Use the exact pinned file `receval/models/parcae.py` via isolated module import,
then `ModelingParcae.from_pretrained(local_model_dir, device='cpu', dtype=None)`.
No convenience loader, field filtering, class substitution or regeneration of
the stored `freqs_cis`. One model construction/load per worker; constructor seed 0.
Independently read the original state dictionary and invoke the already frozen
`load_integrity_v1/state_checks.py` comparison utility (SHA256
`2f1238e8b4b17ede1cc56b6ca40ae57a89f1acd797ac881bbebb892790381ed4`).
This utility is reused, not its old runner; no old experiment is invoked.
All 63 state entries must match original bytes before and after that worker's
inference, with shape/dtype/finite/coverage/alias checks. No state mutation accepted.

Original state_init=like-init draws random h0 even in eval. Set CPU seed
`731000 + prompt_id` immediately before each complete forward or complete
64-token generation call, after model construction. Never reset inside a
generation's 64 steps. Native explicit `num_steps_pair=[0,8]` avoids the stochastic
depth sampler; the outer no_grad means even the named with-grad loop has no graph.
Official generation uses explicit `num_steps=8`. No alternate seed or depth.

## Gates and expected results

Every check records Purpose, Environment, Input, Expected, Actual and Status.
Exit 0 alone never establishes a gate. Zero numerical tolerance is predeclared
for the new byte-equality gates; this does not change or reinterpret old A5.

| Gate | Input and purpose | Expected / acceptance |
|---|---|---|
| F0 | target, Git, frozen source, files, resources | Correct Codespace/interpreter; clean isolated/B1/upstream trees; pinned hashes; all original B1/RoPE/load evidence enumerated and verified; enough resources. Missing/changed baseline is BLOCKED. |
| F1 | official load and tokenizer | Exact evaluation model; all 63 original state entries fully byte-identical; BPE vocabulary exactly IDs 0–32767; 0=bos,1=eos,2=pad; 32/32 exact text round trips; 12 exact prompt encodings nonempty and <=48 tokens, no truncation/padding/special insertion. |
| F2 | prompt 1,4,7 native and generation forward | Same inputs/seed/depth; logits CPU FP32 shape [1,L,32768], finite, no grad; entire native vs generation logits byte-identical, including signed zero. Save full native logits privately for fresh-process direct byte comparison. |
| F3 | 12 prompts in ID order; two planned same-process passes | Each official generate returns exact prompt prefix plus 64 IDs in range. 64 observed full-prefix calls, lengths L…L+63, depth8, cache=None throughout; all full logits finite. Second pass raw IDs, text, EOS, full-logit hashes and last-position raw logits match first pass exactly. |
| F4 | independent interpreter loading same original artifact | Repeat F1/F2 and one full 12-prompt pass. Distinct PID/start record; compare to first worker's first pass. Three full-probe tensors and all 768 last-position vectors compare actual bytes; full-logit hashes, generated IDs, texts, EOS also exact. |
| F5 | read-only final integrity audit | All protected files, directory membership and checkout states unchanged; complete evidence/manifest; all parameters/buffers still original after successful worker calculations. |

Tokenization uses add_special_tokens=False; decoding uses skip_special_tokens=False.
The final filesystem audit always runs, including after an earlier stop. Its
file_integrity_status is reported separately. Aggregate F5 cannot be PASS unless
both workers completed their post-inference state checks; after an early stop
and an otherwise passing file audit, aggregate F5 remains NOT TESTED.
All prompts run separately with attention_mask=None; upstream mask handling is
not used for padding. Prompt length+64 must fit original 2048 context/buffer.
All decode/token identities are preserved; do not clean or manually repair text.

Official generation arguments: max_new_tokens=64, num_steps=8, do_sample=False,
temperature=1.0, top_k=None, top_p=None, use_cache=False. The pinned generator has
no EOS stopping; retain all 64 raw new IDs even after EOS. No KV cache or sampling.

### Transparent observation

Temporarily wrap this instance's bound forward_for_generation method only to
observe official generate calls. Invoke original exactly once with unchanged
arguments and return the same output object. Do not change inputs/outputs,
configuration or state. Save call index, prefix length/hash, depth/cache state,
shape/dtype, full-logit finite check and C-order bytes SHA256. Persist the complete
last-position FP32 vector privately for actual byte comparisons; hashing covers
every component of the full tensor but only last-position vectors are retained
for all generation steps. The three fixed forward probes retain full tensors.
The observation section must leave CPU RNG state unchanged; no seed reset inside
the wrapper. Restore the prior instance attribute state in finally, including
absence if originally inherited. No additional forward for observation. Overhead
is part of diagnostics; timings are not hardware efficiency evidence.

### Language quality: separate final screen

Only the first worker's first pass, exactly 12 samples, is scored. Repeated runs
are consistency controls, not additional samples. Quality uses tokens strictly
before the first raw EOS ID1 (or all64 if none). Automatic rules: >=16 tokens;
any contiguous 4-gram appears fewer than3 times; longest identical-token run<6;
decode succeeds; no U+FFFD. Preserve failed outputs and full64 text as well.
Individual automatic rule failures are descriptive measurements, not intermediate
engineering gates. The predeclared final quality gate is assessed only after
all consistency evidence, preventing quality from selecting which prompts run.

An AI-assisted semantic review marks each first-pass effective continuation
coherent only if understandable, connected to its prompt and locally coherent
language/code structure, without meaningless word sequences. Record a reason for
each. Do not require a complete answer, factual correctness or executable code
for this coherence label; factual/code errors are explicitly reported separately.
Quality PASS requires >=9/12 samples satisfying BOTH automatic and coherence
rules. Otherwise quality FAIL; no regeneration or repair. This is exploratory
AI-assisted screening, not independent human evaluation or capability proof.
Engineering PASS can coexist with quality FAIL. If engineering fails first,
quality acceptance remains NOT TESTED and partial text is evidence only.

## Stops, preservation and interpretation

Missing access/environment/input identity/resource or unexpected runtime exception
=> BLOCKED. Observed finite/shape/state/coverage/determinism violation => FAIL.
Save first failing observation and traceback/partial evidence, then no further
forward, prompt or worker. Later gates remain NOT TESTED. Following a stop, only
stdlib filesystem hashes, Git reads, evidence packaging and checkpoint are allowed.
Existing contexts and the temporary method wrapper may unwind to restore their
prior state; no additional model evaluation or RNG measurement follows a stop.
Never retry or patch after observing formal results. Candidate text quality is
not inferred from exit status. First/repeat/reload are planned conditions within
one invocation, not failure retries.

Evidence: new unique `inference-v1-UTC` run directory under
`/workspaces/mythos-evidence/base_v01/cpu_inference`. All writes exclusive; no
existing run reuse. Raw probe/last-logit bytes remain private on target; public
JSON includes all measured metadata, hashes, check rows and generated texts.
All public records and manifests are committed. No weights/tokenizer binaries
or virtual environment in Git. Full manifest covers private/public bytes; its
own hash and export verification are recorded in operator checkpoint evidence.
Stdout/stderr and warnings are preserved unfiltered. Failure to seal evidence
is BLOCKED, never a silent PASS.
If storage fails before a run directory/terminal record can be created, the
operator launch/completion/stdout/stderr records are the remaining evidence;
absence of terminal summary is BLOCKED, never permission to retry.

Freeze sequence: commit A includes protocol/source/static review; commit B pins
A in the execution checkpoint; run once from clean B. Do not mutate source during
execution. Read-only result review, quality rubric assessment and manifest audit
produce result commit C and push normally; do not merge or touch PR #24.

This phase tests reloading the SAME original artifact, not saving a new checkpoint,
training recovery, generalization, architecture improvement or hardware efficiency.
Original B1 A5 remains BLOCKED at 1e-6; earlier RoPE origin remains UNRESOLVED;
Formal Oracle BLOCKED/NOT_READY and FORMAL_ACCEPTANCE_READY=False. Stop after
result checkpoint. The next unique instruction is determined by actual outcome,
never automatic entry to B2 or D2-A.
