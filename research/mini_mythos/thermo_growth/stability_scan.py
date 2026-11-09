#!/usr/bin/env python3
"""Per-window stability of finished growth runs: does the recurrence blow up on some inputs?

Means hide it: one window whose hidden state diverges can cost several nats while every average
looks fine. For each run the final model (final_space.pt, plus final_base.pt if Parcae was unfrozen)
is scored on every check window (dev windows, the read books' tails, held-out books) and compared
with the native Parcae window by window: NLL difference and the ratio of the largest hidden-state
norm (input of ln_f) to the native one.

  python -B stability_scan.py --data BOOKS --sets EVAL_SETS --upstream P --model-dir M --tokenizer T \
      --out scan.json RUN_DIR...
"""
import argparse
import copy
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "stage2"))
import books as BK  # noqa: E402
import gpu_common as G  # noqa: E402

_spec = importlib.util.spec_from_file_location("grow_mod", HERE / "grow.py")
GR = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(GR)


def scored(torch, model, windows, device):
    """({doc_id: nll}, [largest hidden norm per window])"""
    seen = []
    handle = model.transformer.ln_f.register_forward_hook(
        lambda mod, inputs, output: seen.append(inputs[0].detach().norm(dim=-1).amax(dim=1)))
    try:
        s = GR.score(torch, model, windows, device)
    finally:
        handle.remove()
    return s, torch.cat(seen).tolist()


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("runs", nargs="+")
    p.add_argument("--data", required=True)
    p.add_argument("--sets", required=True)
    p.add_argument("--upstream", default=G.s0.DEFAULTS["upstream"])
    p.add_argument("--model-dir", default=G.s0.DEFAULTS["model_dir"])
    p.add_argument("--tokenizer", default=G.s0.DEFAULTS["tokenizer"])
    p.add_argument("--device", default="cpu")
    p.add_argument("--threads", type=int, default=4)
    p.add_argument("--per-domain", type=int, default=25)
    p.add_argument("--threshold", type=float, default=0.5, help="NLL difference that counts as a blow-up")
    p.add_argument("--out", required=True)
    p.add_argument("--no-pin-check", action="store_true")
    args = p.parse_args()
    torch = G.setup(args.device, args.threads)
    import knowledge_space as KS
    base, _ = G.load_model(torch, args.upstream, args.model_dir, args.tokenizer, args.device,
                           pin_check=not args.no_pin_check)
    for prm in base.parameters():
        prm.requires_grad_(False)
    _, rows = BK.load(args.data)
    windows = GR.eval_windows(args.sets, rows, args.per_domain, BK.load_heldout(args.data))
    native, native_norm = scored(torch, base, windows, args.device)
    out = {}
    for run in args.runs:
        run = Path(run)
        model = copy.deepcopy(base)
        if (run / "final_base.pt").exists():
            model.load_state_dict(torch.load(run / "final_base.pt", weights_only=True), strict=True)
        ks = KS.KnowledgeSpace(model, k_max=max(256, int(torch.load(run / "final_space.pt", weights_only=True)["k"])))
        ks.load_state(torch.load(run / "final_space.pt", weights_only=True))
        s, norm = scored(torch, model, windows, args.device)
        rowsd = [(s[w["doc_id"]] - native[w["doc_id"]], w["doc_id"], norm[i] / native_norm[i])
                 for i, w in enumerate(windows)]
        bad = sorted((r for r in rowsd if r[0] > args.threshold), reverse=True)
        out[run.name] = {"windows": len(rowsd), "k": ks.k,
                         "blow_ups": [{"window": b[1], "nll_diff": b[0], "hidden_norm_ratio": b[2]} for b in bad],
                         "max_nll_diff": max(r[0] for r in rowsd),
                         "max_hidden_norm_ratio": max(r[2] for r in rowsd),
                         "median_nll_diff": sorted(r[0] for r in rowsd)[len(rowsd) // 2]}
        print("%s: %d windows, %d blow-ups (> %.2f), max hidden-norm ratio %.2f, worst %+.2f" % (
            run.name, len(rowsd), len(bad), args.threshold, out[run.name]["max_hidden_norm_ratio"],
            out[run.name]["max_nll_diff"]), flush=True)
        ks.remove()
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
