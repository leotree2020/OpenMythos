# MoDA v2 storage-only continuation: independent static review

Status: implementation review complete; final execution approval awaits the exact target storage preflight and the frozen full-artifact budget. Formal target tests and real-model execution remain NOT TESTED. This reviewer has not executed numerical/model code or accessed the target.

## Reviewed scope and unchanged experiment

The continuation starts from checkpoint d5d6e74888b65b757ecef075f1bd6838f712cc77. The old attempt remains BLOCKED and is never retried or rewritten. The new branch/worktree and evidence path are mythos-moda-residual-cpu-v2 and attempt-v2.

The following seven UTF8 source/input files were compared against the original v1 package and are unchanged: moda_model.py, run_moda.py, audit_row.py, audit_moda.py, test_moda_adapter.py, test_audit.py and INPUT_MANIFEST.json. Therefore the model branch, full32 training graph, initialization, data, training budget, scoring, scientific margins and temporary-logit audit/disposal policy are unchanged. All scientific limitations from v1 still apply, including reused development validation and the restricted frozen-feature/output-projection adaptation.

The physical manifest limit remains2MiB; nonraw artifact allocation remains32MiB; raw allocation remains40MiB; disk reserve remains256MiB; total formal disk admission remains343,932,928 bytes. Lossless representation changes do not justify reducing protected objects, skipping hash checks or relaxing a scientific margin.

## Storage and preservation reasoning

storage_codec.py retains the complete absolute path-to-size/SHA256 map. Distinct paths remain distinct even when their contents/pins are identical. Canonical UTF8 JSON is stored in a single gzip member with zero timestamp, no filename and a fixed header. A small receipt binds canonical and compressed sizes/hashes and exact entry count. The decoder rejects invalid schemas, duplicate JSON keys, changed hashes/counts, CRC errors, truncation, trailing or concatenated streams and decompression beyond32MiB. It verifies the canonical representation after decoding. File writes are exclusive and refuse symlink targets/parents; written data is reread and compared to the original full map.

The operator uses the same collect_protected function for pre-freeze target measurement and formal execution. It retains the original physical-file enumeration, main-worktree untracked files and all earlier runs, and adds the sealed v1 checkout/run plus its launch, closure, publication and log records. prior_scope_preserved checks the old manifest pin and all25,367 old path/pin pairs, rather than using a count-only test. No successful historical object is deduplicated out of protection.

The new operator keeps the complete map in memory for before/after custody and independently verifies the stored gzip roundtrip. Only the named protected_before.json.gz is newly admitted to public exports; private tensors, adapter binaries and input text remain excluded. Reports preserve partial progress on a stop rather than claiming all planned cases completed.

## Measurement binding and tests

The target measurement writes a new preparation-v2/STORAGE_PREFLIGHT.json without loading Torch, NumPy or a model. Existing-path pins must match exactly at formal launch. Final changes inside the new source checkout have an explicit64KiB metadata envelope, with no measured current path allowed to disappear, and the final complete compressed inventory must still pass the actual2MiB gate. The current compressed size plus planning margin is a forecast, not a theorem about incremental gzip compression.

The external target receipt is compared byte-for-byte with its package copy bound by SOURCE_MANIFEST; custody rechecks it afterward. It is deliberately not inserted into its own generating inventory, avoiding a self-reference. The original model/data input manifest remains unchanged.

Reviewed local developer reports: storage12/12 PASS (DEVELOPMENT_STORAGE_ATTEMPT2.json), startup11/11 PASS (DEVELOPMENT_V2_STARTUP_ATTEMPT1.json). The storage fixtures cover full distinct-path roundtrip, deterministic serialization, corruption/duplicate-key rejection, exact limits, a real32MiB+1 synthetic decompression case, exclusive writes and simulated symlink rejection. Startup integration exercises historical/main-untracked coverage, old-scope retention, exact receipt binding, changed existing pins, removed current paths and final metadata limits. These are local development results, not target or real-weight evidence. The unchanged adapter24 and auditor13 checks remain required on the target.

## Remaining approval item

Read the actual target preflight receipt and finalized artifact-budget report, verify sufficient current free space and no protected-scope loss, then record the final static verdict. No model execution is approved by this pending section alone.
