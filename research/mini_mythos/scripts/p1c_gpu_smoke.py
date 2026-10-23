#!/usr/bin/env python3
"""
P1-C Gate 1 GPU Smoke Script
Uses official Parcae (pinned commit 69284c1) via parcae_lm.create_model.
Does NOT modify or reimplement Parcae core.

CPU mode: performs import / config checks only; heavy compute marked NOT TESTED.
GPU mode: limited synthetic fwd/bwd/update + gradient reachability checks.
"""
import argparse
import json
import os
import sys
import time
import traceback
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=4, help="Optimizer steps (GPU only)")
    parser.add_argument("--micro-batch", type=int, default=2)
    parser.add_argument("--seq-len", type=int, default=128)  # reduced for smoke
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=str, default="p1c_gate1_smoke.json")
    parser.add_argument("--log", type=str, default="p1c_gate1_smoke.log")
    args = parser.parse_args()

    result = {
        "status": "NOT_TESTED",
        "parcae_commit": "69284c13746e849104f738d6d1a347b1f457df76",
        "gpu_tested": False,
        "errors": [],
    }

    log_path = Path(args.log)
    log_path.write_text("")  # truncate

    def log(msg):
        print(msg)
        with open(log_path, "a") as f:
            f.write(msg + "\n")

    try:
        import torch
        result["torch_version"] = torch.__version__
        result["cuda_available"] = torch.cuda.is_available()
        if result["cuda_available"]:
            result["gpu_name"] = torch.cuda.get_device_name(0)
            result["cuda_version"] = torch.version.cuda
            result["gpu_tested"] = True
            device = "cuda"
        else:
            result["gpu_name"] = None
            result["status"] = "CPU_ONLY_NOT_TESTED"
            device = "cpu"
            log("CUDA not available. GPU path NOT TESTED.")

        # Try official Parcae
        try:
            import parcae_lm
            result["parcae_import"] = "OK"
            config = parcae_lm.create_config("parcae-small-140m")
            result["mean_recurrence"] = getattr(config, "mean_recurrence", None)
            result["mean_backprop_depth"] = getattr(config, "mean_backprop_depth", None)
            log(f"Config loaded: mean_recurrence={result['mean_recurrence']}, mean_backprop_depth={result['mean_backprop_depth']}")

            if not result["cuda_available"]:
                result["status"] = "CPU_CONFIG_OK_GPU_NOT_TESTED"
                log("CPU config check PASS. Full model construct / train path NOT TESTED on GPU.")
                with open(args.out, "w") as f:
                    json.dump(result, f, indent=2)
                return 0

            # GPU path
            torch.manual_seed(args.seed)
            model = parcae_lm.create_model("parcae-small-140m")
            model = model.to(device)
            model.train()
            result["model_params"] = sum(p.numel() for p in model.parameters())

            # Synthetic tokens
            vocab = getattr(config, "vocab_size", 32768)
            tokens = torch.randint(0, vocab, (args.micro_batch, args.seq_len), device=device)

            optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)  # simple for smoke; official uses MuonAdamW

            peak_mem = 0
            step_times = []
            losses = []

            for step in range(args.steps):
                torch.cuda.reset_peak_memory_stats()
                t0 = time.perf_counter()
                logits = model(tokens)
                # Assume cross-entropy style; adapt if model returns loss directly
                if isinstance(logits, tuple):
                    logits = logits[0]
                loss = torch.nn.functional.cross_entropy(
                    logits.view(-1, logits.size(-1)), tokens.view(-1)
                )
                loss.backward()
                # Gradient reachability (best-effort names)
                core_grad = any(
                    p.grad is not None and p.grad.abs().sum() > 0
                    for n, p in model.named_parameters()
                    if "core" in n.lower() or "recurrent" in n.lower()
                )
                inj_grad = any(
                    p.grad is not None and p.grad.abs().sum() > 0
                    for n, p in model.named_parameters()
                    if "injection" in n.lower() or "diagonal" in n.lower()
                )
                optimizer.step()
                optimizer.zero_grad()
                dt = time.perf_counter() - t0
                step_times.append(dt)
                losses.append(float(loss.detach().cpu()))
                peak = torch.cuda.max_memory_allocated() / 1024**3
                peak_mem = max(peak_mem, peak)
                log(f"step {step}: loss={losses[-1]:.4f} time={dt:.3f}s core_grad={core_grad} inj_grad={inj_grad}")

            tokens_per_sec = (args.micro_batch * args.seq_len) / (sum(step_times) / len(step_times))
            result.update({
                "status": "GPU_SMOKE_RAN",
                "peak_vram_gb": round(peak_mem, 2),
                "avg_step_time_s": round(sum(step_times)/len(step_times), 4),
                "tokens_per_sec": round(tokens_per_sec, 1),
                "losses": losses,
                "core_grad_observed": core_grad,
                "injection_grad_observed": inj_grad,
                "actual_recurrence": result.get("mean_recurrence"),
            })
            if not torch.isfinite(torch.tensor(losses)).all():
                result["status"] = "FAIL_NONFINITE"

        except ImportError as e:
            result["parcae_import"] = "BLOCKED"
            result["errors"].append(str(e))
            result["status"] = "BLOCKED_MISSING_PARCAE"
            log(f"BLOCKED: parcae_lm not importable: {e}")

    except Exception as e:
        result["status"] = "ERROR"
        result["errors"].append(traceback.format_exc())
        log(traceback.format_exc())

    with open(args.out, "w") as f:
        json.dump(result, f, indent=2)
    log(f"Result written to {args.out}")
    return 0 if result["status"] in ("CPU_CONFIG_OK_GPU_NOT_TESTED", "GPU_SMOKE_RAN") else 1

if __name__ == "__main__":
    sys.exit(main())
