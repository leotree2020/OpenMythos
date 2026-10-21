#!/usr/bin/env python3
"""
Validation of revision 6 (PREREGISTRATION 13.6 and definitions A, B) on
non-formal models (seed-99 initialization / 60-step smoke checkpoints, timing
data) and constructed data only. Never reads or writes results/. Writes
validation/rev6_tests.json; exits 1 on any failure.

  1 reachability R vs autograd (hard): R false -> gradient exactly 0; R true
    -> gradient non-zero; on a natural run and on a constructed run whose ACT
    carry at loop 1 is set so that halted early positions reach the readout
    only through a later, still-running position (the multi-hop path)
  2 definition A: ACT masks from single-sample runs vs two batch compositions
  3 D2: negative control (uninformative features, query-dependent validity):
    question-level selection unbalances the slot labels, complete families do
    not; decide() with c_hi > c0 makes "detected" harder and never makes
    "not detected" easier
  4 D4: on a smoke model every unreachable pair is within 10 eps and every
    pre-patch record equals the clean run (hard checks inside run_d4); a
    simulation where the effect exists for some queries only and selection
    depends on the query: the question-level mean moves with the selection
    rates, the complete-family mean does not
  5 grading: H1 uncertain without evaluated I2, with a coverage gap, or with
    reachable pairs excluded by incomplete bodies (definition B); support
    only when fully covered; H4 same-subset re-scoring reproducible, and
    uncertain when the interface is skipped or the detection is not confirmed
"""

import copy
import json
import os
import sys

import numpy as np
import torch

# this directory first: basic_learn/models.py puts loop_mech (which has its
# own analyze.py) at the front of sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze import OPP, SUP, UNC, h1_d4, h4_d4, rescore  # noqa: E402
from act_masks import act_masks, complete, reachability
from common import HERE, READ_POS, family_tensors, load_diag, load_state
from d2 import decide
from d4 import run_d4
from runner import Runner

torch.set_num_threads(4)
res, fail = {}, []
SMOKE = os.path.join(HERE, "..", "budget_a", "smoke", "run1_openmythos.pt")
fam = family_tensors(load_diag("timing"))
x = fam[0]


# ---------------------------------------------------------------- 1
def grad_check(run_kwargs, x, t_min=0):
    r = Runner(load_state("openmythos", 99, 0))
    lg, rec, _ = r.run(x, record=True, grad=True, **run_kwargs)
    T = 4
    M = {"valid": torch.stack([rec[f"valid{t}"] for t in range(T)], 1),
         "still": torch.stack([rec[f"still{t}"] for t in range(T)], 1)}
    R = reachability(M)
    v = torch.randn(lg[:, READ_POS].shape, generator=torch.Generator().manual_seed(0))
    hs = [rec[f"h{t + 1}"] for t in range(t_min, T)]
    grads = torch.autograd.grad((lg[:, READ_POS] * v).sum(), hs, allow_unused=True)
    out = {}
    for t, gr in zip(range(t_min, T), grads):
        gn = gr.norm(dim=-1) if gr is not None else torch.zeros(R[:, t].shape)
        direct = M["still"][:, t] | (M["still"][:, t + 1, READ_POS:READ_POS + 1] if t + 1 < T else False)
        out[f"loop{t}"] = {"reachable": int(R[:, t].sum()), "unreachable_but_grad": int((~R[:, t] & (gn > 0)).sum()),
                           "reachable_but_zero_grad": int((R[:, t] & (gn == 0)).sum()),
                           "reachable_only_via_other_positions": int((R[:, t] & ~direct).sum())}
    return out


natural = grad_check({}, x[:64])
# constructed: at loop 1, positions 0-9 and 18 halted, 10-17 running
r0 = Runner(load_state("openmythos", 99, 0))
_, rc, _ = r0.run(x[:64], record=True)
halted = torch.zeros(64, 19, dtype=torch.bool)
halted[:, :10] = True
halted[:, 18] = True
carry = {"h_before1": rc["h_before1"], "e": rc["e"], "hout_before1": rc["hout_before1"],
         "cum_before1": torch.where(halted, torch.ones(64, 19), torch.zeros(64, 19)),
         "halted_before1": halted}
constructed = grad_check({"patch": {"carry1": (None, carry)}}, x[:64], t_min=1)
res["1_reachability_vs_autograd"] = {"natural_seed99_init": natural, "constructed_multi_hop": constructed}
for part in (natural, constructed):
    for v in part.values():
        if v["unreachable_but_grad"] or v["reachable_but_zero_grad"]:
            fail.append("1 mismatch")
if not any(v["reachable_only_via_other_positions"] for v in constructed.values()):
    fail.append("1 constructed case did not exercise the multi-hop path")

# ---------------------------------------------------------------- 2
for label, m in (("seed99_init", load_state("openmythos", 99, 0)),
                 ("seed99_smoke60", load_state("openmythos", 99, 60, path=SMOKE))):
    run = Runner(m)
    single = act_masks(run, x)
    rec_a = run.run(x, record=True)[1]
    perm = torch.randperm(len(x), generator=torch.Generator().manual_seed(3))
    inv = torch.argsort(perm)
    recs = [run.run(x[perm][i : i + 7], record=True)[1] for i in range(0, len(x), 7)]
    mism = {}
    for t in range(4):
        vb = torch.cat([r[f"valid{t}"] for r in recs])[inv]
        sb = torch.cat([r[f"still{t}"] for r in recs])[inv]
        mism[f"loop{t}"] = {"valid_vs_batch_all": int((rec_a[f"valid{t}"] != single["valid"][:, t]).sum()),
                            "still_vs_batch_all": int((rec_a[f"still{t}"] != single["still"][:, t]).sum()),
                            "valid_vs_batch_7_shuffled": int((vb != single["valid"][:, t]).sum()),
                            "still_vs_batch_7_shuffled": int((sb != single["still"][:, t]).sum())}
    res.setdefault("2_batch_composition", {})[label] = mism

# ---------------------------------------------------------------- 3
g = torch.Generator().manual_seed(11)
slot = torch.arange(4).repeat(500)
valid_q = torch.rand(2000, generator=g) < torch.tensor([0.95, 0.95, 0.6, 0.6]).repeat(500)
q_level = torch.bincount(slot[valid_q], minlength=4).double() / int(valid_q.sum())
cf = complete(valid_q)
fam_level = torch.bincount(slot[cf], minlength=4).double() / int(cf.sum())
c0, c_hi = 0.25, 0.40
cases = {
    "lo above c0 threshold, below c_hi threshold": {"ci95": [0.65, 0.75]},
    "hi <= c0 + 0.10": {"ci95": [0.20, 0.34]},
    "hi between c0 + 0.10 and c_hi + 0.10": {"ci95": [0.30, 0.45]},
}
dec = {k: {"single_c0": decide(v, None, c0), "dual": decide(v, None, c_hi, c0)} for k, v in cases.items()}
res["3_d2"] = {"question_level_slot_shares": q_level.tolist(), "complete_family_slot_shares": fam_level.tolist(),
               "baseline_directions": dec}
if (abs(fam_level - 0.25).max() > 1e-12
        or dec["lo above c0 threshold, below c_hi threshold"]["dual"] == "检测到可线性解码的信息"
        or dec["hi <= c0 + 0.10"]["dual"] != "未检测到足够的可线性解码信息"
        or dec["hi between c0 + 0.10 and c_hi + 0.10"]["dual"] == "未检测到足够的可线性解码信息"):
    fail.append("3")

# ---------------------------------------------------------------- 4
m = load_state("openmythos", 99, 60, path=SMOKE)
d4 = run_d4(Runner(m), fam, chunk_bodies=50)  # raises on any hard-check failure
res["4_d4_smoke"] = {
    "max_unreachable_tv": max(u["max_tv"] for u in d4["unreachable_pairs"].values()),
    "eps_tv": d4["noise_eps"]["tv"],
    "pre_intervention_bitwise_all": all(c["pre_intervention_bitwise"] for c in d4["controls"].values()),
    "share_act_changed": {k: v["share_pairs_act_trajectory_changed"] for k, v in d4["interfaces"].items() if "skipped" not in v},
}
sim = {}
for rates in ((0.95, 0.95, 0.5, 0.5), (0.95, 0.95, 0.9, 0.9)):
    gs = torch.Generator().manual_seed(5)
    eff = torch.tensor([0.05, 0.05, 0.0, 0.0], dtype=torch.double).repeat(20000)  # exact means
    reach_q = torch.rand(80000, generator=gs) < torch.tensor(rates).repeat(20000)
    sim[str(rates)] = {"question_level_mean": float(eff[reach_q].mean()),
                       "complete_family_mean": float(eff[complete(reach_q)].mean())}
res["4_d4_selection_simulation"] = sim
vals = list(sim.values())
if not (abs(vals[0]["complete_family_mean"] - 0.025) < 1e-9 and abs(vals[1]["complete_family_mean"] - 0.025) < 1e-9
        and abs(vals[0]["question_level_mean"] - vals[1]["question_level_mean"]) > 0.002):
    fail.append("4 simulation")


# ---------------------------------------------------------------- 5
def iface(tv=0.001, skipped=False, n_reach=2000, n_inc=2000, n_not=0, i0_neg=True):
    cov = {"n_reachable_questions": n_reach, "n_included_questions": n_inc, "n_included_bodies": n_inc // 4,
           "n_reachable_not_evaluated": n_not}
    if skipped:
        return {"skipped": "x", "coverage": cov}
    return {"tv": {"mean": tv}, "indistinguishable": {"tv": False}, "coverage": cov,
            "I0_same_subset_negligible": i0_neg, "included_question_index": list(range(n_inc))}


def d4r(ifs, i0_tv=0.001):
    I = {"I0:emb@17": iface(i0_tv)} | ifs
    return {"D4": {"interfaces": I, "I0_all_questions": {"tv": {"mean": i0_tv}}, "noise_eps": {"tv": 1e-7}}}


h1 = {
    "no I2 evaluated": h1_d4(d4r({"I2:e@18": iface(skipped=True, n_reach=0, n_not=0)}))[0],
    "coverage gap (skipped, reachable)": h1_d4(d4r({"I2:e@18": iface(), "I2/I3:h3@18": iface(skipped=True, n_reach=300, n_not=300)}))[0],
    "evaluated but reachable pairs excluded": h1_d4(d4r({"I2:e@18": iface(), "I2/I3:h2@18": iface(n_reach=1500, n_inc=1200, n_not=300)}))[0],
    "skipped interface with no reachable pair": h1_d4(d4r({"I2:e@18": iface(), "I2/I3:h4@18": iface(skipped=True, n_reach=0, n_not=0)}))[0],
    "fully covered, negligible": h1_d4(d4r({"I2:e@18": iface(), "I2:coda_out@18": iface()}))[0],
    "subset I0 not negligible": h1_d4(d4r({"I2:e@18": iface(i0_neg=False)}))[0],
    "evaluated I2 with TV >= 0.02": h1_d4(d4r({"I2:e@18": iface(tv=0.03), "I2/I3:h3@18": iface(skipped=True, n_reach=300, n_not=300)}))[0],
}
exp1 = {"no I2 evaluated": UNC, "coverage gap (skipped, reachable)": UNC, "evaluated but reachable pairs excluded": UNC,
        "skipped interface with no reachable pair": SUP, "fully covered, negligible": SUP,
        "subset I0 not negligible": UNC, "evaluated I2 with TV >= 0.02": OPP}
rng = np.random.default_rng(0)
probe = {"decision": "检测到可线性解码的信息", "baseline_c_hi": 0.25, "baseline_c0": 0.25,
         "eval_question_index": list(range(2000)),
         "eval_correct": [int(v) for v in (rng.random(2000) < np.where(np.arange(2000) < 1000, 0.95, 0.05))],
         "eval_correct_shuffled": [int(v) for v in (rng.random(2000) < 0.25)]}
probe_d2 = {"D2": {"probes": {"P1@h_out": probe, "P3@h_out": {"decision": "x"}}}}
first_half, second_half = list(range(1000)), list(range(1000, 2000))
h4 = {
    "interface skipped": h4_d4(d4r({"I2/I3:h_out@18": iface(skipped=True)}) | probe_d2, ["h_out"])[0],
    "not confirmed on subset": h4_d4(d4r({"I2/I3:h_out@18": iface() | {"included_question_index": second_half}}) | probe_d2, ["h_out"])[0],
    "confirmed, negligible": h4_d4(d4r({"I2/I3:h_out@18": iface() | {"included_question_index": first_half}}) | probe_d2, ["h_out"])[0],
    "confirmed, TV >= 0.02": h4_d4(d4r({"I2/I3:h_out@18": iface(tv=0.05) | {"included_question_index": first_half}}) | probe_d2, ["h_out"])[0],
}
exp4 = {"interface skipped": UNC, "not confirmed on subset": UNC, "confirmed, negligible": SUP, "confirmed, TV >= 0.02": OPP}
repro = rescore(probe, first_half) == rescore(copy.deepcopy(probe), first_half)
res["5_grading"] = {"H1": {k: {"got": v, "expected": exp1[k]} for k, v in h1.items()},
                    "H4": {k: {"got": v, "expected": exp4[k]} for k, v in h4.items()},
                    "rescore_reproducible": repro}
if any(v != exp1[k] for k, v in h1.items()) or any(v != exp4[k] for k, v in h4.items()) or not repro:
    fail.append("5")

res["failures"] = fail
with open(os.path.join(HERE, "validation", "rev6_tests.json"), "w") as f:
    json.dump(res, f, indent=1, ensure_ascii=False)
print(json.dumps(res, indent=1, ensure_ascii=False))
sys.exit(1 if fail else 0)
