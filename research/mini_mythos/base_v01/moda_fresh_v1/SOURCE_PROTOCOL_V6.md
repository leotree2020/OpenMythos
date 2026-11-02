# AG News train source feasibility V6

Purpose: establish whether a separately frozen source has enough eligible text
to make the unchanged20-text/5-per-label protocol possible. This stage precedes
historical content parsing, historical tokenization, selection and all model
evaluation. It does not repair or rerun the infeasible AG News test protocol.
Base checkpoint: `b3565ae427df93991bb7f78e633f3229c5930dd5`.

The old7,600-row test source remains BLOCKED: its model-blind eligibility upper
bounds are3/0/27/20. Its corpus, ledger, stopped preparations and inactive V5
drafts remain unchanged. A larger train split is a new source protocol, not a
change to any old result. The dataset's split name does not authorize training.

## Frozen inputs and runtime

Dataset: `fancyzhx/ag_news`; revision
`eb185aade064a813bc0b7f42de02595523103ca4`; split `train`;
file `data/train-00000-of-00001.parquet`.
Exact bytes:18,585,438; SHA-256:
`fc508d6d9868594e3da960a8cfeb63ab5a4746598b93428c224397080c1f52ee`.
The fixed URL is the Hugging Face resolve URL containing that full revision and
file path. Exactly120,000 typed text/label rows are required,30,000 rows for each
integer label0,1,2,3. No alternate file, revision, split, retry or fallback.

Official metadata was read by the root coordinator before source acquisition.
The retained `moda_fresh/source-v6-metadata.json` is630 bytes, SHA-256
`6533620e9c04c31062beeff69ffa384a7c90b31c3806a4e5310166f3e79f034e`.
This implementation binds that receipt; it does not repeat the metadata request.

The designated Codespace is `bookish-pancake-vwqx7rr9x5w3wxjr`. The clean research
worktree is `/workspaces/mythos-moda-fresh-cpu-v1`, branch
`mythos-moda-fresh-cpu-v1`, descending from the above base. Require the exact full
execution freeze passed through `--expected-head` and byte-identical committed
source, test and protocol files. Upstream
`/workspaces/mythos-parcae-pinned` must remain clean at
`69284c13746e849104f738d6d1a347b1f457df76` before and after execution.

Use `/workspaces/mythos-depth-data-cpu312/bin/python -I -B`, Python3.12.3,
PyArrow19.0.1, NumPy1.26.4 and tokenizers0.23.2. No installation or GPU.
Set tokenizer parallelism false, Rayon/OpenBLAS threads1 and CUDA visibility
empty before library import; record initial and effective values. The pinned
original tokenizer is
`/workspaces/mythos-evidence/base_v01/b1/b1-20261101T021657Z/downloads/tokenizer/tokenizer.json`,
SHA-256 `e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77`.
Encode with `add_special_tokens=False`; no text rewriting, padding or BOS.
Torch, parcae_lm, receval and transformers imports are forbidden.

## Gate order

1. Check target/runtime, exact clean source commit, branch/ancestry and upstream.
   Require `specification-v6/FREEZE_RECEIPT.json` PASS at this same execution
   freeze. Bind its `DATA_SPEC.json`, physical/canonical history mapping hashes,
   original specification and all reused policies. The expanded inventory must
   preserve32,244 original paths and include the entire previously inspected
   test corpus and older fresh namespace. Only specification-v6, source-v6,
   preparation-v6 and attempt-v6 are excluded by the separately frozen cutoff.
   Reading and hashing this inventory is not historical content scanning.
2. Pin metadata, tokenizer, committed sources and all existing fresh-namespace
   files, excluding only this new output directory. Admit the fixed storage
   budget before downloading. One request attempt fetches the exact file.
   HTTP200, exact size and SHA are mandatory. Keep the bounded received body,
   final URL/status, observed size/SHA and primary network error on failure.
   Read at most the pinned size plus one byte; never retry.
3. Process all120,000 rows in original row order using batches of1,024. The
   frozen prose rules reject U+FFFD, literal backslash, angle brackets, alphabetic
   fraction below0.65 among non-whitespace characters, or missing `.?!`.
   Only prose-eligible rows are tokenized. Every ID must be an integer in
   `[0,32768)`; at least129 tokens are required. These are the exact old
   `prose_reason` and token-eligibility semantics, copied independently without
   importing an unfinished historical parser. No fingerprint/overlap operation
   can change an eligibility decision in this stage.
4. Save the complete compressed row ledger before checking the quota gate.
   Require all row indices0..119999 once, unique recomputed row identities,
   exactly30,000 rows per label and a completed decision for every row. Only then
   require at least5 eligible rows **separately in every label**. A deficient
   label is BLOCKED; a schema/count/hash/ID mismatch is FAIL. No dependent
   historical scan or model execution follows either state.

The per-label gate is a necessary condition only. Historical exclusion and
new-new exclusion may still make20 texts impossible. Do not use a premature
greedy new-new selection to declare this gate impossible: removing historical
matches can change the later greedy order. This stage selects0 examples and
does not claim freshness, model improvement or successful historical exclusion.

## Evidence, preservation and storage

All outputs are exclusive in
`/workspaces/mythos-evidence/base_v01/moda_fresh/source-v6`:

- `corpus.parquet` for a successful exact acquisition, otherwise
  `failed_acquisition_response.bin` with bounded received bytes.
- `acquisition.json`: fixed URL and expected pin; request_attempts1;
  HTTP/final URL, bounded response limit, observed bytes/hash, body pin, status
  and primary error when applicable.
- `candidates.json.gz`: every complete or partial row receipt in source order.
  Rows contain id, row, label, text_sha256, decision, full_token_count,
  tokenization_started and tokenization_performed. Prose-rejected rows have
  null token count, clearly distinguished from zero-token output.
  No raw text, token arrays or shingle copies are added to this ledger.
- `old_fresh_before.json.gz`: complete pre-existing fresh-namespace byte pins.
- `manifest.json`: Purpose, Environment, Input, Expected, Actual, status,
  error/custody/sealing limitations, all artifact pins and stage counters.

Canonical JSON is sorted-key compact UTF-8 with one final LF. Row id is SHA-256
of canonical `{corpus_sha256,row,text_sha256}`, identical to the old identity
rule with the new corpus hash. Gzip receipts preserve both physical and canonical
`{bytes,sha256}` pins. Plaintext duplicate ledgers are not written. The entire
original corpus is retained externally; raw text is not exported to Git.
The later separately frozen history stage may reread/tokenize this same corpus,
must reconcile the source ledger row by row, and must not redownload or copy it.

The source output allocation is64MiB, including corpus, gzip ledgers, receipts,
any development/operator records placed in this directory, and a64KiB reserved
stop manifest. Every write checks the remaining allocation and preserves256MiB
of filesystem free space. The ledger contains bounded receipt fields rather than
source text; final measured usage is reported. The new allocation is a storage
budget for this larger source, not a scientific or deduplication threshold change.

Recheck original tokenizer, metadata, specification, policies, source code,
acquired corpus, source checkout/upstream and every prior fresh-namespace file
after the stage. A custody mismatch is FAIL. Any interruption stops the one
attempt, keeps partial rows/received bytes and reports BLOCKED. If a failure
prevents a complete ledger or stop record, report that limitation rather than
claiming full preservation. Do not retry or overwrite the directory. Coordinator
stdout/stderr must live outside the preserved fresh namespace while it runs.

## Acceptance and next boundary

PASS requires all byte/runtime/custody/count checks, a complete120,000-row
ledger,30,000 rows per source label, at least5 eligible rows in each label,
lossless receipts within budget and zero history/model/optimizer activity.
Exit0 alone is insufficient. Report the actual four eligibility counts and
decision distribution. Synthetic fixtures and static review are development
evidence only; target execution and source eligibility remain NOT TESTED until
this separately frozen CLI runs once.

After a genuine source PASS, stop at this stage boundary and provide the receipt
to the coordinator. Only a separately frozen history preparer/auditor may use the
corpus, apply unchanged full-text exclusion, and select20. No automatic launch
from this program. Upstream, weights, A5/early-stop/quality thresholds remain
unchanged. No B1 rerun, B2/D2-A, mechanism stacking, GPU or PR24 merge.
Formal Oracle remains BLOCKED/NOT_READY; FORMAL_ACCEPTANCE_READY=False.
