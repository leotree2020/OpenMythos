"""Recompute declared gates and compare seed-42 fresh-process replay."""
import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path


def audit(pilot, replay):
    assert pilot['git_head'] == replay['git_head'] == 'e533fbe36aaf18fd551ee21e5c2d20551b5a2e16'
    assert pilot['git_status'] == replay['git_status'] == ''
    assert pilot['script_sha256'] == replay['script_sha256']
    assert pilot['config_sha256'] == replay['config_sha256']
    assert pilot['data'] == replay['data']
    assert pilot['environment'] == replay['environment']
    assert pilot['upstream_tracked_status_after'] == replay['upstream_tracked_status_after'] == ''
    rows = {(r['seed'], r['arm']): r for r in pilot['rows']}
    assert set(rows) == {(s, a) for s in (42, 20261029, 20261030) for a in ('gpt', 'parcae')}
    replay_rows = {(r['seed'], r['arm']): r for r in replay['rows']}
    assert set(replay_rows) == {(42, a) for a in ('gpt', 'parcae')}
    checks = []
    for key, row in rows.items():
        assert row['train_tokens'] == 30720
        assert len(row['loss_trace']) == len(row['gradient_norm_trace']) == 120
        assert all(math.isfinite(x) for x in row['loss_trace'] + row['gradient_norm_trace'])
        assert row['preflight']['ce_abs_error'] <= 1e-6
        assert row['preflight']['causal_prefix_abs_error'] <= 1e-6
        assert row['initial_weights_sha256'] != row['final_weights_sha256']
        learning = row['final_validation']['nll'] <= row['initial_validation']['nll'] - .01
        assert row['status'] == ('PASS' if learning else 'FAIL')
        for name, i in [('initial_validation', 1), ('final_validation', 1), ('test', 2)]:
            e = row[name]
            assert e['target_tokens'] == ((pilot['data']['byte_lengths'][i] - 1) // 32) * 32
            assert e['target_tokens'] == e['windows'] * 32
            assert abs(math.exp(e['nll']) - e['ppl']) < 1e-10
        if key[0] == 42:
            other = replay_rows[key]
            fields = ['initialization', 'model_config', 'preflight', 'counts',
                      'initial_weights_sha256', 'final_weights_sha256',
                      'batch_starts_sha256', 'train_tokens', 'train_counted_flops',
                      'initial_validation', 'final_validation', 'test',
                      'loss_trace', 'gradient_norm_trace', 'status']
            assert all(row[f] == other[f] for f in fields), 'replay mismatch'
        checks.append(dict(seed=key[0], arm=key[1], learning_status=row['status'],
                           test_nll=row['test']['nll'], test_ppl=row['test']['ppl']))
    deltas = []
    for seed in (42, 20261029, 20261030):
        a, b = rows[seed, 'gpt'], rows[seed, 'parcae']
        assert a['batch_starts_sha256'] == b['batch_starts_sha256']
        assert a['initialization'] == b['initialization']
        for field in ['parameters', 'step_flops']:
            assert max(a['counts'][field], b['counts'][field]) / min(a['counts'][field], b['counts'][field]) <= 1.10
        deltas.append(b['test']['nll'] - a['test']['nll'])
    quality = 'PASS' if max(deltas) <= .05 and sum(deltas) / 3 <= .02 else 'FAIL'
    assert quality == pilot['quality_hypothesis_status']
    return dict(audit_status='PASS', budget_status='PASS', replay_status='PASS',
                learning_status='PASS' if all(r['learning_status'] == 'PASS' for r in checks) else 'FAIL',
                quality_hypothesis_status=quality, paired_test_nll_deltas=deltas,
                mean_test_nll_delta=sum(deltas) / 3, rows=checks,
                grok_review_status='NOT TESTED',
                limits='CPU tiny-corpus pilot; supported-op FLOPs; partial initialization control; no general superiority claim')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--pilot', type=Path, required=True)
    p.add_argument('--replay', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    pilot, replay = [json.loads(f.read_text()) for f in [args.pilot, args.replay]]
    result = audit(pilot, replay)
    import torch
    checked = []
    for path, report in [(args.pilot, pilot), (args.replay, replay)]:
        for row in report['rows']:
            checkpoint = path.parent / row['checkpoint_file']
            assert hashlib.sha256(checkpoint.read_bytes()).hexdigest() == row['checkpoint_sha256']
            weights = torch.load(checkpoint, map_location='cpu', weights_only=True)
            h = hashlib.sha256()
            for name, tensor in sorted(weights.items()):
                assert torch.isfinite(tensor).all()
                h.update(name.encode())
                h.update(tensor.contiguous().numpy().tobytes())
            assert h.hexdigest() == row['final_weights_sha256']
            checked.append(str(checkpoint.relative_to(args.pilot.parent)))
    result['checkpoint_integrity_status'] = 'PASS'
    result['checked_checkpoint_files'] = checked
    for filename, key in [('experiment.py', 'script_sha256'), ('frozen_config.json', 'config_sha256')]:
        blob = subprocess.check_output(['git', '-C', str(Path(__file__).parent), 'show',
            pilot['git_head'] + ':research/mini_mythos/m2_matched/' + filename])
        assert hashlib.sha256(blob).hexdigest() == pilot[key]
    result['frozen_source_identity_status'] = 'PASS'
    result['input_sha256_utf8_lf'] = {str(f.relative_to(args.pilot.parent)): hashlib.sha256(f.read_text().encode()).hexdigest()
                                   for f in [args.pilot, args.replay]}
    args.out.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
