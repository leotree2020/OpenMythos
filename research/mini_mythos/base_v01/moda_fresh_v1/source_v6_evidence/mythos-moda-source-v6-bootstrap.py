import json,subprocess,traceback,sys
from pathlib import Path
r=Path("/workspaces/mythos-moda-fresh-cpu-v1");p=r/"research/mini_mythos/base_v01/moda_fresh_v1";f=Path("/workspaces/mythos-evidence/base_v01/moda_fresh");d=f/"development-v6";d.mkdir(exist_ok=False)
python="/workspaces/mythos-depth-data-cpu312/bin/python";freeze="79ff936b7b3868d6431361b37dd80875d4af0fd1"
report={"Purpose":"Target development checks, pre-acquisition history freeze, and single model-blind source gate","Input":{"freeze":freeze},"Expected":{"target_helpers":87,"model_calls":0},"Actual":{"stages":[],"model_calls":0},"Status":"NOT TESTED"}
try:
 for name,count in [("test_freeze_history_v6.py",3),("test_source_feasibility_v6.py",18),("test_history_jsonl_v5.py",20),("test_data.py",28),("test_history_python_v4.py",18)]:
  target=d/(name+".json");command=[python,"-I","-B",str(p/name),"--report",str(target)];print("TARGET_HELPERS",name,flush=True);q=subprocess.run(command);x=json.loads(target.read_bytes());actual=x["Actual"];n=actual.get("run",actual.get("tests_run"));assert q.returncode==0 and x["Status"]=="PASS" and n==count and all(actual.get(k,0) in (0,[]) for k in ("failures","errors","skipped","expected_failures","unexpected_successes"));report["Actual"]["stages"].append({"name":name,"Status":"PASS","tests":n})
 for name in ("freeze_history_v6.py","source_feasibility_v6.py"):
  print("FORMAL_STAGE",name,flush=True);q=subprocess.run([python,"-I","-B",str(p/name),"--expected-head",freeze]);report["Actual"]["stages"].append({"name":name,"exit":q.returncode});
  if q.returncode!=0:report["Status"]="BLOCKED";break
 else:report["Status"]="PASS"
except BaseException as exc:
 report["Status"]="FAIL";report["error"]={"type":type(exc).__name__,"message":str(exc),"traceback":traceback.format_exc()}
finally:
 out=(f/"specification-v6/BOOTSTRAP_CONTROL.json") if (f/"specification-v6").is_dir() else d/"BOOTSTRAP_CONTROL.json"
 with out.open("x") as stream:json.dump(report,stream,indent=2);stream.write(chr(10))
 print("BOOTSTRAP_FINAL",json.dumps(report),flush=True)
