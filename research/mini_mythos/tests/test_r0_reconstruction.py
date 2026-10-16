"""Unit tests for the R0 static audit and safe CPU checkpoint probe."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from r0_audit import RULES, audit_sources, locate
from r0_probe import checkpoint_roundtrip
from common import load_upstream, get_repo


class R0AuditTests(unittest.TestCase):
    def test_locate_first_matching_line(self):
        self.assertEqual(locate("a\nb\nclass Foo:\n", r"^class Foo:"), 3)
        self.assertIsNone(locate("a\nb\n", r"^class Foo:"))

    def test_static_audit_report_is_complete(self):
        sources = {path: "" for path in {rule[1] for rule in RULES}}
        result = audit_sources(sources)
        self.assertEqual(len(result), len(RULES))
        self.assertEqual(len({entry["id"] for entry in result}), len(RULES))
        self.assertTrue(all(row["line"] is None for row in result))

    def test_missing_heldout_is_gap_not_model_failure(self):
        sources = {path: "" for path in {rule[1] for rule in RULES}}
        report = {r["id"]: r for r in audit_sources(sources)}
        self.assertEqual(report["EVAL_HOLDOUT"]["status"], "GAP")
        self.assertEqual(report["RDT_STRUCTURE"]["status"], "MISSING")
        self.assertIn("static regex", report["EVAL_HOLDOUT"]["method"])

    def test_detect_model_and_checkpoint_tokens(self):
        sources = {path: "" for path in {rule[1] for rule in RULES}}
        sources["open_mythos/main.py"] = "class RecurrentBlock(nn.Module):\n pass\n"
        sources["training/3b_fine_web_edu.py"] = 'x = {"model": model_state, "optimizer": optim_state}\n'
        report = {r["id"]: r for r in audit_sources(sources)}
        self.assertEqual(report["RDT_STRUCTURE"]["status"], "PRESENT")
        self.assertEqual(report["CHECKPOINT_MODEL_OPT"]["status"], "PRESENT")

    def test_actual_tiny_gqa_checkpoint_resume(self):
        root = get_repo(".")
        module = load_upstream(root)
        result = checkpoint_roundtrip(module, "gqa")
        self.assertEqual(result["status"], "PASS", result)


if __name__ == "__main__":
    unittest.main()
