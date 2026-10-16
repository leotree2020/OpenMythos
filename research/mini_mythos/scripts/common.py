"""Minimal, non-invasive adapter to a checked-out upstream OpenMythos."""
import importlib
import os
from pathlib import Path
import subprocess
import sys


def get_repo(repo: str) -> Path:
    root = Path(repo).expanduser().resolve()
    if not (root / 'open_mythos' / 'main.py').is_file():
        raise FileNotFoundError(f'Upstream OpenMythos checkout not found at {root}. Run ./bootstrap.sh first.')
    return root


def commit_id(repo: Path) -> str:
    try:
        return subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return 'unknown'


def load_upstream(repo: Path):
    repo = get_repo(str(repo))
    sys.path.insert(0, str(repo))
    return importlib.import_module('open_mythos.main')


def tiny_config(module, attention='gqa'):
    args = dict(vocab_size=96, dim=48, n_heads=4, n_kv_heads=2,
                max_seq_len=32, max_loop_iters=8, prelude_layers=1,
                coda_layers=1, attn_type=attention, n_experts=4,
                n_shared_experts=1, n_experts_per_tok=1,
                expert_dim=24, lora_rank=4, dropout=0.)
    if attention == 'mla':
        args.update(kv_lora_rank=16, q_lora_rank=16,
                    qk_rope_head_dim=8, qk_nope_head_dim=8, v_head_dim=8)
    return module.MythosConfig(**args)


def toy_batch(torch, seed, batch_size=2, seq_len=16, device='cpu'):
    """Toy tokens only: deterministic *pipeline check*, not a domain benchmark."""
    g = torch.Generator(device='cpu').manual_seed(int(seed))
    rows = []
    for _ in range(batch_size):
        seq = []
        while len(seq) <= seq_len:
            client = int(torch.randint(0, 8, (1,), generator=g).item())
            protocol = int(torch.randint(0, 3, (1,), generator=g).item())
            status = (client + protocol) % 3
            seq += [1, 40 + client, 12 + protocol, 20 + status, 30 + status, 2]
        rows.append(seq[:seq_len + 1])
    data = torch.tensor(rows, dtype=torch.long, device=device)
    return data[:, :-1], data[:, 1:]


def atomic_json(path, payload):
    import json
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + '.tmp')
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(tmp, target)
