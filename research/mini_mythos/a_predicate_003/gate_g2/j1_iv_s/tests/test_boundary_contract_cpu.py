"""CPU-only source-transcribed boundary observations; not formal acceptance."""
import unittest

from j1_iv_s.boundary_contract import compare_field, review_provisional_size


class RegexBoundaryCases(unittest.TestCase):
    def test_token_normal_matches_both(self):
        self.assertEqual(compare_field("token", "hL").result, "AGREE_ACCEPT")

    def test_token_trailing_newline_exposes_difference(self):
        x = compare_field("token", "hL\n")
        self.assertTrue(x.j1_schema_accepts)
        self.assertFalse(x.independent_ivs_accepts)

    def test_token_embedded_newline_rejected_by_both(self):
        self.assertEqual(compare_field("token", "h\nL").result, "AGREE_REJECT")

    def test_token_invalid_character_rejected_by_both(self):
        self.assertEqual(compare_field("token", "h L").result, "AGREE_REJECT")

    def test_token_64_character_boundary(self):
        self.assertEqual(compare_field("token", "a" * 64).result, "AGREE_ACCEPT")

    def test_token_65_character_boundary(self):
        self.assertEqual(compare_field("token", "a" * 65).result, "AGREE_REJECT")

    def test_token_non_string_rejected_by_both(self):
        self.assertEqual(compare_field("token", 1).result, "AGREE_REJECT")

    def test_hex_normal_matches_both(self):
        self.assertEqual(compare_field("hex64", "a" * 64).result, "AGREE_ACCEPT")

    def test_hex_trailing_newline_exposes_difference(self):
        x = compare_field("hex64", "a" * 64 + "\n")
        self.assertEqual(x.result, "J1_ACCEPTS_IVS_REJECTS_UNRESOLVED")

    def test_hex_63_rejected_both(self):
        self.assertEqual(compare_field("hex64", "a" * 63).result, "AGREE_REJECT")

    def test_hex_uppercase_rejected_both(self):
        self.assertEqual(compare_field("hex64", "A" * 64).result, "AGREE_REJECT")

    def test_errno_normal_accepts_both(self):
        self.assertEqual(compare_field("errno", "EPIPE").result, "AGREE_ACCEPT")

    def test_errno_trailing_newline_exposes_difference(self):
        x = compare_field("errno", "EPIPE\n")
        self.assertEqual(x.result, "J1_ACCEPTS_IVS_REJECTS_UNRESOLVED")

    def test_errno_none_accepted_both(self):
        self.assertEqual(compare_field("errno", None).result, "AGREE_ACCEPT")

    def test_errno_invalid_rejected_both(self):
        self.assertEqual(compare_field("errno", "PIPE").result, "AGREE_REJECT")


class NfcBoundaryCases(unittest.TestCase):
    def test_ascii_accepted_both(self):
        self.assertEqual(compare_field("string_nfc", "abc").result, "AGREE_ACCEPT")

    def test_composed_unicode_accepted_both(self):
        self.assertEqual(compare_field("string_nfc", "é").result, "AGREE_ACCEPT")

    def test_decomposed_unicode_exposes_difference(self):
        self.assertEqual(compare_field("string_nfc", "e\u0301").result,
                         "J1_ACCEPTS_IVS_REJECTS_UNRESOLVED")

    def test_overlength_rejected_both(self):
        self.assertEqual(compare_field("string_nfc", "x" * 257).result, "AGREE_REJECT")

    def test_surrogate_log_rejected_both(self):
        self.assertEqual(compare_field("log_utf8_nfc", "\ud800").result, "AGREE_REJECT")

    def test_decomposed_log_exposes_difference(self):
        self.assertEqual(compare_field("log_utf8_nfc", "e\u0301").result,
                         "J1_ACCEPTS_IVS_REJECTS_UNRESOLVED")

    def test_unknown_field_kind_rejected(self):
        with self.assertRaisesRegex(ValueError, "UNKNOWN_FIELD_KIND"):
            compare_field("RUN_REAL", "x")


class BudgetBoundaryCases(unittest.TestCase):
    def test_under_cap_is_provisional_only(self):
        x = review_provisional_size(7_999_999)
        self.assertEqual(x.result, "WITHIN_PROVISIONAL_RESOURCE_BUDGET")
        self.assertEqual(x.formal_input_validity, "NOT_DETERMINED")

    def test_at_cap_is_provisional_only(self):
        x = review_provisional_size(8_000_000)
        self.assertEqual(x.result, "WITHIN_PROVISIONAL_RESOURCE_BUDGET")

    def test_over_cap_is_blocked_not_invalid(self):
        x = review_provisional_size(8_000_001)
        self.assertEqual(x.result, "BLOCKED_RESOURCE_POLICY_UNFROZEN")
        self.assertEqual(x.formal_input_validity, "NOT_DETERMINED")

    def test_negative_measurement_is_unverifiable(self):
        self.assertEqual(review_provisional_size(-1).result, "MEASUREMENT_UNVERIFIABLE")

    def test_boolean_measurement_is_unverifiable(self):
        self.assertEqual(review_provisional_size(True).result, "MEASUREMENT_UNVERIFIABLE")


if __name__ == "__main__":
    unittest.main()
