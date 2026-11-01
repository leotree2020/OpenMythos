"""Read only the failed step's saved bytes; never compute softmax or load a model."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    args.run = args.run.resolve(strict=True)
    args.output = args.output.resolve()
    if args.output.exists() or args.output.is_relative_to(args.run):
        raise ValueError('Audit output must be new and outside the sealed run')
    g = args.run / 'first/generation'
    checks = []

    def check(name, expected, actual, ok):
        checks.append({'Purpose': name, 'Environment': 'stdlib; saved bytes only',
                       'Input': str(g), 'Expected': expected, 'Actual': actual,
                       'Status': 'PASS' if ok else 'FAIL'})

    s = json.loads((g/'public/S_panel1_prompt01_step00_observation.json').read_text())
    ref = json.loads((g/'public/G_panel0_prompt01_step00_observation.json').read_text())
    raw = (g/'private/S_panel1_prompt01_step00_last.bin').read_bytes()
    reference = (g/'private/G_panel0_prompt01_step00_last.bin').read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    check('Partial S last-vector actual bytes equal G', '131072 identical bytes',
          {'size': len(raw), 'sha256': sha}, len(raw) == 131072 and raw == reference
          and sha == s['last_logits']['sha256'] == ref['last_logits']['sha256'])
    finite = len(raw) == 131072 and all(math.isfinite(x[0]) for x in struct.iter_unpack('<f', raw))
    check('Retained partial S vector finite', '32768 finite FP32 values', finite, finite)
    keys = ('full_logits', 'full_logits_shape', 'prefix_ids', 'prefix_ids_sha256',
            'default_rng_before_forward', 'default_rng_after_forward')
    same = {key: s[key] == ref[key] for key in keys}
    check('Saved full-logit/prefix/model-RNG fingerprints match G', 'all match', same, all(same.values()))
    check('Saved sampler RNG unchanged across forward', True,
          s['sampler_rng_before_forward'] == s['sampler_rng_after_forward'],
          s['sampler_rng_before_forward'] == s['sampler_rng_after_forward'])
    failed = [json.loads(line) for line in (g/'public/checks.jsonl').read_text().splitlines()
              if json.loads(line).get('Status') == 'FAIL']
    exact = len(failed) == 1 and failed[0]['Purpose'] == 'probability mass normalized before sampling'
    row = failed[0] if failed else {}
    actual = row.get('Actual')
    expected = row.get('Expected')
    check('Exactly the frozen probability-mass guard failed',
          {'value': 1.0000113072183736, 'tolerance': 1e-6, 'policy': 'S', 'panel': 1, 'prompt_id': 1, 'step': 0}, row,
          exact and actual == 1.0000113072183736 and expected == {'absolute_tolerance': 1e-6, 'target': 1.0}
          and all(row.get('Input', {}).get(k) == v for k, v in {'policy': 'S', 'panel': 1, 'prompt_id': 1, 'step': 0}.items()))
    trace = g/'public/S_panel1_prompt01_trace.jsonl'
    no_sample = trace.stat().st_size == 0 and not (g/'public/S_panel1_prompt01_generation.json').exists()
    check('No completed sampling selection/continuation evidence', True, no_sample, no_sample)
    result = {'Purpose': 'Verify the saved input and stopping point of the failed sampling step',
              'Environment': 'stdlib only; no torch, tokenizer, model, softmax or RNG replay',
              'Input': str(args.run), 'Expected': 'Byte-identical first input and internally consistent frozen guard failure',
              'Actual': {'retained_fp32_values': len(raw)//4, 'reported_probability_sum': actual,
                         'probability_sum_operation': 'FP64 sum of FP32 softmax probabilities',
                         'absolute_error': abs(actual-1.0) if isinstance(actual, (int, float)) else None,
                         'probability_vector_retained': False, 'probability_sum_recomputed': False,
                         'scientific_run_status_unchanged': 'FAIL', 'historical_signal_cause': 'UNRESOLVED'},
              'Status': 'PASS' if all(x['Status'] == 'PASS' for x in checks) else 'FAIL', 'checks': checks,
              'limitations': ['Full logits and RNG comparisons use recorded fingerprints; only retained last vectors are compared as bytes.',
                              'The probability vector was not saved before the guard failed; the FP64 sum of FP32 softmax probabilities is recorded evidence, not independently recomputed here.',
                              'No sampled token was reached according to the frozen source control flow and recorded failure. No new numerical experiment occurred.']}
    result['evidence_binding'] = {name: {'size': (args.run/name).stat().st_size,
        'sha256': hashlib.sha256((args.run/name).read_bytes()).hexdigest()}
        for name in ('FULL_MANIFEST.json', 'public/summary.json')}
    with args.output.open('x') as out:
        json.dump(result, out, indent=2)
        out.write('\n')
    print(json.dumps({'Status': result['Status'], 'checks': len(checks), 'Actual': result['Actual']}))
    return 0 if result['Status'] == 'PASS' else 2


if __name__ == '__main__':
    raise SystemExit(main())
