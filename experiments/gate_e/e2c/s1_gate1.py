#!/usr/bin/env python3
"""
Stage 1, gate 1: R1, R1', R1'' (E2C_PREREG_DRAFT 6). Non-formal seed 99, both
arms, 200 updates, checkpoints at 0, 25, ..., 200.

    R1    train_e2c.py C0 (records on) against E1's train_k.py --task k2:
          every checkpoint bitwise equal (state dict tensors and parameter
          hash); task loss of every update, light log, dev log and first-
          batch hash equal
    R1'   C1 with the head on detached states (--detach-aux, lambda 1.0)
          against C0: every checkpoint bitwise equal, task losses equal
    R1''  records on against records off (--no-records): C0, C1 (lambda 1.0)
          and C2 (lambda2 1.0): every checkpoint bitwise equal, task losses
          equal; for C1 / C2 also auxiliary loss, r_u and kappa_u equal
lambda 1.0 is the largest candidate; the value plays no role in these
identities. Exit 0 if all pass, 3 otherwise (F3; gate 2 is then not run).
"""

import json
import os
import sys

import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import e2c_common as C  # noqa: E402
from s1_budget import STAGE1, Ledger, run_pool  # noqa: E402

OUT = os.path.join(STAGE1, "gate1")
STEPS = 200
SAVE = list(range(25, STEPS + 1, 25))
SEED = C.IMPL_SEED
LAM = "1.0"
PY = sys.executable
GE = os.path.dirname(HERE)


def jobs():
    j = []
    for arm in ("openmythos", "transformer"):
        common = ["--arm", arm, "--seed", str(SEED), "--steps", str(STEPS), "--save-at", ",".join(map(str, SAVE))]
        j.append((f"trk_{arm}", [PY, os.path.join(GE, "train_k.py"), "--task", "k2", *common,
                                 "--ckpt-dir", f"{OUT}/trk", "--out", f"{OUT}/trk_{arm}.json"]))
        tr = [PY, os.path.join(HERE, "train_e2c.py")]
        for name, extra in (("c0", ["--cond", "C0"]), ("c0off", ["--cond", "C0", "--no-records"]),
                            ("c1det", ["--cond", "C1", "--lam", LAM, "--detach-aux"]),
                            ("c1on", ["--cond", "C1", "--lam", LAM]), ("c1off", ["--cond", "C1", "--lam", LAM, "--no-records"]),
                            ("c2on", ["--cond", "C2", "--lam", LAM]), ("c2off", ["--cond", "C2", "--lam", LAM, "--no-records"])):
            j.append((f"{name}_{arm}", tr + extra + common + ["--ckpt-dir", f"{OUT}/{name}", "--out", f"{OUT}/{name}_{arm}.json"]))
    return j


def ck(dirname, prefix, arm, step):
    return torch.load(os.path.join(OUT, dirname, f"{prefix}_{arm}_s{SEED}_step{step}.pt"), map_location="cpu",
                      weights_only=False)["model"]


def pair(arm, a, pa, b, pb, logs):
    """Checkpoint-by-checkpoint equality of runs a and b (dir, file prefix), plus log fields."""
    ra, rb = json.load(open(f"{OUT}/{a}_{arm}.json")), json.load(open(f"{OUT}/{b}_{arm}.json"))
    per = {}
    for s in [0] + SAVE:
        A, B = ck(a, pa, arm, s), ck(b, pb, arm, s)
        per[str(s)] = C.state_dict_equal(A, B)
    lg = {k: ra.get(k) == rb.get(k) and ra.get(k) is not None for k in logs}
    return {"checkpoints_equal": per, "logs_equal": lg, "final_param_sha256": [ra.get("final_param_sha256"),
            rb.get("final_param_sha256")], "pass": all(per.values()) and all(lg.values())}


def main():
    led = Ledger()
    os.makedirs(OUT, exist_ok=True)
    with led.job("gate1") as job:
        status, info = run_pool(jobs(), job, width=4, log_dir=os.path.join(OUT, "logs"))
    res = {"seed": SEED, "updates": STEPS, "checkpoints": [0] + SAVE, "lambda_used": float(LAM), "pool": [status, info]}
    if status != "ok":
        res["pass"] = False
        json.dump(res, open(os.path.join(OUT, "gate1.json"), "w"), indent=1)
        print(json.dumps(res, indent=1))
        sys.exit(7 if status == "cap" else 3)
    out = {}
    for arm in ("openmythos", "transformer"):
        r1 = pair(arm, "trk", "K2", "c0", "C0", ["loss_every_step", "light_log", "dev_log", "first_batch_sha256"])
        # train_k.py's record has no final parameter hash; compare it with the C0 checkpoint of the last step
        r1p = pair(arm, "c1det", "C1", "c0", "C0", ["loss_every_step", "dev_log", "batch_chain"])
        r2 = {"C0": pair(arm, "c0", "C0", "c0off", "C0", ["loss_every_step", "light_log", "dev_log", "kappa_u"]),
              "C1": pair(arm, "c1on", "C1", "c1off", "C1", ["loss_every_step", "light_log", "dev_log", "aux_loss_every_step",
                                                           "r_u", "kappa_u"]),
              "C2": pair(arm, "c2on", "C2", "c2off", "C2", ["loss_every_step", "light_log", "dev_log", "aux_loss_every_step",
                                                           "r_u", "kappa_u"])}
        rec_on = json.load(open(f"{OUT}/c1on_{arm}.json"))
        out[arm] = {"R1": r1, "R1_prime": r1p, "R1_double_prime": r2,
                    "evidence": {"c1det_aux_loss_first": json.load(open(f"{OUT}/c1det_{arm}.json"))["aux_loss_every_step"][:3],
                                 "c1on_param_aux_grad_norm_first": rec_on["param_aux_grad_norm"][:2],
                                 "c1on_r_u_first": rec_on["r_u"][:3], "c1_differs_from_c0_at_200":
                                 not C.state_dict_equal(ck("c1on", "C1", arm, 200), ck("c0", "C0", arm, 200))}}
        out[arm]["pass"] = r1["pass"] and r1p["pass"] and all(v["pass"] for v in r2.values())
    res.update(out)
    res["pass"] = all(out[a]["pass"] for a in out)
    res["stage1_ledger_seconds"] = led.total()
    json.dump(res, open(os.path.join(OUT, "gate1.json"), "w"), indent=1)
    print(json.dumps({a: {"R1": out[a]["R1"]["pass"], "R1'": out[a]["R1_prime"]["pass"],
                          "R1''": {k: v["pass"] for k, v in out[a]["R1_double_prime"].items()}} for a in out}, indent=1))
    print("GATE 1", "PASS" if res["pass"] else "FAIL", f"ledger {led.total():.0f} s")
    sys.exit(0 if res["pass"] else 3)


if __name__ == "__main__":
    main()
