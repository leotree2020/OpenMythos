"""Synthetic audit-v6 contracts; never reads target data or imports a model."""
import argparse
from contextlib import ExitStack,redirect_stdout
import copy
import gzip
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import audit_history_v6 as V
import prepare_history_v6 as W
A,D,S=V.A,V.D,V.S


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(V.canonical(value));return V.pin(path)


def packed(path,value):
    raw=V.canonical(value);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(gzip.compress(raw,mtime=0))
    return {'physical':V.pin(path),'canonical':{'bytes':len(raw),'sha256':A.sha(raw)}}


class Fixture:
    def __init__(self,root):
        self.root=root;self.fresh=root/'fresh';self.repo=root/'repo';self.specdir=self.fresh/'specification-v6';self.prep=self.fresh/'preparation-v6';self.source=self.fresh/'source-v6';self.old=root/'history'
        for p in (self.fresh,self.repo,self.specdir,self.prep,self.source,self.old):p.mkdir(parents=True,exist_ok=True)
        self.rows=[];self.tokens={}
        for i in range(24):
            text=' '.join('item'+str(i)+'word'+str(j) for j in range(35))+'.'
            self.rows.append({'text':text,'label':i//6});self.tokens[text]=list(range(i*200,i*200+129))
        save(self.old/'old.json',{'text':self.rows[0]['text']})
        (self.old/'broken.jsonl').write_bytes(b'{"text":"complete old text"}\n{"text":"retained prefix')
        (self.old/'broken.py').write_bytes(b'x="unterminated\ny="old late literal"\n')
        (self.old/'old.txt').write_text('Earlier unrelated historical words.')
        self.oldtest=self.fresh/'preparation-v2/data/corpus.parquet';self.oldtest.parent.mkdir(parents=True);self.oldtest.write_bytes(b'prior test fixture')
        self.before=self.fresh/'preparation-v4/old_fresh_before.json';save(self.before,{})
        self.external=root/'old-external.log';self.external.write_text('old external receipt')
        self.oldv4={str(p):V.pin(p) for p in (self.before,self.external)}
        policies={}
        for key in ('nontext_entries','format_entries','member_entries','extra_history_inventory'):
            p=self.fresh/'specification-v1'/(key+'.json.gz');policies[key]=(p,packed(p,{})['physical'])
        oldspec={'history_roots':[str(self.old)],'expected_history_file_count':4,'expected_history_suffixes':{'.json':1,'.jsonl':1,'.py':1,'.txt':1}}
        for key,(p,info) in policies.items():oldspec[key+'_path']=str(p);oldspec[key+'_pin']=info
        self.oldspec=self.fresh/'specification-v1/DATA_SPEC.json';save(self.oldspec,oldspec)
        snapshot=self.specdir/'repo_history_snapshot/old.py';snapshot.parent.mkdir();snapshot.write_text('x="prior source fixture"\n')
        originals={str(p):V.pin(p) for p in self.old.iterdir()}
        fresh_old={str(p):V.pin(p) for p in self.fresh.rglob('*') if p.is_file() and not p.is_relative_to(self.specdir) and not p.is_relative_to(self.source) and not p.is_relative_to(self.prep)}
        self.mapping={**originals,**fresh_old,str(self.external):V.pin(self.external),str(snapshot):V.pin(snapshot)}
        self.inventory=self.specdir/'history_before.json.gz';inv=packed(self.inventory,self.mapping)
        self.spec={'schema':'mythos-history-v6-before-source','original_spec':str(self.oldspec),'original_spec_pin':V.pin(self.oldspec),'original_history_count':4,'history_file_count':len(self.mapping),'added_old_fresh_files':len(fresh_old),'added_external_sealed_files':1,'repo_snapshot_files':1,'repo_snapshot_bytes':snapshot.stat().st_size,'repo_snapshot_origins':{str(snapshot):{'original_path':str(self.repo/'old.py'),'pin':V.pin(snapshot)}},'inventory_path':str(self.inventory),'inventory_pin':inv['physical'],'inventory_canonical_pin':inv['canonical'],'policy_reuse':{key:{'path':str(policies[key][0]),'pin':policies[key][1]} for key in ('nontext_entries','format_entries','member_entries')},'excluded_new_protocol_roots':[str(self.fresh/n) for n in ('specification-v6','source-v6','preparation-v6','attempt-v6')],'prior_test_corpus':str(self.oldtest),'source_acquisitions':0,'model_calls':0}
        self.specpath=self.specdir/'DATA_SPEC.json';save(self.specpath,self.spec)
        save(self.specdir/'FREEZE_RECEIPT.json',{'Status':'PASS','Input':{'source_freeze':'a'*40},'Actual':{'spec_pin':V.pin(self.specpath)}})
        self.corpus=self.source/'corpus.parquet';self.corpus.write_bytes(b'train source fixture')
        self.tokenizer=root/'tokenizer.json';self.tokenizer.write_bytes(b'fake tokenizer')
        self.stack=ExitStack()
        for module,key,value in ((S,'FRESH',self.fresh),(S,'REPO',self.repo),(S,'OUT',self.source),(S,'CORPUS_PIN',V.pin(self.corpus)),(S,'PRIOR_TEST_PIN',V.pin(self.oldtest)),(S,'TOTAL_ROWS',24),(S,'ROWS_PER_LABEL',6),(S,'TOKENIZER',self.tokenizer),(S,'TOKENIZER_SHA',V.pin(self.tokenizer)['sha256']),(V,'SPEC_DIR',self.specdir),(V,'SPEC',self.specpath),(V,'PREP',self.prep),(V,'GATE',self.source/'manifest.json'),(V,'ORIGINAL_HISTORY_COUNT',4),(V,'DEFAULT_OUTPUT',self.specdir/'audit_history_v6.json')):
            self.stack.enter_context(patch.object(module,key,value))
        self.stack.enter_context(patch.object(V,'historical_git',side_effect=lambda name:self.oldv4 if 'v4' in name else {}))
        self.gate_rows=[];summary=S.collect_candidates(self.rows,self.tokenize,self.gate_rows)
        acq={'Status':'PASS','http_status':200,'request_attempts':1,'url':S.URL,'actual_response':S.CORPUS_PIN,'pin':S.CORPUS_PIN,'response_file':'corpus.parquet'}
        save(self.source/'acquisition.json',acq);gate_ledger=packed(self.source/'candidates.json.gz',self.gate_rows)
        self.gate={'Status':'PASS','Input':{'freeze':'a'*40,'dataset':S.DATASET,'revision':S.REVISION,'split':'train','url':S.URL,'corpus':S.CORPUS_PIN,'tokenizer_sha256':S.TOKENIZER_SHA},'Actual':{**summary,'source_rows_observed':24,'source_rows_completed':24,'ledger_rows_retained':24,'source_attempts':1,'model_calls':0,'optimizer_steps':0,'history_files_scanned':0,'eligibility_necessary_condition':'PASS','old_fresh_after_status':'PASS','input_after_status':'PASS','corpus_after_status':'PASS','checkout_after_status':'PASS','history_freeze':{'spec':V.pin(self.specpath),'receipt':V.pin(self.specdir/'FREEZE_RECEIPT.json'),'inventory':V.pin(self.inventory)}},'forbidden_imports':[],'artifacts':{'corpus.parquet':S.CORPUS_PIN,'acquisition.json':V.pin(self.source/'acquisition.json'),'candidates.json.gz':gate_ledger}}
        save(V.GATE,self.gate)
        reference={'schema':'mythos-train-source-reference-v6','mode':'LOCAL_PINNED_REUSE','Status':'PASS','source_file':str(self.corpus),'source_pin':S.CORPUS_PIN,'original_acquisition_file':str(self.source/'acquisition.json'),'original_acquisition_pin':V.pin(self.source/'acquisition.json'),'source_gate_file':str(V.GATE),'source_gate_pin':V.pin(V.GATE),'eligibility_file':str(self.source/'candidates.json.gz'),'eligibility_receipt':gate_ledger,'network_requests':0,'copied_corpus_bytes':0}
        self.final=[];candidates,rebuilt=W.rebuild_candidates(self.rows,self.tokenize,self.gate_rows,self.final,total_rows=24,rows_per_label=6)
        entries=[{'path':name,**value,'kind':D.classify_name(name)} for name,value in sorted(self.mapping.items())]
        index=D.ExclusionIndex(candidates)
        with redirect_stdout(io.StringIO()):self.history=D.scan_history(entries,index,self.tokenize,self.reader)
        selected=D.select(candidates,self.final,index);payload=W.payload(selected)
        self.artifacts={}
        for name,value in (('source_reference.json',reference),('inputs.json',payload)):
            self.artifacts[name]=save(self.prep/name,value)
        self.artifacts['public/selection.json']=save(self.prep/'public/selection.json',{'samples':[{k:v for k,v in row.items() if k not in ('text','tokens')} for row in payload['eval']],'input_pin':self.artifacts['inputs.json']})
        protected={**self.mapping,**{str(p):V.pin(p) for p in (self.specpath,self.specdir/'FREEZE_RECEIPT.json',self.inventory,V.GATE,self.corpus,self.source/'acquisition.json',self.source/'candidates.json.gz',self.tokenizer)}}
        for name,value in (('snapshot_policy_aliases.json.gz',[]),('protected_before.json.gz',protected),('candidates.json.gz',self.final),('history_ledger.json.gz',self.history)):
            self.artifacts[name]=packed(self.prep/name,value)
        self.manifest={'Status':'PASS','source_after_status':'PASS','forbidden_imports':[],'Input':{'spec_sha256':V.pin(self.specpath)['sha256'],'source_gate_sha256':V.pin(V.GATE)['sha256']},'Expected':{'source_rows':24,'selected':20,'per_class':5,'tokens':129,'new_source_acquisitions':0,'model_calls':0},'Actual':{**rebuilt,'model_calls':0,'optimizer_steps':0,'new_source_acquisitions':0,'copied_corpus_bytes':0,'selected':20,'per_class':{str(i):5 for i in range(4)},'input_pin':self.artifacts['inputs.json'],'historical_files':len(entries),'historical_files_completed':len(self.history),'historical_strings':index.string_count,'historical_token_arrays':index.token_array_count,'historical_format_notes':index.format_notes,'historical_python_recovery':index.python_recovery,'historical_jsonl_recovery':index.jsonl_recovery,'excluded_by_history':len(index.matches),'source_gate_bridge':'PASS','history_exclusion_complete':True,'new_new_exclusion_complete':True},'artifacts':self.artifacts}
        self.sync()
    def close(self):self.stack.close()
    def tokenize(self,text):return self.tokens.get(text,[31000+(ord(c)%20) for c in text])
    def reader(self,raw,kind):return copy.deepcopy(self.rows) if raw==self.corpus.read_bytes() else [{'text':'Old test corpus text.'}]
    def sync(self):save(self.prep/'manifest.json',self.manifest)
    def change(self,name,value):
        self.artifacts[name]=packed(self.prep/name,value) if name.endswith('.gz') else save(self.prep/name,value);self.sync()
    def audit(self):
        checks=[]
        result=V.audit(V.pin(self.specpath)['sha256'],V.pin(V.GATE)['sha256'],V.pin(self.prep/'manifest.json')['sha256'],self.tokenize,self.reader,lambda *args:checks.append(args))
        return result,checks


class AuditHistoryV6Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.fixture=Fixture(Path(self.temp.name));self.addCleanup(self.temp.cleanup);self.addCleanup(self.fixture.close)
    def test_complete_synthetic_audit_and_independence_limit(self):
        actual,checks=self.fixture.audit();self.assertEqual(actual['selected'],20);self.assertEqual(actual['historical_witnesses']['excluded_candidates'],1)
        self.assertEqual(actual['history']['jsonl_recovery']['files'],1);self.assertEqual(actual['history']['python_recovery']['files'],1)
        self.assertFalse(actual['historical_absence_independently_rescanned']);self.assertTrue(all(row[1] for row in checks))
    def test_producer_decision_helpers_are_not_used_by_audit(self):
        with patch.object(D,'select',side_effect=AssertionError('producer selection')),patch.object(D,'fingerprint',side_effect=AssertionError('producer fingerprint')),patch.object(D,'prose_reason',side_effect=AssertionError('producer prose')),patch.object(W,'scope_paths',side_effect=AssertionError('producer scope')),patch.object(W,'snapshot_policies',side_effect=AssertionError('producer aliases')):
            self.assertEqual(self.fixture.audit()[0]['selected'],20)
    def test_wrong_source_split_or_corpus_reference_fails(self):
        value=V.read(self.fixture.prep/'inputs.json');value['provenance']['split']='test';self.fixture.change('inputs.json',value)
        with self.assertRaises(A.Stop):self.fixture.audit()
    def test_gate_status_blocks_and_old_source_bytes_are_not_replaced(self):
        self.fixture.gate['Status']='BLOCKED';save(V.GATE,self.fixture.gate)
        with self.assertRaises(A.Stop):self.fixture.audit()
    def test_gate_eligibility_tamper_rejected_independently(self):
        gate=copy.deepcopy(self.fixture.gate_rows);gate[1]['full_token_count']=128
        with self.assertRaisesRegex(A.Stop,'eligibility row'):V.independent_candidates(self.fixture.rows,gate,self.fixture.final,self.fixture.tokenize,24,6)
    def test_final_eligibility_fields_or_unknown_decision_rejected(self):
        for field,value in (('tokenization_performed',False),('label',True),('decision','NOT_TESTED')):
            rows=copy.deepcopy(self.fixture.final);rows[1][field]=value
            with self.subTest(field=field),self.assertRaises(A.Stop):V.independent_candidates(self.fixture.rows,self.fixture.gate_rows,rows,self.fixture.tokenize,24,6)
    def test_missing_or_duplicate_source_rows_rejected(self):
        with self.assertRaises(A.Stop):V.independent_candidates(self.fixture.rows[:-1],self.fixture.gate_rows,self.fixture.final,self.fixture.tokenize,24,6)
        final=copy.deepcopy(self.fixture.final);final[1]['id']=final[0]['id']
        with self.assertRaises(A.Stop):V.independent_candidates(self.fixture.rows,self.fixture.gate_rows,final,self.fixture.tokenize,24,6)
    def test_prose_and_length_boundaries_remain_old_rules(self):
        self.assertIsNone(A.exclusion_reason('abcdefghijklm123456.'));self.assertEqual(A.exclusion_reason('abcdefghijkl1234567.'),'ALPHABETIC_RATIO')
        self.assertEqual(A.exclusion_reason('abc\\def.'),'LITERAL_BACKSLASH');self.assertEqual(A.exclusion_reason('abc<def>.'),'ANGLE_BRACKET')
    def test_old_test_corpus_custody_tamper_fails(self):
        self.fixture.oldtest.write_bytes(b'changed')
        with self.assertRaises(A.Stop):self.fixture.audit()
    def test_extra_old_fresh_file_changes_frozen_scope(self):
        (self.fixture.fresh/'previously-unrecorded.txt').write_text('old input added')
        with self.assertRaisesRegex(A.Stop,'count|scope'):self.fixture.audit()
    def test_snapshot_alias_and_copied_content_cannot_disappear(self):
        snapshot=Path(next(iter(self.fixture.spec['repo_snapshot_origins'])));snapshot.write_text('changed')
        with self.assertRaises(A.Stop):self.fixture.audit()
    def test_missing_history_ledger_row_rejected(self):
        self.fixture.change('history_ledger.json.gz',self.fixture.history[:-1])
        with self.assertRaises(A.Stop):self.fixture.audit()
    def test_historical_positive_witness_tamper_fails(self):
        final=copy.deepcopy(self.fixture.final);next(row for row in final if row['decision']=='EXCLUDE_HISTORY')['witness']['source']['location']='absent-location'
        self.fixture.change('candidates.json.gz',final)
        with self.assertRaises(A.Stop):self.fixture.audit()
    def test_selected_129_ids_or_scored_targets_tamper_fails(self):
        value=V.read(self.fixture.prep/'inputs.json');value['eval'][0]['tokens'][65]+=1;self.fixture.change('inputs.json',value)
        with self.assertRaises(A.Stop):self.fixture.audit()
    def test_public_raw_text_or_wrong_pin_fails(self):
        public=V.read(self.fixture.prep/'public/selection.json');public['samples'][0]['text']='must not publish';self.fixture.change('public/selection.json',public)
        with self.assertRaises(A.Stop):self.fixture.audit()
    def test_recovery_global_counter_tamper_fails(self):
        self.fixture.manifest['Actual']['historical_jsonl_recovery']['malformed_records']+=1;self.fixture.sync()
        with self.assertRaises(A.Stop):self.fixture.audit()
    def test_malformed_jsonl_receipt_cannot_be_omitted(self):
        history=copy.deepcopy(self.fixture.history);next(row for row in history if row['kind']=='jsonl').pop('jsonl_recovery');self.fixture.change('history_ledger.json.gz',history)
        with self.assertRaisesRegex(A.Stop,'JSONL'):self.fixture.audit()
    def test_malformed_jsonl_record_hash_or_boundary_tamper_fails(self):
        history=copy.deepcopy(self.fixture.history);note=next(row for row in history if row['kind']=='jsonl')['jsonl_recovery'][0];note['records'][0]['raw_sha256']='0'*64
        with self.assertRaises(A.Stop):V.jsonl_audit(history,{})
    def test_lf_bom_crlf_and_unicode_record_structure_independent(self):
        raw=b'\xef\xbb\xbf{"x":"ok"}\r\n'+json.dumps({'x':'a\u2028b\x85c'},ensure_ascii=False).encode()+b'\n{"x":"bad\r\n'
        complete,broken=V.jsonl_record_structure(raw);self.assertEqual(complete,2);self.assertEqual(broken[0]['record_index'],2)
        self.assertEqual(broken[0]['raw_sha256'],A.sha(b'{"x":"bad\r\n'));self.assertEqual(broken[0]['raw_utf8_bytes'],len(b'{"x":"bad\r\n'))
    def test_numeric_metadata_and_duplicate_json_keys_keep_valid_record_count(self):
        complete,broken=V.jsonl_record_structure(b'{"x":"a","x":"b","n":NaN}\n{"a":')
        self.assertEqual((complete,len(broken)),(1,1))
    def test_unlisted_preparation_file_or_bad_physical_pin_fails(self):
        (self.fixture.prep/'extra.json').write_text('{}')
        with self.assertRaisesRegex(A.Stop,'unlisted'):self.fixture.audit()
    def test_protection_map_cannot_drop_previous_input(self):
        value=V.packed(self.fixture.prep/'protected_before.json.gz',self.fixture.artifacts['protected_before.json.gz']);value.pop(str(self.fixture.oldtest));self.fixture.change('protected_before.json.gz',value)
        with self.assertRaisesRegex(A.Stop,'protection scope'):self.fixture.audit()
    def test_safe_output_rejects_prep_snapshot_and_existing_file(self):
        self.assertTrue(V.safe_output(V.DEFAULT_OUTPUT));self.assertFalse(V.safe_output(self.fixture.prep/'audit.json'))
        self.assertFalse(V.safe_output(self.fixture.specdir/'repo_history_snapshot/audit.json'));V.DEFAULT_OUTPUT.write_text('old');self.assertFalse(V.safe_output(V.DEFAULT_OUTPUT))
    def test_snapshot_binary_and_archive_member_aliases_use_exact_bytes(self):
        info={'bytes':7,'sha256':'a'*64};original=str(self.fixture.old/'archive.tar.gz');copied=str(self.fixture.specdir/'repo_history_snapshot/archive.tar.gz')
        mapping={original:info,copied:info};member=original[:-3]+'!tensors.pt'
        member_policy={'bytes':3,'sha256':'b'*64,'kind':'nontext','reason':'pinned numeric member'}
        policy={'nontext_entries':{},'format_entries':{original:{**info,'kind':'gzip','reason':'registered archive'}},'member_entries':{member:member_policy}}
        effective,notes=V.independent_aliases(mapping,{copied:{}},policy)
        self.assertEqual(effective['format_entries'][copied]['kind'],'gzip');self.assertEqual(effective['member_entries'][copied[:-3]+'!tensors.pt'],member_policy)
        self.assertEqual(len(notes),1);self.assertEqual(notes[0]['member_aliases'][0]['physical_original'],original)
    def test_snapshot_alias_cannot_be_inferred_from_extension_or_conflicting_rules(self):
        info={'bytes':7,'sha256':'a'*64};original=str(self.fixture.old/'weights.pt');copy_path=str(self.fixture.specdir/'repo_history_snapshot/weights.pt')
        policy={'nontext_entries':{original:{**info,'reason':'pinned tensor'}},'format_entries':{},'member_entries':{}}
        effective,notes=V.independent_aliases({original:info,copy_path:{**info,'sha256':'c'*64}},{copy_path:{}},policy)
        self.assertNotIn(copy_path,effective['nontext_entries']);self.assertEqual(notes,[])
        policy['format_entries'][str(self.fixture.old/'other.pt')]={**info,'kind':'text','reason':'conflict'}
        with self.assertRaisesRegex(A.Stop,'Unambiguous'):V.independent_aliases({original:info,copy_path:info},{copy_path:{}},policy)
    def test_explicit_A_B_C_chain_and_source_code_identity(self):
        self.fixture.manifest['Input'].update(implementation='b'*40,acquisition_freeze='a'*40);self.fixture.sync()
        def git(repo,*args):
            self.assertEqual(args[0],'merge-base');return args[1]
        with patch.object(S,'git',side_effect=git),patch.object(V.subprocess,'check_output',return_value=b'frozen'),patch.object(V,'pin',return_value={'bytes':6,'sha256':A.sha(b'frozen')}):
            self.assertEqual(V.ancestry_guard('c'*40),'a'*40)
            self.fixture.manifest['Input']['acquisition_freeze']='d'*40;self.fixture.sync()
            with self.assertRaisesRegex(A.Stop,'Explicit A'):V.ancestry_guard('c'*40)
        self.fixture.manifest['Input']['acquisition_freeze']='a'*40;self.fixture.sync()
        with patch.object(S,'git',side_effect=git),patch.object(V.subprocess,'check_output',return_value=b'frozen'),patch.object(V,'pin',return_value={'bytes':7,'sha256':A.sha(b'changed')}):
            with self.assertRaisesRegex(A.Stop,'unchanged since B'):V.ancestry_guard('c'*40)
    def test_exact_isolated_help_and_invalid_output_do_not_mutate(self):
        help_result=subprocess.run([sys.executable,'-I','-B',str(HERE/'audit_history_v6.py'),'--help'],capture_output=True,text=True,timeout=30)
        self.assertEqual(help_result.returncode,0,help_result.stderr)
        target=self.fixture.prep/'must-not-write.json'
        command=[sys.executable,'-I','-B',str(HERE/'audit_history_v6.py'),'--expected-head','a'*40,'--expected-spec-sha','b'*64,'--expected-gate-sha','c'*64,'--expected-prep-sha','d'*64,'--output',str(target)]
        result=subprocess.run(command,capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,2,result.stderr);self.assertFalse(target.exists());self.assertIn('BLOCKED',result.stdout)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--report',type=Path,required=True);args=parser.parse_args()
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(AuditHistoryV6Tests);ids=[test.id() for test in suite]
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    report={'Purpose':'Independent train/history audit synthetic integration and tamper rejection','Environment':{'python':sys.version,'isolated':bool(sys.flags.isolated),'no_bytecode':sys.dont_write_bytecode,'development_only':True},'Input':{'synthetic_only':True,'real_corpus_reads':0,'target_actions':0,'model_calls':0},'Expected':{'tests':len(ids),'failures':0,'errors':0,'skipped':0},'Actual':{'test_ids':ids,'planned':len(ids),'run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'expected_failures':len(result.expectedFailures),'unexpected_successes':len(result.unexpectedSuccesses),'failure_details':[[t.id(),reason] for t,reason in result.failures+result.errors]},'Status':'PASS' if result.wasSuccessful() and result.testsRun==len(ids) and not result.skipped else 'FAIL'}
    with args.report.open('x',encoding='utf-8',newline='\n') as stream:json.dump(report,stream,sort_keys=True,indent=2,allow_nan=False);stream.write('\n')
    raise SystemExit(0 if report['Status']=='PASS' else 1)
