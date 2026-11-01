# MYTHOS-DECODE-SIGNAL-RECOVERY-V1

## Purpose and frozen scientific scope

Investigate the unsolicited SIGTERM that stopped `decode-v1-20261101T074027Z`, repair the missing signal provenance, validate that observation preserves termination behavior, then perform one explicitly registered diagnostic restart of MYTHOS-DECODE-CONTROL-V1. User authorization: investigate, repair, restart. Historical root cause remains UNRESOLVED unless new evidence establishes it; successful rerun alone is not a causal explanation.

Checkpoint: `db3b9e25d90074680f1aeb0da231248430a0861f`. Numerical implementation A: `e2605841d7eb21c7d8ecbc07aa55ebe6c76f05b7`. Tested stdlib launcher L: `2f6ca9f728c79e3dce51d8f459f927e9e823d87e`. Keep all nine frozen implementation/protocol files byte-identical. Keep original upstream, checkpoint weights, tokenizer, input prompts, CPU environment, seeds, policies, sample counts, RNG handling, model loading, thresholds, and quality rubric unchanged.

No upstream edit, GPU, training, B1 rerun, A5 relaxation, B2, D2-A, or PR #24 operation. Do not stop unrelated processes, change security settings, or suppress any termination signal. Preserve both earlier attempts and their checkpoints. Add only a new subdirectory under `decode_control_v1` and, after the phase ends, archive/update its root checkpoint.

## Known evidence and unresolved cause

The previous worker received SIGTERM (15) while the official loader was reading the checkpoint. Its own preliminary checkpoint read had completed. No forward or continuation was produced. Launcher completion was CHILD_FAILED/2 without cleanup/exception; elapsed time was about 45 seconds, below the 6000-second launcher and 5400-second coordinator bounds. Current frozen coordinator/worker contain receiving handlers, not a matching active TERM sender. Historical sender PID/UID was not captured and cannot be reconstructed from ordinary Python signal handlers. Snapshot OOM counters and inaccessible kernel logs do not establish a memory cause.

Read-only recovery checks branch/checkpoint/clean worktree, focused VSCode logs around 07:41 UTC, process inventory, available memory, and installed tracing tool. Keep extracted relevant evidence; never dump credentials or full environments.

## Engineering change

Use already-installed `/usr/bin/strace` 6.8, recording actual executable hash/version. Wrap the unchanged coordinator command with:

`strace -D -f -ttt -e trace=none -e signal=SIGTERM,SIGINT,SIGHUP -o <new exclusive operator directory>/signals.log -- <unchanged coordinator command>`

`-D` preserves the coordinator as the launcher's direct child; verify this on the target in development controls. Do not use `--seccomp-bpf`, `--kill-on-exit`, injected signals, -DD/-DDD, or trace attach to unrelated processes. Signals must propagate normally into the existing handlers. No `sigwaitinfo` masks or new signal handlers in model code. Tracing is external observation, can affect scheduling, and does not support performance conclusions.

Add a passive stdlib resource observer outside the formal run directory. Record observed UTC/monotonic time, owned process identities/status/cgroup, relevant accessible cgroup memory counters and host MemAvailable/pressure. It must not send signals, change limits, or import numerical libraries. Missing observations are explicit limitations. It stops after launcher completion or its own bounded deadline. Logs reside outside the frozen/sealed numerical run.

## Development acceptance, before formal restart

Run only stdlib fixtures on the designated Codespace, using the frozen launcher and exact strace wrapper. Freeze fixture and observer source before target execution. Each case gets an exclusive directory and no automatic retries.

1. Normal nested coordinator/worker fixture runs 90 seconds (exceeds previous interruption latency), exact expected output/exit, no unexpected TERM/INT/HUP, expected parent relationship, no blocked TERM mask, and no Torch imports. PASS establishes only this fixture's survival under its conditions.
2. Known-sender TERM control: wait for owned worker readiness, send exactly one SIGTERM from the fixture controller, and verify traced signal number, sender PID and UID; original-style receiving handler stops, coordinator returns 2, launcher records CHILD_FAILED/2 without cleanup. The known termination is expected fixture behavior, not an experimental failure.
3. Both cases must demonstrate correct evidence capture and preservation. Any unexpected mismatch is FAIL; unavailable tracing/target/permissions is BLOCKED. Stop and save evidence without a model attempt. No privilege or security changes to make tracing work.

## Formal attempt acceptance

Only after development controls and static review PASS: commit the observer package, then commit a unique run record referencing A, L, observer commit, exact tool/source hashes, new run ID and command. Require clean isolated tree and source/hash/resource gates before dispatch. Exactly one formal attempt, no automatic retry.

Apply the original D0–D4 gates without modification: 63 state entries byte-identical before and after, historical greedy logits/tokens/text/EOS bridge, 84 continuations and 5376 forward calls, all frozen RNG/probability/input checks, protected historical/source files unchanged, and complete evidence sealing. A FAIL or BLOCKED stops that attempt and preserves partial evidence. Quality failures do not stop the planned matrix.

After a complete engineering PASS, independently audit saved evidence and apply the unchanged automatic and two-reviewer blind coherence rubric. Each sampled policy must meet joint acceptance >=9/12 in every one of its three panels; S remains primary, P secondary. No claims about unseen generalization or fresh sampling reload. A partial run has quality NOT TESTED, not 0/12 FAIL.

If another signal arrives, retain original signal/trace, source PID/UID if available, resource observations, and sealed partial result; do not ignore it or retry. Investigate identified sender only within ownership and authorization. If no signal arrives, conclude completed-under-observation, not historical cause fixed.

## Evidence and checkpoint

Every control and formal stage records Purpose, Environment, Input, Expected, Actual, and PASS/FAIL/BLOCKED/NOT TESTED. Verify hashes and scientific invariants rather than exit code alone. Preserve full target run evidence and manifests, commit public evidence/operator diagnostics (no weights or raw tensor payloads), independent review, Git/branch/environment, unresolved issues, and one next instruction. Push normally; verify remote HEAD and clean tree. Original B1 A5 stays BLOCKED and Formal Oracle BLOCKED/NOT_READY, FORMAL_ACCEPTANCE_READY=False.
