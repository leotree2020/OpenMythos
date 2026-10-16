#!/usr/bin/env python3
"""R1 Gate F: one-shot, read-only WikiText-2 TEST split evaluation.

Frozen BEFORE observing test results: same step-600 OpenMythos GQA checkpoint,
byte tokenizer, Add-1 ngrams, EXACT RNG-replayed training examples, evaluation
window algorithm and fixed 256 nonoverlapping length-64 windows. A test win
does not demonstrate Claude Mythos architecture/weight fidelity or fluent text.
No updates to weights, optimizer, tokenizer, data or training hyperparameters.
"""
import argparse
import json
from pathlib import Path

import torch

from common import atomic_json, commit_id, get_repo, load_upstream
from r1_exposure_baselines import fit_seen_ngram, replay_observed_pairs
from r1_gate_e_validation import evaluate_windows, summarize_windows
from r1_gate_f_prepare_test import validate_test_manifest
from r1_language_diagnostics import fitted_byte_models, validate_checkpoint
from r1_text_pilot import TOKENIZER_ID, text_tokens


PROTOCOL = {
    "checkpoint_step": 600,
    "test_docs": 1200,
    "max_test_bytes": 250000,
    "test_windows": 256,
    "byte_tokenizer": TOKENIZER_ID,
    "ngram_smoothing": 1.0,
    "evaluation_split": "test",
    "no_training_or_model_selection": True,
}


def validate_frozen_inputs(report, checkpoint, manifest,
                           train_meta, val_meta, test_meta):
    """Fail closed on drift, mislabeled split or accidental same-file usage."""
    validate_test_manifest(manifest)
    if manifest["file"]["sha256"] != test_meta["file_sha256"]:
        raise ValueError("Test data SHA mismatch; pinned test manifest is invalid")
    if manifest["file"]["documents"] != PROTOCOL["test_docs"]:
        raise ValueError("Test document selection differs from the frozen protocol")
    if report.get("tokenizer") != TOKENIZER_ID:
        raise ValueError("Model tokenizer differs from fixed Gate F protocol")
    if checkpoint.get("step") != PROTOCOL["checkpoint_step"]:
        raise ValueError("Gate F accepts only the previously frozen step-600 checkpoint")
    if (report["hyperparameters"]["seq_len"] != 64 or
            report["hyperparameters"]["attention"] != "gqa" or
            report["hyperparameters"]["depth"] != 2):
        raise ValueError("Unexpected model config; Gate F is fixed to the Gate D model")
    for original in (train_meta, val_meta):
        if test_meta["file_sha256"] == original["file_sha256"]:
            raise ValueError("Test file duplicates training or validation source file")
        if test_meta["selected_bytes_sha256"] == original["selected_bytes_sha256"]:
            raise ValueError("Test prefix duplicates a previously used data prefix")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", default=".")
    p.add_argument("--pilot-dir", default="research/mini_mythos/results/r1/pilot_gqa_step600")
    p.add_argument("--test-dir", default="research/mini_mythos/results/r1/gate_f_test")
    p.add_argument("--test-windows", type=int, default=256)
    p.add_argument("--max-test-bytes", type=int, default=250000)
    p.add_argument("--out", default="research/mini_mythos/results/r1/gate_f_result.json")
    p.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    args = p.parse_args()
    if (args.test_windows != PROTOCOL["test_windows"] or
            args.max_test_bytes != PROTOCOL["max_test_bytes"]):
        p.error("Gate F test protocol is frozen: exactly 256 windows and 250000-byte prefix")
    if args.device == "cuda" and not torch.cuda.is_available():
        p.error("CUDA requested but unavailable")
    root = get_repo(args.repo)
    results = (root / "research/mini_mythos/results").resolve()
    pilot_dir, test_dir, out = (Path(raw).resolve() for raw in (
        args.pilot_dir, args.test_dir, args.out
    ))
    if any(not path.is_relative_to(results) for path in (
        pilot_dir, test_dir, out
    )):
        p.error("All paths must be under research/mini_mythos/results")
    if out.exists():
        p.error("Test result already exists: NEVER overwrite a one-shot test report")

    report = json.loads((pilot_dir / "report.json").read_text(encoding="utf-8"))
    checkpoint = torch.load(
        pilot_dir / "latest.pt", map_location="cpu", weights_only=True)
    manifest = json.loads(
        (test_dir / "manifest.json").read_text(encoding="utf-8")
    )
    test_path = (test_dir / "test.txt").resolve()
    if Path(manifest["file"]["path"]).resolve() != test_path:
        raise ValueError("Test file path differs from pinned test manifest")

    hyper = report["hyperparameters"]
    seq_len = int(hyper["seq_len"])
    train_meta, validation_meta = (
        report["source_provenance"]["train"],
        report["source_provenance"]["validation"],
    )
    train, checked_train = text_tokens(
        train_meta["source_path"], train_meta["selected_bytes"], seq_len)
    validation, checked_validation = text_tokens(
        validation_meta["source_path"], validation_meta["selected_bytes"], seq_len)
    test, checked_test = text_tokens(
        test_path, PROTOCOL["max_test_bytes"], seq_len)
    validate_frozen_inputs(
        report, checkpoint, manifest,
        checked_train, checked_validation, checked_test
    )

    # Validate original training+validation fingerprint without exposing test.
    module = load_upstream(root)
    cfg = module.MythosConfig(**report["configuration"])
    validate_checkpoint(
        checkpoint, report, cfg, checked_train, checked_validation)
    seen_x, seen_y, rng_end, replay = replay_observed_pairs(
        train, steps=600, batch_size=hyper["batch_size"],
        seq_len=seq_len, seed=hyper["seed"]
    )
    if not torch.equal(rng_end, checkpoint["offset_rng_state"]):
        raise ValueError("RNG replay mismatch: cannot claim same train exposure")
    matched_u, matched_b = fit_seen_ngram(seen_x, seen_y, smoothing=1.0)
    _, full_b = fitted_byte_models(train, smoothing=1.0)

    torch.set_num_threads(min(4, torch.get_num_threads()))
    model = module.OpenMythos(cfg).to(args.device).eval()
    model.load_state_dict(checkpoint["model"], strict=True)
    rows = evaluate_windows(
        model, test, seq_len=seq_len, loops=hyper["depth"],
        windows=PROTOCOL["test_windows"], device=args.device,
        matched_unigram=matched_u, matched_bigram=matched_b,
        full_bigram=full_b
    )
    if len(rows) != PROTOCOL["test_windows"]:
        raise ValueError("Not enough test data for 256 fixed windows")
    summary = summarize_windows(rows)

    result = {
        "experiment": "R1 Gate F one-shot frozen WikiText-2 test-split evaluation",
        "protocol": PROTOCOL,
        "code_revision": commit_id(root),
        "split": "test (official separate WikiText-2 split)",
        "test_dataset": {
            "source": manifest["source"], "config": manifest["config"],
            "revision_requested": manifest["revision_requested"],
            "resolved_revision": manifest["resolved_revision"],
            "documents": manifest["file"]["documents"],
            "full_test_file_sha256": checked_test["file_sha256"],
            "selected_test_prefix_sha256": checked_test["selected_bytes_sha256"],
            "selected_test_bytes": checked_test["selected_bytes"],
        },
        "train_selected_sha256": checked_train["selected_bytes_sha256"],
        "validation_selected_sha256": checked_validation["selected_bytes_sha256"],
        "checkpoint_path": str(pilot_dir / "latest.pt"),
        "checkpoint_step": 600,
        "offset_rng_matches_checkpoint": True,
        "training_example_replay": replay,
        "test_summary": summary,
        "per_window": rows,
        "limitations": "Separate WikiText-2 test split, frozen setup; the same "
                       "byte tokenizer and Add-1 baselines as validation. "
                       "Window bootstrap is exploratory and windows can be "
                       "correlated. Single seed/single small model; no "
                       "cross-tokenizer PPL comparisons or evidence of actual "
                       "Anthropic Claude Mythos topology/weights.",
    }
    atomic_json(out, result)
    print("Frozen checkpoint:", result["checkpoint_step"])
    print("Pinned WikiText dataset revision:", manifest["resolved_revision"])
    print("Training RNG replay matches checkpoint: True")
    print("Official test windows:", summary["windows"])
    print("Test scored target bytes:", summary["target_tokens"])
    for key in ("model", "matched_unigram", "matched_bigram", "full_corpus_bigram"):
        stats = summary[key]
        print(key, "test NLL:", round(stats["nll"], 6),
              "test PPL:", round(stats["ppl"], 6))
    paired = summary["paired_matched_bigram_minus_model_nll"]
    print("Matched Bigram minus model test NLL:", paired["observed_mean"])
    print("Exploratory paired window interval:", paired["percentile_95_interval"])
    print("Fraction test windows model wins:",
          summary["fraction_windows_model_better_than_matched_bigram"])
    print("Predicted space fraction:",
          summary["argmax_predicted_space_fraction"])
    print("Saved:", out)


if __name__ == "__main__":
    main()
