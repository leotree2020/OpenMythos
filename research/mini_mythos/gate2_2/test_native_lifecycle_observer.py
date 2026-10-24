"""Observer fixture. Not a Parcae training run."""
import json
import os
import sys
import tempfile
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ["MINI_MYTHOS_EVIDENCE"] = "1"
from native_lifecycle_observer import LOG, enabled


def main():
    assert enabled()
    checks = []
    batches = [torch.tensor([1, 2, 3]), torch.tensor([4, 5]), torch.tensor([6])]
    losses = [torch.tensor(0.1), torch.tensor(0.2), torch.tensor(0.3)]
    for i, (b, loss) in enumerate(zip(batches, losses), start=1):
        LOG.on_microbatch(b, loss, i)
    # first boundary skipped
    LOG.on_optimizer_boundary(1, False)
    # real step
    LOG.on_optimizer_boundary(2, True)
    # nonfinite skip
    LOG.on_optimizer_boundary(3, False)
    checks.append({"name": "all_microbatches", "ok": len([e for e in LOG.events if e["type"] == "microbatch"]) == 3})
    got = [e["loss"] for e in LOG.events if e["type"] == "microbatch"]
    checks.append({"name": "aligned", "ok": all(abs(a-b) < 1e-6 for a, b in zip(got, [0.1, 0.2, 0.3]))})
    checks.append({"name": "update_count", "ok": LOG.update_count == 1})
    LOG.restore_update_count(1)
    checks.append({"name": "resume_keeps_count", "ok": LOG.update_count == 1})
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        f = td / "ckpt.pt"
        f.write_bytes(b"ckpt")
        LOG.on_before_save(f, 3)
        LOG.on_after_save(f, 3)
        LOG.on_after_load(3)
        out = td / "evidence.json"
        obj = LOG.export(out, {"command": "fixture", "note": "TEST FIXTURE"})
        checks.append({"name": "exported", "ok": out.is_file()})
        checks.append({"name": "not_gpu", "ok": obj["source"] != "GPU_RUNTIME" and obj["gpu_runtime"] == "NOT TESTED"})
        checks.append({"name": "missing_marked", "ok": obj["model_index"] == "MISSING"})
        checks.append({"name": "ckpt_hashed", "ok": bool(obj["checkpoint_sha256"])})
    failed = [c["name"] for c in checks if not c["ok"]]
    print(json.dumps({"status": "OBSERVER TEST PASS" if not failed else "FAIL", "kind": "TEST FIXTURE", "checks": checks, "failed": failed, "native_train": "NOT TESTED"}, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
