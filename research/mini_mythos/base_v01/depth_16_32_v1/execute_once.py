"""One manually invoked target-only CPU run. Never retries or installs packages."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import traceback

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]
BRANCH = 'mythos-depth-16-32-cpu-v1'
PYTHON = '/workspaces/mythos-base-v01-cpu312/bin/python'
RUN = Path('/workspaces/mythos-evidence/base_v01/depth_16_32/attempt-v1')
UPSTREAM = Path('/workspaces/mythos-parcae-pinned')
B1 = Path('/workspaces/mythos-base-v01-b1')
MODEL = Path('/workspaces/mythos-evidence/base_v01/b1/b1-20261101T021657Z/downloads/model')
TOKENIZER = MODEL.parent / 'tokenizer/tokenizer.json'
DATA = Path('/workspaces/mythos-evidence/base_v01/boundary_repair/data-20261101T134401Z')
INPUTS = DATA / 'build_first/inputs.json'
PARTITION = DATA / 'build_first/partition.json'
LEDGER = REPO / 'research/mini_mythos/base_v01/boundary_repair_v1/BOUNDARY_LEDGER.json'
PINS = {
    INPUTS: '3abb324ea2876abb78e18d86ec257a9e1d388f9501bd8cdd6c99011ac11cf41e',
    PARTITION: '95a217a815596c928a0b721837b567a08ed8c6f667839fdf6d4311113c253aa4',
    DATA / 'build_first/manifest.json': '6593d2a6906fb803af1095fd4f76980d830635b60cb6c50da0d1def00fbb8cf1',
    DATA / 'independent_audit.json': '6f0e15cbdad4d987b2a0fea9166e2ffc9b53bf1f0bd2dc99155329299498aa44',
    LEDGER: 'f5f7858b989451671e4c7ed27192642dec3f9b2a1ccd214cc9e3cc30bcebb5d3',
    MODEL / 'pytorch_model.bin': 'ed6eb306464dd0d694e9eacd58f7e06ac3e44b43cb7c5c79dbcb1543059c6621',
    MODEL / 'config.json': '5c8fc785c2f6dba67d0370ad715034860e3b22bfce850da825c06baa03923c13',
    TOKENIZER: 'e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77',
}
ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', CUDA_VISIBLE_DEVICES='',
           OMP_NUM_THREADS='2', MKL_NUM_THREADS='2', HF_HUB_OFFLINE='1',
           TRANSFORMERS_OFFLINE='1', TOKENIZERS_PARALLELISM='false')


class Stop(Exception):
    def __init__(self, status, reason):
        super().__init__(reason)
        self.status = status


def save(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        stream.write('\n')


def info(path):
    digest, size = hashlib.sha256(), 0
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            digest.update(block)
            size += len(block)
    return {'bytes': size, 'sha256': digest.hexdigest()}


def git(path, *args):
    return subprocess.check_output(['git', '-C', str(path), *args], text=True, timeout=60).strip()


def git_state(path):
    return {'head': git(path, 'rev-parse', 'HEAD'), 'status': git(path, 'status', '--porcelain=v1', '--untracked-files=all')}


def active_workers():
    result = []
    for item in Path('/proc').iterdir():
        if not item.name.isdigit() or int(item.name) == os.getpid():
            continue
        try:
            argv = (item / 'cmdline').read_bytes().split(b'\0')
            names = {Path(x.decode(errors='replace')).name for x in argv if x}
            if names & {'run_depth_budget.py', 'mythos_launch.py', 'observe_official.py'}:
                result.append({'pid': int(item.name), 'names': sorted(names & {'run_depth_budget.py', 'mythos_launch.py', 'observe_official.py'})})
        except (OSError, ProcessLookupError):
            pass
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--expected-head', required=True)
    args = parser.parse_args()
    if platform.system() != 'Linux' or not Path('/workspaces').is_dir():
        print('BLOCKED: run only inside the designated Codespace; no model started.')
        return 2
    if RUN.exists():
        print('BLOCKED: attempt-v1 already exists; do not rerun or remove it. Evidence: ' + str(RUN))
        return 2
    RUN.mkdir(parents=True, exist_ok=False)
    checks, commands, before, states, inventories = [], [], {}, {}, {}
    outcome, error, scientific, freeze_ok = 'NOT TESTED', None, None, False
    baseline_complete = False

    def check(purpose, actual, expected, failure='FAIL'):
        okay = actual == expected
        record = {'Purpose': purpose, 'Environment': PYTHON, 'Input': {'freeze': args.expected_head},
                  'Expected': expected, 'Actual': actual, 'Status': 'PASS' if okay else failure}
        checks.append(record)
        with (RUN / 'operator_checks.jsonl').open('a') as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + '\n')
        if not okay:
            raise Stop(failure, purpose)

    def command(label, argv, timeout=None):
        process, interruption, cleanup_errors = None, None, []
        start = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with (RUN / (label + '.stdout')).open('x') as stdout, (RUN / (label + '.stderr')).open('x') as stderr:
            try:
                process = subprocess.Popen(argv, cwd=REPO, env=ENV, stdout=stdout, stderr=stderr)
                code = process.wait(timeout=timeout)
            except BaseException as exc:
                interruption = exc
                if process is not None:
                    try:
                        if process.poll() is None:
                            process.send_signal(signal.SIGTERM)
                        process.wait(timeout=20)
                    except BaseException as cleanup:
                        cleanup_errors.append(repr(cleanup))
                        if label != 'formal_launcher':
                            try:
                                if process.poll() is None:
                                    process.kill()
                                process.wait(timeout=5)
                            except BaseException as final_cleanup:
                                cleanup_errors.append(repr(final_cleanup))
                code = process.returncode if process is not None else None
        record = {'label': label, 'argv': argv, 'pid': process.pid if process else None,
                  'returncode': code, 'start_utc': start,
                  'end_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  'interruption': repr(interruption) if interruption else None,
                  'cleanup_errors': cleanup_errors, 'child_reaped': process is not None and process.poll() is not None}
        commands.append(record)
        save(RUN / (label + '_execution.json'), record)
        if interruption is not None:
            raise Stop('BLOCKED', label + ' interrupted; inspect cleanup and process evidence')
        return code

    try:
        check('designated Codespace', os.environ.get('CODESPACE_NAME'), 'bookish-pancake-vwqx7rr9x5w3wxjr', 'BLOCKED')
        check('correct interpreter', sys.executable, PYTHON, 'BLOCKED')
        check('Python version', platform.python_version(), '3.12.3', 'BLOCKED')
        check('isolated no bytecode runtime', bool(sys.flags.isolated) and sys.dont_write_bytecode, True)
        check('frozen branch', git(REPO, 'branch', '--show-current'), BRANCH)
        check('frozen clean execution checkout', git_state(REPO), {'head': args.expected_head, 'status': ''})
        check('remote freeze', git(REPO, 'ls-remote', 'origin', 'refs/heads/' + BRANCH).split()[0], args.expected_head)
        freeze_ok = True
        for name, expected in json.loads((ROOT / 'SOURCE_MANIFEST.json').read_text()).items():
            check('frozen source ' + name, info(ROOT / name), expected)
        check('exclusive model worker', active_workers(), [], 'BLOCKED')
        states = {str(path): git_state(path) for path in (REPO, UPSTREAM, B1)}
        check('pinned upstream', states[str(UPSTREAM)], {'head': '69284c13746e849104f738d6d1a347b1f457df76', 'status': ''})
        check('protected B1 checkout', states[str(B1)], {'head': 'd88be474ebb2529c5b095e3732b1f25509f9b824', 'status': ''})
        inventory_code = 'import importlib.metadata as m,json;print(json.dumps(sorted((d.metadata["Name"],d.version,str(d.locate_file(""))) for d in m.distributions())))'
        for executable in (PYTHON, '/workspaces/mythos-depth-data-cpu312/bin/python', '/workspaces/mythos-parcae-official-eval-cpu312/bin/python'):
            inventories[executable] = json.loads(subprocess.check_output([executable, '-I', '-B', '-c', inventory_code], text=True, timeout=60))
        save(RUN / 'environment_inventories_before.json', inventories)
        mem = dict(line.split(':', 1) for line in Path('/proc/meminfo').read_text().splitlines())
        resources = {'mem_available_bytes': int(mem['MemAvailable'].split()[0]) * 1024,
                     'disk_free_bytes': shutil.disk_usage(RUN).free, 'cpu_count': os.cpu_count()}
        save(RUN / 'resources.json', resources)
        check('available CPU memory >=2.5GiB', resources['mem_available_bytes'] >= 2684354560, True, 'BLOCKED')
        check('evidence free disk >=512MiB', resources['disk_free_bytes'] >= 536870912, True, 'BLOCKED')
        for path, expected in PINS.items():
            actual = info(path)
            check('protected artifact ' + path.name, actual['sha256'], expected)
            before[str(path)] = actual
        samples = json.loads(INPUTS.read_text())['samples']
        partition = json.loads(PARTITION.read_text())
        by_key = {a['source_article_key']: a for a in partition['articles']}
        ledger = json.loads(LEDGER.read_text())
        check('exact32 distinct reviewed sources', len(samples) == 32 and len({s['source_article_key'] for s in samples}) == 32, True)
        for sample in samples:
            source = by_key[sample['source_article_key']]
            check('reviewed source span ' + str(sample['index']),
                  all(sample[k] == source[k] for k in ('heading_row', 'body_rows', 'article_id', 'text_sha256', 'title', 'full_token_count'))
                  and sample['heading_row'] in ledger['accepted_heading_rows'], True)
        check('completed data audit', json.loads((DATA / 'independent_audit.json').read_text())['Status'], 'PASS')
        # Protect tracked sources/history without reading prior model scores as JSON.
        for checkout in (REPO, UPSTREAM, B1):
            for name in git(checkout, 'ls-files').splitlines():
                path = checkout / name
                if path.is_file():
                    before[str(path)] = info(path)
        save(RUN / 'protected_before.json', {'files': before, 'git': states})
        baseline_complete = True
        for test in ('test_depth_helpers.py', 'test_audit_depth_budget.py'):
            print('Development checks: ' + test, flush=True)
            check('synthetic fixtures ' + test,
                  command(test[:-3], [PYTHON, '-I', '-B', str(ROOT / test), '-v'], timeout=180), 0)
        operator = RUN / 'operator'
        operator.mkdir()
        shutil.copyfile(ROOT / 'mythos_launch.py', operator / 'mythos_launch.py')
        check('unchanged validated launcher', info(operator / 'mythos_launch.py')['sha256'],
              '8083b948eebdf08c2d14a79d940ccead72db5f10c6bac8d9061816b6c9ea05c3')
        save(operator / 'source_manifest.json', before)
        spec = {'run_id': 'MYTHOS-DEPTH-16-32-CPU-V1', 'repo': str(REPO), 'upstream': str(UPSTREAM),
                'model_dir': str(MODEL), 'tokenizer_path': str(TOKENIZER), 'inputs_path': str(INPUTS),
                'inputs_sha256': PINS[INPUTS], 'source_manifest_path': str(operator / 'source_manifest.json'),
                'run_dir': str(RUN / 'worker'), 'freeze_commit': args.expected_head, 'expected_head': args.expected_head}
        save(operator / 'spec.json', spec)
        save(operator / 'launcher_config.json', {'command': [PYTHON, '-I', '-B', str(ROOT / 'run_depth_budget.py'),
              '--spec', str(operator / 'spec.json')], 'cwd': str(operator), 'timeout_seconds': 3600})
        print('Running CPU depths8/16/32. Progress file: ' + str(operator / 'stdout.log'), flush=True)
        code = command('formal_launcher', [PYTHON, '-I', '-B', str(operator / 'mythos_launch.py'),
                                          '--config', str(operator / 'launcher_config.json')])
        worker_file = RUN / 'worker/completion.json'
        if not worker_file.is_file():
            raise Stop('BLOCKED', 'Worker completion missing')
        completion = json.loads(worker_file.read_text())
        if code or completion.get('status') != 'PASS':
            raise Stop(completion.get('status') if completion.get('status') in ('FAIL', 'BLOCKED') else 'BLOCKED',
                       'Formal worker did not pass; no retry')
        code = command('audit', [PYTHON, '-I', '-B', str(ROOT / 'audit_depth_budget.py'),
              '--run', str(RUN / 'worker'), '--inputs', str(INPUTS), '--partition', str(PARTITION), '--ledger', str(LEDGER),
              '--output', str(RUN / 'audit.json')], timeout=180)
        if not (RUN / 'audit.json').is_file():
            raise Stop('BLOCKED', 'Independent audit report missing')
        audit = json.loads((RUN / 'audit.json').read_text())
        if audit['Status'] != 'PASS':
            raise Stop(audit['Status'] if audit['Status'] in ('FAIL', 'BLOCKED') else 'BLOCKED', 'Independent audit stopped')
        check('independent audit exit', code, 0)
        code = command('independent_summary', [PYTHON, '-I', '-B', str(ROOT / 'independent_summary.py'),
              '--rows', str(RUN / 'worker/rows.jsonl'), '--audit', str(RUN / 'audit.json'),
              '--output', str(RUN / 'independent_summary.json')], timeout=180)
        if not (RUN / 'independent_summary.json').is_file():
            raise Stop('BLOCKED', 'Separate summary missing')
        summary_status = json.loads((RUN / 'independent_summary.json').read_text())['Status']
        if summary_status != 'PASS':
            raise Stop(summary_status if summary_status in ('FAIL', 'BLOCKED') else 'BLOCKED', 'Separate summary stopped')
        check('separate summary exit', code, 0)
        scientific = audit['Actual']['scientific_results']
        outcome = 'PASS'
    except BaseException as exc:
        outcome = getattr(exc, 'status', 'BLOCKED' if isinstance(exc, (OSError, KeyboardInterrupt, subprocess.SubprocessError)) else 'FAIL')
        error = {'type': type(exc).__name__, 'reason': str(exc), 'traceback': traceback.format_exc()}
    # Always preserve terminal custody. This never runs another model or changes a gate.
    custody = {'changed_files': [], 'changed_git': [], 'unreadable_files': [], 'active_workers': [],
               'changed_environments': [], 'unreaped_or_cleanup_errors': []}
    try:
        for path, expected in before.items():
            try:
                if info(path) != expected:
                    custody['changed_files'].append(path)
            except OSError as exc:
                custody['unreadable_files'].append({'path': path, 'error': repr(exc)})
        custody['git_after'] = {path: git_state(Path(path)) for path in states}
        custody['changed_git'] = [path for path in states if custody['git_after'][path] != states[path]]
        custody['active_workers'] = active_workers()
        custody['unreaped_or_cleanup_errors'] = [c for c in commands if not c['child_reaped'] or c['cleanup_errors']]
        after_inventories = {executable: json.loads(subprocess.check_output([executable, '-I', '-B', '-c', inventory_code], text=True, timeout=60))
                             for executable in inventories}
        custody['changed_environments'] = [e for e in inventories if after_inventories[e] != inventories[e]]
        save(RUN / 'environment_inventories_after.json', after_inventories)
        custody['Status'] = ('FAIL' if any(custody[k] for k in ('changed_files', 'changed_git', 'changed_environments')) else
                            'BLOCKED' if any(custody[k] for k in ('unreadable_files', 'active_workers', 'unreaped_or_cleanup_errors')) else
                            'NOT TESTED' if not baseline_complete else 'PASS')
    except BaseException as exc:
        custody.update(Status='FAIL' if any(custody[k] for k in ('changed_files', 'changed_git', 'changed_environments')) else 'BLOCKED', error=repr(exc))
    custody['baseline_complete'] = baseline_complete
    worker_started = (RUN / 'worker/spec.json').is_file()
    worker_completion = None
    try:
        if (RUN / 'worker/completion.json').is_file():
            worker_completion = json.loads((RUN / 'worker/completion.json').read_text())
            if not isinstance(worker_completion, dict):
                raise ValueError('Worker completion is not an object')
    except BaseException as exc:
        worker_completion = None
        custody['terminal_read_error'] = repr(exc)
        if custody['Status'] != 'FAIL':
            custody['Status'] = 'BLOCKED'
    save(RUN / 'custody.json', custody)
    if custody['Status'] == 'FAIL':
        outcome = 'FAIL'
    elif custody['Status'] != 'PASS' and outcome == 'PASS':
        outcome = 'BLOCKED'
    model_forward_started = bool(worker_completion.get('total_forwards', 0)) if worker_completion is not None else None if worker_started else False
    report = {'Purpose': 'One controlled8/16/32-round CPU evaluation', 'Environment': PYTHON,
              'Input': {'freeze_commit': args.expected_head, 'corrected_inputs_sha256': PINS[INPUTS]},
              'Expected': '297 forwards, fixed evidence gates and independent arithmetic agreement; no automatic quality PASS',
              'Actual': {'commands': commands, 'checks': checks, 'custody': custody, 'scientific_results': scientific},
              'Status': outcome, 'error': error, 'formal_launch_attempted': any(c['label'] == 'formal_launcher' for c in commands),
              'worker_started': worker_started, 'model_forward_started': model_forward_started,
              'Formal_Oracle': 'BLOCKED/NOT_READY', 'FORMAL_ACCEPTANCE_READY': False,
              'utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    save(RUN / 'summary.json', report)
    save(RUN / 'CHECKPOINT.json', {
        'Purpose': report['Purpose'], 'Environment': PYTHON, 'Input': report['Input'],
        'Expected': report['Expected'], 'Actual': {'summary': str(RUN / 'summary.json'), 'error': error},
        'Status': outcome, 'branch': BRANCH, 'requested_freeze_commit': args.expected_head,
        'freeze_verified': freeze_ok, 'worker_started': worker_started, 'model_forward_started': model_forward_started,
        'unresolved': 'interpret saved conditional performance/cost' if outcome == 'PASS' else error or custody,
        'next_unique_instruction': 'Review this evidence; no automatic retry, tuning, training or next experiment.',
        'FORMAL_ACCEPTANCE_READY': False})
    print('\nSTATUS: ' + outcome + '\nEVIDENCE: ' + str(RUN), flush=True)
    if outcome == 'PASS' and scientific:
        print('depth | mean NLL | perplexity | median observed seconds')
        for depth in ('8', '16', '32'):
            row = scientific['per_depth'][depth]
            print(depth, row['mean_nll'], row['ppl'], row['median_observed_forward_seconds'])
        for name, row in scientific['paired_contrasts'].items():
            print(name, row['mean_delta_nll'], row['exploratory_bootstrap_percentile_interval'])
    # Seal compact records and a recovery checkpoint only after child processes stop.
    try:
        if not freeze_ok or custody.get('active_workers') or custody.get('unreaped_or_cleanup_errors') or git(REPO, 'rev-parse', 'HEAD') != args.expected_head:
            raise RuntimeError('Unsafe to publish automatically; external evidence retained')
        if git(REPO, 'status', '--porcelain=v1', '--untracked-files=all'):
            raise RuntimeError('Worktree changed during execution; external evidence retained without staging it')
        exported = ROOT / 'evidence'
        exported.mkdir(exist_ok=False)
        for path in sorted(RUN.rglob('*')):
            if path.is_file() and path.name not in ('rows.jsonl', 'mythos_launch.py'):
                dest = exported / path.relative_to(RUN)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, dest)
        save(ROOT / 'EXTERNAL_EVIDENCE_MANIFEST.json', {str(p): info(p) for p in sorted(RUN.rglob('*')) if p.is_file()})
        checkpoint = ('# MYTHOS-DEPTH-16-32-CPU-V1 checkpoint\n\nStatus: **' + outcome + '**.\n\n'
                      'Freeze commit: `' + args.expected_head + '`. Branch: `' + BRANCH + '`.\n\n'
                      'Environment: Python3.12.3/Torch2.11.0+cpu; CPU FP32,2 intraop/1 interop; no training/GPU.\n\n'
                      'Read evidence/summary.json for Purpose, Environment, Input, Expected, Actual, checks and error. '
                      'Read audit.json and independent_summary.json when present. No missing stage is PASS.\n\n'
                      'External raw evidence: `' + str(RUN) + '`. All external files are bound in EXTERNAL_EVIDENCE_MANIFEST.json. '
                      'This checkpoint commit is the subsequent Git HEAD, verified against origin by the operator.\n\n'
                      'No upstream/A5/B1/B2/D2-A/PR24 change. Old V1 interpretation remains rejected. '
                      'Historical development data; no fresh-test, training benefit, ACT superiority or hardware acceptance. '
                      'Formal Oracle BLOCKED/NOT_READY; FORMAL_ACCEPTANCE_READY=False.\n\n'
                      'Unresolved: ' + ('interpret conditional quality/cost tradeoff; no automatic depth choice' if outcome == 'PASS' else str(error or custody)) + '\n\n'
                      'Next unique instruction: review the saved outcome and cost/quality estimates before any new experiment; '
                      'if blocked or failed, resolve only the recorded cause under a separate protocol. No retry or automatic next phase.\n')
        (ROOT / 'CHECKPOINT.md').write_text(checkpoint, encoding='utf-8')
        subprocess.run(['git', '-C', str(REPO), 'add', '-f', '--', str(exported), str(ROOT / 'CHECKPOINT.md'),
                        str(ROOT / 'EXTERNAL_EVIDENCE_MANIFEST.json')], check=True)
        subprocess.run(['git', '-C', str(REPO), 'commit', '-m', 'Record16/32 CPU outcome and checkpoint: ' + outcome], check=True)
        subprocess.run(['git', '-C', str(REPO), 'push', 'origin', BRANCH], check=True, timeout=120)
        head = git(REPO, 'rev-parse', 'HEAD')
        remote = git(REPO, 'ls-remote', 'origin', 'refs/heads/' + BRANCH).split()[0]
        if head != remote or git(REPO, 'status', '--porcelain=v1', '--untracked-files=all'):
            raise RuntimeError('Final remote/clean verification failed')
        save(RUN / 'publication.json', {'Status': 'PASS', 'head': head, 'remote': remote, 'branch': BRANCH})
        print('CHECKPOINT PUSHED: ' + head)
    except BaseException as exc:
        save(RUN / 'publication.json', {'Status': 'BLOCKED', 'error': repr(exc), 'experiment_status': outcome})
        print('CHECKPOINT PUBLICATION BLOCKED: ' + repr(exc) + '; evidence remains at ' + str(RUN))
        return 2
    return 0 if outcome == 'PASS' else 2


if __name__ == '__main__':
    sys.exit(main())
