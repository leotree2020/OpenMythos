"""
Comparator for the binary evidence schema.

Exit codes:
  0  GPU NUMERICAL PASS only
  1  FAIL or STRUCTURAL PASS (not formal GPU success)
  2  MISSING
  3  BLOCKED

GPU NUMERICAL PASS requires source=GPU_RUNTIME, optimizer_class=MuonAdamW,
and collected CUDA RNG. SYNTHETIC and CPU_PARCAE cannot obtain it.
"""
import hashlib
import json
import sys
from pathlib import Path

TOL = 1e-4
REQUIRED = ["model_index", "optimizer_index", "batch_hashes", "losses", "checkpoint_sha256", "source"]


def load(path):
    p = Path(path)
    return json.loads(p.read_text()) if p.is_file() else None


def read_blob(blob_dir, entry):
    if "blob" not in entry:
        return None, "no blob field"
    p = Path(blob_dir) / entry["blob"]
    if not p.is_file():
        return None, f"missing blob {entry['blob']}"
    raw = p.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    if sha != entry.get("sha256"):
        return None, f"sha mismatch {entry.get('name')}"
    if entry.get("numel") is not None and len(raw) < 1:
        return None, "empty blob"
    return raw, None


def index_map(index):
    return {e["name"]: e for e in index if "name" in e}


def compare_index(a, b, blob_a, blob_b):
    ma, mb = index_map(a), index_map(b)
    if set(ma) != set(mb):
        return "FAIL", {"reason": "key mismatch", "diff": sorted(set(ma) ^ set(mb))}
    bad = []
    for k in ma:
        ea, eb = ma[k], mb[k]
        if ea.get("shape") != eb.get("shape") or ea.get("dtype") != eb.get("dtype") or ea.get("numel") != eb.get("numel"):
            return "FAIL", {"reason": f"meta {k}"}
        if "blob" in ea:
            ra, err = read_blob(blob_a, ea)
            if err:
                return "MISSING", {"reason": err}
            rb, err = read_blob(blob_b, eb)
            if err:
                return "MISSING", {"reason": err}
            if ra != rb and ea.get("sha256") != eb.get("sha256"):
                bad.append(k)
        elif ea.get("discrete") != eb.get("discrete"):
            bad.append(k)
    return ("FAIL", {"bad": bad}) if bad else ("OK", {})


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) < 4:
        print("usage: compare_equivalence.py A.json B1.json B2.json C.json --blob-dir DIR")
        return 2
    blob = Path(".")
    if "--blob-dir" in sys.argv:
        blob = Path(sys.argv[sys.argv.index("--blob-dir") + 1])
    names = ["A", "B1", "B2", "C"]
    objs = []
    for n, p in zip(names, args[:4]):
        o = load(p)
        if o is None:
            print(json.dumps({"status": "MISSING", "who": n}))
            return 2
        mk = [k for k in REQUIRED if k not in o or o[k] is None]
        if mk:
            print(json.dumps({"status": "MISSING", "who": n, "keys": mk}))
            return 2
        objs.append(o)
    A, B1, B2, C = objs
    if not B2.get("resume_from_sha256") or not C.get("resume_from_sha256"):
        print(json.dumps({"status": "MISSING", "keys": ["resume_from_sha256"]}))
        return 2

    st_m, det_m = compare_index(A["model_index"], B2["model_index"], blob, blob)
    if st_m == "MISSING":
        print(json.dumps({"status": "MISSING", "detail": det_m}))
        return 2
    st_o, det_o = compare_index(A["optimizer_index"], B2["optimizer_index"], blob, blob)
    if st_o == "MISSING":
        print(json.dumps({"status": "MISSING", "detail": det_o}))
        return 2
    hash_ok = (B1["batch_hashes"] + B2["batch_hashes"]) == A["batch_hashes"]
    ckpt_ok = B1["checkpoint_sha256"] == B2["resume_from_sha256"] == C["resume_from_sha256"]
    c_offset = next((i for i, (x, y) in enumerate(zip(A["batch_hashes"], B1["batch_hashes"] + C["batch_hashes"])) if x != y), None)
    structural = st_m == "OK" and st_o == "OK" and hash_ok and ckpt_ok and c_offset is not None

    gpu_ok = (
        all(o.get("source") == "GPU_RUNTIME" for o in objs)
        and all(o.get("optimizer_class") == "MuonAdamW" for o in objs)
        and all((o.get("rng_stages") or {}).get("before_save", {}).get("cuda_status") == "COLLECTED" for o in (B2, C))
        and all((o.get("rng_stages") or {}).get("after_load", {}).get("cuda_status") == "COLLECTED" for o in (B2, C))
    )
    if structural and gpu_ok:
        status, code = "GPU NUMERICAL PASS", 0
    elif structural:
        status, code = "STRUCTURAL PASS", 1
    else:
        status, code = "FAIL", 1
    print(json.dumps({
        "status": status,
        "model": st_m,
        "optimizer": st_o,
        "hash_ok": hash_ok,
        "ckpt_ok": ckpt_ok,
        "C_offset": c_offset,
        "gpu_qualified": gpu_ok,
        "model_detail": det_m,
        "opt_detail": det_o,
    }, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
