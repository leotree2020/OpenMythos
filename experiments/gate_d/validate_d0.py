#!/usr/bin/env python3
"""Run D0 (tool checks, then model checks) on all 30 Gate D model states,
with the causal checks of revision 3 (PREREGISTRATION 10.2). Writes
validation/d0_rev3.json; the original failure record validation/d0.json
(commit 1dee3da) is left untouched. Exits 1 if any check fails."""

import json
import os
import sys

import torch

from common import HERE, all_states, load_diag, load_state, param_hash, state_name
from d0 import model_checks, tool_checks

torch.set_num_threads(4)
rows = load_diag("diag_eval")
out = {"tool_checks": tool_checks(), "states": {}}
fail = [k for k, v in out["tool_checks"].items() if not v["pass"]]
for arm, seed, step in all_states():
    m = load_state(arm, seed, step)
    r = model_checks(m, rows)
    r["param_sha256"] = param_hash(m)
    out["states"][state_name(arm, seed, step)] = r
    bad = [k for k, v in r.items() if isinstance(v, dict) and "pass" in v and not v["pass"]]
    fail += [f"{state_name(arm, seed, step)}:{k}" for k in bad]
    print(state_name(arm, seed, step), "FAIL " + ",".join(bad) if bad else "ok", flush=True)
out["failures"] = fail
os.makedirs(os.path.join(HERE, "validation"), exist_ok=True)
with open(os.path.join(HERE, "validation", "d0_rev3.json"), "w") as f:
    json.dump(out, f, indent=1)
print(f"D0: {len(fail)} failing check(s)")
sys.exit(1 if fail else 0)
