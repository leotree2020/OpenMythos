#!/usr/bin/env python3
"""C1 train-only handoff. No prepare, evaluation, source edit, retry or resume.
The reviewer approved the code, NOT the prepared.json bytes. This helper checks
existing local bytes against the owner's uploaded evidence; it is not an
independent reviewer or a new model/infrastructure acceptance stage.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

REPO = Path('/workspaces/OpenMythos')
OUT = REPO / 'mythos_evidence/mech_c_confirm_v1'
PYTHON = Path('/workspaces/mythos-m2-cpu312/bin/python')
UPSTREAM = Path('/workspaces/mythos-parcae-pinned')
PIN = '8a646eb56a9bcffb9767ad9f50843f85670b2fa1'
UPSTREAM_PIN = '69284c13746e849104f738d6d1a347b1f457df76'
PREPARED_SHA = '2f3e1251eaf474d3a49f2de826b6ba6c9711a16a15a9d74c09f8386b5db85829'
IDENTITY_SHA = '750d827c88244dfd4d26dc2be6d2fedf88868c399665c882110fbbde9c86a4e0'
C1T_SHA = '14003d130a3257e5c26d669fe79f6c7b6bed3bf8ce87c1f7c9096605fec595d0'
REVIEW_REF = '89152f19d66b829c4c1aefefb2ac256ad6e5d618'
REVIEW_PATH = 'research/mini_mythos/c_confirm/evidence/C1_CLAUDE_REVIEW_OWNER_TRANSCRIPT_20261031.md'
SEEDS = {'1101', '1202', '1303', '1404', '1505'}
COUNTS = {'GPT': (4843, 73433088), 'P4': (3116, 114130944), 'C4': (3000, 118554624)}


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(path, *args):
    return subprocess.run(['git', '-C', str(path), *args], check=True, stdout=subprocess.PIPE).stdout


def verify_prepared(raw):
    require(sha(raw) == PREPARED_SHA, 'prepared.json differs from uploaded evidence; retained')
    p = json.loads(raw)
    require((p['experiment'], p['phase'], p['status'], p['exit_code']) ==
            ('MYTHOS-C1-EQUAL-COUNT-HOLDOUT-V1', 'prepare', 'PASS', 0), 'invalid prepare state')
    require(p['code_head'] == PIN and p['source_pin'] == UPSTREAM_PIN, 'source pin mismatch')
    source = {k: p['source_identity'][k] for k in ('own', 'inherited')}
    aggregate = sha(json.dumps(source, sort_keys=True, separators=(',', ':'), allow_nan=False).encode())
    require(aggregate == p['source_identity']['sha256'] == IDENTITY_SHA, 'source identity mismatch')
    require(p['holdout']['allocation_sha256'] == C1T_SHA, 'C1T allocation mismatch')
    require(set(p['starts']) == set(p['counts']) == SEEDS, 'five-seed records incomplete')
    require(p['budget']['ceiling_flops'] == 355663872000, 'budget ceiling mismatch')
    for arm, (steps, cost) in COUNTS.items():
        b = p['budget']['arms'][arm]
        require((b['steps'], b['step_flops'], b['total_flops']) ==
                (steps, cost, steps * cost), 'budget mismatch: ' + arm)
    require(p['training_status'] == 'NOT TESTED' and p['C1T_status'] == 'NOT OPENED', 'prepare scope changed')
    return p


def find_worktree(repo):
    matches, record = [], {}
    for part in git(repo, 'worktree', 'list', '--porcelain', '-z').split(b'\0'):
        if not part:
            if record.get('HEAD') == PIN and 'worktree' in record:
                path = Path(record['worktree'])
                if path.is_dir(): matches.append(path)
            record = {}
        else:
            key, _, value = os.fsdecode(part).partition(' ')
            record[key] = value
    require(matches, 'no existing worktree at reviewed pin; no directory created or reset')
    worktree = sorted(matches, key=str)[0]
    require(git(worktree, 'rev-parse', 'HEAD').decode().strip() == PIN, 'worktree HEAD changed')
    require(Path(git(worktree, 'rev-parse', '--show-toplevel').decode().strip()).resolve() ==
            worktree.resolve(), 'wrong worktree root')
    return worktree


def verify_source(worktree, p):
    root = worktree / 'research/mini_mythos'
    here = root / 'c_confirm'
    own = {f.name: sha(f.read_bytes()) for f in here.iterdir()
           if f.suffix in ('.py', '.sh') or f.name == 'PROTOCOL.md'}
    inherited = {name: sha((root / name).read_bytes()) for name in p['source_identity']['inherited']}
    require(own == p['source_identity']['own'] and inherited == p['source_identity']['inherited'],
            'local reviewed source bytes changed; no edits made')
    require(not git(worktree, 'status', '--porcelain', '--untracked-files=no').strip(),
            'tracked worktree changes retained; no reset')


def require_fresh(out):
    for name in ('training.json', 'train.started', 'jobs', 'pretraining_review.md',
                 'train.error.log', 'result.json', 'C1T.json', 'evaluate.started'):
        require(not os.path.lexists(out / name), 'existing/partial evidence retained: ' + name)
    require(not os.path.lexists(str(out) + '.train.console.log'), 'prior training log retained; no retry')


def launch(worktree, out, review):
    require(review.strip(), 'registered actual review is empty')
    env = os.environ.copy()
    env.update(C1_OUTPUT_DIR=str(out), C1_PYTHON=str(PYTHON), C1_PARCAE_DIR=str(UPSTREAM),
               CUDA_VISIBLE_DEVICES='', PYTHONDONTWRITEBYTECODE='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1')
    # This is only a temporary review copy; the reviewed parent archives it in the output.
    with tempfile.TemporaryDirectory(prefix='mythos-c1-actual-review-') as tmp:
        report = Path(tmp) / 'C1_CLAUDE_REVIEW_OWNER_TRANSCRIPT.md'
        report.write_bytes(review)
        print('Registered owner-supplied review SHA256:', sha(review), flush=True)
        return subprocess.run([
            'bash', str(worktree / 'research/mini_mythos/c_confirm/run_codespaces_cpu.sh'), 'train',
            '--review-report', str(report),
            '--reviewer', 'Claude Code (owner-supplied C1 report+addendum; prepared file NOT VERIFIED by Claude)',
            '--review-approved'], cwd=worktree, env=env, check=False).returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--start-training', action='store_true', required=True,
                        help='owner acknowledges the supplied scope-limited code approval')
    parser.parse_args()
    try:
        require_fresh(OUT)
        require(PYTHON.is_file() and os.access(PYTHON, os.X_OK) and UPSTREAM.is_dir(),
                'original CPU environment/upstream missing; no installation')
        p = verify_prepared((OUT / 'prepared.json').read_bytes())
        worktree = find_worktree(REPO)
        verify_source(worktree, p)
        require(sha((OUT / 'train.json').read_bytes()) == p['train_file_sha256'], 'training data file changed')
        review = git(REPO, 'show', REVIEW_REF + ':' + REVIEW_PATH)
        print('Existing reviewed worktree:', worktree, flush=True)
        print('Existing prepared bytes and reviewer-recomputed values: MATCH', flush=True)
        print('TRAIN ONLY: 15 trajectories; no C1T/HC/H2 scoring; no automatic retry.', flush=True)
        return launch(worktree, OUT, review)
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.CalledProcessError) as exc:
        print('BLOCKED:', exc, flush=True)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
