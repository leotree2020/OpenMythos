"""Bounded, stdlib-only strace calibration; not a Mythos model experiment."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
import traceback


LAUNCHER_SHA256 = "8083b948eebdf08c2d14a79d940ccead72db5f10c6bac8d9061816b6c9ea05c3"


class ProbeStop(Exception):
    pass


def save(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json_ready(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def process(pid):
    root = Path("/proc") / str(pid)
    raw = (root / "stat").read_text(encoding="utf-8")
    fields = raw[raw.rfind(")") + 2:].split()
    status = (root / "status").read_text(encoding="utf-8")
    uid_line = next(line for line in status.splitlines() if line.startswith("Uid:"))
    blocked_line = next(line for line in status.splitlines() if line.startswith("SigBlk:"))
    return {
        "pid": pid, "ppid": int(fields[1]), "pgid": int(fields[2]),
        "sid": int(fields[3]), "starttime_ticks": int(fields[19]),
        "uid": int(uid_line.split()[1]),
        "cgroup": (root / "cgroup").read_text(encoding="utf-8"),
        "sigterm_blocked": bool(int(blocked_line.split()[1], 16) & (1 << (signal.SIGTERM - 1))),
    }


def same_live_identity(saved):
    try:
        current = process(saved["pid"])
    except FileNotFoundError:
        return False
    return all(current[key] == saved[key] for key in ("pid", "uid", "starttime_ticks", "pgid", "sid"))


def children(pid):
    text = (Path("/proc") / str(pid) / "task" / str(pid) / "children").read_text(encoding="utf-8")
    return [int(value) for value in text.split()]


def check(report, name, expected, actual, passed):
    report["checks"].append({
        "Purpose": name, "Environment": "Linux; frozen CPU Python 3.12; strace 6.8; stdlib fixture",
        "Input": {"case": report["case"]}, "Expected": expected, "Actual": actual,
        "Status": "PASS" if passed else "FAIL",
    })
    if not passed:
        raise ProbeStop(name)


def discover_group(launcher_pid):
    try:
        for pid in children(launcher_pid):
            entry = process(pid)
            if entry["ppid"] == launcher_pid and entry["pid"] == entry["pgid"] == entry["sid"]:
                return entry
    except (FileNotFoundError, ProcessLookupError):
        pass
    return None


def timeout_cleanup(launcher, launcher_identity, owned_group, report, observer_identity=None):
    # This is reached only after this case's bounded observation deadline.
    # Never select a target by name; ownership is a recorded live /proc identity.
    events = []
    identities = [entry for entry in (owned_group, launcher_identity, observer_identity) if entry is not None]
    for signum in (signal.SIGTERM, signal.SIGKILL):
        for entry in identities:
            if entry["pgid"] != entry["pid"] or not same_live_identity(entry):
                events.append({"signal": int(signum), "pgid": entry["pgid"], "sent": False,
                               "reason": "leader absent or recorded ownership no longer verifiable"})
                continue
            event = {"sender_pid": os.getpid(), "sender_uid": os.getuid(),
                     "signal": int(signum), "pgid": entry["pgid"],
                     "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                     "monotonic_ns": time.monotonic_ns(), "reason": "probe deadline exceeded"}
            try:
                os.killpg(entry["pgid"], signum)
                event["sent"] = True
            except ProcessLookupError:
                event["sent"] = False
            except BaseException as exc:
                event["sent"] = False
                event["error"] = repr(exc)
            events.append(event)
        if signum == signal.SIGTERM:
            time.sleep(1.0)
    try:
        launcher.wait(timeout=2)
    except BaseException as exc:
        events.append({"wait_error": repr(exc)})
    report["timeout_cleanup"] = events


def run_case(args, root, mode):
    case = root / mode
    case.mkdir()
    operator_root = case / "operator"
    operator_root.mkdir()
    launcher_copy = operator_root / "mythos_launch.py"
    with launcher_copy.open("xb") as stream:
        stream.write(args.launcher.read_bytes())
    trace = operator_root / "signals.log"
    command = [str(args.strace), "-D", "-f", "-ttt", "-e", "trace=none", "-e",
               "signal=SIGTERM,SIGINT,SIGHUP", "-o", str(trace), "--", str(args.python),
               "-I", "-B", str(args.fixture), "coordinator", "--case-dir", str(case), "--mode", mode]
    save(operator_root / "config.json", {"command": command, "cwd": str(case), "timeout_seconds": 130})
    report = {"case": mode, "status": "NOT TESTED", "checks": [], "command": command,
              "historical_sender": "UNKNOWN", "model_or_weights_loaded": False}
    launcher = None
    launcher_identity = None
    observer = None
    observer_identity = None
    owned_group = None
    first_error = None
    start = time.monotonic()
    deadline = start + 145.0  # Reserve at most three seconds for owned-process cleanup.
    try:
        with (case / "launcher_stdout.log").open("xb") as out, (case / "launcher_stderr.log").open("xb") as err, \
             (case / "observer_stdout.log").open("xb") as observer_out, (case / "observer_stderr.log").open("xb") as observer_err:
            launcher = subprocess.Popen([str(args.python), "-I", "-B", str(launcher_copy),
                                         "--config", str(operator_root / "config.json")],
                                        cwd=str(case), stdout=out, stderr=err, start_new_session=True)
            launcher_identity = process(launcher.pid)
            save(operator_root / "launch_observation.json", {
                "pid": launcher.pid, "pid_starttime": str(launcher_identity["starttime_ticks"]),
            })
            if args.observer is not None:
                observer = subprocess.Popen([str(args.python), "-I", "-B", str(args.observer),
                                             "--operator-dir", str(operator_root), "--launcher-pid", str(launcher.pid)],
                                            cwd=str(case), stdout=observer_out, stderr=observer_err, start_new_session=True)
                observer_identity = process(observer.pid)
            identities_checked = False
            while launcher.poll() is None and time.monotonic() < deadline:
                if owned_group is None:
                    owned_group = discover_group(launcher.pid)
                worker = read_json_ready(case / "worker_ready.json")
                coord = read_json_ready(case / "coordinator_ready.json")
                claim = read_json_ready(operator_root / "claim.json")
                if worker is not None and coord is not None and claim is not None and not identities_checked:
                    identities_checked = True
                    try:
                        live_worker = process(worker["pid"])
                        live_coord = process(coord["pid"])
                        direct = children(launcher.pid)
                        observation = {"launcher": launcher_identity, "launcher_claim": claim,
                                       "launcher_children": direct, "coordinator": live_coord,
                                       "worker": live_worker, "controller": process(os.getpid())}
                        save(case / "identity_observation.json", observation)
                        check(report, "-D preserves direct child identity", "coordinator is the only direct launcher child",
                              observation, claim["pid"] == launcher.pid and direct == [coord["pid"]]
                              and coord["ppid"] == launcher.pid and live_coord["ppid"] == launcher.pid
                              and live_coord["pid"] == live_coord["pgid"] == live_coord["sid"]
                              and live_worker["ppid"] == coord["pid"]
                              and live_worker["pgid"] == live_coord["pgid"])
                        check(report, "fixture identity is current and owned", "ready identities equal /proc; same uid",
                              {"coordinator": live_coord, "worker": live_worker},
                              all(all(saved[key] == current[key] for key in
                                      ("pid", "ppid", "pgid", "sid", "uid", "starttime_ticks"))
                                  for saved, current in ((coord, live_coord), (worker, live_worker)))
                              and live_coord["uid"] == live_worker["uid"] == os.getuid())
                        check(report, "SIGTERM remains unblocked", False,
                              {"coordinator_ready": coord["sigterm_blocked"], "worker_ready": worker["sigterm_blocked"],
                               "coordinator_live": live_coord["sigterm_blocked"], "worker_live": live_worker["sigterm_blocked"]},
                              not any(entry["sigterm_blocked"] for entry in (coord, worker, live_coord, live_worker)))
                        check(report, "stdlib-only isolated processes", "-I -B; no torch/numpy/tokenizers",
                              {"coordinator": coord["numeric_modules_loaded"], "worker": worker["numeric_modules_loaded"]},
                              all(not entry["numeric_modules_loaded"] and entry["isolated"]
                                  and entry["dont_write_bytecode"] and entry["python"] == str(args.python)
                                  and entry["prefix"] == sys.prefix for entry in (coord, worker))
                              and claim["numerical_libraries_imported"] is False
                              and claim["source_sha256"] == LAUNCHER_SHA256)
                        owned_group = live_coord
                        if mode == "term":
                            if not same_live_identity(live_worker):
                                raise ProbeStop("worker identity changed before known signal")
                            event = {"sender_pid": os.getpid(), "sender_uid": os.getuid(),
                                     "target_pid": live_worker["pid"], "target_starttime_ticks": live_worker["starttime_ticks"],
                                     "signal": int(signal.SIGTERM), "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                     "monotonic_ns": time.monotonic_ns()}
                            save(case / "signal_intent.json", event)
                            os.kill(live_worker["pid"], signal.SIGTERM)
                            save(case / "signal_sent.json", event)
                    except BaseException as exc:
                        first_error = {"type": type(exc).__name__, "error": repr(exc), "traceback": traceback.format_exc()}
                time.sleep(0.05)
            if launcher.poll() is None:
                report["status"] = "BLOCKED"
                timeout_cleanup(launcher, launcher_identity, owned_group, report, observer_identity)
                raise TimeoutError("probe exceeded its 145 second observation deadline")
            report["launcher_returncode"] = launcher.returncode
            if observer is not None:
                while observer.poll() is None and time.monotonic() < deadline:
                    time.sleep(0.05)
                if observer.poll() is None:
                    timeout_cleanup(launcher, launcher_identity, owned_group, report, observer_identity)
                    raise TimeoutError("passive observer exceeded the shared case deadline")
        if first_error is not None:
            report["first_error"] = first_error
            raise ProbeStop("ready-time check failed; no later case permitted")
        if not identities_checked:
            report["startup_evidence"] = {
                "child_stderr": (operator_root / "stderr.log").read_text(encoding="utf-8", errors="replace"),
                "launcher_stderr": (case / "launcher_stderr.log").read_text(encoding="utf-8", errors="replace"),
            }
            raise RuntimeError("Fixture readiness was not established; inspect preserved startup/strace errors")
        check(report, "fixture ready was observed", True, identities_checked, identities_checked)
        completion = json.loads((operator_root / "completion.json").read_text(encoding="utf-8"))
        worker_result = json.loads((case / "worker_result.json").read_text(encoding="utf-8"))
        coord_result = json.loads((case / "coordinator_result.json").read_text(encoding="utf-8"))
        expected_rc = 0 if mode == "normal" else 2
        expected_status = "COMPLETED" if mode == "normal" else "CHILD_FAILED"
        check(report, "launcher preserves child exit and does not clean up", {"status": expected_status, "returncode": expected_rc},
              completion, completion.get("status") == expected_status and completion.get("returncode") == expected_rc
              and launcher.returncode == expected_rc and "cleanup" not in completion and "exception" not in completion)
        check(report, "coordinator preserves worker exit", expected_rc, coord_result["returncode"],
              coord_result["returncode"] == expected_rc)
        expected_worker = "WORKER_READY " + mode + "\n" + ("WORKER_COMPLETE\n" if mode == "normal" else "WORKER_SIGNAL 15\n")
        expected_stdout = (expected_worker + "COORDINATOR_RC " + str(expected_rc) + "\n").encode()
        stdout = (operator_root / "stdout.log").read_bytes()
        stderr = (operator_root / "stderr.log").read_bytes()
        check(report, "stdout and markers are byte-exact", expected_stdout.hex(), stdout.hex(), stdout == expected_stdout
              and coord_result["worker_stdout_hex"] == expected_worker.encode().hex())
        all_stderr = {"child": stderr.hex(), "worker": coord_result["worker_stderr_hex"],
                      "launcher": (case / "launcher_stderr.log").read_bytes().hex(),
                      "launcher_stdout": (case / "launcher_stdout.log").read_bytes().hex()}
        check(report, "stderr and launcher console are empty", "all empty", all_stderr, not any(all_stderr.values()))
        observer_rows = []
        if observer is not None:
            observer_result = json.loads((operator_root / "observer_completion.json").read_text(encoding="utf-8"))
            observer_streams = {"stdout": (case / "observer_stdout.log").read_bytes().hex(),
                                "stderr": (case / "observer_stderr.log").read_bytes().hex()}
            check(report, "passive observer completes without signals or model access",
                  "return 0; launcher_completed; >= 1 sample; empty streams; no signals/imports/model access",
                  {"completion": observer_result, "streams": observer_streams, "returncode": observer.returncode},
                  observer.returncode == 0 and observer_result["reason"] == "launcher_completed"
                  and observer_result["samples"] >= 1 and observer_result["signals_sent"] == 0
                  and observer_result["model_artifacts_opened"] is False and not observer_result["numerical_imports"]
                  and not any(observer_streams.values()))
            observer_rows = [json.loads(line) for line in
                             (operator_root / "resource_samples.jsonl").read_text(encoding="utf-8").splitlines()]
            check(report, "observer sample count matches sealed rows", observer_result["samples"], len(observer_rows),
                  len(observer_rows) == observer_result["samples"])
            if mode == "normal":
                matched_samples = []
                for index, sample in enumerate(observer_rows):
                    matched = set()
                    for entry in sample.get("owned_processes", []):
                        for expected in (live_coord, live_worker):
                            raw_stat = entry.get("stat")
                            cg = entry.get("cgroup")
                            if (entry.get("pid") != expected["pid"] or not isinstance(raw_stat, str)
                                    or not isinstance(cg, str) or cg != expected["cgroup"]):
                                continue
                            if int(raw_stat.rsplit(")", 1)[1].split()[19]) != expected["starttime_ticks"]:
                                continue
                            for line in cg.splitlines():
                                if line.startswith("0::"):
                                    cg_path = str((Path("/sys/fs/cgroup") / line[3:].lstrip("/")).resolve())
                                    memory = sample.get("cgroup_memory", {}).get(cg_path, {})
                                    if (isinstance(memory.get("memory.current"), str)
                                            and memory["memory.current"].strip().isdigit()
                                            and isinstance(memory.get("memory.events"), str)):
                                        matched.add(expected["pid"])
                    if matched == {live_coord["pid"], live_worker["pid"]}:
                        matched_samples.append(index)
                check(report, "observer captured owned processes and their actual cgroup",
                      "one sample has coordinator and worker with exact PID/starttime/cgroup and numeric memory.current",
                      matched_samples, bool(matched_samples))
        trace_text = trace.read_text(encoding="utf-8")
        exits = {int(pid): int(rc) for pid, rc in re.findall(
            r"(?m)^\s*(\d+)\s+\d+(?:\.\d+)?\s+\+\+\+ exited with (\d+) \+\+\+", trace_text)}
        check(report, "trace covers coordinator and worker completion", expected_rc, exits,
              exits.get(coord["pid"]) == expected_rc and exits.get(worker["pid"]) == expected_rc)
        # -f plus -o prefixes every record with the receiver PID; only delivered signals contain --- SIG.
        signal_lines = [line for line in trace_text.splitlines() if "--- SIG" in line]
        report["signal_lines"] = signal_lines
        if mode == "normal":
            check(report, "90 seconds without injected or received selected signals", ">= 90 seconds; COMPLETED; no selected signal records",
                  worker_result, worker_result["status"] == "COMPLETED" and worker_result["signal"] is None
                  and worker_result["elapsed_seconds"] >= 90.0 and not signal_lines)
        else:
            sent = json.loads((case / "signal_sent.json").read_text(encoding="utf-8"))
            pattern = re.compile(r"^\s*(\d+)\s+\d+(?:\.\d+)?\s+--- SIGTERM \{([^}]*)\} ---")
            found = []
            for line in signal_lines:
                match = pattern.search(line)
                if match:
                    fields = dict(re.findall(r"(si_\w+)=([A-Za-z0-9_+-]+)", match.group(2)))
                    found.append({"receiver_pid": int(match.group(1)), "siginfo": fields, "line": line})
            expected = {"receiver_pid": sent["target_pid"], "si_pid": str(os.getpid()),
                        "si_uid": str(os.getuid()), "si_code": "SI_USER", "si_signo": "SIGTERM"}
            exact = len(found) == 1 and len(signal_lines) == 1 and found[0]["receiver_pid"] == sent["target_pid"]
            exact = exact and all(found[0]["siginfo"].get(key) == value for key, value in expected.items() if key != "receiver_pid")
            check(report, "strace captures the known sender and receiver", expected, found, exact)
            if observer is not None:
                combined_trace = "".join(row.get("trace_new", "") for row in observer_rows)
                check(report, "observer captured the exact known-sender signal record", found[0]["line"],
                      {"raw_signal_record_observed": found[0]["line"] in combined_trace,
                       "sender_metadata_is_not_historical_identity_proof": True},
                      found[0]["line"] in combined_trace)
            check(report, "original-style handler receives unchanged SIGTERM", {"status": "INTERRUPTED", "signal": 15},
                  worker_result, worker_result["status"] == "INTERRUPTED" and worker_result["signal"] == 15)
        for name, result in (("worker", worker_result), ("coordinator", coord_result)):
            after = result["identity_after"]
            check(report, name + " remains isolated and stdlib-only", "no numeric imports; -I -B; SIGTERM unblocked", after,
                  not after["numeric_modules_loaded"] and after["isolated"] and after["dont_write_bytecode"]
                  and not after["sigterm_blocked"])
        check(report, "no fixture exception or timeout cleanup", False,
              [p.name for p in case.glob("*_exception.json")], not list(case.glob("*_exception.json"))
              and "timeout_cleanup" not in report)
        report["status"] = "PASS"
    except BaseException as exc:
        report["status"] = "FAIL" if isinstance(exc, ProbeStop) else "BLOCKED"
        report["terminal_error"] = {"type": type(exc).__name__, "error": repr(exc), "traceback": traceback.format_exc()}
        if launcher is not None and (launcher.poll() is None or (observer is not None and observer.poll() is None)):
            # Preserve the first failure and allow the owned fixture its bounded natural exit.
            while (launcher.poll() is None or (observer is not None and observer.poll() is None)) and time.monotonic() < deadline:
                time.sleep(0.05)
            if (launcher.poll() is None or (observer is not None and observer.poll() is None)) and "timeout_cleanup" not in report:
                timeout_cleanup(launcher, launcher_identity, owned_group, report, observer_identity)
    report["elapsed_seconds"] = time.monotonic() - start
    save(case / "result.json", report)
    print(mode + ": " + report["status"], flush=True)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--python", required=True, type=Path)
    parser.add_argument("--strace", required=True, type=Path)
    parser.add_argument("--launcher", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--observer", type=Path)
    args = parser.parse_args()
    # Do not resolve a virtualenv Python symlink to its system interpreter.
    args.python = Path(os.path.abspath(args.python))
    if not args.python.is_file():
        parser.error("--python does not name an existing interpreter")
    args.strace = args.strace.resolve(strict=True)
    args.launcher = args.launcher.resolve(strict=True)
    args.fixture = Path(__file__).resolve().with_name("probe_fixture.py")
    if args.observer is not None:
        args.observer = args.observer.resolve(strict=True)
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=False)
    summary = {"status": "NOT TESTED", "kind": "development-only signal observability probe",
               "cases": [], "historical_sender": "UNKNOWN", "historical_cause_fixed": False,
               "model_or_weights_loaded": False, "formal_model_restart_authorized_by_probe": False}
    try:
        if sys.platform != "linux" or not sys.flags.isolated or not sys.dont_write_bytecode:
            raise ProbeStop("Controller requires Linux -I -B")
        if (sys.version_info[:3] != (3, 12, 3) or Path(os.path.abspath(sys.executable)) != args.python
                or Path(sys.prefix) != args.python.parent.parent or sys.prefix == sys.base_prefix):
            raise ProbeStop("Controller must use the selected frozen virtualenv Python 3.12.3")
        if any(name.split(".")[0] in {"torch", "numpy", "tokenizers"} for name in sys.modules):
            raise ProbeStop("Numeric library imported in stdlib controller")
        if sha(args.launcher) != LAUNCHER_SHA256:
            raise ProbeStop("Frozen launcher SHA-256 mismatch")
        version = subprocess.run([str(args.strace), "--version"], capture_output=True, timeout=5, check=False)
        summary["strace_version"] = {"returncode": version.returncode, "stdout": version.stdout.decode(),
                                     "stderr": version.stderr.decode(), "sha256": sha(args.strace)}
        if version.returncode != 0 or not version.stdout.startswith(b"strace -- version 6.8\n"):
            raise ProbeStop("Expected installed strace 6.8")
        sources = {str(Path(__file__).resolve()): sha(Path(__file__)),
                   str(args.fixture): sha(args.fixture), str(args.launcher): sha(args.launcher)}
        if args.observer is not None:
            sources[str(args.observer)] = sha(args.observer)
        save(args.output / "claim.json", {
            "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "controller": process(os.getpid()),
            "argv": sys.argv, "python": str(args.python), "prefix": sys.prefix, "version": sys.version,
            "source_sha256": sources,
            "strace": summary["strace_version"], "numeric_modules_loaded": False,
        })
        for mode in ("normal", "term"):
            report = run_case(args, args.output, mode)
            summary["cases"].append({"case": mode, "status": report["status"], "elapsed_seconds": report["elapsed_seconds"]})
            if report["status"] != "PASS":
                summary["status"] = report["status"]
                break
        else:
            summary["status"] = "PASS"
        summary["interpretation"] = ("This probe tests signal observation and propagation only. "
                                     "Survival for 90 seconds does not identify the historical sender, "
                                     "prove environmental stability, or validate model numerical behavior.")
    except BaseException as exc:
        summary["status"] = "FAIL" if isinstance(exc, ProbeStop) else "BLOCKED"
        summary["error"] = {"type": type(exc).__name__, "error": repr(exc), "traceback": traceback.format_exc()}
    try:
        save(args.output / "summary.json", summary)
    except BaseException as exc:
        print(json.dumps({"first_summary": summary, "summary_sealing_error": repr(exc)}, allow_nan=False),
              file=sys.stderr, flush=True)
        return 2
    print(json.dumps(summary, allow_nan=False), flush=True)
    return 0 if summary["status"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
