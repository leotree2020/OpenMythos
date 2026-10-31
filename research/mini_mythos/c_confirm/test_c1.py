"""C1 bounded CPU checks. Affine/tanh fixtures are NOT native learning evidence."""
from __future__ import annotations
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import patch
import torch

import c1_policy as P
import c1_runtime as R
CLI = R.ab.load_module('c1_cli_tests', Path(__file__).with_name('run_cpu.py'))
F = R.ab.load_module('c1_old_fixture', R.HERE.parent/'mech_c/test_c.py')
task = R.ab.load_module('c1_task_tests', R.HERE.parent/'r1b_calibration/task.py')
torch.set_num_threads(1)


class GPTFixture(F.Fixture):
    """Enforce pinned GPT restriction rather than a permissive Parcae signature."""
    def __init__(self):
        super().__init__(); self.calls = []
    def forward(self, tokens, labels=None, return_logits=False):
        self.calls.append((labels is not None, return_logits))
        if labels is not None and return_logits:
            raise UnboundLocalError('outputs')
        out = super().forward(tokens, labels, True, [0, 4])
        if not return_logits: out['logits'] = None
        return out


def tensors():
    x = torch.arange(18).reshape(2, 9) % 10
    y = (x+1) % 10; y[:, :5] = -100
    return x, y


class PolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.allocation, cls.manifest = P.allocate(task)
    def test_01_budget(self):
        result = P.budgets(P.EXPECTED_COUNTS)
        self.assertEqual(result['ceiling_flops'], 355663872000)
        self.assertEqual([result['arms'][a]['steps'] for a in P.ARMS], [4843, 3116, 3000])
        for row in result['arms'].values(): self.assertLessEqual(row['unused_fraction'], .001)
    def test_02_budget_drift(self):
        c = dict(P.EXPECTED_COUNTS); c['C4'] += 1
        with self.assertRaises(RuntimeError): P.budgets(c)
    def test_03_new_seeds(self):
        self.assertEqual(P.SEEDS, (1101, 1202, 1303, 1404, 1505))
        self.assertFalse(set(P.SEEDS) & {42, 101, 202, 303, 404, 505, 20261029, 20261030})
    def test_04_legacy_exclusions_and_new_quota(self):
        self.assertEqual(self.manifest['excluded_legacy'], P.LEGACY_DIGESTS)
        self.assertEqual(self.manifest['excluded_pairs'], 5120)
        self.assertEqual(len(self.allocation), 2048)
        self.assertEqual(len({(a,b) for a,b,c in self.allocation}), 2048)
        for c in range(4): self.assertEqual(sum(x[2] == c for x in self.allocation), 512)
        for a,b,c in self.allocation:
            self.assertLessEqual(a,b)
            self.assertEqual(task.role(a,b), 'reserved')
            self.assertEqual(task.role(b,a), 'reserved')
            self.assertEqual(P.carry_count(a,b), c)
    def test_05_allocate_never_calls_example(self):
        class KeysOnly:
            role = staticmethod(task.role)
            @staticmethod
            def example(*args): raise AssertionError('labels must not be generated')
        self.assertEqual(P.allocate(KeysOnly())[1], self.manifest)
    def test_06_snapshot_endpoint_count(self):
        b=P.budgets(P.EXPECTED_COUNTS)['arms']
        self.assertEqual(sum(len(P.saved_steps(a,b[a]['steps'])) for a in P.ARMS)*5,20)
        self.assertEqual(P.saved_steps('P4',3116),[3000,3116])
        self.assertEqual(P.saved_steps('GPT',4843),[4843])
    def test_07_screen_boundaries(self):
        self.assertEqual(P.screen([.8]*5,[.81]*5)['status'],'PASS')
        self.assertEqual(P.screen([.8]*5,[.84,.84,.84,.84,.79])['status'],'PASS')
        self.assertEqual(P.screen([.8]*5,[.84,.84,.84,.84,.789])['status'],'FAIL')
        self.assertEqual(P.screen([.9901]*5,[1.]*5)['status'],'BLOCKED')
        self.assertEqual(P.screen([.99]*5,[1.]*5)['status'],'PASS')
    def test_08_selection_cannot_hide_GPT_failure(self):
        self.assertEqual(P.selection_status('PASS','FAIL'),'FAIL')
        self.assertEqual(P.selection_status('BLOCKED','FAIL'),'FAIL')
        self.assertEqual(P.selection_status('BLOCKED','PASS'),'BLOCKED')
        self.assertEqual(P.selection_status('PASS','PASS'),'PASS')
    def test_09_invalid_screen(self):
        for x in ([.8]*3,[float('nan')]*5):
            with self.assertRaises(RuntimeError): P.screen(x,[.9]*5)
    def test_10_no_early_depth_conditions(self):
        self.assertEqual(len(P.expected_conditions()),20)
        self.assertEqual({r[3] for r in P.expected_conditions()},{4})
    def test_11_bootstrap_pairing(self):
        x=[[0]*8 for _ in P.SEEDS]; y=[[1]*8 for _ in P.SEEDS];s=[0,0,1,1,2,2,3,3]
        self.assertEqual(P.crossed_bootstrap(x,x,s,50)['interval95'],[0.,0.])
        self.assertEqual(P.crossed_bootstrap(x,y,s,50)['interval95'],[1.,1.])
    def test_12_strict_json(self):
        for raw in (b'{"a":1,"a":2}', b'{"a":NaN}'):
            with self.assertRaises((RuntimeError,ValueError)):P.parse_bytes(raw)
    def test_13_bound_json_uses_same_bytes_once(self):
        class OneRead:
            def __init__(self):self.calls=0
            def read_bytes(self):
                self.calls+=1
                return b'{"v":1}' if self.calls==1 else b'{"v":2}'
        p=OneRead();self.assertEqual(P.bound_json(p,P.digest(b'{"v":1}')),{'v':1});self.assertEqual(p.calls,1)
        with tempfile.TemporaryDirectory() as d:
            q=Path(d)/'test.json';q.write_text('{"v":2}')
            with self.assertRaises(RuntimeError):P.bound_json(q,P.digest(b'{"v":1}'))


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.x,self.y=tensors();self.m2=SimpleNamespace(weights_sha=F.digest)
    def test_14_GPT_loss_one_native_call_and_gradient(self):
        base=GPTFixture();model=R.wrap(base,'GPT',1101)
        torch.manual_seed(9);a=base(self.x,labels=self.y,return_logits=False)
        a['loss'].backward();grads=[None if p.grad is None else p.grad.clone() for p in base.parameters()]
        rng=torch.get_rng_state().clone();base.zero_grad(set_to_none=True);base.calls.clear()
        torch.manual_seed(9);b=model(self.x,self.y);b['loss'].backward()
        self.assertEqual(base.calls,[(True,False)]);self.assertIsNone(b['logits'])
        self.assertTrue(torch.equal(a['loss'],b['loss']));self.assertTrue(torch.equal(rng,torch.get_rng_state()))
        for p,g in zip(base.parameters(),grads):
            self.assertEqual(p.grad is None,g is None)
            if g is not None:self.assertTrue(torch.equal(p.grad,g))
    def test_15_GPT_generation_one_native_call(self):
        base=GPTFixture();model=R.wrap(base,'GPT',1101)
        model(self.x);self.assertEqual(base.calls,[(False,True)])
        with self.assertRaises(RuntimeError):model(self.x,depth=2)
    def test_16_GPT_objective_and_caller_state(self):
        base=GPTFixture().train();before=F.digest(base);rng=torch.get_rng_state().clone()
        result=R.gpt_objective_check(base,self.x,self.y,torch)
        self.assertEqual(result['status'],'PASS');self.assertEqual(result['masked_ce_abs_error'],0.)
        self.assertTrue(base.training);self.assertEqual(F.digest(base),before);self.assertTrue(torch.equal(rng,torch.get_rng_state()))
        self.assertEqual(base.calls,[(True,False),(False,True)])
    def test_17_reuses_original_C4_class(self):
        from c_adapters import LoopLoRA
        model=R.wrap(F.fixture(),'C4',1101)
        self.assertIs(type(model),LoopLoRA);self.assertEqual(model.added_parameters(),2560)
        self.assertEqual(sum(p.numel() for p in model.parameters()),62784)
    def test_18_C4_native_zero_path_fixture(self):
        out=R.native_c_check(F.fixture(),1101,torch,self.m2)
        self.assertEqual(out['status'],'PASS');self.assertEqual(len(out['cases']),4)
        self.assertTrue(all(x['max_base_gradient_abs_error']==0 for x in out['cases']))
    def test_19_probe_preserves_full_state_and_rng(self):
        model=R.wrap(F.fixture(),'C4',1101);before=F.digest(model);rng=torch.get_rng_state().clone()
        out=R.probe(model,self.x,self.y,torch,self.m2)
        self.assertEqual(F.digest(model),before);self.assertTrue(torch.equal(rng,torch.get_rng_state()))
        self.assertGreater(out['step_flops'],out['forward_flops'])
        self.assertTrue(all(p.grad is None for p in model.parameters()))
    def test_20_full_adapter_snapshot_roundtrip(self):
        model=R.wrap(F.fixture(),'C4',1101);opt=torch.optim.AdamW(model.parameters(),lr=.002)
        before=F.digest(model.adapters);model(self.x,self.y)['loss'].backward();opt.step()
        self.assertNotEqual(F.digest(model.adapters),before)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'model.pt';rng=torch.get_rng_state().clone();ix=torch.arange(6).reshape(2,3)
            out=R.state(p,model,opt,rng,ix,{'step':1},torch,self.m2)
            self.assertEqual(out['safe_reload_status'],'PASS');self.assertEqual(out['resume_replay_status'],'NOT TESTED')
            loaded=torch.load(p,weights_only=True,map_location='cpu')
            self.assertTrue(any(k.startswith('adapters.') for k in loaded['model']))
            new=R.wrap(F.fixture(6),'C4',6);new.load_state_dict(loaded['model'],strict=True)
            self.assertEqual(F.digest(model),F.digest(new))
            with self.assertRaises(RuntimeError):R.state(p,model,opt,rng,ix,{'step':1},torch,self.m2)
    def test_21_numeric_failure_separate(self):
        with self.assertRaises(R.NumericalFailure):R.numeric(False,'bad')
        with self.assertRaises(RuntimeError):P.require(False,'instrument')
    def test_22_prompt_only_generation(self):
        class Spy:
            def eval(self):pass
            def __init__(self):self.lengths=[]
            def __call__(self,x,depth):
                self.lengths.append(x.shape[1]);z=torch.zeros(*x.shape,256);z[:,:,255]=1
                return {'logits':z}
        spy=Spy();pred,_=R.ab.generate(spy,[[1,2,3,4,5,6]],1101,4,torch)
        self.assertEqual(spy.lengths,[6,7,8,9]);self.assertEqual(pred,[[255]*4])


class BoundaryTests(unittest.TestCase):
    def test_23_review_required(self):
        args=SimpleNamespace(review_report=None,reviewer=None,review_approved=False)
        with self.assertRaises(RuntimeError):CLI.review_input(args)
    def test_24_complete_training_required_before_targets(self):
        with tempfile.TemporaryDirectory() as d:
            args=SimpleNamespace(out=Path(d))
            with self.assertRaises(RuntimeError):CLI.verify_training(args,{}, {'rows':[]})
            self.assertFalse((Path(d)/'C1T.json').exists())
    def test_25_duplicate_worker_preserves_row_and_logs(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d);job=out/'jobs'/'C4_1101';job.mkdir(parents=True)
            old=b'{"status":"PARTIAL","do_not_change":true}'
            (job/'row.json').write_bytes(old);(job/'train.error.log').write_text('old')
            R.ab.write(out/'training.json',dict(experiment=P.EXPERIMENT,phase='train',status='PARTIAL',review={'real':'supplied'}))
            args=SimpleNamespace(out=out,parcae_dir=Path(d),phase='train',worker='C4',seed=1101)
            with patch.object(CLI,'complete',return_value={}),patch.object(CLI,'source_match'):
                self.assertEqual(CLI.worker(args),2)
            self.assertEqual((job/'row.json').read_bytes(),old)
            self.assertEqual((job/'train.error.log').read_text(),'old')
    def test_26_evaluation_worker_verifies_bytes_before_model(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d);R.ab.write(out/'training.json',{'v':1});R.ab.write(out/'C1T.json',[{'target':[1]}])
            parent=dict(experiment=P.EXPERIMENT,phase='evaluate',status='PARTIAL',source_identity={'x':1},
                        training_summary_sha256=R.ab.file_sha(out/'training.json'),
                        C1T_file_sha256='0'*64,C1T_sha256=P.object_sha([{'target':[1]}]))
            R.ab.write(out/'result.json',parent)
            with self.assertRaisesRegex(RuntimeError,'bound file'):
                CLI.load_worker_truth(SimpleNamespace(out=out),{'source_identity':{'x':1}}, {'status':'PASS'})
    def test_27_existing_cli_report_read_only(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d);p=out/'prepared.json'
            r=dict(experiment=P.EXPERIMENT,phase='prepare',status='BLOCKED',exit_code=2)
            R.ab.write(p,r);before=p.read_bytes()
            with patch.object(sys,'argv',['run_cpu.py','prepare','--out',str(out),'--parcae-dir',d]):
                self.assertEqual(CLI.main(),2)
            self.assertEqual(p.read_bytes(),before)
    def test_28_scoring_rejects_incomplete_conditions(self):
        with self.assertRaises(RuntimeError):P.summarize([],[],task)
    def test_29_gpt_safeguard_not_superiority(self):
        self.assertEqual(P.screen([.9]*5,[.895]*5,False)['status'],'PASS')
        self.assertEqual(P.screen([.9]*5,[.895]*5,True)['status'],'FAIL')


if __name__=='__main__':
    unittest.main(verbosity=2)
