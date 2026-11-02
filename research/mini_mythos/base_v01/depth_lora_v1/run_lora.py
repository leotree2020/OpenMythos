"""One frozen CPU depth-LoRA training/evaluation worker and fresh reload check.

No work at import time. Large logits/adapters remain under private/. The operator
owns upstream/input pins, resource gates, custody and repository publication.
"""
from __future__ import annotations
import argparse
import datetime
import gc
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import signal
import struct
import subprocess
import sys
import time
import traceback

SPACE = "bookish-pancake-vwqx7rr9x5w3wxjr"
PYTHON = "/workspaces/mythos-base-v01-cpu312/bin/python"
UPSTREAM = "69284c13746e849104f738d6d1a347b1f457df76"
WEIGHTS = "ed6eb306464dd0d694e9eacd58f7e06ac3e44b43cb7c5c79dbcb1543059c6621"
CONFIG = "5c8fc785c2f6dba67d0370ad715034860e3b22bfce850da825c06baa03923c13"
TRAIN_SEEDS, EVAL_SEEDS, ARMS = (4101, 4202), (5101, 5202), ("shared", "depth")
ENV = {"OMP_NUM_THREADS": "2", "MKL_NUM_THREADS": "2", "OPENBLAS_NUM_THREADS": "1",
       "RAYON_NUM_THREADS": "1", "TOKENIZERS_PARALLELISM": "false", "CUDA_VISIBLE_DEVICES": "",
       "PYTHONDONTWRITEBYTECODE": "1", "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"}


class Stop(Exception):
    def __init__(self, status, reason):
        super().__init__(reason)
        self.status = status


def info(path):
    h, n = hashlib.sha256(), 0
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(1048576), b""):
            h.update(b)
            n += len(b)
    return {"bytes": n, "sha256": h.hexdigest()}


def save(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n")


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def git(path, *args):
    return subprocess.check_output(["git", "-C", str(path), *args], text=True, timeout=60).strip()


def validate_data(data):
    if not isinstance(data, dict) or not all(isinstance(data.get(k), list) and len(data[k]) == 16 for k in ("train", "eval")):
        raise ValueError("exactly16 train and16 eval articles required")
    all_ids, all_tokens = [], []
    for group in ("train", "eval"):
        for row in data[group]:
            if not isinstance(row.get("id"), str) or not row["id"]:
                raise ValueError("article id missing")
            tokens = row.get("tokens")
            if not isinstance(tokens, list) or len(tokens) != 129 or not all(type(t) is int and 0 <= t < 32768 for t in tokens):
                raise ValueError("exact129-token article input required")
            all_ids.append(row["id"])
            all_tokens.append(tuple(tokens))
    if len(set(all_ids)) != 32 or len(set(all_tokens)) != 32:
        raise ValueError("duplicate/overlapping article identity or selected tokens")
    return data


def training_h0_seed(train_seed, step):
    if train_seed not in TRAIN_SEEDS or type(step) is not int or not 0 <= step < 32:
        raise ValueError("invalid frozen training seed/step")
    return 1000000 + 100 * train_seed + step


def normalize(raw):
    clean = {}
    for name, value in raw.items():
        for prefix in ("module.", "_orig_mod.", "model."):
            if name.startswith(prefix):
                name = name[len(prefix):]
        if name in clean:
            raise ValueError("normalized model key collision")
        clean[name] = value
    return clean


def finite_tree(torch, value):
    if isinstance(value, torch.Tensor):
        return not value.is_floating_point() or bool(torch.isfinite(value).all())
    if isinstance(value, dict):
        return all(finite_tree(torch, x) for x in value.values())
    if isinstance(value, (list, tuple)):
        return all(finite_tree(torch, x) for x in value)
    return True


def per_bank_hashes(library, banks):
    return {label: [[library.digest(x) for x in p] for p in parameters]
            for label, parameters in (("A", banks.A), ("B", banks.B))}


def optimizer_state_valid(torch, state, steps=32):
    if not finite_tree(torch, state) or len(state.get("state", {})) != 4:
        return False
    groups = state.get("param_groups", [])
    if len(groups) != 1 or len(groups[0].get("params", [])) != 4:
        return False
    if set(groups[0]["params"]) != set(state["state"]):
        return False
    for value in state["state"].values():
        if set(value) != {"step", "exp_avg", "exp_avg_sq"}:
            return False
        if not isinstance(value["step"], torch.Tensor) or value["step"].numel() != 1 or float(value["step"]) != steps:
            return False
        if value["exp_avg"].shape != value["exp_avg_sq"].shape:
            return False
    return True


class Run:
    def __init__(self, spec, out, reload_mode):
        self.spec, self.out, self.reload = spec, out, reload_mode
        self.public, self.private = out / "public", out / "private"
        self.public.mkdir()
        self.private.mkdir()
        self.journal = (self.public / "checks.jsonl").open("x", encoding="utf-8", buffering=1)
        self.train_log = (self.public / "training.jsonl").open("x", encoding="utf-8", buffering=1)
        self.environment = {"planned": "CPUFP32 native fixed32 fullBPTT; base frozen"}
        self.checks = {"PASS": 0, "FAIL": 0, "BLOCKED": 0}
        self.actual = dict(calls_started=0, calls_completed=0, train_steps=0, eval_rows=0,
                           zero_control_calls=0, model_loads=0, adapters_saved=0, reload_calls=0)
        self.model = self.library = None
        self.before = None
        self.evaluations, self.adapter_rows, self.reload_rows = [], [], []
        self.phase = "preflight"
        self.started = time.perf_counter()

    def check(self, purpose, okay, actual=None, expected=True, failure="FAIL"):
        status = "PASS" if okay else failure
        self.checks[status] += 1
        self.journal.write(json.dumps({"Purpose": purpose, "Environment": self.environment,
            "Input": {"freeze_commit": self.spec["freeze_commit"], "phase": self.phase},
            "Expected": expected, "Actual": actual, "Status": status}, allow_nan=False) + "\n")
        if not okay:
            raise Stop(failure, purpose)

    def call(self, runner, ids, seed, banks=None, training=False):
        limit = 4 if self.reload else 293
        self.check("call budget", self.actual["calls_started"] < limit, self.actual["calls_started"], limit)
        self.actual["calls_started"] += 1
        result = runner.forward(ids, seed, banks, training)
        self.actual["calls_completed"] += 1
        return result


def initialize(run):
    spec = run.spec
    repo, upstream, model_dir = (Path(spec[k]).resolve() for k in ("repo", "upstream", "model_dir"))
    run.check("target CPU runtime", os.environ.get("CODESPACE_NAME") == SPACE and platform.system() == "Linux"
              and platform.python_version() == "3.12.3" and sys.executable == PYTHON
              and sys.flags.isolated and sys.dont_write_bytecode and sys.byteorder == "little", failure="BLOCKED")
    run.check("frozen clean execution checkout", git(repo, "rev-parse", "HEAD") == spec["freeze_commit"]
              and not git(repo, "status", "--porcelain"))
    run.check("clean pinned upstream", git(upstream, "rev-parse", "HEAD") == UPSTREAM
              and not git(upstream, "status", "--porcelain"))
    run.check("frozen official weights", info(model_dir / "pytorch_model.bin")["sha256"] == WEIGHTS)
    run.check("frozen official config", info(model_dir / "config.json")["sha256"] == CONFIG)
    run.check("frozen data payload", info(spec["data_path"])["sha256"] == spec["inputs_sha256"])
    data = validate_data(load(spec["data_path"]))
    for k, value in ENV.items():
        os.environ[k] = value
    sys.path.insert(0, str(upstream))
    import torch
    torch.set_default_device("cpu")
    torch.set_default_dtype(torch.float32)
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True, warn_only=False)
    run.environment = {"python": sys.version, "torch": str(torch.__version__), "device": str(torch.get_default_device()),
        "dtype": str(torch.get_default_dtype()), "intra": torch.get_num_threads(), "interop": torch.get_num_interop_threads(),
        "deterministic": torch.are_deterministic_algorithms_enabled(), "cpu_autocast": torch.is_autocast_enabled("cpu"),
        "cuda_autocast": torch.is_autocast_enabled("cuda"), "env": {k: os.environ.get(k) for k in ENV}}
    run.check("exact numerical runtime", str(torch.__version__) == "2.11.0+cpu"
              and not torch.cuda.is_available() and not run.environment["cpu_autocast"] and not run.environment["cuda_autocast"],
              run.environment, failure="BLOCKED")
    save(run.public / "environment.json", run.environment)
    library_path = Path(__file__).with_name("lora_model.py")
    module_spec = importlib.util.spec_from_file_location("frozen_depth_lora_model", library_path)
    library = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(library)
    run.library = library
    from receval.models.parcae import ModelingParcae
    from parcae_lm.attention_backends import flash_attention
    run.check("native CPU SDPA backend", flash_attention._override_impl is None and not flash_attention.HAS_FA3)
    raw_weights = normalize(torch.load(model_dir / "pytorch_model.bin", map_location="cpu", weights_only=True))
    run.actual["model_loads"] += 1
    run.model = model = ModelingParcae.from_pretrained(model_dir, device="cpu", dtype=None)
    model.eval()
    for p in model.parameters():
        p.requires_grad_(False)
    run.check("native official architecture", type(model) is ModelingParcae and sum(p.numel() for p in model.parameters()) == 144323136
              and len(list(model.parameters())) == 61 and len(model.state_dict()) == 63
              and model.lm_head.weight is model.transformer.wte.weight and not model.gradient_checkpointing)
    run.check("exact original state keys", set(model.state_dict()) == set(raw_weights))
    for name, tensor in model.state_dict().items():
        original = raw_weights[name]
        run.check("original tensor byte identity " + name, tensor.dtype == original.dtype and tensor.shape == original.shape
                  and library.raw(tensor) == library.raw(original) and tensor.device.type == "cpu" and library.finite(tensor))
    del raw_weights
    gc.collect()
    run.before = library.state_hashes(model)
    save(run.public / "base_state_before.json", run.before)
    run.check("native runtime retained after import/load", torch.get_num_threads() == 2 and torch.get_num_interop_threads() == 1
              and torch.are_deterministic_algorithms_enabled() and not torch.is_autocast_enabled("cpu"))
    return torch, library, library.NativeFixed32(model), data


def ids_targets(torch, sample):
    return torch.tensor([sample["tokens"][:128]], dtype=torch.long), torch.tensor(sample["tokens"][1:], dtype=torch.long)


def evaluate(run, torch, library, runner, data, banks, arm, train_seed, references):
    run.phase = "evaluation " + arm + " " + str(train_seed)
    for index, sample in enumerate(data["eval"]):
        ids, targets = ids_targets(torch, sample)
        for seed in EVAL_SEEDS:
            logits, observed = run.call(runner, ids, seed, banks)
            key = (index, seed)
            if arm == "fixed32":
                references[key] = observed
            else:
                run.check("paired actual h0 and native RNG", observed == references[key], observed, references[key])
            values = logits[0, 64:].detach().contiguous()
            run.check("evaluation exact scored shape", tuple(values.shape) == (64, 32768), list(values.shape))
            raw = library.raw(values)
            filename = "private/eval_%s_%s_%02d_%d.bin" % (arm, train_seed, index, seed)
            with (run.out / filename).open("xb") as f:
                f.write(raw)
            metrics = library.score(logits, targets)
            row = {"arm": arm, "train_seed": train_seed, "eval_seed": seed, "article_id": sample["id"],
                "article_index": index, "logits_file": filename, "logits_sha256": hashlib.sha256(raw).hexdigest(),
                "shape": [64, 32768], "dtype": "float32-le", "h0_sha256": observed["h0_sha256"],
                "targets_sha256": hashlib.sha256(struct.pack("<64q", *sample["tokens"][65:129])).hexdigest(),
                "observer": observed, **metrics}
            run.evaluations.append(row)
            run.actual["eval_rows"] += 1
            print(json.dumps({"phase": "eval", "arm": arm, "train_seed": train_seed, "row": run.actual["eval_rows"]}), flush=True)
            del logits, values, raw


def train_adapter(run, torch, library, runner, data, arm, seed, paired_training):
    run.phase = "training " + arm + " " + str(seed)
    banks = library.LoRABanks(arm, seed=seed)
    run.check("trainable parameter budget", sum(p.numel() for p in banks.parameters()) == banks.expected_count()
              == (6144 if arm == "shared" else 196608))
    optimizer = torch.optim.AdamW(banks.parameters(), lr=0.001, betas=(0.9, 0.999), eps=1e-8,
                                 weight_decay=0.0, foreach=False)
    run.check("optimizer only LoRA", {id(p) for g in optimizer.param_groups for p in g["params"]}
              == {id(p) for p in banks.parameters()} and not any(p.requires_grad for p in run.model.parameters()))
    before = library.state_hashes(banks)
    before_banks = per_bank_hashes(library, banks)
    coverage = {"A": [[False] * banks.banks for _ in range(2)], "B": [[False] * banks.banks for _ in range(2)]}
    for step in range(32):
        article = step % 16
        sample = data["train"][article]
        ids, target = ids_targets(torch, sample)
        optimizer.zero_grad(set_to_none=True)
        started = time.perf_counter()
        logits, observed = run.call(runner, ids, training_h0_seed(seed, step), banks, training=True)
        if arm == "shared":
            paired_training[(seed, step)] = observed
        else:
            run.check("training paired initial state", observed == paired_training[(seed, step)])
        loss = torch.nn.functional.cross_entropy(logits.reshape(-1, 32768), target)
        run.check("finite training loss", library.finite(loss), float(loss.detach()))
        loss.backward()
        current = banks.coverage(gradients=True)
        if step == 0:
            run.check("zero-B first A gradient", not any(any(row) for row in current["A"]))
        for label in coverage:
            for block in range(2):
                for bank in range(banks.banks):
                    coverage[label][block][bank] |= current[label][block][bank]
        norm = torch.nn.utils.clip_grad_norm_(banks.parameters(), 1.0, error_if_nonfinite=True, foreach=False)
        run.check("base gradients absent", all(p.grad is None for p in run.model.parameters()))
        optimizer.step()
        run.actual["train_steps"] += 1
        run.check("finite updated adapters", all(library.finite(p) for p in banks.parameters()))
        record = {"arm": arm, "train_seed": seed, "step": step, "epoch": step // 16,
            "article_id": sample["id"], "h0_seed": training_h0_seed(seed, step), "observer": observed,
            "loss": float(loss.detach()), "gradient_norm_before_clip": float(norm), "nonzero_gradient_banks": current,
            "seconds": time.perf_counter() - started, "optimizer_step": step + 1, "targets": 128}
        run.train_log.write(json.dumps(record, allow_nan=False) + "\n")
        print(json.dumps({"phase": "train", "arm": arm, "seed": seed, "step": step + 1, "loss": record["loss"]}), flush=True)
        del logits, loss, norm
    optimizer.zero_grad(set_to_none=True)
    run.check("every B bank gradient path active", all(all(row) for row in coverage["B"]), coverage)
    run.check("every A bank later gradient path active", all(all(row) for row in coverage["A"]), coverage)
    run.check("every B bank updated from zero", all(all(row) for row in banks.coverage()["B"]))
    run.check("adapter weights changed", library.state_hashes(banks) != before)
    after_banks = per_bank_hashes(library, banks)
    bank_changes = {label: [[a != b for a, b in zip(old, new)]
                           for old, new in zip(before_banks[label], after_banks[label])]
                    for label in before_banks}
    run.check("every A/B bank changed from initial bytes", all(all(all(row) for row in groups) for groups in bank_changes.values()), bank_changes)
    run.check("finite complete32step AdamW optimizer state", optimizer_state_valid(torch, optimizer.state_dict()))
    filename = "private/adapter_%s_%d.pt" % (arm, seed)
    checkpoint = {"arm": arm, "train_seed": seed, "freeze_commit": run.spec["freeze_commit"],
        "inputs_sha256": run.spec["inputs_sha256"], "steps": 32, "state_dict": banks.state_dict(),
        "optimizer": optimizer.state_dict(), "rng_state": torch.get_rng_state(), "rank": 2, "alpha": 2}
    with (run.out / filename).open("xb") as f:
        torch.save(checkpoint, f)
    row = {"arm": arm, "train_seed": seed, "path": filename, **info(run.out / filename),
           "steps": 32, "trainable_parameters": banks.expected_count(), "gradient_coverage": coverage,
           "bank_parameter_changes": bank_changes, "bank_hashes_before": before_banks, "bank_hashes_after": after_banks,
           "state": library.state_hashes(banks)}
    run.adapter_rows.append(row)
    run.actual["adapters_saved"] += 1
    del optimizer, checkpoint
    gc.collect()
    return banks


def main_experiment(run, torch, library, runner, data):
    run.phase = "zero controls"
    ids, _ = ids_targets(torch, data["train"][0])
    reference, reference_observer = run.call(runner, ids, 6101)
    run.actual["zero_control_calls"] += 1
    for seed in TRAIN_SEEDS:
        for arm in ARMS:
            banks = library.LoRABanks(arm, seed=seed)
            candidate, observed = run.call(runner, ids, 6101, banks)
            run.actual["zero_control_calls"] += 1
            run.check("zero LoRA exact native logits/h0/RNG", library.raw(candidate) == library.raw(reference)
                      and observed == reference_observer, {"arm": arm, "train_seed": seed})
            del candidate, banks
    del reference
    references, paired_training = {}, {}
    evaluate(run, torch, library, runner, data, None, "fixed32", None, references)
    for seed in TRAIN_SEEDS:
        for arm in ARMS:
            banks = train_adapter(run, torch, library, runner, data, arm, seed, paired_training)
            evaluate(run, torch, library, runner, data, banks, arm, seed, references)
            del banks
            gc.collect()
    expected = dict(calls_started=293, calls_completed=293, train_steps=128, eval_rows=160,
                    zero_control_calls=5, model_loads=1, adapters_saved=4, reload_calls=0)
    run.check("complete frozen main budget", run.actual == expected, run.actual, expected)


def reload_experiment(run, torch, library, runner, data):
    original = Path(run.spec["output"]).resolve()
    run.check("fresh reload distinct directory", original != run.out and not run.out.is_relative_to(original))
    prior = load(original / "public/completion.json")
    run.check("completed main worker required", prior["Status"] == "PASS")
    adapters = load(original / "public/adapters.json")["rows"]
    evaluations = load(original / "public/evaluation.json")["rows"]
    run.check("exact four adapters", [(x["train_seed"], x["arm"]) for x in adapters]
              == [(s, a) for s in TRAIN_SEEDS for a in ARMS])
    for row in adapters:
        run.phase = "reload " + row["arm"] + " " + str(row["train_seed"])
        path = (original / row["path"]).resolve()
        run.check("sealed adapter bytes", path.is_relative_to(original) and info(path) == {"bytes": row["bytes"], "sha256": row["sha256"]})
        checkpoint = torch.load(path, map_location="cpu", weights_only=True)
        run.check("finite saved adapter/optimizer state", finite_tree(torch, checkpoint))
        run.check("saved optimizer complete32steps", optimizer_state_valid(torch, checkpoint["optimizer"]))
        run.check("checkpoint metadata bound", checkpoint["arm"] == row["arm"] and checkpoint["train_seed"] == row["train_seed"]
                  and checkpoint["steps"] == 32 and checkpoint["rank"] == 2 and checkpoint["alpha"] == 2
                  and checkpoint["freeze_commit"] == run.spec["freeze_commit"] and checkpoint["inputs_sha256"] == run.spec["inputs_sha256"])
        banks = library.LoRABanks(row["arm"], seed=row["train_seed"])
        banks.load_state_dict(checkpoint["state_dict"], strict=True)
        run.check("adapter tensor hash equality", library.state_hashes(banks) == row["state"])
        target_rows = [x for x in evaluations if x["arm"] == row["arm"] and x["train_seed"] == row["train_seed"]
                       and x["article_index"] == 0 and x["eval_seed"] == EVAL_SEEDS[0]]
        run.check("unique frozen reload reference", len(target_rows) == 1)
        reference = target_rows[0]
        reference_path = (original / reference["logits_file"]).resolve()
        run.check("reference contained/sealed", reference_path.is_relative_to(original)
                  and info(reference_path)["sha256"] == reference["logits_sha256"])
        ids, targets = ids_targets(torch, data["eval"][0])
        logits, observed = run.call(runner, ids, EVAL_SEEDS[0], banks)
        run.actual["reload_calls"] += 1
        run.check("new-process exact logits and h0/RNG", library.raw(logits[0, 64:]) == reference_path.read_bytes()
                  and observed == reference["observer"])
        run.reload_rows.append({"arm": row["arm"], "train_seed": row["train_seed"], "Status": "PASS",
            "logits_sha256": reference["logits_sha256"], "observer": observed, **library.score(logits, targets)})
        del banks, checkpoint, logits
    expected = dict(calls_started=4, calls_completed=4, train_steps=0, eval_rows=0,
                    zero_control_calls=0, model_loads=1, adapters_saved=0, reload_calls=4)
    run.check("complete frozen reload budget", run.actual == expected, run.actual, expected)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()
    if not args.spec.is_absolute() or not args.out.is_absolute():
        parser.error("absolute spec/out required")
    spec = load(args.spec)
    out = args.out.resolve()
    protected = [Path(spec[k]).resolve() for k in ("repo", "upstream", "model_dir")]
    if any(out == p or out.is_relative_to(p) for p in protected):
        parser.error("evidence must be outside protected trees")
    out.mkdir(parents=True, exist_ok=False)
    run = Run(spec, out, args.reload)
    status, error, preservation = "NOT TESTED", None, "NOT TESTED"
    def interrupted(signum, frame):
        raise Stop("BLOCKED", "worker interrupted by signal " + str(signum))
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        torch, library, runner, data = initialize(run)
        if args.reload:
            reload_experiment(run, torch, library, runner, data)
        else:
            main_experiment(run, torch, library, runner, data)
        status = "PASS"
    except BaseException as exc:
        status = getattr(exc, "status", "BLOCKED" if isinstance(exc, (MemoryError, OSError, KeyboardInterrupt)) else "FAIL")
        error = {"type": type(exc).__name__, "reason": str(exc), "traceback": traceback.format_exc()}
    finally:
        if run.model is not None and run.before is not None:
            try:
                after = run.library.state_hashes(run.model)
                save(run.public / "base_state_after.json", after)
                okay = after == run.before and all(p.grad is None and not p.requires_grad for p in run.model.parameters())
                okay = okay and all(run.library.finite(x) for x in run.model.state_dict().values())
                okay = okay and not any(m._forward_hooks or m._forward_pre_hooks for m in run.model.modules())
                run.check("base state/gradient/hooks preserved", okay)
                preservation = "PASS"
            except BaseException as exc:
                preservation = getattr(exc, "status", "BLOCKED")
                if status == "PASS" or preservation == "FAIL":
                    status = preservation
                error = {"primary": error, "preservation": repr(exc)}
        save(run.public / "evaluation.json", {"Status": status, "rows": run.evaluations, "scored_positions": [64, 128]})
        save(run.public / "adapters.json", {"Status": status, "rows": run.adapter_rows})
        save(run.public / "reload.json", {"Status": status, "rows": run.reload_rows})
        run.journal.close()
        run.train_log.close()
        completion = {"Purpose": "CPU fixed32 depth-specific LoRA versus native/shared controls" if not args.reload else "Fresh-process adapter reload identity",
            "Environment": run.environment, "Input": spec, "Expected": "All frozen engineering controls pass; scientific screens separately audited",
            "Actual": run.actual, "Status": status, "checks": run.checks, "error": error, "preservation": preservation,
            "seconds": time.perf_counter() - run.started, "utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
        save(run.public / "completion.json", completion)
        print(json.dumps(completion, allow_nan=False), flush=True)
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
