#!/usr/bin/env python3
"""Pipeline dry run (not a diagnostic): D1-D5 with a tiny workload on the
non-formal seed-99 smoke models and Random(50000)-style timing data, written
under fake state names into a scratch directory, then analyze.py on it.
Only checks that the analysis code runs end to end; no result is used."""

import json
import os
import subprocess
import sys

import torch

from common import ARMS, SEEDS, STEPS, family_tensors, load_diag, load_state, state_name
from d1 import run_d1
from d2 import run_d2
from d3 import run_d3
from d4 import run_d4
from d5 import run_d5
from diag_state import jsonable
from runner import Runner

out_dir = sys.argv[1]
os.makedirs(out_dir, exist_ok=True)
torch.set_num_threads(4)
rows = load_diag("timing")
fr, er = rows[:50], rows[50:]
pb = load_diag("pool_b")
for arm in ARMS:
    m = load_state(arm, 99, 60, path=f"../budget_a/smoke/run1_{arm}.pt")
    r = Runner(m)
    ef, ff = family_tensors(er), family_tensors(fr)
    res = {"D1": run_d1(r, ef, ff)[0], "D2": run_d2(r, ff, fr, ef, er), "D3": run_d3(r, ef, n_perm=100),
           "D4": run_d4(r, ef, chunk_bodies=25),
           "D5": run_d5(m, er, fr, pb, rows[:40], n_bodies_a=10, R=5, n_boot=100)}
    for s in SEEDS:
        for t in STEPS:
            with open(os.path.join(out_dir, f"{state_name(arm, s, t)}.json"), "w") as f:
                json.dump(jsonable(res), f)
env = dict(os.environ, GATE_D_RESULTS=out_dir, GATE_D_OUT=out_dir)
sys.exit(subprocess.call([sys.executable, "analyze.py"], env=env))
