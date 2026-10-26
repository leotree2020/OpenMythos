#!/usr/bin/env python3
"""D1 independent verifier.

Status: FROZEN CANDIDATE, pending ChatGPT code review. Nothing here has been run
on real data.

Independence rule: this file must not import, and must not share any function
with, d1_reader.py. It rebuilds the reference stream, the source-row mapping and
the nine cursor checks from the config, the parquet/jsonl source and the
tokenizer on its own, and it never trusts reader state: every claim in a trace
(ids, segments, hashes) is re-derived or re-checked.

Sub-commands: config-hash | schedule | check-cursor | verify-clean | verify-lr |
verify-cr | evidence-hashes. Outputs are write-once. Exit codes: 0 PASS,
1 FAIL, 4 BLOCKED.
"""
import argparse
import bisect
import hashlib
import itertools
import json
import os
import re
import struct
import sys
import unicodedata

VERIFIER_VERSION = "d1_verifier/1"
H64 = re.compile(r"^[0-9a-f]{64}$")
H40 = re.compile(r"^[0-9a-f]{40}$")


class Blocked(Exception):
    pass


# ------------------------------------------------------------------ utilities
def sha(b):
    return hashlib.sha256(b).hexdigest()


def pack(ids):
    return b"".join(struct.pack("<I", i) for i in ids)


def cj(o):
    return json.dumps(o, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def fsha(p):
    with open(p, "rb") as fh:
        return sha(fh.read())


def rb(p):
    with open(p, "rb") as fh:
        return fh.read()


def jload(p):
    with open(p, "rb") as fh:
        raw = fh.read()
    return json.loads(raw.decode("utf-8")), sha(raw)


def put(p, text):
    os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
    with open(p, "x", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def flat(o, pre=""):
    """Flatten JSON to {path: leaf}; lists as path[i]."""
    out = {}
    if isinstance(o, dict):
        for k in o:
            out.update(flat(o[k], pre + ("." if pre else "") + k))
    elif isinstance(o, list):
        if not o:
            out[pre + "[]"] = []
        for i, v in enumerate(o):
            out.update(flat(v, "%s[%d]" % (pre, i)))
    else:
        out[pre] = o
    return out


# ------------------------------------------------------------------ reference
class Row:
    __slots__ = ("phys", "text_sha", "ids", "ids_sha")


class Ref:
    """Independent reference: eligible rows -> tokens(r) -> flat stream -> blocks."""

    def __init__(self, cfg, manifest, texts, enc, vocab):
        self.cfg, self.vocab = cfg, vocab
        W = cfg["window"]["window_rows"]
        head = re.compile(cfg["rows"]["level1_heading_regex"])
        eos = cfg["tokenizer"]["special_tokens"]["eos"][1]
        specials = [v[0] for v in cfg["tokenizer"]["special_tokens"].values()]
        self.rows, self.headings = [], 0
        for phys, t in enumerate(texts):
            if not isinstance(t, str):
                raise Blocked("NON_STRING_TEXT:%d" % phys)
            if not t.strip():
                continue
            nfc = unicodedata.normalize("NFC", t)
            if any(s in nfc for s in specials):
                raise Blocked("SPECIAL_LITERAL:%d" % phys)
            is_head = bool(head.match(nfc))
            self.headings += is_head
            ids = ([eos] if is_head and self.rows else []) + list(enc(nfc))
            if not ids:
                raise Blocked("EMPTY_TOKENS:%d" % phys)
            if min(ids) < 1 or max(ids) >= vocab:
                raise Blocked("ID_RANGE_OR_PAD:%d" % phys)
            r = Row()
            r.phys, r.text_sha, r.ids, r.ids_sha = phys, sha(nfc.encode("utf-8")), ids, sha(pack(ids))
            self.rows.append(r)
            if len(self.rows) == W:
                break
        if len(self.rows) < W:
            raise Blocked("WINDOW_TOO_SMALL:%d" % len(self.rows))
        self.W = W
        self.cum = [0] + list(itertools.accumulate(len(r.ids) for r in self.rows))
        self.T = self.cum[-1]
        self.stream = list(itertools.chain.from_iterable(r.ids for r in self.rows))
        self.N = self.T // 65
        self.bdig = [hashlib.sha256(pack(self.stream[j * 65:(j + 1) * 65])).digest() for j in range(self.N)]
        h = hashlib.sha256(b"MINI-MYTHOS-D1-CHAIN-V1").digest()
        self.chain = [h]
        for j in range(self.N):
            h = hashlib.sha256(h + self.bdig[j]).digest()
            self.chain.append(h)

    def locate(self, pos):
        """(ordinal, offset) of stream position pos < T; row end maps to the next row, offset 0."""
        r = bisect.bisect_right(self.cum, pos) - 1
        return r, pos - self.cum[r]

    def decompose(self, a, b):
        """Row pieces (ordinal, offset, count) covering stream positions [a, b)."""
        out = []
        while a < b:
            r, o = self.locate(a)
            n = min(b - a, len(self.rows[r].ids) - o)
            out.append((r, o, n))
            a += n
        return out

    def cursor_bytes(self, manifest, pos):
        """The cursor a correct reader must have written at stream position pos."""
        e = pos // 65
        d = self.cfg["dataset"]
        c = {"schema": "d1_cursor_v2",
             "dataset": {"repo_id": d["repo_id"], "config": d["config"], "revision": d["revision"],
                         "split": d["split"], "parquet_sha256": manifest["parquet_sha256"]},
             "tokenizer_sha256": manifest["tokenizer_sha256"], "window_rows": self.W,
             "seq_len": self.cfg["window"]["seq_len"], "block_len": self.cfg["window"]["block_len"],
             "carry": self.stream[e * 65:pos], "emitted_blocks": e, "stream_token_pos": pos,
             "chain_hash": self.chain[e].hex(), "last_block_hash": self.bdig[e - 1].hex() if e else None,
             "rng": None}
        if pos == self.T:
            c.update(eof=True, next_eligible_row=self.W, row_token_offset=0, source_row_index=None,
                     row_text_sha256=None, row_tokens_sha256=None)
        else:
            r, o = self.locate(pos)
            c.update(eof=False, next_eligible_row=r, row_token_offset=o, source_row_index=self.rows[r].phys,
                     row_text_sha256=self.rows[r].text_sha, row_tokens_sha256=self.rows[r].ids_sha)
        return cj(c).encode("utf-8")


def build_ref(a):
    cfg, _ = jload(a.config)
    manifest, _ = jload(a.manifest)
    kind, _, path = a.source.partition(":")
    if kind != ("parquet" if a.mode == "real" else "jsonl"):
        raise Blocked("MODE_SOURCE_KIND")
    texts = []
    if kind == "parquet":
        import pyarrow.parquet as pq
        texts = pq.read_table(path, columns=["text"]).column("text").to_pylist()
    elif kind == "jsonl":
        with open(path, encoding="utf-8") as fh:
            texts = [json.loads(line)["text"] for line in fh]
    else:
        raise Blocked("SOURCE_KIND")
    tsha = fsha(a.tokenizer)
    if a.mode == "selftest":
        with open(a.tokenizer, "rb") as fh:
            if fh.read().strip() != b"TOY-BYTE-ENCODER-V1":
                raise Blocked("SELFTEST_TOKENIZER")
        enc, vocab = (lambda s: [3 + b for b in s.encode("utf-8")]), 259
    else:
        from tokenizers import Tokenizer
        tk = Tokenizer.from_file(a.tokenizer)
        if tsha != manifest["tokenizer_sha256"]:
            raise Blocked("TOKENIZER_FILE_SHA")
        if tk.post_processor is not None or tk.padding is not None or tk.truncation is not None:
            raise Blocked("TOKENIZER_AUTO_BEHAVIOUR")
        for lit, tid in cfg["tokenizer"]["special_tokens"].values():
            if tk.token_to_id(lit) != tid:
                raise Blocked("SPECIAL_ID")
        vocab = tk.get_vocab_size()
        if vocab != manifest["actual_vocab_size"]:
            raise Blocked("VOCAB")
        enc = lambda s: tk.encode(s, is_pretokenized=False, add_special_tokens=False).ids  # noqa: E731
    if tsha != manifest["tokenizer_sha256"]:
        raise Blocked("MANIFEST_TOKENIZER_SHA")
    return cfg, manifest, Ref(cfg, manifest, texts, enc, vocab), path


# ------------------------------------------------------------------ cursor check (independent)
def check_cursor(ref, manifest, raw):
    """-> (code, step); code None means all nine checks pass."""
    cfg = ref.cfg
    try:
        c = json.loads(raw.decode("utf-8"))
        keys = {"schema", "dataset", "tokenizer_sha256", "window_rows", "seq_len", "block_len",
                "next_eligible_row", "source_row_index", "row_text_sha256", "row_tokens_sha256",
                "row_token_offset", "carry", "emitted_blocks", "stream_token_pos", "chain_hash",
                "last_block_hash", "eof", "rng"}
        ok = isinstance(c, dict) and set(c) == keys and c["schema"] == "d1_cursor_v2"
        ok = ok and isinstance(c["dataset"], dict) and set(c["dataset"]) == {"repo_id", "config", "revision", "split", "parquet_sha256"}
        ok = ok and all(isinstance(c["dataset"][k], str) for k in c["dataset"])
        isint = lambda v: type(v) is int  # noqa: E731
        ok = ok and all(isint(c[k]) for k in ("window_rows", "seq_len", "block_len", "next_eligible_row",
                                              "row_token_offset", "emitted_blocks", "stream_token_pos"))
        ok = ok and type(c["eof"]) is bool and c["rng"] is None
        ok = ok and isinstance(c["carry"], list) and all(isint(v) for v in c["carry"])
        ok = ok and (c["source_row_index"] is None or isint(c["source_row_index"]))
        hx = lambda v, none: (v is None and none) or (isinstance(v, str) and bool(H64.match(v)))  # noqa: E731
        ok = ok and hx(c["tokenizer_sha256"], False) and hx(c["chain_hash"], False) and hx(c["last_block_hash"], True)
        ok = ok and hx(c["row_text_sha256"], True) and hx(c["row_tokens_sha256"], True)
        ok = ok and cj(c).encode("utf-8") == raw
    except Exception:  # noqa: BLE001
        ok = False
    if not ok:
        return "SCHEMA_INVALID", 1
    d, dc = c["dataset"], cfg["dataset"]
    if (d["repo_id"], d["config"], d["split"]) != (dc["repo_id"], dc["config"], dc["split"]):
        return "DATASET_IDENTITY_MISMATCH", 2
    if not H40.match(d["revision"]) or d["revision"] != dc["revision"]:
        return "REVISION_MISMATCH", 2
    if d["parquet_sha256"] != manifest["parquet_sha256"]:
        return "PARQUET_HASH_MISMATCH", 2
    if c["tokenizer_sha256"] != manifest["tokenizer_sha256"]:
        return "TOKENIZER_HASH_MISMATCH", 3
    w = cfg["window"]
    if (c["window_rows"], c["seq_len"], c["block_len"]) != (w["window_rows"], w["seq_len"], w["block_len"]):
        return "WINDOW_PARAMS_MISMATCH", 4
    n, o, e, p, carry = c["next_eligible_row"], c["row_token_offset"], c["emitted_blocks"], c["stream_token_pos"], c["carry"]
    if n < 0 or n > ref.W:
        return "ROW_OUT_OF_RANGE", 5
    if c["eof"]:
        if n != ref.W or o != 0 or c["source_row_index"] is not None or c["row_text_sha256"] is not None or c["row_tokens_sha256"] is not None:
            return "EOF_INCONSISTENT", 5
    else:
        if n == ref.W:
            return "EOF_INCONSISTENT", 5
        if o < 0 or o > len(ref.rows[n].ids) - 1:
            return "OFFSET_OUT_OF_RANGE", 5
        row = ref.rows[n]
        if c["source_row_index"] != row.phys or c["row_text_sha256"] != row.text_sha or c["row_tokens_sha256"] != row.ids_sha:
            return "ROW_IDENTITY_MISMATCH", 6
    if p != ref.cum[n] + o or p != 65 * e + len(carry):
        return "CURSOR_POSITION_MISMATCH", 7
    if len(carry) > 64:
        return "CARRY_LENGTH_INVALID", 8
    if any(v < 1 or v >= ref.vocab for v in carry):
        return "TOKEN_ID_INVALID", 8
    if carry != ref.stream[65 * e:p]:
        return "CARRY_TOKEN_MISMATCH", 8
    if e > ref.N or c["chain_hash"] != ref.chain[e].hex():
        return "CHAIN_HASH_MISMATCH", 9
    if c["last_block_hash"] != (ref.bdig[e - 1].hex() if e else None):
        return "LAST_BLOCK_HASH_MISMATCH", 9
    return None, 9


# ------------------------------------------------------------------ segment tiling (independent)
def tile_errors(segs, ref, start, end):
    """Row-piece list (ordinal, offset, count) must cover stream positions [start, end)
    exactly: no gap, no overlap, nothing uncovered. Returns a list of error strings."""
    errs, pos = [], start
    for (r, o, n) in segs:
        if n < 1 or not 0 <= r < ref.W or o < 0 or o + n > len(ref.rows[r].ids):
            errs.append("SEGMENT_INVALID %s" % ((r, o, n),))
            break
        a = ref.cum[r] + o
        if a > pos:
            errs.append("SEGMENT_GAP at stream pos %d" % pos)
            break
        if a < pos:
            errs.append("SEGMENT_OVERLAP at stream pos %d" % pos)
            break
        pos += n
    if not errs and pos != end:
        errs.append("SEGMENT_UNCOVERED: covered up to %d, expected %d" % (pos, end))
    return errs


# ------------------------------------------------------------------ traces
def load_trace(path):
    recs = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            recs.append(json.loads(line))
    if len(recs) < 2 or recs[0].get("type") != "run" or recs[-1].get("type") != "final":
        raise ValueError("trace structure: %s" % path)
    blocks = recs[1:-1]
    if any(b.get("type") != "block" for b in blocks):
        raise ValueError("trace has non-block records in the middle")
    return recs[0], blocks, recs[-1]


def segs_of(lst):
    return [(s["ordinal"], s["row_offset"], s["count"]) for s in lst]


def claim_errors(ref, ids, seglist, first_new):
    """Verify a reader's segment claims against content (not against position):
    mapping, slice content, and that the claims tile ids[first_new:] exactly."""
    errs, ptr = [], first_new
    for s in seglist:
        r, o, n = s["ordinal"], s["row_offset"], s["count"]
        if not (isinstance(r, int) and 0 <= r < ref.W) or ref.rows[r].phys != s["source_row_index"]:
            return ["CLAIM_ROW_MAPPING %s" % (s,)]
        if n < 1 or o < 0 or o + n > len(ref.rows[r].ids):
            return ["CLAIM_RANGE %s" % (s,)]
        if ids[ptr:ptr + n] != ref.rows[r].ids[o:o + n]:
            return ["CLAIM_CONTENT %s" % (s,)]
        ptr += n
    if ptr != len(ids):
        errs.append("CLAIM_COVERAGE: claims end at %d of %d" % (ptr, len(ids)))
    return errs


class Check:
    def __init__(self):
        self.items, self.blocked = [], []

    def __call__(self, name, ok, detail=""):
        self.items.append({"check": name, "status": "PASS" if ok else "FAIL", "detail": detail})
        return ok

    def block(self, name, detail):
        self.blocked.append({"check": name, "status": "BLOCKED", "detail": detail})

    def verdict(self):
        if self.blocked:
            return "BLOCKED"
        return "PASS" if all(i["status"] == "PASS" for i in self.items) else "FAIL"

    def result(self, extra):
        return dict(extra, verdict=self.verdict(), checks=self.items + self.blocked)


def fallback_result(a, verdict, why):
    """Best effort: leave a result file behind when the verifier cannot finish normally."""
    out = getattr(a, "out", None)
    if out and not os.path.exists(out):
        try:
            put(out, cj({"verdict": verdict, "reason": why[:500], "checks": [], "verifier": VERIFIER_VERSION}))
        except Exception:  # noqa: BLE001
            pass


def emit(out, res):
    if out:
        put(out, cj(res))
    print(json.dumps({"verdict": res["verdict"]}))
    return {"PASS": 0, "FAIL": 1, "BLOCKED": 4}[res["verdict"]]


# ------------------------------------------------------------------ schedule
def build_schedule(ref, cfg):
    ck = Check()
    w, s = cfg["window"], cfg["schedule"]
    ck("precondition level-1 headings >= %d" % w["min_level1_headings"], ref.headings >= w["min_level1_headings"], str(ref.headings))
    ck("precondition blocks >= %d" % w["min_blocks"], ref.N >= w["min_blocks"], str(ref.N))
    pts = {}
    p1 = s["p1"]["row"]
    pts["P1"] = ref.cum[p1]
    lo, hi = s["p2"]["search_ordinals"]
    p2row = next((k for k in range(lo, hi) if len(ref.rows[k].ids) >= s["p2"]["min_row_len"]), None)
    if p2row is None:
        ck("P2 row with len>=%d in [%d,%d)" % (s["p2"]["min_row_len"], lo, hi), False, "none found")
    else:
        pts["P2"] = ref.cum[p2row] + len(ref.rows[p2row].ids) // 2
    for name in ("P3", "P4"):
        base = ref.cum[s[name.lower()]["search_from_row_start"]]
        m, r = s[name.lower()]["stream_pos_mod"]
        pts[name] = base + ((r - base) % m)
    pts["P5"] = ref.T
    ordered = [pts.get(k) for k in ("P1", "P2", "P3", "P4", "P5")]
    if None not in ordered:
        ck("stream positions strictly increasing", all(a < b for a, b in zip(ordered, ordered[1:])), str(ordered))
    out = {}
    for k, pos in pts.items():
        e = {"stream_pos": pos, "carry_len": pos - 65 * (pos // 65), "eof": pos == ref.T}
        if pos < ref.T:
            r, o = ref.locate(pos)
            e.update(ordinal=r, offset=o, row_len=len(ref.rows[r].ids))
        out[k] = e
    if "P1" in out:
        ck("K1 row boundary, not EOF", out["P1"].get("offset") == 0 and not out["P1"]["eof"])
    if "P2" in out:
        ck("K2 inside a row, row_len>=3", 0 < out["P2"].get("offset", 0) < out["P2"].get("row_len", 0) and out["P2"]["row_len"] >= 3)
    if "P3" in out:
        ck("K3 carry_len == 32 (non-empty)", out["P3"]["carry_len"] == 32)
    if "P4" in out:
        ck("K4 carry_len == 0 (empty, legal)", out["P4"]["carry_len"] == 0)
    ck("K5 EOF", out["P5"]["eof"])
    info = {"T": ref.T, "N": ref.N, "tail_len": ref.T % 65, "level1_headings": ref.headings,
            "vocab": ref.vocab, "points": out}
    res = ck.result(info)
    if res["verdict"] == "FAIL":
        res["verdict"] = "BLOCKED"        # a schedule failure is BLOCKED(schedule), never repaired
        res["reason"] = "BLOCKED(schedule)"
    return res


# ------------------------------------------------------------------ verify-clean
def run_checks(ref, ck, label, tr, strict_positions=True):
    """Check one reader run against the reference. Returns the run's recorded row pieces."""
    run, blocks, fin = tr
    c, s0 = run["carry_len"], run["start_stream_pos"]
    e0 = (s0 - c) // 65 if run["start_cursor_sha256"] is not None else 0
    recorded, ok = [], True
    for k, b in enumerate(blocks):
        j = e0 + k
        a, z = 65 * j, 65 * j + 65
        good = (b["block_index"] == j and j < ref.N and b["ids"] == ref.stream[a:z]
                and sha(pack(b["ids"])) == b["block_hash"] == ref.bdig[j].hex())
        first_new = max(0, s0 - a) if run["start_cursor_sha256"] is not None else 0
        want = [(r, o, n) for (r, o, n) in ref.decompose(max(a, s0 if run["start_cursor_sha256"] else 0), z)]
        good = good and segs_of(b["segments"]) == want and not claim_errors(ref, b["ids"], b["segments"], first_new)
        if not good:
            ck("%s block %d content/hash/segments" % (label, j), False)
            ok = False
            break
        recorded += want
    if ok:
        ck("%s %d blocks match reference (ids, hash, segments)" % (label, len(blocks)), True)
    nb = e0 + len(blocks)
    if fin["kind"] == "eof_tail":
        tl, ids, sg = fin["tail_len"], fin["tail_ids"], fin["tail_segments"]
        ck("%s EOF tail is stream[65N:T]" % label, ids == ref.stream[65 * ref.N:] and tl == len(ids) == ref.T % 65
           and fin["tail_sha256"] == sha(pack(ids)) and nb == ref.N)
        st = 65 * nb
        want = ref.decompose(max(st, s0 if run["start_cursor_sha256"] else 0), ref.T)
        ck("%s tail segments match" % label, segs_of(sg) == want and not claim_errors(ref, ids, sg, max(0, (s0 if run["start_cursor_sha256"] else 0) - st)))
        recorded += want
        ck("%s chain_hash == H_N" % label, fin["chain_hash"] == ref.chain[ref.N].hex() and fin["blocks_total"] == ref.N)
    elif fin["kind"] == "carry":
        ids, sg, p = fin["carry_ids"], fin["carry_segments"], fin["stream_token_pos"]
        st = 65 * nb
        ck("%s interrupted-run carry is stream[65e:pos], not a tail" % label,
           ids == ref.stream[st:p] and fin["carry_len"] == len(ids) < 65 and "tail_len" not in fin and p < ref.T)
        want = ref.decompose(max(st, s0 if run["start_cursor_sha256"] else 0), p)
        ck("%s carry segments match" % label, segs_of(sg) == want and not claim_errors(ref, ids, sg, max(0, (s0 if run["start_cursor_sha256"] else 0) - st)))
        recorded += want
        ck("%s chain_hash == H_e" % label, fin["chain_hash"] == ref.chain[nb].hex() and fin["blocks_total"] == nb)
    else:
        ck("%s final kind" % label, False, fin.get("kind"))
    return recorded


def verify_clean(a):
    cfg, manifest, ref, src_path = build_ref(a)
    ck = Check()
    cd = a.clean_dir
    sched, _ = jload(os.path.join(cd, "schedule.json"))
    # The schedule is recomputed here from the frozen rules; the stored file is only compared to it.
    fresh = build_schedule(ref, cfg)
    if fresh["verdict"] != "PASS":
        ck.block("schedule", "BLOCKED(schedule): recomputed schedule is not valid")
        return emit(a.out, ck.result({"verifier": VERIFIER_VERSION, "mode": a.mode}))
    keys = ("points", "T", "N", "tail_len", "level1_headings", "vocab")
    ck("schedule recomputed from the frozen rules equals the stored schedule (all points, all fields)",
       all(fresh[k] == sched.get(k) for k in keys),
       "; ".join(k for k in keys if fresh[k] != sched.get(k)))
    pts = fresh["points"]
    for nm, rule in (("P1", lambda p: p["stream_pos"] == ref.cum[cfg["schedule"]["p1"]["row"]]),
                     ("P5", lambda p: p["stream_pos"] == ref.T)):
        ck("schedule %s equals the frozen rule" % nm, rule(pts[nm]))
    A = load_trace(os.path.join(cd, "A_trace.jsonl"))
    rec_a = run_checks(ref, ck, "A", A)
    ck("A: segments tile the whole window (no gap, no overlap, full coverage)", not tile_errors(rec_a, ref, 0, ref.T),
       "; ".join(tile_errors(rec_a, ref, 0, ref.T)))
    # per-row coverage (R3)
    cons = [0] * ref.W
    for (r, o, n) in rec_a:
        cons[r] += n
    ck("R3 every eligible row consumed exactly len(tokens(r)) tokens (emitted + tail)",
       all(cons[i] == len(ref.rows[i].ids) for i in range(ref.W)))

    names = ["P1", "P2", "P3", "P4", "P5"]
    Bs, rec_b, pids = [], [], []
    for i in range(1, 7):
        t = load_trace(os.path.join(cd, "B_seg%d_trace.jsonl" % i))
        Bs.append(t)
        rec_b += run_checks(ref, ck, "B%d" % i, t)
        pids.append(t[0]["pid"])
        want_cursor = None if i == 1 else os.path.join(cd, "cursors", "%s.json" % names[i - 2])
        ck("B%d starts from the saved cursor file (hash)" % i,
           t[0]["start_cursor_sha256"] == (None if want_cursor is None else fsha(want_cursor)))
        if i <= 4:
            ck("B%d stop_pos == schedule %s" % (i, names[i - 1]), t[0]["stop_pos"] == pts[names[i - 1]]["stream_pos"])
        if i >= 2:
            lr, _ = jload(os.path.join(cd, "load_reports", "B_seg%d.json" % i))
            ck("B%d load report: nine steps PASS" % i, lr["result"] == "PASS" and [s["status"] for s in lr["steps"]] == ["PASS"] * 9)
    ck("B: six separate processes (distinct pids)", len(set(pids)) == 6)
    ck("B: segments tile the whole window across all 6 runs", not tile_errors(rec_b, ref, 0, ref.T),
       "; ".join(tile_errors(rec_b, ref, 0, ref.T)))
    # R1 / R2 equality of A, B, reference
    ck("R2 A and B final chain/tail agree", A[2]["chain_hash"] == Bs[5][2]["chain_hash"] == ref.chain[ref.N].hex()
       and A[2]["tail_sha256"] == Bs[5][2]["tail_sha256"])
    ck("B6 reads zero blocks and its tail is the restored carry", len(Bs[5][1]) == 0 and Bs[5][0]["carry_len"] == ref.T % 65)
    # R4 / R5 cursors
    prev = -1
    for i, nm in enumerate(names):
        raw = rb(os.path.join(cd, "cursors", "%s.json" % nm))
        code, step = check_cursor(ref, manifest, raw)
        ck("R4 %s passes the independent nine-step check" % nm, code is None, str(code))
        pos = pts[nm]["stream_pos"]
        ck("R4 %s bytes equal the cursor a correct reader writes at stream pos %d" % (nm, pos), raw == ref.cursor_bytes(manifest, pos))
        ck("R5 %s stream pos strictly above previous" % nm, pos > prev)
        prev = pos
    ck("R5 K3: P3 carry non-empty (32)", pts["P3"]["carry_len"] == 32)
    ck("R5 K4: P4 carry empty and accepted", pts["P4"]["carry_len"] == 0 and json.loads(rb(os.path.join(cd, "cursors", "P4.json")))["carry"] == [])
    ck("R5 K5: P5 is EOF with carry == tail", json.loads(rb(os.path.join(cd, "cursors", "P5.json")))["eof"] is True
       and json.loads(rb(os.path.join(cd, "cursors", "P5.json")))["carry"] == ref.stream[65 * ref.N:])
    ck("R6 (post-run part only) source file hash equals manifest", fsha(src_path) == manifest["parquet_sha256"])
    res = ck.result({"verifier": VERIFIER_VERSION, "mode": a.mode, "T": ref.T, "N": ref.N, "tail_len": ref.T % 65,
                     "scope": "R1-R5 and the post-run part of R6 only; this verdict is NOT a D1 verdict",
                     "not_tested": {"R6_pre_read_hash_and_split_isolation": "NOT TESTED",
                                    "R7_validation_test_handling": "NOT TESTED",
                                    "T1_to_T6_tokenizer_acceptance": "NOT TESTED",
                                    "data_acquisition_integrity_lfs_oid": "NOT TESTED"},
                     "R8": "see negatives result files"})
    return emit(a.out, res)


# ------------------------------------------------------------------ verify-lr
def verify_lr(a):
    cfg, manifest, ref, _ = build_ref(a)
    spec = cfg["negatives"]["LR"][a.id]
    ck = Check()
    orig, mut = rb(a.orig), rb(a.mutated)
    ck("(a) mutated file differs from original", sha(orig) != sha(mut))
    diff = sorted(k for k in set(flat(json.loads(orig))) | set(flat(json.loads(mut)))
                  if flat(json.loads(orig)).get(k, "<absent>") != flat(json.loads(mut)).get(k, "<absent>"))
    ck("(e) exactly one field differs and it is %s" % spec["field"], diff == [spec["field"]], str(diff))
    lr, _ = jload(a.load_report)
    ck("(b) reader rejected with %s at step %d" % (spec["code"], spec["step"]),
       lr["result"] == "REJECTED" and lr["code"] == spec["code"] and lr["failed_step"] == spec["step"], str((lr["code"], lr["failed_step"])))
    run, blocks, fin = load_trace(a.trace)
    ck("(c) zero blocks in the trace", len(blocks) == 0 and fin["kind"] == "rejected")
    code, step = check_cursor(ref, manifest, mut)
    ck("(d) independent check gives the same code/step", (code, step) == (spec["code"], spec["step"]), str((code, step)))
    ck("original cursor passes the independent check (control)", check_cursor(ref, manifest, orig)[0] is None)
    return emit(a.out, ck.result({"id": a.id, "expected": spec, "verifier": VERIFIER_VERSION}))


# ------------------------------------------------------------------ verify-cr
def account(ref, prefix_blocks, e, s, carry, tr):
    """Whole-window per-row accounting from prefix evidence + carry + continuation.
    Returns (per_row_pieces, errors)."""
    per = [[] for _ in range(ref.W)]
    errs = []
    for b in prefix_blocks:                                  # trusted-but-reverified prefix
        for sg in b["segments"]:
            per[sg["ordinal"]].append((sg["row_offset"], sg["count"], None))
    for (r, o, n) in ref.decompose(65 * e, s):                # carry provenance by independent mapping
        i0 = ref.cum[r] + o - 65 * e
        per[r].append((o, n, carry[i0:i0 + n]))
    run, blocks, fin = tr
    c = run["carry_len"]
    u = 0
    parts = [(b["ids"], b["segments"]) for b in blocks]
    parts.append((fin.get("tail_ids", fin.get("carry_ids", [])), fin.get("tail_segments", fin.get("carry_segments", []))))
    for ids, sgs in parts:
        first_new = max(0, c - u)
        ce = claim_errors(ref, ids, sgs, first_new)
        if ce:
            errs += ce
            break
        ptr = first_new
        for sg in sgs:
            per[sg["ordinal"]].append((sg["row_offset"], sg["count"], ids[ptr:ptr + sg["count"]]))
            ptr += sg["count"]
        u += len(ids)
    return per, errs


def classify(ref, per):
    out = []
    for r in range(ref.W):
        n = len(ref.rows[r].ids)
        used = sum(p[1] for p in per[r])
        if used == 0:
            cls = "ROW_SKIPPED"
        elif used > n:
            cls = "ROW_DUPLICATED"
        else:
            nxt, contiguous = 0, True
            for (o, cnt, _) in per[r]:
                contiguous = contiguous and o == nxt
                nxt += cnt
            ids = []
            for (o, cnt, got) in per[r]:
                ids += got if got is not None else ref.rows[r].ids[o:o + cnt]   # prefix pieces were content-verified
            cls = "OK" if (used == n and contiguous and sha(pack(ids)) == ref.rows[r].ids_sha) else "TOKEN_OFFSET_MISMATCH"
        out.append((cls, used))
    return out


def merge_pieces(pieces):
    """Merge row pieces that continue each other (same row, next offset)."""
    out = []
    for (r, o, n) in pieces:
        if n < 1:
            continue
        if out and out[-1][0] == r and out[-1][1] + out[-1][2] == o:
            out[-1] = (r, out[-1][1], out[-1][2] + n)
        else:
            out.append((r, o, n))
    return out


def fault_plan(ref, inject, n, o):
    """Row pieces (ordinal, offset, count) that a correct reader emits after restoring a cursor at
    (row n, offset o) with exactly ONE mutation. Derived from the frozen CR definitions only."""
    W = ref.W
    if inject is None:
        seq = [(n, o)] + [(r, 0) for r in range(n + 1, W)]
    elif inject == "skip_next_row":
        seq = [(n, o)] + [(r, 0) for r in range(n + 2, W)]
    elif inject == "repeat_next_row":
        seq = [(n, o), (n + 1, 0), (n + 1, 0)] + [(r, 0) for r in range(n + 2, W)]
    elif inject == "shift_consume_offset":
        seq = [(n, o + 1)] + [(r, 0) for r in range(n + 1, W)]
    else:
        raise ValueError("unknown inject %r" % (inject,))
    return [(r, off, len(ref.rows[r].ids) - off) for (r, off) in seq if len(ref.rows[r].ids) - off > 0]


def expected_run(ref, cur, inject):
    """Complete expected output of the run: the stream, its blocks, the chain, the tail."""
    e, carry = cur["emitted_blocks"], cur["carry"]
    pieces = fault_plan(ref, inject, cur["next_eligible_row"], cur["row_token_offset"])
    stream = list(carry)
    for (r, off, cnt) in pieces:
        stream += ref.rows[r].ids[off:off + cnt]
    nb = len(stream) // 65
    chain, digs = bytes.fromhex(cur["chain_hash"]), []
    for j in range(nb):
        d = hashlib.sha256(pack(stream[65 * j:65 * j + 65])).digest()
        digs.append(d)
        chain = hashlib.sha256(chain + d).digest()
    return {"stream": stream, "pieces": pieces, "digests": digs, "chain": chain.hex(), "nb": nb,
            "tail": stream[65 * nb:], "pos_end": 65 * e + len(stream)}


def integrity_errors(ref, tr, cur):
    """Self-consistency of a trace, independent of what it is supposed to contain:
    block numbering, per-block hash recomputed from ids, chain recomputed from the cursor's
    chain over the blocks actually present, totals, stream position, EOF-tail metadata."""
    run, blocks, fin = tr
    e, carry = cur["emitted_blocks"], cur["carry"]
    errs = []
    try:
        if [b["block_index"] for b in blocks] != list(range(e, e + len(blocks))):
            errs.append("BLOCK_NUMBERING")
        chain = bytes.fromhex(cur["chain_hash"])
        out_ids = []
        for b in blocks:
            ids = b["ids"]
            if len(ids) != 65 or any(type(x) is not int or not 1 <= x < ref.vocab for x in ids):
                errs.append("BLOCK_IDS block %s" % b["block_index"])
                break
            if not (isinstance(b["block_hash"], str) and H64.match(b["block_hash"])) or sha(pack(ids)) != b["block_hash"]:
                errs.append("BLOCK_HASH block %s" % b["block_index"])
                break
            chain = hashlib.sha256(chain + bytes.fromhex(b["block_hash"])).digest()
            out_ids += ids
        tail = fin["tail_ids"]
        if fin["kind"] != "eof_tail":
            errs.append("FINAL_KIND")
        if not (len(tail) < 65 and all(type(x) is int and 1 <= x < ref.vocab for x in tail)):
            errs.append("TAIL_IDS")
        if fin["tail_len"] != len(tail) or fin["tail_sha256"] != sha(pack(tail)):
            errs.append("TAIL_META")
        if fin["blocks_total"] != e + len(blocks) or fin["blocks_this_run"] != len(blocks):
            errs.append("BLOCKS_TOTAL")
        if fin["chain_hash"] != chain.hex():
            errs.append("CHAIN_HASH")
        if fin["stream_token_pos"] != 65 * (e + len(blocks)) + len(tail):
            errs.append("STREAM_TOKEN_POS")
        if (out_ids + tail)[:len(carry)] != carry:
            errs.append("RESTORED_CARRY_NOT_AT_STREAM_START")
    except (KeyError, TypeError, ValueError, IndexError) as exc:
        errs.append("MALFORMED %s" % exc)
    return errs


def cont_segments(tr):
    run, blocks, fin = tr
    out = []
    for b in blocks:
        out += segs_of(b["segments"])
    return out + segs_of(fin.get("tail_segments", []))


def stream_errors(ref, tr, exp):
    """The trace must equal the expected run exactly: every block's ids and hash, the tail,
    the final chain and position, and the global order of source pieces."""
    run, blocks, fin = tr
    errs = []
    if [b["ids"] for b in blocks] != [exp["stream"][65 * j:65 * j + 65] for j in range(exp["nb"])]:
        errs.append("BLOCK_IDS_DIFFER_FROM_EXPECTED")
    if [b["block_hash"] for b in blocks] != [d.hex() for d in exp["digests"]]:
        errs.append("BLOCK_HASHES_DIFFER_FROM_EXPECTED")
    if fin.get("tail_ids") != exp["tail"]:
        errs.append("TAIL_DIFFERS_FROM_EXPECTED")
    if fin.get("chain_hash") != exp["chain"] or fin.get("stream_token_pos") != exp["pos_end"]:
        errs.append("CHAIN_OR_POSITION_DIFFERS_FROM_EXPECTED")
    if merge_pieces(cont_segments(tr)) != merge_pieces(exp["pieces"]):
        errs.append("SOURCE_ORDER_DIFFERS_FROM_EXPECTED")
    return errs


def verify_cr(a):
    cfg, manifest, ref, _ = build_ref(a)
    spec = cfg["negatives"]["CR"][a.id]
    ck = Check()
    raw = rb(a.cursor)
    cur = json.loads(raw)
    e, s, carry, n = cur["emitted_blocks"], cur["stream_token_pos"], cur["carry"], cur["next_eligible_row"]
    # evidence isolation (g)
    before, _ = jload(a.evidence_before)
    after, _ = jload(a.evidence_after)
    if before != after:
        ck.block("(g) evidence mutated", "clean evidence / cursor hashes changed during the negative")
    code, _ = check_cursor(ref, manifest, raw)
    ck("(a) starting cursor passes the independent nine-step check, unmodified on disk", code is None, str(code))
    lr, _ = jload(a.load_report)
    ck("(a) reader load report: nine steps PASS", lr["result"] == "PASS" and [x["status"] for x in lr["steps"]] == ["PASS"] * 9)
    tr, ctl = load_trace(a.trace), load_trace(a.control)
    run, blocks, fin = tr
    ck("(b) reader ran to the end of the window", fin["kind"] == "eof_tail")
    ck("(c) trace starts at block %d and repeats no historical block" % e,
       bool(blocks) and blocks[0]["block_index"] == e and all(b["block_index"] >= e for b in blocks)
       and [b["block_index"] for b in blocks] == list(range(e, e + len(blocks))))
    ck("trace header matches the cursor", run["start_cursor_sha256"] == sha(raw) and run["carry_len"] == len(carry)
       and run["inject"] == spec["inject"] and ctl[0]["inject"] is None and ctl[0]["start_cursor_sha256"] == sha(raw))
    # trusted prefix (re-verified, not assumed)
    A = load_trace(os.path.join(a.clean_dir, "A_trace.jsonl"))
    pref = A[1][:e]
    pref_ok = len(pref) == e and all(b["block_index"] == j and b["ids"] == ref.stream[65 * j:65 * j + 65]
                                     and sha(pack(b["ids"])) == b["block_hash"] == ref.bdig[j].hex()
                                     and not claim_errors(ref, b["ids"], b["segments"], 0) for j, b in enumerate(pref))
    h = hashlib.sha256(b"MINI-MYTHOS-D1-CHAIN-V1").digest()
    for b in pref:
        h = hashlib.sha256(h + bytes.fromhex(b["block_hash"])).digest()
    if not (pref_ok and h.hex() == cur["chain_hash"]):
        ck.block("prefix evidence invalid", "clean prefix failed re-verification")
        return emit(a.out, ck.result({"id": a.id, "expected": spec, "verifier": VERIFIER_VERSION}))

    # trace integrity: fault trace and control trace get the SAME checks. The fault chain is NOT
    # required to equal the clean reference chain, but it must equal what its own blocks compute to.
    for label, t in (("fault trace", tr), ("control trace", ctl)):
        ie = integrity_errors(ref, t, cur)
        ck("%s integrity (block numbering, per-block hash, own chain, totals, stream pos, EOF tail metadata)" % label,
           not ie, "; ".join(ie))
    per, cerr = account(ref, pref, e, s, carry, tr)
    ck("trace claims verified against content", not cerr, "; ".join(cerr))
    cls = classify(ref, per)
    bad = [(r, c, u) for r, (c, u) in enumerate(cls) if c != "OK"]
    exp_row = n + 1 if spec["anomalous_row"] == "n+1" else n
    ln = len(ref.rows[exp_row].ids)
    exp_used = {"0": 0, "2*len": 2 * ln, "len-1": ln - 1}[spec["expected_consumed"]]
    ck("(d) exactly one anomalous row, ordinal %d (source row %d, split train)" % (exp_row, ref.rows[exp_row].phys),
       len(bad) == 1 and bad[0][0] == exp_row, str(bad[:5]))
    ck("(d) its class is %s and consumed == %d" % (spec["code"], exp_used),
       len(bad) == 1 and bad[0][1] == spec["code"] and bad[0][2] == exp_used, str(bad[:5]))
    # global check: the whole fault stream equals the expected one-mutation stream
    exp_t, exp_c = expected_run(ref, cur, spec["inject"]), expected_run(ref, cur, None)
    se = stream_errors(ref, tr, exp_t)
    ck("(d') fault trace equals the independently built expected one-mutation run (ids, hashes, tail, chain, source order)",
       not se, "; ".join(se))
    full_act = merge_pieces([(sg["ordinal"], sg["row_offset"], sg["count"]) for b in pref for sg in b["segments"]]
                            + ref.decompose(65 * e, s) + cont_segments(tr))
    full_exp = merge_pieces(ref.decompose(0, s) + exp_t["pieces"])
    ck("(d') whole-window source order (prefix + carry + continuation) equals the expected sequence", full_act == full_exp)
    ck("expected fault run differs from the clean continuation (the mutation is real)", exp_t["stream"] != exp_c["stream"])
    chain_differs = fin["chain_hash"] != ref.chain[ref.N].hex()
    ck("no UNCLASSIFIED_DIVERGENCE (a divergent chain has a classified row)", not (chain_differs and not bad))
    # (e) valid injection, (f) positive control
    idx_t = {b["block_index"]: b["block_hash"] for b in blocks}
    idx_c = {b["block_index"]: b["block_hash"] for b in ctl[1]}
    if idx_t == idx_c and fin["chain_hash"] == ctl[2]["chain_hash"]:
        ck.block("(e) invalid injection", "injected trace identical to control")
    per_c, cerr_c = account(ref, pref, e, s, carry, ctl)
    cls_c = classify(ref, per_c)
    ce = stream_errors(ref, ctl, exp_c)
    ck("(f) control: all rows OK, stream equals the clean continuation, blocks and chain equal the reference",
       not cerr_c and not ce and all(c == "OK" for c, _ in cls_c)
       and all(idx_c[j] == ref.bdig[j].hex() for j in idx_c) and ctl[2]["chain_hash"] == ref.chain[ref.N].hex()
       and len(ctl[1]) == ref.N - e, "; ".join(ce))
    res = ck.result({"id": a.id, "expected": spec, "start_cursor_row": n, "verifier": VERIFIER_VERSION,
                     "expected_total_tokens": exp_t["pos_end"], "expected_tail_len": len(exp_t["tail"]),
                     "anomalies": [{"ordinal": r, "source_row_index": ref.rows[r].phys, "split": "train",
                                    "class": c, "consumed": u, "row_len": len(ref.rows[r].ids)} for r, c, u in bad[:10]]})
    return emit(a.out, res)


# ------------------------------------------------------------------ misc commands
def evidence_hashes(a):
    out = {}
    for base, _, files in os.walk(a.dir):
        for f in files:
            p = os.path.join(base, f)
            out[os.path.relpath(p, a.dir)] = fsha(p)
    for extra in a.extra or []:
        out["EXTRA:" + extra] = fsha(extra)
    put(a.out, cj(out))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--mode", choices=("real", "selftest"), required=True)
        p.add_argument("--config", required=True)
        p.add_argument("--manifest", required=True)
        p.add_argument("--source", required=True)
        p.add_argument("--tokenizer", required=True)
        p.add_argument("--out")

    p = sub.add_parser("config-hash")
    p.add_argument("--config", required=True)
    p = sub.add_parser("schedule")
    common(p)
    p = sub.add_parser("check-cursor")
    common(p)
    p.add_argument("--cursor", required=True)
    p = sub.add_parser("verify-clean")
    common(p)
    p.add_argument("--clean-dir", required=True)
    p = sub.add_parser("verify-lr")
    common(p)
    p.add_argument("--id", required=True)
    p.add_argument("--orig", required=True)
    p.add_argument("--mutated", required=True)
    p.add_argument("--load-report", required=True)
    p.add_argument("--trace", required=True)
    p = sub.add_parser("verify-cr")
    common(p)
    p.add_argument("--id", required=True)
    p.add_argument("--cursor", required=True)
    p.add_argument("--load-report", required=True)
    p.add_argument("--trace", required=True)
    p.add_argument("--control", required=True)
    p.add_argument("--clean-dir", required=True)
    p.add_argument("--evidence-before", required=True)
    p.add_argument("--evidence-after", required=True)
    p = sub.add_parser("evidence-hashes")
    p.add_argument("--dir", required=True)
    p.add_argument("--extra", action="append")
    p.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    try:
        if a.cmd == "config-hash":
            print(fsha(a.config))
            return 0
        if a.cmd == "evidence-hashes":
            return evidence_hashes(a)
        if a.cmd == "schedule":
            cfg, manifest, ref, _ = build_ref(a)
            return emit(a.out, build_schedule(ref, cfg))
        if a.cmd == "check-cursor":
            cfg, manifest, ref, _ = build_ref(a)
            code, step = check_cursor(ref, manifest, rb(a.cursor))
            res = {"verdict": "PASS" if code is None else "FAIL", "code": code, "step": step, "checks": []}
            return emit(a.out, res)
        return {"verify-clean": verify_clean, "verify-lr": verify_lr, "verify-cr": verify_cr}[a.cmd](a)
    except Blocked as e:
        print("BLOCKED %s" % e)
        fallback_result(a, "BLOCKED", "blocked before evaluation: %s" % e)
        return 4
    except Exception as e:  # noqa: BLE001  - malformed/missing evidence or any other abnormal exit is a recorded FAIL
        print("FAIL abnormal exit: %r" % (e,))
        fallback_result(a, "FAIL", "abnormal exit: %r" % (e,))
        return 1


if __name__ == "__main__":
    sys.exit(main())
