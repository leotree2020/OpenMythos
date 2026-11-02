"""Frozen tiny CPU source-mathematics fixtures; no pretrained weights or data."""
from __future__ import annotations
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import sys
import time
import unittest
ENV = {"OMP_NUM_THREADS": "2", "MKL_NUM_THREADS": "2", "OPENBLAS_NUM_THREADS": "1",
       "RAYON_NUM_THREADS": "1", "TOKENIZERS_PARALLELISM": "false", "CUDA_VISIBLE_DEVICES": "",
       "PYTHONDONTWRITEBYTECODE": "1", "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"}
for key, value in ENV.items():
    os.environ[key] = value
import torch

TARGET_PYTHON = "/workspaces/mythos-base-v01-cpu312/bin/python"
SPACE = "bookish-pancake-vwqx7rr9x5w3wxjr"


def config(source, **changes):
    values = dict(vocab_size=31, d_model=16, n_layers=2, n_heads_q=4,
        n_heads_kv=2, head_dim=4, max_seq_len=8, attn_dropout=0.0,
        n_shared_experts=1, n_routed_experts=4, n_activated_experts=2,
        expert_hidden_dim=8, moe_balance_alpha=.01, moe_score_func="softmax",
        moe_n_groups=1, moe_topk_groups=1, moe_route_scale=1.0)
    values.update(changes)
    return source.MoDAConfig(**values)


def load_source(path, expected):
    raw = path.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected:
        raise ValueError("source SHA256 mismatch")
    spec = importlib.util.spec_from_file_location("frozen_openmythos_moda", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def bytes_of(value):
    return value.detach().cpu().contiguous().reshape(-1).view(torch.uint8).numpy().tobytes()


class Case(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(self.SEED)
        self.observations = []

    def close(self, actual, expected, label, atol, rtol):
        self.assertEqual(actual.shape, expected.shape)
        self.assertTrue(bool(torch.isfinite(actual).all()))
        self.assertTrue(bool(torch.isfinite(expected).all()))
        self.observations.append({"label": label, "shape": list(actual.shape),
            "actual_dtype": str(actual.dtype), "expected_dtype": str(expected.dtype),
            "max_abs_error": float((actual.detach().double() - expected.detach().double()).abs().max()),
            "atol": atol, "rtol": rtol})
        torch.testing.assert_close(actual, expected, atol=atol, rtol=rtol)

    def exact(self, actual, expected, label):
        self.assertEqual(actual.shape, expected.shape)
        self.assertEqual(actual.dtype, expected.dtype)
        if actual.is_floating_point() or actual.is_complex():
            self.assertTrue(bool(torch.isfinite(actual).all()))
            self.assertTrue(bool(torch.isfinite(expected).all()))
        okay = bytes_of(actual) == bytes_of(expected)
        self.observations.append({"label": label, "bitwise_equal": okay, "shape": list(actual.shape)})
        self.assertTrue(okay)

    def active(self, value, label):
        self.assertIsNotNone(value, label)
        okay = bool(torch.isfinite(value).all()) and bool(value.abs().max() > 0)
        self.observations.append({"label": label, "finite_nonzero": okay,
                                  "norm64": float(torch.linalg.vector_norm(value.detach().double()))})
        self.assertTrue(okay, label)


class RecordedResult(unittest.TextTestResult):
    def startTest(self, test):
        self.current_started = time.perf_counter()
        super().startTest(test)

    def record(self, test, status, reason=None):
        self.records.append({"Purpose": test.shortDescription() or test.id(),
            "Environment": self.environment,
            "Input": {"test_id": test.id(), "seed": test.SEED, "source_sha256": self.source_sha256},
            "Expected": "Declared exact identities or fixed numerical tolerances; finite gradients where specified",
            "Actual": {"observations": getattr(test, "observations", []), "reason": reason,
                       "seconds": time.perf_counter() - self.current_started}, "Status": status})

    def addSuccess(self, test):
        self.record(test, "PASS")
        super().addSuccess(test)

    def addFailure(self, test, error):
        self.record(test, "FAIL", self._exc_info_to_string(error, test))
        super().addFailure(test, error)

    def addError(self, test, error):
        self.record(test, "BLOCKED" if issubclass(error[0], (OSError, MemoryError)) else "FAIL", self._exc_info_to_string(error, test))
        super().addError(test, error)


def ids(suite):
    return [value for item in suite for value in (ids(item) if isinstance(item, unittest.TestSuite) else [item.id()])]


def main(test_class):
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--development", action="store_true")
    args = parser.parse_args()
    if not re.fullmatch("[0-9a-f]{64}", args.source_sha256):
        parser.error("full source SHA256 required")
    if args.report.exists():
        parser.error("refuse to overwrite a prior report")
    environment = {"python": sys.version, "torch": str(torch.__version__), "platform": platform.platform(),
        "development_only": args.development, "device": "cpu", "actual_source": str(args.source.resolve())}
    records, planned, status, reason = [], [], "NOT TESTED", None
    try:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(test_class)
        planned = sorted(ids(suite))
        if not args.development:
            if (platform.system() != "Linux" or platform.python_version() != "3.12.3"
                or sys.executable != TARGET_PYTHON or str(torch.__version__) != "2.11.0+cpu"
                or os.environ.get("CODESPACE_NAME") != SPACE or not sys.flags.isolated or not sys.dont_write_bytecode):
                raise OSError("designated frozen CPU runtime unavailable")
        torch.set_default_device("cpu")
        torch.set_default_dtype(torch.float32)
        torch.set_num_threads(2)
        torch.set_num_interop_threads(1)
        torch.use_deterministic_algorithms(True)
        if torch.cuda.is_available() or torch.is_autocast_enabled("cpu") or torch.is_autocast_enabled("cuda"):
            raise OSError("unexpected GPU or autocast availability/state")
        environment["torch_runtime"] = {"intra": torch.get_num_threads(), "interop": torch.get_num_interop_threads(),
            "dtype": str(torch.get_default_dtype()), "device": str(torch.get_default_device()),
            "deterministic": torch.are_deterministic_algorithms_enabled(), "cpu_autocast": torch.is_autocast_enabled("cpu"),
            "cuda_autocast": torch.is_autocast_enabled("cuda"), "env": {k: os.environ.get(k) for k in ENV}}
        if not (torch.get_num_threads() == 2 and torch.get_num_interop_threads() == 1
                and torch.get_default_dtype() == torch.float32 and str(torch.get_default_device()) == "cpu"
                and torch.are_deterministic_algorithms_enabled()):
            raise OSError("actual numerical runtime differs from frozen settings")
        test_class.source = load_source(args.source.resolve(), args.source_sha256)
        environment["torch_runtime_after_source"] = {"intra": torch.get_num_threads(), "interop": torch.get_num_interop_threads(),
            "dtype": str(torch.get_default_dtype()), "device": str(torch.get_default_device()),
            "deterministic": torch.are_deterministic_algorithms_enabled(), "cpu_autocast": torch.is_autocast_enabled("cpu"),
            "cuda_autocast": torch.is_autocast_enabled("cuda"), "env": {k: os.environ.get(k) for k in ENV}}
        if (environment["torch_runtime_after_source"] != environment["torch_runtime"]
                or torch.is_autocast_enabled("cpu") or torch.is_autocast_enabled("cuda")):
            raise OSError("source import changed numerical runtime")
        RecordedResult.records = records
        RecordedResult.environment = environment
        RecordedResult.source_sha256 = args.source_sha256
        result = unittest.TextTestRunner(verbosity=2, failfast=True, resultclass=RecordedResult).run(suite)
        status = "PASS" if result.wasSuccessful() and result.testsRun == len(planned) and not result.skipped else "FAIL"
        if any(row["Status"] == "BLOCKED" for row in records):
            status = "BLOCKED"
        if hashlib.sha256(args.source.read_bytes()).hexdigest() != args.source_sha256:
            status, reason = "FAIL", "source changed during tests"
    except BaseException as exc:
        status = "BLOCKED" if isinstance(exc, (OSError, MemoryError, KeyboardInterrupt)) else "FAIL"
        reason = repr(exc)
    tested = {r["Input"]["test_id"] for r in records}
    for identifier in planned:
        if identifier not in tested:
            records.append({"Purpose": identifier, "Environment": environment,
                "Input": {"test_id": identifier}, "Expected": "Run only after preceding checks PASS",
                "Actual": "Not reached due stop rule", "Status": "NOT TESTED"})
    report = {"Purpose": test_class.PURPOSE, "Environment": environment,
        "Input": {"source_sha256": args.source_sha256, "seed": test_class.SEED},
        "Expected": "All frozen mathematical fixtures PASS; no language-quality claim",
        "Actual": {"planned": len(planned), "run": len(tested), "test_ids": planned,
                   "counts": {s: sum(r["Status"] == s for r in records) for s in ("PASS", "FAIL", "BLOCKED", "NOT TESTED")},
                   "reason": reason, "tests": records}, "Status": status,
        "utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    with args.report.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write("\n")
    return 0 if status == "PASS" else 2
