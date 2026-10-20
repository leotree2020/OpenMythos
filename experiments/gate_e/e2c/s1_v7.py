#!/usr/bin/env python3
"""
V7 (E2C_PREREG_DRAFT 6, 7.1, Appendices D and F): re-run the registered
statistics scripts in the implementation environment.

    1  take exact_excl.py, region_table.py and certify.py verbatim from the
       approved preregistration's code blocks; each block's sha256 must equal
       the registered one
    2  run them (python3 -I, in stage1/v7/); each output must equal the
       registered verbatim output exactly
    3  the rejection regions printed by region_table.py must equal the frozen
       table of 7.1, parsed from the preregistration text, for N = 20, 24, 30
Nothing in the preregistration is changed. Exit 0 if all pass, 3 otherwise (F3).
"""

import hashlib
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from s1_budget import STAGE1, Ledger  # noqa: E402

PREREG = os.path.join(HERE, "E2C_PREREG_DRAFT.md")
OUT = os.path.join(STAGE1, "v7")
SCRIPTS = {"exact_excl.py": "d0355a7aebdffb3c52ea91d6a174dc2799381f8575e3d3f91aaa82d1b903f4f1",
           "region_table.py": "7d3e0a1522fba6032fa0ba8cbe036ea01ed5395cc9082ae7cd34d7e93391df8f",
           "certify.py": "d8d5135f88e1b0d770f078874c9d35fcf49701d02ca5043ad26dfd27c7e7abd4"}
RUNS = {"exact_excl.py": ["exact_excl.py"], "region_table.py": ["region_table.py", "exact_excl.py"], "certify.py": ["certify.py"]}


def blocks(text):
    """Code blocks in order: (language, content)."""
    return [(m.group(1), m.group(2)) for m in re.finditer(r"```(\w*)\n(.*?)```", text, re.S)]


def table_from_prereg(text):
    out = {}
    for n in (20, 24, 30):
        line = next(ln for ln in text.splitlines() if ln.strip().startswith(f"- N = {n}：b = 0"))
        tab = {}
        for part in line.split("：", 1)[1].split("；"):
            m = re.match(r"\s*b = (\d+)(?:–(\d+))?：c ≥ (\d+)", part)
            if m:
                lo, hi = int(m.group(1)), int(m.group(2) or m.group(1))
                for b in range(lo, hi + 1):
                    tab[b] = int(m.group(3))
        out[n] = tab
    return out


def table_from_output(out):
    res = {}
    for line in out.splitlines():
        m = re.match(r"N=(\d+):", line)
        if m:
            res[int(m.group(1))] = {int(b): int(c) for b, c in re.findall(r"b=(\d+): c>=(\d+)", line)}
    return res


def main():
    os.makedirs(OUT, exist_ok=True)
    text = open(PREREG).read()
    bl = blocks(text)
    found, expected = {}, {}
    for i, (lang, content) in enumerate(bl):
        if lang != "python":
            continue
        h = hashlib.sha256(content.encode()).hexdigest()
        for name, want in SCRIPTS.items():
            if h == want:
                found[name] = content
                # the registered output is the next plain block after this one
                nxt = next((c for lg, c in bl[i + 1:] if lg == ""), None)
                expected[name] = nxt
    res = {"prereg_sha256": hashlib.sha256(text.encode()).hexdigest(),
           "scripts_found_with_registered_sha256": {n: n in found for n in SCRIPTS}}
    led = Ledger()
    runs = {}
    with led.job("v7"):
        for name in SCRIPTS:
            if name in found:
                open(os.path.join(OUT, name), "w").write(found[name])
        for name, argv in RUNS.items():
            if not all(a in found for a in argv):
                continue
            p = subprocess.run([sys.executable, "-I"] + argv, cwd=OUT, capture_output=True, text=True)
            open(os.path.join(OUT, f"out_{name}.txt"), "w").write(p.stdout)
            runs[name] = {"exit": p.returncode, "output_equals_registered": p.stdout == expected[name],
                          "stderr_tail": p.stderr[-500:]}
    res["runs"] = runs
    pre = table_from_prereg(text)
    got = table_from_output(open(os.path.join(OUT, "out_region_table.py.txt")).read()) if "region_table.py" in runs else {}
    res["table_7_1"] = {str(n): {"prereg": pre[n], "recomputed": got.get(n), "equal": got.get(n) == pre[n]} for n in pre}
    res["pass"] = (all(res["scripts_found_with_registered_sha256"].values()) and len(runs) == 3
                   and all(r["exit"] == 0 and r["output_equals_registered"] for r in runs.values())
                   and all(v["equal"] for v in res["table_7_1"].values()))
    res["stage1_ledger_seconds"] = led.total()
    json.dump(res, open(os.path.join(OUT, "v7.json"), "w"), indent=1)
    print(json.dumps({"found": res["scripts_found_with_registered_sha256"],
                      "runs": {k: (v["exit"], v["output_equals_registered"]) for k, v in runs.items()},
                      "table": {n: v["equal"] for n, v in res["table_7_1"].items()}, "pass": res["pass"]}, indent=1))
    sys.exit(0 if res["pass"] else 3)


if __name__ == "__main__":
    main()
