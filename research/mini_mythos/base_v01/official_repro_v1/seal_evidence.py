"""Post-run evidence custody only. Never imports Torch or starts model evaluation."""
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

REPO = Path('/workspaces/mythos-base-v01-rope-diag-v11')
PACKAGE = REPO / 'research/mini_mythos/base_v01/official_repro_v1'
RUN = Path('/workspaces/mythos-evidence/base_v01/official_repro/official-core-limited-v1-20261101T093733Z')
OPERATOR = Path(str(RUN) + '-operator')
REVIEW = Path(str(RUN) + '-review')
BUNDLE = RUN.parent / 'preparation-v1-20261101/cache/eval_bundle'
BASE_PYTHON = '/workspaces/mythos-base-v01-cpu312/bin/python'
EVAL_PYTHON = '/workspaces/mythos-parcae-official-eval-cpu312/bin/python'


def fingerprint(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return {'bytes': path.stat().st_size, 'sha256': digest.hexdigest()}


def write_json(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as output:
        json.dump(value, output, indent=2, ensure_ascii=False, allow_nan=False)
        output.write('\n')


def command(args, cwd=None):
    result = subprocess.run(args, cwd=cwd, text=True, capture_output=True, timeout=180)
    return {'args': args, 'returncode': result.returncode,
            'stdout': result.stdout, 'stderr': result.stderr}


def manifest():
    return {str(path): fingerprint(path)
            for root in (RUN, OPERATOR) for path in sorted(root.rglob('*')) if path.is_file()}


def main():
    # A completion file alone is insufficient if a reserved PID is still alive.
    if not (OPERATOR / 'completion.json').is_file():
        raise RuntimeError('Formal launcher has not completed; no sealing or audit allowed')
    for pid, expected_start in ((7340, '180513'), (7362, '180521')):
        stat = Path('/proc') / str(pid) / 'stat'
        if stat.exists():
            fields = stat.read_text().rsplit(')', 1)[1].split()
            if fields[19] == expected_start and fields[0] != 'Z':
                raise RuntimeError('Reserved process is still alive: ' + str(pid))
    REVIEW.mkdir(exist_ok=False)
    before = manifest()
    write_json(REVIEW / 'RAW_MANIFEST_BEFORE.json', before)
    post = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'Purpose': 'Verify custody and protection after the stopped official limited run',
            'Environment': 'Designated Codespace; read-only stdlib subprocess checks',
            'Input': str(PACKAGE / 'SOURCE_DATA_MANIFEST.json'),
            'Expected': 'Frozen inputs/source/packages unchanged; no changes outside research package',
            'source_inputs': [], 'protected_inputs': [], 'frozen_tools': [], 'git': {}}
    for filename, expected in {
        'observe_official.py': 'a441740839bdf94f773c1023a917f751807a28ec6f2779d4890edbfa3a30226b',
        'PROTOCOL.md': '0073ebabb3fbca5e7178c5bed4191c6b6d9b07cfe10579ab32af72c5750aeb7d',
        'audit_official.py': '5c211b17fa2473a2950b562991a8fe1fe83c5560d07d99cba0d91bf7d71e1f88',
        'summarize_partial.py': 'bbab37a9c5ffcb42d4d8970cb3c977c0c8459471ad1fec0354b7fb63f40190a6',
    }.items():
        actual = fingerprint(PACKAGE / filename)
        post['frozen_tools'].append({'path': str(PACKAGE / filename), 'expected_sha256': expected,
                                     'actual': actual, 'match': actual['sha256'] == expected})
    sources = json.loads((PACKAGE / 'SOURCE_DATA_MANIFEST.json').read_text())
    for name, expected in sources.items():
        path = Path(name)
        actual = fingerprint(path) if path.is_file() else None
        okay = actual is not None and actual['bytes'] == expected['size'] and actual['sha256'] == expected['sha256']
        post['source_inputs'].append({'path': name, 'expected': expected, 'actual': actual, 'match': okay})
    preflight = json.loads((PACKAGE / 'FINAL_PREFLIGHT.json').read_text())
    for expected in preflight['inputs']:
        actual = fingerprint(Path(expected['path']))
        post['protected_inputs'].append({'path': expected['path'], 'actual': actual,
            'match': actual['bytes'] == expected['bytes'] and actual['sha256'] == expected['sha256']})
    old = json.loads((PACKAGE / 'PREFLIGHT.json').read_text())
    packages = command([BASE_PYTHON, '-I', '-B', '-m', 'pip', 'list', '--format=json', '--disable-pip-version-check'])
    post['baseline_packages'] = packages
    post['baseline_packages_unchanged'] = packages['returncode'] == 0 and json.loads(packages['stdout']) == json.loads(old['packages']['stdout'])
    for name in [str(REPO), '/workspaces/mythos-parcae-pinned', '/workspaces/mythos-base-v01-b1']:
        post['git'][name] = {key: command(['git', '-C', name] + args)
                            for key, args in [('head', ['rev-parse', 'HEAD']),
                                              ('status', ['status', '--porcelain=v1', '--untracked-files=all'])]}
    changes = command(['git', '-C', str(REPO), 'diff', '--name-only', '6b52321746f393fa36711ff3896a5a9c5484c7c0', 'HEAD'])
    post['branch_changes'] = changes
    prefix = 'research/mini_mythos/base_v01/official_repro_v1/'
    post['all_branch_changes_in_scope'] = changes['returncode'] == 0 and all(x.startswith(prefix) for x in changes['stdout'].splitlines())
    work_status = post['git'][str(REPO)]['status']
    post['working_tree_clean_before_seal'] = work_status['returncode'] == 0 and work_status['stdout'] == ''
    post['disk_free_bytes'] = shutil.disk_usage(RUN).free
    protected_git = [post['git'][name] for name in ['/workspaces/mythos-parcae-pinned', '/workspaces/mythos-base-v01-b1']]
    heads_ok = all(post['git'][name]['head']['stdout'] == old['git'][name]['head']['stdout']
                   for name in ['/workspaces/mythos-parcae-pinned', '/workspaces/mythos-base-v01-b1'])
    git_ok = heads_ok and all(r['head']['returncode'] == r['status']['returncode'] == 0 and r['status']['stdout'] == '' for r in protected_git)
    okay = (all(x['match'] for x in post['source_inputs'] + post['protected_inputs'] + post['frozen_tools'])
            and post['baseline_packages_unchanged'] and post['all_branch_changes_in_scope']
            and post['working_tree_clean_before_seal'] and git_ok)
    post['Status'] = 'PASS' if okay else 'FAIL'
    post['Actual'] = {'source_input_count': len(sources), 'protected_input_count': len(post['protected_inputs']),
                      'all_protection_checks': okay}
    write_json(REVIEW / 'POSTFLIGHT.json', post)
    invocations = []
    if okay:
        for filename, interpreter, extra in [
            ('audit_official.py', EVAL_PYTHON, ['--max-per-task', '12']),
            ('summarize_partial.py', BASE_PYTHON, ['--inventory', str(PACKAGE / 'TASK_INVENTORY.json')])]:
            output = REVIEW / (Path(filename).stem + '.json')
            invocation = command([interpreter, '-I', '-B', str(PACKAGE / filename),
                                  '--run', str(RUN), '--bundle', str(BUNDLE), '--output', str(output)] + extra)
            invocation['source'] = fingerprint(PACKAGE / filename)
            invocations.append(invocation)
            write_json(REVIEW / (Path(filename).stem + '_invocation.json'), invocation)
            # Both are read-only evidence examinations, not continuation of a failed model run.
    after = manifest()
    write_json(REVIEW / 'RAW_MANIFEST_AFTER.json', after)
    write_json(REVIEW / 'CUSTODY.json', {'Purpose': 'Ensure post-run auditing did not change original evidence',
        'Environment': 'Stopped formal processes; read-only postprocessing', 'Input': str(RUN),
        'Expected': 'All original run/operator file names, sizes and hashes unchanged',
        'Actual': {'unchanged': before == after, 'files': len(after)},
        'Status': 'PASS' if before == after else 'FAIL'})
    evidence = PACKAGE / 'evidence'
    evidence.mkdir(exist_ok=False)
    copied = []
    for label, root in [('run', RUN), ('operator', OPERATOR), ('review', REVIEW)]:
        for path in sorted(root.rglob('*')):
            if not path.is_file() or path.suffix == '.bin':
                continue
            relative = Path(label) / path.relative_to(root)
            destination = evidence / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, destination)
            original, copy = fingerprint(path), fingerprint(destination)
            if original != copy:
                raise RuntimeError('Evidence copy mismatch: ' + str(path))
            copied.append({'source': str(path), 'copy': str(relative), **copy})
    write_json(evidence / 'COPY_MANIFEST.json', copied)
    result = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'postflight': post['Status'], 'raw_evidence_unchanged': before == after,
              'copied_files': len(copied), 'external_rng_files': sum(Path(name).suffix == '.bin' for name in after),
              'review_dir': str(REVIEW), 'evidence_dir': str(evidence),
              'audit_returns': [x['returncode'] for x in invocations]}
    write_json(PACKAGE / 'SEAL_RESULT.json', result)
    print(json.dumps(result))
    return 0 if okay and before == after else 2


if __name__ == '__main__':
    sys.exit(main())
