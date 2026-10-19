#!/usr/bin/env python3
"""
Determinism of the diagnostics (PREREGISTRATION 12.4.2): the resumable
launcher requires a re-diagnosed state to equal the result it replaces. The
same non-formal state (seed 99, K=2, 500 steps, both arms) was diagnosed twice
by independent processes (--a, --b result directories, level-0 workload).
Compares the result content without the timing fields ("seconds",
"M5.seconds"); writes validation/determinism.json, exits non-zero if any
content differs.
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from run_gate_e import result_digest, sha256_file  # noqa: E402


def first_difference(a, b, path=""):
    if type(a) is not type(b):
        return path or "/"
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k in ("seconds",):
                continue
            if k not in a or k not in b:
                return f"{path}/{k}"
            d = first_difference(a[k], b[k], f"{path}/{k}")
            if d:
                return d
        return None
    if isinstance(a, list):
        if len(a) != len(b):
            return path
        for i, (x, y) in enumerate(zip(a, b)):
            d = first_difference(x, y, f"{path}[{i}]")
            if d:
                return d
        return None
    return None if a == b else path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    args = ap.parse_args()
    out, ok = {}, True
    for fn in sorted(os.listdir(args.a)):
        if not fn.endswith(".json"):
            continue
        pa, pb = os.path.join(args.a, fn), os.path.join(args.b, fn)
        da, db = result_digest(pa), result_digest(pb)
        diff = None if da == db else first_difference(json.load(open(pa)), json.load(open(pb)))
        out[fn] = {"content_equal": da == db, "digest": da, "file_sha256_equal": sha256_file(pa) == sha256_file(pb),
                   "first_difference": diff}
        ok &= da == db
    res = {"states": out, "pass": ok and bool(out),
           "note": "file bytes differ only through the timing fields; content compared without them"}
    with open(os.path.join(HERE, "validation", "determinism.json"), "w") as f:
        json.dump(res, f, indent=1)
    print(json.dumps(res, indent=1))
    sys.exit(0 if res["pass"] else 1)


if __name__ == "__main__":
    main()
