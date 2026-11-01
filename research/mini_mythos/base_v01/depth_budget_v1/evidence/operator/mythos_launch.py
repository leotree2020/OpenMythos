"""Stdlib-only process logger; execute with -I -B in a new operator directory."""
import argparse
import datetime
import hashlib
import json
import operator
import os
from pathlib import Path
import signal
import subprocess
import sys
import sysconfig
import time
import traceback


def save(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    config_path = Path(args.config).resolve()
    root = config_path.parent
    config = json.loads(config_path.read_text(encoding="utf-8"))
    assert Path(__file__).name == "mythos_launch.py"
    assert sys.flags.isolated and sys.dont_write_bytecode
    assert Path(operator.__file__).resolve().is_relative_to(Path(sysconfig.get_path("stdlib")).resolve())
    assert not any(name in sys.modules for name in ("torch", "numpy", "tokenizers"))
    assert type(config["command"]) is list and config["command"] and all(type(x) is str for x in config["command"])
    assert Path(config["command"][0]).is_absolute() and Path(config["cwd"]).is_dir()
    assert type(config["timeout_seconds"]) is int and 1 <= config["timeout_seconds"] <= 6000
    # Claim before opening logs or launching the child; never overwrite/retry.
    save(root / "claim.json", {
        "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "pid": os.getpid(), "argv": sys.argv,
        "python": sys.executable, "python_version": sys.version,
        "operator_origin": operator.__file__, "isolated": sys.flags.isolated,
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "config": config, "numerical_libraries_imported": False,
    })
    result = {"status": "NOT STARTED", "returncode": None}
    def interrupted(signum, frame):
        raise InterruptedError("launcher received signal " + str(signum))
    signal.signal(signal.SIGTERM, interrupted)
    try:
        with (root / "stdout.log").open("xb") as out, (root / "stderr.log").open("xb") as err:
            child = subprocess.Popen(config["command"], cwd=config["cwd"],
                                     stdout=out, stderr=err, start_new_session=True)
            try:
                returncode = child.wait(timeout=config["timeout_seconds"])
            except BaseException:
                cleanup = {"pgid": child.pid, "errors": []}
                def group_exists():
                    try:
                        os.killpg(child.pid, 0)
                        return True
                    except ProcessLookupError:
                        return False
                try:
                    try:
                        os.killpg(child.pid, signal.SIGTERM)
                        cleanup["term_sent"] = True
                    except ProcessLookupError:
                        cleanup["term_sent"] = False
                    deadline = time.monotonic() + 2
                    while group_exists() and time.monotonic() < deadline:
                        child.poll()
                        time.sleep(0.05)
                    if group_exists():
                        try:
                            os.killpg(child.pid, signal.SIGKILL)
                            cleanup["kill_sent"] = True
                        except ProcessLookupError:
                            cleanup["kill_sent"] = False
                    cleanup["leader_returncode"] = child.wait(timeout=10)
                    cleanup["group_still_exists"] = group_exists()
                except BaseException as cleanup_exc:
                    cleanup["errors"].append(repr(cleanup_exc))
                result["cleanup"] = cleanup
                raise
        result.update(status="COMPLETED" if returncode == 0 else "CHILD_FAILED",
                      returncode=returncode)
    except BaseException as exc:
        result.update(status="BLOCKED", exception_type=type(exc).__name__,
                      exception=repr(exc), traceback=traceback.format_exc())
    result["utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    save(root / "completion.json", result)
    return 0 if result["status"] == "COMPLETED" else 2


if __name__ == "__main__":
    sys.exit(main())
