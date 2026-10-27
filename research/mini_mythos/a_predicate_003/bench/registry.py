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
