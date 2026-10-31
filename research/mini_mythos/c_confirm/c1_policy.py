"""C1 preregistered budget, independent holdout and decisions; no model code."""
from __future__ import annotations
import hashlib
import json
import math
from statistics import mean, stdev

EXPERIMENT = 'MYTHOS-C1-EQUAL-COUNT-HOLDOUT-V1'
SEEDS = (1101, 1202, 1303, 1404, 1505)
ARMS = ('GPT', 'P4', 'C4')
BATCH, REFERENCE_STEPS = 32, 3000
EXPECTED_COUNTS = {'GPT': 73433088, 'P4': 114130944, 'C4': 118554624}
EXPECTED_PARAMETERS = {'GPT': 65344, 'P4': 60224, 'C4': 62784}
LEGACY_QUOTAS = {'H1': 512, 'HC': 256, 'H2': 512}
LEGACY_DIGESTS = {
    'H1': '92cf3818dbeb838e62c3937f836ecd3f4c94190ca7b6a9719e0b1a1e0156a6ce',
    'HC': '18ec9725035bb257b0bf62a3ab7f38961a69c42878f522ad41f1daa01d85fab4',
    'H2': 'e6256d5ff6cd99e113ac07b7c373953f5e3b9c9bfd6a689d7e90904064350543',
}
INHERITED = {
    'm2_matched/experiment.py': '74f00c64448ddbc224a48ef83dc031a90c33448ccb92647666707f6b8f988967',
    'r1b_calibration/task.py': '1baebb6e47f39de63e894e7d8379bdcd8403e8cd79ead1e33fa6e525278940af',
    'mech_ab/mechanisms.py': 'a7da3cafda5e0e9c45881f6ed68f1c192e78a04a41c2e89251ec255a88bb5c37',
    'mech_ab/metrics.py': '54249a6edce2c3dcc534b180c047a3539f358ff2f21a55a287d75fd623422c6a',
    'mech_ab/run_cpu.py': 'fef3bcaac0b3b58f6660ba52529df85175187f5f8fa02b680b64c3d3bca15955',
}
INHERITED['mech_c/c_adapters.py'] = '7696f81ac867e030b4d894c44e2fad176a79ec407e1919cf284f5fdb130b9101'


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def object_sha(value):
    return digest(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode())


def budgets(counts):
    require(counts == EXPECTED_COUNTS, 'count drift; no automatic rebudgeting')
    ceiling = counts['C4'] * REFERENCE_STEPS
    arms = {}
    for arm in ARMS:
        n = counts[arm]
        steps = ceiling // n
        unused = ceiling - n * steps
        require(steps >= REFERENCE_STEPS and 0 <= unused <= ceiling * .001, 'budget slack')
        arms[arm] = dict(steps=steps, step_flops=n, total_flops=n*steps,
                         unused_fraction=unused/ceiling)
    return dict(ceiling_flops=ceiling, arms=arms, scope='supported operators, not hardware work')


def saved_steps(arm, endpoint):
    require(arm in ARMS, 'unknown arm')
    return sorted({endpoint, REFERENCE_STEPS} if arm == 'P4' else {endpoint})


def carry_count(a, b):
    carry = count = 0
    for power in (1, 10, 100):
        carry = ((a//power) % 10 + (b//power) % 10 + carry)//10
        count += carry
    return count


def allocate(task):
    """Only unlabelled keys/strata. Never calls task.example for any holdout."""
    buckets = {c: [] for c in range(4)}
    for a in range(100, 1000):
        for b in range(a, 1000):
            if task.role(a, b) == 'reserved':
                rank = digest(f'MYTHOS-MES1-HOLDOUT-V1:{a}:{b}'.encode())
                buckets[carry_count(a, b)].append((rank, a, b))
    legacy = {k: [] for k in LEGACY_QUOTAS}
    for c, rows in buckets.items():
        rows.sort()
        start = 0
        for name, n in LEGACY_QUOTAS.items():
            require(len(rows) >= start+n, 'legacy allocation too small')
            legacy[name].extend([a, b, c] for _, a, b in rows[start:start+n])
            start += n
    hashes = {k: object_sha(v) for k, v in legacy.items()}
    require(hashes == LEGACY_DIGESTS, 'legacy exclusion identity differs')
    excluded = {(a, b) for rows in legacy.values() for a, b, _ in rows}
    require(len(excluded) == 5120, 'legacy duplicate keys')
    selected = []
    for c, rows in buckets.items():
        eligible = sorted((digest(f'MYTHOS-C1-HOLDOUT-V1:{a}:{b}'.encode()), a, b)
                          for _, a, b in rows if (a, b) not in excluded)
        require(len(eligible) >= 512, 'insufficient fresh holdout stratum')
        selected.extend([a, b, c] for _, a, b in eligible[:512])
    keys = {(a, b) for a, b, _ in selected}
    require(len(keys) == 2048 and not keys & excluded, 'new holdout overlap')
    manifest = dict(name='C1T', pairs=2048, per_stratum=512,
                    allocation_sha256=object_sha(selected), excluded_legacy=hashes,
                    excluded_pairs=5120, scope='keys only; no holdout answer materialization')
    return selected, manifest


def test_examples(task, allocation):
    rows = []
    for a, b, c in allocation:
        require(a <= b and task.role(a, b) == 'reserved', 'nonreserved/canonical test pair')
        reverse = hashlib.sha256(f'MYTHOS-C1-ORDER-V1:{a}:{b}'.encode()).digest()[0] & 1
        row = task.example(b, a) if reverse else task.example(a, b)
        require(row['carry'] == c, 'stratum disagreement')
        rows.append(row)
    return rows


def screen(reference, candidate, improvement=True):
    require(len(reference) == len(candidate) == len(SEEDS), 'five paired seeds required')
    require(all(math.isfinite(x) and 0 <= x <= 1 for x in reference+candidate), 'invalid accuracy')
    delta = [b-a for a, b in zip(reference, candidate)]
    if improvement and mean(reference) > .99:
        status, reason = 'BLOCKED', 'CEILING_LIMIT'
    else:
        bound = .01 if improvement else -.01
        ok = mean(delta) >= bound-1e-12 and min(delta) >= -.01-1e-12
        status, reason = ('PASS' if ok else 'FAIL'), 'PREDECLARED_ENGINEERING_SCREEN'
    return dict(status=status, reason=reason, paired_accuracy_deltas=delta,
                mean_accuracy_delta=mean(delta), scope='C1T; not statistical superiority/noninferiority')


def selection_status(primary, safeguard):
    statuses = (primary, safeguard)
    require(all(s in ('PASS', 'FAIL', 'BLOCKED') for s in statuses), 'invalid screen status')
    return 'FAIL' if 'FAIL' in statuses else 'BLOCKED' if 'BLOCKED' in statuses else 'PASS'


def expected_conditions():
    return {(a, s, 'final', 4) for a in ARMS for s in SEEDS} | {
        ('P4', s, 'step3000', 4) for s in SEEDS}


def crossed_bootstrap(reference, candidate, strata, repeats=5000):
    import numpy as np
    x, y, strata = np.asarray(reference, float), np.asarray(candidate, float), np.asarray(strata)
    require(x.shape == y.shape == (len(SEEDS), len(strata)), 'bootstrap shape')
    require(set(strata.tolist()) == set(range(4)), 'bootstrap strata')
    rng = np.random.default_rng(731031)
    groups = [np.flatnonzero(strata == c) for c in range(4)]
    delta = y-x
    draws = np.empty(repeats)
    for i in range(repeats):
        seeds = rng.integers(0, len(SEEDS), size=len(SEEDS))
        questions = np.concatenate([rng.choice(g, len(g), replace=True) for g in groups])
        draws[i] = delta[np.ix_(seeds, questions)].mean()
    return dict(repeats=repeats, seed=731031, interval95=np.quantile(draws, [.025, .975]).tolist(),
                scope='paired crossed percentile bootstrap; five seeds; diagnostic only')


def summarize(rows, truth, task):
    mapping = {(r['arm'], r['seed'], r['checkpoint'], r['depth']): r for r in rows}
    require(set(mapping) == expected_conditions() and len(rows) == len(mapping), 'twenty conditions required')
    for row in rows:
        require(task.score(truth, row['predictions']) == row['metrics'], 'saved answer/score mismatch')
    def values(arm, checkpoint='final'):
        return [mapping[arm, s, checkpoint, 4]['metrics']['all']['accuracy'] for s in SEEDS]
    primary = screen(values('P4'), values('C4'))
    safeguard = screen(values('GPT'), values('C4'), False)
    selected = selection_status(primary['status'], safeguard['status'])
    correct = lambda a: [[p == t['target'] for p, t in
                          zip(mapping[a, s, 'final', 4]['predictions'], truth)] for s in SEEDS]
    descriptive = {}
    for arm in ARMS:
        v = values(arm)
        descriptive[arm] = dict(per_seed=v, mean_accuracy=mean(v), worst_seed_accuracy=min(v), sample_std=stdev(v))
    return dict(primary_equal_budget_C4_P4=primary,
                same_updates_C4_P4=screen(values('P4', 'step3000'), values('C4')),
                external_GPT_safeguard=safeguard, candidate_selection_status=selected,
                descriptive=descriptive,
                primary_uncertainty=crossed_bootstrap(correct('P4'), correct('C4'), [r['carry'] for r in truth]),
                exit_code={'PASS': 0, 'FAIL': 1, 'BLOCKED': 2}[selected],
                hardware_efficiency_status='NOT TESTED', capacity_causality_status='NOT TESTED',
                legacy_HC_H2_status='NOT OPENED')


def parse_bytes(raw):
    def pairs(items):
        value = {}
        for key, item in items:
            require(key not in value, 'duplicate JSON key')
            value[key] = item
        return value
    def invalid(value):
        raise ValueError('nonfinite JSON constant: '+value)
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


def bound_json(path, expected_sha):
    """Hash and parse the SAME byte buffer; no check/reopen window."""
    raw = path.read_bytes()
    require(digest(raw) == expected_sha, 'bound file digest mismatch: '+str(path))
    return parse_bytes(raw)
