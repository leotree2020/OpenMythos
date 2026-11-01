"""Owned-process signal fixture only; no model, numeric libraries, or weights."""
import argparse
import datetime
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import traceback


class Stop(Exception):
    def __init__(self, signum):
        self.signum = signum
        super().__init__("Fixture interrupted: " + str(signum))


def save(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def identity():
    raw = Path("/proc/self/stat").read_text(encoding="utf-8")
    fields = raw[raw.rfind(")") + 2:].split()
    status = Path("/proc/self/status").read_text(encoding="utf-8")
    blocked = signal.pthread_sigmask(signal.SIG_BLOCK, set())
    return {
        "pid": os.getpid(), "ppid": os.getppid(), "pgid": os.getpgrp(),
        "sid": os.getsid(0), "uid": os.getuid(), "euid": os.geteuid(),
        "starttime_ticks": int(fields[19]), "status": status,
        "blocked_signals": sorted(int(value) for value in blocked),
        "sigterm_blocked": signal.SIGTERM in blocked,
        "python": sys.executable, "prefix": sys.prefix, "version": sys.version,
        "isolated": sys.flags.isolated, "dont_write_bytecode": sys.dont_write_bytecode,
        "numeric_modules_loaded": sorted(name for name in sys.modules
                                         if name.split(".")[0] in {"torch", "numpy", "tokenizers"}),
        "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "monotonic_ns": time.monotonic_ns(),
    }


def interrupted(signum, frame):
    raise Stop(signum)


def worker(root, mode):
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    start = time.monotonic()
    ready = identity()
    try:
        print("WORKER_READY " + mode, flush=True)
        save(root / "worker_ready.json", ready)
        deadline = start + 90.0
        while time.monotonic() < deadline:
            time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))
    except Stop as exc:
        save(root / "worker_result.json", {
            "status": "INTERRUPTED", "signal": exc.signum,
            "elapsed_seconds": time.monotonic() - start, "identity_after": identity(),
        })
        print("WORKER_SIGNAL " + str(exc.signum), flush=True)
        return 2
    save(root / "worker_result.json", {
        "status": "COMPLETED", "signal": None,
        "elapsed_seconds": time.monotonic() - start, "identity_after": identity(),
    })
    print("WORKER_COMPLETE", flush=True)
    return 0


def coordinator(root, mode):
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    save(root / "coordinator_ready.json", identity())
    command = [sys.executable, "-I", "-B", str(Path(__file__).resolve()),
               "worker", "--case-dir", str(root), "--mode", mode]
    start = time.monotonic()
    completed = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               timeout=120, check=False)
    # Preserve the worker byte streams; do not rewrite its output or signals.
    sys.stdout.buffer.write(completed.stdout)
    sys.stdout.buffer.flush()
    sys.stderr.buffer.write(completed.stderr)
    sys.stderr.buffer.flush()
    save(root / "coordinator_result.json", {
        "returncode": completed.returncode,
        "elapsed_seconds": time.monotonic() - start,
        "worker_stdout_hex": completed.stdout.hex(),
        "worker_stderr_hex": completed.stderr.hex(),
        "identity_after": identity(),
    })
    print("COORDINATOR_RC " + str(completed.returncode), flush=True)
    return 0 if completed.returncode == 0 else 2


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("role", choices=("coordinator", "worker"))
    parser.add_argument("--case-dir", required=True)
    parser.add_argument("--mode", required=True, choices=("normal", "term"))
    args = parser.parse_args()
    root = Path(args.case_dir).resolve(strict=True)
    try:
        if sys.platform != "linux" or not sys.flags.isolated or not sys.dont_write_bytecode:
            raise RuntimeError("Fixture requires Linux, -I and -B")
        if identity()["numeric_modules_loaded"]:
            raise RuntimeError("Numeric library imported in stdlib-only fixture")
        return worker(root, args.mode) if args.role == "worker" else coordinator(root, args.mode)
    except BaseException as exc:
        error = {"role": args.role, "type": type(exc).__name__, "error": repr(exc),
                 "traceback": traceback.format_exc()}
        try:
            save(root / (args.role + "_exception.json"), error)
        except BaseException as sealing:
            error["sealing_error"] = repr(sealing)
        print(json.dumps(error, allow_nan=False), file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":
    sys.exit(main())
