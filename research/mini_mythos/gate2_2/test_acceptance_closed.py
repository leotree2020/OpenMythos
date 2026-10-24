"""Acceptance-logic self-test. LOGIC TEST only. Not a real GPU result."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import torch
from parcae_lm.models.parcae.parcae import Parcae, ParcaeConfig

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_evidence import from_objects
from compare_equivalence import integrity_of
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


def stamp(o, source="GPU_RUNTIME"):
    o = json.loads(json.dumps(o))
    o["source"] = source
    o["optimizer_class"] = "MuonAdamW"
    o["resume_from_sha256"] = o["checkpoint_sha256"]
    o["rng_stages"] = {
        "before_save": {"cuda_status": "COLLECTED", "cpu": "s"},
        "after_load": {"cuda_status": "COLLECTED", "cpu": "s"},
    }
    o["integrity"] = integrity_of(o)
    return o


def run(td, blob, logic=True):
    files = [str(td / f"{n}.json") for n in ("A", "B1", "B2", "C")]
    cmd = [sys.executable, str(SCRIPT), *files, "--blob-dir", str(blob)]
    if logic:
        cmd.append("--logic-test")
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, r.stdout


def main():
    results = []
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
        def write(A, B1, B2, C):
            for n, o in (("A", A), ("B1", B1), ("B2", B2), ("C", C)):
                (td / f"{n}.json").write_text(json.dumps(o))
        A = stamp(base); B1 = stamp(base); B1["batch_hashes"] = ["h0", "h1"]; B1["losses"] = [1.0, 1.1]; B1["integrity"] = integrity_of(B1)
        B2 = stamp(base); B2["batch_hashes"] = ["h2", "h3"]; B2["losses"] = [1.2, 1.3]; B2["integrity"] = integrity_of(B2)
        C = stamp(base); C["batch_hashes"] = ["h3"]; C["losses"] = [1.3]; C["integrity"] = integrity_of(C)
        write(A, B1, B2, C)
        code, out = run(td, blob)
        results.append({"name": "complete_logic", "code": code, "ok": code == 0 and "LOGIC TEST" in out})

        def mutate(name, fn):
            A2, B12, B22, C2 = json.loads(json.dumps(A)), json.loads(json.dumps(B1)), json.loads(json.dumps(B2)), json.loads(json.dumps(C))
            fn(A2, B12, B22, C2)
            for o in (A2, B12, B22, C2):
                o["integrity"] = integrity_of(o)
            write(A2, B12, B22, C2)
            code, out = run(td, blob)
            results.append({"name": name, "code": code, "ok": code != 0 and "GPU NUMERICAL PASS" not in out.replace("LOGIC TEST", "")})

        mutate("loss", lambda A, B1, B2, C: B2.__setitem__("losses", [9.0, 9.0]))
        mutate("scheduler", lambda A, B1, B2, C: B2.__setitem__("scheduler", {"x": 1}))
        mutate("optimizer_step", lambda A, B1, B2, C: B2.__setitem__("optimizer_step", 99))
        mutate("update_count", lambda A, B1, B2, C: B2.__setitem__("update_count", 99))
        mutate("param_groups", lambda A, B1, B2, C: B2.__setitem__("optimizer_param_groups", [{"lr": 9}]))
        mutate("cuda_rng", lambda A, B1, B2, C: B2["rng_stages"]["after_load"].__setitem__("cpu", "OTHER"))

        # source relabel without integrity update
        bad = json.loads(json.dumps(A)); bad["source"] = "GPU_RUNTIME"
        (td / "A.json").write_text(json.dumps(bad))
        code, out = run(td, blob)
        results.append({"name": "source_without_integrity", "code": code, "ok": code != 0})

    failed = [r for r in results if not r["ok"]]
    print(json.dumps({"tests": results, "failed": len(failed), "note": "LOGIC TEST only, not a real GPU run"}, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
