"""REG: append-only registration file of the GATED-SPAWN protocol (INTENT / REGISTERED / RELEASED / ABORTED / DEAD / RUN_*).
Written by the observer only.  Parsing ignores a torn (newline-less) last line, so a crash mid-write is harmless.
WRITTEN, NOT RUN."""
import json
import os

import common as C

KINDS = ("RUN_START", "INTENT", "FORKED", "REGISTERED", "RELEASED", "ABORTED", "DEAD", "RUN_END")


class RegWriter:
    def __init__(self, path):
        self.path = path
        self.seq = 0
        self.records = []                       # in-memory copy (per-trial checks); the file is what the janitor reads
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    def write(self, kind, **fields):
        if kind not in KINDS:
            raise ValueError(kind)
        self.seq += 1
        rec = {"seq": self.seq, "kind": kind, "mono": C.mono(), "wall": C.wall()}
        rec.update(fields)
        C.append_jsonl(self.path, rec)
        self.records.append(rec)
        return rec


def parse_reg(path):
    """-> (records, info).  A final line without a newline is a torn write and is dropped (info['torn_tail']=True).
    Any other undecodable line, any line that is not a JSON object with a known `kind` and an integer `seq`, is dropped and counted
    in info['corrupt_lines'].  A file that cannot be read at all is reported as missing + unreadable.  NOTHING is guessed here: the
    caller (janitor, observer) must treat every irregularity as an integrity problem, see integrity_issues()."""
    try:
        with open(path, "rb") as f:
            data = f.read()
    except FileNotFoundError:
        return [], {"torn_tail": False, "corrupt_lines": 0, "missing": True, "unreadable": False}
    except OSError:
        return [], {"torn_tail": False, "corrupt_lines": 0, "missing": True, "unreadable": True}
    lines = data.split(b"\n")
    torn = lines[-1] != b""
    complete = lines[:-1]                    # lines[-1] is either b"" (clean end) or a torn tail
    recs, corrupt = [], 0
    for ln in complete:
        if not ln:
            continue
        try:
            obj = json.loads(ln.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            corrupt += 1
            continue
        if not isinstance(obj, dict) or obj.get("kind") not in KINDS or not isinstance(obj.get("seq"), int) or isinstance(obj.get("seq"), bool):
            corrupt += 1
            continue
        recs.append(obj)
    return recs, {"torn_tail": torn, "corrupt_lines": corrupt, "missing": False, "unreadable": False}


def integrity_issues(records):
    """Record-level integrity of what WAS parsed (strings; empty = nothing found).  Detects what parse_reg cannot see:
    lost records (sequence gaps), records of a node whose INTENT is missing, and critical records with unusable fields -- all of
    which would otherwise make a node silently invisible to the cleanup rules."""
    issues = []
    for i, r in enumerate(records):
        if r["seq"] != i + 1:
            issues.append("SEQ_GAP_OR_REORDER at index %d: seq %r (a record was lost, duplicated or reordered)" % (i, r["seq"]))
            break
    for nid, n in fold(records).items():
        if n["intent"] is None:
            issues.append("ORPHAN_RECORD: node %s has records but no INTENT" % nid)
        fk, reg = n["forked"], n["registered"]
        if fk is not None and not isinstance(fk.get("pid"), int):
            issues.append("MALFORMED_FORKED: node %s has a non-integer pid" % nid)
        if reg is not None and (not isinstance(reg.get("pid"), int) or not isinstance(reg.get("starttime"), int)):
            issues.append("MALFORMED_REGISTERED: node %s lacks integer pid/starttime" % nid)
    issues += ["ORDER: " + x for x in check_order(records)]
    issues += lifecycle_issues(records)
    return issues


def lifecycle_issues(records):
    """CLOSEOUT-02.  The minimal run lifecycle a registration file must show before anything may be concluded from it:
      * exactly one RUN_START, first in the file, carrying a run_id (str) and the observer_pid (int);
      * at most one RUN_END; if present it follows RUN_START, names the same run_id, has a boolean cleanup_confirmed and is the LAST
        record (nothing -- in particular no creation record -- may follow it);
      * a RUN_END that claims confirmed cleanup is only legal if every node except the janitor has a DEAD record;
      * no node record before RUN_START, no duplicate INTENT / DEAD, no record for a node after its DEAD.
    A file that is only a RUN_END, only fragments, or an order that could fake a successful end is therefore never accepted."""
    issues = []
    if not records:
        return ["EMPTY_REGISTRY: no RUN_START"]
    starts = [i for i, r in enumerate(records) if r["kind"] == "RUN_START"]
    ends = [i for i, r in enumerate(records) if r["kind"] == "RUN_END"]
    sid = None
    if len(starts) != 1:
        issues.append("RUN_START_COUNT=%d (exactly one is required)" % len(starts))
    else:
        s = records[starts[0]]
        if starts[0] != 0:
            issues.append("RUN_START_NOT_FIRST: %d record(s) precede it" % starts[0])
        if not (isinstance(s.get("run_id"), str) and s["run_id"]) or not isinstance(s.get("observer_pid"), int) or isinstance(s.get("observer_pid"), bool):
            issues.append("RUN_START_ILLEGAL: needs run_id (non-empty str) and observer_pid (int)")
        else:
            sid = s["run_id"]
    if len(ends) > 1:
        issues.append("DUPLICATE_RUN_END (%d)" % len(ends))
    if ends:
        e = records[ends[0]]
        if not starts:
            issues.append("RUN_END_WITHOUT_RUN_START")
        elif ends[0] < starts[0]:
            issues.append("RUN_END_BEFORE_RUN_START")
        elif sid is not None and e.get("run_id") != sid:
            issues.append("RUN_END_FOR_DIFFERENT_RUN: %r != %r" % (e.get("run_id"), sid))
        if not isinstance(e.get("cleanup_confirmed"), bool):
            issues.append("RUN_END_ILLEGAL: cleanup_confirmed must be a bool")
        if ends[0] != len(records) - 1:
            issues.append("RECORD_AFTER_RUN_END: %s" % [r["kind"] for r in records[ends[0] + 1:]][:6])
        if e.get("cleanup_confirmed") is True:
            nodes = fold(records)
            open_ = sorted(nid for nid, n in nodes.items()
                           if n["intent"] is not None and n["intent"].get("role") != "janitor" and n["dead"] is None)
            if open_:
                issues.append("CONFIRMED_RUN_END_WITH_UNFINISHED_NODES: %s" % open_[:6])
    first = starts[0] if starts else None
    seen_intent, dead = set(), set()
    for i, r in enumerate(records):
        nid = r.get("node_id")
        if nid is None:
            continue
        if first is not None and i < first:
            issues.append("NODE_RECORD_BEFORE_RUN_START: %s" % nid)
        if r["kind"] == "INTENT":
            if nid in seen_intent:
                issues.append("DUPLICATE_INTENT: %s" % nid)
            seen_intent.add(nid)
        if nid in dead:
            issues.append("RECORD_AFTER_DEAD: %s %s" % (nid, r["kind"]))
        if r["kind"] == "DEAD":
            dead.add(nid)
    return issues


def fold(records):
    """node_id -> merged view {intent, forked, registered, released, aborted, dead} (the record dicts or None)."""
    nodes = {}
    for r in records:
        nid = r.get("node_id")
        if nid is None:
            continue
        n = nodes.setdefault(nid, {"intent": None, "forked": None, "registered": None, "released": None, "aborted": None, "dead": None})
        k = r["kind"]
        if k == "INTENT":
            n["intent"] = r
        elif k == "FORKED":
            n["forked"] = r
        elif k == "REGISTERED":
            n["registered"] = r
        elif k == "RELEASED":
            n["released"] = r
        elif k == "ABORTED":
            n["aborted"] = r
        elif k == "DEAD":
            n["dead"] = r
    return nodes


def cleanup_targets(records):
    """Janitor rule: act only on nodes that have an INTENT AND a complete REGISTERED record with pid+starttime and that are
    not marked DEAD.  ABORTED does NOT end the responsibility: an aborted node whose process has not been confirmed dead
    (no DEAD record) is still a target.  INTENT-only nodes never produced a known process (it is gated and ends by itself)."""
    out = []
    for nid, n in fold(records).items():
        reg = n["registered"]
        if n["intent"] is None or reg is None or n["dead"] is not None:
            continue
        if not isinstance(reg.get("pid"), int) or not isinstance(reg.get("starttime"), int):
            continue
        out.append({"node_id": nid, "pid": reg["pid"], "starttime": reg["starttime"], "role": reg.get("role")})
    return sorted(out, key=lambda t: t["node_id"])


def unresolved_forked(records):
    """Nodes whose process is known (a FORKED record with a pid) but was never identity-registered and never confirmed dead.
    The janitor must NOT signal them (identity unverified) but must keep reporting them until they are confirmed gone."""
    out = []
    for nid, n in fold(records).items():
        fk = n["forked"]
        if n["intent"] is None or fk is None or n["registered"] is not None or n["dead"] is not None:
            continue
        if not isinstance(fk.get("pid"), int):
            continue
        out.append({"node_id": nid, "pid": fk["pid"], "starttime": fk.get("starttime"), "role": fk.get("role")})
    return sorted(out, key=lambda t: t["node_id"])


def unresolved_tickets(records):
    """CLOSEOUT-01.  Nodes created through a ticket (creator is not the observer) for which the REG file shows neither a known process
    (FORKED / REGISTERED) nor a DEAD record: the creator may have forked and CREATED may still arrive.  Only the observer can resolve
    them (it holds the gate and writes DEAD with its basis); the janitor can only report them -- no pid is guessed, nothing is signalled."""
    out = []
    for nid, n in fold(records).items():
        it = n["intent"]
        if it is None or it.get("creator") in (None, "O") or n["forked"] is not None or n["registered"] is not None or n["dead"] is not None:
            continue
        out.append({"node_id": nid, "creator": it.get("creator"), "label": it.get("label")})
    return sorted(out, key=lambda t: t["node_id"])


def last_run_end(records):
    """The last RUN_END record, or None."""
    ends = [r for r in records if r.get("kind") == "RUN_END"]
    return ends[-1] if ends else None


def check_order(records):
    """BV-4 / BV-5 (pure): every RELEASED follows its REGISTERED which follows its INTENT; a node's creator (other than the
    observer 'O') is itself REGISTERED before the child's INTENT.  Returns a list of violation strings (empty = ok)."""
    bad = []
    seqs = {}
    for r in records:
        nid = r.get("node_id")
        if nid is not None:
            seqs.setdefault(nid, {})[r["kind"]] = r["seq"]
    last = 0
    for r in records:
        if r["seq"] <= last:
            bad.append("non-monotonic seq at %r" % (r,))
        last = r["seq"]
    for nid, s in sorted(seqs.items()):
        if "RELEASED" in s and ("REGISTERED" not in s or s["REGISTERED"] > s["RELEASED"]):
            bad.append("%s: RELEASED without earlier REGISTERED" % nid)
        if "REGISTERED" in s and ("INTENT" not in s or s["INTENT"] > s["REGISTERED"]):
            bad.append("%s: REGISTERED without earlier INTENT" % nid)
        if "RELEASED" in s and "ABORTED" in s:
            bad.append("%s: both RELEASED and ABORTED" % nid)
        if "FORKED" in s and ("INTENT" not in s or s["INTENT"] > s["FORKED"]):
            bad.append("%s: FORKED without earlier INTENT" % nid)
    intents = {r["node_id"]: r for r in records if r["kind"] == "INTENT"}
    for nid, r in intents.items():
        cr = r.get("creator")
        if cr not in (None, "O"):
            if cr not in seqs or "REGISTERED" not in seqs[cr] or seqs[cr]["REGISTERED"] > r["seq"]:
                bad.append("%s: creator %s not registered before child INTENT" % (nid, cr))
    return bad
