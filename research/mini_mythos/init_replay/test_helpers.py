"""Tests of diagnostic mechanics only: no upstream imports or native model runs."""
import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest
import torch
spec = importlib.util.spec_from_file_location('replay', Path(__file__).with_name('run_init_replay.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def rows():
    return [dict(seed=s,arm=a,native_sequence_completed=True,history_match=True,
                 shared_io_match=True,counts_match=True,preflight_match=True,
                 probe_state_preserved=True,probe_rng_preserved=True,
                 pairing_scope_ok=True,all_stored_tensors_finite=True)
            for s in m.SEEDS for a in m.ARMS]

class Helpers(unittest.TestCase):
    def test_complete_success(self):
        v=m.classify(rows())
        self.assertEqual(v['comparison_status'],'PASS')
        self.assertTrue(v['reviewer_mismatch_root_cause'].startswith('OPEN'))
    def test_hash_mismatch_is_fail(self):
        r=rows();r[2]['history_match']=False
        self.assertEqual(m.classify(r)['historical_init_status'],'FAIL')
        self.assertEqual(m.classify(r)['comparison_status'],'FAIL')
    def test_probe_mutation_is_fail(self):
        r=rows();r[1]['probe_rng_preserved']=False
        self.assertEqual(m.classify(r)['probe_preservation_status'],'FAIL')
    def test_duplicate_and_missing(self):
        for r in (rows()[:-1],rows()[:-1]+[rows()[0]]):
            with self.assertRaises(RuntimeError):m.classify(r)
    def test_historical_disagreement(self):
        a={'rows':[dict(seed=r['seed'],arm=r['arm'],init_sha='a',shared_io_initialization={},counts={}) for r in rows()]}
        b={'rows':[dict(seed=r['seed'],arm=r['arm'],initial_weights_sha256='a',initialization={},counts={}) for r in rows()]}
        self.assertEqual(len(m.references(a,b)),6)
        b['rows'][1]['initial_weights_sha256']='b'
        with self.assertRaises(RuntimeError):m.references(a,b)
    def test_hash_includes_buffers_and_exact_change(self):
        model=torch.nn.Linear(2,3,bias=False)
        model.register_buffer('probe',torch.tensor([1.0]))
        x=m.snapshot(model,torch)
        h=hashlib.sha256()
        for name,t in sorted(model.state_dict().items()):
            h.update(name.encode());h.update(t.detach().contiguous().numpy().tobytes())
        self.assertEqual(h.hexdigest(),x['whole_state_sha256'])
        model.probe.add_(1)
        self.assertEqual(m.changed(x,m.snapshot(model,torch)),['probe'])
    def test_no_optimizer_or_training_loop_calls(self):
        tree=ast.parse(Path(m.__file__).read_text())
        calls={n.func.attr for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)}
        self.assertFalse(calls & {'step','AdamW','evaluate','window','load_state_dict'})
        self.assertIn('preflight',calls);self.assertIn('count',calls)
    def test_paired_scope_limit(self):
        r=rows();r[0]['pairing_scope_ok']=False
        self.assertEqual(m.classify(r)['comparison_status'],'FAIL')

if __name__=='__main__': unittest.main(verbosity=2)
