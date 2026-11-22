"""R5 (section 4 change), corrected in round 6: denominators of the token-weighted anchor KL,
sum_{x in X_s} (n_x - 1), over the 300 steps. X_s = documents (4s + i) mod 512, i = 0..3 (protocol 2.7 and 4).
Round 6, item 1c: n_x = length of the id sequence actually fed to the model.

Round-6 correction (Owner round 6, item 5): the round-5 version used [128] * 512 as the length of the truncated ids,
an assumption, not a value computed from the data. This version computes it:
  trunc_len[x] = len(encode(document x)[:128])         from the pinned parquet (independent of the anchor JSON)
  re_len[x]    = len(encode(anchor text x))            the stored decoded text re-encoded
and compares the two per document (lengths and ids). Both candidates for "the id sequence actually fed" are shown;
s = 0..299 and s = 1..300 both shown (the protocol does not fix the first index; the 300 steps are in section 7).
Also: share of each document in the KL term under the token-weighted rule vs a per-document mean (1/4).
Exceptions -> RESULT: FAIL, non-zero exit (r6_guard). PASS iff the decoded truncated ids reproduce my anchor texts.
usage: python -I r5_kl_denoms.py <tokenizer_dir> <my_anchor_json> <anchor_parquet>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json
from collections import Counter
from common import load_tok, enc
from r6_guard import run

T, NDOC, STEPS = 128, 512, 300


def main():
    import pyarrow.parquet as pq
    tok = load_tok(sys.argv[1])
    anchor = json.load(open(sys.argv[2], encoding="utf-8"))
    docs = []
    for b in pq.ParquetFile(sys.argv[3]).iter_batches(columns=["text"], batch_size=256):
        for t in b.column(0).to_pylist():
            if isinstance(t, str) and len(t) >= 600:
                docs.append(t)
                if len(docs) == NDOC:
                    break
        if len(docs) == NDOC:
            break
    trunc = [enc(tok, d)[:T] for d in docs]
    texts_match = len(anchor) == NDOC and [tok.decode(x) for x in trunc] == anchor
    print("documents from parquet:", len(docs), "| anchor texts:", len(anchor),
          "| decode(truncated ids) == my anchor text for all 512:", texts_match)
    n_tr = [len(x) for x in trunc]                       # computed from the data (round-6 fix; was [128] * 512)
    re_ids = [enc(tok, t) for t in anchor]
    n_re = [len(x) for x in re_ids]
    print("truncated id length n_x {n: count}:", dict(Counter(n_tr)), "| documents with n_x != 128:",
          [(i, n) for i, n in enumerate(n_tr) if n != T])
    print("re-encoded length {n: count}:", dict(Counter(n_re)), "| documents with n_x != 128:",
          [(i, n) for i, n in enumerate(n_re) if n != T])
    print("per document: len(truncated ids) != len(re-encoded):", [i for i in range(NDOC) if n_tr[i] != n_re[i]],
          "| truncated ids != re-encoded ids:", [i for i in range(NDOC) if trunc[i] != re_ids[i]])
    for label, steps in (("s = 0..299", range(0, STEPS)), ("s = 1..300", range(1, STEPS + 1))):
        for nlabel, n in (("n_x = len(truncated ids)", n_tr), ("n_x = len(re-encoded text)", n_re)):
            den = {s: sum(n[(4 * s + i) % NDOC] - 1 for i in range(4)) for s in steps}
            odd = {s: (den[s], [(4 * s + i) % NDOC for i in range(4)]) for s in steps if den[s] != 4 * (T - 1)}
            print(f"  {label}, {nlabel}: denominators {{value: steps}} {dict(sorted(Counter(den.values()).items()))} "
                  f"| min {min(den.values())} max {max(den.values())} sum {sum(den.values())} "
                  f"| steps with denominator != {4 * (T - 1)} (denominator, documents): {odd}")
    for s in sorted({s for s in range(0, STEPS + 1) if 340 in [(4 * s + i) % NDOC for i in range(4)]}):
        d = [(4 * s + i) % NDOC for i in range(4)]
        tot = sum(n_tr[x] - 1 for x in d)
        print(f"step {s} documents {d}: KL token count {tot}; document share of the KL term (token-weighted) "
              f"{[round((n_tr[x] - 1) / tot, 4) for x in d]} vs per-document mean [0.25, 0.25, 0.25, 0.25]")
    return texts_match


if __name__ == "__main__":
    run(main)
