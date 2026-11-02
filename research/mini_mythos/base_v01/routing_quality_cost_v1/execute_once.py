"""One target-only paired quality/full-CPU-cost probe; no tuning or retry."""
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
PREVIOUS_V2 = Path('/workspaces/mythos-routing-feasibility-cpu-v2')
PREVIOUS_V3 = Path('/workspaces/mythos-routing-feasibility-cpu-v3')
PREVIOUS_RUN_V3 = Path('/workspaces/mythos-evidence/base_v01/routing_feasibility/attempt-v3')
PREVIOUS_RUN_V2 = Path('/workspaces/mythos-evidence/base_v01/routing_feasibility/attempt-v2')
PREVIOUS_RUN = Path('/workspaces/mythos-evidence/base_v01/routing_feasibility/attempt-v1')
PREFLIGHT = Path('/workspaces/mythos-evidence/base_v01/routing_feasibility/preflight-v2-20261102.json')
CORE_MANIFEST_SHA = '3f521d8b0d18d59af335fd351fa615532b5e270817e1feda9a8e4a32c0356d0b'
BRANCH = 'mythos-routing-quality-cost-cpu-v1'
BASE_CHECKPOINT = 'a4e9b27ff3c7ca8dbfd5760d5c630f59a9d0a683'
EXPECTED_REPO = Path('/workspaces/mythos-routing-quality-cost-cpu-v1')
EXPERIMENT = 'MYTHOS-ROUTING-QUALITY-COST-CPU-V1'
EXPECTED_FORWARD_CALLS = 194
PYTHON = '/workspaces/mythos-base-v01-cpu312/bin/python'
DATA_PYTHON = '/workspaces/mythos-depth-data-cpu312/bin/python'
RUN = Path('/workspaces/mythos-evidence/base_v01/routing_quality_cost/attempt-v1')
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
            protected_names = {'execute_once.py', 'run_smoke.py', 'run_routing.py', 'run_quality.py', 'data_quality.py', 'audit_quality.py', 'data_prepare.py', 'run_depth_budget.py', 'mythos_launch.py',
                               'observe_official.py', 'run_base.py', 'run_forward.py',
                               'run_decode.py'}
            if names & protected_names:
                result.append({'pid': int(item.name), 'names': sorted(names & protected_names)})
        except (OSError, ProcessLookupError):
            pass
    return result


def worker_command(spec_path, output):
    return [PYTHON, '-I', '-B', str(ROOT / 'run_quality.py'), '--spec', str(spec_path), '--out', str(output)]


def data_command(spec_path, output):
    return [DATA_PYTHON, '-I', '-B', str(ROOT / 'data_quality.py'), '--spec', str(spec_path), '--out', str(output)]


def audit_command(run_path, output):
    return [DATA_PYTHON, '-I', '-B', str(ROOT / 'audit_quality.py'), '--run', str(run_path), '--output', str(output)]


def worker_manifest(protected):
    # Keep labels under operator custody but do not let the model worker read them, even for hashing.
    return {name: value for name, value in protected.items() if name != str(RUN / 'data/private/labels.json')}


def descriptive_cpu_environment():
    """Best-effort read-only context, never a new acceptance threshold."""
    result = {'platform': platform.platform(), 'cpu_count': os.cpu_count(), 'scope': 'Shared-host descriptive context, not an isolation proof'}
    for name, filename in (('cpuinfo', '/proc/cpuinfo'), ('loadavg', '/proc/loadavg'), ('cpu_max', '/sys/fs/cgroup/cpu.max')):
        try:
            raw = Path(filename).read_text()
            result[name] = raw if name != 'cpuinfo' else '\n'.join(line for line in raw.splitlines() if line.startswith(('model name', 'flags', 'cpu family', 'model\t', 'stepping')))
        except OSError as exc:
            result[name] = None
            result[name + '_unavailable'] = repr(exc)
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
        print('BLOCKED: quality-cost attempt-v1 already exists; do not rerun or remove it. Evidence: ' + str(RUN))
        return 2
    RUN.mkdir(parents=True, exist_ok=False)
    checks, commands, before, states, inventories = [], [], {}, {}, {}
    outcome, error, mechanism, describe_cost, freeze_ok = 'NOT TESTED', None, None, None, False
    baseline_complete = False
    new_input_info = None
    save(RUN / 'CLAIM.json', {'Purpose': EXPERIMENT, 'Environment': PYTHON,
         'Input': {'freeze_commit': args.expected_head},
         'Expected': 'One frozen194-call paired CPU experiment after data gates; quality/timing screens remain exploratory',
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
              {'execute_once.py', 'run_quality.py', 'data_quality.py', 'audit_quality.py', 'test_startup.py', 'test_worker.py', 'test_data_audit.py', 'TEST_INVENTORY.json', 'PROTOCOL.md', 'CONTINUATION_REVIEW.json'}.issubset(package_manifest), True)
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
        states = {str(path): git_state(path) for path in (REPO, UPSTREAM, B1, PREVIOUS, PREVIOUS_ROUTING, PREVIOUS_V2, PREVIOUS_V3)}
        check('pinned upstream', states[str(UPSTREAM)], {'head': '69284c13746e849104f738d6d1a347b1f457df76', 'status': ''})
        check('protected B1 checkout', states[str(B1)], {'head': 'd88be474ebb2529c5b095e3732b1f25509f9b824', 'status': ''})
        check('protected accepted smoke checkout', states[str(PREVIOUS)], {'head': 'ac62e6ac1c04c54451beabc1138d651f55e383d9', 'status': ''})
        check('prior stopped routing checkout unchanged', states[str(PREVIOUS_ROUTING)], {'head': '919d2db8c2ee48b1d83fd8732720b587bd8be011', 'status': ''})
        check('stopped v2 checkout unchanged', states[str(PREVIOUS_V2)], {'head': 'b470cec1ebc6f9a675ce5b674f2073c14d66c237', 'status': ''})
        check('completed v3 checkout unchanged', states[str(PREVIOUS_V3)], {'head': BASE_CHECKPOINT, 'status': ''})
        for path in sorted(PREVIOUS_RUN_V3.rglob('*')):
            if path.is_file():
                before[str(path)] = info(path)
        for path in sorted(PREVIOUS_RUN_V2.rglob('*')):
            if path.is_file():
                before[str(path)] = info(path)
        for path in sorted(PREVIOUS_RUN.rglob('*')):
            if path.is_file():
                before[str(path)] = info(path)
        inventory_code = 'import importlib.metadata as m,json;print(json.dumps(sorted((d.metadata["Name"],d.version,str(d.locate_file(""))) for d in m.distributions())))'
        for executable in (PYTHON, DATA_PYTHON, '/workspaces/mythos-parcae-official-eval-cpu312/bin/python'):
            inventories[executable] = json.loads(subprocess.check_output([executable, '-I', '-B', '-c', inventory_code], text=True, timeout=60))
        save(RUN / 'environment_inventories_before.json', inventories)
        mem = dict(line.split(':', 1) for line in Path('/proc/meminfo').read_text().splitlines())
        resources = {'mem_available_bytes': int(mem['MemAvailable'].split()[0]) * 1024,
                     'disk_free_bytes': shutil.disk_usage(RUN).free, 'cpu_count': os.cpu_count(),
                     'cpu_environment': descriptive_cpu_environment()}
        save(RUN / 'resources.json', resources)
        check('available CPU memory >=2.5GiB', resources['mem_available_bytes'] >= 2684354560, True, 'BLOCKED')
        check('evidence free disk >=1GiB', resources['disk_free_bytes'] >= 1073741824, True, 'BLOCKED')
        for path, expected in PINS.items():
            actual = info(path)
            check('protected artifact ' + path.name, actual['sha256'], expected)
            before[str(path)] = actual
        check('completed data audit', json.loads((DATA / 'independent_audit.json').read_text())['Status'], 'PASS')
        # Protect tracked sources/history without reading prior model scores as JSON.
        for checkout in (REPO, UPSTREAM, B1, PREVIOUS, PREVIOUS_ROUTING, PREVIOUS_V2, PREVIOUS_V3):
            for name in git(checkout, 'ls-files').splitlines():
                path = checkout / name
                if path.is_file():
                    before[str(path)] = info(path)
        save(RUN / 'protected_before.json', {'files': before, 'git': states})
        baseline_complete = True
        inventories_tests = json.loads((ROOT / 'TEST_INVENTORY.json').read_text())
        for filename in ('test_startup.py', 'test_worker.py', 'test_data_audit.py'):
            label = Path(filename).stem
            print('Development checks: new ' + filename, flush=True)
            helper_report = RUN / (label + '_report.json')
            code = command(label, [PYTHON, '-I', '-B', str(ROOT / filename), '--report', str(helper_report)], timeout=180)
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
        # Verify the previous published seal before constructing labels. Original V3 data remain immutable.
        prior_seal_path = PREVIOUS_V3 / 'research/mini_mythos/base_v01/routing_feasibility_v3/EXTERNAL_EVIDENCE_MANIFEST.json'
        prior_seal = json.loads(prior_seal_path.read_text())
        check('previous v3 seal present', bool(prior_seal), True)
        for name, expected in prior_seal.items():
            path = Path(name)
            check('prior seal path containment', path.is_absolute() and path.is_relative_to(PREVIOUS_RUN_V3), True)
            check('prior sealed evidence ' + name, info(path), expected)
        source_data = PREVIOUS_RUN_V3 / 'data'
        check('original prefix bytes', info(source_data / 'private/inputs.json'),
              {'bytes': 58091, 'sha256': 'ae5f8ad5fd53d25afaf29487a650dc0300528b0926c9883652475c4ca7db127f'})
        data_spec = {'previous_data': str(source_data), 'repo': str(REPO), 'freeze_commit': args.expected_head}
        save(RUN / 'data_spec.json', data_spec)
        code = command('data_quality', data_command(RUN / 'data_spec.json', RUN / 'data'), timeout=180)
        data_completion_path = RUN / 'data/public/completion.json'
        if not data_completion_path.is_file():
            raise Stop('BLOCKED', 'Data completion missing; no model started')
        data_completion = json.loads(data_completion_path.read_text())
        if data_completion.get('Status') != 'PASS':
            raise Stop(data_completion.get('Status') if data_completion.get('Status') in ('FAIL', 'BLOCKED') else 'BLOCKED',
                       'Target label construction did not pass; no model started')
        check('data quality exit', code, 0)
        check('frozen quality data coverage', data_completion['Actual']['sample_count'] == 16
              and data_completion['Actual']['case_count'] == 32 and data_completion['Actual']['context_tokens'] == 128, True)
        for name in ('private/inputs.json', 'private/labels.json', 'public/targets.json'):
            check('new data artifact seal ' + name, info(RUN / 'data' / name), data_completion['artifacts'][name])
        new_inputs = RUN / 'data/private/inputs.json'
        new_input_info = info(new_inputs)
        check('worker inputs remain exact label-blind original bytes', new_input_info,
              {'bytes': 58091, 'sha256': 'ae5f8ad5fd53d25afaf29487a650dc0300528b0926c9883652475c4ca7db127f'})
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
        worker_protected = worker_manifest(before)
        save(operator / 'source_manifest.json', worker_protected)
        spec = {'run_id': EXPERIMENT, 'repo': str(REPO), 'upstream': str(UPSTREAM), 'branch': BRANCH,
                'model_dir': str(MODEL), 'tokenizer_path': str(TOKENIZER), 'inputs_path': str(new_inputs),
                'inputs_sha256': new_input_info['sha256'],
                'data_manifest_path': str(data_completion_path), 'data_manifest_sha256': info(data_completion_path)['sha256'],
                'source_manifest_path': str(operator / 'source_manifest.json'),
                'source_manifest_sha256': info(operator / 'source_manifest.json')['sha256'],
                'prior_run_dir': str(PREVIOUS_RUN_V3), 'run_dir': str(RUN / 'worker'), 'freeze_commit': args.expected_head, 'expected_head': args.expected_head}
        save(operator / 'spec.json', spec)
        save(operator / 'launcher_config.json', {'command': worker_command(operator / 'spec.json', RUN / 'worker'),
              'cwd': str(operator), 'timeout_seconds': 1800})
        print('Running one paired CPU quality/cost probe (194-call ceiling). Progress: '
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
              and completion['Actual']['total_model_calls_started'] == completion['Actual']['total_model_calls_completed'] == EXPECTED_FORWARD_CALLS
              and completion['Actual']['calls_started'] == completion['Actual']['calls_completed'] == 64
              and completion['Actual']['warmup_calls_started'] == completion['Actual']['warmup_calls_completed'] == 2
              and completion['Actual']['timed_calls_started'] == completion['Actual']['timed_calls_completed'] == 128
              and completion['Actual']['groups_completed'] == 16
              and completion['Actual']['loader_attempts'] == completion['Actual']['loader_returns'] == 1, True)
        code = command('audit', audit_command(RUN, RUN / 'audit.json'), timeout=300)
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
    save(RUN / 'resources_after.json', descriptive_cpu_environment())
    save(RUN / 'custody.json', custody)
    if custody['Status'] == 'FAIL':
        outcome = 'FAIL'
    elif custody['Status'] != 'PASS' and outcome == 'PASS':
        outcome = 'BLOCKED'
    calls_started = worker_completion.get('Actual', {}).get('total_model_calls_started', 0) if worker_completion else None
    calls_completed = worker_completion.get('Actual', {}).get('total_model_calls_completed', 0) if worker_completion else None
    model_forward_started = bool(calls_started) if calls_started is not None else None if worker_started else False
    report = {'Purpose': 'Paired adaptive-vs-fixed32 next-token quality and full public-API CPU cost',
              'Environment': {'model': PYTHON, 'data_and_independent_no_torch_audit': DATA_PYTHON},
              'Input': {'freeze_commit': args.expected_head, 'historical_corrected_inputs_sha256': PINS[INPUTS],
                        'prepared_inputs': new_input_info},
              'Expected': '16sources x128tokens x2seeds;64 quality+2warmup+128timed calls; frozen0.01; paired h0,scalarNLL/TV,byte/cost audit',
              'Actual': {'commands': commands, 'checks': checks, 'custody': custody,
                         'mechanism_results': mechanism, 'describe_cost': describe_cost,
                         'model_calls_started': calls_started, 'model_calls_completed': calls_completed},
              'Status': outcome, 'error': error, 'formal_launch_attempted': any(c['label'] == 'formal_launcher' for c in commands),
              'data_preparation_attempted': any(c['label']=='data_quality' for c in commands), 'prefixes_reused': True,
              'quality_cost_screens': mechanism.get('screens', 'NOT TESTED') if isinstance(mechanism, dict) else 'NOT TESTED',
              'worker_started': worker_started, 'model_forward_started': model_forward_started,
              'quality': 'EXPLORATORY_PAIRED_NEXT_TOKEN' if outcome == 'PASS' else 'NOT TESTED', 'training': 'NOT TESTED', 'hardware_efficiency_superiority': 'NOT ESTABLISHED',
              'Formal_Oracle': 'BLOCKED/NOT_READY', 'FORMAL_ACCEPTANCE_READY': False,
              'utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    save(RUN / 'summary.json', report)
    save(RUN / 'CHECKPOINT.json', {
        'Purpose': report['Purpose'], 'Environment': report['Environment'], 'Input': report['Input'],
        'Expected': report['Expected'], 'Actual': {'summary': str(RUN / 'summary.json'), 'error': error,
                                                 'quality_cost_screens': report['quality_cost_screens'], 'mechanism_results': mechanism},
        'Status': outcome, 'branch': BRANCH, 'requested_freeze_commit': args.expected_head,
        'freeze_verified': freeze_ok, 'worker_started': worker_started, 'model_forward_started': model_forward_started,
        'unresolved': 'Paired32-case next-token and same-machine CPU screens only; no fresh-test generalization, multi-token generation, training or population noninferiority' if outcome == 'PASS' else error or custody,
        'next_unique_instruction': 'Review paired quality differences and both timing rounds including overhead. Preserve negative screens without tuning. Decide next protocol separately; on engineering FAIL/BLOCKED resolve only recorded cause. No retry or automatic next phase.',
        'FORMAL_ACCEPTANCE_READY': False})
    print('\nSTATUS: ' + outcome + '\nEVIDENCE: ' + str(RUN), flush=True)
    if outcome == 'PASS':
        print('Paired quality/cost probe completed. Scientific screen failures remain separate from engineering execution status.')
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
        root_public = {'dependency_preflight.json', 'data_reuse.json', 'test_startup_report.json', 'test_worker_report.json', 'test_data_audit_report.json', 'CLAIM.json', 'CHECKPOINT.json', 'summary.json', 'custody.json', 'resources.json', 'resources_after.json',
                       'environment_inventories_before.json', 'environment_inventories_after.json',
                       'protected_before.json', 'operator_checks.jsonl', 'audit.json', 'publication_quiescence.json',
                       'test_data_report.json', 'test_routing_helpers_report.json', 'data_spec.json', 'data_frozen_manifest.json'}
        for label in ('test_startup', 'test_worker', 'test_data_audit', 'data_quality', 'formal_launcher', 'audit'):
            root_public.update({label + '.stdout', label + '.stderr', label + '_execution.json'})
        operator_public = {'claim.json', 'completion.json', 'launcher_config.json', 'source_manifest.json',
                           'spec.json', 'stdout.log', 'stderr.log'}
        worker_public = {'checks.jsonl', 'calls.jsonl', 'protected_before.json', 'protected_after.json',
                         'packages_before.json', 'packages_after.json', 'state_before.json', 'state_after.json',
                         'config_before.json', 'config_after.json', 'environment.json', 'git_after.json',
                         'preservation.json', 'GIT_BUNDLE_MANIFEST.json', 'completion.json', 'spec.json',
                         'input_inventory.json', 'routing_results.json', 'quality_results.json', 'timing_results.json', 'timed_calls.jsonl', 'warmup_calls.jsonl', 'quality_pairs.json', 'timing_calls.jsonl', 'timing_summary.json'}
        data_public = {'selection.json', 'labels_manifest.json', 'targets.json', 'completion.json', 'checks.jsonl', 'spec.json', 'sources_before.json',
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
        checkpoint = ('# ' + EXPERIMENT + ' checkpoint\n\nEngineering Status: **' + outcome + '**.\n\n'
                      'Freeze commit: `' + args.expected_head + '`. Branch: `' + BRANCH + '`.\n\n'
                      'Purpose/Input/Expected/Actual and scientific screens: evidence/summary.json and evidence/audit.json. '
                      'Environment: Python3.12.3/Torch2.11.0+cpu, CPU FP32,2 intra-op/1 inter-op; unchanged existing data environment; no training/GPU.\n\n'
                      'Design: same16 prefixes128tokens, seeds3101/3202; one actual next-token target per source; '
                      '64 observed quality calls,2warmups,128 timed calls,194 total. Timers cover unchanged public API including guards, readouts and policy, '
                      'but exclude external observation hooks and evidence writing. No missing stage is PASS.\n\n'
                      'External raw evidence: `' + str(RUN) + '`. EXTERNAL_EVIDENCE_MANIFEST.json binds all files at sealing; '
                      'publication.json is a later receipt outside that seal. Public metadata only is exported.\n\n'
                      'Scientific screens: ' + str(report['quality_cost_screens']) + '. Negative quality/speed screens do not mean code failure. '
                      'No population noninferiority, fresh-test generalization or general generation-quality claim.\n\n'
                      'Custody: see evidence/custody.json. OldV1/V2/V3 records, upstream, frozenTV0.01 and three environments preserved. '
                      'No A5 relaxation, B1 rerun, B2/D2-A or PR24 operation. Formal Oracle BLOCKED/NOT_READY; FORMAL_ACCEPTANCE_READY=False.\n\n'
                      'Unresolved: ' + ('external generalization, broader quality and deployment performance' if outcome == 'PASS' else str(error or custody)) + '\n\n'
                      'Next unique instruction: review paired quality and both timing rounds; preserve negative results without tuning; '
                      'design the next separately frozen comparison only after review. On engineering FAIL/BLOCKED resolve only recorded cause. Stop, no retry or automatic next phase.\n')
        (ROOT / 'CHECKPOINT.md').write_text(checkpoint, encoding='utf-8')
        subprocess.run(['git', '-C', str(REPO), 'add', '-f', '--', str(exported), str(ROOT / 'CHECKPOINT.md'),
                        str(ROOT / 'EXTERNAL_EVIDENCE_MANIFEST.json'), str(ROOT / 'PUBLIC_EXPORT.json')], check=True)
        subprocess.run(['git', '-C', str(REPO), 'commit', '-m', 'Record paired quality and CPU cost checkpoint: ' + outcome], check=True)
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
