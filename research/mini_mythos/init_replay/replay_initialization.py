#!/usr/bin/env python3
"""INIT-01: replay the original six initial states; no optimizer or training.

Original synthetic preflight/count helpers are replayed at their original boundary.
Exactly one count forward/backward per model; this is NOT gradient-coverage testing.
"""
from __future__ import annotations
import argparse
import dataclasses
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import traceback

os.environ['CUDA_VISIBLE_DEVICES'] = ''
os.environ['TORCHDYNAMO_DISABLE'] = '1'
sys.dont_write_bytecode = True
PIN = '69284c13746e849104f738d6d1a347b1f457df76'
REF_SHA = '74f00c64448ddbc224a48ef83dc031a90c33448ccb92647666707f6b8f988967'
CONFIG_SHA = 'a49b38521a45e716b1cb5f2c2b55d317d06ca7542d02623349c5331e9fe26447'
GOLD_SHA = '4960841f1f685326cf8a4c7d1198718346ef38b8ce0a3d0fb8d48d70daa0637d'
LONG_SHA = 'c5be0f6da8eab77ab499ad97a3aaf318633d2d44f234083165ffcacc3b26d7bb'
SEEDS = (42, 20261029, 20261030)
ARMS = ('gpt', 'parcae')
PHASES = ('constructed', 'paired_io', 'after_preflight', 'after_count')


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(path, *args):
    return subprocess.check_output(['git', '-C', str(path), *args], text=True).strip()


def pinned_json(path, expected):
    data = path.read_bytes()
    require(sha(data) == expected, 'pinned input changed: ' + str(path))
    return json.loads(data)


def write(path, obj):
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(obj, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    os.replace(temporary, path)


def index_rows(rows):
    keys = [(r['seed'], r['arm']) for r in rows]
    require(len(keys) == 6 and set(keys) == {(s, a) for s in SEEDS for a in ARMS},
            'expected six unique historical seed/arm rows')
    return dict(zip(keys, rows))


def state_sha(state):
    """Same semantic hash as the pinned producer, including persistent buffers."""
    h = hashlib.sha256()
    for name, tensor in sorted(state.items()):
        h.update(name.encode())
        h.update(tensor.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


def capture(torch, model):
    state = model.state_dict()
    require(all(bool(torch.isfinite(t).all()) for t in state.values()), 'nonfinite initialized state')
    return {
        'state_sha256': state_sha(state),
        'rng_sha256': sha(torch.get_rng_state().numpy().tobytes()),
        'parameters': sum(p.numel() for p in model.parameters()),
        'tensors': {name: {'shape': list(t.shape), 'dtype': str(t.dtype),
                           'sha256': sha(t.detach().cpu().contiguous().numpy().tobytes())}
                    for name, t in sorted(state.items())},
    }


def changed_names(before, after):
    a, b = before['tensors'], after['tensors']
    return [name for name in sorted(set(a) | set(b)) if a.get(name) != b.get(name)]


def classify(rows):
    index_rows(rows)
    require(all(tuple(r['phases']) == PHASES for r in rows), 'incomplete phase evidence')
    return 'PASS' if all(r['matches_historical_initial'] and r['shared_io_matches']
                         and r['saved_state_roundtrip'] for r in rows) else 'FAIL'


def execute(args, out, report):
    import torch
    import numpy
    import einops
    env = dict(python=platform.python_version(), torch=torch.__version__,
               numpy=numpy.__version__, einops=einops.__version__, platform=platform.platform(),
               pythonhashseed=os.environ.get('PYTHONHASHSEED', '<unset>'))
    report['environment'] = env
    require(platform.system() == 'Linux' and env['python'] == '3.12.3', 'requires producer Linux Python3.12.3')
    require((env['torch'], env['numpy'], env['einops']) == ('2.11.0+cpu', '1.26.4', '0.8.0'),
            'requires exact original CPU dependency builds; do not bypass or install automatically')
    require(torch.get_default_dtype() == torch.float32 and str(torch.get_default_device()) == 'cpu',
            'unexpected default dtype/device')
    root = Path(git(Path(__file__).parent, 'rev-parse', '--show-toplevel'))
    require(not git(root, 'status', '--porcelain', '--untracked-files=no'), 'dirty tracked research sources')
    require(git(args.parcae_dir, 'rev-parse', 'HEAD') == PIN, 'wrong upstream commit')
    require(not git(args.parcae_dir, 'status', '--porcelain', '--untracked-files=no'), 'dirty tracked upstream sources')
    ref_path = root / 'research/mini_mythos/m2_matched/experiment.py'
    require(sha(ref_path.read_bytes()) == REF_SHA, 'original helper bytes changed')
    config = pinned_json(ref_path.with_name('frozen_config.json'), CONFIG_SHA)
    gold = pinned_json(ref_path.parent / 'evidence/linux_e533fbe/pilot.json', GOLD_SHA)
    long_record = pinned_json(args.evidence / 'pilot.json', LONG_SHA)
    gold_rows, long_rows = index_rows(gold['rows']), index_rows(long_record['rows'])
    require(config['status'] == 'PASS' and config['source_pin'] == PIN and config['selected']['ffn'] == 60,
            'unexpected original configuration')
    for key, old in gold_rows.items():
        later = long_rows[key]
        require(old['initial_weights_sha256'] == later['init_sha'], 'historical initial hashes disagree')
        require(old['initialization'] == later['shared_io_initialization'], 'historical IO records disagree')
    report.update(code_head=git(root, 'rev-parse', 'HEAD'), upstream_pin=PIN,
                  script_sha256=sha(Path(__file__).read_bytes()),
                  protocol_sha256=sha(Path(__file__).with_name('PROTOCOL.md').read_bytes()),
                  reference_sha256=REF_SHA, config_sha256=CONFIG_SHA,
                  historical_pilot_sha256=GOLD_SHA, long_pilot_sha256=LONG_SHA,
                  historical_agreement_status='PASS', rows=[], synthetic_backward_probes=0,
                  optimizer_updates=0, training_steps=0, corpus_evaluations=0)
    spec = importlib.util.spec_from_file_location('init01_original_helpers', ref_path)
    require(spec and spec.loader, 'cannot import original helpers')
    m2 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m2)
    m2.setup(args.parcae_dir)
    report['environment']['cpu_threads'] = torch.get_num_threads()
    report['environment']['deterministic_algorithms'] = torch.are_deterministic_algorithms_enabled()
    (out / 'pip-freeze.txt').write_text(subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'], text=True))
    write(out / 'result.json', report)
    for seed in SEEDS:
        # Do not alter constructor order, default parameters or original IO alignment.
        models = {'gpt': m2.make('gpt', 60, seed), 'parcae': m2.make('parcae', 64, seed)}
        records = {}
        for arm in ARMS:
            records[arm] = dict(seed=seed, arm=arm, phases={'constructed': capture(torch, models[arm])})
        io = m2.pair_io(models['gpt'], models['parcae'])
        for arm in ARMS:
            records[arm]['phases']['paired_io'] = capture(torch, models[arm])
        for arm, model in models.items():
            old, row = gold_rows[seed, arm], records[arm]
            # Original run records dataclasses.asdict before preflight. Keep this ordering.
            actual_config = json.loads(json.dumps(dataclasses.asdict(model.config), allow_nan=False))
            require(actual_config == old['model_config'], 'constructed config differs from historical config')
            row['model_config'] = actual_config
            row['shared_io_matches'] = io == old['initialization']
            row['shared_io_actual'] = io
            row['shared_io_expected'] = old['initialization']
            row['preflight'] = m2.preflight(model, arm)
            require(row['preflight'] == old['preflight'], 'original synthetic preflight diverged')
            row['phases']['after_preflight'] = capture(torch, model)
            row['counts'] = m2.count(model, arm)
            report['synthetic_backward_probes'] += 1
            require(row['counts'] == old['counts'], 'original counted operator/parameter values diverged')
            row['phases']['after_count'] = capture(torch, model)
            row['expected_initial_sha256'] = old['initial_weights_sha256']
            row['actual_initial_sha256'] = m2.weights_sha(model)
            require(row['actual_initial_sha256'] == row['phases']['after_count']['state_sha256'], 'hash implementations disagree')
            row['matches_historical_initial'] = row['actual_initial_sha256'] == row['expected_initial_sha256']
            row['matching_phases'] = [phase for phase in PHASES if row['phases'][phase]['state_sha256'] == row['expected_initial_sha256']]
            row['phase_changed_tensors'] = {
                f'{a}_to_{b}': changed_names(row['phases'][a], row['phases'][b])
                for a, b in zip(PHASES, PHASES[1:])}
            checkpoint = out / f'reconstructed_{arm}_{seed}_initial.pt'
            cpu_state = {name: t.detach().cpu().clone() for name, t in model.state_dict().items()}
            rng = torch.get_rng_state().clone()
            torch.save(dict(model=cpu_state, rng=rng, seed=seed, arm=arm,
                            code_head=report['code_head'], source_pin=PIN,
                            matches_historical_initial=row['matches_historical_initial']), checkpoint)
            saved = torch.load(checkpoint, map_location='cpu', weights_only=True)
            row['saved_state_roundtrip'] = (state_sha(saved['model']) == row['actual_initial_sha256']
                                           and torch.equal(saved['rng'], rng))
            require(row['saved_state_roundtrip'], 'initial snapshot readback differs')
            require(all(p.grad is None for p in model.parameters()), 'count helper did not clear probe gradients')
            row['checkpoint_file'] = checkpoint.name
            row['checkpoint_sha256'] = sha(checkpoint.read_bytes())
            row['initial_replay_status'] = 'PASS' if row['matches_historical_initial'] and row['shared_io_matches'] else 'FAIL'
            report['rows'].append(row)
            write(out / 'result.json', report)
            print(json.dumps(dict(seed=seed, arm=arm, initial_replay=row['initial_replay_status'],
                                  matching_phases=row['matching_phases'])), flush=True)
    m2.upstream_check(args.parcae_dir)
    require(not git(root, 'status', '--porcelain', '--untracked-files=no'), 'research sources changed')
    require(report['synthetic_backward_probes'] == 6, 'unexpected count-probe count')
    report.update(execution_status='PASS', initialization_replay_status=classify(report['rows']),
                  source_integrity_after='PASS', reviewer_mismatch_root_cause='OPEN; reviewer raw script/build attribution untested',
                  new_grok_or_claude_review='NOT TESTED', previous_scientific_failures='UNCHANGED')
    report['exported_states_scope'] = ('exact historical initial-state replay in original producer runtime only'
                                     if report['initialization_replay_status'] == 'PASS' else 'diagnostic states only; do not promote')
    write(out / 'result.json', report)
    return 0 if report['initialization_replay_status'] == 'PASS' else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parcae-dir', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    require(not out.is_relative_to(args.evidence.resolve()) and not out.is_relative_to(args.parcae_dir.resolve()),
            'output must be outside original evidence/upstream')
    out.mkdir(parents=True, exist_ok=False)
    report = dict(experiment='MYTHOS-INIT01-ORIGINAL-STATE-REPLAY-V1', execution_status='NOT TESTED',
                  initialization_replay_status='NOT TESTED',
                  limitations=['not a training run', 'not an A-M2L-01 coverage rerun',
                               'does not independently determine Claude mismatch cause',
                               'no quality, efficiency, ACT or resume-parity claim'])
    try:
        code = execute(args, out, report)
    except Exception:
        report.update(execution_status='BLOCKED', error=traceback.format_exc())
        write(out / 'result.json', report)
        traceback.print_exc()
        code = 2
    print(json.dumps(dict(execution=report['execution_status'],
                          initialization_replay=report['initialization_replay_status'],
                          sha256=sha((out/'result.json').read_bytes()), result=str(out/'result.json'))), flush=True)
    return code


if __name__ == '__main__':
    raise SystemExit(main())
