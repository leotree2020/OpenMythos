# CPU Probe Reproduction

## Command

```bash
PYTHONPATH=/tmp/py311-pkgs:/tmp/parcae-src python research/mini_mythos/gate2_2/cpu_model_probe.py
```

Exit code: 0

## Environment

- Python 3.11.2
- PyTorch 2.14.1+cpu
- Parcae `69284c13746e849104f738d6d1a347b1f457df76`
- OpenMythos HEAD at run: `9f6af21c4783f315808acda0502916dae5476628`

## Pre-declared tolerance

`TOL_ABS = 1e-5`. Not adjusted after seeing results.

## RNG audit

Recurrence sampler in `randomized_iteration_sampler`:

```python
seed_n = 514229 + self.step
seed_k = 317811 + self.step
n_generator = torch.Generator(device="cpu")
n_generator.manual_seed(seed_n % (2**31 - 1))
```

`self.step` is a plain attribute, not in `state_dict`. Official train.py sets `model.step = state["microbatch_step"]` on resume.

- Python / NumPy / global torch RNG: snapshotted in the probe; not the recurrence source.
- Recurrence RNG: derived from `model.step`.
- CUDA RNG: NOT APPLICABLE.

## Results

| Group | Data hash vs A | Weight n_diff vs A | Status |
|-------|----------------|--------------------|--------|
| A continuous | — | — | PASS |
| B full restore incl. step | match | 0 | PASS |
| C no step restore | match | 42 | PASS (differs, as required) |
| D extra skip | differ | 42 | PASS (differs, as required) |

Causal: B matches A and C does not → missing `model.step` restore is sufficient to explain the weight divergence.

## Not claimed

Official `scripts/train.py` path remains BLOCKED on CPU.
