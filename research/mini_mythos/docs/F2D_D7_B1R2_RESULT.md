# F2-D D7 B1-R2

Status: **PENDING CHATGPT REVIEW**. Not a final F2-D PASS.

## Guards

- Every S1–S6 run goes through the same sampler/RNG function.
- Conditions for train, step, scheme, input and weights are checked there.
- S6 also checks unchanged weights after forward.
- Bad step, scheme, input and weights are rejected by that function.
- Both sides of each gradient comparison are checked.

## Replay

Same S1–S6. Local status PASS. Exit 0. Old evidence is unchanged.
