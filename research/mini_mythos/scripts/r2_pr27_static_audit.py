#!/usr/bin/env python3
"""R2 upstream-first PR #27 static provenance/known-risk audit (NO GPU).

Requires locally fetched immutable PR commit, but does not fetch or execute
any upstream PR scripts. Does not import experiments/train.py or allocate a
117.8M-model. Source SHA and original flags are logged verbatim for review.
"""
import argparse
import hashlib
from pathlib import Path
import subprocess

from common import atomic_json, commit_id, get_repo


PINNED_SHA = "2954bc275ffb8ad5c60f74f7299a9ad9e531d3e4"
PATHS = ("experiments/README.md", "experiments/config.py", "experiments/data.py",
         "experiments/train.py", "experiments/evaluate.py", "experiments/run_all.sh")


def check_pr27_sources(sources, main_source):
    """Static evidence rules. Flags never imply that any GPU run took place."""
    for path in PATHS:
        if path not in sources:
            raise ValueError("Missing upstream file: " + path)
    train, eval_code, data, config, runner = (
        sources["experiments/train.py"], sources["experiments/evaluate.py"],
        sources["experiments/data.py"], sources["experiments/config.py"],
        sources["experiments/run_all.sh"]
    )
    rules = [
        ("PR27_GPU_HARDCODE", "P0", "CUDA required before execution",
         'device = "cuda"' in train and 'x.to("cuda"' in eval_code,
         "Source hardcodes GPU for training/evaluation; no GPU available in Codespaces."),
        ("PR27_ROPE_COMPLEX_BUFFER_CAST", "P0", "BF16 conversion of complex RoPE buffers",
         "model = OpenMythos(mcfg).to(device=device, dtype=dtype)" in train
         and "register_buffer(\"freqs_cis\"" in main_source
         and "torch.polar(" in main_source,
         "Converting the full module to BF16 casts complex64 buffers to real BF16 "
         "and discards RoPE imaginary components. Confirm with CPU probe. "
         "Retain complex RoPE buffers and separately validate GPU BF16 forward/backward."),
        ("PR27_TRAIN_EVAL_TOKENIZER_MISMATCH", "P0", "Evaluation may override tokenizer",
         'ap.add_argument("--tokenizer"' in eval_code
         and "get_tokenizer(args.tokenizer)" in eval_code
         and "get_tokenizer(cfg.tokenizer)" in train,
         "Evaluation constructs tokenizer from independent CLI argument; checkpoint "
         "stores config that must be enforced for ID and vocabulary equivalence."),
        ("PR27_DATASET_REVISION_MUTABLE", "P0", "Streaming FineWeb-Edu revision unpinned",
         "streaming=True" in data and "revision=" not in data,
         "Data revision, source shard and sample hashes must be pinned."),
        ("PR27_LOADER_NO_RESUME_CURSOR", "P0", "Checkpoint has no dataloader cursor",
         '"model": model.state_dict()' in train and
         '"opt": opt.state_dict()' in train and
         "loader_iter = iter(loader)" in train and
         '"loader_state"' not in train,
         "No serialized loader position and random states; cannot reproduce exact "
         "next batch on resume. PR27 train.py has no resume entry point."),
        ("PR27_HELDOUT_SKIP_ASSUMPTION", "P1", "Heldout skip_docs heuristic",
         "skip_docs=2_000_000" in eval_code and "skip(self.skip_docs)" in data,
         "Document skipping based on estimated train docs does not prove disjoint "
         "train/validation on future mutable streaming revisions."),
        ("PR27_EVAL_UNSAFE_PICKLE", "P1", "Untrusted checkpoint deserialization",
         "weights_only=False" in eval_code,
         "Do not unpickle externally sourced checkpoint; use tensor/primitive-only format."),
        ("PR27_LORA_PARAM_DRIFT", "P1", "Loop depth changes per-loop adapter parameters",
         "max_loop_iters=1" in runner and "max_loop_iters=8" in runner
         and "self.scale = nn.Embedding(max_loops, rank)" in main_source,
         "The single-loop and eight-loop arms differ in adapter embedding "
         "parameters (7 * lora_rank) and active compute budget."),
        ("PR27_BASELINE_NOT_PLAIN_TRANSFORMER", "P1",
         "One-loop recurrent architecture is not a plain Transformer",
         'n_loops=n_loops_step' in train and
         "self.recurrent = RecurrentBlock(cfg)" in main_source
         and "self.injection = LTIInjection(cfg.dim)" in main_source,
         "baseline_1 retains shared recurrent block, LTI injection, ACT, MoE. "
         "It is a one-loop ablation, not an independently implemented dense Transformer."),
        ("PR27_LOOP_COMPUTE_NOT_MATCHED", "P1", "Loop counts change FLOPs",
         "max_loop_iters 8" in runner and "max_loop_iters 1" in runner,
         "The arms use different repeated block forward passes; compare GPU seconds "
         "and measured/estimated FLOPs, not step counts."),
        ("PR27_TRAIN_CHECKPOINT_RNG", "P1", "Training snapshot has no RNG state",
         '"tokens_seen": tokens_seen' in train and
         '"rng_state"' not in train and '"torch_rng_state"' not in train,
         "Restore Python/Torch/CUDA RNG for reproducible stochastic loops and data."),
        ("PR27_ROPE_BUFFER_CODE_AUDIT", "P1", "Complex RoPE numeric correctness",
         "register_buffer(\"freqs_cis_mla\"" in main_source
         and "torch.view_as_complex" in main_source,
         "Training should preserve complex64 RoPE phase under mixed precision."),
        ("PR27_ACT_FP32_PROMOTION", "P1", "ACT dtype under true BF16 parameter cast",
         "cumulative_p = torch.zeros(B, T, device=h.device)" in main_source
         and "still_running.float()" in main_source,
         "Promotes ACT accumulation; after casting other module weights BF16 "
         "may cause mismatched tensor dtype in downstream Coda."),
        ("PR27_FIXED_TRAIN_STEPS", "INFO", "Training budget specified",
         "max_steps: int = 15000" in config and
         "batch_size: int = 32" in config and
         "seq_len: int = 1024" in config,
         "Submitted PR describes ~491M target positions per 15000-step run; "
         "reported timing/quality are submitter claims, not reproduced."),
    ]
    return [{
        "id": rid, "priority": priority,
        "subject": subject,
        "source_flag": "FOUND" if found else "NOT_FOUND",
        "source_evidence": bool(found), "explanation": detail,
        "runtime_proved": False,
    } for rid, priority, subject, found, detail in rules]


def pr_source(repo, sha, path):
    if sha != PINNED_SHA:
        raise ValueError("PR audit must use the preregistered immutable head SHA")
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), "show", f"{sha}:{path}"],
            capture_output=True, text=True, check=True, timeout=15
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise FileNotFoundError(
            "Pinned PR #27 commit is absent from local git objects. First run: "
            "git fetch https://github.com/kyegomez/OpenMythos.git "
            "refs/pull/27/head:refs/remotes/pr27-audit; then re-run audit. "
            "Never execute the PR script before review."
        ) from exc
    return result.stdout


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", default=".")
    p.add_argument("--out", default="research/mini_mythos/results/r2/pr27_static_audit.json")
    args = p.parse_args()
    root = get_repo(args.repo)
    dest = Path(args.out).resolve()
    if not dest.is_relative_to(root / "research/mini_mythos/results"):
        p.error("Output must be under project's ignored research results directory")
    if dest.exists():
        p.error("Do not overwrite existing pinned source audit")
    sources = {path: pr_source(root, PINNED_SHA, path) for path in PATHS}
    main_src = (root / "open_mythos/main.py").read_text(encoding="utf-8")
    findings = check_pr27_sources(sources, main_src)
    report = {
        "experiment": "R2 immutable OpenMythos community PR27 static audit",
        "frozen_upstream_commit": PINNED_SHA,
        "public_PR": "https://github.com/kyegomez/OpenMythos/pull/27",
        "working_fork_git_revision": commit_id(root),
        "source_blobs_sha256": {
            path: hashlib.sha256(content.encode()).hexdigest()
            for path, content in sources.items()
        },
        "fork_core_source_sha256": hashlib.sha256(main_src.encode()).hexdigest(),
        "flags": findings,
        "gpu_execution": "NOT_PERFORMED",
        "next": "Verify complex RoPE BF16 cast on CPU and run only tiny "
                "forward/backward before a version-pinned GPU pilot; "
                "do not launch PR run_all.sh directly.",
        "caveats": "These flags are source-pattern matches, not live GPU test results "
                   "or conclusions about Anthropic Mythos internal architecture.",
    }
    atomic_json(dest, report)
    print("Pinned PR #27 commit:", PINNED_SHA)
    print("Working fork commit:", report["working_fork_git_revision"])
    for row in findings:
        print(f"[{row['priority']}] {row['id']}: {row['source_flag']}")
    print("Actual GPU PR run:", report["gpu_execution"])
    print("Saved:", dest)


if __name__ == "__main__":
    main()
