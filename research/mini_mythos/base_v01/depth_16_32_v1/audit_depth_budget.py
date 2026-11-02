"""Read-only evidence audit for the frozen CPU depth-budget diagnostic.

Standard library only. Never imports a model/tokenizer/Torch, restores RNG state,
reruns a forward pass, or modifies the source run/input files.
"""
import argparse
from collections import Counter
import datetime
import hashlib
import itertools
import json
import math
from pathlib import Path
import random
import statistics
import sys
import traceback

DEPTHS = (8, 16, 32)
SEEDS = (3101, 3202, 3303)
ARTICLES = 32
TARGETS = 192
BOOTSTRAPS = 10000
BOOTSTRAP_SEED = 20261101
ARITHMETIC_TOLERANCE = 1e-10
UPSTREAM = '69284c13746e849104f738d6d1a347b1f457df76'
WEIGHTS = 'ed6eb306464dd0d694e9eacd58f7e06ac3e44b43cb7c5c79dbcb1543059c6621'
CONFIG = '5c8fc785c2f6dba67d0370ad715034860e3b22bfce850da825c06baa03923c13'
TOKENIZER = 'e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77'
CORPUS = '3ee89cd6a2ab912afd5d01e98867b46a67d9ec7a9eca0910e5e4c3cdd4cc1925'
CORRECTED_INPUTS = '3abb324ea2876abb78e18d86ec257a9e1d388f9501bd8cdd6c99011ac11cf41e'
CORRECTED_PARTITION = '95a217a815596c928a0b721837b567a08ed8c6f667839fdf6d4311113c253aa4'
CORRECTED_LEDGER = 'f5f7858b989451671e4c7ed27192642dec3f9b2a1ccd214cc9e3cc30bcebb5d3'
ORDERS = tuple(itertools.permutations(DEPTHS))
CONTROL_NAMES = ('native8', 'wrapper8', 'observed8', 'observed8_repeat',
                 'causal8_mut', 'causal16_base', 'causal16_mut', 'causal32_base', 'causal32_mut')
REQUIRED_CHECKS = {
    'control native-wrapper exact', 'control observer no-op exact',
    'control observed repeat exact', 'control causality depth 8',
    'control causality depth 16', 'control causality depth 32',
    'state exact restore', 'state invariant', 'protected files invariant',
    'upstream invariant', 'repo invariant', 'complete formal coverage',
    'actual parameter inventory', 'CPU runtime after import',
    'CPU runtime after load', 'CPU runtime after evaluation', 'package inventory invariant',
}
FORMAL_CHECKS = (
    'forward shape dtype and finite', 'forward validation consumes no RNG',
    'actual h0 and block coverage', 'paired actual h0 and CPU RNG',
    'independent double NLL equality', 'scoring consumes no CPU RNG',
)
EXPECTED_RUNTIME = {
    'python_version': '3.12.3', 'torch_version': '2.11.0+cpu',
    'default_device': 'cpu', 'default_dtype': 'torch.float32',
    'intraop_threads': 2, 'interop_threads': 1,
    'deterministic_algorithms': True, 'deterministic_warn_only': False,
    'autocast_cpu_enabled': False, 'autocast_cuda_enabled': False,
    'cuda_available': False,
}


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def digest_text(value, length=64):
    return isinstance(value, str) and len(value) == length and all(c in '0123456789abcdef' for c in value)


def canonical_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                                     allow_nan=False).encode('utf-8')).hexdigest()


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate JSON key: ' + key)
            result[key] = value
        return result

    def bad_number(value):
        raise ValueError('Nonfinite JSON literal: ' + value)

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=bad_number)


def nearest_rank(values, probability):
    ordered = sorted(values)
    return ordered[max(0, math.ceil(probability * len(ordered)) - 1)]


def corrected_source_errors(samples, partition, ledger):
    """Bind measured rows to the already approved source partition, not syntax."""
    errors = []
    if not isinstance(partition, dict) or not isinstance(ledger, dict):
        return [{'reason': 'missing corrected partition or ledger object'}]
    articles = partition.get('articles')
    if not isinstance(articles, list) or not all(isinstance(article, dict) for article in articles):
        return [{'reason': 'invalid partition article list'}]
    by_source = {article.get('source_article_key'): article for article in articles
                 if isinstance(article.get('source_article_key'), str)}
    if len(by_source) != len(articles):
        errors.append({'reason': 'duplicate or invalid partition source keys'})
    accepted = [article.get('heading_row') for article in articles]
    decisions = ledger.get('decisions')
    if (not all(type(row) is int for row in accepted) or accepted != sorted(set(accepted))
            or ledger.get('accepted_heading_rows') != accepted
            or not isinstance(decisions, list)
            or sorted(item.get('row') for item in decisions if isinstance(item, dict)
                      and item.get('decision') == 'ACCEPT_TITLE') != accepted):
        errors.append({'reason': 'partition headings do not match reviewed ledger'})
    if partition.get('corpus_sha256') != CORPUS or ledger.get('corpus_sha256') != CORPUS:
        errors.append({'reason': 'incorrect original corpus binding'})
    if partition.get('rows_sha256') != ledger.get('rows_sha256'):
        errors.append({'reason': 'decoded-row identity disagreement'})
    if len({sample.get('source_article_key') for sample in samples}) != len(samples):
        errors.append({'reason': 'selected source keys are not unique'})
    fields = ('article_id', 'title', 'heading_row', 'body_rows', 'source_article_key', 'text_sha256', 'full_token_count')
    for sample in samples:
        key = sample.get('source_article_key')
        article = by_source.get(key)
        if article is None:
            errors.append({'reason': 'selected source missing from partition', 'index': sample.get('index')})
            continue
        expected_key = canonical_digest({'corpus_sha256': CORPUS, 'heading_row': article.get('heading_row'),
                                         'title': article.get('title')})
        mismatch = [field for field in fields if sample.get(field) != article.get(field)]
        if key != expected_key or not digest_text(key) or mismatch:
            errors.append({'reason': 'corrected source metadata mismatch', 'index': sample.get('index'), 'fields': mismatch})
    return errors


class Audit:
    def __init__(self, run, inputs, partition=None, ledger=None):
        self.run, self.inputs = run, inputs
        self.partition, self.ledger = partition, ledger
        self.checks, self.failures, self.blockers = [], [], []
        self.bindings, self.actual = {}, {}
        self.journal = []

    def issue(self, reason, actual=None, blocked=False):
        (self.blockers if blocked else self.failures).append({'reason': reason, 'actual': actual})

    def check(self, purpose, expected, actual, okay, blocked=False):
        status = 'PASS' if okay else 'BLOCKED' if blocked else 'FAIL'
        self.checks.append({'Purpose': purpose, 'Environment': 'saved evidence; Python standard library only',
                            'Input': str(self.run), 'Expected': expected, 'Actual': actual, 'Status': status})
        if not okay:
            self.issue(purpose, actual, blocked)

    def read(self, path):
        if not path.is_file():
            self.issue('Missing evidence file', str(path), blocked=True)
            return None
        raw = path.read_bytes()
        self.bindings[str(path)] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        return raw.decode('utf-8')

    def load(self, path):
        raw = self.read(path)
        return strict_json(raw) if raw is not None else None

    def check_terminal(self, completion):
        status = completion.get('status')
        blocked = status in (None, 'BLOCKED', 'NOT TESTED')
        self.check('Successful runner terminal status', 'PASS', status, status == 'PASS', blocked=blocked)
        for field, expected in [('error', None), ('cleanup_errors', [])]:
            present = field in completion
            self.check('Clean runner terminal field ' + field, expected,
                       {'present': present, 'value': completion.get(field)},
                       present and completion[field] == expected,
                       blocked=not present or blocked)

    def check_corrected_sources(self, samples):
        material = {}
        for name, path, expected in [('partition', self.partition, CORRECTED_PARTITION),
                                     ('ledger', self.ledger, CORRECTED_LEDGER)]:
            if path is None:
                self.issue('Missing explicit corrected ' + name + ' path', blocked=True)
                continue
            material[name] = self.load(path)
            recorded = self.bindings.get(str(path), {}).get('sha256')
            self.check('Immutable corrected ' + name + ' SHA256', expected, recorded,
                       recorded == expected, blocked=recorded is None)
        if isinstance(material.get('partition'), dict) and isinstance(material.get('ledger'), dict):
            errors = corrected_source_errors(samples, material['partition'], material['ledger'])
            self.check('Reviewed source identity, heading and body-span bindings', '32 unique ledger-approved source articles',
                       errors, not errors)

    def check_recorded_checks(self, completion):
        collected = []
        for field in ('control_checks', 'preservation_checks'):
            value = completion.get(field)
            if not isinstance(value, list) or not value:
                self.issue('Missing recorded check list', field, blocked=True)
                continue
            collected.extend(value)
        journal_raw = self.read(self.run / 'checks.jsonl')
        if journal_raw is not None:
            journal = [strict_json(line) for line in journal_raw.splitlines()]
            for field, phase in [('control_checks', 'controls'), ('preservation_checks', 'preservation')]:
                expected = [row for row in journal if isinstance(row, dict)
                            and isinstance(row.get('Input'), dict) and row['Input'].get('phase') == phase]
                actual = completion.get(field)
                self.check('Check journal/completion binding ' + field, len(expected),
                           {'recorded': len(actual) if isinstance(actual, list) else None, 'equal': actual == expected},
                           actual == expected, blocked=actual is None)
            collected = journal
            self.journal = journal
        names = []
        for item in collected:
            if not isinstance(item, dict) or not isinstance(item.get('name'), str):
                self.issue('Invalid recorded check', item)
                continue
            names.append(item['name'])
            lower, upper = item.get('status'), item.get('Status')
            if lower is not None and upper is not None and lower != upper:
                self.issue('Conflicting recorded check statuses', item)
            status = lower if lower is not None else upper
            if status != 'PASS':
                self.issue('Runner check did not pass', {'name': item['name'], 'status': status},
                           blocked=status in (None, 'BLOCKED', 'NOT TESTED'))
        missing = sorted(REQUIRED_CHECKS - set(names))
        self.check('Required control and preservation checks present', sorted(REQUIRED_CHECKS),
                   {'name_counts': dict(Counter(names)), 'missing': missing}, not missing, blocked=True)
        for depth in DEPTHS:
            records = [item for item in collected if isinstance(item, dict)
                       and item.get('name') == 'control causality depth ' + str(depth)]
            self.check('One causal-prefix check at depth ' + str(depth), 1, len(records), len(records) == 1,
                       blocked=not records)
            if len(records) == 1:
                value = records[0].get('Actual')
                valid = (isinstance(value, dict) and value.get('prefix_tokens') == 128
                         and digest_text(value.get('baseline_prefix_sha256'))
                         and value.get('baseline_prefix_sha256') == value.get('mutated_prefix_sha256')
                         and value.get('bytewise_equal') is True and value.get('h0_equal') is True
                         and value.get('rng_after_equal') is True)
                self.check('Recorded causal-prefix digests agree at depth ' + str(depth),
                           '128-token prefix: equal valid digests plus byte/h0/RNG comparisons', value, valid)

    def check_state(self, completion, environment):
        before, after = self.load(self.run / 'state_before.json'), self.load(self.run / 'state_after.json')
        for label, state in [('before', before), ('after', after)]:
            if state is None:
                continue
            if not isinstance(state, dict):
                self.issue('State manifest is not an object', label)
                continue
            entries = state.get('entries') if isinstance(state, dict) else None
            valid = isinstance(entries, dict) and len(entries) == 63 and state.get('state_count') == 63
            if valid:
                for name, entry in entries.items():
                    valid = valid and isinstance(name, str) and isinstance(entry, dict)
                    if not valid:
                        break
                    valid = (isinstance(entry.get('shape'), list)
                             and all(type(n) is int and n >= 0 for n in entry['shape'])
                             and entry.get('dtype') == 'torch.float32'
                             and type(entry.get('bytes')) is int and entry['bytes'] >= 0
                             and entry['bytes'] == math.prod(entry['shape']) * 4
                             and digest_text(entry.get('sha256')))
                    if not valid:
                        break
            valid = valid and digest_text(state.get('aggregate_sha256'))
            valid = valid and state['aggregate_sha256'] == canonical_digest(entries)
            self.check('Recorded state manifest structure ' + label, '63 typed, shaped, hashed entries',
                       {'state_count': state.get('state_count'), 'aggregate_sha256': state.get('aggregate_sha256')}, valid)
            parameter_names = state.get('parameter_names')
            parameter_valid = (valid and isinstance(parameter_names, list) and len(parameter_names) == 61
                               and all(isinstance(name, str) for name in parameter_names)
                               and len(set(parameter_names)) == 61 and parameter_names == sorted(parameter_names)
                               and all(name in entries for name in parameter_names))
            counted = sum(math.prod(entries[name]['shape']) for name in parameter_names) if parameter_valid else None
            parameter_valid = (parameter_valid and counted == 144323136
                               and state.get('parameter_count') == 144323136 and state.get('unique_parameter_tensors') == 61)
            self.check('Measured unique parameter inventory ' + label,
                       {'parameter_count': 144323136, 'unique_parameter_tensors': 61},
                       {'parameter_count': state.get('parameter_count'), 'unique_parameter_tensors': state.get('unique_parameter_tensors'),
                        'counted_from_unique_names_and_shapes': counted}, parameter_valid,
                       blocked=parameter_names is None)
        if isinstance(before, dict) and isinstance(after, dict):
            same = before == after
            self.check('Recorded parameters and buffers preserved', 'identical before/after manifests',
                       {'identical': same}, same)
            for label, state in [('before', before), ('after', after)]:
                reported = completion.get('state_' + label + '_sha256')
                self.check('Completion state hash binding ' + label, state.get('aggregate_sha256'), reported,
                           reported == state.get('aggregate_sha256') and digest_text(reported),
                           blocked=reported is None)
            self.check('Environment original state digest binding', before.get('aggregate_sha256'),
                       environment.get('state_before_sha256'),
                       environment.get('state_before_sha256') == before.get('aggregate_sha256')
                       and digest_text(environment.get('state_before_sha256')),
                       blocked='state_before_sha256' not in environment)
            records = [item for item in self.journal if isinstance(item, dict)
                       and item.get('name') == 'actual parameter inventory']
            self.check('One measured parameter inventory check', 1, len(records), len(records) == 1,
                       blocked=not records)
            if len(records) == 1:
                expected = {name: before.get(name) for name in ('parameter_count', 'unique_parameter_tensors', 'parameter_names')}
                self.check('Parameter inventory check/state binding', expected, records[0].get('Actual'),
                           records[0].get('Actual') == expected)

    def check_runtime_and_packages(self, environment):
        snapshots = [('runtime_after_import', environment.get('runtime_after_import')),
                     ('runtime_after_load', environment.get('runtime_after_load'))]
        for name, phase in [('CPU runtime after import', 'runtime_after_import'),
                            ('CPU runtime after load', 'runtime_after_load'),
                            ('CPU runtime after evaluation', 'runtime_after_evaluation')]:
            records = [item for item in self.journal if isinstance(item, dict) and item.get('name') == name]
            self.check('One actual runtime check ' + name, 1, len(records), len(records) == 1,
                       blocked=not records)
            if len(records) == 1:
                value = records[0].get('Actual')
                if phase in environment:
                    self.check('Runtime check/environment binding ' + name, environment[phase], value,
                               value == environment[phase])
                else:
                    snapshots.append((phase, value))
        for phase, value in snapshots:
            valid = (isinstance(value, dict)
                     and all(value.get(name) == expected and type(value.get(name)) is type(expected)
                             for name, expected in EXPECTED_RUNTIME.items())
                     and isinstance(value.get('executable'), str) and bool(value['executable'])
                     and isinstance(value.get('prefix'), str) and bool(value['prefix']))
            self.check('Actual runtime getters ' + phase, EXPECTED_RUNTIME, value, valid,
                       blocked=value is None)
        packages = {}
        for label in ('before', 'after'):
            value = self.load(self.run / ('packages_' + label + '.json'))
            packages[label] = value
            if value is None:
                continue
            entries = value.get('entries') if isinstance(value, dict) else None
            valid = (isinstance(entries, list) and bool(entries)
                     and all(isinstance(entry, dict) and all(isinstance(entry.get(k), str) and bool(entry[k])
                                                            for k in ('name', 'version', 'location')) for entry in entries))
            if valid:
                valid = (entries == sorted(entries, key=lambda entry: (entry['name'].casefold(), entry['version'], entry['location']))
                         and digest_text(value.get('aggregate_sha256'))
                         and value['aggregate_sha256'] == canonical_digest(entries))
            self.check('Measured package inventory ' + label, 'canonical sorted distribution entries and matching SHA256',
                       {'entries': len(entries) if isinstance(entries, list) else None,
                        'aggregate_sha256': value.get('aggregate_sha256') if isinstance(value, dict) else None}, valid)
        before, after = packages['before'], packages['after']
        if isinstance(before, dict) and isinstance(after, dict):
            self.check('Installed package inventory preserved', 'before and after exactly equal',
                       {'equal': before == after}, before == after)
            self.check('Environment package inventory binding', before.get('aggregate_sha256'),
                       environment.get('packages_before_sha256'),
                       environment.get('packages_before_sha256') == before.get('aggregate_sha256')
                       and digest_text(environment.get('packages_before_sha256')),
                       blocked='packages_before_sha256' not in environment)

    def check_formal_journal(self, rows):
        grouped = {name: {} for name in FORMAL_CHECKS}
        errors = []
        for item in self.journal:
            if not isinstance(item, dict) or item.get('name') not in grouped:
                continue
            context = item.get('Input')
            if not isinstance(context, dict) or context.get('phase') != 'formal':
                continue
            a, r, d = context.get('article_index'), context.get('replica'), context.get('depth')
            if type(a) is not int or not 0 <= a < ARTICLES or type(r) is not int or not 0 <= r < 3 or type(d) is not int or d not in DEPTHS:
                errors.append({'reason': 'invalid formal check context', 'name': item['name'], 'context': context})
                continue
            key = (a, r, d)
            entries = grouped[item['name']].setdefault(key, [])
            entries.append(item)
            if len(entries) > 1:
                errors.append({'reason': 'duplicate mandatory row check', 'name': item['name'], 'key': key})
            if key not in rows:
                # Interrupted forwards can have check records without a completed row.
                self.issue('Formal check has no completed row', {'name': item['name'], 'key': key}, blocked=True)
                continue
            row, value, name = rows[key], item.get('Actual'), item['name']
            if name == 'forward shape dtype and finite':
                okay = isinstance(value, dict) and value.get('shape') == [1, 256, 32768] and value.get('dtype') == 'torch.float32' and value.get('depth') == d
            elif name == 'actual h0 and block coverage':
                okay = (isinstance(value, dict) and value.get('h0_calls') == 1
                        and value.get('h0_sha256') == row.get('h0_sha256') and value.get('block_calls') == row.get('block_calls'))
            elif name == 'paired actual h0 and CPU RNG':
                okay = (isinstance(value, dict) and value.get('article_index') == a and value.get('replica') == r and value.get('depth') == d
                        and value.get('identity') == [row.get(field) for field in ('h0_sha256', 'rng_before_sha256', 'rng_after_sha256')])
            elif name == 'independent double NLL equality':
                expected = item.get('Expected')
                okay = (isinstance(value, dict) and value.get('scored_tokens') == TARGETS and finite(value.get('max_abs_error'))
                        and 0 <= value['max_abs_error'] <= ARITHMETIC_TOLERANCE
                        and isinstance(expected, dict) and expected.get('atol') == ARITHMETIC_TOLERANCE
                        and expected.get('rtol') == 0 and expected.get('scored_tokens') == TARGETS)
            else:
                okay = item.get('status') == 'PASS' and item.get('Status') == 'PASS'
            if not okay:
                errors.append({'reason': 'mandatory check does not bind to row', 'name': name, 'key': key, 'actual': value})
        self.check('Mandatory row checks match recorded numerical/RNG evidence', 'no duplicates or contradictory bindings',
                   errors, not errors)
        expected_keys = {(a, r, d) for a in range(ARTICLES) for r in range(3) for d in DEPTHS}
        for name, mapping in grouped.items():
            missing = sorted(expected_keys - set(mapping))
            self.check('All formal row checks: ' + name, 288,
                       {'unique_row_contexts': len(mapping), 'records': sum(len(v) for v in mapping.values()), 'missing': missing},
                       not missing and len(mapping) == 288 and all(len(v) == 1 for v in mapping.values()), blocked=True)

    def check_protected(self, environment):
        before = self.load(self.run / 'protected_before.json')
        after = self.load(self.run / 'protected_after.json')
        if before is None or after is None:
            return
        if not isinstance(before, dict) or not isinstance(after, dict):
            self.issue('Protected manifest is not an object')
            return
        self.check('Recorded protected source/input manifests preserved', 'identical before/after records',
                   {'equal': before == after}, before == after)
        files = before.get('files') if isinstance(before, dict) else None
        valid = isinstance(files, dict) and bool(files)
        if valid:
            valid = all(isinstance(name, str) and isinstance(entry, dict)
                        and type(entry.get('bytes')) is int and entry['bytes'] >= 0
                        and digest_text(entry.get('sha256')) for name, entry in files.items())
        self.check('Protected file manifest schemas', 'nonempty path/byte/SHA256 mapping',
                   {'files': len(files) if isinstance(files, dict) else None}, valid)
        if isinstance(before, dict):
            self.check('Protected upstream identity', {'head': UPSTREAM, 'status': ''}, before.get('upstream'),
                       before.get('upstream') == {'head': UPSTREAM, 'status': ''})
            repo = before.get('repo', {})
            self.check('Protected execution checkout identity', 'clean checkout bound to environment execution_head', repo,
                       isinstance(repo, dict) and repo.get('status') == '' and repo.get('head') == environment.get('execution_head'))
        if valid:
            values = {entry['sha256'] for entry in files.values()}
            for name, expected in [('original weights', WEIGHTS), ('original config', CONFIG), ('original tokenizer', TOKENIZER),
                                   ('inputs', self.bindings[str(self.inputs)]['sha256']),
                                   ('corrected partition', CORRECTED_PARTITION), ('corrected semantic ledger', CORRECTED_LEDGER),
                                   ('source manifest', environment.get('source_manifest_sha256'))]:
                self.check('Protected manifest contains ' + name, expected, expected in values,
                           digest_text(expected) and expected in values)

    def check_controls(self, completion):
        records = completion.get('control_records', [])
        if not isinstance(records, list):
            self.issue('Invalid control_records field', records)
            records = []
        names = [r.get('name') if isinstance(r, dict) else None for r in records]
        self.check('Nine frozen control forward records', list(CONTROL_NAMES), names,
                   names == list(CONTROL_NAMES), blocked=len(records) < 9)
        for record in records:
            if not isinstance(record, dict):
                self.issue('Invalid control record', record)
                continue
            name = record.get('name', '')
            if not isinstance(name, str):
                self.issue('Invalid control name', name)
                continue
            depth = 16 if name.startswith('causal16') else 32 if name.startswith('causal32') else 8
            if record.get('depth') != depth:
                self.issue('Wrong control depth', record)
            calls = record.get('block_calls')
            expected_calls = {'prelude': 2, 'core': 2 * depth, 'coda': 2}
            # The first two controls deliberately avoid observation hooks.
            if name not in ('native8', 'wrapper8') and calls != expected_calls:
                self.issue('Wrong control block call counts', {'name': name, 'actual': calls, 'expected': expected_calls})
            if name in ('native8', 'wrapper8') and calls is not None:
                self.issue('Unexpected observation in native/wrapper control', {'name': name, 'actual': calls})
            if not digest_text(record.get('logits_sha256')):
                self.issue('Missing/invalid control logits digest', name)
            if not finite(record.get('forward_seconds')) or record['forward_seconds'] < 0:
                self.issue('Invalid control timing', name)
            if type(record.get('maxrss_kib')) is not int or record['maxrss_kib'] < 0:
                self.issue('Invalid control RSS', name)
        if records and all(isinstance(r, dict) for r in records):
            for field in ('rng_before_sha256', 'rng_after_sha256'):
                values = [r.get(field) for r in records]
                self.check('Control RNG identity ' + field, 'same valid digest in every control', values,
                           all(digest_text(v) for v in values) and len(set(values)) == 1)
            observed = [r for r in records if r.get('name') not in ('native8', 'wrapper8')]
            if observed:
                values = [r.get('h0_sha256') for r in observed]
                self.check('Observed control h0 identity', 'same valid h0 digest', values,
                           all(digest_text(v) for v in values) and len(set(values)) == 1)
        if len(records) >= 4 and all(isinstance(r, dict) for r in records[:4]):
            values = [r.get('logits_sha256') for r in records[:4]]
            self.check('Native/wrapper/observer/repeat control output identity', 'four equal valid logits digests',
                       values, all(digest_text(v) for v in values) and len(set(values)) == 1)
        return len(records)

    def audit(self):
        inputs = self.load(self.inputs)
        if not isinstance(inputs, dict) or not isinstance(inputs.get('samples'), list):
            self.issue('Missing or invalid frozen inputs', blocked=inputs is None)
            return
        samples = inputs['samples']
        self.check('Immutable corrected input SHA256', CORRECTED_INPUTS, self.bindings[str(self.inputs)]['sha256'],
                   self.bindings[str(self.inputs)]['sha256'] == CORRECTED_INPUTS)
        valid_inputs = len(samples) == ARTICLES
        for index, sample in enumerate(samples):
            valid_inputs = (valid_inputs and isinstance(sample, dict) and sample.get('index') == index
                            and digest_text(sample.get('article_id')) and digest_text(sample.get('text_sha256'))
                            and digest_text(sample.get('source_article_key')) and type(sample.get('heading_row')) is int
                            and isinstance(sample.get('title'), str) and isinstance(sample.get('tokens'), list)
                            and len(sample['tokens']) == 257
                            and all(type(t) is int and 0 <= t < 32768 for t in sample['tokens']))
        self.check('Frozen article/token inventory', '32 indexed articles, 257 valid token IDs each',
                   {'articles': len(samples)}, valid_inputs)
        if not valid_inputs:
            return
        self.check_corrected_sources(samples)
        token_hash_errors = []
        for index, sample in enumerate(samples):
            for field, tokens in [('input_ids_sha256', sample['tokens'][:256]),
                                  ('target_ids_sha256', sample['tokens'][1:257]),
                                  ('scored_target_ids_sha256', sample['tokens'][65:257])]:
                if sample.get(field) != canonical_digest(tokens):
                    token_hash_errors.append({'article_index': index, 'field': field, 'actual': sample.get(field)})
        self.check('Frozen input, full shifted target and scored target hashes',
                   '256 input / 256 shifted target / 192 scored target IDs independently hashed',
                   token_hash_errors, not token_hash_errors)
        self.check('Unique source articles', ARTICLES, len({s['article_id'] for s in samples}),
                   len({s['article_id'] for s in samples}) == ARTICLES)
        environment = self.load(self.run / 'environment.json')
        if isinstance(environment, dict):
            expected_env = {'device': 'cpu', 'dtype': 'torch.float32', 'threads': 2, 'interop': 1,
                            'deterministic': True, 'autocast': False, 'forced_attention_backend': False,
                            'upstream_commit': UPSTREAM, 'torch': '2.11.0+cpu', 'weights_sha256': WEIGHTS,
                            'autocast_cpu_enabled': False, 'actual_parameter_count': 144323136,
                            'unique_parameter_tensors': 61,
                            'inputs_sha256': self.bindings[str(self.inputs)]['sha256']}
            for key, expected in expected_env.items():
                self.check('Environment binding ' + key, expected, environment.get(key),
                           environment.get(key) == expected and type(environment.get(key)) is type(expected),
                           blocked=key not in environment)
            for key in ('freeze_commit', 'execution_head'):
                self.check('Valid provenance ' + key, '40-character Git SHA', environment.get(key),
                           digest_text(environment.get(key), 40), blocked=key not in environment)
            self.check('Source manifest binding', 'SHA256', environment.get('source_manifest_sha256'),
                       digest_text(environment.get('source_manifest_sha256')), blocked='source_manifest_sha256' not in environment)
            version = environment.get('python')
            self.check('Python version binding', '3.12.3', version,
                       isinstance(version, str) and version.startswith('3.12.3 '), blocked=version is None)
        else:
            self.issue('Missing environment object', blocked=environment is None)
        completion = self.load(self.run / 'completion.json')
        completion = completion if isinstance(completion, dict) else {}
        self.check_terminal(completion)
        self.check_recorded_checks(completion)
        environment = environment if isinstance(environment, dict) else {}
        self.check_state(completion, environment)
        self.check_runtime_and_packages(environment)
        self.check_protected(environment)
        control_count = self.check_controls(completion)
        raw = self.read(self.run / 'rows.jsonl')
        records = []
        if raw is not None:
            for lineno, line in enumerate(raw.splitlines(), 1):
                try:
                    records.append(strict_json(line))
                except (ValueError, TypeError) as exc:
                    self.issue('Unreadable row; original bytes retained', {'line': lineno, 'error': str(exc)}, blocked=True)
        expected_order = [(a, r, d) for a in range(ARTICLES) for r in range(3) for d in ORDERS[(a * 3 + r) % 6]]
        by_key, row_errors = {}, []
        for position, row in enumerate(records):
            if not isinstance(row, dict):
                row_errors.append({'position': position, 'reason': 'row is not an object'})
                continue
            a, r, d = row.get('article_index'), row.get('replica'), row.get('depth')
            key = (a, r, d)
            if type(a) is not int or not 0 <= a < ARTICLES or type(r) is not int or not 0 <= r < 3 or type(d) is not int or d not in DEPTHS:
                row_errors.append({'position': position, 'reason': 'invalid row identity'})
                continue
            if key in by_key:
                row_errors.append({'position': position, 'reason': 'duplicate row identity', 'key': key})
                continue
            sample, order = samples[a], ORDERS[(a * 3 + r) % 6]
            expected = {'article_id': sample['article_id'], 'replica_seed': SEEDS[r],
                        'source_article_key': sample['source_article_key'], 'heading_row': sample['heading_row'],
                        'seed': SEEDS[r] + 100000 * a, 'order': list(order), 'order_position': order.index(d),
                        'input_ids_sha256': canonical_digest(sample['tokens'][:256]),
                        'target_ids_sha256': canonical_digest(sample['tokens'][1:257]),
                        'scored_target_ids_sha256': canonical_digest(sample['tokens'][65:257]),
                        'block_calls': {'prelude': 2, 'core': 2 * d, 'coda': 2}}
            errors = [field for field, value in expected.items() if row.get(field) != value]
            if position >= len(expected_order) or key != expected_order[position]:
                errors.append('frozen_execution_order')
            for field in ('h0_sha256', 'rng_before_sha256', 'rng_after_sha256'):
                if not digest_text(row.get(field)):
                    errors.append(field)
            for field in ('logsumexp', 'target_logits', 'nll'):
                values = row.get(field)
                if not isinstance(values, list) or len(values) != TARGETS or not all(finite(v) for v in values):
                    errors.append(field)
            if not finite(row.get('forward_seconds')) or row['forward_seconds'] < 0:
                errors.append('forward_seconds')
            if type(row.get('maxrss_kib')) is not int or row['maxrss_kib'] < 0:
                errors.append('maxrss_kib')
            if not any(field in errors for field in ('logsumexp', 'target_logits', 'nll')):
                residual = max(abs(n - (lse - target)) for n, lse, target in zip(row['nll'], row['logsumexp'], row['target_logits']))
                mean = math.fsum(row['nll']) / TARGETS
                if residual > ARITHMETIC_TOLERANCE:
                    errors.append('nll_identity')
                if not finite(row.get('mean_nll')) or abs(row['mean_nll'] - mean) > ARITHMETIC_TOLERANCE:
                    errors.append('mean_nll')
                row = dict(row, audited_mean_nll=mean, audited_max_identity_residual=residual)
            if errors:
                row_errors.append({'position': position, 'key': key, 'fields': errors})
            by_key[key] = row
        missing = [key for key in expected_order if key not in by_key]
        self.check('Recorded row identities, arithmetic and metadata', 'no contradictions', row_errors, not row_errors)
        self.check('Complete formal coverage', 288, {'records': len(records), 'unique': len(by_key), 'missing': missing},
                   len(records) == len(by_key) == 288 and not missing, blocked=True)
        self.check_formal_journal(by_key)
        pairing_errors = []
        for a in range(ARTICLES):
            for r in range(3):
                triple = [by_key.get((a, r, d)) for d in DEPTHS]
                if not all(x is not None for x in triple):
                    continue
                for field in ('h0_sha256', 'rng_before_sha256', 'rng_after_sha256'):
                    values = [x.get(field) for x in triple]
                    if not all(digest_text(v) for v in values) or len(set(values)) != 1:
                        pairing_errors.append({'article_index': a, 'replica': r, 'field': field, 'values': values})
        self.check('Common initialization and RNG pairing', 'equal h0 and before/after RNG digests within each depth triple',
                   pairing_errors, not pairing_errors)
        counts = {'formal_rows': len(records), 'control_forwards': control_count, 'total_forwards': len(records) + control_count}
        for field, expected in [('formal_rows', 288), ('control_forwards', 9), ('total_forwards', 297)]:
            value = completion.get(field)
            self.check('Complete runner count ' + field, expected, value, value == expected,
                       blocked=value is None or (type(value) is int and 0 <= value < expected))
            if field != 'total_forwards' and value is not None and value != counts[field]:
                self.issue('Runner count disagrees with saved records', {'field': field, 'declared': value, 'saved': counts[field]})
            if field == 'total_forwards' and type(value) is int and value < counts[field]:
                self.issue('Total forward count smaller than completed records', {'declared': value, 'saved': counts[field]})
        self.actual.update({'formal_rows': len(records), 'unique_formal_rows': len(by_key), 'control_records': control_count,
                            'missing': missing, 'target_tokens_per_row': TARGETS,
                            'unique_scored_target_positions': ARTICLES * TARGETS,
                            'scored_target_instances_expected': 288 * TARGETS,
                            'scientific_results': None})
        if not self.failures and not self.blockers:
            self.actual['scientific_results'] = derive_statistics(by_key, samples)


def derive_statistics(rows, samples):
    means = {d: [math.fsum(rows[(a, r, d)]['audited_mean_nll'] for r in range(3)) / 3
                 for a in range(ARTICLES)] for d in DEPTHS}
    contrasts = {'primary_d16_minus_d8': [means[16][a] - means[8][a] for a in range(ARTICLES)],
                 'secondary_d32_minus_d8': [means[32][a] - means[8][a] for a in range(ARTICLES)]}
    bootstrap = {name: [] for name in contrasts}
    generator = random.Random(BOOTSTRAP_SEED)
    for _ in range(BOOTSTRAPS):
        indices = [generator.randrange(ARTICLES) for _ in range(ARTICLES)]
        for name, values in contrasts.items():
            bootstrap[name].append(math.fsum(values[index] for index in indices) / ARTICLES)
    result = {'analysis_unit': 'whole article; three paired initial-state replicas averaged within each article',
              'articles': ARTICLES, 'initial_state_replica_seeds': list(SEEDS), 'nll_unit': 'nats per scored token',
              'per_depth': {}, 'paired_contrasts': {}, 'per_article': [],
              'bootstrap': {'resamples': BOOTSTRAPS, 'seed': BOOTSTRAP_SEED, 'same_indices_across_contrasts': True,
                            'interval': 'nearest-rank percentile 2.5% and 97.5%; no interpolation',
                            'lower_sorted_index': math.ceil(0.025 * BOOTSTRAPS) - 1,
                            'upper_sorted_index': math.ceil(0.975 * BOOTSTRAPS) - 1},
              'statistical_confirmation': 'NOT TESTED', 'equivalence_or_noninferiority': 'NOT TESTED',
              'upgrade_or_depth_selection_policy': 'NOT ASSESSED', 'hardware_efficiency': 'NOT TESTED',
              'interpretation': 'Exploratory conditional estimates; pointwise intervals are not simultaneous confidence guarantees. No practical improvement threshold or automatic PASS for a quality hypothesis.'}
    for d in DEPTHS:
        nll = math.fsum(means[d]) / ARTICLES
        seconds = [rows[(a, r, d)]['forward_seconds'] for a in range(ARTICLES) for r in range(3)]
        result['per_depth'][str(d)] = {'mean_nll': nll, 'ppl': math.exp(nll) if nll <= math.log(sys.float_info.max) else None,
                                      'ppl_overflow': nll > math.log(sys.float_info.max),
                                      'rows': ARTICLES * 3, 'median_observed_forward_seconds': statistics.median(seconds),
                                      'observed_forward_seconds': math.fsum(seconds),
                                      'prelude_core_coda_block_passes': 4 + 2 * d,
                                      'timing_scope': 'descriptive instrumented CPU observations; not an efficiency acceptance test'}
    for name, values in contrasts.items():
        other = 16 if name.startswith('primary') else 32
        result['paired_contrasts'][name] = {
            'mean_delta_nll': math.fsum(values) / ARTICLES,
            'article_sign_counts': {'negative': sum(v < 0 for v in values), 'zero': sum(v == 0 for v in values),
                                    'positive': sum(v > 0 for v in values)},
            'exploratory_bootstrap_percentile_interval': [nearest_rank(bootstrap[name], 0.025), nearest_rank(bootstrap[name], 0.975)],
            'bootstrap_values_sha256': canonical_digest(bootstrap[name]),
            'per_replica_mean_delta_nll': {str(SEEDS[r]): math.fsum(rows[(a, r, other)]['audited_mean_nll']
                                                                  - rows[(a, r, 8)]['audited_mean_nll']
                                                                  for a in range(ARTICLES)) / ARTICLES for r in range(3)},
            'direction': 'negative means the deeper depth has lower NLL than depth8 on this development sample',
        }
    for a, sample in enumerate(samples):
        result['per_article'].append({'article_index': a, 'article_id': sample['article_id'], 'title': sample['title'],
                                      'source_article_key': sample['source_article_key'], 'heading_row': sample['heading_row'],
                                      'mean_nll_by_depth': {str(d): means[d][a] for d in DEPTHS},
                                      'primary_d16_minus_d8': contrasts['primary_d16_minus_d8'][a],
                                      'secondary_d32_minus_d8': contrasts['secondary_d32_minus_d8'][a]})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--partition', type=Path, required=True)
    parser.add_argument('--ledger', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run, inputs, output = args.run.resolve(), args.inputs.resolve(), args.output.resolve()
    partition, ledger = args.partition.resolve(), args.ledger.resolve()
    if output.exists() or output.is_relative_to(run) or output in (inputs, partition, ledger, Path(__file__).resolve()):
        parser.error('Output must be new, outside the run, and must not overwrite inputs or audit source')
    audit = Audit(run, inputs, partition, ledger)
    try:
        audit.audit()
    except Exception as exc:
        audit.issue('Audit could not finish; source evidence remains untouched',
                    {'type': type(exc).__name__, 'error': repr(exc), 'traceback': traceback.format_exc()}, blocked=True)
    status = 'FAIL' if audit.failures else 'BLOCKED' if audit.blockers else 'PASS'
    result = {'Purpose': 'Audit fixed-weight depth-budget evidence and derive preregistered exploratory article-level estimates',
              'Environment': 'Python standard library only; no model/tokenizer/Torch import or forward pass',
              'Input': {'run': str(run), 'inputs': str(inputs), 'partition': str(partition), 'ledger': str(ledger),
                        'file_bindings': audit.bindings},
              'Expected': {'articles': ARTICLES, 'depths': list(DEPTHS), 'replica_seeds': list(SEEDS),
                           'formal_rows': 288, 'control_forwards': 9, 'total_forwards': 297,
                           'scored_target_slice': [64, 256], 'arithmetic_tolerance': ARITHMETIC_TOLERANCE},
              'Actual': audit.actual, 'Status': status, 'Status_scope': 'Engineering and recorded-evidence integrity only; not scientific superiority',
              'checks': audit.checks, 'check_counts': dict(Counter(c['Status'] for c in audit.checks)),
              'failures': audit.failures, 'blockers': audit.blockers,
              'limitations': [
                  'Only saved logsumexp, target logits and NLL arithmetic are recomputed; vocabulary logits and tokenization are not regenerated.',
                  'State/source preservation is checked from recorded hash manifests and runner checks; original weight tensors are not deserialized here.',
                  'The 32 article windows are the sampling units. Tokens and initial-state replicas are not independent article samples.',
                  'This historical WikiText development sample is not demonstrated free of pretraining overlap or a fresh generalization test.',
                  'Bootstrap intervals are exploratory and conditional on this sample, frozen model, protocol and initialization replicas.',
                  'No confidence-interval inclusion of zero is interpreted as equivalence; no automatic deployment or adaptive-depth policy follows.',
                  'No trained ACT, OpenMythos module transplantation, architecture-superiority or true hardware-efficiency result is established.',
              ],
              'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8', newline='\n') as destination:
        json.dump(result, destination, indent=2, ensure_ascii=False, allow_nan=False)
        destination.write('\n')
    print(json.dumps({'Status': status, 'formal_rows': audit.actual.get('formal_rows'),
                      'failures': len(audit.failures), 'blockers': len(audit.blockers), 'output': str(output)}))
    return 0 if status == 'PASS' else 2


if __name__ == '__main__':
    sys.exit(main())
