import json,subprocess,traceback
from pathlib import Path
f=Path("/workspaces/mythos-evidence/base_v01/moda_fresh");p=Path("/workspaces/mythos-moda-fresh-cpu-v1/research/mini_mythos/base_v01/moda_fresh_v1");python="/workspaces/mythos-depth-data-cpu312/bin/python";freeze="d91f5d30675a9d76480cd89503bd7e3cb2ba0d92"
r={"Purpose":"Single independent train/history audit after complete preparation","Input":{"freeze":freeze},"Expected":{"helpers":27,"model_calls":0},"Actual":{"model_calls":0},"Status":"NOT TESTED"}
try:
 t=f/"specification-v6/AUDIT_TARGET_HELPERS.json";q=subprocess.run([python,"-I","-B",str(p/"test_audit_history_v6.py"),"--report",str(t)]);x=json.loads(t.read_bytes());a=x["Actual"];assert q.returncode==0 and x["Status"]=="PASS" and a.get("run",a.get("tests_run"))==27 and all(a.get(k,0) in (0,[]) for k in ("failures","errors","skipped"));r["Actual"]["helpers_passed"]=27
 c=[python,"-I","-B",str(p/"audit_history_v6.py"),"--expected-head",freeze,"--expected-spec-sha","906581f9c2069f184a9d04f6ab3d343e60e8ed44223d07552cbf7a5bf7cd5d8d","--expected-gate-sha","619e50cb2cc58e4a836f5c24058b5cffe2f9db66f1e6d2dc230134f2c2062de9","--expected-prep-sha","90f71856ad785cfaeb873e1c00070d9d2b55cb6880fafb799a40cca3e08dbfb0","--output",str(f/"specification-v6/audit_history_v6.json")];print("FORMAL_INDEPENDENT_AUDIT_START",json.dumps(c),flush=True);q=subprocess.run(c);x=json.loads((f/"specification-v6/audit_history_v6.json").read_bytes());r["Status"]=x["Status"];r["Actual"]["audit_exit"]=q.returncode;r["Actual"]["check_counts"]=x.get("check_counts")
except BaseException as e:r["Status"]="FAIL";r["error"]={"type":type(e).__name__,"message":str(e),"traceback":traceback.format_exc()}
finally:
 with (f/"specification-v6/AUDIT_CONTROL_V6.json").open("x") as z:json.dump(r,z,indent=2);z.write(chr(10))
 print("AUDIT_CONTROL_FINAL",json.dumps(r),flush=True)
