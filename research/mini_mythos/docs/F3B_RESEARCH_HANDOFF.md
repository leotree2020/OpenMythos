# F3-B Handoff

Status: **F3-B DESIGN COMPLETE / PENDING CHATGPT REVIEW**.

## State

- HEAD at design start: `3cba0ee871efdcc47b9e0b2ddc493e471c822932`
- F3-A fixed-input CPU lifecycle: PASS/CLOSED for that scope
- Official tokenizer: BLOCKED
- FineWeb metadata gates: evidenced
- FineWeb row streaming and real training: NOT TESTED
- Dirty file kept: `research/mini_mythos/gate2_1/TEST_RESULTS.json`

## Recommendation

First controlled experiment, after approval: D1 on pinned WikiText-2 with a train-only small tokenizer. No GPU. No model training until D1 is reviewed.

## Cost

D1 is CPU-only and small. D2 stays on the 247936-parameter model. D3 and any GPU pilot need a separate budget. Current GPU cap remains ¥700 per run and ¥5,000 cumulative, and is not authorized here.

## Risks

- Official tokenizer license still BLOCKED.
- FineWeb row resume is not proved by metadata tests.
- Python 3.14 fork warning from Gate Q does not apply to a single-process D1.
