"""Read-only post-run checks of the formal stage-2 verify (no key space enumeration, no stream regeneration: the
recorded chains are compared with the committed stage-1 records)."""
import glob, gzip, hashlib, json, os, re, subprocess, sys, time
E = "/home/user/OpenMythos/experiments/gate_e/e2c"
RUN = os.path.dirname(os.path.abspath(__file__))
S2 = os.path.join(E, "stage2")
KEY_LIKE = re.compile(r"[A-Za-z]=[0-9];[A-Za-z]=[0-9]")
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()  # noqa: E731
print("# post-run checks", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
rec_launch = dict(l.split(" ", 1) for l in open(os.path.join(RUN, "launch_record.txt")).read().splitlines() if " " in l)
print("launch:", {k: rec_launch.get(k) for k in ("start_utc", "driver_pid", "end_utc", "exit_code")})
print("## files in stage2/ (path, bytes, sha256)")
files = sorted(os.path.join(r, f) for r, _, fs in os.walk(S2) for f in fs)
for f in files:
    print(f"  {os.path.relpath(f, S2)} {os.path.getsize(f)} {sha(f)}")
att = os.path.join(S2, "attempts", "01")
sm = json.load(open(os.path.join(att, "summary.json")))
print("## summary.json", json.dumps(sm, sort_keys=True))
led = json.load(open(os.path.join(S2, "budget_ledger_s2.json")))
print("## ledger: used_seconds", led.get("used_seconds"), "cap", led.get("cap_seconds"), "supplements", led.get("supplements"),
      "stale_reports", led.get("stale_reports"))
for iv in led["intervals"]:
    print("  interval", json.dumps(iv, sort_keys=True))
rp, sp = os.path.join(S2, "stage2_verify.json"), os.path.join(S2, "v2_streams.json")
rec = json.load(open(rp)) if os.path.exists(rp) else None
print("## outputs: stage2_verify.json", os.path.exists(rp) and sha(rp), "| v2_streams.json", os.path.exists(sp) and sha(sp))
if rec:
    print("  record status", rec["status"], "mode", rec["mode"], "reviewed_commit", rec["reviewed_commit"])
    print("  basis code_tree", rec["basis"]["code_tree_sha256"], "prereg", rec["basis"]["preregistration_sha256"][:16],
          "design", rec["basis"]["design_review_sha256"][:16], "manifest", rec["basis"]["sets_manifest_sha256"][:16])
    print("  code changes", rec["code_changes_since_stage1"])
    print("  environment", rec["environment"])
    print("  inputs", rec["inputs"])
    print("  e1_sets manifest", rec["e1_sets"]["manifest_sha256"], "files", len(rec["e1_sets"]["files"]))
    print("  appendix_a", rec["appendix_a"])
    print("  keyspace", rec["keyspace"])
    print("  f11", rec["f11"])
    print("  key_rules", rec["key_rules"])
    v2 = {k: v for k, v in rec["v2"].items()}
    print("  v2", json.dumps(v2, sort_keys=True))
    print("  leak_scan", rec["leak_scan"])
    iv = led["intervals"][-1]
    print("  sha consistency: record = summary", sha(rp) == sm.get("record_sha256"), "| record = ledger.published",
          sha(rp) == (iv.get("published") or {}).get("stage2_verify.json"), "| streams = record.v2.streams_sha256",
          sha(sp) == rec["v2"]["streams_sha256"], "| streams = summary", sha(sp) == sm.get("v2_streams_sha256"),
          "| streams = ledger.published", sha(sp) == (iv.get("published") or {}).get("v2_streams.json"))
    st = json.load(open(sp))
    print("## V2 per seed (seed: updates x batch, accepted, held-out, chain points logged, first batch)")
    for s in sorted(st, key=int):
        r = st[s]
        print(f"  {int(s):3d}: {r['updates']} x {r['batch']}, {r['accepted_samples']}, {r['heldout_hits']}, {len(r['batch_chain'])}, "
              f"{r['first_batch_sha256'][:16]}")
    print("  seeds", len(st), "all 12000 x 64 = 768000 and 0 held-out:",
          all((r["updates"], r["batch"], r["accepted_samples"], r["heldout_hits"]) == (12000, 64, 768000, 0) for r in st.values()))
    # independent comparison with the committed stage-1 reference records (read-only)
    globs = ("stage1/gate1/*.json", "stage1/gate2/r2/*.json", "stage1/gate3/run_*.json", "stage1/gate4/run_archive/*.json.gz", "stage1/v3/*.json")
    n = mism = refs = fb = 0
    for g in globs:
        for f in sorted(glob.glob(os.path.join(E, g))):
            raw = open(f, "rb").read()
            d = json.loads(gzip.decompress(raw) if f.endswith(".gz") else raw)
            if not (isinstance(d, dict) and d.get("batch_chain")):
                continue
            refs += 1
            mine = st[str(d["seed"])]
            for u, cv in d["batch_chain"].items():
                n += 1
                mism += mine["batch_chain"].get(u) != cv
            fb += d.get("first_batch_sha256") == mine["first_batch_sha256"]
    print(f"## stage-1 chains (independent re-comparison): {refs} records, {n} points, {mism} mismatches, first batch equal {fb}/{refs}")
print("## stop / review records:", {n: os.path.exists(os.path.join(S2, n)) for n in
                                     ("verify_stop.json", "budget_review_required.json", "budget_review_required_freeze.json")})
print("## freeze, salt, test2 files:", [p for p in glob.glob(os.path.join(E, "**", "*"), recursive=True)
                                        if re.search(r"(workload_freeze\.json|salt|test2_heldout)", os.path.basename(p))
                                        and "/stage1/" not in p] or "none")
hits = {}
for f in files + [os.path.join(RUN, "verify_console.txt"), os.path.join(RUN, "launch_record.txt")]:
    c = len(KEY_LIKE.findall(open(f, "rb").read().decode("utf-8", "replace")))
    if c:
        hits[os.path.relpath(f, E)] = c
print("## leak scan (key-like text) over stage2/ and the console:", hits or f"0 hits in {len(files) + 2} files")
left = []
for x in os.listdir("/proc"):
    if x.isdigit() and int(x) != os.getpid():
        try:
            cl = open(f"/proc/{x}/cmdline", "rb").read()
            if b"e2c_stage2" in cl or b"_v2-worker" in cl or b"e2c_stage4" in cl or b"keyspace.py" in cl:
                left.append((int(x), cl.replace(b"\0", b" ")[:100].decode()))
        except OSError:
            pass
print("## processes left:", left or "none")
print("## timing: ledger interval start", led["intervals"][-1].get("start_utc"), "end", led["intervals"][-1].get("end_utc"),
      "| summary.json written", time.strftime("%H:%M:%S", time.gmtime(os.path.getmtime(os.path.join(att, "summary.json")))),
      "| driver_log last write", time.strftime("%H:%M:%S", time.gmtime(os.path.getmtime(os.path.join(att, "driver_log.txt")))),
      "| process end (launch record)", rec_launch.get("end_utc"))
end = led["intervals"][-1].get("end")
if end:
    print(f"  after the ledger closed: summary.json +{os.path.getmtime(os.path.join(att, 'summary.json')) - end:.3f} s, "
          f"driver_log +{os.path.getmtime(os.path.join(att, 'driver_log.txt')) - end:.3f} s")
print("## git status:")
print(subprocess.run(["git", "status", "--porcelain", "--untracked-files=normal"], cwd=E, capture_output=True, text=True,
                     env=dict(os.environ, GIT_OPTIONAL_LOCKS="0")).stdout.strip())
