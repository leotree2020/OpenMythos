# Independent Grok review request

Review https://github.com/leotree2020/OpenMythos/pull/12, focusing on
research/mini_mythos/m2_matched. Protocol/config/harness were frozen before
training at e533fbe36aaf18fd551ee21e5c2d20551b5a2e16. Raw Linux training and
fresh-process replay evidence was added in 5c5d3ad. Upstream is unchanged.

Read PROTOCOL.md, experiment.py, frozen_config.json, audit_results.py,
CHECKPOINT.md, evidence/audit.json, evidence/linux_e533fbe/pilot.json and
replay42/pilot.json. Inspect weight files and SHA256 manifest where possible.

Independently assess:

1. Does calibration satisfy both <=10% budgets without quality-based selection?
   Are supported-op FLOPs labelled honestly?
2. Are causal targets, byte splits, complete held-out windows, RNG isolation,
   paired initialization and exact batch/token matching correct?
3. Are native recurrence/backprop settings faithful to the pinned Parcae?
   Identify remaining confounders and training/evaluation state differences.
4. Do raw artifacts support learning, replay and integrity statuses?
5. Test NLL deltas are +.03655765, +.00650032, +.01326738; mean +.01877512.
   Is exploratory tolerance PASS accurately reported, without claiming
   superiority or statistical noninferiority?

Return PASS / FAIL / BLOCKED / NOT TESTED per item, concrete evidence, exact
file/line references and minimal CPU experiments for disagreements. Do not
accept ChatGPT's conclusion merely because it appears in the checkpoint.
No actual Grok response has been obtained. This request is not a review.
