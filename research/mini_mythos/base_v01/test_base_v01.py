"""Fixture tests for the B1 helpers and a tiny-model REHEARSAL of the whole stage chain.

Nothing here is B1 evidence: the rehearsal uses a random tiny model and a toy tokenizer.
Run with the environment that has torch, tokenizers and a checkout of the pinned upstream:
    B1_UPSTREAM=/path/to/parcae python -m unittest research/mini_mythos/base_v01/test_base_v01.py
"""
import dataclasses
import hashlib
import http.server
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('MKL_NUM_THREADS', '1')
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.dont_write_bytecode = True
import base_v01 as B  # noqa: E402

UPSTREAM = os.environ.get('B1_UPSTREAM', '/workspaces/mythos-parcae-pinned')
try:
    import torch
    import tokenizers
    HAVE_STACK = Path(UPSTREAM).is_dir()
except Exception:  # pragma: no cover
    HAVE_STACK = False


# ------------------------------------------------------------------ pure helpers

class HelperTests(unittest.TestCase):
    def test_parse_strict_rejects_duplicates_and_nan(self):
        with self.assertRaises(ValueError):
            B.parse_strict(b'{"a":1,"a":2}')
        with self.assertRaises(ValueError):
            B.parse_strict(b'{"a":NaN}')
        self.assertEqual(B.parse_strict(b'{"a":[1,2]}'), {'a': [1, 2]})

    def test_write_json_exclusive_never_overwrites(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'x.json'
            B.write_json_exclusive(p, {'v': 1})
            with self.assertRaises(FileExistsError):
                B.write_json_exclusive(p, {'v': 2})
            self.assertEqual(json.loads(p.read_text()), {'v': 1})
            self.assertEqual(sorted(os.listdir(d)), ['x.json'])

    def test_pinned_constants_are_wellformed(self):
        for src in B.SOURCES.values():
            self.assertRegex(src['sha256'], r'^[0-9a-f]{64}$')
            self.assertRegex(src['rev'], r'^[0-9a-f]{40}$')
        self.assertEqual(B.SOURCES['model']['size'], 578361537)
        self.assertEqual(B.SOURCES['config']['size'], 1741)
        self.assertEqual(B.SOURCES['tokenizer']['size'], 2326980)
        self.assertEqual(B.UPSTREAM_PIN, '69284c13746e849104f738d6d1a347b1f457df76')

    def test_floating_revision_is_rejected(self):
        with self.assertRaises(B.Blocked):
            B.source_url(dict(repo='a/b', rev='main', name='f'))

    def test_prompts_frozen_file(self):
        doc = json.loads((HERE / 'prompts_v1.json').read_text())
        self.assertEqual([p['id'] for p in doc['prompts']], list(range(1, 13)))
        self.assertEqual(doc['prompts'][6]['text'], 'def fibonacci(n):\n    """Return the nth Fibonacci number."""\n')
        self.assertEqual(doc['prompts'][0]['text'], 'The capital of France is')
        self.assertEqual(doc['prompts'][11]['text'], 'One, two, three, four, five, six, seven,')

    def test_probes_file(self):
        probes = json.loads((HERE / 'tokenizer_probes_v1.json').read_text())['probes']
        self.assertGreaterEqual(len(probes), 30)
        self.assertEqual(len(probes), len(set(probes)))

    def test_split_at_eos(self):
        self.assertEqual(B.split_at_eos([5, 6, 1, 7, 8]), (2, [5, 6]))
        self.assertEqual(B.split_at_eos([5, 6, 7]), (None, [5, 6, 7]))
        self.assertEqual(B.split_at_eos([1, 5]), (0, []))

    def test_worst_status_ordering(self):
        self.assertEqual(B.worst(['PASS', 'NOT TESTED']), 'NOT TESTED')
        self.assertEqual(B.worst(['PASS', 'BLOCKED', 'NOT TESTED']), 'BLOCKED')
        self.assertEqual(B.worst(['PASS', 'FAIL', 'BLOCKED']), 'FAIL')
        self.assertEqual(B.worst(['PASS']), 'PASS')

    def test_exception_without_a_recorded_check_is_still_blocked_or_fail(self):
        with tempfile.TemporaryDirectory() as d:
            def blocked(stage):
                stage.add('x', 'PASS', 't')
                raise B.Blocked('why')

            def failed(stage):
                raise B.Failed('why')
            self.assertEqual(B.run_stage('s1', ['x', 'y'], d, blocked)['status'], 'BLOCKED')
            self.assertEqual(B.run_stage('s2', ['x'], d, failed)['status'], 'FAIL')

    def test_stage_marks_unreached_as_not_tested(self):
        s = B.Stage('x', ['a', 'b'])
        s.add('a', 'PASS', 't')
        r = s.result()
        self.assertEqual(r['status'], 'NOT TESTED')
        self.assertEqual({c['id']: c['status'] for c in r['checks']}, {'a': 'PASS', 'b': 'NOT TESTED'})

    def test_prefix_mapping(self):
        m, p = B.map_prefix(['module.a', 'module.b'])
        self.assertEqual((m, p), ({'module.a': 'a', 'module.b': 'b'}, 'module.'))
        self.assertEqual(B.map_prefix(['a', 'b'])[1], None)
        with self.assertRaises(B.Blocked):
            B.map_prefix(['module.a', 'b'])
        with self.assertRaises(B.Blocked):
            B.map_prefix(['module.a', '_orig_mod.b'])
        with self.assertRaises(B.Blocked):
            B.map_prefix(['model.a', 'a'])


class AutoCheckTests(unittest.TestCase):
    class Tok:
        def decode(self, ids, skip_special_tokens=False):
            assert skip_special_tokens is False
            return ''.join('�' if i == 999 else chr(97 + (i % 26)) for i in ids)

    def check(self, ids):
        return B.auto_checks(self.Tok(), ids)

    def test_good_sequence_passes(self):
        ids = [i for i in range(40)]
        self.assertTrue(self.check(ids)['passed'])

    def test_too_short(self):
        self.assertFalse(self.check(list(range(15)))['rules']['min_16_new_tokens'])
        self.assertTrue(self.check(list(range(16)))['rules']['min_16_new_tokens'])

    def test_4gram_threshold(self):
        two = [1, 2, 3, 4] * 2 + list(range(100, 120))
        three = [1, 2, 3, 4] * 3 + list(range(100, 120))
        self.assertTrue(self.check(two)['rules']['no_4gram_3x'])
        self.assertFalse(self.check(three)['rules']['no_4gram_3x'])

    def test_run_threshold(self):
        base = list(range(100, 120))
        self.assertTrue(self.check([7] * 5 + base)['rules']['no_token_run_6'])
        self.assertFalse(self.check([7] * 6 + base)['rules']['no_token_run_6'])

    def test_u_fffd_is_never_forgiven(self):
        ids = list(range(30)) + [999]
        r = self.check(ids)
        self.assertFalse(r['rules']['no_u_fffd'])
        self.assertFalse(r['passed'])
        self.assertTrue(r['ends_with_u_fffd_note'])
        mid = list(range(10)) + [999] + list(range(20))
        self.assertFalse(self.check(mid)['passed'])


class AccountingTests(unittest.TestCase):
    def setUp(self):
        if not HAVE_STACK:
            self.skipTest('torch/tokenizers/upstream not available')
        self.expected = {'a.weight': ((2, 3), torch.float32), 'b.weight': ((4,), torch.float32),
                         'lm_head.weight': ((2, 3), torch.float32), 'transformer.wte.weight': ((2, 3), torch.float32)}

    def good(self):
        w = torch.randn(2, 3)
        return {'a.weight': torch.randn(2, 3), 'b.weight': torch.randn(4), 'lm_head.weight': w,
                'transformer.wte.weight': w}

    def test_exact_match(self):
        report, mapped = B.account_state_dict(self.good(), self.expected)
        self.assertEqual(report['coverage'], 1.0)
        self.assertEqual(report['tied'][0]['equal'], True)

    def test_missing_unexpected_shape_dtype(self):
        sd = self.good()
        del sd['b.weight']
        with self.assertRaises(B.Blocked):
            B.account_state_dict(sd, self.expected)
        sd = self.good()
        sd['extra'] = torch.zeros(1)
        with self.assertRaises(B.Blocked):
            B.account_state_dict(sd, self.expected)
        sd = self.good()
        sd['b.weight'] = torch.zeros(5)
        with self.assertRaises(B.Blocked):
            B.account_state_dict(sd, self.expected)
        sd = self.good()
        sd['b.weight'] = sd['b.weight'].to(torch.bfloat16)
        with self.assertRaises(B.Blocked):
            B.account_state_dict(sd, self.expected)

    def test_nonfinite_and_tied_mismatch_fail(self):
        sd = self.good()
        sd['b.weight'][0] = float('nan')
        with self.assertRaises(B.Failed):
            B.account_state_dict(sd, self.expected)
        sd = self.good()
        sd['lm_head.weight'] = sd['lm_head.weight'] + 1.0
        with self.assertRaises(B.Failed):
            B.account_state_dict(sd, self.expected)

    def test_prefix_is_mapped_and_recorded(self):
        sd = {'module.' + k: v for k, v in self.good().items()}
        report, mapped = B.account_state_dict(sd, self.expected)
        self.assertEqual(report['prefix_applied'], 'module.')
        self.assertEqual(set(mapped), set(self.expected))

    def test_non_tensor_entries_blocked(self):
        sd = self.good()
        sd['b.weight'] = [1.0]
        with self.assertRaises(B.Blocked):
            B.account_state_dict(sd, self.expected)


# ------------------------------------------------------------------ tokenizer + download fixtures

def make_tiny_tokenizer(path, vocab=512):
    from tokenizers import Tokenizer, decoders, models, pre_tokenizers, trainers
    tok = Tokenizer(models.BPE())
    tok.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
    tok.decoder = decoders.ByteLevel()
    prompts = [p['text'] for p in json.loads((HERE / 'prompts_v1.json').read_text())['prompts']]
    probes = json.loads((HERE / 'tokenizer_probes_v1.json').read_text())['probes']
    corpus = (prompts + probes + ['the quick brown fox jumps over the lazy dog and the cat sat on the mat '] * 20) * 30
    trainer = trainers.BpeTrainer(vocab_size=vocab, special_tokens=['<bos>', '<eos>', '<pad>'],
                                  initial_alphabet=pre_tokenizers.ByteLevel.alphabet(), show_progress=False)
    tok.train_from_iterator(corpus, trainer)
    tok.save(str(path))
    return tok


class TokenizerTests(unittest.TestCase):
    def setUp(self):
        if not HAVE_STACK:
            self.skipTest('tokenizers not available')
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'tokenizer.json'
        self.tok = make_tiny_tokenizer(self.path, 512)

    def tearDown(self):
        self.tmp.cleanup()

    def test_identity_and_checks(self):
        ident = B.tokenizer_identity(self.path, 512, (0, 1, 2))
        self.assertEqual(ident['model_type'], 'BPE')
        self.assertEqual(ident['union_tokens'], 512)
        self.assertTrue(ident['ids_exactly_range'])
        self.assertEqual(ident['decoder_type'], 'ByteLevel')
        stage = B.Stage('t', [])
        B.check_tokenizer_identity(stage, ident, 512, (0, 1, 2))
        self.assertTrue(all(c['status'] == 'PASS' for c in stage.checks.values()))
        stage2 = B.Stage('t', [])
        with self.assertRaises(B.Blocked):
            B.check_tokenizer_identity(stage2, ident, 600, (0, 1, 2))

    def test_probe_round_trip_uses_no_special_tokens_and_keeps_specials(self):
        probes = json.loads((HERE / 'tokenizer_probes_v1.json').read_text())['probes']
        tok = B.load_tokenizer(self.path)
        rows = B.run_probes(tok, probes, 512)
        self.assertTrue(all(r['round_trip_equal'] and r['in_range'] for r in rows), [r['index'] for r in rows if not r['round_trip_equal']])
        self.assertEqual(B.encode_ids(tok, 'hello')[:1] != [0], True)  # no BOS added


class _Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


class FetchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.rev = 'c' * 40
        payload_dir = root / 'srv' / 'o' / 'r' / 'resolve' / self.rev
        payload_dir.mkdir(parents=True)
        self.data = b'hello pinned bytes' * 100
        (payload_dir / 'f.bin').write_bytes(self.data)
        handler = lambda *a, **k: _Handler(*a, directory=str(root / 'srv'), **k)  # noqa: E731
        self.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = 'http://127.0.0.1:%d' % self.server.server_address[1]
        self.root = root

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.tmp.cleanup()

    def src(self, **kw):
        s = dict(repo='o/r', rev=self.rev, name='f.bin', size=len(self.data), sha256=hashlib.sha256(self.data).hexdigest())
        s.update(kw)
        return s

    def test_good_download_verified_and_not_overwritten(self):
        out = self.root / 'dl'
        rec = B.download_verified(self.src(), out, base=self.base)
        self.assertEqual(rec['sha256'], hashlib.sha256(self.data).hexdigest())
        self.assertEqual((out / 'f.bin').read_bytes(), self.data)
        with self.assertRaises(B.Blocked):
            B.download_verified(self.src(), out, base=self.base)

    def test_wrong_hash_is_rejected_and_kept_as_rejected(self):
        out = self.root / 'dl2'
        with self.assertRaises(B.Blocked):
            B.download_verified(self.src(sha256='0' * 64), out, base=self.base)
        self.assertFalse((out / 'f.bin').exists())
        self.assertTrue((out / 'f.bin.rejected').exists())

    def test_wrong_size_and_missing_file(self):
        out = self.root / 'dl3'
        with self.assertRaises(B.Blocked):
            B.download_verified(self.src(size=5), out, base=self.base)
        with self.assertRaises(B.Blocked):
            B.download_verified(self.src(name='nope.bin'), self.root / 'dl4', base=self.base)
        self.assertFalse((self.root / 'dl4' / 'nope.bin').exists())


# ------------------------------------------------------------------ rehearsal of the whole chain

TINY_OVERRIDES = dict(block_size=128, vocab_size=512, n_embd=64, intermediate_size=256, num_attention_heads=4,
                      num_key_value_heads=4, recurrent_embedding_dimension=64,
                      recurrent_intermediation_embedding_dimension=256)


def make_rehearsal_fixture(root):
    sys.path.insert(0, UPSTREAM)
    import parcae_lm
    from receval.models.parcae import ModelingParcae
    root = Path(root)
    model_rev, tok_rev = 'a' * 40, 'b' * 40
    mdir = root / 'Fixture' / 'tiny-model' / 'resolve' / model_rev
    tdir = root / 'Fixture' / 'tiny-tok' / 'resolve' / tok_rev
    mdir.mkdir(parents=True)
    tdir.mkdir(parents=True)
    make_tiny_tokenizer(tdir / 'tokenizer.json', 512)
    cfg = parcae_lm.create_config('parcae-small-140m', **TINY_OVERRIDES)
    doc = dataclasses.asdict(cfg)
    doc['_class_name'] = 'ParcaeConfig'
    (mdir / 'config.json').write_text(json.dumps(doc, indent=2) + '\n')
    torch.manual_seed(5)
    model = ModelingParcae(cfg)
    with torch.no_grad():
        for p in model.parameters():
            p.add_(0.05 * torch.randn_like(p))
    torch.save(model.state_dict(), mdir / 'pytorch_model.bin')

    def entry(repo, rev, path):
        return dict(repo=repo, rev=rev, name=path.name, size=path.stat().st_size, sha256=B.sha256_file(path))
    sources = dict(model=entry('Fixture/tiny-model', model_rev, mdir / 'pytorch_model.bin'),
                   config=entry('Fixture/tiny-model', model_rev, mdir / 'config.json'),
                   tokenizer=entry('Fixture/tiny-tok', tok_rev, tdir / 'tokenizer.json'))
    expect = json.loads(json.dumps(B.EXPECT))
    expect['vocab_size'] = 512
    expect['config'].update(n_embd=64, intermediate_size=256, vocab_size=512, padded_vocab_size=512,
                            num_attention_heads=4, num_key_value_heads=4)
    expect['builtin_overrides'] = TINY_OVERRIDES
    expect['derived'] = dict(parameter_tensors=0, parameter_elements=0, state_dict_entries=0)
    (root / 'fixture_sources.json').write_text(json.dumps(dict(sources=sources, expect=expect), indent=2))
    return root


def cli(*args, check=False):
    env = dict(os.environ)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    return subprocess.run([sys.executable, str(HERE / 'run_base.py'), *args], capture_output=True, text=True, env=env)


class RehearsalChainTests(unittest.TestCase):
    """Whole chain on a random tiny model; each stage is a separate process. NOT B1 evidence."""

    @classmethod
    def setUpClass(cls):
        if not HAVE_STACK:
            raise unittest.SkipTest('torch/tokenizers/upstream not available')
        cls.tmp = tempfile.TemporaryDirectory()
        cls.fixture = make_rehearsal_fixture(Path(cls.tmp.name) / 'fixture')
        cls.evidence = Path(cls.tmp.name) / 'evidence'
        cls.repo = HERE.parents[2]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def stage(self, run_dir, name):
        return json.loads((Path(run_dir) / ('%s.json' % name)).read_text())

    def test_full_chain(self):
        r = cli('env-check', '--rehearsal', '--fixture-dir', str(self.fixture), '--evidence-root', str(self.evidence),
                '--upstream', UPSTREAM, '--repo-dir', str(self.repo), '--run-id', 'rehearsal-test')
        run_dir = self.evidence / 'rehearsal-test'
        self.assertTrue((run_dir / 'env_check.json').exists(), r.stdout + r.stderr)
        env_status = self.stage(run_dir, 'env_check')['status']
        self.assertIn(env_status, ('PASS', 'NOT TESTED'), r.stdout + r.stderr)
        for cmd, name in (('fetch', 'fetch'), ('verify-load', 'verify_load'), ('generate', 'generate'),
                          ('reload-check', 'reload_check')):
            r = cli(cmd, '--run-dir', str(run_dir))
            rec = self.stage(run_dir, name)
            self.assertEqual(rec['status'], 'PASS', '%s\n%s\n%s' % (cmd, r.stdout, json.dumps(rec['checks'], indent=1)[:3000]))
        r = cli('finalize', '--run-dir', str(run_dir))
        summary = json.loads((run_dir / 'summary.json').read_text())
        self.assertTrue(summary['rehearsal'])
        self.assertEqual([i['status'] for i in summary['items']], ['PASS'] * 11)
        gen = self.stage(run_dir, 'generate')
        rel = self.stage(run_dir, 'reload_check')
        self.assertNotEqual(gen['process']['pid'], rel['process']['pid'])
        # three passes exist and agree
        passes = [json.loads((run_dir / ('generation_pass%d.json' % i)).read_text())['rows'] for i in (1, 2, 3)]
        for a, b, c in zip(*passes):
            self.assertEqual(a['new_ids'], b['new_ids'])
            self.assertEqual(a['new_ids'], c['new_ids'])
            self.assertEqual(len(a['new_ids']), 64)
        # stages are exclusive: a second run of the same stage is refused or leaves the record unchanged
        before = (run_dir / 'generate.json').read_bytes()
        r2 = cli('generate', '--run-dir', str(run_dir))
        self.assertNotEqual(r2.returncode, 0)
        self.assertEqual(before, (run_dir / 'generate.json').read_bytes())

    def test_tampered_download_blocks_before_loading(self):
        r = cli('env-check', '--rehearsal', '--fixture-dir', str(self.fixture), '--evidence-root', str(self.evidence),
                '--upstream', UPSTREAM, '--repo-dir', str(self.repo), '--run-id', 'rehearsal-tamper')
        run_dir = self.evidence / 'rehearsal-tamper'
        cli('fetch', '--run-dir', str(run_dir))
        self.assertEqual(self.stage(run_dir, 'fetch')['status'], 'PASS')
        with open(run_dir / 'downloads' / 'model' / 'pytorch_model.bin', 'r+b') as f:
            f.seek(4096)
            byte = f.read(1)
            f.seek(4096)
            f.write(bytes([byte[0] ^ 0xFF]))
        cli('verify-load', '--run-dir', str(run_dir))
        rec = self.stage(run_dir, 'verify_load')
        self.assertEqual(rec['status'], 'BLOCKED')
        self.assertIn('no longer matches', rec['error'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
