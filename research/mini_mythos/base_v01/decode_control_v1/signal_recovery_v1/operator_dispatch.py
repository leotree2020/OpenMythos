"""One-shot dispatch of unchanged numerical code with external signal observation."""
import datetime
import hashlib
import json
import pathlib
import subprocess

repo = pathlib.Path('/workspaces/mythos-base-v01-rope-diag-v11')
rel = pathlib.Path('research/mini_mythos/base_v01/decode_control_v1/signal_recovery_v1')
record = json.loads((repo / rel / 'RUN_RECORD.json').read_text())


def git(*args):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as inp:
        for block in iter(lambda: inp.read(1024 * 1024), b''):
            h.update(block)
    return {'size': path.stat().st_size, 'sha256': h.hexdigest()}


def save(path, value):
    with path.open('x') as out:
        json.dump(value, out, indent=2)
        out.write('\n')


assert git('branch', '--show-current') == 'mythos-base-v01-decode-control-v1'
assert not git('status', '--porcelain=v1', '--untracked-files=all', '--ignored')
assert git('merge-base', '--is-ancestor', record['observer_commit_O'], 'HEAD') == ''
assert not (pathlib.Path('/workspaces/mythos-evidence/base_v01/decode_control') / record['run_id']).exists()
assert digest(pathlib.Path('/usr/bin/strace')) == record['strace_binary']
assert digest(repo / rel / 'resource_observer.py') == record['resource_observer']
launcher_source = repo / 'research/mini_mythos/base_v01/decode_control_v1/launch_recovery_v1/mythos_launch.py'
assert digest(launcher_source)['sha256'] == record['launcher_sha256']
root = pathlib.Path(record['operator_dir'])
root.mkdir(parents=True, exist_ok=False)
(root / 'mythos_launch.py').write_bytes(launcher_source.read_bytes())
(root / 'resource_observer.py').write_bytes((repo / rel / 'resource_observer.py').read_bytes())
save(root / 'config.json', {k: record[k] for k in ('command', 'cwd', 'timeout_seconds')})
trees = {}
for directory in record['preserve_directories']:
    tree = pathlib.Path(directory)
    assert tree.is_dir()
    trees[directory] = {str(p.relative_to(tree)): digest(p) for p in sorted(tree.rglob('*')) if p.is_file()}
save(root / 'prior_attempts_before.json', trees)
cmd = [record['python'], '-I', '-B', str(root / 'mythos_launch.py'), '--config', str(root / 'config.json')]
with (root / 'launcher.stdout').open('xb') as out, (root / 'launcher.stderr').open('xb') as err:
    child = subprocess.Popen(cmd, cwd=repo, stdout=out, stderr=err, start_new_session=True)
launch = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'pid': child.pid,
          'pid_starttime': pathlib.Path(f'/proc/{child.pid}/stat').read_text().rsplit(')', 1)[1].split()[19],
          'run_id': record['run_id'], 'operator_dir': str(root), 'launcher_command': cmd,
          'execution_head': git('rev-parse', 'HEAD'), 'diagnostic_A': record['diagnostic_implementation_A'],
          'launcher_L': record['launcher_commit_L'], 'observer_O': record['observer_commit_O']}
save(root / 'launch_observation.json', launch)
with (root / 'observer.stdout').open('xb') as out, (root / 'observer.stderr').open('xb') as err:
    observer = subprocess.Popen([record['python'], '-I', '-B', str(root / 'resource_observer.py'),
        '--operator-dir', str(root), '--launcher-pid', str(child.pid)], cwd=repo,
        stdout=out, stderr=err, start_new_session=True)
save(root / 'observer_launch.json', {'pid': observer.pid, 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat()})
print(json.dumps({**launch, 'observer_pid': observer.pid}))
