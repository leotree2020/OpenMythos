# MoDA v2 storage-only continuation: independent static review

Verdict: APPROVE the storage-only v2 implementation for source freeze and one guarded formal attempt. The actual target storage preflight has been reviewed. Formal target tests and real-model execution remain NOT TESTED. This reviewer read the target receipt and checked local source bytes; this reviewer did not personally access the target or execute numerical/model code.

## Reviewed scope and unchanged experiment

The continuation starts from checkpoint d5d6e74888b65b757ecef075f1bd6838f712cc77. The old attempt remains BLOCKED and is never retried or rewritten. The new branch/worktree and evidence path are mythos-moda-residual-cpu-v2 and attempt-v2.

The following seven source/input files were compared as raw bytes against the original v1 package and are unchanged: moda_model.py, run_moda.py, audit_row.py, audit_moda.py, test_moda_adapter.py, test_audit.py and INPUT_MANIFEST.json. Therefore the model branch, full32 training graph, initialization, data, training budget, scoring, scientific margins and temporary-logit audit/disposal policy are unchanged. All scientific limitations from v1 still apply, including reused development validation and the restricted frozen-feature/output-projection adaptation.

The physical manifest limit remains2MiB; nonraw artifact allocation remains32MiB; raw allocation remains40MiB; disk reserve remains256MiB; total formal disk admission remains343,932,928 bytes. Lossless representation changes do not justify reducing protected objects, skipping hash checks or relaxing a scientific margin.

## Storage and preservation reasoning

storage_codec.py retains the complete absolute path-to-size/SHA256 map. Distinct paths remain distinct even when their contents/pins are identical. Canonical UTF8 JSON is stored in a single gzip member with zero timestamp, no filename and a fixed header. A small receipt binds canonical and compressed sizes/hashes and exact entry count. The decoder rejects invalid schemas, duplicate JSON keys, changed hashes/counts, CRC errors, truncation, trailing or concatenated streams and decompression beyond32MiB. It verifies the canonical representation after decoding. File writes are exclusive and refuse symlink targets/parents; written data is reread and compared to the original full map.

The operator uses the same collect_protected function for pre-freeze target measurement and formal execution. It retains the original physical-file enumeration, main-worktree untracked files and all earlier runs, and adds the sealed v1 checkout/run plus its launch, closure, publication and log records. prior_scope_preserved checks the old manifest pin and all25,367 old path/pin pairs, rather than using a count-only test. No successful historical object is deduplicated out of protection.

The new operator keeps the complete map in memory for before/after custody and independently verifies the stored gzip roundtrip. Only the named protected_before.json.gz is newly admitted to public exports; private tensors, adapter binaries and input text remain excluded. Reports preserve partial progress on a stop rather than claiming all planned cases completed.

## Measurement binding and tests

The target measurement writes a new preparation-v2/STORAGE_PREFLIGHT.json without loading Torch, NumPy or a model. Existing-path pins must match exactly at formal launch. Final changes inside the new source checkout have an explicit64KiB metadata envelope, with no measured current path allowed to disappear, and the final complete compressed inventory must still pass the actual2MiB gate. The current compressed size plus planning margin is a forecast, not a theorem about incremental gzip compression.

The external target receipt is compared byte-for-byte with its package copy bound by SOURCE_MANIFEST; custody rechecks it afterward. It is deliberately not inserted into its own generating inventory, avoiding a self-reference. The original model/data input manifest remains unchanged.

Reviewed local developer reports: storage12/12 PASS (DEVELOPMENT_STORAGE_ATTEMPT2.json), startup11/11 PASS (DEVELOPMENT_V2_STARTUP_ATTEMPT1.json). The storage fixtures cover full distinct-path roundtrip, deterministic serialization, corruption/duplicate-key rejection, exact limits, a real32MiB+1 synthetic decompression case, exclusive writes and simulated symlink rejection. Startup integration exercises historical/main-untracked coverage, old-scope retention, exact receipt binding, changed existing pins, removed current paths and final metadata limits. These are local development results, not target or real-weight evidence. The unchanged adapter24 and auditor13 checks remain required on the target.

## Exact target measurement and final verdict

Reviewed STORAGE_PREFLIGHT.json from preparation commit e1fec5f88f69add0ac8005a1d6debd2da41e48fa, sealed in proof commit 469c7c2ef86d56ba0b2290706877611f5b5da06a. Local raw-byte pin independently checked: 32,488 bytes; SHA256 9908ed2298b5531006e0e7c6aa9ccd5a7a87ed83acb77f2c3ce8b433d89feef6. Its Status is PASS, model_calls is 0, formal_run_started is false, and roundtrip_exact is true.

The shared collector measured 25,431 physical paths. All 25,367 original path/pin pairs are preserved exactly; the increase is 64 paths, not a reduction through deduplication. Canonical representation is 5,991,034 bytes and gzip is 1,180,984 bytes (SHA256 6a4346af1cb6d1fde59f08a80ac1b2b390ee5d54de4b37fbc506953959d22ddf). The existing/non-current-repository part contains 25,401 entries and is pinned separately for formal preflight. Final new-checkout additions are bounded by the already reviewed 64KiB metadata rule.

Two physical compressed copies consume 2,361,968 measured bytes. The explicit planning quantity (1,180,984 + 65,536 + 4,096) * 2 is 2,501,232 bytes, within the unchanged 4,194,304-byte protected-manifest copy envelope. The final full-artifact planning total remains 28,995,348 bytes under the unchanged 33,554,432-byte nonraw allocation. All other receipt, metadata, checkpoint, history, audit/public-copy and Git/finalization envelopes are retained; none is reduced to make this pass. The old 961,111-byte manifest example is historical context only, superseded for this decision by the exact current target receipt. The estimated gzip margin remains planning, not a guaranteed compression bound; actual final gzip and aggregate artifact guards are mandatory.

Measured free space is 349,962,240 bytes, exceeding the unchanged formal admission floor of 343,932,928 by 6,029,312 bytes. This is a measured pre-freeze observation, not a guarantee of later free space. The final frozen launch must independently recheck actual resources, source and input pins, complete scope and exact manifest size. If a gate is BLOCKED or FAIL, it must stop and preserve evidence without retry or budget relaxation.

No unresolved static blocker remains for this bounded continuation. APPROVE does not assert target test success, MoDA quality improvement, equal-compute benefit or fresh generalization. Freeze SOURCE_MANIFEST and TEST_INVENTORY after all final documentation/measurement updates, then execute only the single already authorized v2 attempt. Preserve the old BLOCKED attempt, all thresholds and all upstream files; no automatic stacking or PR24 operation.
