"""R6-A/B (round 6, items 1a and 1b): general DEV windows and leakage check L6 (DEV part).
Data Auditor's own script; no Executor code is imported, called or copied. Exceptions -> RESULT: FAIL (r6_guard).
Inputs are the pinned sources only (protocol 2.7, DATA_MANIFEST general_text / anchor_text); the anchor texts and ids
are the ones r6_anchor.py rebuilt from the pinned parquet.

eval_sets.jsonl, TEST rows (protocol section 3, item 1g): for every row only the "split" field is located in the raw
line ('"split": "' searched in the first 80 characters; build_data.py writes json.dumps({"domain", "split", ...}))
and counted. A row whose split is not "dev" is never JSON-parsed, decoded, re-encoded or otherwise used.
Dev rows: JSON-parsed, the parsed split must equal the located one; the first 25 per domain in file order are kept.
Every decode goes through decode_row(), which counts decoded rows by their split; the test count is a measured value.

window (protocol 2.7 as changed in round 6, item 1b): parcae decode (special tokens skipped) -> Qwen encode
(add_special_tokens=False) -> at most the first 256 ids, a shorter sequence at full length -> text = Qwen decode.
L6 (protocol section 3 as changed in round 6, item 1a): distinct 13-grams shared by the 512 anchor texts and the 100
window texts, n-grams inside one document only. Judged unit: word = str.split() (whitespace, case-sensitive), limit 0.
Reported only: Qwen token 13-grams (two variants: re-encoding of both texts, and the ids themselves: anchor truncated
ids / window ids), and the \\w+ casefold unit (only to compare with the Executor's report line).
PASS iff: both source pins match DATA_MANIFEST, 25 dev windows per domain, test rows decoded == 0, no window over
256 ids, and str.split() 13-grams shared == 0.
usage: python -I r6_general.py <eval_sets.jsonl> <parcae_tokenizer.json> <qwen_tok_dir> <data_manifest>
                               <split_manifest> <protocol_md> <anchor.json> <anchor_ids.json> <out_summary.json>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, re
from collections import Counter, defaultdict
from common import sha, canon, load_tok, enc
from r6_guard import run

DOMAINS = ["books", "c4", "fineweb", "wikitext"]
PER_DOMAIN, N = 25, 13
KEY = '"split": "'


def grams(seqs, n):
    out = set()
    for x in seqs:
        for i in range(len(x) - n + 1):
            out.add(tuple(x[i:i + n]))
    return out


def shared_profile(a_seqs, g_seqs):
    counts = [len(grams(a_seqs, n) & grams(g_seqs, n)) for n in range(1, N + 1)]
    longest = max([n for n in range(1, N + 1) if counts[n - 1]] + [0])
    return counts, longest


def main():
    ev, ptok_path, qdir, dm_path, sm_path, proto_path, anchor_path, anchor_ids_path, out_path = sys.argv[1:10]
    ok = True
    dm = json.load(open(dm_path, encoding="utf-8"))
    gt = dm["general_text"]
    MAXTOK = gt["truncate_to_model_tokens"]
    print("DATA_MANIFEST general_text.window_rule:", gt.get("window_rule"), "| truncate_to_model_tokens:", MAXTOK)
    sm = json.load(open(sm_path, encoding="utf-8"))
    print("SPLIT_MANIFEST leakage_checks.L6_general_text:", json.dumps(sm["leakage_checks"]["L6_general_text"], ensure_ascii=False))
    proto = open(proto_path, encoding="utf-8").read()
    print("protocol L6 row:", [l for l in proto.split("\n") if l.startswith("| L6 |")])
    print("protocol 2.7 window sentence present ('每个窗口最多 256 token(取前 256 个),不足则取全长'):",
          "每个窗口最多 256 token(取前 256 个),不足则取全长" in proto)
    print("protocol section 4 n_x sentence present ('n_x 为锚文档 x 实际送入模型的 id 序列长度'):",
          "n_x 为锚文档 x 实际送入模型的 id 序列长度" in proto)

    for label, path, key in (("eval_sets.jsonl", ev, "source_file_sha256"),
                             ("parcae tokenizer.json", ptok_path, "decode_tokenizer_json_sha256")):
        h = sha(open(path, "rb").read())
        ok &= h == gt[key]
        print(f"{label} sha256 {h} | DATA_MANIFEST general_text.{key} {gt[key]} | equal {h == gt[key]}")

    from tokenizers import Tokenizer
    ptok = Tokenizer.from_file(ptok_path)
    qtok = load_tok(qdir)

    rows_by_split, kept = Counter(), defaultdict(list)
    with open(ev, encoding="utf-8") as fh:
        for ln, line in enumerate(fh, 1):
            k = line.find(KEY, 0, 80)
            if k < 0:
                raise ValueError(f"line {ln}: split field not found in the first 80 characters")
            e = line.index('"', k + len(KEY))
            split = line[k + len(KEY):e]
            if split not in ("dev", "test"):
                raise ValueError(f"line {ln}: unexpected split value")
            rows_by_split[split] += 1
            if split != "dev":
                continue                                   # TEST row: only its split field was located and counted
            r = json.loads(line)
            if r["split"] != "dev":
                raise ValueError(f"line {ln}: parsed split differs from the located split")
            if len(kept[r["domain"]]) < PER_DOMAIN:
                kept[r["domain"]].append((ln, r))
    print("eval_sets rows by split (split field only):", dict(sorted(rows_by_split.items())))
    print("dev windows kept per domain:", {d: len(kept[d]) for d in DOMAINS}, "| other domains:", sorted(set(kept) - set(DOMAINS)))
    ok &= sorted(kept) == DOMAINS and all(len(kept[d]) == PER_DOMAIN for d in DOMAINS)

    decoded = Counter()

    def decode_row(row, split):
        decoded[split] += 1
        if split != "dev":
            raise RuntimeError("refusing to decode a non-dev row")
        return ptok.decode(row["tokens"], skip_special_tokens=True)

    win = []
    for d in DOMAINS:
        for ln, r in kept[d]:
            full_text = decode_row(r, r["split"])
            full_ids = enc(qtok, full_text)
            ids = full_ids[:MAXTOK]
            text = qtok.decode(ids)
            win.append({"domain": d, "line": ln, "doc_id": r["doc_id"], "ids": ids, "text": text,
                        "n_full": len(full_ids), "re_ids": enc(qtok, text)})
    print("rows decoded by split (counted inside decode_row):", dict(sorted(decoded.items())),
          "| test rows decoded:", decoded["test"])
    ok &= decoded["test"] == 0 and set(decoded) == {"dev"}

    # item 1b: window lengths
    L = [len(w["ids"]) for w in win]
    print("== item 1b: window lengths (Qwen ids)")
    print("windows:", len(win), "| lengths {len: count}:", dict(sorted(Counter(L).items())))
    print("exactly 256:", sum(x == MAXTOK for x in L), "| shorter than 256:", sum(x < MAXTOK for x in L),
          "| shortest:", min(L), "| longest:", max(L), "| longer than 256:", sum(x > MAXTOK for x in L))
    print("per domain (min, max, number shorter than 256):",
          {d: (min(len(w["ids"]) for w in win if w["domain"] == d), max(len(w["ids"]) for w in win if w["domain"] == d),
               sum(len(w["ids"]) < MAXTOK for w in win if w["domain"] == d)) for d in DOMAINS})
    rule = sum(len(w["ids"]) == min(MAXTOK, w["n_full"]) for w in win)
    print("windows whose length == min(256, full Qwen length of the decoded row) (first 256, else full length):", rule, "of", len(win))
    print("windows where encode(window text) != window ids:", sum(w["re_ids"] != w["ids"] for w in win),
          "| re-encoded window text longer than 256:", sum(len(w["re_ids"]) > MAXTOK for w in win))
    print("windows containing an id >= 151643:", sum(any(i >= 151643 for i in w["ids"]) for w in win))
    ok &= len(win) == 100 and max(L) <= MAXTOK and rule == len(win)
    texts, idl = [w["text"] for w in win], [w["ids"] for w in win]
    h_t, h_i = sha(canon(texts)), sha(canon(idl))
    print("general DEV canonical sha256, list of window texts (domain order books, c4, fineweb, wikitext):", h_t)
    print("general DEV canonical sha256, list of token-id lists (same order):", h_i)

    # item 1a: L6
    anchor = json.load(open(anchor_path, encoding="utf-8"))
    aids = json.load(open(anchor_ids_path, encoding="utf-8"))
    print("== item 1a: L6 (DEV part); anchor texts:", len(anchor), "canonical sha256", sha(canon(anchor)))
    units = {
        "ws  (str.split(), JUDGED)": ([a.split() for a in anchor], [t.split() for t in texts]),
        "tok (encode of both texts)": ([enc(qtok, a) for a in anchor], [enc(qtok, t) for t in texts]),
        "tokid (ids fed: anchor trunc ids / window ids)": (aids["trunc_ids"], idl),
        "w   (\\w+ casefold, comparison only)": ([re.findall(r"\w+", a.casefold()) for a in anchor],
                                                 [re.findall(r"\w+", t.casefold()) for t in texts]),
    }
    summary = {"rows_by_split": dict(rows_by_split), "decoded": dict(decoded), "lengths": dict(Counter(L)),
               "texts_sha": h_t, "ids_sha": h_i, "anchor_sha": sha(canon(anchor)), "units": {}}
    for name, (a_seqs, g_seqs) in units.items():
        counts, longest = shared_profile(a_seqs, g_seqs)
        tag = name.split()[0]
        summary["units"][tag] = {"anchor_units": sum(map(len, a_seqs)), "general_units": sum(map(len, g_seqs)),
                                 "shared": counts, "longest": longest}
        print(f"unit {name}: units anchor {sum(map(len, a_seqs))}, general {sum(map(len, g_seqs))} | shared distinct "
              f"n-grams n=1..13: {counts} | longest shared n <= 13: {longest}")
        if counts[N - 1]:
            g13 = grams(g_seqs, N)
            for gram in sorted(grams(a_seqs, N) & g13)[:5]:
                print("   shared 13-gram:", json.dumps(list(gram), ensure_ascii=False))
    j = summary["units"]["ws"]["shared"][N - 1]
    print(f"L6 (DEV part) shared word 13-grams, word = str.split(): {j}; limit 0 -> {'within limit' if j == 0 else 'OVER LIMIT'}")
    print("report only, no limit: Qwen token 13-grams (encode of texts)", summary["units"]["tok"]["shared"][N - 1],
          "| (ids fed)", summary["units"]["tokid"]["shared"][N - 1], "| \\w+ casefold", summary["units"]["w"]["shared"][N - 1])
    ok &= j == 0
    with open(out_path, "wb") as fh:
        fh.write(canon(dict(summary, windows=[{k: w[k] for k in ("domain", "line", "doc_id", "ids", "text")} for w in win])))
    print("wrote", out_path)
    return bool(ok)


if __name__ == "__main__":
    run(main)
