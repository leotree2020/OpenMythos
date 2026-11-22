"""R7 final comparison: the auditor's own rebuilt files (audit_r7) against the Executor's generated files (scratchpad r7)
and against the numbers the Executor recorded in reports/round7/. This is the only round-7 auditor script that reads
Executor files, and it reads them as data only (no Executor code is imported, called or copied).
Exceptions -> RESULT: FAIL (r6_guard). PASS iff every compared item is identical.
usage: python -I r7_compare.py <my_dir audit_r7> <executor_dir r7> <repo_reports_round7_dir> <my_stdout_dir>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, re
from common import sha, canon
from r6_guard import run


def main():
    mine, ex, rep, so = sys.argv[1:5]
    ok = True
    rb = lambda p: open(p, "rb").read()

    def same(label, a, b, sa="", sb=""):
        nonlocal ok
        ok &= a == b
        print("%-70s %s | mine %s | Executor %s" % (label, "IDENTICAL" if a == b else "DIFFERENT", sa, sb))

    m, e = rb(os.path.join(mine, "facts.json")), rb(os.path.join(ex, "facts.json"))
    same("facts.json bytes", m, e, sha(m), sha(e))
    ma, ea = json.loads(rb(os.path.join(mine, "anchor.json"))), json.loads(rb(os.path.join(ex, "anchor.json")))
    ea_texts = ea["texts"] if isinstance(ea, dict) else ea
    print("Executor anchor.json top-level type:", type(ea).__name__, "| keys:", sorted(ea)[:10] if isinstance(ea, dict) else "-")
    same("anchor texts (canonical list of 512)", canon(ma), canon(ea_texts), sha(canon(ma)), sha(canon(ea_texts)))
    for run_dir in ("run1", "run2", "run_py311", "run_py312"):
        for fn in ("train_S.jsonl", "candidates.json"):
            for g in ("gen1", "gen2", "gen3"):
                a, b = rb(os.path.join(mine, run_dir, fn)), rb(os.path.join(ex, g, fn))
                same("%s/%s vs Executor %s/%s bytes" % (run_dir, fn, g, fn), a, b, sha(a), sha(b))

    print("== numbers recorded by the Executor (reports/round7) vs my stdout")
    t1g = open(os.path.join(rep, "t1g_gen_s_cands.txt"), encoding="utf-8").read()
    my04 = open(os.path.join(so, "04_r7_s_cands.txt"), encoding="utf-8").read()
    ea_ = re.findall(r"S derangement attempts per cell: (\{.*\})", t1g)
    ma_ = re.findall(r"S derangement attempts per cell: (\{.*\})", my04)
    same("S derangement attempts per cell (t1g, 2 runs, vs mine)", [json.loads(ma_[0])] * len(ea_), [json.loads(x) for x in ea_],
         ma_[0], ea_)
    ef = re.findall(r"first S row: (.+?) \| first candidates: (\[.*\])", t1g)
    mf = re.search(r"first S row: (\{.*?\}) \| first candidates: \('([^']+)', (\[.*\])\)", my04)
    my_first = (json.loads(mf.group(1).replace("'", '"'))["text"], json.loads(mf.group(3).replace("'", '"')))
    same("first S row text and first candidate list", [my_first] * len(ef), [(a, json.loads(b)) for a, b in ef], my_first, ef)
    t0f = open(os.path.join(rep, "t0_facts_regen.txt"), encoding="utf-8").read()
    my03 = open(os.path.join(so, "03_r4_regen_facts.txt"), encoding="utf-8").read()
    elog = json.loads(re.search(r"cell log: (\[.*\])", t0f).group(1))
    mlog = [{"cell": c, "entity_draws": int(a), "target_pair": [int(x), int(y)], "answer_draws": int(d)} for c, a, x, y, d in
            re.findall(r"cell (\S+): entity_draws (\d+), survey_draws \d+, target \(K_st,K_qa\) \((\d+), (\d+)\).*answer_draws (\d+)", my03)]
    same("per-cell draws and target (K_st, K_qa) (t0_facts_regen vs my 03)", mlog, elog)
    t1f = open(os.path.join(rep, "t1f_think_tokens.txt"), encoding="utf-8").read()
    my09 = open(os.path.join(so, "09_r7_text_items.txt"), encoding="utf-8").read()
    e_think = re.findall(r"'(<think>|</think>)' id (\d+) \| in all_special_ids: (\w+) \| added_tokens_decoder special: (\w+)", t1f)
    m_think = re.findall(r"\[info\] (<think>|</think>)\s+tokenizer.json added_tokens id (\d+) special \w+ \| tokenizer_config special (\w+)"
                         r" \| convert_tokens_to_ids \d+ \| in all_special_ids (\w+)", my09)
    same("<think> / </think>: id, in all_special_ids, special flag", [(t, i, s, c) for t, i, c, s in m_think], e_think)
    e_dec = re.search(r"decode skip_special_tokens=True : (.+)", t1f).group(1).strip()
    m_dec = re.search(r"-> decode\(skip_special_tokens=True\) = (.+)", my09).group(1).strip()
    same("decode(skip_special_tokens=True) of the same synthetic ids", m_dec, e_dec)
    return bool(ok)


if __name__ == "__main__":
    run(main)
