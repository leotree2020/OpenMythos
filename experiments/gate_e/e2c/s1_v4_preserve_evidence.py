#!/usr/bin/env python3
"""
Before the approved V4 remediation (review of 575c5f8): preserve the original
F3 evidence. The two temporary case directories of the failed V4 case
judgment_without_ledger_recovered (development run, 10:48 UTC; gate-5 run,
14:46 UTC) are copied as they are into one tar.gz each (members sorted, original
modification times kept, gzip header mtime 0), with a per-file sha256
manifest; the committed failure records and the archived failure log are
listed with their sha256. The source directories are read only.
"""

import gzip
import hashlib
import io
import json
import os
import sys
import tarfile

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "stage1", "v4", "f3_evidence")
CASES = {"gate5_run_1446": "/tmp/e2c_v4_5ucpfqsu", "dev_run_1048": "/tmp/e2c_v4_1zv57iv_"}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    os.makedirs(OUT, exist_ok=True)
    man = {"cases": {}, "records": {}}
    for label, d in CASES.items():
        if not os.path.isdir(d):
            man["cases"][label] = {"source": d, "missing": True}
            continue
        files = sorted(os.path.relpath(os.path.join(r, f), d) for r, _, fs in os.walk(d) for f in fs)
        per = {f: {"sha256": sha(open(os.path.join(d, f), "rb").read()), "bytes": os.path.getsize(os.path.join(d, f)),
                   "mtime": os.path.getmtime(os.path.join(d, f))} for f in files}
        raw = io.BytesIO()
        with tarfile.open(fileobj=raw, mode="w", format=tarfile.PAX_FORMAT) as t:
            for f in files:
                t.add(os.path.join(d, f), arcname=os.path.join(os.path.basename(d), f), recursive=False)
        buf = io.BytesIO()
        with gzip.GzipFile(filename="", mode="wb", compresslevel=9, fileobj=buf, mtime=0) as g:
            g.write(raw.getvalue())
        dst = os.path.join(OUT, f"{label}_{os.path.basename(d)}.tar.gz")
        if os.path.exists(dst):
            sys.exit(f"REFUSED: {dst} exists; not overwritten")
        open(dst, "wb").write(buf.getvalue())
        with tarfile.open(dst, "r:gz") as t:  # read back: every member equals its source file
            back = {m.name.split("/", 1)[1]: sha(t.extractfile(m).read()) for m in t.getmembers() if m.isfile()}
        man["cases"][label] = {"source": d, "files": len(files), "bytes": sum(v["bytes"] for v in per.values()),
                               "archive": os.path.relpath(dst, HERE), "archive_sha256": sha(buf.getvalue()),
                               "archive_members_equal_sources": back == {f: v["sha256"] for f, v in per.items()}, "per_file": per}
    for rel in ("stage1/v4/launcher_tests.json", "stage1/v4/launcher_tests_dev_run_1037_1049.json", "stage1/gate5_V4.log",
                "stage1/log_archive/gate5_V4.log.gz", "stage1/gate5.json", "stage1/gate5/GATE5_REPORT.md"):
        p = os.path.join(HERE, rel)
        man["records"][rel] = sha(open(p, "rb").read()) if os.path.exists(p) else None
    json.dump(man, open(os.path.join(OUT, "MANIFEST_SHA256.json"), "w"), indent=1)
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "per_file"} for k, v in man["cases"].items()}, indent=1))
    print(json.dumps(man["records"], indent=1))


if __name__ == "__main__":
    main()
