# F3-B D1 / D2 / D3 Draft Gates

Status: **DRAFT**. Not authorized to run.

## D1 — data path

Purpose: read pinned WikiText-2, encode with the train-only tokenizer, and resume without skip or repeat.

Pass: uninterrupted and restored streams match on document ids and token hashes. Train/val/test stay separate. Tokenizer was not fit on test.

Fail: missing, duplicate, or polluted batches.
Blocked: dataset revision or license cannot be pinned.

## D2 — real-text train

Purpose: random-init 2/2/2 model, real batches, AdamW, linear scheduler, checkpoint, resume.

Pass: finite loss and gradients, at least one parameter changes when LR > 0, resume matches within the frozen `1e-6` / `1e-5` tolerance, RNG and step match exactly.

Not a language-ability claim.

## D3 — held-out quality

Purpose: compare recurrent and standard Transformer on the same val/test.

Pass: report NLL, PPL, tokens, and cost. Require more than one seed before any architecture claim.

Do not merge D1, D2 and D3 into one unreviewed run.
