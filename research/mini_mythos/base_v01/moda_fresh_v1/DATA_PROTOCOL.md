# MoDA fresh-text data preparation protocol

This is a separately frozen model-blind preparation stage. No original model,
adapter, Torch, gradient, optimizer or model score is loaded here. Preparation is
allowed only on the designated Codespace and its existing data environment.
All original files remain unchanged. A source, scope, decoding, capacity or
selection BLOCKED/FAIL stops preparation and retains the partial records; there
is no alternate source, reduced sample count or relaxed filter.

## Source and intended population

Source is the dataset author's `fancyzhx/ag_news`, revision
`eb185aade064a813bc0b7f42de02595523103ca4`, test split,
`data/test-00000-of-00001.parquet`: 1,234,829 bytes, SHA-256
`71de87ec66bc5737752a2502204dfa6d7fe9856ade3ea444dc6317789a4f13fb`.
The source has 7,600 records with text and four labels. Official metadata and
file pointer were read before acquisition; the content has not been inspected
with a model. The fixed file URL is constructed from the full revision.

This is a long-enough English news-record transfer test, not an IID extension
of the earlier WikiText article-intro set. AG News records contain titles and
descriptions and may cover the same news event. Distinct selected records are
not a guarantee of independent events. Corpus inclusion in Parcae pretraining
is unknown. The dataset card reports unknown license and describes academic
noncommercial research use; original text is retained only in target external
evidence, not exported to the Git repository.

Primary references:
https://huggingface.co/datasets/fancyzhx/ag_news
https://huggingface.co/datasets/fancyzhx/ag_news/blob/eb185aade064a813bc0b7f42de02595523103ca4/data/test-00000-of-00001.parquet

## Fixed eligibility and selection

Exactly20 records, exactly5 from each source label. Labels only provide a
fixed balanced sampling stratum and are never model targets. Within labels
sort by SHA-256 of canonical JSON containing the pinned corpus hash, original
row index and raw UTF8 text hash. Consider labels in numeric order0,1,2,3.

Eligibility requires no U+FFFD, no literal backslash and no `<` or `>`;
alphabetic characters divided by non-whitespace characters must be at least
0.65; at least one `.`, `?` or `!` must be present. These rules do not rewrite
the text. The original pinned tokenizer uses `add_special_tokens=False`; the
whole source text must produce at least129 valid IDs in `[0,32768)`.
Use the first129 IDs without concatenation, synthetic padding or BOS.
Inputs are IDs0:128; score64 predictions at logit positions64:128 against
IDs65:129, exactly as the accepted MoDA pilot. Evaluation h0 seeds remain
5101 and5202, trained-adapter seeds remain4101 and4202. Optimizer steps are0.

Historical exclusions are applied before selection. At selection time compare
each candidate with every already selected new record, including prior labels.
Choose the first5 remaining candidates per label. Do not search another sample
size, source or filter if a label has insufficient candidates. Unchosen eligible
records are recorded and will count as previously inspected project material
in future stages; they are not silently reused as a fresh test.

## Historical exclusion rules

All comparisons use the full source record, not only its truncated129 tokens.
The historical universe must be explicitly frozen in the history specification,
covering all three old WikiText2 parquet files, prior model inputs and prompts,
official CORE JSONL corpus, earlier TinyShakespeare and project synthetic-data
records, and the old tracked/untracked input-bearing project files. Scope includes
the full `/workspaces/OpenMythos` tree (not only research/), all retained
`/workspaces/mythos-evidence` except the new experiment namespace, and previous
protected-inventory files outside these roots, retaining every old inventory key.
Readable input/source files are scanned; explicitly classified serialized numeric
model/checkpoint binaries are pinned and recorded without loading them. The root
coordinator must review the scope and nontext classifications before freezing.
It is not sufficient to exclude only the32 LoRA train/development examples.

The worker checks the exact file enumeration and hashes before acquisition.
Duplicate physical paths are rejected. Byte-identical payloads of the same
format are parsed/tokenized once, while every physical path and its hash remains
in the historical ledger. The only automatic directory exclusions are `.git`
and `__pycache__`; any additional root exclusion must be an absolute path with a
frozen reason, such as the new experiment's own output namespace. Symlinked
history paths require explicit resolution before freeze and otherwise BLOCK.
Within parsed payloads, an exact UTF8 byte-length/SHA-256 cache of at most50,000
strings avoids repeated tokenization. Every string leaf is still counted, every
physical file remains in the ledger, the first exclusion witness is preserved,
and cache saturation never drops a new string. Historical32/12-grams are streamed
against candidate-sized indexes; no character-length shortcut skips Unicode
strings that can encode to32 IDs. Progress is reported every500 historical files.

Reject a candidate on any of these fixed criteria against a historical string
or selected-new string:

1. Texts are exactly equal after Unicode casefold and whitespace collapse.
2. They share any exact consecutive32 original-tokenizer IDs.
3. They share any exact consecutive12 normalized words. Words are regex
   `[a-z0-9]+` after casefold.
4. Both have at least20 unique5-word shingles and intersection size divided by
   the smaller unique-shingle count is at least0.5. The code compares integers
   `2 * overlap >= min(countA,countB)`, including the exact boundary.

Historical token-ID arrays with at least32 valid IDs receive rule2 directly,
even if their tokenizer provenance is unknown; this is conservative and may
reject additional candidates. String fields are parsed from JSON/JSONL, CSV/TSV,
XML text nodes, Python string literals, plain-text files and supported columnar
containers. Existing archives are decoded in memory without extracting paths.
Historical JSON objects preserve all ordered key/value pairs including repeated
keys. NaN/Infinity/-Infinity numeric constants are counted and represented as
nontext numeric metadata; all adjacent and repeated-key string/token values are
still scanned. Per-file notes and global counts record these cases, and original
bytes remain pinned. This does not validate historical numeric results. Frozen
specification and policy JSON remain strict and reject duplicates/nonfinite
constants. Unknown formats, syntactically invalid JSON, unsupported containers
or missing registered files BLOCK rather than disappear from scope.
Explicitly identified binary weights/logits/RNG/checkpoints may be classified
as nontext with a frozen path, size, hash and rationale; arbitrary unknown
binary data must not receive this label automatically.

Exact matching and shingle containment do not prove semantic-paraphrase
independence. The accepted claim is novelty relative to the fully enumerated,
readable retained historical project inputs under these rules. No unrecorded
chat history, unobserved external history or base-pretraining exclusion is claimed.

## Artifacts, capacity and acceptance

Preparation writes one external corpus copy, exact private `inputs.json` with20
rows under the `eval` key, a
small public selection table without original text or token vectors,
`candidates.json.gz`, `history_ledger.json.gz`, acquisition metadata and
`manifest.json`. Gzip ledgers preserve the full logical records and bind both
canonical and compressed hashes; no large duplicate plaintext ledger is saved.
All writes are exclusive. The total preparation allocation is4MiB including a
reserved64KiB stop/seal record, while256MiB of filesystem free space remains
reserved. Public copying/source code/operator receipts have separate budgets in
the experiment coordinator and are not hidden in this preparation allowance.
Acquisition has one request and no retry: HTTP status, expected and observed
size/hash, final URL and bounded response bytes are retained even for403 or hash
failure. Response reading is bounded by the pinned corpus size plus one byte.
SIGTERM/SIGINT records BLOCKED and enters sealing without retrying; any interrupted
source-after hash audit is explicitly NOT TESTED and must be completed by the
coordinator after process exit. An allocation failure still retains its bounded
stop manifest, including any sealing limitation.

PASS requires the pinned source size/hash and source schema, all7,600 candidate
rows accounted, the complete historical file scope accounted/parsed or explicitly
classified nontext, all old source hashes unchanged, exact20 samples/5 per class,
no forbidden imports, no duplicate selected ID or overlap under the frozen
rules, all output bytes within the frozen allocation and exact hashes saved.
Purpose, Environment, Input, Expected, Actual and Status are recorded. Exit0 is
not by itself scientific acceptance. The final input hash must be frozen before
any model evaluation starts. This data gate does not predict a quality result.

## Implementation interface

`data_prepare.py --spec ABS --expected-spec-sha SHA256 --out NEW_ABS`

History spec schema is `mythos-fresh-history-v1`, with `tokenizer_path`,
`history_roots`, optional `extra_history_files`, and explicit `excluded_roots`
entries `{path,reason}`. Either provide exact `history_entries` containing
`{path,bytes,sha256,kind}` or freeze `discover_before_acquisition:true` and exact
`nontext_entries` keyed by absolute path with `{bytes,sha256,reason}`. In the
latter case all paths are enumerated and pinned before acquiring the new source.
Large classification mappings may be stored as an exact gzip JSON file via
`nontext_entries_path` plus `nontext_entries_pin` (`bytes`,`sha256`); analogous
`format_entries_path` and `member_entries_path` fields bind explicit text-format
overrides and archive member classifications. Inline and external forms cannot
be mixed for the same mapping. Archive members use full virtual names such as
`ABS.zip!member` or `ABS.b64!base64!decoded!member`; their bytes/hashes and reasons
are checked before nontext classification. Base64, gzip/xz, zip/tar chains are
decoded in memory with bounded expansion and never extracted into the filesystem.
`extra_history_files_path` plus `_pin` can bind a gzip JSON absolute-path list.
`extra_history_inventory_path` plus `_pin` binds the entire old protected inventory
map of absolute path to `{bytes,sha256}`; all keys join the root enumeration and
every old pin must match current bytes. Policy expansion is bounded to32MiB.
Optional frozen `expected_history_file_count` and `expected_history_suffixes`
must match the union before acquisition. Format/scope policies and original
tokenizer are also pinned again at the end. No large prior path list is duplicated
inline in the specification.
Registered history formats and the actual target inventory must agree before
this protocol is frozen. The target data interpreter is
`/workspaces/mythos-depth-data-cpu312/bin/python -I -B`, Python3.12.3,
PyArrow19.0.1, NumPy1.26.4 and tokenizers0.23.2; no dependency installation.

Current development report `DEVELOPMENT_DATA_ATTEMPT4.json`:28/28 synthetic
standard-library fixtures PASS. Real source acquisition, tokenizer application,
historical scan and data selection remain NOT TESTED until the final target
scope/classification specification and program are frozen.
