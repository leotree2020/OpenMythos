"""M2 pilot: untouched official GPT and Parcae, common byte-level text LM."""
import argparse
import hashlib
import json
import math
import platform
import subprocess
import sys
import time
from pathlib import Path

import torch
from torch.nn.attention import SDPBackend, sdpa_kernel
from torch.utils.flop_counter import FlopCounterMode

PIN = '69284c13746e849104f738d6d1a347b1f457df76'

def sha(b):
    return hashlib.sha256(b).hexdigest()

def git(path, *args):
    return subprocess.check_output(['git', '-C', str(path), *args], text=True).strip()

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--parcae-dir', type=Path, required=True)
    p.add_argument('--text', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--steps', type=int, default=120)
    p.add_argument('--seeds', type=int, nargs='+', default=[42, 20261029, 20261030])
    a = p.parse_args()
    if a.steps < 1:
        raise ValueError('steps must be positive')
    upstream = a.parcae_dir.resolve()
    assert git(upstream, 'rev-parse', 'HEAD') == PIN
    assert not git(upstream, 'status', '--porcelain', '--untracked-files=no')
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(upstream))
    from parcae_lm.models.gpt import GPT, GPTConfig
    from parcae_lm.models.parcae import Parcae, ParcaeConfig
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    raw = a.text.read_bytes()
    # Split contiguous raw bytes BEFORE constructing windows. No boundary crossing.
    n = len(raw)
    pools = [torch.tensor(list(b), dtype=torch.long) for b in
             (raw[:int(n*.8)], raw[int(n*.8):int(n*.9)], raw[int(n*.9):])]
    assert min(map(len, pools)) > 65, 'need >650 bytes'
    batch, seq = 8, 32
    common = dict(block_size=seq, vocab_size=256, padding_multiple=1,
                  n_embd=32, intermediate_size=64, num_attention_heads=4,
                  num_key_value_heads=4, attn_impl='sdpa', use_fused_head='pytorch',
                  init_strategy='scaled', norm_class_name='LayerNorm')
    criteria = dict(finite_losses_and_gradients=True, weights_updated=True,
                    val_nll_decrease_min=.01, train_tokens_equal=True,
                    compute_ratio_max=1.10, parameter_ratio_max=1.10)
    result = dict(experiment='M2_CPU_TEXT_PILOT', source_pin=PIN,
                  purpose='learning and fairness pilot, no superiority claim',
                  environment=dict(python=platform.python_version(), torch=torch.__version__,
                                   platform=platform.platform(), threads=1, device='cpu'),
                  text_sha256=sha(raw), tokenizer='UTF-8 bytes, ids 0..255; no trained vocabulary',
                  split_sha256=[sha(t.numpy().tobytes()) for t in pools],
                  criteria=criteria, rows=[], comparisons=[],
                  limitations=['small corpus and model, pilot only',
                    'native scaled initialization retained; GPTInit and ParcaeInit differ',
                    'parameter sharing prevents simultaneous exact compute/parameter matching',
                    'FLOPs count supported PyTorch operators, excludes optimizer and scalar ops',
                    'held-out byte intervals may contain repeated phrases; no semantic deduplication',
                    'Grok review pending; M1 archive not independently audited'])
    for seed in a.seeds:
        g = torch.Generator().manual_seed(seed+11)
        starts = torch.randint(len(pools[0])-seq, (a.steps, batch), generator=g)
        def window(pool, ids):
            z = pool[ids[:, None]+torch.arange(seq+1)]
            return z[:, :-1].contiguous(), z[:, 1:].contiguous()
        eval_batches = [window(pool, torch.arange(0, min(len(pool)-seq, 512), seq))
                        for pool in pools[1:]]
        for arm in ('gpt_compute', 'gpt_params', 'parcae'):
            torch.manual_seed(seed)
            if arm == 'parcae':
                cfg = ParcaeConfig(**common, recurrent_embedding_dimension=32,
                    recurrent_intermediation_embedding_dimension=64,
                    n_layers_in_prelude=1, n_layers_in_recurrent_block=1,
                    n_layers_in_coda=1, mean_recurrence=2, mean_backprop_depth=2,
                    recurrent_iteration_method='per-batch', prelude_norm=True)
                m = Parcae(cfg, gradient_checkpointing=False)
            else:
                # Official GPT uses a boolean branch here; 'pytorch' is truthy
                # and selects its optional fused kernel. False selects its native CE.
                cfg = GPTConfig(**dict(common, use_fused_head=False),
                                n_layer=4 if arm=='gpt_compute' else 3)
                m = GPT(cfg, gradient_checkpointing=False)
            def loss(x, y):
                kw = dict(labels=y, return_logits=False)
                if arm == 'parcae':
                    kw['num_steps_pair'] = [0, 2]
                return m(x, **kw)['loss']
            def weights():
                return sha(b''.join(t.detach().contiguous().numpy().tobytes()
                                   for t in m.parameters()))
            @torch.no_grad()
            def evaluate(pair):
                m.eval()
                return float(loss(*pair))
            # Force math SDPA in both arms so attention matmuls are counted.
            with sdpa_kernel(SDPBackend.MATH):
                initial = evaluate(eval_batches[0])
                before = weights()
                rng = torch.get_rng_state()
                m.train()
                with FlopCounterMode(display=False) as counter:
                    loss(*window(pools[0], starts[0])).backward()
                step_flops = counter.get_total_flops()
                m.zero_grad(set_to_none=True)
                torch.set_rng_state(rng)
                opt = torch.optim.AdamW(m.parameters(), lr=.002, betas=(.9,.999),
                                       eps=1e-8, weight_decay=0.)
                t0 = time.perf_counter()
                for ids in starts:
                    m.train()
                    opt.zero_grad(set_to_none=True)
                    value = loss(*window(pools[0], ids))
                    assert torch.isfinite(value)
                    value.backward()
                    gn = torch.nn.utils.clip_grad_norm_(m.parameters(), 1.)
                    assert torch.isfinite(gn)
                    opt.step()
                seconds = time.perf_counter()-t0
                final = evaluate(eval_batches[0])
                test = evaluate(eval_batches[1])
            updated = weights() != before
            row = dict(seed=seed, arm=arm, parameters=sum(t.numel() for t in m.parameters()),
                       initial_val_nll=initial, final_val_nll=final, test_nll=test,
                       test_ppl=math.exp(test), training_s=seconds,
                       train_tokens=a.steps*batch*seq, step_forward_backward_flops=step_flops,
                       train_flops=a.steps*step_flops, batches_sha256=sha(starts.numpy().tobytes()),
                       initial_weights_sha256=before, final_weights_sha256=weights(),
                       optimizer='AdamW lr=.002 betas=(.9,.999) eps=1e-8 wd=0 clip=1',
                       status='PASS' if updated and final <= initial-.01 else 'FAIL')
            result['rows'].append(row)
            print(json.dumps(row), flush=True)
        rows = result['rows'][-3:]
        b = rows[-1]
        for r in rows[:-1]:
            ratio = lambda key: max(r[key], b[key])/min(r[key], b[key])
            result['comparisons'].append(dict(seed=seed, baseline=r['arm'],
                compute_ratio=ratio('train_flops'), parameter_ratio=ratio('parameters'),
                compute_matched=ratio('train_flops')<=1.10,
                parameters_matched=ratio('parameters')<=1.10,
                equal_data_tokens=r['batches_sha256']==b['batches_sha256'] and
                                  r['train_tokens']==b['train_tokens']))
    assert not git(upstream, 'status', '--porcelain', '--untracked-files=no')
    result['execution_status'] = 'PASS' if all(r['status']=='PASS' for r in result['rows']) else 'FAIL'
    result['fairness_status'] = 'PASS' if all(c['equal_data_tokens'] and
        c['compute_matched'] and c['parameters_matched'] for c in result['comparisons']) else 'FAIL'
    result['review_status'] = 'NOT TESTED: independent Grok review pending'
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')

if __name__ == '__main__':
    main()
