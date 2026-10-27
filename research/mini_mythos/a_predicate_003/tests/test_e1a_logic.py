"""E1-A bench tests -- PURE LOGIC (no fork, no signals, no sacrificial processes).  WRITTEN, NOT RUN (PREP-001 forbids running tests
in this round).  These test the bench and the S0 logic against the frozen preregistration; they do not run the experiment."""
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "bench"))
sys.path.insert(0, os.path.join(HERE, "..", "tools"))
import candidates as K      # noqa: E402
import common as C          # noqa: E402
import registry as R        # noqa: E402
import scenarios as S       # noqa: E402
import truth as T           # noqa: E402

PREREG, SHA = S.load_prereg()
CHECKS = PREREG["s0_checks"]
SUP = 1000


def st(pid, ppid, sid, pgrp, start=100, state="S"):
    return {"state": state, "ppid": ppid, "pgrp": pgrp, "sid": sid, "starttime": start, "comm": "x"}


def view(table, root=1001, reg_start=None, sigchld_default=True, sigign=0, problems=None, scan_error=None):
    reg = table[root] if root in table else st(root, SUP, root, root)
    return {"root_registered": {"pid": root, "starttime": reg["starttime"] if reg_start is None else reg_start, "sid": reg["sid"], "pgrp": reg["pgrp"]},
            "sup_pid": SUP, "sup_sid": SUP, "declared_aux": [], "table": None if scan_error else table, "problems": problems or {},
            "scan_error": scan_error, "sigchld_is_default": sigchld_default, "sigign_mask": sigign}


def base_table():
    return {SUP: st(SUP, 1, SUP, SUP), 1001: st(1001, SUP, 1001, 1001)}


OK_SUB = {"set_ok": True, "get_value": 1}


def topology(scn):
    """Synthetic kernel view mirroring what the scenario's real topology looks like to the supervisor (see scenarios.RECIPES)."""
    t, kw, sub = base_table(), {}, OK_SUB
    if scn == "E1A-a2" or scn == "E1A-i":
        t[900] = st(900, 1, SUP, SUP)                              # X: orphaned, supervisor's session, not a child of SUP
    if scn in ("E1A-b", "E1A-i"):
        t[1001] = st(1001, SUP, SUP, SUP)
    if scn == "E1A-c":
        t[1001] = st(1001, SUP, SUP, 1001)
    if scn == "E1A-d":
        t = {SUP: st(SUP, 1, SUP, SUP), 1002: st(1002, 1, 1001, 1001)}
        kw["root"] = 1002
    if scn == "E1A-e1":
        t[1003] = st(1003, 1001, 1001, 1001)
    if scn == "E1A-e2":
        t[1003] = st(1003, SUP, SUP, SUP)
    if scn == "E1A-f":
        kw["reg_start"] = 101
    if scn == "E1A-g":
        kw.update(sigchld_default=False, sigign=C.SIGIGN_SIGCHLD_BIT)
    if scn == "E1A-h1":
        sub = {"set_ok": False, "get_value": 0}
    if scn == "E1A-h2":
        sub = {"set_ok": True, "get_value": 0}
    return view(t, **kw), sub


class TestP2AgainstFrozenTable(unittest.TestCase):
    def test_every_scenario_matches_the_frozen_p2_cell(self):
        for scn in S.SCENARIO_ORDER:
            v, sub = topology(scn)
            out = K.s0_check(v, sub, CHECKS)
            cell = PREREG["classification"][scn]["P2"]
            self.assertEqual(out["verdict"], cell["expected_s0_verdict"], scn)
            if cell["expected_s0_verdict"] == "BLOCKED":
                self.assertEqual(out["codes"], cell["expected_codes"], scn)
                self.assertEqual(out["cited_rules"], cell["cited_rules_required"], scn)

    def test_judge_passes_the_frozen_expectation_for_p2_everywhere(self):
        for scn in S.SCENARIO_ORDER:
            v, sub = topology(scn)
            out = K.s0_check(v, sub, CHECKS)
            events = [{"seq": 1, "phase": "S0", "call": "S0_START", "infra": False}, {"seq": 2, "phase": "S0", "call": "S0_VERDICT", "infra": False}]
            self.assertEqual(T.judge(PREREG, scn, "P2", out, events, [])["verdict"], "PASS", scn)

    def test_premise_c6_blocks_c1_to_c5(self):
        t = base_table()
        t[1001] = st(1001, SUP, SUP, SUP)                          # would be C1,C2,C3 ...
        out = K.s0_check(view(t, reg_start=999), OK_SUB, CHECKS)   # ... but the fingerprint does not hold
        self.assertEqual(out["codes"], ["ROOT_FINGERPRINT_MISMATCH"])

    def test_incomplete_enumeration_is_unknown_never_accept(self):
        out = K.s0_check(view(base_table(), problems={4242: "EACCES"}), OK_SUB, CHECKS)
        self.assertEqual(out["verdict"], "UNKNOWN")
        out = K.s0_check(view(base_table(), scan_error="listdir failed"), OK_SUB, CHECKS)
        self.assertEqual(out["verdict"], "UNKNOWN")

    def test_definite_defect_beats_unknown(self):
        t = base_table()
        t[1001] = st(1001, SUP, SUP, SUP)
        out = K.s0_check(view(t, problems={4242: "EACCES"}), OK_SUB, CHECKS)
        self.assertEqual(out["verdict"], "BLOCKED")

    def test_s0_check_is_pure(self):
        v, sub = topology("E1A-b")
        import copy
        before = copy.deepcopy(v)
        K.s0_check(v, sub, CHECKS)
        self.assertEqual(v, before)


class TestP0P1Adapters(unittest.TestCase):
    """Uses the test process's own pid as the 'root' and fake prctl functions: no fork, no signal, no flag change."""

    def node(self, delta=0):
        fp = C.fingerprint(os.getpid())
        return {"pid": fp["pid"], "starttime": fp["starttime"] + delta, "sid": fp["sid"], "pgrp": fp["pgrp"]}

    def test_p0_accept_and_blocked_codes(self):
        self.assertEqual(K.run_p0(self.node(), lambda f: True, lambda: 1)["verdict"], "ACCEPT")
        self.assertEqual(K.run_p0(self.node(1), lambda f: True, lambda: 1)["codes"], ["ROOT_FINGERPRINT_MISMATCH"])
        self.assertEqual(K.run_p0(self.node(), lambda f: False, lambda: 0)["codes"], ["PREFLIGHT_FAILED"])
        self.assertEqual(K.run_p0(self.node(), lambda f: True, lambda: 0)["codes"], ["PREFLIGHT_FAILED"])

    def test_p1_blocks_a_root_that_is_not_a_dedicated_session(self):
        out = K.run_p1(self.node(), lambda f: True, lambda: 1)
        if os.getsid(0) != os.getpid():                            # the test process is not a session leader
            self.assertEqual(out["codes"], ["STAGE_SESSION_NOT_DEDICATED"])

    def test_p0_is_blind_to_session_defects(self):
        # P0 cannot prove C1..C5/C7: it accepts the test process (a non-leader) -> this is the frozen UNPROVABLE finding
        self.assertEqual(K.run_p0(self.node(), lambda f: True, lambda: 1)["verdict"], "ACCEPT")


class TestVerdictLogic(unittest.TestCase):
    EV_OK = [{"seq": 1, "phase": "S0", "call": "S0_START", "infra": False}, {"seq": 2, "phase": "S0", "call": "S0_VERDICT", "infra": False}]

    def out(self, v, codes=(), cited=()):
        return {"verdict": v, "codes": list(codes), "cited_rules": list(cited)}

    def test_unprovable_accept_is_fail_and_refusal_is_pass(self):
        self.assertEqual(T.judge(PREREG, "E1A-e1", "P1", self.out("ACCEPT"), self.EV_OK, [])["verdict"], "FAIL")
        self.assertEqual(T.judge(PREREG, "E1A-e1", "P1", self.out("BLOCKED", ["X"]), self.EV_OK, [])["verdict"], "PASS")
        self.assertEqual(T.judge(PREREG, "E1A-e1", "P1", self.out("UNKNOWN"), self.EV_OK, [])["verdict"], "PASS")

    def test_provable_blocked_needs_exact_codes_and_cited_rules_within_ecd(self):
        ok = self.out("BLOCKED", ["STAGE_SESSION_NOT_DEDICATED"], ["PR-S0-1", "PR-S0-2"])
        self.assertEqual(T.judge(PREREG, "E1A-b", "P1", ok, self.EV_OK, [])["verdict"], "PASS")
        self.assertEqual(T.judge(PREREG, "E1A-b", "P1", self.out("BLOCKED", ["OTHER"], ["PR-S0-1"]), self.EV_OK, [])["verdict"], "FAIL")
        self.assertEqual(T.judge(PREREG, "E1A-b", "P1", self.out("BLOCKED", ["STAGE_SESSION_NOT_DEDICATED"], ["PR-S0-4"]), self.EV_OK, [])["verdict"], "FAIL")

    def test_false_reject_is_fail(self):
        self.assertEqual(T.judge(PREREG, "E1A-a", "P2", self.out("BLOCKED", ["X"]), self.EV_OK, [])["verdict"], "FAIL")

    def test_unsafe_event_in_s0_is_fail_but_infra_wait_is_not(self):
        bad = self.EV_OK + [{"seq": 3, "phase": "S0", "call": "os.waitpid", "infra": False}]
        self.assertEqual(T.judge(PREREG, "E1A-a", "P2", self.out("ACCEPT"), bad, [])["verdict"], "FAIL")
        infra = self.EV_OK + [{"seq": 3, "phase": "SETUP", "call": "os.waitpid", "infra": True}]
        self.assertEqual(T.judge(PREREG, "E1A-a", "P2", self.out("ACCEPT"), infra, [])["verdict"], "PASS")

    def test_bench_reason_blocks_before_anything_else(self):
        self.assertEqual(T.judge(PREREG, "E1A-a", "P2", self.out("ACCEPT"), self.EV_OK, ["TOPOLOGY_NOT_AS_DESIGNED"])["verdict"], "BLOCKED")

    def test_cell_candidate_experiment_aggregation(self):
        self.assertEqual(T.cell_verdict(["PASS"] * 20, 20, 0.05)[0], "PASS")
        self.assertEqual(T.cell_verdict(["PASS"] * 19 + ["BLOCKED"], 20, 0.05)[0], "PASS")
        self.assertEqual(T.cell_verdict(["PASS"] * 18 + ["BLOCKED"] * 2, 20, 0.05)[0], "BLOCKED")
        self.assertEqual(T.cell_verdict(["PASS"] * 19 + ["FAIL"], 20, 0.05)[0], "FAIL")
        self.assertEqual(T.cell_verdict(["PASS"] * 5, 20, 0.05)[0], "BLOCKED")
        self.assertEqual(T.candidate_verdict(["PASS", "FAIL"]), "FAIL")
        self.assertEqual(T.candidate_verdict(["PASS", "BLOCKED"]), "BLOCKED")
        self.assertEqual(T.experiment_verdict({"P0": "FAIL", "P1": "FAIL", "P2": "PASS"}, True, False), "PASS")
        self.assertEqual(T.experiment_verdict({"P0": "PASS", "P2": "FAIL"}, True, False), "FAIL")
        self.assertEqual(T.experiment_verdict({"P2": "PASS"}, True, True), "FAIL")
        self.assertEqual(T.experiment_verdict({"P2": "PASS"}, False, False), "BLOCKED")


class TestIndependentTruth(unittest.TestCase):
    def test_kernel_defects_match_the_frozen_defect_sets_for_every_real_scenario(self):
        for scn in S.SCENARIO_ORDER:
            if PREREG["scenarios"][scn]["evidence_kind"] != "REAL_KERNEL":
                continue
            v, _ = topology(scn)
            root = v["root_registered"]["pid"]
            sigign = v["sigign_mask"]
            d, _ = T.kernel_defects({"pid": root}, SUP, v["table"], v["problems"], sigign)
            self.assertEqual(sorted(d), sorted(PREREG["scenarios"][scn]["defects"]), scn)

    def test_simulated_scenarios_show_no_real_defect(self):
        for scn in ("E1A-f", "E1A-h1", "E1A-h2"):
            v, _ = topology(scn)
            d, _ = T.kernel_defects({"pid": v["root_registered"]["pid"]}, SUP, v["table"], v["problems"], v["sigign_mask"])
            self.assertEqual(d, set(), scn)
            self.assertEqual(S.expected_real_defects(PREREG, scn), [])

    def test_topology_reasons_flag_a_mismatch_and_a_set_subreaper(self):
        fp = {"starttime": 1, "sid": 2, "pgrp": 3}
        self.assertEqual(T.topology_reasons([], set(), fp, fp, 0, []), [])
        self.assertTrue(T.topology_reasons(["C1"], set(), fp, fp, 0, []))
        self.assertTrue(T.topology_reasons([], set(), fp, dict(fp, sid=9), 0, []))
        self.assertTrue(T.topology_reasons([], set(), fp, fp, 1, []))

    def test_bystander_reasons(self):
        self.assertEqual(T.bystander_reasons("X", st(900, 1, SUP, SUP), SUP, SUP, True), [])
        self.assertTrue(T.bystander_reasons("X", st(900, SUP, SUP, SUP), SUP, SUP, True))
        self.assertTrue(T.bystander_reasons("X", st(900, 1, 5, 5), SUP, SUP, True))
        self.assertTrue(T.bystander_reasons("X", None, SUP, SUP, True))


class TestRegistryLogic(unittest.TestCase):
    def reg(self, d):
        w = R.RegWriter(os.path.join(d, "reg.jsonl"))
        return w

    def test_torn_tail_and_intent_only_are_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            w = self.reg(d)
            w.write("INTENT", node_id="a", creator="O")
            w.write("INTENT", node_id="b", creator="O")
            w.write("REGISTERED", node_id="b", pid=11, starttime=5)
            with open(w.path, "ab") as f:
                f.write(b'{"seq":9,"kind":"REGISTERED","node_id":"a","pid":12')
            recs, info = R.parse_reg(w.path)
            self.assertTrue(info["torn_tail"])
            self.assertEqual([t["node_id"] for t in R.cleanup_targets(recs)], ["b"])

    def test_dead_and_aborted_nodes_are_not_targets(self):
        with tempfile.TemporaryDirectory() as d:
            w = self.reg(d)
            for n in ("a", "b"):
                w.write("INTENT", node_id=n, creator="O")
                w.write("REGISTERED", node_id=n, pid=11, starttime=5)
            w.write("DEAD", node_id="a")
            w.write("ABORTED", node_id="b", reason="x")
            self.assertEqual(R.cleanup_targets(R.parse_reg(w.path)[0]), [])

    def test_check_order_detects_release_before_register(self):
        good = [{"seq": 1, "kind": "INTENT", "node_id": "a", "creator": "O"}, {"seq": 2, "kind": "REGISTERED", "node_id": "a"}, {"seq": 3, "kind": "RELEASED", "node_id": "a"}]
        self.assertEqual(R.check_order(good), [])
        bad = [good[0], good[2], good[1]]
        self.assertTrue(R.check_order([dict(r, seq=i + 1) for i, r in enumerate(bad)]))
        child_first = [{"seq": 1, "kind": "INTENT", "node_id": "c", "creator": "a"}]
        self.assertTrue(R.check_order(child_first))


class TestPlanAndRecipes(unittest.TestCase):
    def test_plan_size_and_cells(self):
        plan = S.plan_trials(PREREG)
        self.assertEqual(len(plan), PREREG["repetitions"]["planned_trials"]["total"])
        self.assertEqual(len({t["trial_id"] for t in plan}), len(plan))
        self.assertEqual(sum(1 for t in plan if t["kind"] == "sweep"), 400)
        self.assertEqual(len({(t["scenario"], t["candidate"]) for t in plan if t["kind"] == "cell"}), 36)

    def test_every_recipe_has_a_root_and_matches_evidence_kind(self):
        for scn, r in S.RECIPES.items():
            self.assertIn("root", S.all_labels(r), scn)
            self.assertEqual(PREREG["scenarios"][scn]["evidence_kind"] == "SIMULATED", bool(r.get("injection")), scn)

    def test_exit_after_ready_nodes_are_not_expected_alive(self):
        self.assertEqual(sorted(S.expected_alive_labels(S.RECIPES["E1A-a2"])), ["X", "root"])
        self.assertEqual(S.expected_alive_labels(S.RECIPES["E1A-d"]), ["root"])


class TestStaticPolicy(unittest.TestCase):
    def test_static_audit_reports_no_violation(self):
        import static_audit
        v = []
        for f in sorted(os.listdir(static_audit.BENCH)):
            if f.endswith(".py"):
                v += static_audit.audit_file(os.path.join(static_audit.BENCH, f))[0]
        self.assertEqual(v, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
