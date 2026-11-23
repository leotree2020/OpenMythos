"""IA-6: general DEV windows (protocol 2.7; DATA_MANIFEST general_text at the freeze commit).
TEST rule (protocol section 3; Implementation Task Order section 3 item 3): eval_sets.jsonl is hashed as a whole file;
it is then read in BINARY mode line by line; for every line only the split value is located in the line prefix
(b'"split": "' within the first 80 bytes) and counted.  A line whose split value is not b"dev" is never
UTF-8-decoded, JSON-parsed or token-decoded, and nothing else about it is computed or printed.
Dev lines: JSON-parsed (the parsed split must equal the located one); per domain (books, c4, fineweb, wikitext) the
first 25 dev lines in file order; tokens decoded with the parcae tokenizer.json (tokenizers library,
skip_special_tokens=True); encoded with the pinned Qwen tokenizer (add_special_tokens=False); first <= 256 ids;
window text (used by L6) = Qwen decode of those ids (default arguments).
Writes <out_dir>/general.json: [{"domain", "line", "dom_index", "doc_id" (source field), "ids", "full_len", "text"}] in domain order
(books, c4, fineweb, wikitext), file order inside a domain.
Data Auditor's own script; no Executor code imported, called or copied.  Loads tokenizers only.
usage: python -I ia_06_general.py <repo_root> <parcae_tokenizer.json> <qwen_tok_dir> <out_dir>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json
from collections import Counter, defaultdict
from ia_common import DOMAINS, sha, canon, file_sha, frozen_json, load_qwen, enc, run

KEY = b'"split": "'


def main():
    repo, ptok_path, qdir, out_dir = sys.argv[1:5]
    ok = True
    gt = frozen_json(repo, "DATA_MANIFEST.json")["general_text"]
    for k in ("source_file", "source_file_sha256", "decode_with", "decode_tokenizer_json_sha256", "dev", "truncate_to_model_tokens", "window_rule"):
        print(f"freeze-commit general_text.{k}: {gt[k]}")
    MAXW = gt["truncate_to_model_tokens"]
    ok &= MAXW == 256 and "first 25 windows per domain" in gt["dev"]
    ev = os.path.join(repo, gt["source_file"])
    for label, path, key in (("eval_sets.jsonl (whole file)", ev, "source_file_sha256"),
                             ("parcae tokenizer.json", ptok_path, "decode_tokenizer_json_sha256")):
        h = file_sha(path)
        print(f"{label} sha256 {h} | manifest {gt[key]} | MATCH {h == gt[key]}")
        ok &= h == gt[key]
    from tokenizers import Tokenizer
    ptok = Tokenizer.from_file(ptok_path)
    qtok = load_qwen(qdir)
    counts, kept = Counter(), defaultdict(list)
    with open(ev, "rb") as fh:
        for ln, line in enumerate(fh, 1):
            k = line.find(KEY, 0, 80)
            if k < 0:
                raise ValueError(f"line {ln}: split field not in the first 80 bytes")
            e = line.index(b'"', k + len(KEY))
            split = line[k + len(KEY):e]
            counts[split] += 1
            if split != b"dev":
                continue                       # not dev: only the split bytes were located and counted
            r = json.loads(line)
            if r["split"] != "dev":
                raise ValueError(f"line {ln}: parsed split differs from the located one")
            if len(kept[r["domain"]]) < 25:
                kept[r["domain"]].append((ln, r))
    print("eval_sets lines by located split value (counts only):", {s.decode("ascii", "replace"): n for s, n in sorted(counts.items())})
    print("non-dev lines: only located and counted (the loop continues before any parse or decode)")
    print("dev lines kept per domain:", {d: len(kept[d]) for d in DOMAINS}, "| domains outside the protocol list:", sorted(set(kept) - set(DOMAINS)))
    ok &= sorted(kept) == DOMAINS and all(len(kept[d]) == 25 for d in DOMAINS)
    out = []
    for d in DOMAINS:
        for j, (ln, r) in enumerate(kept[d]):
            full = enc(qtok, ptok.decode(r["tokens"], skip_special_tokens=True))
            ids = full[:MAXW]
            out.append({"domain": d, "line": ln, "dom_index": j, "doc_id": r.get("doc_id"), "ids": ids, "full_len": len(full),
                        "text": qtok.decode(ids)})
    nw = [len(w["ids"]) for w in out]
    print("windows", len(out), "| n_w == 256:", sum(n == MAXW for n in nw), "| n_w < 256:", [(w["domain"], w["dom_index"], len(w["ids"])) for w in out if len(w["ids"]) < MAXW])
    ok &= len(out) == 100 and all(len(w["ids"]) == min(MAXW, w["full_len"]) for w in out)
    special = set(qtok.all_special_ids)
    print("windows containing a special-token id:", [(w["domain"], w["dom_index"]) for w in out if special & set(w["ids"])])
    print("file lines of the kept windows, first per domain:", {d: kept[d][0][0] for d in DOMAINS}, "| last per domain:", {d: kept[d][-1][0] for d in DOMAINS})
    print(f"AUDIT_VALUE general_dev_ids_canonical_sha256 {sha(canon([w['ids'] for w in out]))}")
    print(f"AUDIT_VALUE general_dev_texts_canonical_sha256 {sha(canon([w['text'] for w in out]))}")
    os.makedirs(out_dir, exist_ok=True)
    open(os.path.join(out_dir, "general.json"), "wb").write(canon(out))
    print("wrote", os.path.join(out_dir, "general.json"))
    return bool(ok)


run(main)
