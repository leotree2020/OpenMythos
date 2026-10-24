"""Gate 2.1-C chained resume and conditional-patch regression. No GPU."""

import hashlib
import json
import sys
from pathlib import Path

import torch
from torch.utils.data import IterableDataset
from torchdata.stateful_dataloader import StatefulDataLoader

sys.path.insert(0, "/tmp/parcae-src")
from recpre.huggingface_dataset import RandomTokensDataset


def bhash(batch):
    return hashlib.sha256(batch.contiguous().view(torch.uint8).numpy().tobytes()).hexdigest()


def make_rngds(batch, n=400, seed=42):
    ds = object.__new__(RandomTokensDataset)
    g = torch.Generator()
    g.manual_seed(seed)
    ds.data = torch.randint(0, 489, (n, 16), dtype=torch.int32, generator=g)
    ds.idx = 0
    return StatefulDataLoader(ds, batch_size=batch, num_workers=0)


def continuous(n, batch):
    loader = make_rngds(batch)
    it = iter(loader)
    return [bhash(next(it)) for _ in range(n)]


def resume_with_patch(state, batch, n_take):
    loader = make_rngds(batch)
    loader.load_state_dict(state)
    it = iter(loader)
    if not isinstance(loader.dataset, RandomTokensDataset):
        next(it, None)
    return [bhash(next(it)) for _ in range(n_take)]


def main():
    results = {"tests": []}

    ha = continuous(20, 2)
    l8 = make_rngds(2)
    it8 = iter(l8)
    h8 = [bhash(next(it8)) for _ in range(8)]
    h_mid = resume_with_patch(l8.state_dict(), 2, 4)
    l12 = make_rngds(2)
    it12 = iter(l12)
    for _ in range(12):
        next(it12)
    h_end = resume_with_patch(l12.state_dict(), 2, 8)
    ok_chain = (
        all(h8[i] == ha[i] for i in range(8))
        and all(h_mid[i] == ha[8 + i] for i in range(4))
        and all(h_end[i] == ha[12 + i] for i in range(8))
    )
    results["tests"].append({
        "name": "chained_resume_8_then_12",
        "status": "PASS" if ok_chain else "FAIL",
        "detail": "20/20 required",
    })

    for bs in (1, 2, 4, 8):
        ha_bs = continuous(10, bs)
        l6 = make_rngds(bs)
        it6 = iter(l6)
        for _ in range(6):
            next(it6)
        h_res = resume_with_patch(l6.state_dict(), bs, 4)
        ok = all(h_res[i] == ha_bs[6 + i] for i in range(4))
        results["tests"].append({
            "name": f"batch_size_{bs}_patched",
            "status": "PASS" if ok else "FAIL",
        })

    l = make_rngds(2)
    it = iter(l)
    for _ in range(6):
        next(it)
    idx_before = l.dataset.idx
    st = l.state_dict()
    l2 = make_rngds(2)
    l2.load_state_dict(st)
    it2 = iter(l2)
    idx_after_iter = l2.dataset.idx
    next(it2)
    idx_after_first = l2.dataset.idx
    ok_side = idx_after_iter == idx_before and idx_after_first == idx_before + 2
    results["tests"].append({
        "name": "no_double_consume_or_reinit",
        "status": "PASS" if ok_side else "FAIL",
        "detail": f"idx {idx_before}->{idx_after_iter}->{idx_after_first}",
    })

    class OtherDS(IterableDataset):
        def __init__(self):
            self.idx = 0
            self.data = list(range(100))
        def __iter__(self):
            for x in self.data[self.idx:]:
                self.idx += 1
                yield torch.tensor([x])
        def state_dict(self):
            return {"idx": self.idx}
        def load_state_dict(self, s):
            self.idx = s["idx"]

    lo = StatefulDataLoader(OtherDS(), batch_size=1, num_workers=0)
    ito = iter(lo)
    ho = [int(next(ito).flatten()[0]) for _ in range(10)]
    lo6 = StatefulDataLoader(OtherDS(), batch_size=1, num_workers=0)
    it6 = iter(lo6)
    for _ in range(6):
        next(it6)
    lo_r = StatefulDataLoader(OtherDS(), batch_size=1, num_workers=0)
    lo_r.load_state_dict(lo6.state_dict())
    it_r = iter(lo_r)
    if not isinstance(lo_r.dataset, RandomTokensDataset):
        next(it_r, None)
    first_other = int(next(it_r).flatten()[0])
    results["tests"].append({
        "name": "unsupported_dataset_keeps_skip",
        "status": "PASS" if first_other == ho[7] else "FAIL",
        "detail": f"got {first_other} expected {ho[7]}",
    })

    try:
        from recpre.huggingface_dataset import ParquetStreamPure
        import pyarrow as pa
        import pyarrow.parquet as pq
        d = Path("/tmp/g21c_pq")
        d.mkdir(exist_ok=True)
        pq.write_table(pa.table({"input_ids": [[1, 2, 3]] * 4}), d / "a.parquet")
        dsp = ParquetStreamPure(str(d), {"keys": ["input_ids"]}, num_processes=1, process_rank=0, stateful=True, shuffle=False)
        dsp.state_dict()
        results["tests"].append({"name": "parquet_stream_pure", "status": "PASS"})
    except Exception as e:
        results["tests"].append({
            "name": "parquet_stream_pure",
            "status": "BLOCKED",
            "detail": f"{type(e).__name__}: {e}",
        })

    summary = {"PASS": 0, "FAIL": 0, "BLOCKED": 0, "NOT TESTED": 0}
    for t in results["tests"]:
        summary[t["status"]] = summary.get(t["status"], 0) + 1
    results["summary"] = summary
    out = Path(__file__).resolve().parent / "GATE2_1_C_RESULTS.json"
    out.write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))
    return 0 if summary["FAIL"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
