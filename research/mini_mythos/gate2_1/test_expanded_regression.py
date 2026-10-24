"""Gate 2.1-B expanded CPU regression. No Parcae changes. No GPU."""

import hashlib
import json
import sys
from pathlib import Path

import torch
from torch.utils.data import IterableDataset
from torchdata.stateful_dataloader import StatefulDataLoader


class MiniRNGDS(IterableDataset):
    def __init__(self, seed=42, vocab_size=489, block_size=16, n=500):
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


def make(batch, n=500):
    return StatefulDataLoader(MiniRNGDS(n=n), batch_size=batch, num_workers=0)


def continuous(n_batches, batch):
    loader = make(batch)
    it = iter(loader)
    return [bhash(next(it)) for _ in range(n_batches)], loader


def resume_no_skip(state, batch, n_take):
    loader = make(batch)
    loader.load_state_dict(state)
    it = iter(loader)
    return [bhash(next(it)) for _ in range(n_take)]


def main():
    results = {"tests": []}

    ha, _ = continuous(20, 2)
    _, l8 = continuous(8, 2)
    h_after8 = resume_no_skip(l8.state_dict(), 2, 12)
    _, l12 = continuous(12, 2)
    h_after12 = resume_no_skip(l12.state_dict(), 2, 8)
    ok_multi = (
        all(h_after8[i] == ha[8 + i] for i in range(12))
        and all(h_after12[i] == ha[12 + i] for i in range(8))
    )
    results["tests"].append({
        "name": "multi_resume_8_and_12",
        "status": "PASS" if ok_multi else "FAIL",
        "detail": (
            f"after8={sum(h_after8[i]==ha[8+i] for i in range(12))}/12 "
            f"after12={sum(h_after12[i]==ha[12+i] for i in range(8))}/8"
        ),
    })

    for bs in (1, 2, 4, 8):
        ha_bs, _ = continuous(10, bs)
        _, l6 = continuous(6, bs)
        h_res = resume_no_skip(l6.state_dict(), bs, 4)
        ok = all(h_res[i] == ha_bs[6 + i] for i in range(4))
        results["tests"].append({
            "name": f"batch_size_{bs}",
            "status": "PASS" if ok else "FAIL",
            "detail": f"match {sum(h_res[i]==ha_bs[6+i] for i in range(4))}/4",
        })

    # Official RandomTokensDataset methods, small table (no 1e6 alloc)
    sys.path.insert(0, "/tmp/parcae-src")
    from recpre.huggingface_dataset import RandomTokensDataset
    ds = object.__new__(RandomTokensDataset)
    g = torch.Generator()
    g.manual_seed(42)
    ds.data = torch.randint(0, 489, (200, 16), dtype=torch.int32, generator=g)
    ds.idx = 0
    l_off = StatefulDataLoader(ds, batch_size=2, num_workers=0)
    it = iter(l_off)
    h_off = [bhash(next(it)) for _ in range(10)]
    ds2 = object.__new__(RandomTokensDataset)
    ds2.data = ds.data
    ds2.idx = 0
    l2 = StatefulDataLoader(ds2, batch_size=2, num_workers=0)
    it2 = iter(l2)
    for _ in range(6):
        next(it2)
    st = l2.state_dict()
    ds3 = object.__new__(RandomTokensDataset)
    ds3.data = ds.data.clone()
    ds3.idx = 0
    l3 = StatefulDataLoader(ds3, batch_size=2, num_workers=0)
    l3.load_state_dict(st)
    it3 = iter(l3)
    h_res = [bhash(next(it3)) for _ in range(4)]
    ok = all(h_res[i] == h_off[6 + i] for i in range(4))
    results["tests"].append({
        "name": "official_rngds_lightweight",
        "status": "PASS" if ok else "FAIL",
        "detail": "real methods, small table, no recovery-logic change",
    })

    # ParquetStreamPure: expected BLOCKED on CPU (cuda + distributed in state_dict)
    try:
        from recpre.huggingface_dataset import ParquetStreamPure
        import pyarrow as pa
        import pyarrow.parquet as pq
        d = Path("/tmp/g21b_pq")
        d.mkdir(exist_ok=True)
        pq.write_table(pa.table({"input_ids": [[1, 2, 3, 4]] * 8}), d / "a.parquet")
        ds_p = ParquetStreamPure(
            dataset_folder_path=str(d),
            data_signature={"keys": ["input_ids"]},
            num_processes=1,
            process_rank=0,
            stateful=True,
            shuffle=False,
        )
        ds_p.state_dict()
        results["tests"].append({"name": "parquet_stream_pure", "status": "PASS", "detail": "unexpected success"})
    except Exception as e:
        results["tests"].append({
            "name": "parquet_stream_pure",
            "status": "BLOCKED",
            "detail": f"{type(e).__name__}: {e}",
        })

    out = Path(__file__).resolve().parent / "EXPANDED_RESULTS.json"
    out.write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))
    fails = sum(1 for t in results["tests"] if t["status"] == "FAIL")
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
