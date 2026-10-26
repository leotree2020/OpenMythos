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
import stat
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
READER = os.path.join(HERE, "d1_reader.py")
VERIFIER = os.path.join(HERE, "d1_verifier.py")
ENVMAN = os.path.join(HERE, "d1_env_manifest.py")
LOG = []


def canon(o):
    return json.dumps(o, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def write_once(p, text):
    os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
    with open(p, "x", encoding="utf-8", newline="\n") as f:
        f.write(text)


def sh(cmd, want=(0,)):
    r = subprocess.run([sys.executable, "-I"] + cmd, capture_output=True, text=True,
                       env=dict(os.environ, TOKENIZERS_PARALLELISM="false", PYTHONHASHSEED="0", CUDA_VISIBLE_DEVICES=""))
    LOG.append({"cmd": [os.path.basename(cmd[0])] + cmd[1:], "rc": r.returncode, "stdout": r.stdout.strip()[-400:], "stderr": r.stderr.strip()[-400:]})
    return r.returncode, r.stdout, r.stderr


def common(a):
    return ["--config", a.config, "--manifest", a.manifest, "--source", a.source, "--tokenizer", a.tokenizer]


def reader(a, extra):
    return [READER, "--mode", a.mode] + common(a) + extra


def verifier(a, sub, extra, out=None):
    return [VERIFIER, sub, "--mode", a.mode] + common(a) + (["--out", out] if out else []) + extra


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
        return "BLOCKED", "environment check rc=%d" % rc
    rc, _, _ = sh(verifier(a, "schedule", [], os.path.join(cd, "schedule.json")))
    if rc != 0:
        return "BLOCKED", "BLOCKED(schedule) rc=%d" % rc
    sched = jread(os.path.join(cd, "schedule.json"))["points"]
    rc, _, _ = sh(reader(a, ["--trace-out", os.path.join(cd, "A_trace.jsonl")]))
    if rc != 0:
        return "FAIL", "reader A rc=%d" % rc
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
        if rc != 0:
            return "FAIL", "reader B segment %d rc=%d" % (i, rc)
    readonly(cd)
    out = os.path.join(ev, "verify_clean_result.json")
    rc, _, _ = sh(verifier(a, "verify-clean", ["--clean-dir", cd], out))
    return {0: "PASS", 1: "FAIL", 4: "BLOCKED"}.get(rc, "FAIL"), "verify-clean rc=%d" % rc


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
    for lid, spec in cfg["LR"].items():
        d = os.path.join(nd, lid)
        orig = os.path.join(cd, "cursors", spec["cursor"] + ".json")
        mut = os.path.join(d, "mutated_cursor.json")
        write_once(mut, canon(mutate(lid, jread(orig), sched, vocab)))
        rc, _, _ = sh(reader(a, ["--cursor-in", mut, "--trace-out", os.path.join(d, "trace.jsonl"),
                                 "--load-report-out", os.path.join(d, "load_report.json")]))
        if rc != 3:
            results[lid] = {"verdict": "FAIL", "why": "reader rc=%d (expected 3)" % rc}
            continue
        rc, _, _ = sh(verifier(a, "verify-lr", ["--id", lid, "--orig", orig, "--mutated", mut,
                                                "--load-report", os.path.join(d, "load_report.json"),
                                                "--trace", os.path.join(d, "trace.jsonl")], os.path.join(d, "result.json")))
        results[lid] = {"verdict": jread(os.path.join(d, "result.json"))["verdict"], "verifier_rc": rc}
    for cid, spec in cfg["CR"].items():
        d = os.path.join(nd, cid)
        cur = os.path.join(cd, "cursors", spec["cursor"] + ".json")
        before, after = os.path.join(d, "evidence_before.json"), os.path.join(d, "evidence_after.json")
        sh([VERIFIER, "evidence-hashes", "--dir", cd, "--extra", cur, "--out", before])
        rc1, _, _ = sh(reader(a, ["--cursor-in", cur, "--inject", spec["inject"], "--trace-out", os.path.join(d, "trace.jsonl"),
                                  "--load-report-out", os.path.join(d, "load_report.json")]))
        rc2, _, _ = sh(reader(a, ["--cursor-in", cur, "--trace-out", os.path.join(d, "control_trace.jsonl"),
                                  "--load-report-out", os.path.join(d, "control_load_report.json")]))
        sh([VERIFIER, "evidence-hashes", "--dir", cd, "--extra", cur, "--out", after])
        if rc1 != 0 or rc2 != 0:
            results[cid] = {"verdict": "FAIL", "why": "reader rc=%d/%d" % (rc1, rc2)}
            continue
        rc, _, _ = sh(verifier(a, "verify-cr", ["--id", cid, "--cursor", cur, "--load-report", os.path.join(d, "load_report.json"),
                                                "--trace", os.path.join(d, "trace.jsonl"), "--control", os.path.join(d, "control_trace.jsonl"),
                                                "--clean-dir", cd, "--evidence-before", before, "--evidence-after", after],
                               os.path.join(d, "result.json")))
        results[cid] = {"verdict": jread(os.path.join(d, "result.json"))["verdict"], "verifier_rc": rc}
    write_once(os.path.join(ev, "negatives_result.json"), canon(results))
    vs = {v["verdict"] for v in results.values()}
    return ("PASS" if vs == {"PASS"} else ("BLOCKED" if "BLOCKED" in vs else "FAIL")), results


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=("clean", "negatives", "all"))
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--mode", choices=("real", "selftest"), required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--source", required=True)
    ap.add_argument("--tokenizer", required=True)
    a = ap.parse_args(argv)
    ev = os.path.join(a.workdir, "evidence")
    decision = {"driver": "d1_driver/1", "mode": a.mode,
                "d1_experiment": a.mode == "real",
                "note": "mode=selftest is a code self-test on synthetic data and is NOT D1 evidence",
                "declared": "script output only; D1 is never PASS/CLOSED without independent ChatGPT review and owner authorization"}
    code = 0
    if a.cmd in ("clean", "all"):
        v, why = do_clean(a)
        decision["read_resume"] = {"verdict": v, "why": why}
        code = 0 if v == "PASS" else 1
    if a.cmd in ("negatives", "all") and code == 0:
        v, res = do_negatives(a)
        decision["negatives_meta"] = {"verdict": v, "items": res}
        code = 0 if v == "PASS" else 1
    decision["steps"] = LOG
    write_once(os.path.join(ev, "D1_DECISION_%s.json" % a.cmd), canon(decision))
    print(json.dumps({k: decision[k] for k in decision if k in ("read_resume", "negatives_meta")}, sort_keys=True)[:3000])
    return code


if __name__ == "__main__":
    sys.exit(main())
