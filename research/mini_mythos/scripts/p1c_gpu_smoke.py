#!/usr/bin/env python3
"""
P1-C Gate 1 GPU Smoke Script (fail-closed, evidence-complete)
Pinned Parcae: 69284c13746e849104f738d6d1a347b1f457df76
Does NOT modify Parcae core / official loss.
"""
import argparse
import json
import subprocess
import sys
import time
import traceback
from pathlib import Path

PARCAE_COMMIT = "69284c13746e849104f738d6d1a347b1f457df76"

def write_result(result, path):
    with open(path, "w") as f:
        json.dump(result, f, indent=2)

def fail(result, reason, log_fn, out_path):
    result["status"] = "FAIL"
    result["fail_reason"] = reason
    result["errors"].append(reason)
    log_fn(f"FAIL: {reason}")
    write_result(result, out_path)
    return 1

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=4)
    parser.add_argument("--micro-batch", type=int, default=2)
    parser.add_argument("--seq-len", type=int, default=128)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=str, default="p1c_gate1_smoke.json")
    parser.add_argument("--log", type=str, default="p1c_gate1_smoke.log")
    parser.add_argument("--parcae-dir", type=str, default=None, help="Path to Parcae clone for HEAD check")
    parser.add_argument("--simulate-fail", type=str, default=None, choices=["nonfinite", "no-core-grad", "no-update"])
    args = parser.parse_args()

    result = {
        "status": "NOT_TESTED",
        "parcae_commit_expected": PARCAE_COMMIT,
        "parcae_commit_actual": None,
        "gpu_tested": False,
        "gpu_operators_executed": False,
        "checks_completed": False,
        "official_muonadamw": "NOT_TESTED",
        "actual_sampled_recurrence": "NOT_MEASURED",
        "label_note": "Synthetic tokens used. This smoke does NOT validate language learning capability.",
        "timing_includes_diagnostics": True,
        "errors": [],
    }

    log_path = Path(args.log)
    log_path.write_text("")

    def log(msg):
        print(msg)
        with open(log_path, "a") as f:
            f.write(msg + "\n")

    # Arg validation
    if args.steps < 1 or args.micro_batch < 1 or args.seq_len < 1:
        return fail(result, "invalid steps/micro-batch/seq-len", log, args.out)

    # Simulate failure paths for CPU testing
    if args.simulate_fail:
        result["status"] = "FAIL"
        result["fail_reason"] = f"simulated: {args.simulate_fail}"
        result["errors"].append(result["fail_reason"])
        log(f"SIMULATED FAIL: {args.simulate_fail}")
        write_result(result, args.out)
        return 1

    # Parcae HEAD check if dir provided
    if args.parcae_dir:
        try:
            head = subprocess.check_output(
                ["git", "-C", args.parcae_dir, "rev-parse", "HEAD"], text=True
            ).strip()
            result["parcae_commit_actual"] = head
            if head != PARCAE_COMMIT:
                return fail(result, f"Parcae HEAD mismatch: {head} != {PARCAE_COMMIT}", log, args.out)
            log(f"Parcae HEAD OK: {head}")
        except Exception as e:
            return fail(result, f"failed to verify Parcae HEAD: {e}", log, args.out)

    try:
        try:
            import torch
            result["torch_version"] = torch.__version__
            result["cuda_available"] = torch.cuda.is_available()
            if result["cuda_available"]:
                result["gpu_name"] = torch.cuda.get_device_name(0)
                result["cuda_version"] = torch.version.cuda
                device = torch.device("cuda")
            else:
                result["status"] = "CPU_ONLY_NOT_TESTED"
                result["gpu_tested"] = False
                log("CUDA not available. GPU path NOT TESTED.")
                write_result(result, args.out)
                return 0
        except ImportError:
            result["status"] = "NO_TORCH_CPU_CHECK_ONLY"
            result["gpu_tested"] = False
            log("torch not installed. GPU path NOT TESTED.")
            write_result(result, args.out)
            return 0

        try:
            import parcae_lm
            result["parcae_import"] = "OK"
            config = parcae_lm.create_config("parcae-small-140m")
            result["mean_recurrence_config"] = getattr(config, "mean_recurrence", None)
            result["mean_backprop_depth_config"] = getattr(config, "mean_backprop_depth", None)
            result["use_fused_head"] = getattr(config, "use_fused_head", None)
            log(f"Config loaded: fused_head={result['use_fused_head']}")

            if not result["cuda_available"]:
                result["status"] = "CPU_CONFIG_OK_GPU_NOT_TESTED"
                write_result(result, args.out)
                return 0

            # GPU path
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
            labels = input_ids.clone()  # synthetic; official training uses shifted labels

            optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)
            result["optimizer_used"] = "AdamW (official MuonAdamW NOT TESTED)"

            peak_alloc = 0.0
            peak_reserved = 0.0
            step_times = []
            losses = []
            param_before = {n: p.detach().clone() for n, p in model.named_parameters() if p.requires_grad}

            for step in range(args.steps):
                torch.cuda.reset_peak_memory_stats()
                torch.cuda.synchronize()
                t0 = time.perf_counter()

                output = model(input_ids, labels=labels, return_logits=False)
                if not isinstance(output, dict) or "loss" not in output:
                    return fail(result, "forward did not return dict with 'loss'", log, args.out)
                loss = output["loss"]
                if loss is None or not torch.isfinite(loss):
                    return fail(result, "nonfinite or missing loss", log, args.out)

                loss.backward()
                result["gpu_operators_executed"] = True

                core_grad_ok = False
                inj_grad_ok = False
                for n, p in model.named_parameters():
                    if p.grad is None:
                        continue
                    if not torch.isfinite(p.grad).all():
                        return fail(result, f"nonfinite grad in {n}", log, args.out)
                    gsum = p.grad.abs().sum().item()
                    if gsum > 0:
                        if any(k in n.lower() for k in ("core", "recurrent", "core_block")):
                            core_grad_ok = True
                        if any(k in n.lower() for k in ("injection", "diagonal", "adapter")):
                            inj_grad_ok = True

                if not core_grad_ok:
                    return fail(result, "Recurrent Core gradient not observed", log, args.out)
                if not inj_grad_ok:
                    return fail(result, "DiagonalInjection / adapter gradient not observed", log, args.out)

                optimizer.step()
                optimizer.zero_grad(set_to_none=True)

                # Finite after update
                for n, p in model.named_parameters():
                    if p.requires_grad and not torch.isfinite(p).all():
                        return fail(result, f"nonfinite parameter after update: {n}", log, args.out)

                torch.cuda.synchronize()
                dt = time.perf_counter() - t0
                step_times.append(dt)
                losses.append(float(loss.detach().cpu()))

                peak_alloc = max(peak_alloc, torch.cuda.max_memory_allocated() / 1024**3)
                peak_reserved = max(peak_reserved, torch.cuda.max_memory_reserved() / 1024**3)
                log(f"step {step}: loss={losses[-1]:.4f} time={dt:.4f}s")

            updated = any(
                not torch.allclose(p, param_before[n], atol=1e-6)
                for n, p in model.named_parameters()
                if n in param_before
            )
            if not updated:
                return fail(result, "no parameters updated after optimizer step", log, args.out)

            tokens_per_sec = (args.micro_batch * args.seq_len) / (sum(step_times) / len(step_times))
            result.update({
                "status": "PASS",
                "gpu_tested": True,
                "checks_completed": True,
                "peak_vram_allocated_gb": round(peak_alloc, 3),
                "peak_vram_reserved_gb": round(peak_reserved, 3),
                "avg_step_time_s": round(sum(step_times) / len(step_times), 4),
                "tokens_per_sec": round(tokens_per_sec, 1),
                "losses": losses,
                "core_grad_observed": True,
                "injection_grad_observed": True,
                "params_updated": True,
                "params_finite_after_update": True,
            })
            log("GPU smoke PASS")

        except ImportError as e:
            result["status"] = "BLOCKED_MISSING_PARCAE"
            result["errors"].append(str(e))
            log(f"BLOCKED: {e}")
            write_result(result, args.out)
            return 1

    except Exception as e:
        result["status"] = "ERROR"
        result["errors"].append(traceback.format_exc())
        log(traceback.format_exc())
        write_result(result, args.out)
        return 1

    write_result(result, args.out)
    log(f"Result written to {args.out}")
    return 0 if result["status"] == "PASS" else 1

if __name__ == "__main__":
    sys.exit(main())
