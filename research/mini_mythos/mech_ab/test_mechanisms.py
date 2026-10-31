"""Small CPU mathematical/plumbing fixtures; NOT native model acceptance."""
from __future__ import annotations
import copy
from pathlib import Path
from types import SimpleNamespace
import unittest
import torch
from torch import nn
from mechanisms import Mechanism,readout,answer_ce
from metrics import screen,transitions,summarize
from run_cpu import generate

torch.set_num_threads(1)


class Injection(nn.Module):
    def __init__(self):
        super().__init__();self.map=nn.Linear(8,8,bias=False)
    def forward(self,x,e):
        return .7*x+self.map(e)


class Block(nn.Module):
    def __init__(self):
        super().__init__();self.map=nn.Linear(8,8)
    def forward(self,x,freqs,mask,ve=None):
        return .2*x+torch.tanh(self.map(x)+(0 if ve is None else .1*ve))


class Fixture(nn.Module):
    """Affine/tanh test double, deliberately NOT a replacement Transformer."""
    def __init__(self):
        super().__init__()
        self.config=SimpleNamespace(use_fused_head='pytorch',randomize_positions_from=None,
            block_size=32,n_layers_in_prelude=1,n_layers_in_recurrent_block=1,
            logit_softcap=None,init=SimpleNamespace(logit_scale=1.))
        self.gradient_checkpointing=False;self.recurrent_iteration_method='per-batch'
        self.transformer=nn.ModuleDict(dict(wte=nn.Embedding(256,8),adapter=Injection(),
             core_block=nn.ModuleList([Block()]),C=nn.Linear(8,8),
             coda=nn.ModuleList([Block()]),ln_f=nn.LayerNorm(8)))
        self.value_embeds=nn.ModuleDict({'2':nn.Embedding(256,8)})
        self.lm_head=nn.Linear(8,256,bias=False)
        self.unused=nn.Parameter(torch.randn(3))
        self.register_buffer('freqs_cis',torch.zeros(1,32,1,1,2))
        self.fail=False
    def forward(self,tokens,labels=None,return_logits=False,num_steps_pair=None):
        e=self.transformer.wte(tokens);x=torch.randn_like(e)
        for _ in range(num_steps_pair[1]):
            x=self.transformer.adapter(x,e)
            if self.fail:
                raise RuntimeError('deliberate fixture failure')
            x=self.transformer.core_block[0](x,None,None)
        # Independently written suffix, not calling production readout().
        x=self.transformer.C(x)
        x=self.transformer.coda[0](x,None,None,ve=self.value_embeds['2'](tokens))
        logits=self.lm_head(self.transformer.ln_f(x)).float()*self.config.init.logit_scale
        if self.config.logit_softcap is not None:
            c=self.config.logit_softcap;logits=c*torch.tanh(logits/c)
        loss=answer_ce(logits,labels) if labels is not None else None
        return {'loss':loss,'logits':logits if return_logits else None}


def tensors():
    x=torch.arange(18).reshape(2,9)%10;y=(x+1)%10;y[:,:5]=-100
    return x,y


class MechanismTests(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(731);self.base=Fixture();self.x,self.y=tensors()
    def test_disabled_logits_loss_gradients_and_rng(self):
        for depth in (2,4):
            a=copy.deepcopy(self.base);b=Mechanism(copy.deepcopy(self.base))
            torch.manual_seed(42);ra=a(self.x,labels=self.y,return_logits=True,num_steps_pair=[0,depth])
            ra['loss'].backward();rng=torch.get_rng_state().clone()
            torch.manual_seed(42);rb=b(self.x,self.y,depth=depth);rb['loss'].backward()
            self.assertTrue(torch.equal(rng,torch.get_rng_state()))
            self.assertTrue(torch.equal(ra['logits'],rb['logits']))
            self.assertTrue(torch.equal(ra['loss'],rb['loss']))
            for p,q in zip(a.parameters(),b.parameters()):
                self.assertEqual(p.grad is None,q.grad is None)
                if p.grad is not None:self.assertTrue(torch.equal(p.grad,q.grad))
    def test_same_trajectory_auxiliary_and_shared_suffix(self):
        a=Mechanism(copy.deepcopy(self.base),auxiliary=.25)
        torch.manual_seed(42);r=a(self.x,self.y,trace=True)
        self.assertEqual(len(r['states']),4)
        torch.testing.assert_close(readout(a.base,r['states'][-1],self.x),r['logits'])
        torch.manual_seed(42);r2=self.base(self.x,labels=self.y,return_logits=True,num_steps_pair=[0,2])
        torch.testing.assert_close(r['aux_loss'],r2['loss'])
        torch.testing.assert_close(r['loss'],.25*r['aux_loss']+.75*r['final_loss'])
        self.assertEqual(sum(p.numel() for p in self.base.parameters()),sum(p.numel() for p in a.parameters()))
    def test_auxiliary_alone_reaches_core(self):
        a=Mechanism(self.base,auxiliary=.25);r=a(self.x,self.y)
        r['aux_loss'].backward()
        grad=self.base.transformer.core_block[0].map.weight.grad
        self.assertIsNotNone(grad);self.assertGreater(float(grad.abs().sum()),0)
    def test_auxiliary_does_not_change_native_rng_or_logits(self):
        a=Mechanism(copy.deepcopy(self.base),auxiliary=.25)
        torch.manual_seed(42);ra=a(self.x,self.y);rng=torch.get_rng_state().clone()
        torch.manual_seed(42);rb=self.base(self.x,labels=self.y,return_logits=True,num_steps_pair=[0,4])
        self.assertTrue(torch.equal(rng,torch.get_rng_state()))
        self.assertTrue(torch.equal(ra['logits'],rb['logits']))
    def test_damping_is_whole_iteration(self):
        a=Mechanism(copy.deepcopy(self.base),alpha=.5)
        torch.manual_seed(43);actual=a(self.x,self.y,trace=True)
        torch.manual_seed(43);e=self.base.transformer.wte(self.x);h=torch.randn_like(e)
        expected=[]
        for _ in range(4):
            candidate=self.base.transformer.core_block[0](self.base.transformer.adapter(h,e),None,None)
            h=h+.5*(candidate-h);expected.append(h)
        for observed,wanted in zip(actual['states'],expected):self.assertTrue(torch.equal(observed,wanted))
        torch.testing.assert_close(actual['logits'],readout(self.base,h,self.x))
        actual['loss'].backward()
        grads=[p.grad for p in a.base.parameters() if p.grad is not None]
        self.assertTrue(grads and all(bool(torch.isfinite(g).all()) for g in grads))
    def test_hooks_removed_after_success(self):
        model=Mechanism(self.base);model(self.x,self.y)
        self.assertFalse(self.base.transformer.adapter._forward_pre_hooks)
        self.assertFalse(self.base.transformer.core_block[0]._forward_hooks)
        self.assertFalse(model._busy)
    def test_hooks_removed_after_error(self):
        self.base.fail=True;model=Mechanism(self.base)
        with self.assertRaises(RuntimeError):model(self.x,self.y)
        self.assertFalse(self.base.transformer.adapter._forward_pre_hooks)
        self.assertFalse(self.base.transformer.core_block[0]._forward_hooks)
        self.assertFalse(model._busy)
    def test_registered_state_not_mutated(self):
        before={n:t.clone() for n,t in self.base.state_dict().items()}
        Mechanism(self.base,alpha=.5,auxiliary=.25)(self.x,self.y)['loss'].backward()
        self.assertTrue(all(torch.equal(before[n],t) for n,t in self.base.state_dict().items()))
    def test_invalid_settings_and_config_rejected(self):
        for value in (-.1,1.1,float('nan')):
            with self.assertRaises(ValueError):Mechanism(self.base,alpha=value)
        self.base.gradient_checkpointing=True
        with self.assertRaises(ValueError):Mechanism(self.base)
    def test_shape_depth_and_mask_rejected(self):
        m=Mechanism(self.base,auxiliary=.25)
        with self.assertRaises(ValueError):m(self.x,self.y,depth=2)
        with self.assertRaises(ValueError):m(self.x,depth=8)
        with self.assertRaises(ValueError):m(self.x,torch.full_like(self.y,-100))
    def test_softcap_readout(self):
        self.base.config.logit_softcap=2.
        r=Mechanism(self.base)(self.x,self.y,trace=True)
        torch.testing.assert_close(r['logits'],readout(self.base,r['states'][-1],self.x))
    def test_prompt_only_free_generation(self):
        class Spy:
            def __init__(self):self.lengths=[]
            def eval(self):return self
            def __call__(self,x,depth):
                self.lengths.append(x.shape[1])
                if x.shape[1]>6:self_outer.assertTrue(bool((x[:,6:]==255).all()))
                logits=torch.zeros(*x.shape,256);logits[:,:,-1]=1
                return {'logits':logits}
        self_outer=self;spy=Spy()
        pred,_=generate(spy,[[1,2,3,4,5,6]],42,4,torch)
        self.assertEqual(spy.lengths,[6,7,8,9]);self.assertEqual(pred,[[255]*4])
    def test_quality_and_ceiling(self):
        self.assertEqual(screen([.8]*3,[.82]*3)['status'],'PASS')
        self.assertEqual(screen([.8]*3,[.81,.81,.77])['status'],'FAIL')
        self.assertEqual(screen([.999]*3,[.9]*3)['status'],'BLOCKED')
    def test_separate_depth_gate(self):
        self.assertEqual(screen([.8]*3,[.82]*3,easy_delta=[0,0,-.02],strict_each=True)['status'],'FAIL')
        self.assertEqual(screen([.8]*3,[.84,.84,.8],strict_each=True)['status'],'FAIL')
    def test_transition_accounting(self):
        t=[[1],[2],[3],[4]];a=[[1],[8],[3],[9]];b=[[7],[2],[3],[9]]
        r=transitions(t,a,b)
        self.assertEqual((r['wrong_to_right'],r['right_to_wrong'],r['net_correct']),(1,1,0))
    def test_missing_rows_rejected(self):
        with self.assertRaises(ValueError):summarize([])


if __name__=='__main__':unittest.main(verbosity=2)
