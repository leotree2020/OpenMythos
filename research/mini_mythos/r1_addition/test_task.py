"""Task/software checks only: no native model capability claim."""
import copy
import unittest
import task


class TaskTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = task.make_splits()

    def test_exhaustive_labels(self):
        for a in range(100):
            for b in range(100):
                r = task.example(a,b)
                self.assertEqual(sum(d*10**i for i,d in enumerate(r['target'])), a+b)
                self.assertEqual(r['target'], task.example(b,a)['target'])

    def test_known_carry_classes(self):
        for a,b,c in ((12,23,0),(18,23,1),(58,67,2),(0,0,0),(99,99,2),(6,39,1)):
            self.assertEqual(task.example(a,b)['carry'],c)

    def test_mask_and_shift(self):
        for rows in self.data.values():
            for r in rows:
                x,y = task.training_tokens(r)
                self.assertEqual(len(x),6)
                self.assertEqual(y[:3],[-100]*3)
                self.assertEqual(y[3:],r['target'])
                self.assertEqual(x[:4],r['prompt'])
                self.assertEqual(x[4:],r['target'][:2])

    def test_grouped_splits(self):
        m = task.manifest(self.data)
        self.assertEqual(sum(v['canonical_pairs'] for v in m.values()),5050)
        self.assertEqual(m['train']['examples'],6993)
        self.assertEqual(m['validation']['examples'],756)
        self.assertEqual(m['test']['examples'],760)

    def test_frozen_hashes(self):
        from run_cpu import EXPECTED_DATA
        self.assertEqual({s:v['sha256'] for s,v in task.manifest(self.data).items()},EXPECTED_DATA)
        self.assertEqual(self.data,task.make_splits())

    def test_swap_leak_rejected(self):
        d=copy.deepcopy(self.data)
        r=d['train'][0]
        d['test'].append(task.example(r['b'],r['a']))
        with self.assertRaises(RuntimeError): task.manifest(d)

    def test_exact_and_invalid_scores(self):
        rows=self.data['test']; targets=[r['target'] for r in rows]
        self.assertEqual(task.score(rows,targets)['all']['accuracy'],1.)
        for bad in ([256,0,0],[0,0],[-1,0,0],[True,0,0]):
            s=task.score(rows,[bad]*len(rows))
            self.assertEqual(s['all']['correct'],0)
            self.assertEqual(s['all']['invalid'],len(rows))
        with self.assertRaises(ValueError): task.score(rows,targets[:-1])

    def test_bad_inputs(self):
        for a in (-1,100,0.5,True):
            with self.assertRaises(ValueError): task.example(a,3)

    @staticmethod
    def metrics(overall=.95,easy=.95,mid=.95,hard=.95):
        return {k:{'accuracy':v} for k,v in zip(('all','0','1','2'),(overall,easy,mid,hard))}

    def test_learning_gates(self):
        m=[self.metrics() for _ in range(3)]
        self.assertEqual(task.learning_gate(m,'gpt'),'PASS')
        m[-1]['2']['accuracy']=.89
        self.assertEqual(task.learning_gate(m,'gpt'),'FAIL')
        self.assertEqual(task.learning_gate(m,'parcae'),'PASS')

    def test_primary_positive_and_failure(self):
        a=[self.metrics(hard=.80) for _ in range(3)]
        b=[self.metrics(hard=.86) for _ in range(3)]
        self.assertEqual(task.benefit(a,b)['status'],'PASS')
        b[-1]['2']['accuracy']=.79
        self.assertEqual(task.benefit(a,b)['status'],'FAIL')

    def test_safeguard_does_not_replace_benefit(self):
        a=[self.metrics(hard=.80) for _ in range(3)]
        self.assertEqual(task.benefit(a,a)['status'],'FAIL')
        b=[self.metrics(easy=.90,hard=.90) for _ in range(3)]
        self.assertEqual(task.benefit(a,b)['status'],'FAIL')

    def test_ceiling_is_not_positive_evidence(self):
        a=[self.metrics(hard=.98) for _ in range(3)]
        b=[self.metrics(hard=1.) for _ in range(3)]
        self.assertEqual(task.benefit(a,b)['status'],'BLOCKED')
        self.assertEqual(task.benefit(a,b)['reason'],'CEILING_LIMIT')

    def test_generation_never_receives_truth(self):
        import torch
        from run_cpu import evaluate
        class Spy(torch.nn.Module):
            def __init__(self):
                super().__init__(); self.inputs=[]
            def forward(self,x,labels=None,return_logits=False):
                if labels is not None: raise AssertionError('teacher forcing during evaluation')
                self.inputs.append(x.clone())
                z=torch.zeros((*x.shape,256)); z[:,:,-1]=1.
                return {'logits':z}
        rows=[task.example(12,23),task.example(18,23),task.example(58,67)]
        model=Spy(); r=evaluate(model,'gpt',rows,42,2,torch)
        self.assertEqual([x.shape[1] for x in model.inputs],[4,5,6])
        self.assertEqual(r['predictions'],[[255,255,255]]*3)
        self.assertEqual(r['metrics']['all']['correct'],0)
        self.assertTrue(bool((model.inputs[1][:,4]==255).all()))
        self.assertTrue(bool((model.inputs[2][:,4:]==255).all()))


if __name__=='__main__': unittest.main()
