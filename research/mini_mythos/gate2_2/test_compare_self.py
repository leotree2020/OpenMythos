"""Extended self-test. No GPU. Synthetic evidence only."""
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
        "model_state": {"w": {"shape": [2], "dtype": "float32", "numel": 2, "values": [0.1, 0.2]}},
        "optimizer_state": {
            "param_groups": [{"lr": 0.001}],
            "state": {"0": {"exp_avg": [0.0, 0.0], "step": 1}},
        },
        "scheduler": {"last_epoch": 3},
        "microbatch_step": 4, "optimizer_step": 1, "update_count": 1,
        "rng": {"cpu": "c", "cuda": "g", "python": "p", "numpy": "n"},
        "rng_at_save": {"cpu": "saved"},
        "rng_at_restore": {"cpu": "saved"},
        "checkpoint_sha256": "CKPT",
        "resume_from_sha256": "CKPT",
    }

def run(a, b1, b2, c):
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        files = []
        for name, obj in (("A", a), ("B1", b1), ("B2", b2), ("C", c)):
            if obj is None:
                files.append(str(td / "missing.json"))
            else:
                p = td / f"{name}.json"
                p.write_text(json.dumps(obj))
                files.append(str(p))
        r = subprocess.run([sys.executable, str(SCRIPT), *files], capture_output=True, text=True)
        return r.returncode, r.stdout

def main():
    results = []
    A = base()
    B1 = base(); B1["batch_hashes"] = ["h0", "h1"]; B1["losses"] = [1.0, 1.1]
    B2 = base(); B2["batch_hashes"] = ["h2", "h3"]; B2["losses"] = [1.2, 1.3]
    C = base(); C["batch_hashes"] = ["h3"]; C["losses"] = [1.3]

    def check(name, expect, code, out):
        ok = (expect == "PASS" and code == 0) or (expect != "PASS" and code != 0 and f'"{expect}"' in out)
        results.append({"name": name, "expect": expect, "code": code, "ok": ok})

    check("identical", "PASS", *run(A, B1, B2, C))

    Bw = json.loads(json.dumps(B2)); Bw["model_state"]["w"]["values"] = [9.0, 9.0]
    check("weight_modified", "FAIL", *run(A, B1, Bw, C))

    Bo = json.loads(json.dumps(B2)); Bo["optimizer_state"]["state"]["0"]["exp_avg"] = [1.0, 1.0]
    check("optimizer_modified", "FAIL", *run(A, B1, Bo, C))

    check("missing_file", "MISSING", *run(A, B1, None, C))

    Bbad = json.loads(json.dumps(B2)); Bbad["batch_hashes"] = ["h2", "WRONG"]
    check("concat_mismatch", "FAIL", *run(A, B1, Bbad, C))

    check("C_skip", "PASS", *run(A, B1, B2, C))

    Csame = json.loads(json.dumps(B2))
    check("C_no_skip", "FAIL", *run(A, B1, B2, Csame))

    Blen = json.loads(json.dumps(B2)); Blen["model_state"]["w"]["values"] = [0.1]
    Blen["model_state"]["w"]["numel"] = 1
    check("length_mismatch", "FAIL", *run(A, B1, Blen, C))

    Bdt = json.loads(json.dumps(B2)); Bdt["model_state"]["w"]["dtype"] = "float16"
    check("dtype_mismatch", "FAIL", *run(A, B1, Bdt, C))

    Bnan = json.loads(json.dumps(B2)); Bnan["model_state"]["w"]["values"] = [0.1, float("nan")]
    check("nan", "FAIL", *run(A, B1, Bnan, C))

    Bmiss = json.loads(json.dumps(B2)); del Bmiss["optimizer_state"]["state"]["0"]["step"]
    check("opt_missing_field", "FAIL", *run(A, B1, Bmiss, C))

    Brng = json.loads(json.dumps(B2)); Brng["rng_at_restore"] = {"cpu": "OTHER"}
    check("rng_mismatch", "FAIL", *run(A, B1, Brng, C))

    Bnosha = json.loads(json.dumps(B2)); Bnosha["resume_from_sha256"] = None
    check("resume_sha_missing", "MISSING", *run(A, B1, Bnosha, C))

    failed = [r for r in results if not r["ok"]]
    print(json.dumps({"tests": results, "failed": len(failed), "source": "SYNTHETIC"}, indent=2))
    return 0 if not failed else 1

if __name__ == "__main__":
    sys.exit(main())
