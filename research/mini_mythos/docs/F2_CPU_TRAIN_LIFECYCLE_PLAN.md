# Native Parcae CPU Training Lifecycle Plan

Status: **DESIGN ONLY**. Not authorized to run. Not a result.

## Goal

From random weights, check one native path:

Forward → Loss → Backward → Optimizer → Scheduler → Checkpoint → Resume

## Frozen scope

- Parcae `69284c13746e849104f738d6d1a347b1f457df76`
- 2/2/2 micro model, 247936 parameters, CPU float32 SDPA
- No pretrained weights
- No GPU
- No architecture change

## Checks to freeze before a run

1. Loss and all gradients are finite.
2. Optimizer step changes at least one parameter.
3. A short controlled run shows non-increasing loss under a fixed seed. This is not a language-learning claim.
4. Scheduler step and learning rate match the native rule.
5. Checkpoint stores model, optimizer, scheduler and RNG.
6. Resume from that file matches an uninterrupted run at the next step, within a predeclared tolerance.
7. Same seed repeats.

## Not in this plan

MuonAdamW GPU step, CUDA RNG, official tokenizer, native train.py end to end, and Gate 2.2-C stay NOT TESTED until separately authorized.

## Next

Wait for ChatGPT review of the F2-E closeout. Do not run this plan yet.
