"""Read-only target restoration and historical-format inventory; no numerical imports."""
import collections, datetime, hashlib, json, os
from pathlib import Path
import shutil, subprocess, sys
REPO=Path("/workspaces/mythos-moda-fresh-cpu-v1")
OUT=Path("/workspaces/mythos-evidence/base_v01/moda_fresh/discovery-v1.json")
BASE="bc6d267cdd8cf9306c1bf08b369cf2b791723d3d"
def git(p,*a): return subprocess.check_output(["git","-C",str(p),*a],text=True).strip()
def main():
    assert os.environ.get("CODESPACE_NAME")=="bookish-pancake-vwqx7rr9x5w3wxjr"
    assert not OUT.exists()
    roots=[Path("/workspaces/mythos-evidence"),Path("/workspaces/OpenMythos/research")]
    report={"Purpose":"Restore accepted MoDA baseline and inventory historical formats before new-source acquisition",
      "Environment":{"python":sys.version,"codespace":os.environ["CODESPACE_NAME"]},
      "Input":{"base":BASE,"roots":list(map(str,roots))},"Expected":"No historical changes or numerical imports",
      "Actual":{},"Status":"NOT TESTED"}
    actual=report["Actual"]
    actual["old_repo"]={"head":git("/workspaces/mythos-moda-residual-cpu-v2","rev-parse","HEAD"),
      "status":git("/workspaces/mythos-moda-residual-cpu-v2","status","--porcelain")}
    actual["upstream"]={"head":git("/workspaces/mythos-parcae-pinned","rev-parse","HEAD"),
      "status":git("/workspaces/mythos-parcae-pinned","status","--porcelain")}
    actual["main_head"]=git("/workspaces/OpenMythos","rev-parse","HEAD")
    actual["main_status"]=git("/workspaces/OpenMythos","status","--porcelain=v1","--untracked-files=all")
    actual["disk_free"]=shutil.disk_usage("/workspaces").free
    special=[]; suffixes={}; binary_groups=collections.defaultdict(list)
    for root in roots:
        counts=collections.Counter()
        for path in sorted(root.rglob("*")):
            if not path.is_file() or any(x in path.parts for x in (".git","__pycache__","moda_fresh")): continue
            ext=path.suffix.lower();counts[ext]+=1
            if ext in (".zip",".xz",".arrow",".parquet",".npy",".xml",".b64",".pt"):
                special.append({"path":str(path),"bytes":path.stat().st_size})
            if ext==".bin":binary_groups[str(path.parent)].append(path.name)
        suffixes[str(root)]=dict(counts)
    actual["suffixes"]=suffixes;actual["special_formats"]=special
    actual["binary_groups"]=[{"parent":p,"count":len(names),"examples":names[:4]} for p,names in sorted(binary_groups.items())]
    actual["model_imports"]=[n for n in sys.modules if n.split(".")[0] in ("torch","numpy","parcae_lm")]
    ok=(actual["old_repo"]=={"head":BASE,"status":""} and
        actual["upstream"]=={"head":"69284c13746e849104f738d6d1a347b1f457df76","status":""}
        and not actual["model_imports"])
    report["Status"]="PASS" if ok else "BLOCKED"
    report["utc"]=datetime.datetime.now(datetime.timezone.utc).isoformat()
    OUT.parent.mkdir(exist_ok=True)
    with OUT.open("x",encoding="utf-8") as f:json.dump(report,f,indent=2);f.write("\n")
    dest=REPO/"research/mini_mythos/base_v01/moda_fresh_v1/TARGET_DISCOVERY.json"
    with dest.open("xb") as f:f.write(OUT.read_bytes())
    print(json.dumps({"Status":report["Status"],"file":str(OUT),"bytes":OUT.stat().st_size,
        "sha256":hashlib.sha256(OUT.read_bytes()).hexdigest(),"free":actual["disk_free"]}))
    return 0 if ok else 2
if __name__=="__main__":raise SystemExit(main())
