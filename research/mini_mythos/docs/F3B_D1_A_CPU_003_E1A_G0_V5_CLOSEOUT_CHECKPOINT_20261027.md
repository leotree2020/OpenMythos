# F3B-D1 CPU-003 E1-A G0 V5 — CPU test closeout checkpoint (2026-10-27)

* Branch `d1-r3-a-cpu-003-e1a-g0-v5-impl-20261027`; base `40f3f5b`; fix + tested HEAD `a4a85095fa1f48234914de09bdee2e7bf35abdad` (results/report/checkpoint are committed on top and change no code).
* Status: **CPU TESTS PASS** (216/216 ×2, 0 sentinel violations). **REAL G0 NOT AUTHORIZED.** No authorization file exists.
* Fixed: (1) any SystemExit after argparse → exit 3 (argparse 0/2 kept); (2) environment info via `os.uname()`, no external process, sentinels first; (3) runner verifies real HEAD from `.git` vs expected SHA, frozen files, bench hash, records 15 key-file hashes; REFUSED/exit 3 otherwise.
* Evidence: `research/mini_mythos/a_predicate_003/g0_v5_closeout_test_results/` (`G0_V5_CLOSEOUT_REPORT.md`, run1/run2 JSON+txt, `verification.txt`, negative controls).
* Frozen/untouched: V1–V5, bench (`b6f52a8c…d3b0`), Parcae, architecture, E1-A prereg, existing tests.
* Next (not started): ChatGPT/Grok short acceptance review → separate application for real G0 authorization.
