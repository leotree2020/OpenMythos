# G0 REAL-001 — first real G0 execution (F3B-D1-A-CPU-003-E1A-G0-V5-REAL-001)

**G0 REAL-001: PASS.  G1/G2/G3 / BV / E1-A: NOT AUTHORIZED.**

## Purpose, environment, input
* Purpose: one real, controlled run of the frozen V5 minimal process-gate test (one observer, one sacrificial gated child, one fork, zero signals, 20 s budget). Scope: G0 only; not evidence for G1/G2/G3, BV or E1-A.
* Environment: Linux 6.18.44-fc-v165 x86_64 (Firecracker VM), 4 CPUs, uid 0, Python 3.13.16 (`python3 -B`), no GPU. `os.pidfd_open`, `socket.send_fds/recv_fds`, `os.link` present.
* Code: branch `d1-r3-a-cpu-003-e1a-g0-v5-impl-20261027`, HEAD **0cf75c170295784aee92e82950f32a749f4fadd6** (docs/results only on top of the CPU-accepted **a4a85095fa1f48234914de09bdee2e7bf35abdad**; `git diff a4a8509 HEAD` over gate_g0, bench, tools, tests is empty). Working tree clean before and after (the authorization file is excluded locally via `.git/info/exclude` and never committed).
* Bindings (all equal to the frozen values): prereg (E1-A original) `e6b7ca5c…ec39`; criteria V5 `d36da0c0…cb821`; G0 prereg V5 `8338f4a0…ef6e25c`; bench `b6f52a8c…d3b0`; g0_code `1a2d71e3c5442f03d151391040d51e19744f4cfb3d0d60cb2c31d1a88ec0586f`. The 15 key files' sha256 equal the CPU-acceptance record (0 mismatches). V1–V5 frozen-file check: 0 problems.
* Authorization: id `OWNER-G0-REAL-001-20261027`, schema e1a-gate-auth-1 / stage G0, grants runs 1 / forks 1 / signals 0 / no fault injection / 1 child / 20 s, expires 2026-10-27T16:43:03Z, local file mode 0400, **not committed** (sha256 `6609ccd7…c3a`, identical to the run's `authorization_used.json`, which is also not committed). Consumed at 2026-10-27T14:43:11Z (consumption marker kept; a post-run `--check` reports it "already consumed (single use)").
* Pre-execution checks (all PASS, nothing started): clean tree; no residual python/g0/sleep process; no evidence directory, no MANUAL_DISPOSITION file, no earlier consumption record anywhere; `g0_run.py --check` exit 0 (`g0_check_pre_auth.json`).

## Execution
`python3 -B gate_g0/g0_run.py --execute`, once, no timeout wrapper, no signal-sending command, no retry. stdout `{"run_id": "g0_20261027_144311_479c54", "exit_code": 0}`; stderr empty; **process exit code 0**.
Registry (7 records): RUN_START → INTENT → FORKED (child pid 298, starttime 13549) → REGISTERED (ppid 297) → RELEASED → DEAD ("confirmed dead from /proc") → RUN_END (cleanup_confirmed true, residual [], token residue []). Observer pid 297. Duration 0.431 s (deadline hits none).

## Expected vs actual
Expected (V5): C01–C17 all satisfied, evidence saved/verified/judged/closed, no residue. Actual: all of that.

## Per-check verdicts (summary file as read back)
| check | state | detail |
|---|---|---|
| G0-C01 | PASS | preflight clean |
| G0-C02 | PASS | binding differences [], consumed=True |
| G0-C03 | PASS | sequence and integrity ok |
| G0-C04 | PASS | registered {'pid': 298, 'starttime': 13549} vs held {'pid': 298, 'starttime': 13549, 'ppid': 297}, fork pids [298], observer 297 |
| G0-C05 | PASS | no action before release |
| G0-C06 | PASS | descriptor hygiene ok |
| G0-C07 | PASS | attempt, success and gate pass in order |
| G0-C08 | PASS | exited-unreaped observed before any wait |
| G0-C09 | PASS | reaped by specific pid, /proc entry gone |
| G0-C10 | PASS | exit status 0 |
| G0-C11 | PASS | one fork, one child, no descendants, no tickets |
| G0-C12 | PASS | violations [], non-trivial kill entries [] |
| G0-C13 | PASS | no residue |
| G0-C14 | PASS | observer descriptors S0=4 S5=4 |
| G0-C15 | PASS | duration 0.431 s, deadline hits [] |
| G0-C16 | PASS | evidence complete and typed |
| G0-C17 | PASS | exception None aborted None |

Notes: C03 PASS (no unevaluable evidence; `c03_fidelity_report` empty); C12 "violations [], non-trivial kill entries []": the cleanup phase made one consultation that found the child `already_exited` and sent nothing; guard violations 0; zero signals.

## Child exit and reap evidence
Child gate pass observed (`first_action_mono` 135.800450 after RELEASED 135.799370); `exit_sent` 135.802890 → `pidfd_readable` 135.803794 (exit observed, unreaped) → `proc_gone` 135.805747; `reap_mono` 135.805713 by `waitpid(298)` returning pid 298, raw status 0, exit status 0. Exactly one fork (`guard.fork_pids` [298]), no descendants, no tickets, observer descriptors S0 = S5 = 4. No process left (ps check after the run).

## Evidence hashes and closure (committed under `evidence/g0_20261027_144311_479c54/`, except the authorization copy)
| file | sha256 |
|---|---|
| g0_evidence.json (8065 B) | 11a8d36dfdf60678a2b5d9a8b53be1b9f8587710d643158b86f3f58371ed33bb |
| g0_summary.json (3562 B) | e54cc1225dd87a36cc951b4d2a831d3792a55ae7d96bcbeb95fad92bd3367032 |
| registry.jsonl | bc2adcd23f7c72c1bb3c5f88f4287aa7fc2d196e5c958a9eadbf87c33dae4133 |
| g0_closed.json (= g0_closed.json.tmp, one inode, tolerated by V5) | de96e1be2faf831bbe5c9e14a09deae9efdad0bb2234350d3942bc796e309736 |
| _g0_consumed/OWNER-G0-REAL-001-20261027.json | 69410104d578cfe94d222c764cc447f03061ba40a796e3ca29bb2a61a6809871 |

Closure marker `g0_closed.json`: recorded_verdict PASS, recorded_exit_code 0, `process_exit_proof` false (as defined by V5: the marker records the verdict, it is not itself process-exit proof). Pipeline P0–P5 as recorded: constructed, saved, read back and verified, 0 invalid fields, judged PASS. My independent verification (`independent_verification.txt`): evidence and summary hashes and sizes match the marker; re-judging the read-back evidence with the frozen criteria gives PASS, 17/17 checks, 0 non-PASS.

## Caveats / unresolved
* One run on one VM (the VM had just been started); it shows that the frozen G0 procedure and tooling work once. It is not a statistical statement and says nothing about G1/G2/G3, BV or E1-A.
* The guards are Python-level; as stated in the V5 safety review they are not proof that no kernel path exists. 
* `g0_closed.json.tmp` remains beside the marker by design (byte-identical hard link).
* Open: independent review of the real evidence by ChatGPT and Grok.

## Not done / unchanged
No G1/G2/G3, BV, E1-A, training or GPU; no second run; Parcae, Bench, V1–V5 and the architecture untouched (no tracked file changed by the run).

## Single next instruction
ChatGPT and Grok independently review this real evidence (`evidence/g0_20261027_144311_479c54/`, `g0_v5_real_001_results/`) and report; no further execution of any stage until the project owner issues a separate authorization.
