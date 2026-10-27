"""Table-driven pure-logic tests: the 67 static V4 rule cases (g0_preflight_review/g0_v4_cases.json) against the V5 judge, the conditional F3 /
requirements table, the fidelity report and M-2.  WRITTEN, NOT RUN (F3B-D1-A-CPU-003-E1A-G0-V5-IMPLEMENTATION-001); running them needs its own
authorization.  The cases are DESIGN-REVIEW records derived by hand from the V4/V5 rules (not results of any execution); this file turns them into
checks of the implementation.  No process is started.

Known label discrepancies between a case record and the frozen rule text (to be settled when the tests are run; the STATE is asserted for every
case, the rule label is asserted by membership in `rules_matched`):
  * CE-E1 : the record labels G0-C07 `C07-U1`; the frozen C07-U1 needs 'no release attempt recorded', but the case has a recorded attempt and no
            ledger, so the implementation reports `C07-U5` (required time missing).  State UNEVALUABLE either way.
  * F3C-2, F3C-6 : the record labels the LAST matching C07 rule (U7 / U6); the implementation lists every matching rule in id order (U5 first, because
            the ledger lacks REGISTERED / RELEASED) and the label must be among them."""
import copy
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import g0_v5_fixtures as F  # noqa: E402
import g0_auth as GA  # noqa: E402
import g0_judge as GJ  # noqa: E402

CRIT = F.criteria()
CASES = F.load_v4_cases()["cases"]
BY_ID = {c["id"]: c for c in CASES}
RULE_ALIASES = {("CE-E1", "C07-U1"): "C07-U5"}


def judge_case(case):
    return GJ.judge(F.case_evidence(case), CRIT, GA.FROZEN_CRITERIA_SHA256)


def base_rule(label):
    return label.split("(")[0] if label else ""


def clause_of(label):
    m = re.search(r"\((\w+)\)", label or "")
    return m.group(1) if m else None


class TestCaseTable(unittest.TestCase):
    def test_the_case_file_has_the_67_cases(self):
        self.assertEqual(len(CASES), 67)
        self.assertEqual(sum(1 for c in CASES if c.get("origin") == "V3 case migrated"), 51)

    def test_every_case_matches_its_recorded_states_rules_and_verdict(self):
        failures = []
        for c in CASES:
            r = judge_case(c)
            c3, c7 = r["checks"]["G0-C03"], r["checks"]["G0-C07"]
            for name, got, want in (("C03", c3, c["c03"]), ("C07", c7, c["c07"])):
                if got["state"] != want["state"]:
                    failures.append("%s %s state %s != %s (%s)" % (c["id"], name, got["state"], want["state"], got.get("detail")))
                    continue
                if want["rule"]:
                    label = RULE_ALIASES.get((c["id"], base_rule(want["rule"])), base_rule(want["rule"]))
                    if label not in got["rules_matched"]:
                        failures.append("%s %s rule %s not in %s" % (c["id"], name, label, got["rules_matched"]))
                    cl = clause_of(want["rule"])
                    if cl and name == "C03" and cl not in got.get("clauses", []):
                        failures.append("%s C03 clause %s not in %s" % (c["id"], cl, got.get("clauses")))
                elif got["state"] != "PASS":
                    failures.append("%s %s should PASS" % (c["id"], name))
            if r["verdict"] != c["final"]:
                failures.append("%s final %s != %s" % (c["id"], r["verdict"], c["final"]))
            if c["c16"] == "PASS" and r["checks"]["G0-C16"]["status"] != "PASS":
                failures.append("%s C16 should PASS: %s" % (c["id"], r["checks"]["G0-C16"]["detail"]))
            if c["c16"] != "PASS" and r["checks"]["G0-C16"]["status"] == "PASS":
                failures.append("%s C16 should not PASS" % c["id"])
        self.assertEqual(failures, [])

    def test_a_final_fail_comes_only_from_an_evidenced_fail_class_check(self):
        for c in CASES:
            r = judge_case(c)
            if r["verdict"] == "FAIL":
                self.assertTrue(set(r["fail_class"]) & {"G0-C03", "G0-C07"}, c["id"])
            else:
                self.assertEqual(r["fail_class"], [], c["id"])

    def test_the_only_pass_is_the_normal_case(self):
        passes = [c["id"] for c in CASES if judge_case(c)["verdict"] == "PASS"]
        self.assertEqual(passes, ["CE-R1"])

    def test_the_three_v3_to_v4_verdict_changes(self):
        changed = {c["id"]: (c["v3_final"], c["final"]) for c in CASES if c.get("changed")}
        self.assertEqual(changed, {"CE-R6": ("FAIL", "BLOCKED"), "CE-R7": ("FAIL", "BLOCKED"), "CE-R8b": ("FAIL", "BLOCKED")})
        for cid in changed:
            self.assertEqual(judge_case(BY_ID[cid])["verdict"], "BLOCKED", cid)

    def test_fail_scope_is_a_bench_protocol_failure(self):
        self.assertIn("bench/protocol", GJ.FAIL_SCOPE)
        self.assertIn("not evidence about the Mythos model architecture", GJ.FAIL_SCOPE)


class TestFidelityAndM2(unittest.TestCase):
    FID = ("FID-A", "FID-B", "FID-C", "FID-D", "FID-E", "FID-F")

    def test_fid_cases_report_the_concrete_unfaithful_evidence(self):
        for cid in self.FID:
            c = BY_ID[cid]
            rep = judge_case(c)["checks"]["G0-C03"]["report"]
            for want in c["fidelity_report_expected"]:
                hit = [e for e in rep if e["type"] == want["type"] and e.get("seq") == want["seq"] and e.get("kind") == want["kind"]]
                self.assertTrue(hit, "%s: %r not in %r" % (cid, want, rep))
                if want.get("fields"):
                    self.assertEqual(sorted(hit[0]["fields"]), sorted(want["fields"]), cid)
                self.assertTrue(hit[0]["ledger_canon_prefix"] and hit[0]["durable_canon_prefix"])

    def test_fid_a_to_e_are_blocked_and_the_disk_dependent_checks_are_unevaluable(self):
        for cid in self.FID[:5]:
            c = BY_ID[cid]
            r = judge_case(c)
            self.assertEqual(r["verdict"], "BLOCKED", cid)
            self.assertEqual(r["fail_class"], [], cid)
            self.assertEqual(r["checks"]["G0-C03"]["rule"], "C03-U2", cid)
            for chk in c["disk_dependent_unevaluable"]:
                self.assertEqual(r["checks"][chk]["status"], "UNEVALUABLE", (cid, chk))
                self.assertEqual(r["checks"][chk]["rule"], "M-2", (cid, chk))

    def test_fid_f_the_ledger_proven_violation_is_not_cancelled_by_the_damaged_file(self):
        r = judge_case(BY_ID["FID-F"])
        self.assertEqual(r["verdict"], "FAIL")
        self.assertEqual(r["checks"]["G0-C03"]["rules_matched"][0], "C03-F1")
        self.assertEqual(r["checks"]["G0-C03"]["credibility"]["level"], "first-hand")

    def test_the_report_lists_lost_foreign_altered_parse_and_count(self):
        ev = F.good_evidence()
        led = ev["reg_memory_records"]
        ev["reg"] = [copy.deepcopy(led[0]), copy.deepcopy(led[1])]          # five records lost
        ev["reg"][1]["creator"] = "n7"                                      # one altered
        ev["reg"].append({"seq": 9, "kind": "FORKED", "node_id": "n9", "pid": 1})  # one foreign
        ev["reg_parse_info"] = {"torn_tail": True, "corrupt_lines": 2, "missing": False, "unreadable": False}
        rep = GJ.fidelity(ev)
        types = {e["type"] for e in rep["report"]}
        self.assertEqual(types, {"PARSE", "COUNT", "LOST", "FOREIGN", "ALTERED"})
        self.assertFalse(rep["faithful"])
        self.assertTrue(rep["foreign"])

    def test_the_report_is_limited_to_fifty_entries_with_the_total(self):
        ev = F.good_evidence()
        big = [{"seq": i, "kind": "FORKED", "node_id": "n1", "pid": i} for i in range(1, 121)]
        ev["reg_memory_records"], ev["reg"], ev["reg_writer_seq"] = big, [], 120
        rep = GJ.fidelity(ev)
        self.assertEqual(len(rep["report"]), 50)
        self.assertGreater(rep["total"], 50)

    def test_a_reordered_durable_copy_is_unfaithful(self):
        ev = F.good_evidence()
        ev["reg"][2], ev["reg"][3] = ev["reg"][3], ev["reg"][2]
        rep = GJ.fidelity(ev)
        self.assertFalse(rep["faithful"])
        self.assertTrue(rep["report"])

    def test_each_parse_irregularity_alone_makes_the_copy_unfaithful(self):
        for k, v in (("torn_tail", True), ("corrupt_lines", 1), ("missing", True), ("unreadable", True)):
            ev = F.good_evidence()
            ev["reg_parse_info"][k] = v
            self.assertFalse(GJ.fidelity(ev)["faithful"], k)
            self.assertEqual(GJ.judge(ev, CRIT, GA.FROZEN_CRITERIA_SHA256)["checks"]["G0-C03"]["rule"], "C03-U2", k)

    def test_identical_records_with_other_key_order_are_faithful(self):
        ev = F.good_evidence()
        ev["reg"] = [dict(reversed(list(r.items()))) for r in ev["reg"]]
        self.assertTrue(GJ.fidelity(ev)["faithful"])


class TestC03Requirements(unittest.TestCase):
    """Rules x witness requirements (checks.G0-C03.rules.requirements) -- every toggle of the table is exercised."""

    def ev(self, cid):
        return F.case_evidence(BY_ID[cid])

    def c03(self, ev):
        return GJ.check_c03(ev, CRIT)

    def test_the_table_in_the_criteria_is_the_one_the_tests_assume(self):
        rows = CRIT["checks"]["G0-C03"]["rules"]["requirements"]["rows"]
        self.assertEqual({k: v["needs_writer_clean"] for k, v in rows.items()},
                         {"C03-F1": False, "C03-F2": True, "C03-F3a": True, "C03-F3b": True, "C03-F3c": False, "C03-F4": True})
        self.assertTrue(all(v["needs_ledger"] and not v["relies_on_durable_copy"] for v in rows.values()))
        self.assertEqual({k for k, v in rows.items() if v["needs_no_foreign_lines"]}, {"C03-F2", "C03-F3a", "C03-F3b", "C03-F3c", "C03-F4"})

    def unclean(self, ev):
        """an append failed: the ledger keeps its records, but a record was lost (seq gap) and the writer's seq is ahead"""
        led = ev["reg_memory_records"]
        led[-1]["seq"] += 1
        ev["reg"][-1]["seq"] += 1
        ev["reg_writer_seq"] = led[-1]["seq"]
        return ev

    def foreign(self, ev):
        ev["reg"].append({"seq": len(ev["reg"]) + 1, "kind": "FORKED", "node_id": "n1", "pid": 999})
        return ev

    def test_f1_needs_neither_a_clean_writer_nor_the_absence_of_foreign_lines(self):
        for mut in (lambda e: e, self.unclean, self.foreign):
            r = self.c03(mut(self.ev("CE-D1")))
            self.assertEqual((r["state"], r["rules_matched"][0]), ("FAIL", "C03-F1"))

    def test_f2_needs_a_clean_writer_and_no_foreign_lines(self):
        self.assertEqual(self.c03(self.ev("CE-F2"))["rules_matched"][0], "C03-F2")
        r = self.c03(self.unclean(self.ev("CE-F2")))
        self.assertEqual((r["state"], r["rule"]), ("UNEVALUABLE", "C03-U3"))
        r = self.c03(self.foreign(self.ev("CE-F2")))
        self.assertEqual((r["state"], r["rule"]), ("UNEVALUABLE", "C03-U2"))

    def test_f3a_needs_a_clean_writer_and_no_foreign_lines(self):
        self.assertEqual(self.c03(self.ev("F3A-1"))["rules_matched"][0], "C03-F3a")
        r = self.c03(self.unclean(self.ev("F3A-1")))
        self.assertEqual((r["state"], r["rule"]), ("UNEVALUABLE", "C03-U3"))
        r = self.c03(self.foreign(self.ev("F3A-1")))
        self.assertEqual((r["state"], r["rule"]), ("UNEVALUABLE", "C03-U2"))

    def test_f3b_needs_a_clean_writer_and_no_foreign_lines(self):
        self.assertEqual(self.c03(self.ev("F3B-1"))["rules_matched"][0], "C03-F3b")
        r = self.c03(self.unclean(self.ev("F3B-1")))
        self.assertEqual((r["state"], r["rule"]), ("UNEVALUABLE", "C03-U3"))
        r = self.c03(self.foreign(self.ev("F3B-1")))
        self.assertEqual((r["state"], r["rule"]), ("UNEVALUABLE", "C03-U2"))

    def test_f3c_does_not_need_a_clean_writer_but_needs_no_foreign_lines(self):
        e = self.ev("CE-R4c")                                   # the writer is NOT clean here (the REGISTERED append failed)
        self.assertFalse(GJ.writer_clean(e["reg_memory_records"], e["reg_writer_seq"]))
        r = self.c03(e)
        self.assertEqual((r["state"], r["rules_matched"][0]), ("FAIL", "C03-F3c"))
        r = self.c03(self.foreign(self.ev("CE-R4c")))
        self.assertEqual((r["state"], r["rule"]), ("UNEVALUABLE", "C03-U2"))

    def test_f3c_needs_a_proven_gate_pass_two_independent_witnesses_in_order(self):
        base = self.ev("CE-R4c")
        for mut, why in ((lambda e: e["guard"]["release_writes"].clear(), "no recorded attempt"),
                         (lambda e: e["guard"]["release_writes"].__setitem__(0, dict(e["guard"]["release_writes"][0], result="error", returned=None, errno=32, error="EPIPE")), "write failed"),
                         (lambda e: e["guard"]["release_writes"].append(dict(e["guard"]["release_writes"][0])), "two attempts"),
                         (lambda e: e["events"].__setitem__("first_action_mono", 1.755), "child before the write returned"),
                         (lambda e: e["events"].__setitem__("first_action_mono", None), "no gate pass")):
            e = copy.deepcopy(base)
            mut(e)
            r = self.c03(e)
            self.assertNotEqual(r["state"], "FAIL", why)

    def test_f4_needs_a_clean_writer_no_foreign_lines_and_a_completed_run(self):
        self.assertEqual(self.c03(self.ev("CE-C1"))["rules_matched"][0], "C03-F4")
        r = self.c03(self.unclean(self.ev("CE-C1")))
        self.assertNotEqual(r["state"], "FAIL")
        r = self.c03(self.foreign(self.ev("CE-C1")))
        self.assertNotEqual(r["state"], "FAIL")
        e = self.ev("CE-C1")
        e["exception"] = "RuntimeError: stopped"
        self.assertNotEqual(self.c03(e)["state"], "FAIL")

    def test_append_failure_or_seq_gap_alone_is_blocked_never_fail(self):
        for cid in ("F3-GAP", "CE-G1", "CE-F5", "CE-R5c"):
            r = self.c03(self.ev(cid))
            self.assertEqual((r["state"], r["rule"]), ("UNEVALUABLE", "C03-U3"), cid)

    def test_unconfirmable_pass_or_contradicting_witnesses_are_blocked(self):
        for cid in ("CE-R6", "CE-R7", "CE-R8a", "CE-R8b", "F3C-2", "F3C-6"):
            r = judge_case(BY_ID[cid])
            self.assertEqual(r["verdict"], "BLOCKED", cid)

    def test_definitions_release_attempt_write_ok_and_gate_passed_are_distinct(self):
        e = self.ev("CE-R2")                                     # an attempt that failed, no gate pass
        ind = GJ.independent(e)
        self.assertEqual((ind["release_attempt"], ind["release_write_ok"], ind["gate_passed"]), (True, False, False))
        e = self.ev("CE-R3")                                     # a write that succeeded, no gate pass
        ind = GJ.independent(e)
        self.assertEqual((ind["release_attempt"], ind["release_write_ok"], ind["gate_passed"]), (True, True, False))
        e = self.ev("CE-R8a")                                    # a gate pass with no recorded attempt
        ind = GJ.independent(e)
        self.assertEqual((ind["release_attempt"], ind["release_write_ok"], ind["gate_passed"], ind["gate_pass_proven"], ind["gate_pass_unconfirmed"]),
                         (False, False, True, False, True))
        ind = GJ.independent(self.ev("CE-R1"))
        self.assertTrue(ind["gate_pass_proven"])
        self.assertFalse(ind["gate_pass_unconfirmed"])

    def test_release_write_ok_needs_a_returned_value_of_exactly_one(self):
        e = F.good_evidence()
        e["guard"]["release_writes"][0]["returned"] = 2
        self.assertFalse(GJ.independent(e)["release_write_ok"])
        e["guard"]["release_writes"][0]["returned"] = True                  # a bool is not an int: the record is format-damaged, the witness is unavailable
        self.assertFalse(GJ.independent(e)["available"])

    def test_writer_clean_is_defined_on_the_ledger_and_the_writer_seq(self):
        led = F.good_ledger()
        self.assertTrue(GJ.writer_clean(led, 7))
        self.assertFalse(GJ.writer_clean(led, 8))
        self.assertTrue(GJ.writer_clean([], 0))
        led[3]["seq"] = 5
        self.assertFalse(GJ.writer_clean(led, 7))


class TestC07Rules(unittest.TestCase):
    def c07(self, mutate=None, **ev_changes):
        e = F.good_evidence()
        if mutate:
            mutate(e)
        return GJ.check_c07(e, CRIT)

    def test_pass_needs_attempt_success_and_gate_pass_in_order(self):
        self.assertEqual(self.c07()["state"], "PASS")

    def test_f1_registered_or_released_later_than_the_attempt(self):
        r = self.c07(lambda e: e["reg_memory_records"][4].update(mono=1.74 + 0.02))
        self.assertEqual((r["state"], r["rule"]), ("FAIL", "C07-F1"))
        r = self.c07(lambda e: (e["reg_memory_records"][3].update(mono=1.8)))
        self.assertEqual((r["state"], r["rule"]), ("FAIL", "C07-F1"))

    def test_f2_more_than_one_release_write(self):
        r = self.c07(lambda e: e["guard"]["release_writes"].append(dict(e["guard"]["release_writes"][0])))
        self.assertEqual((r["state"], r["rules_matched"][0]), ("FAIL", "C07-F2"))

    def test_f3_the_child_acted_before_the_release_was_attempted(self):
        r = self.c07(lambda e: e["events"].update(first_action_mono=1.7))
        self.assertEqual((r["state"], r["rule"]), ("FAIL", "C07-F3"))

    def test_u_rules(self):
        wr = lambda e, **kw: e["guard"]["release_writes"][0].update(kw)
        table = (
            ("C07-U1", lambda e: (e["guard"]["release_writes"].clear(), e["events"].update(first_action_mono=None))),
            ("C07-U2", lambda e: (wr(e, result="error", returned=None, errno=32, error="EPIPE"), e["events"].update(first_action_mono=None))),
            ("C07-U3", lambda e: e["events"].update(first_action_mono=None)),
            ("C07-U4", lambda e: e["guard"]["release_writes"].clear()),
            ("C07-U6", lambda e: wr(e, result="error", returned=None, errno=32, error="EPIPE")),
            ("C07-U7", lambda e: (wr(e, mono_after=1.85), e["events"].update(first_action_mono=1.8))),
        )
        for rule, mut in table:
            r = self.c07(mut)
            self.assertEqual(r["state"], "UNEVALUABLE", rule)
            self.assertIn(rule, r["rules_matched"], rule)

    def test_u5_a_time_is_missing(self):
        r = self.c07(lambda e: e["reg_memory_records"].pop(4))
        self.assertEqual((r["state"], r["rule"]), ("UNEVALUABLE", "C07-U5"))

    def test_a_pre_write_time_is_never_evidence_that_the_byte_was_written(self):
        r = self.c07(lambda e: e["guard"].pop("release_writes"))
        self.assertEqual(r["state"], "UNEVALUABLE")

    def test_the_judge_never_reads_the_v2_pre_write_list(self):
        e = F.good_evidence()
        e["guard"]["release_byte_pre_write_monos"] = [1.75]
        e["guard"]["release_writes"] = []
        e["events"]["first_action_mono"] = None
        self.assertEqual(GJ.check_c07(e, CRIT)["rule"], "C07-U1")


if __name__ == "__main__":
    unittest.main(verbosity=2)
