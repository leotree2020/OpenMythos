"""Unit check of run_e2c.judgment_invalid (approved patch B), before the single
V4 re-run: calls the function on temporary judgment files only; no launcher."""
import json, os, sys, tempfile
sys.path.insert(0, sys.argv[1])
import run_e2c as R
T2 = "a" * 64
ok_doc = {"cond": "C1", "arm": "openmythos", "seed": 201, "set": "test2_heldout", "test2_sha256": T2, "main": {}}
cases = {"valid": (ok_doc, None),
         "wrong_seed": (dict(ok_doc, seed=202), "invalid"), "wrong_cond": (dict(ok_doc, cond="C2"), "invalid"),
         "wrong_arm": (dict(ok_doc, arm="transformer"), "invalid"), "wrong_set": (dict(ok_doc, set="test_heldout"), "invalid"),
         "wrong_test2_sha256": (dict(ok_doc, test2_sha256="b" * 64), "invalid"),
         "missing_test2_sha256": ({k: v for k, v in ok_doc.items() if k != "test2_sha256"}, "invalid"),
         "seed_as_string": (dict(ok_doc, seed="201"), "invalid")}
d = tempfile.mkdtemp(prefix="e2c_unit_")
res = {}
for name, (doc, want) in cases.items():
    p = os.path.join(d, name + ".json")
    json.dump(doc, open(p, "w"))
    got = R.judgment_invalid(p, "C1_openmythos_s201", T2)
    res[name] = {"returned": got, "expected": want, "pass": (got is None) == (want is None)}
p = os.path.join(d, "corrupt.json")
open(p, "w").write("{not json")
got = R.judgment_invalid(p, "C1_openmythos_s201", T2)
res["corrupt_file"] = {"returned": got, "expected": "invalid", "pass": got is not None}
res["all_pass"] = all(v["pass"] for v in res.values() if isinstance(v, dict))
json.dump(res, open(sys.argv[2], "w"), indent=1)
print(json.dumps(res, indent=1))
sys.exit(0 if res["all_pass"] else 3)
