# Mythos M1/M2 checkpoint — 2026-10-29

Latest continuation: ../m2_matched/CHECKPOINT.md records the new pre-training
calibration, actual Linux six-run matched pilot and fresh-process replay.
The original pilot findings below remain unchanged.

## Git and scope

Verified GitHub PR #12 open, Draft, base mini-mythos-research @107c966,
initial HEAD c639112fdab8a5f69951835efe6862e2ed6aed29. M1 clone-order fix committed
as 7fd7ae709b2fa6ed12de763efe614d576c3f9d14 on the same branch.
M2 code/protocol/evidence are the next isolated research commit on that branch.
No merge, no Guard expansion, no GPU. Synced sources/ untouched.
Upstream checked out at 69284c13746e849104f738d6d1a347b1f457df76 with no tracked
changes before/after M2. Native GPT and Parcae source remain unchanged.

## M1 evidence status

User supplied terminal transcripts for all three seeds. Subsequently, the user
provided Codespaces access and the original archive was retrieved through the
authenticated browser terminal, transferred losslessly and independently audited.
Six full JSONs remain in the user's Codespaces
/tmp/mythos-m1-pr12/research/mini_mythos/results/m1_cpu.
Archive /workspaces/OpenMythos/mythos_evidence/M1_CPU_3seeds_20261029.tar.gz
has independently verified SHA256
f5542ebd2e92dd165b5e3155f7496c3698924b834f14b11e00a391366a54ed4c.
Archive integrity and six-JSON consistency audit PASS. The 3,895-byte archive,
verbatim member JSONs and audit.json are preserved in
../m1/evidence/archive_audit_20261029/. Train/val/test ID hashes were independently
regenerated. All six reports meet the .05 NLL decrease gate. Actual weights and
per-step gradients are absent, so those remain NOT TESTED; this is not a rerun.

M1 shell regression PASS: bash syntax, fresh clone, existing clean checkout,
and existing dirty checkout rejected with user modification preserved. Local Git
fixture exercises the exact setup block; this does not claim a full Codespaces
M1 rerun. See evidence/m1_setup_test.json.

## M2 actual run

Protocol/criteria were in run_cpu.py before training. See PROTOCOL.md for purpose,
environment, input, expected behavior and limitations. 9/9 training runs PASS:
3 seeds x GPT4/GPT3/Parcae, finite gradients/loss, weights updated, validation
NLL decreased >=.01, exactly 30,720 input/target tokens per arm and matched batch
hashes within each seed. Evidence/pilot.json and pilot.log are actual CPU outputs.
Independent-process seed-42 replay PASS for all three arms: exact initial/final
weight hashes, initial/final validation NLL, test NLL, batch hashes and FLOPs.
See replay_seed42.json/log and replay_check.json; timing is not an equality gate.

| Arm | Parameters | Counted training FLOPs | Mean test NLL (3 seeds) |
|---|---:|---:|---:|
| official GPT, 4 blocks | 66,368 | 9,106,882,560 | 2.81419055 |
| official GPT, 3 blocks | 58,048 | 7,219,445,760 | 2.78496758 |
| official Parcae, 4 block passes | 60,224 | 9,649,520,640 | 2.80967919 |

Fairness status FAIL against the predeclared simultaneous 10% gates:
GPT4/Parcae compute ratio=1.05958549 PASS, parameter ratio=1.10201913 FAIL.
GPT3/Parcae parameter ratio=1.03748622 PASS, compute ratio=1.33660131 FAIL.
Do not relax the threshold to hide the failure. These data do not establish
architectural superiority. Evaluation covers only the first <=512 bytes of each
held-out interval; native initialization differs; only supported matmul FLOPs are
counted. No inference speed, GPU memory, large-scale quality or ACT claims.

The first attempt failed on GPT optional fused-head construction before training;
preserved as attempt01_fused_head_error.log. Corrected experiment configuration
uses the official non-fused GPT path, without editing upstream. Local dependencies
are Python 3.12.14/torch 2.9.0+cpu/NumPy 2.2.6/einops .8.0: outside M1 pinned
Linux environment, particularly upstream NumPy<2. The subsequent Linux replay
below resolves the missing pinned-environment execution, not the fairness failure.

## Codespaces Linux replay — completed 2026-10-29

Code: 45038f602470001e0bf82d970fc67d1763477871, isolated detached worktree
/tmp/mythos-m2-linux-45038f6. Existing M1 worktree and evidence were preserved.
Upstream: /tmp/mythos-m1-parcae-clean-20261029 at 69284c1, tracked status clean.
Environment: existing /tmp/mythos-m1-cpu-venv, Python 3.12.3, torch 2.11.0+cu130,
NumPy 1.26.4, einops 0.8.0, Linux, CPU only, one thread. No installation or GPU.
Purpose: rerun the unchanged M2 protocol in the existing pinned Linux environment.
Expected: same per-run learning gates and separate fairness assessment; no new
cross-environment numeric-equality threshold was introduced after observing data.

Actual: 9/9 learning runs PASS, exact matched batch hashes/tokens/params/counted
FLOPs against Windows. Linux mean test NLL: GPT4=2.8141905467,
GPT3=2.7849675814, Parcae=2.8096792698. Maximum test NLL absolute difference
across environments is 2.384185791015625e-7 (descriptive, not a preregistered
equivalence PASS). Simultaneous 10% fairness gates still FAIL.
Original JSON, log, exit code, provenance and cross-environment comparison are in
evidence/linux_45038f6/. Remote originals are under
/workspaces/OpenMythos/mythos_evidence/m2_linux_45038f6/.

Native source stayed clean. The old /tmp/mythos-m1-official-parcae incomplete
clone was not repaired or used; the separately verified clean checkout was used.

## Open items and next experiment

Grok independent cross-review NOT TESTED; no connected Grok execution channel.
Keep PR Draft. Review PROTOCOL.md, run_cpu.py, pilot.json and failure evidence.
Codespaces browser access now works. No archive upload is needed: M1 bytes have
been obtained and audited. The remote browser was kept in restricted mode.

Next instruction: review this checkpoint first. Obtain Grok review of the M1
archive audit and native initialization, byte split,
FLOP accounting and 10% gates, preserving disagreements. Before further training,
perform a CPU-only architecture/configuration calibration using parameter/FLOP
counts WITHOUT quality inspection; freeze a new protocol meeting both gates (or
predeclare distinct compute/parameter comparisons). Then run a new pinned Linux
three-seed experiment with larger held-out coverage. Do not change upstream.
