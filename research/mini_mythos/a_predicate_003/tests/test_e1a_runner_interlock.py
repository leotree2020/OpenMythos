"""Runner interlock tests (pure; no process is started).  WRITTEN, NOT RUN.
The detailed per-phase authorization matrix lives in test_e1a_staticfix.py (TestFix4Phases)."""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "bench"))
import e1a_runner as RUN    # noqa: E402
import scenarios as S       # noqa: E402

PREREG, SHA = S.load_prereg()


class TestInterlock(unittest.TestCase):
    def test_missing_file_is_refused(self):
        with self.assertRaises(RUN.AuthorizationError):
            RUN.load_authorization("/nonexistent/auth.json", SHA, "c" * 64)

    def test_execute_without_default_authorization_file_returns_2(self):
        self.assertFalse(os.path.exists(RUN.AUTH_DEFAULT))
        self.assertEqual(RUN.main(["--execute"]), 2)
        self.assertEqual(RUN.main(["--execute", "--phase", "bv", "--bv", "BV-7"]), 2)

    def test_static_checks_are_clean(self):
        self.assertEqual(RUN.static_checks(PREREG, SHA), [])

    def test_bench_code_hash_is_stable_within_a_process(self):
        self.assertEqual(RUN.bench_code_hash(), RUN.bench_code_hash())


if __name__ == "__main__":
    unittest.main(verbosity=2)
