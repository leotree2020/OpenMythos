"""
Gate 2.2-C comparator. schema_version=2.2-c. FROZEN after this fix.

Exit: 0 GPU NUMERICAL PASS | 1 FAIL/STRUCTURAL | 2 MISSING | 3 BLOCKED
Formal mode requires native_entry_artifact from the real training entry.
--logic-test is isolated and labeled LOGIC TEST.
"""
import hashlib
import json
import math
import struct
import sys
from pathlib import Path

SCHEMA = "2.2-c"
TOL_ABS = 1e-4
DTYPE_SIZE = {"float32": 4, "float16": 2, "bfloat16": 2, "int64": 8, "int32": 4, "uint8": 1}
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
    elif dtype == "float16":
        vals = [float(struct.unpack("<e", raw[i:i + 2])[0]) for i in range(0, len(raw), 2)]
    elif dtype == "bfloat16":
        vals = []
        for i in range(0, len(raw), 2):
            u = struct.unpack("<H", raw[i:i + 2])[0]
            vals.append(struct.unpack("<f", struct.pack("<I", u << 16))[0])
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
    if entry.get("shape"):
        prod = 1
        for d in entry["shape"]:
            prod *= int(d)
        if prod != int(entry.get("numel", -1)):
            return None, f"shape product {entry.get('name')}"
    return decode(raw, entry.get("dtype"), entry.get("numel"))


def compare_numeric(a_vals, b_vals, dtype):
    if len(a_vals) != len(b_vals):
        return False, {"reason": "length"}
    max_abs = max_rel = 0.0
    n = 0
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
    def names(idx):
        return [e.get("name") for e in idx]
    if len(names(a)) != len(set(names(a))) or len(names(b)) != len(set(names(b))):
        return "FAIL", {"reason": "duplicate keys"}
    ma, mb = {e["name"]: e for e in a}, {e["name"]: e for e in b}
    if set(ma) != set(mb):
        return "FAIL", {"reason": "key mismatch"}
    worst = {"max_abs": 0.0, "max_rel": 0.0}
    for k in ma:
        ea, eb = ma[k], mb[k]
        if ea.get("shape") != eb.get("shape") or ea.get("dtype") != eb.get("dtype") or ea.get("numel") != eb.get("numel"):
            return "FAIL", {"reason": f"meta {k}"}
        if "blob" not in ea:
            if ea.get("discrete") != eb.get("discrete"):
                return "FAIL", {"reason": f"discrete {k}"}
            continue
        va, err = read_entry(blob, ea)
        if err or va is None:
            return "MISSING", {"reason": err}
        vb, err = read_entry(blob, eb)
        if err or vb is None:
            return "MISSING", {"reason": err}
        ok, detail = compare_numeric(va, vb, ea.get("dtype"))
        if not ok:
            return "FAIL", {"key": k, **detail}
        worst["max_abs"] = max(worst["max_abs"], detail.get("max_abs", 0))
        worst["max_rel"] = max(worst["max_rel"], detail.get("max_rel", 0))
    return "OK", worst


def rng_ok(saved, restored):
    if not isinstance(saved, dict) or not isinstance(restored, dict):
        return False
    if saved.get("stage") != "before_save" or restored.get("stage") != "after_load":
        return False
    return all(saved.get(k) == restored.get(k) for k in ("cpu", "cuda", "python", "numpy"))


def main():
    try:
        logic = "--logic-test" in sys.argv
        args = [a for a in sys.argv[1:] if not a.startswith("--")]
        if len(args) < 4:
            print(json.dumps({"status": "MISSING", "reason": "need 4 evidence files"}))
            return 2
        blob = Path(sys.argv[sys.argv.index("--blob-dir") + 1]) if "--blob-dir" in sys.argv else Path(".")
        objs = []
        for n, p in zip(["A", "B1", "B2", "C"], args[:4]):
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
        if not A.get("losses") or not B1.get("losses") or not B2.get("losses"):
            print(json.dumps({"status": "MISSING", "keys": ["losses"]}))
            return 2
        checks = {
            "hash": (B1["batch_hashes"] + B2["batch_hashes"]) == A["batch_hashes"],
        }
        lb = B1["losses"] + B2["losses"]
        checks["loss"] = len(lb) == len(A["losses"]) and max(abs(float(x) - float(y)) for x, y in zip(A["losses"], lb)) <= TOL_ABS
        st_m, det_m = compare_index(A["model_index"], B2["model_index"], blob)
        if st_m == "MISSING":
            print(json.dumps({"status": "MISSING", "detail": det_m}))
            return 2
        checks["model"] = st_m == "OK"
        st_o, det_o = compare_index(A["optimizer_index"], B2["optimizer_index"], blob)
        if st_o == "MISSING":
            print(json.dumps({"status": "MISSING", "detail": det_o}))
            return 2
        checks["optimizer"] = st_o == "OK"
        checks["param_groups"] = A["optimizer_param_groups"] == B2["optimizer_param_groups"]
        checks["scheduler"] = A["scheduler"] == B2["scheduler"]
        checks["counts"] = A["microbatch_step"] == B2["microbatch_step"] and A["optimizer_step"] == B2["optimizer_step"] and A["update_count"] == B2["update_count"]
        checks["ckpt"] = B1["checkpoint_sha256"] == B2["resume_from_sha256"] == C["resume_from_sha256"]
        checks["rng"] = rng_ok((B1.get("rng_stages") or {}).get("before_save"), (B2.get("rng_stages") or {}).get("after_load"))
        concat_c = B1["batch_hashes"] + C["batch_hashes"]
        offset = next((i for i, (x, y) in enumerate(zip(A["batch_hashes"], concat_c)) if x != y), None)
        checks["C_offset_at_boundary"] = offset == len(B1["batch_hashes"])
        structural = all(checks.values())
        labels_ok = (
            all(o.get("source") == "GPU_RUNTIME" for o in objs)
            and all(o.get("optimizer_class") == "MuonAdamW" for o in objs)
            and all((o.get("rng_stages") or {}).get("before_save", {}).get("cuda_status") == "COLLECTED" for o in (B2, C))
        )
        native = all(o.get("native_entry_artifact") for o in objs)
        if not logic and structural and labels_ok and not native:
            print(json.dumps({"status": "BLOCKED", "reason": "no verifiable native training-entry artifact"}))
            return 3
        if structural and labels_ok and (logic or native):
            status, code = ("GPU NUMERICAL PASS (LOGIC TEST)" if logic else "GPU NUMERICAL PASS"), 0
        elif structural:
            status, code = "STRUCTURAL PASS", 1
        else:
            status, code = "FAIL", 1
        print(json.dumps({"status": status, "schema_version": SCHEMA, "checks": checks, "logic_test": logic, "real_gpu_run": (not logic) and status == "GPU NUMERICAL PASS"}, indent=2))
        return code
    except Exception as e:
        print(json.dumps({"status": "FAIL", "reason": f"{type(e).__name__}: {e}"}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
