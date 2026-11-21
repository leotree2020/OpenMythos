"""R5-A follow-up: why 'parcae_tokens equal to the dev rows' tokens' was False in r5_l6.py.
Reads my general DEV file (r5_l6.py output), the dev rows of eval_sets.jsonl (rows whose split != 'dev' are skipped
right after reading 'split'), and the Executor's general_dev file (comparison only). Prints the type / length /
relation of the Executor's 'parcae_tokens' field to the source rows' token lists; no content is printed.
usage: python -I r5_cmp_general.py <eval_sets.jsonl> <my_general_json> <executor_general_dev_json>"""
import json, sys
from collections import Counter

ev, mine_p, ex_p = sys.argv[1:4]
mine = json.load(open(mine_p, encoding="utf-8"))
ex = json.load(open(ex_p, encoding="utf-8"))
rows = {}
with open(ev, encoding="utf-8") as fh:
    for ln, line in enumerate(fh, 1):
        r = json.loads(line)
        if r["split"] != "dev":
            continue
        rows[ln] = r
src = [rows[w["line"]]["tokens"] for w in mine]
pt = [e["parcae_tokens"] for e in ex]
print("type of parcae_tokens values:", Counter(type(x).__name__ for x in pt))
if all(isinstance(x, list) for x in pt):
    print("lengths of parcae_tokens:", Counter(len(x) for x in pt), "| source rows' token-list lengths:", Counter(len(x) for x in src))
    print("parcae_tokens == source tokens:", sum(a == b for a, b in zip(pt, src)),
          "| == source tokens[:256]:", sum(a == b[:256] for a, b in zip(pt, src)),
          "| is a prefix of the source tokens:", sum(a == b[:len(a)] for a, b in zip(pt, src)))
else:
    print("parcae_tokens values (as numbers) vs len(source tokens):", Counter((x, len(b)) for x, b in zip(pt, src)))
print("other keys equal: doc_id", [e["doc_id"] for e in ex] == [w["doc_id"] for w in mine],
      "| domain", [e["domain"] for e in ex] == [w["domain"] for w in mine],
      "| ids", [e["ids"] for e in ex] == [w["ids"] for w in mine],
      "| text", [e["text"] for e in ex] == [w["text"] for w in mine])
