"""Independent acceptance check for stage 1 data (README 验收 2). Usage: python verify_stage1.py STAGE1_CODE_DIR DATA_DIR"""
import collections, hashlib, json, sys
from pathlib import Path
import numpy as np

code, data = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(code))
import ngrams

out = {}
man = json.loads((data / "manifest.json").read_text())
out["manifest_matches_files"] = all(hashlib.sha256((data / n).read_bytes()).hexdigest() == h for n, h in man.items())

rows = [json.loads(l) for l in open(data / "eval_sets.jsonl", encoding="utf-8")]
out["counts"] = {"%s/%s" % k: v for k, v in sorted(collections.Counter((r["domain"], r["split"]) for r in rows).items())}
out["window_lengths"] = sorted(set(len(r["tokens"]) for r in rows))
out["first_token_is_0"] = sum(1 for r in rows if r["tokens"][0] == 0)
out["duplicate_text_sha256"] = len(rows) - len(set(r["text_sha256"] for r in rows))
out["duplicate_doc_id"] = len(rows) - len(set(r["doc_id"] for r in rows))

tokens = np.fromfile(data / "train_tokens.u16", dtype="<u2")
lengths = np.fromfile(data / "train_doc_lengths.i32", dtype="<i4")
out["train_tokens"], out["train_docs"] = int(tokens.size), int(lengths.size)
out["train_lengths_sum_ok"] = int(lengths.sum()) == tokens.size
out["train_contains_token_0"] = int((tokens == 0).sum())
train = ngrams.corpus_set(tokens, lengths)
del tokens
out["train_unique_ngrams"] = int(len(train))

hits = collections.Counter()
for r in rows:
    h = ngrams.hashes(np.asarray(r["tokens"], dtype=np.uint16))
    if ngrams.member(h, train).any():
        hits["%s/%s" % (r["domain"], r["split"])] += 1
out["eval_windows_with_train_13gram"] = dict(hits)

sets = {s: np.unique(np.concatenate([ngrams.hashes(np.asarray(r["tokens"], dtype=np.uint16)) for r in rows if r["split"] == s]))
        for s in ("dev", "test")}
out["dev_test_shared_13grams"] = int(np.intersect1d(sets["dev"], sets["test"]).size)
test_hit = sum(1 for r in rows if r["split"] == "test"
               and ngrams.member(ngrams.hashes(np.asarray(r["tokens"], dtype=np.uint16)), sets["dev"]).any())
out["test_windows_with_dev_13gram"] = test_hit
print(json.dumps(out, indent=1))
