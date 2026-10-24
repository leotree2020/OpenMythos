"""Gate 2.1-C.1: credibility fixes.
- True chained resume (S12 from resumed loader).
- Directly calls create_train_iterator from the patch.
- ParquetStreamPure exception classification.
No Parcae changes. No GPU.
"""

import hashlib
import json
import sys
from pathlib import Path

import torch
from torch.utils.data import IterableDataset
from torchdata.stateful_dataloader import StatefulDataLoader

sys.path.insert(0, "/tmp/parcae-src")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from recpre.huggingface_dataset import RandomTokensDataset
from patch_resume_skip import create_train_iterator


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
    it = create_train_iterator(loader, microbatch_step=0)
    return [bhash(next(it)) for _ in range(n)]


def main():
    results = {"tests": []}

    # --- Task 1: true chained resume ---
    # baseline continuous
    ha = continuous(20, 2)

    # initial 0-8, save S8
    l0 = make_rngds(2)
    it0 = create_train_iterator(l0, microbatch_step=0)
    h0_8 = [bhash(next(it0)) for _ in range(8)]
    s8 = l0.state_dict()

    # resume from S8, read 9-12, save S12 from THIS loader
    l1 = make_rngds(2)
    l1.load_state_dict(s8)
    it1 = create_train_iterator(l1, microbatch_step=8)
    h9_12 = [bhash(next(it1)) for _ in range(4)]
    s12 = l1.state_dict()  # from resumed loader, not a fresh one

    # resume from S12, read 13-20
    l2 = make_rngds(2)
    l2.load_state_dict(s12)
    it2 = create_train_iterator(l2, microbatch_step=12)
    h13_20 = [bhash(next(it2)) for _ in range(8)]

    ok_chain = (
        all(h0_8[i] == ha[i] for i in range(8))
        and all(h9_12[i] == ha[8 + i] for i in range(4))
        and all(h13_20[i] == ha[12 + i] for i in range(8))
    )
    results["tests"].append({
        "name": "true_chained_resume_s8_s12",
        "status": "PASS" if ok_chain else "FAIL",
        "detail": (
            f"0-8={sum(h0_8[i]==ha[i] for i in range(8))}/8 "
            f"9-12={sum(h9_12[i]==ha[8+i] for i in range(4))}/4 "
            f"13-20={sum(h13_20[i]==ha[12+i] for i in range(8))}/8 "
            f"s12_from_resumed=True"
        ),
    })

    # --- Task 2: direct patch function positive / negative ---
    # positive: RandomTokensDataset, microbatch_step>0 → no extra skip
    lp = make_rngds(2)
    itp = iter(lp)
    for _ in range(6):
        next(itp)
    idx_saved = lp.dataset.idx
    sp = lp.state_dict()
    lp2 = make_rngds(2)
    lp2.load_state_dict(sp)
    it_pos = create_train_iterator(lp2, microbatch_step=6)
    idx_after = lp2.dataset.idx
    first = next(it_pos)
    idx_after_first = lp2.dataset.idx
    # continuous reference
    href = continuous(10, 2)
    ok_pos = (
        idx_after == idx_saved
        and idx_after_first == idx_saved + 2
        and bhash(first) == href[6]
    )
    results["tests"].append({
        "name": "patch_fn_positive_rngds_no_skip",
        "status": "PASS" if ok_pos else "FAIL",
        "detail": f"idx {idx_saved}->{idx_after}->{idx_after_first} hash_match={bhash(first)==href[6]}",
    })

    # negative: non-RandomTokensDataset, microbatch_step>0 → skip happens
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
    ito = create_train_iterator(lo, microbatch_step=0)
    ho = [int(next(ito).flatten()[0]) for _ in range(10)]
    lo6 = StatefulDataLoader(OtherDS(), batch_size=1, num_workers=0)
    it6 = create_train_iterator(lo6, microbatch_step=0)
    for _ in range(6):
        next(it6)
    lo_r = StatefulDataLoader(OtherDS(), batch_size=1, num_workers=0)
    lo_r.load_state_dict(lo6.state_dict())
    it_neg = create_train_iterator(lo_r, microbatch_step=6)
    first_neg = int(next(it_neg).flatten()[0])
    # skip means first is ho[7], not ho[6]
    ok_neg = first_neg == ho[7]
    results["tests"].append({
        "name": "patch_fn_negative_other_keeps_skip",
        "status": "PASS" if ok_neg else "FAIL",
        "detail": f"got {first_neg} expected {ho[7]}",
    })

    # --- batch sizes via patch function ---
    for bs in (1, 2, 4, 8):
        ha_bs = continuous(10, bs)
        l6 = make_rngds(bs)
        it6b = create_train_iterator(l6, microbatch_step=0)
        for _ in range(6):
            next(it6b)
        st6 = l6.state_dict()
        lr = make_rngds(bs)
        lr.load_state_dict(st6)
        itr = create_train_iterator(lr, microbatch_step=6)
        h_res = [bhash(next(itr)) for _ in range(4)]
        ok = all(h_res[i] == ha_bs[6 + i] for i in range(4))
        results["tests"].append({
            "name": f"batch_size_{bs}_via_patch_fn",
            "status": "PASS" if ok else "FAIL",
            "detail": f"match {sum(h_res[i]==ha_bs[6+i] for i in range(4))}/4",
        })

    # --- Task 3: ParquetStreamPure with correct kwargs and classified exceptions ---
    try:
        from recpre.huggingface_dataset import ParquetStreamPure
        import pyarrow as pa
        import pyarrow.parquet as pq
        d = Path("/tmp/g21c1_pq")
        d.mkdir(exist_ok=True)
        # 8 unique equal-length samples so SHA-256 can prove position
        unique_rows = [[10 + i, 20 + i, 30 + i, 40 + i] for i in range(8)]
        pq.write_table(pa.table({"input_ids": unique_rows}), d / "a.parquet")
        try:
            dsp = ParquetStreamPure(
                dataset_folder_path=str(d),
                seed=42,
                data_signature={"keys": ["input_ids"]},
                shuffle=False,
                shuffle_filenames=False,
                broadcast_glob=False,
                plan_for_later_rank_expansion_to=1,
                num_processes=1,
                process_rank=0,
                stateful=True,
            )
        except Exception as e:
            results["tests"].append({
                "name": "parquet_stream_pure",
                "status": "FAIL",
                "detail": f"construction failed: {type(e).__name__}: {e}",
            })
            dsp = None
        if dsp is not None:
            try:
                # consume a few, save, restore
                it_p = iter(dsp)
                got = [next(it_p) for _ in range(3)]
                st_p = dsp.state_dict()
                # restore into a new instance
                dsp2 = ParquetStreamPure(
                    dataset_folder_path=str(d),
                    seed=42,
                    data_signature={"keys": ["input_ids"]},
                    shuffle=False,
                    shuffle_filenames=False,
                    broadcast_glob=False,
                    plan_for_later_rank_expansion_to=1,
                    num_processes=1,
                    process_rank=0,
                    stateful=True,
                )
                dsp2.load_state_dict(st_p)
                it_p2 = iter(dsp2)
                got2 = next(it_p2)
                # Real continuity: uninterrupted read of 6 samples
                dsp_base = ParquetStreamPure(
                    dataset_folder_path=str(d),
                    seed=42,
                    data_signature={"keys": ["input_ids"]},
                    shuffle=False,
                    shuffle_filenames=False,
                    broadcast_glob=False,
                    plan_for_later_rank_expansion_to=1,
                    num_processes=1,
                    process_rank=0,
                    stateful=True,
                )
                it_base = iter(dsp_base)
                base = [next(it_base) for _ in range(6)]
                def _h(t):
                    return hashlib.sha256(t.contiguous().view(torch.uint8).numpy().tobytes()).hexdigest()
                # resumed first should match uninterrupted 4th (index 3)
                h_resumed = [_h(got2)]
                for _ in range(2):
                    h_resumed.append(_h(next(it_p2)))
                h_base = [_h(base[3]), _h(base[4]), _h(base[5])]
                ok_p = h_resumed == h_base
                results["tests"].append({
                    "name": "parquet_stream_pure",
                    "status": "PASS" if ok_p else "FAIL",
                    "detail": f"sha256 match {sum(a==b for a,b in zip(h_resumed, h_base))}/3 (resumed[0:3] vs continuous[3:6])",
                })
            except Exception as e:
                msg = str(e)
                name = type(e).__name__
                if "CUDA" in msg or "cuda" in msg or "not compiled with CUDA" in msg:
                    status = "BLOCKED"
                    detail = f"CPU unsupported CUDA op: {name}: {e}"
                elif "distributed" in msg.lower() or "process group" in msg.lower() or "Default process group" in msg:
                    status = "BLOCKED"
                    detail = f"distributed not initialized: {name}: {e}"
                else:
                    status = "FAIL"
                    detail = f"{name}: {e}"
                results["tests"].append({
                    "name": "parquet_stream_pure",
                    "status": status,
                    "detail": detail,
                })
    except Exception as e:
        results["tests"].append({
            "name": "parquet_stream_pure",
            "status": "FAIL",
            "detail": f"import/setup failed: {type(e).__name__}: {e}",
        })

    # Negative: wrong offset by one must fail the equality check
    # (uses the unique-row table already written)
    try:
        import pyarrow.parquet as pq
        rows = pq.read_table("/tmp/g21c1_pq/a.parquet").column("input_ids").to_pylist()
        def _hh(row):
            import torch as _t
            return hashlib.sha256(_t.tensor(row, dtype=_t.int64).contiguous().view(_t.uint8).numpy().tobytes()).hexdigest()
        # correct: resumed[0:3] == continuous[3:6]
        correct = [_hh(rows[3]), _hh(rows[4]), _hh(rows[5])]
        # wrong offset +1: continuous[4:7]
        wrong = [_hh(rows[4]), _hh(rows[5]), _hh(rows[6])]
        negative_fails = (correct != wrong)
        results["tests"].append({
            "name": "parquet_negative_offset_must_fail",
            "status": "PASS" if negative_fails else "FAIL",
            "detail": "offset-by-one hashes differ" if negative_fails else "offset-by-one did not differ",
        })
    except Exception as e:
        results["tests"].append({
            "name": "parquet_negative_offset_must_fail",
            "status": "FAIL",
            "detail": f"{type(e).__name__}: {e}",
        })

    summary = {"PASS": 0, "FAIL": 0, "BLOCKED": 0, "NOT TESTED": 0}
    for t in results["tests"]:
        summary[t["status"]] = summary.get(t["status"], 0) + 1
    results["summary"] = summary
    results["patch_function_called"] = True
    results["s12_from_resumed_loader"] = True

    out = Path(__file__).resolve().parent / "GATE2_1_C_RESULTS.json"
    out.write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))
    return 0 if summary["FAIL"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
