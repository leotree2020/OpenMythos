# M2 CPU text pilot, 2026-10-29

Purpose: compare official GPT and official Parcae from the same untouched
`sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76` checkout.
This is a small learning/fairness pilot, not a model superiority gate.
Acceptance thresholds are encoded in run_cpu.py before the first run.

Input: Tiny Shakespeare, UTF-8 bytes (256 token IDs), contiguous 80/10/10 split
before window construction. Source:
https://raw.githubusercontent.com/karpathy/char-rnn/master/data/tinyshakespeare/input.txt
Record exact downloaded SHA256 in evidence; reproduce with that file/hash because
the source URL is a moving branch. Do not infer semantic deduplication from byte
interval separation. Evaluation uses the first <=512 bytes of each held-out split.

Common: CPU FP32, one thread, math SDPA, seq=32, batch=8, 120 optimizer steps,
30,720 training tokens per arm, seeds 42/20261029/20261030, AdamW lr=.002,
betas=(.9,.999), eps=1e-8, wd=0, gradient clip=1. Same precomputed batch starts.
Widths=32, FFN=64, heads=4, RoPE and LayerNorm, native scaled initialization.
GPTInit and ParcaeInit retain native differences; initial weights are not equal.
No change to upstream source or OpenMythos architecture.

Arms: official GPT 4 blocks (compute candidate), GPT 3 blocks (parameter candidate),
Parcae 1 prelude + 2 core passes + 1 coda, all core passes with gradients [0,2].
Predeclared ratios max/min <=1.10 for compute and parameters, measured separately.
Never equate block count with FLOPs. Count forward+backward supported operators
with torch.utils.flop_counter using math SDPA, excluding optimizer/scalar ops.
Report native initialization and residual matching differences.

Execution PASS: every run has finite loss/gradient, changed weights, held-out
validation NLL decrease >=.01. Fairness PASS is separate: identical batches/tokens
and BOTH parameter and compute ratios <=1.10 for all comparisons. A ratio failure
does not authorize silently tuning after observing quality; design the next pilot.
Record test NLL/PPL, elapsed training seconds, parameter count and counted FLOPs.
No GPU needed. No Guard expansion. Grok cross-review remains pending until actual
review is supplied; no Grok access is available in this session.

Reproduce from repo root (existing upstream checkout must be clean and pinned):

```sh
python research/mini_mythos/m2/download_text.py
python research/mini_mythos/m2/run_cpu.py --parcae-dir /tmp/mythos-m1-official-parcae --text research/mini_mythos/m2/evidence/tinyshakespeare.txt --out research/mini_mythos/m2/evidence/replay.json
```

The local pilot uses Python 3.12, torch 2.9.0+cpu, einops .8.0; these differ from
the M1 Codespaces torch 2.11 pin. Exact versions and actual outcomes are evidence,
not a claim of cross-environment numerical equivalence.

Actual environment: Python 3.12.14, torch 2.9.0+cpu, NumPy 2.2.6, einops 0.8.0,
Windows. NumPy is outside upstream's numpy<2 declaration. Treat this as a local
pilot; a pinned Linux rerun is NOT TESTED. GPT's native non-fused path is selected
with use_fused_head=False because its code tests truthiness; the string 'pytorch'
selects an unavailable optional kernel. Initial failed attempt is retained in
evidence/attempt01_fused_head_error.log. Parcae uses its native 'pytorch' path.
No upstream edits or monkey patches were used.
