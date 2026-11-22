"""R7-1e (general text part) and L6 (DEV part): general DEV windows rebuilt from the pinned sources, their n_w, and the
word 13-gram check against the anchor documents rebuilt by r6_anchor.py.
Data Auditor's own script; no Executor code is imported, called or copied. Exceptions -> RESULT: FAIL (r6_guard).

TEST rows of eval_sets.jsonl (protocol section 3, definition of "reading TEST data"): the file is opened in BINARY mode;
for every line only the bytes of the split field are located (b'"split": "' searched in the first 80 bytes) and the
line is counted by that value. A line whose split is not b"dev" is never UTF-8-decoded, JSON-parsed, token-decoded or
used in any computation. Dev lines are JSON-parsed; the parsed split must equal the located one.

window (protocol 2.7): parcae decode (special tokens skipped) -> Qwen encode (add_special_tokens=False) -> the first
at most 256 ids; n_w (protocol section 5 as changed in round 7, item 1e) = number of those ids (no decode / re-encode).
Also reported: the length one would get by decoding the ids and encoding again, to show whether the 1e wording matters
on these data.
L6 (DEV part): the count rule written for the TEST part in round 7 (item 1b) is applied to DEV as well: 13-grams are
taken inside each anchor document and inside each window; the set of the 512 anchor documents is intersected with the
set of all windows; the number of elements is counted. Judged unit: word = str.split(); reported only: Qwen token ids.
PASS iff: both source pins equal DATA_MANIFEST; 25 dev windows per domain; 0 test lines decoded; every n_w equals
min(256, full length); no n_w > 256; shared word 13-grams == 0; anchor n_x as in r6_anchor (<= 128, full length if
shorter); the round-7 sentences on n_w and on the anchor length are present in the protocol and the manifest.
usage: python -I r7_general_dev.py <eval_sets.jsonl> <parcae_tokenizer.json> <qwen_tok_dir> <DATA_MANIFEST.json>
                                   <protocol.md> <my anchor.json> <my anchor_ids.json>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json
from collections import Counter, defaultdict
from common import sha, canon, load_tok, enc
from r6_guard import run

DOMAINS = ["books", "c4", "fineweb", "wikitext"]
PER_DOMAIN, N = 25, 13
KEY = b'"split": "'


def grams(seqs, n):
    out = set()
    for x in seqs:
        for i in range(len(x) - n + 1):
            out.add(tuple(x[i:i + n]))
    return out


def main():
    ev, ptok_path, qdir, dm_path, proto_path, anchor_path, anchor_ids_path = sys.argv[1:8]
    ok = True
    dm = json.load(open(dm_path, encoding="utf-8"))
    gt, at = dm["general_text"], dm["anchor_text"]
    MAXW, MAXA = gt["truncate_to_model_tokens"], at["truncate_to_model_tokens"]
    proto = open(proto_path, encoding="utf-8").read()

    print("== protocol / manifest text of item 1e")
    sentences = [
        "n_w 为窗口实际送入模型的 id 序列长度:送入模型的是第 2.7 节用本协议分词器切分后截断得到的原始 id(最多 256 个),不解码再编码",
        "每个窗口最多 256 token(取前 256 个),不足则取全长",
        "每篇最多 128 token(取前 128 个),不足则取全长",
        "512 篇、每篇最多 128 token、解码后的文本",
    ]
    for s in sentences:
        c = proto.count(s)
        print("  protocol contains %r: %d time(s)" % (s, c))
        ok &= c >= 1
    print("  DATA_MANIFEST general_text.window_rule:", gt.get("window_rule"))
    print("  DATA_MANIFEST anchor_text.document_rule:", at.get("document_rule"), "| truncate_to_model_tokens", MAXA)
    ok &= "not decoded and re-encoded" in gt.get("window_rule", "") and "at most 128 tokens" in at.get("document_rule", "")
    body = proto.split("\n## 14.")[0]
    for old in ("各截到 128", "截到 128 token", "窗口的 token 数", "不得共享任何 13-gram"):
        print("  old wording %r outside section 14: %d" % (old, body.count(old)))
        ok &= body.count(old) == 0

    for label, path, key in (("eval_sets.jsonl", ev, "source_file_sha256"),
                             ("parcae tokenizer.json", ptok_path, "decode_tokenizer_json_sha256")):
        h = sha(open(path, "rb").read())
        ok &= h == gt[key]
        print(f"{label} sha256 {h} | DATA_MANIFEST general_text.{key} equal {h == gt[key]}")

    from tokenizers import Tokenizer
    ptok = Tokenizer.from_file(ptok_path)
    qtok = load_tok(qdir)

    by_split, kept = Counter(), defaultdict(list)
    with open(ev, "rb") as fh:
        for ln, line in enumerate(fh, 1):
            k = line.find(KEY, 0, 80)
            if k < 0:
                raise ValueError(f"line {ln}: split field not found in the first 80 bytes")
            e = line.index(b'"', k + len(KEY))
            split = line[k + len(KEY):e]
            if split not in (b"dev", b"test"):
                raise ValueError(f"line {ln}: unexpected split value")
            by_split[split.decode("ascii")] += 1
            if split != b"dev":
                continue                      # TEST line: only its split bytes were located and counted
            r = json.loads(line)
            if r["split"] != "dev":
                raise ValueError(f"line {ln}: parsed split differs from the located split")
            if len(kept[r["domain"]]) < PER_DOMAIN:
                kept[r["domain"]].append((ln, r))
    print("eval_sets lines by split (split bytes only):", dict(sorted(by_split.items())))
    print("dev windows kept per domain:", {d: len(kept[d]) for d in DOMAINS}, "| other domains:", sorted(set(kept) - set(DOMAINS)))
    ok &= sorted(kept) == DOMAINS and all(len(kept[d]) == PER_DOMAIN for d in DOMAINS)

    decoded = Counter()
    win = []
    for d in DOMAINS:
        for ln, r in kept[d]:
            assert r["split"] == "dev"
            decoded[r["split"]] += 1
            full = enc(qtok, ptok.decode(r["tokens"], skip_special_tokens=True))
            ids = full[:MAXW]
            re_ids = enc(qtok, qtok.decode(ids))
            win.append({"domain": d, "ids": ids, "n_full": len(full), "re_len": len(re_ids), "re_same": re_ids == ids,
                        "text": qtok.decode(ids)})
    print("rows token-decoded by split:", dict(decoded), "| test rows decoded: 0 (no code path decodes a non-dev line)")
    ok &= set(decoded) == {"dev"}

    print("== item 1e: n_w of the 100 general DEV windows (= len of the truncated Qwen ids fed to the model)")
    nw = [len(w["ids"]) for w in win]
    print("n_w {len: count}:", dict(sorted(Counter(nw).items())))
    print("n_w == 256:", sum(x == MAXW for x in nw), "| n_w < 256:", sum(x < MAXW for x in nw), "| min", min(nw),
          "| max", max(nw), "| > 256:", sum(x > MAXW for x in nw))
    rule = sum(len(w["ids"]) == min(MAXW, w["n_full"]) for w in win)
    print("windows with n_w == min(256, full length):", rule, "of", len(win))
    print("windows where decode-then-re-encode would change the ids:", sum(not w["re_same"] for w in win),
          "| change the length:", sum(w["re_len"] != len(w["ids"]) for w in win))
    ok &= len(win) == 100 and max(nw) <= MAXW and rule == 100

    print("== item 1e: anchor documents n_x (from r6_anchor.py output)")
    anchor = json.load(open(anchor_path, encoding="utf-8"))
    aids = json.load(open(anchor_ids_path, encoding="utf-8"))
    nx = [len(x) for x in aids["trunc_ids"]]
    short = [(i, n, f) for i, (n, f) in enumerate(zip(nx, aids["full_len"])) if n < MAXA]
    print("anchor texts", len(anchor), "canonical sha256", sha(canon(anchor)))
    print("n_x {len: count}:", dict(sorted(Counter(nx).items())), "| documents shorter than 128 (index, n_x, full):", short)
    print("documents with n_x == min(128, full length):", sum(n == min(MAXA, f) for n, f in zip(nx, aids["full_len"])), "of", len(nx))
    ok &= len(nx) == 512 and all(n == min(MAXA, f) for n, f in zip(nx, aids["full_len"]))

    print("== L6 (DEV part), count rule of round-7 item 1b applied to DEV")
    texts = [w["text"] for w in win]
    a_w, g_w = grams([a.split() for a in anchor], N), grams([t.split() for t in texts], N)
    a_t, g_t = grams(aids["trunc_ids"], N), grams([w["ids"] for w in win], N)
    print("word 13-grams (str.split()): anchor distinct", len(a_w), "| windows distinct", len(g_w),
          "| shared distinct", len(a_w & g_w), "-> limit 0:", "within" if not (a_w & g_w) else "OVER")
    print("report only: Qwen token-id 13-grams (ids fed): anchor", len(a_t), "| windows", len(g_t), "| shared", len(a_t & g_t))
    ok &= len(a_w & g_w) == 0
    print("general DEV canonical sha256: texts", sha(canon(texts)), "| id lists", sha(canon([w["ids"] for w in win])))
    return bool(ok)


if __name__ == "__main__":
    run(main)
