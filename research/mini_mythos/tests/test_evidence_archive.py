"""Offline tests of ACT evidence ZIP integrity and allowlist policy."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from evidence_archive import (
    REQUIRED, SOURCES, pack, selected_artifacts, verify_archive,
)


class EvidenceArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name) / "repository"
        self.repo.mkdir()
        for name in SOURCES:
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# fixture for " + name, encoding="utf-8")
        self.results = self.repo / "research/mini_mythos/results"
        self.results.mkdir(parents=True)

    def payload(self, name):
        if name in ("act_gqa.json", "act_mla.json"):
            return {
                "attention": name.split("_")[1].removesuffix(".json"),
                "depth_results": [{"requested_depth": 1, "original_mass_mean": .5}],
                "upstream_commit": "fixturecommit",
            }
        if name.startswith("act002_"):
            attn = name.split("_")[1]
            seed = int(name.split("seed")[1].split(".")[0])
            return {
                "experiment": "ACT-002_same_weight_counterfactual",
                "seed": seed, "steps": 30, "lr": .003,
                "upstream_commit": "fixturecommit",
                "results": [{
                    "attention": attn, "requested_depth": 2,
                    "events": {"first_original_mass_deficit_step": None},
                    "train_trace": [{"step": 1}],
                    "heldout": {"original_weights_original_act": 2.0,
                                "forced_weights_forced_act": 2.1},
                }],
            }
        if name.startswith("multiseed/"):
            seed = int(name.split("_seed_")[1].split(".")[0])
            return {
                "experiment": "act_final_remainder_ab",
                "seed": seed, "upstream_commit": "fixturecommit",
                "results": [
                    {"attention": attn, "requested_depth": d}
                    for attn in ("gqa", "mla") for d in (1, 2)
                ],
            }
        return {"upstream_commit": "fixturecommit"}

    def write(self, name, value=None):
        path = self.results / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(
            self.payload(name) if value is None else value), encoding="utf-8")
        return path

    def full_results(self):
        for name in REQUIRED:
            self.write(name)

    def test_full_archive_roundtrip_and_manifest(self):
        self.full_results()
        target = self.repo / "research/mini_mythos/archives/fixture.zip"
        manifest = pack(self.repo, target)
        self.assertEqual(manifest["completeness"], "complete")
        self.assertEqual(len(manifest["artifacts"]), len(REQUIRED))
        found = verify_archive(target)
        self.assertEqual(found["snapshot"]["source_sha256_at_pack_time"].keys(),
                         manifest["snapshot"]["source_sha256_at_pack_time"].keys())
        self.assertTrue(all(len(x["sha256"]) == 64 for x in found["artifacts"]))

    def test_missing_required_fails_closed(self):
        self.write("act_gqa.json")
        with self.assertRaises(FileNotFoundError):
            pack(self.repo, self.repo / "out.zip")
        self.assertFalse((self.repo / "out.zip").exists())

    def test_allow_partial_must_be_explicit(self):
        self.write("act_gqa.json")
        path = self.repo / "out.zip"
        manifest = pack(self.repo, path, allow_partial=True)
        self.assertEqual(manifest["completeness"], "partial")
        self.assertEqual(len(manifest["artifacts"]), 1)
        self.assertEqual(verify_archive(path)["completeness"], "partial")

    def test_zip_hash_tamper_detected(self):
        self.full_results()
        path = self.repo / "source.zip"
        pack(self.repo, path)
        altered = self.repo / "corrupted.zip"
        with ZipFile(path) as original, ZipFile(altered, "w", compression=ZIP_DEFLATED) as dest:
            for name in original.namelist():
                raw = original.read(name)
                if name == "results/act_gqa.json":
                    raw += b" "
                dest.writestr(name, raw)
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            verify_archive(altered)

    def test_zip_extra_path_rejected(self):
        self.full_results()
        path = self.repo / "source.zip"
        pack(self.repo, path)
        altered = self.repo / "extra.zip"
        with ZipFile(path) as original, ZipFile(altered, "w", compression=ZIP_DEFLATED) as dest:
            for name in original.namelist():
                dest.writestr(name, original.read(name))
            dest.writestr("../malicious", b"no")
        with self.assertRaisesRegex(ValueError, "unsafe"):
            verify_archive(altered)

    def test_invalid_result_identity_is_rejected(self):
        self.full_results()
        self.write("act002_mla_seed44.json", {
            "experiment": "ACT-002_same_weight_counterfactual",
            "seed": 22,
            "results": [{"attention": "mla", "requested_depth": 2,
                         "train_trace": [], "heldout": {}}],
        })
        with self.assertRaisesRegex(ValueError, "identity"):
            selected_artifacts(self.repo)

    def test_unlisted_json_not_collected(self):
        self.full_results()
        self.write("private/secret.json", {"password": "never archive this"})
        path = self.repo / "evidence.zip"
        pack(self.repo, path)
        with ZipFile(path) as z:
            self.assertFalse(any("secret" in name for name in z.namelist()))

    def test_reject_symlink_result(self):
        self.full_results()
        replace = self.results / "act_gqa.json"
        replace.unlink()
        try:
            replace.symlink_to(self.results / "act_mla.json")
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks not supported")
        with self.assertRaises(ValueError):
            selected_artifacts(self.repo)


if __name__ == "__main__":
    unittest.main()
