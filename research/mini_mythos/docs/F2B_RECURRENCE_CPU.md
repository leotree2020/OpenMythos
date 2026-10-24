# F2-B CPU recurrence probe

Status: **PENDING REVIEW**. Not a final PASS.

## Design

Fixed Parcae `69284c1`. No upstream edits. CPU float32, seed 42.

Config that yields the stated 247,936 parameters:
- n_embd=64, intermediate_size=128, heads=4/4
- vocab_size=128, padded_vocab_size=128
- prelude/core/coda = 2/2/2
- mean_recurrence=2, mean_backprop_depth=2
- recurrent dims aligned to 64/128
- attn_impl=sdpa

Pairs: (0,1), (0,2), (1,1), (2,2).
Core count is hooked on `update_recurrent_state`.
Causal tolerance is fixed at 1e-5 before running.

## Expected

- Default `state_init="like-init"` draws a new state each forward, so unseeded repeats differ.
- With the same seed before each forward: repeats are bit-exact, call count equals the sum of the pair, loss and grads are finite.
- (0,2) and (1,1) have the same forward math and different backward depth.
- Changing the last token must not change earlier logits under the same seed.

## Result

See `research/mini_mythos/gate2_2/evidence/f2b/F2B_RESULTS.json`.

- Unseeded (1,1) logit max abs: 0.341
- All four pairs: repeat max abs 0.0, calls correct, finite
- (0,2) vs (1,1): logit max abs 0.0, grad max abs 0.344
- Causal earlier-token max abs: 0.0
- train vs eval with fixed seed: 0.0

Overall in JSON: PENDING REVIEW.
