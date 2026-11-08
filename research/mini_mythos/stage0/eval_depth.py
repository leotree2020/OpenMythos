#!/usr/bin/env python3
"""Stage 0 depth x BOS evaluation of native Parcae-140M (no training).

For every selected text: build one 256-token window from the document start, then score the
same 255 text tokens with and without a leading BOS, at depths 8/16/32, for R initial-state
replicas (paired: same seed across depths and BOS conditions). Rows are appended to
rows.jsonl as they finish, so an interrupted run resumes where it stopped (same config only).

  python -B eval_depth.py --texts DATA/texts.jsonl --out RUN_DIR
  python -B eval_depth.py --texts DATA/texts.jsonl --out RUN_DIR --limit 2   # quick smoke
"""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402  (sets nothing until setup_runtime is called)

SEED_BASE = 1_000_000


def parse():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--texts", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--upstream", default=common.DEFAULTS["upstream"])
    p.add_argument("--model-dir", default=common.DEFAULTS["model_dir"])
    p.add_argument("--tokenizer", default=common.DEFAULTS["tokenizer"])
    p.add_argument("--threads", type=int, default=2)
    p.add_argument("--replicas", type=int, default=2)
    p.add_argument("--depths", default="8,16,32")
    p.add_argument("--limit", type=int, default=0, help="use only the first N texts per domain (smoke)")
    p.add_argument("--no-pin-check", action="store_true", help="tests only: skip pinned-hash enforcement")
    return p.parse_args()


def load_texts(path, limit):
    rows, per_domain = [], {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            n = per_domain.get(row["domain"], 0)
            if limit and n >= limit:
                continue
            per_domain[row["domain"]] = n + 1
            rows.append(row)
    return rows


def main():
    args = parse()
    torch = common.setup_runtime(args.threads)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    depths = tuple(int(d) for d in args.depths.split(","))
    texts = load_texts(args.texts, args.limit)
    config = {"texts_sha256": common.sha256_file(args.texts), "limit": args.limit, "replicas": args.replicas,
              "depths": list(depths), "window": common.WINDOW, "seed_base": SEED_BASE,
              "model_dir": str(args.model_dir), "threads": args.threads}
    config_hash = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
    cfg_path = out / "config.json"
    if cfg_path.exists():
        old = json.loads(cfg_path.read_text())
        if old.get("config_hash") != config_hash:
            raise SystemExit("run directory holds a different configuration; use a new --out")
    pins = common.check_inputs(args.model_dir, args.tokenizer, strict=not args.no_pin_check)
    tok = common.load_tokenizer(args.tokenizer)

    windows, skipped = [], []
    for row in texts:
        if common.sha256_text(row["text"]) != row["text_sha256"]:
            raise SystemExit("text hash mismatch for %s" % row["doc_id"])
        ids = common.encode(tok, row["text"])
        if len(ids) < common.WINDOW + 1:
            skipped.append({"doc_id": row["doc_id"], "tokens": len(ids)})
            continue
        windows.append({"domain": row["domain"], "doc_id": row["doc_id"], "tokens": ids[:common.WINDOW + 1]})
    model, state_report = common.load_model(torch, args.upstream, args.model_dir)
    env = common.environment_facts(torch)
    if not cfg_path.exists():
        common.write_json(cfg_path, {"config": config, "config_hash": config_hash, "pins": pins,
                                     "state_check": state_report, "environment": env,
                                     "windows": len(windows), "skipped_short": skipped})

    # Determinism control: the same forward twice must give identical NLLs.
    w0 = windows[0]
    ids, pos, tgt = common.build_window(w0["tokens"], True)
    a, _ = common.token_nll(torch, model, ids, pos, tgt, depths[0], SEED_BASE)
    b, _ = common.token_nll(torch, model, ids, pos, tgt, depths[0], SEED_BASE)
    if a != b:
        raise SystemExit("determinism control failed: repeated forward differs")

    rows_path = out / "rows.jsonl"
    done = set()
    if rows_path.exists():
        with open(rows_path, encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                done.add((r["doc_id"], r["rep"], r["bos"], r["depth"]))
    total = len(windows) * args.replicas * 2 * len(depths)
    print("windows=%d skipped=%d forwards=%d already_done=%d" % (len(windows), len(skipped), total, len(done)), flush=True)
    start, finished = time.time(), 0
    with open(rows_path, "a", encoding="utf-8") as f:
        for wi, w in enumerate(windows):
            for rep in range(args.replicas):
                seed = SEED_BASE + 1000 * wi + rep
                for bos in (1, 0):
                    ids, pos, tgt = common.build_window(w["tokens"], bool(bos))
                    for depth in depths:
                        if (w["doc_id"], rep, bos, depth) in done:
                            continue
                        nll, seconds = common.token_nll(torch, model, ids, pos, tgt, depth, seed)
                        f.write(json.dumps({"domain": w["domain"], "doc_id": w["doc_id"], "rep": rep, "bos": bos,
                                            "depth": depth, "seed": seed, "seconds": seconds, "nll": nll}) + "\n")
                        f.flush()
                        finished += 1
            elapsed = time.time() - start
            if finished:
                remaining = total - len(done) - finished
                print("window %d/%d  elapsed %.0fs  eta %.0fs" % (wi + 1, len(windows), elapsed,
                                                                elapsed / finished * remaining), flush=True)
    print("done; rows in", rows_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
