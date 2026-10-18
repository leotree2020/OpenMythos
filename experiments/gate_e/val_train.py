#!/usr/bin/env python3
"""
Pre-run validation of the Gate E training code (PREREGISTRATION 6.1, 6.2,
9.6, 9.10), on the non-formal seed 99 only. Writes validation/train_checks.json;
exits non-zero if any check fails. Checkpoints go to a scratch directory
(--scratch) and are not kept.

  equivalence      train_k.py --task k4-equiv vs gen_gate_a/train_level.py
                   (--schedule extended), 200 steps, both arms: bitwise equal
  reproducibility  train_k.py --task k2 twice, 200 steps: every saved
                   checkpoint bitwise equal; step 0 equals the rebuild
  init pairing     build(arm, 2) and build(arm, 4) with the same seed: all
                   trainable parameters equal; RoPE buffers equal on 12 rows
  bridge command   train_level.py with --compare-tol 0 against a checkpoint of
                   the same trajectory: bitwise_equal true, accepted; against a
                   different checkpoint: aborted (exit 3), rejected
  bridge logic     e_bridge.accept on constructed records: passed true with
                   bitwise_equal false is rejected
"""

import argparse
import json
import os
import subprocess
import sys

import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from e_bridge import accept  # noqa: E402
from e_common import ROOT, jsonable, rebuild_init  # noqa: E402
from models import build  # noqa: E402

ENV = dict(os.environ, PYTHONPATH=os.path.abspath(ROOT))
TL = os.path.join(ROOT, "experiments", "gen_gate_a", "train_level.py")
TK = os.path.join(HERE, "train_k.py")


def sh(cmd):
    p = subprocess.run(cmd, cwd=os.path.abspath(ROOT), env=ENV, capture_output=True, text=True)
    return p.returncode, p.stdout[-2000:] + p.stderr[-2000:]


def sd(path):
    return torch.load(path, map_location="cpu", weights_only=False)["model"]


def equal_sd(a, b):
    return set(a) == set(b) and all(torch.equal(a[k], b[k]) for k in a)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scratch", required=True)
    args = ap.parse_args()
    S = os.path.abspath(args.scratch)
    os.makedirs(S, exist_ok=True)
    res, ok = {}, True
    for arm in ("openmythos", "transformer"):
        r = {}
        rc1, log1 = sh(["python", TL, "--level", "A", "--arm", arm, "--seed", "99", "--steps", "200",
                        "--schedule", "extended", "--save-at", "100", "--out", f"{S}/tl_{arm}.json"])
        rc2, log2 = sh(["python", TK, "--task", "k4-equiv", "--arm", arm, "--seed", "99", "--steps", "200",
                        "--save-at", "100,200", "--ckpt-dir", f"{S}/tk4_{arm}", "--out", f"{S}/tk4_{arm}.json"])
        r["exit_codes"] = [rc1, rc2]
        if rc1 or rc2:
            r["log"] = log1 + log2
            r["pass"] = False
        else:
            r["step100_bitwise"] = equal_sd(sd(f"{S}/tl_{arm}_step100.pt"), sd(f"{S}/tk4_{arm}/K4_{arm}_s99_step100.pt"))
            r["step200_bitwise"] = equal_sd(sd(f"{S}/tl_{arm}.pt"), sd(f"{S}/tk4_{arm}/K4_{arm}_s99_step200.pt"))
            r["first_batch_sha_equal"] = (json.load(open(f"{S}/tl_{arm}.json"))["first_batch_sha256"]
                                          == json.load(open(f"{S}/tk4_{arm}.json"))["first_batch_sha256"])
            r["pass"] = r["step100_bitwise"] and r["step200_bitwise"] and r["first_batch_sha_equal"]
        res[f"equivalence_{arm}"] = r
        ok &= r["pass"]

        r = {}
        outs = []
        for rep in ("a", "b"):
            rc, log = sh(["python", TK, "--task", "k2", "--arm", arm, "--seed", "99", "--steps", "200",
                          "--save-at", "25,100,200", "--ckpt-dir", f"{S}/k2{rep}_{arm}",
                          "--out", f"{S}/k2{rep}_{arm}.json"])
            outs.append(rc)
            if rc:
                r["log"] = log
        r["exit_codes"] = outs
        if any(outs):
            r["pass"] = False
        else:
            r["bitwise_by_step"] = {
                str(t): equal_sd(sd(f"{S}/k2a_{arm}/K2_{arm}_s99_step{t}.pt"),
                                 sd(f"{S}/k2b_{arm}/K2_{arm}_s99_step{t}.pt")) for t in (0, 25, 100, 200)}
            r["step0_equals_rebuild"] = equal_sd(sd(f"{S}/k2a_{arm}/K2_{arm}_s99_step0.pt"),
                                                 rebuild_init(arm, 2, 99).state_dict())
            log = json.load(open(f"{S}/k2a_{arm}.json"))
            r["loss_steps_logged"] = len(log["loss_every_step"])
            r["dev_log_steps"] = [d["step"] for d in log["dev_log"]]
            r["pass"] = all(r["bitwise_by_step"].values()) and r["step0_equals_rebuild"] \
                and r["loss_steps_logged"] == 200
        res[f"reproducibility_k2_{arm}"] = r
        ok &= r["pass"]

        torch.manual_seed(1)
        m4 = build(arm, 4)
        torch.manual_seed(1)
        m2 = build(arm, 2)
        p4, p2 = dict(m4.named_parameters()), dict(m2.named_parameters())
        b4, b2 = dict(m4.named_buffers()), dict(m2.named_buffers())
        r = {"trainable_equal": set(p4) == set(p2) and all(torch.equal(p4[k], p2[k]) for k in p4),
             "buffers": {k: {"shapes": [list(b4[k].shape), list(b2[k].shape)],
                             "first_rows_equal": bool(torch.equal(b4[k][: b2[k].shape[0]], b2[k]))}
                         for k in b4}}
        r["pass"] = r["trainable_equal"] and all(v["first_rows_equal"] for v in r["buffers"].values())
        res[f"init_pairing_{arm}"] = r
        ok &= r["pass"]

    # bridge command form on the non-formal seed: reference = 200-step run above
    arm = "transformer"
    ref = f"{S}/tl_{arm}.pt"
    cmd = ["python", TL, "--level", "A", "--arm", arm, "--seed", "99", "--steps", "200",
           "--schedule", "extended", "--save-at", "25,100", "--probe-every", "25",
           "--compare-at", "200", "--compare-ckpt", ref, "--compare-tol", "0",
           "--out", f"{S}/br_same.json"]
    rc, _ = sh(cmd)
    acc_same, why_same = accept(rc, f"{S}/br_same.json", f"{S}/br_same.pt", ref, arm)
    cmd_bad = [c if c != ref else f"{S}/tl_{arm}_step100.pt" for c in cmd]
    cmd_bad[cmd_bad.index(f"{S}/br_same.json")] = f"{S}/br_diff.json"
    rc_bad, _ = sh(cmd_bad)
    acc_bad, why_bad = accept(rc_bad, f"{S}/br_diff.json", f"{S}/br_diff.pt", f"{S}/tl_{arm}_step100.pt", arm)
    r = {"same_trajectory": {"exit": rc, "accepted": acc_same, "why": why_same},
         "different_reference": {"exit": rc_bad, "accepted": acc_bad, "why": why_bad,
                                 "abort_record": os.path.exists(f"{S}/br_diff_ABORTED.json")}}
    r["pass"] = acc_same and not acc_bad and rc_bad == 3
    res["bridge_command"] = r
    ok &= r["pass"]

    # bridge logic on constructed records: tolerance pass without bitwise equality
    fake = f"{S}/fake.json"
    with open(fake, "w") as f:
        json.dump({"comparability": {"bitwise_equal": False, "passed": True, "tolerance": 0,
                                     "max_abs_diff": 1e-7, "dev_predictions_identical": True}}, f)
    a1, w1 = accept(0, fake, ref, ref, arm)
    with open(fake, "w") as f:
        json.dump({"comparability": {"bitwise_equal": True, "passed": True, "tolerance": 1e-5}}, f)
    a2, w2 = accept(0, fake, ref, ref, arm)
    a3, w3 = accept(0, f"{S}/br_same.json", f"{S}/br_same.pt", f"{S}/tl_{arm}_step100.pt", arm)
    r = {"passed_true_bitwise_false": {"accepted": a1, "why": w1},
         "tolerance_not_zero": {"accepted": a2, "why": w2},
         "param_hash_mismatch": {"accepted": a3, "why": w3}}
    r["pass"] = not a1 and not a2 and not a3
    res["bridge_logic"] = r
    ok &= r["pass"]

    res["pass"] = ok
    os.makedirs(os.path.join(HERE, "validation"), exist_ok=True)
    with open(os.path.join(HERE, "validation", "train_checks.json"), "w") as f:
        json.dump(jsonable(res), f, indent=1)
    print(json.dumps({k: (v["pass"] if isinstance(v, dict) else v) for k, v in res.items()}, indent=1))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
