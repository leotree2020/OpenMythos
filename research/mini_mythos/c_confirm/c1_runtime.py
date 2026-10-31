"""Pinned native factory + unchanged C4. No replacement model or upstream patch."""
from __future__ import annotations
import copy
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import time
import c1_policy as P

HERE = Path(__file__).resolve().parent
AB = HERE.parent/'mech_ab'
sys.path.insert(0, str(AB))
sys.path.insert(0, str(HERE.parent/'mech_c'))
spec = importlib.util.spec_from_file_location('c1_existing_ab', AB/'run_cpu.py')
ab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ab)
require = P.require


class NumericalFailure(RuntimeError):
    """Valid model execution became nonfinite: FAIL, not instrument BLOCKED."""


def numeric(ok, message):
    if not ok:
        raise NumericalFailure(message)


def identity():
    own = {p.name: ab.file_sha(p) for p in HERE.iterdir()
           if p.suffix in ('.py', '.sh') or p.name == 'PROTOCOL.md'}
    inherited = {name: ab.file_sha(HERE.parent/name) for name in P.INHERITED}
    require(inherited == P.INHERITED, 'inherited source drift')
    return dict(own=own, inherited=inherited, sha256=P.object_sha(dict(own=own, inherited=inherited)))


def context(upstream):
    torch, env = ab.runtime()
    root = Path(ab.git(HERE, 'rev-parse', '--show-toplevel'))
    require(not ab.git(root, 'status', '--porcelain', '--untracked-files=no'), 'dirty research sources')
    ident = identity()
    m2 = ab.load_module('c1_pinned_factory', HERE.parent/'m2_matched/experiment.py')
    m2.setup(upstream)
    task = ab.load_module('c1_pinned_task', HERE.parent/'r1b_calibration/task.py')
    return torch, env, root, m2, task, ident


def initial(m2, seed, arm):
    gpt, parcae = m2.make('gpt', 60, seed), m2.make('parcae', 64, seed)
    io = m2.pair_io(gpt, parcae)
    base = gpt if arm == 'GPT' else parcae
    return base, io, m2.weights_sha(base)


def wrap(base, arm, seed):
    require(arm in P.ARMS, 'unknown arm')
    if arm != 'GPT':
        from c_adapters import LoopLoRA
        return LoopLoRA(base, arm, seed)
    import torch
    class GPTPath(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.base = base
        def forward(self, tokens, labels=None, depth=4):
            require(type(depth) is int and depth == 4, 'GPT has four native blocks')
            # Preserve fixed GPT's supported split interface and ONE train forward.
            out = self.base(tokens, labels=labels, return_logits=labels is None)
            return dict(logits=out['logits'], loss=out['loss'], final_loss=out['loss'], aux_loss=None)
    return GPTPath()


def gpt_objective_check(base, x, y, torch):
    from mechanisms import answer_ce
    from torch.nn.attention import SDPBackend, sdpa_kernel
    mode = base.training
    try:
        base.eval()
        with torch.no_grad(), torch.random.fork_rng(devices=[]), sdpa_kernel(SDPBackend.MATH):
            torch.manual_seed(9001)
            native = base(x, labels=y, return_logits=False)['loss']
            torch.manual_seed(9001)
            logits = base(x, return_logits=True)['logits']
            error = abs(float(native-answer_ce(logits, y)))
            require(math.isfinite(error) and error <= 1e-6, 'GPT objective mismatch')
        return dict(status='PASS', masked_ce_abs_error=error, scope='no optimizer updates')
    finally:
        base.train(mode)


def native_c_check(base, seed, torch, m2):
    """Zero correction must preserve native logits/loss/base gradients and RNG."""
    from torch.nn.attention import SDPBackend, sdpa_kernel
    original = m2.weights_sha(base)
    cases = []
    with torch.random.fork_rng(devices=[]), sdpa_kernel(SDPBackend.MATH):
        for length in (6, 9):
            x = torch.arange(2*length).reshape(2, length) % 10
            y = (x+1) % 10
            y[:, :5] = -100
            native = copy.deepcopy(base).train()
            torch.manual_seed(9001)
            ref = native(x, labels=y, return_logits=True, num_steps_pair=[0, 4])
            ref['loss'].backward()
            ref_rng = torch.get_rng_state().clone()
            for arm in ('P4', 'C4'):
                rng = torch.get_rng_state().clone()
                model = wrap(copy.deepcopy(base), arm, seed).train()
                require(torch.equal(rng, torch.get_rng_state()), 'adapter construction RNG drift')
                require(model.added_parameters() == (2560 if arm == 'C4' else 0), 'capacity drift')
                torch.manual_seed(9001)
                out = model(x, y, depth=4, trace=True)
                out['loss'].backward()
                torch.testing.assert_close(ref['logits'], out['logits'], rtol=1e-5, atol=1e-6)
                require(abs(float((ref['loss']-out['loss']).detach())) <= 1e-6, 'zero-init loss differs')
                require(torch.equal(ref_rng, torch.get_rng_state()), 'zero-init forward RNG differs')
                errors = []
                for (n, p), (name, q) in zip(native.named_parameters(), model.base.named_parameters()):
                    require(n == name and (p.grad is None) == (q.grad is None), 'gradient name/None mismatch')
                    if p.grad is not None:
                        torch.testing.assert_close(p.grad, q.grad, rtol=1e-5, atol=1e-6)
                        errors.append(float((p.grad-q.grad).abs().max()))
                if arm == 'C4':
                    require(out['route'] == [(name, i, i) for i in range(4)
                            for name in ('attn_out', 'ffn_out')], 'C4 routing differs')
                    for bank in model.adapters.values():
                        require(bank.down.grad is not None and bank.up.grad is not None, 'adapter gradient absent')
                        numeric(bool(torch.isfinite(bank.up.grad).all()), 'nonfinite adapter gradient')
                        require(bool((bank.down.grad == 0).all()) and bool((bank.up.grad != 0).any()), 'zero-up gradient rule')
                core = model.base.transformer.core_block[0]
                require(not core._forward_pre_hooks and not core.attn.c_proj._forward_hooks
                        and not core.mlp.proj._forward_hooks, 'leaked C4 hooks')
                with torch.no_grad():
                    native.eval(); model.eval()
                    torch.manual_seed(9002)
                    a = native(x, return_logits=True, num_steps_pair=[0, 4])['logits']
                    torch.manual_seed(9002)
                    b = model(x, depth=4)['logits']
                    torch.testing.assert_close(a, b, rtol=1e-5, atol=1e-6)
                cases.append(dict(arm=arm, seed=seed, length=length, depth=4, status='PASS',
                                  max_base_gradient_abs_error=max(errors, default=0.)))
    require(m2.weights_sha(base) == original, 'preflight changed original base')
    return dict(status='PASS', cases=cases, scope='native copies; zero optimizer updates')


def probe(model, x, y, torch, m2):
    from torch.nn.attention import SDPBackend, sdpa_kernel
    from torch.utils.flop_counter import FlopCounterMode
    before = m2.weights_sha(model)
    model.train(); model.zero_grad(set_to_none=True)
    with torch.random.fork_rng(devices=[]), sdpa_kernel(SDPBackend.MATH):
        torch.manual_seed(9001)
        with FlopCounterMode(display=False) as fc:
            out = model(x, y, depth=4)
            forward = fc.get_total_flops()
            numeric(bool(torch.isfinite(out['loss'])), 'nonfinite probe loss')
            out['loss'].backward()
            total = fc.get_total_flops()
    numeric(all(bool(torch.isfinite(p.grad).all()) for p in model.parameters() if p.grad is not None), 'probe gradients')
    result = dict(parameters=sum(p.numel() for p in model.parameters()),
                  gradient_participating_parameters_probe=sum(p.numel() for p in model.parameters() if p.grad is not None),
                  forward_flops=forward, backward_flops=total-forward, step_flops=total)
    model.zero_grad(set_to_none=True)
    require(m2.weights_sha(model) == before, 'probe changed full state')
    return result


def encoded(task, rows, torch):
    items = [task.training_tokens(r) for r in rows]
    return (torch.tensor([x for x, y in items], dtype=torch.long),
            torch.tensor([y for x, y in items], dtype=torch.long))


def state(path, model, opt, rng, indices, metadata, torch, m2):
    require(not path.exists(), 'snapshot already exists')
    payload = dict(model=model.state_dict(), optimizer=opt.state_dict(), cpu_rng=rng,
                   batch_indices=indices, metadata=metadata)
    numeric(all(bool(torch.isfinite(t).all()) for t in payload['model'].values()), 'nonfinite saved model')
    # Includes ALL adapter tensors, not only model.base.
    torch.save(payload, path)
    loaded = torch.load(path, map_location='cpu', weights_only=True)
    def equal(a, b):
        if isinstance(a, torch.Tensor):
            return isinstance(b, torch.Tensor) and torch.equal(a, b)
        if isinstance(a, dict):
            return isinstance(b, dict) and a.keys() == b.keys() and all(equal(a[k], b[k]) for k in a)
        if isinstance(a, (list, tuple)):
            return type(a) is type(b) and len(a) == len(b) and all(equal(x, y) for x, y in zip(a, b))
        return a == b
    require(equal(payload, loaded), 'safe-load model/adapter/optimizer/RNG roundtrip differs')
    return dict(file=path.name, sha256=ab.file_sha(path), model_sha256=m2.weights_sha(model),
                base_sha256=m2.weights_sha(model.base), step=metadata['step'],
                safe_reload_status='PASS', resume_replay_status='NOT TESTED')


def train_one(args, prepared):
    from torch.nn.attention import SDPBackend, sdpa_kernel
    torch, env, root, m2, task, ident = context(args.parcae_dir)
    require(ident == prepared['source_identity'], 'source changed after preparation')
    # Parent/worker dispatcher exclusively owns this directory before entry.
    job = args.out/'jobs'/f'{args.arm}_{args.seed}'
    data = P.bound_json(args.out/'train.json', prepared['train_file_sha256'])
    x, y = encoded(task, data, torch)
    base, io, base_sha = initial(m2, args.seed, args.arm)
    model = wrap(base, args.arm, args.seed)
    full_sha = m2.weights_sha(model)
    start = prepared['starts'][str(args.seed)][args.arm]
    require(start == dict(base_sha256=base_sha, full_sha256=full_sha, shared_io=io), 'initial recipe differs')
    plan = prepared['budget']['arms']
    steps = plan[args.arm]['steps']
    max_steps = max(v['steps'] for v in plan.values())
    indices = torch.randint(len(x), (max_steps, P.BATCH),
                            generator=torch.Generator().manual_seed(args.seed+12000))[:steps].clone()
    opt = torch.optim.AdamW(model.parameters(), lr=.002, betas=(.9, .999), eps=1e-8, weight_decay=0.)
    require({id(p) for g in opt.param_groups for p in g['params']} ==
            {id(p) for p in model.parameters()}, 'optimizer omitted adapter or backbone')
    row = dict(arm=args.arm, seed=args.seed, status='PARTIAL', steps=0, planned_steps=steps,
               initial_model_sha256=base_sha, initial_full_state_sha256=full_sha, shared_io=io,
               source_identity=ident['sha256'], environment=env,
               batch_prefix3000_sha256=m2.tensor_sha(indices[:P.REFERENCE_STEPS]),
               batch_indices_sha256=m2.tensor_sha(indices),
               counted_training_flops=steps*plan[args.arm]['step_flops'],
               problem_exposures=steps*P.BATCH, supervised_target_tokens=steps*P.BATCH*4,
               input_token_positions=steps*P.BATCH*9, loss_trace=[], gradient_norm_trace=[],
               rng_before_forward_sha256=[], snapshots={})
    ab.write(job/'row.json', row)
    model.train(); started = time.perf_counter()
    with torch.random.fork_rng(devices=[]), sdpa_kernel(SDPBackend.MATH):
        torch.manual_seed(args.seed+2000)
        for step, ix in enumerate(indices, 1):
            row['rng_before_forward_sha256'].append(m2.tensor_sha(torch.get_rng_state()))
            opt.zero_grad(set_to_none=True)
            out = model(x[ix], y[ix], depth=4)
            numeric(bool(torch.isfinite(out['loss'])), 'nonfinite training loss')
            require(out['aux_loss'] is None, 'no auxiliary objective authorized')
            out['loss'].backward()
            numeric(all(bool(torch.isfinite(p.grad).all()) for p in model.parameters() if p.grad is not None), 'nonfinite gradient')
            norm = float(torch.nn.utils.clip_grad_norm_(model.parameters(), 1.))
            numeric(math.isfinite(norm), 'nonfinite norm')
            opt.step()
            row['steps'] = step
            row['loss_trace'].append(float(out['loss'].detach()))
            row['gradient_norm_trace'].append(norm)
            if step in P.saved_steps(args.arm, steps):
                meta = dict(arm=args.arm, seed=args.seed, step=step,
                            source_identity=ident['sha256'], initial_full_sha256=full_sha,
                            train_sha256=prepared['train_file_sha256'])
                snap = state(job/f'step{step}.pt', model, opt, torch.get_rng_state().clone(), indices, meta, torch, m2)
                snap['file'] = str((job/snap['file']).relative_to(args.out))
                row['snapshots'][str(step)] = snap
            if step % 500 == 0:
                ab.write(job/'row.json', row)
                print(json.dumps(dict(arm=args.arm, seed=args.seed, step=step, objective=row['loss_trace'][-1])), flush=True)
    row.update(status='PASS', final_model_sha256=m2.weights_sha(model), final_base_sha256=m2.weights_sha(base),
               training_seconds_descriptive=time.perf_counter()-started,
               process_high_water_rss_kib=__import__('resource').getrusage(__import__('resource').RUSAGE_SELF).ru_maxrss,
               rss_scope='worker lifetime including imports; not isolated training memory')
    m2.upstream_check(args.parcae_dir)
    require(identity() == ident, 'source changed during training')
    ab.write(job/'row.json', row)
    return row


def evaluate_one(args, prepared, row, truth):
    torch, env, root, m2, task, ident = context(args.parcae_dir)
    require(ident == prepared['source_identity'], 'source changed before scoring')
    base, _, _ = initial(m2, args.seed, args.arm)
    model = wrap(base, args.arm, args.seed)
    points = [('final', row['steps'])] + ([('step3000', P.REFERENCE_STEPS)] if args.arm == 'P4' else [])
    result = []
    for label, step in points:
        snap = row['snapshots'][str(step)]
        path = (args.out/snap['file']).resolve()
        require(path.is_relative_to(args.out) and ab.file_sha(path) == snap['sha256'], 'snapshot identity')
        loaded = torch.load(path, map_location='cpu', weights_only=True)
        expected = dict(arm=args.arm, seed=args.seed, step=step,
                        source_identity=ident['sha256'], initial_full_sha256=row['initial_full_state_sha256'],
                        train_sha256=prepared['train_file_sha256'])
        require(loaded['metadata'] == expected, 'snapshot metadata')
        model.load_state_dict(loaded['model'], strict=True)
        require(m2.weights_sha(model) == snap['model_sha256'], 'full adapter/model digest')
        value = ab.evaluate(model, truth, args.seed, 4, torch, task)
        value.update(arm=args.arm, seed=args.seed, checkpoint=label, step=step, depth=4,
                     checkpoint_sha256=snap['sha256'], scope='C1T; free generation; teacher-forced CE separate')
        result.append(value)
        require(m2.weights_sha(model) == snap['model_sha256'], 'evaluation changed full state')
    m2.upstream_check(args.parcae_dir)
    require(identity() == ident, 'source changed during scoring')
    return result
