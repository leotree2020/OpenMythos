#!/usr/bin/env python3
"""Stage S: dev NLL of one Parcae size at several recurrence depths (FP32, no BOS, CPU-seeded h0,
2 replicas; the Stage 1 dev windows and scoring). The weights must match models.json (sha256) and
load bit-exactly (full tensor check).

  python -B nll_eval.py --size parcae-370m --model-dir DIR --sets eval_sets.jsonl --depths 4,8,16,32 --out OUT
      [--cpu-reference STAGE1/per_window.csv]     # for parcae-140m: depth 8 must agree with Stage 1

Writes OUT/nll_d{depth}.csv and OUT/nll.json.
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "stage2"))
import gpu_common as G  # noqa: E402


def check_weights(size, model_dir):
    spec = json.loads((HERE / "models.json").read_text())[size]
    got = G.s0.sha256_file(Path(model_dir) / "pytorch_model.bin")
    if got != spec["weights_sha256"]:
        raise SystemExit("%s: weights sha256 %s differs from models.json" % (size, got))
    return spec


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--size", required=True)
    p.add_argument("--model-dir", required=True)
    p.add_argument("--sets", required=True)
    p.add_argument("--depths", default="4,8,16,32")
    p.add_argument("--out", required=True)
    p.add_argument("--cpu-reference")
    p.add_argument("--upstream", default=G.s0.DEFAULTS["upstream"])
    p.add_argument("--tokenizer", default=G.s0.DEFAULTS["tokenizer"])
    p.add_argument("--device", default="cuda")
    p.add_argument("--threads", type=int, default=4)
    p.add_argument("--max-windows", type=int, default=0, help="testing only")
    args = p.parse_args()
    spec = check_weights(args.size, args.model_dir)
    torch = G.setup(args.device, args.threads)
    model, state = G.load_model(torch, args.upstream, args.model_dir, args.tokenizer, args.device, pin_check=False)
    windows = G.load_windows(args.sets, "dev")
    if args.max_windows:
        windows = windows[::max(1, len(windows) // args.max_windows)][:args.max_windows]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    info = {"size": args.size, "spec": spec, "state_check": {"entries": state["entries"], "all_equal": state["all_equal"]},
            "parameters": sum(p.numel() for p in model.parameters()), "windows": len(windows), "depths": {}}
    for depth in [int(d) for d in args.depths.split(",")]:
        t = time.time()
        per = G.evaluate(torch, model, windows, args.device, depth=depth)
        secs = time.time() - t
        G.write_per_window(out / ("nll_d%d.csv" % depth), per, windows)
        info["depths"][depth] = {"seconds": secs, "domain_mean_nll": G.domain_means(per, windows)}
        print("%s depth %d: %s (%.0f s)" % (args.size, depth, json.dumps(info["depths"][depth]["domain_mean_nll"]), secs),
              flush=True)
        if depth == 8 and args.cpu_reference:
            ref = G.read_per_window(args.cpu_reference)
            d = np.array([np.mean(per[w["doc_id"]]) - np.mean(ref[w["doc_id"]]) for w in windows])
            info["agreement_with_stage1_cpu"] = {"mean_abs": float(np.abs(d).mean()), "max_abs": float(np.abs(d).max())}
            if not (np.abs(d).mean() < 1e-3 and np.abs(d).max() < 1e-2):
                raise SystemExit("depth-8 NLL does not agree with the Stage 1 CPU baseline: %s"
                                 % info["agreement_with_stage1_cpu"])
    (out / "nll.json").write_text(json.dumps(info, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
