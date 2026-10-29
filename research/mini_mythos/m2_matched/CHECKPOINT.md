# M2 matched CPU pilot — checkpoint 2026-10-29

Stage provisional: measured gates PASS; Grok independent review NOT TESTED.
PR #12 remains Draft. No merge or architecture-superiority claim.

## Provenance

- Pre-training freeze: e533fbe36aaf18fd551ee21e5c2d20551b5a2e16.
- Raw Linux results and weights: commit 5c5d3ad.
- Training and replay recorded clean e533fbe checkouts. Their script/config hashes
  match the frozen commit, independently checked by audit_results.py.
- Official GPT and Parcae are from unchanged sandyresearch/parcae at
  69284c13746e849104f738d6d1a347b1f457df76.
- Python 3.12.3, torch 2.11.0+cpu, NumPy 1.26.4, einops 0.8.0;
  Linux 6.8.0-1064-azure, CPU FP32, one thread. Full pip freeze is saved.
- No GPU, Guard expansion or upstream source modification.

Read PROTOCOL.md for preregistered criteria and frozen_config.json for calibration.
The earlier M2 simultaneous-budget FAIL remains valid for its old configurations.
This pilot selected GPT FFN 60 from a fixed grid using synthetic counts only,
before language training. No candidate language quality was used for selection.

## Measured gates

| Gate | Actual result | Status |
|---|---|---|
| Native CE and causal-prefix preflight | All six runs within 1e-6 | PASS |
| Learning | Six runs, 120 finite loss/gradient steps each; changed weights; validation NLL decrease > .01 | PASS |
| Same data/tokens | Exact corpus/split/batch hashes; 30,720 training tokens per arm | PASS |
| Parameters | GPT 65,344; Parcae 60,224; max/min 1.08501594 <= 1.10 | PASS |
| Counted FLOPs | GPT 74,317,824/step; Parcae 80,412,672/step; max/min 1.08201058 <= 1.10 | PASS |
| Quality tolerance | Mean paired test delta +.01877512 <= .02; every delta <= .05 | PASS |
| Fresh-process seed-42 replay | Both arms' initial/final weight hashes, batches, full loss/gradient traces, evaluation NLLs and FLOPs identical | PASS |
| Weight integrity | Eight files hashed and loaded weights-only; finite tensors and matching semantic hashes | PASS |
| Grok independent review | No review supplied or direct Grok channel available | NOT TESTED |

## Quality and computation

Same UTF-8 byte tokenizer and Tiny Shakespeare SHA256
86c4e6aa9db7c042ec79f339dcb96d42b0075e16b8fc2e86bf0ca57e2dc565ed.
Contiguous splits: 892,315 / 111,539 / 111,540 bytes. Each held-out split evaluates
all 3,485 complete sequence-32 windows = 111,520 next-token targets; 18 validation
and 19 test tail targets are discarded. No window crosses a split.

| Seed | GPT test NLL | Parcae test NLL | Parcae minus GPT |
|---|---:|---:|---:|
| 42 | 2.56771129 | 2.60426894 | +0.03655765 |
| 20261029 | 2.57582580 | 2.58232612 | +0.00650032 |
| 20261030 | 2.56725868 | 2.58052606 | +0.01326738 |
| Mean | 2.57026526 | 2.58904037 | +0.01877512 |

Lower NLL is better. Parcae is slightly worse in all seeds, although within the
predeclared exploratory tolerance. This is not a statistical noninferiority proof.
Parcae uses 7.84% fewer parameters relative to GPT and 8.20% more counted training
FLOPs. Per run: GPT 8,918,138,880; Parcae 9,649,520,640 counted FLOPs.
CPU training time: GPT 1.61–1.63 s; Parcae 1.71–1.84 s. These short measurements
on shared CPU are descriptive, not reliable throughput claims.

Input embeddings, output heads and final LayerNorm are shared exactly at
initialization; remaining weights retain native scaled initialization. Different
FFN widths and native state/architecture behavior remain confounders. Counted
FLOPs exclude optimizer/scalar operations. Memory, GPU performance, downstream
reasoning and architecture superiority are NOT TESTED. Repeated phrases may
occur across corpus intervals.

## Evidence and recovery

evidence/linux_e533fbe contains raw JSON/logs, six final weights, two replay
weights, exit records, setup logs and pip freeze. evidence/audit.json records
independent local recomputation and tensor verification. evidence/SHA256.json
hashes committed text as UTF-8 LF and binary files verbatim. These state_dict
snapshots do not include optimizer/RNG state for exact mid-training resumption.

Codespace inactivity restart cleared /tmp, including old worktrees and the venv.
M1 archive and earlier M2 reports in /workspaces survived and remain committed.
Persistent paths now used:

- Code: /workspaces/mythos-m2-matched-e533fbe
- Upstream: /workspaces/mythos-parcae-pinned
- Python: /workspaces/mythos-m2-cpu312/bin/python
- Original evidence: /workspaces/OpenMythos/mythos_evidence/m2_matched_e533fbe

Initial default Python 3.14.2 setup was abandoned when NumPy attempted source
compilation; its log is retained. Formal runs only used pinned Python 3.12.3.
A multiline browser archival input was interrupted before execution; short
commands then copied and committed the raw evidence. No retraining was needed.
The original main exit record contains literal backslash-n after 0 due to shell
formatting; replay has a normal newline. Exit records are not used as PASS gates.

## Next instruction

Obtain and preserve Grok's actual independent response using REVIEW_REQUEST.md.
Resolve disagreements through a minimal controlled CPU experiment before claiming
joint acceptance. Do not retune against this test set. After review, preregister
an independent corpus/budget study if justified. No GPU is needed for this step.

Reproduce with a clean e533fbe checkout and pinned Linux environment, running
experiment.py with --parcae-dir /workspaces/mythos-parcae-pinned,
--text research/mini_mythos/m2/evidence/tinyshakespeare.txt and --out in a NEW
directory. Use m2/download_text.py to fetch/hash-check the corpus. Set
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 TORCHDYNAMO_DISABLE=1. Replay adds --seeds 42
and another output directory. Never overwrite existing evidence.
