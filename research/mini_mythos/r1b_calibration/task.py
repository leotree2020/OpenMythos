"""R1-B-CAL: one development-only, three-digit addition difficulty candidate.

The answer format follows the existing minGPT-inspired R1-A task; models are
imported from unchanged upstream code, never implemented here.
"""
from __future__ import annotations
import hashlib
import json
from collections import Counter

SEEDS = (42, 20261029, 20261030)
STEPS, BATCH, EVAL_BATCH = 3000, 32, 64
PROMPT, ANSWER = 6, 4
TRAIN_PER_CARRY, DEV_PER_CARRY = 2500, 256
EXPERIMENT = 'MYTHOS-R1B-DEVELOPMENT-CALIBRATION-V1'


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def object_digest(value) -> str:
    return digest(json.dumps(value, sort_keys=True, separators=(',', ':')).encode())


def column_add(a: int, b: int) -> tuple[list[int], int]:
    if type(a) is not int or type(b) is not int or not (100 <= a < 1000 and 100 <= b < 1000):
        raise ValueError('strictly three-digit integer operands required')
    carry = count = 0
    digits = []
    for power in (1, 10, 100):
        value = (a // power) % 10 + (b // power) % 10 + carry
        digits.append(value % 10)
        carry = value // 10
        count += carry
    return digits + [carry], count


def role(a: int, b: int) -> str:
    a, b = min(a, b), max(a, b)
    h = hashlib.sha256(f'MYTHOS-R1B-ROLE-V1:{a}:{b}'.encode()).digest()
    slot = int.from_bytes(h[:8], 'big') % 100
    return 'train' if slot < 70 else 'development' if slot < 85 else 'reserved'


def example(a: int, b: int) -> dict:
    target, carry = column_add(a, b)
    if target != [int(c) for c in f'{a+b:04d}'[::-1]]:
        raise RuntimeError('column and integer addition disagree')
    return {'a': a, 'b': b, 'key': f'{min(a,b)}:{max(a,b)}', 'carry': carry,
            'prompt': [int(c) for c in f'{a:03d}{b:03d}'], 'target': target}


def training_tokens(row: dict) -> tuple[list[int], list[int]]:
    full = row['prompt'] + row['target']
    if len(row['prompt']) != PROMPT or len(row['target']) != ANSWER:
        raise ValueError('wrong prompt/answer lengths')
    return full[:-1], [-100] * (PROMPT-1) + row['target']


def make_data() -> dict[str, list[dict]]:
    # Do not materialize labels or a model-facing split for reserved-role pairs.
    buckets = {(s, c): [] for s in ('train', 'development') for c in range(4)}
    for a in range(100, 1000):
        for b in range(a, 1000):
            split = role(a, b)
            if split == 'reserved':
                continue
            carry = column_add(a, b)[1]
            rank = digest(f'MYTHOS-R1B-RANK-V1:{a}:{b}'.encode())
            buckets[split, carry].append((rank, a, b))
    result = {'train': [], 'development': []}
    for split, take in (('train', TRAIN_PER_CARRY), ('development', DEV_PER_CARRY)):
        for carry in range(4):
            candidates = sorted(buckets[split, carry])
            if len(candidates) < take:
                raise RuntimeError('insufficient candidates for frozen quota')
            for _, a, b in candidates[:take]:
                if split == 'train':
                    result[split].append(example(a, b))
                    if a != b:
                        result[split].append(example(b, a))
                else:
                    h = hashlib.sha256(f'MYTHOS-R1B-ORDER-V1:{a}:{b}'.encode()).digest()
                    result[split].append(example(b, a) if h[0] & 1 else example(a, b))
    return result


def manifest(data: dict) -> dict:
    if set(data) != {'train', 'development'}:
        raise ValueError('this stage permits train/development ONLY')
    keys = {s: {r['key'] for r in rows} for s, rows in data.items()}
    if keys['train'] & keys['development']:
        raise RuntimeError('commutative split leakage')
    if len(keys['train']) != 4*TRAIN_PER_CARRY or len(keys['development']) != 4*DEV_PER_CARRY:
        raise RuntimeError('canonical quota mismatch')
    if len(data['development']) != len(keys['development']):
        raise RuntimeError('repeated development question')
    for split, rows in data.items():
        for row in rows:
            if role(row['a'], row['b']) != split or row != example(row['a'], row['b']):
                raise RuntimeError('label/order/role drift, or reserved data exposure')
    return {s: {'examples': len(rows), 'canonical_pairs': len(keys[s]),
                'carry_counts': dict(sorted(Counter(str(r['carry']) for r in rows).items())),
                'sha256': object_digest(rows)} for s, rows in data.items()}


def score(rows: list[dict], predictions: list[list[int]]) -> dict:
    if len(rows) != len(predictions) or not rows:
        raise ValueError('incomplete or empty predictions')
    buckets = {k: {'correct': 0, 'total': 0, 'invalid': 0} for k in ('all', '0', '1', '2', '3')}
    for row, pred in zip(rows, predictions):
        bad = len(pred) != ANSWER or any(type(t) is not int or not 0 <= t < 10 for t in pred)
        ok = not bad and pred == row['target']
        for k in ('all', str(row['carry'])):
            buckets[k]['total'] += 1
            buckets[k]['correct'] += int(ok)
            buckets[k]['invalid'] += int(bad)
    for b in buckets.values():
        if not b['total']:
            raise ValueError('missing carry stratum')
        b['accuracy'] = b['correct'] / b['total']
    return buckets


def learning_gate(metrics: list[dict]) -> str:
    if len(metrics) != len(SEEDS):
        raise ValueError('three seed records required')
    return 'PASS' if all(m['all']['accuracy'] >= .80 and m['0']['accuracy'] >= .90
        and all(m[str(c)]['accuracy'] >= .60 for c in range(4)) for m in metrics) else 'FAIL'


def qualify(gpt: list[dict], parcae: list[dict] | None) -> dict:
    base = {'baseline_learning_status': learning_gate(gpt),
            'parcae_learning_status': 'NOT TESTED', 'task_qualification_status': 'FAIL',
            'reason': 'GPT_NOT_LEARNED_AT_FIXED_BUDGET', 'hard_d2_accuracy': [],
            'final_test_status': 'NOT TESTED', 'extra_depth_benefit_status': 'NOT TESTED'}
    if base['baseline_learning_status'] == 'FAIL':
        return base
    if parcae is None:
        raise ValueError('passing baseline requires completed Parcae results')
    base['parcae_learning_status'] = learning_gate(parcae)
    base['hard_d2_accuracy'] = [m['3']['accuracy'] for m in parcae]
    if base['parcae_learning_status'] == 'FAIL':
        base['reason'] = 'PARCAE_NOT_LEARNED_AT_FIXED_BUDGET'
    elif max(base['hard_d2_accuracy']) > .90:
        base.update(task_qualification_status='BLOCKED', reason='DEVELOPMENT_CEILING')
    else:
        base.update(task_qualification_status='PASS', reason='LEARNABLE_WITH_DEVELOPMENT_HEADROOM')
    return base
