"""Frozen C4-versus-S16 primary screen; other comparisons remain separate."""
from __future__ import annotations
import math
import statistics

EXPERIMENT = 'MYTHOS-MECH-C-LORA-CPU-V1'
ARMS = ('P4', 'S16', 'C4')
SEEDS = (42, 20261029, 20261030)


def screen(base, changed, easy=None, strict=False):
    if len(base) != 3 or len(changed) != 3:
        raise ValueError('three paired seeds required')
    if not all(math.isfinite(x) and 0 <= x <= 1 for x in base + changed):
        raise ValueError('invalid accuracy')
    delta = [b-a for a,b in zip(base,changed)]
    passed = statistics.mean(delta) >= .01-1e-12 and min(delta) >= -.01-1e-12
    if strict:
        passed = passed and min(delta) > 0
    if easy is not None:
        if len(easy) != 3 or not all(math.isfinite(v) for v in easy):
            raise ValueError('invalid carry0 deltas')
        passed = passed and min(easy) >= -.01-1e-12
    ceiling = statistics.mean(base) > .99
    return dict(status='BLOCKED' if ceiling else 'PASS' if passed else 'FAIL',
                reason='CEILING' if ceiling else 'PREDECLARED_EXPLORATORY_SCREEN',
                paired_accuracy_deltas=delta,mean_accuracy_delta=statistics.mean(delta),
                scope='already-viewed development; not significance/equal-compute acceptance')


def summarize(rows):
    keyed = {(r['arm'],r['seed']):r for r in rows}
    if (len(rows)!=9 or set(keyed)!={(a,s) for a in ARMS for s in SEEDS}
            or any(r['status']!='PASS' for r in rows)):
        raise ValueError('nine complete unique arms required')
    acc = lambda a,d:[keyed[a,s]['development'][str(d)]['metrics']['all']['accuracy'] for s in SEEDS]
    primary = screen(acc('S16',4),acc('C4',4))
    secondary = {a+'_minus_P4':screen(acc('P4',4),acc(a,4)) for a in ('S16','C4')}
    depth,descriptive = {},{}
    for arm in ARMS:
        easy = [keyed[arm,s]['development']['4']['metrics']['0']['accuracy']-
                keyed[arm,s]['development']['2']['metrics']['0']['accuracy'] for s in SEEDS]
        depth[arm]=screen(acc(arm,2),acc(arm,4),easy,True)
        depth[arm]['carry0_deltas']=easy
        descriptive[arm]={str(d):dict(mean_accuracy=statistics.mean(acc(arm,d)),
                             worst_seed_accuracy=min(acc(arm,d)),
                             sample_std=statistics.stdev(acc(arm,d))) for d in (2,4)}
    return dict(primary_C4_minus_S16=primary,secondary_vs_P4=secondary,
                extra_depth=depth,descriptive=descriptive,
                exit_code={'PASS':0,'FAIL':1,'BLOCKED':2}[primary['status']],
                equal_compute_efficiency_status='NOT TESTED',held_out_test_status='NOT TESTED')
