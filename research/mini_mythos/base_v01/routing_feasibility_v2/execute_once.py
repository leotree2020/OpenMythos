"""One target-only routing feasibility probe; no threshold tuning or retry."""
import argparse
import datetime
import hashlib
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

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]
CORE = ROOT.parent / 'routing_feasibility_v1'
PREVIOUS_ROUTING = Path('/workspaces/mythos-routing-feasibility-cpu-v1')
PREVIOUS_RUN = Path('/workspaces/mythos-evidence/base_v01/routing_feasibility/attempt-v1')
PREFLIGHT = Path('/workspaces/mythos-evidence/base_v01/routing_feasibility/preflight-v2-20261102.json')
CORE_MANIFEST_SHA = '3f521d8b0d18d59af335fd351fa615532b5e270817e1feda9a8e4a32c0356d0b'
BRANCH = 'mythos-routing-feasibility-cpu-v2'
BASE_CHECKPOINT = '919d2db8c2ee48b1d83fd8732720b587bd8be011'
EXPECTED_REPO = Path('/workspaces/mythos-routing-feasibility-cpu-v2')
EXPERIMENT = 'MYTHOS-ROUTING-FEASIBILITY-CPU-V2'
EXPECTED_FORWARD_CALLS = 32
PYTHON = '/workspaces/mythos-base-v01-cpu312/bin/python'
DATA_PYTHON = '/workspaces/mythos-depth-data-cpu312/bin/python'
RUN = Path('/workspaces/mythos-evidence/base_v01/routing_feasibility/attempt-v2')
UPSTREAM = Path('/workspaces/mythos-parcae-pinned')
B1 = Path('/workspaces/mythos-base-v01-b1')
PREVIOUS = Path('/workspaces/mythos-adaptive-depth-140m-smoke-v1')
MODEL = Path('/workspaces/mythos-evidence/base_v01/b1/b1-20261101T021657Z/downloads/model')
TOKENIZER = MODEL.parent / 'tokenizer/tokenizer.json'
DATA = Path('/workspaces/mythos-evidence/base_v01/boundary_repair/data-20261101T134401Z')
INPUTS = DATA / 'build_first/inputs.json'
PARTITION = DATA / 'build_first/partition.json'
OLD_DATA = Path('/workspaces/mythos-evidence/base_v01/depth_budget/preparation-v1-20261101')
CORPUS = OLD_DATA / 'test.parquet'
OLD_INPUTS = OLD_DATA.parent / 'preparation-v2-20261101/inputs.json'
LEDGER = REPO / 'research/mini_mythos/base_v01/boundary_repair_v1/BOUNDARY_LEDGER.json'
SELECTION_CHANGE = REPO / 'research/mini_mythos/base_v01/boundary_repair_v1/evidence/selection_change.json'
CONTROLLER = REPO / 'research/mini_mythos/base_v01/adaptive_depth_v1/adaptive_depth.py'
PINS = {
    CORPUS: '3ee89cd6a2ab912afd5d01e98867b46a67d9ec7a9eca0910e5e4c3cdd4cc1925',
    OLD_INPUTS: 'f38a1618d7904df7c530d9f0f322949a847befcb75e4177de2bc8e65bc53a315',
    SELECTION_CHANGE: '7baab72fb993e2f49f806f99d70fb162441f994371136e52e42277fa361474f6',
    INPUTS: '3abb324ea2876abb78e18d86ec257a9e1d388f9501bd8cdd6c99011ac11cf41e',
    PARTITION: '95a217a815596c928a0b721837b567a08ed8c6f667839fdf6d4311113c253aa4',
    DATA / 'build_first/manifest.json': '6593d2a6906fb803af1095fd4f76980d830635b60cb6c50da0d1def00fbb8cf1',
    DATA / 'independent_audit.json': '6f0e15cbdad4d987b2a0fea9166e2ffc9b53bf1f0bd2dc99155329299498aa44',
    LEDGER: 'f5f7858b989451671e4c7ed27192642dec3f9b2a1ccd214cc9e3cc30bcebb5d3',
    MODEL / 'pytorch_model.bin': 'ed6eb306464dd0d694e9eacd58f7e06ac3e44b43cb7c5c79dbcb1543059c6621',
    MODEL / 'config.json': '5c8fc785c2f6dba67d0370ad715034860e3b22bfce850da825c06baa03923c13',
    TOKENIZER: 'e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77',
    CONTROLLER: 'daa6b5b014f9d5f77cc47e2ba14a7027065c135b2cac7f6bcda58d0e6d6457b8',
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
            protected_names = {'execute_once.py', 'run_smoke.py', 'run_routing.py', 'data_prepare.py', 'run_depth_budget.py', 'mythos_launch.py',
                               'observe_official.py', 'run_base.py', 'run_forward.py',
                               'run_decode.py'}
            if names & protected_names:
                result.append({'pid': int(item.name), 'names': sorted(names & protected_names)})
        except (OSError, ProcessLookupError):
            pass
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--expected-head', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[0-9a-f]{40}', args.expected_head):
        parser.error('--expected-head must be a full frozen commit SHA')
    if platform.system() != 'Linux' or not Path('/workspaces').is_dir():
        print('BLOCKED: run only inside the designated Codespace; no model started.')
        return 2
    if RUN.exists():
        print('BLOCKED: attempt-v2 already exists; do not rerun or remove it. Evidence: ' + str(RUN))
        return 2
    RUN.mkdir(parents=True, exist_ok=False)
    checks, commands, before, states, inventories = [], [], {}, {}, {}
    outcome, error, mechanism, describe_cost, freeze_ok = 'NOT TESTED', None, None, None, False
    baseline_complete = False
    new_input_info = None
    save(RUN / 'CLAIM.json', {'Purpose': EXPERIMENT, 'Environment': PYTHON,
         'Input': {'freeze_commit': args.expected_head},
         'Expected': 'One frozen32-call CPU routing probe after data gates, no quality or speed conclusion',
         'Actual': {'pid': os.getpid(), 'argv': sys.argv}, 'Status': 'NOT TESTED',
         'utc': datetime.datetime.now(datetime.timezone.utc).isoformat()})
    def interrupted(signum, frame):
        raise Stop('BLOCKED', 'Operator received signal ' + str(signum))
    signal.signal(signal.SIGTERM, interrupted)

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
        check('designated isolated worktree', str(REPO.resolve()), str(EXPECTED_REPO))
        check('Python version', platform.python_version(), '3.12.3', 'BLOCKED')
        check('isolated no bytecode runtime', bool(sys.flags.isolated) and sys.dont_write_bytecode, True)
        check('frozen branch', git(REPO, 'branch', '--show-current'), BRANCH)
        check('frozen clean execution checkout', git_state(REPO), {'head': args.expected_head, 'status': ''})
        check('frozen lineage from prior development checkpoint',
              git(REPO, 'merge-base', BASE_CHECKPOINT, args.expected_head), BASE_CHECKPOINT)
        check('remote freeze', git(REPO, 'ls-remote', 'origin', 'refs/heads/' + BRANCH).split()[0], args.expected_head)
        freeze_ok = True
        package_manifest = json.loads((ROOT / 'SOURCE_MANIFEST.json').read_text())
        check('required routing package files',
              {'execute_once.py', 'PROTOCOL.md', 'CONTINUATION_REVIEW.json', 'MECHANISM_SEQUENCE.md'}.issubset(package_manifest), True)
        for name, expected in package_manifest.items():
            check('manifest path inside package ' + name,
                  not Path(name).is_absolute() and (ROOT / name).resolve().is_relative_to(ROOT), True)
            check('frozen source ' + name, info(ROOT / name), expected)
        check('unchanged previously reviewed core manifest', info(CORE / 'SOURCE_MANIFEST.json')['sha256'], CORE_MANIFEST_SHA)
        for name, expected in json.loads((CORE / 'SOURCE_MANIFEST.json').read_text()).items():
            check('old core path containment ' + name, not Path(name).is_absolute() and (CORE / name).resolve().is_relative_to(CORE), True)
            check('unchanged reviewed core ' + name, info(CORE / name), expected)
        preflight = json.loads(PREFLIGHT.read_text())
        check('complete target dependency preflight', preflight['Status'] == 'PASS' and len(preflight['Actual']['checks']) == 36
              and all(c['Status'] == 'PASS' for c in preflight['Actual']['checks'])
              and preflight['Input']['corrected_path'] == str(OLD_INPUTS), True)
        shutil.copyfile(PREFLIGHT, RUN / 'dependency_preflight.json')
        before[str(PREFLIGHT)] = info(PREFLIGHT)
        check('exclusive model worker', active_workers(), [], 'BLOCKED')
        states = {str(path): git_state(path) for path in (REPO, UPSTREAM, B1, PREVIOUS, PREVIOUS_ROUTING)}
        check('pinned upstream', states[str(UPSTREAM)], {'head': '69284c13746e849104f738d6d1a347b1f457df76', 'status': ''})
        check('protected B1 checkout', states[str(B1)], {'head': 'd88be474ebb2529c5b095e3732b1f25509f9b824', 'status': ''})
        check('protected accepted smoke checkout', states[str(PREVIOUS)], {'head': 'ac62e6ac1c04c54451beabc1138d651f55e383d9', 'status': ''})
        check('prior stopped routing checkout unchanged', states[str(PREVIOUS_ROUTING)], {'head': BASE_CHECKPOINT, 'status': ''})
        for path in sorted(PREVIOUS_RUN.rglob('*')):
            if path.is_file():
                before[str(path)] = info(path)
        inventory_code = 'import importlib.metadata as m,json;print(json.dumps(sorted((d.metadata["Name"],d.version,str(d.locate_file(""))) for d in m.distributions())))'
        for executable in (PYTHON, DATA_PYTHON, '/workspaces/mythos-parcae-official-eval-cpu312/bin/python'):
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
        check('completed data audit', json.loads((DATA / 'independent_audit.json').read_text())['Status'], 'PASS')
        # Protect tracked sources/history without reading prior model scores as JSON.
        for checkout in (REPO, UPSTREAM, B1, PREVIOUS, PREVIOUS_ROUTING):
            for name in git(checkout, 'ls-files').splitlines():
                path = checkout / name
                if path.is_file():
                    before[str(path)] = info(path)
        save(RUN / 'protected_before.json', {'files': before, 'git': states})
        baseline_complete = True
        inventories_tests = json.loads((CORE / 'TEST_INVENTORY.json').read_text())
        for filename in ('test_data.py', 'test_routing_helpers.py'):
            label = Path(filename).stem
            print('Development checks: new ' + filename, flush=True)
            helper_report = RUN / (label + '_report.json')
            code = command(label, [PYTHON, '-I', '-B', str(CORE / filename), '--report', str(helper_report)], timeout=180)
            if not helper_report.is_file():
                raise Stop('BLOCKED', label + ' machine-readable report missing')
            helper = json.loads(helper_report.read_text())
            if helper.get('Status') != 'PASS':
                raise Stop(helper.get('Status') if helper.get('Status') in ('FAIL', 'BLOCKED') else 'BLOCKED',
                           label + ' did not pass; no model started')
            check(label + ' exit', code, 0)
            expected_tests = inventories_tests[filename]['test_ids']
            actual_helper = helper['Actual']
            check(label + ' exact frozen coverage',
                  bool(expected_tests) and len(expected_tests) == len(set(expected_tests))
                  and actual_helper['test_ids'] == sorted(expected_tests)
                  and actual_helper['planned'] == actual_helper['run'] == len(expected_tests)
                  and all(actual_helper[k] == 0 for k in ('failures', 'errors', 'skipped',
                                                        'expected_failures', 'unexpected_successes')), True)
        data_spec = {'repo': str(REPO), 'freeze_commit': args.expected_head,
                     'corpus': str(CORPUS), 'tokenizer': str(TOKENIZER), 'ledger': str(LEDGER),
                     'partition': str(PARTITION), 'old_inputs': str(OLD_INPUTS),
                     'corrected_inputs': str(INPUTS), 'selection_change': str(SELECTION_CHANGE)}
        save(RUN / 'data_spec.json', data_spec)
        print('Preparing one frozen16-source,128-token routing dataset; no model imports.', flush=True)
        code = command('data_prepare', [DATA_PYTHON, '-I', '-B', str(CORE / 'data_prepare.py'),
                                       '--spec', str(RUN / 'data_spec.json'), '--out', str(RUN / 'data')], timeout=180)
        data_completion_path = RUN / 'data/public/completion.json'
        if not data_completion_path.is_file():
            raise Stop('BLOCKED', 'Data completion missing; no model started')
        data_completion = json.loads(data_completion_path.read_text())
        if code or data_completion.get('Status') != 'PASS':
            raise Stop(data_completion.get('Status') if data_completion.get('Status') in ('FAIL', 'BLOCKED') else 'BLOCKED',
                       'Data preparation did not pass; no model started')
        check('complete data coverage before model loading',
              data_completion['Actual']['sample_count'] == 16 and data_completion['Actual']['call_budget'] == 32, True)
        new_inputs = RUN / 'data/private/inputs.json'
        new_input_info = info(new_inputs)
        check('sealed new input bytes', new_input_info, data_completion['artifacts']['private/inputs.json'])
        check('sealed selection bytes', info(RUN / 'data/public/selection.json'),
              data_completion['artifacts']['public/selection.json'])
        # Freeze every data-stage artifact before the first model call. Publication
        # later exports only public metadata, never token arrays or source text.
        for path in sorted((RUN / 'data').rglob('*')):
            if path.is_file():
                before[str(path)] = info(path)
        before[str(RUN / 'data_spec.json')] = info(RUN / 'data_spec.json')
        save(RUN / 'data_frozen_manifest.json', {str(path): info(path) for path in sorted((RUN / 'data').rglob('*')) if path.is_file()})
        operator = RUN / 'operator'
        operator.mkdir()
        shutil.copyfile(CORE / 'mythos_launch.py', operator / 'mythos_launch.py')
        check('unchanged validated launcher', info(operator / 'mythos_launch.py')['sha256'],
              '8083b948eebdf08c2d14a79d940ccead72db5f10c6bac8d9061816b6c9ea05c3')
        save(operator / 'source_manifest.json', before)
        spec = {'run_id': EXPERIMENT, 'repo': str(REPO), 'upstream': str(UPSTREAM), 'branch': BRANCH,
                'model_dir': str(MODEL), 'tokenizer_path': str(TOKENIZER), 'inputs_path': str(new_inputs),
                'inputs_sha256': new_input_info['sha256'],
                'data_manifest_path': str(data_completion_path), 'data_manifest_sha256': info(data_completion_path)['sha256'],
                'source_manifest_path': str(operator / 'source_manifest.json'),
                'source_manifest_sha256': info(operator / 'source_manifest.json')['sha256'],
                'run_dir': str(RUN / 'worker'), 'freeze_commit': args.expected_head, 'expected_head': args.expected_head}
        save(operator / 'spec.json', spec)
        save(operator / 'launcher_config.json', {'command': [PYTHON, '-I', '-B', str(CORE / 'run_routing.py'),
              '--spec', str(operator / 'spec.json'), '--out', str(RUN / 'worker')],
              'cwd': str(operator), 'timeout_seconds': 1200})
        print('Running one CPU normal-prefix routing probe (32-call ceiling). Progress: '
              + str(operator / 'stdout.log'), flush=True)
        code = command('formal_launcher', [PYTHON, '-I', '-B', str(operator / 'mythos_launch.py'),
                                          '--config', str(operator / 'launcher_config.json')])
        worker_file = RUN / 'worker/public/completion.json'
        if not worker_file.is_file():
            raise Stop('BLOCKED', 'Worker completion missing')
        completion = json.loads(worker_file.read_text())
        if code or completion.get('Status') != 'PASS':
            raise Stop(completion.get('Status') if completion.get('Status') in ('FAIL', 'BLOCKED') else 'BLOCKED',
                       'Formal worker did not pass; no retry')
        check('complete frozen worker coverage',
              completion.get('complete_coverage') is True
              and completion['Actual']['calls_started'] == completion['Actual']['calls_completed'] == EXPECTED_FORWARD_CALLS
              and completion['Actual']['groups_completed'] == 16
              and completion['Actual']['loader_attempts'] == completion['Actual']['loader_returns'] == 1, True)
        code = command('audit', [DATA_PYTHON, '-I', '-B', str(CORE / 'audit_routing.py'),
              '--run', str(RUN),
              '--output', str(RUN / 'audit.json')], timeout=180)
        if not (RUN / 'audit.json').is_file():
            raise Stop('BLOCKED', 'Independent audit report missing')
        audit = json.loads((RUN / 'audit.json').read_text())
        if audit['Status'] != 'PASS':
            raise Stop(audit['Status'] if audit['Status'] in ('FAIL', 'BLOCKED') else 'BLOCKED', 'Independent audit stopped')
        check('independent audit exit', code, 0)
        mechanism = audit['Actual']['mechanism_results']
        describe_cost = audit['Actual'].get('describe_cost')
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
    worker_started = (RUN / 'worker/public/spec.json').is_file()
    worker_completion = None
    try:
        if (RUN / 'worker/public/completion.json').is_file():
            worker_completion = json.loads((RUN / 'worker/public/completion.json').read_text())
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
    calls_started = worker_completion.get('Actual', {}).get('calls_started', 0) if worker_completion else None
    calls_completed = worker_completion.get('Actual', {}).get('calls_completed', 0) if worker_completion else None
    model_forward_started = bool(calls_started) if calls_started is not None else None if worker_started else False
    report = {'Purpose': 'Normal-length new-to-Parcae-depth/routing CPU early-exit feasibility',
              'Environment': {'model': PYTHON, 'data_and_independent_no_torch_audit': DATA_PYTHON},
              'Input': {'freeze_commit': args.expected_head, 'historical_corrected_inputs_sha256': PINS[INPUTS],
                        'prepared_inputs': new_input_info},
              'Expected': '16 sources x128tokens x2seeds,32 adaptive calls; frozen0.01, input/cost/byte/TV audit; quality and acceleration NOT TESTED',
              'Actual': {'commands': commands, 'checks': checks, 'custody': custody,
                         'mechanism_results': mechanism, 'describe_cost': describe_cost,
                         'model_calls_started': calls_started, 'model_calls_completed': calls_completed},
              'Status': outcome, 'error': error, 'formal_launch_attempted': any(c['label'] == 'formal_launcher' for c in commands),
              'data_preparation_attempted': any(c['label'] == 'data_prepare' for c in commands),
              'early_exit_screen': mechanism.get('early_exit_screen', 'NOT TESTED') if isinstance(mechanism, dict) else 'NOT TESTED',
              'worker_started': worker_started, 'model_forward_started': model_forward_started,
              'quality': 'NOT TESTED', 'training': 'NOT TESTED', 'hardware_efficiency_superiority': 'NOT TESTED',
              'Formal_Oracle': 'BLOCKED/NOT_READY', 'FORMAL_ACCEPTANCE_READY': False,
              'utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    save(RUN / 'summary.json', report)
    save(RUN / 'CHECKPOINT.json', {
        'Purpose': report['Purpose'], 'Environment': report['Environment'], 'Input': report['Input'],
        'Expected': report['Expected'], 'Actual': {'summary': str(RUN / 'summary.json'), 'error': error,
                                                 'early_exit_screen': report['early_exit_screen'], 'mechanism_results': mechanism},
        'Status': outcome, 'branch': BRANCH, 'requested_freeze_commit': args.expected_head,
        'freeze_verified': freeze_ok, 'worker_started': worker_started, 'model_forward_started': model_forward_started,
        'unresolved': 'No quality benefit or hardware-efficiency superiority has been tested; data are new to the Parcae depth/routing experiments, not guaranteed new to earlier project tests or pretraining' if outcome == 'PASS' else error or custody,
        'next_unique_instruction': 'Review source selection,32-call routing distribution and complete overhead. If all32 use depth32, stop expansion and record no early-exit signal on this sample. Otherwise freeze a separate quality/cost protocol before new model calls. On FAIL/BLOCKED resolve only the recorded cause under a new protocol. No retry or automatic next experiment.',
        'FORMAL_ACCEPTANCE_READY': False})
    print('\nSTATUS: ' + outcome + '\nEVIDENCE: ' + str(RUN), flush=True)
    if outcome == 'PASS':
        print('Routing probe completed. Zero early exits is a scientific result, not implementation FAIL. Quality and actual acceleration: NOT TESTED.')
    # Seal compact records and a recovery checkpoint only after child processes stop.
    try:
        publication_workers = active_workers()
        publication_unreaped = [c for c in commands if not c['child_reaped'] or c['cleanup_errors']]
        save(RUN / 'publication_quiescence.json', {'Status': 'PASS' if not publication_workers and not publication_unreaped else 'BLOCKED',
             'active_workers': publication_workers, 'unreaped_or_cleanup_errors': publication_unreaped})
        if not freeze_ok or publication_workers or publication_unreaped or git(REPO, 'rev-parse', 'HEAD') != args.expected_head:
            raise RuntimeError('Unsafe to publish automatically; external evidence retained')
        if git(REPO, 'status', '--porcelain=v1', '--untracked-files=all'):
            raise RuntimeError('Worktree changed during execution; external evidence retained without staging it')
        exported = ROOT / 'evidence'
        exported.mkdir(exist_ok=False)
        root_public = {'dependency_preflight.json', 'CLAIM.json', 'CHECKPOINT.json', 'summary.json', 'custody.json', 'resources.json',
                       'environment_inventories_before.json', 'environment_inventories_after.json',
                       'protected_before.json', 'operator_checks.jsonl', 'audit.json', 'publication_quiescence.json',
                       'test_data_report.json', 'test_routing_helpers_report.json', 'data_spec.json', 'data_frozen_manifest.json'}
        for label in ('test_data', 'test_routing_helpers', 'data_prepare', 'formal_launcher', 'audit'):
            root_public.update({label + '.stdout', label + '.stderr', label + '_execution.json'})
        operator_public = {'claim.json', 'completion.json', 'launcher_config.json', 'source_manifest.json',
                           'spec.json', 'stdout.log', 'stderr.log'}
        worker_public = {'checks.jsonl', 'calls.jsonl', 'protected_before.json', 'protected_after.json',
                         'packages_before.json', 'packages_after.json', 'state_before.json', 'state_after.json',
                         'config_before.json', 'config_after.json', 'environment.json', 'git_after.json',
                         'preservation.json', 'GIT_BUNDLE_MANIFEST.json', 'completion.json', 'spec.json',
                         'input_inventory.json', 'routing_results.json'}
        data_public = {'selection.json', 'completion.json', 'checks.jsonl', 'spec.json', 'sources_before.json',
                       'environment.json', 'protected_before.json', 'protected_after.json', 'preservation.json'}
        exported_files = []
        for path in sorted(RUN.rglob('*')):
            if not path.is_file():
                continue
            relative = path.relative_to(RUN)
            parts = relative.parts
            allowed = (len(parts) == 1 and path.name in root_public
                       or len(parts) == 2 and parts[0] == 'operator' and path.name in operator_public
                       or len(parts) == 2 and parts[0] == 'worker' and path.name in {'FULL_MANIFEST.json', 'EMERGENCY.json'}
                       or len(parts) == 2 and parts[0] == 'data' and path.name in {'FULL_MANIFEST.json', 'EMERGENCY.json'}
                       or len(parts) == 3 and parts[:2] == ('data', 'public') and path.name in data_public
                       or len(parts) == 3 and parts[:2] == ('worker', 'public')
                       and (path.name in worker_public or re.fullmatch(r'call_\d{3}\.json', path.name)))
            if allowed:
                dest = exported / path.relative_to(RUN)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, dest)
                exported_files.append(str(relative))
        save(ROOT / 'PUBLIC_EXPORT.json', {'files': exported_files,
             'private_worker_data_exported': False, 'private_prepared_data_exported': False, 'original_weights_or_tokens_exported': False,
             'policy': 'Explicit public metadata/log allowlist; all raw tensors and input IDs stay external'})
        save(ROOT / 'EXTERNAL_EVIDENCE_MANIFEST.json', {str(p): info(p) for p in sorted(RUN.rglob('*')) if p.is_file()})
        checkpoint = ('# ' + EXPERIMENT + ' checkpoint\n\nStatus: **' + outcome + '**.\n\n'
                      'Freeze commit: `' + args.expected_head + '`. Branch: `' + BRANCH + '`.\n\n'
                      'Environment: model Python3.12.3/Torch2.11.0+cpu; CPU FP32,2 intraop/1 interop; existing data env for PyArrow/tokenizers preparation and independent no-Torch audit. No training/GPU.\n\n'
                      'Read evidence/summary.json for Purpose, Environment, Input, Expected, Actual, checks and error. '
                      'Read evidence/data/public/completion.json, evidence/audit.json and evidence/worker/public/completion.json when present. No missing stage is PASS.\n\n'
                      'External raw evidence: `' + str(RUN) + '`. Files present at sealing are bound in EXTERNAL_EVIDENCE_MANIFEST.json; publication.json is a subsequently generated receipt outside that manifest. '
                      'This checkpoint commit is the subsequent Git HEAD, verified against origin by the operator.\n\n'
                      'Protected-file/environment preservation results are recorded in custody.json; do not infer unchanged state for any unverified or failed check. No A5 relaxation, B1 rerun, B2/D2-A or PR24 operation was scheduled. Old V1 interpretation remains rejected. '
                      '32-call normal-prefix routing feasibility only. A valid all-depth32 result is engineering PASS and scientific early-exit screen FAIL/NO_EARLY_EXIT_ON_THIS_SAMPLE, not implementation failure. '
                      'Recorded scientific screen: ' + str(report['early_exit_screen']) + '. '
                      'Sources are new to the prior Parcae depth/routing inputs only, not guaranteed unseen in earlier project tests or pretraining. No quality, fresh-test, training benefit, ACT superiority or hardware acceptance. '
                      'Formal Oracle BLOCKED/NOT_READY; FORMAL_ACCEPTANCE_READY=False.\n\n'
                      'Unresolved: ' + ('quality benefit and hardware-efficiency superiority remain NOT TESTED' if outcome == 'PASS' else str(error or custody)) + '\n\n'
                      'Next unique instruction: review selection, routing distribution and complete overhead. If all32 calls select32, stop expansion and record no early-exit signal on this sample; otherwise freeze a separate quality/cost protocol before new model calls. '
                      'if blocked or failed, resolve only the recorded cause under a separate protocol. No retry or automatic next phase.\n')
        (ROOT / 'CHECKPOINT.md').write_text(checkpoint, encoding='utf-8')
        subprocess.run(['git', '-C', str(REPO), 'add', '-f', '--', str(exported), str(ROOT / 'CHECKPOINT.md'),
                        str(ROOT / 'EXTERNAL_EVIDENCE_MANIFEST.json'), str(ROOT / 'PUBLIC_EXPORT.json')], check=True)
        subprocess.run(['git', '-C', str(REPO), 'commit', '-m', 'Record normal-prefix routing feasibility and checkpoint: ' + outcome], check=True)
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
