# F2-D B1-R1

Status: **PENDING CHATGPT REVIEW**. D7 was not run.

## Guards

- Weight hash is computed from sorted tensor name, shape, dtype, and bytes.
- Both runs of D1–D6, including baselines, go through the same evaluator.
- Missing gradient names return structured FAIL, not KeyError.
- Negative cases call the same evaluator: bad gradient, missing replay, changed RNG, missing name.

## Replay

Same six cells, seed 42, frozen tolerances. Local status PASS. Exit 0. Old B1 evidence is unchanged.
