"""Read-only maintenance AST audit: no imports/execution of inspected files."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from maintenance_ast_audit import scan


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for name in ("open_mythos", "training", "research/mini_mythos/scripts",
                     "research/mini_mythos/tests"):
            (self.root / name).mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, path, text):
        dst = self.root / path
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(text, encoding="utf-8")
        return dst

    def test_no_execution_even_if_module_would_crash_at_import(self):
        self.write("open_mythos/mod.py", """
raise RuntimeError("DO NOT EXECUTE DURING AST AUDIT")
def public_fn():
    return True
def _private_not_called():
    return 0
""")
        report = scan(self.root)
        self.assertEqual(report["summary"]["python_files"], 1)
        self.assertEqual(report["summary"]["functions_and_methods"], 2)
        self.assertEqual(
            [x["qualname"] for x in report["potential_unreferenced_private"]],
            ["_private_not_called"]
        )
        self.assertEqual(report["protocol"],
                         "MYTHOS_READ_ONLY_AST_MAINTENANCE_AUDIT_V1")

    def test_nested_functions_and_long_control_paths_are_reported(self):
        self.write("training/pipeline.py", """
def main():
    def inner():
        if True:
            for x in range(3):
                while False:
                    pass
        return 10
    return inner()
""")
        report = scan(self.root)
        funcs = {f["qualname"]: f for f in report["complexity_hotspots"]}
        self.assertEqual(report["summary"]["nested_function_definitions"], 1)
        self.assertIn("main.inner", funcs)
        self.assertEqual(funcs["main.inner"]["lexical_parent"], "function")
        self.assertGreaterEqual(funcs["main.inner"]["max_control_nesting"], 3)
        self.assertGreaterEqual(funcs["main.inner"]["complexity_approx"], 4)
        # Parent function must NOT absorb inner function's branches.
        parent = next(x for x in report["top_20_by_complexity"]
                      if x["qualname"] == "main")
        self.assertEqual(parent["complexity_approx"], 1)

    def test_detects_broken_exports_and_untrusted_checkpoint(self):
        self.write("open_mythos/__init__.py",
                   "__all__ = ['hello', 'missing']\ndef hello():\n    pass\n")
        self.write("training/model.py", """
import torch
def load(path):
    return torch.load(path, weights_only=False)
""")
        report = scan(self.root)
        self.assertEqual(report["missing_exports"], [
            {"file": "open_mythos/__init__.py",
             "symbol": "missing", "finding": "__all__ missing binding"}
        ])
        self.assertTrue(any(x["kind"] == "torch.load_weights_only_false"
                            and x["file"] == "training/model.py"
                            for x in report["review_patterns"]))

    def test_flags_hf_manual_inside_worker_and_floating_revision(self):
        self.write("training/data.py", """
from datasets import load_dataset
class Source:
    def __iter__(self):
        source = load_dataset("fake", streaming=True).shard(
            num_shards=2, index=0
        )
        for item in source:
            yield item
""")
        report = scan(self.root)
        kinds = {x["kind"] for x in report["review_patterns"]}
        self.assertIn("hf_load_dataset_unpinned_revision", kinds)
        self.assertIn("hf_manual_shard_inside_iter", kinds)

    def test_public_functions_not_falsely_marked_dead(self):
        self.write("open_mythos/api.py", """
def public_extension_point():
    return "loaded only via importlib"
def _helper():
    return 1
def call_helper():
    return _helper()
""")
        report = scan(self.root)
        self.assertEqual(report["potential_unreferenced_private"], [])


if __name__ == "__main__":
    unittest.main()
