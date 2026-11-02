"""One model-blind AG News train eligibility gate; no historical scan or retry."""
from __future__ import annotations
import argparse
from collections import Counter
import datetime
import gzip
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import subprocess
import sys
import traceback
import urllib.error
import urllib.request

HERE = Path(__file__).resolve().parent
REPO = Path('/workspaces/mythos-moda-fresh-cpu-v1')
PACKAGE = REPO / 'research/mini_mythos/base_v01/moda_fresh_v1'
BASE = 'b3565ae427df93991bb7f78e633f3229c5930dd5'
BRANCH = 'mythos-moda-fresh-cpu-v1'
SPACE = 'bookish-pancake-vwqx7rr9x5w3wxjr'
PYTHON = '/workspaces/mythos-depth-data-cpu312/bin/python'
FRESH = Path('/workspaces/mythos-evidence/base_v01/moda_fresh')
OUT = FRESH / 'source-v6'
METADATA = FRESH / 'source-v6-metadata.json'
METADATA_PIN = {'bytes':630, 'sha256':'6533620e9c04c31062beeff69ffa384a7c90b31c3806a4e5310166f3e79f034e'}
SPECIFICATION = FRESH / 'specification-v6'
PRIOR_TEST_PIN = {'bytes':1234829, 'sha256':'71de87ec66bc5737752a2502204dfa6d7fe9856ade3ea444dc6317789a4f13fb'}
UPSTREAM = Path('/workspaces/mythos-parcae-pinned')
UPSTREAM_HEAD = '69284c13746e849104f738d6d1a347b1f457df76'
TOKENIZER = Path('/workspaces/mythos-evidence/base_v01/b1/b1-20261101T021657Z/downloads/tokenizer/tokenizer.json')
TOKENIZER_SHA = 'e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77'
DATASET = 'fancyzhx/ag_news'
REVISION = 'eb185aade064a813bc0b7f42de02595523103ca4'
SPLIT = 'train'
CORPUS_RELATIVE = 'data/train-00000-of-00001.parquet'
URL = 'https://huggingface.co/datasets/' + DATASET + '/resolve/' + REVISION + '/' + CORPUS_RELATIVE
CORPUS_PIN = {'bytes':18585438, 'sha256':'fc508d6d9868594e3da960a8cfeb63ab5a4746598b93428c224397080c1f52ee'}
TOTAL_ROWS, ROWS_PER_LABEL, PER_CLASS, WINDOW = 120000, 30000, 5, 129
EVIDENCE_BUDGET, DISK_RESERVE, SEAL_ALLOWANCE = 64 * 1024**2, 256 * 1024**2, 65536
VERSIONS = {'pyarrow':'19.0.1', 'numpy':'1.26.4', 'tokenizers':'0.23.2'}
FORBIDDEN = {'torch', 'parcae_lm', 'receval', 'transformers'}
SOURCES = ('source_feasibility_v6.py', 'test_source_feasibility_v6.py', 'SOURCE_PROTOCOL_V6.md')


class Stop(Exception):
    def __init__(self, status, reason):
        super().__init__(reason)
        self.status = status


def require(condition, reason, status='FAIL'):
    if not condition:
        raise Stop(status, reason)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8') + b'\n'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pin(path):
    digest, count = hashlib.sha256(), 0
    with Path(path).open('rb') as stream:
        for raw in iter(lambda:stream.read(1024**2), b''):
            digest.update(raw)
            count += len(raw)
    return {'bytes':count, 'sha256':digest.hexdigest()}


def prose_reason(text):
    """Exact old frozen filter; no rewriting, new filter or model scoring."""
    if not isinstance(text, str): return 'NOT_STRING'
    if '\ufffd' in text: return 'REPLACEMENT_CHARACTER'
    if '\\' in text: return 'LITERAL_BACKSLASH'
    if '<' in text or '>' in text: return 'ANGLE_BRACKET'
    chars = [c for c in text if not c.isspace()]
    if not chars or sum(c.isalpha() for c in chars) / len(chars) < .65: return 'ALPHABETIC_RATIO'
    if not any(c in text for c in '.?!'): return 'NO_SENTENCE_PUNCTUATION'
    return None


def collect_candidates(rows, tokenize, ledger):
    """Store every row receipt, but no source text, IDs or grams in the ledger."""
    labels, eligible, decisions = Counter(), Counter(), Counter()
    tokenizer_calls = 0
    for i, row in enumerate(rows):
        require(i < TOTAL_ROWS, 'Source has more than the frozen120000 rows')
        require(isinstance(row, dict) and set(row) >= {'text', 'label'}, 'AG News row schema')
        text, label = row['text'], row['label']
        require(isinstance(text, str) and type(label) is int and label in range(4), 'AG News text/label schema')
        identity = {'corpus_sha256':CORPUS_PIN['sha256'], 'row':i, 'text_sha256':sha(text.encode('utf-8'))}
        record = {'id':sha(canonical(identity)), 'row':i, 'label':label, 'text_sha256':identity['text_sha256'],
                  'decision':'NOT_TESTED', 'full_token_count':None, 'tokenization_started':False, 'tokenization_performed':False}
        # Retain the failing row as NOT_TESTED if tokenization itself fails.
        ledger.append(record)
        labels[label] += 1
        reason = prose_reason(text)
        if reason:
            record['decision'] = 'EXCLUDE_' + reason
        else:
            tokenizer_calls += 1
            record['tokenization_started'] = True
            ids = tokenize(text)
            require(isinstance(ids, list) and all(type(x) is int and 0 <= x < 32768 for x in ids), 'Original tokenizer ID contract')
            record.update(full_token_count=len(ids), tokenization_performed=True)
            record['decision'] = 'EXCLUDE_SHORT' if len(ids) < WINDOW else 'ELIGIBLE_PENDING_HISTORY'
            if len(ids) >= WINDOW: eligible[label] += 1
        decisions[record['decision']] += 1
    return {'source_rows':len(ledger), 'rows_per_label':{str(i):labels[i] for i in range(4)},
            'eligible_per_label':{str(i):eligible[i] for i in range(4)}, 'prose_length_eligible':sum(eligible.values()),
            'decisions':dict(sorted(decisions.items())), 'tokenizer_calls':tokenizer_calls}


def validate_eligibility(actual, ledger):
    require(actual['source_rows'] == len(ledger) == TOTAL_ROWS, 'Complete120000-row eligibility ledger required')
    require(actual['rows_per_label'] == {str(i):ROWS_PER_LABEL for i in range(4)}, 'Exactly30000 source rows per label required')
    require([row['row'] for row in ledger] == list(range(TOTAL_ROWS)) and len({r['id'] for r in ledger}) == TOTAL_ROWS, 'Complete ordered unique row identities required')
    require(sum(actual['decisions'].values()) == TOTAL_ROWS and all(r['decision'] != 'NOT_TESTED' for r in ledger), 'Every source row must have a completed eligibility decision')
    require(all(actual['eligible_per_label'][str(i)] >= PER_CLASS for i in range(4)),
            'Insufficient pre-history eligible rows for fixed5-per-label quota; no source/filter/quota fallback', 'BLOCKED')


class BudgetWriter:
    def __init__(self, out): self.out = Path(out)
    def used(self): return sum(p.stat().st_size for p in self.out.rglob('*') if p.is_file())
    def write(self, name, raw):
        destination = self.out / name
        require(destination.resolve().is_relative_to(self.out.resolve()), 'Output escaped source-v6')
        require(not destination.exists(), 'Refuse existing evidence: ' + name, 'BLOCKED')
        require(self.used() + len(raw) <= EVIDENCE_BUDGET - SEAL_ALLOWANCE, '64MiB source evidence allocation including64KiB seal exceeded', 'BLOCKED')
        require(shutil.disk_usage(self.out).free >= len(raw) + SEAL_ALLOWANCE + DISK_RESERVE, '256MiB reserve plus64KiB seal unavailable', 'BLOCKED')
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open('xb') as stream: stream.write(raw)
        require(pin(destination) == {'bytes':len(raw), 'sha256':sha(raw)}, 'Evidence readback differs')
        return pin(destination)
    def json(self, name, value): return self.write(name, canonical(value))
    def compressed(self, name, value):
        raw, buffer = canonical(value), io.BytesIO()
        with gzip.GzipFile(fileobj=buffer, mode='wb', filename='', mtime=0, compresslevel=9) as stream: stream.write(raw)
        compressed = buffer.getvalue()
        require(gzip.decompress(compressed) == raw, 'Lossless ledger gzip roundtrip')
        return {'physical':self.write(name, compressed), 'canonical':{'bytes':len(raw), 'sha256':sha(raw)}}


def acquire(writer, opener=None):
    """One bounded request attempt. HTTP/hash/network failures retain response bytes."""
    opener = urllib.request.urlopen if opener is None else opener
    request = urllib.request.Request(URL, headers={'User-Agent':'OpenMythos-frozen-source-feasibility-v6'})
    receipt = {'url':URL, 'expected':CORPUS_PIN, 'request_attempts':1, 'response_body_limit_bytes':CORPUS_PIN['bytes'] + 1, 'Status':'NOT TESTED'}
    data, error = bytearray(), None
    try:
        try: response = opener(request, timeout=60)
        except urllib.error.HTTPError as exc: response = exc
        with response:
            receipt.update(final_url=response.url, http_status=response.status, content_length=response.headers.get('Content-Length'))
            while len(data) <= CORPUS_PIN['bytes']:
                chunk = response.read(min(65536, CORPUS_PIN['bytes'] + 1 - len(data)))
                if not chunk: break
                data.extend(chunk)
    except BaseException as exc:
        error = exc
        receipt['error'] = {'type':type(exc).__name__, 'message':str(exc)}
    data = bytes(data)
    observed = {'bytes':len(data), 'sha256':sha(data)}
    receipt['actual_response'] = observed
    okay = error is None and receipt.get('http_status') == 200 and observed == CORPUS_PIN
    receipt['Status'] = 'PASS' if okay else ('FAIL' if error is None and receipt.get('http_status') == 200 else 'BLOCKED')
    name = 'corpus.parquet' if okay else 'failed_acquisition_response.bin'
    try:
        receipt['pin'] = writer.write(name, data)
        receipt['response_file'] = name
    except BaseException as exc:
        receipt['Status'] = 'BLOCKED'
        receipt['storage_error'] = {'type':type(exc).__name__, 'message':str(exc)}
    writer.json('acquisition.json', receipt)
    if receipt['Status'] != 'PASS': raise Stop(receipt['Status'], 'Single source acquisition failed; preserved acquisition.json and bounded response')
    return writer.out / name, receipt


def old_namespace_pins(root, excluded):
    require(root.is_dir() and not root.is_symlink(), 'Existing evidence namespace missing', 'BLOCKED')
    result = {}
    for path in sorted(root.rglob('*')):
        if path == excluded or path.is_relative_to(excluded): continue
        require(not path.is_symlink(), 'Old evidence namespace symlink: ' + str(path), 'BLOCKED')
        if path.is_file(): result[str(path)] = pin(path)
    return result


def git(repo, *arguments):
    return subprocess.check_output(['git', '-C', str(repo), *arguments], text=True).strip()


def checkout_guard(expected_head):
    require(git(REPO, 'rev-parse', 'HEAD') == expected_head and not git(REPO, 'status', '--porcelain'), 'Frozen clean source checkout required', 'BLOCKED')
    require(git(REPO, 'branch', '--show-current') == BRANCH and git(REPO, 'merge-base', BASE, expected_head) == BASE, 'Authorized source protocol ancestry/branch required', 'BLOCKED')
    require(git(UPSTREAM, 'rev-parse', 'HEAD') == UPSTREAM_HEAD and not git(UPSTREAM, 'status', '--porcelain'), 'Pinned clean read-only upstream required', 'BLOCKED')
    for name in SOURCES:
        relative = 'research/mini_mythos/base_v01/moda_fresh_v1/' + name
        frozen = subprocess.check_output(['git', '-C', str(REPO), 'show', expected_head + ':' + relative])
        require(pin(PACKAGE / name)['sha256'] == sha(frozen), 'Source file differs from execution freeze: ' + name)


def history_freeze_guard(expected_head):
    """Verify the pre-acquisition inventory receipt and bytes, not history content."""
    receipt_path, spec_path = SPECIFICATION / 'FREEZE_RECEIPT.json', SPECIFICATION / 'DATA_SPEC.json'
    require(all(p.is_file() and not p.is_symlink() for p in (receipt_path, spec_path)), 'Frozen history receipt/specification required', 'BLOCKED')
    require(receipt_path.stat().st_size <= SEAL_ALLOWANCE and spec_path.stat().st_size <= 8 * 1024**2, 'Bounded history freeze records required', 'BLOCKED')
    receipt, spec = json.loads(receipt_path.read_bytes()), json.loads(spec_path.read_bytes())
    require(receipt.get('Status') == 'PASS' and receipt.get('Input', {}).get('source_freeze') == expected_head, 'History freeze must PASS at current source commit')
    actual = receipt.get('Actual', {})
    require(actual.get('spec_pin') == pin(spec_path), 'History specification differs from accepted receipt')
    require(spec.get('schema') == 'mythos-history-v6-before-source' and spec.get('original_history_count') == 32244, 'Complete original history scope required')
    require(type(spec.get('history_file_count')) is int and spec['history_file_count'] > 32244 and spec['history_file_count'] == actual.get('history_file_count'), 'Expanded old-fresh history scope required')
    components = ('added_old_fresh_files','added_external_sealed_files','repo_snapshot_files')
    require(all(type(spec.get(name)) is int and spec[name] >= 0 for name in components), 'Expanded historical scope component counts required')
    require(spec['history_file_count'] == 32244 + sum(spec[name] for name in components) and spec['added_old_fresh_files'] == actual.get('added_old_fresh_files'), 'Expanded historical scope total differs')
    require(spec.get('source_acquisitions') == spec.get('model_calls') == actual.get('source_acquisitions') == actual.get('model_calls') == 0, 'History freeze must precede source acquisition/models')
    expected_exclusions = {str(FRESH / name) for name in ('specification-v6','source-v6','preparation-v6','attempt-v6')}
    require(set(spec.get('excluded_new_protocol_roots', [])) == expected_exclusions, 'Only new protocol namespaces may be excluded')
    inventory = SPECIFICATION / 'history_before.json.gz'
    require(spec.get('inventory_path') == str(inventory) and pin(inventory) == spec.get('inventory_pin'), 'Frozen physical history mapping differs')
    with gzip.open(inventory, 'rb') as stream: raw = stream.read(64 * 1024**2 + 1)
    require(len(raw) <= 64 * 1024**2, 'Bounded historical mapping expansion required', 'BLOCKED')
    require({'bytes':len(raw), 'sha256':sha(raw)} == spec.get('inventory_canonical_pin'), 'Frozen canonical history mapping differs')
    mapping = json.loads(raw)
    require(isinstance(mapping, dict) and canonical(mapping) == raw and len(mapping) == spec['history_file_count'], 'Complete canonical history mapping required')
    origins = spec.get('repo_snapshot_origins', {})
    require(isinstance(origins, dict) and len(origins) == spec['repo_snapshot_files'] == actual.get('repo_snapshot_files') and len(origins) > 0, 'Complete repository history snapshot origins required')
    snapshot_root = SPECIFICATION / 'repo_history_snapshot'
    for destination, origin in origins.items():
        target, original_path = Path(destination), Path(origin.get('original_path', ''))
        require(target.is_relative_to(snapshot_root) and original_path.is_relative_to(REPO) and target.relative_to(snapshot_root) == original_path.relative_to(REPO), 'Repository history snapshot path binding differs')
        require(mapping.get(destination) == origin.get('pin') and pin(target) == origin['pin'], 'Repository history snapshot bytes differ')
    require(sum(item['pin']['bytes'] for item in origins.values()) == spec.get('repo_snapshot_bytes') == actual.get('repo_snapshot_bytes'), 'Repository snapshot byte total differs')
    prior_test = str(FRESH / 'preparation-v2/data/corpus.parquet')
    require(spec.get('prior_test_corpus') == prior_test and mapping.get(prior_test) == actual.get('prior_test_corpus_pin') == PRIOR_TEST_PIN, 'Whole previously inspected test corpus must be historical')
    bound = {str(path):pin(path) for path in (receipt_path, spec_path, inventory)}
    original = Path(spec.get('original_spec', ''))
    require(pin(original) == spec.get('original_spec_pin'), 'Original historical specification changed')
    bound[str(original)] = pin(original)
    policies = spec.get('policy_reuse', {})
    require(set(policies) == {'nontext_entries','format_entries','member_entries'}, 'All frozen history policies required')
    for item in policies.values():
        path = Path(item['path'])
        require(pin(path) == item.get('pin'), 'Reused historical policy changed')
        bound[str(path)] = pin(path)
    return bound, {'receipt':pin(receipt_path), 'spec':pin(spec_path), 'inventory':pin(inventory), 'history_file_count':len(mapping), 'repo_snapshot_files':len(origins), 'prior_test_corpus_pin':PRIOR_TEST_PIN, 'content_scan':'NOT TESTED'}


def final_manifest(writer, report):
    """Reserved bounded stop record is exclusive even after an allocation failure."""
    raw = canonical(report)
    require(len(raw) <= SEAL_ALLOWANCE, 'Manifest exceeds reserved64KiB seal')
    require(writer.used() + len(raw) <= EVIDENCE_BUDGET, 'Final source evidence exceeds64MiB')
    require(shutil.disk_usage(writer.out).free >= len(raw) + DISK_RESERVE, 'Final manifest would consume256MiB reserve', 'BLOCKED')
    with (writer.out / 'manifest.json').open('xb') as stream: stream.write(raw)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--expected-head', required=True)
    args = cli.parse_args()
    require(re.fullmatch('[0-9a-f]{40}', args.expected_head), 'Full execution freeze commit required', 'BLOCKED')
    if OUT.exists():
        print('BLOCKED: source-v6 exists; no retry or overwrite', flush=True)
        return 2
    if os.name != 'posix' or not Path('/workspaces').is_dir():
        print('BLOCKED: designated Linux Codespace required', flush=True)
        return 2
    require(FRESH.is_dir() and not any(path.is_symlink() for path in (FRESH, *FRESH.parents)), 'Evidence parent must be an existing regular directory path', 'BLOCKED')
    OUT.mkdir(parents=True, exist_ok=False)
    writer = BudgetWriter(OUT)
    report = {'Purpose':'Determine necessary source eligibility before any full historical scan or model evaluation',
              'Environment':{'python':sys.version, 'executable':sys.executable, 'platform':platform.platform(), 'codespace':os.environ.get('CODESPACE_NAME')},
              'Input':{'base':BASE, 'freeze':args.expected_head, 'dataset':DATASET, 'revision':REVISION, 'split':SPLIT, 'url':URL, 'corpus':CORPUS_PIN, 'metadata':METADATA_PIN, 'tokenizer_sha256':TOKENIZER_SHA},
              'Expected':{'source_rows':TOTAL_ROWS, 'rows_per_label':ROWS_PER_LABEL, 'minimum_eligible_per_label':PER_CLASS, 'minimum_tokens':WINDOW, 'source_attempts':1, 'history_files_scanned':0, 'model_calls':0, 'optimizer_steps':0},
              'Actual':{'source_attempts':0, 'source_rows':0, 'model_calls':0, 'optimizer_steps':0, 'history_files_scanned':0, 'history_tokenizer_calls':0, 'selected':0},
              'Status':'NOT TESTED', 'freshness':'NOT TESTED', 'scientific_conclusion':'NOT TESTED'}
    before, input_pins, ledger, artifacts = None, {}, [], {}
    source_path = None
    checked_git = False
    ledger_saved = False
    def interrupted(signum, frame):
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        report['interruption'] = {'signal':signum}
        raise Stop('BLOCKED', 'Source eligibility interrupted; no retry')
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        require(platform.python_version() == '3.12.3' and sys.executable == PYTHON and sys.flags.isolated and sys.dont_write_bytecode and not sys.flags.optimize, 'Exact isolated data Python required', 'BLOCKED')
        require(os.environ.get('CODESPACE_NAME') == SPACE and HERE == PACKAGE, 'Designated Codespace/source package required', 'BLOCKED')
        checkout_guard(args.expected_head)
        checked_git = True
        history_pins, history_receipt = history_freeze_guard(args.expected_head)
        report['Actual']['history_freeze'] = history_receipt
        require(pin(METADATA) == METADATA_PIN, 'Official train source metadata receipt changed')
        require(pin(TOKENIZER)['sha256'] == TOKENIZER_SHA, 'Original tokenizer changed')
        input_pins = {str(path):pin(path) for path in (METADATA, TOKENIZER, *(PACKAGE / n for n in SOURCES))}
        input_pins.update(history_pins)
        before = old_namespace_pins(FRESH, OUT)
        artifacts['old_fresh_before.json.gz'] = writer.compressed('old_fresh_before.json.gz', before)
        require(shutil.disk_usage(OUT).free >= EVIDENCE_BUDGET - writer.used() + DISK_RESERVE, '64MiB source allocation plus256MiB reserve unavailable', 'BLOCKED')
        versions = {name:importlib.metadata.version(name) for name in VERSIONS}
        require(versions == VERSIONS, 'Existing pinned data dependency versions required', 'BLOCKED')
        report['Environment']['packages'] = versions
        runtime = {'TOKENIZERS_PARALLELISM':'false', 'RAYON_NUM_THREADS':'1', 'OPENBLAS_NUM_THREADS':'1', 'CUDA_VISIBLE_DEVICES':''}
        report['Environment']['env_before'] = {key:os.environ.get(key) for key in runtime}
        os.environ.update(runtime)
        report['Environment']['env_effective'] = {key:os.environ.get(key) for key in runtime}
        import pyarrow.parquet as pq
        from tokenizers import Tokenizer
        tokenizer = Tokenizer.from_file(str(TOKENIZER))
        report['Actual']['source_attempts'] += 1
        source_path, acquisition = acquire(writer)
        artifacts['corpus.parquet'] = acquisition['pin']
        artifacts['acquisition.json'] = pin(OUT / 'acquisition.json')
        require(pin(source_path) == CORPUS_PIN, 'Acquired source before-tokenization exact bytes')
        with pq.ParquetFile(source_path) as parquet:
            require(parquet.metadata.num_rows == TOTAL_ROWS and set(parquet.schema_arrow.names) >= {'text', 'label'}, 'Train parquet row/schema contract')
            rows = (row for batch in parquet.iter_batches(batch_size=1024, columns=['text', 'label']) for row in batch.to_pylist())
            actual = collect_candidates(rows, lambda text:tokenizer.encode(text, add_special_tokens=False).ids, ledger)
        report['Actual'].update(actual)
        # Persist complete evidence before applying the quota necessary-condition gate.
        artifacts['candidates.json.gz'] = writer.compressed('candidates.json.gz', ledger)
        ledger_saved = True
        validate_eligibility(actual, ledger)
        report['Actual']['eligibility_necessary_condition'] = 'PASS'
        report['Status'] = 'PASS'
    except BaseException as exc:
        report['Status'] = getattr(exc, 'status', 'BLOCKED' if isinstance(exc, (OSError, MemoryError, subprocess.SubprocessError, KeyboardInterrupt, importlib.metadata.PackageNotFoundError)) else 'FAIL')
        report['error'] = {'type':type(exc).__name__, 'reason':str(exc), 'traceback':traceback.format_exc()}
    finally:
        report['Actual']['ledger_rows_retained'] = len(ledger)
        report['Actual']['source_rows_observed'] = len(ledger)
        report['Actual']['source_rows_completed'] = sum(row['decision'] != 'NOT_TESTED' for row in ledger)
        report['Actual']['tokenizer_calls'] = sum(row['tokenization_started'] for row in ledger)
        if not ledger_saved:
            try: artifacts['candidates.json.gz'] = writer.compressed('candidates.json.gz', ledger)
            except BaseException as exc:
                report['sealing_error'] = {'type':type(exc).__name__, 'reason':str(exc)}
                report['Status'] = 'BLOCKED' if report['Status'] != 'FAIL' else 'FAIL'
        try:
            if before is not None:
                require(old_namespace_pins(FRESH, OUT) == before, 'Prior fresh evidence changed')
                report['Actual']['old_fresh_after_status'] = 'PASS'
            for path, expected in input_pins.items(): require(pin(path) == expected, 'Protected source/tokenizer/metadata changed: ' + path)
            report['Actual']['input_after_status'] = 'PASS' if input_pins else 'NOT TESTED'
            if source_path is not None:
                require(pin(source_path) == CORPUS_PIN, 'Acquired corpus changed during eligibility')
                report['Actual']['corpus_after_status'] = 'PASS'
            if checked_git:
                checkout_guard(args.expected_head)
                report['Actual']['checkout_after_status'] = 'PASS'
        except BaseException as exc:
            report['Status'] = 'FAIL'
            report['custody_error'] = {'type':type(exc).__name__, 'reason':str(exc)}
        report['forbidden_imports'] = sorted(name for name in sys.modules if name.split('.')[0] in FORBIDDEN)
        if report['forbidden_imports']: report['Status'] = 'FAIL'
        for path in sorted(OUT.rglob('*')):
            if path.is_file() and str(path.relative_to(OUT)) not in artifacts: artifacts[str(path.relative_to(OUT))] = pin(path)
        report['artifacts'] = artifacts
        report['Actual']['evidence_bytes_before_manifest'] = writer.used()
        report['utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        final_manifest(writer, report)
    print(json.dumps({'Status':report['Status'], 'Actual':report['Actual'], 'error':report.get('error'), 'freshness':report['freshness']}, allow_nan=False), flush=True)
    return 0 if report['Status'] == 'PASS' else 2


if __name__ == '__main__': raise SystemExit(main())
