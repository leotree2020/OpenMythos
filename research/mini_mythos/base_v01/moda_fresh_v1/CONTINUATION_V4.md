# Fresh-text preparation continuation V4

Base checkpoint: `b13ab1d799cbd5d37e58d7ea7cdf2540d0093493`. The earlier
preparation-v1 import failure, preparation-v2 historical Python parsing stop and
resource-blocked continuation remain preserved. V4 changes historical decoding
and startup/evidence plumbing only. Source corpus/revision/hash, original
tokenizer, 20 records (5 per class), eligibility filters, all deduplication
thresholds, token/target layout, weights and scientific screens remain unchanged.
No model or upstream code is changed here.

## Actual defect and conservative repair

The retained source `fixtures/history_invalid_inventory.txt` is 2,345 bytes,
SHA-256 `403eee09aec392aa00eb24b46633e64c1333377f13b80e503e4ebf3f7a834bb8`.
Its line 25 contains an actual newline within an ordinary quoted string. It is
not executable Python; its existence in historical evidence must not make the
rest of that file disappear from text-exclusion coverage.

Valid Python uses the previous AST walk unchanged, including the original
literal/token-array locations. If a source has a SyntaxError or invalid-source
ValueError, the scanner first emits the entire decoded raw source as one text
witness. It then examines every quote origin independently, including possible
valid prefixes and all origins after unterminated single/triple quotes. Complete
literal fragments are parsed as expressions without execution; string constants
and literal token arrays are retained. Escapes, raw prefixes and complete
multiline strings are decoded by Python's AST parser. Adjacent complete string
constants separated only by whitespace/comments are also concatenated as a
conservative extra witness. Every `[` and `(` origin is separately considered
for a closed, literal integer list/tuple of at least 32 valid tokenizer IDs.
No `eval`, import, function call, generated program or original-source execution
is used. False-positive extra exclusions are possible and are accepted here.

An unmatched quote does not terminate the search for later origins. Recovery
has a fixed 256 Mi-character scanning-work bound per malformed source, including
adjacent-literal whitespace/comment traversal, literal spans, emitted joined
text length and unsuccessful bracket-tail searches; exceeding it BLOCKS rather
than skipping content. Unknown formats, unreadable files,
invalid UTF8, malformed JSON and unsupported containers retain their existing
BLOCKED/FAIL behavior. Every physical history path remains in scope and pinned.

Per-file `python_recovery` notes include original syntax-error coordinates,
`raw_source_covered=true`, `semantic_reconstruction=false`, and these six
integer counters: `files`, `raw_utf8_bytes`, `string_fragments`, `token_arrays`,
`adjacent_string_groups`, `rejected_origins`. Global manifest totals use
`Actual.historical_python_recovery`. Existing JSON format-note counters are
unchanged. The repair is not complete semantic reconstruction of broken Python:
computed strings, dynamic expressions, variable substitutions and inferred
intended repairs are not executed or guessed. Raw text plus safely recovered
literal fragments is the declared coverage, not proof of unseen private or
pretraining content.

## Complete format preflight

First invoke the designated data interpreter with `-I -B`:

```
data_prepare.py --spec ABS --expected-spec-sha SHA --out preparation-v4/history-preflight --history-preflight-only
```

This enumerates and parses all 32,244 frozen history paths and supported
containers, including explicit registered nontext classifications and every
malformed-file recovery. It does not acquire/read the new corpus, construct or
call the original tokenizer, select examples or load a model. Data-only columnar
readers are required for existing historical parquet files. Byte-identical
payloads reuse parsing while every physical path remains accounted.

The preflight emits a compact manifest and lossless
`preflight_findings.json.gz`, containing every full ledger row with Python
recovery, JSON format notes, an error or FAIL/BLOCKED status. It does not retain
a duplicate full success ledger. `Actual.history_ledger_projection` binds an
ordered canonical projection of all rows: required `path`, `bytes`, `sha256`,
`kind`, `Status`; optional `reason`, `identical_to`. Encoding is sorted-key,
compact UTF8 JSON plus one final LF. Its schema is
`mythos-history-format-projection-v1` with record count and canonical bytes/hash.
The later independent data audit recomputes this projection from the actual
full preparation ledger and compares the complete findings.

PASS requires `historical_files=historical_files_completed=32244`,
`parse_completed=true`, `tokenizer_calls=new_source_acquisitions=model_calls=0`,
all required original pins preserved and no forbidden model imports. A partial
or failed preflight stops the continuation before new selection. Per-stage
Purpose/Environment/Input/Expected/Actual/Status are retained. Exit zero alone
does not establish this acceptance.

## Reuse the already verified original corpus

After preflight PASS, invoke the unchanged normal preparation path with:

```
data_prepare.py --spec ABS --expected-spec-sha SHA --out preparation-v4/data --source-file /workspaces/mythos-evidence/base_v01/moda_fresh/preparation-v2/data/corpus.parquet
```

The corpus remains exactly 1,234,829 bytes with SHA-256
`71de87ec66bc5737752a2502204dfa6d7fe9856ade3ea444dc6317789a4f13fb`.
The exact retained path is required. Its sibling original `acquisition.json`
must report PASS, the frozen URL, HTTP200, matching observed/pinned source bytes
and `response_file=corpus.parquet`. Both retained files are byte-bound before
and after use. No network request, alternate source or duplicate corpus file is
made. A normal legacy invocation without `--source-file` remains implemented
for compatibility, but is not used or authorized by the V4 launcher.

New `source_reference.json` uses schema `mythos-local-corpus-reference-v1` and
fields `mode=LOCAL_PINNED_REUSE`, `Status=PASS`, `source_file`, `source_pin`,
`original_acquisition_file`, `original_acquisition_pin`, `network_requests=0`,
`copied_corpus_bytes=0`. New `acquisition.json` repeats those common fields and
adds frozen `url`, `expected`, and the exact `source_reference_pin`. No local
`corpus.parquet` artifact is present in preparation-v4/data. The independent
audit verifies the external source/provenance and all selection/ledger rules.

The combined preflight plus data output envelope remains 4 MiB, including a
64 KiB final seal allowance; the unused disk reserve remains 256 MiB. The normal
writer counts existing sibling history-preflight files on every write. Helper,
operator and frozen source files retain their separately declared budget. No old
evidence is deleted and no storage admission threshold is lowered.

## Development state and limits

`DEVELOPMENT_HISTORY_PYTHON_V4_ATTEMPT4.json` records 18/18 local synthetic/parser
checks PASS, including the actual pinned malformed file, later literals after
both quote failures, escaped/raw/multiline/adjacent literals, numeric arrays,
non-execution, unchanged valid-AST behavior, preflight projection parity,
no-network exact retained-source reuse, bounded adjacent/bracket recovery and
the combined storage boundary.
These fixtures do not establish target preflight/data/model PASS. Original
28-test data suite passed under the exact isolated launch, recorded in
`DEVELOPMENT_DATA_ATTEMPT7.json`. All earlier attempts and development reports remain preserved.

Next unique action after source freeze: run complete V4 format preflight, then
only if PASS perform one retained-source preparation and its independent audit.
Any BLOCKED/FAIL stops dependent work and seals evidence. No model, new mechanism,
threshold tuning, upstream modification or PR24 operation is authorized by this
data stage.
