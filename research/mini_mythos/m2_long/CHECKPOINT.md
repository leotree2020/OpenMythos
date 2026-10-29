# M2-L CPU long-run stage checkpoint — 2026-10-29

## Status (exactly at protocol/code freeze; no model execution yet)

**M2-L MODEL TRAINING: NOT TESTED.** Evidence of a GitHub commit or executable script is **not** a passing training experiment. No 120/480/1920 learning-curve values have been obtained here. No GPU rented. Upstream code unchanged. M1/M2 matched original evidence remains unchanged in PR #12.

## Inputs and Git provenance

- Main research repo: `leotree2020/OpenMythos`.
- This isolated branch: `mini-mythos-m2l-long-curve-cpu-20261029`, forked from Draft PR #12 at base **`934bc12c2f5737cd233cf8076d820435b95280a8`**. Never modify `mini-mythos-research` or native upstream during this experiment.
- Protocol frozen before M2-L model training: **`3bf4be4b8463d13ae83636c977fb89ac66862ee9`**.
- Runner version after safeguards: **`907bd28e92fbfaf81d11d34d3f871de26f0a346e`**.
- Codespaces launcher: **`a10a83bd88e3ed838aa4ef831840bd117f911645`**.
- Grok review archived from user (not connected Grok execution): **`7395626e1070d6fb85a41fe11ff3dd54ca1e4ff9`**.
- Official native GPT+Parcae pin: **`69284c13746e849104f738d6d1a347b1f457df76`**.
- Reference matched M2 training data `research/mini_mythos/m2_matched/evidence/linux_e533fbe/pilot.json` (no reference quality-based model selection). GPT FFN60, Parcae FFN64 with `[0,2]`. Preserve historical original fair-pilot positive and negative results.

## Purpose, environment, inputs, expected result

See [PROTOCOL.md](PROTOCOL.md). Purpose: test whether recurring architecture's validation NLL gap improves after **continuous** fixed-budget learning at 120, 480, and 1920 steps. CPU Python3.12/torch2.11.0+cpu/NumPy1.26.4/einops0.8.0, one thread. Fixed Tiny Shakespeare train/val bytes. Fresh immutable independent Alice out-of-domain heldout SHA256 `146e69455b17fac23bee136d0121ced326e0b99caf206df0281cb67241963875`, evaluated only once after all six runs.

Predeclared expected acceptance, **NOT YET ACTUAL OUTCOMES**:
- First 120 steps reproduce every saved M2 matched loss/gradient and weight/validation/batch hash **exactly**.
- All six official-model training trajectories run 1920 finite steps, with three checkpoints and full model/optimizer/CPU RNG snapshots.
- Max/min parameter and counted FLOP ratios <=1.10, matching fixed calibration.
- 1920-step validation mean Parcae-minus-GPT NLL <=+.02 and each seed <=+.05 as an *exploratory*, non-statistical tolerance. **This may FAIL and must be preserved unedited.**
- Alice final OOD scores are descriptive only, never a superiority/quality PASS.
- Real inference latency, GPU memory, ACT, reasoning and P2 efficiency superiority: NOT TESTED here.

## Actual results and outstanding gates

| Gate | Status | Evidence |
|---|---|---|
| Freeze-before-training protocol | PASS (Git commit) | 3bf4be4 and PROTOCOL.md |
| Isolated source and pinned-model paths in scripts | PREPARED, NOT TESTED | experiment.py, run_codespaces_cpu.sh |
| Local Python syntax + pinned remote runtime | NOT TESTED | Must run `python -m py_compile` and pinned Linux checks |
| Exact historic M2 120-step replay | NOT TESTED | Expected new `pilot.json` and checkpoint hashes |
| 120/480/1920 continuous training x six | NOT TESTED | Expected per-arm JSON, torch .pt checkpoints |
| Validation tolerance at 1920 | NOT TESTED | No new NLL measurements yet |
| Independent OOD Alice final evaluation | NOT TESTED | Sealed input source; no model scores yet |
| Robust interruption/resumption parity | NOT TESTED | Snapshots supplied; exact resumed vs uninterrupted behavior unverified |
| Grok review of M2-L implementation | NOT TESTED | Prior Grok M1/M2 audit user supplied; no Grok M2-L review yet |

## Next single execution instruction — user Codespaces terminal

These commands run only in the **user's Codespaces** because this session's local Python environment does not have the pinned Parcae checkout and cannot directly execute shell commands in that Codespace. No remote training or GitHub Actions run is claimed here.

```bash
cd /workspaces/OpenMythos
git fetch origin mini-mythos-m2l-long-curve-cpu-20261029
git worktree add --detach /workspaces/mythos-m2long-20261029 FETCH_HEAD
cd /workspaces/mythos-m2long-20261029
bash research/mini_mythos/m2_long/run_codespaces_cpu.sh
```

Actual experiment output is saved persistently to
`/workspaces/OpenMythos/mythos_evidence/m2_long_v1`. The launcher verifies/checksums both corpus inputs, prevents upstream modifications and uses the existing pinned CPU virtualenv. If paths differ, set `M2_CPU_PYTHON` or `M2_PARCAE_DIR` explicitly.

On completion inspect `pilot.json`, per-arm JSON, 18 `.pt` snapshots, `run.log`, `BLOCKED_error.txt` if any, original upstream Git status, current Git branch/commit, and SHA256 before assigning PASS/FAIL. **Negative learning or quality is legitimate evidence.**

## Unresolved issues, next reviewer action

- Fresh Codespaces CPU execution / 120-step equality may expose code or dependency mismatch: preserve error as BLOCKED, do not fake a run or edit upstream.
- The frozen Alice source is an OOD **domain shift**, not an untouched in-domain Shakespeare test; do not substitute conclusions.
- Grok's previous report criticized possible undercounting in operator FLOPs and short-run comparability. Continue to label `counted FLOPs`; model quality may be inferior even when an exploratory gate passes.
- Stage exit checkpoint must incorporate raw results, code commit, dependency freeze, observed statuses, unresolved differences with Grok and one next experimental instruction. No PR merge until evidenced review.
