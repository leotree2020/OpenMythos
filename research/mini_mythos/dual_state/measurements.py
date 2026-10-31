"""Descriptive development-only measurement definitions; no candidate selection."""
from __future__ import annotations
import math

ARMS = ('GPT', 'P4', 'D0', 'D1')
SEEDS = (2101, 2202, 2303)
STEPS, BATCH = 3000, 32
POINTS = (300, 1500, 3000)
EXPERIMENT = 'MYTHOS-D1-DUAL-STATE-PROFILE-V1'


def probe_rows(rows):
    groups = [[r for r in rows if r['carry'] == c][:8] for c in range(4)]
    if any(len(g) != 8 for g in groups):
        raise ValueError('requires eight development questions per stratum')
    return [r for g in groups for r in g]


def transitions(truth, early, final):
    if not (len(truth) == len(early) == len(final)) or not truth:
        raise ValueError('unpaired predictions')
    r = dict(wrong_to_right=0, right_to_wrong=0, stable_correct=0, stable_wrong=0,
             changed_wrong_answer=0)
    for t, p, q in zip(truth, early, final):
        x, y = p == t['target'], q == t['target']
        name = 'stable_correct' if x and y else 'right_to_wrong' if x else 'wrong_to_right' if y else 'stable_wrong'
        r[name] += 1
        r['changed_wrong_answer'] += int(not x and not y and p != q)
    r['net_correct'] = r['wrong_to_right'] - r['right_to_wrong']
    r['scope'] = 'two free-generation policies; not in-place editing of one full answer'
    return r


def screen(deltas, reference):
    if len(deltas) != len(SEEDS) or len(reference) != len(SEEDS):
        raise ValueError('three paired seeds required')
    if not all(math.isfinite(x) for x in deltas+reference):
        raise ValueError('nonfinite screen')
    mean = sum(deltas)/len(deltas)
    status = 'BLOCKED' if sum(reference)/len(reference) > .99 else (
        'PASS' if mean >= .01-1e-12 and min(deltas) >= -.01-1e-12 else 'FAIL')
    return dict(status=status, paired_accuracy_deltas=deltas, mean_accuracy_delta=mean,
                scope='already-viewed development; exploratory only')


def summarize(rows):
    expected = {(s,a,d) for s in SEEDS for a in ARMS for d in ((4,) if a=='GPT' else (2,4))}
    indexed = {(r['seed'],r['arm'],r['depth']):r for r in rows}
    if len(indexed) != len(rows) or set(indexed) != expected:
        raise ValueError('incomplete/duplicate final conditions')
    scores = {a:[indexed[s,a,4]['metrics']['all']['accuracy'] for s in SEEDS] for a in ARMS}
    screens = {}
    for left,right in (('D0','P4'),('D1','P4'),('D1','D0')):
        screens[left+'_minus_'+right] = screen([x-y for x,y in zip(scores[left],scores[right])],scores[right])
    return dict(descriptive={a:dict(per_seed=v,mean=sum(v)/len(v),worst=min(v)) for a,v in scores.items()},
                exploratory_screens=screens,candidate_selection_status='NOT ASSESSED',
                fresh_test_status='NOT TESTED',equal_compute_status='NOT TESTED',
                hardware_efficiency_status='NOT TESTED',depth_extrapolation_status='NOT TESTED')


def state_profile(model, prompts, seed, torch):
    """Same fixed six-digit prefix; no target tokens supplied to model."""
    from mechanisms import readout
    from torch.nn.attention import SDPBackend, sdpa_kernel
    x = torch.tensor(prompts,dtype=torch.long)
    if x.ndim!=2 or x.shape[1]!=6:
        raise ValueError('prefix-only diagnostic')
    model.eval()
    records = []
    def rms(v): return v.flatten(1).square().mean(1).sqrt()
    with torch.no_grad(),torch.random.fork_rng(devices=[]),sdpa_kernel(SDPBackend.MATH):
        torch.manual_seed(seed+91000)
        out=model(x,depth=4,trace=True)
        previous=None
        for item in out['states']:
            z,a=item['z'],item['a']
            eps=1e-12
            zn,an=rms(z),rms(a)
            gap=rms(z-a)
            cos=torch.nn.functional.cosine_similarity(z.flatten(1),a.flatten(1),dim=1,eps=eps)
            row=dict(call=item['call'],role=item['role'],z_rms=zn.tolist(),a_rms=an.tolist(),
                     relative_separation=(gap/(zn+an+eps)).tolist(),cosine=cos.tolist())
            if previous is not None:
                row.update(z_relative_change=(rms(z-previous['z'])/(rms(previous['z'])+eps)).tolist(),
                           a_relative_change=(rms(a-previous['a'])/(rms(previous['a'])+eps)).tolist())
            if item['call'] in (2,4):
                logits=readout(model.base,a,x)[:,-1,:]
                p=logits.softmax(-1)
                row.update(next_token=p.argmax(-1).tolist(),confidence=p.max(-1).values.tolist(),
                           entropy=(-(p*p.clamp_min(1e-30).log()).sum(-1)).tolist())
            records.append(row);previous=item
        # Determinism checks the readout belongs to the SAME trajectory.
        torch.testing.assert_close(readout(model.base,out['states'][-1]['a'],x),out['logits'],rtol=1e-5,atol=1e-6)
    return dict(records=records,scope='same-prefix latent diagnostics; P4 z=a by definition; not full-answer reasoning',
                logical_state_slots=1 if model.arm=='P4' else 2,
                logical_state_payload_bytes=int((1 if model.arm=='P4' else 2)*x.numel()*model.base.config.n_embd*4),
                storage_scope='logical FP32 state-slot payload, not peak memory or full autograd storage')


def sensitivity(model,prompts,seed,torch):
    from torch.nn.attention import SDPBackend,sdpa_kernel
    x=torch.tensor(prompts,dtype=torch.long); model.eval(); out={}
    if x.ndim!=2 or x.shape[1]!=6: raise ValueError('six-digit prompts only')
    with torch.no_grad(),torch.random.fork_rng(devices=[]),sdpa_kernel(SDPBackend.MATH):
        torch.manual_seed(seed+92000); ref=model(x,depth=4)['logits'][:,-1,:]
        for mode in ('noop','zero_z','zero_a'):
            torch.manual_seed(seed+92000); logits=model(x,depth=4,intervention=mode)['logits'][:,-1,:]
            if mode=='noop': torch.testing.assert_close(ref,logits,rtol=0,atol=0)
            out[mode]=dict(per_prompt_logit_l2=(logits-ref).square().sum(-1).sqrt().tolist(),
                           argmax_changed=(logits.argmax(-1)!=ref.argmax(-1)).tolist())
    return dict(interventions=out,scope='final checkpoint,zero one state before cycle2; local next-token sensitivity only')
