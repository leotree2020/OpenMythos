"""M2 matched pilot: configuration calibration and official-model CPU experiment."""
import argparse
import dataclasses
import hashlib
import json
import math
import os
import platform
import subprocess
import sys
import time
import traceback
from pathlib import Path

os.environ['CUDA_VISIBLE_DEVICES'] = ''
import torch
from torch.nn.attention import SDPBackend, sdpa_kernel
from torch.utils.flop_counter import FlopCounterMode

PIN = '69284c13746e849104f738d6d1a347b1f457df76'
TEXT_SHA = '86c4e6aa9db7c042ec79f339dcb96d42b0075e16b8fc2e86bf0ca57e2dc565ed'
HERE = Path(__file__).resolve().parent
SEQ, BATCH, STEPS = 32, 8, 120
COMMON = dict(block_size=SEQ, vocab_size=256, padding_multiple=1, n_embd=32,
              num_attention_heads=4, num_key_value_heads=4, attn_impl='sdpa',
              init_strategy='scaled', norm_class_name='LayerNorm')

def require(condition, message):
    if not condition:
        raise RuntimeError(message)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def tensor_sha(t):
    return sha(t.detach().cpu().contiguous().numpy().tobytes())

def git(path, *args):
    return subprocess.check_output(['git', '-C', str(path), *args], text=True).strip()

def upstream_check(path):
    require(git(path, 'rev-parse', 'HEAD') == PIN, 'wrong upstream pin')
    require(not git(path, 'status', '--porcelain', '--untracked-files=no'), 'dirty upstream')

def setup(path):
    upstream_check(path)
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(path.resolve()))
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)

def make(arm, ffn, seed):
    from parcae_lm.models.gpt import GPT, GPTConfig
    from parcae_lm.models.parcae import Parcae, ParcaeConfig
    torch.manual_seed(seed)
    if arm == 'gpt':
        cfg = GPTConfig(**COMMON, intermediate_size=ffn, n_layer=4, use_fused_head=False)
        return GPT(cfg, gradient_checkpointing=False)
    cfg = ParcaeConfig(**COMMON, intermediate_size=64, use_fused_head='pytorch',
        recurrent_embedding_dimension=32, recurrent_intermediation_embedding_dimension=64,
        n_layers_in_prelude=1, n_layers_in_recurrent_block=1, n_layers_in_coda=1,
        mean_recurrence=2, mean_backprop_depth=2, recurrent_iteration_method='per-batch',
        prelude_norm=True)
    return Parcae(cfg, gradient_checkpointing=False)

def call(m, arm, x, y=None):
    kw = dict(labels=y, return_logits=y is None)
    if arm == 'parcae':
        kw['num_steps_pair'] = [0,2]
    return m(x, **kw)['logits' if y is None else 'loss']

def weights_sha(m):
    h = hashlib.sha256()
    for name, t in sorted(m.state_dict().items()):
        h.update(name.encode())
        h.update(t.detach().contiguous().numpy().tobytes())
    return h.hexdigest()

def count(m, arm):
    # Count only: no optimizer and no natural-language quality computation.
    x = torch.arange(BATCH*SEQ).reshape(BATCH,SEQ) % 256
    y = (x+1) % 256
    with torch.random.fork_rng(devices=[]), sdpa_kernel(SDPBackend.MATH):
        torch.manual_seed(9001)
        with FlopCounterMode(display=False) as fc:
            loss = call(m, arm, x, y)
            forward = fc.get_total_flops()
            loss.backward()
            total = fc.get_total_flops()
    m.zero_grad(set_to_none=True)
    return dict(parameters=sum(p.numel() for p in m.parameters()),
                forward_flops=forward, backward_flops=total-forward, step_flops=total)

def ratio(a,b):
    return max(a,b)/min(a,b)

def calibration(out):
    reference = count(make('parcae',64,9001), 'parcae')
    candidates = []
    for ffn in range(48,81,4):
        r = dict(ffn=ffn, **count(make('gpt',ffn,9001), 'gpt'))
        r['parameter_ratio'] = ratio(r['parameters'], reference['parameters'])
        r['compute_ratio'] = ratio(r['step_flops'], reference['step_flops'])
        r['feasible'] = max(r['parameter_ratio'], r['compute_ratio']) <= 1.10
        candidates.append(r)
    selected = min(candidates, key=lambda r: (max(r['parameter_ratio'],r['compute_ratio']),
        r['parameter_ratio']+r['compute_ratio'],r['ffn']))
    result = dict(status='PASS' if selected['feasible'] else 'FAIL', source_pin=PIN,
        selection='minimax ratios, then ratio sum, then FFN; no quality inspection',
        candidates=candidates, selected=selected, parcae=reference,
        protocol_sha256=sha((HERE/'PROTOCOL.md').read_bytes()),
        environment=dict(python=platform.python_version(),torch=torch.__version__),
        training_status='NOT TESTED during calibration')
    write(out,result)
    require(selected['feasible'], 'no feasible candidate; no training authorized by config')
    print(json.dumps(result,indent=2))

@torch.no_grad()
def pair_io(a,b):
    b.transformer.wte.weight.copy_(a.transformer.wte.weight)
    b.lm_head.weight.copy_(a.lm_head.weight.T)
    b.transformer.ln_f.load_state_dict(a.transformer.ln_f.state_dict())
    require(torch.equal(a.transformer.wte.weight,b.transformer.wte.weight), 'input init')
    require(torch.equal(a.lm_head.weight.T,b.lm_head.weight), 'output init')
    require(a.emb_scale == b.emb_scale and a.config.init.logit_scale == b.config.init.logit_scale,
            'different embedding/logit scales')
    return dict(input_embedding_sha256=tensor_sha(a.transformer.wte.weight),
                output_head_canonical_sha256=tensor_sha(a.lm_head.weight.T),
                embedding_scale=a.emb_scale,logit_scale=a.config.init.logit_scale,
                status='PASS', policy='native_scaled_shared_io_v1')

@torch.no_grad()
def preflight(m,arm):
    m.eval()
    x = torch.arange(2*SEQ).reshape(2,SEQ) % 256
    y = (x+1) % 256
    with torch.random.fork_rng(devices=[]), sdpa_kernel(SDPBackend.MATH):
        torch.manual_seed(100)
        logits = call(m,arm,x)
        torch.manual_seed(100)
        native = call(m,arm,x,y)
        ce = torch.nn.functional.cross_entropy(logits.reshape(-1,256),y.reshape(-1))
        altered = x.clone()
        altered[:,SEQ//2:] = (altered[:,SEQ//2:]+17)%256
        torch.manual_seed(100)
        changed = call(m,arm,altered)
    loss_error = abs(float(native-ce))
    causal_error = float((logits[:,:SEQ//2]-changed[:,:SEQ//2]).abs().max())
    require(logits.shape == (2,SEQ,256), 'wrong output shape')
    require(torch.isfinite(logits).all() and torch.isfinite(native), 'nonfinite preflight')
    require(loss_error <= 1e-6 and causal_error <= 1e-6, 'loss/causality preflight failed')
    return dict(status='PASS',ce_abs_error=loss_error,causal_prefix_abs_error=causal_error)

def window(pool,ids):
    z=pool[ids[:,None]+torch.arange(SEQ+1)]
    return z[:,:-1].contiguous(),z[:,1:].contiguous()

@torch.no_grad()
def evaluate(m,arm,pool,seed):
    m.eval()
    starts=torch.arange(0,len(pool)-SEQ,SEQ)
    total=0.
    with torch.random.fork_rng(devices=[]), sdpa_kernel(SDPBackend.MATH):
        torch.manual_seed(seed)
        for ids in starts.split(32):
            loss=float(call(m,arm,*window(pool,ids)))
            require(math.isfinite(loss),'nonfinite evaluation')
            total+=loss*len(ids)*SEQ
    tokens=len(starts)*SEQ
    return dict(nll=total/tokens,ppl=math.exp(total/tokens),target_tokens=tokens,
                windows=len(starts),discarded_target_tail=len(pool)-1-tokens,
                window_starts_sha256=tensor_sha(starts))

def write(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')

def run(args,result):
    import numpy,einops
    frozen=json.loads(args.config.read_text())
    require(frozen['status']=='PASS' and frozen['source_pin']==PIN,'unaccepted calibration')
    require(frozen['protocol_sha256']==sha((HERE/'PROTOCOL.md').read_bytes()),'protocol changed')
    result.update(config=frozen,config_sha256=sha(args.config.read_bytes()),
        script_sha256=sha(Path(__file__).read_bytes()),source_pin=PIN,
        git_head=git(HERE,'rev-parse','HEAD'),git_status=git(HERE,'status','--porcelain'),
        environment=dict(python=platform.python_version(),torch=torch.__version__,
                         numpy=numpy.__version__,einops=einops.__version__,
                         platform=platform.platform(),device='cpu',threads=1),
        mode='preflight' if args.preflight_only else 'training',rows=[])
    if not args.preflight_only:
        require(sys.version_info[:2]==(3,12) and torch.__version__.split('+')[0]=='2.11.0'
                and numpy.__version__=='1.26.4' and einops.__version__=='0.8.0',
                'formal training requires pinned Linux dependencies')
        require(platform.system()=='Linux','formal training requires Linux')
        raw=args.text.read_bytes()
        require(sha(raw)==TEXT_SHA,'wrong corpus bytes')
        n=len(raw)
        parts=(raw[:int(n*.8)],raw[int(n*.8):int(n*.9)],raw[int(n*.9):])
        pools=[torch.tensor(list(p),dtype=torch.long) for p in parts]
        result['data']=dict(text_sha256=sha(raw),byte_lengths=list(map(len,parts)),
            split_sha256=[sha(p) for p in parts],tokenizer='UTF-8 bytes 0..255',
            split_byte_offsets=[0,int(n*.8),int(n*.9),n])
    ffn=frozen['selected']['ffn']
    for seed in args.seeds:
        models={'gpt':make('gpt',ffn,seed),'parcae':make('parcae',64,seed)}
        io=pair_io(models['gpt'],models['parcae'])
        if not args.preflight_only:
            generator=torch.Generator().manual_seed(seed+11)
            starts=torch.randint(len(pools[0])-SEQ,(STEPS,BATCH),generator=generator)
        for arm,m in models.items():
            row=dict(seed=seed,arm=arm,initialization=io,model_config=dataclasses.asdict(m.config))
            result['rows'].append(row)
            row['preflight']=preflight(m,arm)
            row['counts']=count(m,arm)
            expected=frozen['selected'] if arm=='gpt' else frozen['parcae']
            require(all(row['counts'][k]==expected[k] for k in row['counts']), 'count drift')
            row['initial_weights_sha256']=weights_sha(m)
            if args.preflight_only:
                row['status']='PASS'
                continue
            row['batch_starts_sha256']=tensor_sha(starts)
            row['train_tokens']=STEPS*BATCH*SEQ
            row['train_counted_flops']=row['counts']['step_flops']*STEPS
            row['initial_validation']=evaluate(m,arm,pools[1],1212)
            opt=torch.optim.AdamW(m.parameters(),lr=.002,betas=(.9,.999),eps=1e-8,weight_decay=0.)
            losses,gradients=[],[]
            with torch.random.fork_rng(devices=[]), sdpa_kernel(SDPBackend.MATH):
                torch.manual_seed(seed+2000)
                t0=time.perf_counter()
                for i,ids in enumerate(starts):
                    m.train()
                    opt.zero_grad(set_to_none=True)
                    value=call(m,arm,*window(pools[0],ids))
                    require(torch.isfinite(value),'nonfinite training loss')
                    value.backward()
                    require(all(torch.isfinite(p.grad).all() for p in m.parameters()
                                if p.grad is not None),'nonfinite gradient')
                    gn=float(torch.nn.utils.clip_grad_norm_(m.parameters(),1.))
                    require(math.isfinite(gn),'nonfinite gradient norm')
                    opt.step()
                    losses.append(float(value.detach()))
                    gradients.append(gn)
                row['training_seconds']=time.perf_counter()-t0
            row['loss_trace']=losses
            row['gradient_norm_trace']=gradients
            row['final_validation']=evaluate(m,arm,pools[1],1212)
            row['test']=evaluate(m,arm,pools[2],1313)
            row['final_weights_sha256']=weights_sha(m)
            checkpoint=args.out.parent/f'{arm}_{seed}_weights.pt'
            torch.save(m.state_dict(),checkpoint)
            row['checkpoint_file']=checkpoint.name
            row['checkpoint_sha256']=sha(checkpoint.read_bytes())
            row['status']='PASS' if row['initial_weights_sha256']!=row['final_weights_sha256'] and (
                row['final_validation']['nll']<=row['initial_validation']['nll']-.01) else 'FAIL'
            write(args.out,result)
            print(json.dumps(dict(seed=seed,arm=arm,status=row['status'],
                val_nll=row['final_validation']['nll'],test_nll=row['test']['nll'])),flush=True)
    upstream_check(args.parcae_dir)
    result['execution_status']='PASS' if all(r['status']=='PASS' for r in result['rows']) else 'FAIL'
    if not args.preflight_only:
        comparisons=[]
        for i in range(0,len(result['rows']),2):
            a,b=result['rows'][i:i+2]
            same=a['batch_starts_sha256']==b['batch_starts_sha256'] and a['train_tokens']==b['train_tokens']
            for split in ('final_validation','test'):
                same= same and all(a[split][k]==b[split][k] for k in
                                  ('target_tokens','windows','window_starts_sha256'))
            pr=ratio(a['counts']['parameters'],b['counts']['parameters'])
            cr=ratio(a['train_counted_flops'],b['train_counted_flops'])
            comparisons.append(dict(seed=a['seed'],parameter_ratio=pr,compute_ratio=cr,
                data_equal=same,budget_status='PASS' if same and max(pr,cr)<=1.10 else 'FAIL',
                test_nll_delta_parcae_minus_gpt=b['test']['nll']-a['test']['nll']))
        result['comparisons']=comparisons
        result['budget_status']='PASS' if all(c['budget_status']=='PASS' for c in comparisons) else 'FAIL'
        deltas=[c['test_nll_delta_parcae_minus_gpt'] for c in comparisons]
        result['mean_test_nll_delta']=sum(deltas)/len(deltas)
        result['quality_hypothesis_status']='PASS' if max(deltas)<=.05 and sum(deltas)/len(deltas)<=.02 else 'FAIL'
    result['upstream_tracked_status_after']=git(args.parcae_dir,'status','--porcelain','--untracked-files=no')
    write(args.out,result)
    return 0 if result['execution_status']=='PASS' and result.get('budget_status','PASS')=='PASS' else 1

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--parcae-dir',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--calibrate',action='store_true')
    p.add_argument('--preflight-only',action='store_true')
    p.add_argument('--config',type=Path,default=HERE/'frozen_config.json')
    p.add_argument('--text',type=Path)
    p.add_argument('--seeds',type=int,nargs='+',default=[42,20261029,20261030])
    args=p.parse_args()
    result=dict(experiment='M2_MATCHED_CPU_V1',execution_status='NOT TESTED',
                review_status='NOT TESTED: independent Grok review pending')
    try:
        setup(args.parcae_dir)
        if args.calibrate:
            calibration(args.out)
            return 0
        return run(args,result)
    except Exception:
        result['execution_status']='BLOCKED'
        result['error']=traceback.format_exc()
        write(args.out,result)
        traceback.print_exc()
        return 2

if __name__=='__main__':
    sys.exit(main())
