# Mini-Mythos — Public-Evidence Reconstruction Roadmap

## Project objective (corrected 2026-10-16)

**Primary objective:** Reverse-engineer, as far as public evidence and authorized
black-box observations permit, a functionally useful independent reconstruction
of Anthropic Claude Mythos **starting from the open-source kyegomez/OpenMythos
codebase**. Train weights, measure model quality on real heldout text/tasks,
and evaluate how closely observable behavior approaches a named Mythos target.

This is **not** primarily a program to optimize ACT, maximize synthetic-loss
scores, or prove that the community's guessed recurrent architecture is real.

## Evidence and honesty rules

1. **Verified public facts**: attributable to official Anthropic docs, model
   reports, or published primary research; keep version/date and URL.
2. **Community implementation/hypothesis**: design in
   `kyegomez/OpenMythos` (Prelude/Recurrent/Coda, ACT, injection, MLA/GQA,
   MoE, per-depth LoRA), **not proof that Claude Mythos uses that design**.
3. **Measured reconstruction behavior**: checkpoints, real evaluation sets,
   training logs, computed metrics and exact code/environment provenance.
4. **Unknown**: undisclosed proprietary weight values, training mix,
   detailed target topology, training recipe; don't invent these.

A publicly accessible model interface (when authorized and available) can support
black-box behavioral comparisons, **not exact architecture or weight recovery**.
Use published and lawfully acquired materials only. Do not imply Anthropic
affiliation or claim model/weight equivalence.

## Where the project stands

- Base repository: `leotree2020/OpenMythos` fork,
  `mini-mythos-research` research branch.
- Implemented upstream: candidate recurrent-depth architecture, token generation,
  GQA/MLA, MoE, ACT and training entry points. Upstream code needs independent
  engineering verification before large GPU runs.
- ACT-001 through ACT-004: CPU diagnostics and toy synthetic experiments; these
  do **not** establish actual Mythos architecture fidelity or language-model ability.
- R0 Gate A (2026-10-16): 67/67 tests PASS in Codespaces; a 6-token cached
  prefix plus 2-token chunk fails under unchanged upstream GQA/MLA, while
  an isolated research-only mask correction PASSes with max absolute logit
  difference 2.9802322387695312e-08 for each attention mode. See
  [R0 Gate A](R0_GATE_A_RESULT.md). GPU/FSDP remains unverified.
- R1 Gate A (2026-10-16): user ran 60-step GQA depth-2 byte-tokenized
  WikiText-2 pilot; heldout NLL 5.51615 -> 3.37635, PPL 248.675 ->
  29.264 (1024 validation byte targets). The local checkpoint was saved;
  generated output was 24 spaces, so no demonstrated coherent language ability.
  See [R1 Gate A](R1_GATE_A_RESULT.md).
- R1 Gate B rechecked (2026-10-16): 82/82 unit tests PASS. The 60-step
  model heldout PPL 29.264 was worse than train-fitted Unigram 26.919 and
  Bigram 12.597; argmax always predicted spaces. Reversing history order
  changed next-byte predicted probability TV by just 2.17e-5. See
  [R1 Gate B](R1_GATE_B_RESULT.md).
- R1 Gate C at 200 steps (2026-10-16): checkpoint resume succeeded;
  heldout PPL improved to 25.167, history-order TV 0.002449; greedy output
  remains all spaces. **86/86 tests PASS**. Exact SGD offset replays matched
  checkpoint RNG states at steps 60 and 200, with respectively 15360/51200
  observed supervised targets. Same-exposure unigram/bigram PPL at 60 were
  27.513/19.158 versus model 29.264; at 200 were 26.951/14.812 versus model
  25.167. The 200-step model beats the matched unigram but not the matched
  bigram. See [R1 Gate C](R1_GATE_C_RESULT.md).
- R1 Gate D (verified 2026-10-16): 200→600 step resume succeeded. All
  three checkpoints passed the comparator's configuration, data fingerprint,
  resume-step and RNG replay checks. Step-600 tiny GQA heldout PPL=11.219663
  on 1024 byte targets, beating same-exposure Add-1 Bigram PPL=13.021447
  and full-corpus Add-1 Bigram PPL=12.597172. Argmax-space prediction fell
  from 100% to 32.5% and history-order TV rose to 0.214781; greedy still
  loops 'the the the' and reversed-history last-target delta NLL was -0.03650.
  This is evidence of limited byte-level predictive learning, not fluent
  language or the proprietary Mythos architecture. See
  [Gate D result](R1_GATE_D_RESULT.md).
- R1 Gate E (verified 2026-10-16): 97/97 tests PASS; fixed 600-step
  checkpoint on 128 validation windows (8192 byte targets): model PPL 11.648557,
  same-exposure Add-1 Bigram 13.417210, full-corpus Bigram 12.977333.
  Model lower NLL in 121/128 windows; paired bigram-minus-model +0.141356
  nats/byte with exploratory window bootstrap [0.125281, 0.157897].
  RNG replay and test window counts verified. Validation was reused for model
  decisions; not an untouched test. See [Gate E result](R1_GATE_E_RESULT.md).
- R1 Gate F (VERIFIED 2026-10-16): 106/106 unit tests PASS. On the
  separate official WikiText-2 *test* split, revision pinned at
  b08601e04326c79dfdd32d625aee71d232d685c3 before download,
  step-600 model PPL=10.852968 vs same SGD-exposure Add-1 Bigram
  PPL=12.790071 and whole-train-prefix Bigram PPL=12.404059 across
  256 windows / 16384 byte targets. Model lower NLL in 253/256 windows;
  mean paired NLL improvement +0.164231 nats/byte, exploratory window
  bootstrap [0.154229,0.174337]. No training/test leakage by protocol;
  one tiny seed/limited byte-level claim. See [Gate F result](R1_GATE_F_RESULT.md).
- R2 Gate A (verified 2026-10-16): 110/110 tests PASS, PyTorch
  2.14.1+cu130 but no CUDA device; 13.06 GiB free disk. Production training
  still has DATA_CURSOR, TOKENIZER_REVISION, CHECKPOINT_TRUST, HELDOUT_EVAL,
  CACHE_CHUNK static GAP flags; BF16/ACT/MoE require runtime review.
  See [R2 Gate A](R2_GATE_A_ENVIRONMENT.md).
- R2 Gate B (VERIFIED 2026-10-16): 114/114 tests PASS. Immutable PR #27
  commit 2954bc275ffb8ad5c60f74f7299a9ad9e531d3e4 audit found 14/14
  selected source patterns; no GPU run. Tiny original GQA/MLA RoPE buffers
  `freqs_cis`/`freqs_cis_mla` both started as complex64 (imaginary max ~1)
  and LOST imaginary phase when the whole model was cast to BF16, as PR27
  training code requests. This is a confirmed CPU numerical correctness bug,
  not proof of GPU performance or other pattern flags causing runtime errors.
  See [R2 Gate B evidence](R2_GATE_B_RESULT.md) and
  [PR27 review](R2_PR27_SOURCE_REVIEW.md).
- R2 Gate C (VERIFIED 2026-10-16): 120/120 tests PASS. CPU tiny GQA/MLA
  BF16 autocast retained FP32 master parameters and both Complex64 RoPE
  buffers bit-identically; finite losses 4.521300 / 4.605480 and gradient
  norms 1.924440 / 1.942811; FP32-vs-BF16 logits max abs delta
  0.00234181 / 0.00261885. Original upstream not patched; no real GPU run,
  no optimizer update or long-training performance validation.
  See [R2 Gate C](R2_GATE_C_RESULT.md).
- R2 Gate D (VERIFIED 2026-10-16): 130/130 tests PASS; pinned PR27 GPT2
  tokenizer to HF immutable revision 607a30d783dfa663caf39e06633721c8d4cfcd7e
  and required 50257 embedding rows. Complete token-to-ID SHA256 is
  56547338e1f0301492f97c9ec86f9ff477d96513336d9497331e1f58f4afd911;
  backend SHA256 is 11e818f948f43497f364722def50c13f419158554961ee4bb095fbd3350895c3.
  Frozen contract SHA256 d8c2780bf00fc7a224bfca89725ad9cc0522c48aa67cf796599ae6a04be3d3c9
  reloaded OFFLINE and matched. Original PR27 checkpoint/eval is not patched.
  See [Gate D result](R2_GATE_D_RESULT.md).
- R2 Gate E (VERIFIED 2026-10-16): 140/140 tests PASS. Real offline
  pinned GPT2 tokenizer used with 50257-row, dim4 CPU Embedding/Head,
  one synthetic AdamW update loss=10.897187; both first save/reload and
  independent verify passed full tokenizer ID/backend fingerprint,
  metadata and checkpoint SHA256 sidecar; weights_only=True, step=1.
  Research-layer guard only, upstream PR27 train/eval still unmodified.
  See [Gate E result](R2_GATE_E_RESULT.md).
- R2 Gate F (VERIFIED 2026-10-16): 148/148 tests PASS. Synthetic
  PR27-shaped 55 train/9 heldout docs with pinned real GPT2 tokenizer.
  A single-worker packed source, model/AdamW, Python/Torch RNG and cursor
  checkpoint after step 5 resumed through step 12, precisely matching the
  uninterrupted 12-step run: trace identical, loss delta 0.0, params,
  optimizer, cursor and RNG bitwise equal. No FineWeb-Edu or GPU used.
  See [Gate F result](R2_GATE_F_RESULT.md).
- R2 Gate G (VERIFIED 2026-10-16): 156/156 tests PASS. Two LOGICAL
  workers, ZERO OS processes: committed frontier 5 vs dispatched frontier 9,
  completed-but-UNCOMMITTED task IDs 5/6/7/8. Restarting from 9 would skip
  unused training samples; restarting from 5 yielded identical traces,
  max loss delta 0.0, exact model/AdamW/cursor/Python-Torch RNG states.
  No FineWeb/GPU; not original PR27 DataLoader. See [Gate G result](R2_GATE_G_RESULT.md).
- R2 Gate H (VERIFIED 2026-10-16): 162/162 tests PASS. Actual Linux
  torch DataLoader with 2 distinct OS worker PIDs per continuous, prefix,
  and resumed runs; num_workers=2, prefetch_factor=2. At checkpoint,
  optimizer commit=5 but real __getitem__ workers had already fetched
  tasks 5/6/7/8. Resumed from committed task 5; complete 12 vs 5+7
  trajectories, model, AdamW, cursor, Python/Torch RNG bitwise identical,
  maximum loss delta 0.0. LOCAL INDEXED SYNTHETIC source, no HF training
  and no SIGKILL. See [Gate H result](R2_GATE_H_RESULT.md).
- R2 Gate I (VERIFIED 2026-10-16): 171/171 tests PASS (15.046s).
  Official HuggingFaceFW/fineweb-edu sample-10BT/train repo immutable SHA
  87f09149ef4734204d70ed1d046ddc9ca3f2b8f9 resolved before streaming.
  First 32/32 source records captured with 111361 real UTF-8 text bytes,
  119588-byte canonical JSONL; SHA256
  dbd98514fa4de0df2271fe9ddc214a295108492f20fa993fa33bbe6db5d366e1.
  Offline VERIFY matched and license metadata odc-by captured. No model
  training, no PR27 loader changes or true streaming cursor.
  See [Gate I result](R2_GATE_I_RESULT.md).
- R2 Gate J (VERIFIED 2026-10-16): 179/179 tests PASS in 26.679s.
  REAL frozen 32-document FineWeb text, immutable dataset SHA
  87f09149ef4734204d70ed1d046ddc9ca3f2b8f9 and GPT2 contract SHA
  d8c2780bf00fc7a224bfca89725ad9cc0522c48aa67cf796599ae6a04be3d3c9.
  28 train/4 excluded INTERNAL development-only docs (NOT heldout/eval).
  Three runs used two real OS PIDs each. Prefetched uncommitted batch IDs
  5-8, resume started at 5. Full vs 5+7 CPU Tiny AdamW runs had bitwise
  identical traces/model/optimizer/cursor/RNG, max loss delta 0.0. Data
  globally PACKED first; NOT upstream worker-sharded IterableDataset.
  See [Gate J result](R2_GATE_J_RESULT.md).
- R2 Gate K (VERIFIED 2026-10-16 AFTER FAILED FIRST RUN): original
  187-test suite had one double-shard integration ERROR, documented as
  Failure 001. HF native-auto-only fix then passed 190/190 tests in
  39.748s; Gate I real 32-doc snapshot yielded internal 28 train/4
  excluded records, covered ONCE by two OS workers (14/14). Three
  Loader runs saw distinct worker PIDs, four speculative prefetched
  windows discarded, resumed global batch 5. Tiny CPU 12 vs 5+7 model/
  AdamW/cursor/Python-Torch RNG bitwise equal, max loss delta 0.0.
  Worker-local sharding vs global pack differed at 11 of 12 windows.
  Real remote HF IterableDataset NOT tested. See [Gate K result](R2_GATE_K_RESULT.md).
- R2 Gate L (committed, unverified): use SAME pinned Gate I snapshot but
  pass only hash-based document IDs to 8 LOCAL HF Arrow shards. With two
  REAL OS DataLoader workers compare HF NATIVE auto-shard ONCE versus PR27-
  style explicit per-worker .shard() PLUS HF auto-shard. Both arms must
  show two PID workers; record exact document coverage and silent missing
  source indices in the double-shard arm. No text to workers, no training,
  no live Parquet. See [Gate L plan](R2_GATE_L_DOUBLE_SHARD_COVERAGE_PLAN.md).
- Community training proposal:
  <https://github.com/kyegomez/OpenMythos/pull/27>. Proposed ~117.8M
  MLA+MoE FineWeb-Edu experiment and loop-depth PPL tests; external reports
  are leads to reproduce, not verified project results. Review tokenizer
  consistency and bf16 issues before reuse.

## Milestone R0 — Architecture and training readiness audit (IN PROGRESS)

Deliver one evidence matrix with columns `feature`, `implementation path`,
`source classification`, `test`, `status`, `risk`.
Audit:
- model config and parameter accounting; attention / KV cache / causal mask;
- recurrent shared parameters, position/depth injections, ACT,
  depth-specific LoRA, MoE routing, residual/numerical stability;
- tokenizer, training labels, sequence packing, optimizer, dtype/mixed
  precision, gradient accumulation, gradient clipping and resume checkpoint;
- generation correctness vs full recomputation, depth extrapolation,
  deterministic heldout evaluation and training/evaluation data leakage;
- reproducible torch/environment dependencies.

**Gate R0**: trainable end-to-end pipeline with checkpoint save/resume,
heldout text evaluation, generation and explicit audit findings.
Maintain upstream `open_mythos/main.py` unchanged on research branch until a
reviewed, evidence-justified patch is separately proposed.

## Milestone R1 — Actual small language model training

- Start with manageable ~100–200M parameter class, or smaller as necessary for
  available GPU memory, trained on licensed/publicly usable text.
- Record tokenizer ID, dataset revision, data cutoff, dedup/splits,
  token count, batch/sequence, optimizer schedule, precision, seeds,
  parameter counts, FLOPs estimates, wall-clock, hardware, checkpoints.
- Report real heldout token-level NLL/PPL, nonmemorized task performance,
  and grounded sample generation.
- Reproduce community PR #27 only after confirming code quality and compute
  feasibility, including potential bf16 and tokenizer consistency pitfalls.

**Gate R1**: independently rerunnable real-data checkpoint and PPL result;
a CPU synthetic experiment is not a substitute.

## Milestone R2 — Architectural hypothesis testing

Compare, at equivalent training-token and measured/estimated compute budgets:
- non-recurrent baseline;
- fixed-depth recurrent version;
- ACT/adaptive recurrence;
- optionally GQA/MLA, MoE and injection ablations after baseline is stable.

Record full train/eval cost and inferenced latency, actual loop counts,
quality against budgets and multiple seeds. Seek evidence for or against
the hypothesized recurrent architecture rather than treating it as confirmed.

**Gate R2**: a repeatable cost-quality curve that identifies which features
are valuable in the independent reconstruction.

## Milestone R3 — Behavior-targeted replication

Define a **named target version** (e.g. an available Claude Mythos model) and
an authorized testing interface. Establish public or permissioned evaluation
sets across reasoning, coding, long-context retrieval and instruction following.
Keep prompts/dataset versions fixed; score blind where feasible.
Public model-level benchmark scores compare capabilities; they are not evidence
of matching hidden activations or architecture.

**Gate R3**: documented capability-gap report on tasks accessible to both
the independent reconstruction and the target.

## Milestone R4 — Scaling decision

Only scale to 1B+ parameters once training correctness, inference correctness,
real-data evaluation and an actual hardware budget are known. Continue with
distillation or fine-tuning **only within applicable terms and permissions**;
avoid unsupported claims of proprietary model extraction.

## Immediate work queue

1. Run Gate L full unit tests + 2-real-worker 8-local-HF-shard coverage
   A/B to demonstrate whether PR27-style MANUAL per-worker sharding
   compounded by HF's automatic worker partition silently omits source
   documents even while both worker PIDs are active. Run only in Linux
   Codespaces, using Gate I source SHA; never send real text to workers.
2. Keep verified Gate K 190/190 evidence (28/28 docs, two true OS
   workers per run, 12 vs 5+7 bitwise Tiny AdamW recovery); retain
   its first 187-test/1-error failure report as provenance.
3. Next validate the ORIGINAL pinned remote HF FineWeb-Edu dataset file
   shard identities/assignment at the installed HF datasets version.
   Do not extrapolate local 8-shard omission rate to 2410 remote files.
4. Only with immutable real source + single worker sharding + source
   cursor + optimizer COMMITTED ACK should an isolated PR27 training
   adapter attempt SIGKILL fault and authentic streaming resume.
5. CUDA still absent in Codespaces. Budgeted GPU, BF16/FlashAttention,
   MoE/ACT computation and independent heldout PPL are separate blockers.

## References

- Community implementation: <https://github.com/kyegomez/OpenMythos>
- Community loop-scaling experiment PR (independent report):
  <https://github.com/kyegomez/OpenMythos/pull/27>
- Anthropic model reports: <https://www.anthropic.com/transparency>
- Anthropic Mythos 5.1 documentation:
  <https://platform.claude.com/docs/en/models/mythos-5-1/overview>
