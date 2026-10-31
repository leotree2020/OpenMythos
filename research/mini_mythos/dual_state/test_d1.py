"""CPU fixtures and evidence plumbing; NOT native Parcae acceptance."""
from __future__ import annotations
import copy
import hashlib
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
import torch
from torch import nn
import run_cpu as C
import measurements as M
from dual_state import DualState, independent_reference
from mechanisms import answer_ce,readout

torch.set_num_threads(1)


class Injection(nn.Module):
    def __init__(self):
        super().__init__();self.map=nn.Linear(8,8,bias=False)
    def forward(self,h,e):return .7*h+self.map(e)
class Block(nn.Module):
    def __init__(self):
        super().__init__();self.map=nn.Linear(8,8)
    def forward(self,x,freqs,mask,ve=None):return .2*x+torch.tanh(self.map(x))
class Fixture(nn.Module):
    """Pointwise affine/tanh double with native-like interfaces, NOT Transformer."""
    def __init__(self):
        super().__init__()
        self.config=SimpleNamespace(use_fused_head='pytorch',randomize_positions_from=None,
            block_size=32,n_layers_in_prelude=1,n_layers_in_recurrent_block=1,prelude_norm=True,
            n_embd=8,recurrent_embedding_dimension=8,logit_softcap=None,init=SimpleNamespace(logit_scale=1.))
        self.gradient_checkpointing=False;self.recurrent_iteration_method='per-batch';self.emb_scale=1.
        self.transformer=nn.ModuleDict(dict(wte=nn.Embedding(256,8),adapter=Injection(),
            prelude=nn.ModuleList([Block()]),ln_prelude=nn.LayerNorm(8),core_block=nn.ModuleList([Block()]),
            C=nn.Linear(8,8),coda=nn.ModuleList([Block()]),ln_f=nn.LayerNorm(8)))
        self.value_embeds=nn.ModuleDict();self.lm_head=nn.Linear(8,256,bias=False)
        self.register_buffer('freqs_cis',torch.zeros(1,32,1));self.unused=nn.Parameter(torch.ones(3));self.fail=False
    def initialize_state(self,e):return torch.randn_like(e)
    def update_recurrent_state(self,h,e,freqs,mask,step,total):
        h=self.transformer.adapter(h,e)
        if self.fail: raise RuntimeError('injected failure')
        return self.transformer.core_block[0](h,freqs,mask)
    def forward(self,tokens,labels=None,return_logits=False,num_steps_pair=None):
        freqs=self.freqs_cis[:,:tokens.shape[1]]
        e=self.transformer.ln_prelude(self.transformer.prelude[0](self.transformer.wte(tokens),freqs,None))
        h=self.initialize_state(e);n=num_steps_pair[1]
        for k in range(n):h=self.update_recurrent_state(h,e,freqs,None,torch.tensor(k),torch.tensor(n))
        logits=readout(self,h,tokens)
        return dict(logits=logits if return_logits else None,loss=answer_ce(logits,labels) if labels is not None else None)
class GPTFixture(Fixture):
    def forward(self,tokens,labels=None,return_logits=False):
        if labels is not None and return_logits:raise UnboundLocalError('outputs')
        return super().forward(tokens,labels,return_logits,[0,4])

def digest(m):
    h=hashlib.sha256()
    for n,t in sorted(m.state_dict().items()):h.update(n.encode());h.update(t.detach().contiguous().numpy().tobytes())
    return h.hexdigest()

def tensors():
    x=torch.arange(18).reshape(2,9)%10;y=(x+1)%10;y[:,:5]=-100;return x,y


class RoutingTests(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(731);self.base=Fixture();self.x,self.y=tensors()
    def test_p4_exact_native_logits_loss_grad_rng(self):
        ref=copy.deepcopy(self.base);m=DualState(copy.deepcopy(self.base),'P4')
        torch.manual_seed(1);a=ref(self.x,self.y,True,[0,4]);a['loss'].backward();rng=torch.get_rng_state()
        torch.manual_seed(1);b=m(self.x,self.y);b['loss'].backward()
        self.assertTrue(torch.equal(rng,torch.get_rng_state()));self.assertTrue(torch.equal(a['logits'],b['logits']))
        for p,q in zip(ref.parameters(),m.parameters()):
            self.assertEqual(p.grad is None,q.grad is None)
            if p.grad is not None:self.assertTrue(torch.equal(p.grad,q.grad))
    def test_dual_manual_reference_all_paths(self):
        for arm in ('D0','D1'):
            for depth in (2,4):
                ref=copy.deepcopy(self.base);m=DualState(copy.deepcopy(self.base),arm)
                torch.manual_seed(1);a=independent_reference(ref,self.x,self.y,depth,arm);a['loss'].backward();rng=torch.get_rng_state()
                torch.manual_seed(1);b=m(self.x,self.y,depth,True);b['loss'].backward()
                self.assertTrue(torch.equal(rng,torch.get_rng_state()))
                torch.testing.assert_close(a['logits'],b['logits'],rtol=0,atol=0)
                self.assertEqual(b['route'],['work','answer']*(depth//2))
                for p,q in zip(ref.parameters(),m.parameters()):
                    self.assertEqual(p.grad is None,q.grad is None)
                    if p.grad is not None:torch.testing.assert_close(p.grad,q.grad,rtol=0,atol=0)
    def test_state_update_order_and_unmodified_other_slot(self):
        m=DualState(self.base,'D1');v=m(self.x,self.y,trace=True)['states']
        self.assertEqual(len(v),5)
        for i in (1,3):self.assertIs(v[i]['a'],v[i-1]['a'])
        for i in (2,4):self.assertIs(v[i]['z'],v[i-1]['z'])
        # Initial sampled a0 is not a trainable tensor until its first update.
        self.assertTrue(v[1]['z'].requires_grad)
        self.assertFalse(v[1]['a'].requires_grad)
        self.assertTrue(all(r['a'].requires_grad and r['z'].requires_grad for r in v[2:]))
    def test_final_loss_reaches_both_states(self):
        m=DualState(self.base,'D1');o=m(self.x,self.y,trace=True)
        z,a=o['states'][2]['z'],o['states'][2]['a'];g=torch.autograd.grad(o['loss'],(z,a))
        self.assertTrue(all(bool((x!=0).any()) for x in g))
    def test_no_feedback_is_distinct(self):
        a=DualState(copy.deepcopy(self.base),'D0');b=DualState(copy.deepcopy(self.base),'D1')
        torch.manual_seed(1);x=a(self.x)['logits'];torch.manual_seed(1);y=b(self.x)['logits']
        self.assertFalse(torch.equal(x,y))
    def test_no_new_parameters_and_rng_construction(self):
        before=torch.get_rng_state();m=DualState(self.base,'D1')
        self.assertTrue(torch.equal(before,torch.get_rng_state()))
        self.assertEqual(sum(p.numel() for p in self.base.parameters()),sum(p.numel() for p in m.parameters()))
    def test_hooks_cleanup_on_error(self):
        m=DualState(self.base,'D1');self.base.fail=True
        with self.assertRaises(RuntimeError):m(self.x,self.y)
        self.assertFalse(m._busy);self.assertFalse(self.base.transformer.adapter._forward_pre_hooks)
        self.assertFalse(self.base.transformer.core_block[-1]._forward_hooks)
    def test_hooks_cleanup_on_success(self):
        m=DualState(self.base,'D0');m(self.x)
        self.assertFalse(m._busy);self.assertFalse(self.base.transformer.adapter._forward_pre_hooks)
    def test_only_supported_depths_and_shapes(self):
        m=DualState(self.base,'D1')
        for depth in (0,1,3,8,True):
            with self.assertRaises(ValueError):m(self.x,depth=depth)
        with self.assertRaises(ValueError):m(self.x.float())
        with self.assertRaises(ValueError):m(self.x,torch.full_like(self.y,-100))
    def test_unsupported_configuration_blocks(self):
        self.base.config.recurrent_embedding_dimension=4
        with self.assertRaises(ValueError):DualState(self.base,'D1')
    def test_interventions_eval_only(self):
        m=DualState(self.base,'D1')
        with self.assertRaises(ValueError):m(self.x,intervention='zero_z')
        m.eval()
        with self.assertRaises(ValueError):m(self.x,self.y,intervention='zero_a')
    def test_reference_preflight_runs_on_fixture(self):
        result=C.native_check(self.base,2101,torch,SimpleNamespace(weights_sha=digest))
        self.assertEqual(len(result['cases']),12)
        self.assertTrue(all(r['max_gradient_error']==0 for r in result['cases']))
    def test_gpt_split_api(self):
        m=C.wrap(GPTFixture(),'GPT',2101)
        self.assertIsNone(m(self.x,self.y)['logits']);self.assertIsNotNone(m(self.x)['logits'])


class MeasurementTests(unittest.TestCase):
    def setUp(self):torch.manual_seed(3)
    def test_same_prefix_profile(self):
        m=DualState(Fixture(),'D1');raw=digest(m)
        r=M.state_profile(m,[[1,2,3,4,5,6]]*2,2101,torch)
        self.assertEqual(len(r['records']),5);self.assertEqual(digest(m),raw)
        for row in r['records']:
            for k,v in row.items():
                if isinstance(v,list):self.assertTrue(all(__import__('math').isfinite(x) for x in v))
    def test_p4_gap_is_zero_by_definition(self):
        r=M.state_profile(DualState(Fixture(),'P4'),[[1,2,3,4,5,6]],1,torch)
        self.assertTrue(all(v['relative_separation']==[0.] for v in r['records']))
    def test_noop_and_state_reset_sensitivity(self):
        m=DualState(Fixture(),'D1');r=M.sensitivity(m,[[1,2,3,4,5,6]]*2,2101,torch)
        self.assertEqual(r['interventions']['noop']['per_prompt_logit_l2'],[0.,0.])
        for k in ('zero_z','zero_a'):self.assertGreater(sum(r['interventions'][k]['per_prompt_logit_l2']),0.)
    def test_profile_rejects_teacher_forcing_prefix(self):
        with self.assertRaises(ValueError):M.state_profile(DualState(Fixture(),'D1'),[[1]*9],1,torch)
    def test_transitions_include_stable_wrong(self):
        truth=[dict(target=[x]) for x in (1,2,3,4)]
        r=M.transitions(truth,[[1],[0],[3],[0]],[[0],[2],[3],[5]])
        self.assertEqual((r['wrong_to_right'],r['right_to_wrong'],r['stable_correct'],r['stable_wrong'],r['changed_wrong_answer']),(1,1,1,1,1))
    def test_screen_boundaries(self):
        self.assertEqual(M.screen([.03,.01,-.01],[.8]*3)['status'],'PASS')
        self.assertEqual(M.screen([.1,.1,-.011],[.8]*3)['status'],'FAIL')
        self.assertEqual(M.screen([0]*3,[.999]*3)['status'],'BLOCKED')
    def test_summary_never_selects_candidate(self):
        rows=[dict(seed=s,arm=a,depth=d,metrics={'all':{'accuracy':.8}}) for s in M.SEEDS for a in M.ARMS for d in ((4,) if a=='GPT' else (2,4))]
        self.assertEqual(M.summarize(rows)['candidate_selection_status'],'NOT ASSESSED')
        with self.assertRaises(ValueError):M.summarize(rows+rows[:1])
    def test_probe_selection_balanced_fixed(self):
        rows=[dict(carry=c,key=str(c)+':'+str(i)) for c in range(4) for i in range(10)]
        out=M.probe_rows(rows);self.assertEqual(len(out),32);self.assertEqual(out[8]['key'],'1:0')
    def test_json_strict_and_single_buffer_hash(self):
        for raw in (b'{"a":1,"a":2}',b'{"a":NaN}'):
            with self.assertRaises((ValueError,RuntimeError)):C.parse(raw)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'data.json';p.write_text('{"a":1}')
            prepared={'data_file_sha256':C.sha(p.read_bytes())};args=SimpleNamespace(out=Path(d))
            self.assertEqual(C.data_bytes(args,prepared),{'a':1})
            p.write_text('{"a":2}')
            with self.assertRaises(RuntimeError):C.data_bytes(args,prepared)
    def test_full_snapshot_and_wrong_metadata_visible(self):
        m=DualState(Fixture(),'D1');opt=torch.optim.AdamW(m.parameters());x,y=tensors()
        m(x,y)['loss'].backward();opt.step()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'step1.pt';meta={'step':1,'arm':'D1'}
            r=C.R.state(p,m,opt,torch.get_rng_state(),torch.tensor([[0]]),meta,torch,SimpleNamespace(weights_sha=digest))
            self.assertEqual(r['safe_reload_status'],'PASS')
            self.assertEqual(torch.load(p,weights_only=True)['metadata'],meta)
    def test_duplicate_worker_keeps_old_row_and_log(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);job=root/'jobs'/'D1_2101';job.mkdir(parents=True)
            (job/'row.json').write_text('old');(job/'error.log').write_text('oldlog')
            (root/'training.json').write_text('{"phase":"train","status":"PARTIAL"}')
            argv=['run_cpu.py','train','--worker','--arm','D1','--seed','2101','--out',d,'--parcae-dir',d]
            with patch.object(C,'preparation',return_value={}),patch.object(sys,'argv',argv):
                self.assertEqual(C.main(),2)
            self.assertEqual((job/'row.json').read_text(),'old');self.assertEqual((job/'error.log').read_text(),'oldlog')
    def test_generation_no_teacher_prefix(self):
        class Spy:
            def __init__(self):self.lengths=[]
            def eval(self):return self
            def __call__(self,x,depth):
                self.lengths.append(x.shape[1]);logits=torch.zeros(*x.shape,256);logits[:,:,2]=1
                if x.shape[1]>6:assert bool((x[:,6:]==2).all())
                return {'logits':logits}
        spy=Spy();pred,_=C.ab.generate(spy,[[1,2,3,4,5,6]],1,4,torch)
        self.assertEqual(pred,[[2]*4]);self.assertEqual(spy.lengths,[6,7,8,9])


import sys
if __name__=='__main__':unittest.main(verbosity=2)
