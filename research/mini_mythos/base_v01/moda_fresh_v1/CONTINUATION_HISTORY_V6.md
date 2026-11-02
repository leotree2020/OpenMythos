# Historical JSONL decoder completion for a new protocol

Restored checkpoint: b3565ae4. The old AG News test-source protocol remains
BLOCKED because its retained pre-history candidate counts are 3, 0, 27 and 20,
below the frozen five-per-class requirement. This decoder completion does not
reopen or retry that source protocol and does not establish data novelty.

## Scope and reason

The prior target parser stopped on the retained NarrativeQA JSONL file:
26,476,544 bytes, SHA256
80206805b392801d443defd7a244613ffcc74a17fef80769c5e46c09b9f20bdf.
The checkpoint reports 7,536 complete records and a malformed final record of
2,000 characters. This local stage has not read that corpus. Its structural
fixture uses only synthetic text; no licensed raw corpus text is exported.

The repair affects historical JSONL decoding only. Source constants, row count,
source acquisition paths, tokenizer, sample count, filters, all overlap rules,
all token positions, scientific thresholds and Python V4 recovery are unchanged.
The full historical path inventory remains mandatory. Unknown formats,
invalid UTF8, ordinary malformed JSON, resource errors and unsupported
containers retain their existing stop behavior.

## Exact decoding contract

Records are separated only by literal LF. Unicode line separators inside a
string and escaped newline sequences remain content. Blank records contain
only JSON whitespace space/tab/CR; they are excluded from the complete-record
count. The first-record BOM is omitted only for parsing, retaining the prior
valid-record utf-8-sig behavior. Raw malformed records retain the BOM and their
physical LF terminator when present.

Every complete valid record uses the unchanged history_json/json_leaves path,
including repeated-key values and nonfinite numerical metadata policy. Only
JSONDecodeError enters recovery. Each malformed record first emits all of its
raw text as a historical exclusion witness. Every quote origin is independently
examined, so one malformed escape cannot conceal a later literal.

Recovery decodes only present, valid JSON string units. Complete strings and
known prefixes are emitted. Valid surrogate pairs combine into their Unicode
code point. An incomplete escape, invalid escape, unescaped control character
or unpaired surrogate ends that prefix before the uncertain unit. No replacement
character, missing closing quote, brace, bracket or other absent byte is invented.
All opening square-bracket origins are considered for actual closed literal
arrays; only arrays of at least 32 valid integer tokenizer IDs become token
witnesses. No source expression is executed.

This is conservative lexical coverage, not semantic reconstruction of broken
records. Independent origins may produce additional witnesses and therefore
additional exclusions. Those exclusions cannot make the old quota feasible.

## Resource and evidence contract

All malformed records in one JSONL file share a fixed 256 Mi-character recovery
work bound. Raw/origin traversals, repeated string scans, escape units, emitted
decoded text, bracket searches including unmatched tails, array fragments and
emitted token-array lengths are charged. Exceeding the bound produces BLOCKED;
it does not skip content or silently switch decoders.

The jsonl_recovery leaf is retained in the full history ledger and compact
preflight findings. One summary is emitted for each file with malformed records.
Its nine counters are files, complete_valid_records, malformed_records,
raw_utf8_bytes, string_fragments, decoded_prefixes, token_arrays,
truncated_escapes and rejected_origins. The raw byte count covers malformed
records only, including physical LF terminators. Complete-valid-record totals
in this recovery aggregate cover affected files only.

Each malformed-record note records its zero-based record_index, one-based line,
raw byte count/hash, JSONDecodeError position/column/message, recovery counters
and termination-reason counts. It contains no raw or decoded text. The summary
declares record_boundary=LF, malformed_raw_covered=true and
semantic_reconstruction=false. Actual.historical_jsonl_recovery reconciles
the counters across parsed payloads; byte-identical physical files remain
individually represented by the existing ledger.

## Local acceptance and limits

Purpose: prove the decoder repair preserves readable history while respecting
the declared recovery and resource limits. Environment: local Windows
Python3.12.14, isolated -I -B, synthetic fixtures and the previously pinned
Python invalid-source fixture only. Expected: every planned test executes
without failures, errors or skips; no numerical packages or real tokenizer,
model or new corpus are imported or accessed.

Actual, all first-attempt reports:

- DEVELOPMENT_HISTORY_JSONL_V6_ATTEMPT1.json: 20/20 PASS.
- DEVELOPMENT_DATA_V6_ATTEMPT1.json: 28/28 PASS.
- DEVELOPMENT_HISTORY_PYTHON_V6_ATTEMPT1.json: 18/18 PASS.

The legacy test_duplicate_json_key_and_bad_tail_block ID is retained to preserve
the suite inventory. Its JSONL assertion now verifies raw/recovery coverage;
its strict-JSON duplicate rejection remains unchanged. All old source versions
and development reports remain preserved.

Status: local decoder development PASS. Target historical preflight, complete
historical exclusion, new-source admission and model comparisons remain
NOT TESTED in this stage. The preserved old source remains BLOCKED. These
fixtures do not prove unseen private history or base-model pretraining absence.

Next unique instruction: independently review and freeze this decoder for the
separate new-source protocol; establish that source's per-class feasibility,
then run complete protected-history preflight and exclusion before any model.
Any BLOCKED/FAIL stops dependent work and preserves evidence. No upstream,
scientific threshold, B1, B2/D2-A or PR24 operation is part of this local stage.
