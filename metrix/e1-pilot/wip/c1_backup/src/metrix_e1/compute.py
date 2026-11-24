"""Compute of METRIX E1-PILOT: device, determinism, GPU wall-clock, preflight, FLOPs, cost.

Protocol v1.1 section 0 (one NVIDIA A100 80GB; determinism settings), section 7 (device check and device-name rule;
4 GPU hours from the first model load to the end of the TEST evaluation), section 8 steps 1-2 (GPU check, device
name at the first model load, preflight), section 10 (compute accounting), section 11 ST7, ST8, ST9, ST11. Numbers
from metrix_e1.contract; choices the protocol leaves open: interpretations B17 (preflight estimate), B18 (FLOPs).

The device ledger and the GPU clock are JSON files kept with the run's records, so that the recorded device name and
the accumulated GPU time survive process restarts within one pilot.
"""
import json
import os
import time
from pathlib import Path

import torch

from . import stops as STP
from .mode import SMOKE_DEVICE_NOTE
from .train import ARMS_TRAINED

DETERMINISM_ENV = "CUBLAS_WORKSPACE_CONFIG"


# ------------------------------------------------------------------------------------------ determinism (0)

def set_determinism(contract):
    """Protocol section 0: torch.use_deterministic_algorithms(True), TF32 off, CUBLAS_WORKSPACE_CONFIG as frozen.
    Must run before CUDA is initialised (the cuBLAS workspace setting is read at initialisation). Returns the
    settings (determinism_settings())."""
    want = contract.stops.cublas_workspace_config
    if torch.cuda.is_available() and torch.cuda.is_initialized() and os.environ.get(DETERMINISM_ENV) != want:
        raise RuntimeError("CUDA already initialised without %s=%s" % (DETERMINISM_ENV, want))
    os.environ[DETERMINISM_ENV] = want
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.set_float32_matmul_precision("highest")
    got = determinism_settings()
    if not (got["deterministic_algorithms"] and got[DETERMINISM_ENV] == want and not got["cuda_matmul_allow_tf32"]
            and not got["cudnn_allow_tf32"]):
        raise RuntimeError("determinism settings did not take effect: %r" % got)
    return got


def determinism_settings():
    """The settings as they are now (written into the experiment record)."""
    return {"deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
            DETERMINISM_ENV: os.environ.get(DETERMINISM_ENV),
            "cuda_matmul_allow_tf32": torch.backends.cuda.matmul.allow_tf32,
            "cudnn_allow_tf32": torch.backends.cudnn.allow_tf32,
            "cudnn_benchmark": torch.backends.cudnn.benchmark,
            "cudnn_deterministic": torch.backends.cudnn.deterministic,
            "float32_matmul_precision": torch.get_float32_matmul_precision()}


# ------------------------------------------------------------------------------------------ device (7, ST8, ST9)

def device_info():
    """Full name and total memory of CUDA device 0, or None without CUDA."""
    if not torch.cuda.is_available():
        return None
    return {"name": torch.cuda.get_device_name(0), "total_memory": torch.cuda.get_device_properties(0).total_memory}


def check_device(fz, contract, mode, info=None):
    """ST8 device check (formal and preflight modes). Smoke mode skips it and returns the note that must be recorded
    ("smoke: device check skipped"). `info` overrides device_info() (tests)."""
    if mode.smoke:
        return SMOKE_DEVICE_NOTE
    info = device_info() if info is None else info
    STP.st8(fz, contract, None if info is None else info["name"], 0 if info is None else info["total_memory"])
    return info


class DeviceLedger:
    """Section 7 device-name rule: the full name read at the first model load is recorded; every later training or
    evaluation run compares the name read at its start with it (ST9)."""

    def __init__(self, path):
        self.path = Path(path)

    def recorded(self):
        if not self.path.exists():
            return None
        return json.loads(self.path.read_text(encoding="utf-8"))["device_name"]

    def record_first(self, name):
        if self.path.exists():
            raise RuntimeError("device name already recorded in %s" % self.path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"device_name": name, "recorded_at_unix": time.time()}, ensure_ascii=False) + "\n",
                             encoding="utf-8")
        return name

    def check(self, fz, current_name):
        """ST9 at the start of a run. Nothing recorded yet is a wrong call order (record_first comes first, at the
        first model load), not a device change: it raises RuntimeError, not ST9."""
        recorded = self.recorded()
        if recorded is None:
            raise RuntimeError("no device name recorded in %s; record_first() at the first model load" % self.path)
        STP.st9(fz, recorded, current_name)
        return current_name


# ------------------------------------------------------------------------------------------ GPU clock (7, ST7)

class GpuClock:
    """Cumulative GPU wall-clock from the first model load (section 7), kept in a JSON file {"segments": [[start,
    end], ...], "open": start or null}. open() writes its start at once, so a segment of a process that dies is not
    lost: a later process sees it open and counts it up to now (it may over-count the time after the crash, never
    under-count; ST7 stays on the safe side); close() ends the open segment, whichever process opened it."""

    def __init__(self, path, now=time.time):
        self.path = Path(path)
        self.now = now

    def _state(self):
        if not self.path.exists():
            return {"segments": [], "open": None}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, state):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(state) + "\n", encoding="utf-8")

    def open(self):
        st = self._state()
        if st["open"] is not None:
            raise RuntimeError("GPU clock segment already open since %r (close it first)" % st["open"])
        st["open"] = self.now()
        self._write(st)

    def close(self):
        st = self._state()
        if st["open"] is None:
            raise RuntimeError("no GPU clock segment open")
        st["segments"].append([st["open"], self.now()])
        st["open"] = None
        self._write(st)

    def used(self):
        st = self._state()
        closed = sum(b - a for a, b in st["segments"])
        return closed + (self.now() - st["open"] if st["open"] is not None else 0.0)

    def check(self, fz, contract, next_seconds=0.0):
        """ST7 before a step: stop if the limit is exceeded or the next step would exceed it."""
        STP.st7(fz, contract, self.used(), next_seconds)
        return self.used()


# ------------------------------------------------------------------------------------ FLOPs (10; B18) and cost

def flops(contract, params, tokens, kind):
    """Section 10 (coefficients from the frozen text, contract.Accounting): training ~ 6 P T, forward ~ 2 P T."""
    acc = contract.accounting
    return {"train": acc.train_flops_per_param_token, "forward": acc.forward_flops_per_param_token}[kind] * params * tokens


def run_flops(contract, result, params_forward):
    """Compute accounting of one training run (train.RunResult): fact-token training FLOPs and, for arm A, the
    anchor FLOPs listed separately (B18: base forward + trained model forward and backward)."""
    out = {"params_forward": params_forward, "fact_tokens": result.fact_tokens, "steps": result.steps_run,
           "wall_seconds": result.wall_seconds, "train_flops": flops(contract, params_forward, result.fact_tokens, "train")}
    if result.anchor_tokens:
        out["anchor_tokens"] = result.anchor_tokens
        out["anchor_flops"] = (flops(contract, params_forward, result.anchor_tokens, "forward")
                               + flops(contract, params_forward, result.anchor_tokens, "train"))
    return out


def peak_memory_bytes(device):
    """Peak CUDA memory allocated on the device, or the peak resident set size of the process on CPU."""
    if torch.device(device).type == "cuda":
        return torch.cuda.max_memory_allocated(device)
    import resource
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024


def cost_usd(hours, usd_per_hour):
    """Planning cost; the hourly rate is an input (Implementation Task Order V1 section 8 gives it for the RUNBOOK)."""
    return hours * usd_per_hour


# ----------------------------------------------------------------------------------- preflight (8 step 2; B17)

def preflight_summary(log, device):
    """Per-step seconds, tokens/s and peak memory of the preflight steps (train.RunResult.log entries carry
    cumulative seconds). The first step is reported but excluded from the mean (warm-up)."""
    t = [e["seconds"] for e in log]
    per_step = [t[0]] + [b - a for a, b in zip(t, t[1:])]
    tokens = [e["fact_tokens"] + e.get("anchor_tokens", 0) for e in log]
    rest = per_step[1:] if len(per_step) > 1 else per_step
    mean = sum(rest) / len(rest)
    return {"steps": len(log), "seconds_per_step": per_step, "mean_seconds_per_step_excluding_first": mean,
            "tokens_per_second": sum(tokens[1:] or tokens) / sum(rest), "peak_memory_bytes": peak_memory_bytes(device)}


def evaluation_units(contract):
    """B17: evaluations of the pilot in units of one DEV evaluation (evaluate.evaluate_model, split "dev"): on DEV, N,
    the 30 runs and the second evaluation of F's 3 selected checkpoints (G0.8); on TEST, once, N and the final
    checkpoints of the 5 trained arms x 3 seeds (the selected configurations; unselected search runs are not
    evaluated on TEST), scaled by test / dev questions per fact (taken for the whole evaluation: an upper side)."""
    tr, acc = contract.training, contract.accounting
    dev = 1 + contract.arms.counts["total_training_runs"] + len(tr.training_seeds)
    test = (1 + len(ARMS_TRAINED) * len(tr.training_seeds)) * acc.test_questions_per_fact / acc.dev_questions_per_fact
    return dev + test


def estimate_total_hours(contract, mean_step_seconds, fact_tokens_per_step, anchor_tokens_per_step,
                         dev_evaluation_seconds, used_seconds=0.0):
    """B17: (measured mean seconds per step of the first configuration) x sum over the 30 runs of steps x FLOP factor
    (A: 1 + (forward + train) T_anchor / (train T_fact), section 10 coefficients) + (measured seconds of one float32
    DEV evaluation on the A100) x evaluation_units + GPU time already used. Hours."""
    tr, acc = contract.training, contract.accounting
    a_runs = len(contract.arms.configs["A"]) + len([s for s in tr.training_seeds if s != tr.search_seed])
    other_runs = contract.arms.counts["total_training_runs"] - a_runs
    a_factor = 1.0 + ((acc.forward_flops_per_param_token + acc.train_flops_per_param_token) * anchor_tokens_per_step
                      / (acc.train_flops_per_param_token * fact_tokens_per_step))
    train_s = mean_step_seconds * tr.total_steps * (other_runs + a_runs * a_factor)
    units = evaluation_units(contract)
    eval_s = dev_evaluation_seconds * units
    return (train_s + eval_s + used_seconds) / 3600.0, {"train_seconds": train_s, "eval_seconds": eval_s,
                                                        "evaluation_units": units, "used_seconds": used_seconds,
                                                        "a_runs": a_runs, "other_runs": other_runs, "a_factor": a_factor}
