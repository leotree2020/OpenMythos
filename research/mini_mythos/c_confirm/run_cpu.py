#!/usr/bin/env python3
"""C1 prepare/train/evaluate. No holdout scoring until all fifteen runs complete."""
from __future__ import annotations
import argparse
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import traceback

os.environ['CUDA_VISIBLE_DEVICES'] = ''
sys.dont_write_bytecode = True
import c1_policy as P
import c1_runtime as R
from c1_policy import require

HERE = Path(__file__).resolve().parent
PHASE_FILE = {'prepare': 'prepared.json', 'train': 'training.json', 'evaluate': 'result.json'}


def read(path):
    return P.parse_bytes(path.read_bytes())


def complete(path, phase):
    report = read(path)
    require(report.get('experiment') == P.EXPERIMENT and report.get('phase') == phase
            and report.get('status') == 'PASS' and report.get('exit_code') == 0, 'prerequisite incomplete/unrelated')
    return report


def source_match(prepared):
    require(R.identity() == prepared['source_identity'], 'code/protocol changed since prepare')


def prepare(args, report):
    torch, env, root, m2, task, ident = R.context(args.parcae_dir)
    report.update(environment=env, code_head=R.ab.git(root, 'rev-parse', 'HEAD'), source_pin=R.ab.PIN,
                  source_identity=ident, review_status='PENDING Claude Code',
                  scope='no optimizer updates; no C1T targets or model scoring')
    data, manifest = R.ab.check_data(task)
    R.ab.write(args.out/'train.json', data['train'])
    report.update(data=manifest, train_file_sha256=R.ab.file_sha(args.out/'train.json'))
    _, report['holdout'] = P.allocate(task)
    x, y = R.encoded(task, data['train'], torch)
    ix = [j for c in range(4) for j in [i for i, r in enumerate(data['train']) if r['carry'] == c][:8]]
    report.update(native_preflight=[], gpt_objective_checks=[], starts={}, counts={})
    for seed in P.SEEDS:
        base, _, _ = R.initial(m2, seed, 'P4')
        report['native_preflight'].append(R.native_c_check(base, seed, torch, m2))
        starts, counts = {}, {}
        for arm in P.ARMS:
            base, io, base_sha = R.initial(m2, seed, arm)
            model = R.wrap(base, arm, seed)
            starts[arm] = dict(base_sha256=base_sha, full_sha256=m2.weights_sha(model), shared_io=io)
            counts[arm] = R.probe(model, x[ix], y[ix], torch, m2)
            require(counts[arm]['parameters'] == P.EXPECTED_PARAMETERS[arm], 'registered capacity changed')
            if arm == 'GPT':
                report['gpt_objective_checks'].append(dict(seed=seed, **R.gpt_objective_check(base, x[ix], y[ix], torch)))
        require(starts['P4']['base_sha256'] == starts['C4']['base_sha256'], 'Parcae initial base mismatch')
        require(len({P.object_sha(v['shared_io']) for v in starts.values()}) == 1, 'shared IO differs')
        plan = P.budgets({a: counts[a]['step_flops'] for a in P.ARMS})
        if 'budget' in report:
            require(plan == report['budget'], 'seed-dependent budget')
        report['budget'] = plan
        report['starts'][str(seed)], report['counts'][str(seed)] = starts, counts
        print(json.dumps(dict(seed=seed, native_prepare='PASS', training='NOT TESTED')), flush=True)
    (args.out/'pip-freeze.txt').write_text(subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'], text=True))
    m2.upstream_check(args.parcae_dir); source_match(report)
    report.update(status='PASS', native_compatibility_status='PASS', training_status='NOT TESTED', C1T_status='NOT OPENED')


def verify_training(args, prepared, training):
    rows = training['rows']
    mapping = {(r['arm'], r['seed']): r for r in rows}
    require(len(mapping) == len(rows) == len(P.ARMS)*len(P.SEEDS)
            and set(mapping) == {(a, s) for a in P.ARMS for s in P.SEEDS}, 'fifteen complete unique trajectories required')
    for (arm, seed), row in mapping.items():
        plan = prepared['budget']['arms'][arm]
        require(row['status'] == 'PASS' and row['steps'] == row['planned_steps'] == plan['steps'], 'incomplete job')
        start = prepared['starts'][str(seed)][arm]
        require(row['source_identity'] == prepared['source_identity']['sha256'], 'worker source mismatch')
        require(row['initial_model_sha256'] == start['base_sha256'] and
                row['initial_full_state_sha256'] == start['full_sha256'] and row['shared_io'] == start['shared_io'], 'initial identity mismatch')
        require(row['counted_training_flops'] == plan['total_flops'], 'budget mismatch')
        for key in ('loss_trace', 'gradient_norm_trace', 'rng_before_forward_sha256'):
            require(len(row[key]) == row['steps'], 'incomplete training trace')
        require(all(type(x) in (int, float) and math.isfinite(x)
                    for key in ('loss_trace', 'gradient_norm_trace') for x in row[key]), 'nonfinite saved trajectory')
        require(set(row['snapshots']) == {str(s) for s in P.saved_steps(arm, row['steps'])}, 'snapshot endpoint list')
        for key, snapshot in row['snapshots'].items():
            path = (args.out/snapshot['file']).resolve()
            require(path.is_relative_to(args.out) and snapshot['step'] == int(key)
                    and R.ab.file_sha(path) == snapshot['sha256'], 'snapshot missing/changed')
        require(row['final_model_sha256'] == row['snapshots'][str(row['steps'])]['model_sha256'], 'final full state link')
        require(read(args.out/'jobs'/f'{arm}_{seed}'/'row.json') == row, 'summary/worker record differs')
    for seed in P.SEEDS:
        group = [mapping[a, seed] for a in P.ARMS]
        require(len({r['batch_prefix3000_sha256'] for r in group}) == 1, 'sample prefix mismatch')
        p, c = mapping['P4', seed], mapping['C4', seed]
        n = min(p['steps'], c['steps'])
        require(p['rng_before_forward_sha256'][:n] == c['rng_before_forward_sha256'][:n], 'Parcae RNG prefix mismatch')
    return mapping


def review_input(args):
    require(args.review_report is not None and args.reviewer and args.review_approved,
            'actual Claude Code report and owner acknowledgement required before train')
    raw = args.review_report.read_bytes()
    require(raw.strip(), 'empty report is not review')
    return raw


def train(args, report, prepared):
    raw = review_input(args)
    with (args.out/'pretraining_review.md').open('xb') as f:
        f.write(raw)
    report.update(rows=[], review=dict(reviewer_as_supplied=args.reviewer, report_sha256=P.digest(raw),
        source_identity_sha256=prepared['source_identity']['sha256'], owner_acknowledged_approval=True,
        status='OWNER-SUPPLIED; report author/verdict not cryptographically authenticated'),
        scope='training only; no C1T/HC/H2 model evaluation')
    R.ab.write(args.out/'training.json', report)
    for seed in P.SEEDS:
        for arm in P.ARMS:
            cmd = [sys.executable, '-B', str(HERE/'run_cpu.py'), 'train', '--worker', arm,
                   '--seed', str(seed), '--out', str(args.out), '--parcae-dir', str(args.parcae_dir)]
            rc = subprocess.run(cmd, check=False).returncode
            path = args.out/'jobs'/f'{arm}_{seed}'/'row.json'
            if rc:
                if path.exists(): report['partial_row'] = read(path)
                if rc == 1: raise R.NumericalFailure(f'numerical failure {arm}/{seed}; remaining runs NOT TESTED')
                raise RuntimeError(f'worker blocked {arm}/{seed}; no retry')
            report['rows'].append(read(path))
            R.ab.write(args.out/'training.json', report)
    verify_training(args, prepared, report)
    report.update(status='PASS', pairing_status='PASS', C1T_status='NOT OPENED', quality_status='NOT TESTED')


def load_worker_truth(args, prepared, training):
    parent = read(args.out/'result.json')
    require(parent.get('experiment') == P.EXPERIMENT and parent.get('phase') == 'evaluate'
            and parent.get('status') == 'PARTIAL', 'no active C1T evaluation parent')
    require(parent['source_identity'] == prepared['source_identity'], 'parent source mismatch')
    require(parent['training_summary_sha256'] == R.ab.file_sha(args.out/'training.json'), 'training changed before scoring')
    # Critical: parse exactly the bytes checked, without reopening the file.
    truth = P.bound_json(args.out/'C1T.json', parent['C1T_file_sha256'])
    require(P.object_sha(truth) == parent['C1T_sha256'], 'test object mismatch')
    return truth


def evaluate(args, report, prepared, training):
    verify_training(args, prepared, training)
    torch, env, root, m2, task, ident = R.context(args.parcae_dir)
    allocation, manifest = P.allocate(task)
    require(manifest == prepared['holdout'], 'test allocation changed')
    truth = P.test_examples(task, allocation)
    require(not (args.out/'C1T.json').exists(), 'existing holdout bytes retained')
    R.ab.write(args.out/'C1T.json', truth)
    report.update(C1T_sha256=P.object_sha(truth), C1T_file_sha256=R.ab.file_sha(args.out/'C1T.json'),
        C1T_pairs=len(truth), holdout=manifest, source_identity=ident, environment=env,
        code_head=R.ab.git(root, 'rev-parse', 'HEAD'),
        training_summary_sha256=R.ab.file_sha(args.out/'training.json'), training_rows=training['rows'],
        training_review=training['review'], counts=prepared['counts'], budget=prepared['budget'],
        native_preflight=prepared['native_preflight'], gpt_objective_checks=prepared['gpt_objective_checks'], rows=[])
    R.ab.write(args.out/'result.json', report)
    for seed in P.SEEDS:
        for arm in P.ARMS:
            cmd = [sys.executable, '-B', str(HERE/'run_cpu.py'), 'evaluate', '--worker', arm,
                   '--seed', str(seed), '--out', str(args.out), '--parcae-dir', str(args.parcae_dir)]
            rc = subprocess.run(cmd, check=False).returncode
            if rc == 1: raise R.NumericalFailure(f'numerical evaluation failure {arm}/{seed}')
            require(rc == 0, f'evaluation blocked {arm}/{seed}; no retry')
            report['rows'].extend(read(args.out/'jobs'/f'{arm}_{seed}'/'C1T.json'))
            R.ab.write(args.out/'result.json', report)
    require(P.bound_json(args.out/'C1T.json', report['C1T_file_sha256']) == truth, 'test changed during evaluation')
    require(R.ab.file_sha(args.out/'training.json') == report['training_summary_sha256'], 'training file changed')
    verify_training(args, prepared, training)
    source_match(prepared); m2.upstream_check(args.parcae_dir)
    outcome = P.summarize(report['rows'], truth, task)
    report.update(status='PASS', execution_status='PASS', outcome=outcome, exit_code=outcome['exit_code'],
        post_result_review_status='NOT TESTED; Claude Code report required', legacy_HC_H2_status='NOT OPENED',
        scope='15 trajectories/20 conditions on SAME2048 C1T questions; no model selection or later experiments')


def worker(args):
    args.arm = args.worker
    job = args.out/'jobs'/f'{args.arm}_{args.seed}'
    owned = False
    error_path = None
    try:
        prepared = complete(args.out/'prepared.json', 'prepare')
        source_match(prepared)
        require(args.seed is not None, 'worker seed missing')
        if args.phase == 'train':
            parent = read(args.out/'training.json')
            require(parent.get('experiment') == P.EXPERIMENT and parent.get('phase') == 'train'
                    and parent.get('status') == 'PARTIAL' and parent.get('review'), 'no reviewed parent training phase')
            job.mkdir(parents=True, exist_ok=False)
            owned = True
            error_path = job/'train.error.log'
            R.train_one(args, prepared)
        else:
            require(args.phase == 'evaluate', 'invalid worker phase')
            training = complete(args.out/'training.json', 'train')
            require(job.is_dir(), 'missing completed training job')
            truth = load_worker_truth(args, prepared, training)
            require(not (job/'C1T.json').exists(), 'existing worker predictions retained')
            # Exclusive claim before inference; duplicate errors cannot change old rows/logs.
            with (job/'evaluate.started').open('x') as f: f.write('no automatic retry\n')
            owned = True
            error_path = job/'evaluate.error.log'
            row = next(r for r in training['rows'] if r['arm'] == args.arm and r['seed'] == args.seed)
            result = R.evaluate_one(args, prepared, row, truth)
            R.ab.write(job/'C1T.json', result)
        return 0
    except Exception as exc:
        if owned:
            if error_path and not error_path.exists(): error_path.write_text(traceback.format_exc())
            row_path = job/'row.json'
            if args.phase == 'train' and row_path.exists():
                row = read(row_path)
                row.update(status='FAIL' if isinstance(exc, R.NumericalFailure) else 'BLOCKED', error=str(exc))
                R.ab.write(row_path, row)
        traceback.print_exc()
        return 1 if isinstance(exc, R.NumericalFailure) else 2


def show(report):
    for key in ('experiment', 'phase', 'status', 'execution_status', 'budget', 'outcome', 'error', 'exit_code'):
        if key in report: print(key, json.dumps(report[key], ensure_ascii=False), flush=True)
    if report.get('outcome'):
        o = report['outcome']
        for key in ('primary_equal_budget_C4_P4', 'same_updates_C4_P4', 'external_GPT_safeguard'):
            print(key, o[key]['status'], flush=True)
        print('candidate_selection_status', o['candidate_selection_status'], flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=PHASE_FILE)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--parcae-dir', type=Path, required=True)
    parser.add_argument('--review-report', type=Path)
    parser.add_argument('--reviewer')
    parser.add_argument('--review-approved', action='store_true')
    parser.add_argument('--worker', choices=P.ARMS, help=argparse.SUPPRESS)
    parser.add_argument('--seed', type=int, choices=P.SEEDS, help=argparse.SUPPRESS)
    args = parser.parse_args()
    args.out = args.out.resolve(); args.parcae_dir = args.parcae_dir.resolve()
    if args.worker: return worker(args)
    target = args.out/PHASE_FILE[args.phase]
    if target.exists():
        try:
            old = read(target)
            require(old.get('experiment') == P.EXPERIMENT and old.get('phase') == args.phase, 'unrelated existing result')
            rc = old.get('exit_code', 2)
            require(type(rc) is int and rc in (0, 1, 2), 'invalid saved exit')
            show(old); print('READ ONLY: existing result retained; no resume or rerun.')
            return rc
        except Exception as exc:
            print('BLOCKED: existing bytes retained:', exc); return 2
    try:
        if args.phase == 'prepare':
            require(not args.out.exists(), 'partial preparation retained')
            args.out.mkdir(parents=True, exist_ok=False)
            prepared = training = None
        else:
            prepared = complete(args.out/'prepared.json', 'prepare')
            source_match(prepared); R.context(args.parcae_dir)
            if args.phase == 'train':
                review_input(args)
                require(not (args.out/'jobs').exists() and not (args.out/'pretraining_review.md').exists(),
                        'existing training evidence retained')
            training = complete(args.out/'training.json', 'train') if args.phase == 'evaluate' else None
            if training:
                verify_training(args, prepared, training)
                require(not (args.out/'C1T.json').exists(), 'partial evaluation evidence retained')
        with (args.out/(args.phase+'.started')).open('x') as f:
            f.write('phase reserved; no automatic retry/resume\n')
    except Exception as exc:
        print('BLOCKED:', exc); return 2
    report = dict(experiment=P.EXPERIMENT, phase=args.phase, status='PARTIAL', exit_code=2)
    R.ab.write(target, report)
    try:
        if args.phase == 'prepare': prepare(args, report)
        elif args.phase == 'train': train(args, report, prepared)
        else: evaluate(args, report, prepared, training)
        if args.phase != 'evaluate': report['exit_code'] = 0
    except Exception as exc:
        rc = 1 if isinstance(exc, R.NumericalFailure) else 2
        report.update(status='FAIL' if rc == 1 else 'BLOCKED', error=f'{type(exc).__name__}: {exc}', exit_code=rc)
        (args.out/(args.phase+'.error.log')).write_text(traceback.format_exc())
        traceback.print_exc()
    R.ab.write(target, report); show(report)
    print(R.ab.file_sha(target), target)
    return report['exit_code']


if __name__ == '__main__':
    raise SystemExit(main())
