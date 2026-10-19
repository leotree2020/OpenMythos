#!/usr/bin/env python3
"""
Fault-injection tests of run_gate_e.py (PREREGISTRATION 6.6), with stub jobs
in a temporary test directory (GATE_E_TEST_DIR / GATE_E_TEST_CMDS). Nothing
is trained, diagnosed or pushed. Writes validation/launcher_tests.json; exits
non-zero if any case does not end as expected.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
STUB = '''import os, sys, json
kind, name, out = sys.argv[1], sys.argv[2], sys.argv[3]
fail = os.environ.get("STUB_FAIL_NAME", "")
if fail and fail == name:
    sys.exit(int(os.environ.get("STUB_FAIL_CODE", "1")))
if os.environ.get("STUB_NO_OUTPUT_NAME", "") == name:
    sys.exit(0)
target = sys.argv[4] if len(sys.argv) > 4 else None
if target:
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, target + ".json"), "w") as f:
        json.dump({"stub": name}, f)
'''


def case(label, env_extra, expect_code, expect_in_status=(), expect_not_started=None, prepare=None,
         workload=None, with_test_dir=True, cmds=True):
    d = tempfile.mkdtemp(prefix="gate_e_launcher_")
    stub = os.path.join(d, "stub.py")
    open(stub, "w").write(STUB)
    with open(os.path.join(d, "timing.json"), "w") as f:
        json.dump({"frozen_workload": workload if workload is not None else
                   {"level": 0, "m5a_bodies": 500, "m5b_batches": 200, "mlp_p13_when_linear_detected": True}}, f)
    stubs = {
        "train": f"python {stub} train {{name}} {{out}}",
        "diag": f"python {stub} diag {{name}} {{out}} {{state}}",
        "judge": f"python {stub} judge {{name}} {{out}} {{file}}",
        "events": f"python {stub} events {{name}} {d}",
        "archive": f"python {stub} archive {{name}} {d}",
    }
    cpath = os.path.join(d, "cmds.json")
    json.dump(stubs, open(cpath, "w"))
    if prepare:
        prepare(d)
    env = dict(os.environ, PYTHONPATH=ROOT, **env_extra)
    if with_test_dir:
        env["GATE_E_TEST_DIR"] = d
    if cmds:
        env["GATE_E_TEST_CMDS"] = cpath
    p = subprocess.run(["python", os.path.join(HERE, "run_gate_e.py")], env=env, capture_output=True, text=True,
                       timeout=900)
    status_path = os.path.join(d, "logs", "run_status.txt")
    status = open(status_path).read() if os.path.exists(status_path) else ""
    ok = p.returncode == expect_code and all(s in status for s in expect_in_status)
    if expect_not_started:
        ok &= f"started {expect_not_started}" not in status
    res = {"exit": p.returncode, "expected": expect_code, "status_tail": status.splitlines()[-3:],
           "stderr_tail": p.stderr[-300:], "pass": bool(ok)}
    shutil.rmtree(d)
    return label, res


def main():
    results = dict([
        case("all_succeed", {}, 0, ("all 16 training runs done and archived", "all 280 states diagnosed", "DONE")),
        case("refuse_nonempty_results", {}, 5,
             prepare=lambda d: (os.makedirs(os.path.join(d, "results")),
                                open(os.path.join(d, "results", "x.json"), "w").write("{}"))),
        case("refuse_no_frozen_workload", {}, 5, workload={}),
        case("refuse_m5a_not_500", {}, 5, workload={"level": 0, "m5a_bodies": 1000, "m5b_batches": 200,
                                                     "mlp_p13_when_linear_detected": True}),
        case("refuse_cmds_without_test_dir", {}, 5, with_test_dir=False),
        case("training_integrity_failure", {"STUB_FAIL_NAME": "train_K2_transformer_s3", "STUB_FAIL_CODE": "3"}, 3,
             ("INTEGRITY FAILURE: train_K2_transformer_s3", "stopped with exit 3"), expect_not_started="diag_"),
        case("training_other_error", {"STUB_FAIL_NAME": "train_K4_openmythos_s1", "STUB_FAIL_CODE": "1"}, 4,
             ("RUN ERROR: train_K4_openmythos_s1",), expect_not_started="diag_"),
        case("diag_integrity_failure", {"STUB_FAIL_NAME": "diag_K2_openmythos_s2_step300", "STUB_FAIL_CODE": "3"}, 3,
             ("INTEGRITY FAILURE: diag_K2_openmythos_s2_step300",), expect_not_started="judge_"),
        case("diag_missing_result", {"STUB_NO_OUTPUT_NAME": "diag_K4_transformer_s1_step750"}, 6,
             ("RESULT CHECK FAILED: 279 of 280",), expect_not_started="judge_"),
        case("judge_missing", {"STUB_NO_OUTPUT_NAME": "judge_openmythos_s5"}, 6, ("RESULT CHECK FAILED: 9 of 10",)),
    ])
    lab, r = archive_case()
    results[lab] = r
    out = {"cases": results, "pass": all(v["pass"] for v in results.values())}
    with open(os.path.join(HERE, "validation", "launcher_tests.json"), "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps({k: (v["pass"], v["exit"]) for k, v in results.items()}, indent=1))
    sys.exit(0 if out["pass"] else 1)


def archive_case():
    """The archive stub exits 1 for train_K2_openmythos_s2 -> integrity stop (3)."""
    d = tempfile.mkdtemp(prefix="gate_e_launcher_")
    stub = os.path.join(d, "stub.py")
    open(stub, "w").write(STUB)
    json.dump({"frozen_workload": {"level": 0, "m5a_bodies": 500, "m5b_batches": 200,
                                   "mlp_p13_when_linear_detected": True}}, open(os.path.join(d, "timing.json"), "w"))
    stubs = {"train": f"python {stub} train {{name}} {{out}}",
             "diag": f"python {stub} diag {{name}} {{out}} {{state}}",
             "judge": f"python {stub} judge {{name}} {{out}} {{file}}",
             "events": f"python {stub} events {{name}} {d}",
             "archive": f"python {stub} archive {{name}} {d}"}
    json.dump(stubs, open(os.path.join(d, "cmds.json"), "w"))
    env = dict(os.environ, PYTHONPATH=ROOT, GATE_E_TEST_DIR=d, GATE_E_TEST_CMDS=os.path.join(d, "cmds.json"),
               STUB_FAIL_NAME="train_K2_openmythos_s2", STUB_FAIL_CODE="1")
    # the train stub for that name would fail too; make only the archive fail by renaming the job in the stub
    stubs["train"] = f"python {stub} train X{{name}} {{out}}"
    json.dump(stubs, open(os.path.join(d, "cmds.json"), "w"))
    p = subprocess.run(["python", os.path.join(HERE, "run_gate_e.py")], env=env, capture_output=True, text=True,
                       timeout=900)
    status = open(os.path.join(d, "logs", "run_status.txt")).read()
    ok = p.returncode == 3 and "INTEGRITY FAILURE: archive of train_K2_openmythos_s2" in status \
        and "started diag_" not in status
    shutil.rmtree(d)
    return "archive_failure", {"exit": p.returncode, "expected": 3, "status_tail": status.splitlines()[-3:], "pass": ok}


if __name__ == "__main__":
    main()
