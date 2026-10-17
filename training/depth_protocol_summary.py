#!/usr/bin/env python3
"""
Tables for depth_protocol_eval.py output, following the protocol's three
levels of judgment. Every table is per seed first, then the seed mean, so
cross-seed consistency is visible rather than averaged away.

    L1  rule vs BASE at the same T:            PPL_rule(T) / PPL_BASE(T) - 1
    L2  same rule, deeper vs T=4:              PPL_rule(8)/PPL_rule(4) - 1, 16 vs 4
        (flagged when a rule's own T=4 is worse than BASE's T=4, since a
        smaller 4→8 gap then does not show better extrapolation)
    L3  cost vs benefit per rule and T:        loops per forward call, loop-tokens
        and wall time relative to the same rule at T=4, next to the PPL change
    D   diagnostics: ACT halting depth distribution, weight sum, unhalted
        fraction, per-loop hidden RMS and relative change

    python training/depth_protocol_summary.py proto.jsonl [--metric byte_ppl]
"""

import argparse
import json
import os
import statistics
from collections import defaultdict

RULE_ORDER = ["BASE", "B1", "B2", "C", "B1+C", "B2+C"]


def pct(x):
    return f"{100 * x:+.2f}%"


def mean(xs):
    xs = [x for x in xs if x is not None]
    return statistics.mean(xs) if xs else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results")
    ap.add_argument("--metric", default="byte_ppl", choices=["byte_ppl", "token_ppl"])
    ap.add_argument("--ref-t", type=int, default=4)
    args = ap.parse_args()

    metas, cells = [], {}
    for line in open(args.results):
        r = json.loads(line)
        if r["type"] == "meta":
            metas.append(r)
        else:
            seed = os.path.basename(r["ckpt"]).removesuffix(".pt")
            cells[(seed, r["rule"], r["n_loops"])] = r
    seeds = sorted({k[0] for k in cells})
    rules = [r for r in RULE_ORDER if any(k[1] == r for k in cells)]
    loops = sorted({k[2] for k in cells})
    M, ref = args.metric, args.ref_t

    def get(seed, rule, t, key=M):
        r = cells.get((seed, rule, t))
        return None if r is None else r[key]

    print("## Run metadata\n")
    for m in metas:
        print(
            f"- {os.path.basename(m['ckpt'])}: ckpt sha256 {str(m['ckpt_sha256'])[:12]}, "
            f"step {m['ckpt_step']}, trained T={m['cfg'].get('max_loop_iters')}, "
            f"commit {m['source']['commit'][:10]}{' (dirty)' if m['source']['dirty'] else ''}, "
            f"data sha256 {m['data_token_sha256'][:12]}, {m['n_bytes']} bytes, "
            f"seq {m['seq_len']}, batch {m['batch_size']}, "
            f"equivalence verified: {m['equivalence_verified']}"
        )
    print(
        f"\nMetric: {M}. Definition: {metas[0]['byte_ppl_definition'] if metas else '?'}"
    )

    print(f"\n## Raw {M}\n")
    print("| rule | T | " + " | ".join(seeds) + " | mean |")
    print("|---|---|" + "---|" * (len(seeds) + 1))
    for rule in rules:
        for t in loops:
            v = [get(s, rule, t) for s in seeds]
            print(
                f"| {rule} | {t} | "
                + " | ".join("-" if x is None else f"{x:.4f}" for x in v)
                + f" | {mean(v):.4f} |"
            )

    print("\n## L1: rule vs BASE at the same T\n")
    print("| rule | T | " + " | ".join(seeds) + " | mean |")
    print("|---|---|" + "---|" * (len(seeds) + 1))
    for rule in rules:
        if rule == "BASE":
            continue
        for t in loops:
            v = []
            for s in seeds:
                a, b = get(s, rule, t), get(s, "BASE", t)
                v.append(None if a is None or b is None else a / b - 1)
            print(
                f"| {rule} | {t} | "
                + " | ".join("-" if x is None else pct(x) for x in v)
                + f" | {pct(mean(v)) if mean(v) is not None else '-'} |"
            )

    print(f"\n## L2: same rule, deeper T vs T={ref}\n")
    deeper = [t for t in loops if t > ref]
    print(
        "| rule | "
        + " | ".join(f"{t} vs {ref}: {s}" for t in deeper for s in seeds + ["mean"])
        + " | own T=4 vs BASE T=4 |"
    )
    print("|---|" + "---|" * (len(deeper) * (len(seeds) + 1) + 1))
    for rule in rules:
        parts = []
        for t in deeper:
            v = []
            for s in seeds:
                a, b = get(s, rule, t), get(s, rule, ref)
                v.append(None if a is None or b is None else a / b - 1)
            parts += ["-" if x is None else pct(x) for x in v]
            parts.append(pct(mean(v)) if mean(v) is not None else "-")
        own = [
            (
                None
                if get(s, rule, ref) is None or get(s, "BASE", ref) is None
                else get(s, rule, ref) / get(s, "BASE", ref) - 1
            )
            for s in seeds
        ]
        flag = ""
        if rule != "BASE" and mean(own) is not None and mean(own) > 1e-4:
            flag = " ⚠ worse at T=4"
        print(
            f"| {rule} | "
            + " | ".join(parts)
            + f" | {pct(mean(own)) if mean(own) is not None else '-'}{flag} |"
        )

    print(
        f"\n## L3: compute vs benefit (seed mean, relative to same rule at T={ref})\n"
    )
    print("| rule | T | loops/call | loop-tokens × | wall time × | ΔPPL vs own T=4 |")
    print("|---|---|---|---|---|---|")
    for rule in rules:
        for t in loops:
            lpc = mean([get(s, rule, t, "loops_per_call") for s in seeds])
            lt = mean(
                [
                    get(s, rule, t, "loop_tokens") / get(s, rule, ref, "loop_tokens")
                    for s in seeds
                    if get(s, rule, ref, "loop_tokens")
                ]
            )
            ws = mean(
                [
                    get(s, rule, t, "fwd_seconds") / get(s, rule, ref, "fwd_seconds")
                    for s in seeds
                    if get(s, rule, ref, "fwd_seconds")
                ]
            )
            dp = mean(
                [
                    get(s, rule, t) / get(s, rule, ref) - 1
                    for s in seeds
                    if get(s, rule, ref) and get(s, rule, t)
                ]
            )
            print(
                f"| {rule} | {t} | {lpc:.2f} | {lt:.2f} | {ws:.2f} | "
                f"{pct(dp) if dp is not None else '-'} |"
            )

    print("\n## D: ACT and hidden-state diagnostics (per seed)\n")
    print(
        "| rule | T | seed | mean halt loop | halt dist (loop:frac) | unhalted | "
        "mean weight sum | w<0.99 | h RMS per loop | rel change per loop |"
    )
    print("|---|---|---|---|---|---|---|---|---|---|")
    for rule in rules:
        for t in loops:
            for s in seeds:
                r = cells.get((s, rule, t))
                if r is None:
                    continue
                n = sum(r["act_halt_hist"])
                dist = " ".join(
                    f"{k}:{c / n:.2f}"
                    for k, c in enumerate(r["act_halt_hist"])
                    if k and c / n >= 0.01
                )
                ran = [i for i, c in enumerate(r["loop_calls"]) if c]
                rms = " ".join(f"{r['h_rms_per_loop'][i]:.2f}" for i in ran)
                rel = " ".join(f"{r['rel_change_per_loop'][i]:.3f}" for i in ran)
                mh = r["act_mean_halt_step"]
                print(
                    f"| {rule} | {t} | {s} | {mh:.2f} | {dist} | "
                    f"{r['act_frac_unhalted']:.3f} | {r['act_mean_weight_sum']:.3f} | "
                    f"{r['act_frac_weight_sum_below_0_99']:.3f} | {rms} | {rel} |"
                    if mh is not None
                    else f"| {rule} | {t} | {s} | - | {dist} | {r['act_frac_unhalted']:.3f} | "
                    f"{r['act_mean_weight_sum']:.3f} | {r['act_frac_weight_sum_below_0_99']:.3f} | {rms} | {rel} |"
                )


if __name__ == "__main__":
    main()
