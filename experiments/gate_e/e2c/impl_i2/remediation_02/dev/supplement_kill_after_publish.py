"""I2-R2 supplementary development check (synthetic test repository only, not part of the formal suite): the driver is
SIGKILLed after both verify files are published and before the ledger interval closes. Expected: no PASS anywhere;
freeze refuses (with and without accepting the stale supplement); verify --resume refuses; no process left."""
import json, os, sys, time
HERE = sys.argv[1]
sys.path.insert(0, HERE)
import e2c_stage2_tests as T

print(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "code", {f: T.sha(os.path.join(HERE, f))[:12] for f in ("e2c_stage2.py", "e2c_stage2_tests.py")})
d = T.make_env()
T.set_cfg(d, cap_seconds=300, stub_delay_before_final_write={"verify_before_close": 60})
p = T.popen_verify(d)
rp = os.path.join(d, "stage2", "stage2_verify.json")
T.wait_for(lambda: os.path.exists(rp), 120)
time.sleep(2.0)
p.kill()
p.communicate(timeout=60)
iv = T.ledger(d)["intervals"][0]
att = os.path.join(d, "stage2", "attempts", "01")
res = {"driver_exit": p.returncode, "record_published": os.path.exists(rp),
       "interval_1": {k: iv.get(k) for k in ("status", "end", "published", "status_before_close")},
       "summary_written": os.path.exists(os.path.join(att, "summary.json")),
       "review_record": T.review_state(d)}
T.set_cfg(d, stub_delay_before_final_write=None)
vc, vs = T.approve_verify(d)  # even if a reviewer committed it as it stands
r = T.freeze(d, vc, vs)
res["freeze"] = (r.returncode, T.tail(r, 1000))
r = T.freeze(d, vc, vs, extra=("--accept-stale-supplement",))
res["freeze_accept_stale"] = (r.returncode, T.tail(r, 1000))
r = T.verify(d, resume=True, accept_stale=True)
res["resume_accept_stale"] = (r.returncode, T.tail(r, 1000))
res["freeze_written"] = os.path.exists(os.path.join(d, "e2c_workload_freeze.json"))
res["left_processes"] = T.leftover_processes(d)
ok = (res["driver_exit"] == -9 and res["record_published"] and res["interval_1"]["end"] is None and not res["interval_1"]["published"]
      and not res["summary_written"] and res["freeze"][0] == 5 and res["freeze_accept_stale"][0] == 5
      and "exactly one launch that published" in res["freeze_accept_stale"][1] and res["resume_accept_stale"][0] == 5
      and not res["freeze_written"] and not res["left_processes"])
print(json.dumps(res, indent=1, ensure_ascii=False))
print("SUPPLEMENT", "PASS" if ok else "FAIL")
T.drop(d)
