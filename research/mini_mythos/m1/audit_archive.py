"""Audit M1 submitted evidence; does not claim to rerun training or verify weights."""
import argparse
import hashlib
import json
import math
import platform
import re
import tarfile
from pathlib import Path

import torch

ARCHIVE_SHA = 'f5542ebd2e92dd165b5e3155f7496c3698924b834f14b11e00a391366a54ed4c'
PIN = '69284c13746e849104f738d6d1a347b1f457df76'
SEEDS = (42, 20261029, 20261030)

def digest(t):
    return hashlib.sha256(t.contiguous().numpy().tobytes()).hexdigest()

def audit(path):
    raw = path.read_bytes()
    actual_sha = hashlib.sha256(raw).hexdigest()
    if actual_sha != ARCHIVE_SHA:
        raise ValueError('Archive SHA256 mismatch')
    expected = {f'{arm}_{seed}.json' for arm in ('A', 'B') for seed in SEEDS}
    with tarfile.open(path, 'r:gz') as tar:
        members = tar.getmembers()
        if len(members) != 6 or {m.name for m in members} != expected:
            raise ValueError('Unexpected or duplicate archive members')
        if not all(m.isfile() and 0 < m.size < 65536 for m in members):
            raise ValueError('Non-regular or oversized archive member')
        entries = {m.name: tar.extractfile(m).read() for m in members}
    docs = {name: json.loads(data) for name, data in entries.items()}
    pools = [torch.tensor([i for i in range(16**4) if predicate(i)], dtype=torch.long)
             for predicate in (lambda i: i % 10 < 8, lambda i: i % 10 == 8,
                               lambda i: i % 10 == 9)]
    train, val_pool, test_pool = pools
    eg = torch.Generator().manual_seed(1212)
    val = val_pool[torch.randperm(len(val_pool), generator=eg)[:1024]]
    test = test_pool[torch.randperm(len(test_pool), generator=eg)[:1024]]
    assert set(train.tolist()).isdisjoint(val.tolist())
    assert set(train.tolist()).isdisjoint(test.tolist())
    assert set(val.tolist()).isdisjoint(test.tolist())
    rows = []
    for seed in SEEDS:
        sampler = torch.Generator().manual_seed(seed+11)
        batches = torch.cat([train[torch.randint(len(train), (32,), generator=sampler)]
                             for _ in range(180)])
        expected_data = dict(train_batch_codes_sha256=digest(batches),
                             val_ids_sha256=digest(val), test_ids_sha256=digest(test),
                             zero_split_overlap=True)
        for letter, arm, params in (('A', 'standard', 18704), ('B', 'parcae', 28736)):
            name = f'{letter}_{seed}.json'
            d = docs[name]
            cfg, obs, model = d['config'], d['observed'], d['model']
            expected_cfg = dict(seed=seed, steps=180, batch=32, sequence_length=16,
                                vocab=16, period=4, optimizer='AdamW', lr=.002,
                                weight_decay=0., native_pair=[0,2] if letter=='B' else None,
                                parcae_core_repeats=2 if letter=='B' else None)
            assert cfg == expected_cfg, (name, 'configuration')
            assert d['arm'] == arm and d['data'] == expected_data, (name, 'data identity')
            assert d['source'] == ('official Parcae @ '+PIN if letter=='B'
                                   else 'torch.nn.TransformerEncoderLayer')
            assert d['environment'] == dict(python='3.12.3', torch='2.11.0+cu130',
                                            cpu=True, threads=1)
            assert model['params'] == params
            assert all(re.fullmatch('[0-9a-f]{64}', model[k]) for k in
                       ('initial_weights_sha256', 'final_weights_sha256'))
            assert model['initial_weights_sha256'] != model['final_weights_sha256']
            assert d['criteria'] == dict(validation_nll_decrease_min=.05,
                weights_updated=True, finite_loss_grad=True, identical_dataset_seeds=True)
            for prefix in ('initial_val', 'final_val', 'final_test'):
                nll, ppl = obs[prefix+'_nll'], obs[prefix+'_ppl']
                assert math.isfinite(nll) and nll >= 0
                assert math.isclose(math.exp(nll), ppl, rel_tol=1e-12)
            for key in ('first_10_train_loss', 'last_10_train_loss'):
                assert len(obs[key]) == 10
                assert all(math.isfinite(x) and x >= 0 for x in obs[key])
            assert math.isfinite(obs['training_s']) and obs['training_s'] > 0
            assert obs['maxrss_kib'] > 0 and obs['flops'] == 'NOT MEASURED'
            assert obs['final_val_nll'] <= obs['initial_val_nll']-.05
            assert d['status'] == 'PASS'
            rows.append(dict(file=name, sha256=hashlib.sha256(entries[name]).hexdigest(),
                status='PASS', seed=seed, arm=arm, params=params,
                initial_val_nll=obs['initial_val_nll'], final_val_nll=obs['final_val_nll'],
                final_test_nll=obs['final_test_nll'], training_s=obs['training_s']))
    return dict(experiment='M1_ARCHIVE_INDEPENDENT_AUDIT', status='PASS',
        archive_sha256=actual_sha, archive_bytes=len(raw), files=rows,
        auditor_environment=dict(python=platform.python_version(), torch=torch.__version__),
        verified=['archive bytes match user-reported SHA256', 'exact six regular JSON members',
                  'configuration and parameter counts match frozen M1 specification',
                  'batch/split IDs independently regenerated and SHA256 matched',
                  'split ID sets disjoint', 'saved losses finite and PPL=exp(NLL)',
                  'validation NLL decrease >=.05 in all six reports',
                  'reported initial/final weight hashes differ'],
        limitations=['Evidence audit, not an independent training rerun',
                     'Actual model weights and per-step gradients are absent',
                     'Weight hash correctness and all 180 gradient steps not independently verified',
                     'JSON does not embed experiment Git commit or full pip freeze',
                     'M1 FLOPs not measured; architecture superiority NOT TESTED',
                     'Grok independent review NOT TESTED'])

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('archive', type=Path)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    result = audit(a.archive)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
