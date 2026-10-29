# P1-C Gate 2.2 — first native MuonAdamW CPU eager optimizer/resume evidence (2026-10-29)

## Scientific state

**PASS — precisely scoped native optimizer CPU-eager micro-experiment.** First execution of pinned original Parcae `MuonAdamW` in this P1-C research sequence to validate parameter updates and optimizer `state_dict` save/load across independent CPU Python processes. **NOT** official Parcae training entry, CUDA/compiled kernel, Lightning Fabric or G2 acceptance. Upstream and all mainline model/Oracle/Bench code untouched.

- Upstream: `sandyresearch/parcae`, commit `69284c13746e849104f738d6d1a347b1f457df76`, file `recpre/optim/muon_adamw.py`, exact Git blob `fb2cd5d9e6653f44200d59fcfe5c017f8d7bb82f`. The 5,900-byte file was byte-verified before every run; not altered. MIT licensed.
- Environment: Python 3.13.5, `torch 2.10.0+cpu`, Linux x86_64, one thread, deterministic algorithms, `TORCHDYNAMO_DISABLE=1` (native function bodies in eager mode, not compiled GPU kernels).
- Fixture: separate synthetic shifted next-token tiny neural network (NOT Parcae architecture), vocabulary 32, hidden 16, batch [2, 7], eight updates with cut after four. Original official optimizer class and `get_muon_param_groups`: two Muon matrix params, seven AdamW params.
- Seeds: 42, 20261029, 20261030; 5 fresh processes/seed = **15 subprocesses**; **39/39 explicit acceptance assertions PASS**. Continuous A (8 steps) and B (4 steps, save model+optimizer+RNG to disk, start new process, restore and run 4) have **exact per-step batch SHA-256, exact loss, exact all 9 parameter SHA-256 and exact optimizer state digest**. State had 23 slots.
- Negative controls: omitting optimizer state when loading, and one extra batch skip, each diverges on all **9/9 final parameter tensors** for all three seeds; no false PASS.
- Final loss (A/B same): seed 42 = 3.4723739624023438; seed 20261029 = 3.568131446838379; seed 20261030 = 3.4851253032684326. These are synthetic losses, not model-quality improvements.
- First attempt with native `@torch.compile` CPU/Inuctor timed out after 90 seconds before completing update: **BLOCKED** for compile path, not PASS. Switch to eager mode used original, unchanged optimizer function bodies.
- Interim first fixture assertion expected 6 AdamW parameters but actual official routing has 7: fixture FAIL corrected; full acceptance rerun PASS; original source never changed.

## Evidence and reproduction

Local-only complete archive `Mythos_P1C_Native_Muon_CPU_Eager_MIT_20261029.zip` SHA-256 `8269d134968459ea2c8398f7d718cbd0c67664fcd7a399af5c3400ff2c9227a1`, 44 ZIP entries (including original upstream MIT LICENSE) with internal checked SHA256SUMS manifest, containing byte-pinned source, test runner, validator, 15 full subprocess logs, raw per-mode JSON, three independent disk checkpoints, acceptance JSON/log, and detailed checkpoint. **The local scripts are not committed here; this branch is an evidence checkpoint only.** The source is also public at https://github.com/sandyresearch/parcae/blob/69284c13746e849104f738d6d1a347b1f457df76/recpre/optim/muon_adamw.py.

Acceptance JSON SHA-256 `00b8a7e6478c49bb077ab4737309447bd1fed5727d3e34067773e1761a9d08de`. Raw upstream source SHA-256 `c01b2c54a65e0102b5fa546ae9e8423194daa549619454438b3c9ae38d41a053`.

## Strict gates and next experimental step

**P1-C official full `scripts/train.py` + MuonAdamW + Lightning Fabric + actual CUDA compilation + rngds checkpoint resume numerical equivalence = NOT TESTED.** Previous P1-B native Parcae micro CPU and Gate 1 A100 AdamW mechanism smoke are separate completed experiments; PR #7 Gate 2.2 CPU model probe used AdamW, not native Muon. J1 direct 11 cases NOT TESTED, formal Oracle BLOCKED/NOT_READY, FORMAL_ACCEPTANCE_READY=False, G2 REAL BLOCKED; independent Grok review still DEFERRED.

NEXT: after explicit user approval of GPU rental/cost, run one **official-entry** minimal A/B/C (uninterrupted vs 4+resume vs extra-skip negative) using pinned Parcae, original MuonAdamW, true next-token shifted loss and a separately reviewed research-only iterator patch; compare per-step data SHA, loss, weights, scheduler, optimizer, RNG and checkpoints; report PASS/FAIL/BLOCKED with exact actual logs. Do not merge PR #7 or edit pinned upstream. No Guard V4.
