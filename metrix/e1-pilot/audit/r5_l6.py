"""R5-A: leakage check L6, DEV part (anchor text vs general DEV windows), built from protocol 2.7 and
DATA_MANIFEST.general_text / .anchor_text only. Data Auditor's own script; no Executor code is imported, called or copied.

general DEV (protocol 2.7):
  eval_sets.jsonl, rows with split == 'dev' only. Every other row is skipped right after its 'split' field is read:
  its tokens are never decoded, re-encoded or counted, and nothing about its content is computed or printed.
  Per domain (books, c4, fineweb, wikitext) the first 25 dev rows in file order;
  decode the row's tokens with the parcae tokenizer (tokenizers.Tokenizer, skip_special_tokens=True);
  re-encode with the pinned Qwen tokenizer (add_special_tokens=False); keep the first 256 ids;
  window text = Qwen decode of those ids.
anchor: the 512 anchor texts I rebuilt myself from the pinned parquet (r4_anchor.py output).

L6 = number of distinct word 13-grams that occur both in some anchor text and in some general DEV window (limit 0).
n-grams are formed inside one document / window only, never across a boundary.
The protocol does not define "word". Units used here (all of them are reported):
  W1 ws    : text.split()                                   maximal runs of non-whitespace, case-sensitive
  W2 wlow  : re.findall(r"\\w+", text.casefold())            Unicode word-character runs, case-folded, punctuation dropped
  W3 wpunc : re.findall(r"\\w+|[^\\w\\s]", text.casefold())   case-folded words, each punctuation mark its own unit
references (not words): Qwen token-id n-grams; character-level longest common substring after casefold and
collapsing whitespace runs to one space (independent of any word definition).
Also run on the untruncated parcae-decoded texts of the same 100 dev rows (a superset of the windows' text).

usage: python -I r5_l6.py <eval_sets.jsonl> <parcae_tokenizer.json> <data_lock.json> <qwen_tok_dir> <my_anchor_json>
                          <data_manifest> <out_general_json> [<executor_general_dev_json> <executor_t5_txt>]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ast, hashlib, json, re
from collections import Counter, defaultdict
from tokenizers import Tokenizer
from common import sha, canon, load_tok, enc

ev_path, ptok_path, lock_path, qdir, anchor_path, dm_path, out_path = sys.argv[1:8]
extra = sys.argv[8:]

dm = json.load(open(dm_path, encoding="utf-8"))
gt = dm["general_text"]
print("DATA_MANIFEST.general_text:", json.dumps(gt, ensure_ascii=False))
DOMAINS = ["books", "c4", "fineweb", "wikitext"]
PER_DOMAIN, MAXTOK = 25, gt["truncate_to_model_tokens"]
assert MAXTOK == 256 and "first 25 windows per domain" in gt["dev"]

# parcae tokenizer identity
pb = open(ptok_path, "rb").read()
lock = json.load(open(lock_path, encoding="utf-8"))
blob = hashlib.sha1(b"blob %d\0" % len(pb) + pb).hexdigest()
meta = os.path.join(os.path.dirname(ptok_path), ".cache", "huggingface", "download", "tokenizer.json.metadata")
rev = etag = None
if os.path.exists(meta):
    rev, etag = open(meta).read().split("\n")[:2]
print("parcae tokenizer.json bytes", len(pb), "sha256", sha(pb), "git-blob-sha1", blob)
print("  Stage 1 data_lock tokenizer_sha256", lock["tokenizer_sha256"], "match:", sha(pb) == lock["tokenizer_sha256"])
print("  hf download metadata: revision", rev, "etag", etag, "| revision == 6247b5d0592876b73660f34c2dd16c9db9e9045c:",
      rev == "6247b5d0592876b73660f34c2dd16c9db9e9045c", "| etag == git-blob-sha1:", etag == blob)
ptok = Tokenizer.from_str(pb.decode("utf-8"))
added = ptok.get_added_tokens_decoder() if hasattr(ptok, "get_added_tokens_decoder") else {}
p_special = {i for i, at in added.items() if getattr(at, "special", False)}
print("  parcae vocab size", ptok.get_vocab_size(with_added_tokens=True), "| special added-token ids:", sorted(p_special))

qtok = load_tok(qdir)
q_special = set(qtok.all_special_ids) | {i for i in range(151643, len(qtok))}

# eval_sets: dev rows only
eh = sha(open(ev_path, "rb").read())
print("eval_sets.jsonl sha256", eh)
split_rows = Counter()
dev_rows = defaultdict(list)            # domain -> list of (file line number, row)
dev_domain_count = Counter()
with open(ev_path, encoding="utf-8") as fh:
    for ln, line in enumerate(fh, 1):
        r = json.loads(line)
        sp = r["split"]
        split_rows[sp] += 1
        if sp != "dev":
            continue                    # not dev: nothing else is read from this row
        dev_domain_count[r["domain"]] += 1
        if len(dev_rows[r["domain"]]) < PER_DOMAIN:
            dev_rows[r["domain"]].append((ln, r))
print("rows by split value:", dict(split_rows), "| non-dev rows decoded: 0 (skipped after reading 'split')")
print("dev rows per domain in the file:", dict(dev_domain_count), "| domains outside the protocol list:",
      sorted(set(dev_domain_count) - set(DOMAINS)))
print("kept per domain:", {d: len(dev_rows[d]) for d in DOMAINS})

windows = []
n_special_parcae = n_tok_ne_257 = 0
for d in DOMAINS:
    for ln, r in dev_rows[d]:
        toks = r["tokens"]
        n_tok_ne_257 += len(toks) != 257
        n_special_parcae += sum(1 for t in toks if t in p_special)
        full = ptok.decode(toks, skip_special_tokens=True)
        ids_full = enc(qtok, full)
        ids = ids_full[:MAXTOK]
        windows.append({"domain": d, "line": ln, "doc_id": r["doc_id"], "full_text": full, "ids": ids,
                        "text": qtok.decode(ids), "n_full": len(ids_full),
                        "text_sha256_field": r["text_sha256"]})
print("general DEV windows:", len(windows), "| dev rows whose parcae token list is not 257 long:", n_tok_ne_257,
      "| parcae special ids inside the kept rows:", n_special_parcae)
print("kept file line numbers per domain (first, last):", {d: (dev_rows[d][0][0], dev_rows[d][-1][0]) for d in DOMAINS})
print("windows whose Qwen ids contain a special / added-token id (>= 151643):", sum(1 for w in windows if any(i in q_special for i in w["ids"])))
print("windows whose parcae-decoded text contains a literal '<|':", sum(1 for w in windows if "<|" in w["full_text"]))
print("windows with re-encoded full text shorter than 256 ids:", sum(1 for w in windows if w["n_full"] < MAXTOK))
print("windows where encode(decode(ids[:256])) != ids[:256] (re-tokenisation drift at the cut):",
      sum(1 for w in windows if enc(qtok, w["text"]) != w["ids"]))
print("text_sha256 field == sha256(parcae-decoded text) for kept rows:",
      sum(1 for w in windows if w["text_sha256_field"] == sha(w["full_text"].encode("utf-8"))), "of", len(windows))
lens = Counter(len(w["ids"]) for w in windows)
print("protocol-tokenizer window lengths {len: count}:", dict(sorted(lens.items())))
print("per-domain min/max length:", {d: (min(len(w["ids"]) for w in windows if w["domain"] == d),
                                        max(len(w["ids"]) for w in windows if w["domain"] == d)) for d in DOMAINS})
texts = [w["text"] for w in windows]
idl = [w["ids"] for w in windows]
print("canonical sha256, list of window texts (domain order books, c4, fineweb, wikitext; file order inside):", sha(canon(texts)))
print("canonical sha256, list of token-id lists (same order):", sha(canon(idl)))
fo = sorted(windows, key=lambda w: w["line"])
print("canonical sha256, list of window texts in file-line order (alternative order):", sha(canon([w["text"] for w in fo])))
with open(out_path, "wb") as fh:
    fh.write(canon([{k: w[k] for k in ("domain", "line", "doc_id", "ids", "text")} for w in windows]))
print("wrote", out_path)

anchor = json.load(open(anchor_path, encoding="utf-8"))
print("anchor texts:", len(anchor), "canonical sha256", sha(canon(anchor)),
      "| == 8828bc4fcc5a3552778839f97909f072050431dd6f74dd08ef47602da11b2408:",
      sha(canon(anchor)) == "8828bc4fcc5a3552778839f97909f072050431dd6f74dd08ef47602da11b2408")

UNITS = {
    "W1 ws   ": lambda t: t.split(),
    "W2 wlow ": lambda t: re.findall(r"\w+", t.casefold()),
    "W3 wpunc": lambda t: re.findall(r"\w+|[^\w\s]", t.casefold()),
}


def grams(seqs, n):
    s = set()
    for x in seqs:
        for i in range(len(x) - n + 1):
            s.add(tuple(x[i:i + n]))
    return s


def report(label, aseqs, gseqs):
    shared, n = [], 1
    while True:
        k = len(grams(aseqs, n) & grams(gseqs, n))
        shared.append(k)
        if k == 0 and n >= 13:
            break
        n += 1
    longest = max([i + 1 for i, v in enumerate(shared) if v] + [0])
    print(f"  {label} | units: anchor {sum(map(len, aseqs))}, general {sum(map(len, gseqs))} | shared distinct n-grams n=1..13: {shared[:13]} | longest shared n: {longest} | 13-grams shared: {shared[12]}")
    return shared[12]


def lcs_chars(A, G):
    """longest common substring (characters) between any text of A and any text of G; binary search on length."""
    def has(k):
        if k == 0:
            return ""
        sub = set()
        for a in A:
            for i in range(len(a) - k + 1):
                sub.add(a[i:i + k])
        for g in G:
            for i in range(len(g) - k + 1):
                if g[i:i + k] in sub:
                    return g[i:i + k]
        return None
    lo, hi, best = 0, max(len(g) for g in G), ""
    while lo < hi:
        mid = (lo + hi + 1) // 2
        r = has(mid)
        if r is not None:
            lo, best = mid, r
        else:
            hi = mid - 1
    return lo, best


cn = lambda t: re.sub(r"\s+", " ", t.casefold())
results = {}
for gname, gtexts, gids in (("100 windows (256 Qwen tokens)", texts, idl),
                            ("same 100 dev rows, untruncated parcae-decoded text", [w["full_text"] for w in windows],
                             [enc(qtok, w["full_text"]) for w in windows])):
    print("== L6 general side:", gname)
    for name, f in UNITS.items():
        results[(gname, name.strip())] = report(name, [f(a) for a in anchor], [f(g) for g in gtexts])
    results[(gname, "tok")] = report("Qwen tok", [enc(qtok, a) for a in anchor], gids)
    k, s = lcs_chars([cn(a) for a in anchor], [cn(g) for g in gtexts])
    print(f"  char-level longest common substring (casefold, whitespace collapsed): {k} chars: {json.dumps(s, ensure_ascii=False)}")

w13 = [v for (g, u), v in results.items() if g.startswith("100 windows") and u.startswith("W")]
print("L6 (DEV part) shared word 13-grams, 100 windows:", {u: v for (g, u), v in results.items() if g.startswith("100 windows")},
      "| limit 0 | within limit under every word definition:", all(v == 0 for v in w13))

if extra:
    ex = json.load(open(extra[0], encoding="utf-8"))
    print("FINAL COMPARISON with the Executor general_dev file:", len(ex), "entries")
    print("  domains/doc_id in the same order:", [(e["domain"], e["doc_id"]) for e in ex] == [(w["domain"], w["doc_id"]) for w in windows])
    print("  ids equal:", [e["ids"] for e in ex] == idl, "| texts equal:", [e["text"] for e in ex] == texts,
          "| parcae_tokens equal to the dev rows' tokens:", [e["parcae_tokens"] for e in ex] == [r["tokens"] for d in DOMAINS for _, r in dev_rows[d]])
    print("  its canonical sha256: texts", sha(canon([e["text"] for e in ex])), "ids", sha(canon([e["ids"] for e in ex])))
if len(extra) > 1:
    t5 = open(extra[1], encoding="utf-8").read()
    print("FINAL COMPARISON with", os.path.basename(extra[1]))
    for pat in (r"general DEV windows: (\d+)", r"protocol-tokenizer lengths: (\{.*?\})",
                r"list of window texts.*?: ([0-9a-f]{64})", r"list of token-id lists.*?: ([0-9a-f]{64})",
                r"anchor texts: 512; canonical sha256 ([0-9a-f]{64})"):
        m = re.search(pat, t5)
        print("  executor", pat, "->", m.group(1) if m else None)
    print("  mine: windows", len(windows), "| lengths", dict(sorted(lens.items())) == ast.literal_eval(re.search(r"protocol-tokenizer lengths: (\{.*?\})", t5).group(1)),
          "(length dict equal) | texts hash equal", sha(canon(texts)) in t5, "| ids hash equal", sha(canon(idl)) in t5,
          "| anchor hash equal", sha(canon(anchor)) in t5)
    for m in re.finditer(r"unit (\w+)\s*\| units: anchor (\d+), general (\d+) \| shared n-grams n=1..13: (\[.*?\]) \| longest shared n <= 13: (\d+)", t5):
        print(f"  executor unit {m.group(1)}: anchor {m.group(2)} general {m.group(3)} shared {m.group(4)} longest<=13 {m.group(5)}")
