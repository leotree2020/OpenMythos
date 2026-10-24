"""
Gate 2.2-C comparator. schema_version=2.2-c

Exit:
  0 GPU NUMERICAL PASS
  1 FAIL or STRUCTURAL PASS
  2 MISSING
  3 BLOCKED

GPU NUMERICAL PASS requires every acceptance check, MuonAdamW, collected CUDA RNG,
matching integrity hash, and source=GPU_RUNTIME.
--logic-test allows a complete synthetic package to exercise exit 0.
That path is labeled LOGIC TEST and is not a real GPU result.
"""
import hashlib
import json
import math
import struct
import sys
from pathlib import Path

SCHEMA = "2.2-c"
TOL_ABS = 1e-4
DTYPE_SIZE = {"float32": 4, "float16": 2, "bfloat16": 2, "int64": 8, "int32": 4, "int16": 2, "uint8": 1}
FLOAT_DTYPES = {"float32", "float16", "bfloat16"}

REQUIRED = [
    "schema_version", "model_index", "optimizer_index", "optimizer_param_groups",
    "batch_hashes", "losses", "scheduler", "microbatch_step", "optimizer_step",
    "update_count", "checkpoint_sha256", "source", "optimizer_class", "integrity",
]


def load(path):
    p = Path(path)
    return json.loads(p.read_text()) if p.is_file() else None


def integrity_of(obj):
    payload = {
        "model": [(e.get("name"), e.get("sha256")) for e in obj.get("model_index", [])],
        "opt": [(e.get("name"), e.get("sha256")) for e in obj.get("optimizer_index", [])],
        "groups": obj.get("optimizer_param_groups"),
        "sched": obj.get("scheduler"),
        "counts": [obj.get("microbatch_step"), obj.get("optimizer_step"), obj.get("update_count")],
        "ckpt": obj.get("checkpoint_sha256"),
        "source": obj.get("source"),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def decode(raw, dtype, numel):
    size = DTYPE_SIZE.get(dtype)
    if size is None:
        return None, "unknown dtype"
    if len(raw) != size * numel:
        return None, f"byte length {len(raw)} != {size}*{numel}"
    if dtype == "float32":
        vals = list(struct.unpack(f"<{numel}f", raw))
    elif dtype in ("float16", "bfloat16"):
        vals = [float(struct.unpack("<e", raw[i:i+2])[0]) for i in range(0, len(raw), 2)]
    elif dtype == "int64":
        vals = list(struct.unpack(f"<{numel}q", raw))
    elif dtype == "int32":
        vals = list(struct.unpack(f"<{numel}i", raw))
    else:
        vals = list(raw)
    if any(isinstance(v, float) and (math.isnan(v) or math.isinf(v)) for v in vals):
        return None, "NaN/Inf"
    return vals, None


def read_entry(blob_dir, entry):
    if "blob" not in entry:
        return None, "no blob"
    p = Path(blob_dir) / entry["blob"]
    if not p.is_file():
        return None, f"missing blob {entry['blob']}"
    raw = p.read_bytes()
    if hashlib.sha256(raw).hexdigest() != entry.get("sha256"):
        return None, f"sha mismatch {entry.get('name')}"
    return decode(raw, entry.get("dtype"), entry.get("numel")), None


def compare_numeric(a_vals, b_vals, dtype):
    if len(a_vals) != len(b_vals):
        return False, {"reason": "length"}
    max_abs, max_rel, n = 0.0, 0.0, 0
    for x, y in zip(a_vals, b_vals):
        if dtype in FLOAT_DTYPES:
            d = abs(float(x) - float(y))
            max_abs = max(max_abs, d)
            max_rel = max(max_rel, d / max(abs(float(y)), 1e-8))
            if d > TOL_ABS:
                n += 1
        elif x != y:
            return False, {"reason": "discrete mismatch"}
    return n == 0, {"max_abs": max_abs, "max_rel": max_rel, "n_diff": n}


def compare_index(a, b, blob):
    names_a = [e.get("name") for e in a]
    if len(names_a) != len(set(names_a)):
        return "FAIL", {"reason": "duplicate keys"}
    ma = {e["name"]: e for e in a}
    mb = {e["name"]: e for e in b}
    if set(ma) != set(mb):
        return "FAIL", {"reason": "key mismatch", "diff": sorted(set(ma) ^ set(mb))}
    worst = {"max_abs": 0.0, "max_rel": 0.0}
    for k in ma:
        ea, eb = ma[k], mb[k]
        if ea.get("shape") != eb.get("shape") or ea.get("dtype") != eb.get("dtype") or ea.get("numel") != eb.get("numel"):
            return "FAIL", {"reason": f"meta {k}"}
        if "blob" not in ea:
            if ea.get("discrete") != eb.get("discrete"):
                return "FAIL", {"reason": f"discrete {k}"}
            continue
        (va, err), _ = read_entry(blob, ea)
        if err or va is None:
            return "MISSING", {"reason": err or "decode"}
        (vb, err), _ = read_entry(blob, eb)
        if err or vb is None:
            return "MISSING", {"reason": err or "decode"}
        ok, detail = compare_numeric(va, vb, ea.get("dtype"))
        if not ok:
            return "FAIL", {"key": k, **detail}
        worst["max_abs"] = max(worst["max_abs"], detail.get("max_abs", 0))
        worst["max_rel"] = max(worst["max_rel"], detail.get("max_rel", 0))
    return "OK", worst


def main():
    logic = "--logic-test" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) < 4:
        print("usage: compare_equivalence.py A B1 B2 C --blob-dir DIR [--logic-test]")
        return 2
    blob = Path(sys.argv[sys.argv.index("--blob-dir") + 1]) if "--blob-dir" in sys.argv else Path(".")
    names = ["A", "B1", "B2", "C"]
    objs = []
    for n, p in zip(names, args[:4]):
        o = load(p)
        if o is None:
            print(json.dumps({"status": "MISSING", "who": n}))
            return 2
        if o.get("schema_version") != SCHEMA:
            print(json.dumps({"status": "MISSING", "who": n, "keys": ["schema_version"]}))
            return 2
        mk = [k for k in REQUIRED if k not in o or o[k] is None]
        if mk:
            print(json.dumps({"status": "MISSING", "who": n, "keys": mk}))
            return 2
        if o.get("integrity") != integrity_of(o):
            print(json.dumps({"status": "FAIL", "who": n, "reason": "integrity mismatch"}))
            return 1
        objs.append(o)
    A, B1, B2, C = objs
    if not B2.get("resume_from_sha256") or not C.get("resume_from_sha256"):
        print(json.dumps({"status": "MISSING", "keys": ["resume_from_sha256"]}))
        return 2

    checks = {}
    checks["hash"] = (B1["batch_hashes"] + B2["batch_hashes"]) == A["batch_hashes"]
    lb = B1["losses"] + B2["losses"]
    checks["loss"] = len(lb) == len(A["losses"]) and max(abs(x - y) for x, y in zip(A["losses"], lb)) <= TOL_ABS
    st_m, det_m = compare_index(A["model_index"], B2["model_index"], blob)
    if st_m == "MISSING":
        print(json.dumps({"status": "MISSING", "detail": det_m})); return 2
    checks["model"] = st_m == "OK"
    st_o, det_o = compare_index(A["optimizer_index"], B2["optimizer_index"], blob)
    if st_o == "MISSING":
        print(json.dumps({"status": "MISSING", "detail": det_o})); return 2
    checks["optimizer"] = st_o == "OK"
    checks["param_groups"] = A["optimizer_param_groups"] == B2["optimizer_param_groups"]
    checks["scheduler"] = A["scheduler"] == B2["scheduler"]
    checks["counts"] = (
        A["microbatch_step"] == B2["microbatch_step"]
        and A["optimizer_step"] == B2["optimizer_step"]
        and A["update_count"] == B2["update_count"]
    )
    checks["ckpt"] = B1["checkpoint_sha256"] == B2["resume_from_sha256"] == C["resume_from_sha256"]
    checks["rng"] = (B1.get("rng_stages") or {}).get("before_save") == (B2.get("rng_stages") or {}).get("after_load")
    c_concat = B1["batch_hashes"] + C["batch_hashes"]
    offset = next((i for i, (x, y) in enumerate(zip(A["batch_hashes"], c_concat)) if x != y), None if len(A["batch_hashes"]) == len(c_concat) else min(len(A["batch_hashes"]), len(c_concat)))
    checks["C_offset"] = offset is not None

    structural = all(checks.values())
    gpu_fields = (
        all(o.get("source") == "GPU_RUNTIME" for o in objs)
        and all(o.get("optimizer_class") == "MuonAdamW" for o in objs)
        and all((o.get("rng_stages") or {}).get("before_save", {}).get("cuda_status") == "COLLECTED" for o in (B2, C))
        and all((o.get("rng_stages") or {}).get("after_load", {}).get("cuda_status") == "COLLECTED" for o in (B2, C))
    )
    if structural and gpu_fields:
        status, code = ("GPU NUMERICAL PASS (LOGIC TEST)" if logic else "GPU NUMERICAL PASS"), 0
    elif structural:
        status, code = "STRUCTURAL PASS", 1
    else:
        status, code = "FAIL", 1
    print(json.dumps({
        "status": status, "schema_version": SCHEMA, "checks": checks,
        "model_detail": det_m, "opt_detail": det_o,
        "logic_test": logic, "real_gpu_run": False if logic else status == "GPU NUMERICAL PASS",
    }, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
