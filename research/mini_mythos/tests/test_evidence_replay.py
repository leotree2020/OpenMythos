"""Offline tests for ACT-003 replay comparison and fail-closed provenance."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from evidence_archive import SOURCES, sha256_file, package_version
from evidence_replay import compare_case, guard_environment


class EvidenceReplayTests(unittest.TestCase):
    def fixture(self):
        held = {
            "heldout_batches": 3,
            "original_weights_original_act": 2.0,
            "original_weights_forced_act": 2.01,
            "forced_weights_original_act": 2.02,
            "forced_weights_forced_act": 2.03,
            "total_deployed_delta": 0.03,
            "direct_mechanism_same_original_weights_delta": .01,
            "parameter_history_under_original_act_delta": .02,
            "policy_parameter_interaction_delta": .0,
        }
        return {
            "experiment": "ACT-002_same_weight_counterfactual",
            "seed": 22, "steps": 30, "lr": .003, "device": "cpu",
            "results": [{
                "attention": "mla", "requested_depth": 2,
                "events": {"first_original_mass_deficit_step": None},
                "train_trace": [{"step": 1}, {"step": 2}],
                "heldout": held,
            }],
        }

    def test_exact_match(self):
        import copy
        reference = self.fixture()
        self.assertEqual(compare_case(reference, copy.deepcopy(reference)), [])

    def test_tolerance_allows_small_numeric_drift(self):
        import copy
        reference = self.fixture()
        replay = copy.deepcopy(reference)
        replay["results"][0]["heldout"]["forced_weights_forced_act"] += .00001
        self.assertEqual(compare_case(reference, replay), [])

    def test_event_disagreement_detected(self):
        import copy
        reference = self.fixture()
        replay = copy.deepcopy(reference)
        replay["results"][0]["events"]["first_original_mass_deficit_step"] = 2
        self.assertTrue(any("first-event" in d for d in compare_case(reference, replay)))

    def test_large_heldout_difference_detected(self):
        import copy
        reference = self.fixture()
        replay = copy.deepcopy(reference)
        replay["results"][0]["heldout"]["total_deployed_delta"] += .1
        self.assertTrue(any("heldout" in d for d in compare_case(reference, replay)))

    def test_provenance_drift_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            source_hashes = {}
            for name in SOURCES:
                path = repo / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("fixture", encoding="utf-8")
                source_hashes[name] = sha256_file(path)
            manifest = {"snapshot": {
                "python": sys.version.split()[0],
                "torch_distribution": package_version("torch"),
                "source_sha256_at_pack_time": source_hashes,
            }}
            self.assertEqual(guard_environment(manifest, repo), ([], []))
            changed = repo / SOURCES[0]
            changed.write_text("modified", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Code differs"):
                guard_environment(manifest, repo)
            drift, env = guard_environment(manifest, repo, allow_source_drift=True)
            self.assertEqual(drift, [SOURCES[0]])
            self.assertEqual(env, [])


if __name__ == "__main__":
    unittest.main()
