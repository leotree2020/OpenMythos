#!/usr/bin/env python3
"""Step 1 of the self-growth pilot: is this model able to do the job at all? (README.md, "体检")

No training. On the DEV world (seed 100; the test world, seed 0, is not touched here):
  1. closed book: the questions without any facts. Must be near chance (25%): the knowledge is unknown.
  2. open book: the needed seeds (plus four unrelated ones) are in the prompt. Can the model recall (R),
     take one inference step (I) and combine two seeds (C) when the facts are in front of it?
  3. deriving: given one seed, or two seeds, does what the model writes contain the fact that follows
     (checked by string matching against the world, no judge), and is what it writes consistent?

  python -B checkup.py --model-dir MODEL --out OUT [--world-seed 100 --threads 4]

Writes OUT/checkup.json and OUT/samples.txt; prints the table and the gate verdict (exit 0 pass, 1 fail).
"""
import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lm as LM  # noqa: E402
import world as W  # noqa: E402

# Gate, fixed before the first run (README.md)
GATE = {"closed_max": 0.40,            # every group, closed book: at most this (chance 0.25)
        "open_R_min": 0.90, "open_I_min": 0.75, "open_C_min": 0.60,
        "derive_single_min": 0.50,     # share of K1 seeds whose derivations state the implied guild
        "derive_pair_min": 0.50,       # share of linked pairs whose derivations link the learner to the trainer's town
        "unlinked_none_min": 0.50,     # share of unlinked pairs answered with NONE
        "consistent_min": 0.80}        # share of all derived lines that pass the consistency check


def accuracy(world, logps):
    res = {"by_type": {}, "by_group": {}}
    hit = {}
    for q, lp in zip(world["questions"], logps):
        hit.setdefault(q["type"], []).append(int(max(range(4), key=lambda i: lp[i]) == q["answer"]))
    for t, v in sorted(hit.items()):
        res["by_type"][t] = {"n": len(v), "accuracy": sum(v) / len(v)}
    for g, types in W.GROUPS.items():
        v = [x for t in types for x in hit[t]]
        res["by_group"][g] = {"n": len(v), "accuracy": sum(v) / len(v)}
    return res


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--model-dir", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--world-seed", type=int, default=100)
    p.add_argument("--device", default="cpu")
    p.add_argument("--threads", type=int, default=4)
    p.add_argument("--dtype", choices=["bf16", "fp32"], default="fp32",
                   help="fp32 is exact and, on CPU, far faster than bf16 weights")
    p.add_argument("--gen-batch", type=int, default=8)
    p.add_argument("--singles", type=int, default=16, help="K1 seeds to derive from")
    p.add_argument("--pairs", type=int, default=16, help="linked pairs to connect")
    p.add_argument("--unlinked", type=int, default=8, help="unlinked pairs (the model should say NONE)")
    p.add_argument("--max-new-tokens", type=int, default=160)
    args = p.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    world = W.build(seed=args.world_seed)
    torch, model, tok = LM.load(args.model_dir, args.device, args.threads, args.dtype)
    result = {"model_dir": str(args.model_dir), "world_seed": args.world_seed, "gate": GATE,
              "questions": len(world["questions"]), "seeds": len(world["seeds"])}
    samples = []

    t = time.time()
    closed = LM.mcq(torch, model, tok, [W.closed_book_prompt(q) for q in world["questions"]])
    result["closed_book"] = accuracy(world, closed)
    result["closed_seconds"] = time.time() - t
    t = time.time()
    opened = LM.mcq(torch, model, tok, [W.open_book_prompt(world, q) for q in world["questions"]])
    result["open_book"] = accuracy(world, opened)
    result["open_seconds"] = time.time() - t
    print("closed book:", json.dumps({g: round(v["accuracy"], 3) for g, v in result["closed_book"]["by_group"].items()}),
          "| open book:", json.dumps({g: round(v["accuracy"], 3) for g, v in result["open_book"]["by_group"].items()}), flush=True)

    # deriving from one seed
    singles = sorted((s for s in world["seeds"] if s["kind"] == "K1"), key=lambda s: s["id"])[:args.singles]
    t = time.time()
    texts, n1 = LM.generate(torch, model, tok, [W.derive_prompt(s["text"]) for s in singles], args.max_new_tokens,
                              batch=args.gen_batch)
    lines_all, cov = [], []
    for s, text in zip(singles, texts):
        lines = W.clean_lines(text)
        lines_all += lines
        cov.append(int(any(W.states_guild(x, world, s["persons"][0]) for x in lines)))
        samples.append("[single %s] %s\n%s\n" % (s["id"], s["text"], text))
    # connecting two seeds
    linked = sorted(W.linked_pairs(world), key=lambda x: x[1]["id"])[:args.pairs]
    prompts = [W.connect_prompt(a["text"], b["text"]) if i % 2 == 0 else W.connect_prompt(b["text"], a["text"])
               for i, (_, a, b) in enumerate(linked)]
    texts, n2 = LM.generate(torch, model, tok, prompts, args.max_new_tokens, batch=args.gen_batch, seed=1000)
    pair_cov, pair_none = [], []
    for (learner, a, b), text in zip(linked, texts):
        lines = W.clean_lines(text)
        none = text.strip().upper().startswith("NONE")
        pair_none.append(int(none))
        if not none:
            lines_all += lines
        pair_cov.append(int(any(W.states_trainer_town(x, world, learner) for x in lines)))
        samples.append("[linked pair %s + %s]\n1. %s\n2. %s\n%s\n" % (a["id"], b["id"], a["text"], b["text"], text))
    unlinked = W.unlinked_pairs(world, args.unlinked)
    texts, n3 = LM.generate(torch, model, tok, [W.connect_prompt(a["text"], b["text"]) for a, b in unlinked],
                            args.max_new_tokens, batch=args.gen_batch, seed=2000)
    un_none = []
    for (a, b), text in zip(unlinked, texts):
        none = text.strip().upper().startswith("NONE")
        un_none.append(int(none))
        if not none:
            lines_all += W.clean_lines(text)
        samples.append("[unlinked pair %s + %s]\n1. %s\n2. %s\n%s\n" % (a["id"], b["id"], a["text"], b["text"], text))
    seconds = time.time() - t
    ok = [int(W.consistent(x, world)) for x in lines_all]
    result["derive"] = {"single_implied_coverage": sum(cov) / len(cov), "singles": len(cov),
                        "pair_composed_coverage": sum(pair_cov) / len(pair_cov), "pairs": len(pair_cov),
                        "linked_pairs_answered_none": sum(pair_none) / len(pair_none),
                        "unlinked_pairs_answered_none": sum(un_none) / len(un_none), "unlinked": len(un_none),
                        "lines": len(lines_all), "consistent_lines": sum(ok) / max(1, len(ok)),
                        "distinct_lines": len(set(lines_all)) / max(1, len(lines_all)),
                        "new_tokens": n1 + n2 + n3, "seconds": seconds, "tokens_per_second": (n1 + n2 + n3) / seconds}

    cb, ob, dv = result["closed_book"]["by_group"], result["open_book"]["by_group"], result["derive"]
    checks = {"closed book near chance (all groups <= %.2f)" % GATE["closed_max"]:
              all(v["accuracy"] <= GATE["closed_max"] for v in cb.values()),
              "open book recall >= %.2f" % GATE["open_R_min"]: ob["R"]["accuracy"] >= GATE["open_R_min"],
              "open book one inference step >= %.2f" % GATE["open_I_min"]: ob["I"]["accuracy"] >= GATE["open_I_min"],
              "open book combining two seeds >= %.2f" % GATE["open_C_min"]: ob["C"]["accuracy"] >= GATE["open_C_min"],
              "derives the implied fact from one seed >= %.2f" % GATE["derive_single_min"]:
              dv["single_implied_coverage"] >= GATE["derive_single_min"],
              "connects two linked seeds >= %.2f" % GATE["derive_pair_min"]:
              dv["pair_composed_coverage"] >= GATE["derive_pair_min"],
              "says NONE for unlinked seeds >= %.2f" % GATE["unlinked_none_min"]:
              dv["unlinked_pairs_answered_none"] >= GATE["unlinked_none_min"],
              "derived lines consistent >= %.2f" % GATE["consistent_min"]: dv["consistent_lines"] >= GATE["consistent_min"]}
    result["checks"] = checks
    result["verdict"] = "PASS" if all(checks.values()) else "FAIL"
    (out / "checkup.json").write_text(json.dumps(result, indent=1) + "\n")
    (out / "samples.txt").write_text("\n".join(samples), encoding="utf-8")
    print("accuracy (chance 0.25)   closed book   open book")
    for g in ("R", "I", "C"):
        print("  %s (n=%3d)              %.3f         %.3f" % (g, cb[g]["n"], cb[g]["accuracy"], ob[g]["accuracy"]))
    for t in W.QUESTION_TYPES:
        print("    %s                    %.3f         %.3f" % (t, result["closed_book"]["by_type"][t]["accuracy"],
                                                            result["open_book"]["by_type"][t]["accuracy"]))
    print("deriving:", json.dumps({k: round(v, 3) if isinstance(v, float) else v for k, v in dv.items()}))
    for k, v in checks.items():
        print("  [%s] %s" % ("ok" if v else "NO", k))
    print("VERDICT:", result["verdict"])
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
