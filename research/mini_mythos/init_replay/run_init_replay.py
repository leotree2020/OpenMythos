#!/usr/bin/env python3
"""P1-R1: six exact original initializer/probe sequences, no training or optimizer.

Compare to the immutable M2/M2-L initial hashes in the producer CPU environment.
A successful replay does not establish why a different reviewer failed.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import math
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
PILOT_SHA = 'c5be0f6da8eab77ab499ad97a3aaf318633d2d44f234083165ffcacc3b26d7bb'
REF_SHA = '74f00c64448ddbc224a48ef83dc031a90c33448ccb92647666707f6b8f988967'
CONFIG_SHA = 'a49b38521a45e716b1cb5f2c2b55d317d06ca7542d02623349c5331e9fe26447'
SEEDS = (42, 20261029, 20261030)
ARMS = ('gpt', 'parcae')
PAIRABLE = {'transformer.wte.weight', 'lm_head.weight',
            'transformer.ln_f.weight', 'transformer.ln_f.bias'}


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    return sha(path.read_bytes())


def git(path, *args):
    return subprocess.check_output(['git', '-C', str(path), *args], text=True).strip()


def write(path, data):
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def unique_rows(rows):
    keys = [(r['seed'], r['arm']) for r in rows]
    expected = {(s, a) for s in SEEDS for a in ARMS}
    require(len(keys) == 6 and len(set(keys)) == 6 and set(keys) == expected,
            'expected exactly six unique historical seed/arm rows')
    return dict(zip(keys, rows))


def references(long, matched):
    a, b = unique_rows(long['rows']), unique_rows(matched['rows'])
    for key in a:
        require(a[key]['init_sha'] == b[key]['initial_weights_sha256'],
                'historical reports disagree on initial weights: ' + str(key))
        require(a[key]['shared_io_initialization'] == b[key]['initialization'],
                'historical reports disagree on IO: ' + str(key))
        require(a[key]['counts'] == b[key]['counts'],
                'historical reports disagree on counts: ' + str(key))
    return a


def snapshot(model, torch):
    whole = hashlib.sha256()
    tensors = {}
    for name, tensor in sorted(model.state_dict().items()):
        data = tensor.detach().cpu().contiguous().numpy().tobytes()
        whole.update(name.encode())
        whole.update(data)
        tensors[name] = {'shape': list(tensor.shape), 'dtype': str(tensor.dtype),
                         'sha256': sha(data), 'finite': bool(torch.isfinite(tensor).all())}
    return {'whole_state_sha256': whole.hexdigest(), 'tensors': tensors}


def changed(before, after):
    names = set(before['tensors']) | set(after['tensors'])
    return sorted(n for n in names if before['tensors'].get(n) != after['tensors'].get(n))


def classify(rows):
    unique_rows(rows)
    require(all(r['native_sequence_completed'] for r in rows), 'incomplete native sequences')
    historic = all(r['history_match'] and r['shared_io_match'] and r['counts_match']
                   and r['preflight_match'] for r in rows)
    preserved = all(r['probe_state_preserved'] and r['probe_rng_preserved']
                    and r['pairing_scope_ok'] and r['all_stored_tensors_finite'] for r in rows)
    return {'historical_init_status': 'PASS' if historic else 'FAIL',
            'probe_preservation_status': 'PASS' if preserved else 'FAIL',
            'comparison_status': 'PASS' if historic and preserved else 'FAIL',
            'reviewer_mismatch_root_cause': 'OPEN; original reviewer code/output not supplied',
            'scope': 'original CPU dependency recipe; not cross-build or training reproduction'}


def execute(args, out, report):
    import torch
    import numpy
    import einops
    report['environment'] = {
        'python': platform.python_version(), 'torch': str(torch.__version__),
        'numpy': numpy.__version__, 'einops': einops.__version__,
        'platform': platform.platform(), 'machine': platform.machine(),
        'torch_build': torch.__config__.show(), 'threads_before_setup': torch.get_num_threads(),
        'default_dtype': str(torch.get_default_dtype()), 'device': 'cpu'}
    require(platform.system() == 'Linux' and platform.python_version() == '3.12.3',
            'requires original Linux Python 3.12.3; no environment waiver')
    require((str(torch.__version__), numpy.__version__, einops.__version__) ==
            ('2.11.0+cpu', '1.26.4', '0.8.0'), 'requires original CPU dependency builds')
    require(torch.get_default_dtype() == torch.float32, 'requires original float32 default')
    root = Path(git(Path(__file__).parent, 'rev-parse', '--show-toplevel'))
    require(not git(root, 'status', '--porcelain', '--untracked-files=no'), 'dirty research sources')
    require(git(args.parcae_dir, 'rev-parse', 'HEAD') == PIN, 'wrong upstream pin')
    require(not git(args.parcae_dir, 'status', '--porcelain', '--untracked-files=no'), 'dirty upstream')
    ref = root / 'research/mini_mythos/m2_matched/experiment.py'
    cfg_path = ref.with_name('frozen_config.json')
    old_path = ref.parent / 'evidence/linux_e533fbe/pilot.json'
    require(file_sha(ref) == REF_SHA, 'original factory modified')
    require(file_sha(cfg_path) == CONFIG_SHA, 'original config modified')
    require(file_sha(args.pilot) == PILOT_SHA, 'M2-L input pilot changed')
    long = json.loads(args.pilot.read_text())
    require(long['code_head'] == '09d0d508fa0eef459c8b767b109b236f9490c014'
            and long['original_parcae_pin'] == PIN, 'wrong M2-L provenance')
    require(file_sha(old_path) == long['reference_pilot_sha256'], 'M2 reference pilot changed')
    expected = references(long, json.loads(old_path.read_text()))
    cfg = json.loads(cfg_path.read_text())
    require(cfg['selected']['ffn'] == 60 and cfg['source_pin'] == PIN, 'wrong factory arguments')
    spec = importlib.util.spec_from_file_location('p1r_original_m2', ref)
    require(spec is not None and spec.loader is not None, 'factory import unavailable')
    m2 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m2)
    m2.setup(args.parcae_dir)
    report['environment']['threads_after_setup'] = torch.get_num_threads()
    report.update(code_head=git(root, 'rev-parse', 'HEAD'), source_pin=PIN,
                  factory_sha256=REF_SHA, config_sha256=CONFIG_SHA, pilot_sha256=PILOT_SHA,
                  matched_pilot_sha256=file_sha(old_path), script_sha256=file_sha(Path(__file__)),
                  protocol_sha256=file_sha(Path(__file__).with_name('PROTOCOL.md')),
                  history_agreement_status='PASS', rows=[], native_started=True)
    (out / 'pip-freeze.txt').write_text(
        subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'], text=True))
    write(out / 'result.json', report)
    for seed in SEEDS:
        # Same order as original run(): construct GPT, then Parcae; pair BEFORE probing.
        models = {'gpt': m2.make('gpt', 60, seed), 'parcae': m2.make('parcae', 64, seed)}
        native = {arm: snapshot(model, torch) for arm, model in models.items()}
        shared = m2.pair_io(models['gpt'], models['parcae'])
        paired = {arm: snapshot(model, torch) for arm, model in models.items()}
        for arm, model in models.items():
            before_rng = sha(torch.get_rng_state().numpy().tobytes())
            preflight = m2.preflight(model, arm)
            preflight_rng = sha(torch.get_rng_state().numpy().tobytes())
            after_preflight = snapshot(model, torch)
            counts = m2.count(model, arm)
            count_rng = sha(torch.get_rng_state().numpy().tobytes())
            after_count = snapshot(model, torch)
            require(after_count['whole_state_sha256'] == m2.weights_sha(model),
                    'diagnostic hash implementation disagrees with producer hash')
            old = expected[seed, arm]
            pairing_changes = changed(native[arm], paired[arm])
            stage_values = {'native_constructor': native[arm], 'paired_io': paired[arm],
                            'after_preflight': after_preflight, 'after_count': after_count}
            row = {
                'seed': seed, 'arm': arm, 'native_sequence_completed': True,
                'expected_init_sha256': old['init_sha'], 'stages': stage_values,
                'history_match': after_count['whole_state_sha256'] == old['init_sha'],
                'stage_history_matches': {k: v['whole_state_sha256'] == old['init_sha']
                                          for k, v in stage_values.items()},
                'shared_io_match': shared == old['shared_io_initialization'],
                'counts_match': counts == old['counts'], 'counts': counts,
                'preflight_match': preflight == old['preflight'], 'preflight': preflight,
                'pairing_changed_tensors': pairing_changes,
                'pairing_scope_ok': not pairing_changes if arm == 'gpt'
                                    else set(pairing_changes) <= PAIRABLE,
                'preflight_changed_tensors': changed(paired[arm], after_preflight),
                'count_changed_tensors': changed(after_preflight, after_count),
                'probe_state_preserved': paired[arm] == after_preflight == after_count,
                'probe_rng_preserved': before_rng == preflight_rng == count_rng,
                'rng_sha256': {'before_preflight': before_rng,
                               'after_preflight': preflight_rng, 'after_count': count_rng},
                'all_stored_tensors_finite': all(v['finite'] for s in stage_values.values()
                                                 for v in s['tensors'].values())}
            report['rows'].append(row)
            write(out / 'result.json', report)
            print(json.dumps({'seed': seed, 'arm': arm, 'history_match': row['history_match'],
                              'stages_matching_history': row['stage_history_matches'],
                              'pairing_changed_tensors': pairing_changes,
                              'probe_state_preserved': row['probe_state_preserved']}), flush=True)
    require(not git(args.parcae_dir, 'status', '--porcelain', '--untracked-files=no'), 'upstream changed')
    require(not git(root, 'status', '--porcelain', '--untracked-files=no'), 'research source changed')
    require(file_sha(args.pilot) == PILOT_SHA, 'input evidence changed')
    report.update(execution_status='PASS', outcome=classify(report['rows']),
                  optimizer_updates=0, training_batches=0, native_sequences=6,
                  independent_review='NOT TESTED', upstream_unchanged=True)
    write(out / 'result.json', report)
    print(json.dumps({'execution': report['execution_status'], 'outcome': report['outcome']}), flush=True)
    return 0 if report['outcome']['comparison_status'] == 'PASS' else 1


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--parcae-dir', required=True, type=Path)
    p.add_argument('--pilot', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    args = p.parse_args()
    out = args.out.resolve()
    require(not out.is_relative_to(args.pilot.resolve().parent), 'output inside original evidence')
    out.mkdir(parents=True, exist_ok=False)
    report = {'experiment': 'MYTHOS-P1R1-INITIALIZER-PROVENANCE-V1',
              'execution_status': 'NOT TESTED', 'outcome': None,
              'limitations': ['no training or quality measurements',
                              'reviewer mismatch cause remains OPEN',
                              'not a cross-build test or formal Oracle acceptance']}
    try:
        return execute(args, out, report)
    except Exception:
        report.update(execution_status='FAIL' if report.get('native_started') else 'BLOCKED',
                      error=traceback.format_exc())
        write(out / 'result.json', report)
        traceback.print_exc()
        return 1 if report.get('native_started') else 2


if __name__ == '__main__':
    raise SystemExit(main())
