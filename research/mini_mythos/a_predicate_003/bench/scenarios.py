"""Scenario recipes for E1-A.  Each recipe builds its topology in a SETUP phase through the ticket protocol; the expected REAL
kernel defects are NOT stored here -- they are read from the frozen preregistration (REAL_KERNEL scenarios) or are empty
(SIMULATED scenarios, whose defect is an injection into the candidate's inputs).  WRITTEN, NOT RUN."""
import json

import common as C

SCENARIO_ORDER = ["E1A-a", "E1A-a2", "E1A-b", "E1A-c", "E1A-d", "E1A-e1", "E1A-e2", "E1A-f", "E1A-g", "E1A-h1", "E1A-h2", "E1A-i"]
CANDIDATES = ["P0", "P1", "P2"]
LAUNCH_CONTEXTS = ["L1", "L2", "L3", "L4"]


def load_prereg():
    """-> (prereg dict, sha256).  Refuses when the sidecar hash differs from the file."""
    with open(C.PREREG_PATH, "rb") as f:
        raw = f.read()
    sha = C.sha256_bytes(raw)
    with open(C.PREREG_PATH + ".sha256") as f:
        side = f.read().split()[0]
    if side != sha:
        raise RuntimeError("prereg sidecar hash %s != file hash %s" % (side, sha))
    return json.loads(raw.decode("utf-8")), sha


def _n(label, mode="none", children=(), exit_after_ready=False):
    return {"label": label, "role": "sleeper", "mode": mode, "children": list(children), "exit_after_ready": exit_after_ready}


def _spawn(spec):
    return {"op": "spawn", "label": spec["label"], "spec": spec}


def _reap(ref):
    return {"op": "reap", "ref": ref}


RECIPES = {
    "E1A-a": {"ops": [_spawn(_n("root", "setsid"))]},
    "E1A-a2": {"ops": [_spawn(_n("M", "none", [_n("X", "none")], True)), _reap("M"), _spawn(_n("root", "setsid"))]},
    "E1A-b": {"ops": [_spawn(_n("root", "none"))]},
    "E1A-c": {"ops": [_spawn(_n("root", "setpgid"))]},
    "E1A-d": {"ops": [_spawn(_n("L", "setsid", [_n("root", "none")], True)), _reap("L")]},
    "E1A-e1": {"ops": [_spawn(_n("root", "setsid", [_n("C", "none")]))]},
    "E1A-e2": {"ops": [_spawn(_n("root", "setsid")), _spawn(_n("Y", "none"))]},
    "E1A-f": {"ops": [_spawn(_n("root", "setsid"))], "injection": {"starttime_delta": 1}},
    "E1A-g": {"ops": [_spawn(_n("root", "setsid"))], "sigchld_ignored": True},
    "E1A-h1": {"ops": [_spawn(_n("root", "setsid"))], "injection": {"setter": "fail"}},
    "E1A-h2": {"ops": [_spawn(_n("root", "setsid"))], "injection": {"getter": 0}},
    "E1A-i": {"ops": [_spawn(_n("M", "none", [_n("X", "none")], True)), _reap("M"), _spawn(_n("root", "none"))]},
}


def _walk(spec):
    yield spec
    for c in spec.get("children", []):
        yield from _walk(c)


def all_labels(recipe):
    return [s["label"] for op in recipe["ops"] if op["op"] == "spawn" for s in _walk(op["spec"])]


def expected_alive_labels(recipe):
    """Nodes that must still be alive at S0 (those without exit_after_ready)."""
    return [s["label"] for op in recipe["ops"] if op["op"] == "spawn" for s in _walk(op["spec"]) if not s.get("exit_after_ready")]


def expected_real_defects(prereg, scn):
    """Real-kernel defect ids the topology must exhibit.  SIMULATED scenarios must show NO real defect (the defect is injected)."""
    s = prereg["scenarios"][scn]
    return sorted(s["defects"]) if s["evidence_kind"] == "REAL_KERNEL" else []


def plan_trials(prereg, reps=None, sweep_trials=None, only_cells=None, only_sweep=True):
    """Deterministic trial plan from the preregistration.  reps/sweep_trials default to the frozen values; any other value or
    a cell filter makes the run PARTIAL (the runner records that)."""
    reps = prereg["repetitions"]["deterministic_per_cell"] if reps is None else reps
    sw = prereg["scenarios"]["E1A-a"]["false_reject_sweep"]
    sweep_trials = sw["trials_per_context"] if sweep_trials is None else sweep_trials
    trials = []
    for scn in SCENARIO_ORDER:
        for rep in range(reps):
            for cand in CANDIDATES:
                if only_cells and (scn, cand) not in only_cells:
                    continue
                trials.append({"kind": "cell", "scenario": scn, "candidate": cand, "rep": rep, "launch": "L1"})
    if only_sweep:
        for ctx in sw["contexts"]:
            for rep in range(sweep_trials):
                for cand in sw["candidates"]:
                    if only_cells and ("E1A-a", cand) not in only_cells:
                        continue
                    trials.append({"kind": "sweep", "scenario": "E1A-a", "candidate": cand, "rep": rep, "launch": ctx})
    for i, t in enumerate(trials):
        t["trial_id"] = "T%05d" % (i + 1)
    return trials
