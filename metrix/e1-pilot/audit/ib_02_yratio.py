"""IB-2 (implementation stage B, task 2): Y / F token ratio (protocol 2.6: "Y 语料的 token 总数与 F 语料之比必须在
[0.80, 1.25]"), counted two ways:
  with    : every sequence = encode(text, add_special_tokens=False) + one <|endoftext|> (id 151643, protocol section 0
            "训练输入": statement text followed by endoftext);
  without : encode(text, add_special_tokens=False) only.
Corpora: my own regeneration (ia_05_derived.py output train_F.json / train_Y.json) and, separately, the texts of the
Executor's data_b train_F.jsonl / train_Y.jsonl (counted by me).  The interval is read from the freeze-commit
SEARCH_SPACE.json and checked against the protocol text.  Compared with reports/impl_b/t3_generate_leakage.txt
lines 8-10.
Data Auditor's own script; no Executor code imported, called or copied.  Loads the tokenizer only.
usage: python -I ib_02_yratio.py <repo_root> <qwen_tok_dir> <my_out_dir> <executor_dir>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, re
from ia_common import frozen_json, frozen_protocol, read_jsonl, load_qwen, enc, run

EOT = 151643
T3 = "metrix/e1-pilot/reports/impl_b/t3_generate_leakage.txt"


def main():
    repo, qdir, mine, exdir = sys.argv[1:5]
    ok = True
    ss = frozen_json(repo, "SEARCH_SPACE.json")
    m = re.search(r"Y tokens / F tokens must lie in \[([0-9.]+), ([0-9.]+)\]", ss["training_contract"]["primary_training_token_budget"])
    lo, hi = float(m.group(1)), float(m.group(2))
    in_protocol = "Y 语料的 token 总数与 F 语料之比必须在 [0.80, 1.25]" in frozen_protocol(repo)
    print(f"interval from the freeze-commit SEARCH_SPACE: [{lo}, {hi}] | protocol 2.6 sentence with [0.80, 1.25] present: {in_protocol}")
    ok &= (lo, hi) == (0.80, 1.25) and in_protocol
    tok = load_qwen(qdir)
    eot = tok.convert_tokens_to_ids("<|endoftext|>")
    print(f"tokenizer: <|endoftext|> id {eot} | == {EOT}: {eot == EOT}")
    ok &= eot == EOT
    sources = {
        "auditor regeneration": ([r["text"] for r in json.load(open(os.path.join(mine, "train_F.json"), encoding="utf-8"))],
                                 [r["text"] for r in json.load(open(os.path.join(mine, "train_Y.json"), encoding="utf-8"))]),
        "Executor data_b texts": ([r["text"] for r in read_jsonl(os.path.join(exdir, "train_F.jsonl"))],
                                  [r["text"] for r in read_jsonl(os.path.join(exdir, "train_Y.jsonl"))]),
    }
    res = {}
    for name, (F, Y) in sources.items():
        nf, ny = sum(len(enc(tok, t)) for t in F), sum(len(enc(tok, t)) for t in Y)
        w = (nf + len(F), ny + len(Y), (ny + len(Y)) / (nf + len(F)))
        wo = (nf, ny, ny / nf)
        res[name] = (w, wo)
        print(f"== {name}: sequences F {len(F)} | Y {len(Y)}")
        print(f"  with one <|endoftext|> per sequence: F {w[0]} | Y {w[1]} | ratio {w[2]:.6f} | in [{lo}, {hi}]: {lo <= w[2] <= hi}")
        print(f"  without <|endoftext|>:               F {wo[0]} | Y {wo[1]} | ratio {wo[2]:.6f} | in [{lo}, {hi}]: {lo <= wo[2] <= hi}")
        ok &= len(F) == 120 and len(Y) == 240 and lo <= w[2] <= hi and lo <= wo[2] <= hi
    same_src = res["auditor regeneration"] == res["Executor data_b texts"]
    print("auditor regeneration and data_b texts give the same counts:", same_src)
    ok &= same_src
    t3 = open(os.path.join(repo, T3), encoding="utf-8").read().split("\n")
    print("Executor t3 lines 8-10 (as recorded):")
    for i in (7, 8, 9):
        print(f"  t3:{i + 1}: {t3[i]}")
    m1 = re.fullmatch(r"Y / F token ratio: F (\d+), Y (\d+), ratio ([0-9.]+)", t3[7])
    m2 = re.fullmatch(r"Y / F token ratio without <\|endoftext\|> \(report only\): F (\d+), Y (\d+), ratio ([0-9.]+)", t3[8])
    m3 = re.fullmatch(r"both ratios within \[([0-9.]+), ([0-9.]+)\]: with (\w+), without (\w+)", t3[9])
    (w, wo) = res["auditor regeneration"]
    c1 = m1 is not None and (int(m1.group(1)), int(m1.group(2)), m1.group(3)) == (w[0], w[1], f"{w[2]:.4f}")
    c2 = m2 is not None and (int(m2.group(1)), int(m2.group(2)), m2.group(3)) == (wo[0], wo[1], f"{wo[2]:.4f}")
    c3 = m3 is not None and (float(m3.group(1)), float(m3.group(2)), m3.group(3), m3.group(4)) == (lo, hi, "True", "True")
    print(f"t3 line 8 (with) == mine (F, Y, ratio to 4 places): {c1} | line 9 (without) == mine: {c2} | line 10 interval and both True: {c3}")
    ok &= c1 and c2 and c3
    print(f"protocol 2.6 authoring numbers F 1,889 / Y 2,260 / 1.196 == the 'with' counting: {(w[0], w[1], round(w[2], 3)) == (1889, 2260, 1.196)}")
    return bool(ok)


run(main)
