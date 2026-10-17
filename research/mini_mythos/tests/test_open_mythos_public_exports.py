"""Minimal offline smoke test for the OpenMythos public export contract.
All imports must succeed without downloading tokenizer weights,
network datasets, GPU allocations, or executing training.
"""
import unittest

import open_mythos
from open_mythos import *  # noqa: F401,F403 - star import is the tested API
from open_mythos.main import OpenMythos as MainOpenMythos
from open_mythos.tokenizer import MythosTokenizer as ModuleTokenizer


class PublicExportsTests(unittest.TestCase):
    def test_all_exports_resolve_to_real_bindings(self):
        exported = open_mythos.__all__
        self.assertTrue(exported)
        self.assertEqual(len(exported), len(set(exported)))
        for symbol in exported:
            with self.subTest(symbol=symbol):
                self.assertTrue(
                    hasattr(open_mythos, symbol),
                    f"__all__ references unbound public name {symbol}"
                )
                self.assertIsNotNone(getattr(open_mythos, symbol))

    def test_star_import_uses_actual_model_and_tokenizer_classes(self):
        self.assertIs(OpenMythos, MainOpenMythos)
        self.assertIs(MythosTokenizer, ModuleTokenizer)
        self.assertIs(OpenMythos, open_mythos.OpenMythos)
        self.assertIs(MythosTokenizer, open_mythos.MythosTokenizer)

    def test_no_phantom_helpers_in_public_star_import(self):
        # These have no implementation in current package or tokenizer.
        # Do not invent function semantics or hidden network calls.
        self.assertNotIn("load_tokenizer", open_mythos.__all__)
        self.assertNotIn("get_vocab_size", open_mythos.__all__)


if __name__ == "__main__":
    unittest.main()
