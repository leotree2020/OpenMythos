# MYTHOS-DECODE-CONTROL-V1 — loading interrupted, BLOCKED

The isolated launcher was repaired and passed six real, standard-library-only
development checks. The newly recorded formal CPU attempt started, passed D0,
then stopped at D1 when worker184848 received SIGTERM(15) during the pinned
official loader's torch.load call. The loader did not return. No forward call,
logit, sampled token or continuation was produced. No model retry occurred.

This is an incomplete experiment, not a negative result for either decoding
policy or for Parcae. The sender and trigger of SIGTERM remain unknown.

## Purpose / Environment / Input / Expected / Actual / Status

| Field | Record |
|---|---|
| Purpose | Repair and verify orchestration, then execute the existing frozen CPU decoding control to assess repetition and local language quality. |
| Environment | Codespace bookish-pancake-vwqx7rr9x5w3wxjr; /workspaces/mythos-base-v01-cpu312/bin/python, Python3.12.3, torch2.11.0+cpu, CPU capability AVX2. D0 verified the complete dependency inventory. Worker runtime/import guards passed; model loading was interrupted. |
| Input | Unchanged diagnostic implementation e2605841, original140M weights/config/tokenizer, original12 prompts; G12/S36/P36 matrix and5376 planned forwards unchanged. Tested launcher source SHA8083b948eebdf08c2d14a79d940ccead72db5f10c6bac8d9061816b6c9ea05c3. |
| Expected | Validated launcher; complete D0–D4 engineering evidence, then frozen quality review. No expectation that language quality must pass. |
| Actual | Launcher development6/6 PASS. Formal attempt D0 PASS, D1 BLOCKED with signal15, D2–D4 NOT TESTED. Official loader called once, returned zero times. Zero forwards/generations. |
| Status | Engineering BLOCKED; formal_run_started=True; language-quality NOT TESTED; sealed-file integrity PASS within the independently audited scope. |

## Git and source identity

- Repository leotree2020/OpenMythos, branch mythos-base-v01-decode-control-v1.
- Prior checkpoint: df02037580bf6861a8f61ea145a6ab7770e6c055.
- Diagnostic implementation A remains e2605841d7eb21c7d8ecbc07aa55ebe6c76f05b7.
- Tested launcher freeze L:2f6ca9f728c79e3dce51d8f459f927e9e823d87e.
- New execution record R:57d49092b45c855db24b598609f489dcdcf280ea.
- Result/checkpoint commit: the commit containing this document; the final
  delivery reports its SHA rather than attempting a self-referential hash.

Only launch-recovery additions, evidence and checkpoint documentation changed.
The diagnostic source/protocol/rubric and their frozen11-file inventory retain
their original bytes. Upstream remains read-only at
69284c13746e849104f738d6d1a347b1f457df76. B1 checkout remains
d88be474ebb2529c5b095e3732b1f25509f9b824. No PR was created or modified/merged.
The previous checkpoint is preserved in Git and in
launch_recovery_v1/PRIOR_CHECKPOINT_df020375.md.

## Verified launcher correction

A new directory contains mythos_launch.py and is launched with -I -B using the
existing CPU312 interpreter. This prevents the earlier operator.py shadowing.
The old failed directory was not renamed, patched or reused. The actual frozen
coordinator keeps its original -B arguments and sibling-module imports.

Six target checks passed: normal child completion; exact stdout/stderr capture;
source identity and isolated standard-library origin; refusal of an existing
claim without overwriting seven existing files; correct exit7 recording; and
timeout cleanup of a harmless parent with a TERM-resistant child. That child was
observed absent after cleanup. These fixtures do not load a model or validate
the coordinator numerically. The external SIGTERM-handler route was statically
reviewed, not separately exercised by sending SIGTERM to the helper.

The exact source, all25 smoke files, review and execution record were committed
before the model attempt. A missing or nonzero child result is not called PASS
merely because the launcher itself ran.

## Formal attempt and observed interruption

- Run-id: decode-v1-20261101T074027Z.
- Formal root:
  /workspaces/mythos-evidence/base_v01/decode_control/decode-v1-20261101T074027Z.
- Operator root:
  /workspaces/mythos-evidence/base_v01/decode_operator/decode-v1-20261101T074027Z.
- Launcher PID184596 started2026-11-01T07:41:12.882492Z.
- Coordinator PID184641; worker PID184848 started07:41:22.460620Z.
- Worker stopped07:41:48.831309Z with reason `Worker interrupted`, signal15,
  while reading original weights through official from_pretrained → torch.load.
- Coordinator sealed summary07:41:57.788225Z; launcher recorded CHILD_FAILED,
  child returncode2, at07:41:57.870576Z. No helper timeout/cleanup record exists.

This roughly45-second interval is not the configured6000-second launcher timeout
or5400-second worker timeout. Post-stop reads found all three process IDs absent.
Observed cgroup memory.events and memory.events.local had oom=0/oom_kill=0,
memory.max was `max`. Kernel dmesg access was denied. These observations neither
identify the signal sender nor justify claiming that memory pressure caused the
interruption. Do not equate SIGTERM with an OOM event or model implementation FAIL.

## Results and evidence acceptance

| Item | Status / actual |
|---|---|
| Launcher development tests | PASS,6/6 |
| D0 frozen source/environment/resources | PASS |
| D1 complete model load/tokenizer | BLOCKED, signal15 during official loading |
| D2 historical greedy bridge | NOT TESTED |
| D3 sampling matrix | NOT TESTED |
| D4 complete formal acceptance/sealing gate | NOT TESTED; post-stop file sealing completed separately |
| Recorded individual checks |37 PASS /1 BLOCKED; not language-quality votes |
| Completed continuations |0 of84 planned |
| New language-quality result | NOT TESTED, not0/12 FAIL |
| Read-only sealed-file audit | PASS for all49 listed files plus2 excluded manifests,51 actual files |
| Full experiment audit | BLOCKED / PARTIAL,0 independently detected contradictions |

The independent standard-library auditor made12791 assertions, rehashed3624
protected files, and verified1619 required historical reference manifest entries.
It found0 failures and87 incompleteness/coverage blockers. Those87 entries mostly
reflect outputs that were never produced; they are not87 model errors. Missing
state checks, logits, RNG trajectories and quality reviews are not imputed.
Original files and protected directory membership remain unchanged. The prior
failed operator attempt's six files also match their pre-attempt manifest exactly.

Evidence identifiers:

| File | Bytes | SHA256 |
|---|---:|---|
| FULL_MANIFEST.json |9009|d9ac04ea7c41c9465a370adb67e30fdaedd7298144d88b5a8f604e56bf63617c|
| public/GIT_BUNDLE_MANIFEST.json |8282|d8638bfca46ad76d825edfecfbf2b04b590d90df571b6f6c386260f6ba6bf21a|
| public/summary.json |2343|883d189d6d2563466f1fc4522dc08e228ccd73fb8c3bddb079baa17dca325781|
| POST_RUN_AUDIT.json |24789|fe9321dfff9c286345bda99f30b203944d08d9019bf066c43c88781db5bb53a3|

All51 formal-run files and15 operator evidence files are exported under
launch_recovery_v1/evidence/. Because no model tensor outputs exist, the private
run section contains only text logs and protection/claim metadata; those are also
retained in Git. No original weights or tokenizer binaries are redistributed.
Transport-only base64 is excluded; its verified transfer metadata is retained.
The transferred66-file JSON was3740471 bytes with SHA256
80afe12318d761c934b66525edadc1403da306061967e1042e8d097c0c1edbbc.
RESULT_REVIEW.md distinguishes local independent checks from target-side reads.

## Scientific state and unresolved questions

The prior successful CPU-inference checkpoint af796912 remains authoritative:
engineering PASS, greedy automatic0/12, AI coherence7/12, joint0/12, quality FAIL
on that viewed development set. This interrupted attempt does not change it and
provides no new comparison between G/S/P. The repaired launcher's PASS does not
establish generation quality, model correctness under this attempt, or a usable
Mythos baseline. Training/recovery and new sampling reload consistency remain
NOT TESTED. No quality review was performed on nonexistent samples.

Original B1 A5 remains BLOCKED at1e-6. No upstream/weight/buffer/config mutation,
B1 rerun, GPU, training, B2, D2-A or PR24 merge occurred. Formal Oracle remains
BLOCKED/NOT_READY; FORMAL_ACCEPTANCE_READY=False.

## Next unique instruction

Investigate the sender/source of the non-protocol SIGTERM and the target execution
channel's process-management rules. First specify and validate any controlled
environment probe without loading a model or changing scientific settings.
Preserve this interrupted attempt; do not immediately retry the numerical matrix,
relax gates, or guess a weight/architecture fix. A future formal attempt needs its
own recorded continuation and must retain the same scientific comparisons unless
a separately reviewed protocol explicitly changes them.

Stopped after the BLOCKED run, read-only audits and evidence/checkpoint commit.
No further model computation or automatic retry occurred.
