# Gate 2 Free Preparation Checklist

**Status: FREE PREP ONLY. USER AUTHORIZATION NOT YET GRANTED. NO GPU LAUNCHED.**

Pinned Parcae: `69284c13746e849104f738d6d1a347b1f457df76`
OpenMythos HEAD at prep: `e1a61083e28d0e68b2c99dad822671ced1c19ec8`

## Constraints

- Device (planned): 1× A100 SXM 80GB
- Platform (candidate): RunPod
- Rental window: ≤ 60 minutes
- This-run cost target: ≤ ¥700 (including extras)
- Cumulative GPU research budget cap: ¥5,000
- Do not launch, deploy, or rent until user explicitly approves.
- Prefer a rebuild or verified environment matching the pinned commit; do not blindly use image tag `sha-49c27cb` (different commit).

## Prepared (not executed)

| Item | File | Status |
|------|------|--------|
| Stage A config | `P1_C_GATE2_STAGE_A.yaml` | READY (tokenizer_path blank) |
| Stage B resume config | `P1_C_GATE2_STAGE_B_RESUME.yaml` | READY (ckpt path blank) |
| Alt tokenizer | generated locally earlier | AVAILABLE (vocab 489) |
| Precheck script | `p1c_precheck_launch_config.py` | PASS on CPU |

## Before any launch (requires user approval)

1. Record final RunPod quote and account balance.
2. Fill absolute `tokenizer_path` (ALTERNATIVE TEST TOKENIZER).
3. Confirm `LOCAL_WORLD_SIZE` or real GPU count.
4. Run Stage A with `exit_at_step=4`.
5. Record actual microbatch_step, optimizer_step, real `optimizer.step()` count, and checkpoint path.
6. Fill Stage B `resume_checkpoint_path`.
7. Resume and verify weights, optimizer, scheduler, RNG, data iterator position, and at least one real update.
8. Record batch skip/repeat behavior.
9. Stop immediately if cost or time limit is exceeded; save results, terminate Pod, delete unneeded storage.

## Not done

- No Pod started.
- No GPU rented.
- No training executed.
- Official tokenizer license remains BLOCKED.
- rngds experiment is not language learning.
