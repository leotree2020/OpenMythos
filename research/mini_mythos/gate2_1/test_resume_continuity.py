"""
Gate 2.1 CPU reproduction of rngds + StatefulDataLoader resume continuity.

Mirrors RandomTokensDataset idx / state_dict contract with a small table.
Does not modify Parcae. No GPU.
"""

import hashlib
import json
import sys
from pathlib import Path

import torch
from torch.utils.data import IterableDataset
from torchdata.stateful_dataloader import StatefulDataLoader


class MiniRNGDS(IterableDataset):
    """Same idx contract as Parcae RandomTokensDataset."""

    def __init__(self, seed=42, vocab_size=489, block_size=16, n=200):
        g = torch.Generator()
        g.manual_seed(seed)
        self.data = torch.randint(0, vocab_size, (n, block_size), dtype=torch.int32, generator=g)
        self.idx = 0

    def __iter__(self):
        for entry in self.data[self.idx:]:
            self.idx += 1
            yield entry

    def state_dict(self):
        return {"idx": self.idx}

    def load_state_dict(self, state_dict):
        self.idx = state_dict["idx"]


def bhash(batch):
    return hashlib.sha256(batch.contiguous().view(torch.uint8).numpy().tobytes()).hexdigest()


def make(seed=42, vocab=489, block=16, n=200, batch=2):
    return StatefulDataLoader(
        MiniRNGDS(seed, vocab, block, n), batch_size=batch, num_workers=0
    )


def collect(n, **kw):
    loader = make(**kw)
    it = iter(loader)
    hs, idxs = [], []
    for _ in range(n):
        batch = next(it)
        hs.append(bhash(batch))
        idxs.append(loader.dataset.idx)
    return hs, idxs, loader


def main():
    results = {"pass": 0, "fail": 0, "notes": []}

    ha, ia, _ = collect(20)
    results["control_a_idx_after_20"] = ia[-1]

    h12, i12, l12 = collect(12)
    state = l12.state_dict()
    results["idx_after_12"] = i12[-1]

    # Control B: with extra skip
    lb = make()
    lb.load_state_dict(state)
    itb = iter(lb)
    idx_after_iter = lb.dataset.idx
    next(itb, None)
    idx_after_skip = lb.dataset.idx
    first_b = next(itb)
    hb = [bhash(first_b)] + [bhash(next(itb)) for _ in range(7)]

    # Candidate C: no extra skip
    lc = make()
    lc.load_state_dict(state)
    itc = iter(lc)
    idx_c = lc.dataset.idx
    first_c = next(itc)
    hc = [bhash(first_c)] + [bhash(next(itc)) for _ in range(7)]

    match_b = sum(1 for i in range(8) if hb[i] == ha[12 + i])
    match_c = sum(1 for i in range(8) if hc[i] == ha[12 + i])
    match_b_shifted = sum(1 for i in range(7) if hb[i] == ha[13 + i])

    results["idx_after_load_and_iter"] = idx_after_iter
    results["idx_after_extra_next"] = idx_after_skip
    results["idx_candidate_after_iter"] = idx_c
    results["b_match_a12_20"] = f"{match_b}/8"
    results["c_match_a12_20"] = f"{match_c}/8"
    results["b_match_a13_20"] = f"{match_b_shifted}/7"
    results["b_first_is_a13"] = hb[0] == ha[13]
    results["c_first_is_a12"] = hc[0] == ha[12]
    results["control_a_hash_0"] = ha[0]
    results["control_a_hash_12"] = ha[12]
    results["control_a_hash_13"] = ha[13]

    if match_c == 8 and match_b == 0 and hb[0] == ha[13]:
        results["verdict"] = "PASS: extra next() causes one-batch skip; omitting it restores continuity"
        results["pass"] = 1
    else:
        results["verdict"] = "FAIL: unexpected continuity pattern"
        results["fail"] = 1

    out = Path(__file__).resolve().parent / "TEST_RESULTS.json"
    out.write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))
    return 0 if results["fail"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
