"""S2-3 CPU evidence tests. Not a GPU run."""
import json
import sys
import tempfile
from pathlib import Path

import torch
from parcae_lm.models.parcae.parcae import Parcae, ParcaeConfig

sys.path.insert(0, str(Path(__file__).resolve().parent))
from collect_native_evidence import collect
from verify_provenance import check


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


def main():
    results = []
    torch.manual_seed(1)
    m = Parcae(cfg())
    opt = torch.optim.AdamW(m.parameters(), lr=1e-3)
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: 1.0)
    x = torch.randint(0, 128, (1, 4))
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        cfg_path = td / "cfg.yaml"
        cfg_path.write_text("seed: 42\n")
        ckpt = td / "c.pt"
        torch.save(m.state_dict(), ckpt)
        meta = {
            "command": "python scripts/train.py cfg.yaml",
            "config_path": str(cfg_path),
            "openmythos_commit": "54e9585",
            "parcae_commit": "69284c1",
            "source": "CPU_PARCAE",
        }
        ev = collect(m, opt, sched, x, ckpt, {"hashes": ["h"], "losses": [1.0], "microbatch_step": 1, "optimizer_step": 1, "update_count": 1}, td / "b", meta)
        (td / "ev.json").write_text(json.dumps(ev))
        r = check(td / "ev.json", td / "b")
        results.append({"name": "cpu_parcae_provenance", "ok": r["status"] == "PROVENANCE_OK"})
        # forged GPU label
        fake = json.loads(json.dumps(ev))
        fake["source"] = "GPU_RUNTIME"
        (td / "fake.json").write_text(json.dumps(fake))
        r2 = check(td / "fake.json", td / "b")
        results.append({"name": "forged_gpu_label", "ok": r2["status"] != "PROVENANCE_OK"})
        # missing sidecar
        victim = (td / "b") / ev["model_index"][0]["blob"]
        victim.unlink()
        r3 = check(td / "ev.json", td / "b")
        results.append({"name": "missing_sidecar", "ok": r3["status"] == "MISSING"})
        # missing checkpoint refused at collect
        try:
            collect(m, opt, sched, x, td / "nope.pt", {"hashes": ["h"], "losses": [1.0]}, td / "b2", meta)
            results.append({"name": "missing_ckpt", "ok": False})
        except FileNotFoundError:
            results.append({"name": "missing_ckpt", "ok": True})
    failed = [x for x in results if not x["ok"]]
    print(json.dumps({"tests": results, "failed": len(failed), "gpu_runtime": "NOT PRODUCED"}, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
