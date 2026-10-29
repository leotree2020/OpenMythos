#!/usr/bin/env python3
"""M1 CPU learning, standard PyTorch A vs untouched pinned native Parcae B.
Synthetic periodic task only; NOT a compute-matched superiority experiment.
"""
import argparse
import hashlib
import json
import math
import os
import platform
import resource
import subprocess
import sys
import time
from pathlib import Path
import torch
from torch import nn
from torch.nn import functional as F

PIN="69284c13746e849104f738d6d1a347b1f457df76"
V, PERIOD, T = 16, 4, 16
FULL = V ** PERIOD
TRAIN=torch.tensor([i for i in range(FULL) if i % 10 < 8],dtype=torch.long)
VAL=torch.tensor([i for i in range(FULL) if i % 10 == 8],dtype=torch.long)
TEST=torch.tensor([i for i in range(FULL) if i % 10 == 9],dtype=torch.long)
# Frozen from the original 2026-10-29 M1-A CPU experiments.
TRAIN_HASH={
  42:"d6c6001e83fc7de49790832c9278b81a1b19487dc83e78a0310fa8b54c2edfc0",
  20261029:"be70e617602830038941487ab72dea8637cbaac6ff2cff9a36e111dcae217c2a",
  20261030:"48d974cdb974655bdfb0b2bbe28b5e0bc499cf2e4e582dd422979eba13e3d712"}
VAL_HASH="115a92a8f2e7ce361317c508d5c81b2e149d879350fe4cf8648a046b56aa6c11"
TEST_HASH="a3b8a969ad2c2bfa10a53a5b6a90ea245baccefd41e412f344855c2cb5edf07e"

def digest(x):
    return hashlib.sha256(x.detach().cpu().contiguous().numpy().tobytes()).hexdigest()

def weight_hash(m):
    h=hashlib.sha256()
    for name,t in sorted(m.state_dict().items()):
        h.update(name.encode())
        h.update(t.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()

def samples(codes):
    base=torch.stack([(codes >> (4*j)) & 15 for j in range(PERIOD)],dim=-1)
    whole=base[:,torch.arange(T+1)%PERIOD]
    return whole[:,:-1],whole[:,1:]

class StandardLM(nn.Module):
    # Exactly the original M1-A architecture, no newly designed baseline.
    def __init__(self):
        super().__init__()
        self.token_emb=nn.Embedding(V,32)
        self.position_emb=nn.Embedding(T,32)
        layer=nn.TransformerEncoderLayer(d_model=32,nhead=4,dim_feedforward=64,
                                         batch_first=True,dropout=0.,norm_first=True)
        self.encoder=nn.TransformerEncoder(layer,num_layers=2,enable_nested_tensor=False)
        self.norm=nn.LayerNorm(32)
        self.out=nn.Linear(32,V)
        self.register_buffer("causal_mask",torch.triu(torch.full((T,T),float("-inf")),1),
                             persistent=False)
    def forward(self,input_ids):
        pos=torch.arange(input_ids.shape[1],device=input_ids.device)
        x=self.token_emb(input_ids)+self.position_emb(pos)
        x=self.encoder(x,mask=self.causal_mask[:x.shape[1],:x.shape[1]],is_causal=True)
        return self.out(self.norm(x))

def pinned_native(path):
    if not path:
        raise RuntimeError("Parcae path missing; cannot substitute a toy")
    path=Path(path).resolve()
    def git(*a):
        return subprocess.check_output(["git","-C",str(path),*a],text=True).strip()
    head=git("rev-parse","HEAD")
    if head!=PIN:
        raise RuntimeError("WRONG PARCAE COMMIT: "+head)
    if git("status","--porcelain","--untracked-files=no"):
        raise RuntimeError("Modified upstream tracked files")
    sys.dont_write_bytecode=True
    sys.path.insert(0,str(path))
    from parcae_lm.models.parcae import Parcae,ParcaeConfig
    cfg=ParcaeConfig.from_name(
        "parcae-small-140m",block_size=T,vocab_size=V,padding_multiple=16,
        n_embd=32,intermediate_size=64,num_attention_heads=4,num_key_value_heads=4,
        recurrent_embedding_dimension=32,recurrent_intermediation_embedding_dimension=64,
        n_layers_in_prelude=1,n_layers_in_recurrent_block=1,n_layers_in_coda=1,
        mean_recurrence=2,mean_backprop_depth=2,
        recurrent_iteration_method="per-batch",attn_impl="sdpa",use_fused_head="pytorch",
        prelude_norm=True)
    return Parcae(cfg,gradient_checkpointing=False)

def loss(m,arm,x,y):
    if arm=="standard":
        z=m(x)
        return F.cross_entropy(z[:,PERIOD-1:,:].reshape(-1,V),
                               y[:,PERIOD-1:].reshape(-1))
    labels=y.clone()
    labels[:,:PERIOD-1]=-100
    return m(x,labels=labels,return_logits=False,num_steps_pair=[0,2])["loss"]

@torch.no_grad()
def evaluate(model,arm,pool):
    model.eval()
    total,count=0.,0
    for codes in pool.split(64):
        x,y=samples(codes)
        value=float(loss(model,arm,x,y))
        if not math.isfinite(value):
            raise RuntimeError("Nonfinite validation loss")
        num=codes.numel()*(T-PERIOD+1)
        total+=value*num
        count+=num
    return total/count

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--arm",choices=["standard","parcae"],required=True)
    a.add_argument("--parcae-dir")
    a.add_argument("--seed",type=int,default=42)
    a.add_argument("--steps",type=int,default=180)
    a.add_argument("--batch",type=int,default=32)
    a.add_argument("--out",type=Path,required=True)
    args=a.parse_args()
    if args.steps<=0 or args.batch<=0: raise ValueError("positive steps/batch required")
    args.out.parent.mkdir(parents=True,exist_ok=True)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.manual_seed(args.seed)
    sampler=torch.Generator().manual_seed(args.seed+11)
    eg=torch.Generator().manual_seed(1212)
    val=VAL[torch.randperm(len(VAL),generator=eg)[:1024]]
    test=TEST[torch.randperm(len(TEST),generator=eg)[:1024]]
    assert set(val.tolist()).isdisjoint(TRAIN.tolist())
    assert set(test.tolist()).isdisjoint(TRAIN.tolist())
    assert set(test.tolist()).isdisjoint(val.tolist())
    if digest(val)!=VAL_HASH or digest(test)!=TEST_HASH:
        raise RuntimeError("Frozen validation/test identity mismatch")
    m=StandardLM() if args.arm=="standard" else pinned_native(args.parcae_dir)
    opt=torch.optim.AdamW(m.parameters(),lr=.002,weight_decay=0.)
    start=weight_hash(m)
    initial=evaluate(m,args.arm,val)
    losses=[]
    train_ids=[]
    t0=time.monotonic()
    for i in range(args.steps):
        picked=torch.randint(0,len(TRAIN),(args.batch,),generator=sampler)
        ids=TRAIN[picked]
        train_ids.append(ids)
        x,y=samples(ids)
        m.train()
        value=loss(m,args.arm,x,y)
        if not bool(torch.isfinite(value)):
            raise RuntimeError("Nonfinite train loss "+str(i))
        opt.zero_grad(set_to_none=True)
        value.backward()
        gn=float(torch.nn.utils.clip_grad_norm_(m.parameters(),max_norm=1.))
        if not math.isfinite(gn):
            raise RuntimeError("Nonfinite gradient "+str(i))
        opt.step()
        losses.append(float(value.detach()))
        if (i+1)%30==0:
            print("PROGRESS",args.arm,args.seed,i+1,"train_nll",round(losses[-1],5),flush=True)
    elapsed=time.monotonic()-t0
    identity=digest(torch.cat(train_ids))
    if args.steps==180 and args.batch==32 and identity!=TRAIN_HASH[args.seed]:
        raise RuntimeError("Frozen train batches mismatch: "+identity)
    final=evaluate(m,args.arm,val)
    heldout=evaluate(m,args.arm,test)
    finish=weight_hash(m)
    status="PASS" if final<=initial-.05 and finish!=start else "FAIL"
    result={
        "experiment":"MYTHOS-M1-CPU-"+args.arm.upper()+"-001",
        "status":status,"arm":args.arm,
        "source":"official Parcae @ "+PIN if args.arm=="parcae" else "torch.nn.TransformerEncoderLayer",
        "environment":{"python":platform.python_version(),"torch":torch.__version__,
                       "cpu":True,"threads":torch.get_num_threads()},
        "config":{"seed":args.seed,"steps":args.steps,"batch":args.batch,
                  "sequence_length":T,"vocab":V,"period":PERIOD,
                  "optimizer":"AdamW","lr":.002,"weight_decay":0.,
                  "native_pair":[0,2] if args.arm=="parcae" else None,
                  "parcae_core_repeats":2 if args.arm=="parcae" else None},
        "data":{"train_batch_codes_sha256":identity,"val_ids_sha256":digest(val),
                "test_ids_sha256":digest(test),"zero_split_overlap":True},
        "model":{"params":sum(p.numel() for p in m.parameters()),
                 "initial_weights_sha256":start,"final_weights_sha256":finish},
        "observed":{"initial_val_nll":initial,"final_val_nll":final,
                    "final_test_nll":heldout,"initial_val_ppl":math.exp(initial),
                    "final_val_ppl":math.exp(final),"final_test_ppl":math.exp(heldout),
                    "first_10_train_loss":losses[:10],"last_10_train_loss":losses[-10:],
                    "training_s":elapsed,"maxrss_kib":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                    "flops":"NOT MEASURED"},
        "criteria":{"validation_nll_decrease_min":.05,"weights_updated":True,
                    "finite_loss_grad":True,"identical_dataset_seeds":True},
        "limitations":["synthetic periodic sequences, not natural language",
                       "Parcae prelude + 2 core passes + coda = 4 block passes vs standard 2 independent blocks",
                       "RoPE vs absolute position encoding and other architecture differences",
                       "NOT matched FLOPs/parameter count; this tests learning feasibility only",
                       "NOT official scripts/train.py or MuonAdamW/GPU"]}
    args.out.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"arm":args.arm,"seed":args.seed,"status":status,
                      "initial_val_nll":initial,"final_val_nll":final,
                      "test_nll":heldout,"params":result["model"]["params"],
                      "train_ids_sha":identity,"training_s":elapsed}),flush=True)
    return 0 if status=="PASS" else 1

if __name__=="__main__":
    sys.exit(main())
