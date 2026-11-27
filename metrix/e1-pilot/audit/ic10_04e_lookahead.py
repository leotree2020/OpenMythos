"""ic10_04e (implementation stage C, C2 third fix commit (staged tree c7869d35, parent 2665ab10), round 1; task 3 of the
invocation, numeric part; my ic9_04e with this round's model): the ST7 look-ahead values and the report-only checkpoint
overhead, computed by me from the timing block of the smoke's step 2 record (<smoke>/records/step2_record.json) and the
frozen files, against what the code under audit returns for the same timing (my driver ic10_04e_probe.py, run once as a
subprocess with PYTHONPATH=src; C1 ruling item 5) and against the smoke's own record. This script imports nothing of the
Executor.

My model (written and printed before the probe runs; counts and questions per fact from the frozen SEARCH_SPACE.json and
SPLIT_MANIFEST.json):
  TEST evaluation (from the ST7 check before_run(look_ahead) on): N loaded once (load_s; p.base_model) and hashed once
    in test_evaluate; the 15 checkpoints loaded (reload_s each: load_checkpoint = a fresh model + load_state_dict, what
    preflight's reload_s measures); 16 TEST evaluations (DEV evaluation seconds x TEST / DEV questions per fact); 16
    state hashes in require_test_session. The 15 checkpoint file hashes are done before the ST7 check (they are past
    time at the check) and no file is hashed after it (testgate has no file_sha256 call):
      load_s + 15 reload_s + 16 dev_s x q_test / q_dev + 17 hash_s
  one training run: load_s + total_steps x mean_step_s x (a_factor for arm A only) + 2 hash_s + save_s + file_hash_s +
    reload_s + dev_s (unchanged); one DEV evaluation: "load" load_s + dev_s, "reload" reload_s + dev_s, None dev_s;
    step 3's look-ahead (static, ic10_04_static i): load_s + dev_s + hash_s.
  checkpoint overhead (report only): base-model loads 1 (N, step 3) + 30 (one per run) + 1 (N at TEST) = 32 x load_s;
    30 checkpoints x (2 hash_s + save_s + reload_s + file_hash_s); further reloads 3 (G0.8, one per training seed) + 15
    (TEST) = 18 x reload_s; TEST state hashes 17 x hash_s; TEST checkpoint files 15 x file_hash_s.
usage: python -I -B ic10_04e_lookahead.py <repo_root> <venv_python> <inputs_dir> <smoke_work_dir> <scratch_dir (created,
       must not exist)>"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json
import subprocess
from collections import Counter
from ia_common import frozen_json, run

TOL = 1e-9


def close(a, b):
    return abs(a - b) <= TOL * max(1.0, abs(a), abs(b))


def main():
    repo, py, inputs, work, scratch = sys.argv[1:6]
    if os.path.exists(scratch):
        print("scratch dir %s exists: refused" % scratch)
        return False
    os.makedirs(scratch)
    ok = True
    rec = os.path.join(work, "records")
    s2 = json.load(open(os.path.join(rec, "step2_record.json"), encoding="utf-8"))
    s6 = json.load(open(os.path.join(rec, "step6_record.json"), encoding="utf-8"))
    t = s2["preflight"]["timing"]
    print("smoke step 2 timing block: %s" % json.dumps(t, sort_keys=True))
    ss = frozen_json(repo, "SEARCH_SPACE.json")
    sm = frozen_json(repo, "SPLIT_MANIFEST.json")
    total_steps = ss["training_contract"]["total_steps"]
    seeds = ss["training_contract"]["training_seeds"]
    search_seed = ss["search_seed"]
    per_rel = {k: Counter(x["relation"] for x in sm["templates"] if x["kind"] == k) for k in ("DEV", "TEST")}
    q_dev, q_test = set(per_rel["DEV"].values()), set(per_rel["TEST"].values())
    assert len(q_dev) == 1 and len(q_test) == 1
    q_dev, q_test = q_dev.pop(), q_test.pop()
    test_models = 1 + 5 * len(seeds)                 # N + F, L, A, S, Y x the training seeds (section 8 step 8)
    files = test_models - 1
    hashes = test_models + 1
    print("frozen: total_steps %d | training seeds %s (search seed %s) | questions per fact DEV %d TEST %d | TEST models %d, "
          "checkpoint files %d, state hashes %d" % (total_steps, seeds, search_seed, q_dev, q_test, test_models, files, hashes))
    sel = s6["selected"]
    names = []
    for arm in ("F", "L", "A"):
        names += ["%s-%s%d-seed%d" % (arm, arm, i, search_seed) for i in range(1, 7)]
    for arm in ("F", "L", "A"):
        names += ["%s-%s-seed%d" % (arm, sel[arm], s) for s in seeds if s != search_seed]
    for arm in ("S", "Y"):
        names += ["%s-%s-seed%d" % (arm, sel["F"], s) for s in seeds]
    print("selected (smoke step 6 record) %s | my 30 run names (plan order) == step 6 training_plan: %s" % (
        sel, names == s6["training_plan"]))
    ok &= names == s6["training_plan"] and len(names) == ss["counts"]["total_training_runs"]

    dev = t["dev_evaluation_seconds"]
    my_test = t["load_s"] + files * t["reload_s"] + test_models * dev * q_test / q_dev + hashes * t["hash_s"]
    base_loads, reloads = 1 + len(names) + 1, len(seeds) + files
    my_over = (base_loads * t["load_s"] + len(names) * (2 * t["hash_s"] + t["save_s"] + t["reload_s"] + t["file_hash_s"])
               + reloads * t["reload_s"] + hashes * t["hash_s"] + files * t["file_hash_s"])
    my_counts = {"base_loads": base_loads, "checkpoints": len(names), "checkpoint_reloads": reloads,
                 "test_state_hashes": hashes, "test_file_hashes": files, "test_models": test_models}
    rest = 2 * t["hash_s"] + t["save_s"] + t["file_hash_s"] + t["reload_s"] + dev
    my_runs = {n: t["load_s"] + total_steps * t["mean_step_s"] * (t["a_factor"] if n.startswith("A-") else 1.0) + rest
               for n in names}
    my_eval = {"load": t["load_s"] + dev, "reload": t["reload_s"] + dev, "None": dev}
    print("\n== my values (before the probe runs)")
    print("TEST look-ahead: %.6f + 15 x %.6f + 16 x %.6f x %d/%d + 17 x %.6f = %.9f s (%.4f h)" % (
        t["load_s"], t["reload_s"], dev, q_test, q_dev, t["hash_s"], my_test, my_test / 3600.0))
    prev = my_test + files * t["file_hash_s"]
    print("  (the formula of the previous round, with 15 x file_hash_s: %.9f s; difference %.6f s)" % (prev, prev - my_test))
    print("step 3 look-ahead (load + DEV evaluation + N's hash): %.9f s" % (t["load_s"] + dev + t["hash_s"]))
    print("checkpoint overhead (report only): counts %s | %d x %.6f + %d x (2 x %.6f + %.6f + %.6f + %.6f) + %d x %.6f + "
          "%d x %.6f + %d x %.6f = %.9f s" % (json.dumps(my_counts, sort_keys=True), base_loads, t["load_s"], len(names),
                                              t["hash_s"], t["save_s"], t["reload_s"], t["file_hash_s"], reloads,
                                              t["reload_s"], hashes, t["hash_s"], files, t["file_hash_s"], my_over))
    prev_over = (1 + 30 + 3 + 16) * t["load_s"] + 30 * (2 * t["hash_s"] + t["save_s"] + t["reload_s"] + t["file_hash_s"]) \
        + 17 * t["hash_s"] + 15 * t["file_hash_s"]
    print("  (the previous round's overhead, 50 loads x load_s: %.9f s; difference %.6f s)" % (prev_over, prev_over - my_over))
    f_run = my_runs[names[0]]
    a_run = my_runs[[n for n in names if n.startswith("A-")][0]]
    print("training run look-ahead: non-A %.9f s | A %.9f s (a_factor %.6f) | runs with the A factor: %d" % (
        f_run, a_run, t["a_factor"], sum(1 for n in names if n.startswith("A-"))))
    print("DEV evaluation look-ahead: %s" % json.dumps(my_eval, sort_keys=True))
    parts = s2["preflight"]["b17_parts"]
    my_train_sum = sum(total_steps * t["mean_step_s"] * (t["a_factor"] if n.startswith("A-") else 1.0) for n in names)
    print("sum of my 30 per-run training terms %.9f s | B17 train_seconds recorded %.9f s (other_runs %s, a_runs %s) | equal %s" % (
        my_train_sum, parts["train_seconds"], parts["other_runs"], parts["a_runs"], close(my_train_sum, parts["train_seconds"])))
    ok &= close(my_train_sum, parts["train_seconds"]) and parts["a_runs"] == sum(1 for n in names if n.startswith("A-"))
    sys.stdout.flush()

    tf = os.path.join(scratch, "timing.json")
    json.dump(t, open(tf, "w", encoding="utf-8"))
    pw = os.path.join(scratch, "pilot_work")
    env = dict(os.environ, PYTHONPATH=os.path.join(repo, "metrix/e1-pilot/src"), PYTHONDONTWRITEBYTECODE="1",
               GIT_OPTIONAL_LOCKS="0", METRIX_INPUTS_DIR=inputs)
    cmd = [py, "-B", os.path.join(os.path.dirname(os.path.abspath(__file__)), "ic10_04e_probe.py"), inputs, tf, pw,
           json.dumps(sel)]
    st_args = ("status", "--porcelain", "--ignored", "--untracked-files=all", "--", "metrix", ":(exclude)metrix/e1-pilot/audit")
    gs0 = subprocess.run(["git", "-C", repo, *st_args], capture_output=True, text=True, env=env).stdout
    print("\n== probe (driver subprocess, cwd %s)\n$ PYTHONPATH=%s %s" % (scratch, env["PYTHONPATH"], " ".join(cmd)))
    r = subprocess.run(cmd, cwd=scratch, env=env, capture_output=True, text=True)
    print("----- probe stdout+stderr begin -----\n%s%s----- probe end ----- exit %d" % (r.stdout, r.stderr, r.returncode))
    ok &= r.returncode == 0
    line = [x for x in r.stdout.split("\n") if x.startswith("PROBE ")]
    got = json.loads(line[0][6:]) if len(line) == 1 else None
    if got is None:
        return False

    print("\n== comparison")
    bp = got["before_preflight"]
    print("before the preflight: %s (expected both 0.0): %s" % (bp, bp == {"run_seconds_F1": 0.0, "eval_seconds_load": 0.0}))
    ok &= bp == {"run_seconds_F1": 0.0, "eval_seconds_load": 0.0}
    te = got["test_evaluation_seconds"]
    print("test_evaluation_seconds: code %.9f | mine %.9f | equal (rel. tol %g) %s" % (te, my_test, TOL, close(te, my_test)))
    ok &= close(te, my_test)
    code_names = [x["name"] for x in got["runs"]]
    print("probe's training_plan names == mine: %s" % (code_names == names))
    ok &= code_names == names
    bad = []
    for x in got["runs"]:
        m = my_runs.get(x["name"])
        if m is None or not close(x["run_seconds"], m):
            bad.append((x["name"], x["arm"], x["run_seconds"], m))
    by_arm = {}
    for x in got["runs"]:
        by_arm.setdefault(x["arm"], set()).add(round(x["run_seconds"], 9))
    print("run_seconds per arm (code, distinct values): %s" % {k: sorted(v) for k, v in sorted(by_arm.items())})
    print("run_seconds differing from mine: %s" % bad)
    ok &= not bad
    ge = got["eval_seconds"]
    eq = {k: close(ge[k], my_eval[k]) for k in my_eval}
    print("eval_seconds code %s | mine %s | equal %s" % (json.dumps(ge, sort_keys=True), json.dumps(my_eval, sort_keys=True), eq))
    ok &= all(eq.values())
    ep, co = got["evaluation_plan"], got["checkpoint_overhead_seconds"]
    print("evaluation_plan code %s | mine %s | equal %s" % (json.dumps(ep, sort_keys=True), json.dumps(my_counts, sort_keys=True),
                                                         ep == my_counts))
    ok &= ep == my_counts and co["counts"] == my_counts
    rec_over = s2["preflight"]["checkpoint_overhead_report_only"]
    print("checkpoint_overhead_seconds code %.9f | mine %.9f | the smoke's step 2 record %.9f (counts %s) | all equal %s" % (
        co["seconds"], my_over, rec_over["seconds"], json.dumps(rec_over["counts"], sort_keys=True),
        close(co["seconds"], my_over) and close(rec_over["seconds"], my_over) and rec_over["counts"] == my_counts))
    ok &= close(co["seconds"], my_over) and close(rec_over["seconds"], my_over) and rec_over["counts"] == my_counts
    b17 = s2["preflight"]["b17_estimate_hours"]
    summ = s2["preflight"]["b17_plus_checkpoint_overhead_hours_report_only"]
    print("record: b17_estimate_hours %.9f + my overhead / 3600 = %.9f | recorded sum %.9f | equal %s | st11_reads %r, "
          "st11 %r (bound %s h)" % (b17, b17 + my_over / 3600.0, summ, close(b17 + my_over / 3600.0, summ),
                                     s2["preflight"].get("st11_reads"), s2["preflight"].get("st11"),
                                     s2["preflight"].get("st11_bound_hours")))
    ok &= close(b17 + my_over / 3600.0, summ) and s2["preflight"].get("st11_reads") == "b17_estimate_hours"
    gs1 = subprocess.run(["git", "-C", repo, *st_args], capture_output=True, text=True, env=env).stdout
    print("\nthis repository unchanged by the probe (git status, audit/ excluded): %s | the probe's work directory created: %s" % (
        gs0 == gs1, os.path.exists(pw)))
    ok &= gs0 == gs1
    return bool(ok)


run(main)
