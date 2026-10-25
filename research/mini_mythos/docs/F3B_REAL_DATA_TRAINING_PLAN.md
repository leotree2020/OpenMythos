# F3-B Real Data Training Plan

Status: **DESIGN / PENDING CHATGPT REVIEW**. Not a result. No training was run.

## Goal

Move from fixed synthetic tokens to real text, then measure prediction quality. Loss drop alone is not language ability.

## Recommended first data

WikiText-2 raw (`wikitext`, config `wikitext-2-raw-v1`).

Why:
- Public, version can be pinned.
- Official train / validation / test split.
- Small enough for a CPU correctness run.
- Clearer license than the unconfirmed official Parcae tokenizer.

Do not use the test split to train the tokenizer or the model.

FineWeb-Edu `sample-10BT` remains the later scale candidate. Its HF commit `87f09149ef4734204d70ed1d046ddc9ca3f2b8f9` and 14-file inventory are already recorded. It is not the first CPU experiment.

## Tokenizer

Official Parcae tokenizer stays BLOCKED on license and exact training-asset identity. Do not treat it as available.

Recommended path for D1/D2:
- Train a small BPE on the WikiText-2 train split only.
- Target vocab 4096 for the micro stage. Record the actual size.
- Set BOS/EOS/PAD explicitly. Prefer PAD as ignore index, not BOS.
- Save tokenizer.json SHA-256.
- Mark it `ALTERNATIVE RESEARCH TOKENIZER`, not an official Parcae reproduction.

The existing 489-vocab smoke tokenizer stays smoke-only.

## Model

Keep Prelude → Recurrent Core → Coda. Start from the verified 2/2/2 CPU model, 247936 parameters, random init. No pretrained weights.

## Levels

| Level | Purpose | Run now |
|---|---|---|
| 1 | CPU correctness on real text | Not authorized |
| 2 | Small held-out prediction check | Not authorized |
| 3 | GPU pilot | Separate approval |

## Not in this plan

MuonAdamW GPU, official tokenizer, `scripts/train.py` end to end, and language ability claims stay NOT TESTED until their own gates.
