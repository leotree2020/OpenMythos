"""Implementation Task Order V1, section 6 item 8: every stop condition ST1-ST13 has at least one triggering case
(protocol v1.1 section 11), with the status of section 9 and the action text of the frozen protocol row; and a case
where it does not trigger. Also the device ledger (ST9), the GPU clock (ST7) and the device check (ST8) of
compute.py, and the preflight estimate feeding ST11."""
import math
import os

import pytest
import torch

from metrix_e1 import compute as CP
from metrix_e1 import contract as C
from metrix_e1 import mode as M
from metrix_e1 import stops as STP
from metrix_e1.errors import ST12Error, STATUSES

A100 = {"name": "NVIDIA A100-SXM4-80GB", "total_memory": 85899345920}


def leak(over=()):
    checks = {c: {"within_limit": c not in over} for c in ("L1", "L2", "L3a", "L3b", "L4", "L5", "L6")}
    return {"checks": checks, "result": "FAIL" if over else "PASS"}


def raises(code, fn, *a, **k):
    with pytest.raises(STP.Stop) as e:
        fn(*a, **k)
    assert e.value.stop == code
    assert e.value.status is None or e.value.status in STATUSES
    return e.value


def test_every_code_has_a_check():
    assert STP.CODES == tuple("ST%d" % i for i in range(1, 14))
    for code in STP.CODES:
        assert callable(getattr(STP, code.lower()))


def test_actions_come_from_the_frozen_protocol(fz):
    for code in STP.CODES:
        assert STP.action(fz, code) == C.protocol_row(fz.protocol_text, code).split(" | ")[1]


def test_st1(fz):
    e = raises("ST1", STP.st1, fz, leak(["L4"]))
    assert e.status == "IMPLEMENTATION_FAIL" and "不训练" in e.action
    STP.st1(fz, leak())


def test_st2(fz):
    e = raises("ST2", STP.st2, fz, False)
    assert e.status == "PIPELINE_NOT_QUALIFIED" and "重新校准" in e.action
    STP.st2(fz, True)


def test_st3(fz, contract):
    e = raises("ST3", STP.st3, fz, contract, 0.89, 0.95)
    assert e.status == "PIPELINE_NOT_QUALIFIED" and e.reason == "OPTIMIZATION_FAIL" and "不跑 L、A、S、Y" in e.action
    e = raises("ST3", STP.st3, fz, contract, 0.95, 0.69)
    assert e.reason == "OPTIMIZATION_OR_CAPACITY_UNRESOLVED"
    STP.st3(fz, contract, 0.90, 0.70)


def test_st4_st5(fz):
    e = raises("ST4", STP.st4, fz, False)
    assert e.status == "PIPELINE_NOT_QUALIFIED" and e.reason == "IMPLEMENTATION_FAIL" and "不生成 TEST" in e.action
    e = raises("ST5", STP.st5, fz, False)
    assert e.status == "PIPELINE_NOT_QUALIFIED" and e.reason == "IMPLEMENTATION_FAIL" and "不生成 TEST" in e.action
    STP.st4(fz, True)
    STP.st5(fz, True)


def test_st6(fz):
    e = raises("ST6", STP.st6, fz, [1.0, float("nan")], "F-F1-seed202 loss", True)
    assert e.status == "IMPLEMENTATION_FAIL" and not e.exclude_config
    e = raises("ST6", STP.st6, fz, [float("inf")], "F-F4-seed101 loss", False)
    assert e.status is None and e.exclude_config
    STP.st6(fz, [1.0, -2.0], "ok", True)


def test_st7(fz, contract, tmp_path):
    e = raises("ST7", STP.st7, fz, contract, 4 * 3600 + 1)
    assert e.status == "BLOCKED" and "Owner" in e.action
    raises("ST7", STP.st7, fz, contract, 3 * 3600, 3601)            # the next step would cross the limit
    STP.st7(fz, contract, 3 * 3600, 3600)
    t = [1000.0]
    path = tmp_path / "gpu_clock.json"
    clock = CP.GpuClock(path, now=lambda: t[0])
    clock.open()
    t[0] += 2 * 3600
    clock.close()
    clock.open()
    t[0] += 2 * 3600 + 5
    assert clock.used() == 4 * 3600 + 5
    raises("ST7", clock.check, fz, contract)
    clock.close()
    assert CP.GpuClock(path).used() == 4 * 3600 + 5                     # survives a new process


def test_gpu_clock_counts_a_segment_left_open_by_a_dead_process(tmp_path):
    t = [0.0]
    path = tmp_path / "gpu_clock.json"
    CP.GpuClock(path, now=lambda: t[0]).open()                          # this "process" dies without close()
    t[0] = 600.0
    later = CP.GpuClock(path, now=lambda: t[0])                         # a new process
    assert later.used() == 600.0
    with pytest.raises(RuntimeError):
        later.open()                                                    # the open segment must be closed first
    later.close()
    assert later.used() == 600.0


def test_st8(fz, contract):
    e = raises("ST8", STP.st8, fz, contract, "NVIDIA A10G", 85899345920)
    assert e.status == "BLOCKED"
    raises("ST8", STP.st8, fz, contract, "NVIDIA A100-PCIE-40GB", 42505273344)
    raises("ST8", STP.st8, fz, contract, None, 0)
    raises("ST8", STP.st8, fz, contract, A100["name"], A100["total_memory"], {"torch": "2.10.0", "transformers": "5.22.2"})
    STP.st8(fz, contract, A100["name"], A100["total_memory"], {"torch": "2.11.0+cu130", "transformers": "5.22.2"})
    raises("ST8", CP.check_device, fz, contract, M.FORMAL_MODE, {"name": "Tesla V100", "total_memory": 34359738368})
    assert CP.check_device(fz, contract, M.FORMAL_MODE, A100) == A100
    assert CP.check_device(fz, contract, M.smoke_mode(3)) == M.SMOKE_DEVICE_NOTE == "smoke: device check skipped"


def test_st9(fz, tmp_path):
    led = CP.DeviceLedger(tmp_path / "device.json")
    with pytest.raises(RuntimeError):                               # nothing recorded yet: a call-order error, not ST9
        led.check(fz, A100["name"])
    led.record_first(A100["name"])
    assert led.check(fz, A100["name"]) == A100["name"]
    e = raises("ST9", led.check, fz, "NVIDIA A100-PCIE-80GB")
    assert e.status == "BLOCKED" and e.void_pilot and "整批作废" in e.action
    with pytest.raises(RuntimeError):
        led.record_first("NVIDIA A100-PCIE-80GB")


def test_st10(fz):
    test_leak = leak(["L4"])
    e = raises("ST10", STP.st10, fz, test_leak, 0, 0)
    assert e.status == "BLOCKED" and "不评测 TEST" in e.action
    raises("ST10", STP.st10, fz, leak(), 0, 1)                      # Executor and data-auditor disagree
    raises("ST10", STP.st10, fz, leak(), 0, None)                   # no data-auditor count
    STP.st10(fz, leak(), 0, 0)


def test_st11(fz, contract):
    e = raises("ST11", STP.st11, fz, contract, 3.51)
    assert e.status == "BLOCKED" and "Owner" in e.action
    raises("ST11", STP.st11, fz, contract, float("nan"))
    STP.st11(fz, contract, 3.5)
    hours, parts = CP.estimate_total_hours(contract, mean_step_seconds=0.5, fact_tokens_per_step=128,
                                           anchor_tokens_per_step=508, dev_evaluation_seconds=40.0, used_seconds=60.0)
    assert parts["a_runs"] == 8 and parts["other_runs"] == 22
    assert parts["evaluation_units"] == (1 + 30 + 3) + 31 * 3 / 2 == 80.5
    assert math.isclose(parts["a_factor"], 1 + 8 * 508 / (6 * 128), rel_tol=1e-12)
    assert math.isclose(hours, (0.5 * 300 * (22 + 8 * parts["a_factor"]) + 40.0 * 80.5 + 60.0) / 3600, rel_tol=1e-12)
    raises("ST11", STP.st11, fz, contract, CP.estimate_total_hours(contract, 5.0, 128, 508, 40.0)[0])


def test_preflight_summary_and_flops(contract):
    log = [{"seconds": 2.0, "fact_tokens": 100}, {"seconds": 2.5, "fact_tokens": 120, "anchor_tokens": 508},
           {"seconds": 3.5, "fact_tokens": 80}]
    s = CP.preflight_summary(log, "cpu")
    assert s["seconds_per_step"] == [2.0, 0.5, 1.0] and s["mean_seconds_per_step_excluding_first"] == 0.75
    assert s["tokens_per_second"] == (628 + 80) / 1.5 and s["peak_memory_bytes"] > 0
    assert CP.flops(contract, 10, 3, "train") == 180 and CP.flops(contract, 10, 3, "forward") == 60
    from types import SimpleNamespace
    r = SimpleNamespace(fact_tokens=5, anchor_tokens=7, steps_run=2, wall_seconds=1.0)
    out = CP.run_flops(contract, r, 10)
    assert out["train_flops"] == 300 and out["anchor_flops"] == 2 * 10 * 7 + 6 * 10 * 7


def test_st12(fz, inputs_dir, generated, tmp_path):
    STP.st12(None, inputs_dir, generated["dir"])
    bad = tmp_path / "data"
    bad.mkdir()
    for p in generated["dir"].iterdir():
        if p.is_file():
            (bad / p.name).write_bytes(p.read_bytes())
    b = bytearray((bad / "dev_qa.jsonl").read_bytes())
    b[100] ^= 1
    (bad / "dev_qa.jsonl").write_bytes(bytes(b))
    with pytest.raises(ST12Error) as e:
        STP.st12(None, inputs_dir, bad)
    assert e.value.stop == "ST12" and e.value.status == "BLOCKED"
    with pytest.raises(ST12Error):
        STP.st12(None, None, bad)


def test_st13(fz, tmp_path):
    e = raises("ST13", STP.st13, fz, True)
    assert e.status == "IMPLEMENTATION_FAIL" and e.void_pilot and "全部作废" in e.action
    STP.st13(fz, False)
    # detection: no freeze record is committed in this repository, so a TEST file anywhere scanned is ST13
    d = tmp_path / "data"
    d.mkdir()
    assert STP.st13_scan(fz, fz.repo_root, [d]) == []
    (d / "general_test.jsonl").write_text("", encoding="utf-8")
    e = raises("ST13", STP.st13_scan, fz, fz.repo_root, [tmp_path / "other", d])
    assert e.void_pilot


def test_nonfinite_carries_no_status_and_st6_decides(fz):
    from metrix_e1.train import NonFinite
    from metrix_e1.errors import ProtocolStop
    e = NonFinite("loss is nan", [float("nan")])
    assert e.stop == "ST6" and e.status is None
    with pytest.raises(ValueError):
        ProtocolStop("ST7", None, "only ST6 may carry no status")
    raises("ST6", STP.st6, fz, e.values, "selected run", True)


def test_determinism_settings(contract):
    before = (torch.are_deterministic_algorithms_enabled(), os.environ.get("CUBLAS_WORKSPACE_CONFIG"),
              torch.backends.cuda.matmul.allow_tf32, torch.backends.cudnn.allow_tf32, torch.backends.cudnn.benchmark,
              torch.backends.cudnn.deterministic, torch.get_float32_matmul_precision())
    try:
        got = CP.set_determinism(contract)
        assert got["deterministic_algorithms"] is True
        assert got["CUBLAS_WORKSPACE_CONFIG"] == ":4096:8"
        assert got["cuda_matmul_allow_tf32"] is False and got["cudnn_allow_tf32"] is False
        assert got == CP.determinism_settings()
    finally:
        torch.use_deterministic_algorithms(before[0])
        if before[1] is None:
            os.environ.pop("CUBLAS_WORKSPACE_CONFIG", None)
        else:
            os.environ["CUBLAS_WORKSPACE_CONFIG"] = before[1]
        (torch.backends.cuda.matmul.allow_tf32, torch.backends.cudnn.allow_tf32, torch.backends.cudnn.benchmark,
         torch.backends.cudnn.deterministic) = before[2:6]
        torch.set_float32_matmul_precision(before[6])
