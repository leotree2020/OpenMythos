# P1-U1 Upstream Confirmation and Native Evidence Gap

## A. Tokenizer identity and license

Source: https://github.com/sandyresearch/parcae/issues/2#issuecomment-4313382732
Author reply recommends `SandyResearch/parcae-tokenizer` and calls it open source.
No revision, hash, or LICENSE text is in that comment.

| Question | Result |
|----------|--------|
| Author named the official tokenizer repo | PASS |
| This revision `6247b5d0` is the parcae-small training asset | BLOCKED |
| Explicit license for research training, modification, redistribution | BLOCKED |

"Open source" is not a license grant. Parcae MIT does not cover this file.

Inquiry draft, not sent:

> We use SandyResearch/parcae-tokenizer revision 6247b5d0592876b73660f34c2dd16c9db9e9045c. tokenizer.json SHA-256 is e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77. Please confirm this revision is the tokenizer used for parcae-small-140m, and that independent research training from random weights, plus local config additions for BOS/EOS/PAD, is permitted. The repo has no LICENSE file.

## B. Native Evidence gap

Existing pieces:
- `collect_native_evidence.py` can hash command/config/checkpoint and refuse GPU_RUNTIME without a real run.
- `extract_evidence.from_objects` can export model/optimizer/scheduler/RNG from live objects.
- `verify_provenance.py` rejects GPU_RUNTIME without CUDA provenance.
- CPU object tests exist. They are not a native `train.py` run.

Not wired into frozen `scripts/train.py`:
- per-batch SHA, loss, optimizer update_count
- before_save / after_load RNG
- MuonAdamW sidecar checked against a native checkpoint
- scheduler state from the real train loop

RNG capture points in frozen train.py:
- before_save: inside `maybe_save_checkpoint`, where `state["rng_state_torch"]` is set just before `fabric.save` (around line 1536/1556)
- after_load: after the resume block applies `rng_state_*` (around lines 1403-1415), before the next forward

Still simulated or caller-supplied: live batch hash, loss sequence, update_count, GPU_RUNTIME source. `gpu_confirmed` is not proof of a GPU run.

## Minimal next integration

External wrapper only. Do not edit frozen Parcae.
Hook the existing save and resume points, write sidecars, then run the existing provenance check.
Acceptance: a real run directory produces evidence the frozen comparator can read, with no hand-filled `native_entry_artifact`.

## Verdict

| Item | Result |
|------|--------|
| Official repo named by author | PASS |
| Exact revision identity | BLOCKED |
| License | BLOCKED |
| Native Evidence collector exists | PASS (CPU objects only) |
| Native train.py integration | BLOCKED |
| Overall P1-U1 | BLOCKED |

## Next stage

Do not start GPU or formal training.
Need either a license confirmation, or an explicit user decision to proceed under the current BLOCKED license.
Native Evidence integration needs a separate authorization.
