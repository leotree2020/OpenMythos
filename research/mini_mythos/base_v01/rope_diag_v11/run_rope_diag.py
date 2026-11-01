"""Single formal CPU RoPE diagnostic. Importing this file performs no work."""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import traceback

SPACE = "bookish-pancake-vwqx7rr9x5w3wxjr"
REPO = Path("/workspaces/mythos-base-v01-rope-diag-v11")
UPSTREAM = Path("/workspaces/mythos-parcae-pinned")
B1_REPO = Path("/workspaces/mythos-base-v01-b1")
VENV = Path("/workspaces/mythos-base-v01-cpu312")
B1_RUN = Path("/workspaces/mythos-evidence/base_v01/b1/b1-20261101T021657Z")
EVIDENCE_ROOT = Path("/workspaces/mythos-evidence/base_v01/rope_diag")
REL = Path("research/mini_mythos/base_v01/rope_diag_v11")
UPSTREAM_SHA = "69284c13746e849104f738d6d1a347b1f457df76"
B1_SHA = "d88be474ebb2529c5b095e3732b1f25509f9b824"
INPUTS = {
    "downloads/model/pytorch_model.bin": (578361537, "ed6eb306464dd0d694e9eacd58f7e06ac3e44b43cb7c5c79dbcb1543059c6621"),
    "downloads/model/config.json": (1741, "5c8fc785c2f6dba67d0370ad715034860e3b22bfce850da825c06baa03923c13"),
    "verify_load.json": (7220, "627fd019a46d4529a698d5bd46eadae5d6daf2334cba59e999edabc519c4815f"),
    "env_check.json": (7825, "55373ba603a91745dcabdaa3e09e24bc916d2b7f3f2cd9251ef88b3006c977cd"),
    "manifest.json": (1372, "2ac1ca86c540f3b044304b3abf3951dcbf4d8adf9499056959293cbf315cf962"),
    "summary.json": (3024, "c42cdbfda8239a3786bd05aa02a432d822e787984d5fbfcfa92dd2bca4d91539"),
}
LOCK_HASH = "84440f8945041ed314c29b205c5244e074116ede023d5aae0b11b633b4d6a51e"
RUNTIME_ENV = {
    "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
    "RAYON_NUM_THREADS": "1", "TOKENIZERS_PARALLELISM": "false",
    "CUDA_VISIBLE_DEVICES": "", "PYTHONDONTWRITEBYTECODE": "1",
}
FROZEN_FILES = ["run_rope_diag.py", "paths.py", "metrics.py", "PROTOCOL.md", "README_USAGE.md"]
UPSTREAM_FILES = {
    "parcae_lm/__init__.py": "453bdfc947ecb921b3fca9f6d558a1fe8a6a43e0992b4758c8b8f2627cfc1aac",
    "parcae_lm/modules/utils.py": "e21f09ac8b6c33ac43837877c352c723a97218166a139dd0e9e8222dd7b3b2c5",
    "parcae_lm/modules/blocks.py": "96232cf3543dcf7674d5610d1cb2e1c6bb0aae3c5a244d42db79b502c3d70ea3",
    "parcae_lm/models/config.py": "6c44badecd52f2a58ce3d3a14b70bcb64a181ea058b9bde99cbfbf76d917df95",
    "parcae_lm/models/parcae/config.py": "e9a5e7515b8f5261191491964e4ea45fdb09f633bd55835d604fd544f41e0d18",
    "parcae_lm/models/parcae/parcae.py": "c0d792379c3e965ec75bbe88dbdcf500392a12fd0c67f8a484543b2398470c3d",
}


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return {"size": Path(path).stat().st_size, "sha256": h.hexdigest()}


def write_json(path, value):
    raw = (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    with Path(path).open("xb") as f:
        f.write(raw)


def command(args, *, check=True):
    p = subprocess.run(args, capture_output=True, text=True,
                       env=dict(os.environ, GIT_OPTIONAL_LOCKS="0"))
    if check and p.returncode:
        raise RuntimeError(f"Command failed ({p.returncode}): {args}: {p.stderr}")
    return {"args": [str(x) for x in args], "returncode": p.returncode,
            "stdout": p.stdout, "stderr": p.stderr}


def git(repo, *args):
    return command(["git", "-C", str(repo), *args])["stdout"].strip()


class GuardStop(Exception):
    def __init__(self, gate, status, reason):
        self.gate, self.status, self.reason = gate, status, reason
        super().__init__(reason)


class Run:
    def __init__(self, root, implementation):
        self.root = root
        self.private = root / "private"
        self.public = root / "public"
        self.private.mkdir()
        self.public.mkdir()
        self.implementation = implementation
        self.phase = "G0"
        self.status = "NOT TESTED"
        self.gates = {f"G{i}": "NOT TESTED" for i in range(6)}
        self.records = []
        self.baseline_files = {}
        self.baseline_git = {}
        self.candidate_reports = {}
        self.stop_reason = None
        self.history = None
        self.params = None
        self.protection_complete = False
        self.save_errors = []

    def record(self, gate, status, purpose, expected, actual, inputs=None):
        value = {"utc": utc(), "gate": gate, "Purpose": purpose,
                 "Environment": {"codespace": SPACE, "python": sys.executable,
                                 "implementation_commit": self.implementation},
                 "Input": inputs, "Expected": expected, "Actual": actual, "Status": status}
        self.records.append(value)
        # Flush completed observations before another operation can fail.
        write_json(self.public / f"check_{len(self.records):03d}.json", value)
        return value

    def require(self, condition, gate, status, reason, actual=None, expected=True):
        self.record(gate, "PASS" if condition else status, reason, expected, actual)
        if not condition:
            raise GuardStop(gate, status, reason)

    def protect_file(self, path, expected=None):
        got = digest(path)
        if expected is not None:
            self.require(got == expected, "G0", "BLOCKED", f"Frozen file identity: {path}", got, expected)
        self.baseline_files[str(path)] = got
        return got

    def save_tensors(self, torch, name, tensors):
        # Tensor data and component values are private, never in the Git export.
        with (self.private / f"{name}.pt").open("xb") as f:
            torch.save(tensors, f)
        metadata = {}
        for key, value in tensors.items():
            raw = tensor_bytes(torch, value)
            metadata[key] = {"shape": list(value.shape), "stride": list(value.stride()),
                             "dtype": str(value.dtype), "device": str(value.device),
                             "contiguous": value.is_contiguous(),
                             "sha256_canonical_bytes": hashlib.sha256(raw).hexdigest()}
        write_json(self.private / f"{name}_tensor_identity.json", metadata)
        return metadata


def tensor_bytes(torch, x):
    return x.detach().cpu().contiguous().view(torch.uint8).numpy().tobytes()


def same_tensor(torch, x, y):
    return (x.shape == y.shape and x.dtype == y.dtype and x.stride() == y.stride()
            and tensor_bytes(torch, x) == tensor_bytes(torch, y))


def runtime_state(torch):
    return {"intra_op": torch.get_num_threads(), "inter_op": torch.get_num_interop_threads(),
            "deterministic": torch.are_deterministic_algorithms_enabled(),
            "default_dtype": str(torch.get_default_dtype()), "default_device": str(torch.get_default_device()),
            "autocast_cpu": torch.is_autocast_enabled("cpu"),
            "autocast_cuda": torch.is_autocast_enabled("cuda"),
            "dont_write_bytecode": sys.dont_write_bytecode, "pycache_prefix": sys.pycache_prefix,
            "env": {key: os.environ.get(key) for key in RUNTIME_ENV}}


def runtime_matches(state):
    return (state["intra_op"] == state["inter_op"] == 1 and state["deterministic"] is True
            and state["default_dtype"] == "torch.float32" and state["default_device"] == "cpu"
            and not state["autocast_cpu"] and not state["autocast_cuda"]
            and state["dont_write_bytecode"] and state["env"] == RUNTIME_ENV)


def initialize_runtime(private):
    before_env = {key: os.environ.get(key) for key in RUNTIME_ENV}
    for key, value in RUNTIME_ENV.items():
        os.environ[key] = value
    sys.dont_write_bytecode = True
    sys.pycache_prefix = str(private / "pycache")
    os.environ["PYTHONPYCACHEPREFIX"] = sys.pycache_prefix
    if "torch" in sys.modules or "parcae_lm" in sys.modules:
        raise RuntimeError("Unexpected pre-imported numerical modules")
    import torch
    after_torch_import = runtime_state(torch)
    write_json(private / "runtime_before_settings.json", after_torch_import)
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.set_default_dtype(torch.float32)
    torch.set_default_device("cpu")
    before_import = runtime_state(torch)
    write_json(private / "runtime_before_parcae.json", before_import)
    if not runtime_matches(before_import):
        raise RuntimeError("Runtime settings did not take effect before Parcae import")
    sys.path.insert(0, str(UPSTREAM))
    import parcae_lm
    from parcae_lm.modules.utils import precompute_freqs_cis
    after_import = runtime_state(torch)
    origins = {"parcae_lm": str(Path(parcae_lm.__file__).resolve()),
               "native_helper": str(Path(sys.modules[precompute_freqs_cis.__module__].__file__).resolve())}
    facts = {"env_before_setting": before_env, "after_torch_before_settings": after_torch_import, "before_parcae": before_import,
             "after_parcae": after_import, "origins": origins,
             "torch_version": torch.__version__, "torch_config": torch.__config__.show(),
             "cpu_capability": torch.backends.cpu.get_cpu_capability(),
             "lscpu": command(["lscpu"], check=False), "platform": platform.platform(),
             "pid": os.getpid(), "python": sys.version, "executable": sys.executable,
             "prefix": sys.prefix}
    write_json(private / "runtime.json", facts)
    if before_import != after_import or not runtime_matches(after_import):
        raise RuntimeError("Parcae import changed required global Torch state")
    for origin in origins.values():
        Path(origin).relative_to(UPSTREAM)
    return torch, precompute_freqs_cis, facts


def derive_parameters(cfg):
    # Source proof is recorded in STATIC_REVIEW.md. Do not instantiate a model.
    required = {"block_class_name": "TransformerPreNormBlock", "mup_model_scaling_factor": 1,
                "randomize_positions_from": None, "n_embd": 768, "num_attention_heads": 6,
                "recurrent_embedding_dimension": 768, "block_size": 2048}
    for key, value in required.items():
        if key not in cfg or cfg[key] != value:
            raise ValueError(f"Unmet fixed configuration premise: {key}")
    rec_heads = cfg.get("recurrent_num_attention_heads")
    if rec_heads is None:
        rec_heads = cfg["num_attention_heads"]
    outer_dim = cfg["n_embd"] // cfg["num_attention_heads"]
    core_dim = cfg["recurrent_embedding_dimension"] // rec_heads
    rope = cfg["rope_settings"]
    if (outer_dim != 128 or core_dim != 128 or cfg["n_embd"] % cfg["num_attention_heads"]
            or cfg["recurrent_embedding_dimension"] % rec_heads or rope.get("use_rope") is not True
            or rope["rope_base"] != 50000 or type(rope["rope_base"]) is not int
            or rope["rope_condense_ratio"] != 1 or type(rope["rope_condense_ratio"]) is not int):
        raise ValueError("Unmet RoPE dimension/base/condense premise")
    return {"dim": outer_dim, "end": cfg["block_size"], "theta": rope["rope_base"],
            "condense_ratio": rope["rope_condense_ratio"], "core_dim": core_dim,
            "expanded": False, "layout": [1, 2048, 1, 64, 2]}


def preflight(run):
    run.require(os.environ.get("CODESPACE_NAME") == SPACE, "G0", "BLOCKED", "Target Codespace identity",
                os.environ.get("CODESPACE_NAME"), SPACE)
    run.require(sys.executable == str(VENV / "bin/python") and sys.prefix == str(VENV)
                and platform.python_version() == "3.12.3", "G0", "BLOCKED", "Frozen interpreter identity",
                {"executable": sys.executable, "prefix": sys.prefix, "version": platform.python_version()})
    run.require(Path(__file__).resolve().parent == REPO / REL, "G0", "BLOCKED", "Frozen source location",
                str(Path(__file__).resolve()))
    run.require(git(REPO, "status", "--porcelain=v1", "--untracked-files=all") == "", "G0", "BLOCKED",
                "Committed clean diagnostic worktree", git(REPO, "status", "--porcelain=v1", "--untracked-files=all"), "")
    run.require(git(REPO, "branch", "--show-current") == "mythos-base-v01-rope-diag-v11", "G0", "BLOCKED",
                "Diagnostic branch", git(REPO, "branch", "--show-current"))
    command(["git", "-C", str(REPO), "merge-base", "--is-ancestor", run.implementation, "HEAD"])
    for name in FROZEN_FILES:
        path = REPO / REL / name
        blob = subprocess.check_output(["git", "-C", str(REPO), "show", f"{run.implementation}:{REL / name}"])
        run.require(path.read_bytes() == blob, "G0", "BLOCKED", f"Frozen implementation bytes: {name}",
                    digest(path), {"size": len(blob), "sha256": hashlib.sha256(blob).hexdigest()})
        run.protect_file(path)
    for repo, expected in [(UPSTREAM, UPSTREAM_SHA), (B1_REPO, B1_SHA)]:
        state = {"head": git(repo, "rev-parse", "HEAD"),
                 "status": git(repo, "status", "--porcelain=v1", "--untracked-files=all", "--ignored")}
        run.require(state == {"head": expected, "status": ""}, "G0", "BLOCKED", f"Frozen clean checkout: {repo}",
                    state, {"head": expected, "status": ""})
        run.baseline_git[str(repo)] = state
    for name, (size, sha) in INPUTS.items():
        run.protect_file(B1_RUN / name, {"size": size, "sha256": sha})
    manifest = json.loads((B1_RUN / "manifest.json").read_text())
    run.require(manifest["run_id"] == "b1-20261101T021657Z", "G0", "BLOCKED", "Historical run id", manifest["run_id"])
    for item in manifest["files"]:
        path = (B1_RUN / item["path"]).resolve()
        path.relative_to(B1_RUN)
        if str(path) not in run.baseline_files:
            run.protect_file(path, {"size": item["size"], "sha256": item["sha256"]})
    lock = B1_REPO / "research/mini_mythos/base_v01/requirements.lock"
    run.protect_file(lock, {"size": 2881, "sha256": LOCK_HASH})
    run.history = json.loads((B1_RUN / "env_check.json").read_text())
    historical = json.loads((B1_RUN / "verify_load.json").read_text())
    run.historical_a5 = next(c for c in historical["checks"] if c["id"] == "A5")
    run.old_scalar = run.historical_a5["detail"]["max_abs_diff"]
    run.require(run.old_scalar == historical["rope_check"]["A"]["max_abs_diff"]
                and run.old_scalar == 0.00012207025429233909,
                "G0", "BLOCKED", "Historical scalar copies agree", run.old_scalar,
                historical["rope_check"]["A"]["max_abs_diff"])
    source_preflight = B1_REPO / "research/mini_mythos/base_v01/evidence_b1/b1-20261101T021657Z/operator/source_preflight.json"
    run.protect_file(source_preflight, {"size": 4780, "sha256": "a7a1ce6ebc479f01448858845374d085c5e35c84ac20f669a5a4ca327b933575"})
    run.historical_operator = json.loads(source_preflight.read_text())
    for name, sha in run.history["code_identity"]["file_sha256"].items():
        path = B1_REPO / "research/mini_mythos/base_v01" / name
        run.protect_file(path)
        run.require(run.baseline_files[str(path)]["sha256"] == sha, "G0", "BLOCKED", f"B1 code preserved: {name}",
                    run.baseline_files[str(path)]["sha256"], sha)
    expected_packages = run.history["dependencies"]["distributions"]
    actual = {re.sub(r"[-_.]+", "-", d.metadata["Name"]).lower(): d.version
              for d in importlib.metadata.distributions() if d.metadata.get("Name")}
    run.require(actual == expected_packages, "G0", "BLOCKED", "Complete installed distribution metadata",
                actual, expected_packages)
    cfg = json.loads((B1_RUN / "downloads/model/config.json").read_text())
    run.params = derive_parameters(cfg)
    run.record("G0", "PASS", "Source-derived fixed RoPE parameters", "Approved parameters, no model construction", run.params)
    # Preserve all tracked upstream source bytes for the post-stop invariance audit.
    for rel in git(UPSTREAM, "ls-files").splitlines():
        identity = run.protect_file(UPSTREAM / rel)
        if rel in UPSTREAM_FILES:
            run.require(identity["sha256"] == UPSTREAM_FILES[rel], "G0", "BLOCKED",
                        f"Pinned upstream source bytes: {rel}", identity["sha256"], UPSTREAM_FILES[rel])
    write_json(run.private / "protected_before.json", {"files": run.baseline_files, "git": run.baseline_git})
    run.protection_complete = True


def native_call(helper, params):
    return helper(params["dim"], params["end"], params["theta"], params["condense_ratio"])


def validate_bundle(run, torch, bundle, name, gate):
    for key, value in bundle.items():
        run.require(value.device.type == "cpu" and bool(torch.isfinite(value).all().item()), gate, "FAIL",
                    f"{name}/{key}: CPU and finite", {"device": str(value.device), "shape": list(value.shape)})
    out = bundle["output"]
    expected = [1, 2048, 1, 64, 2]
    run.require(list(out.shape) == expected and out.dtype == torch.float32 and out.is_contiguous()
                and list(out.stride()) == [262144, 128, 128, 2, 1], gate, "FAIL",
                f"{name}: candidate structure", {"shape": list(out.shape), "dtype": str(out.dtype), "stride": list(out.stride())})
    run.require(bool((out[:, 0, :, :, 0] == 1).all().item()) and bool((out[:, 0, :, :, 1] == 0).all().item()),
                gate, "FAIL", f"{name}: position-zero invariant", "cos=1; sin=0")


def build_and_preserve(run, torch, build_path, name, evidence_name, gate):
    bundle = {}
    try:
        build_path(torch, name, run.params["dim"], run.params["end"], run.params["theta"],
                   run.params["condense_ratio"], capture=bundle)
    except ValueError as exc:
        if bundle:
            try:
                run.save_tensors(torch, evidence_name, bundle)
            except BaseException as save_exc:
                run.save_errors.append({"path": evidence_name, "exception": type(save_exc).__name__, "message": str(save_exc)})
        raise GuardStop(gate, "FAIL", f"{evidence_name}: {exc}") from exc
    except BaseException:
        if bundle:
            try:
                run.save_tensors(torch, evidence_name, bundle)
            except BaseException as save_exc:
                run.save_errors.append({"path": evidence_name, "exception": type(save_exc).__name__, "message": str(save_exc)})
        raise
    run.save_tensors(torch, evidence_name, bundle)
    return bundle


def native_child(root, implementation):
    # Child cannot read S: no B1_RUN path or input deserialization in this flow.
    private = root / "private" / "native_child"
    private.mkdir()
    with (private / "stdout.log").open("x") as out, (private / "stderr.log").open("x") as err:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            torch, helper, facts = initialize_runtime(private)
            params = {"dim": 128, "end": 2048, "theta": 50000, "condense_ratio": 1}
            with torch.no_grad():
                value = native_call(helper, params)
            with (private / "N3.pt").open("xb") as f:
                torch.save(value, f)
            write_json(private / "completed.json", {"pid": os.getpid(), "implementation": implementation,
                       "S_read": False, "candidate": "N3", "params": params, "runtime_verified": runtime_matches(facts["after_parcae"])})
    return 0


def experiment(run):
    preflight(run)
    torch, helper, runtime = initialize_runtime(run.private)
    run.record("G0", "PASS", "Actual runtime and import invariance", "Single-thread deterministic CPU FP32; no enabled autocast",
               {"before": runtime["before_parcae"], "after": runtime["after_parcae"], "origins": runtime["origins"]})
    # Only the tensor buffer is retained; never instantiate or load a full model.
    state = torch.load(B1_RUN / "downloads/model/pytorch_model.bin", weights_only=True, map_location="cpu")
    run.require(isinstance(state, dict) and "freqs_cis" in state, "G0", "BLOCKED", "Stored RoPE key exists",
                {"mapping": isinstance(state, dict), "freqs_cis_present": "freqs_cis" in state if isinstance(state, dict) else False})
    stored = state["freqs_cis"]
    run.save_tensors(torch, "stored_S_before_copy", {"output": stored})
    run.require(list(stored.shape) == [1, 2048, 1, 64, 2] and stored.dtype == torch.float32
                and stored.device.type == "cpu" and stored.is_contiguous()
                and list(stored.stride()) == [262144, 128, 128, 2, 1]
                and bool(torch.isfinite(stored).all().item()), "G0", "BLOCKED", "Original S layout before independent copy",
                {"shape": list(stored.shape), "dtype": str(stored.dtype), "stride": list(stored.stride())})
    S = stored.detach().clone()
    del stored
    del state
    run.require(list(S.shape) == [1, 2048, 1, 64, 2] and S.dtype == torch.float32
                and S.device.type == "cpu" and bool(torch.isfinite(S).all().item()), "G0", "BLOCKED", "Stored S identity/structure",
                {"shape": list(S.shape), "dtype": str(S.dtype), "device": str(S.device), "stride": list(S.stride())})
    run.save_tensors(torch, "S", {"output": S})
    run.gates["G0"] = "PASS"
    from paths import build_path
    from metrics import compute_comparison
    run.phase = "G1"
    with torch.no_grad():
        N1 = native_call(helper, run.params)
        run.save_tensors(torch, "N1", {"output": N1})
        validate_bundle(run, torch, {"output": N1}, "N1", "G1")
        N2 = native_call(helper, run.params)
        run.save_tensors(torch, "N2", {"output": N2})
        validate_bundle(run, torch, {"output": N2}, "N2", "G1")
        run.require(same_tensor(torch, N1, N2), "G1", "FAIL", "Native same-process byte repeatability", same_tensor(torch, N1, N2))
        child_args = [str(VENV / "bin/python"), "-B", str(Path(__file__).resolve()), "--native-child",
                      "--run-directory", str(run.root), "--implementation-commit", run.implementation]
        child = command(child_args, check=False)
        write_json(run.private / "native_child_process.json", child)
        run.require(child["returncode"] == 0, "G1", "BLOCKED", "Native fresh-interpreter completion", child["returncode"], 0)
        N3 = torch.load(run.private / "native_child/N3.pt", weights_only=True, map_location="cpu")
        child_info = json.loads((run.private / "native_child/completed.json").read_text())
        run.require(child_info["pid"] != os.getpid() and child_info["runtime_verified"], "G1", "FAIL", "N3 fresh verified process", child_info)
        validate_bundle(run, torch, {"output": N3}, "N3", "G1")
        run.require(same_tensor(torch, N1, N3), "G1", "FAIL", "Native fresh-process byte repeatability", same_tensor(torch, N1, N3))
        I32 = build_and_preserve(run, torch, build_path, "I32", "I32", "G1")
        validate_bundle(run, torch, I32, "I32", "G1")
        run.require(same_tensor(torch, N1, I32["output"]), "G1", "FAIL", "Independent I32 versus native bytes", same_tensor(torch, N1, I32["output"]))
        run.gates["G1"] = "PASS"
        run.phase = "G2"
        env_before = next(c["detail"]["env_before"] for c in run.history["checks"] if c["id"] == "E1")
        write_json(run.public / "environment_comparison.json", {
            "historical_env_before": env_before, "historical_dependencies": run.history["dependencies"],
            "historical_machine_facts": next(c["detail"] for c in run.history["checks"] if c["id"] == "E1"),
            "current_runtime": runtime, "runtime_env_requested": RUNTIME_ENV,
            "historical_operator_record": "evidence_b1/b1-20261101T021657Z/operator/source_preflight.json",
            "historical_operator_actual_record": run.historical_operator,
            "B1_source_declared_settings": {"OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "RAYON_NUM_THREADS": "1", "TOKENIZERS_PARALLELISM": "false", "CUDA_VISIBLE_DEVICES": "", "PYTHONDONTWRITEBYTECODE": "1", "intra_op": 1, "inter_op_requested": 1, "deterministic": True},
            "historical_per_operator_dispatch": "UNKNOWN",
            "limits": "env_before precedes B1 runner settings; operator lscpu was a separate earlier process. No claim of complete environment equivalence."})
        write_json(run.public / "historical_A5_record.json", run.historical_a5)
        old_scalar = run.old_scalar
        observed = float((S - N1).abs().max().item())
        run.record("G2", "PASS" if observed == old_scalar else "BLOCKED", "Historical A5 max-diff scalar reproduction",
                   old_scalar, {"observed": observed, "historical": old_scalar, "threshold": 1e-6,
                                "scope": "Scalar only; not historical tensor equality"})
        if observed != old_scalar:
            raise GuardStop("G2", "BLOCKED", "Historical A5 max-diff scalar reproduction not established")
        run.gates["G2"] = "PASS"
        run.phase = "G3"
        finals = {"N": N1}
        for name in ("T", "P", "R", "Q"):
            first = None
            for repeat in (1, 2):
                bundle = build_and_preserve(run, torch, build_path, name, f"{name}{repeat}", "G3")
                validate_bundle(run, torch, bundle, f"{name}{repeat}", "G3")
                if name in ("T", "P"):
                    for key in (("t32", "omega32", "phi32") if name == "T" else ("t32", "omega32")):
                        run.require(same_tensor(torch, bundle[key], I32[key]), "G3", "FAIL",
                                    f"{name}{repeat}: independently rebuilt {key} matches I32", same_tensor(torch, bundle[key], I32[key]))
                if repeat == 1:
                    first = bundle
                else:
                    match = first.keys() == bundle.keys() and all(same_tensor(torch, first[k], bundle[k]) for k in first)
                    run.require(match, "G3", "FAIL", f"{name}: all kept intermediates and output repeat bytewise", match)
            finals[name] = first["output"]
        for name, value in finals.items():
            try:
                report = compute_comparison(torch, S, value, I32["phi32"], f"{name}-S")
            except ValueError as exc:
                raise GuardStop("G3", "FAIL", f"Metrics validation: {name}-S: {exc}") from exc
            write_json(run.public / f"comparison_S_{name}.json", report["public"])
            write_json(run.private / f"comparison_S_{name}.json", report["private"])
            run.candidate_reports[name] = report["public"]
            del report
        for name, ref, value in [("T-N", N1, finals["T"]), ("P-T", finals["T"], finals["P"]),
                                 ("R-P", finals["P"], finals["R"]), ("Q-N", N1, finals["Q"]), ("N-R", finals["R"], N1)]:
            try:
                report = compute_comparison(torch, ref, value, I32["phi32"], name)
            except ValueError as exc:
                raise GuardStop("G3", "FAIL", f"Metrics validation: {name}: {exc}") from exc
            write_json(run.public / f"comparison_{name}.json", report["public"])
            write_json(run.private / f"comparison_{name}.json", report["private"])
            del report
        run.gates["G3"] = "PASS"
        run.gates["G4"] = "PASS"
        run.record("G3", "PASS", "All four prescribed paths repeated and all metrics produced", "T,T,P,P,R,R,Q,Q; full and secondary scopes", list(finals))
        run.record("G4", "PASS", "All produced candidates structurally checked on arrival", "CPU FP32 contiguous shape and position zero invariant", "All reached candidates checked")
        run.status = "PASS"


def seal(run):
    # No new tensor operations here, including after a guard stops computation.
    invariance = {"files": {}, "git": {}, "errors": [], "unavailable": [], "protection_complete": run.protection_complete,
                  "partial_save_errors": run.save_errors}
    for path, expected in run.baseline_files.items():
        try:
            actual = digest(path)
            invariance["files"][path] = {"expected": expected, "actual": actual, "unchanged": actual == expected}
            if actual != expected:
                invariance["errors"].append(f"Changed protected file: {path}")
        except Exception as exc:
            invariance["unavailable"].append(f"Cannot verify protected file: {path}: {type(exc).__name__}")
    for path, expected in run.baseline_git.items():
        try:
            actual = {"head": git(path, "rev-parse", "HEAD"),
                      "status": git(path, "status", "--porcelain=v1", "--untracked-files=all", "--ignored")}
            invariance["git"][path] = {"expected": expected, "actual": actual, "unchanged": actual == expected}
            if actual != expected:
                invariance["errors"].append(f"Changed protected checkout: {path}")
        except Exception as exc:
            invariance["unavailable"].append(f"Cannot verify protected checkout: {path}: {type(exc).__name__}")
    write_json(run.public / "invariance.json", invariance)
    run.gates["G5"] = ("FAIL" if invariance["errors"] else
                        "PASS" if run.protection_complete and not run.save_errors and not invariance["unavailable"] else "BLOCKED")
    if run.gates["G5"] == "FAIL":
        run.status = "FAIL"
    elif run.gates["G5"] == "BLOCKED" and run.status == "PASS":
        run.status = "BLOCKED"
    run.record("G5", run.gates["G5"], "Post-stop read-only invariance audit", "All protected bytes and Git states unchanged with a complete baseline",
               {"changes": invariance["errors"], "unavailable": invariance["unavailable"],
                "protection_complete": run.protection_complete, "partial_save_errors": run.save_errors})
    summary = {"experiment": "MYTHOS-B1-ROPE-DIAG-V1", "utc": utc(), "status": run.status,
               "implementation_commit": run.implementation, "source_head": git(REPO, "rev-parse", "HEAD"),
               "branch": git(REPO, "branch", "--show-current"), "run_id": run.root.name,
               "gates": run.gates, "stop_reason": run.stop_reason, "candidate_reports": run.candidate_reports,
               "scientific_conclusion": "UNRESOLVED: review path compatibility; no causal conclusion",
               "B1_A5": "BLOCKED", "A3_overall": "NOT TESTED", "A8_A11": "NOT TESTED",
               "language_quality": "NOT TESTED", "Formal_Oracle": "BLOCKED / NOT_READY",
               "FORMAL_ACCEPTANCE_READY": False, "formal_run_started": True,
               "uncovered_paths": ["FP64 frequency rounded to FP32, then FP64 phase/trig", "Other untested construction/device/conversion histories"],
               "limitations": ["N is newly constructed, not B1 historical N", "G2 establishes a scalar only",
                               "A matched candidate means compatibility only", "No-match does not exclude untested paths",
                               "1e-6 is a frozen screen, not a universal error bound"]}
    summary_raw = (json.dumps(summary, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    manifest = []
    for path in sorted(run.root.rglob("*")):
        if path.is_file():
            manifest.append({"path": str(path.relative_to(run.root)), **digest(path),
                             "class": "committable" if path.is_relative_to(run.public) else "private"})
    manifest.append({"path": "public/summary.json", "size": len(summary_raw),
                     "sha256": hashlib.sha256(summary_raw).hexdigest(), "class": "committable"})
    write_json(run.root / "FULL_MANIFEST.json", {"files": manifest, "excluded": ["FULL_MANIFEST.json", "public/GIT_BUNDLE_MANIFEST.json"], "reason": "Manifests exclude themselves and each other to avoid self-reference"})
    write_json(run.public / "GIT_BUNDLE_MANIFEST.json", {"files": [e for e in manifest if e["class"] == "committable"],
                                                        "excluded": ["GIT_BUNDLE_MANIFEST.json"], "private_data_exported": False})
    # A successful final summary is published only after both manifests exist.
    with (run.public / "summary.json").open("xb") as f:
        f.write(summary_raw)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--native-child", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--implementation-commit", required=True)
    parser.add_argument("--run-id")
    parser.add_argument("--run-directory", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.implementation_commit):
        parser.error("Expected a complete frozen implementation commit")
    if args.native_child:
        if args.execute or args.run_directory is None or args.run_directory.parent != EVIDENCE_ROOT:
            parser.error("Invalid native child invocation")
        if not (args.run_directory / "CLAIM.json").is_file():
            parser.error("Child requires existing formal parent claim")
        return native_child(args.run_directory, args.implementation_commit)
    if not args.execute:
        parser.error("No computation performed: explicit --execute is required")
    if not args.run_id or not re.fullmatch(r"rope-v11-[0-9]{8}T[0-9]{6}Z", args.run_id):
        parser.error("Expected unique UTC run-id: rope-v11-YYYYMMDDTHHMMSSZ")
    # Atomic experiment-level claim, before importing any numerical module.
    EVIDENCE_ROOT.mkdir(parents=True, exist_ok=False)
    root = EVIDENCE_ROOT / args.run_id
    root.mkdir()
    write_json(root / "CLAIM.json", {"utc": utc(), "run_id": args.run_id, "pid": os.getpid(),
                                   "implementation_commit": args.implementation_commit, "single_attempt": True})
    run = None
    summary = None
    try:
        run = Run(root, args.implementation_commit)
        with (run.private / "stdout.log").open("x", buffering=1) as out, (run.private / "stderr.log").open("x", buffering=1) as err:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                experiment(run)
    except BaseException as exc:
        status = exc.status if isinstance(exc, GuardStop) else "BLOCKED"
        gate = exc.gate if isinstance(exc, GuardStop) else run.phase if run else "G0"
        detail = {"utc": utc(), "gate": gate, "status": status, "exception_type": type(exc).__name__,
                  "reason": str(exc), "traceback": traceback.format_exc()}
        if run is not None:
            run.gates[gate] = status
            run.status = status
            run.stop_reason = {"gate": gate, "exception_type": type(exc).__name__, "reason": str(exc)}
        try:
            write_json(root / "STOP_DETAIL.json", detail)
        except BaseException:
            print(json.dumps(detail, ensure_ascii=False), file=sys.stderr)
    finally:
        if run is not None:
            try:
                summary = seal(run)
            except BaseException as exc:
                run.gates["G5"] = "BLOCKED"
                if run.status != "FAIL":
                    run.status = "BLOCKED"
                emergency = {"utc": utc(), "status": run.status, "gates": run.gates,
                             "primary_stop": run.stop_reason, "sealing_exception": type(exc).__name__,
                             "message": str(exc), "traceback": traceback.format_exc()}
                try:
                    write_json(root / "EMERGENCY_SEAL_FAILURE.json", emergency)
                except BaseException:
                    print(json.dumps(emergency, ensure_ascii=False), file=sys.stderr)
    if summary is None:
        print(json.dumps({"run_directory": str(root), "status": "BLOCKED", "reason": "Evidence sealing incomplete; preserve existing files; no rerun"}))
        return 2
    print(json.dumps({"run_directory": str(root), "status": summary["status"], "gates": run.gates,
                      "stop_reason": run.stop_reason, "implementation_commit": run.implementation}, indent=2))
    return 0 if run.status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
