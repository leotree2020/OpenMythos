#!/usr/bin/env python3
"""MYTHOS-BASELINE-B1 command line: env-check, fetch, verify-load, generate, reload-check, finalize.

Each stage writes <run-dir>/<stage>.json exactly once (no overwrite, no retry, no resume) and
requires the previous stage to be PASS. Exit codes: PASS 0, FAIL 1, BLOCKED 2, NOT TESTED 3.
"""
import os
import sys

# Must precede any torch / tokenizers import.
_ENV_BEFORE = {k: os.environ.get(k) for k in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'CUDA_VISIBLE_DEVICES',
                                              'PYTHONDONTWRITEBYTECODE', 'TOKENIZERS_PARALLELISM')}
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['RAYON_NUM_THREADS'] = '1'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'
os.environ['CUDA_VISIBLE_DEVICES'] = ''
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
sys.dont_write_bytecode = True

import argparse  # noqa: E402
import json  # noqa: E402
import platform  # noqa: E402
import subprocess  # noqa: E402
import time  # noqa: E402
from datetime import datetime, timezone  # noqa: E402
from pathlib import Path  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import base_v01 as B  # noqa: E402

DEFAULT_UPSTREAM = '/workspaces/mythos-parcae-pinned'
DEFAULT_EVIDENCE_ROOT = '/workspaces/mythos-evidence/base_v01/b1'
EXIT = {'PASS': 0, 'FAIL': 1, 'BLOCKED': 2, 'NOT TESTED': 3}
STAGE_ORDER = ['env_check', 'fetch', 'verify_load', 'generate', 'reload_check']


# ------------------------------------------------------------------ shared plumbing

def read_stage(run_dir, name):
    path = Path(run_dir) / ('%s.json' % name)
    if not path.exists():
        return None
    return B.parse_strict(path.read_bytes())


def gate(run_dir, previous, rehearsal):
    """The previous stage must be PASS (an env-check that is only NOT TESTED is tolerated in rehearsals)."""
    rec = read_stage(run_dir, previous)
    if rec is None:
        raise SystemExit('refused: stage %s has no record in %s' % (previous, run_dir))
    ok = rec['status'] == 'PASS' or (rehearsal and previous == 'env_check' and rec['status'] == 'NOT TESTED')
    if not ok:
        raise SystemExit('refused: stage %s is %s' % (previous, rec['status']))
    return rec


def run_meta(run_dir):
    return B.parse_strict((Path(run_dir) / 'run.json').read_bytes())


def prompts_and_probes():
    prompts = B.parse_strict((HERE / 'prompts_v1.json').read_bytes())['prompts']
    probes = B.parse_strict((HERE / 'tokenizer_probes_v1.json').read_bytes())['probes']
    return prompts, probes


def frozen_inputs():
    return {n: dict(sha256=B.sha256_file(HERE / n), size=(HERE / n).stat().st_size)
            for n in ('prompts_v1.json', 'tokenizer_probes_v1.json')}


def verified_paths(run_dir):
    base = Path(run_dir) / 'downloads'
    return dict(model=base / 'model' / 'pytorch_model.bin', config=base / 'model' / 'config.json',
                tokenizer=base / 'tokenizer' / 'tokenizer.json')


def reverify_downloads(run_dir, sources):
    paths = verified_paths(run_dir)
    for key in ('model', 'config', 'tokenizer'):
        src = sources[key]
        B.require(paths[key].exists(), 'missing downloaded file %s' % paths[key])
        B.require(paths[key].stat().st_size == src['size'] and B.sha256_file(paths[key]) == src['sha256'],
                  'downloaded file %s no longer matches the pinned size/sha256' % key)
    return paths


def finish(record):
    print(json.dumps({k: record[k] for k in ('stage', 'status', 'error') if k in record}, ensure_ascii=False))
    for c in record['checks']:
        print('  %-18s %-10s %s' % (c['id'], c['status'], c['title']))
    return EXIT[record['status']]


# ------------------------------------------------------------------ stage 0: env-check

def stage_env(stage, run_dir, repo_dir, upstream, rehearsal, evidence_root):
    import platform as pf
    stage.add('E1', 'PASS', 'machine facts recorded', cpu_model=B.cpu_model(), logical_cores=os.cpu_count(),
              affinity_cores=len(os.sched_getaffinity(0)), python=pf.python_version(), executable=sys.executable,
              prefix=sys.prefix, os=pf.platform(), pip=B.installed_distributions().get('pip'),
              env_before=_ENV_BEFORE)
    avail, mem, cg = B.effective_available_memory()
    stage.extra['memory'] = dict(meminfo=mem, cgroup=cg, effective_available=avail)
    stage.ok('E2', avail is not None and avail >= B.MIN_MEM_BYTES, 'effective available memory >= 4 GiB',
             fail=B.Blocked, effective_available=avail, required=B.MIN_MEM_BYTES)
    disks = B.disk_report(dict(repo=repo_dir, venv=sys.prefix, evidence=run_dir, upstream=upstream))
    stage.extra['disk'] = disks
    need_estimate = 578361537 + 700 * 10 ** 6 + 200 * 10 ** 6
    required = max(B.MIN_DISK_BYTES, need_estimate + 10 ** 9)
    worst_free = {k: v['free'] for k, v in disks.items() if k in ('evidence', 'venv')}
    disk_ok = all(v >= required for v in worst_free.values())
    disk_detail = dict(free=worst_free, required=required, estimated_need=need_estimate,
                       estimate_basis='578,361,537 B download + ~700 MB package copy + ~200 MB outputs')
    if rehearsal:
        stage.add('E3', 'PASS' if disk_ok else 'NOT TESTED',
                  'free space gate (REHEARSAL: tiny fixture, shortfall waived, not evidence)', **disk_detail)
    else:
        stage.ok('E3', disk_ok, 'free space >= max(5 GiB, estimated need + 1 GB) on the evidence and environment filesystems',
                 fail=B.Blocked, **disk_detail)
    dists = B.installed_distributions()
    try:
        import torch
        torch_version = torch.__version__
    except Exception as exc:
        torch_version = 'IMPORT FAILED: %r' % (exc,)
    actual = dict(python=platform.python_version(), torch=torch_version,
                  numpy=dists.get('numpy'), einops=dists.get('einops'),
                  tokenizers=dists.get('tokenizers'), **{'huggingface-hub': dists.get('huggingface-hub')})
    mismatch = {k: dict(expected=v, actual=actual.get(k)) for k, v in B.ENV_PINS.items() if actual.get(k) != v}
    forbidden = [d for d in B.FORBIDDEN_DISTS if d in dists]
    pip_check = subprocess.run([sys.executable, '-m', 'pip', 'check'], capture_output=True, text=True)
    stage.extra['dependencies'] = dict(pins=B.ENV_PINS, actual=actual, mismatch=mismatch, forbidden_present=forbidden,
                                       pip_check_rc=pip_check.returncode, pip_check_output=pip_check.stdout.strip(),
                                       distributions=dict(sorted(dists.items())))
    env_ok = not mismatch and not forbidden and pip_check.returncode == 0
    if rehearsal:
        stage.add('E4', 'PASS' if env_ok else 'NOT TESTED', 'dependency pins (REHEARSAL: mismatches waived, not evidence)',
                  mismatch=mismatch, forbidden=forbidden)
    else:
        stage.ok('E4', env_ok, 'exact dependency pins, no forbidden packages, pip check clean', fail=B.Blocked,
                 mismatch=mismatch, forbidden=forbidden, pip_check=pip_check.stdout.strip())
    import torch
    B.set_runtime(torch)
    threads_ok = (torch.get_num_threads() == 1 and os.environ['OMP_NUM_THREADS'] == '1'
                  and os.environ['MKL_NUM_THREADS'] == '1')
    stage.ok('E5', threads_ok and not torch.cuda.is_available() and torch.are_deterministic_algorithms_enabled()
             and torch.get_default_dtype() == torch.float32,
             'CPU only, 1 thread, deterministic algorithms, FP32', fail=B.Blocked,
             torch_threads=torch.get_num_threads(), cuda_available=torch.cuda.is_available(),
             deterministic=torch.are_deterministic_algorithms_enabled())
    head = B.git(repo_dir, 'rev-parse', 'HEAD')
    branch = B.git(repo_dir, 'rev-parse', '--abbrev-ref', 'HEAD')
    tracked = B.git(repo_dir, 'status', '--porcelain', '--untracked-files=no')
    own = B.git(repo_dir, 'status', '--porcelain', '--untracked-files=all', '--', str(HERE))
    code_hashes = {p.name: B.sha256_file(p) for p in sorted(HERE.iterdir())
                   if p.is_file() and p.suffix in ('.py', '.json', '.sh', '.txt')}
    stage.extra['code_identity'] = dict(repo=str(repo_dir), head=head, branch=branch, tracked_changes=tracked,
                                        base_v01_status=own, file_sha256=code_hashes)
    if rehearsal:
        stage.add('E6', 'PASS', 'code identity recorded (REHEARSAL: cleanliness not enforced)')
    else:
        stage.ok('E6', not tracked and not own, 'repository tracked tree and base_v01 directory are committed and clean',
                 fail=B.Blocked, head=head, tracked_changes=tracked, base_v01_status=own)
    state = B.setup_upstream(upstream, run_dir)
    origins = B.import_origins()
    inside = all(Path(v).is_relative_to(Path(state['path'])) for v in origins.values())
    stage.ok('E7', inside, 'upstream pinned, clean, and imported from the pinned checkout', fail=B.Blocked,
             upstream_head=state['head'], import_origins=origins, status_lines_before=state['status_lines'])
    same, after = B.upstream_unchanged(state)
    stage.ok('E7b', same, 'upstream HEAD and file state unchanged by imports (no bytecode written)', fail=B.Blocked,
             status_lines_after=after['status_lines'])


def cmd_env_check(args):
    repo_dir = Path(args.repo_dir).resolve()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    run_id = args.run_id or ('%s-%s-%d' % ('rehearsal' if args.rehearsal else 'b1', stamp, os.getpid()))
    root = Path(args.evidence_root)
    root.mkdir(parents=True, exist_ok=True)
    run_dir = root / run_id
    run_dir.mkdir(exist_ok=False)
    meta = dict(experiment=B.EXPERIMENT, run_id=run_id, rehearsal=bool(args.rehearsal),
                start_epoch=time.time(), start_utc=stamp, argv=sys.argv, repo_dir=str(repo_dir),
                upstream=str(Path(args.upstream).resolve()),
                fixture_dir=str(Path(args.fixture_dir).resolve()) if args.fixture_dir else None,
                note='REHEARSAL: not B1 evidence' if args.rehearsal else 'formal B1 run')
    B.write_json_exclusive(run_dir / 'run.json', meta)
    planned = ['E1', 'E2', 'E3', 'E4', 'E5', 'E6', 'E7', 'E7b']
    rec = B.run_stage('env_check', planned, run_dir, stage_env,
                      ctx=dict(run_dir=run_dir, repo_dir=repo_dir, upstream=args.upstream,
                               rehearsal=args.rehearsal, evidence_root=root))
    print('run directory:', run_dir)
    return finish(rec)


# ------------------------------------------------------------------ stage 1: fetch (A1)

def stage_fetch(stage, run_dir, rehearsal, fixture_dir):
    sources, _ = B.load_sources(run_dir, rehearsal, fixture_dir)
    base = B.HF_BASE_URL
    if rehearsal:
        base = Path(fixture_dir).resolve().as_uri()
    stage.extra['frozen_inputs'] = frozen_inputs()
    stage.extra['sources'] = sources
    records = {}
    layout = dict(model=('model', sources['model']), config=('model', sources['config']),
                  tokenizer=('tokenizer', sources['tokenizer']))
    for key in ('config', 'tokenizer', 'model'):
        sub, src = layout[key]
        B.wall_cap_check(run_dir)
        try:
            records[key] = B.download_verified(src, Path(run_dir) / 'downloads' / sub, base=base)
        except B.Blocked as exc:
            stage.add('A1.' + key, 'BLOCKED', 'download + size + sha256 of %s' % src['name'], error=str(exc))
            raise
        stage.add('A1.' + key, 'PASS', 'size and SHA-256 of %s match the pinned value' % src['name'],
                  **{k: records[key][k] for k in ('url', 'size', 'sha256', 'final_host', 'response_headers')})
    stage.extra['downloads'] = records


def cmd_fetch(args):
    run_dir = Path(args.run_dir)
    meta = run_meta(run_dir)
    gate(run_dir, 'env_check', meta['rehearsal'])
    rec = B.run_stage('fetch', ['A1.config', 'A1.tokenizer', 'A1.model'], run_dir, stage_fetch,
                      ctx=dict(run_dir=run_dir, rehearsal=meta['rehearsal'], fixture_dir=meta['fixture_dir']))
    return finish(rec)


# ------------------------------------------------------------------ stage 2: verify-load (A2-A7)

def stage_verify_load(stage, run_dir, upstream):
    meta = run_meta(run_dir)
    sources, expect = B.load_sources(run_dir, meta['rehearsal'], meta['fixture_dir'])
    paths = reverify_downloads(run_dir, sources)
    state = B.setup_upstream(upstream, run_dir)
    B.wall_cap_check(run_dir)
    # Tokenizer identity and probes before any model work.
    ident = B.tokenizer_identity(paths['tokenizer'], expect['vocab_size'], tuple(expect['special_ids']))
    stage.extra['tokenizer_identity'] = ident
    B.check_tokenizer_identity(stage, ident, expect['vocab_size'], tuple(expect['special_ids']))
    tok = B.load_tokenizer(paths['tokenizer'])
    import tokenizers
    stage.extra['tokenizers_version'] = tokenizers.__version__
    stage.ok('A6.loaded_size', tok.get_vocab_size(with_added_tokens=True) == expect['vocab_size'],
             'tokenizers library reports the same vocabulary size', fail=B.Blocked,
             reported=tok.get_vocab_size(with_added_tokens=True))
    eos_content = ident['specials_by_id'].get(str(B.EOS_ID))
    stage.add('A6.eos', 'PASS', 'EOS id %d is a special added token' % B.EOS_ID, eos_content=eos_content,
              note='EOS role taken from the authorization (BOS/EOS/PAD = 0/1/2); content recorded')
    _, probes = prompts_and_probes()
    rows = B.run_probes(tok, probes, expect['vocab_size'])
    probe_doc = dict(probes_file_sha256=B.sha256_file(HERE / 'tokenizer_probes_v1.json'), rows=rows,
                     all_round_trip=all(r['round_trip_equal'] for r in rows), all_in_range=all(r['in_range'] for r in rows))
    B.write_json_exclusive(Path(run_dir) / 'tokenizer_probe_results.json', probe_doc)
    stage.ok('A6.probes', probe_doc['all_round_trip'] and probe_doc['all_in_range'] and len(rows) >= 30,
             'decode(encode(s)) == s for all %d probes, ids in range, special tokens not skipped' % len(rows),
             failures=[r['index'] for r in rows if not (r['round_trip_equal'] and r['in_range'])])
    B.check_backend(stage, 'flash')
    cfg, doc = B.build_config(paths['config'], expect)
    B.check_config_facts(stage, cfg, expect)
    model, details = B.load_model(stage, paths['config'], paths['model'], expect, tag='A')
    stage.extra['model_details'] = details
    same, after = B.upstream_unchanged(state)
    stage.ok('U.upstream', same and after['head'] == B.UPSTREAM_PIN, 'upstream unchanged at the end of the stage',
             fail=B.Blocked, status_lines_after=after['status_lines'])


def cmd_verify_load(args):
    run_dir = Path(args.run_dir)
    meta = run_meta(run_dir)
    gate(run_dir, 'fetch', meta['rehearsal'])
    planned = ['A2', 'A3.accounting', 'A3.shared', 'A4.facts', 'A4.diff', 'A5', 'A6.model_bpe', 'A6.vocab',
               'A6.specials', 'A6.components', 'A6.loaded_size', 'A6.eos', 'A6.probes', 'A7', 'U.upstream']
    rec = B.run_stage('verify_load', planned, run_dir, stage_verify_load, ctx=dict(run_dir=run_dir, upstream=meta['upstream']))
    return finish(rec)


# ------------------------------------------------------------------ stage 3: generate (A8-A10) + package

def run_pass(name, tok, model, prompts, run_dir):
    rows = []
    out_path = Path(run_dir) / ('generation_%s.json' % name)
    try:
        for spec in prompts:
            rows.append(B.prompt_record(tok, spec, model, name, deadline_check=lambda: B.wall_cap_check(run_dir)))
    except BaseException:
        B.write_json_exclusive(Path(run_dir) / ('generation_%s.partial.json' % name),
                               dict(pass_name=name, complete=False, rows=rows))
        raise
    doc = dict(pass_name=name, complete=True, rows=rows, auto_pass_count=sum(1 for r in rows if r['auto']['passed']))
    B.write_json_exclusive(out_path, doc)
    return rows


def stage_generate(stage, run_dir, upstream):
    import torch
    meta = run_meta(run_dir)
    sources, expect = B.load_sources(run_dir, meta['rehearsal'], meta['fixture_dir'])
    paths = reverify_downloads(run_dir, sources)
    state = B.setup_upstream(upstream, run_dir)
    stage.extra['process'] = B.process_identity()
    tok = B.load_tokenizer(paths['tokenizer'])
    prompts, _ = prompts_and_probes()
    model, _ = B.load_model(stage, paths['config'], paths['model'], expect, tag='G')
    # A8: native forward vs generation forward on prompts 1, 4, 7.
    logits_dir = Path(run_dir) / 'logits'
    logits_dir.mkdir()
    a8 = []
    for i in B.LOGIT_PROMPTS:
        B.wall_cap_check(run_dir)
        ids = B.encode_ids(tok, prompts[i - 1]['text'])
        native, engineered = B.native_vs_generation_logits(model, ids, B.PROMPT_SEED_BASE + i)
        max_diff = float((native - engineered).abs().max())
        try:
            torch.testing.assert_close(native, engineered, rtol=1e-5, atol=1e-6)
            close = True
        except AssertionError:
            close = False
        path = logits_dir / ('prompt%d_engineered.pt' % i)
        torch.save(engineered, path)
        a8.append(dict(prompt=i, tokens=len(ids), max_abs_diff=max_diff, close=close,
                       bitwise_equal=bool(torch.equal(native, engineered)),
                       native_sha256=B.tensor_sha256(native), engineered_sha256=B.tensor_sha256(engineered),
                       engineered_file=str(path), finite=bool(torch.isfinite(engineered).all())))
    stage.ok('A8', all(r['close'] and r['finite'] for r in a8),
             'native forward vs forward_for_generation logits within rtol=1e-5, atol=1e-6', rows=a8)
    # A9: first pass over all 12 prompts.
    pass1 = run_pass('pass1', tok, model, prompts, run_dir)
    stage.ok('A9', len(pass1) == 12 and all(len(r['new_ids']) == B.MAX_NEW_TOKENS for r in pass1),
             'all 12 fixed prompts generated 64 raw tokens and were auto-checked (results kept, failures included)',
             fail=B.Blocked, auto_pass_count=sum(1 for r in pass1 if r['auto']['passed']),
             auto_passed_ids=[r['id'] for r in pass1 if r['auto']['passed']])
    n_auto = sum(1 for r in pass1 if r['auto']['passed'])
    stage.extra['quality'] = dict(auto_pass_count=n_auto, required_both=9,
                                  status='FAIL' if n_auto < 9 else 'NOT TESTED',
                                  coherence_review='NOT TESTED: pending ChatGPT AI-assisted review (not a human evaluation)')
    # A10: same-process repeat.
    pass2 = run_pass('pass2', tok, model, prompts, run_dir)
    diffs = [a['id'] for a, b in zip(pass1, pass2) if a['new_ids'] != b['new_ids']]
    stage.ok('A10', not diffs, 'second pass in the same process gives identical raw token sequences', differing_prompts=diffs)
    # Package for the new-process reload.
    package_dir = Path(run_dir) / 'package'
    manifest = B.save_package(model, package_dir, paths['config'], paths['tokenizer'],
                              dict(model=sources['model'], tokenizer=sources['tokenizer'], config=sources['config'],
                                   upstream_pin=B.UPSTREAM_PIN, run_id=meta['run_id'], rehearsal=meta['rehearsal']))
    stage.add('P.package', 'PASS', 'inference package saved with provenance manifest', files=manifest['files'])
    stage.extra['package_manifest_sha256'] = B.sha256_file(package_dir / 'package_manifest.json')
    stage.extra['process_end_wall_time'] = time.time()
    same, after = B.upstream_unchanged(state)
    stage.ok('U.upstream', same, 'upstream unchanged at the end of the stage', fail=B.Blocked,
             status_lines_after=after['status_lines'])


def cmd_generate(args):
    run_dir = Path(args.run_dir)
    meta = run_meta(run_dir)
    gate(run_dir, 'verify_load', meta['rehearsal'])
    planned = ['G2', 'G3.accounting', 'G3.shared', 'G5', 'A8', 'A9', 'A10', 'P.package', 'U.upstream']
    rec = B.run_stage('generate', planned, run_dir, stage_generate, ctx=dict(run_dir=run_dir, upstream=meta['upstream']))
    return finish(rec)


# ------------------------------------------------------------------ stage 4: reload-check (A11)

def stage_reload(stage, run_dir, upstream):
    import torch
    meta = run_meta(run_dir)
    sources, expect = B.load_sources(run_dir, meta['rehearsal'], meta['fixture_dir'])
    gen = read_stage(run_dir, 'generate')
    ident = B.process_identity()
    stage.extra['process'] = ident
    prev = gen['process']
    new_process = (ident['pid'] != prev['pid'] and ident['start_time_ticks'] != prev['start_time_ticks']
                   and ident['wall_time'] >= gen['process_end_wall_time'])
    stage.ok('A11.process', new_process, 'running in a genuinely new process (new pid, later start, started after the save)',
             fail=B.Blocked, previous=prev, current=ident)
    paths = reverify_downloads(run_dir, sources)
    state = B.setup_upstream(upstream, run_dir)
    package_dir = Path(run_dir) / 'package'
    manifest = B.parse_strict((package_dir / 'package_manifest.json').read_bytes())
    for name, rec in manifest['files'].items():
        stage.ok('A11.file.' + name, B.sha256_file(package_dir / name) == rec['sha256'],
                 'package file %s matches its manifest' % name, fail=B.Blocked)
    stage.ok('A11.config_identity', B.sha256_file(package_dir / 'config.json') == sources['config']['sha256']
             and B.sha256_file(package_dir / 'tokenizer.json') == sources['tokenizer']['sha256'],
             'package config.json and tokenizer.json are byte-identical to the pinned originals', fail=B.Blocked)
    tok = B.load_tokenizer(package_dir / 'tokenizer.json')
    prompts, _ = prompts_and_probes()
    model, _ = B.load_model(stage, package_dir / 'config.json', package_dir / 'pytorch_model.bin', expect, tag='R')
    original = torch.load(str(paths['model']), map_location='cpu', weights_only=True)
    mapping, _prefix = B.map_prefix(original.keys())
    after = model.state_dict()
    bad = [new for old, new in mapping.items()
           if new not in after or after[new].dtype != original[old].dtype or not bool(torch.equal(after[new], original[old]))]
    del original
    stage.ok('A11.weights', not bad and len(mapping) == len(after),
             'every tensor of the reloaded package equals the original file bit for bit', differing=bad[:5],
             tensors=len(mapping))
    logit_rows = []
    for i in B.LOGIT_PROMPTS:
        ids = B.encode_ids(tok, prompts[i - 1]['text'])
        _, engineered = B.native_vs_generation_logits(model, ids, B.PROMPT_SEED_BASE + i)
        saved = torch.load(str(Path(run_dir) / 'logits' / ('prompt%d_engineered.pt' % i)), weights_only=True)
        logit_rows.append(dict(prompt=i, bitwise_equal=bool(torch.equal(saved, engineered)),
                               saved_sha256=B.tensor_sha256(saved), reloaded_sha256=B.tensor_sha256(engineered)))
    stage.ok('A11.logits', all(r['bitwise_equal'] for r in logit_rows),
             'logits for prompts 1, 4, 7 are bit-identical to the pre-save values (rtol=atol=0)', rows=logit_rows)
    pass3 = run_pass('pass3', tok, model, prompts, run_dir)
    pass1 = B.parse_strict((Path(run_dir) / 'generation_pass1.json').read_bytes())['rows']
    ids_diff = [a['id'] for a, b in zip(pass1, pass3) if a['new_ids'] != b['new_ids']]
    stage.ok('A11.generation', not ids_diff and len(pass3) == 12,
             'all 12 raw token sequences equal the first pass', differing_prompts=ids_diff)
    text_diff = [a['id'] for a, b in zip(pass1, pass3) if (a['text_all_64_tokens'], a['text_continuation'])
                 != (b['text_all_64_tokens'], b['text_continuation'])]
    stage.ok('A11.text', not text_diff, 'decoded texts (all 64 tokens and effective continuation) are identical',
             differing_prompts=text_diff)
    same, after_state = B.upstream_unchanged(state)
    stage.ok('U.upstream', same, 'upstream unchanged at the end of the stage', fail=B.Blocked,
             status_lines_after=after_state['status_lines'])


def cmd_reload(args):
    run_dir = Path(args.run_dir)
    meta = run_meta(run_dir)
    gate(run_dir, 'generate', meta['rehearsal'])
    planned = ['A11.process', 'A11.file.pytorch_model.bin', 'A11.file.config.json', 'A11.file.tokenizer.json',
               'A11.config_identity', 'R2', 'R3.accounting', 'R3.shared', 'R5', 'A11.weights', 'A11.logits',
               'A11.generation', 'A11.text', 'U.upstream']
    rec = B.run_stage('reload_check', planned, run_dir, stage_reload, ctx=dict(run_dir=run_dir, upstream=meta['upstream']))
    return finish(rec)


# ------------------------------------------------------------------ finalize

A_MAP = [('A1', 'fetch', ['A1.config', 'A1.tokenizer', 'A1.model']),
         ('A2', 'verify_load', ['A2']),
         ('A3', 'verify_load', ['A3.accounting', 'A3.shared']),
         ('A4', 'verify_load', ['A4.facts', 'A4.diff']),
         ('A5', 'verify_load', ['A5']),
         ('A6', 'verify_load', ['A6.model_bpe', 'A6.vocab', 'A6.specials', 'A6.components', 'A6.loaded_size', 'A6.eos', 'A6.probes']),
         ('A7', 'verify_load', ['A7']),
         ('A8', 'generate', ['A8']),
         ('A9', 'generate', ['A9']),
         ('A10', 'generate', ['A10']),
         ('A11', 'reload_check', ['A11.process', 'A11.file.pytorch_model.bin', 'A11.file.config.json',
                                  'A11.file.tokenizer.json', 'A11.config_identity', 'A11.weights', 'A11.logits',
                                  'A11.generation', 'A11.text'])]


def cmd_finalize(args):
    run_dir = Path(args.run_dir)
    meta = run_meta(run_dir)
    recs = {n: read_stage(run_dir, n) for n in STAGE_ORDER}
    table = []
    for label, stage_name, ids in A_MAP:
        rec = recs.get(stage_name)
        if rec is None:
            table.append(dict(item=label, status='NOT TESTED', reason='stage %s not run' % stage_name))
            continue
        by_id = {c['id']: c for c in rec['checks']}
        statuses = [by_id[i]['status'] if i in by_id else 'NOT TESTED' for i in ids]
        table.append(dict(item=label, status=B.worst(statuses), stage=stage_name,
                          failing=[i for i, s in zip(ids, statuses) if s != 'PASS']))
    stage_status = {n: (r['status'] if r else 'NOT TESTED') for n, r in recs.items()}
    engineering = B.worst(list(stage_status.values()))
    gen = recs.get('generate')
    quality = gen['quality'] if gen and 'quality' in gen else dict(status='NOT TESTED')
    files = []
    for p in sorted(run_dir.rglob('*')):
        if p.is_file() and p.name not in ('manifest.json', 'summary.json') and not p.name.endswith('.tmp'):
            files.append(dict(path=str(p.relative_to(run_dir)), size=p.stat().st_size, sha256=B.sha256_file(p)))
    summary = dict(experiment=B.EXPERIMENT, run_id=meta['run_id'], rehearsal=meta['rehearsal'],
                   engineering_status=engineering, language_quality=quality, stage_status=stage_status, items=table,
                   run_directory=str(run_dir), run_directory_bytes=B.dir_bytes(run_dir),
                   elapsed_seconds_since_start=round(time.time() - meta['start_epoch'], 1),
                   active_seconds=round(B.active_seconds(run_dir), 1), wall_cap_seconds=B.WALL_CAP_SECONDS,
                   stage_elapsed={n: (r['elapsed_seconds'] if r else None) for n, r in recs.items()},
                   stage_resource={n: (r.get('resource') if r else None) for n, r in recs.items()},
                   cgroup_memory=B.cgroup_memory(), disk=B.disk_report(dict(evidence=run_dir)),
                   license_status='UNCONFIRMED for weights and tokenizer; local research only; no redistribution',
                   note='exit codes are not evidence; no training was performed')
    B.write_json_exclusive(run_dir / 'summary.json', summary)
    B.write_json_exclusive(run_dir / 'manifest.json', dict(run_id=meta['run_id'], files=files,
                                                           note='summary.json and manifest.json excluded from the list'))
    print(json.dumps({k: summary[k] for k in ('run_id', 'engineering_status', 'language_quality')}, ensure_ascii=False))
    for row in table:
        print('  %-4s %-10s %s' % (row['item'], row['status'], row.get('failing') or ''))
    if args.export_dir:
        export_small(run_dir, Path(args.export_dir), meta)
    return EXIT[engineering]


def export_small(run_dir, export_dir, meta):
    """Copy small reports (no weights, no tokenizer) for committing."""
    export_dir = Path(export_dir) / meta['run_id']
    export_dir.mkdir(parents=True, exist_ok=False)
    names = ['run.json', 'env_check.json', 'fetch.json', 'verify_load.json', 'generate.json', 'reload_check.json',
             'summary.json', 'manifest.json', 'tokenizer_probe_results.json', 'generation_pass1.json',
             'generation_pass2.json', 'generation_pass3.json']
    for name in names:
        src = run_dir / name
        if src.exists():
            if src.stat().st_size > 5 * 1024 * 1024:
                raise SystemExit('refusing to export %s: larger than 5 MiB' % name)
            (export_dir / name).write_bytes(src.read_bytes())
    print('exported small reports to', export_dir)


# ------------------------------------------------------------------ CLI

def build_parser():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='cmd', required=True)
    e = sub.add_parser('env-check')
    e.add_argument('--evidence-root', default=DEFAULT_EVIDENCE_ROOT)
    e.add_argument('--run-id')
    e.add_argument('--upstream', default=DEFAULT_UPSTREAM)
    e.add_argument('--repo-dir', default=str(HERE.parents[2]))
    e.add_argument('--rehearsal', action='store_true', help='fixture rehearsal; produces no B1 evidence')
    e.add_argument('--fixture-dir')
    for name in ('fetch', 'verify-load', 'generate', 'reload-check', 'finalize'):
        s = sub.add_parser(name)
        s.add_argument('--run-dir', required=True)
        if name == 'finalize':
            s.add_argument('--export-dir')
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.cmd == 'env-check' and args.rehearsal and not args.fixture_dir:
        raise SystemExit('--rehearsal needs --fixture-dir')
    handlers = {'env-check': cmd_env_check, 'fetch': cmd_fetch, 'verify-load': cmd_verify_load,
                'generate': cmd_generate, 'reload-check': cmd_reload, 'finalize': cmd_finalize}
    return handlers[args.cmd](args)


if __name__ == '__main__':
    raise SystemExit(main())
