"""MYTHOS-BASELINE-B1 library: controlled load, generation and save/reload of the
official Parcae-140M weights on CPU.

No training, no optimizer, no upstream edits. Every check returns an explicit
PASS / FAIL / BLOCKED / NOT TESTED status; process exit codes are never evidence.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

EXPERIMENT = 'MYTHOS-BASELINE-B1'
UPSTREAM_PIN = '69284c13746e849104f738d6d1a347b1f457df76'
PROMPT_SEED_BASE = 731000
NUM_STEPS = 8
MAX_NEW_TOKENS = 64
MAX_PROMPT_TOKENS = 48
EOS_ID = 1
WALL_CAP_SECONDS = 3 * 3600
MIN_MEM_BYTES = 4 * 1024 ** 3
MIN_DISK_BYTES = 5 * 1024 ** 3
LOGIT_PROMPTS = (1, 4, 7)
HF_BASE_URL = 'https://huggingface.co'

SOURCES = {
    'model': dict(repo='SandyResearch/parcae-140m', rev='236739ce93ba1afc1b3f172fb4a509f4500d2852',
                  name='pytorch_model.bin', size=578361537,
                  sha256='ed6eb306464dd0d694e9eacd58f7e06ac3e44b43cb7c5c79dbcb1543059c6621'),
    'config': dict(repo='SandyResearch/parcae-140m', rev='236739ce93ba1afc1b3f172fb4a509f4500d2852',
                   name='config.json', size=1741,
                   sha256='5c8fc785c2f6dba67d0370ad715034860e3b22bfce850da825c06baa03923c13'),
    'tokenizer': dict(repo='SandyResearch/parcae-tokenizer', rev='6247b5d0592876b73660f34c2dd16c9db9e9045c',
                      name='tokenizer.json', size=2326980,
                      sha256='e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77'),
}

# Facts given in the authorization; verified against the downloaded original bytes.
EXPECT = {
    'vocab_size': 32768,
    'special_ids': (0, 1, 2),
    'config': dict(name='parcae-small-140m', n_embd=768, intermediate_size=3072,
                   num_attention_heads=6, num_key_value_heads=6, vocab_size=32768,
                   padded_vocab_size=32768, n_layers_in_prelude=2, n_layers_in_recurrent_block=2,
                   n_layers_in_coda=2, attn_impl='flash', use_fused_head='pytorch',
                   norm_class_name='RMSNorm', state_init='like-init', injection_type='diagonal',
                   mean_recurrence=8, mean_backprop_depth=4,
                   recurrent_iteration_method='per-sequence', tie_embeddings=True),
    'rope': dict(use_rope=True, rope_condense_ratio=1, rope_base=50000),
    'builtin_config': 'parcae-small-140m',
    # Source-derived numbers: reported against the binary, never used as the gate.
    'derived': dict(parameter_tensors=61, parameter_elements=144323136, state_dict_entries=63),
}
ENV_PINS = {'python': '3.12.3', 'torch': '2.11.0+cpu', 'numpy': '1.26.4', 'einops': '0.8.0',
            'tokenizers': '0.23.2', 'huggingface-hub': '1.33.0'}
FORBIDDEN_DISTS = ('transformers', 'datasets', 'lm-eval', 'lm_eval', 'lightning', 'safetensors')
LABEL_ONLY_CONFIG_FIELDS = ('name', 'hf_config')

STATUS_ORDER = ('FAIL', 'BLOCKED', 'NOT TESTED', 'PASS')


class Blocked(Exception):
    """Source, resource, input or unexplained-difference problem: stop, keep evidence."""


class Failed(Exception):
    """A numerical, determinism or reload assertion failed."""


# ---------------------------------------------------------------- generic helpers

def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def canon(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


def sha256_canon(obj) -> str:
    return sha256_bytes(canon(obj))


def parse_strict(raw: bytes):
    """JSON parse that rejects duplicate keys and non-finite constants."""
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError('duplicate JSON key: ' + key)
            out[key] = value
        return out

    def bad(constant):
        raise ValueError('non-finite JSON constant: ' + constant)
    return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=bad)


def write_json_exclusive(path, obj):
    """Write via a temporary file and hard-link into place so an existing file is never replaced."""
    path = Path(path)
    tmp = path.with_name(path.name + '.tmp%d' % os.getpid())
    data = (json.dumps(obj, indent=2, sort_keys=False, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')
    with open(tmp, 'xb') as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    try:
        try:
            os.link(tmp, path)
        except FileExistsError:
            raise
        except OSError:  # filesystem without hard links: exclusive create instead
            with open(path, 'xb') as f:
                f.write(data)
    finally:
        os.unlink(tmp)
    return path


def git(repo, *args) -> str:
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()


def require(cond, message, exc=Blocked):
    if not cond:
        raise exc(message)


def worst(statuses) -> str:
    present = set(statuses)
    for s in STATUS_ORDER:
        if s in present:
            return s
    return 'NOT TESTED'


class Stage:
    """Collects checks; planned-but-unreached checks become NOT TESTED."""

    def __init__(self, name, planned):
        self.name = name
        self.planned = list(planned)
        self.checks = {}
        self.extra = {}
        self.t0 = time.monotonic()
        self.error = None

    def add(self, cid, status, title='', **detail):
        self.checks[cid] = dict(id=cid, status=status, title=title, detail=detail)
        return status

    def ok(self, cid, cond, title='', fail=Failed, **detail):
        """Record PASS/FAIL (or BLOCKED when fail=Blocked) and raise to stop on failure."""
        if cond:
            self.add(cid, 'PASS', title, **detail)
            return True
        status = 'BLOCKED' if fail is Blocked else 'FAIL'
        self.add(cid, status, title, **detail)
        raise fail('%s: %s' % (cid, title))

    def stop(self, status, message):
        """An exception ended the stage: make sure the record can never read as PASS/NOT TESTED."""
        rank = {s: i for i, s in enumerate(STATUS_ORDER)}
        current = worst(c['status'] for c in self.checks.values()) if self.checks else 'PASS'
        if self.checks and rank[current] <= rank[status]:
            return
        self.add('STOP', status, 'stage stopped by an exception', error=message)

    def result(self):
        checks = []
        for cid in self.planned:
            checks.append(self.checks.get(cid) or dict(id=cid, status='NOT TESTED', title='not reached', detail={}))
        for cid, c in self.checks.items():
            if cid not in self.planned:
                checks.append(c)
        status = worst(c['status'] for c in checks)
        return dict(experiment=EXPERIMENT, stage=self.name, status=status, checks=checks,
                    elapsed_seconds=round(time.monotonic() - self.t0, 3), error=self.error,
                    **self.extra)


def run_stage(name, planned, run_dir, fn, ctx=None):
    """Execute fn(stage); map exceptions to statuses; write the stage record exclusively."""
    stage = Stage(name, planned)
    try:
        fn(stage, **(ctx or {}))
    except Blocked as exc:
        stage.error = 'BLOCKED: %s' % exc
        stage.stop('BLOCKED', str(exc))
    except Failed as exc:
        stage.error = 'FAIL: %s' % exc
        stage.stop('FAIL', str(exc))
    except BaseException as exc:  # unexpected: cannot conclude, never PASS
        stage.error = 'UNEXPECTED %s: %s\n%s' % (type(exc).__name__, exc, traceback.format_exc())
        stage.add('UNEXPECTED', 'BLOCKED', 'unexpected exception', error=stage.error)
    stage.extra.update(resource_snapshot())
    record = stage.result()
    write_json_exclusive(Path(run_dir) / ('%s.json' % name), record)
    return record


# ---------------------------------------------------------------- environment / resources

def read_text(path):
    try:
        return Path(path).read_text()
    except OSError:
        return None


def cpu_model():
    text = read_text('/proc/cpuinfo') or ''
    for line in text.splitlines():
        if line.lower().startswith('model name'):
            return line.split(':', 1)[1].strip()
    return None


def meminfo():
    out = {}
    for line in (read_text('/proc/meminfo') or '').splitlines():
        m = re.match(r'(\w+):\s+(\d+)\s*kB', line)
        if m:
            out[m.group(1)] = int(m.group(2)) * 1024
    return out


def cgroup_memory():
    """Return cgroup v2 / v1 memory limit and usage (bytes or None)."""
    info = dict(version=None, limit=None, current=None, peak=None)
    v2_max = read_text('/sys/fs/cgroup/memory.max')
    if v2_max is not None:
        info['version'] = 'v2'
        v = v2_max.strip()
        info['limit'] = None if v == 'max' else int(v)
        cur = read_text('/sys/fs/cgroup/memory.current')
        info['current'] = int(cur.strip()) if cur else None
        peak = read_text('/sys/fs/cgroup/memory.peak')
        info['peak'] = int(peak.strip()) if peak else None
        return info
    v1_limit = read_text('/sys/fs/cgroup/memory/memory.limit_in_bytes')
    if v1_limit is not None:
        info['version'] = 'v1'
        limit = int(v1_limit.strip())
        info['limit'] = None if limit >= 1 << 60 else limit
        cur = read_text('/sys/fs/cgroup/memory/memory.usage_in_bytes')
        info['current'] = int(cur.strip()) if cur else None
        peak = read_text('/sys/fs/cgroup/memory/memory.max_usage_in_bytes')
        info['peak'] = int(peak.strip()) if peak else None
    return info


def effective_available_memory():
    mem = meminfo()
    cg = cgroup_memory()
    avail = mem.get('MemAvailable')
    candidates = [avail] if avail is not None else []
    if cg['limit'] is not None and cg['current'] is not None:
        candidates.append(cg['limit'] - cg['current'])
    return (min(candidates) if candidates else None), mem, cg


def disk_report(paths):
    out = {}
    for label, path in paths.items():
        path = Path(path)
        probe = path
        while not probe.exists() and probe != probe.parent:
            probe = probe.parent
        usage = shutil.disk_usage(probe)
        out[label] = dict(path=str(path), probed=str(probe), device=os.stat(probe).st_dev,
                          free=usage.free, total=usage.total)
    return out


def installed_distributions():
    import importlib.metadata as md
    return {d.metadata['Name'].lower().replace('_', '-'): d.version for d in md.distributions()
            if d.metadata['Name']}


def resource_snapshot():
    snap = {}
    try:
        import resource
        snap['ru_maxrss_kib'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    except Exception:
        pass
    status = read_text('/proc/self/status') or ''
    m = re.search(r'VmHWM:\s+(\d+)\s*kB', status)
    if m:
        snap['vmhwm_kib'] = int(m.group(1))
    snap['cgroup_memory_peak_bytes'] = cgroup_memory().get('peak')
    snap['pid'] = os.getpid()
    return dict(resource=snap)


def dir_bytes(path):
    total = 0
    for p in Path(path).rglob('*'):
        if p.is_file() and not p.is_symlink():
            total += p.stat().st_size
    return total


PROCESS_T0 = time.monotonic()


def active_seconds(run_dir):
    """Sum of completed stage durations plus this process's running time (idle gaps between stages excluded)."""
    total = time.monotonic() - PROCESS_T0
    for p in Path(run_dir).glob('*.json'):
        try:
            rec = parse_strict(p.read_bytes())
        except Exception:
            continue
        if isinstance(rec, dict) and rec.get('experiment') == EXPERIMENT and 'elapsed_seconds' in rec:
            total += rec['elapsed_seconds']
    return total


def wall_cap_check(run_dir):
    used = active_seconds(run_dir)
    require(used <= WALL_CAP_SECONDS, 'cumulative active run time cap (3h) exceeded: %.0fs' % used)
    return used


# ---------------------------------------------------------------- upstream (read-only)

def upstream_state(path):
    path = Path(path).resolve()
    head = git(path, 'rev-parse', 'HEAD')
    porcelain = git(path, 'status', '--porcelain', '--ignored', '--untracked-files=all')
    lines = sorted(porcelain.splitlines())
    return dict(path=str(path), head=head, status_lines=lines,
                tracked_or_untracked_changes=[l for l in lines if not l.startswith('!!')])


def setup_upstream(path, run_dir=None):
    """Pin check + import path. No bytecode may be written into the upstream tree."""
    state = upstream_state(path)
    require(state['head'] == UPSTREAM_PIN, 'upstream HEAD %s != pin' % state['head'])
    require(not state['tracked_or_untracked_changes'],
            'upstream has tracked/untracked changes: %s' % state['tracked_or_untracked_changes'][:5])
    sys.dont_write_bytecode = True
    if run_dir is not None:
        sys.pycache_prefix = str(Path(run_dir) / 'pycache_redirect')
    if state['path'] not in sys.path:
        sys.path.insert(0, state['path'])
    return state


def upstream_unchanged(before):
    after = upstream_state(before['path'])
    return (after['head'] == before['head'] and after['status_lines'] == before['status_lines'], after)


def import_origins():
    import parcae_lm
    import receval.models.parcae as rp
    return dict(parcae_lm=str(Path(parcae_lm.__file__).resolve()), receval_models_parcae=str(Path(rp.__file__).resolve()))


# ---------------------------------------------------------------- fetch (A1)

def source_url(src, base=HF_BASE_URL):
    require(re.fullmatch(r'[0-9a-f]{40}', src['rev']) is not None, 'revision is not an immutable commit SHA')
    return '%s/%s/resolve/%s/%s' % (base.rstrip('/'), src['repo'], src['rev'], src['name'])


def download_verified(src, dest_dir, base=HF_BASE_URL, timeout=60):
    """Single attempt, streamed to .part, verified, then renamed. Never overwrites; never retries."""
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    final = dest_dir / src['name']
    require(not final.exists(), 'destination exists, not overwriting: %s' % final)
    part = dest_dir / (src['name'] + '.part')
    require(not part.exists(), 'stale partial file retained, not overwriting: %s' % part)
    url = source_url(src, base)
    request = urllib.request.Request(url, headers={'User-Agent': 'mythos-base-v01-b1'})
    h = hashlib.sha256()
    size = 0
    headers = {}
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp, open(part, 'xb') as out:
            for key in ('X-Repo-Commit', 'ETag', 'X-Linked-ETag', 'Content-Length', 'Content-Type'):
                if resp.headers.get(key) is not None:
                    headers[key] = resp.headers.get(key)
            status = resp.status
            final_host = urllib.parse.urlparse(resp.geturl()).netloc
            for chunk in iter(lambda: resp.read(1 << 20), b''):
                out.write(chunk)
                h.update(chunk)
                size += len(chunk)
            out.flush()
            os.fsync(out.fileno())
    except (urllib.error.URLError, OSError) as exc:
        raise Blocked('download failed for %s: %s' % (src['name'], exc))
    record = dict(url=url, http_status=status, final_host=final_host, response_headers=headers,
                  size=size, sha256=h.hexdigest(), expected_size=src['size'], expected_sha256=src['sha256'])
    commit = headers.get('X-Repo-Commit')
    if commit is not None and commit != src['rev']:
        rejected = dest_dir / (src['name'] + '.rejected')
        os.replace(part, rejected)
        record['rejected_as'] = str(rejected)
        raise Blocked('server reported commit %s != pinned %s' % (commit, src['rev']))
    if size != src['size'] or h.hexdigest() != src['sha256']:
        rejected = dest_dir / (src['name'] + '.rejected')
        os.replace(part, rejected)
        record['rejected_as'] = str(rejected)
        raise Blocked('size/sha256 mismatch for %s: got %d / %s' % (src['name'], size, h.hexdigest()))
    os.replace(part, final)
    record['path'] = str(final)
    return record


def load_sources(run_dir, rehearsal=False, fixture_dir=None):
    """Return (sources, expect). Fixtures are allowed only for explicit rehearsals."""
    if not rehearsal:
        return SOURCES, EXPECT
    require(fixture_dir is not None, 'rehearsal needs --fixture-dir')
    spec = parse_strict((Path(fixture_dir) / 'fixture_sources.json').read_bytes())
    return spec['sources'], spec['expect']


# ---------------------------------------------------------------- tokenizer (A6)

def tokenizer_identity(path, expected_vocab=32768, special_ids=(0, 1, 2)):
    raw = Path(path).read_bytes()
    doc = parse_strict(raw)
    model = doc['model']
    vocab = model['vocab']
    added = doc.get('added_tokens') or []
    merges = model.get('merges')
    union = {}
    for tok, idx in vocab.items():
        union[tok] = idx
    for a in added:
        if a['content'] in union and union[a['content']] != a['id']:
            raise Blocked('added token %r id disagrees with model vocab' % a['content'])
        union[a['content']] = a['id']
    ids = sorted(union.values())
    lower_collisions = len(union) - len({t.lower() for t in union})
    ident = dict(
        file_sha256=sha256_bytes(raw), file_size=len(raw), version=doc.get('version'),
        model_type=model.get('type'), model_vocab_entries=len(vocab), added_token_count=len(added),
        union_tokens=len(union), unique_ids=len(set(ids)),
        id_min=ids[0] if ids else None, id_max=ids[-1] if ids else None,
        ids_exactly_range=ids == list(range(expected_vocab)),
        case_sensitive_unique_tokens=len(union), lowercase_collisions_info=lower_collisions,
        special_added_tokens=[dict(id=a['id'], content=a['content'], special=a.get('special'))
                              for a in added if a.get('special')],
        specials_by_id={str(i): next((a['content'] for a in added if a['id'] == i), None) for i in special_ids},
        normalizer=doc.get('normalizer'), post_processor=doc.get('post_processor'),
        pre_tokenizer_type=(doc.get('pre_tokenizer') or {}).get('type'),
        decoder_type=(doc.get('decoder') or {}).get('type'),
        truncation=doc.get('truncation'), padding=doc.get('padding'),
        fingerprints=dict(
            vocab_by_id=sha256_canon(sorted(union.items(), key=lambda kv: kv[1])),
            merges=sha256_canon(merges), added_tokens=sha256_canon(added),
            normalizer=sha256_canon(doc.get('normalizer')), pre_tokenizer=sha256_canon(doc.get('pre_tokenizer')),
            post_processor=sha256_canon(doc.get('post_processor')), decoder=sha256_canon(doc.get('decoder')),
            model_config=sha256_canon({k: v for k, v in model.items() if k not in ('vocab', 'merges')})),
        merges_count=len(merges) if merges is not None else None)
    return ident


def check_tokenizer_identity(stage, ident, expected_vocab=32768, special_ids=(0, 1, 2)):
    stage.ok('A6.model_bpe', ident['model_type'] == 'BPE', 'tokenizer model is BPE', fail=Blocked, model_type=ident['model_type'])
    stage.ok('A6.vocab', ident['union_tokens'] == expected_vocab and ident['unique_ids'] == expected_vocab
             and ident['ids_exactly_range'], 'case-sensitive unique tokens and ids are exactly 0..%d' % (expected_vocab - 1),
             fail=Blocked, union_tokens=ident['union_tokens'], unique_ids=ident['unique_ids'],
             id_min=ident['id_min'], id_max=ident['id_max'])
    present = {s['id'] for s in ident['special_added_tokens']}
    stage.ok('A6.specials', set(special_ids) <= present, 'special tokens exist at ids %s' % (special_ids,),
             fail=Blocked, special_added_tokens=ident['special_added_tokens'])
    stage.ok('A6.components', ident['normalizer'] is None and ident['post_processor'] is None
             and ident['decoder_type'] == 'ByteLevel' and ident['truncation'] is None and ident['padding'] is None,
             'normalizer/post_processor null, ByteLevel decoder, no truncation/padding', fail=Blocked,
             normalizer=ident['normalizer'], post_processor=ident['post_processor'],
             decoder_type=ident['decoder_type'], truncation=ident['truncation'], padding=ident['padding'])


def load_tokenizer(path):
    from tokenizers import Tokenizer
    return Tokenizer.from_file(str(path))


def encode_ids(tok, text):
    return list(tok.encode(text, add_special_tokens=False).ids)


def decode_ids(tok, ids):
    return tok.decode(list(ids), skip_special_tokens=False)


def run_probes(tok, probes, vocab_size):
    rows = []
    for i, text in enumerate(probes):
        ids = encode_ids(tok, text)
        try:
            back = decode_ids(tok, ids)
            err = None
        except Exception as exc:  # recorded, not cleaned up
            back, err = None, repr(exc)
        rows.append(dict(index=i, text=text, ids=ids, in_range=all(0 <= t < vocab_size for t in ids),
                         round_trip_equal=(back == text), decoded=back, error=err,
                         ids_sha256=sha256_canon(ids)))
    return rows


# ---------------------------------------------------------------- state-dict accounting (A2/A3)

PREFIXES = ('module.', '_orig_mod.', 'model.')


def map_prefix(keys):
    """Return (mapping old->new, applied_prefix). Only a single uniform prefix is allowed."""
    keys = list(keys)
    starts = [p for p in PREFIXES if any(k.startswith(p) for k in keys)]
    if not starts:
        return {k: k for k in keys}, None
    require(len(starts) == 1, 'multiple/stacked prefixes present: %s' % starts)
    prefix = starts[0]
    require(all(k.startswith(prefix) for k in keys), 'prefix %r not uniform over all keys' % prefix)
    mapping = {k: k[len(prefix):] for k in keys}
    require(len(set(mapping.values())) == len(mapping), 'prefix removal produces key collisions')
    return mapping, prefix


def account_state_dict(sd, expected, tied_pairs=(('transformer.wte.weight', 'lm_head.weight'),)):
    """Compare a loaded tensor dict with the model's expected state_dict (name -> (shape, dtype)).

    Returns (report, mapped_sd). Raises Blocked for structure/coverage/shape/dtype problems and
    Failed for non-finite values or inconsistent shared tensors.
    """
    import torch
    require(isinstance(sd, dict) and sd, 'weights file is not a non-empty dict')
    bad_values = [k for k, v in sd.items() if not isinstance(v, torch.Tensor)]
    require(not bad_values, 'weights file has non-tensor entries: %s' % bad_values[:5])
    require(all(isinstance(k, str) for k in sd), 'non-string keys in weights file')
    mapping, prefix = map_prefix(sd.keys())
    mapped = {mapping[k]: v for k, v in sd.items()}
    exp_keys, got_keys = set(expected), set(mapped)
    missing, unexpected = sorted(exp_keys - got_keys), sorted(got_keys - exp_keys)
    shape_mismatch = [dict(key=k, expected=list(expected[k][0]), got=list(mapped[k].shape))
                      for k in sorted(exp_keys & got_keys) if tuple(mapped[k].shape) != tuple(expected[k][0])]
    dtype_counts = {}
    for v in mapped.values():
        dtype_counts[str(v.dtype)] = dtype_counts.get(str(v.dtype), 0) + 1
    dtype_mismatch = [dict(key=k, expected=str(expected[k][1]), got=str(mapped[k].dtype))
                      for k in sorted(exp_keys & got_keys) if mapped[k].dtype != expected[k][1]]
    report = dict(prefix_applied=prefix, file_entries=len(sd), expected_entries=len(expected),
                  coverage=(len(exp_keys & got_keys) / len(exp_keys)) if exp_keys else None,
                  missing=missing, unexpected=unexpected, shape_mismatch=shape_mismatch,
                  dtype_counts=dtype_counts, dtype_mismatch=dtype_mismatch)
    require(not missing and not unexpected, 'key mismatch: missing=%s unexpected=%s' % (missing[:5], unexpected[:5]))
    require(not shape_mismatch, 'shape mismatch: %s' % shape_mismatch[:3])
    require(not dtype_mismatch, 'dtype differs from the constructed model (no automatic cast): %s' % dtype_mismatch[:3])
    nonfinite = [k for k, v in mapped.items() if v.is_floating_point() and not bool(torch.isfinite(v).all())]
    report['nonfinite'] = nonfinite
    if nonfinite:
        raise Failed('non-finite tensors in weights file: %s' % nonfinite[:5])
    tied = []
    for a, b in tied_pairs:
        if a in mapped and b in mapped:
            same_storage = mapped[a].data_ptr() == mapped[b].data_ptr()
            equal = bool(torch.equal(mapped[a], mapped[b]))
            tied.append(dict(a=a, b=b, same_storage_in_file=same_storage, equal=equal))
            if not equal:
                report['tied'] = tied
                raise Failed('shared weights %s / %s differ in the file' % (a, b))
    report['tied'] = tied
    return report, mapped


# ---------------------------------------------------------------- model construction / loading

def classify_config_differences(cfg_a, cfg_b):
    """Differences between two dataclass configs, split into label-only and effective."""
    a, b = dataclasses.asdict(cfg_a), dataclasses.asdict(cfg_b)
    label, effective = [], []
    for key in sorted(set(a) | set(b)):
        va, vb = a.get(key, '<absent>'), b.get(key, '<absent>')
        if json.dumps(va, sort_keys=True, default=str) == json.dumps(vb, sort_keys=True, default=str):
            continue
        row = dict(field=key, loaded=va, builtin=vb)
        (label if key in LABEL_ONLY_CONFIG_FIELDS else effective).append(row)
    derived = {}
    for attr in ('n_layer', 'head_size', 'n_head', 'n_query_groups', 'padded_vocab_size'):
        derived[attr] = dict(loaded=getattr(cfg_a, attr, None), builtin=getattr(cfg_b, attr, None))
    derived_diff = [k for k, v in derived.items() if v['loaded'] != v['builtin']]
    return dict(label_only=label, effective=effective, derived=derived, derived_differences=derived_diff)


def build_config(config_path, expect):
    """Construct ParcaeConfig from the verified original JSON bytes (no silent field dropping)."""
    from parcae_lm.models.config import RoPESettings  # noqa: F401  (import check)
    from parcae_lm.models.parcae import ParcaeConfig
    doc = parse_strict(Path(config_path).read_bytes())
    class_name = doc.pop('_class_name', None)
    require(class_name == 'ParcaeConfig', '_class_name is %r' % class_name)
    field_names = {f.name for f in dataclasses.fields(ParcaeConfig)}
    unknown = sorted(set(doc) - field_names)
    require(not unknown, 'config.json has fields unknown to the pinned ParcaeConfig: %s' % unknown)
    require(isinstance(doc.get('rope_settings'), dict), 'rope_settings missing or not an object')
    cfg = ParcaeConfig(**doc)
    return cfg, doc


def check_config_facts(stage, cfg, expect):
    wrong = {}
    for key, value in expect['config'].items():
        if getattr(cfg, key, '<absent>') != value:
            wrong[key] = dict(expected=value, got=getattr(cfg, key, '<absent>'))
    rope = dataclasses.asdict(cfg.rope_settings)
    if rope != expect['rope']:
        wrong['rope_settings'] = dict(expected=expect['rope'], got=rope)
    stage.ok('A4.facts', not wrong, 'loaded config equals the facts given in the authorization',
             fail=Blocked, differences=wrong)
    builtin = None
    try:
        import parcae_lm
        builtin = parcae_lm.create_config(expect['builtin_config'], **expect.get('builtin_overrides', {}))
    except Exception as exc:
        stage.add('A4.builtin', 'BLOCKED', 'built-in config unavailable', error=repr(exc))
        raise Blocked('built-in config %r unavailable' % expect['builtin_config'])
    diff = classify_config_differences(cfg, builtin)
    stage.extra['config_diff'] = diff
    stage.ok('A4.diff', not diff['effective'] and not diff['derived_differences'],
             'no unexplained effective difference from the built-in %s config' % expect['builtin_config'],
             fail=Blocked, effective=diff['effective'], derived_differences=diff['derived_differences'],
             label_only=diff['label_only'])


def set_runtime(torch):
    torch.set_num_threads(1)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        pass
    torch.use_deterministic_algorithms(True)


def load_model(stage, config_path, weights_path, expect, tag='A'):
    """Construct, account, load strictly, verify. Returns (model, details)."""
    import torch
    set_runtime(torch)
    from receval.models.parcae import ModelingParcae
    cfg, doc = build_config(config_path, expect)
    torch.manual_seed(20261031)
    model = ModelingParcae(cfg)
    model.eval()
    expected = {k: (tuple(v.shape), v.dtype) for k, v in model.state_dict().items()}
    expected_freqs = model.freqs_cis.detach().clone()
    n_param_tensors = len(list(model.parameters()))
    n_param_elements = sum(p.numel() for p in model.parameters())
    shared_before = model.lm_head.weight.data_ptr() == model.transformer.wte.weight.data_ptr()
    try:
        sd = torch.load(str(weights_path), map_location='cpu', weights_only=True)
    except Exception as exc:
        stage.add(tag + '2', 'BLOCKED', 'weights_only torch.load', error=repr(exc))
        raise Blocked('weights_only load failed: %r' % (exc,))
    stage.add(tag + '2', 'PASS', 'weights_only torch.load into a dict of tensors', entries=len(sd))
    report, mapped = account_state_dict(sd, expected)
    stage.extra.setdefault('state_accounting', {})[tag] = report
    stage.add(tag + '3.accounting', 'PASS', 'keys/shapes/dtype/finite/shared accounted',
              entries=report['file_entries'], coverage=report['coverage'], dtype_counts=report['dtype_counts'],
              prefix_applied=report['prefix_applied'], tied=report['tied'])
    freq_diff = float((mapped['freqs_cis'].float() - expected_freqs.float()).abs().max())
    stage.extra.setdefault('rope_check', {})[tag] = dict(max_abs_diff=freq_diff, shape=list(expected_freqs.shape))
    if not freq_diff <= 1e-6:
        stage.add(tag + '5', 'BLOCKED', 'freqs_cis differs from native recomputation', max_abs_diff=freq_diff)
        raise Blocked('freqs_cis max abs diff %g > 1e-6' % freq_diff)
    stage.add(tag + '5', 'PASS', 'loaded freqs_cis equals native recomputation (<=1e-6)', max_abs_diff=freq_diff)
    try:
        incompatible = model.load_state_dict(mapped, strict=True)
    except Exception as exc:
        stage.add(tag + '3.load', 'BLOCKED', 'strict load_state_dict', error=repr(exc))
        raise Blocked('strict load_state_dict failed: %r' % (exc,))
    shared_after = model.lm_head.weight.data_ptr() == model.transformer.wte.weight.data_ptr()
    if not (shared_before and shared_after):
        stage.add(tag + '3.shared', 'FAIL', 'expected tied lm_head/wte sharing lost', before=shared_before, after=shared_after)
        raise Failed('tied weight sharing not preserved')
    after = model.state_dict()
    identical = all(bool(torch.equal(after[k], mapped[k])) and after[k].dtype == mapped[k].dtype for k in mapped)
    if not identical:
        raise Failed('model tensors differ from file after strict load')
    stage.add(tag + '3.shared', 'PASS', 'tied lm_head/wte sharing preserved; loaded tensors bit-equal to file',
              shared_before=shared_before, shared_after=shared_after,
              missing=list(incompatible.missing_keys), unexpected=list(incompatible.unexpected_keys))
    derived = expect['derived']
    stage.extra.setdefault('derived_vs_actual', {})[tag] = dict(
        parameter_tensors=dict(derived=derived['parameter_tensors'], actual=n_param_tensors),
        parameter_elements=dict(derived=derived['parameter_elements'], actual=n_param_elements),
        state_dict_entries=dict(derived=derived['state_dict_entries'], actual=len(expected)),
        note='source-derived numbers are reported as findings only; the key/shape check is the gate')
    model.eval()
    return model, dict(parameter_tensors=n_param_tensors, parameter_elements=n_param_elements,
                       state_dict_entries=len(expected))


def check_backend(stage, cfg_attn_impl='flash'):
    import torch
    import parcae_lm.attention_backends.flash_attention as fa
    from parcae_lm.attention_backends.interface import select_attention_implementation
    fn = select_attention_implementation(cfg_attn_impl)
    cuda = torch.cuda.is_available()
    ok = (not cuda) and fa.HAS_FA3 is False and fa._override_impl is None \
        and getattr(getattr(fn, 'func', None), '__name__', None) == 'attention_flash'
    stage.ok('A7', ok, 'CPU, no FA3, no attention override; flash resolves to the SDPA fallback',
             fail=Blocked, cuda_available=cuda, has_fa3=fa.HAS_FA3, override=fa._override_impl,
             selected=getattr(getattr(fn, 'func', None), '__name__', None), attn_impl=cfg_attn_impl,
             sdpa_backend_for_acceptance='SDPBackend.MATH')


# ---------------------------------------------------------------- generation, checks (A8-A10)

def math_ctx():
    from torch.nn.attention import SDPBackend, sdpa_kernel
    return sdpa_kernel(SDPBackend.MATH)


def native_vs_generation_logits(model, ids, seed):
    import torch
    x = torch.tensor([ids], dtype=torch.long)
    with torch.no_grad(), math_ctx():
        torch.manual_seed(seed)
        native = model(x, return_logits=True, num_steps_pair=[0, NUM_STEPS])['logits'].detach().clone()
        torch.manual_seed(seed)
        engineered = model.forward_for_generation(x, num_steps=NUM_STEPS)['logits'].detach().clone()
    return native, engineered


def generate_new_tokens(model, ids, seed):
    import torch
    x = torch.tensor([ids], dtype=torch.long)
    torch.manual_seed(seed)
    with torch.no_grad(), math_ctx():
        out = model.generate(x, max_new_tokens=MAX_NEW_TOKENS, temperature=1.0, top_k=None, top_p=None,
                             do_sample=False, num_steps=NUM_STEPS, use_cache=False)
    require(tuple(out.shape) == (1, len(ids) + MAX_NEW_TOKENS), 'unexpected generate output shape %s' % (tuple(out.shape),), Failed)
    return out[0, len(ids):].tolist()


def split_at_eos(new_ids, eos_id=EOS_ID):
    pos = new_ids.index(eos_id) if eos_id in new_ids else None
    return pos, (new_ids[:pos] if pos is not None else list(new_ids))


def auto_checks(tok, cont_ids):
    """Degeneration checks on the effective continuation. No cleaning, no trimming."""
    counts = {}
    for i in range(len(cont_ids) - 3):
        g = tuple(cont_ids[i:i + 4])
        counts[g] = counts.get(g, 0) + 1
    max_4gram = max(counts.values()) if counts else 0
    run = best = 0
    prev = None
    for t in cont_ids:
        run = run + 1 if t == prev else 1
        prev = t
        best = max(best, run)
    try:
        text = decode_ids(tok, cont_ids)
        decode_error = None
    except Exception as exc:
        text, decode_error = None, repr(exc)
    has_fffd = (text is not None) and ('�' in text)
    rules = dict(
        min_16_new_tokens=len(cont_ids) >= 16,
        no_4gram_3x=max_4gram < 3,
        no_token_run_6=best < 6,
        decodes_without_error=decode_error is None,
        no_u_fffd=(text is not None) and not has_fffd)
    return dict(passed=all(rules.values()), rules=rules, length=len(cont_ids), max_4gram_count=max_4gram,
                longest_token_run=best, decode_error=decode_error, text=text,
                ends_with_u_fffd_note=bool(text) and text.endswith('�'))


def prompt_record(tok, spec, model, pass_name, deadline_check=None):
    idx = spec['id']
    ids = encode_ids(tok, spec['text'])
    if len(ids) > MAX_PROMPT_TOKENS:
        raise Blocked('prompt %d encodes to %d tokens (> %d)' % (idx, len(ids), MAX_PROMPT_TOKENS))
    if deadline_check:
        deadline_check()
    seed = PROMPT_SEED_BASE + idx
    t = time.monotonic()
    new_ids = generate_new_tokens(model, ids, seed)
    elapsed = time.monotonic() - t
    eos_pos, cont = split_at_eos(new_ids)
    checks = auto_checks(tok, cont)
    full_text = decode_ids(tok, new_ids)
    return dict(pass_name=pass_name, id=idx, prompt=spec['text'], prompt_ids=ids, prompt_token_count=len(ids),
                prompt_ids_sha256=sha256_canon(ids), seed=seed, new_ids=new_ids, new_ids_sha256=sha256_canon(new_ids),
                eos_position=eos_pos, continuation_ids=cont, text_all_64_tokens=full_text,
                text_continuation=checks['text'], auto=checks, seconds=round(elapsed, 3),
                note='native generate has no early stop: all 64 tokens were computed; scoring uses the part before the first EOS')


def tensor_sha256(t):
    import numpy as np
    arr = np.ascontiguousarray(t.detach().cpu().numpy())
    return sha256_bytes(arr.tobytes())


# ---------------------------------------------------------------- package (A11)

def save_package(model, package_dir, config_src, tokenizer_src, provenance):
    import torch
    package_dir = Path(package_dir)
    package_dir.mkdir(parents=True, exist_ok=False)
    weights = package_dir / 'pytorch_model.bin'
    tmp = package_dir / 'pytorch_model.bin.tmp'
    torch.save(model.state_dict(), tmp)
    os.replace(tmp, weights)
    shutil.copyfile(config_src, package_dir / 'config.json')
    shutil.copyfile(tokenizer_src, package_dir / 'tokenizer.json')
    manifest = dict(experiment=EXPERIMENT, kind='local inference package, not for redistribution',
                    license_status='UNCONFIRMED for weights and tokenizer; research use only', provenance=provenance,
                    files={n: dict(size=(package_dir / n).stat().st_size, sha256=sha256_file(package_dir / n))
                           for n in ('pytorch_model.bin', 'config.json', 'tokenizer.json')})
    write_json_exclusive(package_dir / 'package_manifest.json', manifest)
    return manifest


def process_identity():
    start_ticks = None
    stat = read_text('/proc/self/stat')
    if stat:
        start_ticks = int(stat.rsplit(')', 1)[1].split()[19])
    return dict(pid=os.getpid(), ppid=os.getppid(), argv=list(sys.argv), executable=sys.executable,
                start_time_ticks=start_ticks, wall_time=time.time())
