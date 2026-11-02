"""One frozen CPU MoDA residual training/evaluation worker and fresh reload check.

No work at import time. Large logits/adapters remain under private/. The operator
owns upstream/input pins, resource gates, custody and repository publication.
"""
from __future__ import annotations
import argparse
import datetime
import gc
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import stat
import struct
import subprocess
import sys
import time
import traceback

SPACE = "bookish-pancake-vwqx7rr9x5w3wxjr"
PYTHON = "/workspaces/mythos-base-v01-cpu312/bin/python"
DATA_PYTHON = "/workspaces/mythos-depth-data-cpu312/bin/python"
UPSTREAM = "69284c13746e849104f738d6d1a347b1f457df76"
WEIGHTS = "ed6eb306464dd0d694e9eacd58f7e06ac3e44b43cb7c5c79dbcb1543059c6621"
CONFIG = "5c8fc785c2f6dba67d0370ad715034860e3b22bfce850da825c06baa03923c13"
TRAIN_SEEDS, EVAL_SEEDS, ARMS = (4101, 4202), (5101, 5202), ("shared", "depth")
ENV = {"OMP_NUM_THREADS": "2", "MKL_NUM_THREADS": "2", "OPENBLAS_NUM_THREADS": "1",
       "RAYON_NUM_THREADS": "1", "TOKENIZERS_PARALLELISM": "false", "CUDA_VISIBLE_DEVICES": "",
       "PYTHONDONTWRITEBYTECODE": "1", "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"}
BUDGET_ROOT = None
BUDGET_SALVAGE = False
BUDGET_TRIGGER = None
RAW_BUDGET, METADATA_BUDGET, DISK_RESERVE = 40 * 1024**2, 32 * 1024**2, 256 * 1024**2


class Stop(Exception):
    def __init__(self, status, reason):
        super().__init__(reason)
        self.status = status


def raw_budget_path(path, root):
    relative = Path(path).relative_to(root)
    return (len(relative.parts) == 3 and relative.parts[:2] == ("worker", "private")
            and re.fullmatch(r"(?:pending|sentinel)_row_[0-9]{3}\.bin", relative.name) is not None)


def budget_guard(path=None, additional_bytes=0):
    """Reserve the entire remaining frozen allocation, not only the next file."""
    global BUDGET_TRIGGER
    if BUDGET_ROOT is None:
        return None
    root = Path(BUDGET_ROOT).resolve()
    if type(additional_bytes) is not int or additional_bytes < 0:
        raise Stop("FAIL", "invalid planned evidence byte count")
    if path is not None:
        target = Path(path).resolve()
        if not target.is_relative_to(root):
            raise Stop("FAIL", "budgeted write escapes current attempt")
        is_raw = raw_budget_path(target, root)
    else:
        is_raw = False
    total, raw = 0, 0
    for entry in root.rglob("*"):
        if entry.is_file():
            size = entry.stat().st_size
            total += size
            if raw_budget_path(entry, root):
                raw += size
    metadata = total - raw
    remaining = max(0, RAW_BUDGET + METADATA_BUDGET - total)
    free = shutil.disk_usage(root).free
    required = additional_bytes if BUDGET_SALVAGE else remaining + DISK_RESERVE
    snapshot = {"total_bytes": total, "raw_bytes": raw, "metadata_bytes": metadata,
        "remaining_allocation_bytes": remaining, "free_bytes": free, "required_free_bytes": required,
        "next_bytes": additional_bytes, "next_path": str(path) if path is not None else None,
        "raw_budget_bytes": RAW_BUDGET, "metadata_budget_bytes": METADATA_BUDGET,
        "reserve_bytes": DISK_RESERVE, "salvage": BUDGET_SALVAGE}
    okay = (raw + (additional_bytes if is_raw else 0) <= RAW_BUDGET
            and metadata + (0 if is_raw else additional_bytes) <= METADATA_BUDGET
            and free >= required and (not BUDGET_SALVAGE or not is_raw))
    if not okay:
        if BUDGET_TRIGGER is None:
            BUDGET_TRIGGER = snapshot
        raise Stop("BLOCKED", "frozen remaining disk budget/reserve unavailable")
    return snapshot


def append_record(stream, value):
    text = json.dumps(value, allow_nan=False) + "\n"
    budget_guard(Path(stream.name), len(text.encode("utf-8")))
    stream.write(text)


def peak_rss_bytes():
    if platform.system() != "Linux":
        return None
    import resource
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024


def info(path):
    h, n = hashlib.sha256(), 0
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(1048576), b""):
            h.update(b)
            n += len(b)
    return {"bytes": n, "sha256": h.hexdigest()}


def save(path, value):
    encoded = (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    budget_guard(path, len(encoded))
    with Path(path).open("xb") as f:
        f.write(encoded)


def save_raw_logits(path, raw):
    """Reserve256MiB even if another process consumes disk during this run."""
    path = Path(path)
    budget_guard(path, len(raw))
    if shutil.disk_usage(path.parent).free < len(raw) + 256 * 1024 ** 2:
        raise Stop("BLOCKED", "insufficient disk for next logits plus frozen256MiB reserve")
    with path.open("xb") as stream:
        stream.write(raw)


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def discard_audited_pending(out, raw_path, row_number, raw_pin, row_input_path, receipt_path, receipt_sha256, identity):
    """Delete only one newly created, independently accepted8MiB pending file."""
    out, raw_path = Path(out).resolve(), Path(raw_path)
    private = out / "private"
    if type(row_number) is not int or not 0 <= row_number < 160:
        raise Stop("FAIL", "invalid temporary row number")
    expected = private / ("pending_row_%03d.bin" % row_number)
    expected_row = out / "public/rows" / ("row_%03d.json" % row_number)
    expected_receipt = out / "public/row_audits" / ("row_%03d.json" % row_number)
    if (not raw_path.is_absolute() or raw_path != expected or raw_path.is_symlink()
            or private.is_symlink() or raw_path.resolve() != expected
            or Path(row_input_path) != expected_row or Path(receipt_path) != expected_receipt
            or expected_row.is_symlink() or expected_receipt.is_symlink()
            or not stat.S_ISREG(raw_path.lstat().st_mode)):
        raise Stop("FAIL", "refuse non-owned/nonregular/symlink temporary removal")
    if raw_pin.get("bytes") != 8388608 or info(expected_receipt)["sha256"] != receipt_sha256:
        raise Stop("FAIL", "temporary receipt/payload binding differs")
    receipt, row = load(expected_receipt), load(expected_row)
    if (receipt.get("Status") != "PASS" or receipt.get("Input", {}).get("identity") != identity
            or receipt.get("Input", {}).get("row_input") != info(expected_row)
            or receipt.get("Actual", {}).get("raw") != raw_pin
            or row.get("raw_path") != str(expected) or row.get("logits_sha256") != raw_pin["sha256"]
            or row.get("retention") not in ("historical_bridge", "audited_then_discarded")):
        raise Stop("FAIL", "temporary lacks a bound independent PASS receipt")
    actual = info(expected)
    if actual != raw_pin or info(expected_receipt)["sha256"] != receipt_sha256:
        raise Stop("FAIL", "temporary or receipt changed after independent audit")
    expected.unlink()
    return actual


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


def history_gradient_record(library, runner):
    record = {}
    for name, tensors in (("key", runner.depth_keys), ("value", runner.depth_values)):
        if len(tensors) != 32:
            raise RuntimeError("incomplete history tensor observations")
        present, norms = [], []
        for tensor in tensors:
            gradient = tensor.grad
            present.append(gradient is not None)
            if gradient is None:
                norms.append(None)
            else:
                if not library.finite(gradient):
                    raise RuntimeError("nonfinite history gradient")
                norms.append(float(gradient.detach().double().norm()))
        record[name] = {"present": present, "norms": norms}
    return record


def optimizer_state_valid(torch, state, steps=32):
    if not finite_tree(torch, state) or len(state.get("state", {})) != 1:
        return False
    groups = state.get("param_groups", [])
    if len(groups) != 1 or len(groups[0].get("params", [])) != 1:
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
        self.retention_log = (self.public / "retention.jsonl").open("x", encoding="utf-8", buffering=1)
        (self.public / "rows").mkdir()
        (self.public / "row_audits").mkdir()
        self.environment = {"planned": "CPUFP32 native fixed32 fullBPTT; base frozen"}
        self.checks = {"PASS": 0, "FAIL": 0, "BLOCKED": 0}
        self.actual = dict(calls_started=0, calls_completed=0, train_steps=0, eval_rows=0,
                           zero_control_calls=0, model_loads=0, adapters_saved=0, reload_calls=0)
        self.model = self.library = None
        self.before = None
        self.evaluations, self.adapter_rows, self.reload_rows = [], [], []
        self.phase = "preflight"
        self.started = time.perf_counter()
        self.peak_rss_at_start_bytes = peak_rss_bytes()

    def check(self, purpose, okay, actual=None, expected=True, failure="FAIL"):
        status = "PASS" if okay else failure
        self.checks[status] += 1
        append_record(self.journal, {"Purpose": purpose, "Environment": self.environment,
            "Input": {"freeze_commit": self.spec["freeze_commit"], "phase": self.phase},
            "Expected": expected, "Actual": actual, "Status": status})
        if not okay:
            raise Stop(failure, purpose)

    def call(self, runner, ids, seed, banks=None, training=False):
        if BUDGET_SALVAGE:
            raise Stop("BLOCKED", "model calls forbidden after entering evidence salvage")
        budget_guard()
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
    library_path = Path(__file__).with_name("moda_model.py")
    module_spec = importlib.util.spec_from_file_location("frozen_moda_residual_model", library_path)
    library = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(library)
    run.library = library
    run.check("pinned MoDA source location", Path(spec["moda_source"]).resolve() == repo / "open_mythos/moda.py"
              and spec["moda_source_sha256"] == library.SOURCE_SHA256)
    run.source = library.load_source(spec["moda_source"])
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
            row_started = time.perf_counter()
            forward_started = time.perf_counter()
            logits, observed = run.call(runner, ids, seed, banks)
            forward_seconds = time.perf_counter() - forward_started
            key = (index, seed)
            if arm == "fixed32":
                references[key] = observed
            else:
                run.check("paired actual h0 and native RNG", observed == references[key], observed, references[key])
            values = logits[0, 64:].detach().contiguous()
            run.check("evaluation exact scored shape", tuple(values.shape) == (64, 32768), list(values.shape))
            raw = library.raw(values)
            number = run.actual["eval_rows"]
            sentinel = arm != "fixed32" and index == 0 and seed == EVAL_SEEDS[0]
            filename = "private/%s_row_%03d.bin" % ("sentinel" if sentinel else "pending", number)
            raw_path = run.out / filename
            run.check("new raw path confined before write", raw_path.parent == run.private.resolve()
                      and not raw_path.is_symlink())
            save_raw_logits(raw_path, raw)
            metrics = library.score(logits, targets)
            columns = values.double()
            peak = columns.max(-1).values
            gold = columns.gather(1, targets[64:, None]).squeeze(1)
            token_nll = (peak - gold) + torch.exp(columns - peak[:, None]).sum(-1).log()
            identity = {"arm": arm, "train_seed": train_seed, "eval_seed": seed, "article_id": sample["id"], "article_index": index}
            row_input_file = "public/rows/row_%03d.json" % number
            row_audit_file = "public/row_audits/row_%03d.json" % number
            retention = "sentinel" if sentinel else ("historical_bridge" if arm == "fixed32" else "audited_then_discarded")
            row = {**identity, "raw_path": str(raw_path), "logits_file": filename if sentinel else None,
                "logits_sha256": hashlib.sha256(raw).hexdigest(), "shape": [64, 32768], "dtype": "float32-le",
                "h0_sha256": observed["h0_sha256"], "targets_sha256": hashlib.sha256(struct.pack("<64q", *sample["tokens"][65:129])).hexdigest(),
                "observer": observed, "branch_trace": runner.last_branch, **metrics,
                "forward_seconds": forward_seconds,
                "worker_per_token": {"nll": token_nll.tolist(), "predictions": columns.argmax(-1).tolist()},
                "row_input_file": row_input_file, "row_audit_file": row_audit_file, "retention": retention}
            save(run.out / row_input_file, row)
            receipt_path = run.out / row_audit_file
            command = [DATA_PYTHON, "-I", "-B", str(Path(__file__).with_name("audit_row.py")),
                       "--spec", str(run.spec["spec_path"]), "--row", str(run.out / row_input_file), "--output", str(receipt_path)]
            audit_started = time.perf_counter()
            completed = subprocess.run(command, capture_output=True, text=True, timeout=60)
            audit_seconds = time.perf_counter() - audit_started
            save(run.public / "row_audits" / ("process_%03d.json" % number),
                 {"command": command, "returncode": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr})
            receipt = load(receipt_path) if receipt_path.is_file() else {}
            run.check("independent row audit PASS", completed.returncode == 0 and receipt.get("Status") == "PASS",
                      {"returncode": completed.returncode, "receipt_status": receipt.get("Status")},
                      failure="BLOCKED" if receipt.get("Status") == "BLOCKED" else "FAIL")
            run.check("formal independent audit environment", receipt.get("Environment", {}).get("development_only") is False)
            raw_pin = {"bytes": len(raw), "sha256": row["logits_sha256"]}
            run.check("row audit bound to exact raw and identity", receipt["Actual"]["raw"] == raw_pin
                      and receipt["Input"]["identity"] == identity
                      and receipt["Input"]["row_input"] == info(run.out / row_input_file)
                      and receipt["Input"]["spec_sha256"] == info(run.spec["spec_path"])["sha256"])
            after_pin = info(raw_path)
            run.check("raw bytes unchanged after audit", after_pin == raw_pin)
            if sentinel:
                retained_path = str(raw_path)
            elif arm == "fixed32":
                retained_path = receipt["Actual"]["baseline_reference"]["path"]
            else:
                retained_path = None
            if not sentinel:
                # Only this run's exact, uniquely named pending row can be
                # removed, after independent acceptance and a second hash.
                after_pin = discard_audited_pending(run.out, raw_path, number, raw_pin,
                    run.out / row_input_file, receipt_path, info(receipt_path)["sha256"], identity)
            ledger = {"identity": identity, "raw_path": str(raw_path), "raw_sha256": row["logits_sha256"],
                "row_input_file": row_input_file, "row_audit_file": row_audit_file,
                "audit_sha256": info(receipt_path)["sha256"], "action": retention,
                "raw_after_audit": after_pin, "retained_path": retained_path, "raw_exists_after": raw_path.exists()}
            ledger.update(audit_process_seconds=audit_seconds, full_row_seconds=time.perf_counter() - row_started)
            append_record(run.retention_log, ledger)
            run.evaluations.append(row)
            run.actual["eval_rows"] += 1
            print(json.dumps({"phase": "eval", "arm": arm, "train_seed": train_seed, "row": run.actual["eval_rows"]}), flush=True)
            del logits, values, raw, columns, token_nll


def train_adapter(run, torch, library, runner, data, arm, seed, paired_training):
    run.phase = "training " + arm + " " + str(seed)
    banks = library.MoDAResidual(arm, run.source, seed=seed)
    trainables = banks.trainable_parameters()
    run.check("matched trainable parameter budget", sum(p.numel() for p in trainables) == banks.expected_count() == 12288
              and sum(p.numel() for p in banks.parameters()) == 73728)
    run.check("only output projection trainable", {id(p) for p in banks.parameters() if p.requires_grad} == {id(p) for p in trainables})
    optimizer = torch.optim.AdamW(trainables, lr=.001, betas=(.9, .999), eps=1e-8, weight_decay=0., foreach=False)
    run.check("optimizer only MoDA output", {id(p) for g in optimizer.param_groups for p in g["params"]} == {id(p) for p in trainables})
    features_before = banks.feature_hashes()
    if arm == "shared":
        paired_training[("features", seed)] = features_before
    else:
        run.check("paired identical frozen reader/writer features", features_before == paired_training[("features", seed)])
    run.check("output projection initially zero", int(torch.count_nonzero(banks.attn.o_proj.weight)) == 0)
    initial_output = library.digest(banks.attn.o_proj.weight)
    coverage, depth_coverage = False, [False] * 32
    history_active = {"key": False, "value": False}
    for step in range(32):
        sample = data["train"][step % 16]
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
        projection = banks.attn.o_proj.weight
        run.check("output gradient finite present", projection.grad is not None and library.finite(projection.grad))
        current = bool(projection.grad.abs().max() > 0)
        coverage |= current
        contributions = library.depth_output_contributions(banks, runner.depth_deltas, runner.depth_features)
        run.check("all32 output gradient contributions finite", all(library.finite(x) for x in contributions))
        current_depth = [bool(x.abs().max() > 0) for x in contributions]
        depth_norms = [float(x.detach().double().norm()) for x in contributions]
        depth_coverage = [a or b for a, b in zip(depth_coverage, current_depth)]
        history = history_gradient_record(library, runner)
        for kind in ("key", "value"):
            present, norms = history[kind]["present"], history[kind]["norms"]
            if arm == "shared":
                run.check("shared history writes unused " + kind, not any(present))
            else:
                run.check("only past31 history writes consumed " + kind, all(present[:31]) and not present[31])
                if step == 0:
                    run.check("zero-output initial history gradient " + kind, all(value == 0 for value in norms[:31]))
                history_active[kind] |= any(value is not None and value > 0 for value in norms)
        norm = torch.nn.utils.clip_grad_norm_(trainables, 1., error_if_nonfinite=True, foreach=False)
        run.check("positive finite output gradient each step", library.finite(norm) and float(norm) > 0, float(norm))
        run.check("base and frozen feature gradients absent", all(p.grad is None for p in run.model.parameters())
                  and all(p.grad is None for p in banks.parameters() if not p.requires_grad))
        before_step = projection.detach().clone()
        optimizer.step()
        run.actual["train_steps"] += 1
        change = projection.detach() - before_step
        update_norm = float(change.double().norm())
        run.check("positive finite output update each step", library.finite(projection) and library.finite(change) and update_norm > 0,
                  update_norm)
        record = {"arm": arm, "train_seed": seed, "step": step, "epoch": step // 16, "article_id": sample["id"],
            "h0_seed": training_h0_seed(seed, step), "observer": observed, "branch_trace": runner.last_branch,
            "loss": float(loss.detach()), "gradient_norm_before_clip": float(norm), "nonzero_o_proj_gradient": current,
            "seconds": time.perf_counter() - started, "optimizer_step": step + 1, "targets": 128,
            "depth_gradient_coverage": current_depth, "depth_o_proj_gradient_norms": depth_norms,
            "output_update_norm": update_norm, "history_gradients": history}
        append_record(run.train_log, record)
        print(json.dumps({"phase": "train", "arm": arm, "seed": seed, "step": step + 1, "loss": record["loss"]}), flush=True)
        del logits, loss, norm, contributions
    optimizer.zero_grad(set_to_none=True)
    run.check("output vector gradient path active", coverage)
    run.check("all32 output projection paths active", all(depth_coverage), depth_coverage)
    run.check("expected history gradient activity", all(history_active.values()) if arm == "depth" else not any(history_active.values()), history_active)
    features_after = banks.feature_hashes()
    run.check("all frozen features unchanged", features_after == features_before)
    output_changed = library.digest(banks.attn.o_proj.weight) != initial_output
    run.check("output projection changed from zero", output_changed)
    run.check("finite complete32step AdamW state", optimizer_state_valid(torch, optimizer.state_dict()))
    filename = "private/adapter_%s_%d.pt" % (arm, seed)
    checkpoint = {"arm": arm, "train_seed": seed, "freeze_commit": run.spec["freeze_commit"],
        "inputs_sha256": run.spec["inputs_sha256"], "steps": 32, "state_dict": banks.state_dict(),
        "optimizer": optimizer.state_dict(), "rng_state": torch.get_rng_state(), "head_dim": 16,
        "rope_theta": 10000., "source_sha256": library.SOURCE_SHA256}
    checkpoint_stream = io.BytesIO()
    torch.save(checkpoint, checkpoint_stream)
    checkpoint_bytes = checkpoint_stream.getvalue()
    run.check("adapter serialization within1MiB allocation", len(checkpoint_bytes) <= 1024**2, len(checkpoint_bytes), failure="BLOCKED")
    budget_guard(run.out / filename, len(checkpoint_bytes))
    with (run.out / filename).open("xb") as stream:
        stream.write(checkpoint_bytes)
    row = {"arm": arm, "train_seed": seed, "path": filename, **info(run.out / filename), "steps": 32,
        "trainable_parameters": banks.expected_count(), "gradient_coverage": coverage,
        "depth_gradient_coverage": depth_coverage, "history_gradient_active": history_active,
        "parameter_changes": {"o_proj": output_changed}, "features_before": features_before, "features_after": features_after,
        "state": library.state_hashes(banks)}
    run.adapter_rows.append(row)
    run.actual["adapters_saved"] += 1
    del optimizer, checkpoint, checkpoint_bytes, checkpoint_stream
    gc.collect()
    return banks


def main_experiment(run, torch, library, runner, data):
    run.phase = "zero controls"
    ids, _ = ids_targets(torch, data["train"][0])
    reference, reference_observer = run.call(runner, ids, 6101)
    run.actual["zero_control_calls"] += 1
    for seed in TRAIN_SEEDS:
        for arm in ARMS:
            banks = library.MoDAResidual(arm, run.source, seed=seed)
            candidate, observed = run.call(runner, ids, 6101, banks)
            run.actual["zero_control_calls"] += 1
            run.check("zero MoDA output exact native logits/h0/RNG", library.raw(candidate) == library.raw(reference)
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
                  and checkpoint["steps"] == 32 and checkpoint["head_dim"] == 16 and checkpoint["rope_theta"] == 10000.0
                  and checkpoint["source_sha256"] == library.SOURCE_SHA256
                  and checkpoint["freeze_commit"] == run.spec["freeze_commit"] and checkpoint["inputs_sha256"] == run.spec["inputs_sha256"])
        banks = library.MoDAResidual(row["arm"], run.source, seed=row["train_seed"])
        run.check("regenerated immutable features exact", banks.feature_hashes() == row["features_before"])
        banks.load_state_dict(checkpoint["state_dict"], strict=True)
        run.check("reloaded immutable features exact", banks.feature_hashes() == row["features_after"])
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
    global BUDGET_ROOT, BUDGET_SALVAGE
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()
    if not args.spec.is_absolute() or not args.out.is_absolute():
        parser.error("absolute spec/out required")
    spec = load(args.spec)
    spec["spec_path"] = str(args.spec.resolve())
    out = args.out.resolve()
    protected = [Path(spec[k]).resolve() for k in ("repo", "upstream", "model_dir")]
    if any(out == p or out.is_relative_to(p) for p in protected):
        parser.error("evidence must be outside protected trees")
    out.mkdir(parents=True, exist_ok=False)
    BUDGET_ROOT = Path(spec["output"]).resolve().parent
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
        status = getattr(exc, "status", "BLOCKED" if isinstance(exc, (MemoryError, OSError, KeyboardInterrupt, subprocess.TimeoutExpired)) else "FAIL")
        error = {"type": type(exc).__name__, "reason": str(exc), "traceback": traceback.format_exc()}
    finally:
        # Once stopped, only bounded custody/error/result metadata is allowed.
        # This does not admit another model call or experimental raw write.
        BUDGET_SALVAGE = status != "PASS"
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
        BUDGET_SALVAGE = status != "PASS"
        save(run.public / "evaluation.json", {"Status": status, "rows": run.evaluations, "scored_positions": [64, 128]})
        save(run.public / "adapters.json", {"Status": status, "rows": run.adapter_rows})
        save(run.public / "reload.json", {"Status": status, "rows": run.reload_rows})
        run.journal.close()
        run.train_log.close()
        run.retention_log.close()
        completion = {"Purpose": "CPU fixed32 MoDA residual history reader versus native/sequence-only controls" if not args.reload else "Fresh-process adapter reload identity",
            "Environment": run.environment, "Input": spec, "Expected": "All frozen engineering controls pass; scientific screens separately audited",
            "Actual": run.actual, "Status": status, "checks": run.checks, "error": error, "preservation": preservation,
            "seconds": time.perf_counter() - run.started, "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "peak_rss_bytes": peak_rss_bytes(), "peak_rss_at_start_bytes": run.peak_rss_at_start_bytes,
            "peak_rss_semantics": "Linux process-lifetime ru_maxrss KiB*1024, includes loading and all work, not per-arm memory",
            "budget_trigger": BUDGET_TRIGGER, "budget_salvage_mode": BUDGET_SALVAGE}
        save(run.public / "completion.json", completion)
        print(json.dumps(completion, allow_nan=False), flush=True)
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
