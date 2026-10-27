"""Failure-path tests for F3B-D1-A-CPU-003-E1A-STATIC-CLOSEOUT-001 (CLOSEOUT-01: unconfirmed creation of revoked tickets;
CLOSEOUT-02: registration-file run lifecycle).  WRITTEN, NOT RUN.  PURE: files, pipes and in-process socket pairs only -- no fork, no
signal, no sacrificial process; /proc and pidfd access is mocked."""
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "bench"))
import common as C          # noqa: E402
import janitor as J         # noqa: E402
import observer as O        # noqa: E402
import proto                # noqa: E402
import registry as R        # noqa: E402

ALIVE = {"state": "S", "starttime": 5, "ppid": 1, "pgrp": 1, "sid": 1, "comm": "x"}


# ===================================================================== CLOSEOUT-01
class TicketCase(unittest.TestCase):
    """A creator (socket pair, no process) is granted a ticket; the test plays the creator and keeps / drops the gate read end."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.obs = O.Observer(os.path.join(self.tmp.name, "registry.jsonl"))
        self.obs.reg.write("RUN_START", run_id="t", observer_pid=1)
        self.obs.trial_tag = "T"
        self.fds, self.socks = [], []
        self.obs.counter += 1
        self.creator = O.NodeRec("n00001", "x", "C", "O", {})
        a, self.peer = proto.socketpair()
        self.socks += [a, self.peer]
        self.creator.trial, self.creator.state, self.creator.pid, self.creator.starttime, self.creator.sock = "T", "RELEASED", 111, 1, a
        self.obs.nodes["n00001"] = self.creator
        # the creator is a registered, released node (excluded from the cleanup under test via exclude ids)
        self.obs.reg.write("INTENT", node_id="n00001", creator="O", label="C", role="x", mode="none")
        self.obs.reg.write("FORKED", node_id="n00001", pid=111, starttime=1)
        self.obs.reg.write("REGISTERED", node_id="n00001", pid=111, starttime=1, role="x")
        self.obs.reg.write("RELEASED", node_id="n00001")

    def tearDown(self):
        for fd in self.fds:
            try:
                os.close(fd)
            except OSError:
                pass
        for r in self.obs.nodes.values():
            if r.gate_w is not None:
                os.close(r.gate_w)
        for s in self.socks:
            s.close()
        self.tmp.cleanup()

    def grant(self, label="kid"):
        self.obs._on_ticket(self.creator, {"t": "TICKET", "role": "sleeper", "label": label, "spec": {}})
        msg, fds = proto.recv_msg(self.peer, 1.0)
        self.assertEqual(msg["t"], "TICKET_OK")
        self.fds += fds
        return self.obs.nodes[msg["node_id"]], fds[0]                   # (ticket node, the gate READ end held by the "creator")

    def drop(self, fd):
        os.close(fd)
        self.fds.remove(fd)

    def cleanup(self, grace=0.02):
        with mock.patch.object(C, "read_stat", return_value=None):
            return self.obs.final_cleanup({"n00001"}, grace=grace)


class TestCloseout01TicketCreation(TicketCase):
    def test_ticket_states(self):
        kid, _ = self.grant()
        self.assertEqual((kid.state, kid.creation), ("INTENT", "TICKET_ISSUED"))
        self.assertFalse(os.get_blocking(kid.gate_w))                              # probe writes can never block
        self.obs.close_intake()
        self.assertEqual((kid.state, kid.creation, kid.revoked), ("ABORTED", "UNRESOLVED_REVOKED", True))
        self.assertIsNotNone(kid.gate_w)                                           # kept open as the probe

    def test_revoked_ticket_whose_gate_may_still_have_a_reader_blocks_the_whole_cleanup(self):
        kid, gate_r = self.grant()
        with mock.patch.object(C, "PidfdHandle") as H:
            rep = self.cleanup()
        H.assert_not_called()                                                      # no pid guessed, no signal
        self.assertFalse(rep["cleanup_ok"])
        self.assertEqual(rep["residual_after_kill"], [kid.node_id])
        self.assertIn("TICKET creation not proven absent", rep["residual_detail"][0]["identity"])
        self.assertTrue(any("not proven absent" in p for p in rep["run_set"]["problems"]))
        self.assertNotEqual(kid.state, "DEAD")
        self.assertIsNone(kid.creation_proof)

    def test_proof_requires_that_nobody_can_hold_the_gate_any_more(self):
        kid, gate_r = self.grant()
        self.obs.close_intake()
        with mock.patch.object(C, "read_stat", return_value=None):
            self.assertFalse(self.obs._confirmed_dead(kid))                         # the creator still holds gate_r
            self.drop(gate_r)                                                       # creator died without ever forking (or its child exited)
            self.assertTrue(self.obs._confirmed_dead(kid))
        self.assertIn("EPIPE", kid.creation_proof)

    def test_after_the_proof_the_cleanup_is_clean_and_the_basis_is_recorded(self):
        kid, gate_r = self.grant()
        self.drop(gate_r)
        rep = self.cleanup()
        self.assertTrue(rep["cleanup_ok"], rep)
        dead = [r for r in self.obs.reg.records if r["kind"] == "DEAD" and r["node_id"] == kid.node_id]
        self.assertEqual(len(dead), 1)
        self.assertIn("EPIPE", dead[0]["basis"])
        self.assertEqual(R.integrity_issues(R.parse_reg(self.obs.reg_path)[0]), [])  # file order stays legal

    def test_created_after_revocation_but_before_the_proof_never_resolves_by_pid(self):
        kid, gate_r = self.grant()
        self.obs.close_intake()
        with mock.patch.object(C, "read_stat", return_value=None), mock.patch.object(C, "PidfdHandle") as H:
            self.obs._on_created(self.creator, {"t": "CREATED", "node_id": kid.node_id, "pid": 4242})
            self.assertEqual(kid.creation, "REPORTED")
            self.assertEqual(kid.forked_pid, 4242)
            self.assertFalse(self.obs._confirmed_dead(kid))                         # /proc says "gone", but the gate may still have a reader
        H.assert_not_called()
        reply, _ = proto.recv_msg(self.peer, 1.0)
        self.assertEqual(reply["t"], "REGISTER_FAILED")
        self.assertNotIn("REGISTERED", [r["kind"] for r in self.obs.reg.records if r.get("node_id") == kid.node_id])
        self.drop(gate_r)
        with mock.patch.object(C, "read_stat", return_value=None):
            self.assertTrue(self.obs._confirmed_dead(kid))                          # now proven

    def test_created_after_the_proof_is_remembered_in_memory_only(self):
        kid, gate_r = self.grant()
        self.drop(gate_r)
        self.assertTrue(self.cleanup()["cleanup_ok"])
        before = len(self.obs.reg.records)
        with mock.patch.object(C, "read_stat", return_value=ALIVE):                  # the pid may even have been reused by now
            self.obs._on_created(self.creator, {"t": "CREATED", "node_id": kid.node_id, "pid": 4242})
        self.assertEqual(kid.late_created_pid, 4242)
        self.assertIsNone(kid.forked_pid)
        self.assertEqual(len(self.obs.reg.records), before)                          # nothing is written after DEAD
        self.assertEqual(kid.state, "DEAD")
        with mock.patch.object(C, "read_stat", return_value=ALIVE):
            self.assertEqual(self.obs.residual([kid]), [])                           # the late report cannot flip a finished cleanup
        proto.recv_msg(self.peer, 1.0)

    def test_created_after_a_failed_verification_cannot_turn_it_into_a_pass(self):
        kid, gate_r = self.grant()
        rep = self.cleanup()
        self.assertFalse(rep["cleanup_ok"])                                         # creation not proven absent at verification time
        with mock.patch.object(C, "read_stat", return_value=None):
            self.obs._on_created(self.creator, {"t": "CREATED", "node_id": kid.node_id, "pid": 4242})
            self.assertEqual(self.obs.residual([kid]), [kid.node_id])                # still open: only the gate proof closes it
        proto.recv_msg(self.peer, 1.0)

    def test_creator_reported_fork_failure_still_needs_the_gate_proof(self):
        kid, gate_r = self.grant()
        proto.send_msg(self.peer, {"t": "CREATE_FAILED", "node_id": kid.node_id, "err": "EAGAIN"})
        self.obs._handle(self.creator)
        self.assertEqual((kid.state, kid.creation), ("ABORTED", "UNRESOLVED_REVOKED"))
        with mock.patch.object(C, "read_stat", return_value=None):
            self.assertFalse(self.obs._confirmed_dead(kid))                         # a claim by the creator is not proof
            self.drop(gate_r)
            self.assertTrue(self.obs._confirmed_dead(kid))

    def test_a_raising_fork_in_the_observer_is_proven_by_the_exception(self):
        with mock.patch.object(O.gate, "fork_gated", side_effect=OSError(11, "EAGAIN")):
            rec = self.obs.spawn_direct("x", "D", {"mode": "none"}, lambda fd: None)
        self.assertEqual((rec.state, rec.creation), ("ABORTED", "NONE_PROVEN_FORK_FAILED"))
        self.assertTrue(self.obs._confirmed_dead(rec))

    def test_registration_failed_ticketed_child_is_resolved_by_the_gate_not_by_its_pid(self):
        kid, gate_r = self.grant()
        with mock.patch.object(C, "fingerprint", return_value={"pid": 4242, "starttime": 5, "sid": 1, "pgrp": 1, "ppid": 999, "state": "S"}), \
                mock.patch.object(C, "PidfdHandle") as H:
            kid.state = "FORKED"
            self.obs._note_forked(kid, 4242, self.creator.pid)
            self.assertFalse(self.obs._register(kid, 4242, self.creator.pid))        # ppid mismatch -> ABORTED, identity never verified
        self.assertEqual(kid.state, "ABORTED")
        self.assertIsNotNone(kid.gate_w)                                             # probe kept for the unverified child
        with mock.patch.object(C, "read_stat", return_value=None):
            self.assertFalse(self.obs._confirmed_dead(kid))
            self.drop(gate_r)
            self.assertTrue(self.obs._confirmed_dead(kid))


class TestCloseout01Registry(unittest.TestCase):
    def test_unresolved_tickets_in_the_registration_file(self):
        recs = [{"seq": 1, "kind": "INTENT", "node_id": "a", "creator": "n1", "label": "k"},
                {"seq": 2, "kind": "ABORTED", "node_id": "a", "creation_unresolved": True},
                {"seq": 3, "kind": "INTENT", "node_id": "b", "creator": "O"},                      # direct: not a ticket
                {"seq": 4, "kind": "INTENT", "node_id": "c", "creator": "n1"}, {"seq": 5, "kind": "FORKED", "node_id": "c", "pid": 9},
                {"seq": 6, "kind": "INTENT", "node_id": "d", "creator": "n1"}, {"seq": 7, "kind": "DEAD", "node_id": "d"}]
        self.assertEqual([t["node_id"] for t in R.unresolved_tickets(recs)], ["a"])

    def test_janitor_reports_but_cannot_resolve_them(self):
        recs = [{"seq": 1, "kind": "INTENT", "node_id": "a", "creator": "n1", "label": "k"}]
        rep = J.unresolved_report(recs)
        self.assertEqual([(u["node_id"], u["alive"], u["kind"]) for u in rep], [("a", None, "TICKET_CREATION_UNPROVEN")])

    def test_a_confirmed_run_end_does_not_hide_an_unresolved_ticket(self):
        base = [{"seq": 1, "kind": "RUN_START", "run_id": "t", "observer_pid": 1}, {"seq": 2, "kind": "INTENT", "node_id": "a", "creator": "n1"}]
        end = {"seq": 3, "kind": "RUN_END", "run_id": "t", "cleanup_confirmed": True}
        self.assertEqual(J.decide(base + [end], False), "CLEANUP")
        with_dead = base + [{"seq": 3, "kind": "DEAD", "node_id": "a"}, dict(end, seq=4)]
        self.assertEqual(J.decide(with_dead, False), "EXIT_CONFIRMED")

    def test_the_janitor_can_never_clear_an_unproven_ticket(self):
        recs = [{"seq": 1, "kind": "INTENT", "node_id": "a", "creator": "n1"}]
        with mock.patch.object(J, "run_cleanup_full", return_value={"targets": [], "unresolved": []}), \
                mock.patch.object(J.R, "parse_reg", return_value=(recs, {})), mock.patch.object(J.time, "sleep"):
            self.assertFalse(J.cleanup_until_clear("x", None, attempts=2, interval=0)[0])


# ===================================================================== CLOSEOUT-02
def reg(path, *items):
    w = R.RegWriter(path)
    for kind, fields in items:
        w.write(kind, **fields)
    return w


START = ("RUN_START", {"run_id": "t", "observer_pid": 1})
INTENT = ("INTENT", {"node_id": "n1", "creator": "O", "label": "L", "role": "bv"})
REGD = ("REGISTERED", {"node_id": "n1", "pid": 1000, "starttime": 5, "role": "bv"})
DEAD = ("DEAD", {"node_id": "n1"})
END = ("RUN_END", {"run_id": "t", "aborted": None, "cleanup_confirmed": True})
JAN = [("INTENT", {"node_id": "n2", "creator": "O", "label": "JANITOR", "role": "janitor"}),
       ("REGISTERED", {"node_id": "n2", "pid": os.getpid(), "starttime": 5, "role": "janitor"})]


class TestCloseout02Lifecycle(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "reg.jsonl")

    def tearDown(self):
        self.tmp.cleanup()

    def issues(self, *items):
        if os.path.exists(self.path):
            os.remove(self.path)
        reg(self.path, *items)
        return R.integrity_issues(R.parse_reg(self.path)[0])

    def has(self, issues, needle):
        self.assertTrue(any(needle in x for x in issues), (needle, issues))

    def test_a_complete_lifecycle_has_no_issue(self):
        self.assertEqual(self.issues(START, INTENT, REGD, DEAD, *JAN, END), [])
        self.assertEqual(self.issues(START, INTENT, REGD), [])                      # a run that is still going on is legal

    def test_run_end_alone_cannot_stand_for_a_lifecycle(self):
        i = self.issues(END)
        self.has(i, "RUN_START_COUNT=0")
        self.has(i, "RUN_END_WITHOUT_RUN_START")

    def test_missing_run_start(self):
        self.has(self.issues(INTENT, REGD, DEAD, END), "RUN_START_COUNT=0")

    def test_duplicate_run_start(self):
        self.has(self.issues(START, START, INTENT), "RUN_START_COUNT=2")

    def test_run_start_must_be_first_and_legal(self):
        i = self.issues(INTENT, START)
        self.has(i, "RUN_START_NOT_FIRST")
        self.has(i, "NODE_RECORD_BEFORE_RUN_START")
        for bad in ({"run_id": "", "observer_pid": 1}, {"run_id": "t"}, {"run_id": "t", "observer_pid": "1"}, {"observer_pid": 1}):
            self.has(self.issues(("RUN_START", bad), INTENT), "RUN_START_ILLEGAL")

    def test_duplicate_run_end(self):
        i = self.issues(START, INTENT, REGD, DEAD, END, END)
        self.has(i, "DUPLICATE_RUN_END")
        self.has(i, "RECORD_AFTER_RUN_END")

    def test_creation_records_after_run_end(self):
        for rec in (("INTENT", {"node_id": "n9", "creator": "O", "label": "late"}), ("REGISTERED", {"node_id": "n1", "pid": 1, "starttime": 5}),
                    ("FORKED", {"node_id": "n1", "pid": 1, "starttime": 5}), ("RELEASED", {"node_id": "n1"}), ("DEAD", {"node_id": "n9"})):
            self.has(self.issues(START, INTENT, REGD, DEAD, END, rec), "RECORD_AFTER_RUN_END")

    def test_run_end_must_belong_to_this_run_and_be_well_formed(self):
        self.has(self.issues(START, INTENT, DEAD, ("RUN_END", {"run_id": "other", "cleanup_confirmed": True})), "RUN_END_FOR_DIFFERENT_RUN")
        self.has(self.issues(START, INTENT, DEAD, ("RUN_END", {"cleanup_confirmed": True})), "RUN_END_FOR_DIFFERENT_RUN")
        for bad in ("yes", 1, None):
            self.has(self.issues(START, INTENT, DEAD, ("RUN_END", {"run_id": "t", "cleanup_confirmed": bad})), "RUN_END_ILLEGAL")

    def test_run_end_before_run_start(self):
        self.has(self.issues(END, START), "RUN_END_BEFORE_RUN_START")

    def test_a_confirmed_run_end_over_unfinished_nodes_is_an_impossible_order(self):
        self.has(self.issues(START, INTENT, REGD, END), "CONFIRMED_RUN_END_WITH_UNFINISHED_NODES")
        self.assertEqual(self.issues(START, INTENT, REGD, *JAN, ("DEAD", {"node_id": "n1"}), END), [])      # the janitor itself is exempt
        self.assertEqual(self.issues(START, INTENT, REGD, ("RUN_END", {"run_id": "t", "cleanup_confirmed": False})), [])

    def test_records_after_dead_and_duplicates(self):
        self.has(self.issues(START, INTENT, DEAD, REGD), "RECORD_AFTER_DEAD")
        self.has(self.issues(START, INTENT, INTENT), "DUPLICATE_INTENT")

    def test_integrity_is_what_the_janitor_sees(self):
        reg(self.path, END)
        with mock.patch.object(J.time, "sleep"):
            r, _ = J.reg_integrity(self.path)
        self.assertEqual((r["status"], r["ok"]), ("CORRUPT", False))


class TestCloseout02Janitor(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "reg.jsonl")
        self.log = os.path.join(self.tmp.name, "j.jsonl")

    def tearDown(self):
        self.tmp.cleanup()

    def main(self, *items, obs_pid=1, clear=True):
        if os.path.exists(self.path):
            os.remove(self.path)
        reg(self.path, *items)
        if os.path.exists(self.log):
            os.remove(self.log)
        obs = mock.Mock()
        obs.exited.return_value = True
        with mock.patch.object(C, "PidfdHandle", return_value=obs), mock.patch.object(C, "process_is_dead", return_value=True), \
                mock.patch.object(J, "cleanup_until_clear", return_value=(clear, {})), mock.patch.object(J.time, "sleep"), \
                mock.patch.object(C, "read_stat", return_value=dict(ALIVE)):
            code = J.main(["janitor", self.path, str(obs_pid), "2", self.log])
        return code, [json.loads(x) for x in open(self.log).read().splitlines()]

    def test_positive_control_a_whole_confirmed_run_exits_clean(self):
        self.assertEqual(self.main(START, INTENT, REGD, DEAD, *JAN, END)[0], J.EXIT_CLEAN)

    def test_broken_lifecycles_never_exit_clean(self):
        scenarios = {"only RUN_END": [END], "missing RUN_START": [INTENT, REGD, DEAD, *JAN, END], "duplicate RUN_END": [START, INTENT, REGD, DEAD, *JAN, END, END],
                     "creation after RUN_END": [START, INTENT, REGD, DEAD, *JAN, END, ("INTENT", {"node_id": "n9", "creator": "O", "label": "x"})],
                     "RUN_END of another run": [START, INTENT, REGD, DEAD, *JAN, ("RUN_END", {"run_id": "other", "cleanup_confirmed": True})],
                     "confirmed over unfinished node": [START, INTENT, REGD, *JAN, END], "duplicate RUN_START": [START, START, INTENT, REGD, DEAD, *JAN, END]}
        for name, items in scenarios.items():
            code, ev = self.main(*items)
            self.assertNotEqual(code, J.EXIT_CLEAN, name)
            self.assertEqual(code, J.EXIT_REG_INTEGRITY, name)                       # the cleanup state itself is fine; the file is not
            exit_ev = [e for e in ev if e["event"] == "JANITOR_EXIT"][0]
            self.assertEqual(exit_ev["reg_integrity"], "CORRUPT", name)
            self.assertTrue(any("RUN" in x or "CONFIRMED" in x for x in exit_ev["reg_issues"]), (name, exit_ev["reg_issues"]))

    def test_without_its_own_registration_the_janitor_never_claims_a_clean_exit(self):
        no_own = [START, INTENT, REGD, DEAD, END]
        code, ev = self.main(*no_own)
        self.assertEqual(code, J.EXIT_REG_INTEGRITY)
        self.assertTrue(any("NO_OWN_REGISTRATION" in x for e in ev for x in e.get("reg_issues", []) + e.get("issues", [])))
        other = [START, INTENT, REGD, DEAD, ("INTENT", {"node_id": "n2", "creator": "O", "label": "JANITOR", "role": "janitor"}),
                 ("REGISTERED", {"node_id": "n2", "pid": os.getpid() + 1, "starttime": 5, "role": "janitor"}), END]       # somebody else's registration
        self.assertEqual(self.main(*other)[0], J.EXIT_REG_INTEGRITY)
        wrong_role = [START, INTENT, REGD, DEAD, ("INTENT", {"node_id": "n2", "creator": "O", "label": "J"}),
                      ("REGISTERED", {"node_id": "n2", "pid": os.getpid(), "starttime": 5, "role": "bv"}), END]
        self.assertEqual(self.main(*wrong_role)[0], J.EXIT_REG_INTEGRITY)

    def test_a_registration_file_of_a_different_observer_is_not_accepted(self):
        self.assertEqual(self.main(START, INTENT, REGD, DEAD, *JAN, END, obs_pid=2)[0], J.EXIT_REG_INTEGRITY)

    def test_unresolved_ticket_and_broken_file_together(self):
        items = [START, INTENT, REGD, DEAD, ("INTENT", {"node_id": "n3", "creator": "n1", "label": "kid"}), *JAN, END]
        code, _ = self.main(*items, clear=False)
        self.assertEqual(code, J.EXIT_BOTH)                                         # confirmed RUN_END over an unfinished ticket node + cleanup unconfirmed

    def test_no_guessing_and_no_unverified_signal_on_a_lifecycle_broken_file(self):
        reg(self.path, END, ("INTENT", {"node_id": "n1", "creator": "O", "label": "L"}), ("FORKED", {"node_id": "n1", "pid": os.getpid(), "starttime": 5}))
        sig = mock.Mock(side_effect=AssertionError("must not signal"))
        full = J.run_cleanup_full(self.path, signal_fn=sig, skip_pids=())
        self.assertEqual(full["targets"], [])                                       # FORKED-only: reported, never signalled
        sig.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
