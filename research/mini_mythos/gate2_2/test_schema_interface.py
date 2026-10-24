"""Interface self-test. No GPU. Does not claim GPU verification."""
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import torch
from parcae_lm.models.parcae.parcae import Parcae, ParcaeConfig

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_evidence import from_objects
SCRIPT = Path(__file__).resolve().parent / "compare_equivalence.py"


def cfg():
    return ParcaeConfig(
        n_embd=32, intermediate_size=64, num_attention_heads=2, num_key_value_heads=2,
        vocab_size=128, padded_vocab_size=128, block_size=8,
        n_layers_in_prelude=1, n_layers_in_recurrent_block=1, n_layers_in_coda=1,
        mean_recurrence=1, mean_backprop_depth=1, recurrent_embedding_dimension=32,
        recurrent_intermediation_embedding_dimension=64, prelude_norm=True,
        injection_type="diagonal", state_init="normal", tie_embeddings=True,
        use_fused_head="pytorch", sampling_scheme="fixed",
    )


def run(files, blob):
    r = subprocess.run([sys.executable, str(SCRIPT), *files, "--blob-dir", str(blob)], capture_output=True, text=True)
    return r.returncode, r.stdout


def main():
    results = []
    torch.manual_seed(1)
    m = Parcae(cfg())
    opt = torch.optim.AdamW(m.parameters(), lr=1e-3)
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: 1.0)
    x = torch.randint(0, 128, (1, 4))
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        blob = td / "blobs"
        ckpt = td / "c.pt"
        torch.save(m.state_dict(), ckpt)
        counts = {"hashes": ["h0", "h1", "h2", "h3"], "losses": [1, 1, 1, 1]}
        A = from_objects(m, opt, sched, x, ckpt, "CPU_PARCAE", counts, blob)
        A["resume_from_sha256"] = A["checkpoint_sha256"]
        B1 = json.loads(json.dumps(A)); B1["batch_hashes"] = ["h0", "h1"]; B1["losses"] = [1, 1]
        B2 = json.loads(json.dumps(A)); B2["batch_hashes"] = ["h2", "h3"]; B2["losses"] = [1, 1]
        C = json.loads(json.dumps(A)); C["batch_hashes"] = ["h3"]; C["losses"] = [1]
        for n, o in (("A", A), ("B1", B1), ("B2", B2), ("C", C)):
            (td / f"{n}.json").write_text(json.dumps(o))
        files = [str(td / f"{n}.json") for n in ("A", "B1", "B2", "C")]
        code, out = run(files, blob)
        results.append({"name": "cpu_structural", "code": code, "ok": code == 1 and "STRUCTURAL PASS" in out})

        # corrupt a blob
        entry = A["model_index"][0]
        bp = blob / entry["blob"]
        bp.write_bytes(b"corrupt")
        code, out = run(files, blob)
        results.append({"name": "blob_corrupt", "code": code, "ok": code != 0 and ("FAIL" in out or "MISSING" in out)})
        # restore blob then delete
        raw = torch.load(ckpt, map_location="cpu", weights_only=False)
        # rebuild clean
        A2 = from_objects(m, opt, sched, x, ckpt, "CPU_PARCAE", counts, blob)
        A2["resume_from_sha256"] = A2["checkpoint_sha256"]
        for n, o in (("A", A2), ("B1", {**A2, "batch_hashes": ["h0", "h1"]}), ("B2", {**A2, "batch_hashes": ["h2", "h3"]}), ("C", {**A2, "batch_hashes": ["h3"]})):
            (td / f"{n}.json").write_text(json.dumps(o))
        victim = blob / A2["model_index"][0]["blob"]
        victim.unlink()
        code, out = run(files, blob)
        results.append({"name": "blob_deleted", "code": code, "ok": code == 2 and "MISSING" in out})

        # shape mismatch via edited json
        A3 = from_objects(m, opt, sched, x, ckpt, "CPU_PARCAE", counts, blob)
        A3["resume_from_sha256"] = A3["checkpoint_sha256"]
        B2s = json.loads(json.dumps(A3)); B2s["batch_hashes"] = ["h2", "h3"]
        B2s["model_index"][0]["shape"] = [999]
        for n, o in (("A", A3), ("B1", {**A3, "batch_hashes": ["h0", "h1"]}), ("B2", B2s), ("C", {**A3, "batch_hashes": ["h3"]})):
            (td / f"{n}.json").write_text(json.dumps(o))
        code, out = run(files, blob)
        results.append({"name": "shape_mismatch", "code": code, "ok": code != 0 and "FAIL" in out})

        # optimizer differ
        A4 = from_objects(m, opt, sched, x, ckpt, "CPU_PARCAE", counts, blob)
        A4["resume_from_sha256"] = A4["checkpoint_sha256"]
        B2o = json.loads(json.dumps(A4)); B2o["batch_hashes"] = ["h2", "h3"]
        if B2o["optimizer_index"]:
            B2o["optimizer_index"][0]["sha256"] = "0" * 64
        for n, o in (("A", A4), ("B1", {**A4, "batch_hashes": ["h0", "h1"]}), ("B2", B2o), ("C", {**A4, "batch_hashes": ["h3"]})):
            (td / f"{n}.json").write_text(json.dumps(o))
        code, out = run(files, blob)
        results.append({"name": "optimizer_differ", "code": code, "ok": code != 0})

        # relabel source cannot forge GPU PASS
        A5 = from_objects(m, opt, sched, x, ckpt, "CPU_PARCAE", counts, blob)
        for o in (A5,):
            o["source"] = "GPU_RUNTIME"
            o["optimizer_class"] = "MuonAdamW"
            o["resume_from_sha256"] = o["checkpoint_sha256"]
        B1f = {**A5, "batch_hashes": ["h0", "h1"]}
        B2f = {**A5, "batch_hashes": ["h2", "h3"]}
        Cf = {**A5, "batch_hashes": ["h3"]}
        for n, o in (("A", A5), ("B1", B1f), ("B2", B2f), ("C", Cf)):
            (td / f"{n}.json").write_text(json.dumps(o))
        code, out = run(files, blob)
        results.append({"name": "relabel_not_gpu_pass", "code": code, "ok": code != 0 and "GPU NUMERICAL PASS" not in out})

    failed = [r for r in results if not r["ok"]]
    print(json.dumps({"tests": results, "failed": len(failed)}, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
