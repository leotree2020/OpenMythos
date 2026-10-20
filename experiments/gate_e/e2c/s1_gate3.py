#!/usr/bin/env python3
"""
Stage 1, gate 3: V1 pairing integrity and auxiliary supervision (E2C_PREREG_DRAFT
3.5, 6). Run only after gates 1 and 2 passed. Non-formal seed 99, both arms,
300 updates (the early window W), lambda = lambda2 = 0.1 (the value plays no
role in these identities).

    common C0 / C1 / C2   step-0 parameter sha256 and step-0 checkpoints
                          bitwise; batch hash chain at 100, 200, 300; first-
                          batch hash; learning-rate schedule hash; optimizer
                          settings; clip; batch size
    C1 / C2 only          head sha256 per record point (also against a fresh
                          recomputation); record points; positions; mask
    C1 only / C2 only     lambda as configured; C2 digit code sha256 equal to
                          Random(80000 + seed) recomputed
    restart (C2)          attempt 1 stopped after update 150 (simulated
                          interruption, exit 9), quarantined; the full re-run
                          must equal it on the overlap: checkpoints 0-150,
                          batch chain at 100, r_u, kappa_u, auxiliary and task
                          losses of updates 1-150, ACT log, parameter-level
                          norms; digit code sha256 of both starts equal
    recomputation         s1_recompute.py twice in separate processes, from the
                          checkpoints of steps 9, 99, 199, 299 and the batches
                          of updates 10, 100, 200, 300: r_u, kappa_u, losses,
                          parameter-level norm, pre-clip gradient norm, loops
                          and ACT statistics identical to each other and to
                          the run's record
    s1_v1_aux.py          record points equal to gate_d's Runner; heads not in
                          the optimizer and unchanged by training; gradient
                          scope of L_aux; labels
Exit 0 if all pass; 3 otherwise (F8 for a pairing / restart inconsistency, F3).
"""

import json
import os
import shutil
import sys

import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import e2c_common as C  # noqa: E402
from s1_budget import STAGE1, Ledger, run_pool  # noqa: E402

OUT = os.path.join(STAGE1, "gate3")
SEED, STEPS, LAM = C.IMPL_SEED, 300, "0.1"
SAVE = (9, 25, 50, 75, 99, 100, 150, 199, 200, 250, 299, 300)
KS = (9, 99, 199, 299)
ARMS = ("openmythos", "transformer")
PY = sys.executable


def tr(arm, cond, ckdir, out, extra=()):
    a = [PY, os.path.join(HERE, "train_e2c.py"), "--cond", cond, "--arm", arm, "--seed", str(SEED), "--steps", str(STEPS),
         "--save-at", ",".join(map(str, SAVE)), "--ckpt-dir", ckdir, "--out", out]
    return a + (["--lam", LAM] if cond != "C0" else []) + list(extra)


def phase_a():
    j = []
    for arm in ARMS:
        for cond in C.CONDS:
            j.append((f"run_{cond}_{arm}", tr(arm, cond, f"{OUT}/ckpt", f"{OUT}/run_{cond}_{arm}.json")))
        att = tr(arm, "C2", f"{OUT}/attempt1/ckpt", f"{OUT}/attempt1/run_C2_{arm}.json", ["--stop-after", "150"])
        j.append((f"attempt1_C2_{arm}", ["sh", "-c", " ".join(att) + "; test $? -eq 9"]))
    return j


def phase_b():
    j = []
    for arm in ARMS:
        for cond in ("C1", "C2"):
            for rep in ("a", "b"):
                j.append((f"recompute_{cond}_{arm}_{rep}",
                          [PY, os.path.join(HERE, "s1_recompute.py"), "--cond", cond, "--lam", LAM, "--arm", arm, "--seed", str(SEED),
                           "--ckpt-dir", f"{OUT}/ckpt", "--ks", ",".join(map(str, KS)), "--out", f"{OUT}/recompute_{cond}_{arm}_{rep}.json"]))
        j.append((f"aux_{arm}", [PY, os.path.join(HERE, "s1_v1_aux.py"), "--arm", arm,
                                 "--ckpt", f"{OUT}/ckpt/C1_{arm}_s{SEED}_step300.pt", "--out", f"{OUT}/aux_{arm}.json"]))
    return j


def sd(path):
    return torch.load(path, map_location="cpu", weights_only=False)["model"]


def analyse(arm):
    R = {c: json.load(open(f"{OUT}/run_{c}_{arm}.json")) for c in C.CONDS}
    common_keys = ("init_param_sha256", "batch_chain", "first_batch_sha256", "lr_schedule_sha256", "optimizer", "clip", "batch_size")
    common = {k: all(R[c][k] == R["C0"][k] for c in C.CONDS) for k in common_keys}
    common["step0_checkpoints_bitwise"] = all(C.state_dict_equal(sd(f"{OUT}/ckpt/C0_{arm}_s{SEED}_step0.pt"),
                                                                 sd(f"{OUT}/ckpt/{c}_{arm}_s{SEED}_step0.pt")) for c in ("C1", "C2"))
    fresh = dict(zip(C.RECORD_POINTS[arm], C.heads_sha(C.make_heads(arm, SEED, 128))))
    c12 = {"heads_sha256_equal": R["C1"]["heads_sha256"] == R["C2"]["heads_sha256"] == fresh,
           "record_points_equal": R["C1"]["record_points"] == R["C2"]["record_points"] == list(C.RECORD_POINTS[arm]),
           "positions_equal": R["C1"]["positions"] == R["C2"]["positions"] == list(C.DIGIT_POS),
           "mask_equal": R["C1"]["mask"] == R["C2"]["mask"]}
    own = {"C1_lambda": R["C1"]["lam"] == float(LAM), "C2_lambda2": R["C2"]["lam"] == float(LAM),
           "C2_digit_code_sha256": R["C2"]["digit_code_sha256"] == C.code_sha(C.digit_code(SEED))}
    # restart consistency (quarantined attempt 1 against the full re-run)
    A = json.load(open(f"{OUT}/quarantine/attempt1/run_C2_{arm}.json.progress.json"))
    F = R["C2"]
    n = 150
    rs = {"attempt_stopped_at": len(A["r_u"]),
          "digit_code_sha256_equal": A["digit_code_sha256"] == F["digit_code_sha256"],
          "checkpoints_0_150_bitwise": all(C.state_dict_equal(sd(f"{OUT}/quarantine/attempt1/ckpt/C2_{arm}_s{SEED}_step{t}.pt"),
                                                              sd(f"{OUT}/ckpt/C2_{arm}_s{SEED}_step{t}.pt")) for t in (0,) + SAVE if t <= n),
          "batch_chain_100": A["batch_chain"].get("100") == F["batch_chain"]["100"],
          "r_u_1_150": A["r_u"] == F["r_u"][:n], "kappa_u_1_150": A["kappa_u"] == F["kappa_u"][:n],
          "aux_loss_1_150": A["aux_loss_every_step"] == F["aux_loss_every_step"][:n],
          "task_loss_1_150": A["loss_every_step"] == F["loss_every_step"][:n],
          "act_log": A["act_log"] == [x for x in F["act_log"] if x["step"] <= n],
          "param_aux_grad_norm": A["param_aux_grad_norm"] == [x for x in F["param_aux_grad_norm"] if x["step"] <= n]}
    rs["pass"] = rs["attempt_stopped_at"] == n and all(v for k, v in rs.items() if isinstance(v, bool))
    # recomputation
    rec = {}
    for cond in ("C1", "C2"):
        a = json.load(open(f"{OUT}/recompute_{cond}_{arm}_a.json"))
        b = json.load(open(f"{OUT}/recompute_{cond}_{arm}_b.json"))
        run = R[cond]
        per = {}
        for k in KS:
            u = str(k + 1)
            x = a[u]
            light = next(e for e in run["light_log"] if e["step"] == k + 1)
            pn = next(e for e in run["param_aux_grad_norm"] if e["step"] == k + 1)
            act = next((e for e in run["act_log"] if e["step"] == k + 1), None)
            per[u] = {"two_recomputations_identical": a[u] == b[u],
                      "r_u": x["r_u"] == run["r_u"][k], "kappa_u": x["kappa_u"] == run["kappa_u"][k],
                      "aux_loss": x["aux_loss"] == run["aux_loss_every_step"][k], "task_loss": x["task_loss"] == run["loss_every_step"][k],
                      "grad_norm_preclip": x["grad_norm_preclip"] == light["grad_norm_preclip"],
                      "param_aux_grad_norm": x["param_aux_grad_norm"] == pn["norm"],
                      "loops": arm != "openmythos" or x["loops"] == run["loops_every_step"][k],
                      "act": arm != "openmythos" or (act is not None and x["act"] == {kk: act[kk] for kk in x["act"]})}
        rec[cond] = {"per_update": per, "pass": all(all(v.values()) for v in per.values())}
    aux = json.load(open(f"{OUT}/aux_{arm}.json"))
    out = {"common_C0_C1_C2": common, "C1_C2": c12, "own": own, "restart_C2": rs, "recompute": rec, "aux_checks": aux}
    out["pass"] = (all(common.values()) and all(c12.values()) and all(own.values()) and rs["pass"]
                   and all(v["pass"] for v in rec.values()) and aux["pass"])
    return out


def main():
    led = Ledger()
    os.makedirs(OUT, exist_ok=True)
    res = {"seed": SEED, "updates": STEPS, "lambda": float(LAM)}
    with led.job("gate3") as job:
        st, info = run_pool(phase_a(), job, width=4, log_dir=os.path.join(OUT, "logs"))
        res["pool_a"] = [st, info]
        if st == "ok":
            os.makedirs(f"{OUT}/quarantine", exist_ok=True)
            shutil.move(f"{OUT}/attempt1", f"{OUT}/quarantine/attempt1")
            st, info = run_pool(phase_b(), job, width=4, log_dir=os.path.join(OUT, "logs"))
            res["pool_b"] = [st, info]
    if st != "ok":
        res["pass"] = False
        json.dump(res, open(os.path.join(OUT, "gate3.json"), "w"), indent=1)
        print(json.dumps(res, indent=1))
        sys.exit(7 if st == "cap" else 3)
    for arm in ARMS:
        res[arm] = analyse(arm)
    res["pass"] = all(res[a]["pass"] for a in ARMS)
    res["stage1_ledger_seconds"] = led.total()
    json.dump(res, open(os.path.join(OUT, "gate3.json"), "w"), indent=1)
    print(json.dumps({a: {k: (v.get("pass") if isinstance(v, dict) and "pass" in v else
                              (all(v.values()) if isinstance(v, dict) else v)) for k, v in res[a].items()} for a in ARMS}, indent=1))
    print("GATE 3", "PASS" if res["pass"] else "FAIL", f"ledger {led.total():.0f} s")
    sys.exit(0 if res["pass"] else 3)


if __name__ == "__main__":
    main()
