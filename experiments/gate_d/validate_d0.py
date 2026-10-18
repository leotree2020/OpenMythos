#!/usr/bin/env python3
"""Run D0 (tool checks, then model checks) on all 30 Gate D model states.
Writes validation/d0.json. For a state whose causal_mask check fails, also
records the causal_structural investigation (not a pre-registered check) and
which record point first differs. Exits 1 if any check fails."""

import json
import os
import sys

import torch

from common import HERE, all_states, family_tensors, load_diag, load_state, param_hash, state_name
from d0 import causal_structural, model_checks, tool_checks
from runner import Runner

torch.set_num_threads(4)
rows = load_diag("diag_eval")
x = family_tensors(rows)[0]
out = {"tool_checks": tool_checks(), "states": {}}
fail = [k for k, v in out["tool_checks"].items() if not v["pass"]]
for arm, seed, step in all_states():
    m = load_state(arm, seed, step)
    r = model_checks(m, rows)
    r["param_sha256"] = param_hash(m)
    if not r["causal_mask"]["pass"]:
        sub = x[:64]
        r["causal_investigation"] = {}
        for j in (17, 10, 3):
            inv = causal_structural(m, sub, j)
            s2 = sub.clone()
            s2[:, j] = ord("Z") if j == 17 else ord("0") if j == 10 else ord("z")
            a = Runner(m).run(sub, record=True)[1]
            b = Runner(m).run(s2, record=True)[1]
            diffs = {k: (a[k][:, :j].float() - b[k][:, :j].float()).abs().max().item()
                     for k in a if a[k].dim() >= 2 and a[k].shape[1] == 19}
            inv["first_differing_record_point"] = next((k for k, v in diffs.items() if v > 0), None)
            r["causal_investigation"][str(j)] = inv
    out["states"][state_name(arm, seed, step)] = r
    bad = [k for k, v in r.items() if isinstance(v, dict) and "pass" in v and not v["pass"]]
    fail += [f"{state_name(arm, seed, step)}:{k}" for k in bad]
    print(state_name(arm, seed, step), "FAIL " + ",".join(bad) if bad else "ok", flush=True)
out["failures"] = fail
os.makedirs(os.path.join(HERE, "validation"), exist_ok=True)
with open(os.path.join(HERE, "validation", "d0.json"), "w") as f:
    json.dump(out, f, indent=1)
print(f"D0: {len(fail)} failing check(s)")
sys.exit(1 if fail else 0)
