"""R2 PR #27 upstream-source provenance and RoPE BF16 regression tests.

No network and no 118M model instantiation; exercises only source scanners
and a four-element CPU PyTorch buffer.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from r2_pr27_static_audit import PINNED_SHA, PATHS, check_pr27_sources, pr_source
from r2_rope_dtype_probe import demonstrate_complex_to_bf16


class R2PR27Tests(unittest.TestCase):
    def test_all_insecure_patterns_detected_from_short_source_snippets(self):
        train = """
device = "cuda"
model = OpenMythos(mcfg).to(device=device, dtype=dtype)
tok = get_tokenizer(cfg.tokenizer)
loader_iter = iter(loader)
for step in range(cfg.max_steps):
  logits = model(x, n_loops=n_loops_step)
  state = {
      "model": model.state_dict(),
      "opt": opt.state_dict(),
      "tokens_seen": tokens_seen,
  }
"""
        evaluation = """
ap.add_argument("--tokenizer")
tok = get_tokenizer(args.tokenizer)
x = x.to("cuda", non_blocking=True)
skip_docs=2_000_000
checkpoint = torch.load(file, weights_only=False)
"""
        data = "streaming=True\n ds = ds.skip(self.skip_docs)"
        config = "max_steps: int = 15000\nbatch_size: int = 32\nseq_len: int = 1024"
        runner = "python train.py --max_loop_iters 8\npython train.py --max_loop_iters 1"
        main = """
self.register_buffer("freqs_cis", frequencies)
self.register_buffer("freqs_cis_mla", frequencies_mla)
freqs = torch.polar(x, phase)
z = torch.view_as_complex(x)
self.recurrent = RecurrentBlock(cfg)
self.injection = LTIInjection(cfg.dim)
self.scale = nn.Embedding(max_loops, rank)
cumulative_p = torch.zeros(B, T, device=h.device)
weight = weight * still_running.float()
"""
        sources = {
            "experiments/README.md": "",
            "experiments/config.py": config,
            "experiments/data.py": data,
            "experiments/train.py": train,
            "experiments/evaluate.py": evaluation,
            "experiments/run_all.sh": runner,
        }
        findings = check_pr27_sources(sources, main)
        by_name = {item["id"]: item for item in findings}
        self.assertGreaterEqual(len(by_name), 12)
        for issue in (
            "PR27_ROPE_COMPLEX_BUFFER_CAST",
            "PR27_TRAIN_EVAL_TOKENIZER_MISMATCH",
            "PR27_DATASET_REVISION_MUTABLE",
            "PR27_LOADER_NO_RESUME_CURSOR",
            "PR27_LORA_PARAM_DRIFT",
            "PR27_BASELINE_NOT_PLAIN_TRANSFORMER",
            "PR27_LOOP_COMPUTE_NOT_MATCHED",
            "PR27_ACT_FP32_PROMOTION",
        ):
            self.assertEqual(by_name[issue]["source_flag"], "FOUND", issue)
        self.assertTrue(all(not i["runtime_proved"] for i in findings))

    def test_missing_source_not_silently_ignored(self):
        with self.assertRaisesRegex(ValueError, "Missing upstream file"):
            check_pr27_sources({}, "")

    def test_unpinned_commit_is_rejected_without_git_access(self):
        with self.assertRaisesRegex(ValueError, "preregistered"):
            pr_source(Path("."), "main", PATHS[0])
        self.assertEqual(len(PINNED_SHA), 40)

    def test_torch_complex_to_bf16_discards_imaginary_component(self):
        outcome = demonstrate_complex_to_bf16()
        self.assertTrue(outcome["original_complex"])
        self.assertFalse(outcome["after_complex"])
        self.assertGreater(outcome["original_max_abs_imag"], 0.5)
        self.assertEqual(outcome["after_dtype"], "torch.bfloat16")
        self.assertIsNone(outcome["remaining_imaginary_phase"])


if __name__ == "__main__":
    unittest.main()
