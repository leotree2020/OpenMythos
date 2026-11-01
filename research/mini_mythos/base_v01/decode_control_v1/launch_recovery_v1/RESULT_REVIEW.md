# Decode-control interrupted-run evidence review

**Verdict: APPROVE the BLOCKED classification and evidence sealing.** The experiment did start, but no model forward or generation was reached. This is not a model-quality FAIL.

| Field | Record |
|---|---|
| Purpose | Independently review the complete retained evidence, interruption classification and protection audit. |
| Environment | Local stdlib file/JSON/hash review only; no model, launcher or audit rerun. |
| Input | All 66 downloaded files under `evidence/run` and `evidence/operator`, frozen source copies and the previous failed-attempt evidence. |
| Expected | Complete sealed-file membership/hashes, consistent identity/stop records, unchanged protected evidence, honest partial acceptance. |
| Actual | All 49 full-manifest entries match local bytes; exactly 51 run files including its two declared excluded manifests. Public-manifest subset matches. Stop, runtime, process, launcher and partial-audit records agree. |
| Status | Evidence review **PASS**; engineering experiment **BLOCKED**; new language quality **NOT TESTED**. |

Run: `decode-v1-20261101T074027Z`. Diagnostic A remains `e2605841d7eb21c7d8ecbc07aa55ebe6c76f05b7`; execution R is `57d49092b45c855db24b598609f489dcdcf280ea`, on `mythos-base-v01-decode-control-v1`.

The coordinator claim and worker record establish `formal_run_started=true`. D0 passed. The worker attempted the official loader once, returned no model, and caught **SIGTERM(15)** during `torch.load` inside `from_pretrained`; its traceback and D1 stop agree. D1 is **BLOCKED**; D2-D4 are **NOT TESTED**. There is no generation directory, inference result, or new quality sample. CPU runtime records show one thread per pool, deterministic mode, FP32 CPU, no active autocast and no initialized CUDA before/after upstream import; this does not establish an inference result.

The actual launcher source matches its claim and the reviewed SHA-256 `8083b948eebdf08c2d14a79d940ccead72db5f10c6bac8d9061816b6c9ea05c3`. Its completion is `CHILD_FAILED`, child return code 2, about 45 seconds after its claim. There is no launcher timeout exception or cleanup record; its configured timeout is 6,000 seconds. Subsequent read-only observations find launcher, coordinator and worker PIDs absent.

The signal sender and trigger remain **unknown**. Observed cgroup `oom`/`oom_kill` counters are zero and `memory.max` is `max`; kernel logs were inaccessible. These observations neither establish OOM nor rule out every external resource/process-management cause. No model defect or specific external actor is identified.

The independent target audit reports **0 audit failures**, sealed-run file integrity **PASS**, incomplete coverage and **BLOCKED**. Local enumeration confirms **37 PASS and 1 BLOCKED check records**. Its 87 blockers consist of 84 unavailable planned generations plus three incomplete-acceptance/coverage conditions; they are **not 87 model errors**. Panel `available=0` makes quality NOT TESTED, not a measured 0/12 quality failure.

All 3,624 protected-file rows are internally consistent with the saved baseline; target rehash results report no changes/unavailable files. The four historical directory records have no added/removed members, and source/B1/upstream Git observations are clean and unchanged. Locally, all nine frozen source/protocol files match that baseline. `PRESERVATION.json` reports the previous failed attempt's six files unchanged; all six retained local originals match its manifest. Those target-wide protection checks were performed on the target; this reviewer independently rehashed the downloaded run files and cross-checked the supplied records, not every historical target artifact.

No numerical retry was performed during this review. Preserve this attempt, keep original B1 A5 and later-stage statuses unchanged, and investigate the signal's source/launch-channel behavior before proposing another model attempt. This reviewer changed only this review document; upstream, thresholds, B1/B2/D2-A and PR #24 were not modified.
