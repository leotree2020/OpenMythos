# Mythos Base v0.1 — B1 usage (controlled load, text generation, save/reload)

Local research use only. The weights and the tokenizer have **no confirmed license** (the code is MIT, the
weights and tokenizer are not covered by that statement): do not redistribute them or derived models.
This is an engineering integration around the official Parcae-140M weights, not a model trained here.
B1 performs **no training**: no backward pass, no optimizer, no GPU, no KV cache.

## Pinned sources (immutable revisions)

| What | Value |
|---|---|
| Model | `SandyResearch/parcae-140m` @ `236739ce93ba1afc1b3f172fb4a509f4500d2852` |
| `pytorch_model.bin` | 578,361,537 B, SHA-256 `ed6eb306464dd0d694e9eacd58f7e06ac3e44b43cb7c5c79dbcb1543059c6621` |
| `config.json` | 1,741 B, SHA-256 `5c8fc785c2f6dba67d0370ad715034860e3b22bfce850da825c06baa03923c13` |
| Tokenizer | `SandyResearch/parcae-tokenizer` @ `6247b5d0592876b73660f34c2dd16c9db9e9045c` |
| `tokenizer.json` | 2,326,980 B, SHA-256 `e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77` |
| Upstream code | `sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76` (read-only, MIT) |

## 1. Environment (target machine)

```bash
cd <this repository checkout>            # the committed B1 execution commit
bash research/mini_mythos/base_v01/build_env.sh
```

This creates `/workspaces/mythos-base-v01-cpu312` (Python 3.12.3, never an existing directory), resolves the
closure of `requirements.direct.txt` under `constraints.txt` without installing, writes a hash lock and a
release-age review (every release at least 14 days old), installs strictly by hash, then runs `pip check`
and `pip freeze` and compares them with the lock. On any violation it stops with `BLOCKED`.
Review the generated `requirements.lock`, copy it to `research/mini_mythos/base_v01/requirements.lock`
and commit it **before** the formal run (the formal `env-check` refuses a dirty tree).

## 2. Helper tests (fixtures; the tiny-model rehearsal is not B1 evidence)

```bash
export B1_UPSTREAM=/workspaces/mythos-parcae-pinned
/workspaces/mythos-base-v01-cpu312/bin/python -B -m unittest research/mini_mythos/base_v01/test_base_v01.py
```

## 3. Formal stages (each is a separate process; each writes one record and refuses to run twice)

```bash
PY=/workspaces/mythos-base-v01-cpu312/bin/python
R=research/mini_mythos/base_v01/run_base.py
$PY -B $R env-check --upstream /workspaces/mythos-parcae-pinned     # prints the run directory
RUN=/workspaces/mythos-evidence/base_v01/b1/<run-id>
$PY -B $R fetch        --run-dir $RUN     # A1: pinned download, size + SHA-256
$PY -B $R verify-load  --run-dir $RUN     # A2-A7: weights_only load, keys/shapes/dtype, config, RoPE, tokenizer, backend
$PY -B $R generate     --run-dir $RUN     # A8-A10: native vs generation logits, 12 prompts x 2 passes, package save
$PY -B $R reload-check --run-dir $RUN     # A11: genuinely new process: weights, logits, generations, texts
$PY -B $R finalize     --run-dir $RUN --export-dir research/mini_mythos/base_v01/evidence_b1
```

Exit codes: 0 PASS, 1 FAIL, 2 BLOCKED, 3 NOT TESTED. Exit codes are not evidence: read `<stage>.json`,
`summary.json` and `manifest.json` in the run directory. A stage whose predecessor is not PASS is refused.
Nothing is retried, resumed, overwritten or relaxed; failures keep all partial output.

## Generation protocol

`ModelingParcae.generate(use_cache=False, do_sample=False, num_steps=8, max_new_tokens=64)`, temperature 1,
no top-k/top-p, `eval()`, no gradients, CPU FP32, one thread, SDPA `MATH` backend, no BOS/EOS added.
Prompt *i* (1..12) uses `torch.manual_seed(731000 + i)`; a prompt longer than 48 tokens is a BLOCKED, never truncated.
The frozen generate has no early stop: all 64 tokens are computed and stored; scoring uses the part before the
first EOS (id 1). Automatic checks per prompt: at least 16 new tokens, no 4-gram three or more times, no token
six or more times in a row, decoding succeeds with no U+FFFD anywhere. Coherence is a separate review
(AI-assisted, not a human evaluation); language quality is PASS only if at least 9 of 12 prompts pass both.

## Supported and unsupported

Supported: CPU inference on the pinned weights with the settings above; saving and reloading an inference package.
Not supported / not tested: training, resume of training, KV cache, sampling, GPU, bf16/fp16, torch.compile,
distributed, streaming data, any other model size.
