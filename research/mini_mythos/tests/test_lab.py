import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from common import toy_batch, atomic_json
import torch

class PipelineTests(unittest.TestCase):
    def test_shifted_labels(self):
        x,y=toy_batch(torch,2,batch_size=2,seq_len=16)
        self.assertEqual(tuple(x.shape),(2,16))
        self.assertTrue(torch.equal(x[:,1:],y[:,:-1]))
        self.assertTrue((x>=0).all() and (x<96).all())

    def test_deterministic_dataset(self):
        x1,y1=toy_batch(torch,42)
        x2,y2=toy_batch(torch,42)
        self.assertTrue(torch.equal(x1,x2))
        self.assertTrue(torch.equal(y1,y2))

    def test_seed_is_effective(self):
        x1,_=toy_batch(torch,42)
        x2,_=toy_batch(torch,43)
        self.assertFalse(torch.equal(x1,x2))

if __name__=='__main__':
    unittest.main()
