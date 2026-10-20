#!/usr/bin/env python3
"""
Stage 1, gate 5: V7, V5, V3, V4 (E2C_PREREG_DRAFT 6), in that order, after gates
1-4 passed. The first failure stops the gate (F3 for V4 / V7, F5 for V5).

    V7  s1_v7.py               registered statistics scripts re-run; table of 7.1
    V7a s1_analysis_tests.py   the stage-4 analysis code: p-bar of Appendix F, table <=> p-bar
                               rule, McNemar / Holm, decision table, t_P2lin vs E1 (R3 data)
    V5  s1_v5.py               non-formal LFS storage test, volume projection
    V3  s1_v3.py               timing on seed 99 and the stage-3 forecast (uses V5's rates)
    V4  e2c_launcher_tests.py  fault-injection tests of run_e2c.py (stubs, simulated salt)
Each script runs under the stage-1 ledger itself; writes stage1/gate5.json.
"""

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from s1_budget import STAGE1, Ledger  # noqa: E402

STEPS = (("V7", ["s1_v7.py"], "v7/v7.json", 3), ("V7a", ["s1_analysis_tests.py"], "analysis_tests.json", 3), ("V5", ["s1_v5.py"], "v5/v5.json", 5),
         ("V3", ["s1_v3.py"], "v3/v3.json", 3), ("V4", ["s1_budget.py", "exec", "v4_launcher_tests", "--", sys.executable,
                                                       os.path.join(HERE, "e2c_launcher_tests.py")], "v4/launcher_tests.json", 3))


def main():
    res = {}
    for name, argv, out, fail_code in STEPS:
        led = Ledger()
        if led.total() >= led.cap:
            res["stopped"] = "F9: stage-1 cap reached"
            break
        p = subprocess.run([sys.executable, os.path.join(HERE, argv[0])] + argv[1:], cwd=HERE, capture_output=True, text=True)
        open(os.path.join(STAGE1, f"gate5_{name}.log"), "w").write(p.stdout + p.stderr)
        r = json.load(open(os.path.join(STAGE1, out))) if os.path.exists(os.path.join(STAGE1, out)) else {}
        ok = p.returncode == 0 and (r.get("pass") is True or r.get("all_pass") is True)
        res[name] = {"exit": p.returncode, "pass": ok, "record": out}
        print(f"{name}: {'PASS' if ok else 'FAIL'} (exit {p.returncode})", flush=True)
        if not ok:
            res["stopped"] = f"{name} failed"
            break
    res["pass"] = all(res.get(n, {}).get("pass") for n, *_ in STEPS)
    res["stage1_ledger_seconds"] = Ledger().total()
    json.dump(res, open(os.path.join(STAGE1, "gate5.json"), "w"), indent=1)
    print("GATE 5", "PASS" if res["pass"] else "FAIL", f"ledger {res['stage1_ledger_seconds']:.0f} s")
    sys.exit(0 if res["pass"] else 3)


if __name__ == "__main__":
    main()
