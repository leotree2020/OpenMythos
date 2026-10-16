#!/usr/bin/env python3
"""Record source provenance without GitHub API access or remote mutations."""
import argparse
import hashlib
from pathlib import Path
import re
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import atomic_json

EXPECTED_FORK = 'leotree2020/OpenMythos'
EXPECTED_UPSTREAM = 'kyegomez/OpenMythos'


def github_repository(remote):
    """Extract owner/repo for common GitHub HTTPS and SSH remotes; no secret output."""
    if not remote:
        return None
    m = re.fullmatch(r'(?:https://github\.com/|git@github\.com:|ssh://git@github\.com/)([\w.-]+)/([\w.-]+?)(?:\.git)?/?', remote.strip(), re.I)
    return f'{m.group(1)}/{m.group(2)}' if m else None


def git(repo, *args):
    p = subprocess.run(['git', '-C', str(repo), *args], capture_output=True, text=True)
    if p.returncode:
        return None
    return p.stdout.strip()


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def build_manifest(repo):
    repo = Path(repo).resolve()
    origin = github_repository(git(repo, 'remote', 'get-url', 'origin'))
    upstream = github_repository(git(repo, 'remote', 'get-url', 'upstream'))
    files = ['open_mythos/main.py', 'open_mythos/tokenizer.py', 'training/3b_fine_web_edu.py', 'LICENSE']
    digest = {f: sha256(repo / f) if (repo / f).is_file() else None for f in files}
    return {
        'repo': EXPECTED_FORK,
        'expected_upstream': EXPECTED_UPSTREAM,
        'origin_matches_fork': origin is not None and origin.lower() == EXPECTED_FORK.lower(),
        'origin_repository': origin,
        'upstream_repository': upstream,
        'git_commit': git(repo, 'rev-parse', 'HEAD'),
        'current_branch': git(repo, 'branch', '--show-current'),
        'working_tree_has_changes': bool(git(repo, 'status', '--porcelain')),
        'file_sha256': digest,
        'notes': 'Local git metadata only. Does not establish GitHub server Fork parentage or confirm remote changes.',
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', default='.')
    parser.add_argument('--out', default='research/mini_mythos/results/provenance.json')
    parser.add_argument('--strict', action='store_true', help='Exit nonzero if origin is not the expected fork or core upstream source is absent')
    args = parser.parse_args()
    manifest = build_manifest(args.repo)
    atomic_json(args.out, manifest)
    print('origin:', manifest['origin_repository'] or '(unknown)')
    print('branch:', manifest['current_branch'] or '(detached)')
    print('commit:', manifest['git_commit'] or '(unknown)')
    print('wrote:', args.out)
    if args.strict and (not manifest['origin_matches_fork'] or manifest['file_sha256']['open_mythos/main.py'] is None):
        raise SystemExit('Fork identity or model source could not be validated. No changes were pushed.')


if __name__ == '__main__':
    main()
