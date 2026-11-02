"""Development-only complete-accounting fixtures for the target storage forecast."""
import argparse
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import measure_storage as m


class ForecastTests(unittest.TestCase):
    def fixtures(self):
        protected={"/workspaces/history/a":{"bytes":1,"sha256":"a"*64},"/workspaces/history/b":{"bytes":1,"sha256":"a"*64}}
        payload={"Status":"PASS","Actual":{"measured_payload_external_bytes":12345,"measured_payload_both_copies_bytes":24690}}
        base={"tensor%02d"%n:{"sha256":"a"*64,"shape":[16,16],"dtype":"torch.float32"} for n in range(63)}
        adapters=json.loads((Path(__file__).parent/"OLD_ADAPTERS.json").read_text())
        return protected,payload,base,adapters
    def test_both_full_inventory_paths_and_every_copy_accounted(self):
        args=self.fixtures();budget,receipt=m.forecast(*args)
        self.assertEqual(receipt["record_count"],2)
        parts=budget["parts"]
        self.assertEqual(parts["worker_and_auditor_payload_both_copies"],24690)
        self.assertEqual(parts["complete_protected_gzip_both_copies"],2*receipt["compressed"]["bytes"])
        actual_adapter_schema={r["arm"]+"_"+str(r["train_seed"]):r["state"] for r in args[3]["rows"]}
        self.assertEqual(parts["frozen_base_and_adapter_before_after_both_copies"],4*(len(m.encoded(args[2]))+len(m.encoded(actual_adapter_schema))))
        self.assertEqual(parts["remaining_operator_environment_tests_logs_both_copies_allowance"],1024*1024)
        self.assertEqual(parts["git_and_finalization_allowance"],4*1024**2)
        self.assertEqual(parts["final_inventory_gzip_growth_both_copies_allowance"],131072)
        self.assertEqual(budget["projected_total_nonraw_bytes"],sum(parts.values()))
        self.assertEqual(budget["metadata_budget_bytes"],12*1024**2)
    def test_missing_adapter_or_base_state_stops(self):
        p,b,s,a=self.fixtures();a["rows"].pop()
        with self.assertRaises(m.executor.Stop):m.forecast(p,b,s,a)
        p,b,s,a=self.fixtures();s.pop(next(iter(s)))
        with self.assertRaises(m.executor.Stop):m.forecast(p,b,s,a)
    def test_unaccepted_or_single_copy_payload_stops(self):
        p,b,s,a=self.fixtures();b["Status"]="NOT TESTED"
        with self.assertRaises(m.executor.Stop):m.forecast(p,b,s,a)
        b["Status"]="PASS";b["Actual"]["measured_payload_both_copies_bytes"]=12345
        with self.assertRaises(m.executor.Stop):m.forecast(p,b,s,a)


if __name__=="__main__":
    cli=argparse.ArgumentParser();cli.add_argument("--report",required=True,type=Path);args=cli.parse_args()
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(ForecastTests);ids=sorted(x.id() for x in suite)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    report={"Purpose":"Development-only complete evidence capacity accounting","Environment":"Local stdlib; synthetic inventory/base63 plus previously copied adapter metadata; no target/model/new-data execution","Input":{"tests":ids},"Expected":{"run":len(ids),"failures":0,"errors":0},"Actual":{"test_ids":ids,"planned":len(ids),"run":result.testsRun,"failures":len(result.failures),"errors":len(result.errors),"skipped":len(result.skipped),"expected_failures":len(result.expectedFailures),"unexpected_successes":len(result.unexpectedSuccesses)},"Status":"PASS" if result.wasSuccessful() and result.testsRun==len(ids) and not result.skipped else "FAIL"}
    m.write(args.report,report);raise SystemExit(0 if report["Status"]=="PASS" else 1)
