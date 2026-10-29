#!/usr/bin/env python3
"""M2-L: continuous 1920-step official GPT/Parcae CPU learning curves; not an efficiency claim.

The 120-step continuation must exactly replay the independently preserved M2 matched
pilot before any longer training. OOD Alice is evaluated once, after all arms finish.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import platform
import resource
import subprocess
import sys
import time
import traceback
from pathlib import Path
from urllib.request import urlopen

os.environ["CUDA_VISIBLE_DEVICES"] = ""
import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE_PY = ROOT / "research/mini_mythos/m2_matched/experiment.py"
BASE_PILOT = ROOT / "research/mini_mythos/m2_matched/evidence/linux_e533fbe/pilot.json"
BASE_CONFIG = ROOT / "research/mini_mythos/m2_matched/frozen_config.json"
SEEDS = (42, 20261029, 20261030)
CHECKPOINTS = (120, 480, 1920)
TEXT_SHA = "86c4e6aa9db7c042ec79f339dcb96d42b0075e16b8fc2e86bf0ca57e2dc565ed"
ALICE_SHA = "146e69455b17fac23bee136d0121ced326e0b99caf206df0281cb67241963875"
ALICE_GIT_BLOB = "6c89ee6db335fcd14ff756e5841aba7b9cd708d0"
ALICE_URL = ("https://raw.githubusercontent.com/dakrone/corpus/"
             "f25de55809404f0173504d6853b7b6df93d51ae0/data/alice-in-wonderland.txt")
EXPECTED_BASE = "e533fbe36aaf18fd551ee21e5c2d20551b5a2e16"


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(buf: bytes) -> str:
    return hashlib.sha256(buf).hexdigest()


def file_sha(path: Path) -> str:
    return sha(path.read_bytes())


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def atomic_save(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    torch.save(obj, temp)
    os.replace(temp, path)


def load_matched():
    require(BASE_PY.exists() and BASE_PILOT.exists() and BASE_CONFIG.exists(),
            "M2 matched immutable reference files missing")
    spec = importlib.util.spec_from_file_location("mythos_m2_reference", BASE_PY)
    require(spec and spec.loader, "cannot import M2 reference")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def pinned_file(path: Path, expected_sha: str, url: str | None = None) -> bytes:
    if not path.exists():
        require(url is not None, "file missing: " + str(path))
        data = urlopen(url, timeout=120).read()
        require(sha(data) == expected_sha, "download SHA256 mismatch: " + str(path))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    data = path.read_bytes()
    require(sha(data) == expected_sha, "pinned SHA256 mismatch: " + str(path))
    return data


def source_version(path: Path) -> str:
    return subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"],
                                   text=True).strip()


def assert_early(ref, arm, seed, initial, final, batch_hash, first_losses, first_grads,
                 init_val, val_120, count):
    """A strict historical comparison, not a retuned tolerance."""
    require(ref["git_head"] == EXPECTED_BASE, "reference pilot has unexpected HEAD")
    old = next((r for r in ref["rows"] if r["arm"] == arm and r["seed"] == seed), None)
    require(old is not None, "missing historical seed/arm")
    fields = (
        (initial, old["initial_weights_sha256"], "initial weights"),
        (final, old["final_weights_sha256"], "step120 weights"),
        (batch_hash, old["batch_starts_sha256"], "batch SHA"),
        (first_losses, old["loss_trace"], "120 training losses"),
        (first_grads, old["gradient_norm_trace"], "120 gradient norms"),
        (init_val, old["initial_validation"]["nll"], "initial val NLL"),
        (val_120, old["final_validation"]["nll"], "step120 val NLL"),
        (count, old["counts"], "parameter/FLOP counts"),
    )
    for actual, expected, label in fields:
        require(actual == expected, f"120-step reference mismatch: {seed}/{arm}/{label}")
    return {"status": "PASS", "reference_git_head": EXPECTED_BASE,
            "exact_equality_fields": [x[2] for x in fields]}


def main(args):
    require(sys.version_info[:2] == (3, 12), "Python 3.12 required")
    import numpy
    import einops
    require(torch.__version__ == "2.11.0+cpu", "exact 120-step replay requires torch 2.11.0+cpu")
    require(numpy.__version__ == "1.26.4" and einops.__version__ == "0.8.0",
            "pinned dependency mismatch")
    require(platform.system() == "Linux", "formal M2-L requires Linux CPU")
    require(not torch.cuda.is_available() or os.environ["CUDA_VISIBLE_DEVICES"] == "",
            "GPU execution prohibited")
    require(set(args.seeds).issubset(SEEDS) and len(set(args.seeds)) == len(args.seeds),
            "invalid or repeated seed list")
    m2 = load_matched()
    require(source_version(ROOT) != "", "unversioned OpenMythos code")
    require(not subprocess.check_output(["git", "-C", str(ROOT), "status",
                                         "--porcelain", "--untracked-files=no"],
                                        text=True).strip(), "tracked research files changed")
    require(file_sha(BASE_CONFIG) == "a49b38521a45e716b1cb5f2c2b55d317d06ca7542d02623349c5331e9fe26447",
            "frozen M2 config drift")
    require(file_sha(BASE_PY) == "74f00c64448ddbc224a48ef83dc031a90c33448ccb92647666707f6b8f988967",
            "M2 reference harness drift")
    frozen = read(BASE_CONFIG)
    ref = read(BASE_PILOT)
    require(frozen["status"] == "PASS" and frozen["source_pin"] == m2.PIN,
            "M2 calibration/pin mismatch")
    m2.setup(args.parcae_dir)
    require(source_version(args.parcae_dir) == m2.PIN, "upstream mismatch")
    raw = pinned_file(args.text, TEXT_SHA)
    val_start, test_start = int(len(raw)*.8), int(len(raw)*.9)
    train = torch.tensor(list(raw[:val_start]), dtype=torch.long)
    val = torch.tensor(list(raw[val_start:test_start]), dtype=torch.long)
    report_path = args.out / "pilot.json"
    args.out.mkdir(parents=True, exist_ok=True)
    identity = {
        "experiment": "MYTHOS-M2-L-CONTINUOUS-CPU-V1",
        "protocol_sha256": file_sha(HERE/"PROTOCOL.md"),
        "script_sha256": file_sha(Path(__file__)),
        "reference_config_sha256": file_sha(BASE_CONFIG),
        "reference_pilot_sha256": file_sha(BASE_PILOT),
        "original_parcae_pin": m2.PIN,
        "code_head": source_version(ROOT),
        "environment": {"python": platform.python_version(), "torch": torch.__version__,
                        "numpy": numpy.__version__, "einops": einops.__version__,
                        "platform": platform.platform(), "cpu_threads": 1,
                        "gpu": False},
        "data": {"train_sha256": sha(raw[:val_start]), "val_sha256": sha(raw[val_start:test_start]),
                 "full_sha256": sha(raw), "train_bytes": len(train), "val_bytes": len(val),
                 "original_seen_test_bytes_excluded": len(raw)-test_start,
                 "independent_ood_source": ALICE_URL, "independent_ood_sha256": ALICE_SHA},
        "steps": list(CHECKPOINTS), "seeds": list(args.seeds)
    }
    if report_path.exists():
        report = read(report_path)
        for key in ("experiment", "protocol_sha256", "script_sha256",
                    "reference_config_sha256", "reference_pilot_sha256",
                    "original_parcae_pin", "data", "seeds", "code_head", "environment"):
            require(report[key] == identity[key], "resume incompatible report: " + key)
    else:
        report = dict(identity, execution_status="NOT TESTED", continuity_status="NOT TESTED",
                      quality_validation_status="NOT TESTED", ood_status="NOT TESTED", rows=[])
        write(report_path, report)

    # Deterministic mathematical counting is rechecked on both actual native models.
    for seed in args.seeds:
        models = {"gpt": m2.make("gpt", frozen["selected"]["ffn"], seed),
                  "parcae": m2.make("parcae", 64, seed)}
        pair_init = m2.pair_io(models["gpt"], models["parcae"])
        generator = torch.Generator().manual_seed(seed+11)
        starts = torch.randint(len(train)-m2.SEQ, (CHECKPOINTS[-1], m2.BATCH),
                               generator=generator)
        reference_starts_sha = m2.tensor_sha(starts[:120])
        for arm, model in models.items():
            row_path = args.out / f"{arm}_{seed}.json"
            ckpt_paths = {s: args.out / f"{arm}_{seed}_step{s}.pt" for s in CHECKPOINTS}
            if row_path.exists():
                row = read(row_path)
                require(row["seed"] == seed and row["arm"] == arm
                        and row["batch_starts_sha256_120"] == reference_starts_sha,
                        "incompatible saved row")
            else:
                row = {"seed": seed, "arm": arm, "status": "NOT TESTED",
                       "batch_starts_sha256_120": reference_starts_sha,
                       "batch_starts_sha256_all": m2.tensor_sha(starts),
                       "shared_io_initialization": pair_init,
                       "checkpoints": {}, "total_train_tokens": CHECKPOINTS[-1]*m2.BATCH*m2.SEQ}
            preflight = m2.preflight(model, arm)
            require(preflight["status"] == "PASS", "native preflight failure")
            counts = m2.count(model, arm)
            expected = frozen["selected"] if arm == "gpt" else frozen["parcae"]
            require(all(counts[k] == expected[k] for k in counts), "parameter/FLOP count drift")
            row["counts"] = counts
            row["preflight"] = preflight
            # Same ordering as the pinned M2 pilot: preflight, FLOP count, then initial weight hash.
            current_initial_sha = m2.weights_sha(model)
            if "init_sha" in row:
                require(row["init_sha"] == current_initial_sha, "initial weight hash changed")
            row["init_sha"] = current_initial_sha

            # Fresh historical trajectory starts exactly like original M2 matched.
            initial_validation = m2.evaluate(model, arm, val, 1212)
            if "initial_validation" in row:
                require(row["initial_validation"] == initial_validation, "initial val changed")
            row["initial_validation"] = initial_validation
            old_row = next(r for r in ref["rows"] if r["seed"] == seed and r["arm"] == arm)
            require(row["init_sha"] == old_row["initial_weights_sha256"]
                    and reference_starts_sha == old_row["batch_starts_sha256"],
                    "initial M2 reference mismatch")
            opt = torch.optim.AdamW(model.parameters(), lr=.002, betas=(.9,.999),
                                    eps=1e-8, weight_decay=0.)
            prior = [step for step, path in ckpt_paths.items() if path.exists()]
            step_start, loss_trace, grad_trace, total_train_seconds = 0, [], [], 0.0
            resume_rng = None
            if prior:
                step_start = max(prior)
                ckpt = torch.load(ckpt_paths[step_start], map_location="cpu", weights_only=True)
                require(ckpt["step"] == step_start and ckpt["arm"] == arm
                        and ckpt["seed"] == seed
                        and ckpt["script_sha256"] == identity["script_sha256"]
                        and ckpt["batch_sha256"] == row["batch_starts_sha256_all"],
                        "checkpoint provenance mismatch")
                model.load_state_dict(ckpt["model"])
                opt.load_state_dict(ckpt["optimizer"])
                resume_rng = ckpt["rng"]
                loss_trace = ckpt["loss_trace"]
                grad_trace = ckpt["gradient_norm_trace"]
                total_train_seconds = ckpt["train_seconds"]
                require(len(loss_trace) == len(grad_trace) == step_start,
                        "checkpoint train history length mismatch")
                require(row["checkpoints"].get(str(step_start), {}).get("weight_sha256")
                        == m2.weights_sha(model), "checkpoint row/state mismatch")
                require(row["checkpoints"]["120"]["continuity"]["status"] == "PASS",
                        "checkpoint missing 120-step continuity")
            with torch.random.fork_rng(devices=[]), sdpa_kernel(SDPBackend.MATH):
                if resume_rng is None:
                    torch.manual_seed(seed+2000)
                else:
                    torch.set_rng_state(resume_rng)
                for ix in range(step_start, CHECKPOINTS[-1]):
                    step_clock = time.perf_counter()
                    batch_ids = starts[ix]
                    model.train()
                    opt.zero_grad(set_to_none=True)
                    value = m2.call(model, arm, *m2.window(train, batch_ids))
                    require(bool(torch.isfinite(value)), f"nonfinite loss at {seed}/{arm}/{ix+1}")
                    value.backward()
                    require(all(bool(torch.isfinite(p.grad).all()) for p in model.parameters()
                                if p.grad is not None), "nonfinite gradient")
                    gn = float(torch.nn.utils.clip_grad_norm_(model.parameters(), 1.))
                    require(math.isfinite(gn), "nonfinite gradient norm")
                    opt.step()
                    total_train_seconds += time.perf_counter() - step_clock
                    loss_trace.append(float(value.detach()))
                    grad_trace.append(gn)
                    if ix+1 not in CHECKPOINTS:
                        continue
                    now = ix+1
                    v = m2.evaluate(model, arm, val, 1212)
                    weight_sha = m2.weights_sha(model)
                    entry = {"step": now, "val": v, "weight_sha256": weight_sha,
                             "train_tokens": now*m2.BATCH*m2.SEQ,
                             "counted_training_flops": now*counts["step_flops"],
                             "train_seconds": total_train_seconds,
                             "process_maxrss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
                    if now == 120:
                        entry["continuity"] = assert_early(
                            ref, arm, seed, row["init_sha"], weight_sha,
                            reference_starts_sha, loss_trace[:120], grad_trace[:120],
                            initial_validation["nll"], v["nll"], counts)
                    state = {"model": model.state_dict(), "optimizer": opt.state_dict(),
                             "rng": torch.get_rng_state(), "arm": arm, "seed": seed,
                             "step": now, "script_sha256": identity["script_sha256"],
                             "batch_sha256": row["batch_starts_sha256_all"],
                             "loss_trace": loss_trace, "gradient_norm_trace": grad_trace,
                             "train_seconds": total_train_seconds}
                    atomic_save(ckpt_paths[now], state)
                    entry["checkpoint_file"] = ckpt_paths[now].name
                    entry["checkpoint_sha256"] = file_sha(ckpt_paths[now])
                    row["checkpoints"][str(now)] = entry
                    row["status"] = "PARTIAL" if now < CHECKPOINTS[-1] else "PASS"
                    write(row_path, row)
                    print(json.dumps({"seed": seed, "arm": arm, "step": now,
                                      "validation_nll": v["nll"], "state": row["status"]}),
                          flush=True)
            row["final_weights_sha256"] = m2.weights_sha(model)
            row["final_validation"] = row["checkpoints"]["1920"]["val"]
            require(row["initial_validation"]["nll"]-row["final_validation"]["nll"] >= .01,
                    "final validation improvement below .01")
            require(row["init_sha"] != row["final_weights_sha256"], "weights unchanged")
            require(row["status"] == "PASS" and len(loss_trace) == CHECKPOINTS[-1],
                    "incomplete training")
            row["loss_trace_sha256"] = sha(json.dumps(loss_trace).encode("utf-8"))
            row["grad_trace_sha256"] = sha(json.dumps(grad_trace).encode("utf-8"))
            row["status"] = "PASS"
            write(row_path, row)
            report["rows"] = [r for r in report["rows"]
                              if not (r["seed"] == seed and r["arm"] == arm)] + [row]
            report["execution_status"] = "PARTIAL"
            write(report_path, report)

    required = {(seed, arm) for seed in SEEDS for arm in ("gpt", "parcae")}
    observed = {(r["seed"], r["arm"]) for r in report["rows"] if r["status"] == "PASS"}
    if observed != required:
        # No independent OOD test until *all six* completed, regardless of requested subset.
        report["execution_status"] = "PARTIAL"
        write(report_path, report)
        return 0

    paired = []
    for seed in SEEDS:
        a = next(r for r in report["rows"] if r["seed"] == seed and r["arm"] == "gpt")
        b = next(r for r in report["rows"] if r["seed"] == seed and r["arm"] == "parcae")
        for key in ("120", "480", "1920"):
            require(a["checkpoints"][key]["train_tokens"] == b["checkpoints"][key]["train_tokens"],
                    "training token mismatch")
        param_ratio = m2.ratio(a["counts"]["parameters"], b["counts"]["parameters"])
        flops_ratio = m2.ratio(a["counts"]["step_flops"], b["counts"]["step_flops"])
        require(max(param_ratio, flops_ratio) <= 1.10, "frozen budget violation")
        paired.append({"seed": seed, "parameter_ratio": param_ratio,
                       "flops_ratio": flops_ratio,
                       "validation_nll_deltas_parcae_minus_gpt": {
                           key: b["checkpoints"][key]["val"]["nll"] -
                                a["checkpoints"][key]["val"]["nll"]
                           for key in ("120", "480", "1920")}})
    last_deltas = [p["validation_nll_deltas_parcae_minus_gpt"]["1920"] for p in paired]
    report["paired"] = paired
    report["continuity_status"] = "PASS"
    report["budget_status"] = "PASS"
    report["quality_validation_status"] = (
        "PASS" if sum(last_deltas)/3 <= .02 and max(last_deltas) <= .05 else "FAIL")
    report["mean_validation_nll_delta_step1920"] = sum(last_deltas)/3
    report["execution_status"] = "PASS"
    write(report_path, report)

    # OOD test is strictly delayed until *all* six training runs and hypotheses are frozen.
    alice = pinned_file(args.alice, ALICE_SHA, ALICE_URL)
    require(len(alice) == 167497, "OOD byte length mismatch")
    git_blob = hashlib.sha1(b"blob " + str(len(alice)).encode() + bytes([0]) + alice).hexdigest()
    require(git_blob == ALICE_GIT_BLOB, "OOD Git blob mismatch")
    ood_pool = torch.tensor(list(alice), dtype=torch.long)
    ood_rows = []
    for seed in SEEDS:
        models = {"gpt": m2.make("gpt", frozen["selected"]["ffn"], seed),
                  "parcae": m2.make("parcae", 64, seed)}
        m2.pair_io(models["gpt"], models["parcae"])
        for arm, model in models.items():
            checkpoint = args.out / f"{arm}_{seed}_step1920.pt"
            state = torch.load(checkpoint, map_location="cpu", weights_only=True)
            require(file_sha(checkpoint) ==
                    next(r for r in report["rows"] if r["seed"] == seed and r["arm"] == arm)
                    ["checkpoints"]["1920"]["checkpoint_sha256"], "final weight file changed")
            model.load_state_dict(state["model"])
            v = m2.evaluate(model, arm, ood_pool, 1313)
            ood_rows.append({"seed": seed, "arm": arm, "result": v})
    report["ood"] = {"corpus_sha256": ALICE_SHA, "git_blob_sha1": ALICE_GIT_BLOB,
                     "domain": "public-domain Alice; independent out-of-domain diagnostic",
                     "rows": ood_rows,
                     "paired_nll_deltas_parcae_minus_gpt": [
                         next(r for r in ood_rows if r["seed"] == seed and r["arm"] == "parcae")
                         ["result"]["nll"] -
                         next(r for r in ood_rows if r["seed"] == seed and r["arm"] == "gpt")
                         ["result"]["nll"] for seed in SEEDS]}
    report["ood_status"] = "PASS (one-time OOD evaluation completed; no quality claim)"
    m2.upstream_check(args.parcae_dir)
    report["upstream_clean_after"] = True
    report["grok_review_status"] = "USER-SUPPLIED REVIEW; not a connected repeat audit"
    write(report_path, report)
    print(json.dumps({"execution": report["execution_status"],
                      "continuity": report["continuity_status"],
                      "budget": report["budget_status"],
                      "validation_tolerance": report["quality_validation_status"],
                      "validation_delta_step1920": report["mean_validation_nll_delta_step1920"],
                      "ood_nll_deltas": report["ood"]["paired_nll_deltas_parcae_minus_gpt"]}),
          flush=True)
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--parcae-dir", type=Path, required=True)
    p.add_argument("--text", type=Path, required=True)
    p.add_argument("--alice", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--seeds", nargs="+", type=int, default=list(SEEDS))
    ns = p.parse_args()
    try:
        sys.exit(main(ns))
    except Exception:
        ns.out.mkdir(parents=True, exist_ok=True)
        (ns.out / "BLOCKED_error.txt").write_text(traceback.format_exc(), encoding="utf-8")
        traceback.print_exc()
        sys.exit(2)
