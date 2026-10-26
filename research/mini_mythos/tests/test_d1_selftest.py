"""Code self-tests for the D1 reader / verifier / driver (research/mini_mythos/gate3_d1).

SYNTHETIC DATA ONLY. No Parquet is downloaded, no tokenizer is fitted, no model is
built, no GPU is used. A pass here says the code behaves as designed on toy input;
it is NOT a D1 result. Real-mode tests run only when pyarrow and tokenizers are
installed (they are not needed for the stdlib self-test path).
"""
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
        self.assertFalse(dec["d1_experiment"])            # selftest is never a D1 experiment

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


class Blocked(unittest.TestCase):
    def test_p2_rule_without_candidate_row_is_blocked_schedule(self):
        tmp = tempfile.mkdtemp(prefix="d1blk_")
        try:
            src, tok, man = d1_selftest_data.build(tmp, "no_p2_row")
            r = run_py(D1 / "d1_driver.py", "clean", "--workdir", tmp + "/w", "--mode", "selftest", "--config", CFG,
                       "--manifest", man, "--source", "jsonl:" + src, "--tokenizer", tok)
            self.assertEqual(r.returncode, 1)
            dec = jread(tmp + "/w/evidence/D1_DECISION_clean.json")
            self.assertEqual(dec["read_resume"]["verdict"], "BLOCKED")
            self.assertIn("schedule", dec["read_resume"]["why"])
            self.assertFalse(os.path.exists(tmp + "/w/evidence/clean/A_trace.jsonl"))   # nothing was read
        finally:
            writable(tmp)
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


@unittest.skipUnless(importlib.util.find_spec("pyarrow") and importlib.util.find_spec("tokenizers"),
                     "pyarrow/tokenizers not installed")
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
        finally:
            writable(tmp)
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
