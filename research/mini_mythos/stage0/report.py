#!/usr/bin/env python3
"""Summarise eval_depth.py rows into summary.json and summary.md (numpy only, no torch).

Unit of analysis is the text window (replicas are averaged first). Token index i in a row's
`nll` list scores text token t[i+1]; the primary scope is t[65..255] (i >= 64, at least 64
tokens of context), the early scope is t[1..64] (where a missing BOS should matter most).

  python report.py --run RUN_DIR
"""
import argparse
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np

PRIMARY = slice(64, 255)
EARLY = slice(0, 64)
BOOT = 10000
BOOT_SEED = 20261108
ORACLE_EPS = 0.01   # nats: "cheapest depth within eps of the best depth for this text"
VERDICT_DOMAINS = ("wikitext", "c4")   # the two domains named in the frozen Stage 0 acceptance
TOKENS_PER_FORWARD = 256


def cost(depth):
    """Relative block calls of one forward: 2 prelude + 2 coda + 2 recurrent blocks per step."""
    return 4 + 2 * depth


def load(run):
    """Rows grouped by condition. A row repeated for the same (window, replica, BOS, depth) -
    e.g. two overlapping runs - is counted once if its NLLs are identical; differing repeats
    are an error, because the seed fixes the result."""
    per = defaultdict(list)   # (domain, doc, bos, depth) -> list of per-replica nll arrays
    secs = defaultdict(list)
    seen, duplicates = {}, 0
    with open(Path(run) / "rows.jsonl", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            key = (r["domain"], r["doc_id"], r["rep"], r["bos"], r["depth"])
            if key in seen:
                if seen[key] != r["nll"]:
                    raise SystemExit("conflicting duplicate rows for %s" % (key,))
                duplicates += 1
                continue
            seen[key] = r["nll"]
            per[(r["domain"], r["doc_id"], r["bos"], r["depth"])].append(np.array(r["nll"], dtype=np.float64))
            secs[(r["bos"], r["depth"])].append(r["seconds"])
    return per, secs, duplicates


def contrast(diff, rng):
    diff = np.asarray(diff, dtype=np.float64)
    n = len(diff)
    idx = rng.integers(0, n, size=(BOOT, n))
    boots = np.sort(diff[idx].mean(axis=1))
    worst = int(np.argmax(np.abs(diff)))
    return {"n": n, "mean": float(diff.mean()), "median": float(np.median(diff)),
            "ci95": [float(boots[int(0.025 * BOOT)]), float(boots[int(0.975 * BOOT) - 1])],
            "negative": int((diff < 0).sum()), "positive": int((diff > 0).sum()),
            "mean_without_largest": float(np.delete(diff, worst).mean()) if n > 1 else None,
            "largest_effect": float(diff[worst]),
            "ppl_change_pct": 100.0 * (math.exp(float(diff.mean())) - 1.0)}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--run", required=True)
    args = p.parse_args()
    per, secs, duplicates = load(args.run)
    replicas = {len(v) for v in per.values()}
    if len(replicas) != 1:
        raise SystemExit("incomplete run: windows have different replica counts %s" % sorted(replicas))
    domains = sorted({k[0] for k in per})
    depths = sorted({k[3] for k in per})
    rng = np.random.default_rng(BOOT_SEED)

    def window_means(domain, bos, depth, scope):
        docs = sorted({k[1] for k in per if k[0] == domain})
        missing = [d for d in docs if (domain, d, bos, depth) not in per]
        if missing:
            raise SystemExit("incomplete run: %d windows missing %s bos=%d depth=%d" % (len(missing), domain, bos, depth))
        return docs, np.array([np.mean([a[scope].mean() for a in per[(domain, d, bos, depth)]]) for d in docs])

    summary = {"replicas": replicas.pop(), "depths": depths, "domains": {}, "timing": {},
               "duplicate_rows_ignored": duplicates}
    for domain in domains:
        dom = {"levels": {}, "depth_contrasts": {}, "bos_contrasts": {}, "oracle": {}}
        for bos in (1, 0):
            for depth in depths:
                docs, m = window_means(domain, bos, depth, PRIMARY)
                _, e = window_means(domain, bos, depth, EARLY)
                dom["levels"]["bos%d_d%d" % (bos, depth)] = {"windows": len(docs), "mean_nll": float(m.mean()),
                                                             "ppl": math.exp(float(m.mean())),
                                                             "early_mean_nll": float(e.mean())}
            base = window_means(domain, bos, depths[0], PRIMARY)[1]
            for depth in depths[1:]:
                dom["depth_contrasts"]["bos%d_d%d_minus_d%d" % (bos, depth, depths[0])] = contrast(
                    window_means(domain, bos, depth, PRIMARY)[1] - base, rng)
        for depth in depths:
            for scope_name, scope in (("primary", PRIMARY), ("early", EARLY)):
                dom["bos_contrasts"]["d%d_%s_bos_minus_nobos" % (depth, scope_name)] = contrast(
                    window_means(domain, 1, depth, scope)[1] - window_means(domain, 0, depth, scope)[1], rng)
        # Oracle (uses the labels, so it is an upper bound, not a deployable policy), BOS on.
        table = np.stack([window_means(domain, 1, d, PRIMARY)[1] for d in depths], axis=1)  # windows x depths
        best = table.min(axis=1)
        pick = [next(j for j, d in enumerate(depths) if table[w, j] <= best[w] + ORACLE_EPS) for w in range(len(table))]
        chosen = table[np.arange(len(table)), pick]
        dmax = depths[-1]
        dom["oracle"] = {
            "eps_nats": ORACLE_EPS,
            "cheapest_within_eps_mean_nll": float(chosen.mean()),
            "fixed_max_depth_mean_nll": float(table[:, -1].mean()),
            "cost_relative_to_fixed_max_depth": float(np.mean([cost(depths[j]) for j in pick]) / cost(dmax)),
            "depth_choice_counts": {str(d): int(sum(1 for j in pick if depths[j] == d)) for d in depths},
            "per_text_best_mean_nll": float(best.mean()),
        }
        summary["domains"][domain] = dom
    for (bos, depth), values in sorted(secs.items()):
        summary["timing"]["bos%d_d%d" % (bos, depth)] = {"median_seconds": float(np.median(values)), "n": len(values)}
    t8 = summary["timing"].get("bos1_d%d" % depths[0], {}).get("median_seconds")
    for depth in depths:
        t = summary["timing"].get("bos1_d%d" % depth, {}).get("median_seconds")
        if t8 and t:
            summary["timing"]["bos1_d%d"
                              % depth]["ratio_to_d%d" % depths[0]] = t / t8
    for depth in depths:
        t = summary["timing"].get("bos1_d%d" % depth)
        if t:
            t["tokens_per_second"] = TOKENS_PER_FORWARD / t["median_seconds"]
    summary["verdict"] = verdict(summary, depths)
    write_csv(Path(args.run, "per_window.csv"), per, depths)
    Path(args.run, "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    Path(args.run, "summary.md").write_text(render(summary) + "\n", encoding="utf-8")
    print(render(summary))
    return 0


def verdict(summary, depths):
    """Frozen three-way statement per deeper depth, BOS on: significant (95% CI entirely below 0)
    in both verdict domains / in exactly one / in none."""
    present = [d for d in VERDICT_DOMAINS if d in summary["domains"]]
    out = {"domains": present}
    for depth in depths[1:]:
        key = "bos1_d%d_minus_d%d" % (depth, depths[0])
        sig = [d for d in present if summary["domains"][d]["depth_contrasts"][key]["ci95"][1] < 0]
        if len(present) < 2:
            label = "INCOMPLETE: fewer than two verdict domains"
        elif len(sig) == len(present):
            label = "depth %d significantly better than %d in both domains" % (depth, depths[0])
        elif sig:
            label = "depth %d significantly better than %d only in %s" % (depth, depths[0], sig[0])
        else:
            label = "depth %d not significantly better than %d" % (depth, depths[0])
        out["d%d" % depth] = {"significant_in": sig, "statement": label}
    return out


def write_csv(path, per, depths):
    """One row per window: mean primary NLL (replicas averaged) for every BOS x depth condition."""
    keys = sorted({(k[0], k[1]) for k in per})
    cols = ["bos%d_d%d" % (b, d) for b in (1, 0) for d in depths]
    with open(path, "w", encoding="utf-8") as f:
        f.write("domain,doc_id," + ",".join(cols) + "\n")
        for domain, doc in keys:
            vals = []
            for b in (1, 0):
                for d in depths:
                    arrs = per.get((domain, doc, b, d))
                    vals.append("%.6f" % np.mean([a[PRIMARY].mean() for a in arrs]) if arrs else "")
            f.write("%s,%s,%s\n" % (domain, doc, ",".join(vals)))


def render(s):
    lines = ["# Stage 0 summary", "", "Replicas per window: %d. NLL in nats/token (lower is better). "
             "Primary scope t[65..255]; early scope t[1..64]. Identical duplicate rows ignored: %d."
             % (s["replicas"], s.get("duplicate_rows_ignored", 0)), ""]
    for domain, dom in s["domains"].items():
        lines += ["## %s" % domain, "", "| condition | windows | mean NLL | ppl | early NLL |", "|---|---:|---:|---:|---:|"]
        for name, v in dom["levels"].items():
            lines.append("| %s | %d | %.4f | %.2f | %.4f |" % (name, v["windows"], v["mean_nll"], v["ppl"], v["early_mean_nll"]))
        lines += ["", "| contrast | mean | 95% CI | median | neg/pos | mean w/o largest | ppl change |", "|---|---:|---|---:|---:|---:|---:|"]
        for group in ("depth_contrasts", "bos_contrasts"):
            for name, c in dom[group].items():
                lines.append("| %s | %+.4f | [%+.4f, %+.4f] | %+.4f | %d/%d | %+.4f | %+.2f%% |" % (
                    name, c["mean"], c["ci95"][0], c["ci95"][1], c["median"], c["negative"], c["positive"],
                    c["mean_without_largest"] if c["mean_without_largest"] is not None else float("nan"),
                    c["ppl_change_pct"]))
        o = dom["oracle"]
        lines += ["", "Oracle (BOS on, upper bound): cheapest depth within %.2f nats of the best -> mean NLL %.4f vs "
                  "fixed max depth %.4f at %.0f%% of its cost; choices %s." % (
                      o["eps_nats"], o["cheapest_within_eps_mean_nll"], o["fixed_max_depth_mean_nll"],
                      100 * o["cost_relative_to_fixed_max_depth"], o["depth_choice_counts"]), ""]
    lines += ["## Verdict (BOS on; frozen three-way statement)", ""]
    for k, v in s["verdict"].items():
        if k != "domains":
            lines.append("- %s" % v["statement"])
    lines += ["", "## Timing (median seconds per %d-token forward)" % TOKENS_PER_FORWARD, ""]
    for name, t in s["timing"].items():
        extra = "".join(" (%s %.2fx)" % (k, v) for k, v in t.items() if k.startswith("ratio"))
        if "tokens_per_second" in t:
            extra += ", %.0f tokens/s" % t["tokens_per_second"]
        lines.append("- %s: %.3f s over %d forwards%s" % (name, t["median_seconds"], t["n"], extra))
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
