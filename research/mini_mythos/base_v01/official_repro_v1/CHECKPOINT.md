# MYTHOS-PARCAE-OFFICIAL-CORE-CPU-V1 — calibration RUNNING

As of 2026-11-01T09:50:15.167176+00:00. Read this checkpoint before doing any more work; the existing process must not be relaunched.

Purpose: execute original official CORE and compare it with our twelve free continuations.
Environment: designated Codespace, 2CPU/8GiB, isolated eval overlay, original CPU torch2.11.0+cpu.
Input: fixed upstream69284c13, original140M weights/config and official tokenizer, unmodified official bundle SHA90a7c19e28ee7a52b4f6e1f87658deb9fde7f63deba2379045bdb1fe9ea5d200.
Expected: calibration22 tasks x12 examples x3 official seeds =792 examples,66 task summaries; independent saved-score/answer audits; no protected-file changes. Full exam is273111 examples.
Actual: 127 completed example observations, 10 completed task observations at checkpoint time. Run continues. This snapshot is not a final result.
Status: preparation PASS; calibration final acceptance NOT TESTED / RUNNING; full CORE NOT TESTED; author-score replication NOT TESTED.

Branch: mythos-parcae-official-repro-cpu-v1.
Prior completed checkpoint6b52321746f393fa36711ff3896a5a9c5484c7c0.
Frozen observer/protocol22b415118a6482d8957bff29126ef56e3e9a71b4.
Run record57f5c891de83ef06ccce46b64509cf2121fcdb0b.
Read-only audit freeze920d615276f434512cdae6fd877a1e53f8cfc9a1 (prepared after model launch, before result auditing).

Run: /workspaces/mythos-evidence/base_v01/official_repro/official-core-limited-v1-20261101T093733Z
Operator: /workspaces/mythos-evidence/base_v01/official_repro/official-core-limited-v1-20261101T093733Z-operator
Launcher PID7340/starttime180513; child7362/starttime180521. Existing launcher has6000s timeout and exclusive claim; do not restart.
Interpreter: /workspaces/mythos-parcae-official-eval-cpu312/bin/python. Overlay reads baseline site-packages; original baseline was rechecked unchanged before launch. eval_overlay.lock contains exact package URLs/hashes. New overlay transformers5.22.1/lm_eval0.4.12/jsonargparse4.53.0. Official CLI help and pip check passed.

Scientific caveats: official limited mode also limits the few-shot pool. Its score cannot be equated with paper14.04+/-0.20. CPU path isFP32, not GPU/BF16 paper conditions. Official h0 is not seeded by its few-shot seed argument; RNG states are saved but never reset. Public weight SHA-to-paper-table mapping is not independently established.

Current differences: official CORE uses candidate mean NLL or exact teacher-forced answer matching, explicit BOS fallback1/PAD0 with metadata-free official tokenizer, taskwise chance-centered macro scores. Our earlier12 prompts used64-token free greedy continuations and repetition/AI-coherence screens. See EXAM_COMPARISON.md.

Unresolved: calibration still running; full runtime/resource feasibility pending measured task times; no CUDA GPU on current target or local PC; no full score or sampling-quality conclusion. The prior probability-sum guard FAIL and original B1A5 BLOCKED are unchanged. Formal Oracle BLOCKED/NOT_READY; FORMAL_ACCEPTANCE_READY=False. No training/B2/D2-A/PR24/upstream change.

Next unique instruction: observe this existing run until normal completion or its first failure/timeout; preserve all evidence, independently audit saved results, write final checkpoint, then assess full-run resources without relabeling the subset as full reproduction.
