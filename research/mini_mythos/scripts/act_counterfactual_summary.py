#!/usr/bin/env python3
"""Print a compact, interpretable ACT-002 trace from a JSON report."""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', help='Path to act_counterfactual.py output JSON')
    parser.add_argument('--first', type=int, default=15, help='Maximum training steps per run to show')
    args = parser.parse_args()
    if args.first < 1:
        parser.error('--first must be positive')

    report = json.loads(Path(args.report).read_text(encoding='utf-8'))
    if report.get('experiment') != 'ACT-002_same_weight_counterfactual':
        parser.error('The file is not an ACT-002 report')

    for run in report['results']:
        print(f"\n{run['attention'].upper()} | depth={run['requested_depth']} | seed={report['seed']}")
        print('First events:', json.dumps(run['events'], sort_keys=True))
        print('Step | Deficit% | ParamGap | DirectACT | History | Interaction | Total | GradGap')
        for row in run['train_trace'][:args.first]:
            l = row['effects']['logits']
            print(
                f"{row['step']:>4} | "
                f"{row['original_act_deficit_fraction_original_weights'] * 100:>7.2f} | "
                f"{row['parameter_l2_difference_pre_update']:.6g} | "
                f"{l['direct_mechanism_same_original_weights']['max_abs']:.6g} | "
                f"{l['parameter_history_under_original_act']['max_abs']:.6g} | "
                f"{l['policy_parameter_interaction']['max_abs']:.6g} | "
                f"{l['total_deployed']['max_abs']:.6g} | "
                f"{row['deployed_gradient_l2_difference_preclip']:.6g}"
            )
        h = run['heldout']
        print('Heldout original ACT/original weights:',
              round(h['original_weights_original_act'], 6))
        print('Heldout forced ACT/forced weights:',
              round(h['forced_weights_forced_act'], 6))
        print('Heldout total delta:', round(h['total_deployed_delta'], 6))
        print('Note: the magnitudes in the table are NOT additive shares.')


if __name__ == '__main__':
    main()
