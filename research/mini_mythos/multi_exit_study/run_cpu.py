#!/usr/bin/env python3
"""MES-1 prepare/train/evaluate: no holdout inference until all20 training runs finish."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback

os.environ['CUDA_VISIBLE_DEVICES']=''
sys.dont_write_bytecode=True
import mes_policy as P
import mes_runtime as R
from mes_policy import require

HERE=Path(__file__).resolve().parent
PHASE_FILE={'prepare':'prepared.json','train':'training.json','evaluate':'result.json'}


def read(path):
    def pairs(items):
        out={}
        for k,v in items:
            require(k not in out,'duplicate JSON key')
            out[k]=v
        return out
    def bad(value): raise ValueError('nonfinite JSON: '+value)
    return json.loads(path.read_text(),object_pairs_hook=pairs,parse_constant=bad)


def complete(path):
    r=read(path)
    require(r.get('experiment')==P.EXPERIMENT and r.get('status')=='PASS','prerequisite incomplete or unrelated')
    return r


def source_match(prepared):
    require(R.identity()==prepared['source_identity'],'code/protocol changed since prepare')


def prepare(args,report):
    torch,env,root,m2,task,ident=R.context(args.parcae_dir)
    report.update(environment=env,code_head=R.ab.git(root,'rev-parse','HEAD'),source_pin=R.ab.PIN,
                  source_identity=ident,scope='no optimizer updates, no H1 evaluation',
                  review_status='DEFERRED; actual report required before train')
    data,manifest=R.ab.check_data(task)
    R.ab.write(args.out/'train.json',data['train'])
    report.update(data=manifest,train_file_sha256=R.ab.file_sha(args.out/'train.json'))
    _,report['holdouts']=P.allocate(task)
    x,y=R.encoded(task,data['train'],torch)
    ix=[j for c in range(4) for j in [i for i,r in enumerate(data['train']) if r['carry']==c][:8]]
    report['native_preflight']=[];report['gpt_objective_checks']=[];report['starts']={};report['counts']={}
    for seed in P.SEEDS:
        base,_,_=R.initial(m2,seed,'P4')
        report['native_preflight'].append(R.ab.native_preflight(base,seed,torch,m2))
        starts={};counts={}
        for arm in P.ARMS:
            base,io,h=R.initial(m2,seed,arm)
            starts[arm]=dict(model_sha256=h,shared_io=io)
            counts[arm]=R.probe(R.wrap(base,arm),x[ix],y[ix],P.DEPTH[arm],torch,m2)
            if arm=='GPT':
                report['gpt_objective_checks'].append(dict(seed=seed,**R.gpt_objective_check(base,x[ix],y[ix],torch)))
        require(len({starts[a]['model_sha256'] for a in ('P2','P4','A')})==1,'Parcae starts differ')
        plan=P.budgets({a:counts[a]['step_flops'] for a in P.ARMS})
        if 'budget' in report: require(plan==report['budget'],'seed-dependent compute budget')
        report['budget']=plan;report['starts'][str(seed)]=starts;report['counts'][str(seed)]=counts
        print(json.dumps(dict(seed=seed,native_prepare='PASS',training='NOT TESTED')),flush=True)
    (args.out/'pip-freeze.txt').write_text(subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True))
    m2.upstream_check(args.parcae_dir); source_match(report)
    report.update(status='PASS',native_compatibility_status='PASS',training_status='NOT TESTED',H1_status='NOT OPENED')


def verify_training(args,prepared,training):
    rows=training['rows']
    require(len(rows)==len(P.SEEDS)*len(P.ARMS),'twenty completed trajectories required')
    mapping={(r['arm'],r['seed']):r for r in rows}
    require(set(mapping)=={(a,s) for a in P.ARMS for s in P.SEEDS} and len(mapping)==len(rows),'duplicate/missing jobs')
    for (arm,seed),r in mapping.items():
        require(r['status']=='PASS' and r['steps']==prepared['budget']['arms'][arm]['steps'],'incomplete trajectory')
        require(r['initial_model_sha256']==prepared['starts'][str(seed)][arm]['model_sha256'],'initial identity mismatch')
        require(r['source_identity']==prepared['source_identity']['sha256'],'worker source identity')
        require(r['counted_training_flops']==prepared['budget']['arms'][arm]['total_flops'],'budget record mismatch')
        for key in ('loss_trace','final_loss_trace','aux_loss_trace','gradient_norm_trace','rng_before_forward_sha256'):
            require(len(r[key])==r['steps'],'incomplete training trace')
        for step in {P.REFERENCE_STEPS,r['steps']}:
            sn=r['snapshots'][str(step)];path=(args.out/sn['file']).resolve()
            require(path.is_relative_to(args.out) and R.ab.file_sha(path)==sn['sha256'],'snapshot missing or changed')
    for seed in P.SEEDS:
        group=[mapping[a,seed] for a in P.ARMS]
        require(len({r['batch_prefix3000_sha256'] for r in group})==1,'batch prefix mismatch')
        par=[mapping[a,seed] for a in ('P2','P4','A')]
        n=min(r['steps'] for r in par)
        require(par[0]['rng_before_forward_sha256'][:n]==par[1]['rng_before_forward_sha256'][:n]
                ==par[2]['rng_before_forward_sha256'][:n],'Parcae RNG prefix mismatch')
    return mapping


def review_input(args):
    require(args.review_report is not None and args.review_approved and args.reviewer,
            'supply actual --review-report FILE --reviewer NAME --review-approved before training')
    raw=args.review_report.read_bytes()
    require(len(raw.strip())>0,'empty review report')
    return raw


def train(args,report,prepared):
    raw=review_input(args)
    (args.out/'pretraining_review.md').write_bytes(raw)
    report.update(review={'reviewer_as_supplied':args.reviewer,'report_sha256':P.digest(raw),
                         'source_identity_sha256':prepared['source_identity']['sha256'],
                         'owner_acknowledged_approval':True,
                         'status':'PROVIDED_BY_OWNER; identity/verdict not independently authenticated'},
                  scope='training only, H1/HC/H2 not evaluated',rows=[])
    R.ab.write(args.out/'training.json',report)
    for seed in P.SEEDS:
        for arm in P.ARMS:
            cmd=[sys.executable,'-B',str(HERE/'run_cpu.py'),'train','--worker',arm,'--seed',str(seed),
                 '--out',str(args.out),'--parcae-dir',str(args.parcae_dir)]
            rc=subprocess.run(cmd,check=False).returncode
            rowfile=args.out/'jobs'/f'{arm}_{seed}'/'row.json'
            if rc!=0:
                if rowfile.exists(): report['partial_row']=read(rowfile)
                if rc==1: raise R.NumericalFailure(f'numerical failure {arm}/{seed}; remaining jobs NOT TESTED')
                raise RuntimeError(f'worker blocked {arm}/{seed}; evidence retained')
            report['rows'].append(read(rowfile));R.ab.write(args.out/'training.json',report)
    verify_training(args,prepared,report)
    report.update(status='PASS',pairing_status='PASS',H1_status='NOT OPENED',quality_status='NOT TESTED')


def evaluate(args,report,prepared,training):
    # No test labels or model evaluation are created before this full-run barrier.
    verify_training(args,prepared,training)
    torch,env,root,m2,task,ident=R.context(args.parcae_dir)
    allocation,manifest=P.allocate(task)
    require(manifest==prepared['holdouts'],'holdout allocation changed')
    truth=P.h1_examples(task,allocation)
    R.ab.write(args.out/'H1.json',truth)
    report.update(H1_sha256=P.object_sha(truth),H1_file_sha256=R.ab.file_sha(args.out/'H1.json'),
                  H1_pairs=len(truth),source_identity=ident,code_head=R.ab.git(root,'rev-parse','HEAD'),
                  training_summary_sha256=R.ab.file_sha(args.out/'training.json'),
                  training_review=training['review'],rows=[],training_rows=training['rows'],
                  native_preflight=prepared['native_preflight'],gpt_objective_checks=prepared.get('gpt_objective_checks',[]),
                  budget=prepared['budget'],counts=prepared['counts'],
                  outcome=None,post_result_review_status='NOT TESTED / DEFERRED')
    R.ab.write(args.out/'result.json',report)
    for seed in P.SEEDS:
        for arm in P.ARMS:
            cmd=[sys.executable,'-B',str(HERE/'run_cpu.py'),'evaluate','--worker',arm,'--seed',str(seed),
                 '--out',str(args.out),'--parcae-dir',str(args.parcae_dir)]
            require(subprocess.run(cmd,check=False).returncode==0,f'H1 inference blocked {arm}/{seed}')
            report['rows'].extend(read(args.out/'jobs'/f'{arm}_{seed}'/'H1.json'))
            R.ab.write(args.out/'result.json',report)
    outcome=P.summarize(report['rows'],truth)
    report.update(status='PASS',execution_status='PASS',outcome=outcome,exit_code=outcome['exit_code'],
                  HC_status='NOT OPENED',H2_status='NOT OPENED',scope='20 trajectories, 40 H1 conditions; no later MES phases')
    m2.upstream_check(args.parcae_dir);source_match(prepared)


def show(report):
    for key in ('experiment','phase','status','execution_status','budget','outcome','error','exit_code'):
        if key in report: print(key,json.dumps(report[key],ensure_ascii=False),flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('phase',choices=PHASE_FILE)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--parcae-dir',type=Path,required=True)
    p.add_argument('--review-report',type=Path);p.add_argument('--reviewer')
    p.add_argument('--review-approved',action='store_true')
    p.add_argument('--worker',choices=P.ARMS,help=argparse.SUPPRESS)
    p.add_argument('--seed',type=int,choices=P.SEEDS,help=argparse.SUPPRESS)
    args=p.parse_args();args.out=args.out.resolve();args.parcae_dir=args.parcae_dir.resolve()
    if args.worker:
        args.arm=args.worker
        try:
            prepared=complete(args.out/'prepared.json');source_match(prepared)
            require(args.seed is not None,'worker seed missing')
            if args.phase=='train':
                parent=read(args.out/'training.json')
                require(parent['status']=='PARTIAL' and parent.get('review'),'no active reviewed train phase')
                R.train_one(args,prepared)
            else:
                require(args.phase=='evaluate','invalid worker phase')
                t=complete(args.out/'training.json')
                r=next(r for r in t['rows'] if r['arm']==args.arm and r['seed']==args.seed)
                output=R.evaluate_one(args,prepared,r,read(args.out/'H1.json'))
                path=args.out/'jobs'/f'{args.arm}_{args.seed}'/'H1.json'
                require(not path.exists(),'existing worker H1 results retained')
                R.ab.write(path,output)
            return 0
        except Exception as exc:
            job=args.out/'jobs'/f'{args.arm}_{args.seed}'
            if job.is_dir():
                (job/'error.log').write_text(traceback.format_exc())
                rowpath=job/'row.json'
                if args.phase=='train' and rowpath.exists():
                    r=read(rowpath);r.update(status='FAIL' if isinstance(exc,R.NumericalFailure) else 'BLOCKED',error=str(exc))
                    R.ab.write(rowpath,r)
            traceback.print_exc();return 1 if isinstance(exc,R.NumericalFailure) else 2
    target=args.out/PHASE_FILE[args.phase]
    if target.exists():
        try:
            old=read(target);require(old.get('experiment')==P.EXPERIMENT,'unrelated result')
            show(old);print('READ ONLY: existing phase is not rerun.')
            code=old.get('exit_code',2);require(type(code)is int and code in (0,1,2),'invalid exit code')
            return code
        except Exception as exc:
            print('BLOCKED: existing bytes retained:',exc);return 2
    # Read-only prerequisites before reserving a phase; a missing review does not poison a prepared run.
    try:
        if args.phase=='prepare':
            require(not args.out.exists(),'existing partial directory retained')
            args.out.mkdir(parents=True,exist_ok=False)
            prepared=training=None
        else:
            prepared=complete(args.out/'prepared.json');source_match(prepared)
            R.context(args.parcae_dir)
            if args.phase=='train': review_input(args)
            training=complete(args.out/'training.json') if args.phase=='evaluate' else None
            if training: verify_training(args,prepared,training)
        claim=args.out/(args.phase+'.started')
        with claim.open('x') as f: f.write('phase reserved; no automatic retry or resume\n')
    except Exception as exc:
        print('BLOCKED:',exc);return 2
    report=dict(experiment=P.EXPERIMENT,phase=args.phase,status='PARTIAL',exit_code=2)
    R.ab.write(target,report)
    try:
        if args.phase=='prepare': prepare(args,report)
        elif args.phase=='train': train(args,report,prepared)
        else: evaluate(args,report,prepared,training)
        if args.phase!='evaluate': report['exit_code']=0
    except Exception as exc:
        code=1 if isinstance(exc,R.NumericalFailure) else 2
        report.update(status='FAIL' if code==1 else 'BLOCKED',error=f'{type(exc).__name__}: {exc}',exit_code=code)
        (args.out/(args.phase+'.error.log')).write_text(traceback.format_exc());traceback.print_exc()
    R.ab.write(target,report);show(report)
    print(R.ab.file_sha(target),target)
    return report['exit_code']


if __name__=='__main__': raise SystemExit(main())
