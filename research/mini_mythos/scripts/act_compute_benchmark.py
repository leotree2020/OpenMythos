"""Paired CPU forward/backward microbenchmark on already-trained ACT arms.

No optimizer steps are performed. Identical deterministic batches and alternating
measurement order reduce, but do not eliminate, CPU timing confounding.
"""
import statistics
import time

import torch
from act_remainder import act_probability_hook
from common import toy_batch


def paired_benchmark(original, forced, depth, *, device="cpu", warmup=3,
                     repeats=15, batch_seed=88001):
    if warmup < 0 or repeats < 1 or depth < 1:
        raise ValueError("Invalid benchmark warmup/repeats/depth")
    original.eval()
    forced.eval()
    x, y = toy_batch(torch, batch_seed, device=device)
    samples = {"original": [], "forced_final": []}
    models = {"original": original, "forced_final": forced}

    def once(name):
        model = models[name]
        model.zero_grad(set_to_none=True)
        observed = []
        start = time.perf_counter()
        with act_probability_hook(model, depth, force_final=(name == "forced_final"),
                                  observed=observed):
            logits = model(x, n_loops=depth)
        forward = time.perf_counter() - start
        loss = torch.nn.functional.cross_entropy(
            logits.reshape(-1, logits.shape[-1]), y.reshape(-1)
        )
        start = time.perf_counter()
        loss.backward()
        backward = time.perf_counter() - start
        if not bool(torch.isfinite(loss.detach())):
            raise RuntimeError("Nonfinite benchmark loss")
        return {"forward_seconds": forward, "backward_seconds": backward,
                "total_seconds": forward + backward, "actual_loops": len(observed)}

    for iteration in range(warmup + repeats):
        # Alternate arm ordering to mitigate drift in clock, cache and temperature.
        order = ("original", "forced_final") if iteration % 2 == 0 else ("forced_final", "original")
        for name in order:
            measurement = once(name)
            if iteration >= warmup:
                samples[name].append(measurement)

    def stats(name):
        values = samples[name]
        return {
            "forward_median_seconds": statistics.median(v["forward_seconds"] for v in values),
            "backward_median_seconds": statistics.median(v["backward_seconds"] for v in values),
            "total_median_seconds": statistics.median(v["total_seconds"] for v in values),
            "actual_loops_mean": statistics.mean(v["actual_loops"] for v in values),
            "raw_samples": values,
        }

    a, b = stats("original"), stats("forced_final")
    return {
        "warmup": warmup, "repeats": repeats, "batch_seed": batch_seed,
        "original": a, "forced_final": b,
        "forced_to_original_median_total_ratio":
            b["total_median_seconds"] / a["total_median_seconds"],
        "caveat": "CPU wall-clock, includes probability hook overhead; not FLOPs. "
                  "Single synthetic batch reused; no optimizer update. "
                  "Timing is noisy and not an inference-throughput benchmark.",
    }
