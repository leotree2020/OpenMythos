"""Single frozen CPU development acceptance; never loads pretrained weights."""
import argparse
import contextlib
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time
import traceback
import unittest


UPSTREAM = "69284c13746e849104f738d6d1a347b1f457df76"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def protected(root):
    names = subprocess.check_output(["git", "-C", str(root), "ls-files", "-z"]).decode().split("\0")
    files = {name: digest((root / name).read_bytes()) for name in names if name}
    return {"head": git(root, "rev-parse", "HEAD"),
            "status": git(root, "status", "--porcelain=v1", "--untracked-files=all"),
            "files": files, "aggregate_sha256": digest(canonical(files))}


def packages():
    rows = sorted((d.metadata.get("Name", ""), d.version) for d in importlib.metadata.distributions())
    return {"entries": rows, "sha256": digest(canonical(rows))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--freeze-commit", required=True)
    parser.add_argument("--manifest-sha256", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.freeze_commit):
        parser.error("freeze-commit must be a full Git SHA")
    if not re.fullmatch(r"[0-9a-f]{64}", args.manifest_sha256):
        parser.error("manifest-sha256 must be a full SHA256")
    # Never overwrite an earlier attempt, including an incomplete one.
    args.output.mkdir(parents=True, exist_ok=False)
    root = Path(__file__).resolve().parent
    upstream = args.upstream.absolute()
    environment = {"python": sys.version, "executable": sys.executable,
                   "platform": platform.platform(), "machine": platform.machine(),
                   "isolated": sys.flags.isolated, "no_bytecode": sys.dont_write_bytecode,
                   "test_kind": "development synthetic / untrained native tiny; not 140M"}
    result = {"Purpose": "Validate isolated adaptive-depth engineering against pinned native CPU source",
              "Environment": environment,
              "Input": {"freeze_commit": args.freeze_commit, "source_directory": str(root),
                        "upstream": str(upstream), "upstream_pin": UPSTREAM},
              "Expected": "All frozen tests and preservation checks pass; native skips are BLOCKED",
              "Actual": {}, "Status": "NOT TESTED", "checks": [], "tests": [],
              "formal_140m_started": False, "quality_improvement": "NOT TESTED",
              "training_recovery": "NOT TESTED", "claude_mythos_parity": "NOT TESTED"}
    write_json(args.output / "CLAIM.json", result)
    before = package_before = None

    def check(name, condition, actual, expected=True):
        result["checks"].append({"Purpose": name, "Environment": "current CPU development process",
                                 "Input": args.freeze_commit, "Expected": expected,
                                 "Actual": actual, "Status": "PASS" if condition else "FAIL"})
        if not condition:
            raise AssertionError(name)

    class RecordedResult(unittest.TextTestResult):
        def record(self, test, status, actual):
            result["tests"].append({"Purpose": test.shortDescription() or test.id(),
                                     "Environment": "current CPU development process",
                                     "Input": test.id(),
                                     "Expected": "All assertions in the frozen test pass",
                                     "Actual": actual, "Status": status})

        def addSuccess(self, test):
            super().addSuccess(test)
            self.record(test, "PASS", "Assertions completed without failure")

        def addFailure(self, test, err):
            super().addFailure(test, err)
            self.record(test, "FAIL", self._exc_info_to_string(err, test))

        def addError(self, test, err):
            super().addError(test, err)
            self.record(test, "FAIL", self._exc_info_to_string(err, test))

        def addSkip(self, test, reason):
            super().addSkip(test, reason)
            self.record(test, "BLOCKED", reason)
            self.stop()

        def addExpectedFailure(self, test, err):
            super().addExpectedFailure(test, err)
            self.record(test, "FAIL", "Expected failures are forbidden: " + self._exc_info_to_string(err, test))
            self.stop()

        def addUnexpectedSuccess(self, test):
            super().addUnexpectedSuccess(test)
            self.record(test, "FAIL", "Unexpected success cannot bypass a frozen failing test")
            self.stop()

        def addSubTest(self, test, subtest, err):
            super().addSubTest(test, subtest, err)
            if err is not None:
                self.record(subtest, "FAIL", self._exc_info_to_string(err, test))

    started = time.monotonic()
    with (args.output / "stdout.log").open("w", encoding="utf-8") as stdout, \
            (args.output / "stderr.log").open("w", encoding="utf-8") as stderr, \
            contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        try:
            upstream = upstream.resolve(strict=True)
            check("isolated interpreter with bytecode disabled",
                  bool(sys.flags.isolated and sys.dont_write_bytecode), environment)
            manifest_path = root / "SOURCE_MANIFEST.json"
            manifest_bytes = manifest_path.read_bytes()
            check("source manifest identity", digest(manifest_bytes) == args.manifest_sha256,
                  digest(manifest_bytes), args.manifest_sha256)
            manifest = json.loads(manifest_bytes)
            check("exact executable source inventory", set(manifest["files"]) == {
                "adaptive_depth.py", "test_adaptive_depth.py", "run_development.py"},
                sorted(manifest["files"]))
            for name, expected in manifest["files"].items():
                data = (root / name).read_bytes()
                actual = {"bytes": len(data), "sha256": digest(data)}
                check("source identity " + name, actual == expected, actual, expected)
            before = protected(upstream)
            write_json(args.output / "UPSTREAM_BEFORE.json", before)
            check("pinned clean upstream", before["head"] == UPSTREAM and not before["status"],
                  {"head": before["head"], "status": before["status"]})
            package_before = packages()
            write_json(args.output / "PACKAGES_BEFORE.json", package_before)
            for name, value in {"CUDA_VISIBLE_DEVICES": "", "OMP_NUM_THREADS": "1",
                                "MKL_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
                                "PYTHONDONTWRITEBYTECODE": "1"}.items():
                os.environ[name] = value
            os.environ["MYTHOS_PARCAE_UPSTREAM"] = str(upstream)
            import torch
            torch.set_default_device("cpu")
            torch.set_default_dtype(torch.float32)
            torch.set_num_threads(1)
            torch.set_num_interop_threads(1)
            torch.use_deterministic_algorithms(True)
            def runtime():
                return {"torch": torch.__version__, "device": str(torch.get_default_device()),
                                "dtype": str(torch.get_default_dtype()), "threads": torch.get_num_threads(),
                                "interop": torch.get_num_interop_threads(),
                                "deterministic": torch.are_deterministic_algorithms_enabled(),
                                "warn_only": torch.is_deterministic_algorithms_warn_only_enabled(),
                                "autocast_cpu": torch.is_autocast_enabled("cpu"),
                                "autocast_cuda": torch.is_autocast_enabled("cuda")}
            runtime_before = runtime()
            environment.update(runtime_before)
            check("CPU deterministic runtime", environment["device"] == "cpu"
                  and environment["dtype"] == "torch.float32" and environment["threads"] == 1
                  and environment["interop"] == 1 and environment["deterministic"]
                  and not environment["warn_only"]
                  and not environment["autocast_cpu"] and not environment["autocast_cuda"], environment)
            sys.path.insert(0, str(root))
            spec = importlib.util.spec_from_file_location("test_adaptive_depth", root / "test_adaptive_depth.py")
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            check("runtime unchanged after test imports", runtime() == runtime_before, runtime(), runtime_before)
            suite = unittest.defaultTestLoader.loadTestsFromModule(module)
            planned = suite.countTestCases()

            def test_ids(node):
                if isinstance(node, unittest.TestSuite):
                    return [value for child in node for value in test_ids(child)]
                return [node.id()]

            discovered = sorted(test_ids(suite))
            expected_ids = manifest["test_ids"]
            native_ids = manifest["required_native_test_ids"]
            check("exact frozen test discovery", planned > 0 and discovered == sorted(expected_ids)
                  and len(discovered) == len(set(discovered)) and bool(native_ids)
                  and set(native_ids).issubset(discovered), discovered, expected_ids)
            outcome = unittest.TextTestRunner(stream=stderr, verbosity=2, failfast=True,
                                              resultclass=RecordedResult).run(suite)
            result["Actual"].update({"planned_tests": planned, "run_tests": outcome.testsRun,
                                      "failures": len(outcome.failures), "errors": len(outcome.errors),
                                      "skipped": len(outcome.skipped),
                                      "expected_failures": len(outcome.expectedFailures),
                                      "unexpected_successes": len(outcome.unexpectedSuccesses),
                                      "not_run": planned - outcome.testsRun})
            has_failure = bool(outcome.failures or outcome.errors or outcome.expectedFailures
                               or outcome.unexpectedSuccesses
                               or any(row["Status"] == "FAIL" for row in result["tests"]))
            result["Status"] = ("FAIL" if has_failure else "BLOCKED" if outcome.skipped
                                else "PASS" if outcome.wasSuccessful()
                                and not outcome.expectedFailures and not outcome.unexpectedSuccesses
                                and outcome.testsRun == planned
                                and len(result["tests"]) == planned
                                and all(row["Status"] == "PASS" for row in result["tests"])
                                else "FAIL")
            if result["Status"] == "PASS":
                check("full suite completion", outcome.testsRun == planned, outcome.testsRun, planned)
        except (ModuleNotFoundError, FileNotFoundError) as error:
            result["Status"] = "BLOCKED"
            result["Actual"]["exception"] = repr(error)
            traceback.print_exc()
        except (KeyboardInterrupt, SystemExit) as error:
            result["Status"] = "BLOCKED"
            result["Actual"]["interruption"] = repr(error)
            traceback.print_exc()
        except Exception as error:
            result["Status"] = "FAIL"
            result["Actual"]["exception"] = repr(error)
            traceback.print_exc()
        finally:
            try:
                if "runtime_before" in locals():
                    check("runtime unchanged after tests", runtime() == runtime_before, runtime(), runtime_before)
                if before is not None:
                    after = protected(upstream)
                    write_json(args.output / "UPSTREAM_AFTER.json", after)
                    check("upstream tracked bytes and Git state unchanged", before == after,
                          {"equal": before == after, "sha256": after["aggregate_sha256"]})
                if package_before is not None:
                    package_after = packages()
                    write_json(args.output / "PACKAGES_AFTER.json", package_after)
                    check("dependency inventory unchanged", package_before == package_after,
                          {"equal": package_before == package_after, "sha256": package_after["sha256"]})
                if "manifest" in locals():
                    for name, expected in manifest["files"].items():
                        data = (root / name).read_bytes()
                        check("source unchanged " + name,
                              {"bytes": len(data), "sha256": digest(data)} == expected,
                              digest(data), expected["sha256"])
            except BaseException as error:
                result["Status"] = "FAIL"
                result["Actual"]["preservation_exception"] = repr(error)
                traceback.print_exc()
    result["Actual"]["elapsed_seconds"] = time.monotonic() - started
    write_json(args.output / "DEVELOPMENT_RESULTS.json", result)
    print(json.dumps({"Status": result["Status"], "Actual": result["Actual"],
                      "evidence": str(args.output)}))
    return 0 if result["Status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
