#!/usr/bin/env python3
"""R1 Gate C: equal-example-exposure unigram/bigram control.

Reconstruct exactly the sampled next-byte targets seen by r1_text_pilot.py
during training, using its independent checkpointed offset RNG stream.
Fit smoothed n-grams only on those supervised (previous_byte, next_byte)
pairs, NOT on the entire training corpus. Verify the reconstructed generator
state matches the checkpoint; otherwise refuse to report "matched" results.
Read-only for existing checkpoints and data.
"""
import argparse
import json
import math
from pathlib import Path

import torch

from common import atomic_json, commit_id, get_repo
from r1_language_diagnostics import fitted_byte_models, metrics_from_sums, validate_checkpoint
from r1_text_pilot import VOCAB_SIZE, TOKENIZER_ID, text_tokens, validation_offsets


def replay_observed_pairs(tokens, *, steps, batch_size, seq_len, seed):
    """Replicate only offset draws of r1_text_pilot.draw_batch across all steps.

    The training loop uses independent CPU torch.Generator seeded with seed+17,
    exactly one torch.randint call of size (batch_size,) per optimizer step.
    We include repeated positions because repeated targets contribute repeated
    supervised examples, just as they do during model optimization.
    """
    if not torch.is_tensor(tokens) or tokens.ndim != 1:
        raise ValueError("Training tokens must be a 1-D tensor")
    if not all(isinstance(v, int) for v in (steps, batch_size, seq_len, seed)):
        raise ValueError("Training configuration must use integer values")
    if steps < 1 or batch_size < 1 or seq_len < 1 or seed < 0:
        raise ValueError("Invalid replay parameters")
    if len(tokens) <= seq_len:
        raise ValueError("Not enough training tokens")
    g = torch.Generator(device="cpu").manual_seed(seed + 17)
    x_parts = []
    y_parts = []
    offsets_all = []
    for _ in range(steps):
        offsets = torch.randint(
            low=0, high=len(tokens) - seq_len,
            size=(batch_size,), generator=g
        ).tolist()
        offsets_all.extend(offsets)
        for offset in offsets:
            x_parts.append(tokens[offset:offset + seq_len])
            y_parts.append(tokens[offset + 1:offset + seq_len + 1])
    x = torch.cat(x_parts).long()
    y = torch.cat(y_parts).long()
    return x, y, g.get_state(), {
        "training_steps_replayed": steps,
        "mini_batches_replayed": steps * batch_size,
        "supervised_target_positions": int(y.numel()),
        "unique_window_starts": len(set(offsets_all)),
        "repeated_window_starts": len(offsets_all) - len(set(offsets_all)),
        "note": "Number of unique window starts is not unique byte coverage. "
                "Overlapping windows are counted as separate supervised exposures.",
    }


def fit_seen_ngram(x, y, smoothing=1.0):
    if not isinstance(x, torch.Tensor) or not isinstance(y, torch.Tensor):
        raise ValueError("Inputs must be tensors")
    if x.ndim != 1 or y.ndim != 1 or x.numel() != y.numel() or x.numel() < 1:
        raise ValueError("Supervised x/y must be same-length nonempty vectors")
    if not 0 < smoothing <= 100 or x.min() < 0 or y.min() < 0:
        raise ValueError("Invalid smoothing or token id")
    if x.max() >= VOCAB_SIZE or y.max() >= VOCAB_SIZE:
        raise ValueError("Token id exceeds vocabulary")
    counts_y = torch.bincount(y, minlength=VOCAB_SIZE).double()
    count_xy = torch.bincount(
        x * VOCAB_SIZE + y, minlength=VOCAB_SIZE * VOCAB_SIZE
    ).reshape(VOCAB_SIZE, VOCAB_SIZE).double()
    uni = (counts_y + smoothing) / (
        counts_y.sum() + smoothing * VOCAB_SIZE
    )
    bi = (count_xy + smoothing) / (
        count_xy.sum(dim=1, keepdim=True) + smoothing * VOCAB_SIZE
    )
    return uni, bi


def heldout_ngram_metrics(unigram, bigram, validation, *, seq_len, windows):
    if unigram.shape != (VOCAB_SIZE,) or bigram.shape != (VOCAB_SIZE, VOCAB_SIZE):
        raise ValueError("Invalid n-gram probability dimensions")
    if not torch.isfinite(unigram).all() or not torch.isfinite(bigram).all():
        raise ValueError("Nonfinite probability table")
    total_u = total_b = 0.0
    count = 0
    for offset in validation_offsets(len(validation), seq_len, windows):
        x = validation[offset:offset + seq_len].long()
        y = validation[offset + 1:offset + seq_len + 1].long()
        total_u += float(-unigram[y].log().sum())
        total_b += float(-bigram[x, y].log().sum())
        count += y.numel()
    return {
        "unigram": metrics_from_sums(total_u, count),
        "bigram": metrics_from_sums(total_b, count),
    }


def compare_exposures(train, validation, *, hyperparameters, steps,
                      offset_rng_state, windows, seq_len):
    x, y, regenerated_state, replay = replay_observed_pairs(
        train, steps=steps, batch_size=hyperparameters["batch_size"],
        seq_len=seq_len, seed=hyperparameters["seed"]
    )
    if not isinstance(offset_rng_state, torch.Tensor) or not torch.equal(
        regenerated_state, offset_rng_state
    ):
        raise ValueError(
            "Checkpoint offset RNG state mismatch: cannot assert equal "
            "training-data exposure. Check training script, seed or checkpoint."
        )
    matched_u, matched_b = fit_seen_ngram(x, y)
    full_u, full_b = fitted_byte_models(train)
    return {
        "replay": replay,
        "checkpoint_offset_rng_matches_replay": True,
        "exposure_matched": heldout_ngram_metrics(
            matched_u, matched_b, validation, seq_len=seq_len, windows=windows
        ),
        "full_corpus_reference": heldout_ngram_metrics(
            full_u, full_b, validation, seq_len=seq_len, windows=windows
        ),
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", default=".")
    p.add_argument("--pilot-dir", required=True)
    p.add_argument("--eval-windows", type=int, default=16)
    p.add_argument("--out")
    args = p.parse_args()
    if args.eval_windows < 1:
        p.error("--eval-windows must be positive")
    root = get_repo(args.repo)
    directory = Path(args.pilot_dir).resolve()
    if not directory.is_relative_to(root / "research/mini_mythos/results"):
        p.error("--pilot-dir must be under research/mini_mythos/results")
    out = Path(args.out).resolve() if args.out else directory / "exposure_baselines.json"
    if not out.is_relative_to(root / "research/mini_mythos/results"):
        p.error("--out must be under research/mini_mythos/results")

    report = json.loads((directory / "report.json").read_text(encoding="utf-8"))
    checkpoint = torch.load(
        directory / "latest.pt", map_location="cpu", weights_only=True
    )
    hyper = report["hyperparameters"]
    cfg = checkpoint["cfg"]
    seq_len = hyper["seq_len"]
    train_meta = report["source_provenance"]["train"]
    val_meta = report["source_provenance"]["validation"]
    train, checked_train = text_tokens(
        train_meta["source_path"], train_meta["selected_bytes"], seq_len
    )
    validation, checked_val = text_tokens(
        val_meta["source_path"], val_meta["selected_bytes"], seq_len
    )
    # Do not import/model-instantiate heavyweight parameters; use a dataclass
    # created from the same upstream configuration as the checkpoint.
    from common import load_upstream
    module = load_upstream(root)
    model_cfg = module.MythosConfig(**cfg)
    validate_checkpoint(
        checkpoint, report, model_cfg, checked_train, checked_val
    )
    results = compare_exposures(
        train, validation, hyperparameters=hyper,
        steps=int(checkpoint["step"]),
        offset_rng_state=checkpoint["offset_rng_state"],
        windows=args.eval_windows, seq_len=seq_len
    )
    result = {
        "experiment": "R1 exposure-matched vs full-train-corpus ngram baselines",
        "repository_commit": commit_id(root),
        "checkpoint_step": int(checkpoint["step"]),
        "checkpoint_source": str(directory / "latest.pt"),
        "model_reference": report["heldout_after_this_run"],
        "tokenizer": TOKENIZER_ID,
        "smoothing": "Laplace add-1 to all 257 next-byte token classes",
        "evaluation_windows": args.eval_windows,
        "dataset_sha256": {
            "train": checked_train["file_sha256"],
            "validation": checked_val["file_sha256"],
            "selected_train_prefix": checked_train["selected_bytes_sha256"],
            "selected_validation_prefix": checked_val["selected_bytes_sha256"],
        },
        "comparison": results,
        "interpretation": "Only matches count and identity of target (prev,next) "
                          "byte pairs seen by SGD; unigram/bigram capacity, training "
                          "objectives, and compute still differ. No proof of equivalence "
                          "or lack of equivalence to Anthropic Mythos.",
    }
    atomic_json(out, result)
    print("Checkpoint step:", checkpoint["step"])
    print("Replay offset RNG matches checkpoint:", True)
    print("Target-byte observations:", results["replay"]["supervised_target_positions"])
    for key in ("exposure_matched", "full_corpus_reference"):
        stats = results[key]
        print(key, "unigram ppl:", round(stats["unigram"]["ppl"], 6),
              "bigram ppl:", round(stats["bigram"]["ppl"], 6))
    print("Model reference heldout PPL:",
          report["heldout_after_this_run"]["perplexity"])
    print("Saved:", out)


if __name__ == "__main__":
    main()
