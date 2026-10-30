"""Small local helper tests; no native GPT/Parcae construction or fake model outcomes."""
import ast
import copy
import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path
import torch
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('init01',HERE/'replay_initialization.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
torch.set_num_threads(1)

class Preparation(unittest.TestCase):
    def rows(self):
        return [dict(seed=s,arm=a,phases={p:{} for p in m.PHASES},
                     matches_historical_initial=True,shared_io_matches=True,saved_state_roundtrip=True)
                for s in m.SEEDS for a in m.ARMS]
    def test_six_pairs_required(self):
        rows=self.rows();self.assertEqual(len(m.index_rows(rows)),6)
        with self.assertRaises(RuntimeError):m.index_rows(rows[:-1])
        with self.assertRaises(RuntimeError):m.index_rows(rows[:-1]+[rows[0]])
    def test_no_partial_success(self):
        rows=self.rows();self.assertEqual(m.classify(rows),'PASS')
        for key in ('matches_historical_initial','shared_io_matches','saved_state_roundtrip'):
            bad=copy.deepcopy(rows);bad[5][key]=False
            self.assertEqual(m.classify(bad),'FAIL')
        del rows[0]['phases']['after_count']
        with self.assertRaises(RuntimeError):m.classify(rows)
    def test_state_hash_sorted_and_buffer_sensitive(self):
        a={'b':torch.arange(4,dtype=torch.float32),'a':torch.ones(2)}
        self.assertEqual(m.state_sha(a),m.state_sha(dict(reversed(list(a.items())))))
        h=hashlib.sha256()
        for name,t in sorted(a.items()):h.update(name.encode());h.update(t.numpy().tobytes())
        self.assertEqual(m.state_sha(a),h.hexdigest())
        b=copy.deepcopy(a);b['b'][0]+=1
        self.assertNotEqual(m.state_sha(a),m.state_sha(b))
    def test_capture_does_not_consume_rng(self):
        model=torch.nn.Linear(3,2);model.register_buffer('buf',torch.ones(2))
        rng=torch.get_rng_state().clone();before=m.capture(torch,model)
        self.assertTrue(torch.equal(rng,torch.get_rng_state()))
        model.buf[0]+=1;after=m.capture(torch,model)
        self.assertEqual(m.changed_names(before,after),['buf'])
    def test_restricted_initial_fixture_roundtrip(self):
        model=torch.nn.Linear(3,2)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'test.pt';state={'model':model.state_dict(),'rng':torch.get_rng_state(),'seed':42}
            torch.save(state,p);loaded=torch.load(p,weights_only=True,map_location='cpu')
            self.assertEqual(m.state_sha(loaded['model']),m.state_sha(state['model']))
            self.assertTrue(torch.equal(loaded['rng'],state['rng']))
    def test_no_training_or_extra_probe_calls(self):
        tree=ast.parse((HERE/'replay_initialization.py').read_text())
        attrs=[n.func.attr for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)]
        self.assertNotIn('step',attrs);self.assertNotIn('AdamW',attrs)
        self.assertNotIn('backward',attrs)
        # The sole backward path is the pinned original count helper, called once in the six-model loop.
        self.assertEqual(attrs.count('count'),1)
        self.assertEqual(attrs.count('preflight'),1)
        self.assertEqual(attrs.count('make'),2)

if __name__=='__main__':unittest.main(verbosity=2)
