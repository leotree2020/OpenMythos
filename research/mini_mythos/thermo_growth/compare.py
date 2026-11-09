#!/usr/bin/env python3
"""Side-by-side summary of the growth runs (auto / schedule / static).

  python -B compare.py RUN_DIR... [--out OUT.md]
"""
import argparse
import json
import sys
from pathlib import Path


def load(run):
    run = Path(run)
    s = json.loads((run / "summary.json").read_text())
    ev = [json.loads(x) for x in open(run / "evals.jsonl", encoding="utf-8") if x.strip()]
    gr = [json.loads(x) for x in open(run / "growth.jsonl", encoding="utf-8") if x.strip()]
    return s, ev, gr


def f(v):
    return "-" if v is None else "%+.4f" % v


def render(runs):
    L = ["# Growth by surprise while reading books (CPU)", "",
         "Differences are model minus native Parcae (nats per token): negative = better. 'Read so far' is the",
         "own-book tail windows (never read) of the books already read; 'held-out books' are books never read,",
         "prepared like the read ones; 'Stage 1 books' are the hard-wrapped Stage 1 windows; c4 / wikitext /",
         "fineweb show whether the rest of what Parcae knows stays intact.", "",
         "| run | mode | directions k | prequential gain (all / 2nd half) | read-so-far tails | held-out books | Stage 1 books (hard-wrapped) | c4 | wikitext | fineweb |",
         "|---|---|---:|---|---:|---:|---:|---:|---:|---:|"]
    for name, (s, ev, gr) in runs.items():
        fc = s["final_check"]
        L.append("| %s | %s%s | %d | %s / %s | %s | %s | %s | %s | %s | %s |" % (
            name, s["mode"], " + unfrozen" if s.get("unfreeze") else "", s["k_final"], f(s["prequential_gain_all"]),
            f(s["prequential_gain_second_half"]), f(fc["own_books_read"]), f(fc.get("heldout_books")), f(fc["domains"]["books"]),
            f(fc["domains"]["c4"]), f(fc["domains"]["wikitext"]), f(fc["domains"]["fineweb"])))
    L += ["", "Prequential gain = native loss minus the model's loss on each chunk BEFORE it learned from it",
          "(positive = it predicts new text better than native).", "",
          "Forgetting:", "", "| run | anchor | crystallize | general text (c4/wiki/fineweb) | books: gain right after | at the end | lost | kept |",
          "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for name, (s, ev, gr) in runs.items():
        kept = s.get("book_gain_kept_fraction")
        L.append("| %s | %s | %s | %s (%s%% ppl) | %s | %s | %s | %s |" % (
            name, s.get("anchor", 0), s.get("crystallize", 0), f(s.get("forgetting_nats")),
            "%+.1f" % s["forgetting_ppl_pct"] if s.get("forgetting_ppl_pct") is not None else "-",
            f(-s["book_gain_right_after"]) if s.get("book_gain_right_after") is not None else "-",
            f(-s["book_gain_at_end"]) if s.get("book_gain_at_end") is not None else "-",
            f(s.get("book_gain_lost")), "%.0f%%" % (100 * kept) if kept is not None else "-"))
    L.append("")
    for name, (s, ev, gr) in runs.items():
        L.append("## %s: checks while reading" % name)
        L.append("")
        L.append("| books read | k | read-so-far tails | unread tails | held-out books | Stage 1 books | c4 | wikitext | fineweb |")
        L.append("|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
        for e in ev:
            L.append("| %d | %d | %s | %s | %s | %s | %s | %s | %s |" % (
                e["books_read"], e["k"], f(e["own_books_read"]), f(e["own_books_unread"]), f(e.get("heldout_books")),
                f(e["domains"]["books"]),
                f(e["domains"]["c4"]), f(e["domains"]["wikitext"]), f(e["domains"]["fineweb"])))
        grown = [g for g in gr if g.get("grew")]
        if grown:
            L += ["", "Directions as they grew (page, book, structure/noise vs temperature, tokens behind the pull):", ""]
            for i, g in enumerate(grown):
                toks = " ".join(repr(t["token"]) for t in g.get("tokens_behind", [])[:10])
                L.append("- #%d page %d, book %d: %.2f vs T %.2f - %s" % (
                    i + 1, g["page"], g["book"], g["ratio"] if g.get("ratio") is not None else float("nan"), g["T"], toks))
        if s.get("base_relative_change"):
            L += ["", "Relative change of Parcae's own weights: " + ", ".join(
                "%s %.4f" % (k, v) for k, v in s["base_relative_change"].items() if v is not None)]
        L.append("")
    return "\n".join(L)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("runs", nargs="+")
    p.add_argument("--out")
    args = p.parse_args()
    runs = {Path(r).name: load(r) for r in args.runs if (Path(r) / "summary.json").exists()}
    text = render(runs)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
