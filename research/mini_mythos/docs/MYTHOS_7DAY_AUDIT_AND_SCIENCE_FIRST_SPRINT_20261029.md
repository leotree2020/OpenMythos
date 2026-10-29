# Mythos science-first realignment — 2026-10-29

**Purpose:** restore the original OpenMythos→Mythos objective: prove correct open-source baselines, then quantify whether recurrence/dynamic depth improves heldout quality or per-compute efficiency, then separately explore memory/new architecture. **Not** maximize CPU guard/docs PASS or reverse engineer proprietary Claude architecture. **Review document only; not a model experiment.**

## Seven-day audit (Asia/Tokyo, Oct 23–29)

Observed on the ancestor history of `d1-r3-a-cpu-003-e1a-g2-j1-direct-schema-differential-20261029@ec9e610bc17a7a6100b99736f70d09fcd21762a0`: **380 commits**, of which **240 use a docs( prefix** (~63%). This is one ancestry slice, not a cross-branch unique repository total.

| Day | Count / docs prefix | Model/experiment progress | Cost or gap |
|---|---:|---|---|
| 10/23 | 23 / 14 | Official Parcae P1-C audit; A100 144M-parameter 4-step AdamW synthetic mechanism smoke, limited PASS; tokenizer/config preparation | No official train.py/Muon optimizer |
| 10/24 | 69 / 19 | rngds + StatefulDataLoader resume extra-skip reproduced; isolated CPU patch; model-level AdamW resume equivalence; native Parcae F2-B recurrence and F2-C selected finite-difference gradient checks | No official training entry / generalization results |
| 10/25 | 69 / 44 | F2-D RNG/checkpoint/depth and F2-E E1–E5 sampling masks scope PASS (E6 INCONCLUSIVE); F3-A six-step native micro-model AdamW training and CPU restore PASS | No heldout quality or balanced Transformer baseline |
| 10/26 | 25 / 15 | F3B D1 R3 runner/supervisor specification, limited CPU checks | Reliability infrastructure, indirect science |
| 10/27 | 51 / 26 | D1 process predicate CPU-001 1860 and CPU-002 430 controlled trials, G0 REAL 17/17 | Real model/D1 text training still absent |
| 10/28 | 137 / 120 | G1 4 negative cases, scoped evidence-reviewed PASS; J1/IV-S independent unit and boundary work | G2 REAL BLOCKED, 11 native direct J1 tests NOT TESTED; documentation overhead too high |
| 10/29 | 6 / 4 in this ancestry | Separate local Guard V1–V3 11/28/39 unit PASS; shared-layer toy 3 seeds; **native unmodified Parcae MuonAdamW CPU-eager 15 subprocesses/39 assertions PASS**, PR #10 Draft | No official Parcae train.py + Fabric + CUDA/Muon restore; no fair quality-vs-FLOPs evidence |

**Status source limits:** F2-B/C/D/E and F3-A accepted only their frozen micro-scopes, generally from Grok-run evidence plus ChatGPT independent source/hash/math review, not fresh executions in this audit. The Muon test ran locally and includes independent process traces, but used a **toy network** with official optimizer under eager CPU, not native full training. R2 Gate N/O/P and P1-B were completed earlier and must not be reimplemented. Other D1/Guardian-scoped successes do not imply scientific/learning performance. Frozen original upstream Parcae and R3/Oracle remain unmodified.

## Priority ruling (no automatic criteria changes)

- **KEEP/REUSE:** original pinned Parcae P1-B; native F2-B/C/D/E, F3-A evidence; R2 data correctness; P1-C Gate2 rngds continuity and native optimizer state; one reproducible stable standard Transformer baseline.
- **IMMEDIATE SCIENCE:** actually **train** standard Transformer vs pinned native Parcae on identical controlled dataset/tokenizer with heldout NLL/PPL, real gradient and optimizer updates, identical train tokens, and two distinct fairness protocols (same tokens vs comparable FLOPs). Only after A/B, test dynamic depth as a single variable.
- **STOP NEW WORK:** Guard V4/V5, repeated J1 proof-of-proof, repetitive checkpoint revisions, bulk draft branch merges. Keep G2/J1 BLOCKED in their own formal lifecycle; do **not** bypass their frozen criteria, but do not make them a prerequisite for unrelated safe single-process local CPU model pilots.
- **NO CLAIMS:** neither 59.8% toy stored-parameter decrease nor increased recursion shows better inference, memory, FLOPs or difficult reasoning. Official `scripts/train.py`+MuonAdamW/CUDA restore NOT TESTED. PR #6/#7/#10 remain Draft.

## Hard deliverables (JST deadline = evidence or explicit blocker, not guaranteed PASS)

| Milestone | Deadline | Must actually deliver | Gate and fallback |
|---|---|---|---|
| M0 audit and priority freeze | 10/29 | One Git checkpoint + machine-readable board | DONE only for project audit |
| M1 first real CPU A/B learning | 10/30 | Standard Transformer vs pinned native Parcae, identical frozen synthetic/text split, first seed, train loss + separate validation NLL, source/input hashes, actual optimizer update | 2-hour blocker timebox; if no full checkout, BLOCKED and capture actual error |
| M2 replicated CPU quality/efficiency pilot | 11/02 | At least 2 seeds, actual heldout NLL/PPL/params/CPU step time/peak RAM, two comparison regimes; 3 seeds required before positive superiority claim | GO/NO-GO, not automatic success |
| M3 official entry minimal GPU resume | 11/05 | One resource-bounded pinned Parcae `scripts/train.py` + MuonAdamW + Lightning Fabric `rngds` A continuous/B resume/C extra-skip negative, actual data/LR/weights/optimizer/RNG/VRAM and spend | User authorized continuation but no accessible GPU runner here: BLOCKED_RESOURCE if unprovisioned; budget ceiling ¥5,000 cumulative, target ≤¥700/run, no unattended rental |
| M4 first quality–compute comparison | 11/08 | A/B learning-quality-to-cost curve; optional C dynamic depth pilot only after accepted A/B | No overstated claims from 1–2 seeds |
| M5 bounded science GO/NO-GO | 11/10 | Independent ChatGPT/Grok review of actual results, one checkpoint, next single-variable hypothesis | P3/P4/P5 not unlocked without valid gates |

## Execution rules and next instruction

Every run needs **purpose / frozen SHA/seed/env/input / expected / actual / full stdout-stderr / exit / PASS-FAIL-BLOCKED-NOT TESTED / Git status**. Multiple seeds/heldout metrics gate claims; actual GPU time/cost required before performance claims. Never change original Parcae, freeze R3/J1 criteria, Oracle, or architecture to make a microtest PASS. ChatGPT/Grok differences are archived, resolved via minimal controlled experiment only. No daily documentation commits absent real evidence: machine board status is the daily track; per-stage checkpoint only.

**Next command-level task (M1):** In authorized CPU Codespaces, check out pinned native Parcae and a clean OpenMythos research comparison branch, lock local dataset+tokenizer hash and standard transformer config; run one true optimizer-update learning curve and validation NLL for both original open-source architectures. The experiment is NOT TESTED until original execution logs exist.

**GitHub Issues is disabled (API 410)**; use the adjacent JSON execution board and this one draft PR for accountable state instead of enabling Issues or creating another Guard. Full detailed Chinese local audit artifact SHA-256: `86b94e73644d602ce858a0de22b65e5b7b3f0cb2371ae876105b8acb1694af88`.