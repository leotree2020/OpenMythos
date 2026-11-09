"""Attach a Stage 3 mechanism (or the C-LoRA control) to a loaded Parcae model through hooks."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "stage2"))
import gpu_common as G  # noqa: E402
from moda_p import MoDAP  # noqa: E402,F401


def attach(torch, model, mode, rank=28, alpha=None, seed=0):
    if mode == "lora":
        return G.LoRA(torch, model, rank=rank, alpha=2.0 * rank if not alpha else alpha, seed=seed)
    if mode == "moda":
        return MoDAP(model)
    raise ValueError(mode)


def load_params(torch, mech, path):
    saved = torch.load(path, map_location="cpu", weights_only=True)
    if set(saved) != set(mech.params):
        raise SystemExit("saved parameters do not match the mechanism")
    with torch.no_grad():
        for k, v in saved.items():
            mech.params[k].copy_(v.to(mech.params[k].device))
