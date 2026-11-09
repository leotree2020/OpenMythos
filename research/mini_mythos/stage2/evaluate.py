#!/usr/bin/env python3
"""Stage 2 native evaluation on the device and agreement with the Stage 1 CPU baseline.

  python -B evaluate.py --sets SETS --cpu-reference STAGE1/per_window.csv --out DIR

Writes native_dev.csv (FP32), native_dev_bf16.csv, agreement.json. Agreement (acceptance 1):
per window, the replica-mean NLL difference GPU-FP32 minus CPU: mean |diff| < 0.001 and
max |diff| < 0.01. bf16-vs-FP32 differences are reported only. Exit 1 if agreement fails.
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gpu_common as G  # noqa: E402


def diffs(a, b, keys):
    d = np.array([np.mean(a[k]) - np.mean(b[k]) for k in keys])
    return {"windows": len(d), "mean_abs": float(np.abs(d).mean()), "max_abs": float(np.abs(d).max()),
            "mean_signed": float(d.mean())}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sets", required=True)
    p.add_argument("--cpu-reference", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--upstream", default=G.s0.DEFAULTS["upstream"])
    p.add_argument("--model-dir", default=G.s0.DEFAULTS["model_dir"])
    p.add_argument("--tokenizer", default=G.s0.DEFAULTS["tokenizer"])
    p.add_argument("--device", default="cuda")
    p.add_argument("--threads", type=int, default=4)
    p.add_argument("--no-pin-check", action="store_true")
    args = p.parse_args()
    torch = G.setup(args.device, args.threads)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    model, state = G.load_model(torch, args.upstream, args.model_dir, args.tokenizer, args.device,
                                pin_check=not args.no_pin_check)
    windows = G.load_windows(args.sets, "dev")
    t = time.time()
    fp32 = G.evaluate(torch, model, windows, args.device)
    fp32_s = time.time() - t
    t = time.time()
    bf16 = G.evaluate(torch, model, windows, args.device, bf16=True)
    bf16_s = time.time() - t
    G.write_per_window(out / "native_dev.csv", fp32, windows)
    G.write_per_window(out / "native_dev_bf16.csv", bf16, windows)
    cpu = G.read_per_window(args.cpu_reference)
    keys = [w["doc_id"] for w in windows]
    missing = [k for k in keys if k not in cpu]
    if missing:
        raise SystemExit("CPU reference lacks %d dev windows (e.g. %s)" % (len(missing), missing[:3]))
    by_domain = {}
    for w in windows:
        by_domain.setdefault(w["domain"], []).append(w["doc_id"])
    agree = {"all": diffs(fp32, cpu, keys), "by_domain": {d: diffs(fp32, cpu, k) for d, k in by_domain.items()},
             "bf16_minus_fp32": {d: diffs(bf16, fp32, k) for d, k in by_domain.items()},
             "eval_tokens_per_s_fp32": 2 * len(windows) * G.WINDOW / fp32_s,
             "eval_tokens_per_s_bf16": 2 * len(windows) * G.WINDOW / bf16_s,
             "device": torch.cuda.get_device_name() if args.device.startswith("cuda") else "cpu",
             "state_check": state, "native_dev_domain_mean_nll": G.domain_means(fp32, windows)}
    agree["pass"] = agree["all"]["mean_abs"] < 0.001 and agree["all"]["max_abs"] < 0.01
    G.s0.write_json(out / "agreement.json", agree)
    print(json.dumps(agree, indent=1))
    return 0 if agree["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
