#!/usr/bin/env python3
"""Stage 1 native baseline on the dev/test windows: depth 8, no BOS, R initial-state replicas.

  python -B baseline.py run    --sets DATA/eval_sets.jsonl --out RUN_DIR
  python    baseline.py report --out RUN_DIR

`run` appends one row per (window, replica) to rows.jsonl and can be resumed with the same
command; a lock file refuses a second concurrent run. `report` writes baseline.json/.md:
per domain and split the mean NLL over windows (primary scope t[65..255], as in Stage 0) with a
bootstrap 95% CI, and the noise floor from the random initial recurrent state.
"""
import argparse
import json
import math
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "stage0"))
import common                                   # noqa: E402  (Stage 0 helpers)
from eval_depth import read_rows_repairing_tail  # noqa: E402

SEED_BASE = 2_000_000
PRIMARY = slice(64, 255)
BOOT, BOOT_SEED = 10000, 20261108


def run(args):
    torch = common.setup_runtime(args.threads)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    lock = open(out / "run.lock", "w")
    try:
        import fcntl
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit("another baseline run is using %s" % out)
    with open(args.sets, encoding="utf-8") as f:
        windows = [json.loads(line) for line in f]
    if args.limit:
        keep, count = [], {}
        for w in windows:
            key = (w["domain"], w["split"])
            if count.get(key, 0) < args.limit:
                keep.append(w)
                count[key] = count.get(key, 0) + 1
        windows = keep
    config = {"sets_sha256": common.sha256_file(args.sets), "limit": args.limit, "replicas": args.replicas,
              "depth": args.depth, "bos": False, "seed_base": SEED_BASE, "threads": args.threads}
    cfg_path = out / "config.json"
    if cfg_path.exists() and json.loads(cfg_path.read_text())["config"] != config:
        raise SystemExit("run directory holds a different configuration; use a new --out")
    pins = common.check_inputs(args.model_dir, args.tokenizer, strict=not args.no_pin_check)
    model, state = common.load_model(torch, args.upstream, args.model_dir)
    if not cfg_path.exists():
        common.write_json(cfg_path, {"config": config, "pins": pins, "state_check": state,
                                     "environment": common.environment_facts(torch), "windows": len(windows)})
    rows_path = out / "rows.jsonl"
    done, spent = set(), 0.0
    if rows_path.exists():
        for r in read_rows_repairing_tail(rows_path):
            done.add((r["doc_id"], r["rep"]))
            spent += r["seconds"]
    total = len(windows) * args.replicas
    print("windows=%d forwards=%d already_done=%d" % (len(windows), total, len(done)), flush=True)
    start, finished = time.time(), 0
    with open(rows_path, "a", encoding="utf-8") as f:
        for wi, w in enumerate(windows):
            ids, pos, tgt = common.build_window(w["tokens"], False)
            for rep in range(args.replicas):
                if (w["doc_id"], rep) in done:
                    continue
                if spent >= args.max_hours * 3600:
                    print("STOPPED at the %.1f h cap; rerun to continue" % args.max_hours, flush=True)
                    return 3
                seed = SEED_BASE + 1000 * wi + rep
                nll, seconds = common.token_nll(torch, model, ids, pos, tgt, args.depth, seed)
                spent += seconds
                f.write(json.dumps({"domain": w["domain"], "split": w["split"], "doc_id": w["doc_id"], "rep": rep,
                                    "seed": seed, "seconds": seconds, "nll": nll}) + "\n")
                f.flush()
                finished += 1
            if finished and (wi + 1) % 25 == 0:
                el = time.time() - start
                print("window %d/%d  elapsed %.0fs  eta %.0fs" % (wi + 1, len(windows), el,
                                                                el / finished * (total - len(done) - finished)), flush=True)
    print("done; rows in", rows_path)
    return 0


def report(args):
    import numpy as np
    out = Path(args.out)
    per = {}
    seen = {}
    secs = []
    with open(out / "rows.jsonl", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            key = (r["doc_id"], r["rep"])
            if key in seen:
                if seen[key] != r["nll"]:
                    raise SystemExit("conflicting duplicate rows for %s" % (key,))
                continue
            seen[key] = r["nll"]
            per.setdefault((r["domain"], r["split"], r["doc_id"]), {})[r["rep"]] = float(np.mean(r["nll"][PRIMARY]))
            secs.append(r["seconds"])
    reps = {len(v) for v in per.values()}
    if len(reps) != 1:
        raise SystemExit("incomplete run: windows have different replica counts %s" % sorted(reps))
    R = reps.pop()
    rng = np.random.default_rng(BOOT_SEED)
    result = {"replicas": R, "depth": json.loads((out / "config.json").read_text())["config"]["depth"],
              "bos": False, "groups": {}, "median_seconds_per_forward": float(np.median(secs)),
              "tokens_per_second": 256 / float(np.median(secs))}
    for domain, split in sorted({(k[0], k[1]) for k in per}):
        vals = [per[k] for k in sorted(per) if k[0] == domain and k[1] == split]
        means = np.array([np.mean(list(v.values())) for v in vals])
        idx = rng.integers(0, len(means), size=(BOOT, len(means)))
        boots = np.sort(means[idx].mean(axis=1))
        g = {"windows": len(means), "mean_nll": float(means.mean()), "ppl": math.exp(float(means.mean())),
             "ci95": [float(boots[int(0.025 * BOOT)]), float(boots[int(0.975 * BOOT) - 1])],
             "between_window_sd": float(means.std(ddof=1)) if len(means) > 1 else None}
        if R >= 2:
            d = np.array([v[0] - v[1] for v in vals])
            sigma = float(d.std(ddof=1) / math.sqrt(2)) if len(d) > 1 else None   # per-replica h0 noise SD
            g["replica_noise_sd"] = sigma
            g["h0_noise_se_of_mean"] = sigma / math.sqrt(R * len(means)) if sigma is not None else None
        result["groups"]["%s/%s" % (domain, split)] = g
    (out / "baseline.json").write_text(json.dumps(result, indent=1) + "\n")
    lines = ["# Stage 1 native baseline", "",
             "Depth %d, no BOS, %d replicas, primary scope t[65..255]; %.0f tokens/s per 256-token forward." % (
                 result["depth"], R, result["tokens_per_second"]), "",
             "| domain/split | windows | mean NLL | 95% CI | ppl | between-window SD | replica noise SD | h0-noise SE of mean |",
             "|---|---:|---:|---|---:|---:|---:|---:|"]
    for name, g in result["groups"].items():
        lines.append("| %s | %d | %.4f | [%.4f, %.4f] | %.2f | %s | %s | %s |" % (
            name, g["windows"], g["mean_nll"], g["ci95"][0], g["ci95"][1], g["ppl"],
            "%.4f" % g["between_window_sd"] if g["between_window_sd"] is not None else "-",
            "%.5f" % g["replica_noise_sd"] if g.get("replica_noise_sd") is not None else "-",
            "%.5f" % g["h0_noise_se_of_mean"] if g.get("h0_noise_se_of_mean") is not None else "-"))
    (out / "baseline.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--sets", required=True)
    r.add_argument("--out", required=True)
    r.add_argument("--upstream", default=common.DEFAULTS["upstream"])
    r.add_argument("--model-dir", default=common.DEFAULTS["model_dir"])
    r.add_argument("--tokenizer", default=common.DEFAULTS["tokenizer"])
    r.add_argument("--threads", type=int, default=2)
    r.add_argument("--replicas", type=int, default=2)
    r.add_argument("--depth", type=int, default=8)
    r.add_argument("--limit", type=int, default=0, help="first N windows per domain/split (smoke)")
    r.add_argument("--max-hours", type=float, default=3.0)
    r.add_argument("--no-pin-check", action="store_true")
    q = sub.add_parser("report")
    q.add_argument("--out", required=True)
    args = p.parse_args()
    return run(args) if args.cmd == "run" else report(args)


if __name__ == "__main__":
    sys.exit(main())
