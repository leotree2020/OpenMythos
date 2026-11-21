"""R4-A1: rebuild the 512 anchor texts from the pinned parquet (protocol 2.7, DATA_MANIFEST.anchor_text) and write them
as my own intermediate file; checks that bear on the round-4 wording (no special token prepended, t from 2).
usage: python -I r4_anchor.py <parquet> <tokenizer_dir> <data_manifest> <out_anchor_json> [executor_anchor_json_for_final_comparison]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, re
from collections import Counter
import pyarrow.parquet as pq
from common import sha, canon, load_tok, enc

pqpath, tokdir, dm_path, out_path = sys.argv[1:5]
dm = json.load(open(dm_path, encoding="utf-8"))
src = dm["anchor_text"]["source"]
pinned = re.search(r"sha256 ([0-9a-f]{64})", src).group(1)
print("DATA_MANIFEST.anchor_text:", json.dumps(dm["anchor_text"], ensure_ascii=False))
fsha = sha(open(pqpath, "rb").read())
print("parquet sha256:", fsha, "| pinned:", pinned, "| match:", fsha == pinned)
tok = load_tok(tokdir)
pf = pq.ParquetFile(pqpath)
print("columns:", pf.schema_arrow.names, "| rows in file:", pf.metadata.num_rows)
texts, read = [], 0
for b in pf.iter_batches(columns=["text"], batch_size=256):
    for t in b.column(0).to_pylist():
        read += 1
        if len(t) >= 600:                                  # "at least 600 characters"
            texts.append(tok.decode(enc(tok, t)[:128]))   # "truncate to 128 model tokens", decoded text
            if len(texts) == 512:
                break
    if len(texts) == 512:
        break
h = sha(canon(texts))
print("documents read", read, "kept", len(texts), "| canonical sha256 of the texts list", h)
print("previous-round value 8828bc4fcc5a3552778839f97909f072050431dd6f74dd08ef47602da11b2408 match:",
      h == "8828bc4fcc5a3552778839f97909f072050431dd6f74dd08ef47602da11b2408")
print("total chars", sum(len(t) for t in texts))
with open(out_path, "wb") as fh:
    fh.write(canon(texts))
print("wrote", out_path)

# round-4 wording: anchor documents get no prepended special token; t starts at 2 (needs n_x >= 2)
special_ids = set(tok.all_special_ids) | {i for i in range(151643, len(tok))}
re_ids = [enc(tok, t) for t in texts]
n_x = Counter(len(x) for x in re_ids)
print("re-encoded token count n_x per anchor text (count: number of texts):", dict(sorted(n_x.items())))
print("texts with n_x < 2:", sum(1 for x in re_ids if len(x) < 2))
print("texts whose re-encoding contains a special / added-token id (>= 151643):", sum(1 for x in re_ids if any(i in special_ids for i in x)))
print("texts containing a literal '<|' marker:", sum(1 for t in texts if "<|" in t))
print("texts whose first re-encoded id is a special id:", sum(1 for x in re_ids if x and x[0] in special_ids))

if len(sys.argv) > 5:
    ex = json.load(open(sys.argv[5], encoding="utf-8"))
    ex_texts = ex["texts"] if isinstance(ex, dict) else ex
    print("FINAL COMPARISON with Executor anchor file: equal =", ex_texts == texts, "| its canonical sha256", sha(canon(ex_texts)))
