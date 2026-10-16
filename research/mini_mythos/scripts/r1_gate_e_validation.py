#!/usr/bin/env python3
"""R1 Gate E: broader, read-only, paired heldout evaluation of step-600.

This script never trains, samples generation, overwrites the prior 16-window
diagnostic, or chooses model/nd-gram hyperparameters based on heldout text.
Compute neural / matched-exposure unigram / matched-exposure bigram / full-
training-prefix bigram losses on IDENTICAL targets, then report window-based
paired differences and an exploratory bootstrap interval. Not an independent
test-set evaluation, significance claim, or Anthropic Mythos reproduction.
"""
import argparse
import json
import math
import random
from pathlib import Path

import torch
import torch.nn.functional as F

from common import atomic_json, commit_id, get_repo, load_upstream
from r1_exposure_baselines import fit_seen_ngram, replay_observed_pairs
from r1_language_diagnostics import fitted_byte_models, validate_checkpoint
from r1_text_pilot import VOCAB_SIZE, TOKENIZER_ID, text_tokens, validation_offsets


def quantile(values, fraction):
    if not values or not 0 <= fraction <= 1:
        raise ValueError("quantile input empty or fraction outside [0,1]")
    ordered = sorted(values)
    location = (len(ordered) - 1) * fraction
    i = math.floor(location)
    j = math.ceil(location)
    return ordered[i] + (ordered[j] - ordered[i]) * (location - i)


def paired_bootstrap(values, *, repetitions=2000, seed=20261016):
    """Exploratory window-level CI; windows are not assumed fully independent."""
    if not values or repetitions < 100 or not all(math.isfinite(v) for v in values):
        raise ValueError("Invalid bootstrap input")
    rng = random.Random(seed)
    count = len(values)
    means = []
    for _ in range(repetitions):
        means.append(
            math.fsum(values[rng.randrange(count)] for _ in range(count)) / count
        )
    return {
        "observed_mean": math.fsum(values) / count,
        "percentile_95_interval": [
            quantile(means, 0.025), quantile(means, 0.975)
        ],
        "unit": "deterministically selected nonoverlapping validation windows",
        "caveat": "Exploratory interval assumes exchangeable windows; "
                  "adjacent corpus passages and preselected eval data may "
                  "break independence. Not a confirmatory hypothesis test.",
        "bootstrap_repetitions": repetitions,
        "bootstrap_seed": seed,
    }


@torch.no_grad()
def evaluate_windows(model, heldout, *, seq_len, loops, windows, device,
                     matched_unigram, matched_bigram, full_bigram):
    """Return per-window byte NLL on identical heldout target positions."""
    if windows < 1:
        raise ValueError("At least one evaluation window is required")
    for p in (matched_unigram, matched_bigram, full_bigram):
        if not torch.isfinite(p).all() or (p <= 0).any():
            raise ValueError("N-gram probability tensor must be positive and finite")
    if matched_unigram.shape != (VOCAB_SIZE,) or (
        matched_bigram.shape != (VOCAB_SIZE, VOCAB_SIZE)
    ) or full_bigram.shape != (VOCAB_SIZE, VOCAB_SIZE):
        raise ValueError("N-gram tensor has wrong shape")
    model.eval()
    result = []
    for start in validation_offsets(len(heldout), seq_len, windows):
        x = heldout[start:start + seq_len].long()
        y = heldout[start + 1:start + seq_len + 1].long()
        logits = model(x[None, :].to(device), n_loops=loops)
        nll = F.cross_entropy(
            logits.reshape(-1, VOCAB_SIZE),
            y.to(device), reduction="none"
        ).detach().cpu().double()
        pred = logits[0].argmax(dim=-1).detach().cpu()
        count = int(y.numel())
        model_nll = float(nll.mean())
        un = float(-matched_unigram[y].log().mean())
        bg = float(-matched_bigram[x, y].log().mean())
        full_bg = float(-full_bigram[x, y].log().mean())
        result.append({
            "offset": int(start), "target_count": count,
            "model_mean_nll": model_nll,
            "matched_unigram_mean_nll": un,
            "matched_bigram_mean_nll": bg,
            "full_corpus_bigram_mean_nll": full_bg,
            "matched_bigram_minus_model_nll": bg - model_nll,
            "full_bigram_minus_model_nll": full_bg - model_nll,
            "predicted_space_count": int((pred == 32).sum()),
            "target_space_count": int((y == 32).sum()),
            "top1_correct_count": int((pred == y).sum()),
        })
    return result


def summarize_windows(rows):
    if not rows:
        raise ValueError("No validation windows supplied")
    total = sum(r["target_count"] for r in rows)
    if total < 1:
        raise ValueError("No scored tokens")
    def avg(key):
        return sum(r[key] * r["target_count"] for r in rows) / total
    def loss(label):
        nll = avg(label)
        return {"nll": nll, "ppl": math.exp(min(nll, 60)), "target_tokens": total}
    deltas = [r["matched_bigram_minus_model_nll"] for r in rows]
    full_deltas = [r["full_bigram_minus_model_nll"] for r in rows]
    return {
        "windows": len(rows), "target_tokens": total,
        "model": loss("model_mean_nll"),
        "matched_unigram": loss("matched_unigram_mean_nll"),
        "matched_bigram": loss("matched_bigram_mean_nll"),
        "full_corpus_bigram": loss("full_corpus_bigram_mean_nll"),
        "fraction_windows_model_better_than_matched_bigram":
            sum(d > 0 for d in deltas) / len(deltas),
        "argmax_predicted_space_fraction":
            sum(r["predicted_space_count"] for r in rows) / total,
        "target_space_fraction":
            sum(r["target_space_count"] for r in rows) / total,
        "argmax_accuracy":
            sum(r["top1_correct_count"] for r in rows) / total,
        "paired_matched_bigram_minus_model_nll":
            paired_bootstrap(deltas),
        "paired_full_bigram_minus_model_nll":
            paired_bootstrap(full_deltas),
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", default=".")
    p.add_argument("--pilot-dir", default="research/mini_mythos/results/r1/pilot_gqa_step600")
    p.add_argument("--eval-windows", type=int, default=128)
    p.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    p.add_argument("--out", default="research/mini_mythos/results/r1/gate_e_validation_128.json")
    args = p.parse_args()
    if args.eval_windows < 2:
        p.error("Need >=2 heldout windows for window-paired comparison")
    if args.device == "cuda" and not torch.cuda.is_available():
        p.error("CUDA was requested but is not available")
    root = get_repo(args.repo)
    results = root / "research/mini_mythos/results"
    directory = Path(args.pilot_dir).resolve()
    out = Path(args.out).resolve()
    if not directory.is_relative_to(results) or not out.is_relative_to(results):
        p.error("Pilot directory and output must be under the project's results directory")
    if out.exists():
        p.error("Output already exists; choose a new --out to preserve prior evidence")

    report = json.loads((directory / "report.json").read_text(encoding="utf-8"))
    checkpoint = torch.load(
        directory / "latest.pt", map_location="cpu", weights_only=True)
    if report.get("tokenizer") != TOKENIZER_ID:
        raise ValueError("Unexpected tokenizer for byte-level pilot")
    hyper = report["hyperparameters"]
    seq_len = int(hyper["seq_len"])
    depth = int(hyper["depth"])
    train_meta = report["source_provenance"]["train"]
    validation_meta = report["source_provenance"]["validation"]
    train, checked_train = text_tokens(
        train_meta["source_path"], train_meta["selected_bytes"], seq_len
    )
    heldout, checked_heldout = text_tokens(
        validation_meta["source_path"], validation_meta["selected_bytes"], seq_len
    )
    module = load_upstream(root)
    cfg = module.MythosConfig(**report["configuration"])
    validate_checkpoint(
        checkpoint, report, cfg, checked_train, checked_heldout)
    # Fail rather than quietly compare a checkpoint other than 600 steps.
    if int(checkpoint["step"]) != 600:
        raise ValueError("Gate E protocol explicitly fixes checkpoint step=600")
    x_seen, y_seen, rng_state, replay = replay_observed_pairs(
        train, steps=600, batch_size=hyper["batch_size"],
        seq_len=seq_len, seed=hyper["seed"]
    )
    if not torch.equal(rng_state, checkpoint["offset_rng_state"]):
        raise ValueError("Checkpoint offset RNG mismatch; cannot assert matched exposure")
    uni, bigram = fit_seen_ngram(x_seen, y_seen)
    _, full_bigram = fitted_byte_models(train)
    torch.set_num_threads(min(4, torch.get_num_threads()))
    model = module.OpenMythos(cfg).to(args.device).eval()
    model.load_state_dict(checkpoint["model"], strict=True)
    rows = evaluate_windows(
        model, heldout, seq_len=seq_len, loops=depth,
        windows=args.eval_windows, device=args.device,
        matched_unigram=uni, matched_bigram=bigram,
        full_bigram=full_bigram
    )
    summary = summarize_windows(rows)
    atomic_json(out, {
        "experiment": "R1 Gate E larger validation-window matched ngram comparison",
        "code_revision": commit_id(root),
        "dataset_role": "validation (not an untouched independent test set)",
        "tokenizer": TOKENIZER_ID,
        "checkpoint_step": int(checkpoint["step"]),
        "checkpoint_path": str(directory / "latest.pt"),
        "data_sha256": {
            "train": checked_train["file_sha256"],
            "validation": checked_heldout["file_sha256"],
            "train_selected": checked_train["selected_bytes_sha256"],
            "validation_selected": checked_heldout["selected_bytes_sha256"],
        },
        "replayed_training_exposure": replay,
        "checkpoint_rng_matches": True,
        "requested_windows": args.eval_windows,
        "summary": summary,
        "window_details": rows,
        "limitations": "Only 600-step tiny GQA byte-token model and heldout validation; "
                       "not a blinded independent test. Fixed Add-1 unigram/bigram. "
                       "Bootstrap intervals are descriptive and may overstate "
                       "confidence due to corpus dependence. Does not demonstrate "
                       "Anthropic Claude Mythos architecture/weights.",
    })
    print("Checkpoint step:", int(checkpoint["step"]))
    print("Observed supervised tokens:", replay["supervised_target_positions"])
    print("Offset RNG matches checkpoint: True")
    print("Heldout evaluation windows:", summary["windows"])
    print("Heldout target bytes:", summary["target_tokens"])
    for key in ("model", "matched_unigram", "matched_bigram", "full_corpus_bigram"):
        print(key, "NLL:", round(summary[key]["nll"], 6),
              "PPL:", round(summary[key]["ppl"], 6))
    paired = summary["paired_matched_bigram_minus_model_nll"]
    print("Matched bigram minus model NLL:", paired["observed_mean"])
    print("Exploratory window-bootstrap 95% interval:", paired["percentile_95_interval"])
    print("Model lower NLL in fraction of windows:",
          summary["fraction_windows_model_better_than_matched_bigram"])
    print("Predicted space fraction:", summary["argmax_predicted_space_fraction"])
    print("Saved:", out)


if __name__ == "__main__":
    main()
