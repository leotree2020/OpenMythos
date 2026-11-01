"""One frozen CPU checkpoint restoration check. Standard-library imports only."""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import subprocess
import sys
import traceback

SPACE = "bookish-pancake-vwqx7rr9x5w3wxjr"
REPO = Path("/workspaces/mythos-base-v01-rope-diag-v11")
REL = Path("research/mini_mythos/base_v01/load_integrity_v1")
BRANCH = "mythos-base-v01-cpu-load-v1"
BASE = "a20ec43914f8e7bb5a7c17dedd27f1acf2a95ec3"
UPSTREAM = Path("/workspaces/mythos-parcae-pinned")
UPSTREAM_SHA = "69284c13746e849104f738d6d1a347b1f457df76"
B1_REPO = Path("/workspaces/mythos-base-v01-b1")
B1_SHA = "d88be474ebb2529c5b095e3732b1f25509f9b824"
B1_RUN = Path("/workspaces/mythos-evidence/base_v01/b1/b1-20261101T021657Z")
ROPE_RUN = Path("/workspaces/mythos-evidence/base_v01/rope_diag/rope-v11-20261101T051150Z")
VENV = Path("/workspaces/mythos-base-v01-cpu312")
EVIDENCE_ROOT = Path("/workspaces/mythos-evidence/base_v01/load_integrity")
MODEL_DIR = B1_RUN / "downloads/model"
FROZEN_FILES = ("run_load_check.py", "state_checks.py", "PROTOCOL.md", "README_USAGE.md")
INPUTS = {
    "downloads/model/pytorch_model.bin": (578361537, "ed6eb306464dd0d694e9eacd58f7e06ac3e44b43cb7c5c79dbcb1543059c6621"),
    "downloads/model/config.json": (1741, "5c8fc785c2f6dba67d0370ad715034860e3b22bfce850da825c06baa03923c13"),
    "env_check.json": (7825, "55373ba603a91745dcabdaa3e09e24bc916d2b7f3f2cd9251ef88b3006c977cd"),
    "manifest.json": (1372, "2ac1ca86c540f3b044304b3abf3951dcbf4d8adf9499056959293cbf315cf962"),
}
RUNTIME_ENV = {
    "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
    "RAYON_NUM_THREADS": "1", "TOKENIZERS_PARALLELISM": "false", "CUDA_VISIBLE_DEVICES": "",
    "PYTHONDONTWRITEBYTECODE": "1", "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
}


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return {"size": Path(path).stat().st_size, "sha256": h.hexdigest()}


def json_bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode()


def save(path, value):
    with Path(path).open("xb") as stream:
        stream.write(json_bytes(value))


def git(repo, *args):
    p = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                       env=dict(os.environ, GIT_OPTIONAL_LOCKS="0"))
    if p.returncode:
        raise RuntimeError(f"Git operation failed: {args}: {p.stdout}{p.stderr}")
    return p.stdout.strip()


def git_state(repo):
    return {"head": git(repo, "rev-parse", "HEAD"), "branch": git(repo, "branch", "--show-current"),
            "status": git(repo, "status", "--porcelain=v1", "--untracked-files=all", "--ignored")}


class Stop(Exception):
    def __init__(self, gate, status, reason):
        self.gate, self.status, self.reason = gate, status, reason
        super().__init__(reason)


class Run:
    def __init__(self, root, implementation):
        self.root, self.implementation = root, implementation
        self.public, self.private = root / "public", root / "private"
        self.public.mkdir(); self.private.mkdir()
        self.gates = {f"L{i}": "NOT TESTED" for i in range(6)}
        self.phase, self.status, self.stop_reason = "L0", "NOT TESTED", None
        self.check_count, self.rows = 0, []
        self.files, self.git_before, self.trees = {}, {}, {}
        self.protection_complete = False
        self.loader_calls = 0
        self.comparison = None
        self.result_counts = None
        self.save_errors = []

    def record(self, gate, status, purpose, expected, actual, inputs=None):
        self.check_count += 1
        record = {"utc": utc(), "gate": gate, "Purpose": purpose,
                  "Environment": {"codespace": SPACE, "python": sys.executable,
                                  "implementation_commit": self.implementation},
                  "Input": inputs if inputs is not None else "Frozen local artifact and official loader",
                  "Expected": expected, "Actual": actual, "Status": status}
        save(self.public / f"check_{self.check_count:03d}.json", record)

    def require(self, condition, status, reason, actual, expected=True):
        self.record(self.phase, "PASS" if condition else status, reason, expected, actual)
        if not condition:
            self.gates[self.phase] = status
            raise Stop(self.phase, status, reason)

    def protect(self, path, expected=None):
        path = Path(path)
        self.require(not path.is_symlink() and path.resolve() == path, "BLOCKED",
                     "Protected input has an unambiguous local path", str(path))
        value = digest(path)
        if expected is not None:
            self.require(value == expected, "BLOCKED", "Frozen file identity", value, expected)
        self.files[str(path)] = value
        return value

    def tensor_row(self, row):
        save(self.public / f"tensor_{len(self.rows) + 1:03d}.json", row)
        self.rows.append(row)


def preflight(run):
    run.require(os.environ.get("CODESPACE_NAME") == SPACE, "BLOCKED", "Target identity",
                os.environ.get("CODESPACE_NAME"), SPACE)
    run.require(sys.executable == str(VENV / "bin/python") and sys.prefix == str(VENV)
                and platform.python_version() == "3.12.3", "BLOCKED", "Frozen interpreter",
                {"executable": sys.executable, "prefix": sys.prefix, "version": platform.python_version()})
    run.require(Path(__file__).resolve() == REPO / REL / "run_load_check.py", "BLOCKED",
                "Frozen runner location", str(Path(__file__).resolve()))
    for repo, expected in ((UPSTREAM, UPSTREAM_SHA), (B1_REPO, B1_SHA), (REPO, None)):
        state = git_state(repo)
        run.require(not state["status"] and (expected is None or state["head"] == expected),
                    "BLOCKED", "Clean protected checkout", {"path": str(repo), **state})
        run.git_before[str(repo)] = state
    run.require(run.git_before[str(REPO)]["branch"] == BRANCH, "BLOCKED", "Isolated check branch",
                run.git_before[str(REPO)]["branch"], BRANCH)
    git(REPO, "merge-base", "--is-ancestor", BASE, run.implementation)
    git(REPO, "merge-base", "--is-ancestor", run.implementation, "HEAD")
    changed = git(REPO, "diff", "--name-only", BASE, "HEAD").splitlines()
    run.require(bool(changed) and all(x.startswith(str(REL) + "/") for x in changed), "BLOCKED",
                "All stage changes isolated from prior research", changed)
    for name in FROZEN_FILES:
        path = REPO / REL / name
        blob = subprocess.check_output(["git", "-C", str(REPO), "show", f"{run.implementation}:{REL / name}"])
        run.require(path.read_bytes() == blob, "BLOCKED", "Frozen implementation bytes", name)
        run.protect(path)
    for name, (size, sha) in INPUTS.items():
        run.protect(B1_RUN / name, {"size": size, "sha256": sha})
    manifest = json.loads((B1_RUN / "manifest.json").read_text())
    for item in manifest["files"]:
        path = (B1_RUN / item["path"]).resolve(); path.relative_to(B1_RUN)
        run.protect(path, {"size": item["size"], "sha256": item["sha256"]})
    run.protect(B1_REPO / "research/mini_mythos/base_v01/requirements.lock",
                {"size": 2881, "sha256": "84440f8945041ed314c29b205c5244e074116ede023d5aae0b11b633b4d6a51e"})
    history = json.loads((B1_RUN / "env_check.json").read_text())
    actual_packages = {re.sub(r"[-_.]+", "-", d.metadata["Name"]).lower(): d.version
                       for d in importlib.metadata.distributions() if d.metadata.get("Name")}
    run.require(actual_packages == history["dependencies"]["distributions"], "BLOCKED",
                "Complete frozen dependency inventory", actual_packages,
                history["dependencies"]["distributions"])
    # All upstream files, all prior B1/RoPE artifacts, and frozen implementation
    # bytes are protected. No old runner is imported or called.
    for name in git(UPSTREAM, "ls-files").splitlines():
        run.protect(UPSTREAM / name)
    for name, sha in history["code_identity"]["file_sha256"].items():
        value = run.protect(B1_REPO / "research/mini_mythos/base_v01" / name)
        run.require(value["sha256"] == sha, "BLOCKED", "Original B1 code identity", value["sha256"], sha)
    run.protect(ROPE_RUN / "FULL_MANIFEST.json", {"size": 42773, "sha256": "1e8c2ac5a35e52ce71a633ffaab8636de0e90eacb3ea6f1323e63d3e01ac04f5"})
    for item in json.loads((ROPE_RUN / "FULL_MANIFEST.json").read_text())["files"]:
        path = (ROPE_RUN / item["path"]).resolve(); path.relative_to(ROPE_RUN)
        run.protect(path, {"size": item["size"], "sha256": item["sha256"]})
    for tree in (B1_RUN, ROPE_RUN):
        members = sorted(str(p.relative_to(tree)) for p in tree.rglob("*") if p.is_file())
        run.trees[str(tree)] = members
        for name in members:
            if str(tree / name) not in run.files:
                run.protect(tree / name)
    resources = {"disk_free": shutil.disk_usage(EVIDENCE_ROOT).free,
                 "meminfo": [s for s in Path("/proc/meminfo").read_text().splitlines()
                             if s.startswith(("MemTotal:", "MemAvailable:"))]}
    available = int(next(x.split()[1] for x in resources["meminfo"] if x.startswith("MemAvailable:"))) * 1024
    run.require(resources["disk_free"] >= 1024 ** 3 and available >= 3 * 1024 ** 3,
                "BLOCKED", "CPU load resource floor", resources,
                "At least 1 GiB free disk and 3 GiB MemAvailable; no weight copy or save")
    save(run.private / "protected_before.json", {"files": run.files, "git": run.git_before, "trees": run.trees})
    run.protection_complete = True


def runtime_state(torch):
    return {"intra_op": torch.get_num_threads(), "inter_op": torch.get_num_interop_threads(),
            "deterministic": torch.are_deterministic_algorithms_enabled(),
            "dtype": str(torch.get_default_dtype()), "device": str(torch.get_default_device()),
            "autocast_cpu": torch.is_autocast_enabled("cpu"), "autocast_cuda": torch.is_autocast_enabled("cuda"),
            "cuda_initialized": torch.cuda.is_initialized(),
            "dont_write_bytecode": sys.dont_write_bytecode,
            "env": {k: os.environ.get(k) for k in RUNTIME_ENV}}


def runtime_ok(s):
    return (s["intra_op"] == s["inter_op"] == 1 and s["deterministic"]
            and s["dtype"] == "torch.float32" and s["device"] == "cpu"
            and not s["autocast_cpu"] and not s["autocast_cuda"]
            and not s["cuda_initialized"]
            and s["dont_write_bytecode"] and s["env"] == RUNTIME_ENV)


def module_from_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def initialize(run):
    run.require("torch" not in sys.modules and "parcae_lm" not in sys.modules,
                "BLOCKED", "Fresh numerical interpreter", {"preimported": [x for x in ("torch", "parcae_lm") if x in sys.modules]})
    before_env = {k: os.environ.get(k) for k in RUNTIME_ENV}
    os.environ.update(RUNTIME_ENV)
    sys.dont_write_bytecode = True
    sys.pycache_prefix = str(run.private / "pycache")
    os.environ["PYTHONPYCACHEPREFIX"] = sys.pycache_prefix
    import torch
    run.require(torch.__version__ == "2.11.0+cpu" and torch.version.cuda is None
                and Path(torch.__file__).resolve().is_relative_to(VENV), "BLOCKED", "Frozen CPU Torch origin",
                {"version": torch.__version__, "cuda_build": torch.version.cuda, "file": torch.__file__})
    before_settings = runtime_state(torch)
    torch.set_num_threads(1); torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.set_default_dtype(torch.float32); torch.set_default_device("cpu")
    torch.manual_seed(0)  # Constructor only; all accepted state must be overwritten by the artifact.
    before = runtime_state(torch)
    run.require(runtime_ok(before), "BLOCKED", "Required actual CPU runtime before upstream import", before)
    sys.path.insert(0, str(UPSTREAM))
    import parcae_lm
    official = module_from_file("mythos_frozen_receval_parcae", UPSTREAM / "receval/models/parcae.py")
    after = runtime_state(torch)
    origins = {"package": str(Path(parcae_lm.__file__).resolve()),
               "loader": str(Path(official.ModelingParcae.from_pretrained.__func__.__code__.co_filename).resolve())}
    facts = {"env_before": before_env, "before_settings": before_settings,
             "before_upstream": before, "after_upstream": after, "origins": origins,
             "torch_version": torch.__version__, "torch_build": torch.__config__.show(),
             "cpu_capability": torch.backends.cpu.get_cpu_capability(),
             "lscpu": subprocess.run(["lscpu"], capture_output=True, text=True).stdout,
             "pid": os.getpid(), "python": sys.version, "constructor_seed": 0}
    save(run.private / "runtime.json", facts)
    run.require(before == after and runtime_ok(after), "BLOCKED", "Upstream import preserves runtime", after, before)
    run.require(origins == {"package": str(UPSTREAM / "parcae_lm/__init__.py"),
                           "loader": str(UPSTREAM / "receval/models/parcae.py")},
                "BLOCKED", "Pinned official loader origin", origins)
    checker = module_from_file("mythos_frozen_state_checks", REPO / REL / "state_checks.py")
    return torch, official.ModelingParcae, checker


def experiment(run):
    preflight(run)
    torch, cls, checker = initialize(run)
    run.gates["L0"] = "PASS"
    run.phase = "L1"
    run.require(MODEL_DIR.is_dir() and MODEL_DIR.resolve() == MODEL_DIR, "BLOCKED",
                "Existing absolute local model directory; no download fallback", str(MODEL_DIR))
    reference = torch.load(MODEL_DIR / "pytorch_model.bin", map_location="cpu", weights_only=True)
    try:
        normalized, provenance = checker.normalize_checkpoint(reference)
    except ValueError as exc:
        run.require(False, "FAIL", "Checkpoint key normalization", str(exc))
    save(run.public / "key_normalization.json", provenance)
    source_meta = {k: {"tensor": isinstance(v, torch.Tensor), "shape": list(v.shape) if isinstance(v, torch.Tensor) else None,
                       "dtype": str(v.dtype) if isinstance(v, torch.Tensor) else None,
                       "device": str(v.device) if isinstance(v, torch.Tensor) else None} for k, v in normalized.items()}
    save(run.public / "source_metadata.json", source_meta)
    run.require(bool(normalized) and all(isinstance(v, torch.Tensor) and v.device.type == "cpu" for v in normalized.values()),
                "FAIL", "Independent nonempty CPU tensor checkpoint reference", source_meta)
    run.gates["L1"] = "PASS"
    run.phase = "L2"
    save(run.public / "loader_invocation.json", {"utc": utc(), "call_count_before": run.loader_calls,
         "entry": "pinned receval.models.parcae.ModelingParcae.from_pretrained",
         "path": str(MODEL_DIR), "device": "cpu", "dtype": None, "config_kwargs": {},
         "reference_read_count": 1, "official_internal_read_expected": 1})
    run.loader_calls += 1
    model = cls.from_pretrained(MODEL_DIR, device="cpu", dtype=None)
    run.require(type(model) is cls and not model.training and all(not m.training for m in model.modules()),
                "FAIL", "Official loader returns exact evaluation model", {"type": type(model).__name__, "training": model.training})
    run.require(runtime_ok(runtime_state(torch)), "BLOCKED", "Runtime remains CPU after official loading", runtime_state(torch))
    run.gates["L2"] = "PASS"
    run.phase = "L3"
    with torch.no_grad():
        run.comparison = checker.compare_state(torch, normalized, model, run.tensor_row)
    save(run.public / "state_comparison.json", run.comparison)
    run.require(run.comparison["status"] == "PASS", run.comparison["status"], "Complete state coverage and byte agreement",
                {"rows": len(run.rows), "errors": run.comparison["errors"]}, "All named parameters and buffers covered and byte-identical")
    run.gates["L3"] = "PASS"
    run.phase = "L4"
    rows = {r["name"]: r for r in run.rows}
    run.require(len(rows) == len(normalized) and all(r["hash_complete"] and r["bytewise_equal"]
                and r["bytes_hashed"] == r["source_bytes_hashed"] == r["model_bytes_hashed"] == r["expected_bytes"]
                for r in rows.values()), "FAIL",
                "Every checkpoint key has one complete direct byte comparison", {"keys": len(normalized), "rows": len(rows)})
    rope = rows.get("freqs_cis")
    run.require(rope is not None and rope["category"] == "buffer" and rope["bytewise_equal"], "FAIL",
                "Explicit restored RoPE buffer equality to original checkpoint", rope)
    cfg = json.loads((MODEL_DIR / "config.json").read_text())
    run.require(cfg.get("tie_embeddings") is True, "BLOCKED", "Frozen tied-embedding premise", cfg.get("tie_embeddings"))
    left, right = model.transformer.wte.weight, model.lm_head.weight
    alias = {"same_object": left is right, "same_storage": left.untyped_storage().data_ptr() == right.untyped_storage().data_ptr(),
             "same_offset": left.storage_offset() == right.storage_offset(), "same_shape": left.shape == right.shape,
             "same_stride": left.stride() == right.stride(),
             "both_paths_directly_equal_to_independent_file": all(rows.get(k, {}).get("bytewise_equal") is True
                  for k in ("transformer.wte.weight", "lm_head.weight"))}
    run.require(all(alias.values()), "FAIL", "Tied model aliases and both artifact paths agree", alias)
    parameters = list(model.named_parameters(remove_duplicate=False)); buffers = list(model.named_buffers(remove_duplicate=False))
    unique = {id(v): v for _, v in parameters}
    run.result_counts = {"checkpoint_keys": len(normalized), "compared_keys": len(rows),
                         "parameter_paths": len(parameters), "unique_parameter_tensors": len(unique),
                         "unique_parameter_numel": sum(v.numel() for v in unique.values()),
                         "buffer_paths": len(buffers), "buffer_numel": sum(v.numel() for _, v in buffers),
                         "compared_bytes": sum(r["bytes_hashed"] for r in rows.values()),
                         "nonpersistent_buffer_slots": len(run.comparison["nonpersistent_buffers"]),
                         "none_buffer_slots": len(run.comparison["none_buffer_slots"])}
    run.require(run.loader_calls == 1, "FAIL", "Exactly one official model loading invocation", run.loader_calls, 1)
    save(run.public / "loading_acceptance.json", {"counts": run.result_counts, "rope": rope, "tied_alias": alias,
                                                 "runtime_after": runtime_state(torch)})
    run.gates["L4"] = "PASS"
    run.status = "PASS"


def seal(run):
    # Only filesystem hashing, recorded metadata and Git checks after a stop.
    audit = {"files": {}, "git": {}, "trees": {}, "changes": [], "unavailable": [],
             "complete_baseline": run.protection_complete, "save_errors": run.save_errors}
    for name, expected in run.files.items():
        try:
            actual = digest(name); same = actual == expected
            audit["files"][name] = {"expected": expected, "actual": actual, "unchanged": same}
            if not same: audit["changes"].append(name)
        except Exception as exc:
            audit["unavailable"].append({"path": name, "error": str(exc)})
    for name, expected in run.git_before.items():
        try:
            actual = git_state(name); same = actual == expected
            audit["git"][name] = {"expected": expected, "actual": actual, "unchanged": same}
            if not same: audit["changes"].append(name)
        except Exception as exc:
            audit["unavailable"].append({"path": name, "error": str(exc)})
    for name, expected in run.trees.items():
        try:
            path = Path(name); actual = sorted(str(p.relative_to(path)) for p in path.rglob("*") if p.is_file())
            audit["trees"][name] = {"added": sorted(set(actual) - set(expected)), "removed": sorted(set(expected) - set(actual))}
            if actual != expected: audit["changes"].append(name)
        except Exception as exc:
            audit["unavailable"].append({"path": name, "error": str(exc)})
    save(run.public / "invariance.json", audit)
    status = "FAIL" if audit["changes"] else "PASS" if run.protection_complete and not audit["unavailable"] and not run.save_errors else "BLOCKED"
    run.gates["L5"] = status
    if status == "FAIL" or (status == "BLOCKED" and run.status == "PASS"):
        run.status = status
        if run.stop_reason is None:
            run.stop_reason = {"gate": "L5", "reason": "Protected-state or evidence completeness check did not pass"}
    run.record("L5", status, "Protected artifacts, source and checkouts unchanged", "Complete baseline and no changes",
               {"protected_files": len(run.files), "changes": audit["changes"], "unavailable": audit["unavailable"],
                "complete_baseline": run.protection_complete, "save_errors": run.save_errors})
    summary = {"experiment": "MYTHOS-CPU-LOAD-INTEGRITY-V1", "run_id": run.root.name, "utc": utc(),
               "status": run.status, "gates": run.gates, "stop_reason": run.stop_reason,
               "implementation_commit": run.implementation, "execution_head": git(REPO, "rev-parse", "HEAD"),
               "branch": BRANCH, "loader_invocations": run.loader_calls, "tensor_rows_saved": len(run.rows),
               "counts": run.result_counts, "formal_run_started": True,
               "conclusion": "All original parameters and buffers restored byte-identically" if run.status == "PASS" else "Complete loading integrity not established",
               "historical_A5": "BLOCKED", "A5_threshold": 1e-6,
               "forward": "NOT TESTED", "generation": "NOT TESTED", "language_quality": "NOT TESTED",
               "training_and_resume": "NOT TESTED", "historical_artifact_creation_environment": "UNKNOWN",
               "Formal_Oracle": "BLOCKED / NOT_READY", "FORMAL_ACCEPTANCE_READY": False}
    raw = json_bytes(summary)
    entries = [{"path": str(p.relative_to(run.root)), **digest(p),
                "class": "public" if p.is_relative_to(run.public) else "private"}
               for p in sorted(run.root.rglob("*")) if p.is_file()]
    entries.append({"path": "public/summary.json", "size": len(raw), "sha256": hashlib.sha256(raw).hexdigest(), "class": "public"})
    save(run.root / "FULL_MANIFEST.json", {"files": entries,
         "excluded": ["FULL_MANIFEST.json", "public/GIT_BUNDLE_MANIFEST.json"], "reason": "Avoid self-reference"})
    save(run.public / "GIT_BUNDLE_MANIFEST.json", {"files": [e for e in entries if e["class"] == "public"],
         "excluded": ["GIT_BUNDLE_MANIFEST.json"], "private_tensor_values_exported": False})
    with (run.public / "summary.json").open("xb") as stream: stream.write(raw)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--implementation-commit", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    if not args.execute or not re.fullmatch(r"[0-9a-f]{40}", args.implementation_commit) or not re.fullmatch(r"load-v1-\d{8}T\d{6}Z", args.run_id):
        parser.error("Explicit execution, full frozen SHA and a UTC run identifier are required")
    EVIDENCE_ROOT.mkdir(parents=True, exist_ok=False)
    root = EVIDENCE_ROOT / args.run_id; root.mkdir()
    save(root / "CLAIM.json", {"utc": utc(), "pid": os.getpid(), "implementation_commit": args.implementation_commit,
         "runner_identity": digest(__file__), "run_id": args.run_id, "attempt": 1})
    run = None
    summary = None
    emergency = None
    def interrupted(signum, frame):
        raise KeyboardInterrupt(f"Termination signal {signum}; stop and seal")
    signal.signal(signal.SIGTERM, interrupted)
    try:
        run = Run(root, args.implementation_commit)
        with (run.private / "stdout.log").open("w") as out, (run.private / "stderr.log").open("w") as err:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                try:
                    experiment(run)
                except Stop as exc:
                    run.gates[exc.gate] = exc.status
                    run.status, run.stop_reason = exc.status, {"gate": exc.gate, "reason": exc.reason}
                except BaseException as exc:
                    run.status = run.gates[run.phase] = "BLOCKED"
                    run.stop_reason = {"gate": run.phase, "reason": str(exc), "exception": type(exc).__name__}
                    try: traceback.print_exc()
                    except BaseException as save_exc: run.save_errors.append(repr(save_exc))
                    try:
                        run.record(run.phase, "BLOCKED", "Exception stops the single formal attempt",
                                   "No retries; preserve partial evidence", run.stop_reason)
                    except BaseException as save_exc: run.save_errors.append(repr(save_exc))
    except BaseException as exc:
        if run is not None:
            if run.stop_reason is None:
                run.stop_reason = {"gate": run.phase, "reason": str(exc), "exception": type(exc).__name__}
                run.status = run.gates[run.phase] = "BLOCKED"
            run.save_errors.append(repr(exc))
        else:
            emergency = {"status": "BLOCKED", "reason": "Run initialization failed after claim", "exception": repr(exc)}
    finally:
        # Log contexts have exited. Attempt normal sealing even after a logging
        # failure or an interrupt. No tensor operation occurs in this block.
        if run is not None:
            try:
                summary = seal(run)
            except BaseException as exc:
                emergency = {"status": "FAIL" if run.status == "FAIL" else "BLOCKED",
                             "reason": "Evidence sealing failed", "exception": repr(exc),
                             "previous_stop": run.stop_reason, "gates": run.gates, "save_errors": run.save_errors}
        if emergency is not None:
            try: save(root / "EMERGENCY.json", emergency)
            except BaseException: pass
    if emergency is not None:
        print(json.dumps(emergency)); return 2
    print(json.dumps({"run_directory": str(root), "status": summary["status"], "gates": summary["gates"],
                      "stop_reason": summary["stop_reason"], "counts": summary["counts"]}, indent=2))
    return 0 if summary["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
