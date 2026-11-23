"""Stop conditions ST1-ST13 of METRIX E1-PILOT.

Protocol v1.1 section 11 (events and actions), section 9 (statuses), section 8 (the steps the stops belong to).
Each check raises Stop (an errors.ProtocolStop) when its event holds; the exception carries the stop code, the
section 9 status, the action text of the frozen protocol row (read from the frozen protocol, not written here) and
two flags: `void_pilot` (ST9, ST13: every result of the pilot is void) and `exclude_config` (ST6 outside the selected
configurations and the controls: the configuration is dropped from selection, section 7). Statuses that section 11
does not state are interpretation B16. Thresholds come from metrix_e1.contract.

ST12 is raised by metrix_e1.frozen and metrix_e1.data (errors.ST12Error); st12() runs those checks.
"""
import math
from pathlib import Path

from . import contract as C
from . import data as D
from . import frozen as FZ
from .errors import ProtocolStop, ST8Error, ST12Error

CODES = tuple("ST%d" % i for i in range(1, 14))


class Stop(ProtocolStop):
    def __init__(self, code, status, action, message, reason=None, void_pilot=False, exclude_config=False):
        super().__init__(code, status, "%s [%s]%s" % (message, action, " reason %s" % reason if reason else ""))
        self.action = action
        self.reason = reason
        self.void_pilot = void_pilot
        self.exclude_config = exclude_config


def action(fz, code):
    """The action cell of the frozen protocol row of `code`."""
    cells = C.protocol_row(fz.protocol_text, code).split(" | ")
    if len(cells) != 2:
        raise ValueError("protocol row %s does not have an event and an action cell" % code)
    return cells[1]


def st1(fz, leakage_report):
    """Step 2: any leakage check over its limit -> stop; no training; IMPLEMENTATION_FAIL."""
    over = sorted(c for c, x in leakage_report["checks"].items() if not x["within_limit"])
    if over or leakage_report["result"] != "PASS":
        raise Stop("ST1", "IMPLEMENTATION_FAIL", action(fz, "ST1"), "leakage over limit: %s" % over)


def st2(fz, g03_satisfied):
    """Step 3: N does not satisfy G0.3 -> stop; no training; PIPELINE_NOT_QUALIFIED (recalibration)."""
    if not g03_satisfied:
        raise Stop("ST2", "PIPELINE_NOT_QUALIFIED", action(fz, "ST2"), "N does not satisfy G0.3")


def st3(fz, contract, acc_cb_f101, acc_dev_learned_f101):
    """Step 4: F's selected configuration (search seed) has Acc_CB below the ST3 bound or Acc(F, DEV-QA, learned)
    below the ST3 bound -> stop; no L, A, S, Y (B16: PIPELINE_NOT_QUALIFIED with a section 9 reason)."""
    s = contract.stops
    if acc_cb_f101 < s.st3_cb_min or acc_dev_learned_f101 < s.st3_acc_min:
        reason = "OPTIMIZATION_FAIL" if acc_cb_f101 < s.st3_cb_min else "OPTIMIZATION_OR_CAPACITY_UNRESOLVED"
        raise Stop("ST3", "PIPELINE_NOT_QUALIFIED", action(fz, "ST3"),
                   "positive control: Acc_CB %.4f (min %g), Acc(F, DEV-QA, learned) %.4f (min %g)" % (
                       acc_cb_f101, s.st3_cb_min, acc_dev_learned_f101, s.st3_acc_min), reason=reason)


def st4(fz, g07_satisfied):
    """Y does not satisfy G0.7 -> stop; no TEST."""
    if not g07_satisfied:
        raise Stop("ST4", "PIPELINE_NOT_QUALIFIED", action(fz, "ST4"), "Y does not satisfy G0.7",
                   reason="IMPLEMENTATION_FAIL")


def st5(fz, g06_satisfied):
    """S does not satisfy G0.6 -> stop; no TEST."""
    if not g06_satisfied:
        raise Stop("ST5", "PIPELINE_NOT_QUALIFIED", action(fz, "ST5"), "S does not satisfy G0.6",
                   reason="IMPLEMENTATION_FAIL")


def st6(fz, values, what, selected_or_control):
    """Any non-finite value in a training run or an evaluation -> stop that run. In a selected configuration or a
    control: IMPLEMENTATION_FAIL; otherwise the configuration is excluded from selection (section 7)."""
    bad = [x for x in values if not math.isfinite(x)]
    if bad:
        if selected_or_control:
            raise Stop("ST6", "IMPLEMENTATION_FAIL", action(fz, "ST6"), "%s: %d non-finite values" % (what, len(bad)))
        raise Stop("ST6", None, action(fz, "ST6"), "%s: %d non-finite values; configuration excluded" % (
            what, len(bad)), exclude_config=True)


def st7(fz, contract, used_seconds, next_seconds=0.0):
    """Cumulative GPU wall-clock above the limit, or a next step that would take it above -> stop and report (B16:
    BLOCKED)."""
    limit = contract.stops.st7_hours * 3600.0
    if used_seconds > limit or used_seconds + next_seconds > limit:
        raise Stop("ST7", "BLOCKED", action(fz, "ST7"), "GPU wall-clock %.0f s used + %.0f s next > limit %.0f s" % (
            used_seconds, next_seconds, limit))


def st8(fz, contract, device_name, total_memory, libraries=None):
    """Environment not as section 0 / section 7 require: device name prefix, total memory, library versions."""
    tr = contract.training
    if device_name is None or not device_name.startswith(tr.device_prefix) or total_memory < tr.device_min_gib * 2 ** 30:
        raise Stop("ST8", "BLOCKED", action(fz, "ST8"), "device %r with %r bytes; required: name starting %r and at "
                   "least %d GiB" % (device_name, total_memory, tr.device_prefix, tr.device_min_gib))
    try:
        FZ.check_library_versions(fz.data_manifest, libraries)
    except ST8Error as e:
        raise Stop("ST8", "BLOCKED", action(fz, "ST8"), str(e)) from e


def st9(fz, recorded_name, current_name):
    """The full device name read at the start of a run differs from the recorded one -> the whole batch is void;
    BLOCKED; restart from section 8 step 3 on a machine with the recorded name."""
    if recorded_name is None or current_name != recorded_name:
        raise Stop("ST9", "BLOCKED", action(fz, "ST9"), "device name %r, recorded %r" % (current_name, recorded_name),
                   void_pilot=True)


def st10(fz, test_leakage_report, executor_l6, auditor_l6):
    """Step 8: any TEST part of L3-L6 over its limit, or the L6 TEST counts of Executor and data-auditor differ ->
    stop; no TEST evaluation; BLOCKED; report to the Owner."""
    over = sorted(c for c, x in test_leakage_report["checks"].items() if not x["within_limit"])
    if over or test_leakage_report["result"] != "PASS" or auditor_l6 is None or executor_l6 != auditor_l6:
        raise Stop("ST10", "BLOCKED", action(fz, "ST10"), "TEST part over limit %s; L6 TEST Executor %r, data-auditor %r" % (
            over, executor_l6, auditor_l6))


def st11(fz, contract, estimate_hours):
    """Preflight estimate above the ST11 bound -> stop; report to the Owner (B16: BLOCKED)."""
    if not math.isfinite(estimate_hours) or estimate_hours > contract.stops.st11_hours:
        raise Stop("ST11", "BLOCKED", action(fz, "ST11"), "preflight estimate %.3f h > %g h" % (
            estimate_hours, contract.stops.st11_hours))


def st12(repo_root=None, inputs_dir=None, data_dir=None):
    """ST12 at the start of a step: PROTOCOL_FROZEN, the four frozen files (git cat-file), and, when given, the
    inputs and the data directory (data.verify). Raises errors.ST12Error. Returns the loaded Frozen."""
    fz = FZ.load(repo_root)
    if data_dir is not None:
        if inputs_dir is None:
            raise ST12Error("the data directory is checked against its regeneration from the inputs; no inputs given")
        D.verify(fz, inputs_dir, data_dir)
    return fz


def st13(fz, test_read_before_freeze):
    """TEST read before the configurations are frozen -> IMPLEMENTATION_FAIL; the whole pilot is void. The flag is
    the caller's knowledge; st13_scan() detects the files."""
    if test_read_before_freeze:
        raise Stop("ST13", "IMPLEMENTATION_FAIL", action(fz, "ST13"), "TEST read before the configuration freeze",
                   void_pilot=True)


def st13_scan(fz, repo_root, dirs):
    """ST13 by detection: while the freeze record of the selected configurations is not committed, a TEST file
    (test_qa.jsonl, general_test.jsonl) in any of `dirs` means TEST was generated before the freeze."""
    from . import record as R
    try:
        R.committed_json(repo_root, R.SELECTION_FREEZE_REL)
        return []
    except R.NotCommitted:
        pass
    found = [str(Path(d) / n) for d in dirs for n in D.TEST_FILES if (Path(d) / n).exists()]
    st13(fz, bool(found))
    return found
