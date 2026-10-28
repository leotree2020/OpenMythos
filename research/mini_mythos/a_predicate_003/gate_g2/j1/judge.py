"""J1 judge: pure function `evaluate(assertion_id, subject_observables, declared_trust_model)`.  NOT TESTED / NEVER EXECUTED.

    * Pure and deterministic: no I/O, no clock, no /proc, no randomness, no process, no signal, no Bench import, no oracle import.
    * Lane S only: the input is validated by schema.validate_input (closed whitelist, answer firewall, harness-bound trust map).  A malformed or
      Lane-O-tainted input is a BLOCKED result with code INPUT_INVALID -- it is never a verdict about the subject and is never silently repaired.
    * The verdict is derived from observed records and from the roles the harness granted; there is no fixture-keyed table, no per-assertion
      constant, and no way to ask for a fixture id.  Authority comes ONLY from the trust map (roles are capped by schema.ROLE_CEILING); a record
      can never promote itself, and NODE_CLAIM_SIM / SUBJECT_LOG_READBACK never carry authority.
    * PASS means "established inside the stated data and the stated synthetic trust" -- see ACCEPTED_CLAIM.  It never means native B0 safety.

Coverage honesty (V0.1): ATTRIBUTION, UNIQUE_REGISTRY, ZOMBIE_AT_T, LOG_MATCHES_SEAL and WRITE_COMPLETE have contrasting outcomes.  PREVENT_PROOF,
LAWFUL_REAP, EVIDENCE_USABLE and DELIVERY are SMOKE_ONLY: V0.1 defines no trusted source that could ever establish them, so their handlers validate
the input and explain WHY the evidence is insufficient (distinct basis codes) but have NO PASS path.  Nothing here claims they discriminate.

Frozen semantics pinned from bench source (read-only, by value): RELEASED is written BEFORE `os.write(R)` and is only the release INTENT;
REGISTERED is the observer's registration of a creator-reported pid; a zombie, a DEAD record or ECHILD is never a lawful reap.
"""
from . import codec
from . import schema as S

ACCEPTED_CLAIM = {
    "ATTRIBUTION": "Observed agreement between the B0-registered identity and the harness-declared SIMULATED trusted gate-child witness for the same "
                   "node token. Not a proof of unique fork, of lineage, of the recipient of R, or of native B0 safety.",
    "UNIQUE_REGISTRY": "No duplicate (pid, starttime) among the supplied, prerequisite-complete B0 REGISTERED records. Not a statement about "
                       "unobserved processes, kernel PID reuse or native B0 safety.",
    "ZOMBIE_AT_T": "The pinned identity was in state Z in the single trusted snapshot. Not a lawful reap, not an exit status, not a statement "
                   "about any other time.",
    "LOG_MATCHES_SEAL": "The read-back log bytes, final sequence, last digest and run id match the independently declared SIMULATED seal manifest. "
                        "Integrity of bytes only: not event authenticity, not custody, not kernel provenance.",
    "WRITE_COMPLETE": "The harness-declared SIMULATED trusted write wrapper recorded a one-byte R write without error. Not delivery, not the "
                      "recipient, not a first action.",
}

_DUPLICATE_UNIQUE_KINDS = ("INTENT", "FORKED", "REGISTERED", "RELEASED", "DEAD")


# ---------------------------------------------------------------- helpers
def _result(assertion_id, verdict, codes, refs, diagnostics=()):
    valid = type(assertion_id) is str and assertion_id in S.ASSERTION_IDS
    if valid and assertion_id in S.EVIDENCE_SENSITIVE:
        coverage = "DISCRIMINATIVE"
    elif valid:
        coverage = "SMOKE_ONLY"
    else:
        coverage = None
    return {
        "assertion_id": assertion_id if valid else None,
        "subject_verdict": verdict,
        "evidence_basis_codes": sorted(set(codes)),
        "supporting_observable_refs": sorted(set(refs)),
        "accepted_claim": ACCEPTED_CLAIM.get(assertion_id) if (valid and verdict == S.PASS) else None,
        "coverage": coverage,
        "input_diagnostics": list(diagnostics),
        "measurement_target": S.MEASUREMENT_TARGET,
        "native_B0_safety_status": S.NATIVE_B0_SAFETY_STATUS,
        "scope": S.SCOPE,
    }


def _auth(events, trust, role, kind=None):
    """Events whose source holds `role` AND whose role can carry authority (the harness table decides; the record cannot)."""
    out = []
    for e in events:
        t = trust[e.source_handle]
        if t.role == role and t.authority and (kind is None or e.event_kind == kind):
            out.append(e)
    return out


def _claims(events, trust, claim_kind):
    return [e for e in events if trust[e.source_handle].role == S.ROLE_NODE_CLAIM and e.event_kind == "NODE_CLAIM"
            and e.raw.get("claim_kind") == claim_kind]


def _aggregate(verdicts):
    if S.FAIL in verdicts:
        return S.FAIL
    if S.BLOCKED in verdicts or not verdicts:
        return S.BLOCKED
    return S.PASS


def _ledger_prerequisite_problems(evs):
    """Prerequisites for treating ONE source's B0 records as a complete scoped ledger (implementer proposal, open question OQ-4).  `evs` sorted by
    order.  Rules mirror bench/registry.py::lifecycle_issues / check_order, re-stated by value (J1 never imports the Bench)."""
    p = set()
    if [e.order for e in evs] != list(range(1, len(evs) + 1)):
        p.add("SEQ_NOT_CONTIGUOUS_FROM_1")
    kinds = [e.event_kind for e in evs]
    starts = [i for i, k in enumerate(kinds) if k == "RUN_START"]
    if len(starts) != 1 or starts[0] != 0:
        p.add("RUN_START_NOT_SINGLE_FIRST")
    ends = [i for i, k in enumerate(kinds) if k == "RUN_END"]
    if len(ends) > 1 or (ends and ends[0] != len(kinds) - 1):
        p.add("RUN_END_NOT_SINGLE_LAST")
    seen = {}
    dead = set()
    for e in evs:
        n = e.node_token
        if n is None:
            continue
        d = seen.setdefault(n, set())
        k = e.event_kind
        if n in dead:
            p.add("RECORD_AFTER_DEAD")
        if k in _DUPLICATE_UNIQUE_KINDS and k in d:
            p.add("DUPLICATE_" + k)
        if k in ("FORKED", "REGISTERED") and "INTENT" not in d:
            p.add(k + "_WITHOUT_INTENT")
        if k == "RELEASED" and "REGISTERED" not in d:
            p.add("RELEASED_WITHOUT_REGISTERED")
        d.add(k)
        if k == "DEAD":
            dead.add(n)
    for n, d in seen.items():
        if "RELEASED" in d and "ABORTED" in d:
            p.add("RELEASED_AND_ABORTED")
    return p


def _seal_outcome(events, trust):
    """-> (state, codes, refs); state in MATCH | MISMATCH | UNAVAILABLE.  UNAVAILABLE never becomes a FAIL: a missing / untrusted / unreadable
    / malformed seal or log is lack of evidence, not an observed contradiction."""
    codes, refs = set(), set()
    logs = [e for e in events if trust[e.source_handle].role == S.ROLE_SUBJECT_LOG and e.event_kind == "LOG_READBACK"]
    if not logs:
        codes.add("NO_LOG_READBACK")
        return "UNAVAILABLE", codes, refs
    if len(logs) != 1:
        codes.add("MULTIPLE_LOG_READBACKS")
        return "UNAVAILABLE", codes, refs
    log = logs[0]
    refs.add(log.ref)
    if log.read_status != "OK":
        codes.add("LOG_READ_NOT_OK")
        return "UNAVAILABLE", codes, refs
    mans = _auth(events, trust, S.ROLE_SEAL_MANIFEST, "SEAL_MANIFEST")
    if not mans:
        codes.add("NO_TRUSTED_SEAL_MANIFEST")
        return "UNAVAILABLE", codes, refs
    for m in mans:
        refs.add(m.ref)
    if any(m.read_status != "OK" for m in mans):
        codes.add("SEAL_READ_NOT_OK")
        return "UNAVAILABLE", codes, refs
    first = mans[0].raw
    if any(m.raw != first for m in mans):
        codes.add("CONFLICTING_SEAL_MANIFESTS")
        return "UNAVAILABLE", codes, refs
    status, reasons = codec.compare_seal(log.raw["log_utf8"], log.raw["run_id"], first)
    for r in reasons:
        codes.add("SEAL_" + r)
    if status == codec.MATCH:
        return "MATCH", codes, refs
    if status == codec.MISMATCH:
        return "MISMATCH", codes, refs
    return "UNAVAILABLE", codes, refs


# ---------------------------------------------------------------- the five discriminative assertions
def _attribution(events, trust):
    codes, refs = set(), set()
    ledger = _auth(events, trust, S.ROLE_B0_LEDGER)
    if any(e.read_status != "OK" for e in ledger):
        codes.add("LEDGER_READ_NOT_OK")
        return S.BLOCKED, codes, refs
    regs = [e for e in ledger if e.event_kind == "REGISTERED"]
    if not regs:
        codes.add("NO_B0_REGISTERED_RECORD")
        return S.BLOCKED, codes, refs
    witnesses = _auth(events, trust, S.ROLE_G2_WITNESS, "GATE_CHILD_OBSERVATION")
    claims = _claims(events, trust, "GATE_CHILD_IDENTITY")
    releases = {}
    for e in ledger:
        if e.event_kind == "RELEASED":
            releases[e.node_token] = e
    by_node = {}
    for e in regs:
        by_node.setdefault(e.node_token, []).append(e)
    verdicts = []
    for node in sorted(by_node):
        recs = by_node[node]
        if len(recs) != 1:
            codes.add("DUPLICATE_REGISTERED_RECORD_FOR_NODE")
            verdicts.append(S.BLOCKED)
            continue
        reg = recs[0]
        refs.add(reg.ref)
        if reg.identity.ppid is not None:
            codes.add("PPID_NOT_USED_AS_LINEAGE_PROOF")
        if any(c.node_token == node for c in claims):
            codes.add("UNTRUSTED_NODE_CLAIM_NOT_EVIDENCE")
        usable = []
        for w in witnesses:
            if w.node_token != node:
                continue
            if w.read_status != "OK":
                codes.add("WITNESS_READ_NOT_OK")
                continue
            if w.gate_token is not None and reg.gate_token is not None and w.gate_token != reg.gate_token:
                codes.add("WITNESS_GATE_TOKEN_MISMATCH")
                continue
            usable.append(w)
        if not usable:
            codes.add("NO_TRUSTED_GATE_CHILD_WITNESS")
            verdicts.append(S.BLOCKED)
            continue
        for w in usable:
            refs.add(w.ref)
        first = usable[0].identity
        if not all(w.identity.same_instance(first) for w in usable):
            codes.add("CONFLICTING_TRUSTED_WITNESSES")
            verdicts.append(S.BLOCKED)
            continue
        rel = releases.get(node)
        if rel is None:
            codes.add("WITNESS_ORDER_NOT_COMPARABLE_NO_RELEASED_RECORD")
        elif all(w.order < rel.order for w in usable):
            codes.add("WITNESS_BEFORE_RELEASED_INTENT")
        else:
            codes.add("WITNESS_NOT_BEFORE_RELEASED_INTENT")
        if reg.identity.same_instance(first):
            codes.add("ATTRIBUTION_AGREEMENT_OBSERVED_UNDER_SIMULATED_TRUST")
            verdicts.append(S.PASS)
        else:
            codes.add("ATTRIBUTION_MISMATCH_OBSERVED_UNDER_SIMULATED_TRUST")
            verdicts.append(S.FAIL)
    return _aggregate(verdicts), codes, refs


def _unique_registry(events, trust):
    codes, refs = set(), set()
    ledger = _auth(events, trust, S.ROLE_B0_LEDGER)
    if not ledger:
        codes.add("NO_B0_LEDGER")
        return S.BLOCKED, codes, refs
    good = [e for e in ledger if e.read_status == "OK"]
    regs = [e for e in good if e.event_kind == "REGISTERED"]
    duplicate = False
    for i in range(len(regs)):
        for j in range(i + 1, len(regs)):
            a, b = regs[i], regs[j]
            if a.node_token != b.node_token and a.identity.same_instance(b.identity):
                duplicate = True
                refs.add(a.ref)
                refs.add(b.ref)
    if duplicate:                      # a positive contradiction inside the supplied OK records, whatever else is incomplete
        codes.add("DUPLICATE_PID_STARTTIME_ACROSS_NODES")
        return S.FAIL, codes, refs
    if len(good) != len(ledger):
        codes.add("LEDGER_READ_NOT_OK")
        return S.BLOCKED, codes, refs
    by_handle = {}
    for e in ledger:
        by_handle.setdefault(e.source_handle, []).append(e)
    for handle in sorted(by_handle):
        evs = sorted(by_handle[handle], key=lambda x: x.order)
        for pcode in sorted(_ledger_prerequisite_problems(evs)):
            codes.add("LEDGER_PREREQUISITE_FAILED_" + pcode)
    if any(c.startswith("LEDGER_PREREQUISITE_FAILED_") for c in codes):
        return S.BLOCKED, codes, refs
    if not regs:
        codes.add("NO_B0_REGISTERED_RECORD")
        return S.BLOCKED, codes, refs
    for e in regs:
        refs.add(e.ref)
    codes.add("NO_DUPLICATE_IN_SUPPLIED_COMPLETE_SET")
    return S.PASS, codes, refs


def _zombie_at_t(events, trust):
    codes, refs = set(), set()
    ledger = _auth(events, trust, S.ROLE_B0_LEDGER)
    snaps = _auth(events, trust, S.ROLE_KERNEL_SNAPSHOT, "KERNEL_SNAPSHOT")
    if _claims(events, trust, "OTHER") or _claims(events, trust, "WAIT_RESULT") or _claims(events, trust, "READY"):
        codes.add("UNTRUSTED_NODE_CLAIM_NOT_EVIDENCE")
    if not snaps:
        codes.add("NO_TRUSTED_KERNEL_SNAPSHOT")
        return S.BLOCKED, codes, refs
    for s in snaps:
        refs.add(s.ref)
    if any(s.read_status != "OK" for s in snaps):
        codes.add("SNAPSHOT_READ_NOT_OK")
        return S.BLOCKED, codes, refs
    if any(e.read_status != "OK" for e in ledger):
        codes.add("LEDGER_READ_NOT_OK")
        return S.BLOCKED, codes, refs
    first = snaps[0].identity
    if not all(s.identity.same_instance(first) for s in snaps):
        codes.add("MULTIPLE_SNAPSHOT_SUBJECTS")
        return S.BLOCKED, codes, refs
    if len(snaps) != 1:
        codes.add("MULTIPLE_SNAPSHOTS_T_NOT_SELECTED")          # OQ-1: the V0.1 assertion has no selector for T
        return S.BLOCKED, codes, refs
    regs = [e for e in ledger if e.event_kind == "REGISTERED"]
    if regs:
        if not any(r.identity.same_instance(first) for r in regs):
            codes.add("SNAPSHOT_NOT_PINNED_TO_REGISTERED_IDENTITY")
            return S.BLOCKED, codes, refs
        codes.add("IDENTITY_PINNED_BY_B0_REGISTERED")
    else:
        codes.add("IDENTITY_PINNED_BY_SNAPSHOT_ONLY")
    if snaps[0].raw["state"] == "Z":
        codes.add("ZOMBIE_STATE_OBSERVED_AT_T")
        codes.add("ZOMBIE_IS_NOT_LAWFUL_REAP")
        return S.PASS, codes, refs
    codes.add("NOT_ZOMBIE_AT_T")
    return S.FAIL, codes, refs


def _log_matches_seal(events, trust):
    state, codes, refs = _seal_outcome(events, trust)
    if state == "MATCH":
        return S.PASS, codes, refs
    if state == "MISMATCH":
        return S.FAIL, codes, refs
    return S.BLOCKED, codes, refs


def _write_complete(events, trust):
    codes, refs = set(), set()
    ledger = _auth(events, trust, S.ROLE_B0_LEDGER)
    released = {e.node_token: e for e in ledger if e.event_kind == "RELEASED"}
    for e in released.values():
        refs.add(e.ref)
    if released:
        codes.add("B0_RELEASED_IS_INTENT_NOT_DELIVERY")
    if _claims(events, trust, "R_WRITTEN"):
        codes.add("UNTRUSTED_WRITE_CLAIM_NOT_EVIDENCE")
    wraps = _auth(events, trust, S.ROLE_G2_WRAP, "R_WRITE_RESULT")
    if not wraps:
        codes.add("NO_TRUSTED_WRAPPER_RESULT")
        return S.BLOCKED, codes, refs
    for w in wraps:
        refs.add(w.ref)
    if any(w.read_status != "OK" for w in wraps):
        codes.add("WRAPPER_READ_NOT_OK")
        return S.BLOCKED, codes, refs
    by_node = {}
    for w in wraps:
        by_node.setdefault(w.node_token, []).append(w)
    verdicts = []
    for node in sorted(by_node):
        group = by_node[node]
        if released and node not in released:
            codes.add("WRAPPER_NODE_HAS_NO_RELEASED_RECORD")
            verdicts.append(S.BLOCKED)
            continue
        sig = (group[0].raw["bytes"], group[0].raw["errno"])
        if any((w.raw["bytes"], w.raw["errno"]) != sig for w in group):
            codes.add("CONFLICTING_WRAPPER_RESULTS")
            verdicts.append(S.BLOCKED)
            continue
        nbytes, errno = sig
        if nbytes >= 2:
            codes.add("WRAPPER_BYTES_EXCEED_ONE_BYTE_WRITE")
            verdicts.append(S.BLOCKED)
        elif nbytes == 1 and errno is not None:
            codes.add("CONTRADICTORY_WRAPPER_RESULT")
            verdicts.append(S.BLOCKED)
        elif nbytes == 1:
            codes.add("R_WRITE_COMPLETED_NOT_RECIPIENT_PROOF")
            verdicts.append(S.PASS)
        else:
            codes.add("R_WRITE_NOT_COMPLETE")
            verdicts.append(S.FAIL)
    return _aggregate(verdicts), codes, refs


# ---------------------------------------------------------------- the four SMOKE_ONLY assertions (no PASS path in V0.1, by design)
def _smoke_common(events, trust):
    codes, refs = set(), set()
    codes.add("SMOKE_ONLY_NO_PASS_PATH_IN_V0_1")
    ledger = _auth(events, trust, S.ROLE_B0_LEDGER)
    for e in ledger:
        if e.event_kind == "RELEASED":
            codes.add("B0_RELEASED_IS_INTENT_NOT_DELIVERY")
            refs.add(e.ref)
    return codes, refs, ledger


def _prevent_proof(events, trust):
    codes, refs, ledger = _smoke_common(events, trust)
    codes.add("NO_PRE_RELEASE_WITNESS_SOURCE_IN_V0_1")
    if _claims(events, trust, "READY"):
        codes.add("UNTRUSTED_READY_CLAIM_NOT_PREVENTION")
    released = {e.node_token: e for e in ledger if e.event_kind == "RELEASED"}
    for w in _auth(events, trust, S.ROLE_G2_WITNESS, "GATE_CHILD_OBSERVATION"):
        rel = released.get(w.node_token)
        if rel is not None and w.order < rel.order:
            codes.add("PRE_RELEASE_WITNESS_PRESENT_BUT_PREVENT_PROOF_UNDEFINED")
            refs.add(w.ref)
    return S.BLOCKED, codes, refs


def _lawful_reap(events, trust):
    codes, refs, ledger = _smoke_common(events, trust)
    codes.add("NO_TRUSTED_WAIT_WITNESS_SOURCE_IN_V0_1")
    for e in ledger:
        if e.event_kind == "DEAD":
            codes.add("DEAD_RECORD_IS_NOT_REAP")
            refs.add(e.ref)
    for s in _auth(events, trust, S.ROLE_KERNEL_SNAPSHOT, "KERNEL_SNAPSHOT"):
        if s.raw["state"] == "Z":
            codes.add("ZOMBIE_IS_NOT_REAP")
            refs.add(s.ref)
    if _claims(events, trust, "WAIT_RESULT"):
        codes.add("UNTRUSTED_WAIT_OR_ECHILD_CLAIM_NOT_REAP")
    return S.BLOCKED, codes, refs


def _evidence_usable(events, trust):
    codes, refs, _ledger = _smoke_common(events, trust)
    state, scodes, srefs = _seal_outcome(events, trust)
    codes |= scodes
    refs |= srefs
    if state == "MISMATCH":
        codes.add("LOG_SEAL_MISMATCH_DOWNSTREAM_UNUSABLE")
    elif state == "MATCH":
        codes.add("INTEGRITY_MATCH_ONLY_NO_AUTHENTICITY_BASIS")          # OQ-5: V0.1 defines no PASS condition for usability
    else:
        codes.add("SEAL_COMPARISON_UNAVAILABLE")
    return S.BLOCKED, codes, refs


def _delivery(events, trust):
    codes, refs, _ledger = _smoke_common(events, trust)
    codes.add("NO_TRUSTED_RECIPIENT_RECEIPT_SOURCE_IN_V0_1")
    for w in _auth(events, trust, S.ROLE_G2_WRAP, "R_WRITE_RESULT"):
        codes.add("WRITE_RESULT_IS_NOT_RECIPIENT_PROOF")
        refs.add(w.ref)
    if _claims(events, trust, "R_WRITTEN") or _claims(events, trust, "READY"):
        codes.add("UNTRUSTED_NODE_CLAIM_NOT_EVIDENCE")
    return S.BLOCKED, codes, refs


_HANDLERS = {
    "ATTRIBUTION": _attribution,
    "UNIQUE_REGISTRY": _unique_registry,
    "ZOMBIE_AT_T": _zombie_at_t,
    "LOG_MATCHES_SEAL": _log_matches_seal,
    "WRITE_COMPLETE": _write_complete,
    "PREVENT_PROOF": _prevent_proof,
    "LAWFUL_REAP": _lawful_reap,
    "EVIDENCE_USABLE": _evidence_usable,
    "DELIVERY": _delivery,
}


# ---------------------------------------------------------------- the only public entry point
def evaluate(assertion_id, subject_observables, declared_trust_model):
    """-> dict with subject_verdict PASS | FAIL | BLOCKED, evidence_basis_codes, supporting_observable_refs, accepted_claim (PASS only), coverage and
    the mandatory scope labels.  The subject verdict is about the synthetic evidence, not about native B0 safety."""
    try:
        events, trust = S.validate_input(assertion_id, subject_observables, declared_trust_model)
    except S.InputInvalid as exc:
        return _result(assertion_id, S.BLOCKED, ["INPUT_INVALID"], [], exc.problems)
    verdict, codes, refs = _HANDLERS[assertion_id](events, trust)
    return _result(assertion_id, verdict, codes, refs)
