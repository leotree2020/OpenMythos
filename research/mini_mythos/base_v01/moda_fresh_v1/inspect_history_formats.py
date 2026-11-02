"""Inventory metadata and archive member formats, without model/numerical imports."""
import base64, collections, gzip, hashlib, io, json, tarfile, zipfile
from pathlib import Path
ROOT=Path("/workspaces/mythos-moda-fresh-cpu-v1/research/mini_mythos/base_v01/moda_fresh_v1")
OUT=Path("/workspaces/mythos-evidence/base_v01/moda_fresh/history-formats-v1.json")
def archive(blob, label):
    if blob.startswith(b"PK"):
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            return {"format":"zip","members":[{"name":m.filename,"bytes":m.file_size} for m in z.infolist() if not m.is_dir()]}
    try:
        with tarfile.open(fileobj=io.BytesIO(blob),mode="r:*") as z:
            return {"format":"tar","members":[{"name":m.name,"bytes":m.size} for m in z.getmembers() if m.isfile()]}
    except tarfile.ReadError:pass
    if blob.startswith(bytes([31,139])):
        b=gzip.decompress(blob)
        return {"format":"gzip","expanded_bytes":len(b),"inner":archive(b,label+".decoded")}
    try:
        j=json.loads(blob)
        return {"format":"json","type":type(j).__name__,"keys":list(j)[:20] if isinstance(j,dict) else []}
    except (ValueError,UnicodeDecodeError):return {"format":"unknown","header_hex":blob[:16].hex(),"bytes":len(blob)}
def main():
    assert not OUT.exists()
    prior=json.loads(gzip.decompress(Path("/workspaces/mythos-evidence/base_v01/moda_residual/attempt-v2/protected_before.json.gz").read_bytes()))
    paths=set(Path(p) for p in prior)
    for root in (Path("/workspaces/OpenMythos"),Path("/workspaces/mythos-evidence")):
        paths.update(p for p in root.rglob("*") if p.is_file())
    paths=sorted(p for p in paths if not any(n in p.parts for n in (".git","__pycache__","moda_fresh")) and not str(p).startswith("/workspaces/mythos-moda-fresh-cpu-v1/"))
    counts=collections.Counter(); special=[]; bins=collections.defaultdict(list); missing=[]
    for p in paths:
        if not p.is_file():missing.append(str(p));continue
        ext=p.suffix.lower();counts[ext]+=1
        if ext in (".bin",".pt",".pyc"):bins[str(p.parent)].append({"name":p.name,"bytes":p.stat().st_size})
        elif ext not in (".py",".md",".json",".jsonl",".txt",".log",".stdout",".stderr",".yaml",".yml",".csv",".tsv",".sh",".lock",".sha256",".gitignore",".toml",".cfg",".ini",".rst",".sql",".js",".html",".css",".svg"):
            entry={"path":str(p),"bytes":p.stat().st_size}
            if ext in (".zip",".gz",".b64"):
                b=p.read_bytes()
                if ext==".b64":b=base64.b64decode(b,validate=False)
                entry["container"]=archive(b,str(p))
            else:
                with p.open("rb") as f:entry["header_hex"]=f.read(16).hex()
            special.append(entry)
    report={"Purpose":"Complete retained project history format discovery","Environment":"stdlib only; no model",
       "Input":{"prior_protected_count":len(prior),"roots":["/workspaces/OpenMythos","/workspaces/mythos-evidence"]},
       "Expected":"Enumerate every old path including containers before novelty-parser freeze",
       "Actual":{"count":len(paths),"suffixes":dict(counts),"special":special,
       "binary_groups":[{"parent":p,"files":v} for p,v in sorted(bins.items())],"missing":missing},
       "Status":"PASS" if not missing else "BLOCKED"}
    s=json.dumps(report,indent=2)+"\n"
    with OUT.open("x") as f:f.write(s)
    with (ROOT/"HISTORY_FORMAT_DISCOVERY.json").open("x") as f:f.write(s)
    print(json.dumps({"Status":report["Status"],"count":len(paths),"bytes":len(s.encode()),"special":len(special),"binary_groups":len(bins)}))
if __name__=="__main__":main()
