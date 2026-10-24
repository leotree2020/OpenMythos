"""
Checkpoint numerical comparator. Does not run training.
STATIC VALIDATION tool. Not GPU evidence.
"""
import json
import math
import sys
from pathlib import Path

TOL_LOSS = 1e-4
TOL_WEIGHT = 1e-4
TOL_OPT = 1e-4

REQUIRED_RUN = [
    "batch_hashes", "losses", "model_state", "optimizer_state",
    "scheduler", "microbatch_step", "optimizer_step", "update_count",
    "rng", "checkpoint_sha256",
]
REQUIRED_RNG = ["cpu", "cuda", "python", "numpy"]


def load(path):
    p = Path(path)
    if not p.is_file():
        return None
    return json.loads(p.read_text())


def missing_keys(obj, keys):
    return [k for k in keys if k not in obj or obj[k] is None]


def bad_number(x):
    return isinstance(x, float) and (math.isnan(x) or math.isinf(x))


def tensor_equal(a, b, tol):
    """Full compare. No zip truncation. Returns ok, max_abs, max_rel, n_diff, reason."""
    if not isinstance(a, list) or not isinstance(b, list):
        return False, 0.0, 0.0, 1, "not a list"
    if len(a) != len(b):
        return False, 0.0, 0.0, abs(len(a) - len(b)), f"length {len(a)}!={len(b)}"
    max_abs, max_rel, n = 0.0, 0.0, 0
    for x, y in zip(a, b):  # lengths already equal
        if bad_number(x) or bad_number(y):
            return False, max_abs, max_rel, n + 1, "NaN/Inf"
        d = abs(float(x) - float(y))
        denom = max(abs(float(y)), 1e-8)
        r = d / denom
        max_abs = max(max_abs, d)
        max_rel = max(max_rel, r)
        if d > tol:
            n += 1
    return n == 0, max_abs, max_rel, n, "ok"


def model_diff(a, b):
    if set(a) != set(b):
        return False, {"reason": "key mismatch", "diff": sorted(set(a) ^ set(b))}
    worst = {"max_abs": 0.0, "max_rel": 0.0, "n_diff": 0, "bad": []}
    for k in a:
        if a[k].get("shape") != b[k].get("shape"):
            return False, {"reason": f"shape {k}"}
        if a[k].get("dtype") != b[k].get("dtype"):
            return False, {"reason": f"dtype {k}"}
        va, vb = a[k].get("values"), b[k].get("values")
        if va is None or vb is None:
            return False, {"reason": f"missing values {k}"}
        if a[k].get("numel") != len(va) or b[k].get("numel") != len(vb):
            return False, {"reason": f"numel mismatch {k}"}
        ok, ma, mr, n, why = tensor_equal(va, vb, TOL_WEIGHT)
        worst["max_abs"] = max(worst["max_abs"], ma)
        worst["max_rel"] = max(worst["max_rel"], mr)
        worst["n_diff"] += n
        if not ok:
            worst["bad"].append({"key": k, "why": why, "max_abs": ma})
    return worst["n_diff"] == 0 and not worst["bad"], worst


def opt_diff(a, b):
    """Exact on structure/discrete; tolerance on numeric tensors."""
    if a.get("param_groups") != b.get("param_groups"):
        return False, {"reason": "param_groups differ"}
    sa, sb = a.get("state", {}), b.get("state", {})
    if set(sa) != set(sb):
        return False, {"reason": "state keys differ", "diff": sorted(set(sa) ^ set(sb))}
    worst = {"max_abs": 0.0, "max_rel": 0.0, "bad": []}
    for k in sa:
        for field in set(sa[k]) | set(sb[k]):
            if field not in sa[k] or field not in sb[k]:
                return False, {"reason": f"missing field {k}.{field}"}
            va, vb = sa[k][field], sb[k][field]
            if isinstance(va, list) and isinstance(vb, list):
                ok, ma, mr, n, why = tensor_equal(va, vb, TOL_OPT)
                worst["max_abs"] = max(worst["max_abs"], ma)
                worst["max_rel"] = max(worst["max_rel"], mr)
                if not ok:
                    worst["bad"].append({"key": f"{k}.{field}", "why": why, "max_abs": ma})
            elif va != vb:
                return False, {"reason": f"discrete mismatch {k}.{field}"}
    return not worst["bad"], worst


def first_mismatch(a, b):
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return i
    if len(a) != len(b):
        return min(len(a), len(b))
    return None


def main():
    if len(sys.argv) < 5:
        print("usage: compare_equivalence.py A.json B1.json B2.json C.json")
        return 2
    names = ["A", "B1", "B2", "C"]
    objs = []
    for n, p in zip(names, sys.argv[1:5]):
        o = load(p)
        if o is None:
            print(json.dumps({"status": "MISSING", "who": n, "path": p}))
            return 2
        mk = missing_keys(o, REQUIRED_RUN)
        if mk:
            print(json.dumps({"status": "MISSING", "who": n, "keys": mk}))
            return 2
        rk = missing_keys(o.get("rng", {}), REQUIRED_RNG)
        if rk:
            print(json.dumps({"status": "MISSING", "who": n, "rng": rk}))
            return 2
        objs.append(o)
    A, B1, B2, C = objs
    if not B2.get("resume_from_sha256") or not C.get("resume_from_sha256"):
        print(json.dumps({"status": "MISSING", "keys": ["resume_from_sha256"]}))
        return 2

    concat = B1["batch_hashes"] + B2["batch_hashes"]
    hash_ok = concat == A["batch_hashes"]
    losses_b = B1["losses"] + B2["losses"]
    if len(losses_b) != len(A["losses"]):
        loss_ok, loss_detail = False, "length mismatch"
    else:
        md = max(abs(x - y) for x, y in zip(A["losses"], losses_b))
        loss_ok, loss_detail = md <= TOL_LOSS, f"max_abs={md}"
    model_ok, model_detail = model_diff(A["model_state"], B2["model_state"])
    opt_ok, opt_detail = opt_diff(A["optimizer_state"], B2["optimizer_state"])
    sched_ok = A["scheduler"] == B2["scheduler"]
    count_ok = (
        A["microbatch_step"] == B2["microbatch_step"]
        and A["optimizer_step"] == B2["optimizer_step"]
        and A["update_count"] == B2["update_count"]
    )
    ckpt_ok = B1["checkpoint_sha256"] == B2["resume_from_sha256"] == C["resume_from_sha256"]
    # RNG: B1 saved vs B2 restored (not mere presence)
    rng_ok = B1.get("rng_at_save") == B2.get("rng_at_restore")
    if B1.get("rng_at_save") is None or B2.get("rng_at_restore") is None:
        print(json.dumps({"status": "MISSING", "keys": ["rng_at_save/rng_at_restore"]}))
        return 2
    # C offset position
    c_concat = B1["batch_hashes"] + C["batch_hashes"]
    offset = first_mismatch(A["batch_hashes"], c_concat)
    c_ok = offset is not None

    checks = {
        "hash_A_eq_B1B2": hash_ok,
        "loss_A_eq_B1B2": loss_ok,
        "model_A_eq_B2": model_ok,
        "optimizer_A_eq_B2": opt_ok,
        "scheduler_A_eq_B2": sched_ok,
        "counts_A_eq_B2": count_ok,
        "ckpt_B1_eq_B2_C": ckpt_ok,
        "rng_B1_save_eq_B2_restore": rng_ok,
        "C_offset_detected": c_ok,
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    print(json.dumps({
        "status": status,
        "checks": checks,
        "loss_detail": loss_detail,
        "model_detail": model_detail,
        "opt_detail": opt_detail,
        "C_first_mismatch_index": offset,
        "tolerance": {"loss": TOL_LOSS, "weight": TOL_WEIGHT, "opt": TOL_OPT},
        "source": "STATIC VALIDATION",
    }, indent=2))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
