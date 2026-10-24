"""
Evidence extractor. Synthetic mode is labeled SYNTHETIC.
Does not read a real Parcae checkpoint unless --native is given and the file exists.
Native Parcae / MuonAdamW / GPU evidence is NOT produced here.
"""
import json
import sys
from pathlib import Path


def synthetic():
    w = [0.1, 0.2]
    return {
        "source": "SYNTHETIC",
        "batch_hashes": ["h0", "h1"],
        "losses": [1.0, 1.1],
        "model_state": {"w": {"shape": [2], "dtype": "float32", "numel": 2, "values": w}},
        "optimizer_state": {
            "param_groups": [{"lr": 0.001, "kind": "adamw"}],
            "state": {"0": {"exp_avg": [0.0, 0.0], "step": 1}},
        },
        "scheduler": {"last_epoch": 1},
        "microbatch_step": 2,
        "optimizer_step": 1,
        "update_count": 1,
        "rng": {"cpu": "c", "cuda": "g", "python": "p", "numpy": "n"},
        "rng_at_save": {"cpu": "c"},
        "rng_at_restore": {"cpu": "c"},
        "checkpoint_sha256": "CKPT",
        "resume_from_sha256": "CKPT",
    }


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("synthetic_evidence.json")
    obj = synthetic()
    out.write_text(json.dumps(obj, indent=2))
    print(json.dumps({"wrote": str(out), "source": "SYNTHETIC", "native_parcae": False}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
