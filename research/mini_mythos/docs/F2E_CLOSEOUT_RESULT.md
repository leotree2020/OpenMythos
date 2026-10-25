# F2-E closeout

Status: **PENDING CHATGPT REVIEW**. E1–E5 LOCAL PASS. Not a final F2-E PASS.

## Delta

- Each recurrent mask now has an archived SHA-256.
- Checkpoint-on replay must be exactly 2. Replay 1 is rejected.
- Sampler exit and post-backward RNG are recorded and paired.
- Pre/post weight hashes and 74 gradient names/shapes are checked.
- `--fail-demo` returns exit 1 without a model run.
- E6 stays INCONCLUSIVE.

## Command

```bash
PYTHONPATH=/tmp/py311-pkgs /usr/bin/python3.11 \
  research/mini_mythos/tests/test_parcae_sampling_modes_cpu.py \
  --parcae-root /tmp/parcae-src \
  --output research/mini_mythos/gate2_2/evidence/f2e/b1_closeout/F2E_CLOSEOUT_RESULTS.json
```
