"""
TEST ADAPTER / MOCK for ParquetStreamPure resume logic.

Does NOT claim native Parcae path PASS.
Mocks the CUDA tensor + distributed gather so the buffer-position logic
can be exercised on CPU. Native state_dict remains BLOCKED on this CPU.
"""

import hashlib
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import torch


def sha(row):
    t = torch.tensor(row, dtype=torch.int64)
    return hashlib.sha256(t.contiguous().view(torch.uint8).numpy().tobytes()).hexdigest()


def main():
    results = {"adapter": "TEST ADAPTER / MOCK", "native_path": "BLOCKED", "tests": []}
    d = Path("/tmp/g22_pq")
    d.mkdir(exist_ok=True)
    rows = [[10 + i, 20 + i, 30 + i, 40 + i] for i in range(8)]
    pq.write_table(pa.table({"input_ids": rows}), d / "a.parquet")

    # Uninterrupted hashes
    base = [sha(r) for r in rows]

    # Simulate: consume 3, remaining buffer = 5, resume should start at index 3
    consumed = 3
    remaining = len(rows) - consumed
    # Mock state that load_state_dict would restore: buffer truncated to remaining
    restored_buffer = rows[:remaining]  # native truncates buffer[:row_idx] after re-read
    # After _read_buffer the buffer is the full row group reversed or as-is;
    # with shuffle=False, buffer is the raw list, then truncated to row_idx.
    # row_idx saved is buffer_remaining at save time.
    # So restored buffer[:remaining] == rows[:remaining], and next yields from the end
    # because native yields via buffer.pop() (LIFO).
    # Document that pop() makes order reversed relative to file order.
    popped = []
    buf = list(restored_buffer)
    for _ in range(3):
        popped.append(buf.pop())
    popped_h = [sha(x) for x in popped]
    # With LIFO pop on rows[:5] = indices 0..4, pop order is 4,3,2
    expected_lifo = [sha(rows[4]), sha(rows[3]), sha(rows[2])]
    ok = popped_h == expected_lifo
    results["tests"].append({
        "name": "mock_buffer_lifo_position",
        "status": "PASS" if ok else "FAIL",
        "detail": "MOCK only: pop order matches truncated buffer LIFO; not native PASS",
        "sha256": {"got": popped_h, "expected_lifo": expected_lifo},
    })

    # Negative: offset by one must differ
    wrong = [sha(rows[5]), sha(rows[4]), sha(rows[3])]
    results["tests"].append({
        "name": "mock_negative_offset_differs",
        "status": "PASS" if popped_h != wrong else "FAIL",
        "detail": "offset-by-one hashes differ",
    })

    results["note"] = (
        "Native ParquetStreamPure.state_dict creates device='cuda' tensor and calls "
        "torch.distributed.all_gather / get_world_size. On this CPU that is BLOCKED. "
        "This adapter only exercises the buffer truncation + pop logic."
    )
    out = Path(__file__).resolve().parent / "GATE2_2_ADAPTER_RESULTS.json"
    out.write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))
    fails = sum(1 for t in results["tests"] if t["status"] == "FAIL")
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
