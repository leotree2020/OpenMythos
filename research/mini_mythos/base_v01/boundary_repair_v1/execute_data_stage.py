"""Frozen data-only operator: two new processes, then one independent audit."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback

REPO = Path('/workspaces/mythos-base-v01-rope-diag-v11')
ROOT = Path(__file__).resolve().parent
PYTHON = '/workspaces/mythos-depth-data-cpu312/bin/python'
CORPUS = Path('/workspaces/mythos-evidence/base_v01/depth_budget/preparation-v1-20261101/test.parquet')
TOKENIZER = Path('/workspaces/mythos-evidence/base_v01/b1/b1-20261101T021657Z/downloads/tokenizer/tokenizer.json')
LEDGER_SHA = 'f5f7858b989451671e4c7ed27192642dec3f9b2a1ccd214cc9e3cc30bcebb5d3'
BRANCH = 'mythos-data-boundary-repair-v1'


def info(path):
    data = Path(path).read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def save(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as out:
        json.dump(value, out, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        out.write('\n')


def git(*args):
    return subprocess.check_output(['git', '-C', str(REPO), *args], text=True).strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--freeze', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not args.output.is_absolute() or args.output.exists():
        parser.error('Output must be a new absolute external directory')
    output = args.output.resolve()
    if not output.is_relative_to(Path('/workspaces/mythos-evidence/base_v01/boundary_repair')):
        parser.error('Output must be in the dedicated external evidence directory')
    output.mkdir(parents=True, exist_ok=False)
    checks, executions = [], []
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', CUDA_VISIBLE_DEVICES='',
               TOKENIZERS_PARALLELISM='false', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1')

    def check(name, actual, expected):
        okay = actual == expected
        checks.append({'Purpose': name, 'Environment': PYTHON, 'Input': {'freeze': args.freeze},
                       'Expected': expected, 'Actual': actual, 'Status': 'PASS' if okay else 'FAIL'})
        save(output / ('guard_%02d.json' % len(checks)), checks[-1])
        if not okay:
            raise RuntimeError(name)

    def guard(label):
        check(label + ' actual branch', git('branch', '--show-current'), BRANCH)
        check(label + ' actual commit', git('rev-parse', 'HEAD'), args.freeze)
        check(label + ' clean worktree', git('status', '--porcelain=v1', '--untracked-files=all'), '')
        check(label + ' exact semantic ledger', info(ROOT / 'BOUNDARY_LEDGER.json')['sha256'], LEDGER_SHA)
        for name, expected in json.loads((ROOT / 'SOURCE_MANIFEST.json').read_text()).items():
            check(label + ' frozen source ' + name, info(ROOT / name), expected)

    def execute(label, command):
        start = datetime.datetime.now(datetime.timezone.utc).isoformat()
        process, interruption, cleanup_errors = None, None, []
        pid, returncode = None, None
        with (output / (label + '.stdout')).open('x') as stdout, (output / (label + '.stderr')).open('x') as stderr:
            try:
                process = subprocess.Popen(command, stdout=stdout, stderr=stderr, env=env, cwd=str(REPO))
                pid = process.pid
                returncode = process.wait()
            except BaseException as exc:
                interruption = exc
                if process is not None:
                    try:
                        if process.poll() is None:
                            process.terminate()
                        returncode = process.wait(timeout=5)
                    except BaseException as cleanup:
                        cleanup_errors.append(repr(cleanup))
                        try:
                            if process.poll() is None:
                                process.kill()
                            returncode = process.wait(timeout=5)
                        except BaseException as final_cleanup:
                            cleanup_errors.append(repr(final_cleanup))
        record = {'label': label, 'command': command, 'pid': pid, 'returncode': returncode,
                  'start_utc': start, 'end_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  'stdout': info(output / (label + '.stdout')), 'stderr': info(output / (label + '.stderr')),
                  'interruption': repr(interruption) if interruption else None, 'cleanup_errors': cleanup_errors,
                  'child_reaped': process is not None and process.poll() is not None}
        executions.append(record)
        save(output / (label + '_execution.json'), record)
        if interruption is not None:
            raise interruption
        return record

    status, error, audit = 'NOT TESTED', None, None
    try:
        check('freeze is a commit identity', len(args.freeze) == 40 and all(c in '0123456789abcdef' for c in args.freeze), True)
        remote = git('ls-remote', 'origin', 'refs/heads/' + BRANCH).split()
        check('remote freeze published', remote[0] if remote else None, args.freeze)
        for label in ('build_first', 'build_repeat'):
            guard(label)
            spec = {'corpus': str(CORPUS), 'tokenizer': str(TOKENIZER), 'ledger': str(ROOT / 'BOUNDARY_LEDGER.json'),
                    'output_dir': str(output / label), 'expected_corpus_sha256': '3ee89cd6a2ab912afd5d01e98867b46a67d9ec7a9eca0910e5e4c3cdd4cc1925',
                    'frozen_commit': args.freeze}
            spec_path = output / (label + '_spec.json')
            save(spec_path, spec)
            execution = execute(label, [PYTHON, '-I', '-B', str(ROOT / 'build_inputs.py'), '--spec', str(spec_path)])
            completion_path = output / label / 'completion.json'
            if not completion_path.is_file():
                status = 'BLOCKED'
                raise RuntimeError(label + ' missing completion')
            completion = json.loads(completion_path.read_text())
            if completion.get('Status') != 'PASS' or execution['returncode'] != 0:
                status = completion.get('Status', 'BLOCKED')
                if status not in ('FAIL', 'BLOCKED'):
                    status = 'BLOCKED'
                raise RuntimeError(label + ' did not pass')
            check(label + ' actual child PID bound', completion.get('process_id'), execution['pid'])
        guard('independent_audit')
        command = [PYTHON, '-I', '-B', str(ROOT / 'audit_boundary_inputs.py'), '--corpus', str(CORPUS),
                   '--tokenizer', str(TOKENIZER), '--ledger', str(ROOT / 'BOUNDARY_LEDGER.json'),
                   '--run', str(output / 'build_first'), '--repeat', str(output / 'build_repeat'),
                   '--output', str(output / 'independent_audit.json')]
        execution = execute('audit', command)
        if not (output / 'independent_audit.json').is_file():
            status = 'BLOCKED'
            raise RuntimeError('Independent audit missing report')
        audit = json.loads((output / 'independent_audit.json').read_text())
        if audit.get('Status') != 'PASS' or execution['returncode'] != 0:
            status = audit.get('Status', 'BLOCKED')
            if status not in ('FAIL', 'BLOCKED'):
                status = 'BLOCKED'
            raise RuntimeError('Independent audit did not pass')
        guard('after_audit')
        status = 'PASS'
    except BaseException as exc:
        if status not in ('BLOCKED', 'FAIL'):
            status = 'BLOCKED' if isinstance(exc, (OSError, MemoryError, KeyboardInterrupt, subprocess.CalledProcessError)) else 'FAIL'
        error = {'type': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc()}
    report = {'Purpose': 'Guard frozen data-only execution and stop on first failure',
              'Environment': {'python': PYTHON, 'cpu_only': True, 'dependency_installation': False},
              'Input': {'freeze': args.freeze, 'output': str(output), 'ledger_sha256': LEDGER_SHA},
              'Expected': 'Two distinct process builds plus independent source/token audit PASS; no model run',
              'Actual': {'executions': executions, 'guard_count': len(checks),
                         'audit_check_counts': audit.get('check_counts') if audit else None,
                         'audit_actual': audit.get('Actual') if audit else None},
              'Status': status, 'error': error, 'checks': checks,
              'model_execution': 'NOT TESTED', 'scientific_performance_evidence': 'NOT TESTED'}
    save(output / 'operator_summary.json', report)
    print(json.dumps({'Status': status, 'output': str(output), 'error': error,
                      'audit_check_counts': report['Actual']['audit_check_counts']}), flush=True)
    return 0 if status == 'PASS' else 2


if __name__ == '__main__':
    sys.exit(main())
