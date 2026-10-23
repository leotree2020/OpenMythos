#!/usr/bin/env python3
"""
P1-C Gate 1 GPU Smoke Script (fail-closed)
Uses official Parcae pinned at 69284c13746e849104f738d6d1a347b1f457df76.
Does NOT modify or reimplement Parcae core / loss / training architecture.

Official forward() returns dict["loss"] | ["logits"] | ["log_ppl"].
This script passes labels and uses output["loss"].
"""
import argparse
import json
import sys
import time
import traceback
from pathlib import Path

PARCAE_COMMIT = "69284c13746e849104f738d6d1a347b1f457df76"

def fail(result, reason, log_fn, exit_code=1):
    result["status"] = "FAIL"
    result["fail_reason"] = reason
    result["errors"].append(reason)
    log_fn(f"FAIL: {reason}")
    return exit_code

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=4)
    parser.add_argument("--micro-batch", type=int, default=2)
    parser.add_argument("--seq-len", type=int, default=128)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=str, default="p1c_gate1_smoke.json")
    parser.add_argument("--log", type=str, default="p1c_gate1_smoke.log")
    args = parser.parse_args()

    result = {
        "status": "NOT_TESTED",
        "parcae_commit": PARCAE_COMMIT,
        "gpu_tested": False,
        "official_muonadamw": "NOT_TESTED",
        "actual_sampled_recurrence": "NOT_MEASURED",
        "errors": [],
    }

    log_path = Path(args.log)
    log_path.write_text("")

    def log(msg):
        print(msg)
        with open(log_path, "a") as f:
            f.write(msg + "\n")

    if args.steps < 1 or args.micro_batch < 1 or args.seq_len < 1:
        with open(args.out, "w") as f:
            json.dump(result, f, indent=2)
        return fail(result, "invalid steps/micro-batch/seq-len", log)

    try:
        try:
            import torch
            result["torch_version"] = torch.__version__
            result["cuda_available"] = torch.cuda.is_available()
            if result["cuda_available"]:
                result["gpu_name"] = torch.cuda.get_device_name(0)
                result["cuda_version"] = torch.version.cuda
                result["gpu_tested"] = True
                device = torch.device("cuda")
            else:
                result["status"] = "CPU_ONLY_NOT_TESTED"
                log("CUDA not available. GPU path NOT TESTED.")
                device = torch.device("cpu")
        except ImportError:
            result["status"] = "NO_TORCH_CPU_CHECK_ONLY"
            log("torch not installed. GPU path NOT TESTED.")
            with open(args.out, "w") as f:
                json.dump(result, f, indent=2)
            return 0

        try:
            import parcae_lm
            result["parcae_import"] = "OK"
            config = parcae_lm.create_config("parcae-small-140m")
            result["mean_recurrence_config"] = getattr(config, "mean_recurrence", None)
            result["mean_backprop_depth_config"] = getattr(config, "mean_backprop_depth", None)
            result["use_fused_head"] = getattr(config, "use_fused_head", None)
            log(f"Config: mean_recurrence={result['mean_recurrence_config']}, fused_head={result['use_fused_head']}")

            if not result["cuda_available"]:
                result["status"] = "CPU_CONFIG_OK_GPU_NOT_TESTED"
                log("CPU config check PASS. Full GPU path NOT TESTED.")
                with open(args.out, "w") as f:
                    json.dump(result, f, indent=2)
                return 0

            torch.manual_seed(args.seed)
            model = parcae_lm.create_model("parcae-small-140m")
            model = model.to(device)
            model.train()
            result["model_params"] = sum(p.numel() for p in model.parameters())
            result["effective_config"] = {
                "micro_batch": args.micro_batch,
                "seq_len": args.seq_len,
                "steps": args.steps,
                "seed": args.seed,
            }

            vocab = getattr(config, "vocab_size", 32768)
            input_ids = torch.randint(0, vocab, (args.micro_batch, args.seq_len), device=device)
            labels = input_ids.clone()

            optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)
            result["optimizer_used"] = "AdamW (official MuonAdamW NOT TESTED)"

            peak_mem = 0.0
            step_times = []
            losses = []
            param_before = {n: p.detach().clone() for n, p in model.named_parameters() if p.requires_grad}

            for step in range(args.steps):
                torch.cuda.reset_peak_memory_stats()
                torch.cuda.synchronize()
                t0 = time.perf_counter()

                output = model(input_ids, labels=labels, return_logits=False)
                if not isinstance(output, dict) or "loss" not in output:
                    return fail(result, "forward did not return dict with 'loss'", log)
                loss = output["loss"]
                if loss is None or not torch.isfinite(loss):
                    return fail(result, "nonfinite or missing loss", log)

                loss.backward()

                core_grad_ok = False
                inj_grad_ok = False
                for n, p in model.named_parameters():
                    if p.grad is None:
                        continue
                    if not torch.isfinite(p.grad).all():
                        return fail(result, f"nonfinite grad in {n}", log)
                    gsum = p.grad.abs().sum().item()
                    if gsum > 0:
                        if any(k in n.lower() for k in ("core", "recurrent", "core_block")):
                            core_grad_ok = True
                        if any(k in n.lower() for k in ("injection", "diagonal", "adapter")):
                            inj_grad_ok = True

                if not core_grad_ok:
                    return fail(result, "Recurrent Core gradient not observed", log)
                if not inj_grad_ok:
                    return fail(result, "DiagonalInjection / adapter gradient not observed", log)

                optimizer.step()
                optimizer.zero_grad(set_to_none=True)

                torch.cuda.synchronize()
                dt = time.perf_counter() - t0
                step_times.append(dt)
                losses.append(float(loss.detach().cpu()))

                peak = torch.cuda.max_memory_allocated() / 1024**3
                peak_mem = max(peak_mem, peak)
                log(f"step {step}: loss={losses[-1]:.4f} time={dt:.4f}s")

            updated = False
            for n, p in model.named_parameters():
                if n in param_before and not torch.allclose(p, param_before[n], atol=1e-6):
                    updated = True
                    break
            if not updated:
                return fail(result, "no parameters updated after optimizer step", log)

            tokens_per_sec = (args.micro_batch * args.seq_len) / (sum(step_times) / len(step_times))
            result.update({
                "status": "PASS",
                "peak_vram_gb": round(peak_mem, 3),
                "avg_step_time_s": round(sum(step_times) / len(step_times), 4),
                "tokens_per_sec": round(tokens_per_sec, 1),
                "losses": losses,
                "core_grad_observed": True,
                "injection_grad_observed": True,
                "params_updated": True,
            })
            log("GPU smoke PASS")

        except ImportError as e:
            result["status"] = "BLOCKED_MISSING_PARCAE"
            result["errors"].append(str(e))
            log(f"BLOCKED: {e}")
            with open(args.out, "w") as f:
                json.dump(result, f, indent=2)
            return 1

    except Exception as e:
        result["status"] = "ERROR"
        result["errors"].append(traceback.format_exc())
        log(traceback.format_exc())
        with open(args.out, "w") as f:
            json.dump(result, f, indent=2)
        return 1

    with open(args.out, "w") as f:
        json.dump(result, f, indent=2)
    log(f"Result written to {args.out}")
    return 0 if result["status"] == "PASS" else 1

if __name__ == "__main__":
    sys.exit(main())
