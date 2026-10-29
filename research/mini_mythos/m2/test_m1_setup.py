"""Exercise actual M1 shell setup block with a local Git fixture, no training."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

script = Path(__file__).resolve().parents[1]/'m1/run_m1_codespaces_cpu.sh'
bash = 'C:/Program Files/Git/bin/bash.exe' if os.name == 'nt' else 'bash'
def run(*args, **kw):
    return subprocess.run(args, check=True, capture_output=True, text=True, **kw)
def git(path, *args):
    return run('git', '-C', str(path), *args).stdout.strip()

run(bash, '-n', str(script))
block = script.read_text().split('if [[ ! -d "$PARCAE_DIR/.git" ]]; then',1)[1]
block = 'if [[ ! -d "$PARCAE_DIR/.git" ]]; then'+block.split('M1="',1)[0]
rows = []
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    src = root/'source'
    src.mkdir()
    git(src, 'init')
    git(src, 'config', 'user.name', 'fixture')
    git(src, 'config', 'user.email', 'fixture@example.invalid')
    (src/'tracked.txt').write_text('original\n')
    git(src, 'add', '.')
    git(src, 'commit', '-m', 'fixture')
    pin = git(src, 'rev-parse', 'HEAD')
    block = block.replace('https://github.com/sandyresearch/parcae.git', src.as_posix())
    target = root/'target'
    env = dict(os.environ, PARCAE_DIR=target.as_posix(), PIN=pin)
    for case in ('fresh', 'existing_clean', 'existing_dirty'):
        if case == 'existing_dirty':
            (target/'tracked.txt').write_text('user modification\n')
        r = subprocess.run([bash, '-c', 'set -euo pipefail\n'+block], env=env,
                           capture_output=True, text=True)
        if case == 'existing_dirty':
            assert r.returncode == 2
            assert (target/'tracked.txt').read_text() == 'user modification\n'
        else:
            assert r.returncode == 0, r.stderr
            assert git(target, 'rev-parse', 'HEAD') == pin
            assert not git(target, 'status', '--porcelain')
        rows.append(dict(case=case, exit_code=r.returncode, status='PASS'))
print(json.dumps(dict(bash_syntax='PASS', cases=rows), indent=2))
