"""R5-B: the 28-token scoring sequence pinned in reports/round3/verify_scoring.py, rebuilt from the protocol text
(section 0 rows "问答输入" and "候选打分输入", section 5 s_QA). Data Auditor's own script; the Executor's code is not
imported or executed: PINNED is read from the file text with ast.literal_eval (a literal only), and the round-3 record
is read from t7_verify_scoring.txt (working tree and the git object of the round-3 commit).
chat(q)  = chat template of the pinned tokenizer, one user turn, add_generation_prompt=True, enable_thinking=False,
           no system prompt
sequence = chat(q) + "The answer is" + " " + c, c = a_f; scored = tokens of " " + c; start = number of context tokens
fact E1P-L-capital-nat-01 from MY regenerated facts; question = first capital DEV template of SPLIT_MANIFEST,
cross-checked with the protocol 2.4 table. DEV only.
usage: python -I r5_pinned.py <tokenizer_dir> <my_facts_json> <split_manifest> <protocol_md> <verify_scoring.py>
                              <t7_verify_scoring.txt> <repo_root> <round3_commit>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ast, json, re, subprocess
from common import load_tok, enc

tokdir, facts_p, sm_p, proto_p, vs_p, t7_p, repo, r3 = sys.argv[1:9]
tok = load_tok(tokdir)
facts = json.load(open(facts_p, encoding="utf-8"))
sm = json.load(open(sm_p, encoding="utf-8"))
f = next(x for x in facts if x["fact_id"] == "E1P-L-capital-nat-01")
print("my fact E1P-L-capital-nat-01:", json.dumps(f))
dev_cap = [t for t in sm["templates"] if t["set"] == "DEV" and t["relation"] == "capital"]
print("capital DEV templates in SPLIT_MANIFEST order:", [(t["template_id"], t["text"]) for t in dev_cap])
row = re.search(r"^\| capital \| DEV \| (.+) \|$", open(proto_p, encoding="utf-8").read(), re.M).group(1)
print("protocol 2.4 capital DEV row:", json.dumps(row), "| first listed == manifest first:", row.split(" / ")[0] == dev_cap[0]["text"])
q = dev_cap[0]["text"].replace("{E}", f["entity"])
print("question:", json.dumps(q))
PFX = "The answer is"


def build(q, c, **kw):
    ctx = tok.apply_chat_template([{"role": "user", "content": q}], tokenize=False, add_generation_prompt=True, **kw) + PFX
    full = enc(tok, ctx + " " + c)
    ctx_ids = enc(tok, ctx)
    assert full[:len(ctx_ids)] == ctx_ids
    return ctx, full, len(ctx_ids)


ctx, ids, start = build(q, f["answer"], enable_thinking=False)
print("rendered text (enable_thinking=False):", json.dumps(ctx + " " + f["answer"]))
print("my ids (%d):" % len(ids), ids)
print("my tokens:", tok.convert_ids_to_tokens(ids))
print("my scored start:", start, "| scored ids:", ids[start:], "| == encode(' '+a_f):", ids[start:] == enc(tok, " " + f["answer"]))
# piecewise construction (no cross-boundary merge)
chat_ids = enc(tok, ctx[:-len(PFX)])
piece = chat_ids + enc(tok, PFX) + enc(tok, " " + f["answer"])
print("piecewise encode(chat(q)) + encode('The answer is') + encode(' '+a_f) == my ids:", piece == ids)
direct = tok.apply_chat_template([{"role": "user", "content": q}], tokenize=True, add_generation_prompt=True, enable_thinking=False)
direct = list(direct["input_ids"] if hasattr(direct, "keys") else direct)
print("apply_chat_template(tokenize=True) ids == my chat(q) ids:", direct == chat_ids)

# PINNED from the Executor file (literal only)
src = open(vs_p, encoding="utf-8").read()
m = re.search(r"^PINNED = (\{.*?^\})", src, re.M | re.S)
pinned = ast.literal_eval(m.group(1))
print("PINNED (verify_scoring.py, read as a literal):", json.dumps(pinned))
print("PINNED input_ids count:", len(pinned["input_ids"]), "| start:", pinned["start"])
print("my ids == PINNED input_ids:", ids == pinned["input_ids"], "| my start == PINNED start:", start == pinned["start"],
      "| fact/entity/answer/question equal:", (f["fact_id"], f["entity"], f["answer"], q) == (pinned["fact_id"], pinned["entity"], pinned["answer"], pinned["question"]))

# round-3 record: t7 lines 42 and 44, working tree and the round-3 commit's git object
wt = open(t7_p, encoding="utf-8").read().split("\n")
rel = os.path.relpath(os.path.abspath(t7_p), repo)
g3 = subprocess.check_output(["git", "-C", repo, "show", f"{r3}:{rel}"]).decode("utf-8").split("\n")
print("t7 path", rel, "| working tree == round-3 commit object", r3[:8], ":", wt == g3)
print("t7 last commit touching it:", subprocess.check_output(["git", "-C", repo, "log", "-1", "--format=%H %cI %s", "--", rel]).decode().strip())
for name, lines in (("working tree", wt), (f"commit {r3[:8]}", g3)):
    l42, l44 = lines[41], lines[43]
    m42 = re.fullmatch(r"input_ids \((\d+)\): (\[.*\])", l42)
    m44 = re.match(r"scored slice start (\d+), scored ids (\[.*?\])", l44)
    rec_ids, rec_start = json.loads(m42.group(2)), int(m44.group(1))
    print(f"t7 ({name}) line 42: {l42}")
    print(f"t7 ({name}) line 44: {l44}")
    print(f"  recorded count {m42.group(1)} ids == mine: {rec_ids == ids} | recorded start {rec_start} == mine: {rec_start == start}"
          f" | recorded scored ids == mine: {json.loads(m44.group(2)) == ids[start:]} | == PINNED: {rec_ids == pinned['input_ids']}")

# enable_thinking=True and the template default
for label, kw in (("enable_thinking=True", {"enable_thinking": True}), ("enable_thinking not passed (template default)", {})):
    c2, ids2, st2 = build(q, f["answer"], **kw)
    first = next((i for i, (a, b) in enumerate(zip(ids2, ids)) if a != b), min(len(ids2), len(ids)))
    print(f"{label}: ids ({len(ids2)}) {ids2} | start {st2} | equal to PINNED: {ids2 == pinned['input_ids']} | first difference at position {first}"
          f" | scored ids {ids2[st2:]}")
