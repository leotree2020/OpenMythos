"""Preparation checks, not native GPT/Parcae experiment outcomes."""
from __future__ import annotations
import contextlib
import copy
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import task
import run_cpu


def metrics(overall=.85, easy=.95, hard=.75):
    return {'all':{'accuracy':overall}, '0':{'accuracy':easy},
            '1':{'accuracy':.80}, '2':{'accuracy':.80}, '3':{'accuracy':hard}}


class TaskTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = task.make_data()

    def test_all_canonical_labels_and_symmetry(self):
        count=0
        for a in range(100,1000):
            for b in range(a,1000):
                digits,carry=task.column_add(a,b)
                self.assertEqual(sum(d*10**i for i,d in enumerate(digits)),a+b)
                self.assertEqual((digits,carry),task.column_add(b,a))
                self.assertIn(carry,range(4));count+=1
        self.assertEqual(count,405450)

    def test_bad_domains(self):
        for a,b in ((99,100),(100,1000),(True,100),(100.0,200)):
            with self.assertRaises(ValueError):task.example(a,b)

    def test_example_and_mask(self):
        r=task.example(578,677)
        self.assertEqual(r['prompt'],[5,7,8,6,7,7])
        self.assertEqual(r['target'],[5,5,2,1]);self.assertEqual(r['carry'],3)
        x,y=task.training_tokens(r)
        self.assertEqual(x,r['prompt']+r['target'][:-1])
        self.assertEqual(y,[-100]*5+r['target']);self.assertEqual(len(x),len(y))

    def test_split_counts_and_identities(self):
        m=task.manifest(self.data)
        self.assertEqual(m['train']['examples'],19977)
        self.assertEqual(m['train']['canonical_pairs'],10000)
        self.assertEqual(m['development']['examples'],1024)
        self.assertEqual(m['development']['carry_counts'],dict.fromkeys('0123',256))
        self.assertEqual({s:v['sha256'] for s,v in m.items()},run_cpu.EXPECTED_DATA)

    def test_swapped_pair_isolation_and_old_task_exclusion(self):
        a={r['key'] for r in self.data['train']};b={r['key'] for r in self.data['development']}
        self.assertFalse(a&b)
        for split,rows in self.data.items():
            for r in rows:
                self.assertEqual(task.role(r['a'],r['b']),split)
                self.assertEqual(task.role(r['b'],r['a']),split)
                self.assertGreaterEqual(min(r['a'],r['b']),100)

    def test_train_both_orders_and_dev_deterministic_order(self):
        ordered={(r['a'],r['b']) for r in self.data['train']}
        for a,b in ordered:self.assertIn((b,a),ordered)
        for r in self.data['development']:
            a,b=sorted((r['a'],r['b']))
            odd=hashlib.sha256(f'MYTHOS-R1B-ORDER-V1:{a}:{b}'.encode()).digest()[0]&1
            self.assertEqual((r['a'],r['b']),(b,a) if odd else (a,b))

    def test_no_final_split_and_reject_extra(self):
        self.assertEqual(set(self.data),{'train','development'})
        with self.assertRaises(ValueError):task.manifest(dict(self.data,test=[]))

    def test_correct_and_invalid_scoring(self):
        rows=[self.data['development'][c*256] for c in range(4)]
        p=[r['target'][:] for r in rows]
        self.assertEqual(task.score(rows,p)['all']['accuracy'],1)
        p[0]=[256,0,0,0];p[1]=[True,0,0,0];p[2]=[1,2,3]
        s=task.score(rows,p)
        self.assertEqual(s['all']['invalid'],3);self.assertEqual(s['all']['correct'],1)

    def test_missing_predictions_or_stratum_rejected(self):
        with self.assertRaises(ValueError):task.score([],[])
        with self.assertRaises(ValueError):task.score(self.data['development'],[])
        row=self.data['development'][0]
        with self.assertRaises(ValueError):task.score([row],[row['target']])

    def test_learning_floors(self):
        m=[metrics(overall=.8,easy=.9,hard=.6) for _ in task.SEEDS]
        self.assertEqual(task.learning_gate(m),'PASS')
        m[1]['3']['accuracy']=.599999
        self.assertEqual(task.learning_gate(m),'FAIL')

    def test_baseline_failure_does_not_promote_parcae(self):
        g=[metrics(overall=.79) for _ in task.SEEDS]
        q=task.qualify(g,None)
        self.assertEqual(q['task_qualification_status'],'FAIL')
        self.assertEqual(q['parcae_learning_status'],'NOT TESTED')
        self.assertEqual(q['reason'],'GPT_NOT_LEARNED_AT_FIXED_BUDGET')

    def test_parcae_learning_failure(self):
        q=task.qualify([metrics()]*3,[metrics(easy=.89)]*3)
        self.assertEqual(q['task_qualification_status'],'FAIL')
        self.assertEqual(q['reason'],'PARCAE_NOT_LEARNED_AT_FIXED_BUDGET')

    def test_headroom_exact_boundary(self):
        q=task.qualify([metrics()]*3,[metrics(hard=.9)]*3)
        self.assertEqual(q['task_qualification_status'],'PASS')
        self.assertEqual(q['final_test_status'],'NOT TESTED')
        self.assertEqual(q['extra_depth_benefit_status'],'NOT TESTED')

    def test_one_ceiling_seed_blocks_without_changing_old_gate(self):
        p=[metrics(hard=.75),metrics(hard=.90),metrics(hard=.900001)]
        q=task.qualify([metrics()]*3,p)
        self.assertEqual(q['task_qualification_status'],'BLOCKED')
        self.assertEqual(q['parcae_learning_status'],'PASS')
        self.assertEqual(q['reason'],'DEVELOPMENT_CEILING')

    def test_incomplete_seed_records_rejected(self):
        with self.assertRaises(ValueError):task.learning_gate([metrics()]*2)
        with self.assertRaises(ValueError):task.qualify([metrics()]*3,None)

    def test_free_generation_uses_only_prompt_then_own_output(self):
        import torch
        class Spy:
            def __init__(self):self.inputs=[]
            def eval(self):return self
            def __call__(self,x,**kw):
                self.inputs.append(x.clone())
                assert kw=={'labels':None,'return_logits':True,'num_steps_pair':[0,2]}
                logits=torch.zeros((*x.shape,256));logits[:,:,-1]=1
                return {'logits':logits}
        spy=Spy();prompts=[r['prompt'] for r in self.data['development'][:2]]
        pred,_=run_cpu.generate(spy,'parcae',prompts,42,torch)
        self.assertEqual(pred,[[255]*4]*2)
        self.assertEqual([x.shape[1] for x in spy.inputs],[6,7,8,9])
        self.assertEqual(spy.inputs[0].tolist(),prompts)
        for x in spy.inputs[1:]:self.assertTrue(bool((x[:,6:]==255).all()))

    def test_existing_result_bytes_unchanged(self):
        for status,code in (('PASS',0),('FAIL',1),('BLOCKED',2)):
            with tempfile.TemporaryDirectory() as d:
                p=Path(d)/'result.json'
                r={'experiment':task.EXPERIMENT,'execution_status':'PASS',
                   'qualification':{'task_qualification_status':status},'exit_code':code}
                p.write_text(json.dumps(r));before=p.read_bytes()
                with contextlib.redirect_stdout(io.StringIO()):self.assertEqual(run_cpu.read_existing(p),code)
                self.assertEqual(p.read_bytes(),before)

    def test_partial_or_other_task_not_reused(self):
        for r in ({'experiment':'OTHER'}, {'experiment':task.EXPERIMENT,'execution_status':'NOT TESTED'}):
            with tempfile.TemporaryDirectory() as d:
                p=Path(d)/'result.json';p.write_text(json.dumps(r))
                with self.assertRaises(RuntimeError):run_cpu.read_existing(p)


if __name__=='__main__':unittest.main()
