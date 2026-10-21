"""Read-only: the stage-2 ledger in the working tree equals the committed one (accepted verify commit e79acc6) and holds
exactly the closed PASS verify interval, with caps of 3600 s, no supplement and no stale report. Exit 0 only when so;
a failed git command or an unreadable ledger is a failure (exit 1), never a pass."""
import json, subprocess, sys
REPO, C = "/home/user/OpenMythos", "e79acc6e7a39e1ec4e720d9a66ec05bc8848f150"
P = "experiments/gate_e/e2c/stage2/budget_ledger_s2.json"
try:
    r = subprocess.run(["git", "show", f"{C}:{P}"], cwd=REPO, capture_output=True)
    if r.returncode:
        raise RuntimeError(f"git show {C[:12]}:{P} failed (exit {r.returncode}): {r.stderr.decode(errors='replace').strip()[:300]}")
    committed = r.stdout
    now = open(f"{REPO}/{P}", "rb").read()
    d = json.loads(now)
    iv = d["intervals"]
    checks = {
        "working-tree ledger byte-equal to the committed one": now == committed,
        "exactly one interval": len(iv) == 1,
        "interval 1: verify, PASS, closed": iv[0]["label"] == "verify" and iv[0]["status"] == "PASS" and iv[0]["end"] is not None,
        "caps: top level and interval 1 are 3600 s": d["cap_seconds"] == 3600.0 and iv[0]["cap_seconds"] == 3600.0,
        "interval 1 used_seconds_at_end 113.33917 < 3600": iv[0]["used_seconds_at_end"] == 113.33917 < 3600,
        "no supplement, no stale report, no review interval": d.get("supplements") == [] and "stale_reports" not in d
        and all(x["status"] != "BUDGET_CAP_REVIEW_REQUIRED" for x in iv),
        "interval 1 published the accepted record": iv[0].get("published", {}).get("stage2_verify.json")
        == "6331b06a73071c1a8d464a96fe47c4c8499bf1456e0c1f87dfbfbee16611564a",
    }
except Exception as e:  # noqa: BLE001
    print(f"FAIL ledger: check could not be completed: {e}")
    sys.exit(1)
for k, v in checks.items():
    print(("PASS " if v else "FAIL ") + "ledger: " + k)
print(f"ledger: remaining {3600 - iv[0]['used_seconds_at_end']:.6f} s of the shared stage-2 cap")
sys.exit(0 if all(checks.values()) else 1)
