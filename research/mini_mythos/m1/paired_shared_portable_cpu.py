#!/usr/bin/env python3
"""Mythos CPU paired architecture preflight: identical two-layer computation,
independent weights versus tying the two PyTorch TransformerEncoderLayer instances.
No upstream Parcae changes; does NOT claim native Parcae or matched-quality superiority.
"""
import argparse,copy,hashlib,json,math,platform,time
from pathlib import Path
import torch
from torch import nn
from torch.nn import functional as F
V,P,T=16,4,16
EXPECTED_TRAIN={
 42:'d6c6001e83fc7de49790832c9278b81a1b19487dc83e78a0310fa8b54c2edfc0',
 20261029:'be70e617602830038941487ab72dea8637cbaac6ff2cff9a36e111dcae217c2a',
 20261030:'48d974cdb974655bdfb0b2bbe28b5e0bc499cf2e4e582dd422979eba13e3d712',
}
VAL_HASH='115a92a8f2e7ce361317c508d5c81b2e149d879350fe4cf8648a046b56aa6c11'
TEST_HASH='a3b8a969ad2c2bfa10a53a5b6a90ea245baccefd41e412f344855c2cb5edf07e'

def digest(t):
 return hashlib.sha256(t.detach().cpu().contiguous().numpy().tobytes()).hexdigest()

def weights(m):
 h=hashlib.sha256()
 for n,p in sorted(m.state_dict().items()):
  h.update(n.encode());h.update(p.detach().cpu().contiguous().numpy().tobytes())
 return h.hexdigest()

def sample(codes):
 base=torch.stack([(codes>>(4*i))&15 for i in range(P)],dim=-1)
 seq=base[:,torch.arange(T+1)%P]
 return seq[:,:-1],seq[:,1:]

class LM(nn.Module):
 def __init__(self):
  super().__init__()
  self.token_emb=nn.Embedding(V,32)
  self.position_emb=nn.Embedding(T,32)
  layer=nn.TransformerEncoderLayer(d_model=32,nhead=4,dim_feedforward=64,
                                   batch_first=True,dropout=0.,norm_first=True)
  self.encoder=nn.TransformerEncoder(layer,num_layers=2,enable_nested_tensor=False)
  self.norm=nn.LayerNorm(32)
  self.out=nn.Linear(32,V)
  self.register_buffer('causal_mask',torch.triu(torch.full((T,T),float('-inf')),1),persistent=False)
 def forward(self,x):
  z=self.token_emb(x)+self.position_emb(torch.arange(x.shape[1],device=x.device))
  z=self.encoder(z,mask=self.causal_mask[:x.shape[1],:x.shape[1]],is_causal=True)
  return self.out(self.norm(z))

def loss(m,x,y):
 z=m(x)
 return F.cross_entropy(z[:,P-1:,:].reshape(-1,V),y[:,P-1:].reshape(-1))

@torch.no_grad()
def val_nll(m,codes):
 m.eval();total,n=0.,0
 for part in codes.split(64):
  x,y=sample(part); k=len(part)*(T-P+1)
  total+=float(loss(m,x,y))*k;n+=k
 return total/n

def experiment(seed):
 torch.manual_seed(seed)
 A=LM();B=copy.deepcopy(A)
 B.encoder.layers[1]=B.encoder.layers[0]
 assert B.encoder.layers[0] is B.encoder.layers[1]
 train=torch.tensor([i for i in range(V**P) if i%10<8],dtype=torch.long)
 vp=torch.tensor([i for i in range(V**P) if i%10==8],dtype=torch.long)
 tp=torch.tensor([i for i in range(V**P) if i%10==9],dtype=torch.long)
 g=torch.Generator().manual_seed(1212)
 validation=vp[torch.randperm(len(vp),generator=g)[:1024]]
 testing=tp[torch.randperm(len(tp),generator=g)[:1024]]
 rng=torch.Generator().manual_seed(seed+11)
 batches=[train[torch.randint(0,len(train),(32,),generator=rng)] for _ in range(180)]
 hashes={'train_batch_sha256':digest(torch.cat(batches)),
         'validation_ids_sha256':digest(validation),'test_ids_sha256':digest(testing)}
 if hashes!={'train_batch_sha256':EXPECTED_TRAIN[seed],
             'validation_ids_sha256':VAL_HASH,'test_ids_sha256':TEST_HASH}:
  raise RuntimeError('M1 frozen data identity mismatch')
 x,_=sample(batches[0]);A.eval();B.eval()
 initial_diff=float((A(x)-B(x)).detach().abs().max())
 out=[]
 for name,m in [('independent',A),('shared',B)]:
  opt=torch.optim.AdamW(m.parameters(),lr=.002,weight_decay=0.)
  initial=val_nll(m,validation);first=None;last=None
  start=time.monotonic()
  for ids in batches:
   x,y=sample(ids);m.train();objective=loss(m,x,y)
   if not bool(torch.isfinite(objective)):
    raise RuntimeError('nonfinite loss')
   opt.zero_grad(set_to_none=True);objective.backward()
   grad=float(torch.nn.utils.clip_grad_norm_(m.parameters(),max_norm=1.))
   if not math.isfinite(grad):raise RuntimeError('nonfinite gradient')
   opt.step()
   if first is None:first=float(objective.detach())
   last=float(objective.detach())
  sec=time.monotonic()-start
  final=val_nll(m,validation);heldout=val_nll(m,testing)
  out.append({'name':name,'unique_parameters':sum(p.numel() for p in m.parameters()),
              'initial_validation_nll':initial,'final_validation_nll':final,
              'final_test_nll':heldout,'final_test_ppl':math.exp(heldout),
              'first_train_nll':first,'last_train_nll':last,'train_wall_seconds':sec,
              'final_weights_sha256':weights(m)})
 checks={'identical_initial_logits':initial_diff<=1e-6,
         'same_frozen_batches':True,
         'both_validation_improve_0_05':all(x['final_validation_nll']<=x['initial_validation_nll']-.05 for x in out),
         'tied_fewer_unique_parameters':out[1]['unique_parameters']<out[0]['unique_parameters'],
         'predeclared_absolute_noninferiority_0_05':out[1]['final_validation_nll']<=out[0]['final_validation_nll']+.05}
 return {'seed':seed,'status':'PASS' if all(checks.values()) else 'FAIL',
         'checks':checks,'init_logits_max_abs':initial_diff,'data':hashes,'arms':out}

def main():
 a=argparse.ArgumentParser();a.add_argument('--out',type=Path,required=True);args=a.parse_args()
 args.out.parent.mkdir(parents=True,exist_ok=True)
 torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
 rows=[experiment(s) for s in EXPECTED_TRAIN]
 meanA=sum(r['arms'][0]['final_validation_nll'] for r in rows)/3
 meanB=sum(r['arms'][1]['final_validation_nll'] for r in rows)/3
 summary={'experiment':'MYTHOS-P2-CPU-TIED-LAYERS-001',
          'environment':{'python':platform.python_version(),'torch':torch.__version__,'cpu':True},
          'protocol':'same init, 2 block passes, 180 steps AdamW, identical input batch SHA256, 3 seeds',
          'seeds':rows,'status':'PASS' if all(r['status']=='PASS' for r in rows) else 'FAIL',
          'mean_validation_nll':{'independent':meanA,'shared':meanB},
          'relative_nll_increase':meanB/meanA-1,
          'param_reduction':1-rows[0]['arms'][1]['unique_parameters']/rows[0]['arms'][0]['unique_parameters'],
          'posthoc_stricter_10_percent_nll_equivalence':'NOT MET' if meanB>1.10*meanA else 'MET',
          'limit':['synthetic period-4 data','not native Parcae','no FLOPs profiler or matched-quality superiority']}
 args.out.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'status':summary['status'],'means':summary['mean_validation_nll'],
                   'relative_nll_increase':summary['relative_nll_increase'],
                   'param_reduction':summary['param_reduction'],
                   'negative_observation':summary['posthoc_stricter_10_percent_nll_equivalence']}))
 return 0 if summary['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
