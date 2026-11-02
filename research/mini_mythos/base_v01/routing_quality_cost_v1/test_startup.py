"""Real operator/worker startup contracts with stdlib-only synthetic target stubs."""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import struct
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parent
EXPECTED_BASE = "a4e9b27ff3c7ca8dbfd5760d5c630f59a9d0a683"
EXPECTED_BRANCH = "mythos-routing-quality-cost-cpu-v1"
EXPECTED_REPO = "/workspaces/" + EXPECTED_BRANCH
FREEZE = "c" * 40
ORIGINAL_DATA_FREEZE = "d" * 40


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


worker = load("quality_cost_startup_worker_under_test", ROOT / "run_quality.py")
operator = load("quality_cost_startup_operator_under_test", ROOT / "execute_once.py")


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


class ReachedPreTorch(BaseException):
    """Exit precisely before the first frozen helper import and before Torch."""


class TargetFixture:
    """Virtual Linux paths; no reads of /workspaces or real model/corpus bytes."""

    def __init__(self):
        self.files, self.asset_metadata, self.saved, self.checks, self.git_calls = {}, {}, {}, [], []
        fixture = self

        class VirtualPath(PurePosixPath):
            def resolve(self):
                return self

            def read_text(self, encoding="utf-8"):
                return fixture.files[str(self)].decode(encoding)

        self.Path = VirtualPath
        self.root = "/fixture/quality-cost-attempt"
        self.inputs = self.root + "/data/private/inputs.json"
        self.completion = self.root + "/data/public/completion.json"
        self.source_manifest = self.root + "/operator/source_manifest.json"
        self.spec = {
            "repo": EXPECTED_REPO, "branch": EXPECTED_BRANCH,
            "upstream": "/fixture/upstream", "model_dir": "/fixture/model",
            "inputs_path": self.inputs, "data_manifest_path": self.completion,
            "source_manifest_path": self.source_manifest,
            "freeze_commit": FREEZE, "expected_head": FREEZE,
            "prior_run_dir": "/workspaces/mythos-evidence/base_v01/routing_feasibility/attempt-v3",
        }
        samples = []
        for index in range(16):
            tokens = [100 + index] * 128
            samples.append({"index": index, "tokens": tokens,
                "source_article_key": "fixture-source-" + str(index),
                "article_id": f"fixture-article-{index:03d}", "heading_row": index * 10,
                "input_ids_sha256": digest(canonical(tokens)),
                "raw_input_sha256": digest(struct.pack("<128q", *tokens))})
        self.payload = {"context_tokens": 128, "seeds": [3101, 3202], "samples": samples}
        self.put(self.inputs, self.payload)
        # Explicit synthetic byte-metadata stub: never load real frozen tokens.
        # Mutation returns real fixture metadata so byte-change rejection still exercises production guards.
        self.frozen_input_fixture_bytes = self.files[self.inputs]
        self.frozen_input_metadata = {"bytes": 58091, "sha256": "ae5f8ad5fd53d25afaf29487a650dc0300528b0926c9883652475c4ca7db127f"}
        self.original_data_spec = {"repo": "/workspaces/mythos-routing-feasibility-cpu-v2",
                                   "freeze_commit": ORIGINAL_DATA_FREEZE,
                                   "corpus": "/fixture/original/test.parquet"}
        self.data_completion = {"Status": "PASS", "Input": copy.deepcopy(self.original_data_spec),
            "Actual": {"sample_count": 16, "case_count": 32, "context_tokens": 128},
            "artifacts": {"private/inputs.json": self.info(self.inputs),
                          "public/selection.json": {"bytes": 123, "sha256": "e" * 64}}}
        self.put(self.completion, self.data_completion)
        extra = EXPECTED_REPO + "/research/synthetic_startup_source.txt"
        self.files[extra] = b"Synthetic fixture source; no model data.\n"
        self.put(self.source_manifest, {extra: self.info(extra)})
        self.spec.update(inputs_sha256=self.info(self.inputs)["sha256"],
                         data_manifest_sha256=self.info(self.completion)["sha256"],
                         source_manifest_sha256=self.info(self.source_manifest)["sha256"])
        # Model/source metadata is explicitly stubbed; no real weights are read.
        for path, pin in {
            "/fixture/model/pytorch_model.bin": worker.WEIGHTS_SHA,
            "/fixture/model/config.json": worker.CONFIG_SHA,
            EXPECTED_REPO + "/research/mini_mythos/base_v01/adaptive_depth_v1/adaptive_depth.py": worker.LIBRARY_SHA,
            EXPECTED_REPO + "/research/mini_mythos/base_v01/depth_16_32_v1/run_depth_budget.py": worker.HELPER_SHA,
            EXPECTED_REPO + "/research/mini_mythos/base_v01/adaptive_140m_smoke_v1/run_smoke.py": worker.SMOKE_SHA,
        }.items():
            self.asset_metadata[path] = {"bytes": 1, "sha256": pin}
        self.git_repo = {"head": FREEZE, "branch": EXPECTED_BRANCH, "status": ""}
        self.run = SimpleNamespace(spec=self.spec, public=self.Path(self.root + "/worker/public"),
                                   private=self.Path(self.root + "/worker/private"), check=self.check)
        self.smoke = SimpleNamespace(git_state=self.git_state, git=self.git, load_module=self.pre_torch_boundary)
        self.helper_boundary_count = 0

    def put(self, path, value):
        self.files[str(path)] = canonical(value)

    def info(self, path):
        name = str(path)
        if name == self.inputs and self.files[name] == self.frozen_input_fixture_bytes:
            return dict(self.frozen_input_metadata)
        if name in self.asset_metadata:
            return dict(self.asset_metadata[name])
        raw = self.files[name]
        return {"bytes": len(raw), "sha256": digest(raw)}

    def save(self, path, value):
        name = str(path)
        if name in self.saved:
            raise FileExistsError(name)
        self.saved[name] = copy.deepcopy(value)

    def check(self, purpose, okay, actual=None, expected=True, failure="FAIL"):
        self.checks.append((purpose, bool(okay)))
        if not okay:
            raise worker.Stop(failure, purpose, actual)

    def git_state(self, path):
        if str(path) == self.spec["upstream"]:
            return {"head": worker.UPSTREAM_SHA, "branch": "fixture-upstream", "status": ""}
        return dict(self.git_repo)

    def git(self, path, *args):
        self.git_calls.append((str(path), args))
        return ""

    def pre_torch_boundary(self, name, path, expected):
        self.helper_boundary_count += 1
        if name != "mythos_routing_frozen_helpers" or expected != worker.HELPER_SHA:
            raise AssertionError("Unexpected first helper import")
        raise ReachedPreTorch()

    def execute(self):
        with ExitStack() as stack:
            stack.enter_context(patch.object(worker, "Path", self.Path))
            stack.enter_context(patch.object(worker, "info", self.info))
            stack.enter_context(patch.object(worker, "save", self.save))
            stack.enter_context(patch.object(worker.platform, "system", return_value="Linux"))
            stack.enter_context(patch.object(worker.platform, "python_version", return_value="3.12.3"))
            stack.enter_context(patch.object(worker.sys, "executable", worker.PYTHON))
            stack.enter_context(patch.object(worker.sys, "flags", SimpleNamespace(isolated=1)))
            stack.enter_context(patch.object(worker.sys, "dont_write_bytecode", True))
            stack.enter_context(patch.dict(os.environ, {"CODESPACE_NAME": worker.SPACE}))
            worker.execute(self.run, self.smoke)


class StartupTests(unittest.TestCase):
    def tearDown(self):
        self.assertFalse({"torch", "numpy", "tokenizers", "pyarrow", "parcae_lm", "receval"} & set(sys.modules))

    def reject(self, fixture, reason):
        with self.assertRaises(worker.Stop) as raised:
            fixture.execute()
        self.assertEqual(raised.exception.status, "FAIL")
        self.assertEqual(str(raised.exception), reason)
        self.assertEqual(fixture.helper_boundary_count, 0)

    def test_operator_command_and_worker_identity_match(self):
        """Production launcher command uses the quality/cost worker and matching immutable identity."""
        spec, out = Path("/fixture/operator/spec.json"), Path("/fixture/worker")
        command = operator.worker_command(spec, out)
        self.assertEqual(command, [operator.PYTHON, "-I", "-B", str(ROOT / "run_quality.py"),
                                   "--spec", str(spec), "--out", str(out)])
        self.assertEqual(worker.PYTHON, operator.PYTHON)
        self.assertEqual(worker.BRANCH, operator.BRANCH)
        self.assertEqual(worker.BRANCH, EXPECTED_BRANCH)
        self.assertEqual(worker.EXPECTED_REPO, operator.EXPECTED_REPO.as_posix())
        self.assertEqual(worker.EXPECTED_REPO, EXPECTED_REPO)
        self.assertEqual(worker.BASE, EXPECTED_BASE)

    def test_matching_startup_reaches_pre_torch_boundary(self):
        """The real execute path accepts the intended contract before any numerical import."""
        fixture = TargetFixture()
        with self.assertRaises(ReachedPreTorch):
            fixture.execute()
        self.assertEqual(fixture.helper_boundary_count, 1)
        self.assertTrue(fixture.checks and all(okay for _, okay in fixture.checks))
        self.assertEqual(fixture.git_calls, [(EXPECTED_REPO, ("merge-base", "--is-ancestor", EXPECTED_BASE, FREEZE)),
                                             (EXPECTED_REPO, ("merge-base", "--is-ancestor", FREEZE, FREEZE))])
        self.assertIn(fixture.root + "/worker/public/input_inventory.json", fixture.saved)

    def test_old_v1_identity_rejected(self):
        """V1 branch/worktree cannot be mistaken for the new authorized execution identity."""
        fixture = TargetFixture()
        fixture.spec.update(repo="/workspaces/mythos-routing-feasibility-cpu-v1", branch="mythos-routing-feasibility-cpu-v1")
        self.reject(fixture, "designated routing worktree and branch")

    def test_old_v2_identity_rejected(self):
        """V2 branch/worktree cannot pass the quality/cost worker even with otherwise valid fixtures."""
        fixture = TargetFixture()
        fixture.spec.update(repo="/workspaces/mythos-routing-feasibility-cpu-v2", branch="mythos-routing-feasibility-cpu-v2")
        self.reject(fixture, "designated routing worktree and branch")

    def test_old_v3_identity_rejected(self):
        """The accepted routing V3 checkout cannot masquerade as this new experiment."""
        fixture = TargetFixture()
        fixture.spec.update(repo="/workspaces/mythos-routing-feasibility-cpu-v3", branch="mythos-routing-feasibility-cpu-v3")
        self.reject(fixture, "designated routing worktree and branch")

    def test_data_and_audit_cli_contracts(self):
        """Production data and audit commands use the correct new script and isolated interpreter."""
        spec, out, run = Path("/fixture/spec.json"), Path("/fixture/report.json"), Path("/fixture/run")
        self.assertEqual(operator.data_command(spec, out), [operator.DATA_PYTHON, "-I", "-B", str(ROOT / "data_quality.py"), "--spec", str(spec), "--out", str(out)])
        self.assertEqual(operator.audit_command(run, out), [operator.DATA_PYTHON, "-I", "-B", str(ROOT / "audit_quality.py"), "--run", str(run), "--output", str(out)])

    def test_worker_manifest_excludes_label_bytes(self):
        """The worker never reads target label bytes; labels stay protected by the operator."""
        labels = str(operator.RUN / "data/private/labels.json")
        inputs = str(operator.RUN / "data/private/inputs.json")
        original = {labels: {"sha256": "a" * 64}, inputs: {"sha256": "b" * 64}}
        snapshot = copy.deepcopy(original)
        self.assertEqual(operator.worker_manifest(original), {inputs: snapshot[inputs]})
        self.assertEqual(original, snapshot)

    def test_wrong_prior_evidence_path_rejected(self):
        """A different prior run cannot supply the frozen comparison evidence."""
        fixture = TargetFixture()
        fixture.spec["prior_run_dir"] = "/fixture/wrong-prior"
        self.reject(fixture, "fixed prior V3 evidence path")

    def test_self_consistent_wrong_prefix_pin_rejected(self):
        """A resigned synthetic data artifact still cannot replace the frozen real-prefix identity."""
        fixture = TargetFixture()
        fixture.frozen_input_metadata = {"bytes": 58091, "sha256": "1" * 64}
        fixture.spec["inputs_sha256"] = "1" * 64
        fixture.data_completion["artifacts"]["private/inputs.json"] = dict(fixture.frozen_input_metadata)
        fixture.put(fixture.completion, fixture.data_completion)
        fixture.spec["data_manifest_sha256"] = fixture.info(fixture.completion)["sha256"]
        self.reject(fixture, "unchanged128-token inputs exact prior bytes")

    def test_wrong_execution_head_rejected(self):
        """A clean checkout at the wrong commit fails before helper/model import."""
        fixture = TargetFixture()
        fixture.git_repo["head"] = "f" * 40
        self.reject(fixture, "frozen clean execution checkout")

    def test_dirty_checkout_rejected(self):
        """Uncommitted checkout changes cannot enter the frozen worker."""
        fixture = TargetFixture()
        fixture.git_repo["status"] = " M synthetic.py"
        self.reject(fixture, "frozen clean execution checkout")

    def test_changed_source_manifest_rejected(self):
        """Source manifest bytes are bound to the operator spec before using its entries."""
        fixture = TargetFixture()
        fixture.files[fixture.source_manifest] += b" "
        self.reject(fixture, "source manifest hash")

    def test_changed_data_completion_rejected(self):
        """Copied data completion must retain the sealed byte identity."""
        fixture = TargetFixture()
        fixture.files[fixture.completion] += b" "
        self.reject(fixture, "new data manifest hash")

    def test_changed_private_input_rejected(self):
        """Private prepared input bytes cannot change between operator and worker."""
        fixture = TargetFixture()
        fixture.files[fixture.inputs] += b" "
        self.reject(fixture, "new input payload hash")

    def test_data_artifact_binding_rejected(self):
        """A self-consistent completion hash cannot hide a stale private-input artifact pin."""
        fixture = TargetFixture()
        fixture.data_completion["artifacts"]["private/inputs.json"]["sha256"] = "0" * 64
        fixture.put(fixture.completion, fixture.data_completion)
        fixture.spec["data_manifest_sha256"] = fixture.info(fixture.completion)["sha256"]
        self.reject(fixture, "data completion binds exact16sample32call inputs")

    def test_nonpassing_data_stage_rejected(self):
        """A failed data stage stops before model work even if all input hashes match."""
        fixture = TargetFixture()
        fixture.data_completion["Status"] = "FAIL"
        fixture.put(fixture.completion, fixture.data_completion)
        fixture.spec["data_manifest_sha256"] = fixture.info(fixture.completion)["sha256"]
        self.reject(fixture, "Data stage did not pass")

    def test_reused_v2_data_provenance_stays_unchanged(self):
        """Copied data keeps its historical V2 provenance while new worker paths bind the copy."""
        fixture = TargetFixture()
        before = dict(fixture.files)
        with self.assertRaises(ReachedPreTorch):
            fixture.execute()
        self.assertEqual(fixture.files, before)
        self.assertEqual(json.loads(fixture.files[fixture.completion])["Input"], fixture.original_data_spec)
        self.assertNotEqual(fixture.original_data_spec["freeze_commit"], fixture.spec["freeze_commit"])
        inventory = fixture.saved[fixture.root + "/worker/public/input_inventory.json"]
        self.assertEqual(inventory["data_manifest_sha256"], digest(before[fixture.completion]))
        self.assertEqual(fixture.saved[fixture.root + "/worker/private/input_prefixes.json"], fixture.payload)


def canonical_id(test):
    ident = test.id()
    return "test_startup." + ident.split(".", 1)[1] if ident.startswith("__main__.") else ident


class Recorded(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.records.append({"id": canonical_id(test), "Purpose": test.shortDescription(), "Status": "PASS"})

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.records.append({"id": canonical_id(test), "Purpose": test.shortDescription(), "Status": "FAIL", "detail": self._exc_info_to_string(err, test)})

    def addError(self, test, err):
        super().addError(test, err)
        self.records.append({"id": canonical_id(test), "Purpose": test.shortDescription(), "Status": "FAIL", "detail": self._exc_info_to_string(err, test)})

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.records.append({"id": canonical_id(test), "Purpose": test.shortDescription(), "Status": "NOT TESTED", "detail": reason})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    if not args.report.is_absolute() or args.report.exists():
        parser.error("report must be an absolute new path; no overwrite")
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(StartupTests)
    expected = sorted(canonical_id(t) for t in suite)
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=Recorded, failfast=True).run(suite)
    okay = result.wasSuccessful() and result.testsRun == len(expected) and not result.skipped and not result.expectedFailures and not result.unexpectedSuccesses
    report = {"Purpose": "Real quality/cost operator/worker startup-contract synthetic fixtures; no model or target data",
        "Environment": {"python": sys.version, "executable": sys.executable, "fixture_target": "Virtual Linux paths and stdlib stubs only"},
        "Input": {"planned_test_ids": expected, "source_sha256": {p.name: digest(p.read_bytes()) for p in (Path(__file__).resolve(), ROOT / "execute_once.py", ROOT / "run_quality.py")}},
        "Expected": "All declared tests pass with zero skips, errors or numerical imports; startup accepts current worktree and rejects stale identity/tampering",
        "Actual": {"test_ids": sorted(r["id"] for r in result.records), "planned": len(expected), "run": result.testsRun,
            "failures": len(result.failures), "errors": len(result.errors), "skipped": len(result.skipped),
            "expected_failures": len(result.expectedFailures), "unexpected_successes": len(result.unexpectedSuccesses),
            "tests": result.records, "unittest_output": stream.getvalue()}, "Status": "PASS" if okay else "FAIL"}
    with args.report.open("x", encoding="utf-8", newline="\n") as out:
        json.dump(report, out, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        out.write("\n")
    print(stream.getvalue(), file=sys.stderr, end="")
    print(json.dumps({"Status": report["Status"], "tests": result.testsRun, "report": str(args.report)}), flush=True)
    return 0 if okay else 2


if __name__ == "__main__":
    sys.exit(main())
