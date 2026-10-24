"""
S2-2 strengthened CPU resume-chain test.

Boundaries:
- Real Parcae model object for model/optimizer/scheduler restore.
- Self-built checkpoint (AdamW), not native fabric MuonAdamW checkpoint.
- Logic branch for rngds skip vs native skip.
- Native train.py / MuonAdamW / CUDA RNG: NOT TESTED.
"""
import hashlib
import json
import random
import sys
import tempfile
from pathlib import Path

import numpy as np
import torch
from parcae_lm.models.parcae.parcae import Parcae, ParcaeConfig
from recpre.huggingface_dataset import RandomTokensDataset

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "gate2_1"))
from patch_resume_skip import create_train_iterator


class Loader:
    def __init__(self, data, dataset):
        self.data = data
        self.dataset = dataset

    def __iter__(self):
        return iter(self.data)


def native_iterator(loader, microbatch_step):
    """Mirror pinned Parcae: always next() when microbatch_step > 0."""
    it = iter(loader)
    if microbatch_step > 0:
        next(it, None)
    return it


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


def tensors_equal(a, b):
    if torch.is_tensor(a) and torch.is_tensor(b):
        return torch.equal(a.cpu(), b.cpu())
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(tensors_equal(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(tensors_equal(x, y) for x, y in zip(a, b))
    return a == b


def main():
    results = []
    torch.manual_seed(42)
    np.random.seed(42)
    random.seed(42)
    m = Parcae(cfg())
    opt = torch.optim.AdamW(m.parameters(), lr=1e-3)
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: 1.0)
    x = torch.randint(0, 128, (1, 4))
    y = m(x, labels=x, return_logits=False, num_steps_pair=(torch.tensor(1), torch.tensor(1)))
    y["loss"].backward()
    opt.step()
    sched.step()

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        ckpt = td / "b1.pt"
        payload = {
            "model": m.state_dict(),
            "opt": opt.state_dict(),
            "sched": sched.state_dict(),
            "rng_torch": torch.get_rng_state(),
            "rng_numpy": np.random.get_state(),
            "rng_python": random.getstate(),
            "microbatch_step": 12,
            "optimizer_step": 3,
            "data": list(range(20)),
            "data_idx": 12,
        }
        torch.save(payload, ckpt)
        sha = hashlib.sha256(ckpt.read_bytes()).hexdigest()

        raw_b2 = torch.load(ckpt, map_location="cpu", weights_only=False)
        raw_c = torch.load(ckpt, map_location="cpu", weights_only=False)
        sha_b2 = hashlib.sha256(ckpt.read_bytes()).hexdigest()
        sha_c = hashlib.sha256(ckpt.read_bytes()).hexdigest()
        results.append({"name": "same_file_sha256", "ok": sha == sha_b2 == sha_c})

        def restore(raw):
            mm = Parcae(cfg())
            mm.load_state_dict(raw["model"])
            oo = torch.optim.AdamW(mm.parameters(), lr=1e-3)
            oo.load_state_dict(raw["opt"])
            ss = torch.optim.lr_scheduler.LambdaLR(oo, lambda st: 1.0)
            ss.load_state_dict(raw["sched"])
            return mm, oo, ss

        m2, o2, s2 = restore(raw_b2)
        m3, o3, s3 = restore(raw_c)
        model_ok = all(torch.equal(a, b) for a, b in zip(m2.state_dict().values(), m3.state_dict().values()))
        opt_ok = tensors_equal(o2.state_dict(), o3.state_dict())
        sched_ok = s2.state_dict() == s3.state_dict()
        def np_eq(a, b):
            return a[0] == b[0] and all(np.array_equal(x, y) if hasattr(x, "shape") else x == y for x, y in zip(a[1:], b[1:]))
        rng_ok = (
            torch.equal(raw_b2["rng_torch"], raw_c["rng_torch"])
            and np_eq(raw_b2["rng_numpy"], raw_c["rng_numpy"])
            and raw_b2["rng_python"] == raw_c["rng_python"]
        )
        results.append({"name": "restore_model_equal", "ok": model_ok})
        results.append({"name": "restore_optimizer_full", "ok": opt_ok})
        results.append({"name": "restore_scheduler", "ok": sched_ok})
        results.append({"name": "restore_rng_equal", "ok": rng_ok})
        results.append({"name": "same_start_before_skip", "ok": model_ok and opt_ok and sched_ok and rng_ok and raw_b2["data_idx"] == raw_c["data_idx"]})

        window = raw_b2["data"][raw_b2["data_idx"]:]
        ds = RandomTokensDataset(seed=1, vocab_size=8, block_size=2)
        b2 = create_train_iterator(Loader(window, ds), raw_b2["microbatch_step"])
        c = native_iterator(Loader(window, ds), raw_c["microbatch_step"])
        results.append({"name": "b2_rngds_no_extra_skip", "ok": next(b2) == 12})
        results.append({"name": "c_native_extra_skip", "ok": next(c) == 13})

        class Other:
            pass
        other = create_train_iterator(Loader(list(range(20)), Other()), 12)
        results.append({"name": "non_rngds_keeps_skip", "ok": next(other) == 1})

        try:
            torch.load(td / "missing.pt", map_location="cpu", weights_only=False)
            results.append({"name": "missing", "ok": False})
        except FileNotFoundError:
            results.append({"name": "missing", "ok": True})
        bad = td / "bad.pt"
        bad.write_bytes(b"not a checkpoint")
        try:
            torch.load(bad, map_location="cpu", weights_only=False)
            results.append({"name": "corrupt", "ok": False})
        except Exception:
            results.append({"name": "corrupt", "ok": True})

    failed = [r for r in results if not r["ok"]]
    print(json.dumps({
        "tests": results,
        "failed": len(failed),
        "boundaries": {
            "real_parcae_model": True,
            "self_built_checkpoint": True,
            "optimizer": "AdamW, not MuonAdamW",
            "skip_rule": "logic branch",
            "native_train_py": "NOT TESTED",
            "cuda_rng": "NOT TESTED",
            "muonadamw_state": "NOT TESTED",
        },
    }, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
