"""Independent data-only boundary/input audit; never imports builder or parser.

The original Parquet and tokenizer are read directly. The semantic decisions are
external frozen evidence, not inferred by this program. No weights or V1 scores
are inputs, and no Torch or model package is imported.
"""
import argparse
from collections import Counter
import datetime
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import sys
import traceback

CORPUS_SHA = '3ee89cd6a2ab912afd5d01e98867b46a67d9ec7a9eca0910e5e4c3cdd4cc1925'
TOKENIZER_SHA = 'e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77'
ROWS_SHA = '8a970098c794df2d25494abf3caf6cb8499f57cc54bca35e45b70e168f7d9a74'
EXPECTED_PACKAGES = {'numpy': '1.26.4', 'pyarrow': '19.0.1', 'tokenizers': '0.23.2'}
FORBIDDEN_MODULES = ('torch', 'parcae_lm', 'receval', 'transformers', 'open_mythos', 'boundary_parser', 'build_inputs')
SELECTION = 'first32 by ascending SHA256(stripped title + newline + exact concatenated body), after >=257-token filter'
REQUIRED_BUILD_CHECKS = {
    'no model imports before data preparation', 'frozen source identity requested',
    'implementation freeze identity', 'original corpus hash', 'original corpus bytes',
    'original tokenizer hash', 'frozen data-only runtime', 'complete original source row count',
    'two recorded semantic reviews agree with ledger', 'reviewed source partition and fixed selection',
    'source files unchanged', 'corpus tokenizer ledger and spec unchanged', 'no model imports after data preparation',
}


class AuditStop(Exception):
    def __init__(self, status, reason, actual=None):
        super().__init__(reason)
        self.status, self.actual = status, actual


def require(condition, reason, actual=None, status='FAIL'):
    if not condition:
        raise AuditStop(status, reason, actual)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def valid_digest(value, length=64):
    return isinstance(value, str) and len(value) == length and all(char in '0123456789abcdef' for char in value)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def strict_json(raw):
    def pairs(items):
        value = {}
        for key, item in items:
            require(key not in value, 'Duplicate JSON object key', key)
            value[key] = item
        return value

    def invalid_number(value):
        raise AuditStop('FAIL', 'Nonfinite JSON literal', value)
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid_number)


def file_record(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': digest(raw)}


def package_inventory():
    entries = [{'name': item.metadata['Name'], 'version': item.version,
                'location': str(Path(item.locate_file('')).resolve())}
               for item in importlib.metadata.distributions()]
    entries.sort(key=lambda item: (item['name'].casefold(), item['version'], item['location']))
    return {'entries': entries, 'aggregate_sha256': digest(canonical(entries))}


def forbidden_imports():
    return sorted(name for name in sys.modules
                  if any(name == prefix or name.startswith(prefix + '.') for prefix in FORBIDDEN_MODULES))


def independently_partition(rows, ledger, corpus_sha):
    """Reference from sorted accepted row intervals, independent of builder code."""
    require(isinstance(rows, list) and all(isinstance(row, str) for row in rows), 'Invalid source rows')
    require(isinstance(ledger, dict), 'Missing semantic ledger', status='BLOCKED')
    row_digest = digest(canonical(rows))
    require(ledger.get('corpus_sha256') == corpus_sha and ledger.get('rows_sha256') == row_digest
            and type(ledger.get('row_count')) is int and ledger['row_count'] == len(rows),
            'Semantic ledger does not identify exact corpus', status='BLOCKED')
    broad = [i for i, row in enumerate(rows) if row.strip().startswith('=') or row.strip().endswith('=')]
    decisions = ledger.get('decisions')
    require(isinstance(decisions, list), 'Missing ledger decisions', status='BLOCKED')
    seen, headers = set(), []
    for entry in decisions:
        require(isinstance(entry, dict), 'Invalid ledger entry', status='BLOCKED')
        position = entry.get('row')
        require(type(position) is int and position in broad and position not in seen,
                'Unknown or duplicate candidate identity', position, 'BLOCKED')
        seen.add(position)
        raw = rows[position]
        require(entry.get('row_sha256') == digest(raw.encode('utf-8')) and entry.get('title') == raw.strip(),
                'Ledger row bytes/title changed', position, 'BLOCKED')
        expected_neighbors = {'prev_row_sha256': digest(rows[position - 1].encode('utf-8')) if position else None,
                              'next_row_sha256': digest(rows[position + 1].encode('utf-8')) if position + 1 < len(rows) else None,
                              'structural_context': {'before_blank': position == 0 or not rows[position - 1].strip(),
                                                     'after_blank': position + 1 == len(rows) or not rows[position + 1].strip()}}
        require(all(field in entry and entry[field] == value for field, value in expected_neighbors.items()),
                'Ledger neighboring-row evidence changed', position, 'BLOCKED')
        require(isinstance(entry.get('reason'), str) and bool(entry['reason'].strip()),
                'Missing explicit semantic reason', position, 'BLOCKED')
        outcome = entry.get('decision')
        require(outcome in ('BODY', 'ACCEPT_TITLE'), 'Unresolved semantic decision', position, 'BLOCKED')
        if outcome == 'ACCEPT_TITLE':
            title = raw.strip()
            require(title.startswith('=') and title.endswith('=') and title.count('=') == 2,
                    'Accepted title has unexpected frozen syntax', position, 'BLOCKED')
            headers.append(position)
    require(seen == set(broad), 'Incomplete broad-candidate ledger', sorted(set(broad) - seen), 'BLOCKED')
    require(bool(headers), 'No accepted source title', status='BLOCKED')
    headers.sort()
    require(all(not value.strip() for value in rows[:headers[0]]),
            'Nonempty leading rows lack an accepted source', status='BLOCKED')
    roles = [{'row': i, 'role': 'LEADING', 'source_article_key': None, 'heading_row': None}
             for i in range(headers[0])]
    reconstructed = list(rows[:headers[0]])
    articles = []
    ownership = list(range(headers[0]))
    for start, stop in zip(headers, headers[1:] + [len(rows)]):
        positions = list(range(start + 1, stop))
        title = rows[start].strip()
        body = ''.join(rows[start + 1:stop])
        source_key = digest(canonical({'corpus_sha256': corpus_sha, 'heading_row': start, 'title': title}))
        articles.append({'heading_row': start, 'title': title, 'body_rows': positions,
                         'source_article_key': source_key, 'article_id': digest((title + '\n' + body).encode('utf-8')),
                         'text_sha256': digest(body.encode('utf-8'))})
        roles.append({'row': start, 'role': 'HEADING', 'source_article_key': source_key, 'heading_row': start})
        roles.extend({'row': i, 'role': 'BODY', 'source_article_key': source_key, 'heading_row': start} for i in positions)
        ownership.extend([start] + positions)
        reconstructed.append(rows[start])
        reconstructed.extend(rows[i] for i in positions)
    require(ownership == list(range(len(rows))) and len(set(ownership)) == len(rows),
            'Omitted, repeated or reordered source rows')
    require(reconstructed == rows and ''.join(reconstructed).encode('utf-8') == ''.join(rows).encode('utf-8'),
            'Source byte reconstruction changed')
    for field in ('source_article_key', 'article_id', 'text_sha256'):
        require(len({article[field] for article in articles}) == len(articles), 'Duplicate independent source identity', field)
    return {'corpus_sha256': corpus_sha, 'rows_sha256': row_digest,
            'corpus_utf8_sha256': digest(''.join(rows).encode('utf-8')), 'row_count': len(rows),
            'candidate_rows': broad, 'leading_rows': list(range(headers[0])),
            'articles': articles, 'row_roles': roles,
            'all_row_sha256': [digest(row.encode('utf-8')) for row in rows]}


def independently_tokenize(rows, partition, encode, selected_count=32):
    """Tokenize every reviewed source body, then apply the fixed hash ranking."""
    eligible = []
    for article in partition['articles']:
        text = ''.join(rows[i] for i in article['body_rows'])
        ids = encode(text)
        require(isinstance(ids, list) and all(type(token) is int and 0 <= token < 32768 for token in ids),
                'Tokenizer returned invalid IDs', article['source_article_key'])
        article['full_token_count'] = len(ids)
        article['eligible'] = len(ids) >= 257
        if article['eligible']:
            sample = {key: value for key, value in article.items() if key != 'eligible'}
            sample['tokens'] = ids[:257]
            eligible.append(sample)
    eligible.sort(key=lambda sample: sample['article_id'])
    require(len(eligible) >= selected_count, 'Insufficient reviewed eligible sources', len(eligible), 'BLOCKED')
    samples = eligible[:selected_count]
    for index, sample in enumerate(samples):
        tokens = sample['tokens']
        sample['index'] = index
        for field, vector in [('window_sha256', tokens), ('input_ids_sha256', tokens[:256]),
                              ('target_ids_sha256', tokens[1:257]), ('scored_target_ids_sha256', tokens[65:257])]:
            sample[field] = digest(canonical(vector))
    for field in ('source_article_key', 'text_sha256', 'article_id'):
        require(len({sample[field] for sample in samples}) == selected_count,
                'Selected sources are not distinct', field)
    return samples, len(eligible)


def validate_review(ledger, accepted):
    review = ledger.get('semantic_review')
    require(ledger.get('accepted_heading_rows') == accepted and isinstance(review, dict),
            'Missing or inconsistent review consensus', status='BLOCKED')
    require(review.get('agreement') is True and review.get('unresolved_rows') == []
            and review.get('not_human_or_external_independent_review') is True,
            'Unresolved review or incorrect independence claim', status='BLOCKED')
    for name in ('root', 'independent'):
        item = review.get(name)
        require(isinstance(item, dict) and item.get('verdict') == 'APPROVE'
                and item.get('accepted_heading_rows') == accepted and valid_digest(item.get('review_inventory_sha256')),
                'Missing completed semantic review', name, 'BLOCKED')
    require(review['root']['review_inventory_sha256'] == review['independent']['review_inventory_sha256'],
            'Reviewers used different context inventories', status='BLOCKED')
    require(valid_digest(review['independent'].get('report_sha256')), 'Missing review report identity', status='BLOCKED')


class Audit:
    def __init__(self, args):
        self.args, self.checks, self.bindings, self.actual = args, [], {}, {}

    def record(self, purpose, expected, actual, okay=True, status='FAIL'):
        result = 'PASS' if okay else status
        self.checks.append({'Purpose': purpose, 'Environment': 'CPU data-only independent audit',
                            'Input': {'run': str(self.args.run), 'repeat': str(self.args.repeat)},
                            'Expected': expected, 'Actual': actual, 'Status': result})
        require(okay, purpose, actual, status)

    def read_json(self, path):
        require(path.is_file(), 'Missing evidence file', str(path), 'BLOCKED')
        raw = path.read_bytes()
        info = {'bytes': len(raw), 'sha256': digest(raw)}
        require(str(path) not in self.bindings or self.bindings[str(path)] == info,
                'Evidence changed between reads', str(path))
        self.bindings[str(path)] = info
        return strict_json(raw)

    def execute(self):
        args = self.args
        custody_before = {}
        packages_before = package_inventory()
        try:
            self.record('No model packages imported before audit', [], forbidden_imports(), not forbidden_imports())
            for path in (args.corpus, args.tokenizer, args.ledger):
                self.record('Required original input exists', True, str(path), path.is_file(), 'BLOCKED')
                custody_before[str(path)] = file_record(path)
            self.record('Original corpus byte identity', {'bytes': 731216, 'sha256': CORPUS_SHA},
                        custody_before[str(args.corpus)], custody_before[str(args.corpus)] == {'bytes': 731216, 'sha256': CORPUS_SHA})
            self.record('Original tokenizer identity', TOKENIZER_SHA, custody_before[str(args.tokenizer)]['sha256'],
                        custody_before[str(args.tokenizer)]['sha256'] == TOKENIZER_SHA)
            import pyarrow
            import pyarrow.parquet as parquet
            import numpy
            import tokenizers
            runtime = {'python_version': platform.python_version(), 'executable': sys.executable, 'prefix': sys.prefix,
                       'pyarrow_version': pyarrow.__version__, 'numpy_version': numpy.__version__,
                       'tokenizers_version': tokenizers.__version__, 'torch_imported': bool(forbidden_imports()),
                       'package_locations': {'pyarrow': pyarrow.__file__, 'numpy': numpy.__file__, 'tokenizers': tokenizers.__file__}}
            expected_runtime = {'python_version': '3.12.3', 'torch_imported': False,
                                **{name + '_version': version for name, version in EXPECTED_PACKAGES.items()}}
            self.record('Actual data-only interpreter and package versions', expected_runtime, runtime,
                        all(runtime.get(key) == value for key, value in expected_runtime.items()), 'BLOCKED')
            self.actual['runtime'] = runtime
            rows = parquet.read_table(args.corpus, columns=['text']).column('text').to_pylist()
            self.record('Direct complete Parquet decoding', {'rows': 4358, 'rows_sha256': ROWS_SHA},
                        {'rows': len(rows), 'rows_sha256': digest(canonical(rows))},
                        len(rows) == 4358 and digest(canonical(rows)) == ROWS_SHA and all(isinstance(row, str) for row in rows))
            ledger = self.read_json(args.ledger)
            partition = independently_partition(rows, ledger, CORPUS_SHA)
            accepted = [article['heading_row'] for article in partition['articles']]
            validate_review(ledger, accepted)
            self.record('Complete corpus-bound review and independent row-span partition',
                        'all 710 broad candidates resolved; each source row assigned once',
                        {'broad_candidates': len(partition['candidate_rows']), 'accepted_heading_rows': accepted,
                         'source_rows': len(partition['row_roles']), 'leading_rows': partition['leading_rows']},
                        len(partition['candidate_rows']) == 710 and len(partition['row_roles']) == 4358)
            tokenizer = tokenizers.Tokenizer.from_file(str(args.tokenizer))
            samples, eligible_count = independently_tokenize(rows, partition,
                                                            lambda text: tokenizer.encode(text, add_special_tokens=False).ids)
            expected_inputs = {'samples': samples, 'selection': SELECTION, 'context_tokens': 256, 'window_tokens': 257,
                               'scored_logit_positions': [64, 256], 'scored_tokens_per_sample': 192,
                               'corpus_sha256': CORPUS_SHA, 'rows_sha256': ROWS_SHA,
                               'data_role': 'historical development; not fresh-test'}
            expected_counts = {'row_count': 4358, 'source_article_count': len(accepted),
                               'eligible_article_count': eligible_count, 'selected_sample_count': 32,
                               'scored_tokens_per_sample': 192}
            manifests, process_ids = [], []
            for label, root in [('first', args.run), ('repeat', args.repeat)]:
                completion = self.read_json(root / 'completion.json')
                require(isinstance(completion, dict), 'Missing completion object', label, 'BLOCKED')
                process_id = completion.get('process_id')
                self.record('Recorded builder process identity ' + label, 'positive integer PID', process_id,
                            type(process_id) is int and process_id > 0, 'BLOCKED' if process_id is None else 'FAIL')
                process_ids.append(process_id)
                self.record('Successful clean builder completion ' + label, 'PASS; error null; cleanup_errors empty',
                            {key: completion.get(key) for key in ('status', 'Status', 'error', 'cleanup_errors')},
                            completion.get('status') == completion.get('Status') == 'PASS'
                            and 'error' in completion and completion['error'] is None and completion.get('cleanup_errors') == [],
                            'BLOCKED' if completion.get('status') in (None, 'BLOCKED', 'NOT TESTED') else 'FAIL')
                manifest = self.read_json(root / 'manifest.json')
                require(isinstance(manifest, dict), 'Missing builder manifest', label, 'BLOCKED')
                manifests.append(manifest)
                self.record('Completion binds manifest ' + label, file_record(root / 'manifest.json')['sha256'],
                            completion.get('manifest_sha256'), completion.get('manifest_sha256') == file_record(root / 'manifest.json')['sha256'])
                recorded_runtime = manifest.get('runtime')
                self.record('Recorded runtime matches audit runtime except bound process ID ' + label,
                            dict(runtime, pid=process_id),
                            {'manifest': manifest.get('runtime'), 'completion': completion.get('Environment')},
                            isinstance(recorded_runtime, dict) and recorded_runtime == completion.get('Environment')
                            and type(recorded_runtime.get('pid')) is int and recorded_runtime['pid'] == process_id
                            and {key: value for key, value in recorded_runtime.items() if key != 'pid'} == runtime)
                expected_manifest = {'status': 'PASS', 'protocol': 'MYTHOS-DATA-BOUNDARY-REPAIR-V1',
                                     'counts': expected_counts, 'accepted_heading_rows': accepted, 'rows_sha256': ROWS_SHA,
                                     'corpus_utf8_sha256': partition['corpus_utf8_sha256'],
                                     'ledger_sha256': custody_before[str(args.ledger)]['sha256'], 'selection': SELECTION,
                                     'torch_imported': False, 'model_execution': 'NOT TESTED', 'scientific_performance_evidence': 'NOT TESTED'}
                self.record('Manifest identity and measured counts ' + label, expected_manifest,
                            {key: manifest.get(key) for key in expected_manifest},
                            all(manifest.get(key) == value for key, value in expected_manifest.items())
                            and valid_digest(manifest.get('frozen_commit'), 40))
                self.record('Completion data-only boundary ' + label, expected_counts, completion.get('Actual'),
                            completion.get('Actual') == expected_counts and completion.get('torch_imported') is False
                            and completion.get('model_execution') == completion.get('scientific_performance_evidence') == 'NOT TESTED')
                journal_path = root / 'checks.jsonl'
                require(journal_path.is_file(), 'Missing builder check journal', label, 'BLOCKED')
                journal = [strict_json(line) for line in journal_path.read_text(encoding='utf-8').splitlines()]
                names = [item.get('Purpose') for item in journal if isinstance(item, dict)]
                self.record('All builder checks bind to complete journal ' + label, sorted(REQUIRED_BUILD_CHECKS),
                            {'names': names, 'journal_equal': journal == completion.get('checks')},
                            journal == completion.get('checks') and REQUIRED_BUILD_CHECKS.issubset(names)
                            and len(names) == len(journal) and all(item.get('Status') == 'PASS' for item in journal))
                artifacts = manifest.get('artifacts')
                self.record('Exactly frozen payload artifact set ' + label, ['checks.jsonl', 'inputs.json', 'partition.json'],
                            sorted(artifacts) if isinstance(artifacts, dict) else artifacts,
                            isinstance(artifacts, dict) and set(artifacts) == {'checks.jsonl', 'inputs.json', 'partition.json'})
                for name, expected_info in artifacts.items():
                    path = root / name
                    actual_info = file_record(path)
                    custody_before[str(path)] = actual_info
                    self.record('Manifest artifact bytes ' + label + '/' + name, expected_info, actual_info, actual_info == expected_info)
                actual_partition = self.read_json(root / 'partition.json')
                actual_inputs = self.read_json(root / 'inputs.json')
                self.record('Independent full source partition comparison ' + label, digest(canonical(partition)),
                            digest(canonical(actual_partition)), actual_partition == partition)
                self.record('Independent tokenization, source identities and first32 selection ' + label,
                            digest(canonical(expected_inputs)), digest(canonical(actual_inputs)), actual_inputs == expected_inputs)
                sources, source_files = manifest.get('sources'), manifest.get('source_files')
                require(isinstance(sources, dict) and len(sources) == 4 and isinstance(source_files, dict) and bool(source_files),
                        'Invalid source custody manifest', label)
                required_paths = {str(args.corpus), str(args.tokenizer), str(args.ledger)}
                require(required_paths.issubset(sources), 'Builder used different input paths', label)
                other_paths = set(sources) - required_paths
                require(len(other_paths) == 1, 'Ambiguous builder spec source', label)
                spec_path = Path(next(iter(other_paths)))
                require(spec_path.is_absolute() and spec_path.suffix == '.json', 'Unexpected builder spec path', str(spec_path))
                spec = self.read_json(spec_path)
                require(spec == completion.get('Input') and spec.get('output_dir') == str(root)
                        and spec.get('frozen_commit') == manifest['frozen_commit'], 'Builder spec provenance mismatch', label)
                for key in ('corpus', 'tokenizer', 'ledger'):
                    require(spec.get(key) == str(getattr(args, key)), 'Builder spec source mismatch', key)
                for path_string, expected_info in {**sources, **source_files}.items():
                    path = Path(path_string)
                    require(path.is_absolute() and (path_string in sources or path.suffix in ('.py', '.md')),
                            'Unexpected source custody path', path_string)
                    actual_info = file_record(path)
                    self.record('Protected source bytes remain frozen ' + label, expected_info, actual_info, actual_info == expected_info)
                    custody_before[path_string] = actual_info
                source_hashes = {info['sha256'] for info in source_files.values()}
                self.record('Frozen audit and semantic report source identities ' + label,
                            'current auditor and independent review report hashes present',
                            {'auditor_sha256': file_record(Path(__file__))['sha256'],
                             'review_report_sha256': ledger['semantic_review']['independent']['report_sha256']},
                            file_record(Path(__file__))['sha256'] in source_hashes
                            and ledger['semantic_review']['independent']['report_sha256'] in source_hashes)
            self.record('One frozen implementation across the two builder processes', manifests[0]['frozen_commit'],
                        manifests[1]['frozen_commit'], manifests[0]['frozen_commit'] == manifests[1]['frozen_commit']
                        and manifests[0]['source_files'] == manifests[1]['source_files'])
            self.record('Distinct recorded builder process identities', 'two different PIDs', process_ids,
                        len(set(process_ids)) == 2)
            for name in ('partition.json', 'inputs.json'):
                first, repeat = (args.run / name).read_bytes(), (args.repeat / name).read_bytes()
                self.record('Independent process byte repeat ' + name, digest(first), digest(repeat), first == repeat)
            self.actual.update({'counts': expected_counts, 'accepted_heading_rows': accepted, 'builder_process_ids': process_ids,
                                'partition_sha256': file_record(args.run / 'partition.json')['sha256'],
                                'inputs_sha256': file_record(args.run / 'inputs.json')['sha256'],
                                'selected_sources': [{key: sample[key] for key in ('index', 'source_article_key', 'article_id', 'heading_row',
                                                                                'text_sha256', 'full_token_count', 'window_sha256')}
                                                     for sample in samples]})
        finally:
            # Preserve custody even when an earlier evidence check has stopped.
            for path, info in self.bindings.items():
                require(path not in custody_before or custody_before[path] == info,
                        'Source changed before its later evidence read', path)
                custody_before.setdefault(path, info)
            after = {path: file_record(Path(path)) for path in custody_before}
            self.record('All audit-read source and payload files unchanged', custody_before, after, after == custody_before)
            packages_after = package_inventory()
            self.record('Installed distribution inventory unchanged', packages_before['aggregate_sha256'],
                        packages_after['aggregate_sha256'], packages_before == packages_after)
            self.actual['package_inventory_before_sha256'] = packages_before['aggregate_sha256']
            self.actual['package_inventory_after_sha256'] = packages_after['aggregate_sha256']
            self.actual['forbidden_imports'] = forbidden_imports()
            self.record('No Torch or model package imported by audit', [], forbidden_imports(), not forbidden_imports())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('corpus', 'tokenizer', 'ledger', 'run', 'repeat', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    for name, path in vars(args).items():
        if not path.is_absolute():
            parser.error('--' + name + ' must be absolute')
        setattr(args, name, path.resolve())
    if (args.output.exists() or args.output.is_relative_to(args.run) or args.output.is_relative_to(args.repeat)
            or args.output in (args.corpus, args.tokenizer, args.ledger, Path(__file__).resolve())
            or args.run == args.repeat):
        parser.error('Output must be new and external; run/repeat must be distinct')
    audit = Audit(args)
    status, error = 'PASS', None
    try:
        audit.execute()
    except AuditStop as exc:
        status, error = exc.status, {'reason': str(exc), 'actual': exc.actual}
    except Exception as exc:
        status, error = 'BLOCKED', {'reason': repr(exc), 'traceback': traceback.format_exc()}
    result = {'Purpose': 'Independent source-boundary/token verification and deterministic repeat audit',
              'Environment': 'Data-only; no parser/builder import or model/weights/scores',
              'Input': {key: str(value) for key, value in vars(args).items() if key != 'output'},
              'Expected': {'source_rows': 4358, 'broad_candidates': 710, 'selected_sources': 32},
              'Actual': audit.actual, 'Status': status, 'error': error, 'checks': audit.checks,
              'check_counts': dict(Counter(check['Status'] for check in audit.checks)), 'file_bindings': audit.bindings,
              'source_sha256': file_record(Path(__file__))['sha256'],
              'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'limitations': ['Semantic title decisions are frozen review inputs, not inferred from syntax by this audit.',
                             'No model quality, V1 score repair, iid sampling or absence of pretraining overlap is established.',
                             'No human, Claude Code, Grok or independent third-party review is claimed.']}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8', newline='\n') as handle:
        json.dump(result, handle, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        handle.write('\n')
    print(json.dumps({'Status': status, 'output': str(args.output), 'error': error}))
    return 0 if status == 'PASS' else 2


if __name__ == '__main__':
    sys.exit(main())
