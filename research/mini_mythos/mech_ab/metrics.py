"""Preregistered exploratory screens; no Torch or model dependencies."""
from __future__ import annotations
import math
import statistics

SEEDS = (42, 20261029, 20261030)
ARMS = ('P4', 'A', 'B')
EXPERIMENT = 'MYTHOS-MECH-AB-CPU-V1'


def transitions(targets, predictions2, predictions4):
    if not targets or not (len(targets) == len(predictions2) == len(predictions4)):
        raise ValueError('incomplete paired predictions')
    before = [p == y for p, y in zip(predictions2, targets)]
    after = [p == y for p, y in zip(predictions4, targets)]
    fixed = sum(not a and b for a, b in zip(before, after))
    broken = sum(a and not b for a, b in zip(before, after))
    correct, wrong = sum(before), len(before) - sum(before)
    return {'wrong_to_right': fixed, 'right_to_wrong': broken, 'net_correct': fixed-broken,
            'original_correct': correct, 'original_wrong': wrong, 'problems': len(targets),
            'correction_rate': fixed/wrong if wrong else None,
            'corruption_rate': broken/correct if correct else None}


def screen(base, changed, *, easy_delta=None, strict_each=False):
    if len(base) != 3 or len(changed) != 3:
        raise ValueError('exactly three paired seeds required')
    if not all(math.isfinite(x) and 0 <= x <= 1 for x in base+changed):
        raise ValueError('invalid accuracy')
    deltas = [b-a for a, b in zip(base, changed)]
    passed = statistics.mean(deltas) >= .01-1e-12 and min(deltas) >= -.01-1e-12
    if strict_each:
        passed = passed and min(deltas) > 0
    if easy_delta is not None:
        if len(easy_delta) != 3:
            raise ValueError('three easy deltas required')
        passed = passed and min(easy_delta) >= -.01-1e-12
    ceiling = statistics.mean(base) > .99
    return {'status': 'BLOCKED' if ceiling else 'PASS' if passed else 'FAIL',
            'reason': 'CEILING' if ceiling else 'PREDECLARED_EXPLORATORY_SCREEN',
            'paired_accuracy_deltas': deltas, 'mean_accuracy_delta': statistics.mean(deltas),
            'scope': 'already-viewed development only; not significance or efficiency acceptance'}


def summarize(rows):
    keyed = {(r['arm'], r['seed']): r for r in rows}
    expected = {(a, s) for a in ARMS for s in SEEDS}
    if len(rows) != 9 or set(keyed) != expected or any(r['status'] != 'PASS' for r in rows):
        raise ValueError('nine complete unique arms required')
    accuracy = lambda a, d: [keyed[a, s]['development'][str(d)]['metrics']['all']['accuracy'] for s in SEEDS]
    primary = {a: screen(accuracy('P4', 4), accuracy(a, 4)) for a in ('A', 'B')}
    depth = {}
    descriptive = {}
    for arm in ARMS:
        easy = [keyed[arm, s]['development']['4']['metrics']['0']['accuracy'] -
                keyed[arm, s]['development']['2']['metrics']['0']['accuracy'] for s in SEEDS]
        depth[arm] = screen(accuracy(arm, 2), accuracy(arm, 4), easy_delta=easy, strict_each=True)
        depth[arm]['easy_deltas'] = easy
        descriptive[arm] = {str(d): {'mean_accuracy': statistics.mean(accuracy(arm,d)),
                           'worst_seed_accuracy': min(accuracy(arm,d)),
                           'sample_std': statistics.stdev(accuracy(arm,d))} for d in (2,4)}
    codes = [v['status'] for v in primary.values()]
    return {'primary_quality': primary, 'extra_depth': depth, 'descriptive': descriptive,
            'depth2_deltas_vs_P4': {a:[b-c for b,c in zip(accuracy(a,2),accuracy('P4',2))] for a in ('A','B')},
            'exit_code': 1 if 'FAIL' in codes else 2 if 'BLOCKED' in codes else 0,
            'equal_compute_efficiency_status': 'NOT TESTED', 'held_out_test_status': 'NOT TESTED'}
