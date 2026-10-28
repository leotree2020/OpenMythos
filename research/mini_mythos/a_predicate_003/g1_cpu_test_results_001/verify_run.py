import ast, glob, json, os, sys, collections
f = sys.argv[1]
j = json.load(open(f))
A = "tests"
exp = []
for p in sorted(glob.glob(os.path.join(A, "test_g1_*.py"))):
    mod = os.path.basename(p)[:-3]
    for c in ast.parse(open(p).read()).body:
        if isinstance(c, ast.ClassDef):
            exp += ["%s.%s.%s" % (mod, c.name, m.name) for m in c.body if isinstance(m, ast.FunctionDef) and m.name.startswith("test_")]
rows = [r for g in j["groups"] for r in g["rows"]]
ids = [r["id"] for r in rows]
st = collections.Counter(r["status"] for r in rows)
env = j["environment"]; ci = env["checkout_identity"]
checks = {
 "expected_unique_289": len(set(exp)) == 289 == len(exp),
 "executed_rows_289": len(rows) == 289,
 "ids_unique": len(set(ids)) == len(ids),
 "ids_equal_expected_set": set(ids) == set(exp),
 "all_PASS": st == {"PASS": 289},
 "no_FAIL_ERROR_SKIP_XFAIL_XPASS": not any(st.get(k) for k in ("FAIL", "ERROR", "SKIP", "XFAIL", "XPASS")),
 "load_errors_0": sum(len(g["load_errors"]) for g in j["groups"]) == 0,
 "sentinel_violations_0": j["sentinel_violations"] == [],
 "verdict_PASS": j["verdict"] == "PASS",
 "acceptance_FULL_PASS": j["acceptance"]["verdict"] == "PASS" and j["acceptance"]["acceptance_scope"] == "FULL" and j["acceptance"]["exit_code"] == 0,
 "acceptance_numbers": (j["acceptance"]["expected_total"], j["acceptance"]["executed_unique"], j["acceptance"]["pass_unique"], j["acceptance"]["missing_ids"], j["acceptance"]["unexpected_ids"], j["acceptance"]["duplicate_ids"]) == (289, 289, 289, [], [], []),
 "three_groups_full": [g["group"] for g in j["groups"]] == ["g1_judge_cases", "g2_auth_preflight_pipeline", "g3_boundaries_mutations_acceptance"],
 "head_matches_expected": env["git_head_actual"] == env["git_sha_expected"] == "d1" + "75a1ab89c521ec78de9fa39fb139a0e20b1788" and env["git_sha_match"] is True,
 "checkout_identity_ok": ci["ok"] is True and ci["problems"] == [],
 "bench_hash": ci["bench_code_sha256"] == "b6f52a8c1f62cf94be2591c681dc42f10f5741a901fff968d66ed8b35425d3b0",
 "gpu_unused": env["gpu_used"] is False,
}
print(f, "status counts", dict(st), "groups", [(g["group"], g["tests_run"], g["counts"]) for g in j["groups"]])
for k, v in checks.items():
    print(("OK   " if v else "FAIL ") + k)
print("ALL CONDITIONS:", all(checks.values()))
