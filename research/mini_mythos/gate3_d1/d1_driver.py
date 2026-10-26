#!/usr/bin/env python3
"""D1 orchestration: clean A/B runs, then the twelve controlled negatives.

Status: FROZEN CANDIDATE, pending ChatGPT code review. Nothing here has been run
on real data.

This file is coupled to d1_reader.py and d1_verifier.py ONLY through their
command lines (subprocess), so it cannot share any of their functions. It owns
the cursor *mutations* for LR1-LR9 (plain JSON edits) and the evidence layout:

  <workdir>/evidence/clean/        A_trace, B_seg1..6_trace, cursors/P1..P5, load_reports/, schedule  (read-only)
  <workdir>/evidence/negatives/    LR1..LR9, CR1..CR3  (write-once, each in its own directory)

Sub-commands: clean | negatives | all. Exit 0 only if every step behaved as frozen.
"""
import argparse
import json
import os
import re
import stat
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
READER = os.path.join(HERE, "d1_reader.py")
VERIFIER = os.path.join(HERE, "d1_verifier.py")
ENVMAN = os.path.join(HERE, "d1_env_manifest.py")
LOG = []
DEADLINE = [None]
H64 = re.compile(r"^[0-9a-f]{64}$")


class StepTimeout(Exception):
    pass


FROZEN_LIMIT_SECONDS = 1800.0                 # the 30-minute hard cap; a code constant so a config edit cannot relax it
VERDICT_EXIT = {"PASS": 0, "FAIL": 1, "BLOCKED": 4}


def identity(mode, cfg, manifest):
    """Bookkeeping label, not a security boundary: only a run in mode=real with a FROZEN config and a
    manifest that carries an authorization reference, a hub revision equal to the frozen one and an LFS
    oid equal to the parquet hash can be labelled a formal D1 candidate. Synthetic data never can."""
    if mode == "selftest":
        return "SELFTEST_SYNTHETIC"
    f = manifest.get("formal")
    ok = (cfg.get("status") == "FROZEN" and manifest.get("synthetic") is not True and isinstance(f, dict)
          and isinstance(f.get("authorization_ref"), str) and f["authorization_ref"].strip() != ""
          and f.get("hub_revision") == cfg["dataset"]["revision"]
          and f.get("lfs_oid_parquet") == manifest.get("parquet_sha256")
          and isinstance(f.get("tokenizer_fit_manifest_sha256"), str) and H64.match(f["tokenizer_fit_manifest_sha256"]) is not None)
    return "FORMAL_D1_CANDIDATE" if ok else "REAL_CODE_PATH_NON_FORMAL"


def canon(o):
    return json.dumps(o, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def write_once(p, text):
    os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
    with open(p, "x", encoding="utf-8", newline="\n") as f:
        f.write(text)


def sh(cmd, want=(0,)):
    name = [os.path.basename(cmd[0])] + cmd[1:]
    remaining = DEADLINE[0] - time.monotonic()
    if remaining <= 0:
        LOG.append({"cmd": name, "rc": "NOT_STARTED_DEADLINE_PASSED"})
        raise StepTimeout(name[0])
    try:
        r = subprocess.run([sys.executable, "-I"] + cmd, capture_output=True, text=True, timeout=remaining,
                           env=dict(os.environ, TOKENIZERS_PARALLELISM="false", PYTHONHASHSEED="0", CUDA_VISIBLE_DEVICES=""))
    except subprocess.TimeoutExpired:
        LOG.append({"cmd": name, "rc": "TIMEOUT_KILLED"})       # never retried
        raise StepTimeout(name[0])
    LOG.append({"cmd": name, "rc": r.returncode, "stdout": r.stdout.strip()[-400:], "stderr": r.stderr.strip()[-400:]})
    return r.returncode, r.stdout, r.stderr


def common(a):
    return ["--config", a.config, "--manifest", a.manifest, "--source", a.source, "--tokenizer", a.tokenizer]


def reader(a, extra):
    return [READER, "--mode", a.mode] + common(a) + extra


def verifier(a, sub, extra, out=None):
    return [VERIFIER, sub, "--mode", a.mode] + common(a) + (["--out", out] if out else []) + extra


def reader_status(rc, expect=0):
    """Map a reader exit code to OK | BLOCKED | FAIL. Exit 4 is a BLOCKED input/precondition and must never
    be reported as FAIL; exit 5 (self-check) and every other code are FAIL."""
    if rc == expect:
        return "OK"
    return "BLOCKED" if rc == 4 else "FAIL"


def verifier_verdict(rc, out_path):
    """Map a verifier exit code plus its result file to (PASS | FAIL | BLOCKED, why). A PASS needs BOTH exit 0 and
    a readable result file whose verdict is PASS. The only BLOCKED-without-a-verdict case is exit 4 with NO result
    file at all (the verifier stopped before evaluating). A result file that exists but cannot be parsed, an unknown
    verdict value, an exit-code/verdict disagreement and abnormal exit codes are all FAIL."""
    if rc not in VERDICT_EXIT.values():
        return "FAIL", "verifier abnormal exit rc=%r" % (rc,)
    if not os.path.lexists(out_path):
        if rc == 4:
            return "BLOCKED", "verifier exit 4 and no result file (blocked before evaluation)"
        return "FAIL", "verifier rc=%d: result file does not exist" % rc
    try:
        with open(out_path, "r", encoding="utf-8") as f:
            verdict = json.load(f)["verdict"]
    except Exception as e:  # noqa: BLE001
        return "FAIL", "verifier rc=%d: result file exists but is unreadable/malformed (%s)" % (rc, type(e).__name__)
    if verdict not in VERDICT_EXIT:
        return "FAIL", "verifier rc=%d: unknown verdict value %r" % (rc, verdict)
    expected = {v: k for k, v in VERDICT_EXIT.items()}[rc]
    if verdict != expected:
        return "FAIL", "verifier exit code %d disagrees with result verdict %s" % (rc, verdict)
    return verdict, "verifier rc=%d" % rc


def aggregate(verdicts):
    """FAIL takes precedence over BLOCKED, BLOCKED over PASS. Anything that is not exactly PASS/BLOCKED/FAIL, and an
    empty list (nothing was evaluated), count as FAIL. Per-item detail is kept by the caller."""
    vs = list(verdicts)
    if not vs or any(v not in VERDICT_EXIT for v in vs) or "FAIL" in vs:
        return "FAIL"
    return "BLOCKED" if "BLOCKED" in vs else "PASS"


def readonly(path):
    for base, _, files in os.walk(path):
        for f in files:
            p = os.path.join(base, f)
            os.chmod(p, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)


def flip(h):
    return h[:-1] + ("0" if h[-1] != "0" else "1")


def jread(p):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


# ------------------------------------------------------------------ clean
def do_clean(a):
    ev = os.path.join(a.workdir, "evidence")
    cd = os.path.join(ev, "clean")
    os.makedirs(cd, exist_ok=False)
    rc, _, _ = sh([ENVMAN, "--mode", a.mode, "--config", a.config, "--out", os.path.join(ev, "RUN_META.json")])
    if rc != 0:
        return ("BLOCKED" if rc == 4 else "FAIL"), "environment check rc=%d" % rc
    sched_path = os.path.join(cd, "schedule.json")
    rc, _, _ = sh(verifier(a, "schedule", [], sched_path))
    v, why = verifier_verdict(rc, sched_path)
    if v != "PASS":
        return v, ("BLOCKED(schedule): " if v == "BLOCKED" else "schedule step: ") + why
    sched = jread(sched_path)["points"]
    rc, _, _ = sh(reader(a, ["--trace-out", os.path.join(cd, "A_trace.jsonl")]))
    st = reader_status(rc)
    if st != "OK":
        return st, "reader A rc=%d" % rc
    names = ["P1", "P2", "P3", "P4", "P5"]
    for i in range(1, 7):
        x = ["--trace-out", os.path.join(cd, "B_seg%d_trace.jsonl" % i)]
        if i >= 2:
            x += ["--cursor-in", os.path.join(cd, "cursors", names[i - 2] + ".json"),
                  "--load-report-out", os.path.join(cd, "load_reports", "B_seg%d.json" % i)]
        if i <= 5:
            x += ["--cursor-out", os.path.join(cd, "cursors", names[i - 1] + ".json")]
        if i <= 4:
            x += ["--stop-pos", str(sched[names[i - 1]]["stream_pos"])]
        rc, _, _ = sh(reader(a, x))
        st = reader_status(rc)
        if st != "OK":
            return st, "reader B segment %d rc=%d" % (i, rc)
    readonly(cd)
    out = os.path.join(ev, "verify_clean_result.json")
    rc, _, _ = sh(verifier(a, "verify-clean", ["--clean-dir", cd], out))
    return verifier_verdict(rc, out)


# ------------------------------------------------------------------ negatives
def mutate(lid, c, sched, vocab):
    if lid == "LR1":
        c["row_token_offset"] += 1
    elif lid == "LR2":
        c["tokenizer_sha256"] = flip(c["tokenizer_sha256"])
    elif lid == "LR3":
        c["dataset"]["revision"] = "main"
    elif lid == "LR4":
        v = c["carry"][0]
        c["carry"][0] = v + 1 if v + 1 < vocab else v - 1
        assert c["carry"][0] >= 1 and c["carry"][0] != v
    elif lid == "LR5":
        c["row_tokens_sha256"] = flip(c["row_tokens_sha256"])
    elif lid == "LR6":
        c["row_token_offset"] = sched["P2"]["row_len"]
    elif lid == "LR7":
        c["row_token_offset"] = 1
    elif lid == "LR8":
        c["chain_hash"] = flip(c["chain_hash"])
    elif lid == "LR9":
        c["last_block_hash"] = flip(c["last_block_hash"])
    return c


def do_negatives(a):
    ev = os.path.join(a.workdir, "evidence")
    cd = os.path.join(ev, "clean")
    nd = os.path.join(ev, "negatives")
    cfg = jread(a.config)["negatives"]
    sch = jread(os.path.join(cd, "schedule.json"))
    sched, vocab = sch["points"], sch["vocab"]
    results = {}

    def hashes(path, cur):
        rc, _, _ = sh([VERIFIER, "evidence-hashes", "--dir", cd, "--extra", cur, "--out", path])
        return rc == 0 and os.path.exists(path)

    for lid, spec in cfg["LR"].items():
        d = os.path.join(nd, lid)
        orig = os.path.join(cd, "cursors", spec["cursor"] + ".json")
        mut = os.path.join(d, "mutated_cursor.json")
        write_once(mut, canon(mutate(lid, jread(orig), sched, vocab)))
        rc, _, _ = sh(reader(a, ["--cursor-in", mut, "--trace-out", os.path.join(d, "trace.jsonl"),
                                 "--load-report-out", os.path.join(d, "load_report.json")]))
        st = reader_status(rc, expect=3)                # a rejected cursor (exit 3) is the expected behaviour
        if st != "OK":
            results[lid] = {"verdict": st, "why": "reader rc=%d (expected 3)" % rc}
            continue
        res = os.path.join(d, "result.json")
        rc, _, _ = sh(verifier(a, "verify-lr", ["--id", lid, "--orig", orig, "--mutated", mut,
                                                "--load-report", os.path.join(d, "load_report.json"),
                                                "--trace", os.path.join(d, "trace.jsonl")], res))
        v, why = verifier_verdict(rc, res)
        results[lid] = {"verdict": v, "why": why}
    for cid, spec in cfg["CR"].items():
        d = os.path.join(nd, cid)
        cur = os.path.join(cd, "cursors", spec["cursor"] + ".json")
        before, after = os.path.join(d, "evidence_before.json"), os.path.join(d, "evidence_after.json")
        ok_before = hashes(before, cur)
        rc1, _, _ = sh(reader(a, ["--cursor-in", cur, "--inject", spec["inject"], "--trace-out", os.path.join(d, "trace.jsonl"),
                                  "--load-report-out", os.path.join(d, "load_report.json")]))
        rc2, _, _ = sh(reader(a, ["--cursor-in", cur, "--trace-out", os.path.join(d, "control_trace.jsonl"),
                                  "--load-report-out", os.path.join(d, "control_load_report.json")]))
        ok_after = hashes(after, cur)
        sts = [reader_status(rc1), reader_status(rc2)]
        if "BLOCKED" in sts or "FAIL" in sts:
            results[cid] = {"verdict": "BLOCKED" if "BLOCKED" in sts else "FAIL", "why": "reader rc=%d/%d" % (rc1, rc2)}
            continue
        if not (ok_before and ok_after):
            results[cid] = {"verdict": "FAIL", "why": "evidence hash files could not be written"}
            continue
        res = os.path.join(d, "result.json")
        rc, _, _ = sh(verifier(a, "verify-cr", ["--id", cid, "--cursor", cur, "--load-report", os.path.join(d, "load_report.json"),
                                                "--trace", os.path.join(d, "trace.jsonl"), "--control", os.path.join(d, "control_trace.jsonl"),
                                                "--clean-dir", cd, "--evidence-before", before, "--evidence-after", after], res))
        v, why = verifier_verdict(rc, res)
        results[cid] = {"verdict": v, "why": why}
    write_once(os.path.join(ev, "negatives_result.json"), canon(results))
    return aggregate(v["verdict"] for v in results.values()), results


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=("clean", "negatives", "all"))
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--mode", choices=("real", "selftest"), required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--source", required=True)
    ap.add_argument("--tokenizer", required=True)
    ap.add_argument("--timeout-seconds", type=float,
                    help="selftest only: a SHORTER wall-clock limit than the frozen 30 minutes; refused in mode=real")
    a = ap.parse_args(argv)
    LOG.clear()
    ev = os.path.join(a.workdir, "evidence")
    os.makedirs(ev, exist_ok=True)
    decision = {"driver": "d1_driver/4", "mode": a.mode,
                "note": "identity SELFTEST_SYNTHETIC / REAL_CODE_PATH_NON_FORMAL results are code self-tests and are NOT D1 evidence",
                "component_scope": {"read_resume": "R1-R5 and the post-run part of R6", "negatives_meta": "R8 (LR1-LR9, CR1-CR3)"},
                "not_tested": ["R6: hash before the read and validation/test isolation",
                               "R7: validation/test hash, row count, token count, round-trip",
                               "T1-T6: tokenizer acceptance, repeat-fit determinism",
                               "data acquisition integrity (Hub listing, LFS oid, README/licence)"],
                "d1_overall": "NOT_DECLARED__PIPELINE_INCOMPLETE",
                "declared": "script output only; this pipeline cannot emit an overall D1 verdict, and D1 is never PASS/CLOSED without independent ChatGPT review and owner authorization"}
    verdict, code = "PASS", 0

    def finish(verdict):
        decision["verdict"] = verdict
        decision["steps"] = LOG
        try:
            write_once(os.path.join(ev, "D1_DECISION_%s.json" % a.cmd), canon(decision))
        except Exception as e:  # noqa: BLE001
            sys.stderr.write("DECISION_NOT_WRITTEN %r\n%s\n" % (e, canon(decision)))
            return 1
        print(json.dumps({k: decision[k] for k in decision if k in (
            "identity", "read_resume", "negatives_meta", "timeout", "timeout_override_refused", "driver_exception", "d1_overall")},
            sort_keys=True)[:3000])
        return VERDICT_EXIT[verdict]

    # The 30-minute cap is frozen: no override in real mode, and a selftest override may only shorten it.
    refusal = None
    if a.timeout_seconds is not None:
        if a.mode != "selftest":
            refusal = "--timeout-seconds is not allowed in mode=real; the frozen 30-minute limit applies"
        elif not 0 < a.timeout_seconds <= FROZEN_LIMIT_SECONDS:
            refusal = "--timeout-seconds must be in (0, %d] (it may only shorten the frozen limit)" % FROZEN_LIMIT_SECONDS
    if refusal:
        decision["timeout_override_refused"] = {"verdict": "BLOCKED", "reason": refusal}
        return finish("BLOCKED")
    try:
        cfg, manifest = jread(a.config), jread(a.manifest)
        cfg_limit = cfg["environment"]["wallclock_limit_minutes"] * 60.0
        if a.mode == "real" and cfg_limit != FROZEN_LIMIT_SECONDS:
            decision["timeout_override_refused"] = {"verdict": "BLOCKED", "reason": "config wallclock limit %s differs from the frozen %d s" % (cfg_limit, FROZEN_LIMIT_SECONDS)}
            return finish("BLOCKED")
        limit = min(a.timeout_seconds if a.timeout_seconds is not None else cfg_limit, FROZEN_LIMIT_SECONDS)
        DEADLINE[0] = time.monotonic() + limit
        ident = identity(a.mode, cfg, manifest)
        decision.update(identity=ident, d1_formal_experiment=ident == "FORMAL_D1_CANDIDATE", wallclock_limit_seconds=limit)
        if a.cmd in ("clean", "all"):
            v, why = do_clean(a)
            decision["read_resume"] = {"verdict": v, "why": why}
            verdict = v
        if a.cmd in ("negatives", "all"):
            if verdict == "PASS":
                v, res = do_negatives(a)
                decision["negatives_meta"] = {"verdict": v, "items": res,
                                              "counts": {k: sum(1 for x in res.values() if x["verdict"] == k) for k in VERDICT_EXIT},
                                              "aggregation": "FAIL > BLOCKED > PASS; every item keeps its own verdict and reason"}
                verdict = v
            else:
                decision["negatives_meta"] = {"verdict": "NOT TESTED", "why": "clean stage verdict was %s" % verdict}
    except StepTimeout as e:
        decision["timeout"] = {"verdict": "BLOCKED(timeout)", "step": str(e),
                               "policy": "BLOCKED; existing evidence kept as is; no automatic retry"}
        decision["evidence_files_at_timeout"] = sorted(
            os.path.relpath(os.path.join(b, f), ev) for b, _, fs in os.walk(ev) for f in fs) if os.path.isdir(ev) else []
        verdict = "BLOCKED"
    except Exception as e:  # noqa: BLE001  - never terminate without a decision record
        decision["driver_exception"] = {"verdict": "FAIL", "error": repr(e)[:500]}
        verdict = "FAIL"
    return finish(verdict)


if __name__ == "__main__":
    sys.exit(main())
