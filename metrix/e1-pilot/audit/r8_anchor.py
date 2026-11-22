"""R8-3: anchor text (DATA_MANIFEST anchor_text, round 8 item 1d). Data Auditor's own script; no Executor code is
imported, called or copied (in particular not reports/round2/anchor_check.py). Exceptions -> RESULT: FAIL (r6_guard).

Expected values are read from the freeze commit (git cat-file blob <commit>:metrix/e1-pilot/DATA_MANIFEST.json):
  anchor_text.source                         -> pinned parquet sha256 (the 64-hex inside "(sha256 ...)")
  anchor_text.decoded_texts_canonical_sha256 -> expected canonical SHA-256 of the 512 decoded texts
Rule implemented (anchor_text.selection / document_rule / decoded_texts_hash_rule, protocol 2.7):
  documents = rows of the parquet in file order whose "text" has at least 600 characters (Python len), first 512;
  ids_i  = encode(document_i, add_special_tokens=False)[:128]   (pinned Qwen tokenizer, transformers 5.22.2)
  text_i = decode(ids_i) with default arguments
  hash   = sha256(json.dumps([text_0..text_511], sort_keys=True, ensure_ascii=False, separators=(",", ":"),
                             allow_nan=False).encode("utf-8"))
Informational alternatives (ALT, not used for PASS): decode(skip_special_tokens=True); tokenizers-backend decode;
no truncation; threshold > 600.
Writes <out_dir>/anchor_texts.json (canonical bytes of the list) for r8_facts.py.
Prints AUDIT_VALUE lines for r8_compare.py.
PASS iff parquet sha256 == pinned and the decoded-texts hash == manifest value.
usage: python -I r8_anchor.py <repo_root> <commit> <parquet> <qwen_tok_dir> <out_dir>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, re, subprocess, hashlib
from collections import Counter
from common import sha, canon, load_tok, enc
from r6_guard import run


def manifest(repo, commit, name):
    return json.loads(subprocess.run(["git", "-C", repo, "cat-file", "blob", f"{commit}:metrix/e1-pilot/{name}"],
                                     capture_output=True, check=True).stdout)


def file_sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    repo, commit, pqpath, tokdir, out_dir = sys.argv[1:6]
    import pyarrow.parquet as pq, transformers
    at = manifest(repo, commit, "DATA_MANIFEST.json")["anchor_text"]
    print("freeze-commit DATA_MANIFEST.anchor_text:")
    for k, v in at.items():
        print(f"  {k}: {v}")
    pinned = re.findall(r"sha256 ([0-9a-f]{64})", at["source"])
    assert len(pinned) == 1, pinned
    pinned = pinned[0]
    exp_texts = at["decoded_texts_canonical_sha256"]
    T = at["truncate_to_model_tokens"]
    assert T == 128, T
    ok = True
    fsha = file_sha(pqpath)
    print(f"parquet sha256 {fsha} | manifest {pinned} | MATCH {fsha == pinned}")
    print(f"AUDIT_VALUE parquet_sha256 {fsha}")
    ok &= fsha == pinned
    pf = pq.ParquetFile(pqpath)
    print("parquet schema columns:", pf.schema_arrow.names, "| row groups", pf.num_row_groups, "| rows", pf.metadata.num_rows)
    tok = load_tok(tokdir)
    print("tokenizer:", type(tok).__name__, "| len", len(tok), "| transformers", transformers.__version__,
          "| files in dir", sorted(x for x in os.listdir(tokdir) if not x.startswith(".")))
    docs, read = [], 0
    for b in pf.iter_batches(columns=["text"], batch_size=128):
        for t in b.column(0).to_pylist():
            read += 1
            if isinstance(t, str) and len(t) >= 600:
                docs.append(t)
                if len(docs) == 512:
                    break
        if len(docs) == 512:
            break
    print(f"rows read until the 512th kept document: {read} | kept {len(docs)}")
    ok &= len(docs) == 512
    texts, alt_skip, alt_backend, alt_full, lens = [], [], [], [], Counter()
    for d in docs:
        full = enc(tok, d)
        ids = full[:T]
        lens["128" if len(ids) == T else "<128"] += 1
        texts.append(tok.decode(ids))
        alt_skip.append(tok.decode(ids, skip_special_tokens=True))
        alt_backend.append(tok.backend_tokenizer.decode(ids))
        alt_full.append(tok.decode(full))
    print("documents with 128 ids / fewer:", dict(lens), "| total chars of the 512 texts", sum(len(t) for t in texts))
    h = sha(canon(texts))
    print(f"decoded texts (512) canonical sha256 {h} | manifest {exp_texts} | MATCH {h == exp_texts}")
    print(f"AUDIT_VALUE anchor_decoded_texts_canonical_sha256 {h}")
    ok &= h == exp_texts
    for label, alt in (("ALT decode(skip_special_tokens=True)", alt_skip), ("ALT tokenizers backend decode", alt_backend),
                       ("ALT no truncation (full document decode)", alt_full)):
        print(f"{label}: sha256 {sha(canon(alt))} | equal to main texts: {alt == texts}")
    alt_gt = []
    read2 = 0
    for b in pf.iter_batches(columns=["text"], batch_size=128):
        for t in b.column(0).to_pylist():
            read2 += 1
            if isinstance(t, str) and len(t) > 600 and len(alt_gt) < 512:
                alt_gt.append(tok.decode(enc(tok, t)[:T]))
        if len(alt_gt) == 512:
            break
    print(f"ALT threshold len > 600: sha256 {sha(canon(alt_gt))} | equal to main: {alt_gt == texts}")
    sp = [i for i, t in enumerate(texts) if any(s in t for s in ("<|endoftext|>", "<|im_start|>", "<|im_end|>"))]
    print("texts containing a special-token string:", sp)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "anchor_texts.json"), "wb") as fh:
        fh.write(canon(texts))
    print("wrote", os.path.join(out_dir, "anchor_texts.json"))
    return ok


run(main)
