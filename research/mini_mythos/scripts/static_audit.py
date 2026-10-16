#!/usr/bin/env python3
"""Text-based guardrails on a real upstream checkout (does not modify upstream)."""
import argparse
from pathlib import Path
from common import get_repo, commit_id, atomic_json


def inspect(repo):
    repo = get_repo(str(repo))
    main = (repo / 'open_mythos/main.py').read_text(encoding='utf-8')
    train = (repo / 'training/3b_fine_web_edu.py').read_text(encoding='utf-8')
    tokenizer = (repo / 'open_mythos/tokenizer.py').read_text(encoding='utf-8')
    checks = [
        ('ARCH_RDT', 'RecurrentBlock' in main and 'prelude' in main and 'coda' in main,
         'RDT block names exist (structural presence, not behavior proof).'),
        ('ARCH_GQA_MLA', 'class GQAttention' in main and 'class MLAttention' in main,
         'Both attention classes are present.'),
        ('MODEL_TIED_EMBED', 'self.head.weight = self.embed.weight' in main,
         'Language-model head and embedding use tied weights.'),
        ('MASK_DTYPE', 'self._causal_mask(T, device, x.dtype)' in main,
         'Causal mask is requested in activation dtype; check entire path dynamically.'),
        ('ACT_DTYPE_RISK', 'cumulative_p = torch.zeros(B, T, device=h.device)' in main,
         'ACT accumulator created without explicit dtype (potential mixed-precision promotion).'),
        ('ACT_TRUNCATION_RISK', 'return h_out' in main and 'h_out = h_out + weight.unsqueeze(-1) * h' in main,
         'ACT weighted output has no explicit final-step residual at n_loops exhaustion.'),
        ('TRAIN_SCALER', 'GradScaler' in train,
         'FP16 GradScaler path found; if absent, validate stability before using FP16.'),
        ('TRAIN_VALIDATION', 'val_loss' in train or 'eval_loss' in train,
         'Validation logging token found; manually inspect actual eval path.'),
        ('TRAIN_DATA_RESUME', 'stateful_dataloader' in train or 'dataset_state' in train,
         'Dataset position recovery found; if absent, resumed streaming repeats earlier samples.'),
        ('TRAIN_FSDP', 'FullyShardedDataParallel' in train,
         'FSDP is imported.'),
        ('TOKENIZER_EXTERNAL', 'AutoTokenizer.from_pretrained' in tokenizer,
         'Tokenizer downloaded from a separate provider; pin name/revision + vocab.'),
        ('CHECKPOINT_PICKLE', 'weights_only=False' in train,
         'Checkpoint uses pickle-compatible load: load only trusted checkpoints.'),
    ]
    return {
        'upstream_commit': commit_id(repo), 'upstream_path': str(repo),
        'checks': [{'id': key, 'found': found, 'meaning': note} for key, found, note in checks],
        'interpretation': 'Found=False does NOT prove a capability is absent; review code and execute smoke tests.'
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--repo', default='.')
    p.add_argument('--out', default='research/mini_mythos/results/static_audit.json')
    args = p.parse_args()
    result = inspect(args.repo)
    atomic_json(args.out, result)
    print('Upstream:', result['upstream_commit'])
    for check in result['checks']:
        print(('FOUND' if check['found'] else 'NOT FOUND').ljust(10), check['id'], '-', check['meaning'])
    print('Saved to', args.out)


if __name__ == '__main__':
    main()
