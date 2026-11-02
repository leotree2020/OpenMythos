import json,subprocess,sys,traceback
from pathlib import Path
p=Path("/workspaces/mythos-moda-fresh-cpu-v1/research/mini_mythos/base_v01/moda_fresh_v1");f=Path("/workspaces/mythos-evidence/base_v01/moda_fresh");python="/workspaces/mythos-depth-data-cpu312/bin/python"
freeze="7a293a2b9ab8b0c667c5c839e152a1423cd93c10";report={"Purpose":"Target helper admission and single full-history train-text preparation","Input":{"implementation":freeze},"Expected":{"helpers":18,"history_files":32603,"selected":20,"model_calls":0},"Actual":{"model_calls":0},"Status":"NOT TESTED"}
try:
 target=f/"specification-v6/PREP_TARGET_HELPERS.json";q=subprocess.run([python,"-I","-B",str(p/"test_prepare_history_v6.py"),"--report",str(target)]);x=json.loads(target.read_bytes());a=x["Actual"];assert q.returncode==0 and x["Status"]=="PASS" and a.get("run",a.get("tests_run"))==18 and all(a.get(k,0) in (0,[]) for k in ("failures","errors","skipped"));report["Actual"]["helpers_passed"]=18
 command=[python,"-I","-B",str(p/"prepare_history_v6.py"),"--expected-head",freeze,"--expected-spec-sha","906581f9c2069f184a9d04f6ab3d343e60e8ed44223d07552cbf7a5bf7cd5d8d","--expected-gate-sha","619e50cb2cc58e4a836f5c24058b5cffe2f9db66f1e6d2dc230134f2c2062de9"];print("FORMAL_HISTORY_START",json.dumps(command),flush=True);q=subprocess.run(command);report["Actual"]["preparation_exit"]=q.returncode
 m=json.loads((f/"preparation-v6/manifest.json").read_bytes());report["Status"]=m["Status"];report["Actual"]["preparation"]=m["Actual"]
except BaseException as exc:report["Status"]="FAIL";report["error"]={"type":type(exc).__name__,"message":str(exc),"traceback":traceback.format_exc()}
finally:
 with (f/"specification-v6/PREPARATION_CONTROL_V6.json").open("x") as stream:json.dump(report,stream,indent=2);stream.write(chr(10))
 print("HISTORY_CONTROL_FINAL",json.dumps(report),flush=True)
