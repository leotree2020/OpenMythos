"""Failure-path tests for F3B-D1-A-CPU-003-E1A-STATIC-FIX-002 (A: final cleanup set, B: registration-file integrity, C: BV provenance).
WRITTEN, NOT RUN.  Every test is PURE: only files, pipes and in-process socket pairs; no fork, no signal, no sacrificial process.
/proc and pidfd access is replaced by monkeypatching."""
import inspect
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "bench"))
import common as C          # noqa: E402
import e1a_runner as RUN    # noqa: E402
import evidence as EV       # noqa: E402
import janitor as J         # noqa: E402
import observer as O        # noqa: E402
import proto                # noqa: E402
import registry as R        # noqa: E402
import scenarios as S       # noqa: E402

PREREG, SHA = S.load_prereg()
CODE = "c" * 64
ALIVE = {"state": "S", "starttime": 5, "ppid": 1, "pgrp": 1, "sid": 1, "comm": "x"}


# ===================================================================== FIX-002-A: final cleanup set
class ObsCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.obs = O.Observer(os.path.join(self.tmp.name, "registry.jsonl"))
        self.obs.reg.write("RUN_START", run_id="t")
        self.obs.trial_tag = "T"
        self.socks = []

    def tearDown(self):
        for s in self.socks:
            s.close()
        for r in self.obs.nodes.values():
            for fd in (r.gate_w,):
                if fd is not None:
                    try:
                        os.close(fd)
                    except OSError:
                        pass
        self.tmp.cleanup()

    def add(self, state="ABORTED", pid=None, forked=4242, start=5, tag="T"):
        self.obs.counter += 1
        r = O.NodeRec("n%05d" % self.obs.counter, "x", "L", "O", {})
        r.trial, r.state, r.forked_pid, r.forked_starttime = tag, state, forked, start
        self.obs.nodes[r.node_id] = r
        return r

    def creator(self):
        a, b = proto.socketpair()
        self.socks += [a, b]
        c = self.add("RELEASED", forked=None)
        c.pid, c.starttime, c.sock = 111, 1, a
        return c, b


class TestFix002AIntake(ObsCase):
    def test_ticket_is_denied_once_intake_is_closed_and_creates_no_node(self):
        c, peer = self.creator()
        n = len(self.obs.nodes)
        self.obs.close_intake()
        self.obs._on_ticket(c, {"t": "TICKET", "role": "sleeper", "label": "late", "spec": {}})
        msg, fds = proto.recv_msg(peer, 1.0)
        self.assertEqual((msg["t"], fds), ("TICKET_DENIED", []))
        self.assertEqual(len(self.obs.nodes), n)
        self.assertEqual([r for r in self.obs.reg.records if r["kind"] == "INTENT"], [])

    def test_in_flight_ticket_is_revoked_with_the_abort_byte(self):
        c, peer = self.creator()
        self.obs._on_ticket(c, {"t": "TICKET", "role": "sleeper", "label": "kid", "spec": {}})
        msg, fds = proto.recv_msg(peer, 1.0)
        self.assertEqual(msg["t"], "TICKET_OK")
        gate_r = fds[0]
        for fd in fds[1:]:
            os.close(fd)
        kid = self.obs.nodes[msg["node_id"]]
        self.assertEqual(kid.state, "INTENT")
        self.obs.close_intake()
        self.assertEqual((kid.state, kid.revoked), ("ABORTED", True))
        self.assertEqual(os.read(gate_r, 1), b"A")                                   # a child forked from this ticket exits by itself
        os.close(gate_r)
        self.assertEqual([r["kind"] for r in self.obs.reg.records if r.get("node_id") == kid.node_id], ["INTENT", "ABORTED"])

    def test_creation_reported_after_revocation_is_recorded_not_registered_and_stays_residual(self):
        c, peer = self.creator()
        self.obs._on_ticket(c, {"t": "TICKET", "role": "sleeper", "label": "kid", "spec": {}})
        msg, fds = proto.recv_msg(peer, 1.0)
        for fd in fds:
            os.close(fd)
        kid = self.obs.nodes[msg["node_id"]]
        self.obs.close_intake()
        with mock.patch.object(C, "read_stat", return_value=ALIVE), mock.patch.object(C, "PidfdHandle") as H:
            self.obs._on_created(c, {"t": "CREATED", "node_id": kid.node_id, "pid": 4242})
            self.assertEqual(self.obs.residual([kid]), [kid.node_id])             # known, alive, identity unverified -> responsibility kept
        H.assert_not_called()                                                     # never registered, never signalled
        reply, _ = proto.recv_msg(peer, 1.0)
        self.assertEqual(reply["t"], "REGISTER_FAILED")
        kinds = [r["kind"] for r in self.obs.reg.records if r.get("node_id") == kid.node_id]
        self.assertIn("FORKED", kinds)
        self.assertNotIn("REGISTERED", kinds)
        self.assertEqual(self.obs.problems, [])

    def test_open_intake_after_a_trial_cleanup_closed_it(self):
        self.obs.finish_cleanup(grace=0.01)                                       # trial-level: reopens
        self.assertFalse(self.obs.intake_closed)
        self.obs.final_cleanup(set(), grace=0.01)                                 # run-level: stays closed
        self.assertTrue(self.obs.intake_closed)


class TestFix002AFixpoint(ObsCase):
    def test_a_node_that_appears_while_cleaning_is_picked_up_by_the_next_round(self):
        first = self.add("ABORTED")
        late = {}

        def inject(timeout):
            if not late:
                late["n"] = self.add("ABORTED", forked=4343)
        with mock.patch.object(C, "read_stat", return_value=None), mock.patch.object(self.obs, "serve", side_effect=inject):
            rep = self.obs.final_cleanup(set(), grace=0.01)
        self.assertEqual(len(rep["rounds"]), 2)
        self.assertEqual(rep["rounds"][0]["new_nodes"], [late["n"].node_id])
        self.assertTrue(rep["stable_set"])
        self.assertEqual({first.state, late["n"].state}, {"DEAD"})                # the late node was cleaned and confirmed too

    def test_a_set_that_never_stabilises_is_never_reported_clean(self):
        self.add("ABORTED")

        def keep_adding(timeout):
            self.add("ABORTED", forked=4300 + self.obs.counter)
        with mock.patch.object(C, "read_stat", return_value=None), mock.patch.object(self.obs, "serve", side_effect=keep_adding):
            rep = self.obs.finish_cleanup(lambda: self.obs.run_level_nodes(), grace=0.01, reopen_intake=False, max_rounds=3)
        self.assertFalse(rep["stable_set"])
        self.assertFalse(rep["cleanup_ok"])
        self.assertEqual(rep["residual_after_kill"], [])                           # nothing alive, yet NOT clean: the set was incomplete

    def test_cleanup_does_not_use_a_stale_snapshot(self):
        src = inspect.getsource(O.Observer.finish_cleanup)
        self.assertEqual(src.count("callable(nodes)"), 3)                          # re-evaluated before the round, after it, and for the final set

    def test_final_cleanup_fails_when_the_run_set_does_not_verify(self):
        self.add("ABORTED")
        bad = {"consistent": False, "problems": ["x"], "nodes": 1, "excluded": [], "reg_records": 0, "residual": []}
        with mock.patch.object(C, "read_stat", return_value=None), mock.patch.object(self.obs, "verify_run_set", return_value=bad):
            self.assertFalse(self.obs.final_cleanup(set(), grace=0.01)["cleanup_ok"])


class TestFix002AVerifyRunSet(ObsCase):
    def consistent(self, exclude=()):
        with mock.patch.object(C, "read_stat", return_value=None):
            return self.obs.verify_run_set(exclude)

    def test_clean_run_set_is_consistent(self):
        n = self.add("ABORTED")
        self.obs.reg.write("INTENT", node_id=n.node_id, creator="O", label="L")
        self.obs.reg.write("DEAD", node_id=n.node_id)
        n.state = "DEAD"
        self.assertTrue(self.consistent()["consistent"], self.consistent())

    def test_node_id_without_a_record(self):
        self.obs.counter += 1
        r = self.consistent()
        self.assertFalse(r["consistent"])
        self.assertIn("without a record", r["problems"][0])

    def test_registration_file_changed_behind_the_observers_back(self):
        with open(self.obs.reg_path, "ab") as f:
            f.write(b"garbage line\n")
        self.assertFalse(self.consistent()["consistent"])
        with open(self.obs.reg_path, "wb") as f:
            f.write(b"")                                                          # records lost
        self.assertFalse(self.consistent()["consistent"])

    def test_registration_file_mentions_a_node_memory_does_not_know(self):
        rec = {"seq": len(self.obs.reg.records) + 1, "kind": "INTENT", "node_id": "n99999", "creator": "O", "label": "ghost"}
        C.append_jsonl(self.obs.reg_path, rec)
        r = self.consistent()
        self.assertFalse(r["consistent"])
        self.assertTrue(any("unknown node ids" in p or "records" in p for p in r["problems"]))

    def test_pending_ticket_and_unconfirmed_node_break_consistency_but_excluded_nodes_do_not(self):
        t = self.add("INTENT", forked=None)
        self.assertTrue(any("pending" in p for p in self.consistent()["problems"]))
        t.state = "DEAD"
        alive = self.add("RELEASED", forked=4242)
        with mock.patch.object(C, "read_stat", return_value=ALIVE):
            self.assertFalse(self.obs.verify_run_set(set())["consistent"])
            res = self.obs.verify_run_set({alive.node_id})
        self.assertFalse(any("not confirmed dead" in p for p in res["problems"]))   # the janitor is excluded by id


class TestFix002ARecoveryState(unittest.TestCase):
    OK = dict(cleanup_confirmed=True, final_residual=[], residue=[], scan_problems=[], janitor_started=True, janitor_exit=0, janitor_running=False,
              janitor_stopped_after_discharge=False)

    def state(self, **kw):
        return RUN.recovery_state(**dict(self.OK, **kw))

    def test_closed_only_when_everything_holds(self):
        self.assertFalse(self.state()["recovery_open"])
        self.assertEqual(self.state()["state"], "CLOSED")

    def test_every_single_failure_keeps_recovery_open(self):
        for kw in ({"cleanup_confirmed": False}, {"final_residual": [{"node_id": "n1"}]}, {"residue": [{"pid": 1}]}, {"scan_problems": [7]},
                   {"janitor_exit": 4}, {"janitor_exit": 5}, {"janitor_exit": 6}, {"janitor_exit": 2}, {"janitor_exit": None},
                   {"janitor_started": False, "janitor_exit": None}, {"janitor_exit": -9}):
            self.assertTrue(self.state(**kw)["recovery_open"], kw)

    def test_a_running_janitor_is_delegated_not_declared_closed(self):
        s = self.state(janitor_running=True, janitor_exit=None, cleanup_confirmed=False)
        self.assertTrue(s["recovery_open"])
        self.assertFalse(s["manual_disposition_required"])
        self.assertIn("STILL-RUNNING JANITOR", s["state"])

    def test_abnormal_janitor_exit_with_residual_requires_manual_disposition(self):
        s = self.state(janitor_exit=4, final_residual=[{"node_id": "n1"}], cleanup_confirmed=False)
        self.assertTrue(s["manual_disposition_required"])
        self.assertIn("MANUAL DISPOSITION", s["state"])

    def test_a_janitor_stopped_by_us_after_discharge_is_not_abnormal(self):
        self.assertFalse(self.state(janitor_exit=-9, janitor_stopped_after_discharge=True)["recovery_open"])
        self.assertTrue(self.state(janitor_exit=-9, janitor_stopped_after_discharge=True, final_residual=[{"node_id": "n"}])["recovery_open"])

    def test_the_janitor_may_be_stopped_only_when_fully_discharged(self):
        self.assertTrue(RUN.may_stop_janitor(True, [], [], []))
        for args in ((False, [], [], []), (True, [{"n": 1}], [], []), (True, [], [{"pid": 1}], []), (True, [], [], [9])):
            self.assertFalse(RUN.may_stop_janitor(*args), args)

    def test_execute_never_kills_a_janitor_that_still_carries_responsibility(self):
        src = inspect.getsource(RUN.execute)
        self.assertEqual(src.count("kill_registered("), 1)
        self.assertLess(src.index("may_stop_janitor(confirmed"), src.index("kill_registered(only=jid"))
        self.assertLess(src.index("obs.final_cleanup(jid)"), src.index('obs.reg.write("RUN_END"'))
        self.assertIn("janitor_alive()", src)
        self.assertIn("MANUAL_DISPOSITION_REQUIRED.json", src)

    def test_open_recovery_blocks_the_experiment_verdict(self):
        plan = S.plan_trials(PREREG, reps=1, only_cells={("E1A-a", "P2")}, only_sweep=False)
        s = RUN.summarize(PREREG, plan, [], True, None, False, (), True, True)
        self.assertTrue(s["experiment_verdict"].startswith("BLOCKED - recovery"))


# ===================================================================== FIX-002-B: registration file integrity
class TestFix002BIntegrity(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "reg.jsonl")

    def tearDown(self):
        self.tmp.cleanup()

    def good(self, n=2):
        w = R.RegWriter(self.path)
        w.write("RUN_START", run_id="t")
        for i in range(n):
            nid = "n%05d" % (i + 1)
            w.write("INTENT", node_id=nid, creator="O", label="L%d" % i)
            w.write("FORKED", node_id=nid, pid=1000 + i, starttime=5)
            w.write("REGISTERED", node_id=nid, pid=1000 + i, starttime=5)
        return w

    def integ(self):
        with mock.patch.object(J.time, "sleep"):
            return J.reg_integrity(self.path)[0]

    def test_intact_file_is_ok(self):
        self.good()
        self.assertEqual(self.integ()["status"], "OK")

    def test_missing_file(self):
        r = self.integ()
        self.assertEqual((r["status"], r["ok"]), ("MISSING", False))

    def test_unreadable_file(self):
        os.mkdir(self.path)                                                       # a directory where the file should be
        r = self.integ()
        self.assertEqual((r["status"], r["info"]["unreadable"]), ("MISSING", True))

    def test_corrupt_lines_of_every_kind(self):
        for junk in (b"not json\n", b"[1,2]\n", b'{"seq":99,"kind":"BOGUS"}\n', b'{"seq":"x","kind":"INTENT"}\n', b'{"kind":"INTENT"}\n', b"\xff\xfe\n"):
            self.good()
            with open(self.path, "ab") as f:
                f.write(junk)
            self.assertEqual(self.integ()["status"], "CORRUPT", junk)
            os.remove(self.path)

    def test_torn_tail_is_retried_then_reported(self):
        self.good()
        with open(self.path, "ab") as f:
            f.write(b'{"seq":8,"kind":"REGISTERED","node_id":"n00003","pid":4242')
        self.assertEqual(self.integ()["status"], "TORN_TAIL")
        clean = R.parse_reg(self.path)
        seq = [(clean[0], dict(clean[1], torn_tail=True)), (clean[0], dict(clean[1], torn_tail=False))]
        with mock.patch.object(J.R, "parse_reg", side_effect=seq), mock.patch.object(J.time, "sleep") as sl:
            self.assertEqual(J.reg_integrity(self.path)[0]["status"], "OK")       # the observer was mid-append: second read is whole
        sl.assert_called_once()

    def test_a_lost_record_is_a_sequence_gap(self):
        self.good()
        lines = open(self.path, "rb").read().split(b"\n")
        del lines[3]
        open(self.path, "wb").write(b"\n".join(lines))
        r = self.integ()
        self.assertEqual(r["status"], "CORRUPT")
        self.assertTrue(any("SEQ_GAP" in x for x in r["issues"]))

    def fresh(self, build):
        if os.path.exists(self.path):
            os.remove(self.path)
        build(R.RegWriter(self.path))
        return self.integ()

    def test_orphan_record(self):
        r = self.fresh(lambda w: w.write("REGISTERED", node_id="n00001", pid=1, starttime=5))        # no INTENT for this node
        self.assertEqual(r["status"], "CORRUPT")
        self.assertTrue(any("ORPHAN_RECORD" in x for x in r["issues"]))

    def test_malformed_registered_record(self):
        def build(w):
            w.write("INTENT", node_id="n00001", creator="O", label="A")
            w.write("REGISTERED", node_id="n00001", pid="12", starttime=5)                             # pid is not an integer
        r = self.fresh(build)
        self.assertEqual(r["status"], "CORRUPT")
        self.assertTrue(any("MALFORMED_REGISTERED" in x for x in r["issues"]))

    def test_malformed_forked_record(self):
        def build(w):
            w.write("INTENT", node_id="n00001", creator="O", label="A")
            w.write("FORKED", node_id="n00001", pid=None)
        r = self.fresh(build)
        self.assertEqual(r["status"], "CORRUPT")
        self.assertTrue(any("MALFORMED_FORKED" in x for x in r["issues"]))

    def test_decisions_with_integrity(self):
        recs = [{"seq": 1, "kind": "INTENT", "node_id": "a"}, {"seq": 2, "kind": "REGISTERED", "node_id": "a", "pid": 4242, "starttime": 5},
                {"seq": 3, "kind": "RUN_END", "cleanup_confirmed": True}]
        with mock.patch.object(C, "process_is_dead", return_value=True):
            self.assertEqual(J.decide_with_integrity(recs, False, True), "EXIT_CONFIRMED")
            self.assertEqual(J.decide_with_integrity(recs, False, False), "CLEANUP")                  # never EXIT_CONFIRMED on a damaged file
        self.assertEqual(J.decide_with_integrity(recs[:2], False, False), "WAIT")                     # live run: no cleanup of live nodes
        self.assertEqual(J.decide_with_integrity(recs[:2], True, False), "CLEANUP")

    def test_exit_code_needs_both_facts(self):
        self.assertEqual(J.final_exit_code(True, True), J.EXIT_CLEAN)
        self.assertEqual(J.final_exit_code(True, False), J.EXIT_REG_INTEGRITY)
        self.assertEqual(J.final_exit_code(False, True), J.EXIT_INCOMPLETE)
        self.assertEqual(J.final_exit_code(False, False), J.EXIT_BOTH)
        self.assertEqual(len({J.EXIT_CLEAN, J.EXIT_REG_INTEGRITY, J.EXIT_INCOMPLETE, J.EXIT_BOTH, J.EXIT_IDENTITY}), 5)

    def test_nothing_unidentifiable_is_ever_signalled(self):
        w = R.RegWriter(self.path)
        w.write("REGISTERED", node_id="n00001", pid=os.getpid(), starttime=5)                       # orphan: no INTENT
        w.write("INTENT", node_id="n00002", creator="O", label="B")
        w.write("REGISTERED", node_id="n00002", pid="12", starttime=5)                              # malformed
        w.write("INTENT", node_id="n00003", creator="O", label="C")
        w.write("FORKED", node_id="n00003", pid=os.getpid(), starttime=5)                           # forked, never identity-registered
        with open(self.path, "ab") as f:
            f.write(b'{"seq":9,"kind":"REGISTERED","node_id":"n00004","pid":' + str(os.getpid()).encode())     # torn
        sig = mock.Mock(side_effect=AssertionError("must not signal"))
        full = J.run_cleanup_full(self.path, signal_fn=sig, skip_pids=())
        self.assertEqual(full["targets"], [])
        sig.assert_not_called()

    def test_complete_records_are_still_handled_when_other_lines_are_corrupt(self):
        self.good(1)
        with open(self.path, "ab") as f:
            f.write(b"junk\n")
        fake = mock.Mock()
        with mock.patch.object(C, "PidfdHandle", return_value=fake):
            full = J.run_cleanup_full(self.path, signal_fn=lambda h, s: "sent", skip_pids=())
        self.assertEqual([t["result"] for t in full["targets"]], ["sent"])        # verified identity -> still cleaned; integrity is reported separately

    def run_main(self, prepare, cleanup_clear=True, dead=True):
        log = os.path.join(self.tmp.name, "j.jsonl")
        prepare()
        obs = mock.Mock()
        obs.exited.return_value = True
        with mock.patch.object(C, "PidfdHandle", return_value=obs), mock.patch.object(C, "process_is_dead", return_value=dead), \
                mock.patch.object(J, "cleanup_until_clear", return_value=(cleanup_clear, {})), mock.patch.object(J.time, "sleep"), \
                mock.patch.object(C, "read_stat", return_value=None):
            code = J.main(["janitor", self.path, "1", "2", log])
        events = [json.loads(x) for x in open(log).read().splitlines()]
        return code, events

    def finished(self):
        self.good(1)
        w = R.RegWriter(self.path)
        w.seq = len(R.parse_reg(self.path)[0])
        w.write("DEAD", node_id="n00001")
        w.write("RUN_END", cleanup_confirmed=True, aborted=None)

    def test_main_returns_clean_only_for_a_whole_file_and_a_confirmed_cleanup(self):
        code, ev = self.run_main(self.finished)
        self.assertEqual(code, J.EXIT_CLEAN)
        self.assertEqual([e["event"] for e in ev if e["event"] == "JANITOR_EXIT"][0], "JANITOR_EXIT")

    def test_main_never_returns_clean_on_a_damaged_file(self):
        def torn():
            self.finished()
            with open(self.path, "ab") as f:
                f.write(b'{"seq":9,"kind":"DEAD"')

        def corrupt():
            self.finished()
            with open(self.path, "ab") as f:
                f.write(b"junk\n")

        def missing():
            pass
        for prep, name in ((torn, "TORN_TAIL"), (corrupt, "CORRUPT"), (missing, "MISSING")):
            if os.path.exists(self.path):
                os.remove(self.path)
            code, ev = self.run_main(prep)
            self.assertEqual(code, J.EXIT_REG_INTEGRITY, name)
            alert = [e for e in ev if e["event"] == "REG_INTEGRITY_ALERT"]
            self.assertEqual(alert[0]["reg_integrity"], name)
            exit_ev = [e for e in ev if e["event"] == "JANITOR_EXIT"][0]
            self.assertEqual((exit_ev["cleanup_state"], exit_ev["reg_integrity"]), ("CONFIRMED", name))   # the two facts are logged separately

    def test_main_reports_incomplete_cleanup_and_both_failures_distinctly(self):
        def unconfirmed():
            self.good(1)
            w = R.RegWriter(self.path)
            w.seq = len(R.parse_reg(self.path)[0])
            w.write("RUN_END", cleanup_confirmed=False, aborted="runner exception")
        code, ev = self.run_main(unconfirmed, cleanup_clear=False, dead=False)
        self.assertEqual(code, J.EXIT_INCOMPLETE)                                   # cleanup open, file intact
        self.assertEqual([e for e in ev if e["event"] == "JANITOR_EXIT"][0]["cleanup_state"], "INCOMPLETE_RESPONSIBILITY_OPEN")
        os.remove(self.path)
        code, _ = self.run_main(lambda: None, cleanup_clear=False)                  # cleanup open AND file missing
        self.assertEqual(code, J.EXIT_BOTH)


# ===================================================================== FIX-002-C: BV evidence provenance
LABELS = {"BV-1": ("BV1", ["INTENT", "FORKED", "REGISTERED", "ABORTED", "DEAD"]), "BV-2": ("BV2-helper", ["INTENT", "FORKED", "REGISTERED", "RELEASED", "DEAD"]),
          "BV-3": ("BV3", ["INTENT", "FORKED", "REGISTERED", "DEAD"]), "BV-6": ("BV6", ["INTENT", "FORKED", "REGISTERED", "RELEASED", "DEAD"])}


def write_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, sort_keys=True)


def make_bv_run(root, run_id="bvrun1", auth_id="AUTH-BV-1", prereg=SHA, code=CODE, checks=EV.BV_RUN_LEVEL_IDS, confirmed=True, drop_label=None):
    d = os.path.join(root, run_id)
    os.makedirs(os.path.join(d, "validity_work"))
    open(os.path.join(d, EV.BV7_FILE), "w").write("torn\n")
    auth = {"schema": "e1a-auth-2", "authorized_by": "owner", "authorization_id": auth_id, "prereg_sha256": prereg, "bench_code_sha256": code,
            "phases": {EV.PHASE_BV: {"checks": list(EV.BV_RUN_LEVEL_IDS)}}}
    auth_bytes = json.dumps(auth, sort_keys=True).encode()
    open(os.path.join(d, "authorization_used.json"), "wb").write(auth_bytes)
    write_json(os.path.join(d, "environment.json"), {"phase": "bv", "prereg_sha256": prereg, "bench_code_sha256": code, "run_id": run_id,
                                                       "authorization_sha256": C.sha256_bytes(auth_bytes), "authorization_id": auth_id})
    write_json(os.path.join(d, "plan.json"), {"phase": "bv", "bv_checks": list(checks), "trials": []})
    write_json(os.path.join(d, "validity.json"), {"meta": {"run_id": run_id, "authorization_id": auth_id, "prereg_sha256": prereg, "bench_code_sha256": code,
                                                           "checks_run": list(checks)}, "results": {k: {"ok": True, "cleanup": {"cleanup_ok": True}} for k in checks}})
    w = R.RegWriter(os.path.join(d, "registry.jsonl"))
    w.write("RUN_START", run_id=run_id, prereg_sha256=prereg, phase="bv")
    n = 0
    for chk, (label, kinds) in LABELS.items():
        if label == drop_label:
            continue
        n += 1
        nid = "n%05d" % n
        for k in kinds:
            extra = {"pid": 1000 + n, "starttime": 5} if k in ("FORKED", "REGISTERED") else {}
            w.write(k, node_id=nid, creator="O", label=label, role="bv", mode="none", **extra)
    n += 1
    for k in ("INTENT", "FORKED", "REGISTERED", "RELEASED"):
        w.write(k, node_id="n%05d" % n, creator="O", label="JANITOR", role="janitor", mode="none", **({"pid": 7, "starttime": 5} if k in ("FORKED", "REGISTERED") else {}))
    w.write("RUN_END", aborted=None, cleanup_confirmed=confirmed)
    write_json(os.path.join(d, "summary.json"), {"phase": "bv", "aborted": None, "cleanup_confirmed": confirmed, "recovery_open": False, "janitor_exit": 0,
                                                 "planned_trials": 0})
    att = EV.build_attestation(d)
    return d, {"run_id": run_id, "bv_authorization_id": auth_id, "attestation_sha256": att["attestation_sha256"]}


class TestFix002CProvenance(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def verify(self, binding, **kw):
        return EV.verify_bv_provenance(binding, kw.get("prereg", SHA), kw.get("code", CODE), self.root)

    def assertRejected(self, binding, needle, **kw):
        ok, why = self.verify(binding, **kw)
        self.assertFalse(ok)
        self.assertTrue(any(needle in x for x in why), (needle, why))

    def test_a_genuine_consistent_run_verifies(self):
        d, b = make_bv_run(self.root)
        ok, why = self.verify(b)
        self.assertEqual((ok, why), (True, []))

    def test_no_binding_means_smoke_not_counted(self):
        make_bv_run(self.root)
        for b in (None, {}, {"run_id": "bvrun1"}, {"run_id": "bvrun1", "bv_authorization_id": "A"}, "bvrun1"):
            self.assertFalse(self.verify(b)[0], b)
        a = {"schema": RUN.AUTH_SCHEMA, "phases": {RUN.PHASE_CELLS: {"cells": ["E1A-a:P2"], "max_reps": 1}}}
        counted, detail = EV.evaluate_counting(a, True, SHA, CODE, self.root)
        self.assertFalse(counted)
        self.assertFalse(detail["verified"])

    def test_owner_binding_makes_the_cells_count(self):
        _, b = make_bv_run(self.root)
        a = {"phases": {RUN.PHASE_CELLS: {"cells": ["E1A-a:P2"], "max_reps": 1, "bv_binding": b}}}
        self.assertTrue(EV.evaluate_counting(a, True, SHA, CODE, self.root)[0])
        self.assertFalse(EV.evaluate_counting(a, False, SHA, CODE, self.root)[0])

    def test_edited_results_after_attestation(self):
        d, b = make_bv_run(self.root)
        v = json.load(open(os.path.join(d, "validity.json")))
        v["results"]["BV-2"]["ok"] = False
        write_json(os.path.join(d, "validity.json"), v)
        self.assertRejected(b, "recomputation")

    def test_edited_registry_summary_or_authorization_copy(self):
        for name, mutate in (("registry.jsonl", lambda p: open(p, "ab").write(b"\n")),
                             ("summary.json", lambda p: write_json(p, dict(json.load(open(p)), recovery_open=True))),
                             ("authorization_used.json", lambda p: write_json(p, {"authorization_id": "OTHER"})),
                             ("environment.json", lambda p: write_json(p, dict(json.load(open(p)), phase="cells")))):
            with tempfile.TemporaryDirectory() as t:
                self.root = t
                d, b = make_bv_run(t)
                mutate(os.path.join(d, name))
                ok, why = self.verify(b)
                self.assertFalse(ok, name)

    def test_the_owner_bound_digest_must_match(self):
        d, b = make_bv_run(self.root)
        self.assertRejected(dict(b, attestation_sha256="0" * 64), "digest differs")

    def test_a_hand_written_attestation_is_not_enough(self):
        d, b = make_bv_run(self.root)
        att = json.load(open(os.path.join(d, "bv_attestation.json")))
        att["results_sha256"] = "0" * 64                                           # forged field, digest recomputed to look valid
        att["attestation_sha256"] = EV.attestation_digest(att)
        write_json(os.path.join(d, "bv_attestation.json"), att)
        self.assertRejected(dict(b, attestation_sha256=att["attestation_sha256"]), "recomputation")

    def test_identity_fields_must_match_the_binding_and_the_current_build(self):
        d, b = make_bv_run(self.root)
        self.assertRejected(dict(b, bv_authorization_id="AUTH-OTHER"), "authorization")
        self.assertRejected(b, "preregistration", prereg="0" * 64)
        self.assertRejected(b, "bench code", code="d" * 64)

    def test_partial_or_failed_checks_never_count_even_when_self_consistent(self):
        _, b = make_bv_run(self.root, run_id="partial", checks=("BV-1", "BV-7"))
        self.assertRejected(b, "not all run-level checks")

    def test_missing_process_evidence_in_the_registry(self):
        _, b = make_bv_run(self.root, run_id="nobv2", drop_label="BV2-helper")
        self.assertRejected(b, "BV2-helper")

    def test_unconfirmed_cleanup_never_counts(self):
        _, b = make_bv_run(self.root, run_id="dirty", confirmed=False)
        self.assertRejected(b, "cleanup")

    def test_path_tricks_and_links_are_refused(self):
        d, b = make_bv_run(self.root)
        for rid in ("../bvrun1", "/etc", ".", "..", "a/b", "", "bv run", ".hidden"):
            self.assertFalse(self.verify(dict(b, run_id=rid))[0], rid)
        link = os.path.join(self.root, "linked")
        os.symlink(d, link)
        self.assertRejected(dict(b, run_id="linked"), "link")

    def test_missing_files(self):
        d, b = make_bv_run(self.root)
        os.remove(os.path.join(d, "bv_attestation.json"))
        self.assertRejected(b, "lacks")
        d2, b2 = make_bv_run(self.root, run_id="second")
        os.remove(os.path.join(d2, EV.BV7_FILE))
        self.assertRejected(b2, "BV-7")

    def test_a_cells_run_is_not_a_bv_run(self):
        d, b = make_bv_run(self.root)
        e = json.load(open(os.path.join(d, "environment.json")))
        e["phase"] = "cells"
        write_json(os.path.join(d, "environment.json"), e)
        att = EV.build_attestation(d)
        self.assertRejected(dict(b, attestation_sha256=att["attestation_sha256"]), "not a BV-phase run")

    def test_runner_wiring(self):
        src = inspect.getsource(RUN.execute)
        self.assertLess(src.index("authorization_used.json"), src.index("obs = O.Observer("))          # the copy is taken before anything runs
        self.assertLess(src.index('"summary.json"'), src.index("EV.build_attestation(out_dir)"))       # attestation is computed last, from final files
        self.assertEqual(tuple(RUN.V_RUN_LEVEL_IDS), tuple(EV.BV_RUN_LEVEL_IDS))
        main_src = inspect.getsource(RUN.main)
        self.assertIn("EV.evaluate_counting(", main_src)
        self.assertNotIn("bv_evidence", main_src)
        self.assertNotIn("verify_bv_evidence", inspect.getsource(RUN))


if __name__ == "__main__":
    unittest.main(verbosity=2)
