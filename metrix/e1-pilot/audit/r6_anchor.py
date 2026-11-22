"""R6-C (part 1): rebuild the 512 anchor documents from the pinned parquet (protocol 2.7, DATA_MANIFEST anchor_text)
and record, per document, the truncated id sequence and the re-encoding of its decoded text.
Data Auditor's own script; no Executor code is imported, called or copied. Exceptions -> RESULT: FAIL (r6_guard).

  documents: first 512 rows of the parquet (file order) whose text has at least 600 characters
  full_ids  = encode(text)                      pinned Qwen tokenizer, add_special_tokens=False
  trunc_ids = full_ids[:128]                    "truncate to 128 model tokens"; its length is computed, not assumed
  anchor_text = decode(trunc_ids)               the stored anchor text (input of L3a, L3b, L6 and of the name rule)
  re_ids    = encode(anchor_text)               what a loader gets if it re-encodes the stored text
Writes <out_dir>/anchor.json (canonical list of the 512 texts; same format as rounds 4-5) and
<out_dir>/anchor_ids.json ({"trunc_ids": [...], "re_ids": [...], "full_len": [...]}).
PASS iff the parquet sha256 equals the pin, 512 documents are found and the texts hash equals the round 2-5 value.
usage: python -I r6_anchor.py <parquet> <qwen_tok_dir> <data_manifest> <out_dir>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, re
from collections import Counter
from common import sha, canon, load_tok, enc
from r6_guard import run

PREV_TEXTS_SHA = "8828bc4fcc5a3552778839f97909f072050431dd6f74dd08ef47602da11b2408"


def main():
    pqpath, tokdir, dm_path, out_dir = sys.argv[1:5]
    import pyarrow.parquet as pq
    at = json.load(open(dm_path, encoding="utf-8"))["anchor_text"]
    print("DATA_MANIFEST.anchor_text:", json.dumps(at, ensure_ascii=False))
    pinned = re.search(r"sha256 ([0-9a-f]{64})", at["source"]).group(1)
    T, NDOC = at["truncate_to_model_tokens"], 512
    fsha = sha(open(pqpath, "rb").read())
    print("parquet sha256", fsha, "| pinned", pinned, "| match", fsha == pinned)
    tok = load_tok(tokdir)
    docs, read = [], 0
    pf = pq.ParquetFile(pqpath)
    for b in pf.iter_batches(columns=["text"], batch_size=256):
        for t in b.column(0).to_pylist():
            read += 1
            if isinstance(t, str) and len(t) >= 600:
                docs.append(t)
                if len(docs) == NDOC:
                    break
        if len(docs) == NDOC:
            break
    full = [enc(tok, d) for d in docs]
    trunc = [f[:T] for f in full]
    texts = [tok.decode(x) for x in trunc]
    re_ids = [enc(tok, t) for t in texts]
    print(f"rows read {read}, documents kept {len(docs)} (truncate_to_model_tokens {T})")
    print("full (untruncated) token count: min", min(map(len, full)), "| documents with fewer than", T, "tokens:",
          [(i, len(f)) for i, f in enumerate(full) if len(f) < T])
    print("truncated id length {len: count}:", dict(sorted(Counter(map(len, trunc)).items())))
    print("re-encoded length of the decoded text {len: count}:", dict(sorted(Counter(map(len, re_ids)).items())))
    diff_len = [(i, len(a), len(b)) for i, (a, b) in enumerate(zip(trunc, re_ids)) if len(a) != len(b)]
    diff_ids = [i for i, (a, b) in enumerate(zip(trunc, re_ids)) if a != b]
    print("documents where len(re-encoded) != len(truncated ids):", diff_len)
    print("documents where re-encoded ids != truncated ids (any position):", diff_ids)
    h = sha(canon(texts))
    print("canonical sha256 of the 512 texts:", h, "| == round 2-5 value", PREV_TEXTS_SHA, h == PREV_TEXTS_SHA)
    print("canonical sha256 of the 512 truncated id lists:", sha(canon(trunc)))
    special = set(tok.all_special_ids) | set(range(151643, len(tok)))
    print("documents whose truncated ids contain an id >= 151643 or a special id:", sum(any(i in special for i in x) for x in trunc))
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "anchor.json"), "wb") as fh:
        fh.write(canon(texts))
    with open(os.path.join(out_dir, "anchor_ids.json"), "wb") as fh:
        fh.write(canon({"trunc_ids": trunc, "re_ids": re_ids, "full_len": list(map(len, full))}))
    print("wrote", os.path.join(out_dir, "anchor.json"), "and anchor_ids.json")
    return fsha == pinned and len(docs) == NDOC and h == PREV_TEXTS_SHA


if __name__ == "__main__":
    run(main)
