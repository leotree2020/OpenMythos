import pyarrow.parquet as pq
from transformers import AutoTokenizer
tok = AutoTokenizer.from_pretrained("qwen_tok")
path = "r4/cache/data/sample-100BT/train/shard_00000.parquet"
docs = []
for batch in pq.ParquetFile(path).iter_batches(columns=["text"], batch_size=256):
    for t in batch.column(0).to_pylist():
        if isinstance(t, str) and len(t) >= 600:
            docs.append(t)
            if len(docs) == 512:
                break
    if len(docs) == 512:
        break
n = [len(tok.encode(d, add_special_tokens=False)) for d in docs]
print("documents:", len(docs))
for i, (d, k) in enumerate(zip(docs, n)):
    if k < 128:
        cut = tok.encode(d, add_special_tokens=False)[:128]
        same = tok.encode(tok.decode(cut), add_special_tokens=False) == cut
        print("doc index %d: %d chars, %d tokens before the cut (n_x = %d); decode/re-encode round trip identical: %s" % (i, len(d), k, min(k, 128), same))
print("documents with fewer than 128 tokens before the cut:", sum(k < 128 for k in n))
