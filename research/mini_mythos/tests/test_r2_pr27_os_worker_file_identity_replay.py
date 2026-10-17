"""Gate P: offline 14 real-path-shape local replay, with real OS workers.

No online HF, no Parquet access, no content, no GPU or model training.
The CLI source paths are REAL immutable Gate O evidence. Tests use only
synthetic filenames of the same format and strict provenance invariants.
"""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import r2_pr27_os_worker_file_identity_replay as gate
import r2_pr27_live_hf_shard_metadata as n_gate
import r2_pr27_real_hf_file_shard_mapping as o_gate
from r2_pr27_remote_parquet_inventory import canonical_digest, contiguous_indices


def fake_names():
    return [f"sample/10BT/{i:03d}_00000.parquet" for i in range(14)]


class ArrowExamplesIterable:
    def __init__(self, names):
        self.kwargs = {
            "files": list(names),
            "row_groups_list": [None] * len(names),
        }

ArrowExamplesIterable.__module__ = "datasets.iterable_dataset"


class LocalMetadataFake:
    """No I/O; mimic only the official metadata operations under audit."""
    def __init__(self, names):
        self.names = list(names)
        self.num_shards = len(names)
        self._ex_iterable = ArrowExamplesIterable(names)

    def __iter__(self):
        raise AssertionError("Gate P test fake must never iterate source")

    def shard(self, *, num_shards, index, contiguous=True):
        if contiguous:
            chosen = [self.names[i] for i in contiguous_indices(
                len(self.names), index
            )]
        else:
            chosen = self.names[index::num_shards]
        return LocalMetadataFake(chosen)


def fake_prior_evidence(names):
    versions = {
        "python": "3.14.2", "datasets": "5.1.0", "torch": "2.14.1",
        "huggingface_hub": "2.2.0", "pyarrow": "26.0.0",
    }
    # Synthetic test manifests have the independent Gate M SHA as an
    # externally required, known constant: source body remains synthetic.
    m = {
        "file_inventory_sha256": gate.SOURCE_FILE_INVENTORY_SHA256,
        "file_metadata": [
            {"path": path, "size": i + 1000} for i, path in enumerate(names)
        ],
    }
    n = n_gate.build_report(
        LocalMetadataFake(names), source_sha=gate.SOURCE_REVISION,
        file_count=14,
        file_inventory_sha=gate.SOURCE_FILE_INVENTORY_SHA256,
        versions=versions
    )
    o = o_gate.build_report(
        LocalMetadataFake(names), gate_m=m, gate_n=n, versions=versions
    )
    return m, n, o, versions


def fake_mode_rows(names, mode):
    expected = gate.expected_identity_paths(names, mode)
    before = 14 if mode == "native_once" else 7
    return [
        {"source_file_id": path, "worker_id": wid,
         "num_shards_before_auto": before}
        for wid in (0,1)
        for path in expected[str(wid)]
    ]


class GatePTests(unittest.TestCase):
    def setUp(self):
        self.names = fake_names()
        self.pids = {"0": 101, "1": 102}

    def test_identity_source_has_exactly_14_one_row_arrow_shards(self):
        ds = gate.source_from_frozen_paths(self.names)
        self.assertEqual(ds.num_shards, 14)
        data = list(ds)  # These are SYNTHETIC PATH IDs only, never Parquet.
        self.assertEqual([r["source_file_id"] for r in data], self.names)
        self.assertTrue(all(set(r) == {"source_file_id"} for r in data))

    def test_identity_source_rejects_foreign_duplicate_or_wrong_count(self):
        with self.assertRaisesRegex(ValueError, "14"):
            gate.source_from_frozen_paths(self.names[:-1])
        bad = self.names[:]
        bad[3] = bad[2]
        with self.assertRaisesRegex(ValueError, "duplicate"):
            gate.source_from_frozen_paths(bad)
        bad = self.names[:]
        bad[3] = "http://evil.example/not-fineweb"
        with self.assertRaises(ValueError):
            gate.source_from_frozen_paths(bad)

    def test_worker_projection_uses_actual_hf_source_order(self):
        order = list(reversed(self.names))
        self.assertEqual(
            gate.expected_identity_paths(order, "native_once")["1"], order[1::2]
        )
        self.assertEqual(
            gate.expected_identity_paths(order, "explicit_twice")["0"],
            [order[i] for i in (0,2,4,6)]
        )
        self.assertEqual(
            gate.expected_identity_paths(order, "explicit_twice")["1"],
            [order[i] for i in (8,10,12)]
        )
        with self.assertRaisesRegex(ValueError, "Invalid mode"):
            gate.expected_identity_paths(order, "unsupported")

    def test_summaries_preserve_14_and_7_exact_source_id_coverage(self):
        good = gate.summarize_worker_rows(
            self.names, "native_once",
            fake_mode_rows(self.names, "native_once"), self.pids
        )
        bad = gate.summarize_worker_rows(
            self.names, "explicit_twice",
            fake_mode_rows(self.names, "explicit_twice"), self.pids
        )
        self.assertTrue(good["covers_source_file_ids_once"])
        self.assertFalse(bad["covers_source_file_ids_once"])
        self.assertEqual(good["covered_source_file_identifiers"], 14)
        self.assertEqual(bad["covered_source_file_identifiers"], 7)
        self.assertEqual(
            bad["missing_source_file_identifiers"], self.names[1::2]
        )
        self.assertFalse(bad["original_remote_parquet_read"])
        self.assertFalse(good["real_original_pr27_worker_execution"])

    def test_unknown_duplicate_or_foreign_worker_records_rejected(self):
        records = fake_mode_rows(self.names, "native_once")
        records[0]["source_file_id"] = records[1]["source_file_id"]
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            gate.summarize_worker_rows(self.names, "native_once", records, self.pids)
        records = fake_mode_rows(self.names, "native_once")
        records[0]["source_file_id"] = "sample/10BT/999_00000.parquet"
        with self.assertRaisesRegex(ValueError, "foreign"):
            gate.summarize_worker_rows(self.names, "native_once", records, self.pids)
        records = fake_mode_rows(self.names, "native_once")
        records[0]["num_shards_before_auto"] = 7
        with self.assertRaisesRegex(ValueError, "before auto"):
            gate.summarize_worker_rows(self.names, "native_once", records, self.pids)

    def test_worker_pid_and_missing_worker_cannot_be_forged(self):
        records = fake_mode_rows(self.names, "native_once")
        with self.assertRaisesRegex(ValueError, "PID"):
            gate.summarize_worker_rows(
                self.names, "native_once", records, {"0":99,"1":99}
            )
        records[0]["worker_id"] = 2
        with self.assertRaisesRegex(ValueError, "Unknown worker"):
            gate.summarize_worker_rows(self.names, "native_once", records, self.pids)
        with self.assertRaisesRegex(ValueError, "Incorrect number"):
            gate.summarize_worker_rows(
                self.names, "native_once", records[:-1], self.pids
            )

    def test_offline_manifest_verification_and_scope_guards(self):
        m,n,o,versions = fake_prior_evidence(self.names)
        a = gate.summarize_worker_rows(
            self.names, "native_once",
            fake_mode_rows(self.names, "native_once"), self.pids
        )
        b = gate.summarize_worker_rows(
            self.names, "explicit_twice",
            fake_mode_rows(self.names, "explicit_twice"), {"0":103,"1":104}
        )
        payload = {
            "protocol": gate.PROTOCOL,
            "source_dataset": o["source_dataset"],
            "dataset_config": o["config"],
            "source_revision": gate.SOURCE_REVISION,
            "real_fineweb_snapshot_sha256": gate.SOURCE_SNAPSHOT_SHA256,
            "gate_m_inventory_sha256": gate.SOURCE_FILE_INVENTORY_SHA256,
            "gate_n_report_sha256": n["report_sha256"],
            "gate_o_report_sha256": o["report_sha256"],
            "real_hf_source_order": self.names,
            "real_file_identity_count": 14,
            "local_one_id_per_arrow_shard": True,
            "real_os_workers_per_mode": 2,
            "native_hf_auto_once": a,
            "manual_plus_native_hf_auto": b,
            "datasets_version": "5.1.0",
            "package_versions": versions,
            "research_git_commit": "synthetic",
            "no_source_text_sent_to_workers": True,
            "no_remote_parquet_rows_read": True,
            "model_training_performed": False,
            "gpu_training_performed": False,
            "original_pr27_dataloader_executed": False,
            "limits": "synthetic source-id only",
        }
        report = dict(payload, report_sha256=canonical_digest(payload))
        self.assertEqual(
            gate.verify_report(report,gate_m=m,gate_n=n,gate_o=o),report
        )
        with tempfile.TemporaryDirectory() as td:
            file = Path(td)/"gate-p.json"
            file.write_text(json.dumps(report),encoding="utf-8")
            self.assertEqual(
                gate.verify_report(json.loads(file.read_text()),
                                   gate_m=m,gate_n=n,gate_o=o),report
            )
        tampered = copy.deepcopy(report)
        tampered["real_fineweb_snapshot_sha256"] = "a" * 64
        tampered["report_sha256"] = canonical_digest({
            k:v for k,v in tampered.items() if k!="report_sha256"
        })
        with self.assertRaisesRegex(ValueError, "snapshot SHA mismatch"):
            gate.verify_report(tampered,gate_m=m,gate_n=n,gate_o=o)
        tampered = copy.deepcopy(report)
        tampered["no_remote_parquet_rows_read"] = False
        tampered["report_sha256"] = canonical_digest({
            k:v for k,v in tampered.items() if k!="report_sha256"
        })
        with self.assertRaisesRegex(ValueError, "scope overstated"):
            gate.verify_report(tampered,gate_m=m,gate_n=n,gate_o=o)
        tampered = copy.deepcopy(report)
        tampered["manual_plus_native_hf_auto"]["per_worker_counts"]["0"]=1
        tampered["report_sha256"] = canonical_digest({
            k:v for k,v in tampered.items() if k!="report_sha256"
        })
        with self.assertRaisesRegex(ValueError, "coverage digest or schema"):
            gate.verify_report(tampered,gate_m=m,gate_n=n,gate_o=o)

    @unittest.skipUnless(sys.platform=="linux", "Two OS workers require Linux Codespaces")
    def test_two_true_os_workers_replay_fourteen_real_path_shaped_ids(self):
        source=gate.source_from_frozen_paths(self.names)
        for mode in gate.MODES:
            rows,pids=gate.collect(source,mode)
            report=gate.summarize_worker_rows(self.names,mode,rows,pids)
            self.assertEqual(set(pids),{"0","1"})
            self.assertNotEqual(pids["0"],pids["1"])
            self.assertEqual(
                report["covered_source_file_identifiers"],
                14 if mode=="native_once" else 7
            )


if __name__=="__main__":
    unittest.main()
