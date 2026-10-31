"""MES-1 fixed design, data allocation and paired decision rules; no model code."""
from __future__ import annotations
import hashlib
import json
import math
from statistics import mean, stdev

EXPERIMENT = 'MYTHOS-MES1-EQUAL-COUNT-HOLDOUT-V1'
SEEDS = (101, 202, 303, 404, 505)
ARMS = ('GPT', 'P2', 'P4', 'A')
DEPTH = {'GPT': 4, 'P2': 2, 'P4': 4, 'A': 4}
EXPECTED_COUNTS = {'GPT': 73433088, 'P2': 80289792, 'P4': 114130944, 'A': 145428480}
BATCH, REFERENCE_STEPS = 32, 3000
QUOTAS = {'H1': 512, 'HC': 256, 'H2': 512}
INHERITED = {
    'm2_matched/experiment.py': '74f00c64448ddbc224a48ef83dc031a90c33448ccb92647666707f6b8f988967',
    'r1b_calibration/task.py': '1baebb6e47f39de63e894e7d8379bdcd8403e8cd79ead1e33fa6e525278940af',
    'mech_ab/mechanisms.py': 'a7da3cafda5e0e9c45881f6ed68f1c192e78a04a41c2e89251ec255a88bb5c37',
    'mech_ab/metrics.py': '54249a6edce2c3dcc534b180c047a3539f358ff2f21a55a287d75fd623422c6a',
    'mech_ab/run_cpu.py': 'fef3bcaac0b3b58f6660ba52529df85175187f5f8fa02b680b64c3d3bca15955',
}


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def object_sha(value):
    return digest(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode())


def budgets(counts):
    require(counts == EXPECTED_COUNTS, 'count drift: stop before training; no automatic re-budgeting')
    ceiling = REFERENCE_STEPS * counts['A']
    result = {}
    for arm in ARMS:
        steps = ceiling // counts[arm]
        total = steps * counts[arm]
        require(steps >= REFERENCE_STEPS and 0 <= ceiling-total <= ceiling*.001, 'budget tolerance')
        result[arm] = dict(steps=steps, step_flops=counts[arm], total_flops=total,
                           unused_fraction=(ceiling-total)/ceiling)
    return {'ceiling_flops': ceiling, 'arms': result, 'scope': 'supported operators, not hardware work'}


def carry_count(a, b):
    # Select strata without constructing full answer labels.
    carry = count = 0
    for power in (1, 10, 100):
        carry = ((a//power)%10 + (b//power)%10 + carry)//10
        count += carry
    return count


def allocate(task):
    buckets = {c: [] for c in range(4)}
    for a in range(100, 1000):
        for b in range(a, 1000):
            if task.role(a, b) == 'reserved':
                rank = digest(f'MYTHOS-MES1-HOLDOUT-V1:{a}:{b}'.encode())
                buckets[carry_count(a, b)].append((rank, a, b))
    selected = {name: [] for name in QUOTAS}
    for c, rows in buckets.items():
        rows.sort()
        require(len(rows) >= sum(QUOTAS.values()), 'insufficient reserved stratum')
        start = 0
        for name, n in QUOTAS.items():
            selected[name].extend([a, b, c] for _, a, b in rows[start:start+n])
            start += n
    keys = [{(a, b) for a, b, _ in selected[name]} for name in QUOTAS]
    require(sum(map(len, keys)) == len(set.union(*keys)), 'holdout collision')
    manifest = {name: {'pairs': len(rows), 'per_stratum': QUOTAS[name],
                       'allocation_sha256': object_sha(rows)} for name, rows in selected.items()}
    return selected, manifest


def h1_examples(task, allocation):
    rows = []
    for a, b, c in allocation['H1']:
        require(task.role(a, b) == 'reserved', 'nonreserved H1')
        reverse = hashlib.sha256(f'MYTHOS-MES1-ORDER-V1:{a}:{b}'.encode()).digest()[0] & 1
        row = task.example(b, a) if reverse else task.example(a, b)
        require(row['carry'] == c, 'stratum disagreement')
        rows.append(row)
    return rows


def screen(reference, candidate, improvement=True):
    require(len(reference) == len(candidate) == len(SEEDS), 'five complete paired seeds required')
    require(all(math.isfinite(x) and 0 <= x <= 1 for x in reference+candidate), 'invalid accuracy')
    delta = [b-a for a, b in zip(reference, candidate)]
    if improvement and mean(reference) > .99:
        status, reason = 'BLOCKED', 'CEILING_LIMIT'
    else:
        ok = (mean(delta) >= .01-1e-12 if improvement else mean(delta) >= -.01-1e-12)
        ok = ok and min(delta) >= -.01-1e-12
        status, reason = ('PASS' if ok else 'FAIL'), 'PREDECLARED_ENGINEERING_SCREEN'
    return dict(status=status, reason=reason, paired_accuracy_deltas=delta,
                mean_accuracy_delta=mean(delta), scope='H1; not statistical superiority/noninferiority')


def crossed_bootstrap(reference, candidate, strata, repeats=5000):
    """Resample seeds and questions, not their product as independent observations."""
    import numpy as np
    x, y = np.asarray(reference, dtype=float), np.asarray(candidate, dtype=float)
    s = np.asarray(strata)
    require(x.shape == y.shape == (len(SEEDS), len(s)), 'bootstrap pairing shape')
    require(set(s.tolist()) == set(range(4)), 'bootstrap strata')
    rng = np.random.default_rng(731031)
    groups = [np.flatnonzero(s == c) for c in range(4)]
    draws = np.empty(repeats)
    delta = y-x
    for i in range(repeats):
        seeds = rng.integers(0, len(SEEDS), size=len(SEEDS))
        # The SAME question sample is used for all selected seeds and both methods.
        questions = np.concatenate([rng.choice(g, size=len(g), replace=True) for g in groups])
        draws[i] = delta[np.ix_(seeds, questions)].mean()
    return dict(repeats=repeats, seed=731031, interval95=np.quantile(draws, [.025,.975]).tolist(),
                scope='paired crossed percentile bootstrap; five seeds; diagnostic, not acceptance')


def summarize(rows, truth):
    mapping = {(r['arm'], r['seed'], r['checkpoint'], r['depth']): r for r in rows}
    expected = {(a,s,'final',d) for s in SEEDS for a in ARMS
                for d in ((4,) if a=='GPT' else (2,) if a=='P2' else (2,4))}
    expected |= {('P4',s,'step3000',d) for s in SEEDS for d in (2,4)}
    require(set(mapping) == expected and len(mapping) == len(rows), 'forty complete evaluations required')
    require(all(len(r['predictions']) == len(truth) for r in rows), 'incomplete H1 predictions')
    def values(arm, depth, cp='final'):
        return [mapping[arm,s,cp,depth]['metrics']['all']['accuracy'] for s in SEEDS]
    primary = screen(values('P4',4), values('A',4))
    depth = screen(values('A',2), values('A',4))
    easy = [mapping['A',s,'final',4]['metrics']['0']['accuracy']-
            mapping['A',s,'final',2]['metrics']['0']['accuracy'] for s in SEEDS]
    if depth['status'] != 'BLOCKED':
        depth['status'] = 'PASS' if (mean(depth['paired_accuracy_deltas'])>=.01-1e-12 and
                           min(depth['paired_accuracy_deltas'])>0 and min(easy)>=-.01-1e-12) else 'FAIL'
    depth['carry0_deltas'] = easy
    transition_rows = []
    for seed in SEEDS:
        a = mapping['A',seed,'final',2]['predictions']
        b = mapping['A',seed,'final',4]['predictions']
        old = [p == t['target'] for p,t in zip(a,truth)]
        new = [p == t['target'] for p,t in zip(b,truth)]
        fixed = sum(not x and y for x,y in zip(old,new))
        broken = sum(x and not y for x,y in zip(old,new))
        transition_rows.append(dict(seed=seed,wrong_to_right=fixed,right_to_wrong=broken,net_correct=fixed-broken))
    descriptive = {}
    for arm in ARMS:
        depths=(4,) if arm=='GPT' else (2,) if arm=='P2' else (2,4)
        descriptive[arm]={}
        for d in depths:
            v=values(arm,d)
            descriptive[arm][str(d)]=dict(per_seed=v,mean_accuracy=mean(v),worst_seed_accuracy=min(v),sample_std=stdev(v))
    correct = lambda arm: [[p == t['target'] for p,t in
                zip(mapping[arm,s,'final',4]['predictions'], truth)] for s in SEEDS]
    return dict(primary_equal_budget_A4_P4=primary,
                same_updates_A4_P4=screen(values('P4',4,'step3000'),values('A',4)),
                external_GPT_safeguard=screen(values('GPT',4),values('A',4),False),
                intermediate_P2_safeguard=screen(values('P2',2),values('A',2),False),
                A_extra_depth=depth,A_transitions=transition_rows,descriptive=descriptive,
                primary_uncertainty=crossed_bootstrap(correct('P4'),correct('A'),[r['carry'] for r in truth]),
                exit_code={'PASS':0,'FAIL':1,'BLOCKED':2}[primary['status']],
                hardware_efficiency_status='NOT TESTED',HC_status='NOT OPENED',H2_status='NOT OPENED')
