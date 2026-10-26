"""Code self-tests for the D1 reader / verifier / driver (research/mini_mythos/gate3_d1).

SYNTHETIC DATA ONLY. No Parquet is downloaded, no tokenizer is fitted, no model is
built, no GPU is used. A pass here says the code behaves as designed on toy input;
it is NOT a D1 result. Real-mode tests run only when pyarrow and tokenizers are
installed (they are not needed for the stdlib self-test path).
"""
import argparse
import ast
import hashlib
import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

D1 = Path(__file__).resolve().parents[1] / "gate3_d1"
sys.path.insert(0, str(D1))
import d1_driver  # noqa: E402
import d1_reader  # noqa: E402
import d1_selftest_data  # noqa: E402
import d1_verifier  # noqa: E402

CFG = str(D1 / "D1_FROZEN_CONFIG.json")


def run_py(*args, check=None):
    r = subprocess.run([sys.executable, "-I"] + [str(a) for a in args], capture_output=True, text=True)
    if check is not None:
        assert r.returncode == check, (r.returncode, r.stdout[-500:], r.stderr[-800:])
    return r


def jread(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def lines_of(p):
    with open(p, encoding="utf-8") as f:
        return f.read().splitlines()


def write_text(p, text):
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def sha_file(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def writable(tree):
    for base, dirs, files in os.walk(tree):
        for f in files:
            os.chmod(os.path.join(base, f), stat.S_IRUSR | stat.S_IWUSR)


class Pipeline(unittest.TestCase):
    """Runs the whole synthetic pipeline once for the class."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="d1st_")
        cls.src, cls.tok, cls.man = d1_selftest_data.build(cls.tmp)
        cls.w = os.path.join(cls.tmp, "w")
        r = run_py(D1 / "d1_driver.py", "all", "--workdir", cls.w, "--mode", "selftest", "--config", CFG,
                   "--manifest", cls.man, "--source", "jsonl:" + cls.src, "--tokenizer", cls.tok)
        cls.rc, cls.out = r.returncode, r.stdout + r.stderr
        cls.ev = os.path.join(cls.w, "evidence")
        cls.clean = os.path.join(cls.ev, "clean")
        cls.ref = d1_verifier.build_ref(argparse.Namespace(config=CFG, manifest=cls.man, source="jsonl:" + cls.src,
                                                           tokenizer=cls.tok, mode="selftest"))[2]

    @classmethod
    def tearDownClass(cls):
        writable(cls.tmp)
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def common(self, sub, out=None):
        a = [D1 / "d1_verifier.py", sub, "--mode", "selftest", "--config", CFG, "--manifest", self.man,
             "--source", "jsonl:" + self.src, "--tokenizer", self.tok]
        return a + (["--out", out] if out else [])

    def scratch(self):
        d = tempfile.mkdtemp(prefix="d1tamper_", dir=self.tmp)
        return d

    # ---- the happy path ----
    def test_full_pipeline_passes(self):
        self.assertEqual(self.rc, 0, self.out[-1500:])
        dec = jread(os.path.join(self.ev, "D1_DECISION_all.json"))
        self.assertEqual(dec["read_resume"]["verdict"], "PASS")
        self.assertEqual(dec["negatives_meta"]["verdict"], "PASS")
        self.assertEqual(sorted(dec["negatives_meta"]["items"]), ["CR1", "CR2", "CR3"] + ["LR%d" % i for i in range(1, 10)])
        self.assertEqual(dec["identity"], "SELFTEST_SYNTHETIC")
        self.assertFalse(dec["d1_formal_experiment"])     # selftest is never a D1 experiment

    def test_cr_results_name_expected_row_and_class(self):
        for cid, cls in (("CR1", "ROW_SKIPPED"), ("CR2", "ROW_DUPLICATED"), ("CR3", "TOKEN_OFFSET_MISMATCH")):
            r = jread(os.path.join(self.ev, "negatives", cid, "result.json"))
            self.assertEqual(len(r["anomalies"]), 1)
            self.assertEqual(r["anomalies"][0]["class"], cls)
            self.assertEqual(r["anomalies"][0]["split"], "train")

    def test_carry_versus_eof_tail(self):
        sched = jread(os.path.join(self.clean, "schedule.json"))
        T = sched["T"]
        for i, name in enumerate(["P1", "P2", "P3", "P4"], start=1):
            fin = json.loads(lines_of(os.path.join(self.clean, "B_seg%d_trace.jsonl" % i))[-1])
            self.assertEqual(fin["kind"], "carry")
            self.assertNotIn("tail_len", fin)
            self.assertEqual(fin["carry_len"], sched["points"][name]["stream_pos"] % 65)
        for f in ("A_trace.jsonl", "B_seg5_trace.jsonl", "B_seg6_trace.jsonl"):
            fin = json.loads(lines_of(os.path.join(self.clean, f))[-1])
            self.assertEqual(fin["kind"], "eof_tail")
            self.assertEqual(fin["tail_len"], T % 65)
        c = {n: jread(os.path.join(self.clean, "cursors", n + ".json")) for n in ("P1", "P2", "P3", "P4", "P5")}
        self.assertEqual(len(c["P3"]["carry"]), 32)
        self.assertEqual(c["P4"]["carry"], [])            # empty carry is a legal cursor
        self.assertTrue(c["P5"]["eof"])
        self.assertEqual(len(c["P5"]["carry"]), T % 65)    # EOF cursor carry == tail

    def test_clean_evidence_is_read_only_and_write_once(self):
        for f in os.listdir(self.clean):
            p = os.path.join(self.clean, f)
            if os.path.isfile(p):
                self.assertEqual(os.stat(p).st_mode & 0o222, 0, f)
        r = run_py(D1 / "d1_reader.py", "--mode", "selftest", "--config", CFG, "--manifest", self.man,
                   "--source", "jsonl:" + self.src, "--tokenizer", self.tok,
                   "--trace-out", os.path.join(self.clean, "A_trace.jsonl"))
        self.assertNotEqual(r.returncode, 0)               # opening with 'x' refuses to overwrite

    # ---- the verifier must fail when it should ----
    def test_tamper_clean_trace_id(self):
        d = self.scratch()
        shutil.copytree(self.clean, d + "/c")
        writable(d)
        p = d + "/c/A_trace.jsonl"
        lines = lines_of(p)
        rec = json.loads(lines[101])
        rec["ids"][0] += 1
        lines[101] = d1_reader.canon(rec)
        write_text(p, "\n".join(lines) + "\n")
        r = run_py(*self.common("verify-clean", d + "/o.json"), "--clean-dir", d + "/c")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr[-400:])

    def test_tamper_cursor_file(self):
        d = self.scratch()
        shutil.copytree(self.clean, d + "/c")
        writable(d)
        cur = jread(d + "/c/cursors/P3.json")
        cur["carry"] = cur["carry"][:-1]
        write_text(d + "/c/cursors/P3.json", d1_reader.canon(cur))
        r = run_py(*self.common("verify-clean", d + "/o.json"), "--clean-dir", d + "/c")
        self.assertEqual(r.returncode, 1)

    def test_tamper_segment_claim_in_clean_trace(self):
        d = self.scratch()
        shutil.copytree(self.clean, d + "/c")
        writable(d)
        p = d + "/c/A_trace.jsonl"
        lines = lines_of(p)
        rec = json.loads(lines[50])
        rec["segments"][0]["count"] -= 1                   # a hole inside the block
        lines[50] = d1_reader.canon(rec)
        write_text(p, "\n".join(lines) + "\n")
        r = run_py(*self.common("verify-clean", d + "/o.json"), "--clean-dir", d + "/c")
        self.assertEqual(r.returncode, 1)

    def lr_args(self, lid, mutated, out):
        d = os.path.join(self.ev, "negatives", lid)
        spec = jread(CFG)["negatives"]["LR"][lid]
        return self.common("verify-lr", out) + ["--id", lid, "--orig", os.path.join(self.clean, "cursors", spec["cursor"] + ".json"),
                                                "--mutated", mutated, "--load-report", d + "/load_report.json", "--trace", d + "/trace.jsonl"]

    def test_lr_rejects_two_field_mutation(self):
        d = self.scratch()
        m = jread(os.path.join(self.ev, "negatives", "LR1", "mutated_cursor.json"))
        m["chain_hash"] = m["chain_hash"][:-1] + ("0" if m["chain_hash"][-1] != "0" else "1")
        write_text(d + "/m.json", d1_reader.canon(m))
        r = run_py(*self.lr_args("LR1", d + "/m.json", d + "/o.json"))
        self.assertEqual(r.returncode, 1)                  # criterion (e): more than one field differs

    def test_lr_wrong_reader_report_fails(self):
        d = self.scratch()
        args = self.lr_args("LR2", os.path.join(self.ev, "negatives", "LR2", "mutated_cursor.json"), d + "/o.json")
        args[args.index("--load-report") + 1] = os.path.join(self.ev, "negatives", "LR3", "load_report.json")
        self.assertEqual(run_py(*args).returncode, 1)         # reader reported REVISION_MISMATCH, LR2 expects TOKENIZER_HASH_MISMATCH

    def cr_args(self, cid, out, trace=None, before=None, after=None, clean=None):
        d = os.path.join(self.ev, "negatives", cid)
        spec = jread(CFG)["negatives"]["CR"][cid]
        return self.common("verify-cr", out) + [
            "--id", cid, "--cursor", os.path.join(self.clean, "cursors", spec["cursor"] + ".json"),
            "--load-report", d + "/load_report.json", "--trace", trace or d + "/trace.jsonl",
            "--control", d + "/control_trace.jsonl", "--clean-dir", clean or self.clean,
            "--evidence-before", before or d + "/evidence_before.json", "--evidence-after", after or d + "/evidence_after.json"]

    def test_cr_uninjected_trace_is_invalid_injection(self):
        d = self.scratch()
        ctl = os.path.join(self.ev, "negatives", "CR1", "control_trace.jsonl")
        r = run_py(*self.cr_args("CR1", d + "/o.json", trace=ctl))
        self.assertIn(r.returncode, (1, 4))
        self.assertNotEqual(r.returncode, 0)

    def test_cr_evidence_mutation_is_blocked(self):
        d = self.scratch()
        after = jread(os.path.join(self.ev, "negatives", "CR2", "evidence_after.json"))
        k = sorted(after)[0]
        after[k] = "0" * 64
        write_text(d + "/a.json", d1_reader.canon(after))
        r = run_py(*self.cr_args("CR2", d + "/o.json", after=d + "/a.json"))
        self.assertEqual(r.returncode, 4)

    def test_cr_prefix_tamper_is_blocked(self):
        d = self.scratch()
        shutil.copytree(self.clean, d + "/c")
        writable(d)
        p = d + "/c/A_trace.jsonl"
        lines = lines_of(p)
        rec = json.loads(lines[3])
        rec["ids"][5] += 1
        lines[3] = d1_reader.canon(rec)
        write_text(p, "\n".join(lines) + "\n")
        r = run_py(*self.cr_args("CR3", d + "/o.json", clean=d + "/c"))
        self.assertEqual(r.returncode, 4)

    def test_cr_wrong_id_for_trace_fails(self):
        d = self.scratch()
        cr1 = os.path.join(self.ev, "negatives", "CR1")
        spec = jread(CFG)["negatives"]["CR"]["CR2"]
        r = run_py(*(self.common("verify-cr", d + "/o.json") + [
            "--id", "CR2", "--cursor", os.path.join(self.clean, "cursors", "P2.json"),
            "--load-report", cr1 + "/load_report.json", "--trace", cr1 + "/trace.jsonl",
            "--control", cr1 + "/control_trace.jsonl", "--clean-dir", self.clean,
            "--evidence-before", cr1 + "/evidence_before.json", "--evidence-after", cr1 + "/evidence_after.json"]))
        self.assertEqual(r.returncode, 1)
        self.assertEqual(spec["inject"], "repeat_next_row")

    def test_cr_forged_segment_claim_fails(self):
        d = self.scratch()
        cr = os.path.join(self.ev, "negatives", "CR1")
        lines = lines_of(cr + "/trace.jsonl")
        rec = json.loads(lines[5])
        rec["segments"][0]["source_row_index"] += 1
        lines[5] = d1_reader.canon(rec)
        write_text(d + "/t.jsonl", "\n".join(lines) + "\n")
        r = run_py(*self.cr_args("CR1", d + "/o.json", trace=d + "/t.jsonl"))
        self.assertEqual(r.returncode, 1)

    # ---------------- C1 P0: fault-trace integrity, global order, control integrity ----------------
    def edit_lines(self, src, fn, name):
        d = self.scratch()
        lines = lines_of(src)
        fn(lines)
        out = os.path.join(d, name)
        write_text(out, "\n".join(lines) + "\n")
        return d, out

    def edit_rec(self, lines, idx, fn):
        rec = json.loads(lines[idx])
        fn(rec)
        lines[idx] = d1_reader.canon(rec)

    def cr_trace(self, cid, name="trace.jsonl"):
        return os.path.join(self.ev, "negatives", cid, name)

    def verify_cr_with(self, cid, trace, d):
        r = run_py(*self.cr_args(cid, d + "/o.json", trace=trace))
        res = jread(d + "/o.json") if os.path.exists(d + "/o.json") else None
        return r.returncode, res

    def failed_checks(self, res):
        return [c["check"] for c in res["checks"] if c["status"] != "PASS"]

    def test_cr_single_block_hash_tamper_fails(self):
        d, t = self.edit_lines(self.cr_trace("CR2"), lambda L: self.edit_rec(L, 40, lambda r: r.update(block_hash="0" * 64)), "t.jsonl")
        rc, res = self.verify_cr_with("CR2", t, d)
        self.assertEqual(rc, 1)
        self.assertTrue(any("fault trace integrity" in c for c in self.failed_checks(res)))

    def test_cr_final_chain_hash_tamper_fails(self):
        d, t = self.edit_lines(self.cr_trace("CR1"), lambda L: self.edit_rec(L, len(L) - 1, lambda r: r.update(chain_hash="1" * 64)), "t.jsonl")
        self.assertEqual(self.verify_cr_with("CR1", t, d)[0], 1)

    def test_cr_tail_sha256_tamper_fails(self):
        d, t = self.edit_lines(self.cr_trace("CR3"), lambda L: self.edit_rec(L, len(L) - 1, lambda r: r.update(tail_sha256="2" * 64)), "t.jsonl")
        rc, res = self.verify_cr_with("CR3", t, d)
        self.assertEqual(rc, 1)
        self.assertTrue(any("fault trace integrity" in c for c in self.failed_checks(res)))

    def test_cr_totals_position_and_numbering_tamper_fail(self):
        for name, fn, last in (("blocks_total", lambda r: r.update(blocks_total=r["blocks_total"] + 1), True),
                               ("stream_token_pos", lambda r: r.update(stream_token_pos=r["stream_token_pos"] + 1), True),
                               ("tail_len", lambda r: r.update(tail_len=r["tail_len"] + 1), True),
                               ("block_index_gap", lambda r: r.update(block_index=r["block_index"] + 1), False)):
            d, t = self.edit_lines(self.cr_trace("CR1"), lambda L: self.edit_rec(L, len(L) - 1 if last else 30, fn), "t.jsonl")
            self.assertEqual(self.verify_cr_with("CR1", t, d)[0], 1, name)

    def test_cr_control_trace_tamper_fails(self):
        for what, fn in (("ids", lambda r: r["ids"].__setitem__(0, r["ids"][0] + 1)),
                         ("block_hash", lambda r: r.update(block_hash="3" * 64))):
            d, t = self.edit_lines(self.cr_trace("CR1", "control_trace.jsonl"), lambda L: self.edit_rec(L, 25, fn), "c.jsonl")
            r = run_py(*self.cr_args("CR1", d + "/o.json"))      # untouched baseline stays PASS
            self.assertEqual(r.returncode, 0)
            args = self.cr_args("CR1", d + "/o2.json")
            args[args.index("--control") + 1] = t
            r = run_py(*args)
            self.assertEqual(r.returncode, 1, what)
            self.assertTrue(any("control trace integrity" in c for c in self.failed_checks(jread(d + "/o2.json"))), what)

    def forge(self, cid, pieces):
        """Build a self-consistent CR trace (valid hashes, chain, tail, segments) from arbitrary row pieces."""
        ref = self.ref
        spec = jread(CFG)["negatives"]["CR"][cid]
        cur = jread(os.path.join(self.clean, "cursors", spec["cursor"] + ".json"))
        hdr = json.loads(lines_of(self.cr_trace(cid))[0])
        e, carry = cur["emitted_blocks"], cur["carry"]
        c = len(carry)
        prov, new = [], []
        for (r, o, n) in pieces:
            for k in range(n):
                new.append(ref.rows[r].ids[o + k])
                prov.append((r, o + k))
        stream = carry + new
        nb = len(stream) // 65

        def group(lo, hi):
            segs = []
            for (r, off) in prov[lo:hi]:
                if segs and segs[-1]["ordinal"] == r and segs[-1]["row_offset"] + segs[-1]["count"] == off:
                    segs[-1]["count"] += 1
                else:
                    segs.append({"ordinal": r, "source_row_index": ref.rows[r].phys, "row_offset": off, "count": 1})
            return segs

        chain = bytes.fromhex(cur["chain_hash"])
        recs = [hdr]
        for j in range(nb):
            ids = stream[65 * j:65 * j + 65]
            bh = hashlib.sha256(d1_verifier.pack(ids)).digest()
            chain = hashlib.sha256(chain + bh).digest()
            recs.append({"type": "block", "block_index": e + j, "block_hash": bh.hex(), "ids": ids,
                         "segments": group(max(65 * j, c) - c, 65 * j + 65 - c)})
        tail = stream[65 * nb:]
        recs.append({"type": "final", "kind": "eof_tail", "tail_ids": tail, "tail_segments": group(max(65 * nb, c) - c, len(stream) - c),
                     "tail_len": len(tail), "tail_sha256": hashlib.sha256(d1_verifier.pack(tail)).hexdigest(),
                     "blocks_total": e + nb, "blocks_this_run": nb, "chain_hash": chain.hex(), "stream_token_pos": 65 * e + len(stream)})
        d = self.scratch()
        out = os.path.join(d, "forged.jsonl")
        write_text(out, "".join(d1_reader.canon(x) + "\n" for x in recs))
        return d, out, cur, spec

    def test_forged_exact_expected_trace_passes(self):
        for cid in ("CR1", "CR2", "CR3"):
            spec = jread(CFG)["negatives"]["CR"][cid]
            cur = jread(os.path.join(self.clean, "cursors", spec["cursor"] + ".json"))
            pieces = d1_verifier.fault_plan(self.ref, spec["inject"], cur["next_eligible_row"], cur["row_token_offset"])
            d, t, _, _ = self.forge(cid, pieces)
            rc, res = self.verify_cr_with(cid, t, d)
            self.assertEqual(rc, 0, (cid, self.failed_checks(res) if res else None))    # forge helper itself is faithful

    def test_cr_global_source_order_change_fails_even_when_row_classification_passes(self):
        # CR1 with the skipped row as required, but two later whole rows swapped. Every row is still consumed
        # exactly once, contiguously, so the per-row classification sees only the skip; the global order check must fail.
        spec = jread(CFG)["negatives"]["CR"]["CR1"]
        cur = jread(os.path.join(self.clean, "cursors", "P2.json"))
        pieces = d1_verifier.fault_plan(self.ref, spec["inject"], cur["next_eligible_row"], cur["row_token_offset"])
        pieces[5], pieces[6] = pieces[6], pieces[5]
        d, t, _, _ = self.forge("CR1", pieces)
        rc, res = self.verify_cr_with("CR1", t, d)
        self.assertEqual(rc, 1)
        failed = self.failed_checks(res)
        self.assertFalse(any(c.startswith("(d) ") for c in failed), failed)     # per-row classification alone would have passed
        self.assertTrue(any(c.startswith("(d')") for c in failed), failed)

    def test_cr_second_mutation_hidden_from_row_classification_fails(self):
        # CR3-style shift plus a second, compensating shift elsewhere is also not "the one unique mutation".
        spec = jread(CFG)["negatives"]["CR"]["CR2"]
        cur = jread(os.path.join(self.clean, "cursors", "P4.json"))
        pieces = d1_verifier.fault_plan(self.ref, spec["inject"], cur["next_eligible_row"], cur["row_token_offset"])
        pieces[7], pieces[8] = pieces[8], pieces[7]
        d, t, _, _ = self.forge("CR2", pieces)
        self.assertEqual(self.verify_cr_with("CR2", t, d)[0], 1)

    # ---------------- C1 P0-4: schedule recomputed in verify-clean ----------------
    def test_verify_clean_recomputes_schedule(self):
        d = self.scratch()
        shutil.copytree(self.clean, d + "/c")
        writable(d)
        sch = jread(d + "/c/schedule.json")
        sch["points"]["P3"]["stream_pos"] += 65             # still ascending, still carry 32 -> old checks would not notice
        write_text(d + "/c/schedule.json", d1_reader.canon(sch))
        r = run_py(*self.common("verify-clean", d + "/o.json"), "--clean-dir", d + "/c")
        self.assertEqual(r.returncode, 1)
        failed = self.failed_checks(jread(d + "/o.json"))
        self.assertTrue(any(c.startswith("schedule recomputed") for c in failed), failed)

    # ---------------- C1 P1: scope of the output ----------------
    def test_pipeline_never_outputs_a_full_d1_pass(self):
        dec = jread(os.path.join(self.ev, "D1_DECISION_all.json"))
        self.assertTrue(dec["d1_overall"].startswith("NOT_DECLARED"))
        text = json.dumps(dec)
        self.assertNotIn("D1 PASS", text)
        joined = " ".join(dec["not_tested"])
        for k in ("R6", "R7", "T1-T6", "acquisition"):
            self.assertIn(k, joined)
        vc = jread(os.path.join(self.ev, "verify_clean_result.json"))
        self.assertEqual(sorted(vc["not_tested"].values()), ["NOT TESTED"] * 4)
        self.assertIn("NOT a D1 verdict", vc["scope"])


STUB_TEMPLATE = """import sys
a = sys.argv
out = a[a.index("--out") + 1] if "--out" in a else None
content = %r
if content is not None and out:
    with open(out, "w") as f:
        f.write(content)
%s
sys.exit(%d)
"""


class C2Gates(unittest.TestCase):
    """C2: reader exit-code mapping, frozen 30-minute cap, safe handling of abnormal verifier results."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="d1c2_")
        cls.src, cls.tok, cls.man = d1_selftest_data.build(cls.tmp)
        cls.n = 0

    @classmethod
    def tearDownClass(cls):
        writable(cls.tmp)
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def setUp(self):
        self._reader, self._verifier = d1_driver.READER, d1_driver.VERIFIER

    def tearDown(self):
        d1_driver.READER, d1_driver.VERIFIER = self._reader, self._verifier

    def stub(self, rc, content=None, extra=""):
        type(self).n += 1
        p = os.path.join(self.tmp, "stub%d.py" % self.n)
        write_text(p, STUB_TEMPLATE % (content, extra, rc))
        return p

    def drive(self, cmd="clean", mode="selftest", extra=(), workdir=None, src=None, tok=None, man=None):
        type(self).n += 1
        w = workdir or os.path.join(self.tmp, "w%d" % self.n)
        rc = d1_driver.main([cmd, "--workdir", w, "--mode", mode, "--config", CFG, "--manifest", man or self.man,
                             "--source", src or ("jsonl:" + self.src), "--tokenizer", tok or self.tok] + list(extra))
        return rc, w, jread(os.path.join(w, "evidence", "D1_DECISION_%s.json" % cmd))

    # ---- 1. reader exit code -> status
    def test_reader_status_mapping(self):
        rs = d1_driver.reader_status
        self.assertEqual([rs(0), rs(4), rs(5), rs(3), rs(1), rs(2), rs(-11)], ["OK", "BLOCKED", "FAIL", "FAIL", "FAIL", "FAIL", "FAIL"])
        self.assertEqual([rs(3, expect=3), rs(4, expect=3), rs(0, expect=3)], ["OK", "BLOCKED", "FAIL"])

    def test_reader_blocked_precondition_is_blocked_not_fail(self):
        d1_driver.READER = self.stub(4)
        rc, w, dec = self.drive("clean")
        self.assertEqual((rc, dec["verdict"], dec["read_resume"]["verdict"]), (4, "BLOCKED", "BLOCKED"))

    def test_reader_selfcheck_and_crash_are_fail(self):
        for code in (5, 1, 3):
            d1_driver.READER = self.stub(code)
            rc, w, dec = self.drive("clean")
            self.assertEqual((rc, dec["read_resume"]["verdict"]), (1, "FAIL"), code)

    def test_negatives_reader_blocked_is_blocked_and_clean_failure_marks_negatives_not_tested(self):
        d1_driver.READER = self.stub(5)
        rc, w, dec = self.drive("all")
        self.assertEqual(dec["read_resume"]["verdict"], "FAIL")
        self.assertEqual(dec["negatives_meta"]["verdict"], "NOT TESTED")        # explicit, not silently absent
        d1_driver.READER = self._reader
        rc, w, dec = self.drive("clean")                                          # a real clean run to reuse
        self.assertEqual(rc, 0)
        d1_driver.READER = self.stub(4)
        w2 = os.path.join(self.tmp, "wneg")
        shutil.copytree(os.path.join(w, "evidence", "clean"), os.path.join(w2, "evidence", "clean"))
        writable(w2)
        rc, _, dec = self.drive("negatives", workdir=w2)
        self.assertEqual((rc, dec["negatives_meta"]["verdict"]), (4, "BLOCKED"))
        self.assertTrue(all(v["verdict"] == "BLOCKED" for v in dec["negatives_meta"]["items"].values()))

    # ---- 2. frozen 30-minute cap
    def test_real_mode_refuses_timeout_override(self):
        w = os.path.join(self.tmp, "wreal")
        r = run_py(D1 / "d1_driver.py", "all", "--workdir", w, "--mode", "real", "--config", CFG, "--manifest", self.man,
                   "--source", "parquet:/nonexistent.parquet", "--tokenizer", "/nonexistent.json", "--timeout-seconds", "5")
        self.assertEqual(r.returncode, 4, r.stdout + r.stderr)
        dec = jread(w + "/evidence/D1_DECISION_all.json")
        self.assertEqual(dec["timeout_override_refused"]["verdict"], "BLOCKED")
        self.assertEqual(dec["steps"], [])                                         # nothing was executed
        self.assertFalse(os.path.exists(w + "/evidence/clean"))

    def test_selftest_override_may_only_shorten(self):
        for bad in ("5000", "0", "-3"):
            rc, w, dec = self.drive("clean", extra=["--timeout-seconds", bad])
            self.assertEqual((rc, dec["verdict"]), (4, "BLOCKED"), bad)
            self.assertEqual(dec["steps"], [])
        d1_driver.READER = self.stub(0)
        rc, w, dec = self.drive("clean", extra=["--timeout-seconds", "1500"])      # shorter than 1800: accepted
        self.assertEqual(dec["wallclock_limit_seconds"], 1500.0)

    def test_real_mode_cannot_relax_the_cap_through_the_config(self):
        c = jread(CFG)
        c["environment"]["wallclock_limit_minutes"] = 120
        cfg = os.path.join(self.tmp, "relaxed.json")
        write_text(cfg, json.dumps(c))
        w = os.path.join(self.tmp, "wrelax")
        r = run_py(D1 / "d1_driver.py", "clean", "--workdir", w, "--mode", "real", "--config", cfg, "--manifest", self.man,
                   "--source", "parquet:/nonexistent.parquet", "--tokenizer", "/nonexistent.json")
        self.assertEqual(r.returncode, 4)
        self.assertEqual(jread(w + "/evidence/D1_DECISION_clean.json")["steps"], [])

    # ---- 3. abnormal verifier outcomes
    def test_verifier_verdict_mapping(self):
        d = tempfile.mkdtemp(dir=self.tmp)
        res = os.path.join(d, "r.json")
        vv = d1_driver.verifier_verdict
        write_text(res, json.dumps({"verdict": "PASS"}))
        self.assertEqual(vv(0, res)[0], "PASS")
        self.assertEqual(vv(1, res)[0], "FAIL")                                     # exit 1 but result says PASS
        self.assertEqual(vv(4, res)[0], "FAIL")
        self.assertEqual(vv(2, res)[0], "FAIL")
        self.assertEqual(vv(-11, res)[0], "FAIL")
        write_text(res + "2", json.dumps({"verdict": "BLOCKED"}))
        self.assertEqual(vv(4, res + "2")[0], "BLOCKED")
        self.assertEqual(vv(0, res + "2")[0], "FAIL")
        for bad in ("{not json", "[]", json.dumps({"verdict": "MAYBE"}), json.dumps({})):
            with open(res + "3", "w") as f:
                f.write(bad)
            self.assertEqual(vv(0, res + "3")[0], "FAIL", bad)
            self.assertEqual(vv(1, res + "3")[0], "FAIL", bad)
        # C2a: exit 4 is BLOCKED only when the result file does not exist; an existing but unusable file is FAIL
        for bad in ("{not json", "", "[]", json.dumps({"verdict": "MAYBE"}), json.dumps({}), json.dumps({"verdict": "PASS"})):
            with open(res + "4", "w") as f:
                f.write(bad)
            self.assertEqual(vv(4, res + "4")[0], "FAIL", repr(bad))
        os.makedirs(d + "/isdir.json")
        self.assertEqual(vv(4, d + "/isdir.json")[0], "FAIL")                      # exists but is not a readable file
        self.assertEqual(vv(0, d + "/missing.json")[0], "FAIL")                    # exit 0 without a result is never PASS
        self.assertEqual(vv(1, d + "/missing.json")[0], "FAIL")
        self.assertEqual(vv(4, d + "/missing.json")[0], "BLOCKED")

    def test_exit4_with_unparseable_result_is_fail_through_the_driver(self):
        for content in ("{oops", "", json.dumps({"verdict": "MAYBE"})):
            d1_driver.VERIFIER = self.stub(4, content)
            rc, w, dec = self.drive("clean")
            self.assertEqual((dec["read_resume"]["verdict"], rc), ("FAIL", 1), content)
        d1_driver.VERIFIER = self.stub(4, json.dumps({"verdict": "BLOCKED"}))      # a proper BLOCKED record is still BLOCKED
        rc, w, dec = self.drive("clean")
        self.assertEqual((dec["read_resume"]["verdict"], rc), ("BLOCKED", 4))

    # ---- C2a: FAIL takes precedence over BLOCKED when results are mixed
    def test_aggregate_precedence(self):
        ag = d1_driver.aggregate
        self.assertEqual(ag(["PASS"] * 3), "PASS")
        self.assertEqual(ag(["PASS", "BLOCKED"]), "BLOCKED")
        self.assertEqual(ag(["BLOCKED", "BLOCKED"]), "BLOCKED")
        self.assertEqual(ag(["PASS", "FAIL"]), "FAIL")
        self.assertEqual(ag(["BLOCKED", "FAIL", "PASS"]), "FAIL")
        self.assertEqual(ag(["FAIL", "BLOCKED"]), "FAIL")
        self.assertEqual(ag([]), "FAIL")
        self.assertEqual(ag(["PASS", "NOT TESTED"]), "FAIL")
        self.assertEqual(ag(["PASS", None]), "FAIL")

    def test_mixed_negative_results_report_fail_and_keep_item_detail(self):
        rc, w, dec = self.drive("clean")
        self.assertEqual(rc, 0)
        w2 = os.path.join(self.tmp, "wmix")
        shutil.copytree(os.path.join(w, "evidence", "clean"), os.path.join(w2, "evidence", "clean"))
        writable(w2)
        # LR1's reader is BLOCKED (exit 4); every other reader exits 3 without writing evidence -> the real verifier FAILs
        type(self).n += 1
        p = os.path.join(self.tmp, "mixstub%d.py" % self.n)
        write_text(p, "import sys\nsys.exit(4 if any('/LR1/' in x for x in sys.argv) else 3)\n")
        d1_driver.READER = p
        rc, _, dec = self.drive("negatives", workdir=w2)
        nm = dec["negatives_meta"]
        self.assertEqual((rc, dec["verdict"], nm["verdict"]), (1, "FAIL", "FAIL"))        # FAIL wins, exit code 1
        self.assertEqual(nm["items"]["LR1"]["verdict"], "BLOCKED")                       # the BLOCKED item is still visible
        self.assertEqual(nm["items"]["LR2"]["verdict"], "FAIL")
        self.assertEqual(nm["counts"], {"PASS": 0, "FAIL": 11, "BLOCKED": 1})
        # all-BLOCKED stays BLOCKED (exit 4); this already holds in test_negatives_reader_blocked...

    # ---- C2b fix 1: CR reader pair uses FAIL > BLOCKED > PASS and keeps both readers' details
    def test_cr_reader_pair_verdict(self):
        f = d1_driver.cr_reader_verdict
        for rcs, want in (((4, 1), "FAIL"), ((1, 4), "FAIL"), ((4, 4), "BLOCKED"), ((0, 4), "BLOCKED"), ((4, 0), "BLOCKED"),
                          ((5, 0), "FAIL"), ((0, 5), "FAIL"), ((0, 0), "PASS"), ((3, 0), "FAIL"), ((0, 3), "FAIL")):
            self.assertEqual(f(*rcs)[0], want, rcs)
        v, detail = f(4, 1)
        self.assertEqual(detail, {"fault": {"rc": 4, "status": "BLOCKED"}, "control": {"rc": 1, "status": "FAIL"}})

    def test_cr_mixed_reader_outcomes_through_the_driver(self):
        rc, w, dec = self.drive("clean")
        self.assertEqual(rc, 0)
        w2 = os.path.join(self.tmp, "wcrmix")
        shutil.copytree(os.path.join(w, "evidence", "clean"), os.path.join(w2, "evidence", "clean"))
        writable(w2)
        type(self).n += 1
        p = os.path.join(self.tmp, "crstub%d.py" % self.n)
        # exit codes (fault run, control run) per CR; LR readers exit 3 without evidence (not under test here)
        write_text(p, "import sys\na = sys.argv\nif any('/LR' in x for x in a):\n    sys.exit(3)\nfault = '--inject' in a\n"
                      "codes = {'/CR1/': (4, 1), '/CR2/': (1, 4), '/CR3/': (4, 4)}\n"
                      "for k, (f, c) in codes.items():\n    if any(k in x for x in a):\n        sys.exit(f if fault else c)\nsys.exit(0)\n")
        d1_driver.READER = p
        rc, _, dec = self.drive("negatives", workdir=w2)
        it = dec["negatives_meta"]["items"]
        self.assertEqual((it["CR1"]["verdict"], it["CR2"]["verdict"], it["CR3"]["verdict"]), ("FAIL", "FAIL", "BLOCKED"))
        self.assertEqual(it["CR1"]["readers"], {"fault": {"rc": 4, "status": "BLOCKED"}, "control": {"rc": 1, "status": "FAIL"}})
        self.assertEqual(it["CR2"]["readers"], {"fault": {"rc": 1, "status": "FAIL"}, "control": {"rc": 4, "status": "BLOCKED"}})
        self.assertEqual(it["CR3"]["readers"], {"fault": {"rc": 4, "status": "BLOCKED"}, "control": {"rc": 4, "status": "BLOCKED"}})
        self.assertEqual((rc, dec["verdict"]), (1, "FAIL"))

    # ---- C2b fix 2: a non-string verdict is FAIL, never an unhandled TypeError
    NON_STRING_VERDICTS = ('{"verdict":[]}', '{"verdict":{}}', '{"verdict":null}', '{"verdict":123}', '{"verdict":true}')

    def test_non_string_verdict_is_fail_not_typeerror(self):
        d = tempfile.mkdtemp(dir=self.tmp)
        vv = d1_driver.verifier_verdict
        for text in self.NON_STRING_VERDICTS:
            with open(d + "/r.json", "w") as f:
                f.write(text)
            for rc in (0, 1, 4):
                self.assertEqual(vv(rc, d + "/r.json")[0], "FAIL", (text, rc))
        # behaviours that must not change
        self.assertEqual(vv(4, d + "/absent.json")[0], "BLOCKED")
        for text, rc, want in (('{"verdict":"BLOCKED"}', 4, "BLOCKED"), ('{"verdict":"PASS"}', 0, "PASS"), ('{"verdict":"FAIL"}', 1, "FAIL"),
                               ('{oops', 4, "FAIL"), ('{"verdict":"MAYBE"}', 4, "FAIL"), ('{"verdict":"PASS"}', 4, "FAIL")):
            with open(d + "/k.json", "w") as f:
                f.write(text)
            self.assertEqual(vv(rc, d + "/k.json")[0], want, (text, rc))
        self.assertEqual(d1_driver.aggregate(["PASS", []]), "FAIL")                 # unhashable members must not raise either
        self.assertEqual(d1_driver.aggregate([{}]), "FAIL")

    def test_non_string_verdict_through_the_driver_is_a_clean_fail(self):
        for text in self.NON_STRING_VERDICTS:
            d1_driver.VERIFIER = self.stub(0, text)
            rc, w, dec = self.drive("clean")
            self.assertEqual((dec["read_resume"]["verdict"], rc), ("FAIL", 1), text)
            self.assertNotIn("driver_exception", dec, text)                         # handled, not an escaped exception

    def test_driver_records_abnormal_verifier_runs(self):
        cases = (("exit0_no_result", 0, None, "", "FAIL", 1), ("exit0_malformed", 0, "{oops", "", "FAIL", 1),
                 ("exit0_but_FAIL", 0, json.dumps({"verdict": "FAIL"}), "", "FAIL", 1),
                 ("exit1_no_result", 1, None, "", "FAIL", 1), ("exit4_no_result", 4, None, "", "BLOCKED", 4),
                 ("exit4_says_PASS", 4, json.dumps({"verdict": "PASS"}), "", "FAIL", 1),
                 ("killed_by_signal", 0, None, "import os, signal\nos.kill(os.getpid(), signal.SIGSEGV)", "FAIL", 1))
        for name, rc_stub, content, extra, want, want_rc in cases:
            d1_driver.VERIFIER = self.stub(rc_stub, content, extra)
            rc, w, dec = self.drive("clean")
            self.assertEqual((dec["read_resume"]["verdict"], rc, dec["verdict"]), (want, want_rc, want), name)
            self.assertEqual(dec["negatives_meta"]["verdict"] if "negatives_meta" in dec else None, None, name)

    def test_real_verifier_leaves_a_fail_result_on_abnormal_exit(self):
        d = tempfile.mkdtemp(dir=self.tmp)
        common = [D1 / "d1_verifier.py", "schedule", "--mode", "selftest", "--config", CFG, "--manifest", self.man,
                  "--tokenizer", self.tok, "--out", d + "/r.json"]
        r = run_py(*common, "--source", "jsonl:" + d + "/does_not_exist.jsonl")       # OSError inside the verifier
        self.assertEqual(r.returncode, 1)
        res = jread(d + "/r.json")                                                   # a record exists
        self.assertEqual(res["verdict"], "FAIL")
        self.assertIn("abnormal exit", res["reason"])
        r = run_py(D1 / "d1_verifier.py", "verify-lr", "--mode", "selftest", "--config", CFG, "--manifest", self.man,
                   "--source", "jsonl:" + self.src, "--tokenizer", self.tok, "--out", d + "/r2.json", "--id", "LR1",
                   "--orig", d + "/a", "--mutated", d + "/b", "--load-report", d + "/c", "--trace", d + "/d")
        self.assertEqual((r.returncode, jread(d + "/r2.json")["verdict"]), (1, "FAIL"))
        man2 = d + "/m.json"
        write_text(man2, json.dumps({"parquet_sha256": "0" * 64, "tokenizer_sha256": "0" * 64, "actual_vocab_size": 259}))
        r = run_py(D1 / "d1_verifier.py", "schedule", "--mode", "selftest", "--config", CFG, "--manifest", man2,
                   "--source", "jsonl:" + self.src, "--tokenizer", self.tok, "--out", d + "/r3.json")
        self.assertEqual((r.returncode, jread(d + "/r3.json")["verdict"]), (4, "BLOCKED"))

    def test_driver_exception_still_writes_a_decision(self):
        w = os.path.join(self.tmp, "wexc")
        os.makedirs(w + "/evidence/clean")                     # do_clean's makedirs(exist_ok=False) will raise
        rc, _, dec = self.drive("clean", workdir=w)
        self.assertEqual((rc, dec["verdict"]), (1, "FAIL"))
        self.assertIn("FileExistsError", dec["driver_exception"]["error"])

    def test_verifier_crash_inside_negatives_is_recorded_not_fatal(self):
        rc, w, dec = self.drive("clean")
        self.assertEqual(rc, 0)
        w2 = os.path.join(self.tmp, "wneg2")
        shutil.copytree(os.path.join(w, "evidence", "clean"), os.path.join(w2, "evidence", "clean"))
        writable(w2)
        d1_driver.READER = self.stub(3)                        # claims "cursor rejected" but writes no report/trace
        rc, _, dec = self.drive("negatives", workdir=w2)
        self.assertEqual(rc, 1)
        items = dec["negatives_meta"]["items"]
        self.assertEqual({v["verdict"] for k, v in items.items() if k.startswith("LR")}, {"FAIL"})   # real verifier fails safely
        self.assertTrue(os.path.exists(w2 + "/evidence/negatives/LR1/result.json"))


class Blocked(unittest.TestCase):
    def test_p2_rule_without_candidate_row_is_blocked_schedule(self):
        tmp = tempfile.mkdtemp(prefix="d1blk_")
        try:
            src, tok, man = d1_selftest_data.build(tmp, "no_p2_row")
            r = run_py(D1 / "d1_driver.py", "clean", "--workdir", tmp + "/w", "--mode", "selftest", "--config", CFG,
                       "--manifest", man, "--source", "jsonl:" + src, "--tokenizer", tok)
            self.assertEqual(r.returncode, 4)                  # BLOCKED is exit 4, never reported as FAIL (exit 1)
            dec = jread(tmp + "/w/evidence/D1_DECISION_clean.json")
            self.assertEqual(dec["verdict"], "BLOCKED")
            self.assertEqual(dec["read_resume"]["verdict"], "BLOCKED")
            self.assertIn("schedule", dec["read_resume"]["why"])
            self.assertFalse(os.path.exists(tmp + "/w/evidence/clean/A_trace.jsonl"))   # nothing was read
        finally:
            writable(tmp)
            shutil.rmtree(tmp, ignore_errors=True)


class IdentityTimeoutEnv(unittest.TestCase):
    def cfg(self, status="FROZEN"):
        c = jread(CFG)
        c["status"] = status
        return c

    def formal(self, **kw):
        f = {"authorization_ref": "owner-2026-xx", "hub_revision": "b08601e04326c79dfdd32d625aee71d232d685c3",
             "lfs_oid_parquet": "a" * 64, "tokenizer_fit_manifest_sha256": "b" * 64}
        f.update(kw)
        return {"parquet_sha256": "a" * 64, "formal": f}

    def test_identity_labels(self):
        ident = d1_driver.identity
        self.assertEqual(ident("selftest", self.cfg(), self.formal()), "SELFTEST_SYNTHETIC")
        self.assertEqual(ident("real", self.cfg("FROZEN_CANDIDATE__PENDING_CHATGPT_CODE_REVIEW"), self.formal()), "REAL_CODE_PATH_NON_FORMAL")
        self.assertEqual(ident("real", self.cfg(), {"parquet_sha256": "a" * 64}), "REAL_CODE_PATH_NON_FORMAL")
        self.assertEqual(ident("real", self.cfg(), dict(self.formal(), synthetic=True)), "REAL_CODE_PATH_NON_FORMAL")
        self.assertEqual(ident("real", self.cfg(), self.formal(lfs_oid_parquet="c" * 64)), "REAL_CODE_PATH_NON_FORMAL")
        self.assertEqual(ident("real", self.cfg(), self.formal(authorization_ref=" ")), "REAL_CODE_PATH_NON_FORMAL")
        self.assertEqual(ident("real", self.cfg(), self.formal()), "FORMAL_D1_CANDIDATE")
        self.assertNotEqual(jread(CFG)["status"], "FROZEN")      # the shipped config cannot yield a formal run yet

    def test_wallclock_timeout_is_blocked_keeps_evidence_and_never_retries(self):
        tmp = tempfile.mkdtemp(prefix="d1to_")
        try:
            src, tok, man = d1_selftest_data.build(tmp)
            r = run_py(D1 / "d1_driver.py", "clean", "--workdir", tmp + "/w", "--mode", "selftest", "--config", CFG, "--manifest", man,
                       "--source", "jsonl:" + src, "--tokenizer", tok, "--timeout-seconds", "0.8")
            self.assertEqual(r.returncode, 4, r.stdout[-500:] + r.stderr[-500:])
            dec = jread(tmp + "/w/evidence/D1_DECISION_clean.json")
            self.assertEqual(dec["timeout"]["verdict"], "BLOCKED(timeout)")
            self.assertIn("no automatic retry", dec["timeout"]["policy"])
            self.assertIn("RUN_META.json", dec["evidence_files_at_timeout"])      # evidence already on disk is kept
            self.assertTrue(os.path.exists(tmp + "/w/evidence/RUN_META.json"))
            cmds = [json.dumps(x["cmd"]) for x in dec["steps"]]
            self.assertEqual(len(cmds), len(set(cmds)))                          # no command was run twice
            self.assertIn(dec["steps"][-1]["rc"], ("TIMEOUT_KILLED", "NOT_STARTED_DEADLINE_PASSED"))
            self.assertNotIn("read_resume", dec)
        finally:
            writable(tmp)
            shutil.rmtree(tmp, ignore_errors=True)

    def test_real_mode_requires_exact_python_patch_version(self):
        tmp = tempfile.mkdtemp(prefix="d1env_")
        try:
            c = jread(CFG)
            c["environment"]["python_full_version"] = "0.0.0"
            write_text(tmp + "/c.json", json.dumps(c))
            r = run_py(D1 / "d1_env_manifest.py", "--mode", "real", "--config", tmp + "/c.json", "--out", tmp + "/m1.json")
            self.assertEqual(r.returncode, 4)
            self.assertIn("python", jread(tmp + "/m1.json")["problems"][0])
            r = run_py(D1 / "d1_env_manifest.py", "--mode", "selftest", "--config", tmp + "/c.json", "--out", tmp + "/m2.json")
            self.assertEqual(r.returncode, 0)             # selftest only needs an allowed minor version
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class Primitives(unittest.TestCase):
    """Frozen byte conventions (R2 section 5 synthetic vector)."""

    H0 = "c5a91b61d09dd6ace479fcb77286d5f3da165cc4c0f0010d44aa271aa2d9dd11"
    BH0 = "fee16ec542015efdeec7654ea06333eb655815da008a8a349efad6d02e86ed35"
    H1 = "9bc269374738a4926714df76039ce40097138356c621e2aab3dfc7dff8875a10"
    BH1 = "67e5aabc0cc44b005d4a0eedeec3c54ae65ea2b62f758f6077ea48547b9aaa57"
    H2 = "7ae2356958f57f0ef4ac1f872392f55f44dd422703ed64e82a4655e033833d2e"
    HEXCAT = "2f001906d9e7048e83651dd08c43581c14aed68fbfc2d9c7c6e03897c056c329"

    def check(self, ser):
        b0, b1 = list(range(65)), list(range(65, 130))
        self.assertEqual(len(ser(b0)), 260)
        h0 = hashlib.sha256(b"MINI-MYTHOS-D1-CHAIN-V1").digest()
        bh0, bh1 = hashlib.sha256(ser(b0)).digest(), hashlib.sha256(ser(b1)).digest()
        h1 = hashlib.sha256(h0 + bh0).digest()
        h2 = hashlib.sha256(h1 + bh1).digest()
        self.assertEqual([x.hex() for x in (h0, bh0, h1, bh1, h2)], [self.H0, self.BH0, self.H1, self.BH1, self.H2])
        self.assertNotEqual(hashlib.sha256((h0.hex() + bh0.hex()).encode()).hexdigest(), self.H1)
        self.assertEqual(hashlib.sha256((h0.hex() + bh0.hex()).encode()).hexdigest(), self.HEXCAT)

    def test_reader_serialization(self):
        self.check(d1_reader.ser_ids)
        self.assertEqual(hashlib.sha256(d1_reader.CHAIN_INIT).hexdigest(), self.H0)

    def test_verifier_serialization(self):
        self.check(d1_verifier.pack)

    def test_reader_assert_tiles(self):
        lens = [3, 2, 4]
        ok = [{"ordinal": 0, "row_offset": 0, "count": 3}, {"ordinal": 1, "row_offset": 0, "count": 2}, {"ordinal": 2, "row_offset": 0, "count": 4}]
        d1_reader.assert_tiles(ok, lens, 0, 0, 3, 0)
        for bad, msg in (([dict(ok[0], count=2)] + ok[1:], "GAP"),                      # hole
                         ([ok[0], dict(ok[1], row_offset=1, count=1)] + ok[2:], "GAP"),
                         ([ok[0], ok[0]] + ok[1:], "OVERLAP"),                            # repeated piece
                         (ok[:2], "UNCOVERED"),                                           # tail not covered
                         ([ok[0], ok[2]], "GAP")):                                        # skipped row
            with self.assertRaises(d1_reader.SelfCheckFailed) as cm:
                d1_reader.assert_tiles(bad, lens, 0, 0, 3, 0)
            self.assertIn(msg, str(cm.exception))

    def test_verifier_tile_errors(self):
        class R:
            pass
        ref = R()
        rows = []
        for n in (3, 2, 4):
            r = R()
            r.ids = list(range(1, n + 1))
            rows.append(r)
        ref.rows, ref.W, ref.cum = rows, 3, [0, 3, 5, 9]
        self.assertEqual(d1_verifier.tile_errors([(0, 0, 3), (1, 0, 2), (2, 0, 4)], ref, 0, 9), [])
        self.assertTrue(d1_verifier.tile_errors([(0, 0, 2), (1, 0, 2), (2, 0, 4)], ref, 0, 9)[0].startswith("SEGMENT_GAP"))
        self.assertTrue(d1_verifier.tile_errors([(0, 0, 3), (0, 0, 3), (1, 0, 2)], ref, 0, 9)[0].startswith("SEGMENT_OVERLAP"))
        self.assertTrue(d1_verifier.tile_errors([(0, 0, 3), (1, 0, 2)], ref, 0, 9)[0].startswith("SEGMENT_UNCOVERED"))
        self.assertTrue(d1_verifier.tile_errors([(0, 0, 3), (2, 0, 4)], ref, 0, 9)[0].startswith("SEGMENT_GAP"))


class Static(unittest.TestCase):
    def imports(self, name):
        tree = ast.parse((D1 / name).read_text())
        mods = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                mods |= {a.name.split(".")[0] for a in n.names}
            elif isinstance(n, ast.ImportFrom):
                mods.add((n.module or "").split(".")[0])
        return mods

    def test_reader_verifier_driver_are_independent(self):
        for f, forbidden in (("d1_reader.py", {"d1_verifier", "d1_driver", "d1_selftest_data"}),
                             ("d1_verifier.py", {"d1_reader", "d1_driver", "d1_selftest_data"}),
                             ("d1_driver.py", {"d1_reader", "d1_verifier", "d1_selftest_data"})):
            self.assertFalse(self.imports(f) & forbidden, f)

    def test_only_stdlib_and_the_two_pinned_libraries(self):
        allowed = set(sys.stdlib_module_names) | {"pyarrow", "tokenizers"}
        for f in ("d1_reader.py", "d1_verifier.py", "d1_driver.py", "d1_env_manifest.py", "d1_selftest_data.py"):
            self.assertLessEqual(self.imports(f) - {""}, allowed, f)

    def test_no_gpu_or_torch(self):
        for f in D1.glob("*.py"):
            text = f.read_text()
            self.assertNotIn("import torch", text, f.name)
            self.assertNotIn("from torch", text, f.name)
            low = text.lower().replace("cuda_visible_devices", "")
            self.assertNotIn("cuda", low, f.name)

    def test_config_is_valid_and_matches_frozen_numbers(self):
        c = jread(CFG)
        self.assertEqual(c["dataset"]["revision"], "b08601e04326c79dfdd32d625aee71d232d685c3")
        self.assertEqual((c["window"]["window_rows"], c["window"]["seq_len"], c["window"]["block_len"]), (2048, 64, 65))
        self.assertEqual(sorted(c["negatives"]["LR"]), ["LR%d" % i for i in range(1, 10)])
        self.assertEqual(c["negatives"]["CR"]["CR3"]["delta"], 1)
        self.assertEqual(c["schedule"]["p2"]["search_ordinals"], [600, 900])
        self.assertEqual(c["schedule"]["p2"]["min_row_len"], 3)


def real_mode_pins_match():
    try:
        import importlib.metadata as md
        env = jread(CFG)["environment"]
        return ("%d.%d.%d" % sys.version_info[:3] == env["python_full_version"]
                and md.version("tokenizers") == env["pins"]["tokenizers"] and md.version("pyarrow") == env["pins"]["pyarrow"])
    except Exception:  # noqa: BLE001
        return False


@unittest.skipUnless(importlib.util.find_spec("pyarrow") and importlib.util.find_spec("tokenizers") and real_mode_pins_match(),
                     "pyarrow/tokenizers/python do not match the frozen pins (real mode is BLOCKED by design)")
class RealModeCodePath(unittest.TestCase):
    """Exercises the parquet + native `tokenizers` code path with a HAND-BUILT, UNTRAINED
    byte-level tokenizer (no fitting) on the synthetic rows. Code self-test only."""

    def test_real_mode_pipeline(self):
        import pyarrow as pa
        import pyarrow.parquet as pq
        from tokenizers import AddedToken, Tokenizer, decoders, models, normalizers, pre_tokenizers
        tmp = tempfile.mkdtemp(prefix="d1real_")
        try:
            src, _, _ = d1_selftest_data.build(tmp)
            texts = [json.loads(line)["text"] for line in lines_of(src)]
            pq_path = tmp + "/train.parquet"
            pq.write_table(pa.table({"text": texts}), pq_path)
            vocab = {"<|pad|>": 0, "<|bos|>": 1, "<|eos|>": 2}
            for i, ch in enumerate(sorted(pre_tokenizers.ByteLevel.alphabet())):
                vocab[ch] = 3 + i
            tk = Tokenizer(models.BPE(vocab=vocab, merges=[]))
            tk.normalizer = normalizers.NFC()
            tk.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False, use_regex=True)
            tk.decoder = decoders.ByteLevel()
            tk.add_special_tokens([AddedToken(s, special=True, normalized=False) for s in ("<|pad|>", "<|bos|>", "<|eos|>")])
            tok_path = tmp + "/tokenizer.json"
            tk.save(tok_path)
            sha = sha_file
            man = tmp + "/manifest.json"
            write_text(man, json.dumps({"parquet_sha256": sha(pq_path), "tokenizer_sha256": sha(tok_path),
                                        "actual_vocab_size": tk.get_vocab_size()}))
            r = run_py(D1 / "d1_driver.py", "all", "--workdir", tmp + "/w", "--mode", "real", "--config", CFG, "--manifest", man,
                       "--source", "parquet:" + pq_path, "--tokenizer", tok_path)
            self.assertEqual(r.returncode, 0, r.stdout[-1500:] + r.stderr[-800:])
            dec = jread(tmp + "/w/evidence/D1_DECISION_all.json")
            self.assertEqual(dec["read_resume"]["verdict"], "PASS")
            self.assertEqual(dec["negatives_meta"]["verdict"], "PASS")
            self.assertEqual(dec["identity"], "REAL_CODE_PATH_NON_FORMAL")   # synthetic Parquet + hand-built BPE
            self.assertFalse(dec["d1_formal_experiment"])
        finally:
            writable(tmp)
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
