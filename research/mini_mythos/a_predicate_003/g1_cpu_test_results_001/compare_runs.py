import json, sys
a = json.load(open("/tmp/g1_cpu_run1.json")); b = json.load(open("/tmp/g1_cpu_run2.json"))
def rows(j): return {r["id"]: r["status"] for g in j["groups"] for r in g["rows"]}
ra, rb = rows(a), rows(b)
out = {}
out["same_test_id_set"] = set(ra) == set(rb)
out["same_per_test_status"] = ra == rb
out["same_group_stats"] = [(g["group"], g["modules"], g["tests_run"], g["counts"], len(g["load_errors"])) for g in a["groups"]] == [(g["group"], g["modules"], g["tests_run"], g["counts"], len(g["load_errors"])) for g in b["groups"]]
ea, eb = dict(a["environment"]), dict(b["environment"])
for k in ("tmpdir",): ea.pop(k), eb.pop(k)
out["same_environment_except_tmpdir"] = ea == eb
out["same_checkout_identity_and_key_file_hashes"] = a["environment"]["checkout_identity"] == b["environment"]["checkout_identity"]
out["same_sentinel_record"] = a["sentinel_violations"] == b["sentinel_violations"] == []
out["same_acceptance_block"] = a["acceptance"] == b["acceptance"]
out["same_verdict"] = a["verdict"] == b["verdict"] == "PASS"
out["same_head"] = a["environment"]["git_head_actual"] == b["environment"]["git_head_actual"]
out["order_of_test_ids_identical"] = [r["id"] for g in a["groups"] for r in g["rows"]] == [r["id"] for g in b["groups"] for r in g["rows"]]
out["tests"] = len(ra)
out["ALL_CONSISTENT"] = all(v for k, v in out.items() if isinstance(v, bool))
print(json.dumps(out, indent=1))
sys.exit(0 if out["ALL_CONSISTENT"] else 1)
