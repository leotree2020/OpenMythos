# MYTHOS-DECODE-CONTROL-V1 — greedy reproduction PASS; sampling guard FAIL

The authorized diagnostic restart completed model loading and all 12 greedy continuations, reproducing the historical logits/tokens/text evidence exactly. No SIGTERM, SIGINT or SIGHUP was recorded in this attempt. The first sampling step stopped at the frozen probability-mass check, before `torch.multinomial` was reached. No sampling continuation exists. The program stopped and all evidence was retained; there was no further model attempt.

The earlier SIGTERM sender/cause remains UNRESOLVED. External observation was added and calibrated, but absence of that signal in this attempt is not proof that its historical cause was repaired. This attempt has a separate, precisely recorded numerical guard failure, not a new language-quality verdict or evidence that the original weights are corrupt.

## Purpose / Environment / Input / Expected / Actual / Status

| Field | Record |
|---|---|
| Purpose | Investigate the earlier interruption, repair missing signal provenance, validate observation, and execute one registered CPU decoding restart. |
| Environment | Designated Codespace bookish-pancake-vwqx7rr9x5w3wxjr; existing CPU312 venv, Python 3.12.3, torch 2.11.0+cpu; deterministic single-thread CPU FP32, MATH attention; installed strace 6.8 observes signals externally. No numerical dependency change. |
| Input | Frozen implementation A, original weights/config/tokenizer, 12 original development prompts and unchanged G12/S36/P36 plan, seeds and acceptance thresholds. |
| Expected | Signal provenance and unchanged signal propagation; complete original D0–D4 checks and only then complete quality review. No expected quality success was assumed. |
| Actual | Development controls 35/35 PASS. D0/D1/D2 PASS; D3 FAIL at S/panel1/prompt1/step0. 12/84 complete continuations, 769 forward calls: 768 greedy steps plus one partial sampling step. Zero sampled tokens. |
| Status | Formal engineering FAIL; full-matrix coverage BLOCKED/PARTIAL; new sampling quality NOT TESTED. Sealed-file integrity PASS. No automatic retry. |

## Git and frozen sources

- Repository: leotree2020/OpenMythos.
- Branch: mythos-base-v01-decode-control-v1.
- Prior result/checkpoint: db3b9e25d90074680f1aeb0da231248430a0861f.
- Numerical implementation A, unchanged: e2605841d7eb21c7d8ecbc07aa55ebe6c76f05b7.
- Tested launcher L, unchanged: 2f6ca9f728c79e3dce51d8f459f927e9e823d87e.
- Observation/protocol freeze O: d495ab0ed10ad46135febbd5bab27ea9f11bc5ee.
- New execution record R: 5837494b6c153bd818659419755f1b2450f540f5.
- Result/checkpoint commit: the commit containing this document; final delivery reports its SHA.

Only the new signal_recovery_v1 package, evidence and checkpoint documentation changed. The nine frozen numerical/protocol files remain byte-identical to A. The previous checkpoint is archived at signal_recovery_v1/PRIOR_CHECKPOINT_db3b9e25.md. Upstream remains read-only at 69284c13746e849104f738d6d1a347b1f457df76. B1 checkout remains d88be474ebb2529c5b095e3732b1f25509f9b824. No PR was created, reviewed, commented on, or merged.

Dependencies remain the existing /workspaces/mythos-base-v01-cpu312 environment. D0 verified the complete installed inventory against B1. The2881-byte requirements.lock remains SHA256 84440f8945041ed314c29b205c5244e074116ede023d5aae0b11b633b4d6a51e. No packages were installed or changed. The external strace binary is2087432 bytes, SHA256 28f957c227012de0b18d1bd7fff2d396cb693ea60ed8013be68de071e84b5001.

## What was repaired and validated

Read-only logs did not identify the old signal sender. The prior frozen launcher timeout-cleanup branch was not supported as its source: recorded CHILD_FAILED/2, no cleanup/exception, and neither timeout reached. Cgroup/host observations do not establish an OOM cause.

The repair addresses missing observability. The unchanged coordinator is launched under installed strace with `-D -f -ttt -e trace=none -e signal=SIGTERM,SIGINT,SIGHUP`. A passive stdlib observer records owned PID/starttime/parent/cgroup/resource data. Neither mechanism suppresses signals or changes numerical code. Tracing can change timing; this run is not a performance experiment.

Two unique stdlib-only controls passed 17 and 18 checks respectively. The normal worker ran 90.0001158 seconds and produced exact expected output. The deliberate TERM control recorded sender PID232276/UID1000, receiver PID234384, unchanged handler behavior and exit2. Both verified parent identity, unblocked TERM, frozen interpreter/launcher and real observer records. No weights or numerical libraries were used. Development probe: signal-probe-v1-20261101T081654Z; 44 files retained and committed. Original cause remains unknown despite these controls passing.

## Formal attempt and exact new stopping point

- Run ID: decode-v1-20261101T082021Z.
- Run root: /workspaces/mythos-evidence/base_v01/decode_control/decode-v1-20261101T082021Z.
- Operator root: /workspaces/mythos-evidence/base_v01/decode_operator/decode-v1-20261101T082021Z.
- Launch: 2026-11-01T08:20:34.605920Z, launcher237392, coordinator237416, worker237750.
- D1 completed: all63 restored state entries match original bytes; tied storage and tokenizer guards PASS.
- D2 completed: all12 greedy outputs, all768 complete last-vector byte pairs and retained historical full-logit fingerprints match the reference. This is a new-process reproduction of the existing greedy behavior.
- D3 stopped: 08:25:49.824758Z, S/panel1/prompt1/step0, model seed731001, sampling seed841101.
- Reported quantity: `probabilities.double().sum()` after FP32 `torch.nn.functional.softmax`, temperature1, no filtering.
- Actual: 1.0000113072183736; absolute error: 1.1307218373612926e-5.
- Frozen acceptance: absolute error <=1e-6. This probability guard is separate from original B1 A5, even though both use the numeral1e-6.
- Failure precedes probability-vector digest and `torch.multinomial`. No sampled token or sampling continuation was produced. The FP32 probability vector was not retained; the recorded sum has not been independently recomputed.
- Both coordinator and worker exited2 normally according to the trace; launcher CHILD_FAILED/2 has no cleanup or exception. All selected termination-signal records are absent in this attempt. Observer completed with163 resource samples and no identity gaps in its recorded scope.

The saved partial S last-vector has131072 bytes and SHA256 5e4ca3c5df1abc143a58565ba5cf920a42027936be363e5311efba6db9567506. A separate read-only audit confirmed its actual bytes equal G's first vector, all32768 retained FP32 components are finite, and recorded prefix/full-logit/model-RNG fingerprints agree. The sampling failure therefore follows an identical verified first-step model output. A specific softmax/kernel cause or appropriate correction has not yet been experimentally established.

## Acceptance and independent evidence review

| Item | Actual / status |
|---|---|
| Development observation controls |35 PASS /0 FAIL |
| D0 source/environment/resources |PASS |
| D1 restored model/tokenizer |PASS |
| D2 historical greedy bridge |PASS,12/12 continuations |
| D3 sampling matrix |FAIL at its first probability-mass guard |
| D4 complete acceptance |NOT TESTED; partial evidence was sealed |
| Complete continuation rows |12 G;0 S;0 P |
| Forward calls |769;768 complete G traces plus1 partial S input |
| Recorded checks |11632 PASS /2 FAIL records; the two failures propagate the same stopping cause |
| Independent full-run audit |BLOCKED/PARTIAL;0 contradictions,75 coverage blockers; not a model PASS |
| Sealed run integrity |PASS,1634 manifest entries plus2 excluded manifests =1636 files |
| Greedy replay |768 actual historical last-vector byte pairs and1536 raw G RNG blocks verified |
| Restored state comparison |63 entries before generation; after-generation comparison NOT TESTED because of stop |
| Protected sources/history |3624 files rehashed;1619 required historical reference entries checked |
| Partial S input audit |6 PASS; no softmax, sampling, tokenizer or model replay |
| External observation/preservation audit |27 PASS; no failures/blockers; all previous6/51/17-file directories unchanged |
| New sampling quality and blind AI review |NOT TESTED; blind exporter was not run |

The read-only numerical auditor made61076 assertions. Its audit-level BLOCKED means incomplete coverage while preserving the runner's formal FAIL. It does not erase that FAIL or turn it into a quality result. The current greedy automatic screen is again0/12, consistent with identical historical output; no new coherence rating was imputed. Previous inference quality FAIL remains authoritative. No S/P quality comparison, training/recovery acceptance, fresh generalization or sampling reload validation was established.

## Evidence locations and hashes

All target raw evidence remains in the immutable run/operator directories. Git contains883 copied evidence files totaling11666589 bytes under signal_recovery_v1/evidence/, plus the export manifest and reviews. All781 raw vector/RNG binary files totaling108560384 bytes stay on the target and are covered by FULL_MANIFEST.json; weights are not redistributed. No raw evidence was replaced or discarded.

| File | Bytes | SHA256 |
|---|---:|---|
| FULL_MANIFEST.json |360381|f81af7f33f5f85a2517e0fbc0818a38b61fdfaee8099564a492f977177781fdc|
| public/summary.json |5963|4a73cb7c864f07740859078f7341441b134514088e81ae97d7d266d18532d17b|
| POST_RUN_AUDIT.json |26094|235256cd0b2f838df57d0d71d9f1e12a3d133b230d521bea2aa722013412c33d|
| POST_OPERATOR_AUDIT.json |13106|0aae797b68cb8e91df30ff5fdd9e89472c44c5fe227fd371e63e243e9a658026|
| PARTIAL_STEP_AUDIT.json |4627|b8ac0af94e3906d4fca017506674a65569af0e5225ebe174775496048930f771|

The13-file review export was1094613 bytes, SHA256 c5f0d8341ffb29a25b15d27c32e153ff5353dd25d7180b1fe2b4b9a9b2b37b7d; its exact file hashes were checked locally with0 mismatches. Audit limitations remain explicit: full logits use retained hashes, probabilities were not replayed, and no missing output was imputed.

## Boundaries and unresolved work

Original B1 A5 remains BLOCKED, its threshold untouched. No upstream, original weight, buffer, tokenizer, seed, prompt, decoding-policy or architecture change; no GPU, B1 rerun, B2, D2-A or PR24 action. Formal Oracle remains BLOCKED/NOT_READY and FORMAL_ACCEPTANCE_READY=False. The first trainable/resumable Mythos research baseline is not yet fully accepted.

Open issues: historical SIGTERM cause; origin of the observed probability-mass error; the correct numerical sampling implementation under an explicit new protocol; incomplete S/P quality data; training and optimizer-resume validation still deferred.

## Next unique instruction

Design and freeze a CPU-only, no-model controlled diagnostic using the already saved S_panel1_prompt01_step00_last.bin. Compare the frozen FP32 softmax path with a high-precision reference and explicitly normalized alternatives, retaining the1e-6 acceptance threshold and original raw input. First establish the source of the probability-mass discrepancy and test the proposed correction on saved data; do not rerun the model matrix, change upstream, or infer better language quality. Preserve this FAIL permanently. This checkpoint records the next task, not an executed probability experiment.

Stopped after the one registered model attempt, read-only audits, and evidence/checkpoint recording. No model process remains running.
