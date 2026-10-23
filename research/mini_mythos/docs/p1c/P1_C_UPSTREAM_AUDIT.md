# P1-C Upstream Parcae Training Audit

**Status**: Planning / Source Audit only. No GPU training executed.
**Base**: OpenMythos `mini-mythos-research` @ `107c966a4046ebe3b596ae17fd2db3d39e05e768`
**Upstream Parcae**: `sandyresearch/parcae` @ fixed commit `69284c13746e849104f738d6d1a347b1f457df76`
**Focus config**: `launch_configs/parcae-small-140m.yaml`

## VERIFIED from source / config

- Model name: `parcae-small-140m`
- Architecture: Prelude / Core / Coda (from README table): 2 / 2 / 2 layers, dim 768, mean recurrence 8
- Vocab size overwrite: 32768
- Block size: 2048
- Optimizer: MuonAdamW (lr 8e-3, betas [0.8, 0.95], muon_lr 8e-3, muon_momentum 0.95, muon_wd 0.2)
- LR schedule: trapezoid, warmup_steps 0.0, cooldown_steps 0.5, min_lr 0, grad_clip 1.0
- Precision: bf16-mixed (fabric_precision)
- World batch size: 256, micro batch size: 32
- Fabric: ddp, compile_model true
- Data: pqds-pure on FineWeb-Edu paths (train/val under `/resource/data/fineweb-edu-100b-shuffle/`)
- Tokenizer path: `/resource/tokenizer/parcae_tokenizer`
- Partial depth eval: [1, 2, 4] + automatic mean_recurrence
- Logging / checkpoint: log every step, save every 1024, eval every 512

## ESTIMATED / NOT TESTED

- Exact parameter count (README lists ~140M)
- Mean recurrence / backprop depth / Poisson sampling details (present in code, not fully expanded here)
- DiagonalInjection decay schedule (known from P1-B ~0.447 initial)
- Actual GPU memory, throughput, FLOPs for full run
- Dataset download size and license confirmation for FineWeb-Edu

## Notes

This audit prioritizes the official small config. Full source walk of recurrence sampling, state injection, and telemetry is deferred to implementation of Stage 1 smoke once GPU is authorized.

Do not modify upstream Parcae mathematics.
