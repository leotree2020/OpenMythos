"""G1 runner parts (CPU; WRITTEN, NOT RUN -- NOT TESTED): the guard logic with fake 'real' functions (the guard is never installed and no process is started),
the in-run safety rule, the preflight composition (with /proc, the residue scans and the G0 history mocked), directory preparation, the evidence pipeline
P0..P7 and the atomic closure publication K0..K7 in temporary directories, including write / read-back / link / fsync faults and the never-overwrite rule."""
import contextlib
import errno
import hashlib
import io
import json
import os
import sys
import tempfile
import types
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import g1_fixtures as F  # noqa: E402
import g1_auth as G1A  # noqa: E402
import g1_judge as GJ  # noqa: E402
import g1_run as R  # noqa: E402

CRIT = F.criteria()
SHA = G1A.FROZEN_G1_CRITERIA_SHA256


def guard_with(fork_result=None, write_exc=None, short=False):
    g = R.G1Guard()
    calls = {"fork": 0, "write": [], "close": [], "wait": []}

    def fork():
        calls["fork"] += 1
        return 7000 + calls["fork"] if fork_result is None else fork_result

    def waitpid(pid, opts=0):
        calls["wait"].append((pid, opts))
        return (pid, 111 * 256)

    def write(fd, data):
        calls["write"].append((fd, bytes(data)))
        if write_exc is not None:
            raise write_exc
        return 0 if short else len(data)

    def close(fd):
        calls["close"].append(fd)
    g.real = {"os.fork": fork, "os.waitpid": waitpid, "os.write": write, "os.close": close}
    return g, calls


class TestGuardLogic(unittest.TestCase):
    def test_one_fork_per_test_with_a_recorded_event(self):
        g, calls = guard_with()
        g.begin_test("T1_ABORT")
        self.assertEqual(g.fork(), 7001)
        self.assertEqual(g.fork_pids, [7001])
        self.assertEqual(len(g.fork_events), 1)
        e = g.fork_events[0]
        self.assertEqual((e["test"], e["pid"]), ("T1_ABORT", 7001))
        self.assertLessEqual(e["mono_before"], e["mono_after"])
        with self.assertRaises(R.GuardViolation):
            g.fork()
        self.assertEqual(calls["fork"], 1)
        self.assertEqual(len(g.violations), 1)
        self.assertEqual(g.fork_calls, 1)

    def test_no_new_fork_while_the_previous_child_is_unreaped(self):
        g, calls = guard_with()
        g.begin_test("T1_ABORT")
        g.fork()
        g.begin_test("T2_EOF")
        with self.assertRaises(R.GuardViolation):
            g.fork()
        self.assertEqual(calls["fork"], 1)
        g.waitpid(7001, 1)
        self.assertEqual(g.fork(), 7002)                           # allowed once the previous child was reaped
        self.assertEqual(g.allowed_pid, 7002)

    def test_at_most_four_forks_in_total(self):
        g, calls = guard_with()
        for i, tid in enumerate(F.TESTS):
            g.begin_test(tid)
            pid = g.fork()
            g.waitpid(pid, 1)
        g.begin_test("T5_EXTRA")
        with self.assertRaises(R.GuardViolation):
            g.fork()
        self.assertEqual((g.fork_calls, calls["fork"], len(g.fork_events)), (4, 4, 4))

    def test_fork_outside_a_test_is_a_violation(self):
        g, calls = guard_with()
        with self.assertRaises(R.GuardViolation):
            g.fork()
        self.assertEqual(calls["fork"], 0)

    def test_the_child_side_of_a_fork_records_no_pid(self):
        g, _ = guard_with(fork_result=0)
        g.begin_test("T1_ABORT")
        self.assertEqual(g.fork(), 0)
        self.assertEqual((g.fork_pids, g.live_pid, g.allowed_pid), ([], None, None))

    def test_waitpid_only_on_the_current_child(self):
        g, calls = guard_with()
        g.begin_test("T1_ABORT")
        g.fork()
        for bad in (7002, 0, -1, "7001", None, 1):
            with self.assertRaises(R.GuardViolation):
                g.waitpid(bad, 1)
        self.assertEqual(calls["wait"], [])
        self.assertEqual(len(g.violations), 6)
        self.assertEqual(g.waitpid(7001, 1), (7001, 111 * 256))
        c = g.waitpid_calls[0]
        self.assertEqual((c["test"], c["pid"], c["returned"], c["options"]), ("T1_ABORT", 7001, 7001, 1))
        self.assertIsNone(g.live_pid)

    def test_a_poll_that_returned_zero_does_not_free_the_child(self):
        g, calls = guard_with()
        g.begin_test("T1_ABORT")
        g.fork()
        g.real["os.waitpid"] = lambda pid, opts=0: (0, 0)
        g.waitpid(7001, 1)
        self.assertEqual(g.live_pid, 7001)

    def test_gate_writes_are_recorded_only_on_the_watched_descriptor(self):
        g, calls = guard_with()
        g.begin_test("T3_INVALID_BYTE")
        g.write(5, b"x")
        self.assertEqual(g.gate_writes, [])
        g.watch_fd = 7
        self.assertEqual(g.write(7, b"r"), 1)
        w = g.gate_writes[0]
        self.assertEqual((w["test"], w["byte"], w["result"], w["returned"], w["errno"], w["error"]), ("T3_INVALID_BYTE", 114, "ok", 1, None, None))
        self.assertLessEqual(w["mono_before"], w["mono_after"])
        self.assertEqual(calls["write"], [(5, b"x"), (7, b"r")])

    def test_abort_byte_is_recorded_as_65(self):
        g, _ = guard_with()
        g.begin_test("T1_ABORT")
        g.watch_fd = 7
        g.write(7, b"A")
        self.assertEqual(g.gate_writes[0]["byte"], 65)

    def test_an_r_write_is_trapped_and_never_reaches_the_pipe(self):
        g, calls = guard_with()
        g.begin_test("T2_EOF")
        g.watch_fd = 7
        with self.assertRaises(R.GuardViolation):
            g.write(7, b"R")
        self.assertEqual((calls["write"], g.gate_writes), ([], []))
        self.assertEqual(g.violations[0]["call"], GJ.R_WRITE_CALL)
        r, w = os.pipe()
        try:
            g.watch_fd = None
            with self.assertRaises(R.GuardViolation):                # any pipe, watched or not
                g.write(w, b"R")
            self.assertEqual(calls["write"], [])
        finally:
            os.close(r)
            os.close(w)
        self.assertEqual(len(g.violations), 2)

    def test_r_to_a_non_pipe_descriptor_is_not_a_gate_write(self):
        g, calls = guard_with()
        g.begin_test("T2_EOF")
        g.write(987654, b"R")                                         # not a pipe (fstat fails), not watched
        self.assertEqual(calls["write"], [(987654, b"R")])
        self.assertEqual(g.violations, [])

    def test_a_failed_gate_write_is_recorded_not_dropped(self):
        g, _ = guard_with(write_exc=BrokenPipeError(errno.EPIPE, "broken pipe"))
        g.begin_test("T1_ABORT")
        g.watch_fd = 7
        with self.assertRaises(BrokenPipeError):
            g.write(7, b"A")
        w = g.gate_writes[0]
        self.assertEqual((w["result"], w["errno"], w["returned"]), ("error", errno.EPIPE, None))
        self.assertIsNotNone(w["mono_after"])
        self.assertIn("BrokenPipeError", w["error"])

    def test_a_short_or_multi_byte_gate_write_is_an_error_or_has_no_byte(self):
        g, _ = guard_with(short=True)
        g.begin_test("T1_ABORT")
        g.watch_fd = 7
        g.write(7, b"A")
        self.assertEqual(g.gate_writes[0]["result"], "error")
        g2, _ = guard_with()
        g2.begin_test("T1_ABORT")
        g2.watch_fd = 7
        g2.write(7, b"AB")
        self.assertIsNone(g2.gate_writes[0]["byte"])

    def test_closing_the_watched_descriptor_is_recorded_once_and_clears_the_watch(self):
        g, calls = guard_with()
        g.begin_test("T2_EOF")
        g.watch_fd = 7
        g.close(5)
        self.assertEqual(g.gate_closes, [])
        g.close(7)
        g.close(7)
        self.assertEqual(len(g.gate_closes), 1)
        self.assertEqual((g.gate_closes[0]["test"], g.gate_closes[0]["fd"]), ("T2_EOF", 7))
        self.assertIsNone(g.watch_fd)
        self.assertEqual(calls["close"], [5, 7, 7])

    def test_begin_test_resets_the_per_test_state(self):
        g, _ = guard_with()
        g.begin_test("T1_ABORT")
        g.watch_fd = 7
        g.fork()
        g.begin_test("T2_EOF")
        self.assertEqual((g.test, g.forks_this_test, g.watch_fd), ("T2_EOF", 0, None))

    def test_traps_record_and_raise(self):
        g, _ = guard_with()
        g.begin_test("T1_ABORT")
        for name in ("os.kill", "os.killpg", "signal.pidfd_send_signal", "subprocess.run", "Observer.release"):
            with self.assertRaises(R.GuardViolation):
                g._trap(name)(1, 9)
        self.assertEqual([v["call"] for v in g.violations], ["os.kill", "os.killpg", "signal.pidfd_send_signal", "subprocess.run", "Observer.release"])
        self.assertTrue(all(v["test"] == "T1_ABORT" for v in g.violations))

    def test_summary_has_exactly_the_evidence_keys_and_is_json(self):
        g, _ = guard_with()
        g.begin_test("T1_ABORT")
        g.fork()
        s = g.summary()
        self.assertEqual(set(s), {"violations", "fork_calls", "fork_pids", "fork_events", "waitpid_calls", "gate_writes", "gate_closes"})
        json.dumps(s)
        self.assertEqual(GJ.TYPE_VALIDATORS[GJ.T_FORKS](s["fork_events"]), None)

    def test_the_install_list_traps_every_signal_exec_spawn_and_wait_function(self):
        src = open(os.path.join(G1A.HERE, "g1_run.py"), encoding="utf-8").read()
        for name in ("kill", "killpg", "system", "popen", "execv", "execve", "execvp", "execl", "spawnl", "spawnv", "posix_spawn", "forkpty", "wait", "wait3",
                     "wait4", "waitid", "pidfd_send_signal", "raise_signal", "pthread_kill", "Popen", "check_output"):
            self.assertIn('"%s"' % name, src, name)
        self.assertIn("O.Observer.release = self._trap(GJ.RELEASE_CALL)", src)


class TestInRunAssessment(unittest.TestCase):
    SCN = {"expected_exit": 111}

    def good(self):
        return {"messages_received": 0, "first_action_mono": None, "ready_received": False, "cleanup": {"cleanup_ok": True}}

    def test_a_clearly_expected_test_continues(self):
        self.assertEqual(R.in_run_assessment(self.good(), self.SCN, 111, [], []), (True, []))

    def test_anything_else_stops_the_run(self):
        cases = [(self.good(), 112, [], []), (self.good(), 0, [], []), (self.good(), None, [], []),
                 (dict(self.good(), messages_received=1), 111, [], []), (dict(self.good(), first_action_mono=1.0), 111, [], []),
                 (dict(self.good(), ready_received=True), 111, [], []), (dict(self.good(), ready_received=None), 111, [], []),
                 (dict(self.good(), cleanup={"cleanup_ok": False}), 111, [], []), (dict(self.good(), cleanup=None), 111, [], []),
                 (self.good(), 111, [{"call": "os.kill"}], []), (self.good(), 111, [], ["exit:T1_ABORT"])]
        for t, code, viol, hits in cases:
            ok, reasons = R.in_run_assessment(t, self.SCN, code, viol, hits)
            self.assertFalse(ok, (t, code, viol, hits))
            self.assertTrue(reasons)

    def test_it_is_not_the_verdict(self):
        src = open(os.path.join(G1A.HERE, "g1_run.py"), encoding="utf-8").read()
        self.assertIn("This is NOT the verdict", src)


class TestSmallHelpers(unittest.TestCase):
    def test_blank_test_has_exactly_the_per_test_schema_fields(self):
        names = {f["path"].split(".")[-1] for f in CRIT["evidence_schema"]["fields"] if f["path"].startswith("tests.T1_ABORT.")}
        b = R.blank_test("T1_ABORT")
        self.assertEqual(set(b), names)
        self.assertEqual({k: v for k, v in b.items() if v is not None}, {"ran": False, "scenario": "T1_ABORT"})

    def test_msgs_counts_every_kind_of_message(self):
        rec = types.SimpleNamespace(ready=None, first_action_mono=None, messages=[])
        self.assertEqual(R.msgs(rec), 0)
        rec = types.SimpleNamespace(ready={"t": "READY"}, first_action_mono=1.0, messages=[{}, {}])
        self.assertEqual(R.msgs(rec), 4)

    def test_token_scan_finds_live_marker_processes_only(self):
        table = {10: {"state": "S", "starttime": 1, "ppid": 1}, 11: {"state": "Z", "starttime": 2, "ppid": 1}, 12: {"state": "S", "starttime": 3, "ppid": 1},
                 13: {"state": "S", "starttime": 4, "ppid": 1}}
        cmds = {10: ["python3", "g1_run.py", "--execute"], 11: ["python3", "g1_run.py"], 12: ["python3", "g1_run.py"], 13: ["python3", "other.py"]}
        with mock.patch.object(R.C, "scan_proc", return_value=(table, {})), mock.patch.object(R.C, "read_cmdline", side_effect=lambda p: cmds[p]):
            found, problems = R.token_scan({12})
        self.assertEqual([x["pid"] for x in found], [10])
        self.assertEqual(problems, {})

    def test_manual_disposition_is_written_exclusively_and_recorded_in_the_evidence(self):
        ev = {"exception": None, "manual_disposition": None}
        ident = {"pid": 5001, "starttime": 700001, "node_id": "n00002", "verified_by": "REGISTERED record + pidfd", "ends_by": "gate timer; NO signal"}
        with tempfile.TemporaryDirectory() as d:
            R._manual(d, F.RUN_ID, ident, ev)
            body = json.load(open(os.path.join(d, "MANUAL_DISPOSITION_REQUIRED.json")))
            self.assertEqual((body["run_id"], body["alive"], body["decision"]), (F.RUN_ID, ident, "a person decides"))
            self.assertEqual((ev["manual_disposition"], ev["exception"]), (ident, None))
            ev2 = {"exception": None, "manual_disposition": None}
            R._manual(d, F.RUN_ID, dict(ident, pid=1), ev2)                  # exists: never overwritten, the failure is recorded, nothing raised
            self.assertEqual(json.load(open(os.path.join(d, "MANUAL_DISPOSITION_REQUIRED.json")))["alive"]["pid"], 5001)
            self.assertIn("MANUAL_DISPOSITION_REQUIRED.json not written", ev2["exception"])
            self.assertEqual(ev2["manual_disposition"]["pid"], 1)

    def test_current_has_the_ten_bindings(self):
        with mock.patch.object(R.GR, "git_head", return_value="a" * 40), mock.patch.object(R.GR, "prereg_sha", return_value="b" * 64), \
                mock.patch.object(R.GR, "bench_code_hash", return_value="c" * 64):
            b = R.current()
        self.assertEqual(set(b), set(G1A.BINDING_KEYS))
        self.assertEqual((b["git_head"], b["prereg_sha256"], b["bench_code_sha256"]), ("a" * 40, "b" * 64, "c" * 64))


class TestPreflightComposition(unittest.TestCase):
    def run_pf(self, run_dir, kids=(), residue=(), g0_residue=(), unres_g0=(), unres_g1=(), g0ref=None, enum=None, flag=True, version=(3, 13, 16, "final", 0), sig=0):
        fake_sys = types.SimpleNamespace(version_info=version, version="%d.%d.%d" % version[:3], flags=types.SimpleNamespace(dont_write_bytecode=flag))
        g0ref = g0ref if g0ref is not None else {"ok": True, "problems": [], "run_id": "g0_x", "closed_sha256": "a" * 64}
        with contextlib.ExitStack() as st:
            st.enter_context(mock.patch.object(R, "sys", fake_sys))
            st.enter_context(mock.patch.object(R.C, "scan_proc", return_value=({1: {}}, dict(enum or {}))))
            st.enter_context(mock.patch.object(R.C, "children_of", return_value=list(kids)))
            st.enter_context(mock.patch.object(R.C, "read_sigign", return_value=sig))
            st.enter_context(mock.patch.object(R, "token_scan", return_value=(list(residue), {})))
            st.enter_context(mock.patch.object(R.GR, "token_scan", return_value=(list(g0_residue), {})))
            st.enter_context(mock.patch.object(R.GR, "closure_preflight", return_value=(list(unres_g0), {})))
            st.enter_context(mock.patch.object(R, "closure_preflight", return_value=(list(unres_g1), {})))
            st.enter_context(mock.patch.object(R.GJ0, "load_criteria", return_value={}))
            st.enter_context(mock.patch.object(R.G1A, "g0_reference_status", return_value=g0ref))
            return R.preflight(run_dir, {1}, CRIT)

    def test_a_clean_environment_is_ok(self):
        with tempfile.TemporaryDirectory() as d:
            pf = self.run_pf(os.path.join(d, "g1_new"))
        self.assertTrue(pf["ok"], pf)
        self.assertEqual((pf["problems"], pf["children"], pf["unresolved_prior"], pf["token_residue"], pf["run_id_unique"]), ([], 0, [], [], True))
        self.assertTrue(pf["g0_reference"]["ok"])
        self.assertEqual(GJ.TYPE_VALIDATORS[GJ.T_PREFLIGHT](pf), None)

    def test_every_blocking_condition_makes_the_preflight_not_ok(self):
        with tempfile.TemporaryDirectory() as d:
            new = os.path.join(d, "g1_new")
            cases = {"child": dict(kids=[99]), "g1 residue": dict(residue=[{"pid": 5}]), "g0 residue": dict(g0_residue=[{"pid": 6}]),
                     "unresolved g0 run": dict(unres_g0=["g0_x:NO_CLOSED"]), "unresolved g1 run": dict(unres_g1=["g1_x:NO_CLOSED"]),
                     "g0 reference": dict(g0ref={"ok": False, "problems": ["missing"], "run_id": "g0_x", "closed_sha256": None}),
                     "enumeration": dict(enum={"123": "unreadable"}), "no -B": dict(flag=False), "python": dict(version=(3, 12, 1, "final", 0)),
                     "sigchld ignored": dict(sig=1 << 16), "sigign unreadable": dict(sig=None)}
            for name, kw in cases.items():
                pf = self.run_pf(new, **kw)
                self.assertFalse(pf["ok"], name)
            os.makedirs(new)
            self.assertFalse(self.run_pf(new)["ok"])                      # the run id already exists
            self.assertFalse(self.run_pf(new)["run_id_unique"])

    def test_the_g0_reference_failure_is_reported_in_problems(self):
        with tempfile.TemporaryDirectory() as d:
            pf = self.run_pf(os.path.join(d, "g1_new"), g0ref={"ok": False, "problems": ["g0_closed.json is not a regular file"], "run_id": "g0_x", "closed_sha256": None})
        self.assertTrue(any("G0 REAL-001 reference not verified" in p for p in pf["problems"]))

    def test_the_preflight_never_raises(self):
        for exc in (RuntimeError("proc unreadable"), OSError(5, "io"), SystemExit(1), KeyboardInterrupt()):
            with mock.patch.object(R, "preflight", side_effect=exc):
                pf = R.safe_preflight("/nonexistent/g1_x", set(), CRIT)
            self.assertFalse(pf["ok"])
            self.assertEqual(pf["g0_reference"], {"ok": False})
            self.assertTrue(pf["problems"][0].startswith("preflight raised"))
            self.assertEqual(GJ.TYPE_VALIDATORS[GJ.T_PREFLIGHT](pf), None)


class TestDirectories(unittest.TestCase):
    def test_directories_are_created_validated_and_never_reused(self):
        with tempfile.TemporaryDirectory() as d:
            root = os.path.join(d, "evidence")
            consumed = os.path.join(root, "_g1_consumed")
            run_dir = os.path.join(root, "g1_20261101_000000_aaaaaa")
            with mock.patch.object(G1A, "EVIDENCE_ROOT", root), mock.patch.object(G1A, "CONSUMED_DIR", consumed):
                r, c, rd = R.prepare_dirs(run_dir)
                self.assertEqual((r["created_by_this_run"], c["created_by_this_run"], rd["created_by_this_process"]), (True, True, True))
                self.assertTrue(os.path.isdir(run_dir))
                with self.assertRaises(R.DirError):
                    R.prepare_dirs(run_dir)                              # the run directory is created exclusively
                r2, c2, rd2 = R.prepare_dirs(os.path.join(root, "g1_20261101_000001_bbbbbb"))
                self.assertEqual((r2["created_by_this_run"], c2["created_by_this_run"]), (False, False))

    def test_a_symlinked_or_group_writable_root_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            real = os.path.join(d, "real")
            os.mkdir(real)
            link = os.path.join(d, "link")
            os.symlink(real, link)
            with mock.patch.object(G1A, "EVIDENCE_ROOT", link), mock.patch.object(G1A, "CONSUMED_DIR", os.path.join(link, "_g1_consumed")):
                with self.assertRaises(R.DirError):
                    R.prepare_dirs(os.path.join(link, "g1_x"))
            wide = os.path.join(d, "wide")
            os.mkdir(wide)
            os.chmod(wide, 0o777)
            with mock.patch.object(G1A, "EVIDENCE_ROOT", wide), mock.patch.object(G1A, "CONSUMED_DIR", os.path.join(wide, "_g1_consumed")):
                with self.assertRaises(R.DirError):
                    R.prepare_dirs(os.path.join(wide, "g1_x"))


def run_fin(ev, setup=None, patches=()):
    """finalize() in a fresh temporary run directory.  -> (exit code, stderr text, {file: bytes}, inode pairs)."""
    err = io.StringIO()
    with tempfile.TemporaryDirectory() as d, contextlib.ExitStack() as st:
        run_dir = os.path.join(d, F.RUN_ID)
        os.mkdir(run_dir)
        if setup:
            setup(run_dir)
        for obj, name, val in patches:
            st.enter_context(mock.patch.object(obj, name, val))
        st.enter_context(mock.patch.object(G1A, "EVIDENCE_ROOT", d))
        st.enter_context(contextlib.redirect_stderr(err))
        rc = R.finalize(ev, F.RUN_ID, run_dir, CRIT, SHA)
        files = {n: open(os.path.join(run_dir, n), "rb").read() for n in os.listdir(run_dir)}
        same = None
        if "g1_closed.json" in files and "g1_closed.json.tmp" in files:
            same = os.stat(os.path.join(run_dir, "g1_closed.json")).st_ino == os.stat(os.path.join(run_dir, "g1_closed.json.tmp")).st_ino
    return rc, err.getvalue(), files, same


class TestPipelineAndClosure(unittest.TestCase):
    def test_a_passing_run_is_saved_judged_and_closed(self):
        rc, err, files, same = run_fin(F.good_evidence())
        self.assertEqual((rc, err), (0, ""))
        self.assertEqual(sorted(files), ["g1_closed.json", "g1_closed.json.tmp", "g1_evidence.json", "g1_summary.json"])
        self.assertEqual(files["g1_closed.json"], files["g1_closed.json.tmp"])
        self.assertTrue(same)                                                       # the temporary name is a second name of the same inode
        state, marker = GJ.classify_marker(files["g1_closed.json"])
        self.assertEqual(state, "ok")
        self.assertEqual((marker["recorded_verdict"], marker["recorded_exit_code"], marker["run_id"], marker["process_exit_proof"]), ("PASS", 0, F.RUN_ID, False))
        self.assertEqual(marker["evidence_sha256"], hashlib.sha256(files["g1_evidence.json"]).hexdigest())
        self.assertEqual(marker["summary_sha256"], hashlib.sha256(files["g1_summary.json"]).hexdigest())
        self.assertEqual((marker["evidence_bytes"], marker["summary_bytes"]), (len(files["g1_evidence.json"]), len(files["g1_summary.json"])))
        summary = json.loads(files["g1_summary.json"])
        self.assertEqual((summary["verdict"], summary["exit_code"], summary["criteria_id"], summary["criteria_sha256"]), ("PASS", 0, CRIT["criteria_id"], SHA))
        self.assertEqual({t: summary["tests"][t]["verdict"] for t in F.TESTS}, {t: "PASS" for t in F.TESTS})
        self.assertEqual(sorted(summary["pipeline"]), ["P0", "P1", "P2", "P3", "P4", "P5"])
        self.assertTrue(summary["scope"].startswith("G1 only"))
        self.assertNotIn("fail_scope", summary)

    def test_the_exit_code_is_the_recorded_verdict_for_fail_and_blocked(self):
        rc, err, files, _ = run_fin(F.mutate(F.good_evidence(), **{"tests.T1_ABORT.reap.exit_status": 0}))
        self.assertEqual(rc, 1)
        marker = GJ.classify_marker(files["g1_closed.json"])[1]
        self.assertEqual((marker["recorded_verdict"], marker["recorded_exit_code"]), ("FAIL", 1))
        self.assertIn("fail_scope", json.loads(files["g1_summary.json"]))
        rc, err, files, _ = run_fin(F.good_evidence(ran=2))
        self.assertEqual(rc, 3)
        marker = GJ.classify_marker(files["g1_closed.json"])[1]
        self.assertEqual((marker["recorded_verdict"], marker["recorded_exit_code"]), ("BLOCKED", 3))
        self.assertEqual(json.loads(files["g1_summary.json"])["tests"]["T4_TIMEOUT"]["verdict"], "NOT_RUN")

    def test_the_verdict_is_computed_from_the_read_back_evidence(self):
        seen = []
        real = R.GJ.judge

        def spy(e2, crit, sha, validation=None):
            seen.append(e2)
            return real(e2, crit, sha, validation=validation)
        ev = F.good_evidence()
        ev["observer"] = {"pid": 4000, "sid": 3900, "pgrp": 3950}
        rc, err, files, _ = run_fin(ev, patches=[(R.GJ, "judge", spy)])
        self.assertEqual(rc, 0)
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0], json.loads(files["g1_evidence.json"]))
        self.assertIsNot(seen[0], ev)

    def test_unserialisable_evidence_is_blocked_before_anything_is_written(self):
        for bad in (float("nan"), {1, 2}, float("inf")):
            rc, err, files, _ = run_fin(F.mutate(F.good_evidence(), **{"timing.duration": bad}))
            self.assertEqual(rc, 3)
            self.assertIn("G1-EVIDENCE-UNSAVED", err)
            self.assertIn("stage=P1", err)
            self.assertEqual(files, {})

    def test_an_existing_evidence_file_is_never_overwritten(self):
        def setup(d):
            open(os.path.join(d, "g1_evidence.json"), "wb").write(b"old")
        rc, err, files, _ = run_fin(F.good_evidence(), setup=setup)
        self.assertEqual(rc, 3)
        self.assertIn("G1-EVIDENCE-UNSAVED", err)
        self.assertEqual(files["g1_evidence.json"], b"old")
        self.assertIn("g1_blocked_%s.json" % F.RUN_ID, files)
        self.assertNotIn("g1_summary.json", files)
        self.assertNotIn("g1_closed.json", files)

    def test_an_unverified_read_back_is_blocked(self):
        rc, err, files, _ = run_fin(F.good_evidence(), patches=[(R, "save_and_verify", mock.Mock(side_effect=R.Unverified("differs", "a", "b")))])
        self.assertEqual(rc, 3)
        self.assertIn("G1-EVIDENCE-UNVERIFIED", err)
        self.assertNotIn("g1_closed.json", files)

    def test_a_judge_error_is_blocked_with_the_evidence_kept(self):
        rc, err, files, _ = run_fin(F.good_evidence(), patches=[(R.GJ, "judge", mock.Mock(side_effect=RuntimeError("boom")))])
        self.assertEqual(rc, 3)
        self.assertIn("G1-JUDGE-ERROR", err)
        self.assertIn("g1_evidence.json", files)
        self.assertNotIn("g1_summary.json", files)
        self.assertNotIn("g1_closed.json", files)

    def test_an_unsaved_summary_is_blocked_and_closes_nothing(self):
        def setup(d):
            open(os.path.join(d, "g1_summary.json"), "wb").write(b"old")
        rc, err, files, _ = run_fin(F.good_evidence(), setup=setup)
        self.assertEqual(rc, 3)
        self.assertIn("G1-SUMMARY-UNSAVED", err)
        self.assertEqual(files["g1_summary.json"], b"old")
        self.assertNotIn("g1_closed.json", files)

    def test_a_failed_link_publishes_nothing(self):
        rc, err, files, _ = run_fin(F.good_evidence(), patches=[(R.os, "link", mock.Mock(side_effect=OSError(errno.EIO, "io error")))])
        self.assertEqual(rc, 3)
        self.assertIn("G1-CLOSE-UNPUBLISHED", err)
        self.assertIn("step=K4", err)
        self.assertIn("g1_closed.json.tmp", files)
        self.assertNotIn("g1_closed.json", files)
        self.assertIn(hashlib.sha256(files["g1_evidence.json"]).hexdigest(), err)

    def test_an_existing_marker_is_never_replaced(self):
        def setup(d):
            open(os.path.join(d, "g1_closed.json"), "wb").write(b"keep")
        rc, err, files, _ = run_fin(F.good_evidence(), setup=setup)
        self.assertEqual(rc, 3)
        self.assertIn("G1-CLOSE-UNPUBLISHED", err)
        self.assertEqual(files["g1_closed.json"], b"keep")
        self.assertEqual(GJ.classify_marker(files["g1_closed.json.tmp"])[0], "ok")

    def test_an_existing_temporary_name_is_never_reused(self):
        def setup(d):
            open(os.path.join(d, "g1_closed.json.tmp"), "wb").write(b"x")
        rc, err, files, _ = run_fin(F.good_evidence(), setup=setup)
        self.assertEqual(rc, 3)
        self.assertIn("G1-CLOSE-UNPUBLISHED", err)
        self.assertIn("step=K2", err)
        self.assertEqual(files["g1_closed.json.tmp"], b"x")
        self.assertNotIn("g1_closed.json", files)

    def test_a_temporary_file_that_does_not_read_back_is_not_published(self):
        rc, err, files, _ = run_fin(F.good_evidence(), patches=[(R, "read_back", lambda p: b"bad")])
        self.assertEqual(rc, 3)
        self.assertIn("G1-CLOSE-UNPUBLISHED", err)
        self.assertIn("step=K3", err)
        self.assertNotIn("g1_closed.json", files)

    def test_a_published_marker_that_does_not_read_back_is_unconfirmed(self):
        real, calls = R.read_back, [0]

        def rb(path):
            calls[0] += 1
            return real(path) if calls[0] == 1 else b"bad"
        rc, err, files, _ = run_fin(F.good_evidence(), patches=[(R, "read_back", rb)])
        self.assertEqual(rc, 3)
        self.assertIn("G1-CLOSE-UNCONFIRMED", err)
        self.assertIn("step=K6", err)
        self.assertEqual(GJ.classify_marker(files["g1_closed.json"])[0], "ok")        # published, but not confirmed: exit 3, never 0

    def test_a_failed_directory_fsync_after_the_link_is_unconfirmed(self):
        rc, err, files, _ = run_fin(F.good_evidence(), patches=[(R, "fsync_dir", mock.Mock(side_effect=OSError(errno.EIO, "io error")))])
        self.assertEqual(rc, 3)
        self.assertIn("G1-CLOSE-UNCONFIRMED", err)
        self.assertIn("step=K5", err)

    def test_a_second_finalize_in_the_same_directory_changes_nothing(self):
        err = io.StringIO()
        with tempfile.TemporaryDirectory() as d, mock.patch.object(G1A, "EVIDENCE_ROOT", d), contextlib.redirect_stderr(err):
            run_dir = os.path.join(d, F.RUN_ID)
            os.mkdir(run_dir)
            self.assertEqual(R.finalize(F.good_evidence(), F.RUN_ID, run_dir, CRIT, SHA), 0)
            before = {n: open(os.path.join(run_dir, n), "rb").read() for n in os.listdir(run_dir) if n.startswith("g1_")}
            self.assertEqual(R.finalize(F.good_evidence(), F.RUN_ID, run_dir, CRIT, SHA), 3)
            after = {n: open(os.path.join(run_dir, n), "rb").read() for n in os.listdir(run_dir) if n.startswith("g1_") and not n.startswith("g1_blocked")}
            self.assertEqual(before, after)

    def test_the_closure_publication_never_deletes_or_renames(self):
        import ast
        tree = ast.parse(open(os.path.join(G1A.HERE, "g1_run.py"), encoding="utf-8").read())
        for n in ast.walk(tree):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name) and n.func.value.id == "os":
                self.assertNotIn(n.func.attr, ("rename", "replace", "unlink", "remove", "renames", "truncate", "ftruncate"), "line %d" % n.lineno)
        self.assertIn("follow_symlinks=False", open(os.path.join(G1A.HERE, "g1_run.py"), encoding="utf-8").read())


if __name__ == "__main__":
    unittest.main(verbosity=2)
