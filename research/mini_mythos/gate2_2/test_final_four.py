"""Targeted tests for the four final fixes. Not a real GPU run."""
import json
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

import torch
from parcae_lm.models.parcae.parcae import Parcae, ParcaeConfig

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_evidence import from_objects
from compare_equivalence import decode, integrity_of
SCRIPT = Path(__file__).resolve().parent / "compare_equivalence.py"


def test_bf16():
    # 1.0 in bf16 is 0x3f80
    raw = struct.pack("<H", 0x3F80)
    vals, err = decode(raw, "bfloat16", 1)
    fp16, _ = decode(raw, "float16", 1)
    return err is None and abs(vals[0] - 1.0) < 1e-6 and vals != fp16


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


def stamp(o):
    o = json.loads(json.dumps(o))
    o["source"] = "GPU_RUNTIME"
    o["optimizer_class"] = "MuonAdamW"
    o["resume_from_sha256"] = o["checkpoint_sha256"]
    o["rng_stages"] = {
        "before_save": {"stage": "before_save", "cpu": "c", "cuda": "g", "python": "p", "numpy": "n", "cuda_status": "COLLECTED"},
        "after_load": {"stage": "after_load", "cpu": "c", "cuda": "g", "python": "p", "numpy": "n", "cuda_status": "COLLECTED"},
    }
    o["integrity"] = integrity_of(o)
    return o


def run(td, blob, logic=False):
    files = [str(td / f"{n}.json") for n in ("A", "B1", "B2", "C")]
    cmd = [sys.executable, str(SCRIPT), *files, "--blob-dir", str(blob)]
    if logic:
        cmd.append("--logic-test")
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, r.stdout


def main():
    results = [{"name": "bf16_ne_fp16", "ok": test_bf16()}]
    torch.manual_seed(1)
    m = Parcae(cfg())
    opt = torch.optim.AdamW(m.parameters(), lr=1e-3)
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: 1.0)
    x = torch.randint(0, 128, (1, 4))
    with tempfile.TemporaryDirectory() as td:
        td = Path(td); blob = td / "b"; blob.mkdir()
        ckpt = td / "c.pt"; torch.save({"m": 1}, ckpt)
        counts = {"hashes": ["h0", "h1", "h2", "h3"], "losses": [1.0, 1.1, 1.2, 1.3],
                  "microbatch_step": 4, "optimizer_step": 1, "update_count": 1}
        base = from_objects(m, opt, sched, x, ckpt, "CPU_PARCAE", counts, blob)
        A, B1, B2, C = stamp(base), stamp(base), stamp(base), stamp(base)
        B1["batch_hashes"] = ["h0", "h1"]; B1["losses"] = [1.0, 1.1]; B1["integrity"] = integrity_of(B1)
        B2["batch_hashes"] = ["h2", "h3"]; B2["losses"] = [1.2, 1.3]; B2["integrity"] = integrity_of(B2)
        C["batch_hashes"] = ["h3"]; C["losses"] = [1.3]; C["integrity"] = integrity_of(C)
        for n, o in (("A", A), ("B1", B1), ("B2", B2), ("C", C)):
            (td / f"{n}.json").write_text(json.dumps(o))
        code, out = run(td, blob, logic=True)
        results.append({"name": "logic_test_exit0", "code": code, "ok": code == 0 and "LOGIC TEST" in out})
        code, out = run(td, blob, logic=False)
        results.append({"name": "formal_without_artifact_blocked", "code": code, "ok": code == 3 and "BLOCKED" in out})
        # RNG value change
        B2r = json.loads(json.dumps(B2)); B2r["rng_stages"]["after_load"]["cuda"] = "CHANGED"; B2r["integrity"] = integrity_of(B2r)
        (td / "B2.json").write_text(json.dumps(B2r))
        code, out = run(td, blob, logic=True)
        results.append({"name": "rng_value_changed", "code": code, "ok": code != 0})
        # empty loss
        (td / "B2.json").write_text(json.dumps(B2))
        Ae = json.loads(json.dumps(A)); Ae["losses"] = []; Ae["integrity"] = integrity_of(Ae)
        (td / "A.json").write_text(json.dumps(Ae))
        code, out = run(td, blob, logic=True)
        results.append({"name": "empty_loss", "code": code, "ok": code == 2 and "MISSING" in out})
    failed = [r for r in results if not r["ok"]]
    print(json.dumps({"tests": results, "failed": len(failed), "note": "not a real GPU run"}, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
