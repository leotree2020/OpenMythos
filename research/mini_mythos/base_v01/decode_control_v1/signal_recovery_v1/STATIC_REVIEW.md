# Signal-observation package: independent static review

**Verdict: APPROVE for the two frozen stdlib development controls.** Formal restart remains conditional on their evidence passing and a separately frozen execution record. Historical SIGTERM cause is UNRESOLVED.

| Field | Record |
|---|---|
| Purpose | Review external signal observation, owned-process handling and target-control acceptance without changing numerical implementation A. |
| Environment | Local source and SHA-256 review only; no target probe/model execution by this reviewer. |
| Input | The four Python sources and PROTOCOL.md identified below; frozen launcher and prior interruption evidence. |
| Expected | Preserve signal delivery/parent/exit semantics; retain frozen venv; record actual sender evidence; avoid unrelated processes and false causal claims. |
| Actual | Mandatory review findings were corrected. Current source supports the prescribed bounded controls and preserves the numerical-code boundary. No remaining blocking static defect identified. |
| Status | Static review **PASS**; development controls and formal restart **NOT TESTED** at review time. |

| File | Bytes | SHA-256 |
|---|---:|---|
| probe_test.py | 26,683 | `e3e99a5adfa4f51a942ab3a989037b8f78fbadaa202a65f3efa433142daa0a9f` |
| probe_fixture.py | 4,989 | `d7dfacf944e0e34a6c94ee6e9938c328093bb3966c683102bc7f16d1ebcc5bec` |
| resource_observer.py | 7,019 | `77a053266449fa82ab9fe287a8f145bd9a3118c322b106783f209c03a874824b` |
| operator_dispatch.py | 3,515 | `ca24e9c9480255c87002f2b89abecbb755c54cb4f361e0951380e6e74e6c993e` |
| PROTOCOL.md | 6,763 | `f003c3995ce5a473df5d7de8534094054d516c1966ad53092e93ed0d644e8009` |

The reviewed wrapper uses strace 6.8 with `-D -f`, timestamps, no syscall output and only TERM/INT/HUP signal output. It does not enable signal injection, `--seccomp-bpf` or `--kill-on-exit`. The [version-pinned upstream manual](https://raw.githubusercontent.com/strace/strace/v6.8/doc/strace.1.in) documents the parent-preservation purpose of `-D` and the implicit kill-on-exit behavior of seccomp-bpf; the target controls must verify actual behavior here.

The controls check live parent/worker identities, unblocked TERM, exact stdout/stderr and exit propagation. One bounded worker survives 90 seconds; the other receives exactly one intentional TERM from its controller. Its trace must match receiver PID and sender PID/UID/code, and the existing-style handler must exit with the recorded interruption. Trace records also identify both worker and coordinator completion. These cases stop on unexpected failure and do not retry.

Review corrections now present:

- The interpreter path preserves the frozen venv symlink instead of replacing it with the system Python target; exact Python 3.12.3, prefix and child identity are checked.
- The passive observer tracks PID plus starttime, checks parent identity before following descendants and rechecks identity after reading metadata. Reused/absent PIDs are not silently attributed to owned processes. Sender metadata read later is explicitly not proof of historical identity; original siginfo remains authoritative.
- Observer integration reads the actual JSONL rows: count consistency, a normal-case sample containing the owned coordinator/worker and their actual cgroup, and the exact known-sender trace line in the signal case. Observer exit code alone is insufficient.

The observer only reads process/resource/signal metadata, sends no signals and opens no model artifacts. Probe signals target only the controlled fixture; deadline cleanup uses recorded live ownership. Dispatcher pins the tool/observer/launcher, preserves prior directories and creates an exclusive new attempt. Numerical A, original launcher L, model artifacts and scientific thresholds remain unchanged.

A passing 90-second control does not identify the earlier sender or prove stability under model load. Tracing can affect scheduling; it provides no performance conclusion. No root-cause fix, new model result, B1 upgrade, B2/D2-A work, or PR #24 action is established by this review. Only this review document was written by the reviewer.
