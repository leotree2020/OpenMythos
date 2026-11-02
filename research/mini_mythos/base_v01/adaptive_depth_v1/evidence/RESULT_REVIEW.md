# MYTHOS-ADAPTIVE-DEPTH-DEV-V1: final development result review

Review date: 2026-11-02. Reviewer: ChatGPT research-review agent in the same project team. This is an additional evidence and scope review, not external or human-independent validation.

**Verdict: PASS for the frozen local CPU development acceptance only.** The evidence supports the implemented engineering behavior on synthetic fixtures and untrained native tiny models. It does not establish behavior or quality on the official 140M weights.

## Review scope and provenance

- Purpose: check that the one final development result satisfies the frozen test inventory, preserves protected sources and the recorded dependency inventory, and does not overstate its scientific scope.
- Environment: read-only local file inspection, JSON field comparison and SHA-256 computation in PowerShell. The reviewer did not import torch, rerun tests, run a model, or alter original run evidence or frozen sources.
- Input: `attempt-v1/DEVELOPMENT_RESULTS.json`, `CLAIM.json`, `stdout.log`, `stderr.log`, both upstream snapshots, both dependency snapshots, and the frozen package's `SOURCE_MANIFEST.json`. The three executable source files were rehashed against that manifest.
- Expected: exactly the 15 frozen test IDs, including all five required native tests, pass without failures, errors, skips or missing tests; all preservation checks pass; scope remains development only.
- Actual: all these evidence checks agree, as detailed below.
- Status: PASS.

The result and initial claim both identify execution freeze commit `93e66ebfd8a1b6d3da07cde57fdfd97b552604af`. The operator separately reports that eight remote blobs were matched to local bytes before the final run. This review verified the local manifest and executable source identities; it did not independently repeat that remote publication check.

`CLAIM.json` remains `NOT TESTED` and is the pre-execution claim, not a competing final result. `DEVELOPMENT_RESULTS.json` is the terminal result and records `PASS`.

## Verified acceptance evidence

| Check | Expected | Actual | Status |
|---|---|---|---|
| Frozen suite identity | Exactly 15 unique test IDs | 15 unique IDs; zero differences from manifest | PASS |
| Required native coverage | All five native test IDs execute and pass | 5/5 PASS; zero differences from required-native list | PASS |
| Full suite completion | No failure, error, skip or missing test | 15 run, 0 failures, 0 errors, 0 skipped, 0 not run; also 0 expected failures and 0 unexpected successes | PASS |
| Guard and preservation checks | Every recorded check passes | 17/17 PASS | PASS |
| Executable source identity | All three files match manifest size and SHA-256 | All three match | PASS |
| Runtime | CPU FP32, one intra-op and inter-op thread, deterministic, no autocast | Recorded runtime matches; import and post-test state checks PASS | PASS |
| Upstream protection | Pin and tracked bytes/Git state unchanged | Both snapshots byte-identical; pin unchanged, clean status, 106 tracked-file records | PASS |
| Dependency inventory protection | Recorded installed name/version inventory unchanged | Both snapshots byte-identical; 14 entries | PASS |
| Transcript consistency | Full named suite agrees with structured result | All 15 named tests report `ok`; final `OK` | PASS |

The actual execution environment was Windows AMD64, Python 3.12.14, torch 2.9.0+cpu, isolated interpreter with bytecode disabled, CPU FP32, threads 1/1, deterministic algorithms enabled and warn-only disabled, with CPU and CUDA autocast disabled. This is the local development environment, not a claim of identity with the target 140M environment.

The outer runner records **6.344 seconds** elapsed (`6.344000000000051` in JSON). The unittest transcript records **2.649 seconds** for the suite itself. These are different measurement scopes and are consistent. Neither is an inference-speed or adaptive-routing performance benchmark. `stdout.log` is empty; unittest's verbose output and final summary are in `stderr.log`.

Both upstream snapshots record HEAD `69284c13746e849104f738d6d1a347b1f457df76` and empty Git status. Their recorded aggregate is `eb0f998edc0e849b5f08c5dd6e53ea6745b4764591087b5aa658c9a3a879f1b8`. This review establishes agreement between the before/after snapshots and the driver's preservation result; it does not claim a fresh post-review live Git audit. The package inventory aggregate is `995229ef9e11b2d0db785675b8cc13468ebc27cb139cf680ab6b72fd66f30150`. That inventory covers package names and versions, not every package file, installation provenance or the whole machine.

## Supported and unsupported conclusions

The five native tests and the previously reviewed source support exact fixed/continued tiny-model outputs at depths 8/16/32, observed native h0 consistency, the selected-path hook/count checks, state preservation, prefix/repeat controls, same-length suffix causality, and rejection of unsupported configurations. The other ten tests cover the TV rule and controlled execution behavior, including both 16-exit and 32-continue branches and a stable-but-wrong fixture.

Important qualifications remain:

- Native tests use untrained tiny models. Toy tests call a private execution helper and do not make toy models a supported public API.
- The continuation is within one process and one inference call. No disk serialization, cross-process continuation or training-checkpoint recovery is implemented or validated here.
- The public prediction outputs are for the final supplied prefix position. A gate computed from a full window must not be used to score earlier teacher-forced positions.
- The `TV <= 0.01` rule is a frozen, uncalibrated engineering heuristic. Stability does not establish correctness or confidence.
- The implementation's counters describe executed paths; the native selected-path test additionally verifies block counts with hooks. Toy schedule counts are not measurements of native block execution or hardware speed.
- Additional intermediate readouts have a cost. No latency, FLOPs, memory, efficiency or quality superiority is established by these tests.
- This is heuristic adaptive depth inspired by adaptive-computation research. It is not a trained ACT gate, a reproduction of a private Claude architecture, or evidence of Claude Mythos capability parity.

The terminal fields correctly retain `formal_140m_started=false`, `quality_improvement=NOT TESTED`, `training_recovery=NOT TESTED`, and `claude_mythos_parity=NOT TESTED`. Formal 140M validation, fresh-sample generalization, adaptive versus fixed/random-routing quality/cost comparison and learned ACT remain NOT TESTED. This development PASS does not revise historical B1 A5 or Formal Oracle status.

No outstanding blocker was found for accepting this local development stage. The next stage must use a separately frozen real-weight validation protocol; it cannot inherit a 140M PASS from this review.

## Evidence identities read in this review

All paths below are relative to this acceptance directory unless otherwise stated.

| File | Bytes | SHA-256 |
|---|---:|---|
| `attempt-v1/DEVELOPMENT_RESULTS.json` | 18984 | `16b6a38ddbc46bfac51c26851c18022b52a0dc831c1f81e2468df94c7cce848b` |
| `attempt-v1/CLAIM.json` | 1287 | `64851cf3664883326bc984bb364c2b2b33f1be908c07b078b374d831ef38f9d7` |
| `attempt-v1/stderr.log` | 3137 | `ad912bfa074d53f4906e2568b7238245cf21670d88f975a0fe87a3d9ecfdc981` |
| `attempt-v1/stdout.log` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `attempt-v1/UPSTREAM_BEFORE.json` | 11207 | `581a3809c557221b829b2802b36d29792d6ae29e606609ac1a258e785cfd1f79` |
| `attempt-v1/UPSTREAM_AFTER.json` | 11207 | `581a3809c557221b829b2802b36d29792d6ae29e606609ac1a258e785cfd1f79` |
| `attempt-v1/PACKAGES_BEFORE.json` | 796 | `5f2ece757fae410bb7762920e03f398ff518814fad7d613094c7560378737766` |
| `attempt-v1/PACKAGES_AFTER.json` | 796 | `5f2ece757fae410bb7762920e03f398ff518814fad7d613094c7560378737766` |
| `../adaptive_depth_v1_work/SOURCE_MANIFEST.json` | 2246 | `a4d9d11a19eb02ad8b5ca0e67d25647e3d72a4325dfeba00408bcd02ce766d31` |

The three rehashed executable source identities are: `adaptive_depth.py` (16059 bytes), `daa6b5b014f9d5f77cc47e2ba14a7027065c135b2cac7f6bcda58d0e6d6457b8`; `test_adaptive_depth.py` (19656 bytes), `ed8b956490c8e90cb9461e8905a521fea5a429199b665d970e65958230544a66`; `run_development.py` (14138 bytes), `867ef8819f9fd2cfeb807471594f0048cb0594ab67897837cf6cf8db70aa29d7`.
