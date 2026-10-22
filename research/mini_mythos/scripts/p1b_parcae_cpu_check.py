#!/usr/bin/env python3
"""P1-B: native CPU correctness check of an unmodified, pinned Parcae checkout.

Imports the official implementation from a separate sandyresearch/parcae
checkout at PINNED_SHA; no Parcae source is copied, patched or monkeypatched
here. Builds the official ``parcae-small-140m`` config with only its sizes
shrunk, initialises every weight randomly (no checkpoint download) and runs
six checks on tiny synthetic CPU batches:

1. Prelude -> Recurrent Core -> Coda forward path
2. finite loss, logits and gradients
3. backward reaches the shared core and the injection parameters
4. state norms and state changes for 1, 2, 4 and 8 loops
5. the actual DiagonalInjection decay
6. Parcae's native no-grad / with-grad loop configuration

Only observational forward hooks, tensor grad hooks and Parcae's own methods
are used. Three AdamW steps on one fixed batch break the scaled-zero
symmetry for the "after steps" diagnostics; that is not a training run and
nothing here is a model-quality result.

Run inside the isolated P1-B venv (see p1b_setup_env.sh):

    python p1b_parcae_cpu_check.py --parcae-dir PARCAE --out-dir OUT \
        [--reference-dir PREVIOUS_OUT]

With --reference-dir the four JSON payloads are compared with a previous
run (``run_meta`` excluded) and the result is written into P1_B_RESULT.md.
"""
import argparse
import hashlib
import json
import math
import os
import platform
import subprocess
import sys
import time
import traceback
from importlib import metadata
from pathlib import Path

import torch

PINNED_SHA = "69284c13746e849104f738d6d1a347b1f457df76"
UPSTREAM_URL = "https://github.com/sandyresearch/parcae"
BASE_CONFIG = "parcae-small-140m"
# Sizes only. Every mechanism field keeps its official parcae-small-140m value.
TINY_OVERRIDES = dict(
    block_size=32,
    vocab_size=256,
    n_embd=64,
    num_attention_heads=4,
    num_key_value_heads=4,
    intermediate_size=256,
    recurrent_embedding_dimension=64,
    recurrent_intermediation_embedding_dimension=256,
    n_layers_in_prelude=1,
    n_layers_in_recurrent_block=2,
    n_layers_in_coda=1,
)
MECHANISM_FIELDS = (
    "block_class_name", "norm_class_name", "norm_eps", "mlp_class_name",
    "nonlin_name", "qk_norm", "logit_softcap", "prelude_norm", "bias",
    "tie_embeddings", "padding_multiple", "init_strategy", "init_orthogonal",
    "injection_type", "state_init", "mean_recurrence", "mean_backprop_depth",
    "sampling_scheme", "recurrent_iteration_method", "attn_impl",
    "use_fused_head", "activation_checkpoint_impl", "lockstep_n", "lockstep_k",
    "curriculum_target",
)
SEED = 20261022
BATCH, SEQ = 4, 16
LOOPS = (1, 2, 4, 8)
ADAMW_STEPS, ADAMW_LR = 3, 1e-3
SAMPLER_STEPS = 1000
NUM_THREADS = 1
OUTPUT_FILES = {
    "environment": "P1_B_ENVIRONMENT.json",
    "forward_backward": "P1_B_FORWARD_BACKWARD.json",
    "state": "P1_B_STATE_DIAGNOSTICS.json",
    "gradient": "P1_B_GRADIENT_DIAGNOSTICS.json",
}
RESULT_MD = "P1_B_RESULT.md"
# Committed evidence lives under docs/ because research/mini_mythos/results/ is git-ignored.
EVIDENCE_DIR = "research/mini_mythos/docs/p1b"
CHECK_TITLES = {
    "check_1_forward_path": "Prelude -> Recurrent Core -> Coda forward path",
    "check_2_finite": "Loss, logits and gradients are finite",
    "check_3_backprop_reach": "Backward reaches shared core and injection",
    "check_4_loop_states": "State norms / changes for 1, 2, 4, 8 loops",
    "check_5_injection_decay": "Actual DiagonalInjection decay",
    "check_6_no_grad_with_grad": "Native no-grad / with-grad loop configuration",
}


# ---------------------------------------------------------------- utilities

def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fnum(x):
    return float(x.detach().double().item()) if torch.is_tensor(x) else float(x)


def finite(t):
    return bool(torch.isfinite(t).all())


def item(name, ok, observed, criterion, required=True):
    return {"name": name, "required": required,
            "status": "PASS" if ok else "FAIL",
            "criterion": criterion, "observed": observed}


def verdict(items):
    req = [i for i in items if i["required"]]
    return "PASS" if req and all(i["status"] == "PASS" for i in req) else "FAIL"


def guarded(fn, *args):
    """Run one check; an exception is recorded as FAIL instead of aborting."""
    try:
        result = fn(*args)
        result["status"] = verdict(result["items"])
    except Exception:
        result = {"status": "FAIL", "items": [],
                  "error": traceback.format_exc(limit=8)}
    return result


def tok_norm(x):
    return x.float().norm(dim=-1)


def max_abs_diff(a, b):
    return fnum((a.float() - b.float()).abs().max())


def rel_diff(a, b):
    den = max(abs(a), abs(b), 1e-30)
    return abs(a - b) / den


# ---------------------------------------------------------- upstream source

def upstream_state(parcae_dir):
    status = git(parcae_dir, "status", "--porcelain", "--untracked-files=all",
                 "--ignored").splitlines()
    return {
        "head": git(parcae_dir, "rev-parse", "HEAD"),
        "tracked_changes": git(parcae_dir, "status", "--porcelain",
                               "--untracked-files=no").splitlines(),
        "untracked_files": [line[3:] for line in status if line.startswith("??")],
        "ignored_files": [line[3:] for line in status if line.startswith("!!")],
    }


def import_parcae(parcae_dir):
    state = upstream_state(parcae_dir)
    if state["head"] != PINNED_SHA:
        raise SystemExit(f"Parcae HEAD {state['head']} != pinned {PINNED_SHA}")
    if state["tracked_changes"]:
        raise SystemExit(f"Parcae checkout is modified: {state['tracked_changes']}")
    sys.dont_write_bytecode = True  # leave the upstream checkout untouched
    sys.path.insert(0, str(parcae_dir))
    import parcae_lm
    if not Path(parcae_lm.__file__).resolve().is_relative_to(parcae_dir):
        raise SystemExit(f"parcae_lm imported from {parcae_lm.__file__}, "
                         f"not from {parcae_dir}")
    return state


def imported_upstream_files(parcae_dir):
    """Every Parcae module actually loaded, checked blob-by-blob against HEAD."""
    files = sorted({
        Path(m.__file__).resolve().relative_to(parcae_dir).as_posix()
        for m in list(sys.modules.values())
        if getattr(m, "__file__", None)
        and Path(m.__file__).resolve().is_relative_to(parcae_dir)})
    worktree = git(parcae_dir, "hash-object", "--", *files).splitlines()
    rows = []
    for rel, blob in zip(files, worktree):
        head_blob = git(parcae_dir, "rev-parse", f"{PINNED_SHA}:{rel}")
        rows.append({"path": rel, "sha256": sha256_file(parcae_dir / rel),
                     "git_blob": blob, "matches_pinned_commit": blob == head_blob})
    return rows


# -------------------------------------------------------------- environment

def cpu_model():
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or "unknown"


def environment_info():
    import numpy
    import einops
    from parcae_lm.attention_backends import flash_attention
    return {
        "python": {"version": sys.version.split()[0],
                   "implementation": platform.python_implementation(),
                   "venv_isolated": sys.prefix != sys.base_prefix},
        "platform": {"system": platform.system(), "release": platform.release(),
                     "machine": platform.machine(), "cpu_model": cpu_model(),
                     "os_cpu_count": os.cpu_count()},
        "torch": {"version": torch.__version__,
                  "cuda_build": torch.version.cuda,
                  "cuda_available": torch.cuda.is_available(),
                  "mkldnn_available": torch.backends.mkldnn.is_available(),
                  "num_threads": torch.get_num_threads(),
                  "num_interop_threads": torch.get_num_interop_threads(),
                  "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
                  "default_dtype": str(torch.get_default_dtype())},
        "numpy": numpy.__version__,
        "einops": einops.__version__,
        "parcae_attention_backend": {
            "HAS_FA3": bool(flash_attention.HAS_FA3),
            "uses_fa3": bool(flash_attention._use_fa3()),
            "effective": "fa3" if flash_attention._use_fa3() else "torch SDPA fallback"},
        "installed_distributions": sorted(
            f"{d.metadata['Name']}=={d.version}" for d in metadata.distributions()),
    }


# -------------------------------------------------------------- model setup

def make_config(Config, **extra):
    return Config.from_name(BASE_CONFIG, **TINY_OVERRIDES, **extra)


def build_model(Config, **extra):
    cfg = make_config(Config, **extra)
    torch.manual_seed(SEED)
    model = cfg.construct_model()
    model.train()
    return cfg, model


def config_record(Config, cfg):
    official = Config.from_name(BASE_CONFIG)
    return {
        "base_config": BASE_CONFIG,
        "size_overrides": {k: {"official": getattr(official, k), "p1b": getattr(cfg, k)}
                           for k in TINY_OVERRIDES},
        "unchanged_mechanism_fields": {
            k: getattr(cfg, k) for k in MECHANISM_FIELDS if hasattr(cfg, k)},
        "mechanism_fields_equal_official": all(
            getattr(cfg, k) == getattr(official, k)
            for k in MECHANISM_FIELDS if hasattr(cfg, k)),
        "padded_vocab_size": cfg.padded_vocab_size,
        "init": repr(cfg.init),
        "recurrent_block_init": repr(cfg.recurrent_block_config.init),
        "logit_scale": cfg.init.logit_scale,
        "embedding_scale": cfg.init.embedding_scale,
    }


def make_batch(cfg):
    g = torch.Generator().manual_seed(SEED + 1)
    tokens = torch.randint(0, cfg.vocab_size, (BATCH, SEQ + 1), generator=g)
    return tokens[:, :-1].contiguous(), tokens[:, 1:].contiguous()


def forward(model, batch, pair=None, state_seed=SEED + 2, backward=True):
    ids, labels = batch
    model.zero_grad(set_to_none=True)
    torch.manual_seed(state_seed)  # Parcae draws the initial state x0 from the global RNG
    kwargs = {} if pair is None else {"num_steps_pair": torch.tensor(list(pair))}
    out = model(ids, labels=labels, return_logits=True, **kwargs)
    if backward:
        out["loss"].backward()
    return out


def group_of(name):
    parts = name.split(".")
    if parts[0] == "transformer":
        return parts[1]
    if parts[0] == "value_embeds":
        return f"value_embeds.{parts[1]}"
    return parts[0]


def param_inventory(model):
    rows, groups = [], {}
    for name, p in model.named_parameters():
        g = group_of(name)
        groups[g] = groups.get(g, 0) + p.numel()
        rows.append({"name": name, "group": g, "shape": list(p.shape),
                     "init_mean": fnum(p.mean()), "init_std": fnum(p.std()) if p.numel() > 1 else 0.0,
                     "init_all_zero": bool((p == 0).all())})
    return {"total_parameters": sum(groups.values()), "parameters_by_group": groups,
            "tied_lm_head_to_wte": model.lm_head.weight is model.transformer.wte.weight,
            "parameters": rows}


def tracked_names(cfg):
    names = ["transformer.wte"]
    names += [f"transformer.prelude.{i}" for i in range(cfg.n_layers_in_prelude)]
    if cfg.prelude_norm:
        names.append("transformer.ln_prelude")
    names.append("transformer.adapter")
    names += [f"transformer.core_block.{j}" for j in range(cfg.n_layers_in_recurrent_block)]
    names.append("transformer.C")
    names += [f"transformer.coda.{i}" for i in range(cfg.n_layers_in_coda)]
    return names + ["transformer.ln_f", "lm_head"]


def expected_calls(cfg, total_loops):
    names = tracked_names(cfg)
    a = names.index("transformer.adapter")
    c = names.index("transformer.C")
    return names[:a] + names[a:c] * total_loops + names[c:]


class Recorder:
    """Observational hooks: record calls and states, never change outputs."""

    def __init__(self, model, cfg, keep_states=False, grad_hooks=False):
        self.calls, self.adapter_in, self.adapter_out, self.core_out = [], [], [], []
        self.c_in, self.iter_grad, self.module_ids = None, {}, {}
        self.keep_states, self.grad_hooks = keep_states, grad_hooks
        self.last_core = f"transformer.core_block.{cfg.n_layers_in_recurrent_block - 1}"
        modules = dict(model.named_modules())
        self.handles = [modules[n].register_forward_hook(self._hook(n))
                        for n in tracked_names(cfg)]

    def _hook(self, name):
        def hook(module, args, output):
            self.calls.append({"module": name, "grad_enabled": torch.is_grad_enabled(),
                               "output_shape": list(output.shape)})
            self.module_ids.setdefault(name, set()).add(id(module))
            if name == "transformer.adapter":
                idx = len(self.adapter_out)
                if self.keep_states:
                    self.adapter_in.append(args[0].detach().clone())
                self.adapter_out.append(output.detach().clone() if self.keep_states else None)
                if self.grad_hooks and output.requires_grad:
                    output.register_hook(
                        lambda g, i=idx: self.iter_grad.__setitem__(i, fnum(g.norm())))
            elif name == self.last_core and self.keep_states:
                self.core_out.append(output.detach().clone())
            elif name == "transformer.C" and self.keep_states:
                self.c_in = args[0].detach().clone()
        return hook

    def remove(self):
        for h in self.handles:
            h.remove()


def grad_rows(model):
    rows = []
    for name, p in model.named_parameters():
        row = {"name": name, "group": group_of(name)}
        if p.grad is None:
            row.update(grad=None, finite=True, nonzero=0)
        else:
            g = p.grad
            row.update(grad_norm=fnum(g.norm()), grad_max_abs=fnum(g.abs().max()),
                       finite=finite(g), nonzero=int((g != 0).sum()), numel=g.numel())
        rows.append(row)
    return rows


def group_grad_norms(rows):
    out = {}
    for r in rows:
        out[r["group"]] = out.get(r["group"], 0.0) + (r.get("grad_norm") or 0.0) ** 2
    return {k: math.sqrt(v) for k, v in out.items()}


def is_core(r):
    return r["group"] == "core_block"


def is_adapter(r):
    return r["group"] == "adapter"


def is_output_proj(r):
    return r["name"].endswith("attn.c_proj.weight") or r["name"].endswith("mlp.proj.weight")


def pair_default(cfg):
    s = cfg.mean_backprop_depth
    return (max(cfg.mean_recurrence - s, 0), s)


def find_mixed_step(model, cfg):
    """First model.step whose native per-sequence sample gates both loop phases."""
    for step in range(10_000):
        model.step = step
        n, k = model._sample_batch_depths(BATCH)
        if n.max() > 0 and k.max() > 0 and (n < n.max()).any() and (k < k.max()).any():
            model.step = 0
            return step, n.tolist(), k.tolist()
    model.step = 0
    raise RuntimeError("no step with mixed per-sample depths found")


def adamw_steps(model, batch, cfg):
    opt = torch.optim.AdamW(model.parameters(), lr=ADAMW_LR, weight_decay=0.0)
    losses = []
    for i in range(ADAMW_STEPS):
        out = forward(model, batch, pair_default(cfg), state_seed=SEED + 100 + i)
        losses.append(fnum(out["loss"]))
        opt.step()
    model.zero_grad(set_to_none=True)
    return {"optimizer": "torch.optim.AdamW", "lr": ADAMW_LR, "weight_decay": 0.0,
            "steps": ADAMW_STEPS, "num_steps_pair": list(pair_default(cfg)),
            "same_fixed_batch_each_step": True, "losses_before_each_step": losses,
            "purpose": "break scaled-zero symmetry for diagnostics only; not a training run"}


# ------------------------------------------------------------ check 1

def check_forward_path(model, cfg, batch):
    items = []
    pair = pair_default(cfg)
    total = sum(pair)
    model.train()
    rec = Recorder(model, cfg)
    out = forward(model, batch, pair, backward=False)
    rec.remove()
    observed = [c["module"] for c in rec.calls]
    expected = expected_calls(cfg, total)
    items.append(item(
        f"module call order, train mode, num_steps_pair={list(pair)}",
        observed == expected, {"observed": observed},
        f"exact match: wte, prelude, ln_prelude, (adapter, core_block.*) x {total}, C, coda, ln_f, lm_head"))

    hidden, rec_dim, vocab = cfg.n_embd, cfg.recurrent_embedding_dimension, cfg.padded_vocab_size
    want = {"transformer.adapter": rec_dim, "lm_head": vocab, "transformer.C": hidden}
    shapes = {c["module"]: c["output_shape"] for c in rec.calls}
    shape_ok = all(s == [BATCH, SEQ, want.get(m, rec_dim if "core_block" in m else hidden)]
                   for m, s in shapes.items())
    items.append(item("module output shapes", shape_ok, shapes,
                      f"[B, T, d]: d={hidden} outside the core, {rec_dim} for adapter/core, {vocab} for lm_head"))

    core = [n for n in tracked_names(cfg) if "core_block" in n]
    per_layer_calls = {n: observed.count(n) for n in core + ["transformer.adapter"]}
    shared = all(len(rec.module_ids[n]) == 1 for n in core + ["transformer.adapter"])
    items.append(item(
        "core layers and injection are one shared set of modules reused each loop",
        shared and all(v == total for v in per_layer_calls.values())
        and len(model.transformer.core_block) == cfg.n_layers_in_recurrent_block,
        {"calls_per_module": per_layer_calls, "distinct_module_objects_per_name": 1 if shared else "more than 1",
         "n_core_layers": len(model.transformer.core_block)},
        f"each core layer and the adapter called exactly {total} times through one module object"))

    logits = out["logits"]
    items.append(item("logits and loss shape", list(logits.shape) == [BATCH, SEQ, vocab]
                      and out["loss"].dim() == 0,
                      {"logits_shape": list(logits.shape), "loss": fnum(out["loss"])},
                      f"logits [{BATCH}, {SEQ}, {vocab}], scalar loss"))

    model.eval()
    eval_pair = (cfg.mean_recurrence, 0)
    rec = Recorder(model, cfg)
    with torch.no_grad():
        out = forward(model, batch, eval_pair, backward=False)
    rec.remove()
    model.train()
    observed = [c["module"] for c in rec.calls]
    items.append(item(
        f"eval mode with upstream eval pair num_steps_pair={list(eval_pair)}",
        observed == expected_calls(cfg, sum(eval_pair)) and finite(out["loss"]),
        {"adapter_calls": observed.count("transformer.adapter"), "loss": fnum(out["loss"])},
        f"same path with {sum(eval_pair)} loops (pair used by upstream receval/scripts/train.py eval)"))
    return {"items": items}


# ------------------------------------------------------------ check 2

def finite_record(model, out):
    rows = grad_rows(model)
    none = [r["name"] for r in rows if "grad_norm" not in r]
    bad = [r["name"] for r in rows if not r["finite"]]
    return {"loss": fnum(out["loss"]), "loss_finite": finite(out["loss"]),
            "log_ppl_finite": finite(out["log_ppl"]),
            "logits_finite": finite(out["logits"]),
            "logits_abs_max": fnum(out["logits"].abs().max()),
            "params_with_grad": len(rows) - len(none), "params_total": len(rows),
            "params_grad_none": none, "params_grad_nonfinite": bad}


def check_finite(model, cfg, batch, phase, mixed_step):
    items = []
    pair = pair_default(cfg)
    rec = finite_record(model, forward(model, batch, pair))
    ok = rec["loss_finite"] and rec["logits_finite"] and rec["log_ppl_finite"] \
        and not rec["params_grad_none"] and not rec["params_grad_nonfinite"]
    items.append(item(f"{phase}: fixed num_steps_pair={list(pair)}", ok, rec,
                      "finite loss/log_ppl/logits; every parameter has a finite gradient"))

    model.step = mixed_step
    rec = finite_record(model, forward(model, batch, None))
    model.step = 0
    ok = rec["loss_finite"] and rec["logits_finite"] and not rec["params_grad_nonfinite"]
    items.append(item(f"{phase}: native sampled depths (train, model.step={mixed_step})", ok, rec,
                      "finite loss/logits; no non-finite gradient"))

    for r in (16, 32):
        rec = finite_record(model, forward(model, batch, (r - cfg.mean_backprop_depth, cfg.mean_backprop_depth)))
        ok = rec["loss_finite"] and rec["logits_finite"] and not rec["params_grad_nonfinite"]
        items.append(item(f"{phase}: deeper recurrence {r} loops (supplementary)", ok, rec,
                          "finite loss/logits and gradients", required=False))
    return items


# ------------------------------------------------------------ check 3

def check_backprop_reach(model, cfg, batch, phase):
    pair = pair_default(cfg)
    rec = Recorder(model, cfg, grad_hooks=True)
    forward(model, batch, pair)
    rec.remove()
    rows = grad_rows(model)
    n, k = pair
    iter_grad = {str(i): rec.iter_grad[i] for i in sorted(rec.iter_grad)}
    items = []

    adapter = [r for r in rows if is_adapter(r)]
    items.append(item(
        f"{phase}: injection parameters A_log, dt_bias, B receive non-zero finite gradients",
        len(adapter) == 3 and all(r["nonzero"] > 0 and r["finite"] for r in adapter),
        {r["name"]: r.get("grad_norm") for r in adapter}, "3 parameters, each grad norm > 0 and finite"))

    core = [r for r in rows if is_core(r)]
    if phase == "init":
        target = [r for r in core if is_output_proj(r)]
        crit = "every core attn.c_proj / mlp.proj weight has a non-zero finite gradient " \
               "(other core weights sit behind these zero-initialised projections)"
    else:
        target = core
        crit = "every shared-core parameter has a non-zero finite gradient"
    items.append(item(f"{phase}: gradients reach the shared recurrent core",
                      bool(target) and all(r["nonzero"] > 0 and r["finite"] for r in target),
                      {r["name"]: r.get("grad_norm") for r in target}, crit))

    with_grad = list(range(n, n + k))
    ok = sorted(rec.iter_grad) == with_grad and all(
        v > 0 and math.isfinite(v) for v in rec.iter_grad.values())
    items.append(item(f"{phase}: gradient arrives at every with-grad loop iteration",
                      ok, {"iteration_to_state_grad_norm": iter_grad},
                      f"grad hooks fire for iterations {with_grad} only, each norm > 0 and finite"))

    if phase == "after_adamw_steps":
        none_or_bad = [r["name"] for r in rows if "grad_norm" not in r or not r["finite"]]
        items.append(item(f"{phase}: every parameter has a finite gradient", not none_or_bad,
                          {"missing_or_nonfinite": none_or_bad}, "no missing or non-finite gradient"))

    zero = [r["name"] for r in rows if r["nonzero"] == 0]
    items.append(item(f"{phase}: parameters with all-zero or missing gradient (informational)",
                      True, zero,
                      "at init scaled-zero sets attn.c_proj/mlp.proj to 0, so weights upstream of "
                      "them get exactly zero gradient", required=False))
    detail = {"num_steps_pair": list(pair), "parameters": rows,
              "group_grad_norms": group_grad_norms(rows),
              "iteration_to_state_grad_norm": iter_grad}
    return items, detail


# ------------------------------------------------------------ check 4

def loop_trajectories(model, cfg, batch):
    model.monitoring = True
    runs, states_by_r = [], {}
    try:
        for r in LOOPS:
            rec = Recorder(model, cfg, keep_states=True)
            out = forward(model, batch, (0, r))
            rec.remove()
            native = {k: fnum(v) for k, v in model.latest_metrics.items()}
            rows = grad_rows(model)
            states = [rec.adapter_in[0]] + rec.core_out
            states_by_r[r] = states
            traj = []
            for j, s in enumerate(states):
                row = {"iteration": j, "state_norm_mean": fnum(tok_norm(s).mean())}
                if j:
                    d = tok_norm(s - states[j - 1])
                    row["delta_norm_mean"] = fnum(d.mean())
                    row["rel_delta_mean"] = fnum((d / tok_norm(s)).mean())
                if j > 1:
                    row["delta_ratio_to_previous"] = row["delta_norm_mean"] / traj[-1]["delta_norm_mean"]
                traj.append(row)
            threading = max([max_abs_diff(rec.adapter_in[j], rec.core_out[j - 1])
                             for j in range(1, r)] or [0.0])
            core_identity = [max_abs_diff(rec.core_out[j], rec.adapter_out[j]) for j in range(r)]
            runs.append({
                "loops": r, "num_steps_pair": [0, r], "loss": fnum(out["loss"]),
                "all_finite": finite(out["loss"]) and all(finite(s) for s in states),
                "trajectory": traj,
                "final_state_norm_mean": traj[-1]["state_norm_mean"],
                "final_delta_norm_mean": traj[-1]["delta_norm_mean"],
                "native_monitoring": native,
                "native_vs_hook_rel_diff": {
                    "recurrent_state_norm": rel_diff(native["recurrent_state_norm"], traj[-1]["state_norm_mean"]),
                    "recurrent_residual": rel_diff(native["recurrent_residual"], traj[-1]["delta_norm_mean"]),
                    "rel_residual": rel_diff(native["rel_residual"], traj[-1]["rel_delta_mean"])},
                "C_input_vs_final_state_max_abs_diff": max_abs_diff(rec.c_in, states[-1]),
                "state_threading_max_abs_diff": threading,
                "core_output_minus_injection_max_abs_diff": core_identity,
                "grad_norms": {"adapter": group_grad_norms(rows).get("adapter"),
                               "core_block": group_grad_norms(rows).get("core_block")},
            })
    finally:
        model.monitoring = False
    longest = states_by_r[max(LOOPS)]
    prefix = {str(r): max(max_abs_diff(s, longest[j]) for j, s in enumerate(states_by_r[r]))
              for r in LOOPS}
    return runs, prefix


def check_loop_states(model, cfg, batch, phase, decay):
    runs, prefix = loop_trajectories(model, cfg, batch)
    items = [
        item(f"{phase}: loops {list(LOOPS)} run with finite states and loss",
             all(r["all_finite"] for r in runs),
             {str(r["loops"]): {"loss": r["loss"], "final_state_norm_mean": r["final_state_norm_mean"],
                                "final_delta_norm_mean": r["final_delta_norm_mean"]} for r in runs},
             "all states and losses finite"),
        item(f"{phase}: native monitoring agrees with hook-measured states",
             all(v <= 1e-5 for r in runs for v in r["native_vs_hook_rel_diff"].values()),
             {str(r["loops"]): r["native_vs_hook_rel_diff"] for r in runs},
             "relative difference <= 1e-5 for recurrent_state_norm, recurrent_residual, rel_residual"),
        item(f"{phase}: state threading (iteration j input = iteration j-1 output, C input = final state)",
             all(r["state_threading_max_abs_diff"] == 0.0 and r["C_input_vs_final_state_max_abs_diff"] == 0.0
                 for r in runs),
             {str(r["loops"]): [r["state_threading_max_abs_diff"], r["C_input_vs_final_state_max_abs_diff"]]
              for r in runs}, "max abs diff exactly 0"),
        item(f"{phase}: shorter runs are exact prefixes of the {max(LOOPS)}-loop trajectory",
             all(v == 0.0 for v in prefix.values()), prefix,
             "same x0 seed: states of iteration j identical across loop counts (max abs diff 0)"),
    ]
    if phase == "init":
        r8 = runs[-1]
        ident = max(r8["core_output_minus_injection_max_abs_diff"])
        ratios = [row["delta_ratio_to_previous"] for row in r8["trajectory"] if "delta_ratio_to_previous" in row]
        items.append(item(
            "init: scaled-zero core is an exact identity, so each state change shrinks by the injection decay",
            ident == 0.0 and all(abs(x - decay) <= 1e-5 for x in ratios),
            {"core_output_minus_injection_max_abs_diff": ident,
             "delta_ratio_to_previous": ratios, "injection_decay": decay},
             "core output == injection output exactly; |delta ratio - decay| <= 1e-5"))
    return items, {"runs": runs, "prefix_max_abs_diff_vs_longest": prefix}


# ------------------------------------------------------------ check 5

def decay_report(adapter):
    D, Din = adapter.A_log.numel(), adapter.B.shape[1]
    with torch.no_grad():
        probe = adapter(torch.ones(1, 1, D), torch.zeros(1, 1, Din)).flatten()  # native forward: decay
        dt = torch.nn.functional.softplus(adapter.dt_bias)
        formula = torch.exp(-dt * torch.exp(adapter.A_log))  # docstring formula, cross-check only
        eye = torch.eye(D, Din) if D == Din else None
    return {
        "state_dim": D, "input_dim": Din,
        "native_get_spectral_norm": adapter.get_spectral_norm(),
        "native_get_contraction_factor": adapter.get_contraction_factor(),
        "probe_decay": {"min": fnum(probe.min()), "max": fnum(probe.max()),
                        "mean": fnum(probe.mean()), "std": fnum(probe.std())},
        "probe_vs_formula_max_abs_diff": max_abs_diff(probe, formula),
        "dt": {"min": fnum(dt.min()), "max": fnum(dt.max()), "mean": fnum(dt.mean())},
        "A_log": {"min": fnum(adapter.A_log.min()), "max": fnum(adapter.A_log.max())},
        "dt_bias": {"min": fnum(adapter.dt_bias.min()), "max": fnum(adapter.dt_bias.max())},
        "B_minus_identity_max_abs": max_abs_diff(adapter.B, eye) if eye is not None else None,
        "B_spectral_norm": fnum(torch.linalg.matrix_norm(adapter.B.detach(), ord=2)),
        "_probe": probe,
    }


def decay_items(rep, phase, target=None):
    p = rep["probe_decay"]
    items = [
        item(f"{phase}: every channel decays strictly inside (0, 1)", 0.0 < p["min"] and p["max"] < 1.0,
             p, "0 < decay_i < 1 for all channels"),
        item(f"{phase}: native get_spectral_norm / get_contraction_factor match the probed decay",
             abs(rep["native_get_spectral_norm"] - p["max"]) <= 1e-7
             and abs(rep["native_get_contraction_factor"] - p["mean"]) <= 1e-6
             and rep["probe_vs_formula_max_abs_diff"] <= 1e-7,
             {"spectral_norm": rep["native_get_spectral_norm"],
              "contraction_factor": rep["native_get_contraction_factor"],
              "probe_vs_formula_max_abs_diff": rep["probe_vs_formula_max_abs_diff"]},
             "spectral = max(decay), contraction = mean(decay), forward probe = exp(-softplus(dt_bias)*exp(A_log))"),
    ]
    if target is not None:
        items.append(item(
            f"{phase}: decay equals the Parcae default ssm_decay sqrt(1/5)",
            abs(p["min"] - target) <= 1e-6 and abs(p["max"] - target) <= 1e-6
            and rep["A_log"]["min"] == 0.0 and rep["A_log"]["max"] == 0.0
            and (rep["B_minus_identity_max_abs"] in (None, 0.0)),
            {"target": target, "min": p["min"], "max": p["max"], "A_log": rep["A_log"],
             "dt_mean": rep["dt"]["mean"], "B_minus_identity_max_abs": rep["B_minus_identity_max_abs"]},
            "|decay - 0.4472136| <= 1e-6 on every channel, A_log = 0, B = I"))
    return items


def check_injection_decay(Config, phase_reports):
    target = math.sqrt(1.0 / 5.0)
    items = []
    for phase, rep in phase_reports.items():
        items += decay_items(rep, phase, target if phase == "init" else None)
    from parcae_lm.modules.injection import DiagonalInjection
    official = Config.from_name(BASE_CONFIG)
    torch.manual_seed(SEED)
    rep140 = decay_report(DiagonalInjection(official))
    items += decay_items(rep140, f"official {BASE_CONFIG} config, DiagonalInjection only", target)
    init_probe = phase_reports["init"]["_probe"]
    if "after_adamw_steps" in phase_reports:
        moved = max_abs_diff(phase_reports["after_adamw_steps"]["_probe"], init_probe)
        items.append(item("after_adamw_steps: decay parameters are trainable (moved from init)",
                          moved > 0.0, {"max_abs_change": moved}, "max |decay_after - decay_init| > 0",
                          required=False))
    reports = {k: {kk: vv for kk, vv in v.items() if kk != "_probe"} for k, v in phase_reports.items()}
    reports[f"official_{BASE_CONFIG}_injection"] = {k: v for k, v in rep140.items() if k != "_probe"}
    return items, reports


# ------------------------------------------------------------ check 6

def run_pair(model, cfg, batch, pair):
    rec = Recorder(model, cfg, grad_hooks=True)
    out = forward(model, batch, pair)
    rec.remove()
    loop_flags = [c["grad_enabled"] for c in rec.calls if c["module"] == "transformer.adapter"]
    outer_flags = [c["grad_enabled"] for c in rec.calls if "core_block" not in c["module"]
                   and c["module"] != "transformer.adapter"]
    grads = {name: p.grad.detach().clone() if p.grad is not None else None
             for name, p in model.named_parameters()}
    return {"out": out, "loop_flags": loop_flags, "outer_flags": outer_flags,
            "iter_grad": dict(rec.iter_grad), "grads": grads, "rows": grad_rows(model)}


def flat_group_grad(grads, group):
    parts = [g.flatten() for n, g in grads.items() if group_of(n) == group and g is not None]
    return torch.cat(parts) if parts else torch.zeros(0)


def check_pairs(model, cfg, batch, phase):
    pairs = [(8, 0), (6, 2), (4, 4), (2, 6), (0, 8)]
    res = {p: run_pair(model, cfg, batch, p) for p in pairs}
    ref = res[(8, 0)]["out"]
    invariance = {str(list(p)): {"loss": fnum(r["out"]["loss"]),
                                 "loss_abs_diff_vs_8_0": abs(fnum(r["out"]["loss"]) - fnum(ref["loss"])),
                                 "logits_max_abs_diff_vs_8_0": max_abs_diff(r["out"]["logits"], ref["logits"])}
                  for p, r in res.items()}
    items = [item(f"{phase}: forward is identical whatever the no-grad / with-grad split",
                  all(v["loss_abs_diff_vs_8_0"] <= 1e-6 and v["logits_max_abs_diff_vs_8_0"] <= 1e-6
                      for v in invariance.values()), invariance,
                  "same x0 seed and 8 loops: loss and logits differ by <= 1e-6 across splits")]

    flags = {str(list(p)): r["loop_flags"] for p, r in res.items()}
    items.append(item(
        f"{phase}: first n loops run under torch.no_grad, last k with grad enabled",
        all(r["loop_flags"] == [False] * p[0] + [True] * p[1] and all(r["outer_flags"])
            for p, r in res.items()),
        flags, "adapter grad_enabled flags = [False]*n + [True]*k; prelude/coda/head always grad-enabled"))

    hooks = {str(list(p)): sorted(r["iter_grad"]) for p, r in res.items()}
    items.append(item(
        f"{phase}: backward reaches exactly the with-grad iterations",
        all(sorted(r["iter_grad"]) == list(range(p[0], p[0] + p[1])) for p, r in res.items()),
        hooks, "state grad hooks fire for iterations n..n+k-1 only"))

    a, b = res[(4, 4)]["iter_grad"], res[(0, 8)]["iter_grad"]
    common = {str(i): rel_diff(a[i], b[i]) for i in range(4, 8)}
    items.append(item(
        f"{phase}: truncation is an exact stop-gradient at loop n",
        all(v <= 1e-6 for v in common.values()), {"iterations_4_to_7_rel_diff_(4,4)_vs_(0,8)": common},
        "state gradients on the shared with-grad iterations agree within 1e-6"))

    pre_c = {"prelude", "ln_prelude", "adapter", "core_block"} | {
        f"value_embeds.{i}" for i in range(cfg.n_layers_in_prelude + cfg.n_layers_in_recurrent_block)}
    rows80 = res[(8, 0)]["rows"]
    leaked = [r["name"] for r in rows80 if r["group"] in pre_c and r["nonzero"] > 0]
    post = {g: v for g, v in group_grad_norms(rows80).items() if g in ("C", "coda", "ln_f", "wte")}
    items.append(item(
        f"{phase}: (8, 0) all-no-grad recurrence leaves prelude/injection/core without gradient",
        not leaked and all(v > 0 for v in post.values()) and len(post) == 4,
        {"pre_C_params_with_nonzero_grad": leaked, "post_C_group_grad_norms": post},
        "no gradient before C; C, coda, ln_f and tied wte/lm_head still get gradients"))

    reach = {}
    for p in [(4, 4), (0, 8)]:
        gn = group_grad_norms(res[p]["rows"])
        reach[str(list(p))] = {g: gn.get(g) for g in ("prelude", "adapter", "core_block")}
    items.append(item(f"{phase}: with k > 0 gradients reach prelude, injection and core",
                      all(v and v > 0 for d in reach.values() for v in d.values()), reach,
                      "group grad norms > 0 for (4, 4) and (0, 8)"))

    diffs = {}
    for g in ("adapter", "core_block"):
        x, y = flat_group_grad(res[(4, 4)]["grads"], g), flat_group_grad(res[(0, 8)]["grads"], g)
        diffs[g] = fnum((x - y).norm() / y.norm().clamp_min(1e-30))
    items.append(item(f"{phase}: backprop depth k changes the gradient ((4, 4) vs (0, 8))",
                      all(v > 1e-6 for v in diffs.values()), diffs,
                      "relative gradient difference > 1e-6 for adapter and core"))
    return items


def sampler_stats(model, cfg):
    s = cfg.mean_backprop_depth
    t = max(cfg.mean_recurrence - s, 0)
    model.train()
    seq = {"n": [], "k": [], "total": [], "violations": 0, "nondeterministic": 0}
    bat = {"n": [], "k": [], "total": [], "violations": 0, "nondeterministic": 0}
    for step in range(SAMPLER_STEPS):
        model.step = step
        n, k = model._sample_batch_depths(BATCH)
        n2, k2 = model._sample_batch_depths(BATCH)
        seq["nondeterministic"] += int(not (torch.equal(n, n2) and torch.equal(k, k2)))
        tot = n + k
        seq["violations"] += int(((k > s) | (n < 0) | (tot < 1) | (k != tot.clamp(max=s))).sum())
        seq["n"] += n.tolist(); seq["k"] += k.tolist(); seq["total"] += tot.tolist()
        n, k = model.randomized_iteration_sampler()
        n2, k2 = model.randomized_iteration_sampler()
        bat["nondeterministic"] += int(not (torch.equal(n, n2) and torch.equal(k, k2)))
        bat["violations"] += int(((n < 1) | (k != n.clamp(max=s))).sum())
        bat["n"] += n.tolist(); bat["k"] += k.tolist(); bat["total"] += (n + k).tolist()
    model.step = 0

    def summary(d):
        hist = {}
        for v in d["total"]:
            hist[str(v)] = hist.get(str(v), 0) + 1
        mean = lambda xs: sum(xs) / len(xs)
        return {"samples": len(d["total"]), "mean_no_grad_n": mean(d["n"]), "mean_with_grad_k": mean(d["k"]),
                "mean_total": mean(d["total"]), "max_k": max(d["k"]), "min_total": min(d["total"]),
                "max_total": max(d["total"]), "rule_violations": d["violations"],
                "nondeterministic_resamples": d["nondeterministic"],
                "total_histogram": dict(sorted(hist.items(), key=lambda kv: int(kv[0])))}

    model.eval()
    eval_pair = [int(x) for x in model.randomized_iteration_sampler()]
    model.train()
    return {"t": t, "s": s, "per_sequence": summary(seq), "per_batch": summary(bat),
            "eval_mode_randomized_iteration_sampler": eval_pair}


def native_gating(model, cfg, batch, step):
    model.train()
    model.step = step
    n_b, k_b = model._sample_batch_depths(BATCH)
    rec = Recorder(model, cfg, keep_states=True)
    out = forward(model, batch, None)
    rec.remove()
    native = {k: fnum(v) for k, v in model.latest_metrics.items()} if model.monitoring else None
    model.step = 0
    n_max, k_max = int(n_b.max()), int(k_b.max())
    states = rec.adapter_in + [rec.c_in]
    mismatches, table = 0, []
    for j in range(len(rec.adapter_in)):
        changed = (states[j + 1] != states[j]).flatten(1).any(1)
        expect = (j < n_b) if j < n_max else ((j - n_max) < k_b)
        mismatches += int((changed != expect).sum())
        table.append({"loop_call": j, "phase": "no_grad" if j < n_max else "with_grad",
                      "samples_updated": changed.tolist(), "expected": expect.tolist()})
    flags = [c["grad_enabled"] for c in rec.calls if c["module"] == "transformer.adapter"]
    rows = grad_rows(model)
    return {
        "model_step": step, "per_sample_n": n_b.tolist(), "per_sample_k": k_b.tolist(),
        "loop_calls": len(rec.adapter_in), "expected_loop_calls": n_max + k_max,
        "grad_flags": flags, "gating_mismatches": mismatches, "gating_table": table,
        "loss": fnum(out["loss"]), "loss_finite": finite(out["loss"]),
        "grads_finite": all(r["finite"] for r in rows),
        "core_grad_norm": group_grad_norms(rows).get("core_block"),
        "native_monitoring": native,
    }


def check_native_config(model, cfg, batch, mixed_step):
    items = []
    stats = sampler_stats(model, cfg)
    sq, bt = stats["per_sequence"], stats["per_batch"]
    items.append(item(
        "native config of parcae-small-140m is kept",
        (cfg.mean_recurrence, cfg.mean_backprop_depth, cfg.sampling_scheme, cfg.recurrent_iteration_method)
        == (8, 4, "poisson-truncated-full", "per-sequence"),
        {"mean_recurrence": cfg.mean_recurrence, "mean_backprop_depth": cfg.mean_backprop_depth,
         "sampling_scheme": cfg.sampling_scheme, "recurrent_iteration_method": cfg.recurrent_iteration_method,
         "activation_checkpoint_impl": cfg.activation_checkpoint_impl},
        "mean_recurrence 8, mean_backprop_depth 4, poisson-truncated-full, per-sequence"))
    items.append(item(
        "per-sequence sampler (_sample_batch_depths): total ~ clamp(Poisson(t+s), 1), k = min(total, s), n = total - k",
        sq["rule_violations"] == 0 and sq["nondeterministic_resamples"] == 0 and sq["max_k"] <= stats["s"]
        and abs(sq["mean_total"] - (stats["t"] + stats["s"])) <= 0.3,
        {k: v for k, v in sq.items()},
        f"0 rule violations over {SAMPLER_STEPS} steps x batch {BATCH}; same step resamples identically; "
        f"|mean total - {stats['t'] + stats['s']}| <= 0.3"))
    items.append(item(
        "per-batch sampler (randomized_iteration_sampler): n = clamp(Poisson(t+s), 1), k = min(n, s)",
        bt["rule_violations"] == 0 and bt["nondeterministic_resamples"] == 0
        and abs(bt["mean_no_grad_n"] - (stats["t"] + stats["s"])) <= 0.5,
        {k: v for k, v in bt.items()},
        "0 rule violations; deterministic per step; |mean n - 8| <= 0.5 (not the 140M mode)", required=False))
    items.append(item("eval mode randomized_iteration_sampler returns (mean_recurrence, 0)",
                      stats["eval_mode_randomized_iteration_sampler"] == [cfg.mean_recurrence, 0],
                      stats["eval_mode_randomized_iteration_sampler"], "[8, 0]", required=False))

    model.monitoring = True
    try:
        gate = native_gating(model, cfg, batch, mixed_step)
    finally:
        model.monitoring = False
    n_max, k_max = max(gate["per_sample_n"]), max(gate["per_sample_k"])
    items.append(item(
        "native sampled train forward (no num_steps_pair): per-sample torch.where gating matches the sampled (n, k)",
        gate["gating_mismatches"] == 0 and gate["loop_calls"] == gate["expected_loop_calls"]
        and gate["grad_flags"] == [False] * n_max + [True] * k_max
        and gate["loss_finite"] and gate["grads_finite"] and (gate["core_grad_norm"] or 0) > 0,
        {k: v for k, v in gate.items() if k != "gating_table"},
        "0 gating mismatches; max(n) no-grad calls then max(k) grad calls; finite loss/grads; core grad > 0"))

    model.eval()
    model.step = mixed_step
    rec = Recorder(model, cfg)
    with torch.no_grad():
        forward(model, batch, None, backward=False)
    rec.remove()
    model.step = 0
    model.train()
    eval_calls = sum(c["module"] == "transformer.adapter" for c in rec.calls)
    items.append(item(
        "observation: eval mode without num_steps_pair still samples per-sequence depths",
        True, {"loop_calls": eval_calls, "model_step": mixed_step,
               "note": "upstream eval passes num_steps_pair=[mean_recurrence, 0] explicitly "
                       "(receval/tasks/core_eval.py, scripts/train.py)"},
        "informational only", required=False))
    return items, stats, gate


def check_checkpointing_equivalence(Config, model, cfg, batch):
    torch.manual_seed(SEED)
    ckpt = make_config(Config).construct_model(gradient_checkpointing=True)
    ckpt.load_state_dict(model.state_dict())
    ckpt.train()
    pair = pair_default(cfg)
    a = forward(model, batch, pair)
    ga = {n: p.grad.clone() for n, p in model.named_parameters()}
    b = forward(ckpt, batch, pair)
    diff = max(max_abs_diff(ga[n], p.grad) for n, p in ckpt.named_parameters())
    return item(
        f"supplementary: gradient_checkpointing ({cfg.activation_checkpoint_impl}) gives the same loss and grads",
        abs(fnum(a["loss"]) - fnum(b["loss"])) <= 1e-6 and diff <= 1e-5,
        {"loss_plain": fnum(a["loss"]), "loss_checkpointed": fnum(b["loss"]), "grad_max_abs_diff": diff},
        "loss diff <= 1e-6, grad max abs diff <= 1e-5", required=False)


def check_per_batch_forward(Config, model, cfg, batch):
    pcfg, pb = build_model(Config, recurrent_iteration_method="per-batch")
    pb.load_state_dict(model.state_dict())
    pb.step = 3
    n, k = (int(x) for x in pb.randomized_iteration_sampler())
    rec = Recorder(pb, pcfg)
    out = forward(pb, batch, None)
    rec.remove()
    flags = [c["grad_enabled"] for c in rec.calls if c["module"] == "transformer.adapter"]
    return item(
        "supplementary: per-batch mode native forward runs n no-grad then k grad loops",
        flags == [False] * n + [True] * k and finite(out["loss"]),
        {"model_step": 3, "n": n, "k": k, "grad_flags": flags, "loss": fnum(out["loss"])},
        "flags = [False]*n + [True]*k, finite loss", required=False)


# ------------------------------------------------------------ outputs

def canonical(payload):
    body = {k: v for k, v in payload.items() if k != "run_meta"}
    return json.dumps(body, sort_keys=True, separators=(",", ":"))


def write_json(path, payload):
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def diff_paths(a, b, prefix="", out=None):
    out = [] if out is None else out
    if type(a) is not type(b):
        out.append(prefix or "/")
    elif isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append(f"{prefix}/{k}")
            else:
                diff_paths(a[k], b[k], f"{prefix}/{k}", out)
    elif isinstance(a, list):
        if len(a) != len(b):
            out.append(prefix)
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                diff_paths(x, y, f"{prefix}[{i}]", out)
    elif a != b:
        out.append(prefix)
    return out


def compare_reference(payloads, ref_dir):
    files = {}
    for key, name in OUTPUT_FILES.items():
        ref_path = ref_dir / name
        if not ref_path.exists():
            files[name] = {"identical": False, "error": "missing in reference"}
            continue
        ref = json.loads(ref_path.read_text(encoding="utf-8"))
        cur = json.loads(canonical(payloads[key]))
        ref_body = {k: v for k, v in ref.items() if k != "run_meta"}
        paths = diff_paths(ref_body, cur)
        files[name] = {"identical": not paths, "differing_paths": paths[:20],
                       "sha256_current": hashlib.sha256(canonical(payloads[key]).encode()).hexdigest(),
                       "sha256_reference": hashlib.sha256(canonical(ref).encode()).hexdigest()}
    return {"status": "PASS" if all(f["identical"] for f in files.values()) else "FAIL",
            "reference_run_utc": json.loads((ref_dir / OUTPUT_FILES["environment"]).read_text())
            .get("run_meta", {}).get("finished_utc") if (ref_dir / OUTPUT_FILES["environment"]).exists() else None,
            "files": files}


def short(obs, limit=220):
    text = json.dumps(obs, default=str) if not isinstance(obs, str) else obs
    return text if len(text) <= limit else text[:limit] + " ..."


def write_result_md(path, checks, env_payload, cfg_rec, repro, extra):
    up = env_payload["upstream"]
    env = env_payload["environment"]
    six_pass = all(checks[c]["status"] == "PASS" for c in CHECK_TITLES)
    done = six_pass and repro["status"] == "PASS"
    L = []
    L.append("# P1-B: Parcae native CPU correctness check — result\n")
    L.append(f"**P1-B status: {'COMPLETE' if done else 'NOT COMPLETE'}** "
             f"(six required checks: {'all PASS' if six_pass else 'not all PASS'}; "
             f"re-run reproducibility: {repro['status']}).\n")
    L.append("Scope: numerical/mechanical correctness of the *official, unmodified* Parcae code on CPU "
             "with a size-reduced, randomly initialised `parcae-small-140m` config and synthetic tokens. "
             "No checkpoint was downloaded, no 140M model was built or trained, no GPU was used. "
             f"The only optimisation is {ADAMW_STEPS} AdamW steps on one fixed batch to break the scaled-zero "
             "symmetry for the after-step diagnostics. **This is not a model-quality result.**\n")
    L.append("## Upstream source\n")
    L.append(f"- Repository: {UPSTREAM_URL}")
    L.append(f"- Pinned commit: `{up['pinned_sha']}` ({up['commit_date']}, \"{up['commit_subject']}\")")
    L.append(f"- Checkout clean before/after run: tracked changes {len(up['before_run']['tracked_changes'])}"
             f"/{len(up['after_run']['tracked_changes'])}, untracked files {len(up['before_run']['untracked_files'])}"
             f"/{len(up['after_run']['untracked_files'])}, ignored files {len(up['before_run']['ignored_files'])}"
             f"/{len(up['after_run']['ignored_files'])}")
    files = up["imported_files"]
    L.append(f"- Imported Parcae modules: {len(files)} files, all blobs equal to the pinned commit: "
             f"{all(f['matches_pinned_commit'] for f in files)}")
    L.append("- Parcae code is called from the checkout via `sys.path`; nothing is copied into OpenMythos.\n")
    L.append("## Environment\n")
    L.append(f"- Python {env['python']['version']} (isolated venv: {env['python']['venv_isolated']}), "
             f"torch {env['torch']['version']} (CUDA build {env['torch']['cuda_build']}, CUDA available: "
             f"{env['torch']['cuda_available']}), numpy {env['numpy']}, einops {env['einops']}")
    L.append(f"- {env['platform']['system']} {env['platform']['release']} {env['platform']['machine']}, "
             f"CPU: {env['platform']['cpu_model']}; torch threads {env['torch']['num_threads']}, "
             f"deterministic algorithms {env['torch']['deterministic_algorithms']}")
    L.append(f"- Parcae attention backend in effect: {env['parcae_attention_backend']['effective']}")
    L.append("- torch is the PyPI `torch==2.11.0` wheel pinned in `requirements-p1b-parcae.txt` (a CUDA-enabled "
             "build, used on CPU only). Full package list in `P1_B_ENVIRONMENT.json`.\n")
    L.append("## Size-reduced config (mechanism unchanged)\n")
    L.append("| field | official 140M | P1-B |\n|---|---|---|")
    for k, v in cfg_rec["size_overrides"].items():
        L.append(f"| `{k}` | {v['official']} | {v['p1b']} |")
    L.append(f"\nAll {len(cfg_rec['unchanged_mechanism_fields'])} mechanism fields (injection, init, sampling, "
             f"norms, nonlinearity, qk_norm, tying, ...) equal the official values: "
             f"{cfg_rec['mechanism_fields_equal_official']}. Batch {BATCH} x {SEQ} tokens, seed {SEED}. "
             f"Parameters: {extra['total_parameters']}.\n")
    L.append("## Results\n")
    L.append("| # | check | status | required sub-checks |\n|---|---|---|---|")
    for i, (cid, title) in enumerate(CHECK_TITLES.items(), 1):
        c = checks[cid]
        req = [x for x in c["items"] if x["required"]]
        L.append(f"| {i} | {title} | **{c['status']}** | "
                 f"{sum(x['status'] == 'PASS' for x in req)}/{len(req)} PASS |")
    L.append(f"| R | Re-run reproducibility | **{repro['status']}** | "
             f"{sum(f['identical'] for f in repro.get('files', {}).values())}/{len(OUTPUT_FILES)} JSON identical |\n")
    L.append("## Key observed values\n")
    for line in extra["highlights"]:
        L.append(f"- {line}")
    L.append("")
    L.append("## Sub-check details\n")
    for i, (cid, title) in enumerate(CHECK_TITLES.items(), 1):
        c = checks[cid]
        L.append(f"### {i}. {title} — {c['status']}\n")
        if c.get("error"):
            L.append(f"```\n{c['error']}\n```")
        for x in c["items"]:
            tag = x["status"] if x["required"] else f"{x['status']} (not required)"
            L.append(f"- **{tag}** {x['name']}  \n  criterion: {x['criterion']}  \n  observed: `{short(x['observed'])}`")
        L.append("")
    failed = [(cid, x["name"]) for cid in CHECK_TITLES for x in checks[cid]["items"]
              if x["status"] == "FAIL"]
    L.append("## Failures\n")
    if failed or any(checks[c].get("error") for c in CHECK_TITLES):
        for cid, name in failed:
            L.append(f"- {cid}: {name}")
        for c in CHECK_TITLES:
            if checks[c].get("error"):
                L.append(f"- {c}: exception (see details)")
    else:
        L.append("- None.")
    L.append("\n## NOT TESTED\n")
    for line in extra["not_tested"]:
        L.append(f"- {line}")
    L.append("\n## Observations about upstream behaviour (not failures)\n")
    for line in extra["observations"]:
        L.append(f"- {line}")
    L.append("\n## Reproducibility\n")
    if repro.get("files"):
        L.append(f"Compared with the previous run finished {repro.get('reference_run_utc')} (`run_meta` excluded):\n")
        L.append("| file | identical | sha256 (canonical, this run) |\n|---|---|---|")
        for name, f in repro["files"].items():
            L.append(f"| `{name}` | {f['identical']} | `{f.get('sha256_current', '-')}` |")
        L.append("\nA re-run on another machine or package set changes `P1_B_ENVIRONMENT.json` by design; "
                 "the criterion here is a re-run in the same environment.")
    else:
        L.append("NOT TESTED in this invocation (no `--reference-dir`).")
    L.append("\nRe-run from the OpenMythos repository root (CPU only, about 10 s):\n")
    L.append("```bash\nbash research/mini_mythos/scripts/p1b_setup_env.sh ./venv_p1b ./parcae\n"
             "./venv_p1b/bin/python -I research/mini_mythos/scripts/p1b_parcae_cpu_check.py \\\n"
             "    --parcae-dir ./parcae --out-dir /tmp/p1b_rerun \\\n"
             f"    --reference-dir {EVIDENCE_DIR}\n```\n")
    L.append("## Files\n")
    for name in list(OUTPUT_FILES.values()) + [RESULT_MD]:
        L.append(f"- `{EVIDENCE_DIR}/{name}`")
    path.write_text("\n".join(L) + "\n", encoding="utf-8")
    return done


# ------------------------------------------------------------ main

def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--parcae-dir", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--reference-dir", type=Path)
    args = ap.parse_args()
    parcae_dir = args.parcae_dir.resolve()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()
    started_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    torch.set_num_threads(NUM_THREADS)
    torch.use_deterministic_algorithms(True)
    before = import_parcae(parcae_dir)
    from parcae_lm.models.config import Config

    cfg, model = build_model(Config)
    cfg_rec = config_record(Config, cfg)
    inventory = param_inventory(model)
    batch = make_batch(cfg)
    mixed_step, mixed_n, mixed_k = find_mixed_step(model, cfg)
    timings = {}

    def timed(key, fn, *a):
        t0 = time.time()
        r = fn(*a)
        timings[key] = round(time.time() - t0, 3)
        return r

    checks = {cid: {"status": "NOT TESTED", "items": []} for cid in CHECK_TITLES}
    grad_detail, state_detail, decay_detail, native_detail = {}, {}, {}, {}

    # --- phase: init
    checks["check_1_forward_path"] = timed("check_1", guarded, check_forward_path, model, cfg, batch)
    c2_items = []
    c3_items = []
    c4_items = []

    def phase_checks(phase):
        c2_items.extend(check_finite(model, cfg, batch, phase, mixed_step))
        items, detail = check_backprop_reach(model, cfg, batch, phase)
        c3_items.extend(items)
        grad_detail[phase] = detail
        rep = decay_report(model.transformer.adapter)
        decay_detail[phase] = rep
        items, detail = check_loop_states(model, cfg, batch, phase, rep["probe_decay"]["mean"])
        c4_items.extend(items)
        state_detail[phase] = detail

    pair_items = []
    errors = {}
    for phase in ("init", "after_adamw_steps"):
        try:
            if phase == "after_adamw_steps":
                native_detail["adamw"] = adamw_steps(model, batch, cfg)
            timed(f"phase_{phase}", phase_checks, phase)
            pair_items.extend(check_pairs(model, cfg, batch, phase))
        except Exception:
            errors[phase] = traceback.format_exc(limit=8)
            break

    def finish(items):
        out = {"items": items, "status": verdict(items) if items else "NOT TESTED"}
        if errors:
            out["error"] = "\n".join(f"[{k}]\n{v}" for k, v in errors.items())
            out["status"] = "FAIL"
        return out

    checks["check_2_finite"] = finish(c2_items)
    checks["check_3_backprop_reach"] = finish(c3_items)
    checks["check_4_loop_states"] = finish(c4_items)

    def c5():
        items, reports = check_injection_decay(Config, decay_detail)
        native_detail["decay_reports"] = reports
        return {"items": items}
    checks["check_5_injection_decay"] = timed("check_5", guarded, c5)

    def c6():
        items, stats, gate = check_native_config(model, cfg, batch, mixed_step)
        native_detail["sampler_stats"] = stats
        native_detail["native_gating"] = gate
        items = pair_items + items
        items.append(check_checkpointing_equivalence(Config, model, cfg, batch))
        items.append(check_per_batch_forward(Config, model, cfg, batch))
        return {"items": items}
    checks["check_6_no_grad_with_grad"] = timed("check_6", guarded, c6)
    if errors:
        checks["check_6_no_grad_with_grad"]["status"] = "FAIL"
        checks["check_6_no_grad_with_grad"]["error"] = "\n".join(errors.values())

    after = upstream_state(parcae_dir)
    env = environment_info()
    imported = imported_upstream_files(parcae_dir)
    finished_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    script = Path(__file__).resolve()
    run_meta = {"started_utc": started_utc, "finished_utc": finished_utc,
                "wall_seconds": round(time.time() - started, 2), "timings_seconds": timings,
                "parcae_dir": str(parcae_dir), "out_dir": str(args.out_dir.resolve()),
                "argv": sys.argv, "executable": sys.executable,
                "openmythos_head": _try(lambda: git(script.parent, "rev-parse", "HEAD"))}

    env_payload = {
        "schema": "P1_B_ENVIRONMENT_V1",
        "upstream": {"url": UPSTREAM_URL, "pinned_sha": PINNED_SHA,
                     "commit_date": git(parcae_dir, "show", "-s", "--format=%cI", PINNED_SHA),
                     "commit_subject": git(parcae_dir, "show", "-s", "--format=%s", PINNED_SHA),
                     "license_file_sha256": _try(lambda: sha256_file(parcae_dir / "LICENSE")),
                     "before_run": before, "after_run": after,
                     "unmodified": before["head"] == after["head"] == PINNED_SHA
                     and not before["tracked_changes"] and not after["tracked_changes"],
                     "imported_files": imported,
                     "how_called": "pinned checkout inserted at sys.path[0]; parcae_lm imported from it"},
        "environment": env,
        "check_script": {"path": "research/mini_mythos/scripts/p1b_parcae_cpu_check.py",
                         "sha256": sha256_file(script)},
        "determinism": {"torch_num_threads": NUM_THREADS, "use_deterministic_algorithms": True,
                        "seed": SEED, "x0_seed_reset_before_every_forward": True,
                        "pytorch_bytecode_written_to_checkout": False},
        "run_meta": run_meta,
    }
    fb_payload = {
        "schema": "P1_B_FORWARD_BACKWARD_V1",
        "model_config": cfg_rec,
        "batch": {"batch_size": BATCH, "seq_len": SEQ, "data": "uniform random token ids, torch.Generator seed "
                  f"{SEED + 1}; labels = next token", "mixed_depth_model_step": mixed_step,
                  "mixed_step_per_sample_n": mixed_n, "mixed_step_per_sample_k": mixed_k},
        "parameter_inventory": inventory,
        "checks": {k: checks[k] for k in ("check_1_forward_path", "check_2_finite",
                                          "check_6_no_grad_with_grad")},
        "adamw_diagnostic_steps": native_detail.get("adamw"),
        "native_sampler_statistics": native_detail.get("sampler_stats"),
        "native_gating_run": native_detail.get("native_gating"),
        "run_meta": {"finished_utc": finished_utc},
    }
    state_payload = {
        "schema": "P1_B_STATE_DIAGNOSTICS_V1",
        "checks": {k: checks[k] for k in ("check_4_loop_states", "check_5_injection_decay")},
        "loop_state_trajectories": state_detail,
        "injection_decay_reports": native_detail.get("decay_reports"),
        "run_meta": {"finished_utc": finished_utc},
    }
    grad_payload = {
        "schema": "P1_B_GRADIENT_DIAGNOSTICS_V1",
        "checks": {"check_3_backprop_reach": checks["check_3_backprop_reach"]},
        "per_parameter_gradients": grad_detail,
        "run_meta": {"finished_utc": finished_utc},
    }
    payloads = {"environment": env_payload, "forward_backward": fb_payload,
                "state": state_payload, "gradient": grad_payload}

    repro = {"status": "NOT TESTED"}
    if args.reference_dir:
        repro = compare_reference(payloads, args.reference_dir.resolve())
    env_payload["run_meta"]["reproducibility_vs_reference"] = repro
    for key, name in OUTPUT_FILES.items():
        write_json(args.out_dir / name, payloads[key])

    extra = {"total_parameters": inventory["total_parameters"],
             "highlights": highlights(state_detail, native_detail, grad_detail),
             "not_tested": [
                 "GPU / FlashAttention-3 path (CPU run uses Parcae's SDPA fallback); P1-C scope.",
                 "Fused heads `cce`, `hhe`, `full-triton` (need Triton/CUDA); the official 140M default `pytorch` head is used.",
                 "`per-token` recurrent_iteration_method (not the 140M setting).",
                 "axonn tensor parallel, torch.compile, bf16 autocast, distributed sampler seeding, KV-cache generation.",
                 "The full 140M model forward/backward and any training (excluded by the P1-B scope).",
                 "Pretrained weights (excluded; all weights are random)."],
             "observations": observations(native_detail, inventory, cfg)}
    done = write_result_md(args.out_dir / RESULT_MD, checks, env_payload, cfg_rec, repro, extra)

    print(json.dumps({"checks": {k: v["status"] for k, v in checks.items()},
                      "reproducibility": repro["status"], "p1b_complete": done,
                      "out_dir": str(args.out_dir)}, indent=2))
    return 0 if all(checks[c]["status"] == "PASS" for c in CHECK_TITLES) else 1


def _try(fn):
    try:
        return fn()
    except Exception as exc:
        return f"unavailable: {type(exc).__name__}"


def highlights(state_detail, native_detail, grad_detail):
    out = []
    try:
        for phase, d in state_detail.items():
            vals = ", ".join(f"r={r['loops']}: |x|={r['final_state_norm_mean']:.4f}, "
                             f"|dx|={r['final_delta_norm_mean']:.4g}" for r in d["runs"])
            out.append(f"State norms ({phase}, mean per-token L2 of final state / last change): {vals}")
        init = state_detail["init"]["runs"][-1]["trajectory"]
        ratios = [row["delta_ratio_to_previous"] for row in init if "delta_ratio_to_previous" in row]
        out.append(f"Init: successive state-change ratios {min(ratios):.7f}..{max(ratios):.7f} "
                   f"(exact linear injection dynamics; scaled-zero core is identity at init)")
        for k, rep in native_detail["decay_reports"].items():
            p = rep["probe_decay"]
            out.append(f"Decay ({k}): min {p['min']:.7f}, max {p['max']:.7f}, mean {p['mean']:.7f}; "
                       f"get_spectral_norm {rep['native_get_spectral_norm']:.7f}, "
                       f"get_contraction_factor {rep['native_get_contraction_factor']:.7f}")
        for phase, d in grad_detail.items():
            g = d["group_grad_norms"]
            out.append(f"Group grad norms ({phase}, pair {d['num_steps_pair']}): "
                       + ", ".join(f"{k} {v:.4g}" for k, v in g.items()))
        sq = native_detail["sampler_stats"]["per_sequence"]
        out.append(f"Native per-sequence sampler over {sq['samples']} draws: mean n {sq['mean_no_grad_n']:.3f}, "
                   f"mean k {sq['mean_with_grad_k']:.3f}, mean total {sq['mean_total']:.3f}, "
                   f"max k {sq['max_k']}, violations {sq['rule_violations']}")
        gate = native_detail["native_gating"]
        out.append(f"Native gated forward (model.step={gate['model_step']}): per-sample n {gate['per_sample_n']}, "
                   f"k {gate['per_sample_k']}, gating mismatches {gate['gating_mismatches']}, loss {gate['loss']:.5f}")
        out.append("AdamW diagnostic losses before each step: "
                   + ", ".join(f"{x:.5f}" for x in native_detail["adamw"]["losses_before_each_step"]))
    except Exception as exc:  # highlights are a summary; details stay in the JSON files
        out.append(f"(highlight extraction incomplete: {type(exc).__name__})")
    return out


def observations(native_detail, inventory, cfg):
    out = []
    try:
        sq = native_detail["sampler_stats"]["per_sequence"]
        bt = native_detail["sampler_stats"]["per_batch"]
        out.append(f"`poisson-truncated-full` means different totals per mode: per-sequence draws a total "
                   f"(mean {sq['mean_total']:.3f}) and splits it as k = min(total, {cfg.mean_backprop_depth}); "
                   f"per-batch draws n (mean {bt['mean_no_grad_n']:.3f}) and adds k = min(n, "
                   f"{cfg.mean_backprop_depth}), mean total {bt['mean_total']:.3f}.")
    except Exception:
        pass
    out.append("In `per-sequence`/`per-token` mode, `iterate_forward` samples depths whenever "
               "`num_steps_pair` is None, also in eval mode; upstream eval code passes "
               "`num_steps_pair=[mean_recurrence, 0]` explicitly, which P1-B mirrors.")
    ve = [r for r in inventory["parameters"] if r["group"].startswith("value_embeds")]
    if ve:
        out.append("`value_embeds` (and attention `ve_gate`) are plain `torch.nn` modules not re-initialised by "
                   f"`reset_parameters`; observed value-embedding init std: "
                   + ", ".join(f"{r['name']} {r['init_std']:.6f}" for r in ve) + ".")
    out.append("`scaled-zero` zero-initialises every attention `c_proj` and MLP `proj`, so at init every block "
               "is an exact identity and q/k/v/fc/norm/ve_gate weights and the value-embedding tables get exactly zero gradient; "
               "they receive gradient after the first optimiser step (see check 3).")
    return out


if __name__ == "__main__":
    sys.exit(main())
