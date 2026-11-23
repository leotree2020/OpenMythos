"""IA-3: anchor text (protocol 2.7; DATA_MANIFEST anchor_text at the freeze commit).
  documents = rows of the parquet ("text" column) in file order with len(text) >= 600 characters; the first 512;
  ids_i  = encode(document_i, add_special_tokens=False)[:128]  (pinned Qwen tokenizer, transformers 5.22.2)
  text_i = decode(ids_i) with default arguments
  frozen value: canonical SHA-256 of the JSON list [text_0 .. text_511]  (decoded_texts_hash_rule)
Writes <out_dir>/anchor.json: [{"row": parquet row index, "ids": ids_i, "full_len": len of the full encoding,
"text": text_i}, ...] for the later ia_ scripts.
Data Auditor's own script; no Executor code imported, called or copied.  Loads the tokenizer only.
usage: python -I ia_03_anchor.py <repo_root> <parquet> <qwen_tok_dir> <out_dir>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, re
from collections import Counter
from ia_common import sha, canon, file_sha, frozen_json, load_qwen, enc, run


def main():
    repo, pq_path, qdir, out_dir = sys.argv[1:5]
    import pyarrow.parquet as pq
    ok = True
    at = frozen_json(repo, "DATA_MANIFEST.json")["anchor_text"]
    for k in ("source", "selection", "truncate_to_model_tokens", "document_rule", "decoded_texts_canonical_sha256"):
        print(f"freeze-commit anchor_text.{k}: {at[k]}")
    MAXT = at["truncate_to_model_tokens"]
    ok &= MAXT == 128 and "at least 600 characters" in at["selection"] and "first 512" in at["selection"]
    pin = re.findall(r"sha256 ([0-9a-f]{64})", at["source"])[0]
    h = file_sha(pq_path)
    print(f"parquet sha256 {h} | pinned {pin} | MATCH {h == pin}")
    ok &= h == pin
    pf = pq.ParquetFile(pq_path)
    print("parquet columns", pf.schema_arrow.names, "| rows", pf.metadata.num_rows, "| row groups", pf.num_row_groups)
    tok = load_qwen(qdir)
    print("tokenizer class", type(tok).__name__, "| len", len(tok), "| dir files", sorted(x for x in os.listdir(qdir) if not x.startswith(".")))
    docs, row = [], -1
    for batch in pf.iter_batches(columns=["text"], batch_size=256):
        for t in batch.column(0).to_pylist():
            row += 1
            if isinstance(t, str) and len(t) >= 600:
                docs.append((row, t))
                if len(docs) == 512:
                    break
        if len(docs) == 512:
            break
    print("parquet rows read up to the 512th selected document:", row + 1, "| selected", len(docs),
          "| first rows", [r for r, _ in docs[:5]], "| last row", docs[-1][0])
    ok &= len(docs) == 512
    out = []
    for r, d in docs:
        full = enc(tok, d)
        ids = full[:MAXT]
        out.append({"row": r, "ids": ids, "full_len": len(full), "text": tok.decode(ids)})
    nx = Counter(len(x["ids"]) for x in out)
    print("ids per document {n: count}:", dict(sorted(nx.items())), "| documents with fewer than 128 ids:",
          [(i, len(x["ids"]), x["full_len"]) for i, x in enumerate(out) if len(x["ids"]) < MAXT])
    ok &= all(len(x["ids"]) == min(MAXT, x["full_len"]) for x in out)
    special = set(tok.all_special_ids)
    print("documents containing a special-token id:", [i for i, x in enumerate(out) if special & set(x["ids"])])
    texts = [x["text"] for x in out]
    ht = sha(canon(texts))
    exp = at["decoded_texts_canonical_sha256"]
    print(f"anchor decoded texts (512) canonical sha256 {ht} | frozen {exp} | MATCH {ht == exp}")
    print(f"AUDIT_VALUE anchor_texts_canonical_sha256 {ht}")
    ok &= ht == exp
    print("id lists canonical sha256 (informational):", sha(canon([x["ids"] for x in out])))
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "anchor.json"), "wb") as fh:
        fh.write(canon(out))
    print("wrote", os.path.join(out_dir, "anchor.json"))
    return bool(ok)


run(main)
