"""ic9_04e probe (implementation stage C, C2 second fix commit, round 1). Data Auditor's own driver code, run ONLY as a
subprocess by ic9_04e_lookahead.py (C1 ruling item 5: the Executor's code as a driver). It checks nothing and computes
nothing itself: it calls the three ST7 look-ahead functions under audit with a given timing block and prints what they
return as one JSON line, for my comparison script (which imports nothing of the Executor):
  metrix_e1.pilot.test_evaluation_seconds(contract, timing)
  Pilot.run_seconds(spec) for every spec of train.training_plan(contract, selected), and Pilot.eval_seconds(load) for
  load in ("load", "reload", None), with p.pre = timing (as preflight sets it)
  Pilot.run_seconds / eval_seconds before the preflight (p.pre None).
A formal-mode Pilot is constructed with a work directory that must not exist (Pilot() reads the frozen files with git
cat-file and writes nothing); no model is built or loaded; no data is read.
usage (PYTHONPATH=<repo>/metrix/e1-pilot/src): python -B ic9_04e_probe.py <inputs_dir> <timing_json_file> <work_dir>
       <selected_json>"""
import json
import sys


def main():
    inputs, timing_f, work, selected = sys.argv[1], sys.argv[2], sys.argv[3], json.loads(sys.argv[4])
    from metrix_e1 import mode as M
    from metrix_e1 import pilot as P
    from metrix_e1 import train as T
    timing = json.load(open(timing_f, encoding="utf-8"))
    p = P.Pilot(M.FORMAL_MODE, inputs, work, "cpu")
    before = {"run_seconds_F1": p.run_seconds(T.search_runs(p.contract, "F")[0]),
              "eval_seconds_load": p.eval_seconds("load")}
    p.pre = dict(timing)
    out = {"before_preflight": before,
           "test_evaluation_seconds": P.test_evaluation_seconds(p.contract, timing),
           "runs": [{"name": s.name, "arm": s.arm, "run_seconds": p.run_seconds(s)}
                    for s in T.training_plan(p.contract, selected)],
           "eval_seconds": {"load": p.eval_seconds("load"), "reload": p.eval_seconds("reload"),
                            "None": p.eval_seconds(None)}}
    print("PROBE " + json.dumps(out))


main()
