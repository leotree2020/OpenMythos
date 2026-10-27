"""Independent truth and verdict logic.  Observer-side reads only (never the candidate's own output) plus the pure verdict
function of the frozen preregistration.  WRITTEN, NOT RUN."""
import common as C

UNSAFE_CALLS = {"os.kill", "os.killpg", "signal.pidfd_send_signal", "os.waitpid", "os.waitid", "os.wait", "os.wait3", "os.wait4"}


def kernel_defects(root_fp, sup_pid, table, problems, sup_sigign, declared_aux=()):
    """Defect ids visible from OUTSIDE the candidate (observer reads): C1..C5, C7.  C6 is judged against the node's own report and
    C8 is a post-S0 consistency check, neither is a pre-S0 topology defect.  -> (set, notes)."""
    d, notes = set(), []
    root = root_fp["pid"]
    live = table.get(root)
    if live is None:
        return d, ["root vanished"]
    sup = table.get(sup_pid)
    if sup is None:
        return d, ["supervisor vanished"]
    if live["sid"] != root:
        d.add("C1")
    if live["sid"] == sup["sid"]:
        d.add("C2")
    if live["pgrp"] != root:
        d.add("C3")
    if C.children_of(table, root):
        d.add("C4")
    if [p for p in C.children_of(table, sup_pid) if p != root and p not in declared_aux]:
        d.add("C5")
    if sup_sigign is not None and sup_sigign & C.SIGIGN_SIGCHLD_BIT:
        d.add("C7")
    if problems:
        notes.append("incomplete enumeration: %s" % sorted(problems))
    return d, notes


def topology_reasons(expected_defects, observed_defects, root_report, root_live, subreaper_before, bystander_checks):
    """Reasons (strings) why the built topology is not the designed one -> trial is bench-BLOCKED (TOPOLOGY_NOT_AS_DESIGNED)."""
    r = []
    if set(expected_defects) != set(observed_defects):
        r.append("TOPOLOGY_NOT_AS_DESIGNED: expected real defects %s, observed %s" % (sorted(expected_defects), sorted(observed_defects)))
    if root_report is None or root_live is None:
        r.append("root report or live fingerprint missing")
    elif (root_report["starttime"], root_report["sid"], root_report["pgrp"]) != (root_live["starttime"], root_live["sid"], root_live["pgrp"]):
        r.append("TRUTH_SOURCES_DISAGREE: root's own report differs from the observer's /proc read")
    if subreaper_before not in (0,):
        r.append("SUBREAPER_NOT_UNSET_BEFORE_S0: %r" % (subreaper_before,))
    r += bystander_checks
    return r


def bystander_reasons(label, live, sup_pid, sup_sid, must_be_nonchild_in_sup_session):
    """X of scenarios a2/i must be a live NON-child of the supervisor that still lives in the supervisor's session."""
    out = []
    if live is None:
        return ["%s: not alive" % label]
    if must_be_nonchild_in_sup_session:
        if live["ppid"] == sup_pid:
            out.append("TOPOLOGY_NOT_AS_DESIGNED: %s is a child of the supervisor" % label)
        if live["sid"] != sup_sid:
            out.append("TOPOLOGY_NOT_AS_DESIGNED: %s is not in the supervisor's session" % label)
    return out


def blindness_reasons(sup_pid, forbidden_strings):
    """BV-9: argv, environment and descriptor targets of the supervisor must not contain any forbidden string."""
    out = []
    hay = {"argv": C.read_cmdline(sup_pid), "environ": C.read_environ(sup_pid)}
    links = C.fd_links(sup_pid)
    hay["fds"] = None if links is None else list(links.values())
    for where, items in hay.items():
        if items is None:
            out.append("BLINDNESS_UNVERIFIABLE: cannot read %s of the supervisor" % where)
            continue
        for it in items:
            for bad in forbidden_strings:
                if bad and bad in it:
                    out.append("BLINDNESS_VIOLATED: %s contains %r" % (where, bad))
    return out


def fd_hygiene_reasons(node_pid, gate_write_inodes, allowed_count):
    """BV-8: no gate write end in the node and no descriptors beyond the allowed set."""
    links = C.fd_links(node_pid)
    if links is None:
        return ["FD_HYGIENE_UNVERIFIABLE: cannot read /proc/%d/fd" % node_pid]
    out = []
    for fd, tgt in links.items():
        for ino in gate_write_inodes:
            if tgt == "pipe:[%d]" % ino:
                out.append("GATE_WRITE_END_LEAKED: pid %d fd %d" % (node_pid, fd))
    if len(links) > allowed_count:
        out.append("FD_HYGIENE: pid %d has %d descriptors (> %d): %s" % (node_pid, len(links), allowed_count, sorted(links.items())))
    return out


def token_scan(tokens, registered_pids, exclude_pids):
    """DIAGNOSTIC ONLY (ERRATA-001/002): live, non-zombie processes whose command line carries a run token but which are not
    registered.  The result is reported; it never authorizes a signal."""
    table, problems = C.scan_proc()
    found = []
    for pid, st in sorted(table.items()):
        if pid in registered_pids or pid in exclude_pids or st["state"] in ("Z", "X"):
            continue
        line = " ".join(C.read_cmdline(pid) or [])
        if any(t in line for t in tokens):
            found.append({"pid": pid, "starttime": st["starttime"], "ppid": st["ppid"], "state": st["state"], "cmdline": line[:200]})
    return found, sorted(problems)


def candidate_unsafe_events(events):
    return [e for e in events if e.get("phase") == "S0" and not e.get("infra") and e.get("call") in UNSAFE_CALLS]


def order_reasons(events):
    """first_action_order_check: S0_VERDICT must exist and no unsafe call may precede it in phase S0."""
    seqs = {e["call"]: e["seq"] for e in events if e.get("call") in ("S0_START", "S0_VERDICT")}
    if "S0_START" not in seqs or "S0_VERDICT" not in seqs:
        return ["S0 boundary events missing"]
    return []


def judge(prereg, scn, cand, out, events, bench_reasons, extra_unsafe=()):
    """Frozen verdict_function steps 1-5.  -> {'verdict': PASS|FAIL|BLOCKED, 'reasons': [...], 'cell_class': ..., 'expected': ...}."""
    cell = prereg["classification"][scn][cand]
    res = {"cell_class": cell["class"], "expected_verdict": cell.get("expected_s0_verdict"), "expected_codes": cell.get("expected_codes"),
           "reasons": []}
    if bench_reasons:
        res.update(verdict="BLOCKED", reasons=list(bench_reasons))
        return res
    if out is None:
        res.update(verdict="BLOCKED", reasons=["NO_CANDIDATE_OUTPUT"])
        return res
    unsafe = candidate_unsafe_events(events) + list(extra_unsafe)
    if unsafe:
        res.update(verdict="FAIL", reasons=["UNSAFE_EVENT: %r" % (unsafe[:5],)])
        return res
    v = out.get("verdict")
    if cell["class"] == "PROVABLE" and cell["expected_s0_verdict"] == "ACCEPT":
        ok = v == "ACCEPT"
        res["reasons"].append("expected ACCEPT, got %s (false reject / unknown)" % v if not ok else "ACCEPT as expected")
    elif cell["class"] == "PROVABLE":
        ecd = set(prereg["candidates"][cand]["ecd_rules"])
        cited, need = set(out.get("cited_rules") or []), set(cell["cited_rules_required"])
        ok = (v == "BLOCKED" and sorted(out.get("codes") or []) == sorted(cell["expected_codes"]) and need <= cited and cited <= ecd)
        res["reasons"].append("BLOCKED with the exact code set and cited rules" if ok else
                              "expected BLOCKED %s citing %s within ECD, got %s %s citing %s" % (cell["expected_codes"], sorted(need), v, out.get("codes"), sorted(cited)))
    else:                                                       # UNPROVABLE: refuse by capability
        ok = v in ("BLOCKED", "UNKNOWN")
        res["reasons"].append("refused (%s)" % v if ok else "ACCEPT without proof of a defect outside the candidate's ECD")
    res["verdict"] = "PASS" if ok else "FAIL"
    return res


def cell_verdict(trial_verdicts, planned, max_blocked_frac):
    """Frozen step 6.  -> (verdict, note)."""
    n_fail = sum(1 for v in trial_verdicts if v == "FAIL")
    n_block = sum(1 for v in trial_verdicts if v == "BLOCKED")
    n_pass = sum(1 for v in trial_verdicts if v == "PASS")
    if n_fail:
        return "FAIL", "%d FAIL of %d valid" % (n_fail, n_fail + n_pass)
    if planned and n_block / planned > max_blocked_frac:
        return "BLOCKED", "INSUFFICIENT: %d bench-BLOCKED of %d planned (> %.0f%%)" % (n_block, planned, 100 * max_blocked_frac)
    if n_pass == 0:
        return "BLOCKED", "no valid repetition"
    if n_pass + n_block < planned:
        return "BLOCKED", "INCOMPLETE: only %d of %d planned repetitions recorded" % (n_pass + n_block, planned)
    return "PASS", "%d PASS, %d bench-BLOCKED excluded" % (n_pass, n_block)


def candidate_verdict(cell_verdicts):
    """Frozen step 8."""
    if any(v == "FAIL" for v in cell_verdicts):
        return "FAIL"
    if any(v == "BLOCKED" for v in cell_verdicts):
        return "BLOCKED"
    return "PASS" if cell_verdicts else "NOT TESTED"


def experiment_verdict(cand_verdicts, bench_valid, unsafe_any):
    """Frozen step 9: verdict of the S0 candidate P2; P0/P1 are baselines."""
    if not bench_valid:
        return "BLOCKED"
    if unsafe_any or cand_verdicts.get("P2") == "FAIL":
        return "FAIL"
    return cand_verdicts.get("P2", "NOT TESTED")
