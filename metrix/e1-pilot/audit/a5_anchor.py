"""A5: rebuild anchor texts from the pinned parquet per DATA_MANIFEST.anchor_text; compare with the anchor.json used for name generation."""
import json, sys
import pyarrow.parquet as pq
from common import *

pqpath, tokdir, anchor_path = sys.argv[1:4]
print("parquet sha256:", sha(open(pqpath, "rb").read()))
tok = load_tok(tokdir)
pf = pq.ParquetFile(pqpath)
print("columns:", pf.schema_arrow.names)
out, read = [], 0
for b in pf.iter_batches(columns=["text"], batch_size=256):
    for t in b.column(0).to_pylist():
        read += 1
        if len(t) >= 600:
            out.append(tok.decode(enc(tok, t)[:128]))
            if len(out) == 512: break
    if len(out) == 512: break
print("documents read", read, "kept", len(out), "canonical sha256 of texts list", sha(canon(out)))
a = json.load(open(anchor_path))
texts = a["texts"] if isinstance(a, dict) else a
print("equal to anchor.json texts:", out == texts, "| anchor.json canonical sha256", sha(canon(texts)))
