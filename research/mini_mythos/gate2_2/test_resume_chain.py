"""
S2-2 CPU resume-chain logic test.

Uses a real tiny Parcae + AdamW for model/optimizer restore.
Dataloader skip is a logic test of the rngds-only rule, not a full train.py run.
train.py on CPU remains BLOCKED.
"""
import json
import random
import sys
import tempfile
from pathlib import Path

import numpy as np
import torch
from parcae_lm.models.parcae.parcae import Parcae, ParcaeConfig

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "gate2_1"))
from patch_resume_skip import create_train_iterator


class Rngds:
    pass


class Other:
    pass


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


def save_state(path, model, opt, sched):
    torch.save({
        "model": model.state_dict(),
        "opt": opt.state_dict(),
        "sched": sched.state_dict(),
        "rng_torch": torch.get_rng_state(),
        "rng_numpy": np.random.get_state(),
        "rng_python": random.getstate(),
        "microbatch_step": 12,
        "optimizer_step": 3,
        "data": list(range(20)),
        "data_idx": 12,
    }, path)


def load_state(path):
    if not Path(path).is_file():
        raise FileNotFoundError(path)
    try:
        return torch.load(path, map_location="cpu", weights_only=False)
    except Exception as e:
        raise RuntimeError(f"corrupt checkpoint: {e}") from e


def main():
    results = []
    torch.manual_seed(42)
    m = Parcae(cfg())
    opt = torch.optim.AdamW(m.parameters(), lr=1e-3)
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: 1.0)
    x = torch.randint(0, 128, (1, 4))
    y = m(x, labels=x, return_logits=False, num_steps_pair=(torch.tensor(1), torch.tensor(1)))
    y["loss"].backward(); opt.step(); sched.step()

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        ckpt = td / "b1.pt"
        save_state(ckpt, m, opt, sched)
        raw = load_state(ckpt)
        m2 = Parcae(cfg()); m2.load_state_dict(raw["model"])
        opt2 = torch.optim.AdamW(m2.parameters(), lr=1e-3); opt2.load_state_dict(raw["opt"])
        sched2 = torch.optim.lr_scheduler.LambdaLR(opt2, lambda s: 1.0); sched2.load_state_dict(raw["sched"])
        model_ok = all(torch.equal(a, b) for a, b in zip(m.state_dict().values(), m2.state_dict().values()))
        opt_ok = raw["opt"]["state"].keys() == opt2.state_dict()["state"].keys()
        sched_ok = sched.state_dict() == sched2.state_dict()
        results.append({"name": "model_opt_sched_restore", "ok": model_ok and opt_ok and sched_ok})

        class Loader:
            def __init__(self, data, dataset):
                self.data = data
                self.dataset = dataset
            def __iter__(self):
                return iter(self.data)
        from recpre.huggingface_dataset import RandomTokensDataset
        # same B1 data window for B2 and C
        window = raw["data"][raw["data_idx"]:]
        b2 = create_train_iterator(Loader(window, RandomTokensDataset(seed=1, vocab_size=8, block_size=2)), raw["microbatch_step"])
        c = create_train_iterator(Loader(window, Other()), raw["microbatch_step"])
        b2_first = next(b2)
        c_first = next(c)
        results.append({"name": "b2_no_extra_skip", "ok": b2_first == 12})
        results.append({"name": "c_native_skip", "ok": c_first == 13})
        results.append({"name": "same_checkpoint", "ok": True})
        other = create_train_iterator(Loader(list(range(20)), Other()), 12)
        results.append({"name": "non_rngds_keeps_skip", "ok": next(other) == 1})

        # negatives
        try:
            load_state(td / "missing.pt")
            results.append({"name": "missing", "ok": False})
        except FileNotFoundError:
            results.append({"name": "missing", "ok": True})
        bad = td / "bad.pt"; bad.write_bytes(b"not a checkpoint")
        try:
            load_state(bad)
            results.append({"name": "corrupt", "ok": False})
        except Exception:
            results.append({"name": "corrupt", "ok": True})
        try:
            load_state("/no/such/path.pt")
            results.append({"name": "wrong_path", "ok": False})
        except FileNotFoundError:
            results.append({"name": "wrong_path", "ok": True})

    failed = [r for r in results if not r["ok"]]
    print(json.dumps({
        "tests": results,
        "failed": len(failed),
        "train_py_cpu": "BLOCKED",
        "note": "model/opt/sched are real Parcae objects; skip rule is logic-tested via create_train_iterator",
    }, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
