"""Bounded MES-specific CPU tests. Fixture training never counts as native evidence."""
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
from types import SimpleNamespace
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import torch

import mes_policy as P
import mes_runtime as R
# Import the new CLI by a distinct name; inherited tests import their own run_cpu.
spec=importlib.util.spec_from_file_location('mes_cli',Path(__file__).with_name('run_cpu.py'))
CLI=importlib.util.module_from_spec(spec);spec.loader.exec_module(CLI)
old=sys.modules.get('run_cpu');sys.modules['run_cpu']=R.ab
spec=importlib.util.spec_from_file_location('old_math_fixture',R.AB/'test_mechanisms.py')
F=importlib.util.module_from_spec(spec);spec.loader.exec_module(F)
if old is None: del sys.modules['run_cpu']
else: sys.modules['run_cpu']=old
task=R.ab.load_module('mes_test_task',R.HERE.parent/'r1b_calibration/task.py')
torch.set_num_threads(1)


def weights(m):
    h=hashlib.sha256()
    for name,t in sorted(m.state_dict().items()): h.update(name.encode());h.update(t.detach().contiguous().numpy().tobytes())
    return h.hexdigest()


class GPTFixture(F.Fixture):
    """Enforce the actual pinned GPT interface instead of Parcae's richer return path."""
    def forward(self,tokens,labels=None,return_logits=False):
        if labels is not None and return_logits:
            raise UnboundLocalError("cannot access local variable 'outputs' where it is not associated with a value")
        return super().forward(tokens,labels,return_logits,[0,4])


class PolicyTests(unittest.TestCase):
    def test_exact_budget(self):
        b=P.budgets(P.EXPECTED_COUNTS)
        self.assertEqual([b['arms'][a]['steps'] for a in P.ARMS],[5941,5433,3822,3000])
        self.assertEqual(b['ceiling_flops'],436285440000)
        for v in b['arms'].values():self.assertLessEqual(v['unused_fraction'],.001)
    def test_count_drift_blocks(self):
        c=dict(P.EXPECTED_COUNTS);c['A']+=1
        with self.assertRaises(RuntimeError): P.budgets(c)
    def test_seed_scope(self):
        self.assertEqual(P.SEEDS,(101,202,303,404,505))
        self.assertFalse(set(P.SEEDS)&{42,20261029,20261030})
    def test_carry_count(self):
        for a in (100,109,499,578,999):
            for b in range(100,1000):self.assertEqual(P.carry_count(a,b),task.column_add(a,b)[1])
    def test_reserved_partition(self):
        a,m=P.allocate(task)
        self.assertEqual({k:len(v) for k,v in a.items()},{'H1':2048,'HC':1024,'H2':2048})
        keys=[]
        for name,rows in a.items():
            self.assertEqual(m[name]['allocation_sha256'],P.object_sha(rows))
            for x,y,c in rows:
                self.assertEqual(task.role(x,y),'reserved');self.assertEqual(task.role(y,x),'reserved')
                self.assertEqual(c,P.carry_count(x,y));keys.append((x,y))
        self.assertEqual(len(keys),len(set(keys)))
        self.assertEqual(P.allocate(task)[1],m)
    def test_h1_only_materialized(self):
        a=next((x,y) for x in range(100,110) for y in range(x,120) if task.role(x,y)=='reserved')
        class Spy:
            role=staticmethod(task.role)
            def __init__(self): self.calls=[]
            def example(self,x,y):self.calls.append((x,y));return task.example(x,y)
        spy=Spy();v=P.h1_examples(spy,{'H1':[[*a,P.carry_count(*a)]],'HC':'DO NOT READ','H2':'DO NOT READ'})
        self.assertEqual(len(spy.calls),1);self.assertEqual(len(v),1)
    def test_main_screen_and_per_seed_regression(self):
        self.assertEqual(P.screen([.8]*5,[.82]*5)['status'],'PASS')
        self.assertEqual(P.screen([.8]*5,[.99,.82,.82,.82,.78])['status'],'FAIL')
    def test_ceiling_not_success(self):
        self.assertEqual(P.screen([.999]*5,[1]*5)['status'],'BLOCKED')
    def test_safeguard_not_superiority(self):
        self.assertEqual(P.screen([.8]*5,[.795]*5,False)['status'],'PASS')
        self.assertEqual(P.screen([.8]*5,[.795]*5,True)['status'],'FAIL')
    def test_bad_pairing(self):
        with self.assertRaises(RuntimeError): P.screen([.8]*3,[.9]*3)
        with self.assertRaises(RuntimeError): P.screen([.8]*5,[math.nan]*5)
    def test_paired_bootstrap_identity_and_fixed_difference(self):
        x=[[0]*8 for _ in P.SEEDS];s=[0,0,1,1,2,2,3,3]
        self.assertEqual(P.crossed_bootstrap(x,x,s,100)['interval95'],[0.,0.])
        y=[[1]*8 for _ in P.SEEDS]
        self.assertEqual(P.crossed_bootstrap(x,y,s,100)['interval95'],[1.,1.])
        self.assertEqual(P.crossed_bootstrap(x,y,s,100),P.crossed_bootstrap(x,y,s,100))
    def test_incomplete_evaluations_rejected(self):
        with self.assertRaises(RuntimeError): P.summarize([],[])


class RuntimeTests(unittest.TestCase):
    def test_P2_matches_native(self):
        torch.manual_seed(77);base=F.Fixture();x,y=F.tensors()
        torch.manual_seed(88);a=base(x,labels=y,return_logits=True,num_steps_pair=[0,2]);a['loss'].backward()
        grads=[None if p.grad is None else p.grad.clone() for p in base.parameters()];rng=torch.get_rng_state().clone()
        base.zero_grad(set_to_none=True);torch.manual_seed(88)
        b=R.wrap(base,'P2')(x,y,depth=2);b['loss'].backward()
        self.assertTrue(torch.equal(a['logits'],b['logits']));self.assertTrue(torch.equal(rng,torch.get_rng_state()))
        for before,p in zip(grads,base.parameters()):
            self.assertEqual(before is None,p.grad is None)
            if before is not None:self.assertTrue(torch.equal(before,p.grad))
    def test_GPT_route(self):
        base=GPTFixture();x,y=F.tensors();model=R.wrap(base,'GPT')
        torch.manual_seed(90);a=base(x,labels=y,return_logits=False)
        torch.manual_seed(90);b=model(x,y,depth=4)
        self.assertTrue(torch.equal(a['loss'],b['loss']));self.assertIsNone(b['aux_loss'])
        with self.assertRaises(RuntimeError):model(x,depth=2)
    def test_GPT_pinned_joint_request_is_rejected(self):
        base=GPTFixture();x,y=F.tensors()
        with self.assertRaises(UnboundLocalError):base(x,labels=y,return_logits=True)
    def test_GPT_training_single_call_and_exact_gradients(self):
        base=GPTFixture();reference=copy.deepcopy(base);x,y=F.tensors()
        torch.manual_seed(9001)
        expected=reference(x,labels=y,return_logits=False);expected['loss'].backward()
        rng=torch.get_rng_state().clone()
        torch.manual_seed(9001)
        with patch.object(base,'forward',wraps=base.forward) as calls:
            actual=R.wrap(base,'GPT')(x,y,depth=4);actual['loss'].backward()
            self.assertEqual(calls.call_count,1)
            self.assertFalse(calls.call_args.kwargs['return_logits'])
        self.assertIsNone(actual['logits'])
        self.assertTrue(torch.equal(actual['loss'],expected['loss']))
        self.assertTrue(torch.equal(rng,torch.get_rng_state()))
        for a,b in zip(base.parameters(),reference.parameters()):
            self.assertEqual(a.grad is None,b.grad is None)
            if a.grad is not None:self.assertTrue(torch.equal(a.grad,b.grad))
    def test_GPT_inference_single_call_returns_logits(self):
        base=GPTFixture();x,_=F.tensors()
        torch.manual_seed(55);expected=base(x,return_logits=True)
        torch.manual_seed(55)
        with patch.object(base,'forward',wraps=base.forward) as calls:
            actual=R.wrap(base,'GPT')(x,depth=4)
            self.assertEqual(calls.call_count,1)
            self.assertIsNone(calls.call_args.kwargs['labels'])
            self.assertTrue(calls.call_args.kwargs['return_logits'])
        self.assertTrue(torch.equal(actual['logits'],expected['logits']))
    def test_GPT_objective_check_preserves_rng_mode_weights(self):
        base=GPTFixture().train();x,y=F.tensors()
        before=weights(base);rng=torch.get_rng_state().clone()
        with patch.object(base,'forward',wraps=base.forward) as calls:
            report=R.gpt_objective_check(base,x,y,torch)
            self.assertEqual(calls.call_count,2)
            self.assertFalse(calls.call_args_list[0].kwargs['return_logits'])
            self.assertNotIn('labels',calls.call_args_list[1].kwargs)
        self.assertEqual(report['status'],'PASS');self.assertEqual(report['masked_ce_abs_error'],0.)
        self.assertEqual(before,weights(base));self.assertTrue(base.training)
        self.assertTrue(torch.equal(rng,torch.get_rng_state()))
        self.assertTrue(all(p.grad is None for p in base.parameters()))
    def test_GPT_objective_check_restores_on_error(self):
        base=GPTFixture().train();x,y=F.tensors();rng=torch.get_rng_state().clone()
        with patch.object(base,'forward',side_effect=ValueError('controlled failure')):
            with self.assertRaises(ValueError):R.gpt_objective_check(base,x,y,torch)
        self.assertTrue(base.training);self.assertTrue(torch.equal(rng,torch.get_rng_state()))
    def test_GPT_probe_matches_native_single_forward_cost(self):
        from torch.utils.flop_counter import FlopCounterMode
        base=GPTFixture();x,y=F.tensors();reference=copy.deepcopy(base)
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(9001)
            with FlopCounterMode(display=False) as counter:
                loss=reference(x,labels=y,return_logits=False)['loss']
                forward=counter.get_total_flops();loss.backward();total=counter.get_total_flops()
        actual=R.probe(R.wrap(base,'GPT'),x,y,4,torch,SimpleNamespace(weights_sha=weights))
        self.assertEqual(actual['forward_flops'],forward);self.assertEqual(actual['step_flops'],total)

    def test_prepare_reaches_all_arms_with_strict_GPT_interface(self):
        def make(arm,ffn,seed):
            torch.manual_seed(seed)
            return GPTFixture() if arm=='gpt' else F.Fixture()
        factory=SimpleNamespace(make=make,pair_io=lambda a,b:{'fixture_only':True},
                                weights_sha=weights,upstream_check=lambda p:None)
        data={'train':[task.example(a,b) for a,b in [(100,100),(109,101),(199,101),(999,101)]]}
        ident={'fixture_only':True}
        seen=[]
        def budget(counts):
            seen.append(set(counts))
            return {'fixture_only':True}
        with tempfile.TemporaryDirectory() as td:
            args=SimpleNamespace(out=Path(td),parcae_dir=Path(td))
            context=(torch,{'fixture_only':True},Path(td),factory,task,ident)
            with patch.object(R,'context',return_value=context),patch.object(R,'identity',return_value=ident),\
                 patch.object(R.ab,'git',return_value='FIXTURE_ONLY'),\
                 patch.object(R.ab,'check_data',return_value=(data,{'fixture_only':True})),\
                 patch.object(P,'allocate',return_value=({}, {'fixture_only':True})),\
                 patch.object(P,'budgets',side_effect=budget),\
                 patch.object(CLI.subprocess,'check_output',return_value='fixture-only\n'),\
                 patch.object(torch.optim,'AdamW',side_effect=AssertionError('prepare must not train')):
                report={};CLI.prepare(args,report)
            self.assertEqual(report['status'],'PASS')
            self.assertEqual(len(report['starts']),5);self.assertEqual(len(seen),5)
            self.assertTrue(all(x==set(P.ARMS) for x in seen))
            self.assertEqual(len(report['gpt_objective_checks']),5)
            self.assertTrue(all(x['masked_ce_abs_error']==0 for x in report['gpt_objective_checks']))
            self.assertEqual(report['training_status'],'NOT TESTED')
            self.assertFalse((args.out/'H1.json').exists());self.assertFalse((args.out/'jobs').exists())

    def test_A_formula_and_rng(self):
        base=F.Fixture();x,y=F.tensors()
        torch.manual_seed(91);a=R.wrap(base,'A')(x,y);rng=torch.get_rng_state().clone()
        torch.manual_seed(91);b=R.wrap(base,'P4')(x,y)
        self.assertTrue(torch.equal(rng,torch.get_rng_state()))
        self.assertTrue(torch.equal(a['logits'],b['logits']))
        torch.testing.assert_close(a['loss'],.25*a['aux_loss']+.75*a['final_loss'])
    def test_probe_preserves_state_and_rng(self):
        base=F.Fixture();model=R.wrap(base,'A');x,y=F.tensors()
        rng=torch.get_rng_state().clone();before=weights(base)
        c=R.probe(model,x,y,4,torch,SimpleNamespace(weights_sha=weights))
        self.assertTrue(torch.equal(rng,torch.get_rng_state()));self.assertEqual(weights(base),before)
        self.assertGreater(c['step_flops'],c['forward_flops'])
    def test_snapshot_optimizer_rng_roundtrip(self):
        base=F.Fixture();opt=torch.optim.AdamW(base.parameters(),lr=.002);x,y=F.tensors()
        R.wrap(base,'A')(x,y)['loss'].backward();opt.step()
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'state.pt';rng=torch.get_rng_state().clone();ix=torch.arange(8).reshape(2,4)
            r=R.state(p,base,opt,rng,ix,{'step':1},torch,SimpleNamespace(weights_sha=weights))
            self.assertEqual(r['safe_reload_status'],'PASS')
            self.assertEqual(r['resume_replay_status'],'NOT TESTED')
            with self.assertRaises(RuntimeError):R.state(p,base,opt,rng,ix,{'step':1},torch,SimpleNamespace(weights_sha=weights))
    def test_numeric_failure_distinct(self):
        with self.assertRaises(R.NumericalFailure): R.numeric(False,'bad model')
    def test_prompt_only_GPT_generation(self):
        class Spy:
            def eval(self):pass
            def __init__(self):self.lengths=[]
            def __call__(self,x,depth):
                self.lengths.append(x.shape[1]);z=torch.zeros(*x.shape,256);z[:,:,255]=1
                return {'logits':z}
        model=Spy();pred,_=R.ab.generate(model,[[1,2,3,4,5,6]],101,4,torch)
        self.assertEqual(model.lengths,[6,7,8,9]);self.assertEqual(pred,[[255]*4])
    def test_review_not_fabricated(self):
        args=SimpleNamespace(review_report=None,review_approved=False,reviewer=None)
        with self.assertRaises(RuntimeError):CLI.review_input(args)
    def test_h1_barrier_before_all_training(self):
        with tempfile.TemporaryDirectory() as td:
            args=SimpleNamespace(out=Path(td))
            with self.assertRaises(RuntimeError):CLI.verify_training(args,{}, {'rows':[]})
            self.assertFalse((Path(td)/'H1.json').exists())
    def test_strict_json(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'x.json'
            for bad in ('{"x":1,"x":2}','{"x":NaN}'):
                p.write_text(bad)
                with self.assertRaises((RuntimeError,ValueError)):CLI.read(p)


if __name__=='__main__':unittest.main(verbosity=2)
