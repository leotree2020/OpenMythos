"""Run-level bench validity checks for GATED-SPAWN (BV-1, 2, 3, 6, 7).  BV-4, 5, 8, 9, 10 are evaluated inside every trial
(trial.py).  Each check returns {'ok': bool, 'detail': ...}.  Nothing here is trusted until a controlled run has executed it:
WRITTEN, NOT RUN."""
import json
import os
import traceback

import common as C
import gate
import janitor
import node as N
import proto
import registry as R

SLEEPER = {"label": "bv", "role": "sleeper", "mode": "setsid", "children": [], "exit_after_ready": False}


def _wait_dead(obs, rec, timeout):
    return obs.wait_for(lambda: rec.pid is not None and C.process_is_dead(rec.pid, rec.starttime), timeout)


def bv1_unreleased_cannot_act(obs):
    """A registered-but-unreleased node must do nothing even though its SPEC is already queued in its control socket."""
    obs.trial_tag = "BV1"
    rec = obs.spawn_direct("bv", "BV1", dict(SLEEPER, label="BV1"), N.node_main, hold_release=True)
    if rec.state != "REGISTERED":
        return {"ok": False, "detail": "not held in REGISTERED: %s" % rec.state}
    proto.send_msg(rec.sock, {"t": "SPEC", "spec": dict(SLEEPER, label="BV1")})      # pre-queued: a leaky gate would act on it
    before = C.fingerprint(rec.pid)
    obs.serve(1.0)
    after = C.fingerprint(rec.pid)
    acted = rec.first_action_mono is not None or rec.ready is not None
    unchanged = after is not None and after["sid"] == before["sid"] and after["pgrp"] == before["pgrp"]
    obs.abort_held(rec)
    died = _wait_dead(obs, rec, 5.0)
    obs.reap_direct()
    ok = (not acted) and unchanged and died and rec.exit_status == C.EXIT_GATE_ABORT
    return {"ok": ok, "detail": {"acted": acted, "unchanged": unchanged, "died": died, "exit": rec.exit_status}}


def bv3_gate_silent_timeout(obs):
    """A node whose gate stays silent exits by itself with EXIT_GATE_TIMEOUT."""
    obs.trial_tag = "BV3"
    rec = obs.spawn_direct("bv", "BV3", dict(SLEEPER, label="BV3"), N.node_main, t_gate_max=2.0, hold_release=True)
    if rec.state != "REGISTERED":
        return {"ok": False, "detail": "not held: %s" % rec.state}
    died = _wait_dead(obs, rec, 6.0)
    obs.reap_direct()
    if rec.gate_w is not None:
        os.close(rec.gate_w)
        rec.gate_w = None
    return {"ok": died and rec.exit_status == C.EXIT_GATE_TIMEOUT, "detail": {"died": died, "exit": rec.exit_status}}


def _bv2_helper_entry(result_path, reg_path):
    """Runs in a gated child of the real observer: a MINI-OBSERVER that writes INTENT, forks a gated child G, records G's identity
    and then dies before it registers or releases G."""
    def entry(_ctrl_fd):
        reg = R.RegWriter(reg_path)
        reg.write("INTENT", node_id="g", creator="O", creator_pid=os.getpid(), role="bv2-g", label="G", mode="none", t_gate_max=C.T_GATE_MAX)
        gate_r, gate_w = os.pipe()
        marker = result_path + ".G_ACTED"

        def g_entry(_fd):
            open(marker, "w").close()                         # would exist only if G acted after a release it must never get
            os._exit(0)
        pid = gate.fork_gated(gate_r, -1, g_entry, C.T_GATE_MAX)
        os.close(gate_r)
        st = C.read_stat(pid)
        with open(result_path, "w") as f:
            json.dump({"pid": pid, "starttime": st["starttime"] if st else None}, f)
        os._exit(0)                                           # observer death: gate_w closes with this process
    return entry


def bv2_observer_death_before_register(obs, workdir):
    """If the (mini-)observer dies after fork but before REGISTERED/RELEASE, the gated child exits by itself and never acts."""
    obs.trial_tag = "BV2"
    result_path = os.path.join(workdir, "bv2_g.json")
    reg_path = os.path.join(workdir, "bv2_mini_registry.jsonl")
    rec = obs.spawn_direct("bv", "BV2-helper", dict(SLEEPER, label="BV2-helper"), _bv2_helper_entry(result_path, reg_path))
    if rec.state != "RELEASED":
        return {"ok": False, "detail": "helper not released: %s" % rec.state}
    if not _wait_dead(obs, rec, 10.0):
        return {"ok": False, "detail": "helper still alive"}
    obs.reap_direct()
    try:
        with open(result_path) as f:
            g = json.load(f)
    except (OSError, ValueError) as e:
        return {"ok": False, "detail": "no result file: %r" % (e,)}
    if g["starttime"] is None:
        return {"ok": False, "detail": "G identity not recorded"}
    deadline = C.mono() + C.T_GATE_MAX + 3.0
    while C.mono() < deadline and not C.process_is_dead(g["pid"], g["starttime"]):
        obs.serve(0.1)
    dead = C.process_is_dead(g["pid"], g["starttime"])
    acted = os.path.exists(result_path + ".G_ACTED")
    recs, _ = R.parse_reg(reg_path)
    registered = any(r["kind"] == "REGISTERED" for r in recs)
    return {"ok": dead and not acted and not registered, "detail": {"G_dead": dead, "G_acted": acted, "G_registered": registered}}


def bv6_janitor_refuses_wrong_identity(obs, workdir):
    """The janitor must not signal a live process whose starttime differs from the registered one, and must act when it matches."""
    obs.trial_tag = "BV6"
    rec = obs.spawn_direct("bv", "BV6", dict(SLEEPER, label="BV6"), N.node_main)
    if rec.state != "RELEASED":
        return {"ok": False, "detail": "node not released"}
    if not obs.wait_for(lambda: rec.ready is not None, 5.0):
        return {"ok": False, "detail": "node not ready"}

    def write_reg(path, starttime):
        w = R.RegWriter(path)
        w.write("INTENT", node_id="n1", creator="O", creator_pid=os.getpid(), role="bv", label="BV6", mode="setsid")
        w.write("REGISTERED", node_id="n1", pid=rec.pid, starttime=starttime, role="bv", label="BV6")
    bad_path = os.path.join(workdir, "bv6_wrong_identity.jsonl")
    good_path = os.path.join(workdir, "bv6_right_identity.jsonl")
    write_reg(bad_path, rec.starttime + 1)
    write_reg(good_path, rec.starttime)
    refused = janitor.run_cleanup(bad_path)
    alive_after_refusal = not C.process_is_dead(rec.pid, rec.starttime)
    acted = janitor.run_cleanup(good_path)
    obs.wait_for(lambda: C.process_is_dead(rec.pid, rec.starttime), 3.0)
    obs.reap_direct()
    ok = (len(refused) == 1 and refused[0]["result"] == "refused_identity_mismatch" and alive_after_refusal
          and len(acted) == 1 and acted[0]["result"] == "sent" and C.process_is_dead(rec.pid, rec.starttime))
    return {"ok": ok, "detail": {"refused": refused, "alive_after_refusal": alive_after_refusal, "acted": acted}}


def bv7_janitor_ignores_intent_only_and_torn(workdir):
    """Pure file test: INTENT-only nodes and a torn final line yield no cleanup target."""
    path = os.path.join(workdir, "bv7_torn.jsonl")
    w = R.RegWriter(path)
    w.write("INTENT", node_id="a", creator="O", creator_pid=1, role="x", label="A", mode="none")
    w.write("INTENT", node_id="b", creator="O", creator_pid=1, role="x", label="B", mode="none")
    with open(path, "ab") as f:
        f.write(b'{"seq":3,"kind":"REGISTERED","node_id":"b","pid":' + str(os.getpid()).encode() + b',"starttime":1')   # torn: no newline
    recs, info = R.parse_reg(path)
    targets = R.cleanup_targets(recs)
    results = janitor.run_cleanup(path, signal_fn=lambda h, s: (_ for _ in ()).throw(AssertionError("must not signal")))
    return {"ok": info["torn_tail"] and targets == [] and results == [], "detail": {"torn": info["torn_tail"], "targets": targets}}


def run_all(obs, workdir):
    os.makedirs(workdir, exist_ok=True)
    results = {}
    for name, fn in (("BV-1", lambda: bv1_unreleased_cannot_act(obs)),
                     ("BV-2", lambda: bv2_observer_death_before_register(obs, workdir)),
                     ("BV-3", lambda: bv3_gate_silent_timeout(obs)),
                     ("BV-6", lambda: bv6_janitor_refuses_wrong_identity(obs, workdir)),
                     ("BV-7", lambda: bv7_janitor_ignores_intent_only_and_torn(workdir))):
        try:
            results[name] = fn()
        except Exception:
            results[name] = {"ok": False, "detail": "EXCEPTION " + traceback.format_exc()}
        obs.problems.clear()
        if obs.trial_tag not in (None, "RUN"):                 # never touch run-level nodes (the janitor)
            cleanup = obs.finish_trial_cleanup()
            results[name]["cleanup"] = cleanup
            if not cleanup["cleanup_ok"]:
                results[name]["ok"] = False
        obs.trial_tag = "RUN"
    return results
