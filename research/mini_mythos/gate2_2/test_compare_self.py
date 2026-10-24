"""Self-test compare_equivalence.py with synthetic evidence. No GPU."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "compare_equivalence.py"

def base():
    return {
        "batch_hashes": ["h0", "h1", "h2", "h3"],
        "losses": [1.0, 1.1, 1.2, 1.3],
        "model_state": {"w": {"shape": [2], "dtype": "float32", "values": [0.1, 0.2]}},
        "optimizer_state": {"param_groups": [{"lr": 0.001}], "state": {"0": {"exp_avg": [0.0]}}},
        "scheduler": {"last_epoch": 3, "lr_trace": [0.001, 0.001]},
        "microbatch_step": 4,
        "optimizer_step": 1,
        "update_count": 1,
        "rng": {"cpu": "c", "cuda": "g", "python": "p", "numpy": "n"},
        "checkpoint_sha256": "CKPT",
        "resume_from_sha256": "CKPT",
    }

def write(d, obj):
    p = d / "x.json"
    # unique names
    return p

def run(a, b1, b2, c):
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        files = []
        for name, obj in (("A", a), ("B1", b1), ("B2", b2), ("C", c)):
            p = td / f"{name}.json"
            if obj is None:
                files.append(str(td / "missing.json"))
            else:
                p.write_text(json.dumps(obj))
                files.append(str(p))
        r = subprocess.run([sys.executable, str(SCRIPT), *files], capture_output=True, text=True)
        return r.returncode, r.stdout

def main():
    results = []
    A = base()
    B1 = base(); B1["batch_hashes"] = ["h0", "h1"]; B1["losses"] = [1.0, 1.1]
    B2 = base(); B2["batch_hashes"] = ["h2", "h3"]; B2["losses"] = [1.2, 1.3]
    C = base(); C["batch_hashes"] = ["h3"]  # skip h2
    C["losses"] = [1.3]

    code, out = run(A, B1, B2, C)
    results.append({"name": "identical_with_C_skip", "expect": "PASS", "code": code, "ok": code == 0 and '"PASS"' in out})

    B2w = json.loads(json.dumps(B2)); B2w["model_state"]["w"]["values"] = [9.0, 9.0]
    code, out = run(A, B1, B2w, C)
    results.append({"name": "weight_modified", "expect": "FAIL", "code": code, "ok": code != 0 and '"FAIL"' in out})

    B2o = json.loads(json.dumps(B2)); B2o["optimizer_state"]["state"]["0"]["exp_avg"] = [1.0]
    code, out = run(A, B1, B2o, C)
    results.append({"name": "optimizer_modified", "expect": "FAIL", "code": code, "ok": code != 0 and '"FAIL"' in out})

    code, out = run(A, B1, None, C)
    results.append({"name": "checkpoint_missing", "expect": "MISSING", "code": code, "ok": code != 0 and '"MISSING"' in out})

    B2bad = json.loads(json.dumps(B2)); B2bad["batch_hashes"] = ["h2", "WRONG"]
    code, out = run(A, B1, B2bad, C)
    results.append({"name": "concat_mismatch", "expect": "FAIL", "code": code, "ok": code != 0 and '"FAIL"' in out})

    code, out = run(A, B1, B2, C)
    results.append({"name": "C_skip_detected", "expect": "PASS", "code": code, "ok": code == 0})

    Csame = json.loads(json.dumps(B2))  # C matches B2, no skip
    code, out = run(A, B1, B2, Csame)
    results.append({"name": "C_no_skip", "expect": "FAIL", "code": code, "ok": code != 0 and '"FAIL"' in out})

    failed = [r for r in results if not r["ok"]]
    print(json.dumps({"tests": results, "failed": len(failed)}, indent=2))
    return 0 if not failed else 1

if __name__ == "__main__":
    sys.exit(main())
