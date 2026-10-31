# Mythos Base v0.1 — B1 checkpoint: implementation complete; target-machine execution NOT TESTED

2026-10-31. Experiment MYTHOS-BASELINE-B1. Branch `mythos-base-v01-b1`.

## Current decision

**The B1 code, tests, configuration and runbook are implemented and committed. The B1 acceptance run on the target machine has NOT been executed: this session has no access to the target machine, and the network policy of this session denies `huggingface.co` (HTTP 403 on the CONNECT tunnel, re-checked 2026-10-31T13:39Z for both pinned URLs) and `download.pytorch.org`.** Nothing in this checkpoint is B1 evidence. Engineering baseline: NOT TESTED. Language quality: NOT TESTED (no generation on the real weights has occurred).

No training, no backward pass, no optimizer, no GPU, no KV cache, no upstream edit, no PR action was performed. PR #24 was not touched.

## 1. Purpose

Controlled load, fixed-prompt text generation and save/reload of the official Parcae-140M weights on CPU, as the first step toward a trainable, resumable, text-generating small research model. B2 (bounded training and resume) and B3 (package acceptance) are not started.

## 2. Git, code identity and sources

- Repository `leotree2020/OpenMythos`, new branch `mythos-base-v01-b1` created from `4308099bfc90d9398f54a47f9272b6bd4582f7b9`; only `research/mini_mythos/base_v01/` is added.
- **Frozen execution commit: `d39eabb0f1ec33230bfdd00337877c647dfa42db`** (code, fixtures, runbook, tooling). The commit that adds this file is documentation only.
- Upstream `sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76` (read-only; `git status --ignored` was empty before and after every local run).
- Model `SandyResearch/parcae-140m@236739ce93ba1afc1b3f172fb4a509f4500d2852`: `pytorch_model.bin` 578,361,537 B `ed6eb306464dd0d694e9eacd58f7e06ac3e44b43cb7c5c79dbcb1543059c6621` (LFS metadata value, never recomputed here); `config.json` 1,741 B `5c8fc785c2f6dba67d0370ad715034860e3b22bfce850da825c06baa03923c13`.
- Tokenizer `SandyResearch/parcae-tokenizer@6247b5d0592876b73660f34c2dd16c9db9e9045c`: `tokenizer.json` 2,326,980 B `e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77`.
- **License: UNCONFIRMED** for weights and tokenizer (no declaration found). Local research use only; no redistribution of weights, tokenizer or derived models; nothing of that kind is committed.

## 3. What was implemented

|File|Role|
|---|---|
|`base_v01.py`|pinned sources and expectations, exclusive JSON records, environment/memory/disk facts, read-only upstream pin check, single-attempt verified download, tokenizer identity and probes, state-dict accounting (prefix rule, missing/unexpected/shape/dtype/finite/shared), config construction without silent field dropping and built-in config diff, RoPE buffer check, backend check, native-vs-generation logits, generation and automatic degeneration checks, package save|
|`run_base.py`|stages `env-check`, `fetch`, `verify-load`, `generate`, `reload-check`, `finalize`; each writes one record, refuses to rerun, requires the previous stage to be PASS|
|`prompts_v1.json`, `tokenizer_probes_v1.json`|12 frozen prompts (prompt 7 holds real newlines), 32 frozen tokenizer probes|
|`build_env.sh`, `make_lock.py`, `requirements.direct.txt`, `constraints.txt`|isolated Python 3.12.3 environment, pip resolution report → hash lock with a 14-day release-age review → install by hash → `pip check` → freeze/lock comparison|
|`test_base_v01.py`|28 fixture tests including a tiny-model rehearsal of the whole chain (each stage a separate process)|
|`README_USAGE.md`|runbook, protocol, supported/unsupported scope|

Design facts that differ from the earlier plan: `attn_impl=flash` is kept unchanged (`flash`, `sdpa` and `tridao` select the same function; on CPU `HAS_FA3` is false and the SDPA fallback is used; every numerical check runs under `SDPBackend.MATH`); `tokenizers==0.23.2` requires `huggingface-hub>=0.16.4,<2.0`, so `huggingface-hub==1.33.0` is pinned and no `--no-deps` is used before the closure is locked; the cumulative 3-hour limit counts active stage time, not idle gaps between stages.

## 4. Checks actually run in this session (development only, NOT on the target, NOT B1 evidence)

Sandbox: Intel Xeon @2.10GHz, 4 vCPU, 16 GB RAM, ~2.4 GB free disk, Python 3.12.3, torch 2.11.0+cu130 (CPU use), numpy 1.26.4, `tokenizers` 0.23.2 installed to a scratch directory.

|Check|Result|
|---|---|
|`python -m unittest test_base_v01`|28/28 PASS: parsing, exclusive writes, pinned-constant format, floating-revision refusal, prefix mapping, state-dict accounting negatives (missing/unexpected/shape/dtype/non-finite/tied mismatch), degeneration rules (incl. U+FFFD never forgiven), tokenizer identity and 32-probe round trip on a toy tokenizer, local-HTTP download (good, wrong hash, wrong size, missing file, no overwrite), exception-to-status mapping, full chain on a random tiny model, tampered download|
|Tiny-model rehearsal|env-check NOT TESTED by design (disk/dependency waivers), fetch, verify-load, generate, reload-check all PASS; 12 prompts × 3 passes bit-identical; reload in a separate process|
|Exposed and fixed during development|stage status could read NOT TESTED after an exception that recorded no check (now mapped to BLOCKED/FAIL, covered by a test); `run_stage` keyword clash|
|Real-architecture smoke, random weights, in memory (script not committed)|built-in `parcae-small-140m` config constructs on CPU in 10.8 s; 144,323,136 parameters, 61 parameter tensors, 63 state_dict entries, tied head, value-embedding keys {1,3,5} with gates at `prelude.1`, `core_block.1`, `coda.1`; `attn_impl=flash`, `use_fused_head=pytorch`, `n_layer=8`; native forward vs `forward_for_generation` on 24 tokens bitwise equal; 4-token no-cache greedy generation 0.8 s; process RSS 1.44 GiB. These are checks of the source-derived numbers on a constructed model, not of the Hugging Face binary|
|Lock tooling on the non-torch closure|18 packages resolved, hash lock written, release-age review: 3 packages too new without `constraints.txt` (filelock 4.2.5, hf-xet 1.8.0, certifi 2026.10.23), 0 violations with it. The PyTorch CPU wheel (`torch==2.11.0+cpu`) could not be resolved here|

Sandbox timing is not a prediction for the target: about 0.2 s per no-cache generation step at ~26 tokens (single thread) suggests roughly 30 s per 64-token prompt and 5–6 minutes for 12 prompts, unmeasured on the target.

## 5. Acceptance status (A1–A11)

|Item|Status|Reason|
|---|---|---|
|Target preflight (CPU, memory ≥4 GiB, disk ≥5 GiB, dependencies, threads)|NOT TESTED|no access to the target machine|
|A1 pinned files: size and SHA-256|NOT TESTED / BLOCKED here|`huggingface.co` denied (403); no weights downloaded|
|A2 `weights_only` load into tensor dict|NOT TESTED|needs A1|
|A3 keys, shapes, dtype, finite, shared weights|NOT TESTED|needs A1|
|A4 actual config vs built-in config|NOT TESTED|needs A1|
|A5 RoPE buffer vs native recomputation (≤1e-6)|NOT TESTED|needs A1|
|A6 tokenizer identity and 32 probes|NOT TESTED|needs A1|
|A7 CPU/SDPA-fallback backend|NOT TESTED on the real run (backend resolution verified on the fixture and the real architecture)|needs the target run|
|A8 native vs generation logits (rtol 1e-5, atol 1e-6)|NOT TESTED on the real weights (bitwise equal on a random real-size model)|needs A1|
|A9 12 prompts: generation and automatic checks|NOT TESTED|needs A1|
|A10 same-process repeat|NOT TESTED|needs A9|
|A11 new-process reload (weights, logits, tokens, text)|NOT TESTED|needs A10|
|Engineering baseline|NOT TESTED||
|Language quality (≥9/12 prompts passing automatic checks AND AI-assisted coherence review)|NOT TESTED|coherence review is ChatGPT's step and has not happened; it is not a human evaluation|

Resource use on the target, evidence directory, run id and manifest: none exist yet.

## 6. Unresolved items

1. Run on the target machine (below). 2. `requirements.lock` is not committed: it must be generated on the target by `build_env.sh`, reviewed, and committed before the formal run (a dirty tree is refused). 3. License of weights and tokenizer is unconfirmed. 4. `config.json` content beyond the facts in the authorization has not been read by this session. 5. Source-derived counts (144,323,136 / 61 / 63) are confirmed only on a constructed model, not on the shipped binary. 6. The `X-Repo-Commit` header is recorded when the server provides it after redirects; the pinned revision in the URL is the immutability guarantee.

## 7. Next single instruction

On the target machine, check out `d39eabb0f1ec33230bfdd00337877c647dfa42db`, follow `README_USAGE.md` steps 1–3 exactly once (build the environment and lock, commit the lock, run the helper tests, then `env-check` → `fetch` → `verify-load` → `generate` → `reload-check` → `finalize`), keep the whole run directory, and stop. Any BLOCKED or FAIL stops the chain with evidence preserved; no automatic retry, no training, no B2.

Formal Oracle stays BLOCKED/NOT_READY, `FORMAL_ACCEPTANCE_READY=False`. D2-A stays deferred.
