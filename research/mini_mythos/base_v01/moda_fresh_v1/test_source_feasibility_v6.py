"""Development-only fixtures. No real corpus, tokenizer, network, history or model."""
from __future__ import annotations
import argparse
import contextlib
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import source_feasibility_v6 as source


class Response(io.BytesIO):
    def __init__(self, raw, status=200):
        super().__init__(raw)
        self.status, self.url, self.headers = status, source.URL, {'Content-Length':str(len(raw))}


class SourceV6Tests(unittest.TestCase):
    def small_contract(self):
        stack = contextlib.ExitStack()
        stack.enter_context(mock.patch.object(source, 'TOTAL_ROWS', 20))
        stack.enter_context(mock.patch.object(source, 'ROWS_PER_LABEL', 5))
        return stack
    def rows(self, count=20):
        return ({'text':'A complete ordinary news sentence.', 'label':i % 4} for i in range(count))
    def synthetic_pin(self, raw): return {'bytes':len(raw), 'sha256':hashlib.sha256(raw).hexdigest()}
    def test_frozen_train_metadata_and_names(self):
        self.assertEqual(source.BASE, 'b3565ae427df93991bb7f78e633f3229c5930dd5')
        self.assertEqual(source.OUT.name, 'source-v6')
        self.assertEqual((source.SPLIT, source.TOTAL_ROWS, source.ROWS_PER_LABEL, source.PER_CLASS, source.WINDOW), ('train',120000,30000,5,129))
        self.assertIn('/data/train-00000-of-00001.parquet', source.URL)
        self.assertEqual(source.CORPUS_PIN, {'bytes':18585438,'sha256':'fc508d6d9868594e3da960a8cfeb63ab5a4746598b93428c224397080c1f52ee'})
        self.assertEqual((source.EVIDENCE_BUDGET,source.DISK_RESERVE,source.SEAL_ALLOWANCE), (67108864,268435456,65536))
    def test_exact_isolated_help_without_forbidden_imports(self):
        with tempfile.TemporaryDirectory() as folder:
            for name in ('source_feasibility_v6.py','test_source_feasibility_v6.py'):
                result = subprocess.run([sys.executable,'-I','-B',str(HERE/name),'--help'], cwd=folder,capture_output=True,text=True,timeout=30)
                self.assertEqual(result.returncode,0,(result.stdout,result.stderr));self.assertIn('usage:',result.stdout)
        self.assertFalse(set(sys.modules)&source.FORBIDDEN)
    def test_prose_filters_match_frozen_rules_and_boundaries(self):
        cases = [(None,'NOT_STRING'),('Hello\ufffd.','REPLACEMENT_CHARACTER'),('Hello\\world.','LITERAL_BACKSLASH'),('Hello<tag>.','ANGLE_BRACKET'),('12345.','ALPHABETIC_RATIO'),('Only words','NO_SENTENCE_PUNCTUATION'),('abcdefghijklm123456.',None),('abcdefghijkl1234567.','ALPHABETIC_RATIO'),('  A normal sentence.  ',None)]
        for text, expected in cases:
            with self.subTest(text=text): self.assertEqual(source.prose_reason(text),expected)
    def test_complete_real_count_synthetic_ledger(self):
        ledger=[]
        actual=source.collect_candidates(self.rows(120000),lambda _: [7]*129,ledger)
        source.validate_eligibility(actual,ledger)
        self.assertEqual(actual['rows_per_label'],{str(i):30000 for i in range(4)})
        self.assertEqual(len(ledger),120000);self.assertEqual(ledger[-1]['row'],119999)
        expected={'corpus_sha256':source.CORPUS_PIN['sha256'],'row':0,'text_sha256':source.sha('A complete ordinary news sentence.'.encode())}
        self.assertEqual(ledger[0]['id'],source.sha(source.canonical(expected)))
        self.assertTrue(all(not ({'text','tokens','fingerprint'} & set(row)) for row in ledger))
    def test_129_token_boundary_and_failed_prose_not_tokenized(self):
        rows=[{'text':'A short sentence.','label':0},{'text':'A longer sentence.','label':1},{'text':'Bad\\sentence.','label':2}]
        tokenize=mock.Mock(side_effect=[[1]*128,[2]*129]);ledger=[]
        actual=source.collect_candidates(rows,tokenize,ledger)
        self.assertEqual([r['decision'] for r in ledger],['EXCLUDE_SHORT','ELIGIBLE_PENDING_HISTORY','EXCLUDE_LITERAL_BACKSLASH'])
        self.assertEqual([r['full_token_count'] for r in ledger],[128,129,None]);self.assertEqual(tokenize.call_count,2)
        self.assertEqual(actual['eligible_per_label'],{'0':0,'1':1,'2':0,'3':0})
    def test_malformed_label_or_invalid_tokens_fail_and_retain_row(self):
        for value in (True,4,'0'):
            with self.subTest(label=value),self.assertRaises(source.Stop):source.collect_candidates([{'text':'Sentence.','label':value}],lambda _:[],[])
        for ids in ([32768],[-1],[True],(1,2)):
            ledger=[]
            with self.subTest(ids=ids),self.assertRaises(source.Stop):source.collect_candidates([{'text':'Sentence.','label':0}],lambda _:ids,ledger)
            self.assertEqual(len(ledger),1);self.assertEqual(ledger[0]['decision'],'NOT_TESTED');self.assertTrue(ledger[0]['tokenization_started'])
    def test_incomplete_or_unbalanced_rows_fail(self):
        with self.small_contract():
            for rows in (self.rows(19),[{'text':'A sentence.','label':0} for _ in range(20)]):
                ledger=[];actual=source.collect_candidates(rows,lambda _:[1]*129,ledger)
                with self.assertRaises(source.Stop) as caught:source.validate_eligibility(actual,ledger)
                self.assertEqual(caught.exception.status,'FAIL')
            with self.assertRaises(source.Stop):source.collect_candidates(self.rows(21),lambda _:[1]*129,[])
    def test_insufficient_class_blocks_after_ledger_saved(self):
        with self.small_contract(),tempfile.TemporaryDirectory() as folder:
            rows=list(self.rows());rows[1]['text']='Short.'
            ledger=[];actual=source.collect_candidates(rows,lambda text:[1]*(128 if text=='Short.' else 129),ledger)
            writer=source.BudgetWriter(folder);receipt=writer.compressed('candidates.json.gz',ledger)
            with self.assertRaises(source.Stop) as caught:source.validate_eligibility(actual,ledger)
            self.assertEqual(caught.exception.status,'BLOCKED');self.assertEqual(actual['eligible_per_label']['1'],4)
            self.assertEqual(json.loads(gzip.decompress((Path(folder)/'candidates.json.gz').read_bytes())),ledger)
            self.assertEqual(receipt['physical'],source.pin(Path(folder)/'candidates.json.gz'))
    def test_duplicate_id_or_unfinished_decision_fails(self):
        with self.small_contract():
            ledger=[];actual=source.collect_candidates(self.rows(),lambda _:[1]*129,ledger)
            ledger[1]['id']=ledger[0]['id']
            with self.assertRaises(source.Stop):source.validate_eligibility(actual,ledger)
            ledger=[];actual=source.collect_candidates(self.rows(),lambda _:[1]*129,ledger);ledger[1]['decision']='NOT_TESTED'
            with self.assertRaises(source.Stop):source.validate_eligibility(actual,ledger)
    def test_download_success_one_attempt_and_exact_bytes(self):
        raw=b'fake parquet bytes'
        with tempfile.TemporaryDirectory() as folder,mock.patch.object(source,'CORPUS_PIN',self.synthetic_pin(raw)):
            opener=mock.Mock(return_value=Response(raw));path,receipt=source.acquire(source.BudgetWriter(folder),opener)
            self.assertEqual(opener.call_count,1);self.assertEqual(path.read_bytes(),raw);self.assertEqual(receipt['Status'],'PASS')
            self.assertEqual(receipt['request_attempts'],1);self.assertEqual(json.loads((Path(folder)/'acquisition.json').read_bytes()),receipt)
    def test_http_error_hash_error_and_bounded_body_preserved_no_retry(self):
        raw=b'12345';expected=self.synthetic_pin(raw)
        for body,status,verdict in ((b'denied',403,'BLOCKED'),(b'bad!!',200,'FAIL'),(raw+b'overflow',200,'FAIL')):
            with self.subTest(status=status,body=body),tempfile.TemporaryDirectory() as folder,mock.patch.object(source,'CORPUS_PIN',expected):
                opener=mock.Mock(return_value=Response(body,status))
                with self.assertRaises(source.Stop) as caught:source.acquire(source.BudgetWriter(folder),opener)
                self.assertEqual(caught.exception.status,verdict);self.assertEqual(opener.call_count,1)
                receipt=json.loads((Path(folder)/'acquisition.json').read_bytes());retained=(Path(folder)/receipt['response_file']).read_bytes()
                self.assertEqual(retained,body[:len(raw)+1]);self.assertEqual(receipt['pin'],self.synthetic_pin(retained))
    def test_network_failure_preserves_primary_exception(self):
        with tempfile.TemporaryDirectory() as folder:
            opener=mock.Mock(side_effect=OSError('fixture unreachable'))
            with self.assertRaises(source.Stop) as caught:source.acquire(source.BudgetWriter(folder),opener)
            self.assertEqual(caught.exception.status,'BLOCKED');self.assertEqual(opener.call_count,1)
            receipt=json.loads((Path(folder)/'acquisition.json').read_bytes())
            self.assertEqual(receipt['error'],{'type':'OSError','message':'fixture unreachable'});self.assertEqual(receipt['actual_response']['bytes'],0)
    def test_budget_exact_boundary_and_reserved_manifest(self):
        with tempfile.TemporaryDirectory() as folder,mock.patch.object(source,'EVIDENCE_BUDGET',1024),mock.patch.object(source,'SEAL_ALLOWANCE',100):
            writer=source.BudgetWriter(folder);writer.write('payload',b'x'*924)
            with self.assertRaises(source.Stop) as caught:writer.write('too-much',b'x')
            self.assertEqual(caught.exception.status,'BLOCKED')
            source.final_manifest(writer,{'Status':'BLOCKED'});self.assertLessEqual(writer.used(),1024)
            with self.assertRaises(FileExistsError):source.final_manifest(writer,{'Status':'BLOCKED'})
    def test_disk_reserve_and_output_confinement(self):
        with tempfile.TemporaryDirectory() as folder:
            writer=source.BudgetWriter(folder)
            free=source.DISK_RESERVE+source.SEAL_ALLOWANCE+4
            with mock.patch.object(source.shutil,'disk_usage',return_value=type('Usage',(),{'free':free})()):
                writer.write('exact',b'1234')
                with self.assertRaises(source.Stop):writer.write('too-large',b'12345')
            with self.assertRaises(source.Stop):writer.write('../escape',b'x')
    def test_exclusive_outputs_and_old_namespace_preservation(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);old=root/'preparation-v4';old.mkdir();(old/'manifest.json').write_bytes(b'old failure')
            current=root/'source-v6';current.mkdir();writer=source.BudgetWriter(current)
            before=source.old_namespace_pins(root,current);writer.write('new',b'new source evidence')
            self.assertEqual(before,source.old_namespace_pins(root,current))
            with self.assertRaises(source.Stop):writer.write('new',b'changed')
            (old/'manifest.json').write_bytes(b'changed');self.assertNotEqual(before,source.old_namespace_pins(root,current))
    def test_gzip_retains_canonical_full_records(self):
        with tempfile.TemporaryDirectory() as folder:
            rows=[{'row':0,'label':0,'decision':'EXCLUDE_SHORT','full_token_count':128},{'row':1,'label':1,'decision':'ELIGIBLE_PENDING_HISTORY','full_token_count':129}]
            receipt=source.BudgetWriter(folder).compressed('eligibility.json.gz',rows)
            raw=gzip.decompress((Path(folder)/'eligibility.json.gz').read_bytes())
            self.assertEqual(raw,source.canonical(rows));self.assertEqual(receipt['canonical'],self.synthetic_pin(raw))
    def test_checkout_guard_binds_clean_base_branch_and_upstream(self):
        head='a'*40
        def git(repo,*args):
            if args==('rev-parse','HEAD'):return head if repo==source.REPO else source.UPSTREAM_HEAD
            if args==('status','--porcelain'):return ''
            if args==('branch','--show-current'):return source.BRANCH
            if args==('merge-base',source.BASE,head):return source.BASE
            raise AssertionError(args)
        with mock.patch.object(source,'git',side_effect=git),mock.patch.object(source.subprocess,'check_output',return_value=b'frozen'),mock.patch.object(source,'pin',return_value=self.synthetic_pin(b'frozen')):
            source.checkout_guard(head)
        with mock.patch.object(source,'git',return_value='dirty'):
            with self.assertRaises(source.Stop) as caught:source.checkout_guard(head)
            self.assertEqual(caught.exception.status,'BLOCKED')
    def test_complete_history_freeze_binding_before_source(self):
        with tempfile.TemporaryDirectory() as folder:
            fresh=Path(folder);specification=fresh/'specification-v6';specification.mkdir()
            old=fresh/'original.json';old.write_bytes(b'original')
            policies={}
            for name in ('nontext_entries','format_entries','member_entries'):
                path=fresh/(name+'.gz');path.write_bytes(name.encode());policies[name]={'path':str(path),'pin':source.pin(path)}
            prior=str(fresh/'preparation-v2/data/corpus.parquet')
            snapshot=specification/'repo_history_snapshot/readme.txt';snapshot.parent.mkdir();snapshot.write_bytes(b'snapshot text')
            origins={str(snapshot):{'original_path':str(source.REPO/'readme.txt'),'pin':source.pin(snapshot)}}
            mapping={str(fresh/('old-'+str(i))):{'bytes':1,'sha256':'a'*64} for i in range(32244)};mapping[prior]=source.PRIOR_TEST_PIN;mapping[str(snapshot)]=source.pin(snapshot)
            raw=source.canonical(mapping);inventory=specification/'history_before.json.gz';inventory.write_bytes(gzip.compress(raw,mtime=0))
            spec={'schema':'mythos-history-v6-before-source','original_spec':str(old),'original_spec_pin':source.pin(old),'original_history_count':32244,'history_file_count':len(mapping),'added_old_fresh_files':1,'added_external_sealed_files':0,'repo_snapshot_files':1,'repo_snapshot_bytes':snapshot.stat().st_size,'repo_snapshot_origins':origins,'inventory_path':str(inventory),'inventory_pin':source.pin(inventory),'inventory_canonical_pin':self.synthetic_pin(raw),'policy_reuse':policies,'excluded_new_protocol_roots':[str(fresh/n) for n in ('specification-v6','source-v6','preparation-v6','attempt-v6')],'prior_test_corpus':prior,'source_acquisitions':0,'model_calls':0,'fixture_padding':'x'*65536}
            specpath=specification/'DATA_SPEC.json';specpath.write_bytes(source.canonical(spec))
            receipt={'Status':'PASS','Input':{'source_freeze':'a'*40},'Actual':{'history_file_count':len(mapping),'added_old_fresh_files':1,'repo_snapshot_files':1,'repo_snapshot_bytes':snapshot.stat().st_size,'prior_test_corpus_pin':source.PRIOR_TEST_PIN,'spec_pin':source.pin(specpath),'source_acquisitions':0,'model_calls':0}}
            receiptpath=specification/'FREEZE_RECEIPT.json';receiptpath.write_bytes(source.canonical(receipt))
            with mock.patch.object(source,'SPECIFICATION',specification),mock.patch.object(source,'FRESH',fresh):
                bound,summary=source.history_freeze_guard('a'*40)
                self.assertEqual(summary['history_file_count'],32246);self.assertIn(str(inventory),bound)
                receipt['Status']='BLOCKED';receiptpath.write_bytes(source.canonical(receipt))
                with self.assertRaises(source.Stop):source.history_freeze_guard('a'*40)
                receipt['Status']='PASS';receiptpath.write_bytes(source.canonical(receipt));inventory.write_bytes(b'changed')
                with self.assertRaises(source.Stop):source.history_freeze_guard('a'*40)


if __name__ == '__main__':
    cli=argparse.ArgumentParser(description=__doc__);cli.add_argument('--report',required=True,type=Path);args=cli.parse_args()
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(SourceV6Tests);ids=[test.id() for test in suite]
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    report={'Purpose':'Development-only source-v6 eligibility, evidence, admission and isolated-startup fixtures',
            'Environment':{'executable':sys.executable,'version':sys.version,'isolated':bool(sys.flags.isolated),'no_bytecode':sys.dont_write_bytecode},
            'Input':{'synthetic_only':True,'real_source_acquisitions':0,'real_tokenizer_calls':0,'history_files_scanned':0,'model_calls':0},
            'Expected':{'tests':len(ids),'failures':0,'errors':0,'skipped':0},
            'Actual':{'test_ids':ids,'planned':len(ids),'run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'expected_failures':len(result.expectedFailures),'unexpected_successes':len(result.unexpectedSuccesses),'failure_details':[[test.id(),error] for test,error in result.failures+result.errors]},
            'Status':'PASS' if result.wasSuccessful() and result.testsRun==len(ids) and not result.skipped else 'FAIL'}
    with args.report.open('x',encoding='utf-8',newline='\n') as stream:json.dump(report,stream,sort_keys=True,indent=2,allow_nan=False);stream.write('\n')
    raise SystemExit(0 if report['Status']=='PASS' else 1)
