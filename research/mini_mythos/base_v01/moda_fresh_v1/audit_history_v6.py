"""Independent train-source eligibility/selection audit; shared byte parser only.

This does not independently tokenize the complete historical universe. It binds
all historical bytes/classifications and reconstructs every positive exclusion.
"""
from __future__ import annotations
import argparse
from collections import Counter
import datetime
import gzip
import importlib.metadata
import io
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import traceback

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import audit_data as A
import data_prepare as D
import source_feasibility_v6 as S

SPEC_DIR=S.FRESH/'specification-v6'
SPEC=SPEC_DIR/'DATA_SPEC.json'
PREP=S.FRESH/'preparation-v6'
GATE=S.OUT/'manifest.json'
DEFAULT_OUTPUT=SPEC_DIR/'audit_history_v6.json'
LIMIT=64*1024**2
ORIGINAL_HISTORY_COUNT=32244
JSONL_KEYS=('files','complete_valid_records','malformed_records','raw_utf8_bytes','string_fragments','decoded_prefixes','token_arrays','truncated_escapes','rejected_origins')
SOURCES=('audit_history_v6.py','test_audit_history_v6.py','audit_data.py','data_prepare.py','source_feasibility_v6.py','prepare_history_v6.py','freeze_history_v6.py')
require=A.require
pin=A.pin
canonical=A.encoded


def read(path,limit=LIMIT):
    path=Path(path)
    require(path.is_file() and not any(p.is_symlink() for p in (path,*path.parents)),'Regular immutable evidence path','BLOCKED')
    with path.open('rb') as stream:raw=stream.read(limit+1)
    require(len(raw)<=limit,'Bounded evidence read','BLOCKED')
    return A.loads(raw)


def packed(path,receipt):
    require(pin(path)==receipt['physical'],'Physical gzip receipt')
    with gzip.open(path,'rb') as stream:raw=stream.read(LIMIT+1)
    require(len(raw)<=LIMIT,'Canonical evidence expansion bound','BLOCKED')
    require({'bytes':len(raw),'sha256':A.sha(raw)}==receipt['canonical'],'Canonical gzip receipt')
    value=A.loads(raw);require(canonical(value)==raw,'Canonical encoding')
    return value


def verify_artifacts(prep,manifest):
    names={'source_reference.json','snapshot_policy_aliases.json.gz','protected_before.json.gz','candidates.json.gz','history_ledger.json.gz','inputs.json','public/selection.json'}
    require(set(manifest['artifacts'])==names,'Exact complete V6 preparation artifact set')
    observed={p.relative_to(prep).as_posix() for p in prep.rglob('*') if p.is_file()}
    require(observed==names|{'manifest.json'},'No omitted/unlisted preparation file')
    values={}
    for name,receipt in manifest['artifacts'].items():
        path=prep/name
        if name.endswith('.gz'):values[name]=packed(path,receipt)
        else:require(pin(path)==receipt,'Artifact byte receipt '+name);values[name]=read(path)
    return values


def source_binding(reference,expected_gate_sha):
    require(pin(GATE)['sha256']==expected_gate_sha,'Frozen source-gate SHA')
    gate=read(GATE,65536);actual=gate['Actual'];inputs=gate['Input']
    require(gate['Status']=='PASS' and actual['eligibility_necessary_condition']=='PASS' and not gate['forbidden_imports'],'Completed source gate')
    require(inputs['dataset']==S.DATASET and inputs['revision']==S.REVISION and inputs['split']=='train' and inputs['url']==S.URL and inputs['corpus']==S.CORPUS_PIN,'Train source provenance')
    require(inputs['tokenizer_sha256']==S.TOKENIZER_SHA,'Original tokenizer provenance')
    require(actual['source_rows']==S.TOTAL_ROWS and actual['rows_per_label']=={str(i):S.ROWS_PER_LABEL for i in range(4)},'Full train source coverage')
    require(all(actual[key]==S.TOTAL_ROWS for key in ('source_rows_observed','source_rows_completed','ledger_rows_retained')),'All train rows completed')
    require(actual['history_freeze']['spec']==pin(SPEC) and actual['history_freeze']['receipt']==pin(SPEC_DIR/'FREEZE_RECEIPT.json') and actual['history_freeze']['inventory']==pin(SPEC_DIR/'history_before.json.gz'),'Source gate binds original pre-acquisition cutoff')
    require(actual['source_attempts']==1 and actual['model_calls']==actual['optimizer_steps']==actual['history_files_scanned']==0,'Model-blind single acquisition gate')
    require(all(actual[k]=='PASS' for k in ('old_fresh_after_status','input_after_status','corpus_after_status','checkout_after_status')),'Source-gate custody')
    source=S.OUT/'corpus.parquet';acq=S.OUT/'acquisition.json';ledger=S.OUT/'candidates.json.gz'
    require(pin(source)==gate['artifacts']['corpus.parquet']==S.CORPUS_PIN,'Retained exact train source')
    require(pin(acq)==gate['artifacts']['acquisition.json'],'Original acquisition receipt')
    acquisition=read(acq,65536)
    require(acquisition['Status']=='PASS' and acquisition['http_status']==200 and acquisition['request_attempts']==1 and acquisition['url']==S.URL and acquisition['actual_response']==acquisition['pin']==S.CORPUS_PIN and acquisition['response_file']=='corpus.parquet','Original HTTP acquisition')
    expected={'schema':'mythos-train-source-reference-v6','mode':'LOCAL_PINNED_REUSE','Status':'PASS','source_file':str(source),'source_pin':S.CORPUS_PIN,'original_acquisition_file':str(acq),'original_acquisition_pin':pin(acq),'source_gate_file':str(GATE),'source_gate_pin':pin(GATE),'eligibility_file':str(ledger),'eligibility_receipt':gate['artifacts']['candidates.json.gz'],'network_requests':0,'copied_corpus_bytes':0}
    require(reference==expected,'Exact source/gate/eligibility reference; no acquisition/copy')
    records=packed(ledger,expected['eligibility_receipt'])
    return source,gate,records,expected


def independent_candidates(source,gate_rows,final_rows,tokenize,total_rows=120000,rows_per_label=30000):
    require(len(source)==len(gate_rows)==len(final_rows)==total_rows,'Complete source/gate/final row coverage')
    require(len({r['id'] for r in final_rows})==total_rows,'Unique candidate IDs')
    eligible={};labels=Counter();decisions=Counter();counts=Counter()
    for index,(row,gate,final) in enumerate(zip(source,gate_rows,final_rows)):
        text,label=row['text'],row['label']
        require(type(text)is str and type(label)is int and label in range(4),'Independent source types')
        identity={'corpus_sha256':S.CORPUS_PIN['sha256'],'row':index,'text_sha256':A.sha(text.encode())}
        expected={'id':A.sha(canonical(identity)),'row':index,'label':label,'text_sha256':identity['text_sha256'],'decision':None,'full_token_count':None,'tokenization_started':False,'tokenization_performed':False}
        reason=A.exclusion_reason(text);ids=None
        if reason:expected['decision']='EXCLUDE_'+reason
        else:
            ids=tokenize(text);require(A.valid_ids(ids),'Independent original-tokenizer IDs')
            expected.update(full_token_count=len(ids),tokenization_started=True,tokenization_performed=True,decision='EXCLUDE_SHORT' if len(ids)<129 else 'ELIGIBLE_PENDING_HISTORY')
        require(gate==expected,'Independent source-gate eligibility row '+str(index))
        labels[label]+=1;decisions[expected['decision']]+=1
        if expected['decision']!='ELIGIBLE_PENDING_HISTORY':require(final==expected,'Excluded eligibility unchanged');continue
        counts[label]+=1
        require(final['decision'] in ('EXCLUDE_HISTORY','EXCLUDE_NEW_DUPLICATE','SELECTED','ELIGIBLE_NOT_SELECTED'),'Eligible final decision')
        reduced={k:v for k,v in final.items() if k not in ('decision','witness')}
        require(reduced=={k:v for k,v in expected.items() if k!='decision'},'Eligible receipt fields unchanged')
        require(set(final)==set(expected)|({'witness'} if final['decision'].startswith('EXCLUDE_') else set()),'Exact final receipt schema')
        eligible[expected['id']]={**expected,'text':text,'fingerprint':A.fingerprint(text,ids)}
    require(labels==Counter({i:rows_per_label for i in range(4)}),'Independent source label counts')
    require(all(counts[i]>=5 for i in range(4)),'Independent necessary quota','BLOCKED')
    return eligible,{'source_rows':total_rows,'rows_per_label':{str(i):labels[i] for i in range(4)},'eligible_per_label':{str(i):counts[i] for i in range(4)},'prose_length_eligible':len(eligible),'decisions':dict(sorted(decisions.items()))}


def jsonl_record_structure(raw):
    """Independent LF/syntax/hash audit; not shared prefix-recovery logic."""
    lines=raw.decode('utf-8').split('\n');complete=0;bad=[]
    for index,line in enumerate(lines):
        text=line[1:] if index==0 and line.startswith('\ufeff') else line
        if not text.strip(' \t\r'):continue
        try:json.loads(text)
        except json.JSONDecodeError as error:
            original=(line+('\n' if index<len(lines)-1 else '')).encode()
            bad.append({'record_index':index,'line':index+1,'raw_utf8_bytes':len(original),'raw_sha256':A.sha(original),'json_error':{'type':'JSONDecodeError','position':error.pos,'column':error.colno,'message':error.msg}})
        else:complete+=1
    return complete,bad


def jsonl_audit(history,member_policy,arrow_reader=None):
    totals={k:0 for k in JSONL_KEYS}
    for row in history:
        notes=row.get('jsonl_recovery',[]);structure=None
        if row['kind']=='jsonl' and row['Status']=='PASS':
            structure=jsonl_record_structure(Path(row['path']).read_bytes())
            require(bool(notes)==bool(structure[1]),'Malformed JSONL cannot omit/add recovery receipt')
        if not notes:continue
        require(row['Status']=='PASS','Recovery requires actual payload scan')
        observed=[{'location':where,**value} for typ,value,where in D.byte_leaves(Path(row['path']).read_bytes(),row['kind'],row['path'],arrow_reader,member_policy=member_policy) if typ=='jsonl_recovery']
        require(observed==notes,'All JSONL recovery notes exactly reproduced with pinned shared parser')
        for note in notes:
            require(note['files']==1 and note['record_boundary']=='LF' and note['malformed_raw_covered'] is True and note['semantic_reconstruction'] is False,'Conservative JSONL recovery scope')
            for key in JSONL_KEYS:require(type(note[key])is int and note[key]>=0,'JSONL recovery counter');totals[key]+=note[key]
            require(note['malformed_records']==len(note['records']) and note['raw_utf8_bytes']==sum(r['raw_utf8_bytes'] for r in note['records']),'Malformed record/byte counters')
        if structure is not None:
            require(len(notes)==1 and notes[0]['complete_valid_records']==structure[0],'Independent complete LF-record count')
            require([{k:r[k] for k in basic} for r,basic in zip(notes[0]['records'],structure[1])]==structure[1] and len(notes[0]['records'])==len(structure[1]),'Independent malformed LF record indices/bytes/error')
    return totals


def payload_audit(selected,payload,public,input_pin):
    require(payload['context_tokens']==128 and payload['scored_positions']==[64,128] and payload['scored_target_offsets']==[65,129],'Frozen token alignment')
    require(payload['eval_seeds']==[5101,5202] and payload['train_seeds']==[4101,4202] and payload['optimizer_steps']==0,'Frozen seeds and zero training')
    require(len(payload['eval'])==len(selected)==20,'Exact selected input count')
    for index,(chosen,row) in enumerate(zip(selected,payload['eval'])):
        ids=chosen['fingerprint']['ids'][:129]
        expected={'id':chosen['id'],'index':index,'row':chosen['row'],'label':chosen['label'],'text':chosen['text'],'text_sha256':chosen['text_sha256'],'full_row_token_count':len(chosen['fingerprint']['ids']),'tokens':ids,'window_sha256':A.ids_pin(ids),'input_sha256':A.ids_pin(ids[:128]),'scored_targets_sha256':A.ids_pin(ids[65:129])}
        require(row==expected,'Exact source/token/target payload row')
    require(public=={'samples':[{k:v for k,v in row.items() if k not in ('text','tokens')} for row in payload['eval']],'input_pin':input_pin},'Exact public projection')
    provenance=payload['provenance']
    require(provenance['dataset']==S.DATASET and provenance['revision']==S.REVISION and provenance['split']=='train' and provenance['corpus']==S.CORPUS_PIN,'New train-source evaluation provenance')


def historical_git(name):
    raw=subprocess.check_output(['git','-C',str(S.REPO),'show',S.BASE+':research/mini_mythos/base_v01/moda_fresh_v1/'+name])
    return A.loads(raw)


def expanded_scope(spec,mapping,old,policy):
    """Independently enumerate roots; immutable repo copies are explicit entries."""
    original=A.collect_paths(old,policy)
    require(len(original)==spec['original_history_count']==ORIGINAL_HISTORY_COUNT,'Original complete history enumeration')
    exclusions={S.FRESH/name for name in ('specification-v6','source-v6','preparation-v6','attempt-v6')}
    require(set(spec['excluded_new_protocol_roots'])=={str(p) for p in exclusions},'Only declared new namespaces excluded')
    observed=set(original)
    for current,dirs,files in os.walk(S.FRESH,followlinks=False):
        parent=Path(current);kept=[]
        for name in dirs:
            path=parent/name
            if name in ('.git','__pycache__') or path in exclusions:continue
            require(not path.is_symlink(),'Historical directory symlink');kept.append(name)
        dirs[:]=kept
        for name in files:
            path=parent/name;require(not path.is_symlink(),'Historical file symlink');observed.add(str(path))
    old_v4=historical_git('continuation_v4_evidence/EXTERNAL_MANIFEST.json')
    before_path=S.FRESH/'preparation-v4/old_fresh_before.json'
    require(pin(before_path)==old_v4[str(before_path)],'Previously sealed old-fresh map')
    sealed=read(before_path)
    def merge(extra):
        require(all(sealed[k]==extra[k] for k in sealed.keys()&extra.keys()),'Historic custody maps consistent')
        sealed.update(extra)
    merge(old_v4)
    merge({r['source']:{k:r[k] for k in ('bytes','sha256')} for r in historical_git('CONTINUATION_V5_EXPORT_MANIFEST.json').values()})
    require(all(mapping.get(p)==value for p,value in sealed.items()),'All committed prior custody pins retained')
    origins=spec['repo_snapshot_origins'];root=SPEC_DIR/'repo_history_snapshot'
    require(len(origins)==spec['repo_snapshot_files'] and bool(origins),'Every repository snapshot declared')
    for copy,origin in origins.items():
        target,source=Path(copy),Path(origin['original_path'])
        require(target.is_relative_to(root) and source.is_relative_to(S.REPO) and target.relative_to(root)==source.relative_to(S.REPO),'Immutable snapshot origin binding')
        require(mapping.get(copy)==origin['pin'],'Snapshot origin byte pin')
    require({str(p) for p in root.rglob('*') if p.is_file()}==set(origins),'Exact immutable snapshot physical inventory')
    require(sum(r['pin']['bytes'] for r in origins.values())==spec['repo_snapshot_bytes'],'Snapshot byte total')
    require(spec['added_old_fresh_files']==len(observed-original) and spec['added_external_sealed_files']==len(set(sealed)-observed),'Independent history component counts')
    require(set(mapping)==observed|set(sealed)|set(origins),'Exact expanded historical scope')
    require(len(mapping)==spec['history_file_count']==ORIGINAL_HISTORY_COUNT+spec['added_old_fresh_files']+spec['added_external_sealed_files']+len(origins),'Independent expanded count')
    test_path=str(S.FRESH/'preparation-v2/data/corpus.parquet')
    require(spec['prior_test_corpus']==test_path and mapping.get(test_path)==S.PRIOR_TEST_PIN,'Entire old test corpus remains historical')
    return original


def independent_aliases(mapping,origins,policy):
    """Derive byte-identical snapshot policy aliases independently of preparer."""
    out={key:dict(policy[key]) for key in ('nontext_entries','format_entries','member_entries')};notes=[]
    for copy in sorted(origins):
        item=mapping[copy];suffix=Path(copy).suffix.casefold();matches=[]
        for table,default in (('nontext_entries','nontext'),('format_entries',None)):
            for name,entry in policy[table].items():
                if A.bytepin(entry)==item and Path(name).suffix.casefold()==suffix:matches.append((name,default or entry['kind'],entry))
        note={'path':copy,'pin':item,'registered_origins':[],'member_aliases':[]}
        if matches:
            kinds={kind for _,kind,_ in matches};require(len(kinds)==1,'Unambiguous identical-byte classification')
            kind=next(iter(kinds));paths=sorted(name for name,_,_ in matches)
            value={**item,'kind':kind,'reason':'Exact-byte and suffix-matched snapshot copy of registered paths: '+'; '.join(paths)}
            out['nontext_entries' if kind=='nontext' else 'format_entries'][copy]=value
            note.update(kind=kind,registered_origins=[{'path':name,'reason':entry['reason']} for name,_,entry in matches])
        for name,value in mapping.items():
            if name in origins or value!=item or Path(name).suffix.casefold()!=suffix:continue
            prefixes=[(name,copy)]
            if name.endswith(('.gz','.xz')):prefixes.append((name[:-3],copy[:-3]))
            for prefix,target in prefixes:
                for member,entry in policy['member_entries'].items():
                    if member!=prefix and not member.startswith(prefix+'!'):continue
                    alias=target+member[len(prefix):]
                    require(alias not in out['member_entries'] or out['member_entries'][alias]==entry,'Consistent member alias')
                    out['member_entries'][alias]=entry;note['member_aliases'].append({'original':member,'alias':alias,'physical_original':name})
        if note['registered_origins'] or note['member_aliases']:notes.append(note)
    return out,notes


def historical_audit(spec,history,aliases,arrow_reader):
    mapping=packed(spec['inventory_path'],{'physical':spec['inventory_pin'],'canonical':spec['inventory_canonical_pin']})
    original=Path(spec['original_spec']);require(pin(original)==spec['original_spec_pin'],'Original history spec custody')
    old=read(original);policy=A.policies(old)
    require(spec['policy_reuse']=={key:{'path':old[key+'_path'],'pin':old[key+'_pin']} for key in ('nontext_entries','format_entries','member_entries')},'Exact original policies')
    expanded_scope(spec,mapping,old,policy)
    effective,expected_aliases=independent_aliases(mapping,spec['repo_snapshot_origins'],policy)
    require(aliases==expected_aliases,'Every snapshot alias independently derived')
    # Full root enumeration happened above. Adapt old independent byte/classifier
    # auditor to this explicit complete inventory, without producer scope helpers.
    audit_spec={'history_roots':[],'expected_history_file_count':len(mapping),'expected_history_suffixes':dict(Counter(Path(p).suffix.casefold() for p in mapping))}
    audit_policy={**effective,'extra_history_files':[],'extra_history_inventory':mapping}
    historical=A.audit_history(audit_spec,audit_policy,history,arrow_reader=arrow_reader)
    historical['jsonl_recovery']=jsonl_audit(history,effective['member_entries'],arrow_reader)
    return historical,effective,mapping


def audit(expected_spec_sha,expected_gate_sha,expected_prep_sha,tokenize,arrow_reader,check):
    require(pin(SPEC)['sha256']==expected_spec_sha and pin(PREP/'manifest.json')['sha256']==expected_prep_sha,'Frozen history/preparation receipts')
    spec=read(SPEC,8*1024**2);manifest=read(PREP/'manifest.json',65536);freeze=read(SPEC_DIR/'FREEZE_RECEIPT.json',65536)
    require(spec['schema']=='mythos-history-v6-before-source' and freeze['Status']=='PASS' and freeze['Actual']['spec_pin']==pin(SPEC),'History cutoff receipt')
    actual=manifest['Actual']
    require(manifest['Status']=='PASS' and manifest['source_after_status']=='PASS' and manifest['forbidden_imports']==[],'Successful preserved preparation')
    require(manifest['Input']['spec_sha256']==expected_spec_sha and manifest['Input']['source_gate_sha256']==expected_gate_sha,'Preparation exact frozen input receipts')
    require(manifest['Expected']=={'source_rows':S.TOTAL_ROWS,'selected':20,'per_class':5,'tokens':129,'new_source_acquisitions':0,'model_calls':0},'Exact preparation acceptance header')
    require(actual['model_calls']==actual['optimizer_steps']==actual['new_source_acquisitions']==actual['copied_corpus_bytes']==0,'Zero model/training/acquisition/copy')
    values=verify_artifacts(PREP,manifest);check('All physical and canonical preparation receipts',True)
    source,gate,gate_rows,custody=source_binding(values['source_reference.json'],expected_gate_sha)
    require(gate['Input']['freeze']==freeze['Input']['source_freeze'],'Source gate and history cutoff share source freeze A')
    check('Original train corpus and acquisition/source gate retained',True)
    historical,effective,mapping=historical_audit(spec,values['history_ledger.json.gz'],values['snapshot_policy_aliases.json.gz'],arrow_reader)
    check('Complete expanded inventory, byte custody, classifications and recovery receipts',True,historical)
    protection=values['protected_before.json.gz']
    required={**mapping,**{str(path):pin(path) for path in (SPEC,SPEC_DIR/'FREEZE_RECEIPT.json',Path(spec['inventory_path']),GATE,source,Path(custody['original_acquisition_file']),Path(custody['eligibility_file']),S.TOKENIZER)}}
    require(all(protection.get(path)==value for path,value in required.items()),'Full frozen protection scope retained')
    for path,expected in protection.items():require(pin(path)==expected,'Protected preparation input unchanged')
    ledger=values['candidates.json.gz'];rows=arrow_reader(source.read_bytes(),'parquet')
    eligible,summary=independent_candidates(rows,gate_rows,ledger,tokenize,total_rows=S.TOTAL_ROWS,rows_per_label=S.ROWS_PER_LABEL)
    require(all(summary[key]==gate['Actual'][key]==actual[key] for key in summary),'All source eligibility aggregates independently reconciled')
    check('Every source identity/prose criterion/eligible-token count independently checked',True,summary)
    witnesses=A.audit_witnesses(eligible,ledger,values['history_ledger.json.gz'],tokenize,arrow_reader,effective['member_entries'])
    check('Every positive history exclusion independently reconstructed',True,witnesses)
    selected=A.independent_selection(eligible,ledger);input_pin=pin(PREP/'inputs.json')
    payload_audit(selected,values['inputs.json'],values['public/selection.json'],input_pin)
    check('Deterministic 5-per-class selection, full-text new-new exclusion and exact 129-token payload',True)
    require(actual['selected']==20 and actual['per_class']=={str(i):5 for i in range(4)} and actual['input_pin']==input_pin,'Selection aggregates')
    require(actual['historical_files']==actual['historical_files_completed']==historical['files'] and actual['historical_strings']==historical['strings'] and actual['historical_token_arrays']==historical['token_arrays'],'Historical counts')
    require(actual['historical_format_notes']==historical['format_notes'] and actual['historical_python_recovery']==historical['python_recovery'] and actual['historical_jsonl_recovery']==historical['jsonl_recovery'],'Recovery aggregates')
    require(actual['excluded_by_history']==witnesses['excluded_candidates'] and actual['source_gate_bridge']=='PASS' and actual['history_exclusion_complete'] is True and actual['new_new_exclusion_complete'] is True,'Completion declarations supported')
    require(source_binding(values['source_reference.json'],expected_gate_sha)[3]==custody,'Source/gate/receipt preserved after audit')
    for path,expected in protection.items():require(pin(path)==expected,'Protected input after audit')
    return {**summary,'selected':20,'selected_ids':[row['id'] for row in selected],'per_class':{str(i):5 for i in range(4)},'history':historical,'source_custody':custody,'input_pin':input_pin,'preparation_manifest':pin(PREP/'manifest.json'),'historical_witnesses':witnesses,'new_model_calls':0,'new_source_acquisitions':0,'historical_absence_independently_rescanned':False,'historical_absence_basis':'Complete frozen preparer scan; this audit independently checks coverage/byte pins/classification/positive witnesses, not a second full-history tokenization'}


def safe_output(path):
    return path==DEFAULT_OUTPUT and path.is_absolute() and path.parent.is_dir() and not path.exists() and not any(p.is_symlink() for p in (path,*path.parents))


def ancestry_guard(expected_head):
    source_freeze=read(GATE,65536)['Input']['freeze']
    require(S.git(S.REPO,'merge-base',source_freeze,expected_head)==source_freeze,'Original source freeze is auditor ancestor')
    prep_input=read(PREP/'manifest.json',65536)['Input'];prep_head=prep_input['implementation']
    require(prep_input['acquisition_freeze']==source_freeze and S.git(S.REPO,'merge-base',source_freeze,prep_head)==source_freeze and S.git(S.REPO,'merge-base',prep_head,expected_head)==prep_head,'Explicit A source to B preparation to C auditor ancestry')
    for head,names,label in ((prep_head,('prepare_history_v6.py','test_prepare_history_v6.py','data_prepare.py','freeze_history_v6.py','source_feasibility_v6.py'),'Preparation source unchanged since B'),(source_freeze,S.SOURCES,'Original acquisition source unchanged since A')):
        for name in names:
            original=subprocess.check_output(['git','-C',str(S.REPO),'show',head+':research/mini_mythos/base_v01/moda_fresh_v1/'+name])
            require(pin(HERE/name)['sha256']==A.sha(original),label)
    return source_freeze


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    for flag in ('expected-head','expected-spec-sha','expected-gate-sha','expected-prep-sha'):cli.add_argument('--'+flag,required=True)
    cli.add_argument('--output',required=True,type=Path);args=cli.parse_args()
    report={'Purpose':'Independent expanded-history/source/selection audit before zero-training models','Environment':{},'Input':vars(args)|{'output':str(args.output)},'Expected':'All custody/eligibility/selection checks PASS; shared-parser independence limits explicit','Actual':{},'checks':[],'Status':'NOT TESTED'}
    if not safe_output(args.output):print('BLOCKED: invalid/existing audit output; no file written',flush=True);return 2
    def check(name,okay,actual=None):report['checks'].append({'Purpose':name,'Expected':True,'Actual':actual,'Status':'PASS' if okay else 'FAIL'});require(okay,name)
    try:
        require(platform.system()=='Linux' and platform.python_version()=='3.12.3' and sys.executable==S.PYTHON and sys.flags.isolated and sys.dont_write_bytecode and not sys.flags.optimize and os.environ.get('CODESPACE_NAME')==S.SPACE,'Frozen target data environment','BLOCKED')
        require(S.git(S.REPO,'rev-parse','HEAD')==args.expected_head and not S.git(S.REPO,'status','--porcelain'),'Frozen clean auditor checkout','BLOCKED')
        own={}
        for name in SOURCES:
            raw=subprocess.check_output(['git','-C',str(S.REPO),'show',args.expected_head+':research/mini_mythos/base_v01/moda_fresh_v1/'+name])
            require(pin(HERE/name)['sha256']==A.sha(raw),'Frozen auditor/parser/source bytes');own[str(HERE/name)]=pin(HERE/name)
        source_freeze=ancestry_guard(args.expected_head)
        versions={name:importlib.metadata.version(name) for name in S.VERSIONS};require(versions==S.VERSIONS,'Frozen data dependencies','BLOCKED')
        require(pin(S.TOKENIZER)['sha256']==S.TOKENIZER_SHA,'Original tokenizer')
        os.environ.update(TOKENIZERS_PARALLELISM='false',RAYON_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',CUDA_VISIBLE_DEVICES='')
        import numpy as np
        import pyarrow as pa
        import pyarrow.parquet as pq
        from tokenizers import Tokenizer
        report['Environment']={'python':sys.version,'executable':sys.executable,'packages':versions,'development_only':False,'model_calls':0}
        report['Input'].update(audit_source_pin=pin(__file__),shared_parser_pin=pin(D.__file__),source_pin=S.CORPUS_PIN,tokenizer_pin=pin(S.TOKENIZER),source_freeze_A=source_freeze,spec_pin=pin(SPEC),source_gate_pin=pin(GATE),prep_pin=pin(PREP/'manifest.json'))
        tokenizer=Tokenizer.from_file(str(S.TOKENIZER))
        def reader(raw,kind):
            if kind=='npy':
                array=np.load(io.BytesIO(raw),allow_pickle=False);require(array.dtype.kind in 'biufUS','Historical NPY type')
                return [{'array':array.tolist(),'dtype':str(array.dtype)}]
            buffer=pa.BufferReader(raw)
            if kind=='parquet':return pq.read_table(buffer).to_pylist()
            try:return pa.ipc.open_file(buffer).read_all().to_pylist()
            except pa.ArrowInvalid:buffer.seek(0);return pa.ipc.open_stream(buffer).read_all().to_pylist()
        report['Actual']=audit(args.expected_spec_sha,args.expected_gate_sha,args.expected_prep_sha,lambda text:tokenizer.encode(text,add_special_tokens=False).ids,reader,check)
        require(all(pin(path)==expected for path,expected in own.items()) and pin(S.TOKENIZER)['sha256']==S.TOKENIZER_SHA,'Code/tokenizer unchanged')
        require(not any(name.split('.')[0] in S.FORBIDDEN for name in sys.modules),'No model imports')
        report['Status']='PASS'
    except BaseException as exc:
        report['Status']=getattr(exc,'status','BLOCKED' if isinstance(exc,(OSError,MemoryError,KeyboardInterrupt)) else 'FAIL');report['error']={'type':type(exc).__name__,'reason':str(exc),'traceback':traceback.format_exc()}
    report['Limits']=['Shares pinned historical byte/container parser; independently implements selection, source eligibility, overlap and coverage audit.','No independent second full-history tokenization; no absence proof for unretained/unreadable/semantic-paraphrase/base-pretraining content.','No model quality, timing or statistical acceptance implied.']
    report['check_counts']={state:sum(row['Status']==state for row in report['checks']) for state in ('PASS','FAIL')};report['utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    raw=canonical(report);require(len(raw)<=65536,'Bounded audit receipt')
    require(sum(p.stat().st_size for p in SPEC_DIR.rglob('*') if p.is_file())+len(raw)<=64*1024**2 and shutil.disk_usage(SPEC_DIR).free>=256*1024**2+len(raw),'Audit allocation/reserve','BLOCKED')
    with args.output.open('xb') as stream:stream.write(raw)
    print(json.dumps({'Status':report['Status'],'checks':report['check_counts'],'error':report.get('error')},allow_nan=False),flush=True)
    return 0 if report['Status']=='PASS' else 2


if __name__=='__main__':raise SystemExit(main())

