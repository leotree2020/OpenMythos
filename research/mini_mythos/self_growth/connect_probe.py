#!/usr/bin/env python3
"""Which wording, if any, makes the model connect two linked seeds by itself? (dev world only)

Follow-up to the step 1 check-up, which failed on exactly this point. Every variant is generic: it names
no question and no answer. For each variant: all 24 linked pairs (K2 of a learner + K3 of the trainer)
and 8 unlinked pairs of the dev world. Reported: share of linked pairs whose output links the learner
to the trainer's town, share answered NONE, share of unlinked pairs answered NONE, share of lines that
pass the consistency check. The gate values of checkup.py are unchanged.

  python -B connect_probe.py --model-dir MODEL --out OUT --variants v2 v3 [--thinking v1]
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


def probe(torch, model, tok, world, variant, thinking, args):
    linked = sorted(W.linked_pairs(world), key=lambda x: x[1]["id"])
    unlinked = W.unlinked_pairs(world, args.unlinked)
    prompts = [W.connect_prompt(a["text"], b["text"], variant=variant) if i % 2 == 0 else
               W.connect_prompt(b["text"], a["text"], variant=variant) for i, (_, a, b) in enumerate(linked)]
    prompts += [W.connect_prompt(a["text"], b["text"], variant=variant) for a, b in unlinked]
    t = time.time()
    texts, n = LM.generate(torch, model, tok, prompts, args.max_new_tokens * (4 if thinking else 1),
                           batch=args.gen_batch, seed=3000, thinking=thinking)
    cov, none, lines_all, samples = [], [], [], []
    for (learner, a, b), text in zip(linked, texts):
        lines = W.clean_lines(text)
        is_none = text.strip().upper().startswith("NONE")
        none.append(int(is_none))
        cov.append(int(any(W.states_trainer_town(x, world, learner) for x in lines)))
        if not is_none:
            lines_all += lines
        samples.append("[linked] %s | %s\n%s\n" % (a["text"], b["text"], text))
    un_none, un_lines = [], []
    for (a, b), text in zip(unlinked, texts[len(linked):]):
        is_none = text.strip().upper().startswith("NONE")
        un_none.append(int(is_none))
        if not is_none:
            un_lines += W.clean_lines(text)
        samples.append("[unlinked] %s | %s\n%s\n" % (a["text"], b["text"], text))
    ok = [int(W.consistent(x, world)) for x in lines_all + un_lines]
    first16 = cov[:16]                                   # the 16 pairs of the check-up; the other 8 are fresh
    return {"variant": variant, "thinking": thinking, "linked_pairs": len(cov),
            "composed_coverage": sum(cov) / len(cov), "composed_coverage_first16": sum(first16) / len(first16),
            "composed_coverage_other8": sum(cov[16:]) / max(1, len(cov[16:])),
            "linked_answered_none": sum(none) / len(none), "unlinked_answered_none": sum(un_none) / len(un_none),
            "lines": len(ok), "consistent_lines": sum(ok) / max(1, len(ok)),
            "consistent_lines_unlinked": sum(int(W.consistent(x, world)) for x in un_lines) / max(1, len(un_lines)),
            "new_tokens": n, "seconds": time.time() - t}, samples


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--model-dir", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--world-seed", type=int, default=100)
    p.add_argument("--variants", nargs="*", default=[])
    p.add_argument("--thinking", nargs="*", default=[], help="variants to run with the model's thinking mode on")
    p.add_argument("--unlinked", type=int, default=8)
    p.add_argument("--max-new-tokens", type=int, default=160)
    p.add_argument("--gen-batch", type=int, default=8)
    p.add_argument("--threads", type=int, default=4)
    p.add_argument("--dtype", choices=["bf16", "fp32"], default="fp32")
    args = p.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    world = W.build(seed=args.world_seed)
    torch, model, tok = LM.load(args.model_dir, "cpu", args.threads, args.dtype)
    results = []
    for variant, thinking in [(v, False) for v in args.variants] + [(v, True) for v in args.thinking]:
        r, samples = probe(torch, model, tok, world, variant, thinking, args)
        results.append(r)
        name = "%s%s" % (variant, "_thinking" if thinking else "")
        (out / ("samples_%s.txt" % name)).write_text("\n".join(samples), encoding="utf-8")
        print(json.dumps({k: round(v, 3) if isinstance(v, float) else v for k, v in r.items()}), flush=True)
        (out / "connect_probe.json").write_text(json.dumps(results, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
