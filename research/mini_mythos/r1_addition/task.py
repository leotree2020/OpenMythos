"""R1-A: carry-stratified addition; model-free task and verdict definitions.

Task format inspired by minGPT's projects/adder at 37baab71; independently
implemented grouped splits. No model architecture or arithmetic predictor here.
"""
from __future__ import annotations
import hashlib
import json
from collections import Counter

SEEDS = (42, 20261029, 20261030)
STEPS, BATCH, EVAL_BATCH = 3000, 32, 64


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def object_digest(value) -> str:
    return digest(json.dumps(value, sort_keys=True, separators=(',', ':')).encode())


def column_add(a: int, b: int) -> tuple[list[int], int]:
    if type(a) is not int or type(b) is not int or not (0 <= a < 100 and 0 <= b < 100):
        raise ValueError('operands must be integers in 0..99')
    carry = count = 0
    digits = []
    for power in (1, 10):
        value = (a // power) % 10 + (b // power) % 10 + carry
        digits.append(value % 10)
        carry = value // 10
        count += carry
    return digits + [carry], count


def example(a: int, b: int) -> dict:
    target, carry = column_add(a, b)
    expected = [int(c) for c in f'{a+b:03d}'[::-1]]
    if target != expected:
        raise RuntimeError('independent column and integer labels disagree')
    return {'a': a, 'b': b, 'key': f'{min(a,b):02d}:{max(a,b):02d}',
            'carry': carry, 'prompt': [int(c) for c in f'{a:02d}{b:02d}'],
            'target': target}


def training_tokens(row: dict) -> tuple[list[int], list[int]]:
    full = row['prompt'] + row['target']
    return full[:-1], [-100] * 3 + full[4:]


def make_splits() -> dict[str, list[dict]]:
    buckets = {c: [] for c in range(3)}
    for a in range(100):
        for b in range(a, 100):
            buckets[column_add(a, b)[1]].append((a, b))
    splits = {s: [] for s in ('train', 'validation', 'test')}
    for c in range(3):
        pairs = sorted(buckets[c], key=lambda ab: digest(
            f'MYTHOS-R1A-SPLIT-V1:{ab[0]}:{ab[1]}'.encode()))
        n_train, n_val = len(pairs) * 70 // 100, len(pairs) * 15 // 100
        for i, (a, b) in enumerate(pairs):
            split = 'train' if i < n_train else 'validation' if i < n_train+n_val else 'test'
            if split == 'train':
                splits[split].append(example(a, b))
                if a != b:
                    splits[split].append(example(b, a))
            else:
                h = hashlib.sha256(f'MYTHOS-R1A-ORDER-V1:{a}:{b}'.encode()).digest()
                splits[split].append(example(b, a) if h[0] & 1 else example(a, b))
    return splits


def manifest(splits: dict) -> dict:
    keys = {s: {e['key'] for e in rows} for s, rows in splits.items()}
    if any(keys[a] & keys[b] for a, b in (('train','validation'), ('train','test'), ('validation','test'))):
        raise RuntimeError('commutative split leakage')
    if len(set.union(*keys.values())) != 5050:
        raise RuntimeError('missing canonical pairs')
    for split in ('validation', 'test'):
        if len(keys[split]) != len(splits[split]):
            raise RuntimeError('repeated evaluation pair')
    return {s: {'examples': len(rows), 'canonical_pairs': len(keys[s]),
                'carry_counts': dict(sorted(Counter(str(r['carry']) for r in rows).items())),
                'sha256': object_digest(rows)} for s, rows in splits.items()}


def score(rows: list[dict], predictions: list[list[int]]) -> dict:
    if len(rows) != len(predictions) or not rows:
        raise ValueError('incomplete/empty prediction set')
    buckets = {k: {'correct': 0, 'total': 0, 'invalid': 0} for k in ('all','0','1','2')}
    for row, pred in zip(rows, predictions):
        invalid = len(pred) != 3 or any(type(t) is not int or not 0 <= t < 10 for t in pred)
        correct = not invalid and pred == row['target']
        for key in ('all', str(row['carry'])):
            buckets[key]['total'] += 1
            buckets[key]['correct'] += int(correct)
            buckets[key]['invalid'] += int(invalid)
    for item in buckets.values():
        if item['total'] == 0:
            raise ValueError('missing carry stratum')
        item['accuracy'] = item['correct']/item['total']
    return buckets


def learning_gate(metrics: list[dict], arm: str) -> str:
    if arm not in ('gpt', 'parcae') or len(metrics) != 3:
        raise ValueError('gate requires one native arm and exactly three seeds')
    overall, each = (.95, .90) if arm == 'gpt' else (.90, .80)
    return 'PASS' if all(m['all']['accuracy'] >= overall and
                         all(m[str(c)]['accuracy'] >= each for c in range(3))
                         for m in metrics) else 'FAIL'


def benefit(depth2: list[dict], depth4: list[dict]) -> dict:
    if len(depth2) != 3 or len(depth4) != 3:
        raise ValueError('benefit requires three paired seeds')
    hard = [b['2']['accuracy']-a['2']['accuracy'] for a,b in zip(depth2, depth4)]
    easy = [b['0']['accuracy']-a['0']['accuracy'] for a,b in zip(depth2, depth4)]
    ceiling = sum(a['2']['accuracy'] for a in depth2)/3 > .95
    passed = sum(hard)/3 >= .05 and min(hard) > 0 and min(easy) >= -.01
    return {'status': 'BLOCKED' if ceiling else 'PASS' if passed else 'FAIL',
            'reason': 'CEILING_LIMIT' if ceiling else 'prespecified_hard_gain_and_easy_safeguard',
            'hard_paired_accuracy_deltas': hard, 'mean_hard_gain': sum(hard)/3,
            'easy_paired_accuracy_deltas': easy,
            'scope': 'same trained Parcae, test carry2, d4 minus d2; elementary arithmetic only'}
