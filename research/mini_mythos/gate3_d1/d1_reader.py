#!/usr/bin/env python3
"""D1 reader: single-process, CPU-only, cursor save/restore over the first 2048
eligible train rows, packed into 65-token blocks.

Status: FROZEN CANDIDATE, pending ChatGPT code review. Nothing here has been run
on real data. Design: docs/F3B_D1_FROZEN_EXECUTION_PROPOSAL{,_R1,_R2}.md.

Independence rule: this file must not import, and must not share any function
with, d1_verifier.py. Cursor validation, source-row mapping and the reference
stream are implemented here separately (the verifier has its own).

Exit codes: 0 ok, 3 cursor rejected at load, 4 BLOCKED input, 5 self-check failed.
Outputs are write-once (opened with mode 'x').
"""
import argparse
import bisect
import hashlib
import json
import os
import re
import struct
import sys
import unicodedata

READER_VERSION = "d1_reader/1"
CHAIN_INIT = b"MINI-MYTHOS-D1-CHAIN-V1"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
INJECTIONS = (None, "skip_next_row", "repeat_next_row", "shift_consume_offset")


class CursorError(Exception):
    def __init__(self, code, step, detail=""):
        super().__init__("%s (step %d) %s" % (code, step, detail))
        self.code, self.step, self.detail = code, step, detail


class Blocked(Exception):
    pass


class SelfCheckFailed(Exception):
    pass


# ---------------------------------------------------------------- primitives
def sha_hex(b):
    return hashlib.sha256(b).hexdigest()


def ser_ids(ids):
    return struct.pack("<%dI" % len(ids), *ids)


def canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def write_once(path, text):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "x", encoding="utf-8", newline="\n") as f:
        f.write(text)


def file_sha(path):
    with open(path, "rb") as f:
        return sha_hex(f.read())


# ---------------------------------------------------------------- inputs
def load_json(path):
    with open(path, "rb") as f:
        raw = f.read()
    return json.loads(raw.decode("utf-8")), sha_hex(raw)


def load_texts(source):
    kind, _, path = source.partition(":")
    if kind == "parquet":
        import pyarrow.parquet as pq  # real mode only
        return pq.read_table(path, columns=["text"]).column("text").to_pylist()
    if kind == "jsonl":
        out = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                out.append(json.loads(line)["text"])
        return out
    raise Blocked("UNKNOWN_SOURCE_KIND:%s" % kind)


def make_encoder(mode, tokenizer_path, manifest, cfg):
    """Returns (encode, vocab_size, tokenizer_sha256)."""
    tcfg = cfg["tokenizer"]
    sha = file_sha(tokenizer_path)
    if mode == "selftest":
        # Synthetic stand-in; only for code self-tests. ids = 3 + utf-8 byte.
        with open(tokenizer_path, "rb") as f:
            if f.read().strip() != b"TOY-BYTE-ENCODER-V1":
                raise Blocked("SELFTEST_TOKENIZER_FILE_INVALID")
        return (lambda s: [3 + b for b in s.encode("utf-8")]), 259, sha
    from tokenizers import Tokenizer  # real mode only
    if sha != manifest["tokenizer_sha256"]:
        raise Blocked("TOKENIZER_FILE_HASH_MISMATCH")
    tk = Tokenizer.from_file(tokenizer_path)
    if tk.post_processor is not None or tk.padding is not None or tk.truncation is not None:
        raise Blocked("TOKENIZER_HAS_POSTPROCESSOR_PADDING_OR_TRUNCATION")
    for name, (lit, tid) in tcfg["special_tokens"].items():
        if tk.token_to_id(lit) != tid:
            raise Blocked("SPECIAL_TOKEN_ID_MISMATCH:%s" % name)
    if tk.get_vocab_size() != manifest["actual_vocab_size"]:
        raise Blocked("VOCAB_SIZE_MISMATCH")

    def encode(s):
        return tk.encode(s, is_pretokenized=False, add_special_tokens=False).ids

    return encode, tk.get_vocab_size(), sha


# ---------------------------------------------------------------- window / reference
class Window:
    """First `window_rows` eligible rows with tokens(r), cumulative offsets,
    the flat reference stream, block hashes and the hash chain."""

    def __init__(self, cfg, texts, encode, vocab):
        w = cfg["window"]
        self.W, self.vocab = w["window_rows"], vocab
        heading = re.compile(cfg["rows"]["level1_heading_regex"])
        eos = cfg["tokenizer"]["special_tokens"]["eos"][1]
        lits = [v[0] for v in cfg["tokenizer"]["special_tokens"].values()]
        self.phys, self.text_sha, self.toks, self.tok_sha = [], [], [], []
        self.n_headings = 0
        for idx, t in enumerate(texts):
            if not isinstance(t, str):
                raise Blocked("NON_STRING_TEXT:%d" % idx)
            if t.strip() == "":
                continue
            ordinal = len(self.phys)
            nfc = unicodedata.normalize("NFC", t)
            if any(l in nfc for l in lits):
                raise Blocked("SPECIAL_TOKEN_LITERAL_IN_TEXT:%d" % idx)
            is_head = heading.match(nfc) is not None
            self.n_headings += int(is_head)
            ids = ([eos] if (is_head and ordinal > 0) else []) + list(encode(nfc))
            if not ids:
                raise Blocked("EMPTY_TOKENS:%d" % idx)
            if min(ids) < 1 or max(ids) >= vocab:
                raise Blocked("TOKEN_ID_OUT_OF_RANGE_OR_PAD:%d" % idx)
            self.phys.append(idx)
            self.text_sha.append(sha_hex(nfc.encode("utf-8")))
            self.toks.append(ids)
            self.tok_sha.append(sha_hex(ser_ids(ids)))
            if len(self.phys) == self.W:
                break
        if len(self.phys) < self.W:
            raise Blocked("WINDOW_TOO_SMALL:%d" % len(self.phys))
        self.cum = [0]
        for ids in self.toks:
            self.cum.append(self.cum[-1] + len(ids))
        self.T = self.cum[-1]
        self.flat = [x for ids in self.toks for x in ids]
        self.N = self.T // 65
        self.bh = [hashlib.sha256(ser_ids(self.flat[65 * j:65 * j + 65])).digest() for j in range(self.N)]
        self.H = [hashlib.sha256(CHAIN_INIT).digest()]
        for j in range(self.N):
            self.H.append(hashlib.sha256(self.H[j] + self.bh[j]).digest())


# ---------------------------------------------------------------- cursor
CURSOR_KEYS = ("schema", "dataset", "tokenizer_sha256", "window_rows", "seq_len", "block_len",
               "next_eligible_row", "source_row_index", "row_text_sha256", "row_tokens_sha256",
               "row_token_offset", "carry", "emitted_blocks", "stream_token_pos", "chain_hash",
               "last_block_hash", "eof", "rng")
DATASET_KEYS = ("repo_id", "config", "revision", "split", "parquet_sha256")


def _isint(x):
    return isinstance(x, int) and not isinstance(x, bool)


def _hex_or_none(x, allow_none):
    return (x is None and allow_none) or (isinstance(x, str) and HEX64.match(x) is not None)


def validate_cursor(raw_bytes, cfg, manifest, win):
    """Nine ordered checks. Returns (cursor_dict, steps). Raises CursorError at
    the first failing check; the caller gets the passed-steps list via .steps."""
    steps = []

    def done(n, name):
        steps.append({"step": n, "name": name, "status": "PASS"})

    def fail(code, step, detail=""):
        e = CursorError(code, step, detail)
        e.steps = steps
        raise e

    # 1 schema / types / canonical form
    try:
        cur = json.loads(raw_bytes.decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        fail("SCHEMA_INVALID", 1, "unparsable: %s" % exc)
    if not isinstance(cur, dict) or set(cur) != set(CURSOR_KEYS):
        fail("SCHEMA_INVALID", 1, "key set")
    if cur["schema"] != cfg["cursor"]["schema"]:
        fail("SCHEMA_INVALID", 1, "schema id")
    ds = cur["dataset"]
    if not isinstance(ds, dict) or set(ds) != set(DATASET_KEYS) or not all(isinstance(ds[k], str) for k in DATASET_KEYS):
        fail("SCHEMA_INVALID", 1, "dataset block")
    for k in ("window_rows", "seq_len", "block_len", "next_eligible_row", "row_token_offset",
              "emitted_blocks", "stream_token_pos"):
        if not _isint(cur[k]):
            fail("SCHEMA_INVALID", 1, k)
    if not (isinstance(cur["eof"], bool) and cur["rng"] is None):
        fail("SCHEMA_INVALID", 1, "eof/rng")
    if not (_hex_or_none(cur["tokenizer_sha256"], False) and _hex_or_none(cur["chain_hash"], False)
            and _hex_or_none(cur["last_block_hash"], True) and _hex_or_none(cur["row_text_sha256"], True)
            and _hex_or_none(cur["row_tokens_sha256"], True)):
        fail("SCHEMA_INVALID", 1, "hex fields")
    if not (cur["source_row_index"] is None or _isint(cur["source_row_index"])):
        fail("SCHEMA_INVALID", 1, "source_row_index")
    if not (isinstance(cur["carry"], list) and all(_isint(x) for x in cur["carry"])):
        fail("SCHEMA_INVALID", 1, "carry")
    if canon(cur).encode("utf-8") != raw_bytes:
        fail("SCHEMA_INVALID", 1, "not canonical JSON bytes")
    done(1, "schema")

    # 2 dataset identity
    dcfg = cfg["dataset"]
    if (ds["repo_id"], ds["config"], ds["split"]) != (dcfg["repo_id"], dcfg["config"], dcfg["split"]):
        fail("DATASET_IDENTITY_MISMATCH", 2)
    if not HEX40.match(ds["revision"]) or ds["revision"] != dcfg["revision"]:
        fail("REVISION_MISMATCH", 2)
    if ds["parquet_sha256"] != manifest["parquet_sha256"]:
        fail("PARQUET_HASH_MISMATCH", 2)
    done(2, "dataset identity")

    # 3 tokenizer
    if cur["tokenizer_sha256"] != manifest["tokenizer_sha256"]:
        fail("TOKENIZER_HASH_MISMATCH", 3)
    done(3, "tokenizer hash")

    # 4 window parameters
    wcfg = cfg["window"]
    if (cur["window_rows"], cur["seq_len"], cur["block_len"]) != (wcfg["window_rows"], wcfg["seq_len"], wcfg["block_len"]):
        fail("WINDOW_PARAMS_MISMATCH", 4)
    done(4, "window params")

    # 5 ranges / EOF / offset
    nr, off = cur["next_eligible_row"], cur["row_token_offset"]
    if not 0 <= nr <= win.W:
        fail("ROW_OUT_OF_RANGE", 5)
    if cur["eof"]:
        if nr != win.W or off != 0 or any(cur[k] is not None for k in ("source_row_index", "row_text_sha256", "row_tokens_sha256")):
            fail("EOF_INCONSISTENT", 5)
    else:
        if nr >= win.W:
            fail("EOF_INCONSISTENT", 5)
        if not 0 <= off <= len(win.toks[nr]) - 1:
            fail("OFFSET_OUT_OF_RANGE", 5)
    done(5, "ranges / EOF / offset")

    # 6 source-row identity
    if not cur["eof"]:
        if (cur["source_row_index"] != win.phys[nr] or cur["row_text_sha256"] != win.text_sha[nr]
                or cur["row_tokens_sha256"] != win.tok_sha[nr]):
            fail("ROW_IDENTITY_MISMATCH", 6)
    done(6, "source row identity")

    # 7 position formulas
    e, pos, carry = cur["emitted_blocks"], cur["stream_token_pos"], cur["carry"]
    if pos != win.cum[nr] + off or pos != 65 * e + len(carry):
        fail("CURSOR_POSITION_MISMATCH", 7)
    done(7, "position formulas")

    # 8 carry
    if len(carry) > 64:
        fail("CARRY_LENGTH_INVALID", 8)
    if any(not 1 <= x < win.vocab for x in carry):
        fail("TOKEN_ID_INVALID", 8)
    if carry != win.flat[65 * e:pos]:
        fail("CARRY_TOKEN_MISMATCH", 8)
    done(8, "carry")

    # 9 hash chain
    if e > win.N or cur["chain_hash"] != win.H[e].hex():
        fail("CHAIN_HASH_MISMATCH", 9)
    want_last = None if e == 0 else win.bh[e - 1].hex()
    if cur["last_block_hash"] != want_last:
        fail("LAST_BLOCK_HASH_MISMATCH", 9)
    done(9, "hash chain")
    return cur, steps


def make_cursor(cfg, manifest, win, pos, emitted, pending, chain, last_hash):
    d = cfg["dataset"]
    base = {
        "schema": cfg["cursor"]["schema"],
        "dataset": {"repo_id": d["repo_id"], "config": d["config"], "revision": d["revision"],
                    "split": d["split"], "parquet_sha256": manifest["parquet_sha256"]},
        "tokenizer_sha256": manifest["tokenizer_sha256"],
        "window_rows": win.W, "seq_len": cfg["window"]["seq_len"], "block_len": cfg["window"]["block_len"],
        "carry": list(pending), "emitted_blocks": emitted, "stream_token_pos": pos,
        "chain_hash": chain.hex(), "last_block_hash": last_hash, "rng": None,
    }
    if pos == win.T:
        base.update(next_eligible_row=win.W, source_row_index=None, row_text_sha256=None,
                    row_tokens_sha256=None, row_token_offset=0, eof=True)
    else:
        r = bisect.bisect_right(win.cum, pos) - 1  # row containing pos; pos==cum[r+1] -> r+1
        base.update(next_eligible_row=r, source_row_index=win.phys[r], row_text_sha256=win.text_sha[r],
                    row_tokens_sha256=win.tok_sha[r], row_token_offset=pos - win.cum[r], eof=False)
    return base


# ---------------------------------------------------------------- segment assertion
def assert_tiles(segs, lens, start_ord, start_off, end_ord, end_off):
    """No gap, no overlap, full coverage between (start) and (end) row positions."""
    r, o = start_ord, start_off
    for s in segs:
        if s["count"] < 1:
            raise SelfCheckFailed("SEGMENT_EMPTY")
        if s["ordinal"] > r or (s["ordinal"] == r and s["row_offset"] > o):
            raise SelfCheckFailed("SEGMENT_GAP at row %d offset %d" % (r, o))
        if s["ordinal"] < r or s["row_offset"] < o:
            raise SelfCheckFailed("SEGMENT_OVERLAP at row %d offset %d" % (r, o))
        if o + s["count"] > lens[r]:
            raise SelfCheckFailed("SEGMENT_OVERLAP past row end %d" % r)
        o += s["count"]
        if o == lens[r]:
            r, o = r + 1, 0
    if (r, o) != (end_ord, end_off):
        raise SelfCheckFailed("SEGMENT_UNCOVERED: stopped at (%d,%d), expected (%d,%d)" % (r, o, end_ord, end_off))


# ---------------------------------------------------------------- run
def jl(obj):
    return canon(obj) + "\n"


def run(args):
    cfg, cfg_sha = load_json(args.config)
    manifest, manifest_sha = load_json(args.manifest)
    want_kind = "parquet" if args.mode == "real" else "jsonl"
    if not args.source.startswith(want_kind + ":"):
        raise Blocked("MODE_%s_REQUIRES_%s_SOURCE" % (args.mode.upper(), want_kind.upper()))
    texts = load_texts(args.source)
    encode, vocab, tok_sha = make_encoder(args.mode, args.tokenizer, manifest, cfg)
    if tok_sha != manifest["tokenizer_sha256"]:
        raise Blocked("MANIFEST_TOKENIZER_SHA_MISMATCH")
    win = Window(cfg, texts, encode, vocab)
    lens = [len(t) for t in win.toks]

    inject = None if args.inject in (None, "none") else args.inject
    if inject not in INJECTIONS:
        raise Blocked("UNKNOWN_INJECTION")

    trace = []
    run_rec = {"type": "run", "reader": READER_VERSION, "mode": args.mode, "pid": os.getpid(),
               "config_sha256": cfg_sha, "manifest_sha256": manifest_sha, "inject": inject,
               "stop_pos": args.stop_pos, "start_cursor_sha256": None, "carry_len": 0, "start_stream_pos": 0,
               "window_tokens": win.T, "window_blocks": win.N, "level1_headings": win.n_headings}

    # ---- start state
    if args.cursor_in:
        with open(args.cursor_in, "rb") as f:
            raw = f.read()
        run_rec["start_cursor_sha256"] = sha_hex(raw)
        try:
            cur, steps = validate_cursor(raw, cfg, manifest, win)
        except CursorError as e:
            report = {"result": "REJECTED", "code": e.code, "failed_step": e.step, "detail": e.detail,
                      "steps": e.steps + [{"step": e.step, "status": "FAIL", "code": e.code}]}
            if args.load_report_out:
                write_once(args.load_report_out, canon(report))
            trace_text = jl(run_rec) + jl({"type": "final", "kind": "rejected", "code": e.code, "blocks_total": 0})
            write_once(args.trace_out, trace_text)
            print("CURSOR_REJECTED %s step=%d" % (e.code, e.step))
            return 3
        if args.load_report_out:
            write_once(args.load_report_out, canon({"result": "PASS", "code": None, "failed_step": None, "steps": steps}))
        if cur["eof"] and inject:
            raise Blocked("INJECTION_ON_EOF_CURSOR")
        k, o = cur["next_eligible_row"], cur["row_token_offset"]
        pending = list(cur["carry"])
        emitted, last_hash = cur["emitted_blocks"], cur["last_block_hash"]
        chain = bytes.fromhex(cur["chain_hash"])
        run_rec["carry_len"], run_rec["start_stream_pos"] = len(pending), cur["stream_token_pos"]
        plan = [] if cur["eof"] else [(k, o)] + [(i, 0) for i in range(k + 1, win.W)]
        start_ord, start_off = (win.W, 0) if cur["eof"] else (k, o)
    else:
        if inject:
            raise Blocked("INJECTION_REQUIRES_CURSOR")
        pending, emitted, last_hash, chain = [], 0, None, win.H[0]
        plan = [(i, 0) for i in range(win.W)]
        start_ord, start_off = 0, 0

    # ---- injection: applied to the read plan only, after the load checks passed
    if inject == "skip_next_row":
        del plan[1]                      # whole row n+1 is never read
    elif inject == "repeat_next_row":
        plan.insert(2, plan[1])          # row n+1 is read a second time
    elif inject == "shift_consume_offset":
        plan[0] = (plan[0][0], plan[0][1] + 1)   # token at index o is never consumed
    stop = args.stop_pos
    if stop is not None and inject:
        raise Blocked("STOP_POS_WITH_INJECTION_NOT_SUPPORTED")
    if stop is not None and not (65 * emitted + len(pending) < stop < win.T):
        raise Blocked("STOP_POS_OUT_OF_RANGE")

    trace.append(jl(run_rec))
    all_segs, cur_segs, stopped = [], [], False
    blocks_this_run = 0

    def pos():
        return 65 * emitted + len(pending)

    for ordinal, start in plan:
        toks = win.toks[ordinal]
        i = start
        if stop is not None and pos() == stop:
            stopped = True
            break
        while i < len(toks):
            if stop is not None and pos() == stop:
                stopped = True
                break
            take = min(len(toks) - i, 65 - len(pending))
            if stop is not None:
                take = min(take, stop - pos())
            pending.extend(toks[i:i + take])
            seg = {"ordinal": ordinal, "source_row_index": win.phys[ordinal], "row_offset": i, "count": take}
            cur_segs.append(seg)
            all_segs.append(seg)
            i += take
            if len(pending) == 65:
                bh = hashlib.sha256(ser_ids(pending)).digest()
                trace.append(jl({"type": "block", "block_index": emitted, "block_hash": bh.hex(),
                                 "ids": pending, "segments": cur_segs}))
                chain = hashlib.sha256(chain + bh).digest()
                last_hash = bh.hex()
                emitted += 1
                blocks_this_run += 1
                pending, cur_segs = [], []
        if stopped:
            break

    # ---- finish
    p = pos()
    if stopped:
        if p != stop:
            raise SelfCheckFailed("STOP_POS_NOT_REACHED")
        final = {"type": "final", "kind": "carry", "carry_ids": pending, "carry_segments": cur_segs,
                 "carry_len": len(pending), "blocks_total": emitted, "blocks_this_run": blocks_this_run,
                 "chain_hash": chain.hex(), "stream_token_pos": p}
        end_ord, end_off = win.W, 0
        if p < win.T:
            end_ord = bisect.bisect_right(win.cum, p) - 1
            end_off = p - win.cum[end_ord]
    else:
        # real end of the window: what is left is the EOF tail (not a carry)
        if not inject and (p != win.T or len(pending) != win.T - 65 * (win.T // 65)):
            raise SelfCheckFailed("EOF_TAIL_ACCOUNTING")
        final = {"type": "final", "kind": "eof_tail", "tail_ids": pending, "tail_segments": cur_segs,
                 "tail_len": len(pending), "tail_sha256": sha_hex(ser_ids(pending)),
                 "blocks_total": emitted, "blocks_this_run": blocks_this_run,
                 "chain_hash": chain.hex(), "stream_token_pos": p}
        end_ord, end_off = win.W, 0
    trace.append(jl(final))

    if inject is None:
        try:
            assert_tiles(all_segs, lens, start_ord, start_off, end_ord, end_off)
            if chain != win.H[emitted]:
                raise SelfCheckFailed("CHAIN_VS_REFERENCE")
        except SelfCheckFailed as exc:
            print("SELF_CHECK_FAILED %s" % exc)
            return 5
        self_check = "tiles+chain OK"
    else:
        self_check = "skipped (injection)"
    print("OK kind=%s blocks_this_run=%d blocks_total=%d pos=%d self_check=%s"
          % (final["kind"], blocks_this_run, emitted, p, self_check))

    write_once(args.trace_out, "".join(trace))
    if args.cursor_out:
        if inject:
            raise Blocked("CURSOR_OUT_WITH_INJECTION_NOT_ALLOWED")
        c = make_cursor(cfg, manifest, win, p, emitted, pending, chain, last_hash)
        write_once(args.cursor_out, canon(c))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--mode", choices=("real", "selftest"), required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--source", required=True, help="parquet:PATH or jsonl:PATH (selftest)")
    ap.add_argument("--tokenizer", required=True)
    ap.add_argument("--trace-out", required=True)
    ap.add_argument("--cursor-in")
    ap.add_argument("--cursor-out")
    ap.add_argument("--load-report-out")
    ap.add_argument("--stop-pos", type=int)
    ap.add_argument("--inject", choices=("none", "skip_next_row", "repeat_next_row", "shift_consume_offset"))
    args = ap.parse_args(argv)
    try:
        return run(args)
    except Blocked as e:
        print("BLOCKED %s" % e)
        return 4
    except SelfCheckFailed as e:
        print("SELF_CHECK_FAILED %s" % e)
        return 5


if __name__ == "__main__":
    sys.exit(main())
