#!/usr/bin/env python3
"""Stage 0 text generation with BOS, greedy and sampled, plus descriptive repetition metrics.

Decoding settings
  greedy   argmax (kept for comparison with the earlier 0/12 result)
  sample   temperature 0.8, top-p 0.9, repetition penalty 1.1, two sampler seeds
Every prompt starts with BOS. Generation stops at EOS or after --max-new tokens. Depth 8
(the native training depth), no KV cache. Sampling probabilities are computed in FP64 and
renormalised after filtering, so floating-point mass error cannot stop the run.

There is deliberately no automatic PASS/FAIL on text quality: the metrics are descriptive and
the texts are written to generations.md for reading.

  python -B generate.py --out RUN_DIR
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

PROMPTS = Path(__file__).resolve().parent.parent / "base_v01" / "prompts_v1.json"
SETTINGS = [
    {"name": "greedy", "sample": False, "temperature": 1.0, "top_p": None, "rep_penalty": 1.0, "seeds": [0]},
    {"name": "sample", "sample": True, "temperature": 0.8, "top_p": 0.9, "rep_penalty": 1.1, "seeds": [1, 2]},
]


def next_token(torch, logits, history, setting, generator):
    """Choose one token from FP32 last-position logits."""
    logits = logits.double().clone()
    if setting["rep_penalty"] != 1.0 and history:
        seen = torch.tensor(sorted(set(history)), dtype=torch.long)
        vals = logits[seen]
        logits[seen] = torch.where(vals > 0, vals / setting["rep_penalty"], vals * setting["rep_penalty"])
    if not setting["sample"]:
        return int(torch.argmax(logits))
    logits = logits / setting["temperature"]
    probs = torch.softmax(logits, dim=-1)
    if setting["top_p"] is not None:
        sorted_p, order = torch.sort(probs, descending=True)
        keep = torch.cumsum(sorted_p, dim=-1) - sorted_p < setting["top_p"]   # always keeps the top token
        mask = torch.zeros_like(probs, dtype=torch.bool)
        mask[order[keep]] = True
        probs = torch.where(mask, probs, torch.zeros_like(probs))
    probs = probs / probs.sum()
    return int(torch.multinomial(probs, 1, generator=generator))


def generate(torch, model, prompt_ids, setting, seed, max_new, depth):
    ids = [common.BOS_ID] + list(prompt_ids)
    generator = torch.Generator().manual_seed(10_000 + seed)
    new = []
    for step in range(max_new):
        torch.manual_seed(20_000 + 1000 * seed + step)   # fixes the random initial recurrent state
        out = model.forward_for_generation(torch.tensor([ids], dtype=torch.long), num_steps=depth)
        token = next_token(torch, out["logits"][0, -1], ids[1:], setting, generator)
        if token == common.EOS_ID:
            break
        ids.append(token)
        new.append(token)
    return new


def metrics(tokens):
    def grams(n):
        return [tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]
    out = {"new_tokens": len(tokens)}
    for n in (1, 2):
        g = grams(n)
        out["distinct_%d" % n] = len(set(g)) / len(g) if g else None
    g4 = grams(4)
    counts = {}
    for g in g4:
        counts[g] = counts.get(g, 0) + 1
    out["max_4gram_count"] = max(counts.values()) if counts else 0
    out["repeated_4gram_fraction"] = (sum(c for c in counts.values() if c > 1) / len(g4)) if g4 else None
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", required=True)
    p.add_argument("--upstream", default=common.DEFAULTS["upstream"])
    p.add_argument("--model-dir", default=common.DEFAULTS["model_dir"])
    p.add_argument("--tokenizer", default=common.DEFAULTS["tokenizer"])
    p.add_argument("--prompts", default=str(PROMPTS))
    p.add_argument("--threads", type=int, default=2)
    p.add_argument("--max-new", type=int, default=64)
    p.add_argument("--depth", type=int, default=8)
    p.add_argument("--no-pin-check", action="store_true")
    args = p.parse_args()
    torch = common.setup_runtime(args.threads)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    common.check_inputs(args.model_dir, args.tokenizer, strict=not args.no_pin_check)
    tok = common.load_tokenizer(args.tokenizer)
    model, _ = common.load_model(torch, args.upstream, args.model_dir)
    prompts = json.loads(Path(args.prompts).read_text(encoding="utf-8"))["prompts"]
    rows, md = [], ["# Stage 0 generations", "",
                    "BOS + prompt, depth %d, up to %d new tokens. No automatic quality verdict." % (args.depth, args.max_new), ""]
    for prompt in prompts:
        md += ["## Prompt %d" % prompt["id"], "", "```text", prompt["text"], "```", ""]
        pids = common.encode(tok, prompt["text"])
        for setting in SETTINGS:
            for seed in setting["seeds"]:
                new = generate(torch, model, pids, setting, prompt["id"] * 10 + seed, args.max_new, args.depth)
                text = tok.decode(new, skip_special_tokens=False)
                row = {"prompt_id": prompt["id"], "setting": setting["name"], "seed": seed, "tokens": new,
                       "text": text, **metrics(new)}
                rows.append(row)
                md += ["**%s seed %d** (distinct-2 %s, max 4-gram %d)" % (
                    setting["name"], seed, "%.2f" % row["distinct_2"] if row["distinct_2"] is not None else "n/a",
                    row["max_4gram_count"]), "", "```text", text, "```", ""]
        print("prompt %d done" % prompt["id"], flush=True)
    with open(out / "generations.jsonl", "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    agg = {}
    for setting in SETTINGS:
        sel = [r for r in rows if r["setting"] == setting["name"]]
        agg[setting["name"]] = {k: sum(r[k] for r in sel if r[k] is not None) / max(1, sum(1 for r in sel if r[k] is not None))
                                for k in ("new_tokens", "distinct_2", "max_4gram_count", "repeated_4gram_fraction")}
    md += ["## Averages", "", "```json", json.dumps(agg, indent=1), "```"]
    (out / "generations.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    common.write_json(out / "generation_summary.json", {"settings": SETTINGS, "averages": agg,
                                                       "depth": args.depth, "max_new": args.max_new})
    print(json.dumps(agg, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
