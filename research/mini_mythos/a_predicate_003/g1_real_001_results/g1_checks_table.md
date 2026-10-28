# G1-REAL-001 check results (from g1_summary.json, read back and hash-verified; re-asserted by independent_verify.py)

| check | name | T1_ABORT | T2_EOF | T3_INVALID_BYTE | T4_TIMEOUT |
|---|---|---|---|---|---|
| G1-C01 | preflight_clean | PASS | PASS | PASS | PASS |
| G1-C02 | authorization_and_bindings | PASS | PASS | PASS | PASS |
| G1-C03 | registration_sequence_and_integrity | PASS | PASS | PASS | PASS |
| G1-C04 | identity_registered_before_stimulus | PASS | PASS | PASS | PASS |
| G1-C05 | no_action_without_release | PASS | PASS | PASS | PASS |
| G1-C06 | gate_descriptor_hygiene | PASS | PASS | PASS | PASS |
| G1-C07 | stimulus_exactness | PASS | PASS | PASS | PASS |
| G1-C08 | exit_observed_unreaped | PASS | PASS | PASS | PASS |
| G1-C09 | reap_by_specific_pid | PASS | PASS | PASS | PASS |
| G1-C10 | gate_path_exit_status | PASS | PASS | PASS | PASS |
| G1-C11 | process_budget | PASS | PASS | PASS | PASS |
| G1-C12 | zero_signals | PASS | PASS | PASS | PASS |
| G1-C13 | cleanup_and_no_residue | PASS | PASS | PASS | PASS |
| G1-C14 | observer_descriptor_baseline | PASS | PASS | PASS | PASS |
| G1-C15 | time_bounds | PASS | PASS | PASS | PASS |
| G1-C16 | evidence_complete | PASS | PASS | PASS | PASS |
| G1-C17 | no_unexplained_error | PASS | PASS | PASS | PASS |

Run-level checks: G1-C01 PASS (preflight clean), G1-C02 PASS (binding differences [], consumed=True), G1-C16 PASS (evidence complete and typed), G1-C17 PASS (no unexplained error)

Per-test detail:

* **T1_ABORT** — verdict PASS
    * G1-C04 identity_registered_before_stimulus: identity registered before the stimulus: pid/starttime/ppid agree in 7 places
    * G1-C07 stimulus_exactness: writes [65] and closes 1 as planned, no R, no release
    * G1-C08 exit_observed_unreaped: exited-unreaped observed before any wait
    * G1-C09 reap_by_specific_pid: reaped by specific pid, /proc entry gone
    * G1-C10 gate_path_exit_status: exit status 111 as expected
    * G1-C15 time_bounds: within the time bounds
* **T2_EOF** — verdict PASS
    * G1-C04 identity_registered_before_stimulus: identity registered before the stimulus: pid/starttime/ppid agree in 7 places
    * G1-C07 stimulus_exactness: writes [] and closes 1 as planned, no R, no release
    * G1-C08 exit_observed_unreaped: exited-unreaped observed before any wait
    * G1-C09 reap_by_specific_pid: reaped by specific pid, /proc entry gone
    * G1-C10 gate_path_exit_status: exit status 111 as expected
    * G1-C15 time_bounds: within the time bounds
* **T3_INVALID_BYTE** — verdict PASS
    * G1-C04 identity_registered_before_stimulus: identity registered before the stimulus: pid/starttime/ppid agree in 7 places
    * G1-C07 stimulus_exactness: writes [114] and closes 1 as planned, no R, no release
    * G1-C08 exit_observed_unreaped: exited-unreaped observed before any wait
    * G1-C09 reap_by_specific_pid: reaped by specific pid, /proc entry gone
    * G1-C10 gate_path_exit_status: exit status 111 as expected
    * G1-C15 time_bounds: within the time bounds
* **T4_TIMEOUT** — verdict PASS
    * G1-C04 identity_registered_before_stimulus: identity registered before the stimulus: pid/starttime/ppid agree in 7 places
    * G1-C07 stimulus_exactness: writes [] and closes 1 as planned, no R, no release
    * G1-C08 exit_observed_unreaped: exited-unreaped observed before any wait
    * G1-C09 reap_by_specific_pid: reaped by specific pid, /proc entry gone
    * G1-C10 gate_path_exit_status: exit status 112 as expected
    * G1-C15 time_bounds: within the time bounds
