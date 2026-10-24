# Gate 2.1 CPU Reproduction

## Environment

- Python 3.11.2
- PyTorch 2.14.1+cpu
- torchdata 0.11.0+cpu
- StatefulDataLoader: importable
- Parcae: `69284c13746e849104f738d6d1a347b1f457df76`
- OpenMythos base: `e1a61083e28d0e68b2c99dad822671ced1c19ec8`

## Command

```bash
PYTHONPATH=/tmp/py311-pkgs python research/mini_mythos/gate2_1/test_resume_continuity.py
```

## Notes

Official `RandomTokensDataset` preallocates 1e6 rows and was killed in this environment.
The test uses `MiniRNGDS` with the same `idx` / `state_dict` / `load_state_dict` contract and a small table.
This is sufficient to reproduce the skip; it is not a full ParquetStreamPure test.
