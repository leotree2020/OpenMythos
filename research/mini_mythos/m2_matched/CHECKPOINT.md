# M2 matched pilot checkpoint — pre-training freeze

Previous PR head: d3209effa135d55605ea82efa1152133267ea1aa. PR #12 remains Draft.
Read PROTOCOL.md and frozen_config.json before running.

Calibration PASS: GPT FFN 60, 65,344 parameters, 74,317,824 counted FLOPs/step;
Parcae 60,224 parameters, 80,412,672 counted FLOPs/step. Max/min ratios
1.0850159404888418 and 1.082010582010582 both satisfy the predeclared 1.10 limit.
No language quality was inspected during selection. Local seed-42 preflight PASS
for both official models, including shared IO initialization, native CE,
causality and exact frozen counts. See evidence/local_preflight.json.

Formal Linux training: NOT TESTED. Quality hypothesis: NOT TESTED.
Fresh-process replay: NOT TESTED. Grok cross-review: NOT TESTED.
Local calibration/preflight environment: Python 3.12.14, torch 2.9.0+cpu,
NumPy 2.2.6, einops 0.8.0. Upstream pin remains clean and unchanged.

Next: commit this protocol, harness and calibration before formal training;
use Linux Python 3.12.x/torch 2.11.0/NumPy 1.26.4/einops 0.8.0, CPU only.
Run three seeds and fresh-process seed 42 replay into separate new evidence
directories. Save JSON/logs and model weights; evaluate each gate separately.

```bash
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 TORCHDYNAMO_DISABLE=1 \
python research/mini_mythos/m2_matched/experiment.py \
  --parcae-dir /path/to/clean/pinned/parcae \
  --text research/mini_mythos/m2/evidence/tinyshakespeare.txt \
  --out /path/to/new/evidence/pilot.json
```

The corpus can be obtained using the existing m2/download_text.py hash-checked
downloader. Replay uses the same command plus --seeds 42 and a separate output
directory. Do not overwrite original M1 or earlier M2 evidence.
