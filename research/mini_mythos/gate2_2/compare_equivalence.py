"""
Compare A vs B2 vs C evidence. Does not run training.
Missing evidence → MISSING. Mismatch → FAIL. Not a MuonAdamW runtime PASS by itself.
"""
import json
import sys
from pathlib import Path

TOL_LOSS = 1e-4
TOL_WEIGHT = 1e-4


def load(path):
    p = Path(path)
    if not p.is_file():
        return None
    return json.loads(p.read_text())


def main():
    if len(sys.argv) < 3:
        print("usage: compare_equivalence.py A.json B2.json [C.json]")
        return 2
    a, b = load(sys.argv[1]), load(sys.argv[2])
    c = load(sys.argv[3]) if len(sys.argv) > 3 else None
    if a is None or b is None:
        print(json.dumps({"status": "MISSING", "detail": "A or B2 evidence file absent"}))
        return 2
    # expected keys
    required = ["batch_hashes", "losses", "optimizer_step", "microbatch_step", "update_count"]
    for name, obj in (("A", a), ("B2", b)):
        missing = [k for k in required if k not in obj]
        if missing:
            print(json.dumps({"status": "MISSING", "who": name, "keys": missing}))
            return 2
    hash_ok = a["batch_hashes"] == b["batch_hashes"]
    loss_ok = max(abs(x - y) for x, y in zip(a["losses"], b["losses"])) <= TOL_LOSS if len(a["losses"]) == len(b["losses"]) else False
    count_ok = a["update_count"] == b["update_count"] and a["optimizer_step"] == b["optimizer_step"]
    status = "PASS" if (hash_ok and loss_ok and count_ok) else "FAIL"
    out = {"status": status, "hash_ok": hash_ok, "loss_ok": loss_ok, "count_ok": count_ok, "muonadamw": "NOT TESTED unless evidence includes muon state"}
    if c is not None and "batch_hashes" in c:
        out["C_hash_differs"] = c["batch_hashes"] != a["batch_hashes"]
    print(json.dumps(out, indent=2))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
