"""R5 (section 4 change): denominators of the token-weighted anchor KL, sum_{x in X_s} (n_x - 1), over the 300 steps.
X_s = documents (4s + i) mod 512, i = 0..3 (protocol 2.7); n_x = token count of anchor document x. The protocol does
not say whether n_x is the count of the original truncated ids (128 for every document) or of the stored decoded text
re-encoded; both are shown. s = 0..299 and s = 1..300 both shown (the protocol does not fix the first index).
Also: weight of each document in the KL term under the token-weighted rule vs a per-document mean (1/4).
usage: python -I r5_kl_denoms.py <tokenizer_dir> <my_anchor_json>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json
from collections import Counter
from common import load_tok, enc

tok = load_tok(sys.argv[1])
anchor = json.load(open(sys.argv[2], encoding="utf-8"))
n_re = [len(enc(tok, t)) for t in anchor]
print("anchor documents:", len(anchor), "| re-encoded n_x {n: count}:", dict(Counter(n_re)), "| documents with n_x != 128:",
      [(i, n) for i, n in enumerate(n_re) if n != 128])
for label, steps in (("s = 0..299", range(0, 300)), ("s = 1..300", range(1, 301))):
    for nlabel, n in (("re-encoded n_x", n_re), ("n_x = 128 (truncated ids)", [128] * 512)):
        den = {s: sum(n[(4 * s + i) % 512] - 1 for i in range(4)) for s in steps}
        odd = {s: d for s, d in den.items() if d != 4 * 127}
        print(f"  {label}, {nlabel}: denominators {dict(Counter(den.values()))} | steps with denominator != 508: {odd}")
s = 85
docs = [(4 * s + i) % 512 for i in range(4)]
w = [(n_re[d] - 1) / sum(n_re[x] - 1 for x in docs) for d in docs]
print(f"step {s} documents {docs}: per-token weight 1/{sum(n_re[x] - 1 for x in docs)}; document share of the KL term "
      f"(token-weighted) {[round(x, 4) for x in w]} vs per-document mean [0.25, 0.25, 0.25, 0.25]")
