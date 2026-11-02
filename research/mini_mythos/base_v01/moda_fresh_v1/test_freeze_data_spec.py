"""Stdlib synthetic fixtures only; never target history/model/new source."""
import argparse
import gzip
import io
import json
from pathlib import Path
import sys
import tempfile
import tarfile
import unittest
from unittest import mock
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parent))
import freeze_data_spec as f


class SpecificationFixtures(unittest.TestCase):
    def test_complete_union_keeps_duplicate_payload_paths_and_external_prior(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/"history";root.mkdir();excluded=root/"new";excluded.mkdir()
            (root/"a.txt").write_text("same");(root/"b.txt").write_text("same")
            (excluded/"ignored.txt").write_text("new");(root/".git").mkdir();(root/".git"/"ignored").write_text("git")
            external=Path(tmp)/"old.txt";external.write_text("old")
            self.assertEqual(set(f.enumerate_union([root],{str(external):{}},excluded)),{str(root/"a.txt"),str(root/"b.txt"),str(external)})

    def test_missing_prior_stops(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with self.assertRaises(f.Stop):f.enumerate_union([root],{str(root/"missing"):{}},root/"new")

    def test_unknown_format_not_silently_nontext(self):
        with self.assertRaises(f.Stop):f.text_exception("unknown.pt",b"tensor")
        with self.assertRaises(f.Stop):f.text_exception("unknown.binary",b"text")

    def test_known_text_strict_decoding_and_raw_json(self):
        self.assertEqual(f.text_exception(".gitignore",b"*.pt")[0],"text")
        self.assertEqual(f.text_exception("run.started",b"")[0],"text")
        self.assertEqual(f.text_exception("ACQUISITION.json.raw",b'{"text":"kept"}')[0],"json")
        with self.assertRaises(UnicodeDecodeError):f.text_exception("run.sh",b"\xff")
        with self.assertRaises(Exception):f.text_exception("x.raw",b'{"x":1,"x":2}')

    def test_zip_unknown_text_member_is_pinned(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"old.zip"
            with zipfile.ZipFile(p,"w") as z:z.writestr("folder/.gitkeep",b"");z.writestr("data.json",b"{}")
            d={"container":{"format":"zip","members":[{"name":"folder/.gitkeep","bytes":0},{"name":"data.json","bytes":2}]}}
            policies=f.archive_policy(p,d,lambda p:None)
            self.assertEqual(list(policies),[str(p)+"!folder/.gitkeep"])
            self.assertEqual(policies[str(p)+"!folder/.gitkeep"]["kind"],"text")

    def test_unregistered_archive_checkpoint_stops(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"old.zip"
            with zipfile.ZipFile(p,"w") as z:z.writestr("weights.pt",b"1234")
            d={"container":{"format":"zip","members":[{"name":"weights.pt","bytes":4}]}}
            with self.assertRaises(f.Stop):f.archive_policy(p,d,lambda p:None)

    def test_gzip_tar_member_uses_decoded_virtual_name_and_exact_physical_pin(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/"old.tar.gz";physical=root/"m2_long_v1";physical.mkdir();(physical/"gpt_42_step120.pt").write_bytes(b"checkpoint")
            name="m2_long_v1/gpt_42_step120.pt";info=tarfile.TarInfo(name);info.size=10
            with tarfile.open(p,"w:gz") as z:z.addfile(info,io.BytesIO(b"checkpoint"))
            d={"container":{"format":"tar","members":[{"name":name,"bytes":10}]}}
            with mock.patch.object(f,"M2_ARCHIVE",str(p)),mock.patch.object(f,"M2_PHYSICAL",root):
                policies=f.archive_policy(p,d,f.pin)
                self.assertEqual(policies[str(p)[:-3]+"!"+name]["kind"],"nontext")
                with self.assertRaises(f.Stop):f.archive_policy(p,d,lambda p:{"bytes":10,"sha256":"0"*64})

    def test_archive_extra_member_stops(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"old.zip"
            with zipfile.ZipFile(p,"w") as z:z.writestr("data.json",b"{}");z.writestr("extra.json",b"{}")
            d={"container":{"format":"zip","members":[{"name":"data.json","bytes":2}]}}
            with self.assertRaises(f.Stop):f.archive_policy(p,d,lambda p:None)

    def test_serialization_compressed_complete_and_prior_referenced_not_copied(self):
        policy={"/history/weights.pt":{"bytes":10,"sha256":"1"*64,"reason":"known"}}
        result=f.serialize_outputs(policy,{}, {},{"Actual":{"suffixes":{".pt":1}}})
        self.assertEqual(json.loads(gzip.decompress(result["nontext_entries.json.gz"])),policy)
        spec=json.loads(result["DATA_SPEC.json"])
        self.assertEqual(spec["extra_history_inventory_path"],str(f.PRIOR))
        self.assertEqual(spec["extra_history_inventory_pin"],f.PRIOR_PIN)
        self.assertNotIn("extra_history_files",spec)
        self.assertEqual(spec["nontext_entries_pin"]["sha256"],f.sha(result["nontext_entries.json.gz"]))
        self.assertEqual(result,f.serialize_outputs(policy,{}, {},{"Actual":{"suffixes":{".pt":1}}}))

    def test_output_budget_and_no_overwrite(self):
        with mock.patch.object(f,"MAX_OUTPUT",100):
            with self.assertRaises(f.Stop):f.serialize_outputs({}, {}, {},{"Actual":{"suffixes":{}}})
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"receipt";f.write_exclusive(p,b"original")
            with self.assertRaises(f.Stop):f.write_exclusive(p,b"replacement")
            self.assertEqual(p.read_bytes(),b"original")


if __name__=="__main__":
    cli=argparse.ArgumentParser();cli.add_argument("--report");args=cli.parse_args()
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(SpecificationFixtures)
    ids=[t.id() for t in suite];result=unittest.TextTestRunner(verbosity=2).run(suite)
    report={"Purpose":"Development-only historical specification freezer fixtures","Environment":"Local Python stdlib; synthetic temporary files; no target history/model/source acquisition","Input":{"tests":ids},"Expected":{"tests_run":len(ids),"failures":0,"errors":0,"skipped":0},"Actual":{"tests_run":result.testsRun,"failures":[[a.id(),b] for a,b in result.failures],"errors":[[a.id(),b] for a,b in result.errors],"skipped":result.skipped},"Status":"PASS" if result.wasSuccessful() and result.testsRun==len(ids) and not result.skipped else "FAIL","formal_run_started":False}
    if args.report:f.write_exclusive(Path(args.report),f.encoded(report)+b"\n")
    raise SystemExit(0 if report["Status"]=="PASS" else 1)
