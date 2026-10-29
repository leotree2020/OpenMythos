# Mythos P2 CPU parameter sharing — measured checkpoint (2026-10-29 JST)

## Mainline boundary
- Model R&D hypothesis: with **identical two-block PyTorch computation and identical initial outputs**, tie both TransformerEncoderLayer instances and measure next-token learning impact; not a new model architecture.
- Original native Parcae M1-B remains **BLOCKED_RESOURCE / NOT TESTED**. PR #12 (`mini-mythos-m1-parcae-learning-cpu-20261029`, HEAD `c639112fdab8a5f69951835efe6862e2ed6aed29`) still Draft, GitHub Actions run count zero, no native B NLL/PPL. Do not claim this PyTorch experiment replaces Parcae.
- Original upstream Parcae `69284c13746e849104f738d6d1a347b1f457df76` was not modified, no GPU rented, no merge.

## Execution and prior acceptance
- Python 3.13.5, torch 2.10.0+cpu, Linux x86_64, one thread, deterministic; seeds 42, 20261029, 20261030, each 180 AdamW updates (LR 0.002), period-4 synthetic next-token, vocab 16, sequence 16, batch 32. Original M1 A fixed train batch/val/test SHA-256 **exact match**. No overlapping base-sequence code IDs.
- A: two independent but identically initialised PyTorch TransformerEncoderLayer objects; B: two calls of **the same** layer object. All embeddings, head, seeds, data, objective, clipping and optimizer settings identical. A and B initial logits exactly equal (max abs=0). Dropout=0.
- **PREDECLARED PASS criteria**: initial logit diff <=1e-6; equal batch ID SHA; both validation NLL improve >=0.05; B has fewer unique parameters; B final val NLL <= A+0.05 absolute. **PASS 3/3 seeds** under these narrow criteria.
- Independent Python rerun: **48/48 numerical and weight-hash comparisons match**. A reproduced existing M1-A validation NLL exactly.
- Source is committed to this isolated branch: `research/mini_mythos/m1/paired_shared_portable_cpu.py`, Git Blob SHA `67fe1f77e54500e81c81365d36bf408254419a03`, verified byte-identical to locally executed script; SHA-256 `95238937cd2bfd33ce863ae25e6ba92cd889d6a89af223cfaf4765e99765d6b5`.

| Seed | A independent val NLL | B tied val NLL | Outcome |
|---|---:|---:|---|
| 42 | 0.0208534349 | 0.0285548291 | Both learn |
| 20261029 | 0.0236762235 | 0.0301405623 | Both learn |
| 20261030 | 0.0212633185 | 0.0284898172 | Both learn |
| Mean | **0.0219309923** | **0.0290617362** | B loss +32.51% relative |

- Unique trainable parameters: A=18,704; B=10,160; **45.6801% lower**. Both execute two layers; weight tying does not by itself establish fewer FLOPs, better throughput, or less peak memory.
- **Important adverse observation:** B NLL is **32.5145% higher** relative to A. A **post-hoc stricter 10% relative noninferiority threshold is NOT MET**; it was not predeclared, so record as a follow-up caution, not relabel the preregistered trial. The initial absolute +0.05 criterion is loose on this easy task. No architecture breakthrough / natural-language result.
- Full machine outputs and two independent rerun logs: local ZIP `Mythos_M1_P2_CPU_Measured_20261029.zip` SHA256 `d38cd5d2e5277aa9a8647205c7c171951be2cd9163e09605dd0b625b20377f20` (not uploaded to GitHub).

## Stage decision and next instruction
- **P2 preflight: PASS limited; formal matched compute/quality performance: NOT TESTED.**
- Next FIRST priority: run **native Parcae M1-B CPU learning** on authorized real pinned checkout using existing PR #12 `run_m1_codespaces_cpu.sh 42`, check real JSON, exit status, train/val/test NLL. If blocked, log actual root cause; do not write Guard V4 or another toy as substitute.
- After native B PASS: compare at matched **actual FLOPs / tokens / quality**. Strict model-quality threshold must be set before run, not after. Grok reviewer not yet obtained; Oracle/G2 REAL remain BLOCKED.
