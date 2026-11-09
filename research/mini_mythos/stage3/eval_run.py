#!/usr/bin/env python3
"""Stage 3 evaluation of a trained run, of the native model, or of MoDA-P at initialisation.
FP32, no BOS, CPU-seeded h0, exactly like Stage 1/2.

  python -B eval_run.py --run RUN --split test --out RUN/eval_test.csv       # trained mechanism / control
  python -B eval_run.py --native --split dev --depth 16 --out native_d16.csv  # native model
  python -B eval_run.py --moda-init --split dev --compare native_dev.csv --out moda_init.csv
      # MoDA-P with all gates 0 must reproduce the native scores (max |diff| <= 1e-6), else exit 1

Writes OUT (per-window CSV) and OUT with .json (domain means, timing, MoDA statistics).
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "stage2"))
import gpu_common as G  # noqa: E402
import mechanisms as M  # noqa: E402


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    who = p.add_mutually_exclusive_group(required=True)
    who.add_argument("--run")
    who.add_argument("--native", action="store_true")
    who.add_argument("--moda-init", action="store_true")
    p.add_argument("--split", choices=["dev", "test"], required=True)
    p.add_argument("--depth", type=int, default=8)
    p.add_argument("--compare", help="per-window CSV the result must reproduce (with --moda-init)")
    p.add_argument("--sets", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--upstream", default=G.s0.DEFAULTS["upstream"])
    p.add_argument("--model-dir", default=G.s0.DEFAULTS["model_dir"])
    p.add_argument("--tokenizer", default=G.s0.DEFAULTS["tokenizer"])
    p.add_argument("--device", default="cuda")
    p.add_argument("--threads", type=int, default=4)
    p.add_argument("--no-pin-check", action="store_true")
    args = p.parse_args()
    torch = G.setup(args.device, args.threads)
    model, _ = G.load_model(torch, args.upstream, args.model_dir, args.tokenizer, args.device,
                            pin_check=not args.no_pin_check)
    for prm in model.parameters():
        prm.requires_grad_(False)
    mech, what = None, "native"
    if args.run:
        cfg = json.loads((Path(args.run) / "config.json").read_text())["config"]
        mech = M.attach(torch, model, cfg["mode"], rank=cfg["rank"], alpha=cfg["alpha"], seed=cfg["seed"])
        M.load_params(torch, mech, Path(args.run) / "final_params.pt")
        what = "run " + Path(args.run).name
    elif args.moda_init:
        mech = M.attach(torch, model, "moda")
        what = "moda at initialisation"
    if mech is not None and hasattr(mech, "collect_stats"):
        mech.collect_stats = True
    windows = G.load_windows(args.sets, args.split)
    t = time.time()
    per = G.evaluate(torch, model, windows, args.device, depth=args.depth)
    seconds = time.time() - t
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    G.write_per_window(out, per, windows)
    info = {"what": what, "split": args.split, "depth": args.depth, "windows": len(windows), "seconds": seconds,
            "domain_mean_nll": G.domain_means(per, windows)}
    if mech is not None and hasattr(mech, "summary_stats"):
        info["moda_stats"] = mech.summary_stats()
    rc = 0
    if args.compare:
        ref = G.read_per_window(args.compare)
        d = np.array([abs(a - b) for w in windows for a, b in zip(per[w["doc_id"]], ref[w["doc_id"]])])
        info["compare"] = {"against": str(args.compare), "max_abs_diff": float(d.max()), "pass": bool(d.max() <= 1e-6)}
        rc = 0 if info["compare"]["pass"] else 1
    out.with_suffix(".json").write_text(json.dumps(info, indent=1) + "\n")
    print(json.dumps(info, indent=1))
    return rc


if __name__ == "__main__":
    sys.exit(main())
