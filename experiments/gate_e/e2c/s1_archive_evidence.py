#!/usr/bin/env python3
"""
Administrative evidence supplement after the gate-4 review of 216f66a (no
experiment is run; no original file is changed or removed).

The repository's root .gitignore ignores every directory named "runs" (line
25) and every directory named "logs" (line 65), so gate 4's run records
(stage1/gate4/runs/) and the job logs of gates 1-4 never entered a commit.

    A  the 30 gate-4 run records: completeness (parseable, complete, the
       run's own condition / arm / seed / lambda / length, one value per
       update in every per-update series, no non-finite marker, no leftover
       progress file, the job ended with exit 0 in gate4_stdout.log and its
       log says "saved"), then a deterministic gzip copy (mtime 0, no file
       name in the header, level 9) in stage1/gate4/run_archive/; every copy
       is decompressed again and must equal the original bytes
    B  from the raw r_u of those records: E_W = sum_{u<=300} r_u^2 of the 6
       C1 runs at the selected lambda and the 6 C2 runs, the 4 means over the
       seeds and the 2 lambda2, recomputed (i) with the same float operations
       as s1_gate4.py (must be bitwise equal to calibration.json) and (ii)
       with math.fsum (agreement stated as a relative difference); the clip
       shares and E_W after clipping per seed as well
    C  the job and stdout logs of gates 1-4 (same archival gap): the same
       deterministic gzip copies in stage1/log_archive/ with flattened names
       (a path component "logs" would be ignored again)
Writes the manifests run_archive/MANIFEST_SHA256.json (and .txt),
log_archive/MANIFEST_SHA256.json and stage1/gate4/evidence_check.json.
Exit 0 only if A and B pass; 3 otherwise (nothing is rebuilt or overwritten).
"""

import glob
import gzip
import hashlib
import io
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
S1 = os.path.join(HERE, "stage1")
G4 = os.path.join(S1, "gate4")
ARMS = ("openmythos", "transformer")
SEEDS = (91, 92, 93)
LAMS = (0.03, 0.1, 0.3, 1.0)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def gz(data):
    buf = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", compresslevel=9, fileobj=buf, mtime=0) as f:
        f.write(data)
    return buf.getvalue()


def tag(lam):
    return str(lam).replace(".", "p")


def archive(src_files, dst_dir, name_of):
    os.makedirs(dst_dir, exist_ok=True)
    rows = []
    for src in src_files:
        data = open(src, "rb").read()
        z = gz(data)
        dst = os.path.join(dst_dir, name_of(src))
        if os.path.exists(dst):
            if open(dst, "rb").read() != z:
                raise SystemExit(f"REFUSED: {dst} exists with other content; not overwritten")
        else:
            with open(dst, "wb") as f:
                f.write(z)
        back = gzip.decompress(open(dst, "rb").read())
        rows.append({"original": os.path.relpath(src, HERE), "original_sha256": sha(data), "original_bytes": len(data),
                     "archive": os.path.relpath(dst, HERE), "archive_sha256": sha(z), "archive_bytes": len(z),
                     "decompressed_equals_original": back == data})
    return rows


def main():
    log = open(os.path.join(S1, "gate4_stdout.log")).read()
    expected = [f"C1_{a}_s{s}_lam{tag(l)}" for a in ARMS for l in LAMS for s in SEEDS]
    cal = json.load(open(os.path.join(G4, "calibration.json")))
    sel = cal["selection_summary"]["selected_lambda"]
    expected += [f"C2_{a}_s{s}_lam{tag(sel[a])}" for a in ARMS for s in SEEDS]
    present = sorted(os.path.basename(p)[:-5] for p in glob.glob(os.path.join(G4, "runs", "*.json")))
    res = {"A_completeness": {}, "expected_runs": len(expected), "present_files": len(present),
           "missing": sorted(set(expected) - set(present)), "unexpected": sorted(set(present) - set(expected)),
           "progress_files_left": sorted(os.path.basename(p) for p in glob.glob(os.path.join(G4, "runs", "*.progress.json")))}
    recs = {}
    for name in expected:
        p = os.path.join(G4, "runs", f"{name}.json")
        if not os.path.exists(p):
            continue
        r = json.load(open(p))
        recs[name] = r
        cond, arm, s, lt = name.split("_")
        lam = float(lt[3:].replace("p", "."))
        n = r.get("steps")
        series = {k: len(r.get(k) or []) for k in ("loss_every_step", "r_u", "kappa_u", "aux_loss_every_step")}
        joblog = os.path.join(G4, "logs", f"train_{name}.log")
        c = {"complete": r.get("complete") is True, "cond": r.get("cond") == cond, "arm": r.get("arm") == arm,
             "seed": r.get("seed") == int(s[1:]), "lam": r.get("lam") == lam,
             "steps": n == (3000 if cond == "C1" else 300), "series_lengths": all(v == n for v in series.values()),
             "no_nonfinite_marker": "nonfinite_at" not in r,
             "all_values_finite": all(math.isfinite(v) for k in series for v in r[k]),
             "E_W_present": isinstance(r.get("E_W"), float), "final_param_sha256_present": bool(r.get("final_param_sha256")),
             "job_exit_0_in_gate4_log": f"end train_{name} rc=0" in log,
             "job_log_saved": os.path.exists(joblog) and "saved" in open(joblog).read()}
        res["A_completeness"][name] = {"checks": c, "series_lengths": series, "pass": all(c.values())}
    a_pass = (not res["missing"] and not res["unexpected"] and not res["progress_files_left"] and len(recs) == 30
              and all(v["pass"] for v in res["A_completeness"].values()))
    res["A_pass"] = a_pass
    if not a_pass:
        json.dump(res, open(os.path.join(G4, "evidence_check.json"), "w"), indent=1)
        print("STOP: run records missing or incomplete; nothing archived")
        sys.exit(3)
    rows = archive([os.path.join(G4, "runs", f"{n}.json") for n in expected], os.path.join(G4, "run_archive"),
                   lambda src: os.path.basename(src) + ".gz")
    man = {"gzip": "python gzip, compresslevel 9, mtime 0, empty file name in the header (deterministic)",
           "reason": "root .gitignore line 25 ('runs') ignores stage1/gate4/runs/; originals left in place, unchanged",
           "files": rows}
    json.dump(man, open(os.path.join(G4, "run_archive", "MANIFEST_SHA256.json"), "w"), indent=1)
    with open(os.path.join(G4, "run_archive", "MANIFEST_SHA256.txt"), "w") as f:
        f.write("original_file\toriginal_sha256\toriginal_bytes\tarchive_file\tarchive_sha256\tarchive_bytes\n")
        for x in rows:
            f.write(f"{x['original']}\t{x['original_sha256']}\t{x['original_bytes']}\t{x['archive']}\t{x['archive_sha256']}\t{x['archive_bytes']}\n")
    res["A_archive"] = {"files": len(rows), "all_decompress_equal": all(x["decompressed_equals_original"] for x in rows),
                        "original_bytes": sum(x["original_bytes"] for x in rows), "archive_bytes": sum(x["archive_bytes"] for x in rows)}
    # B: independent recomputation
    b = {}
    ok = True
    for arm in ARMS:
        lam = sel[arm]
        c2 = cal["lambda2_calibration"][arm]
        e1 = {s: recs[f"C1_{arm}_s{s}_lam{tag(lam)}"]["r_u"][:300] for s in SEEDS}
        e2 = {s: recs[f"C2_{arm}_s{s}_lam{tag(lam)}"]["r_u"][:300] for s in SEEDS}
        same = {s: sum(v * v for v in e1[s]) for s in SEEDS}  # the arithmetic of train_e2c.progress
        same2 = {s: sum(v * v for v in e2[s]) for s in SEEDS}
        fs1 = {s: math.fsum(v * v for v in e1[s]) for s in SEEDS}
        fs2 = {s: math.fsum(v * v for v in e2[s]) for s in SEEDS}
        m1, m2 = sum(same.values()) / 3, sum(same2.values()) / 3  # the arithmetic of s1_gate4.lambda2
        raw = lam * math.sqrt(m1 / m2)
        l2 = min(max(raw, lam / 10), 10 * lam)
        fm1, fm2 = math.fsum(fs1.values()) / 3, math.fsum(fs2.values()) / 3
        fl2 = lam * math.sqrt(fm1 / fm2)
        rel = lambda a, x: abs(a - x) / abs(x)  # noqa: E731
        checks = {
            "E_W_C1_per_seed_bitwise_vs_calibration": all(same[s] == c2["E_W_C1_per_seed"][str(s)] for s in SEEDS),
            "E_W_C2_per_seed_bitwise_vs_calibration": all(same2[s] == c2["E_W_C2_at_lambda_per_seed"][str(s)] for s in SEEDS),
            "E_W_bitwise_vs_run_record_field": all(same[s] == recs[f"C1_{arm}_s{s}_lam{tag(lam)}"]["E_W"] and
                                                   same2[s] == recs[f"C2_{arm}_s{s}_lam{tag(lam)}"]["E_W"] for s in SEEDS),
            "mean_E_W_C1_bitwise": m1 == c2["mean_E_W_C1"], "mean_E_W_C2_bitwise": m2 == c2["mean_E_W_C2"],
            "lambda2_unclipped_bitwise": raw == c2["lambda2_unclipped"], "lambda2_bitwise": l2 == c2["lambda2"],
            "lambda2_bitwise_vs_lambda_selected_json": l2 == json.load(open(os.path.join(G4, "lambda_selected.json")))["lambda2"][arm],
            "at_bound_same": (raw <= lam / 10 or raw >= 10 * lam) == c2["at_bound"],
            "clip_share_W_per_seed_equal": all(sum(k < 1.0 for k in recs[f"{c}_{arm}_s{s}_lam{tag(lam)}"]["kappa_u"][:300]) / 300
                                               == c2[f"clip_share_W_{c}"][str(s)] for c in ("C1", "C2") for s in SEEDS),
            "E_W_after_clip_per_seed_equal": all(sum((v * k) ** 2 for v, k in zip(recs[f"{c}_{arm}_s{s}_lam{tag(lam)}"]["r_u"][:300],
                                                                                   recs[f"{c}_{arm}_s{s}_lam{tag(lam)}"]["kappa_u"][:300]))
                                                 == c2[f"E_W_after_clip_{c}"][str(s)] for c in ("C1", "C2") for s in SEEDS)}
        b[arm] = {"lambda": lam, "E_W_C1_per_seed": same, "E_W_C2_per_seed": same2, "mean_E_W_C1": m1, "mean_E_W_C2": m2,
                  "lambda2_unclipped": raw, "lambda2": l2,
                  "fsum_check": {"mean_E_W_C1": fm1, "mean_E_W_C2": fm2, "lambda2": fl2,
                                 "max_rel_diff_per_seed": max(max(rel(same[s], fs1[s]), rel(same2[s], fs2[s])) for s in SEEDS),
                                 "rel_diff_lambda2": rel(l2, fl2)},
                  "checks": checks, "pass": all(checks.values()) and rel(l2, fl2) < 1e-12}
        ok = ok and b[arm]["pass"]
    res["B_recomputation"] = b
    res["B_pass"] = ok
    # C: logs of gates 1-4 (same archival gap)
    logs = sorted(glob.glob(os.path.join(S1, "gate*", "logs", "*.log")) + glob.glob(os.path.join(S1, "*.log"))
                  + glob.glob(os.path.join(S1, "dev", "*.log")))
    lrows = archive(logs, os.path.join(S1, "log_archive"), lambda src: os.path.relpath(src, S1).replace("/", "__") + ".gz")
    json.dump({"gzip": man["gzip"], "reason": "root .gitignore ignores directories named 'logs' (line 65) and these log files; "
               "originals left in place, unchanged; names flattened so no path component is 'logs'", "files": lrows},
              open(os.path.join(S1, "log_archive", "MANIFEST_SHA256.json"), "w"), indent=1)
    res["C_logs"] = {"files": len(lrows), "all_decompress_equal": all(x["decompressed_equals_original"] for x in lrows),
                     "by_dir": {d: sum(x["original"].startswith(f"stage1/{d}") for x in lrows)
                                for d in ("gate1/logs", "gate2/logs", "gate3/logs", "gate4/logs", "dev/")},
                     "stdout_logs": [x["original"] for x in lrows if x["original"].count("/") == 1]}
    res["pass"] = res["A_pass"] and res["A_archive"]["all_decompress_equal"] and res["B_pass"] and res["C_logs"]["all_decompress_equal"]
    json.dump(res, open(os.path.join(G4, "evidence_check.json"), "w"), indent=1)
    print(json.dumps({"A": [res["A_pass"], res["A_archive"]], "B": {a: [b[a]["pass"], b[a]["lambda2"], b[a]["fsum_check"]["rel_diff_lambda2"]]
                                                                     for a in ARMS}, "C": res["C_logs"], "pass": res["pass"]}, indent=1))
    sys.exit(0 if res["pass"] else 3)


if __name__ == "__main__":
    main()
