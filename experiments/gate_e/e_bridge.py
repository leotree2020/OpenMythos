"""
K=4 bridge acceptance (PREREGISTRATION 9.6). A bridge run counts as the same
training trajectory as the archived budget_a run only if all three hold:
  1. train_level.py ended normally (no comparability abort; with
     --compare-tol 0 its own pass rule reduces to bitwise equality)
  2. the output JSON reports comparability.bitwise_equal == True
     (passed == True alone is not enough: compare_to_reference() also passes
     within a tolerance when predictions agree)
  3. the parameter hash (gate_d common.param_hash) of the bridge's step-3000
     weights equals that of the archived checkpoint
"""

import e_common  # noqa: F401,E402  (first: puts the archived modules on sys.path)
import json
import os

import torch

from e_common import param_hash
from models import build


def bridge_command(arm, seed, out_json, ref_ckpt):
    return ["python", "experiments/gen_gate_a/train_level.py", "--level", "A", "--arm", arm,
            "--seed", str(seed), "--steps", "3000", "--schedule", "extended",
            "--save-at", "25,50,75,100,150,200,300,400,500,750,1000,1500,2000",
            "--probe-every", "25", "--compare-at", "3000", "--compare-ckpt", ref_ckpt,
            "--compare-tol", "0", "--out", out_json]


def hash_of_ckpt(path, arm, K=4):
    ck = torch.load(path, map_location="cpu", weights_only=False)
    m = build(arm, K)
    m.load_state_dict(ck["model"])
    return param_hash(m)


def accept(exit_code, out_json, new_ckpt, ref_ckpt, arm, K=4):
    """Returns (accepted, reasons). Never trusts 'passed' on its own."""
    why = {}
    why["exit_code_0"] = exit_code == 0
    aborted = out_json.replace(".json", "_ABORTED.json")
    why["no_abort_record"] = not os.path.exists(aborted)
    try:
        comp = json.load(open(out_json))["comparability"]
        why["bitwise_equal"] = comp.get("bitwise_equal") is True
        why["tolerance_zero"] = comp.get("tolerance") == 0
    except (OSError, ValueError, KeyError, TypeError):
        why["bitwise_equal"] = False
        why["tolerance_zero"] = False
    try:
        why["param_hash_equal"] = hash_of_ckpt(new_ckpt, arm, K) == hash_of_ckpt(ref_ckpt, arm, K)
    except (OSError, RuntimeError, KeyError):
        why["param_hash_equal"] = False
    return all(why.values()), why
