"""REG: append-only registration file of the GATED-SPAWN protocol (INTENT / REGISTERED / RELEASED / ABORTED / DEAD / RUN_*).
Written by the observer only.  Parsing ignores a torn (newline-less) last line, so a crash mid-write is harmless.
WRITTEN, NOT RUN."""
import json
import os

import common as C

KINDS = ("RUN_START", "INTENT", "REGISTERED", "RELEASED", "ABORTED", "DEAD", "RUN_END")


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
    Any other undecodable line is dropped and counted in info['corrupt_lines'] (the janitor then refuses to guess)."""
    try:
        with open(path, "rb") as f:
            data = f.read()
    except FileNotFoundError:
        return [], {"torn_tail": False, "corrupt_lines": 0, "missing": True}
    lines = data.split(b"\n")
    torn = lines[-1] != b""
    complete = lines[:-1]                    # lines[-1] is either b"" (clean end) or a torn tail
    recs, corrupt = [], 0
    for ln in complete:
        if not ln:
            continue
        try:
            recs.append(json.loads(ln.decode("utf-8")))
        except (ValueError, UnicodeDecodeError):
            corrupt += 1
    return recs, {"torn_tail": torn, "corrupt_lines": corrupt, "missing": False}


def fold(records):
    """node_id -> merged view {intent, registered, released, aborted, dead} (the record dicts or None)."""
    nodes = {}
    for r in records:
        nid = r.get("node_id")
        if nid is None:
            continue
        n = nodes.setdefault(nid, {"intent": None, "registered": None, "released": None, "aborted": None, "dead": None})
        k = r["kind"]
        if k == "INTENT":
            n["intent"] = r
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
    neither ABORTED nor marked DEAD.  INTENT-only nodes were never registered: their process is gated and ends by itself."""
    out = []
    for nid, n in fold(records).items():
        reg = n["registered"]
        if n["intent"] is None or reg is None or n["aborted"] is not None or n["dead"] is not None:
            continue
        if not isinstance(reg.get("pid"), int) or not isinstance(reg.get("starttime"), int):
            continue
        out.append({"node_id": nid, "pid": reg["pid"], "starttime": reg["starttime"], "role": reg.get("role")})
    return sorted(out, key=lambda t: t["node_id"])


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
    intents = {r["node_id"]: r for r in records if r["kind"] == "INTENT"}
    for nid, r in intents.items():
        cr = r.get("creator")
        if cr not in (None, "O"):
            if cr not in seqs or "REGISTERED" not in seqs[cr] or seqs[cr]["REGISTERED"] > r["seq"]:
                bad.append("%s: creator %s not registered before child INTENT" % (nid, cr))
    return bad
