# MYTHOS-PARCAE-OFFICIAL-CORE-CPU-V1

## Purpose and scope

Execute unchanged official Parcae CORE evaluation on the released 140M checkpoint, first in the official limited mode to validate all task types and measure resource requirements. Compare this exam with our twelve free continuations. This is a new protocol, not a retry or retrospective relaxation of B1 or DECODE-CONTROL. No training, upstream edits, weight/config/buffer edits, B2, D2-A, GPU, or PR24 action.

Base result commit 6b52321746f393fa36711ff3896a5a9c5484c7c0; upstream read-only 69284c13746e849104f738d6d1a347b1f457df76. Original weight SHA256 ed6eb306464dd0d694e9eacd58f7e06ac3e44b43cb7c5c79dbcb1543059c6621; config 5c8fc785c2f6dba67d0370ad715034860e3b22bfce850da825c06baa03923c13; tokenizer e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77. Public model revision236739ce93ba1afc1b3f172fb4a509f4500d2852, tokenizer6247b5d0592876b73660f34c2dd16c9db9e9045c.

Official bundle URL https://karpathy-public.s3.us-west-2.amazonaws.com/eval_bundle.zip; 26060410 bytes; SHA25690a7c19e28ee7a52b4f6e1f87658deb9fde7f63deba2379045bdb1fe9ea5d200. Unmodified core.yaml, CSV and JSONL. Actual full count91037 per seed,273111 across3. ARC Challenge has1172 rows despite CSV2376. Hash all input files before execution.

## Environment and execution

Designated Codespace bookish-pancake-vwqx7rr9x5w3wxjr,2CPU/8GiB. New isolated eval venv reads the frozen baseline site-packages but cannot modify it. Torch2.11.0+cpu/numpy1.26.4/tokenizers0.23.2 unchanged. Exact overlay dependencies pinned by URLs and hashes; pip check and official CLI help/import checked before numerical execution. No copying or rewriting official scoring. Local tokenizer directory contains the official tokenizer.json only, matching the public repository; do not manufacture special-token metadata. Capture actual tokenizer IDs including None and official fallbacks.

Call original scripts/eval.py via runpy with original eval-core.yaml and local --hf_repo, external --out_dir/run_config.json specifying tokenizer_path, --device_type cpu. Original precision field bf16 remains; upstream CPU nullcontext makes actual weights/operations FP32. CPU2 intra-op and1 inter-op threads for the available machine; no forced attention backend, manual torch seed, deterministic-algorithm override or autocast. This is official CPU code-path reproduction, not exact GPU/BF16 paper environment.

The observer uses Python profiling/tracing solely to retain existing function inputs/returns, exceptions, timing and process maximum RSS. It does not replace model.forward, scoring, tokenization, prompts, RNG state or tensors. It saves RNG state but never restores/reseeds it. A forward_model exception is recorded and stops after the current example, because upstream can otherwise silently fall back. No added probability-sum test. Any exception/nonfinite score/coverage failure stops this run; no result-dependent retries.

## Stage C: limited calibration (pre-registered)

--tasks.core.max_per_task=12, all22 tasks, official seeds[1234,2345,3456], total792 scored examples. Original shuffle1337, sample selection, few-shot selection, left-crop2048, BOS/padding, option batching, mean NLL and exact teacher-forced match unchanged. Each task's few-shot pool is also limited to12; do not interpret the score as an unbiased estimate of full CORE.12 is greater than maximum few-shot10.

Before running: source hashes, dependency inventory, original input hashes, task inventory and this protocol frozen in Git. Official --help/import and observer syntax are preparation-only; do not call these model evidence.

Expected:792 unique(task,seed,idx) results and66 task results; original eval/core.json, finite task/aggregate values; model mean_recurrence8/FP32, official loader; no observed fallback exception; upstream/protected inputs and baseline environment unchanged. Observe exactly one model forward per scored example from official source; instrumented exception reporting verifies no silent fallback, but do not invent a measured forward count without a dedicated observation.

Acceptance:
- Input/source/environment identity and CLI preparation PASS before numerical run.
- Completion code0 is necessary but insufficient. Recompute each MC decision from recorded mean NLL/gold and each LM exact match from recorded predicted/gold tokens. Verify792 rows,264 per seed,12 per task/seed, no duplicates or missing IDs,66 task summaries.
- Recompute task accuracy from Boolean rows, chance-centered values from original CSV, CORE macro averages and population SD. Absolute tolerance2e-7 for FP32 mean versus independent arithmetic, not a performance margin. All official reported scores finite.
- File/input preservation PASS; runtime provenance, warnings, stdout/stderr and all partial results retained on failure.
- Pipeline PASS does not mean positive language quality or author-score match. Limited-mode scientific outcome is descriptive only. All actual measurements and FAIL/BLOCKED must be retained.

## Full evaluation decision

After calibration, estimate full runtime per task as full row count times measured per-example mean, report uncertainty and observed peak memory. Do not automatically substitute fewer seeds, fewer tasks or fewer questions. Full run requires original max_per_task=-1 and all273111 examples with the same observation and official scoring. If machine resources or available uninterrupted execution cannot support this, record the concrete blocker and leave full reproduction NOT TESTED/BLOCKED; retain actual limited results. Full-run settings and execution commit must be recorded before starting it. No claim that14.04±0.20 is an acceptance interval: it is author Table5 CORE percentage-point mean±SD for140M/T8, not raw accuracy. Exact mapping from paper score to released weight SHA remains unestablished. Do not report author-score replication until full coverage and comparable configuration are established.

## Deliverable and checkpoint

Purpose/Environment/Input/Expected/Actual/PASS-FAIL-BLOCKED-NOT TESTED; execution and result commits, dependency lock, original outputs, item observations, recomputation audit, resource estimate, official-versus-custom exam comparison, unresolved limitations and next unique action. Commit research code/documentation and compact evidence; keep original model, tokenizer, benchmark source and binary RNG files external with manifests. Stop at BLOCKED/FAIL and preserve evidence; successful calibration proceeds to the documented full-run feasibility decision.

## Final static-review clarifications

All path arguments are absolute; execute with -I -B and PYTHONDONTWRITEBYTECODE=1. Reuse unchanged, previously validated mythos_launch.py (SHA2568083b948eebdf08c2d14a79d940ccead72db5f10c6bac8d9061816b6c9ea05c3) in a new operator directory;6000s calibration ceiling. Its completion record remains external to the observed process and retains stdout/stderr on child initialization failure, signal exit, or exception. An absent child completion file is BLOCKED, never PASS; no new signal suppression or handlers in the numerical child. Launcher interruption/timeout preserves its reason and cleans only its own child group. Abnormal termination has partial evidence, not a fabricated clean completion.

The observer additionally has an outer failure record beside its immutable spec, covering setup and cleanup exceptions. Normal and incomplete function returns are distinct; None never counts as scored. Runtime measurements include observation overhead and are for budgeting this observed run, not a native-speed benchmark. Dependency preparation first encountered an over-constrained fsspec/datasets requirement; the resolver was stopped before installing anything. Only the new overlay uses fsspec2026.7.0; original baseline2026.9.0 is unchanged. The new overlay uses Transformers5.22.1, lm_eval0.4.12 and jsonargparse4.53.0, with all resolved URLs/hashes retained. Official CLI help/import and pip check passed; official tokenizer wrapper reports BOS/EOS/PAD=None on the repository's metadata-free tokenizer.json, so CORE's original BOS1 and PAD0 fallbacks apply. We do not overwrite these to our earlier assumed special IDs.
