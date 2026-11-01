# Signal-observation controls: evidence review

**Verdict: APPROVE / PASS for the two development controls.** The captured evidence supports signal observation and propagation under these conditions. It does not identify or fix the historical SIGTERM cause.

| Field | Record |
|---|---|
| Purpose | Independently check raw controlled-signal, process-identity, output, exit and resource-observer evidence before the registered restart. |
| Environment | Local stdlib JSON/byte/hash review of the target's 44 retained files. The target used frozen venv Python 3.12.3 and installed strace 6.8; no model computation was performed by this reviewer. |
| Input | DEVELOPMENT_PROBE claim/summary, both case reports, ready/result identities, signal intent/sent records, exact logs and resource JSONL. |
| Expected | Normal 90-second survival; one known TERM correctly attributed and delivered; preserved parent/exit semantics; genuine observer records. |
| Actual | 17 normal-case and 18 TERM-case checks are PASS and agree with inspected raw records. Source hashes match the reviewed probe, fixture, launcher and observer. No review mismatch. |
| Status | Development evidence **PASS**; historical sender/cause **UNKNOWN**; formal model restart **NOT TESTED** at review time. |

The normal worker ran **90.00011581299987 seconds**, returned 0 and received no selected signal in the trace. Launcher completion is COMPLETED/0. The observer retained **93 samples**; 89 locally counted samples contain both expected coordinator and worker PID/starttime identities. The raw records include their actual cgroup and resource observations.

The controlled TERM event names sender **PID 232276, UID 1000**, receiver **PID 234384**, and signal 15. Intent and sent records agree. The trace contains exactly:

`234384 1793521107.458545 --- SIGTERM {si_signo=SIGTERM, si_code=SI_USER, si_pid=232276, si_uid=1000} ---`

The worker's original-style handler records INTERRUPTED/15; worker and coordinator trace exits are 2, and the launcher records CHILD_FAILED/2 without timeout/cleanup. The observer's **4 samples** contain this exact signal line. The expected interruption is a successful development control, not a model-experiment failure.

Both cases preserve the coordinator as the launcher's direct child and the worker as the coordinator's child, with matching live identities and unblocked TERM. Their stdout markers are byte-exact; inspected stderr and launcher/observer console streams are empty. Venv path/prefix, isolated mode and absence of numerical imports are recorded. Observer sample counts match JSONL row counts; it records no signals sent or model artifacts opened.

Key evidence hashes (SHA-256):

| File under DEVELOPMENT_PROBE | Bytes | SHA-256 |
|---|---:|---|
| summary.json | 1,174 | `d10c623ee4014e4f32292d3dada57fef7719fc8f13de0bf920bb9094017d3e0d` |
| claim.json | 2,450 | `f4b58b76009ca1b23dbfa7e7e9c422d0f9933cf363af41ca92db50a7b7af53c3` |
| normal/operator/signals.log | 94 | `4f3861cdb302c9b365c9775b6d80bfd2b4bf84ec6c211649e4792ce52c8a8d6a` |
| term/operator/signals.log | 199 | `8ed71d3687e98713f44b17f9cd334bf6d3f9d64b023d6eff97d277df5632b291` |
| normal/operator/resource_samples.jsonl | 250,949 | `875e1651b16459ebb2968f90762169d5ab685679108befa14504fb0f470d7d21` |
| term/operator/resource_samples.jsonl | 4,974 | `ecccffd29ccf3ed333ad4aedbcd919687cb553a102b2dbf72d111ad3497c6c5c` |

These hashes identify the locally reviewed bytes; they do not imply another target execution. Ninety seconds of stdlib survival does not validate model-load memory behavior or prove future stability. A successful instrumented restart would still not establish the earlier signal's sender. Proceed only through the separately registered single attempt, unchanged A/L and original stopping rules; no numerical retry was performed in this review.
