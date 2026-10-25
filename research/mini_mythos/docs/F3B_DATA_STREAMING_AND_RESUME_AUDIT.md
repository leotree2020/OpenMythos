# F3-B Data Streaming and Resume Audit

Status: **AUDIT**. Not a new test.

## Already evidenced

| Item | Status | Limit |
|---|---|---|
| FineWeb-Edu sample-10BT commit `87f09149` | Recorded | Not a training result |
| 14 parquet files, Gate M inventory | VERIFIED | Header/metadata, not full row read |
| Gate N shard count | VERIFIED | No document iteration claimed |
| Gate O file-to-shard map | VERIFIED | Metadata, not row read |
| Gate P two-worker file identity replay | VERIFIED | File IDs, not training |
| Gate Q local 14-shard worker split | 8/8 local PASS | Synthetic local files, remote rows NOT read |

## Not closed

- Remote FineWeb row-level streaming resume: NOT TESTED.
- Real DataLoader resume on WikiText-2: NOT TESTED.
- Native `scripts/train.py` data resume: NOT TESTED.
- Official tokenizer license: BLOCKED.

## Three classes

1. Passed in Git: shard count, file map, local worker split, file-id replay.
2. Code exists, not accepted on real text: OpenMythos loaders and R2 scripts.
3. Missing: a frozen D1 test on a pinned small corpus with train/val/test isolation.

## Design rule

D1 must use a pinned small dataset and compare uninterrupted reads with a save/restore path. Count documents and tokens. Reject duplicates and skips. Do not claim FineWeb resume from the old metadata tests.
