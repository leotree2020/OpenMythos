"""
Checkpoint numerical comparator. Does not run training.

Statuses:
  PASS    all required conditions hold
  FAIL    evidence present but values disagree
  MISSING required evidence absent
Non-zero exit on FAIL or MISSING.

Not a MuonAdamW runtime verification by itself.
"""

import hashlib
import json
import sys
from pathlib import Path

TOL_LOSS = 1e-4
TOL_WEIGHT = 1e-4

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


def model_diff(a, b):
    """Compare key set, shape, dtype, and numeric sha or max_abs."""
    if set(a) != set(b):
        return False, f"key mismatch {set(a)^set(b)}"
    n_diff = 0
    max_abs = 0.0
    for k in a:
        if a[k].get("shape") != b[k].get("shape") or a[k].get("dtype") != b[k].get("dtype"):
            return False, f"shape/dtype {k}"
        if "values" in a[k] and "values" in b[k]:
            for x, y in zip(a[k]["values"], b[k]["values"]):
                d = abs(x - y)
                max_abs = max(max_abs, d)
                if d > TOL_WEIGHT:
                    n_diff += 1
        elif a[k].get("sha256") != b[k].get("sha256"):
            n_diff += 1
    return n_diff == 0, f"n_diff={n_diff} max_abs={max_abs}"


def main():
    if len(sys.argv) < 5:
        print("usage: compare_equivalence.py A.json B1.json B2.json C.json")
        return 2
    paths = sys.argv[1:5]
    objs = [load(p) for p in paths]
    names = ["A", "B1", "B2", "C"]
    for n, o, p in zip(names, objs, paths):
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

    A, B1, B2, C = objs
    # 1. concatenated hashes
    concat = B1["batch_hashes"] + B2["batch_hashes"]
    hash_ok = concat == A["batch_hashes"]
    # 2. losses
    losses_b = B1["losses"] + B2["losses"]
    if len(losses_b) != len(A["losses"]):
        loss_ok = False
        loss_detail = "length mismatch"
    else:
        md = max(abs(x - y) for x, y in zip(A["losses"], losses_b))
        loss_ok = md <= TOL_LOSS
        loss_detail = f"max_abs={md}"
    # 3. model endpoint A vs B2
    model_ok, model_detail = model_diff(A["model_state"], B2["model_state"])
    # 4. optimizer
    opt_ok = A["optimizer_state"] == B2["optimizer_state"]
    # 5. scheduler
    sched_ok = A["scheduler"] == B2["scheduler"]
    # 6. counts
    count_ok = (
        A["microbatch_step"] == B2["microbatch_step"]
        and A["optimizer_step"] == B2["optimizer_step"]
        and A["update_count"] == B2["update_count"]
    )
    # 8. checkpoint identity
    ckpt_ok = B1["checkpoint_sha256"] == B2.get("resume_from_sha256") == C.get("resume_from_sha256")
    # C negative
    c_concat = B1["batch_hashes"] + C["batch_hashes"]
    c_differs = c_concat != A["batch_hashes"]

    checks = {
        "hash_A_eq_B1B2": hash_ok,
        "loss_A_eq_B1B2": loss_ok,
        "model_A_eq_B2": model_ok,
        "optimizer_A_eq_B2": opt_ok,
        "scheduler_A_eq_B2": sched_ok,
        "counts_A_eq_B2": count_ok,
        "ckpt_B1_eq_B2_C": ckpt_ok,
        "C_detects_skip": c_differs,
    }
    if all(checks.values()):
        status = "PASS"
        code = 0
    else:
        status = "FAIL"
        code = 1
    print(json.dumps({
        "status": status,
        "checks": checks,
        "loss_detail": loss_detail,
        "model_detail": model_detail,
        "tolerance": {"loss": TOL_LOSS, "weight": TOL_WEIGHT},
        "note": "PASS requires all checks. Batch hash + loss alone is not equivalence.",
    }, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
