# MoDA v2 evidence-storage repair

Status: implementation and local startup fixtures complete; exact target preflight and final freeze pending. No target/model execution by this implementation agent.

## Problem and controlled change

The v1 operator stopped before tests/model work because a25,367-entry6,460,524-byte historical inventory exceeded its2MiB artifact envelope. That record is preserved atd5d6e74888b65b757ecef075f1bd6838f712cc77. The error was a forecast based on a smaller scope, not a scientific finding.

The v2 operator retains every actual path/pin and adds the old v1 run/checkout/closure records. It changes only duplicate storage of the inventory to deterministic, lossless gzip with independently pinned canonical content. Distinct file paths sharing the same SHA remain distinct protected records. Every original path/pin is explicitly required in the new map.

Scientific implementation, worker, per-row/final numerical auditors and scientific fixtures remain byte-identical. All model/data/h0/seed/train-step/scoring/tolerance decisions stay frozen. The2MiB physical manifest envelope,32MiB total nonraw budget,40MiB maximum raw allocation,256MiB reserve and343,932,928-byte initial floor remain unchanged.

## Shared preflight and integrity

measure_storage.py and execute_once.py use the same actual scope collector. Preparation writes only a compact measurement receipt outside attempt-v2, never the6MB raw map or a model result. Existing objects outside the new v2 repo must match that premeasurement exactly. The final frozen current-repository inventory can only add/change bounded entry metadata (<=64KiB, no removed premeasured path). Complete actual gzip is checked against2MiB at formal preflight, regardless of forecast.

The receipt is copied byte-for-byte into the source freeze and separately checked at beginning/end; it is intentionally not part of its own input inventory. The full protected gzip and receipt are exported as evidence. Codec roundtrip equality is checked before model start and during custody. Corruption is FAIL; representation capacity is BLOCKED. No retry is performed.

## Local validation

DEVELOPMENT_V2_STARTUP_ATTEMPT1.json:11/11 PASS. Coverage includes the new branch/base/old math/v1 HEAD bindings, unchanged capacity and call counts, real collector retention of main untracked files/old runs/closure records, full-map gzip integration, original-scope preservation and receipt-bound premeasurement/delta checks. Codec has its separate development report. Target equivalents remain NOT TESTED until run.

## Freeze dependencies

Root must obtain exact STORAGE_PREFLIGHT.json from the designated Codespace using the preparation source, then include that exact file and update the complete budget proof. Collector/codec/measurement logic must not change after this target measurement. Review and source/test inventories are frozen afterward. Any discrepancy is resolved before freeze; real model data never select storage settings or thresholds.
