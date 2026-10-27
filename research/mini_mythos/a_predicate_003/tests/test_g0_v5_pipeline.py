"""Pure-logic tests for the evidence pipeline P0..P7 and the closure publication K0..K7 of g0_run: the 19 closure-pipeline failure cases of
g0_preflight_review/g0_v5_cases.json and the 15 pipeline cases of g0_v4_cases.json, with injected faults (write / fsync / read-back / link
failures, an exception in the judge, a non-JSON value in the evidence, a pre-existing file).  WRITTEN, NOT RUN
(F3B-D1-A-CPU-003-E1A-G0-V5-IMPLEMENTATION-001); running them needs its own authorization.  Everything happens in a temporary directory; the
evidence root of the repository is never written (GA.EVIDENCE_ROOT is redirected); no process is started."""
import contextlib
import errno
import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import g0_v5_fixtures as F  # noqa: E402
import g0_auth as GA  # noqa: E402
import g0_judge as GJ  # noqa: E402
import g0_run as GR  # noqa: E402

CRIT = F.criteria()
V5 = F.load_v5_cases()
V4 = F.load_v4_cases()
TOOL_SHA, TOOL_ID = GA.FROZEN_CRITERIA_SHA256, GA.CRITERIA_ID
NAMES = {"REG": "registry.jsonl", "EV": "g0_evidence.json", "SUM": "g0_summary.json", "CL": "g0_closed.json", "TMP": "g0_closed.json.tmp", "MAN": "MANUAL_DISPOSITION_REQUIRED.json"}


class Harness(unittest.TestCase):
    RUN_ID = "g0_pipe_test_1"

    @contextlib.contextmanager
    def fresh(self):
        """a new temporary evidence root with one empty run directory; GA.EVIDENCE_ROOT is redirected so that the repository is never written"""
        with tempfile.TemporaryDirectory() as root, mock.patch.object(GA, "EVIDENCE_ROOT", root):
            self.root = root
            self.run_dir = os.path.join(root, self.RUN_ID)
            os.mkdir(self.run_dir)
            open(os.path.join(self.run_dir, "registry.jsonl"), "wb").close()
            yield

    def setUp(self):
        stack = contextlib.ExitStack()
        stack.enter_context(self.fresh())
        self.addCleanup(stack.close)

    def evidence(self, verdict="PASS"):
        ev = F.good_evidence()
        ev["run_id"] = self.RUN_ID
        if verdict == "FAIL":
            ev["guard"]["violations"] = [{"call": "os.kill", "mono": 1.0, "args": "()"}]
        elif verdict == "BLOCKED":
            ev["exception"] = "RuntimeError: stopped"
        return ev

    def fin(self, ev=None, patches=None):
        """run GR.finalize on `ev` with {(module, name): replacement} patches -> (exit code, stderr text)"""
        patches = patches or {}
        ev = ev if ev is not None else self.evidence()
        err = io.StringIO()
        with contextlib.ExitStack() as st:
            for (obj, name), val in patches.items():
                st.enter_context(mock.patch.object(obj, name, val))
            st.enter_context(contextlib.redirect_stderr(err))
            rc = GR.finalize(ev, self.RUN_ID, self.run_dir, CRIT, TOOL_SHA)
        return rc, err.getvalue()

    def files(self):
        return sorted(os.listdir(self.run_dir))

    def want_files(self, keys):
        return sorted(NAMES[k] for k in keys)

    def next_preflight(self):
        facts = GR.collect_run_facts(self.RUN_ID, self.run_dir, TOOL_ID, TOOL_SHA)
        return [h["reason"] for h in GJ.closure_reasons(facts, {"root_manual_disposition": False, "root_listing": "complete", "live_marker_process": False}, CRIT)
                if h["scope"] == "directory"], facts

    def read(self, name):
        return open(os.path.join(self.run_dir, name), "rb").read()


# ------------------------------------------------------------------ fault injectors
def write_fails(suffix, half=False, partial=True):
    real = GR.write_exclusive

    def w(path, data):
        if path.endswith(suffix):
            if half:
                with open(path, "wb") as f:
                    f.write(data[: len(data) // 2])
            raise GR.Unsaved(partial, "injected write failure (ENOSPC)", GJ.sha256_hex(data))
        return real(path, data)
    return w


def read_differs(suffix):
    real = GR.read_back

    def r(path):
        b = real(path)
        return (b[:-2] + b"xy") if path.endswith(suffix) else b
    return r


def read_raises(suffix, why="not a regular file"):
    real = GR.read_back

    def r(path):
        if path.endswith(suffix):
            raise GR.Unverified(why)
        return real(path)
    return r


class FsyncFault:
    """os.fsync that fails on the n-th call.  Calls in a normal run: 1 evidence file, 2 run directory, 3 summary file, 4 run directory,
    5 temporary marker file (K2), 6 run directory (K5)."""

    def __init__(self, *fail_at):
        self.n, self.fail_at, self.real = 0, set(fail_at), os.fsync

    def __call__(self, fd):
        self.n += 1
        if self.n in self.fail_at:
            raise OSError(errno.EIO, "injected fsync failure")
        return self.real(fd)


def link_then_alter():
    real = os.link

    def l(src, dst, *a, **k):
        real(src, dst, *a, **k)
        with open(dst, "ab") as f:                                   # the shared inode is altered after the link returned
            f.write(b"\n")
    return l


class Bomb(dict):
    """a summary whose second read of 'exit_code' raises (the read in K7, after K1 read it once)"""

    def __init__(self, *a, **k):
        dict.__init__(self, *a, **k)
        self.reads = 0

    def __getitem__(self, key):
        if key == "exit_code":
            self.reads += 1
            if self.reads >= 2:
                raise RuntimeError("injected exception at K7")
        return dict.__getitem__(self, key)


class TestClosurePipelineCases(Harness):
    """The 19 cases of closure.publication / P-stage failures."""

    def apply(self, cid):
        """-> (exit code, stderr) for one case id"""
        d = self.run_dir
        if cid == "PC-P2":
            return self.fin(patches={(GR, "write_exclusive"): write_fails("g0_evidence.json", half=True)})
        if cid == "PC-P3":
            return self.fin(patches={(GR, "read_back"): read_differs("g0_evidence.json")})
        if cid == "PC-P5":
            return self.fin(patches={(GJ, "judge"): mock.Mock(side_effect=RuntimeError("judge exploded"))})
        if cid == "PC-P6a":
            return self.fin(patches={(GR, "write_exclusive"): write_fails("g0_summary.json", half=True)})
        if cid == "PC-P6b":
            return self.fin(patches={(GR, "read_back"): read_differs("g0_summary.json")})
        if cid == "PC-P6c":
            return self.fin(patches={(os, "fsync"): FsyncFault(3)})
        if cid == "PC-K1":
            return self.fin(patches={(GJ, "build_marker"): mock.Mock(side_effect=ValueError("impossible pair"))})
        if cid == "PC-K2a":
            open(os.path.join(d, "g0_closed.json.tmp"), "wb").write(b"pre-existing")
            return self.fin()
        if cid == "PC-K2b":
            return self.fin(patches={(GR, "write_exclusive"): write_fails("g0_closed.json.tmp", half=True)})
        if cid == "PC-K2c":
            return self.fin(patches={(os, "fsync"): FsyncFault(5)})
        if cid == "PC-K3":
            return self.fin(patches={(GR, "read_back"): read_differs("g0_closed.json.tmp")})
        if cid == "PC-K4a":
            open(os.path.join(d, "g0_closed.json"), "wb").write(b'{"foreign":true}')
            return self.fin()
        if cid == "PC-K4b":
            return self.fin(patches={(os, "link"): mock.Mock(side_effect=OSError(errno.EPERM, "links are not permitted"))})
        if cid == "PC-K5":
            return self.fin(patches={(os, "fsync"): FsyncFault(6)})
        if cid == "PC-K6":
            return self.fin(patches={(os, "link"): link_then_alter()})
        if cid in ("PC-K7", "PC-K7b", "PC-OK", "PC-OK2"):
            raise AssertionError("handled separately")
        raise AssertionError(cid)

    def test_cases_with_an_injected_fault(self):
        bad = []
        for c in V5["pipeline_cases"]:
            if c["id"] in ("PC-K7", "PC-K7b", "PC-OK", "PC-OK2"):
                continue
            with self.fresh():
                rc, err = self.apply(c["id"])
                reasons, facts = self.next_preflight()
                e = c["expected"]
                names = [n for n in self.files() if not n.startswith("g0_blocked_")]
                problems = []
                if rc != e["process_exit_code"]:
                    problems.append("exit %s != %s" % (rc, e["process_exit_code"]))
                if c["stderr_marker"] not in err:
                    problems.append("stderr lacks %s: %r" % (c["stderr_marker"], err))
                if names != sorted(c["files_present"]):                 # the case record already lists real file names
                    problems.append("files %s != %s" % (names, sorted(c["files_present"])))
                want = {"absent": ["NO_CLOSED"], "schema_invalid": ["CLOSED_SCHEMA"], "noncanonical": ["CLOSED_NONCANONICAL"], "ok": []}[c["closed_after"]]
                if reasons != e["next_preflight_reasons"] or reasons != want:
                    problems.append("next preflight %s != %s" % (reasons, e["next_preflight_reasons"]))
                if facts["closed"] != c["closed_after"]:
                    problems.append("closed fact %s != %s" % (facts["closed"], c["closed_after"]))
                if facts["tmp"] != c["tmp_after"]:
                    problems.append("tmp fact %s != %s" % (facts["tmp"], c["tmp_after"]))
                if (c["published"] and "G0-CLOSE-UNCONFIRMED" not in err) or (not c["published"] and c["stderr_marker"].startswith("G0-CLOSE") and "G0-CLOSE-UNPUBLISHED" not in err):
                    problems.append("published flag vs marker")
                if problems:
                    bad.append((c["id"], problems))
        self.assertEqual(bad, [])

    def test_k7_an_exception_after_the_marker_was_verified(self):
        bc_ev = GJ.strict_bytes(self.evidence())
        s = {"run_id": self.RUN_ID, "criteria_id": TOOL_ID, "criteria_sha256": TOOL_SHA, "evidence_sha256": GJ.sha256_hex(bc_ev), "verdict": "PASS", "exit_code": 0}
        sb = GJ.strict_bytes(s)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rc = GR.publish_closure(self.run_dir, self.RUN_ID, TOOL_SHA, bc_ev, sb, Bomb(s))
        c = next(x for x in V5["pipeline_cases"] if x["id"] == "PC-K7")
        self.assertEqual(rc, c["expected"]["process_exit_code"])
        self.assertIn("G0-CLOSE-UNCONFIRMED", err.getvalue())
        self.assertIn("step=K7", err.getvalue())
        reasons, facts = self.next_preflight()
        self.assertEqual(facts["closed"], "ok")

    def test_k7b_a_base_exception_right_after_the_link_returned(self):
        calls = {"n": 0}
        real = GR.fsync_dir

        def fsync_dir(path):
            calls["n"] += 1
            if calls["n"] == 3:                                    # P2, P6, then K5
                raise KeyboardInterrupt()
            return real(path)
        rc, err = self.fin(self.evidence("FAIL"), patches={(GR, "fsync_dir"): fsync_dir})
        c = next(x for x in V5["pipeline_cases"] if x["id"] == "PC-K7b")
        self.assertEqual(rc, c["expected"]["process_exit_code"])
        self.assertIn("G0-CLOSE-UNCONFIRMED", err)
        reasons, facts = self.next_preflight()
        self.assertEqual((reasons, facts["closed"], facts["tmp"]), ([], "ok", "identical"))
        recorded = json.loads(self.read("g0_closed.json").decode())
        self.assertEqual((recorded["recorded_verdict"], recorded["recorded_exit_code"]), ("FAIL", 1))     # the saved record is not altered by the failure

    def test_success_returns_the_recorded_exit_code_after_the_marker_was_verified(self):
        for cid, verdict, code in (("PC-OK2", "PASS", 0), ("PC-OK", "FAIL", 1), (None, "BLOCKED", 3)):
            with self.fresh():
                rc, err = self.fin(self.evidence(verdict))
                self.assertEqual((rc, err), (code, ""), cid)
                reasons, facts = self.next_preflight()
                self.assertEqual((reasons, facts["closed"], facts["tmp"]), ([], "ok", "identical"), cid)
                o = json.loads(self.read("g0_closed.json").decode())
                self.assertEqual((o["recorded_verdict"], o["recorded_exit_code"], o["process_exit_proof"]), (verdict, code, False))
                s = json.loads(self.read("g0_summary.json").decode())
                self.assertEqual((s["verdict"], s["exit_code"]), (verdict, code))
                self.assertEqual("fail_scope" in s, verdict == "FAIL")
                if verdict == "FAIL":
                    self.assertEqual(s["fail_scope"], GJ.FAIL_SCOPE)

    def test_the_cases_cover_the_expected_ids(self):
        self.assertEqual(len(V5["pipeline_cases"]), 19)
        self.assertEqual({c["id"] for c in V5["pipeline_cases"]},
                         {"PC-P2", "PC-P3", "PC-P5", "PC-P6a", "PC-P6b", "PC-P6c", "PC-K1", "PC-K2a", "PC-K2b", "PC-K2c", "PC-K3", "PC-K4a", "PC-K4b", "PC-K5", "PC-K6",
                          "PC-K7", "PC-K7b", "PC-OK", "PC-OK2"})


class TestPublicationProperties(Harness):
    def test_publication_is_atomic_exclusive_and_the_temporary_name_is_kept(self):
        rc, _ = self.fin()
        self.assertEqual(rc, 0)
        a, b = os.stat(os.path.join(self.run_dir, "g0_closed.json")), os.stat(os.path.join(self.run_dir, "g0_closed.json.tmp"))
        self.assertEqual((a.st_ino, a.st_nlink), (b.st_ino, 2))
        self.assertEqual(self.read("g0_closed.json"), self.read("g0_closed.json.tmp"))

    def test_an_existing_final_marker_is_never_replaced(self):
        open(os.path.join(self.run_dir, "g0_closed.json"), "wb").write(b'{"foreign":true}')
        rc, err = self.fin()
        self.assertEqual(rc, 3)
        self.assertEqual(self.read("g0_closed.json"), b'{"foreign":true}')

    def test_no_fallback_creates_the_final_name_when_link_is_unsupported(self):
        rc, err = self.fin(patches={(os, "link"): mock.Mock(side_effect=OSError(errno.ENOTSUP, "no hard links"))})
        self.assertEqual(rc, 3)
        self.assertFalse(os.path.exists(os.path.join(self.run_dir, "g0_closed.json")))
        self.assertIn("G0-CLOSE-UNPUBLISHED", err)

    def test_evidence_and_summary_are_never_overwritten(self):
        open(os.path.join(self.run_dir, "g0_evidence.json"), "wb").write(b"older run")
        rc, err = self.fin()
        self.assertEqual((rc, self.read("g0_evidence.json")), (3, b"older run"))
        self.assertIn("G0-EVIDENCE-UNSAVED", err)
        self.assertNotIn("g0_summary.json", self.files())

    def test_the_order_of_the_stages_and_steps(self):
        order = []
        reals = {"write_exclusive": GR.write_exclusive, "read_back": GR.read_back, "fsync_dir": GR.fsync_dir}

        def spy(name):
            def f(*a, **k):
                order.append((name, os.path.basename(a[0]) if a and name != "fsync_dir" else "dir"))
                return reals[name](*a, **k)
            return f
        real_judge, real_link, real_build = GJ.judge, os.link, GJ.build_marker

        def judge(*a, **k):
            order.append(("judge", "-"))
            return real_judge(*a, **k)

        def link(*a, **k):
            order.append(("link", os.path.basename(a[1])))
            return real_link(*a, **k)

        def build(*a, **k):
            order.append(("build_marker", "-"))
            return real_build(*a, **k)
        self.fin(patches={(GR, "write_exclusive"): spy("write_exclusive"), (GR, "read_back"): spy("read_back"), (GR, "fsync_dir"): spy("fsync_dir"),
                    (GJ, "judge"): judge, (os, "link"): link, (GJ, "build_marker"): build})
        self.assertEqual(order, [("write_exclusive", "g0_evidence.json"), ("fsync_dir", "dir"), ("read_back", "g0_evidence.json"), ("judge", "-"),
                                 ("write_exclusive", "g0_summary.json"), ("fsync_dir", "dir"), ("read_back", "g0_summary.json"), ("build_marker", "-"),
                                 ("write_exclusive", "g0_closed.json.tmp"), ("read_back", "g0_closed.json.tmp"), ("link", "g0_closed.json"), ("fsync_dir", "dir"),
                                 ("read_back", "g0_closed.json")])

    def test_the_judge_receives_only_the_read_back_evidence(self):
        ev = self.evidence()
        ev["guard"]["fork_pids"] = (200,)                             # a tuple becomes a list only through the saved bytes
        seen = {}
        real = GJ.judge

        def judge(e2, *a, **k):
            seen["e2"] = e2
            return real(e2, *a, **k)
        rc, _ = self.fin(ev, patches={(GJ, "judge"): judge})
        self.assertIsNot(seen["e2"], ev)
        self.assertEqual(seen["e2"]["guard"]["fork_pids"], [200])
        self.assertEqual(seen["e2"], json.loads(self.read("g0_evidence.json").decode()))

    def test_the_summary_binds_the_evidence_bytes_that_were_read_back(self):
        self.fin()
        s = json.loads(self.read("g0_summary.json").decode())
        self.assertEqual(s["evidence_sha256"], GJ.sha256_hex(self.read("g0_evidence.json")))
        self.assertEqual(s["criteria_id"], TOOL_ID)
        self.assertEqual(s["criteria_sha256"], TOOL_SHA)
        for k in ("run_id", "verdict", "exit_code", "checks", "c03_fidelity_report", "pipeline"):
            self.assertIn(k, s)

    def test_a_blocked_note_is_written_exclusively_when_the_evidence_cannot_be_saved(self):
        rc, err = self.fin(patches={(GR, "write_exclusive"): write_fails("g0_evidence.json", half=False, partial=False)})
        self.assertEqual(rc, 3)
        self.assertIn("g0_blocked_%s.json" % self.RUN_ID, self.files())


class TestV4PipelineCases(Harness):
    """The 15 pipeline cases of g0_v4_cases.json (PIPE-1..15), with the V5 exit-code rule (0 / 1 only after the closure marker)."""

    def case(self, pid):
        return next(p for p in V4["pipeline"] if p["id"] == pid)

    def check(self, pid, rc, err):
        p = self.case(pid)
        self.assertEqual(rc, p["exit_code"], pid)
        if p["stderr_marker"]:
            self.assertIn(p["stderr_marker"], err, pid)
        elif p["verdict"] == "PASS" or p["verdict"] == "FAIL":
            self.assertEqual(err, "", pid)

    def test_pipe_1_everything_succeeds(self):
        rc, err = self.fin()
        self.check("PIPE-1", rc, err)
        self.assertEqual(self.files(), self.want_files(["REG", "EV", "SUM", "CL", "TMP"]))

    def test_pipe_2_a_non_json_value_is_never_converted(self):
        ev = self.evidence()
        ev["unexpected"] = {1, 2}
        rc, err = self.fin(ev)
        self.check("PIPE-2", rc, err)
        self.assertEqual(self.files(), self.want_files(["REG"]))

    def test_pipe_3_nan_is_refused(self):
        ev = self.evidence()
        ev["timing"]["duration"] = float("nan")
        rc, err = self.fin(ev)
        self.check("PIPE-3", rc, err)
        self.assertEqual(self.files(), self.want_files(["REG"]))

    def test_pipe_4_an_existing_evidence_file_is_not_overwritten(self):
        open(os.path.join(self.run_dir, "g0_evidence.json"), "wb").write(b"another run")
        rc, err = self.fin()
        self.check("PIPE-4", rc, err)
        self.assertEqual(self.read("g0_evidence.json"), b"another run")

    def test_pipe_5_a_write_error_keeps_the_partial_file(self):
        rc, err = self.fin(patches={(GR, "write_exclusive"): write_fails("g0_evidence.json", half=True)})
        self.check("PIPE-5", rc, err)
        self.assertIn("g0_evidence.json", self.files())

    def test_pipe_6_an_fsync_failure_of_the_file_or_the_directory(self):
        for n in (1, 2):
            with self.fresh():
                rc, err = self.fin(patches={(os, "fsync"): FsyncFault(n)})
                self.check("PIPE-6", rc, err)

    def test_pipe_7_bytes_read_back_differ(self):
        rc, err = self.fin(patches={(GR, "read_back"): read_differs("g0_evidence.json")})
        self.check("PIPE-7", rc, err)
        self.assertIn("g0_evidence.json", self.files())
        self.assertNotIn("g0_summary.json", self.files())

    def test_pipe_8_not_a_regular_file_or_not_parseable(self):
        rc, err = self.fin(patches={(GR, "read_back"): read_raises("g0_evidence.json")})
        self.check("PIPE-8", rc, err)
        with self.fresh():
            rc, err = self.fin(patches={(GJ, "parse_strict"): mock.Mock(side_effect=ValueError("not JSON"))})
            self.check("PIPE-8", rc, err)

    def test_pipe_9_a_type_error_in_the_read_back_evidence_is_a_finding_not_a_pipeline_failure(self):
        ev = self.evidence()
        ev["reg_writer_seq"] = "7"
        rc, err = self.fin(ev)
        self.check("PIPE-9", rc, err)
        s = json.loads(self.read("g0_summary.json").decode())
        self.assertEqual(s["verdict"], "BLOCKED")
        self.assertEqual(s["checks"]["G0-C16"]["status"], "FAIL_EVIDENCED")
        self.assertEqual(s["checks"]["G0-C03"]["rule"], "C03-U0")
        self.assertIn("g0_closed.json", self.files())

    def test_pipe_10_the_judge_raises(self):
        rc, err = self.fin(patches={(GJ, "judge"): mock.Mock(side_effect=RuntimeError("boom"))})
        self.check("PIPE-10", rc, err)
        self.assertNotIn("g0_summary.json", self.files())
        self.assertNotIn("g0_closed.json", self.files())

    def test_pipe_11_a_fail_that_cannot_be_recorded_is_not_exit_code_1(self):
        rc, err = self.fin(self.evidence("FAIL"), patches={(GR, "write_exclusive"): write_fails("g0_summary.json", half=True)})
        self.check("PIPE-11", rc, err)
        self.assertIn("verdict=FAIL", err)
        self.assertNotEqual(rc, 1)

    def test_pipe_12_a_pass_that_cannot_be_recorded_is_not_exit_code_0(self):
        rc, err = self.fin(patches={(GR, "write_exclusive"): write_fails("g0_summary.json")})
        self.check("PIPE-12", rc, err)
        self.assertNotEqual(rc, 0)

    def test_pipe_13_the_summary_reads_back_differently(self):
        rc, err = self.fin(patches={(GR, "read_back"): read_differs("g0_summary.json")})
        self.check("PIPE-13", rc, err)
        self.assertIn("g0_summary.json", self.files())
        self.assertNotIn("g0_closed.json", self.files())

    def test_pipe_14_a_fail_saved_and_closed_exits_1(self):
        rc, err = self.fin(self.evidence("FAIL"))
        self.check("PIPE-14", rc, err)
        self.assertIn("g0_closed.json", self.files())

    def test_pipe_15_an_uncaught_exception_is_mapped_to_3_never_to_1(self):
        err, out = io.StringIO(), io.StringIO()
        auth = ({"authorization_id": "OWNER-G0-0001", "bindings": F.bindings()}, b"{}")
        with contextlib.ExitStack() as st:
            st.enter_context(mock.patch.object(GA, "frozen_problems", return_value=[]))
            st.enter_context(mock.patch.object(GA, "load", return_value=auth))
            st.enter_context(mock.patch.object(GR, "current", return_value=F.bindings()))
            st.enter_context(mock.patch.object(GR, "safe_preflight", return_value={"ok": True}))
            st.enter_context(mock.patch.object(GR, "prepare_dirs", return_value=({}, {}, {})))
            st.enter_context(mock.patch.object(GR, "run", return_value=self.evidence()))
            st.enter_context(mock.patch.object(GR, "finalize", side_effect=RuntimeError("escaped")))
            st.enter_context(contextlib.redirect_stderr(err))
            st.enter_context(contextlib.redirect_stdout(out))
            rc = GR.main(["--execute", "--auth", os.path.join(self.root, "auth.json"), "--run-id", "g0_pipe_main"])
        self.assertEqual(rc, 3)
        self.assertIn("G0-PIPELINE-ERROR", err.getvalue())

    def test_the_15_cases_are_present(self):
        self.assertEqual([p["id"] for p in V4["pipeline"]], ["PIPE-%d" % i for i in range(1, 16)])


if __name__ == "__main__":
    unittest.main(verbosity=2)
