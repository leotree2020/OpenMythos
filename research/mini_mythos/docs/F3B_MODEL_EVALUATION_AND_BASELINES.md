# F3-B Evaluation and Baselines

Status: **DESIGN**. Not a result.

## Metrics

Report separately:
- Validation NLL and test NLL.
- Token-level perplexity. Do not mix with byte-level PPL.
- Train/validation gap.
- Seed repeats when a run is authorized.

Generation quality is qualitative at this size. Mark complex reasoning NOT APPLICABLE until the model is large enough.

## Efficiency

Record parameters, tokens, CPU peak memory, step time, and a stated FLOPs estimate. Mark unmeasured numbers ESTIMATED. Separate stored parameters from recurrent compute.

## Fair controls

A: standard Transformer.
B: fixed-depth recurrent Transformer.
C: dynamic depth, only after its own gate.

Two comparisons, not one:
1. Same training tokens.
2. Closest practical FLOPs budget.

Same data, same tokenizer, same optimizer family, independent val/test. Do not claim architecture superiority from one metric.
