"""FIX2 fixture. TEST FIXTURE — NOT NATIVE TRAINING."""
import json
import os
import sys
import tempfile
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ["MINI_MYTHOS_EVIDENCE"] = "1"
from native_lifecycle_observer import LifecycleLog


def main():
    a = LifecycleLog()
    a.on_optimizer_boundary(1, False)
    a.on_optimizer_boundary(2, True)
    assert a.update_count == 1
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        state = {"optimizer_step": 2}
        a.stamp_update_count(state)
        path = td / "ckpt.pt"
        torch.save(state, path)
        loaded = torch.load(path, map_location="cpu", weights_only=False)
        b = LifecycleLog()
        status = b.restore_update_count(loaded.get("mini_mythos_update_count"))
        b.on_optimizer_boundary(3, True)
        missing = dict(loaded)
        missing.pop("mini_mythos_update_count")
        c = LifecycleLog()
        missing_status = c.restore_update_count(missing.get("mini_mythos_update_count"))
        ok = status == "RESTORED" and b.update_count == 2 and missing_status == "MISSING" and c.update_count == 0
    print(json.dumps({
        "status": "FIX2 FIXTURE PASS" if ok else "FAIL",
        "kind": "TEST FIXTURE — NOT NATIVE TRAINING",
        "saved": loaded.get("mini_mythos_update_count"),
        "restored": status,
        "after_next": b.update_count,
        "missing": missing_status,
    }, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
