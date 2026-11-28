"""data-auditor: independent L6 TEST-part count (protocol section 3 L6; section 8 step 8; ST10).

Written by data-auditor; does not import or reuse any Executor code (metrix_e1.*).
Prints only counts, hashes, line counts and structural info. Never prints any
row, field value text or n-gram. Exceptions are reported as type + line number only.

Rule (protocol 3, L6 row): words = str.split(); 13-grams taken within each
document (each anchor document, each window), never across documents; union over
512 anchor docs vs union over all general_test windows; count = size of intersection.
Text = decode (pinned Qwen tokenizer) of the ids actually fed to the model
(anchor <= 128 ids, window <= 256 ids).
"""
import hashlib
import json
import sys
import traceback

ANCHOR = "/root/metrix-run/metrix-work/data/anchor_text.jsonl"
GTEST = "/root/metrix-run/metrix-work/test/general_test.jsonl"
TOKDIR = "/root/metrix-run/metrix-inputs/qwen_tokenizer"
OUT = "/root/OpenMythos/metrix/e1-pilot/audit/st10_l6_test_count.json"
FROZEN = "87a244db28a901f9e89282b50df76778ab5c2887"
TOK_SHA = {
    "tokenizer.json": "aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4",
    "tokenizer_config.json": "d5d09f07b48c3086c508b30d1c9114bd1189145b74e982a265350c923acd8101",
    "vocab.json": "ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910",
    "merges.txt": "8831e4f1a044471340f7c0a83d7bd71306a5b867e95fd870f74d0c5308a904d5",
}
ANCHOR_DECODED_SHA = "8828bc4fcc5a3552778839f97909f072050431dd6f74dd08ef47602da11b2408"
ANCHOR_BYTE_SHA = "2089e656819d1fe0f6ececcc26e5cade09ee80a92c50e7c8f607fa4e0ef46da5"
N = 13


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def canon(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def word_ngrams(text, n):
    w = text.split()
    return {tuple(w[i:i + n]) for i in range(len(w) - n + 1)}


def tok_ngrams(ids, n):
    return {tuple(ids[i:i + n]) for i in range(len(ids) - n + 1)}


def load_ids(path, cap, label):
    rows = []
    with open(path, "rb") as f:
        for ln, line in enumerate(f, 1):
            o = json.loads(line)
            ids = o["ids"]
            assert isinstance(ids, list) and all(isinstance(x, int) for x in ids), f"{label} line {ln}: ids type"
            assert 1 <= len(ids) <= cap, f"{label} line {ln}: ids length out of range"
            rows.append((ids, o.get("text")))
    return rows


def main():
    print("== tokenizer files (sha256 vs DATA_MANIFEST model.tokenizer.files_sha256)")
    ok_tok = True
    for name, exp in TOK_SHA.items():
        got = sha_file(f"{TOKDIR}/{name}")
        print(f"  {name} {got} {'MATCH' if got == exp else 'MISMATCH'}")
        ok_tok &= got == exp

    import transformers
    from transformers import AutoTokenizer
    print("transformers", transformers.__version__)
    tok = AutoTokenizer.from_pretrained(TOKDIR)  # tokenizer only; no model weights
    print("tokenizer class", type(tok).__name__)

    a_sha = sha_file(ANCHOR)
    g_sha = sha_file(GTEST)
    print("== input files")
    print("  anchor_text.jsonl sha256", a_sha, "MATCH manifest" if a_sha == ANCHOR_BYTE_SHA else "MISMATCH manifest")
    print("  general_test.jsonl sha256", g_sha)

    anchors = load_ids(ANCHOR, 128, "anchor")
    windows = load_ids(GTEST, 256, "general_test")
    print("  anchor docs", len(anchors))
    print("  general_test windows", len(windows))
    print("  anchor ids len min/max", min(len(i) for i, _ in anchors), max(len(i) for i, _ in anchors))
    print("  window ids len min/max", min(len(i) for i, _ in windows), max(len(i) for i, _ in windows))

    a_texts = [tok.decode(ids) for ids, _ in anchors]
    w_texts = [tok.decode(ids) for ids, _ in windows]
    a_dec_sha = hashlib.sha256(canon(a_texts).encode("utf-8")).hexdigest()
    print("== anchor decoded-text canonical sha256", a_dec_sha,
          "MATCH manifest" if a_dec_sha == ANCHOR_DECODED_SHA else "MISMATCH manifest")
    print("  anchor docs whose stored 'text' == decode(ids):", sum(t == s for t, (_, s) in zip(a_texts, anchors)), "/", len(anchors))
    print("  windows whose stored 'text' == decode(ids):", sum(t == s for t, (_, s) in zip(w_texts, windows)), "/", len(windows))
    # cross-check: decode with raw `tokenizers` library gives the same strings (count only)
    from tokenizers import Tokenizer
    raw = Tokenizer.from_file(f"{TOKDIR}/tokenizer.json")
    print("  raw-tokenizers decode agreement: anchor",
          sum(raw.decode(ids, skip_special_tokens=False) == t for (ids, _), t in zip(anchors, a_texts)), "/", len(anchors),
          " windows", sum(raw.decode(ids, skip_special_tokens=False) == t for (ids, _), t in zip(windows, w_texts)), "/", len(windows))

    A = set()
    for t in a_texts:
        A |= word_ngrams(t, N)
    G = set()
    for t in w_texts:
        G |= word_ngrams(t, N)
    inter = A & G
    print("== word 13-grams (str.split, per document, union)")
    print("  anchor set size", len(A))
    print("  general_test set size", len(G))
    print("  intersection size (L6 TEST count)", len(inter))

    TA = set()
    for ids, _ in anchors:
        TA |= tok_ngrams(ids, N)
    TG = set()
    for ids, _ in windows:
        TG |= tok_ngrams(ids, N)
    print("== Qwen token 13-grams (report only, no limit)")
    print("  anchor set size", len(TA), " general_test set size", len(TG), " intersection", len(TA & TG))

    res = {"kind": "st10_auditor_l6", "frozen_commit": FROZEN, "general_test_sha256": g_sha, "l6_test_count": len(inter)}
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(json.dumps(res) + "\n")
    print("== wrote", OUT)
    print("  sha256", sha_file(OUT))
    ok = ok_tok and a_sha == ANCHOR_BYTE_SHA and a_dec_sha == ANCHOR_DECODED_SHA and len(anchors) == 512 and len(windows) == 100
    print("checks (tokenizer, anchor hashes, 512 docs, 100 windows):", "OK" if ok else "NOT OK")
    print("RESULT:", "PASS" if ok and len(inter) == 0 else "FAIL")
    return 0 if ok and len(inter) == 0 else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # do not let a traceback print row content
        tb = traceback.extract_tb(e.__traceback__)
        print("ERROR", type(e).__name__, "at line", tb[-1].lineno if tb else "?")
        sys.exit(2)
