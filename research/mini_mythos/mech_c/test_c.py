"""CPU mathematics/plumbing tests with a labelled fixture, NOT native results."""
from __future__ import annotations
import copy
import hashlib
import io
import types
import unittest
import torch
from torch import nn
from torch.nn import functional as F
from c_adapters import LoopLoRA,LowRankBank
from c_metrics import summarize,screen,ARMS,SEEDS

torch.set_num_threads(1)


class FixtureCore(nn.Module):
    def __init__(self):
        super().__init__()
        self.attn=nn.Module();self.attn.c_proj=nn.Linear(32,32,bias=False)
        self.mlp=nn.Module();self.mlp.fc=nn.Linear(32,64,bias=False);self.mlp.proj=nn.Linear(64,32,bias=False)
        self.fail=False
    def forward(self,x):
        x=x+torch.tanh(self.attn.c_proj(x))
        if self.fail:raise RuntimeError('deliberate fixture error')
        return x+self.mlp.proj(torch.tanh(self.mlp.fc(x)))


class Fixture(nn.Module):
    """Affine/tanh recurrence. Padding only exercises fixed-size metadata gates."""
    def __init__(self):
        super().__init__()
        self.config=types.SimpleNamespace(use_fused_head='pytorch',randomize_positions_from=None,block_size=32)
        self.gradient_checkpointing=False;self.recurrent_iteration_method='per-batch'
        self.transformer=nn.Module();self.transformer.wte=nn.Embedding(256,32)
        self.transformer.core_block=nn.ModuleList([FixtureCore()]);self.lm_head=nn.Linear(32,256,bias=False)
        self.unused_padding=nn.Parameter(torch.zeros(60224-sum(p.numel() for p in self.parameters())))
    def forward(self,tokens,labels=None,return_logits=True,num_steps_pair=None):
        e=self.transformer.wte(tokens);h=torch.randn_like(e)*.02
        for _ in range(num_steps_pair[1]):h=self.transformer.core_block[0](h+e*.1)
        logits=self.lm_head(h)
        loss=F.cross_entropy(logits.reshape(-1,256),labels.reshape(-1),ignore_index=-100) if labels is not None else torch.tensor(0.)
        return dict(logits=logits,loss=loss)


def fixture(seed=42):
    torch.manual_seed(seed);return Fixture()


def digest(module):
    return hashlib.sha256(b''.join(n.encode()+t.detach().contiguous().numpy().tobytes()
                                  for n,t in sorted(module.state_dict().items()))).hexdigest()


class Tests(unittest.TestCase):
    def setUp(self):
        self.base=fixture();self.x=torch.arange(18).reshape(2,9)%10
        self.y=(self.x+1)%10;self.y[:,:5]=-100
    def test_01_parameter_counts_and_canonical_init(self):
        s=LoopLoRA(copy.deepcopy(self.base),'S16',42);c=LoopLoRA(copy.deepcopy(self.base),'C4',42)
        self.assertEqual(s.added_parameters(),2560);self.assertEqual(c.added_parameters(),2560)
        for name in s.adapters:
            self.assertTrue(torch.equal(s.adapters[name].down.flatten(),c.adapters[name].down.flatten()))
            self.assertEqual(int(c.adapters[name].up.count_nonzero()),0)
    def test_02_init_does_not_advance_rng(self):
        state=torch.get_rng_state().clone()
        LoopLoRA(self.base,'C4',42)
        self.assertTrue(torch.equal(state,torch.get_rng_state()))
    def test_03_zero_init_native_logits_loss_base_gradients(self):
        for mode in ARMS:
            for depth in (2,4):
                a=copy.deepcopy(self.base);b=LoopLoRA(copy.deepcopy(self.base),mode,42)
                torch.manual_seed(7);r=a(self.x,self.y,num_steps_pair=[0,depth]);r['loss'].backward();rng=torch.get_rng_state()
                torch.manual_seed(7);q=b(self.x,self.y,depth);q['loss'].backward()
                torch.testing.assert_close(r['logits'],q['logits'],rtol=0,atol=0)
                self.assertTrue(torch.equal(rng,torch.get_rng_state()))
                for p,t in zip(a.parameters(),b.base.parameters()):
                    self.assertEqual(p.grad is None,t.grad is None)
                    if p.grad is not None:torch.testing.assert_close(p.grad,t.grad,rtol=0,atol=0)
    def test_04_low_rank_algebra_and_gradient(self):
        bank=LowRankBank(5,3,'C4',torch.Generator().manual_seed(8))
        with torch.no_grad():bank.up.copy_(torch.randn_like(bank.up))
        x=torch.randn(2,5,requires_grad=True)
        a=bank(x,2);b=F.linear(x,bank.up[2]@bank.down[2])
        torch.testing.assert_close(a,b)
        ga=torch.autograd.grad(a.square().sum(),(x,bank.down,bank.up),retain_graph=True)
        gb=torch.autograd.grad(b.square().sum(),(x,bank.down,bank.up))
        for p,q in zip(ga,gb):torch.testing.assert_close(p,q)
    def test_05_phase_selection_nonzero(self):
        bank=LowRankBank(4,4,'C4',torch.Generator().manual_seed(1))
        with torch.no_grad():
            for i in range(4):bank.down[i].copy_(torch.eye(4));bank.up[i].copy_((i+1)*torch.eye(4))
        for i in range(4):torch.testing.assert_close(bank(torch.ones(1,4),i),torch.full((1,4),float(i+1)))
    def test_06_shared_control_identical_each_phase(self):
        b=LowRankBank(5,3,'S16',torch.Generator().manual_seed(4))
        with torch.no_grad():b.up.fill_(.1)
        x=torch.randn(2,5)
        for i in range(1,4):torch.testing.assert_close(b(x,0),b(x,i),rtol=0,atol=0)
    def test_07_routing_and_no_hook_leak(self):
        for mode in ('S16','C4'):
            m=LoopLoRA(copy.deepcopy(self.base),mode,42)
            for d in (2,4):
                out=m(self.x,depth=d,trace=True)
                self.assertEqual(out['route'],[(n,i,i if mode=='C4' else 0) for i in range(d) for n in ('attn_out','ffn_out')])
            self.assertFalse(m.base.transformer.core_block[0]._forward_pre_hooks)
            self.assertFalse(m.base.transformer.core_block[0].attn.c_proj._forward_hooks)
    def test_08_error_cleanup(self):
        m=LoopLoRA(self.base,'C4',42);core=m.base.transformer.core_block[0];core.fail=True
        with self.assertRaisesRegex(RuntimeError,'deliberate'):m(self.x)
        self.assertFalse(m._busy);self.assertFalse(core._forward_pre_hooks);self.assertFalse(core.mlp.proj._forward_hooks)
        core.fail=False;m(self.x)
    def test_09_zero_up_gradient_semantics(self):
        m=LoopLoRA(self.base,'C4',42);m(self.x,self.y)['loss'].backward()
        for b in m.adapters.values():
            self.assertIsNotNone(b.down.grad);self.assertEqual(int(b.down.grad.count_nonzero()),0)
            self.assertGreater(int(b.up.grad.count_nonzero()),0)
    def test_10_optimizer_includes_and_changes_adapters(self):
        m=LoopLoRA(self.base,'S16',42);before=digest(m.adapters)
        opt=torch.optim.AdamW(m.parameters(),lr=.002,weight_decay=0.)
        m(self.x,self.y)['loss'].backward();torch.nn.utils.clip_grad_norm_(m.parameters(),1.);opt.step()
        self.assertNotEqual(digest(m.adapters),before)
        for p in m.adapters.parameters():self.assertIn(p,opt.state)
    def test_11_full_checkpoint_roundtrip(self):
        m=LoopLoRA(self.base,'C4',42)
        opt=torch.optim.AdamW(m.parameters(),lr=.002);m(self.x,self.y)['loss'].backward();opt.step()
        stream=io.BytesIO();torch.save(dict(model=m.state_dict(),optimizer=opt.state_dict()),stream);stream.seek(0)
        saved=torch.load(stream,weights_only=True,map_location='cpu')
        n=LoopLoRA(fixture(99),'C4',99);n.load_state_dict(saved['model'])
        torch.manual_seed(71);a=m(self.x)['logits'];torch.manual_seed(71);b=n(self.x)['logits']
        torch.testing.assert_close(a,b,rtol=0,atol=0);self.assertEqual(digest(m),digest(n))
    def test_12_invalid_inputs(self):
        with self.assertRaises(ValueError):LoopLoRA(self.base,'A+C',42)
        m=LoopLoRA(self.base,'C4',42)
        for d in (0,1,3,8,True):
            with self.assertRaises(ValueError):m(self.x,depth=d)
        with self.assertRaises(ValueError):m(self.x.float())
        with self.assertRaises(ValueError):m(self.x,torch.full_like(self.x,-100))
        with self.assertRaises(ValueError):m(self.x[:0])
    def test_13_base_registered_state_unmodified(self):
        before=digest(self.base);m=LoopLoRA(self.base,'C4',42);m(self.x,self.y)['loss'].backward()
        self.assertEqual(before,digest(self.base))
    def test_14_development_classifier(self):
        self.assertEqual(screen([.8]*3,[.82]*3)['status'],'PASS')
        self.assertEqual(screen([.8]*3,[.95,.8,.78])['status'],'FAIL')
        self.assertEqual(screen([.995]*3,[1.]*3)['status'],'BLOCKED')
        with self.assertRaises(ValueError):screen([.8],[.9])
    def test_15_primary_is_capacity_control_not_native(self):
        rows=[]
        for arm,acc in [('P4',.5),('S16',.95),('C4',.9)]:
            for seed in SEEDS:
                metrics={'all':{'accuracy':acc},'0':{'accuracy':acc}}
                rows.append(dict(arm=arm,seed=seed,status='PASS',development={'2':{'metrics':metrics},'4':{'metrics':metrics}}))
        out=summarize(rows)
        self.assertEqual(out['primary_C4_minus_S16']['status'],'FAIL')
        self.assertEqual(out['secondary_vs_P4']['C4_minus_P4']['status'],'PASS')
        self.assertEqual(out['exit_code'],1)
        with self.assertRaises(ValueError):summarize(rows[:-1])
    def test_16_no_adapter_in_p4(self):
        m=LoopLoRA(self.base,'P4',42)
        self.assertEqual(m.added_parameters(),0)
        self.assertEqual(len(m.adapters),0)
    def test_17_nonzero_up_changes_predictions(self):
        m=LoopLoRA(self.base,'C4',42)
        torch.manual_seed(99);a=m(self.x)['logits']
        with torch.no_grad():m.adapters['attn_out'].up.fill_(.05)
        torch.manual_seed(99);b=m(self.x)['logits']
        self.assertFalse(torch.equal(a,b))
    def test_18_native_gate_fixture_only(self):
        import run_cpu
        m2=types.SimpleNamespace(weights_sha=digest)
        out=run_cpu.native_preflight(self.base,42,torch,m2)
        self.assertEqual(len(out['zero_init_identity_cases']),12)
        self.assertEqual(out['status'],'PASS') # fixture exercise, NOT native compatibility evidence


if __name__=='__main__':unittest.main(verbosity=2)
