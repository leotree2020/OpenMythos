#!/usr/bin/env python3
"""
Regression tests of the D3 gate (d3_gate.py, PREREGISTRATION 12.4) and of its
effect on the H3 grading. Constructed calibration files (copies of the real
ones, mutated in a scratch directory) and one dry-run result of a non-formal
model (validation/fixtures/dryrun_smoke_openmythos_state.json: seed-99 smoke
checkpoint, timing data). Never reads or writes results/. Writes
validation/gate_tests.json; exits 1 on any failure.
"""

import copy
import json
import os
import sys
import tempfile

from analyze import NA, OPP, SUP, UNC, classes, grade, seed_direction
from common import HERE
from d3_gate import ADD, ORIG, d3_gate

orig, add = json.load(open(ORIG)), json.load(open(ADD))
tmp = tempfile.mkdtemp()
res, fail = {}, []


def gate(o=orig, a=add, drop=None):
    po, pa = os.path.join(tmp, "o.json"), os.path.join(tmp, "a.json")
    for p in (po, pa):
        if os.path.exists(p):
            os.remove(p)
    if drop != "orig":
        json.dump(o, open(po, "w"))
    if drop != "add":
        json.dump(a, open(pa, "w"))
    return d3_gate(po, pa)


def case(name, expected, o=orig, a=add, drop=None):
    ok, why = gate(o, a, drop)
    res[name] = {"expected_open": expected, "open": ok, "why": {k: v for k, v in why.items() if k != "_passed"}}
    if ok != expected:
        fail.append(name)


def mut(base, path, value):
    d = copy.deepcopy(base)
    x = d
    for k in path[:-1]:
        x = x[k]
    x[path[-1]] = value
    return d


case("all calibrations satisfied", True)
case("A fails (revision 4 detects the counterexample)", False,
     o=mut(orig, ["A_counterexample", "revision4", "decision"], "检测到按查询定向的注意力"))
case("A fails (legacy does not detect)", False, o=mut(orig, ["A_counterexample", "legacy_53e5492", "detected"], False))
case("B1 fails (Wilson lower > 0.05)", False, o=mut(orig, ["B1", "rate_p_le_0.05"], 0.1))
case("B2 fails (Wilson lower > 0.05)", False, o=mut(orig, ["B2", "rate_p_le_0.05"], 0.09))
case("B2 fails (full decision above p rate)", False, o=mut(orig, ["B2", "rate_full_decision"], 0.05))
case("B3' fails (Wilson lower > 0.05)", False, a=mut(add, ["B3prime", "rate_p_le_0.05"], 0.1))
case("C' fails (detection 0.85)", False, a=mut(add, ["Cprime", "rate_full_decision"], 0.85))
case("B3' has an invalid simulation", False, a=mut(add, ["B3prime", "invalid_simulations"], 1))
case("C' has an invalid simulation", False, a=mut(add, ["Cprime", "invalid_simulations"], 1))
case("original calibration file missing", False, drop="orig")
case("addendum file missing", False, drop="add")
case("status says pass but C' numbers fail", False,
     a=mut(mut(add, ["Cprime", "rate_full_decision"], 0.5), ["Cprime", "status"], "通过"))
case("status says pass but B3' numbers fail", False,
     a=mut(mut(add, ["B3prime", "rate_p_le_0.05"], 0.2), ["B3prime", "status"], "通过"))
case("original says no failures but B1 numbers fail", False,
     o=mut(mut(orig, ["B1", "rate_p_le_0.05"], 0.2), ["failures"], []))
case("addendum spec differs (p_valid)", False, a=mut(add, ["spec", "p_valid"], [0.95, 0.95, 0.6, 0.6]))
case("addendum spec differs (n_sim)", False, a=mut(add, ["B3prime", "n_sim"], 300))
case("rate is not a count out of n", False, a=mut(add, ["Cprime", "rate_full_decision"], 0.955))
case("missing key", False, a={k: v for k, v in add.items() if k != "Cprime"})
case("original C failure on record does not by itself close the gate", True,
     o=mut(orig, ["failures"], ["C"]))

# H3 grading: D3 never yields strong evidence on its own
def g(cl):
    return grade([seed_direction(c) for c in cl])

h3 = {
    "D3 excluded, D2 supports in 3/3": g([{"D2": SUP}] * 3),
    "D3 alone supports, D2 uncertain in 3/3": g([{"D2": UNC, "D3": SUP}] * 3),
    "D2 and D3 support in 3/3": g([{"D2": SUP, "D3": SUP}] * 3),
}
res["h3_grading"] = h3
if not (h3["D3 excluded, D2 supports in 3/3"]["grade"] == "中"
        and h3["D3 alone supports, D2 uncertain in 3/3"]["grade"] != "强"
        and h3["D2 and D3 support in 3/3"]["grade"] == "强"):
    fail.append("h3_grading")

# classes(): the D3 class appears only when the gate is open (dry-run result
# of a non-formal model)
r = json.load(open(os.path.join(HERE, "validation", "fixtures", "dryrun_smoke_openmythos_state.json")))
r["_seed"] = 1
d0 = json.load(open(os.path.join(HERE, "validation", "d0_rev3.json")))
closed = classes(copy.deepcopy(r), "openmythos", d0, True, False)["H3"]
opened = classes(copy.deepcopy(r), "openmythos", d0, True, True)["H3"]
res["classes_H3"] = {"gate_closed": closed, "gate_open": opened}
if "D3" in closed or "D3" not in opened:
    fail.append("classes_H3")

res["failures"] = fail
with open(os.path.join(HERE, "validation", "gate_tests.json"), "w") as f:
    json.dump(res, f, indent=1, ensure_ascii=False)
for k, v in res.items():
    if isinstance(v, dict) and "open" in v:
        print(("PASS" if v["open"] == v["expected_open"] else "FAIL"), "|", k, "| open =", v["open"])
print("h3:", {k: v["grade"] for k, v in h3.items()}, "| classes:", res["classes_H3"])
print("failures:", fail)
sys.exit(1 if fail else 0)
