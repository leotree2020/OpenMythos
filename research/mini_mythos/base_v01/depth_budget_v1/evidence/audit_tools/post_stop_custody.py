"""Read-only external custody after worker/launcher completion. No model imports."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess


def info(path):
    h = hashlib.sha256()
    size = 0
    with path.open('rb') as stream:
        for raw in iter(lambda: stream.read(1048576), b''):
            size += len(raw)
            h.update(raw)
    return {'bytes': size, 'sha256': h.hexdigest()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    root = args.root.resolve()
    spec = json.loads((root / 'operator/spec.json').read_text())
    package = Path(spec['source_manifest_path']).parent
    manifest = json.loads(Path(spec['source_manifest_path']).read_text())
    observed = {}
    errors = []
    for name, expected in manifest.items():
        path = Path(name)
        try:
            actual = info(path)
            observed[name] = actual
            if actual != expected:
                errors.append({'reason': 'Protected file differs', 'path': name, 'expected': expected, 'actual': actual})
        except OSError as exc:
            errors.append({'reason': 'Protected file unreadable', 'path': name, 'error': repr(exc)})
    inventories = {}
    expected_inventories = json.loads((package / 'ENVIRONMENT_RECOVERY.json').read_text())['original_inventories_before']
    code = 'import importlib.metadata as m,json;print(json.dumps(sorted([(x.metadata["Name"],x.version,str(x.locate_file(""))) for x in m.distributions()])))'
    for executable, expected in expected_inventories.items():
        result = subprocess.run([executable, '-I', '-B', '-c', code], capture_output=True, text=True, timeout=60)
        inventories[executable] = {'returncode': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}
        if result.returncode or result.stdout != expected:
            errors.append({'reason': 'Original package inventory changed', 'executable': executable})
    git = {}
    for path, expected in [(Path(spec['repo']), spec['expected_head']),
                           (Path(spec['upstream']), '69284c13746e849104f738d6d1a347b1f457df76'),
                           (Path('/workspaces/mythos-base-v01-b1'), 'd88be474ebb2529c5b095e3732b1f25509f9b824')]:
        head = subprocess.check_output(['git', '-C', str(path), 'rev-parse', 'HEAD'], text=True).strip()
        status = subprocess.check_output(['git', '-C', str(path), 'status', '--porcelain=v1'], text=True)
        git[str(path)] = {'head': head, 'status': status}
        if head != expected or status:
            errors.append({'reason': 'Protected Git state differs', 'path': str(path)})
    active = []
    for process in Path('/proc').iterdir():
        if not process.name.isdigit() or int(process.name) == os.getpid():
            continue
        try:
            argv = (process / 'cmdline').read_bytes().split(b'\0')
            strings = [x.decode(errors='replace') for x in argv if x]
            if any(Path(x).name in ('mythos_launch.py', 'run_depth_budget.py') for x in strings) and any(str(root) in x for x in strings):
                active.append({'pid': int(process.name), 'argv': strings})
        except (OSError, ProcessLookupError):
            continue
    if active:
        errors.append({'reason': 'Experiment process still active', 'processes': active})
    completion = {}
    for component in ('operator', 'worker'):
        path = root / component / 'completion.json'
        completion[component] = json.loads(path.read_text()) if path.exists() else None
    if any(value is None for value in completion.values()):
        errors.append({'reason': 'Terminal completion missing'})
    files = {str(path.relative_to(root)): info(path) for path in sorted(root.rglob('*')) if path.is_file() and path != args.output}
    report = {'Purpose': 'Post-stop custody regardless of scientific outcome',
              'Environment': 'Standard-library file/Git/metadata inspection; no model import',
              'Input': spec['run_id'], 'Expected': 'Stopped processes, preserved original files/checkouts/environments, retained raw evidence',
              'Actual': {'protected_files': len(observed), 'raw_files': len(files), 'active': active, 'errors': errors},
              'Status': 'PASS' if not errors else 'BLOCKED', 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'protected_observed': observed, 'inventories': inventories, 'git': git,
              'files': files, 'completion': completion,
              'limitation': 'Does not reload or validate in-memory post-state after a failed worker; package identity is metadata, not a full environment binary hash.'}
    with args.output.open('x') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'Status': report['Status'], 'actual': report['Actual']}))
    return 0 if not errors else 2


if __name__ == '__main__':
    raise SystemExit(main())
