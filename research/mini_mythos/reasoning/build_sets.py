#!/usr/bin/env python3
"""Generate the reasoning probe sets (deterministic): dev = seed 1, 200 items per cell; test = seed 2,
300 items per cell. Every answer is re-derived by the independent solver; any mismatch aborts.

  python build_sets.py --out reasoning_sets.jsonl [--check MANIFEST.json]

Writes OUT and OUT with .manifest.json (sha256, counts). With --check, exits 1 unless the sha256
equals the one in MANIFEST.json (the committed manifest).
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import tasks as T  # noqa: E402

SPLITS = {"dev": (1, 200), "test": (2, 300)}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", required=True)
    p.add_argument("--check")
    args = p.parse_args()
    lines, counts = [], {}
    for split, (seed, n) in SPLITS.items():
        for it in T.build(seed, n):
            if T.solve(it) != it["answer"]:
                raise SystemExit("solver disagrees with generator on %s/%s" % (split, it["id"]))
            it = dict(it, split=split, id="%s-%s" % (split, it["id"]))
            lines.append(json.dumps(it, sort_keys=True))
            counts[split] = counts.get(split, 0) + 1
    data = ("\n".join(lines) + "\n").encode("utf-8")
    Path(args.out).write_bytes(data)
    man = {"sha256": hashlib.sha256(data).hexdigest(), "counts": counts, "levels": T.LEVELS, "shots": T.SHOTS,
           "splits": {k: {"seed": s, "per_cell": n} for k, (s, n) in SPLITS.items()}}
    Path(args.out + ".manifest.json").write_text(json.dumps(man, indent=1, sort_keys=True) + "\n")
    print(json.dumps(man))
    if args.check:
        want = json.loads(Path(args.check).read_text())["sha256"]
        if want != man["sha256"]:
            print("REASONING SETS DIFFER FROM THE COMMITTED MANIFEST", file=sys.stderr)
            return 1
        print("reasoning sets identical to the committed manifest")
    return 0


if __name__ == "__main__":
    sys.exit(main())
