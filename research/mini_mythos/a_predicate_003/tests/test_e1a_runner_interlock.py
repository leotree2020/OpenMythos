"""Runner interlock tests (pure; no process is started).  WRITTEN, NOT RUN."""
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "bench"))
import e1a_runner as RUN    # noqa: E402
import scenarios as S       # noqa: E402

PREREG, SHA = S.load_prereg()


class TestInterlock(unittest.TestCase):
    def write(self, d, **kw):
        a = {"authorization_id": "X", "authorized_by": "owner", "scope": "CPU-003 E1-A first controlled run", "prereg_sha256": SHA}
        a.update(kw)
        p = os.path.join(d, "auth.json")
        json.dump(a, open(p, "w"))
        return p

    def test_missing_file_is_refused(self):
        self.assertIsNotNone(RUN.check_authorization("/nonexistent/auth.json", SHA))

    def test_wrong_hash_or_incomplete_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(RUN.check_authorization(self.write(d), SHA))
            self.assertIsNotNone(RUN.check_authorization(self.write(d, prereg_sha256="0" * 64), SHA))
            self.assertIsNotNone(RUN.check_authorization(self.write(d, authorized_by="claude"), SHA))
            self.assertIsNotNone(RUN.check_authorization(self.write(d, scope="E2"), SHA))

    def test_execute_without_default_authorization_file_returns_2(self):
        self.assertFalse(os.path.exists(RUN.AUTH_DEFAULT))
        self.assertEqual(RUN.main(["--execute"]), 2)

    def test_static_checks_are_clean(self):
        self.assertEqual(RUN.static_checks(PREREG, SHA), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
