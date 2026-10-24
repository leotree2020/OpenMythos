"""Independent provenance check. Does not modify the frozen comparator."""
import hashlib
import json
import sys
from pathlib import Path


def check(evidence_path, blob_dir):
    p = Path(evidence_path)
    if not p.is_file():
        return {"status": "MISSING", "reason": "evidence file"}
    ev = json.loads(p.read_text())
    if ev.get("source") == "GPU_RUNTIME" and not ev.get("provenance", {}).get("cuda"):
        return {"status": "BLOCKED", "reason": "GPU_RUNTIME without CUDA provenance"}
    if ev.get("source") == "SYNTHETIC":
        return {"status": "REJECTED", "reason": "SYNTHETIC"}
    prov = ev.get("provenance") or {}
    for k in ("command", "config_sha256", "checkpoint_sha256", "openmythos_commit", "parcae_commit"):
        if not prov.get(k):
            return {"status": "MISSING", "keys": [k]}
    if not ev.get("native_entry_artifact"):
        return {"status": "MISSING", "keys": ["native_entry_artifact"]}
    expected = hashlib.sha256(json.dumps({
        "command": prov["command"],
        "config_sha": prov["config_sha256"],
        "ckpt_sha": prov["checkpoint_sha256"],
        "openmythos": prov["openmythos_commit"],
        "parcae": prov["parcae_commit"],
    }, sort_keys=True).encode()).hexdigest()
    if ev["native_entry_artifact"] != expected:
        return {"status": "FAIL", "reason": "artifact not derived from provenance"}
    blob_dir = Path(blob_dir)
    for entry in ev.get("model_index", []):
        if "blob" not in entry:
            continue
        bp = blob_dir / entry["blob"]
        if not bp.is_file():
            return {"status": "MISSING", "reason": f"sidecar {entry['blob']}"}
        if hashlib.sha256(bp.read_bytes()).hexdigest() != entry.get("sha256"):
            return {"status": "FAIL", "reason": f"sidecar sha {entry.get('name')}"}
    return {"status": "PROVENANCE_OK", "source": ev.get("source")}


def main():
    if len(sys.argv) < 3:
        print("usage: verify_provenance.py evidence.json blob_dir")
        return 2
    out = check(sys.argv[1], sys.argv[2])
    print(json.dumps(out, indent=2))
    return 0 if out["status"] == "PROVENANCE_OK" else 1


if __name__ == "__main__":
    sys.exit(main())
