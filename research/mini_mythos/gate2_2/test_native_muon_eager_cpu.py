"""Isolated CPU regression of pinned native Parcae MuonAdamW, not a model test.

Run: PARCAE_SRC=/absolute/path/to/pinned/parcae TORCHDYNAMO_DISABLE=1 \
     python -m unittest discover -s research/mini_mythos/gate2_2 \
       -p 'test_native_muon_eager_cpu.py' -v
Does not modify or vendor upstream. Compiled CUDA/official train.py are NOT TESTED.
"""
import copy
import importlib.util
import os
from pathlib import Path
import subprocess
import unittest

import torch

PIN = 'fb2cd5d9e6653f44200d59fcfe5c017f8d7bb82f'


class SmallFixture(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.block = torch.nn.Linear(8, 8)
        self.lm_head = torch.nn.Linear(8, 8)

    def forward(self, x):
        return self.lm_head(torch.tanh(self.block(x))).square().mean()


def load_native():
    if os.getenv('TORCHDYNAMO_DISABLE') != '1':
        raise RuntimeError('CPU eager only: TORCHDYNAMO_DISABLE=1 required')
    root = os.getenv('PARCAE_SRC')
    if not root:
        raise RuntimeError('PARCAE_SRC must point to exact pinned unmodified Parcae checkout')
    source = Path(root) / 'recpre/optim/muon_adamw.py'
    if not source.is_file():
        raise RuntimeError(f'Missing official file: {source}')
    actual = subprocess.check_output(['git', 'hash-object', str(source)], text=True).strip()
    if actual != PIN:
        raise RuntimeError(f'Wrong upstream file: {actual} != {PIN}')
    spec = importlib.util.spec_from_file_location('pinned_parcae_muon_cpu', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_run(native):
    torch.manual_seed(20261029)
    model = SmallFixture()
    groups = native.get_muon_param_groups(model.named_parameters())
    optimizer = native.MuonAdamW(groups)
    return model, optimizer


def run_steps(model, opt, data, start, stop):
    for i in range(start, stop):
        opt.zero_grad(set_to_none=True)
        loss = model(data[i])
        if not torch.isfinite(loss).item():
            raise AssertionError('non-finite loss')
        loss.backward()
        opt.step()
    return {k: p.detach().clone() for k, p in model.named_parameters()}


class NativeMuonOptimizerCPU(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)
        torch.use_deterministic_algorithms(True)
        cls.native = load_native()

    def test_native_group_routing(self):
        model, opt = make_run(self.native)
        self.assertEqual([g['kind'] for g in opt.param_groups], ['adamw', 'muon'])
        self.assertEqual(len(opt.param_groups[0]['params']), 3)
        self.assertEqual(len(opt.param_groups[1]['params']), 1)

    def test_resume_exact_and_missing_state_negative(self):
        gen = torch.Generator().manual_seed(13579)
        data = torch.randn(6, 2, 8, generator=gen)
        a, oa = make_run(self.native)
        full = run_steps(a, oa, data, 0, 6)
        b, ob = make_run(self.native)
        run_steps(b, ob, data, 0, 3)
        snapshot = copy.deepcopy({'model': b.state_dict(), 'optimizer': ob.state_dict()})
        restored, orst = make_run(self.native)
        restored.load_state_dict(snapshot['model'])
        orst.load_state_dict(snapshot['optimizer'])
        resumed = run_steps(restored, orst, data, 3, 6)
        for name in full:
            self.assertTrue(torch.equal(full[name], resumed[name]), f'mismatch after resume {name}')
        self.assertTrue(orst.state)
        missing, omiss = make_run(self.native)
        missing.load_state_dict(snapshot['model'])
        divergent = run_steps(missing, omiss, data, 3, 6)
        self.assertTrue(any(not torch.equal(full[k], divergent[k]) for k in full),
                        'missing optimizer state negative control failed')


if __name__ == '__main__':
    unittest.main()
