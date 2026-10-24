"""CPU save/reload of a real tiny Parcae. Distinguishes model vs optimizer consistency.
Not a training-path numerical equivalence claim. No GPU.
"""
import json
import sys
import tempfile
from pathlib import Path

import torch
from parcae_lm.models.parcae.parcae import Parcae, ParcaeConfig

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_evidence import from_objects, collect_rng, read_checkpoint


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
    torch.manual_seed(42)
    m = Parcae(cfg())
    opt = torch.optim.AdamW(m.parameters(), lr=1e-3)
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: 1.0)
    x = torch.randint(0, 128, (1, 4))
    y = m(x, labels=x, return_logits=False, num_steps_pair=(torch.tensor(1), torch.tensor(1)))
    y["loss"].backward(); opt.step(); sched.step()
    before = collect_rng("before_save")
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        ckpt = td / "m.pt"
        torch.save({"model": m.state_dict(), "opt": opt.state_dict()}, ckpt)
        # reload
        blob = torch.load(ckpt, map_location="cpu", weights_only=False)
        m2 = Parcae(cfg())
        m2.load_state_dict(blob["model"])
        opt2 = torch.optim.AdamW(m2.parameters(), lr=1e-3)
        opt2.load_state_dict(blob["opt"])
        after = collect_rng("after_load")
        ev1 = from_objects(m, opt, sched, x, ckpt, "CPU_PARCAE", {"hashes": None, "losses": None}, td / "b", {"before_save": before})
        ev2 = from_objects(m2, opt2, sched, x, ckpt, "CPU_PARCAE", {"hashes": None, "losses": None}, td / "b", {"after_load": after})
        model_same = [a["sha256"] for a in ev1["model_index"]] == [a["sha256"] for a in ev2["model_index"]]
        opt_same = [a.get("sha256") for a in ev1["optimizer_index"]] == [a.get("sha256") for a in ev2["optimizer_index"]]
        ck = read_checkpoint(ckpt, td / "b")
        out = {
            "model_state_consistent": model_same,
            "optimizer_state_consistent": opt_same,
            "training_path_numerical": "NOT TESTED",
            "cuda_rng": before["cuda_status"],
            "muonadamw_step": "NOT TESTED",
            "checkpoint_keys": ck.get("top_keys"),
            "source": "CPU_PARCAE",
            "gpu_numerical_pass": False,
        }
        print(json.dumps(out, indent=2))
        return 0 if model_same and opt_same else 1


if __name__ == "__main__":
    sys.exit(main())
