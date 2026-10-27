"""Acceptance summary of one guarded unittest run (reads only the saved raw files).  usage: summarize.py NAME OUTPUT EXITCODE GUARD_JSON"""
import json, re, sys
name, out_p, rc_p, guard_p = sys.argv[1:5]
out = open(out_p).read()
rc = int(open(rc_p).read().strip())
g = json.load(open(guard_p))
m = re.search(r"^Ran (\d+) tests? in", out, re.M)
ran = int(m.group(1)) if m else 0
ok_lines = len(re.findall(r"\.\.\. ok$", out, re.M))
skips = len(re.findall(r"\.\.\. skipped", out, re.M))
fails = len(re.findall(r"\.\.\. FAIL$", out, re.M))
errs = len(re.findall(r"\.\.\. ERROR$", out, re.M))
loader_failed = "_FailedTest" in out
final = "OK" if re.search(r"^OK", out, re.M) else ("FAILED" if "FAILED" in out else "NO-FINAL-LINE")
viol = len(g.get("violations", []))
status = "PASS" if (rc == 0 and ran > 0 and ok_lines + skips == ran and fails == 0 and errs == 0 and not loader_failed and final == "OK" and viol == 0) else "FAIL/BLOCKED"
res = {"file": name, "exit_code": rc, "tests_run": ran, "pass": ok_lines, "fail": fails, "error": errs, "skip": skips, "loader_failures": loader_failed,
       "final_line": final, "guard_violations": viol, "status_by_acceptance_rule": status}
json.dump(res, open(out_p.replace(".output.txt", ".summary.json"), "w"), indent=1)
print(json.dumps(res))
sys.exit(0 if status == "PASS" else 1)
