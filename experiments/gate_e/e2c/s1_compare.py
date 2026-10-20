"""
R3 comparison (E2C_PREREG_DRAFT 6): every value of a D2c result against the
corresponding value of E1's archived result of the same state. Numbers must
agree within 1e-6 (absolute); strings, booleans and None exactly; lists in
length; dicts in their keys. Compared parts: M1; M2 linear_std / linear_raw
P2@* (every checkpoint); M2 mlp P2@*, planted P2@<last point>, M3, M6 (heavy
checkpoints); M0 (steps 0, 12000).
"""

import math

TOL = 1e-6


def diff(a, b, path="", out=None):
    out = out if out is not None else {"n_values": 0, "max_abs_diff": 0.0, "mismatches": []}
    if isinstance(a, bool) or isinstance(b, bool) or a is None or b is None or isinstance(a, str) or isinstance(b, str):
        out["n_values"] += 1
        if a != b or type(a) is not type(b):
            out["mismatches"].append({"path": path, "d2c": a, "e1": b})
        return out
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        out["n_values"] += 1
        if math.isnan(a) or math.isnan(b):
            if not (math.isnan(a) and math.isnan(b)):
                out["mismatches"].append({"path": path, "d2c": a, "e1": b})
            return out
        d = abs(a - b)
        out["max_abs_diff"] = max(out["max_abs_diff"], d)
        if d > TOL:
            out["mismatches"].append({"path": path, "d2c": a, "e1": b, "abs_diff": d})
        return out
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out["mismatches"].append({"path": path, "reason": f"list length {len(a)} vs {len(b)}"})
            return out
        for i, (x, y) in enumerate(zip(a, b)):
            diff(x, y, f"{path}[{i}]", out)
        return out
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) != set(b):
            out["mismatches"].append({"path": path, "reason": "keys differ",
                                      "only_d2c": sorted(set(a) - set(b))[:10], "only_e1": sorted(set(b) - set(a))[:10]})
        for k in sorted(set(a) & set(b)):
            diff(a[k], b[k], f"{path}.{k}", out)
        return out
    out["mismatches"].append({"path": path, "reason": f"type {type(a).__name__} vs {type(b).__name__}"})
    return out


def compare_state(d, e1):
    """d: D2c result; e1: E1 result of the same state."""
    out = {"n_values": 0, "max_abs_diff": 0.0, "mismatches": []}
    parts = [("M1", d["M1"], e1["M1"])]
    for kind in ("linear_std", "linear_raw"):
        for k, v in d["M2"][kind].items():
            parts.append((f"M2.{kind}.{k}", v, e1["M2"][kind].get(k)))
    if d.get("heavy"):
        for k, v in d["M2"]["mlp"].items():
            parts.append((f"M2.mlp.{k}", v, e1["M2"]["mlp"].get(k)))
        for k, v in d["M2"]["planted"].items():
            parts.append((f"M2.planted.{k}", v, e1["M2"]["planted"].get(k)))
        parts += [("M3", d["M3"], e1["M3"]), ("M6", d["M6"], e1["M6"])]
    if "M0" in d:
        parts.append(("M0", d["M0"], e1["M0"]))
    for name, a, b in parts:
        diff(a, b, name, out)
    out["param_sha256_equal"] = d["param_sha256"] == e1["param_sha256"]
    out["parts"] = [p[0] for p in parts]
    out["pass"] = not out["mismatches"] and out["param_sha256_equal"]
    return out
