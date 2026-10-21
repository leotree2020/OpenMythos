"""
D3 gate (PREREGISTRATION 12.4, approved after the review of cbe2321).

D3 enters the H3 grading only if all of the following hold, recomputed from
the numbers in the two calibration files; the "status" / "failures" fields are
never trusted:
    original  validation/d3_calibration.json (commit 29280ea, not modified)
      A    the 53e5492 test detects the counterexample, the revision-4 test
           does not
      B1, B2  n_sim = 400, integer counts; Wilson 95% lower bound of the
           p <= 0.05 rate <= 0.05; full-decision rate <= p <= 0.05 rate
    addendum  validation/d3_calibration_addendum.json (revision 5)
      spec  p_valid [0.98, 0.98, 0.85, 0.85]; B3' seed 2025, n_sim 400,
            targets [1, 2, 3, 4]; C' seed 2026, n_sim 100, targets [2]
      B3'  no invalid simulation; same criterion as B1 / B2
      C'   no invalid simulation; full-decision rate >= 0.9
The original B3 / C results stay on record and are reported; they are not
part of this gate (revision 5). Any missing file, key or malformed number
closes the gate.
"""

import json
import math
import os

from common import HERE, wilson

ORIG = os.path.join(HERE, "validation", "d3_calibration.json")
ADD = os.path.join(HERE, "validation", "d3_calibration_addendum.json")
SPEC = {"p_valid": [0.98, 0.98, 0.85, 0.85],
        "B3prime": {"seed": 2025, "n_sim": 400, "targets": [1, 2, 3, 4]},
        "Cprime": {"seed": 2026, "n_sim": 100, "targets": [2]}}


def _count(rate, n):
    k = rate * n
    if not isinstance(rate, (int, float)) or abs(k - round(k)) > 1e-9 or not 0 <= k <= n:
        raise ValueError(f"rate {rate} is not a count out of {n}")
    return int(round(k))


def _null_ok(r, n_expected):
    n = r["n_sim"]
    if n != n_expected:
        return False, f"n_sim {n} != {n_expected}"
    k = _count(r["rate_p_le_0.05"], n)
    kd = _count(r["rate_full_decision"], n)
    lo = wilson(k, n)[0]
    if lo > 0.05:
        return False, f"Wilson lower bound {lo:.4f} > 0.05 ({k}/{n})"
    if kd > k:
        return False, f"full decision {kd} > p<=0.05 count {k}"
    return True, f"{k}/{n}, Wilson lower {lo:.4f}, full decision {kd}/{n}"


def d3_gate(orig_path=ORIG, add_path=ADD):
    """Returns (passed, {check: reason})."""
    why = {}
    try:
        o = json.load(open(orig_path))
        a = json.load(open(add_path))
    except (OSError, ValueError) as e:
        return False, {"files": f"missing or unreadable: {e}"}
    try:
        A = o["A_counterexample"]
        okA = A["legacy_53e5492"]["detected"] is True and A["revision4"]["decision"] == "未检测到"
        why["A"] = (okA, "legacy detects, revision 4 does not" if okA else f"A failed: {A}")
        for k in ("B1", "B2"):
            why[k] = _null_ok(o[k], 400)
        sp = a["spec"]
        okspec = (sp["p_valid"] == SPEC["p_valid"]
                  and all(sp[x][f] == SPEC[x][f] for x in ("B3prime", "Cprime") for f in ("seed", "n_sim", "targets")))
        why["addendum_spec"] = (okspec, "matches PREREGISTRATION 12.1" if okspec else f"spec {sp}")
        b = a["B3prime"]
        if b["invalid_simulations"] != 0:
            why["B3prime"] = (False, f"{b['invalid_simulations']} invalid simulations")
        else:
            why["B3prime"] = _null_ok(b, SPEC["B3prime"]["n_sim"])
        c = a["Cprime"]
        if c["invalid_simulations"] != 0:
            why["Cprime"] = (False, f"{c['invalid_simulations']} invalid simulations")
        elif c["n_sim"] != SPEC["Cprime"]["n_sim"]:
            why["Cprime"] = (False, f"n_sim {c['n_sim']}")
        else:
            kd = _count(c["rate_full_decision"], c["n_sim"])
            okc = kd >= math.ceil(0.9 * c["n_sim"])
            why["Cprime"] = (okc, f"full decision {kd}/{c['n_sim']}")
    except (KeyError, TypeError, ValueError) as e:
        why["structure"] = (False, f"malformed calibration file: {e!r}")
    passed = bool(why) and all(v[0] for v in why.values())
    return passed, {k: v[1] for k, v in why.items()} | {"_passed": {k: v[0] for k, v in why.items()}}
