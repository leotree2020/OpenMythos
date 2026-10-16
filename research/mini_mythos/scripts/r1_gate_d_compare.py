#!/usr/bin/env python3
"""R1 Gate D: verify and compare resumed 60/200/600-step pilot artifacts.

No training, inference or model modifications. Load existing local reports,
diagnostics, exposure controls and checkpoints, reject inconsistent runs,
then build a machine-readable longitudinal learning curve.
"""
import argparse
import json
import math
from pathlib import Path

import torch

from common import atomic_json, commit_id, get_repo


def require(condition, message):
    if not condition:
        raise ValueError(message)


def finite_positive(value, label):
    require(isinstance(value, (int, float)) and not isinstance(value, bool),
            f"{label} must be numeric")
    require(math.isfinite(float(value)) and float(value) > 0,
            f"{label} must be finite and positive")
    return float(value)


def summarize_artifacts(entries):
    """Entries hold verified dictionaries from each step; pure and offline."""
    require(len(entries) >= 2, "At least two checkpoints are required")
    first = entries[0]["report"]
    hyper = first["hyperparameters"]
    provenance = first["source_provenance"]
    config = first["configuration"]
    tokenizer = first["tokenizer"]
    params = first["model_parameters"]
    common_eval = None
    earlier_step = None
    records = []
    for idx, entry in enumerate(entries):
        report = entry["report"]
        diag = entry["diagnostics"]
        expo = entry["exposure"]
        ckpt = entry["checkpoint"]
        step = int(report["target_step"])
        require(earlier_step is None or step > earlier_step,
                "Checkpoints must be supplied in strictly increasing step order")
        require(report["hyperparameters"] == hyper and
                report["source_provenance"] == provenance and
                report["configuration"] == config and
                report["tokenizer"] == tokenizer and
                report["model_parameters"] == params,
                "Model, corpus, tokenizer or training hyperparameters drifted")
        require(ckpt.get("step") == step and ckpt.get("provenance") == provenance
                and ckpt.get("hyperparameters") == hyper
                and ckpt.get("cfg") == config,
                f"Checkpoint mismatch at step {step}")
        require(diag["checkpoint_step"] == step and
                expo["checkpoint_step"] == step,
                f"Diagnostics/exposure checkpoint-step mismatch at step {step}")
        require(expo["comparison"]["checkpoint_offset_rng_matches_replay"] is True,
                f"Training offset RNG replay did not verify at step {step}")
        require(
            expo["comparison"]["replay"]["supervised_target_positions"]
            == step * hyper["batch_size"] * hyper["seq_len"],
            f"Training token exposure count mismatch at step {step}"
        )
        require(idx == 0 and report["start_step"] == 0
                or idx > 0 and report["start_step"] == earlier_step,
                f"Missing or inconsistent resumption chain at step {step}")
        d_model = diag["model_heldout_and_baselines"]["model"]
        base = expo["comparison"]["exposure_matched"]
        benchmark = report["heldout_after_this_run"]
        require(abs(float(d_model["nll"]) - float(benchmark["nll"])) < 5e-5,
                f"Checkpoint validation NLL mismatch at step {step}")
        require(abs(float(d_model["ppl"]) -
                    float(benchmark["perplexity"])) < 5e-4,
                f"Checkpoint validation PPL mismatch at step {step}")
        require(abs(float(expo["model_reference"]["perplexity"]) -
                    float(benchmark["perplexity"])) < 5e-4,
                f"Exposure report model PPL mismatch at step {step}")
        require(d_model["tokens"] == benchmark["tokens"] ==
                base["bigram"]["tokens"] == base["unigram"]["tokens"],
                f"Different heldout token counts at step {step}")
        require(diag["context_order_probe"]["windows"] >= 1,
                f"Missing context-order probe at step {step}")
        if common_eval is None:
            common_eval = d_model["tokens"]
        require(d_model["tokens"] == common_eval,
                "Heldout token counts differ across checkpoints")
        model_ppl = finite_positive(d_model["ppl"], "model PPL")
        uni_ppl = finite_positive(base["unigram"]["ppl"], "matched unigram PPL")
        bi_ppl = finite_positive(base["bigram"]["ppl"], "matched bigram PPL")
        stats = diag["model_heldout_and_baselines"]["token_statistics"]
        tv = float(diag["context_order_probe"]["mean_probability_total_variation"])
        space = float(stats["predicted_space_fraction"])
        require(0 <= tv <= 1 and math.isfinite(tv), "Invalid probability TV")
        require(0 <= space <= 1 and math.isfinite(space),
                "Invalid predicted-space fraction")
        records.append({
            "step": step,
            "seen_supervised_target_positions": int(
                expo["comparison"]["replay"]["supervised_target_positions"]),
            "heldout_tokens": d_model["tokens"],
            "model_nll": float(d_model["nll"]),
            "model_ppl": model_ppl,
            "matched_unigram_ppl": uni_ppl,
            "matched_bigram_ppl": bi_ppl,
            "beats_matched_unigram": model_ppl < uni_ppl,
            "beats_matched_bigram": model_ppl < bi_ppl,
            "predicted_space_fraction": space,
            "target_space_fraction": float(stats["target_space_fraction"]),
            "reverse_history_probability_tv": tv,
            "reverse_history_delta_nll": float(
                diag["context_order_probe"]["reversed_minus_original_target_nll"]),
            "all_space_argmax": space == 1.,
        })
        earlier_step = step
    return {
        "experiment": "R1 identical-config longitudinal learning and matched exposure",
        "model": "upstream OpenMythos tiny model; independent reconstruction pilot",
        "training_configuration": hyper,
        "model_configuration": config,
        "tokenizer": tokenizer,
        "source_provenance": provenance,
        "eval_tokens_per_checkpoint": common_eval,
        "checkpoints": records,
        "scope": "Same observed training examples as ngram baselines; not "
                 "equal parameter count, compute or model optimization. "
                 "No Anthropic Mythos architectural fidelity established.",
    }


def load_entry(directory):
    def read_json(filename):
        return json.loads((directory / filename).read_text(encoding="utf-8"))
    checkpoint = torch.load(
        directory / "latest.pt", map_location="cpu", weights_only=True
    )
    # Only preserve metadata to avoid constructing huge intermediate objects.
    return {
        "report": read_json("report.json"),
        "diagnostics": read_json("diagnostics.json"),
        "exposure": read_json("exposure_baselines.json"),
        "checkpoint": {
            "step": checkpoint.get("step"),
            "provenance": checkpoint.get("provenance"),
            "hyperparameters": checkpoint.get("hyperparameters"),
            "cfg": checkpoint.get("cfg"),
        },
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", default=".")
    p.add_argument("--pilot-dirs", nargs="+", required=True)
    p.add_argument("--out", default="research/mini_mythos/results/r1/gate_d_comparison.json")
    a = p.parse_args()
    root = get_repo(a.repo)
    results = (root / "research/mini_mythos/results").resolve()
    out = Path(a.out).resolve()
    if not out.is_relative_to(results):
        p.error("Output must be under research/mini_mythos/results")
    directories = [Path(raw).resolve() for raw in a.pilot_dirs]
    if len(set(directories)) != len(directories) or any(
        not folder.is_relative_to(results) for folder in directories
    ):
        p.error("Pilot paths must be distinct paths under research/mini_mythos/results")
    result = summarize_artifacts([load_entry(folder) for folder in directories])
    result["repository_commit"] = commit_id(root)
    result["sources"] = [str(folder) for folder in directories]
    atomic_json(out, result)
    for row in result["checkpoints"]:
        print(
            f"step={row['step']} model_ppl={row['model_ppl']:.4f} "
            f"matched_unigram={row['matched_unigram_ppl']:.4f} "
            f"matched_bigram={row['matched_bigram_ppl']:.4f} "
            f"space_argmax={row['predicted_space_fraction']:.3f} "
            f"history_TV={row['reverse_history_probability_tv']:.6f}"
        )
    print("Verified identical model/training config, corpus, eval token counts, "
          "checkpoint steps, resume chain and RNG replay for all experiments.")
    print("Saved:", out)


if __name__ == "__main__":
    main()
