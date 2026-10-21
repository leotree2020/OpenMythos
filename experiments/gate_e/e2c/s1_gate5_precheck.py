#!/usr/bin/env python3
"""
Read-only check before gate 5 (GATE 5 conditional GO on b72a404). Writes only
stage1/gate5_precheck.json; runs no job, changes no file.

    1  sensitive content: every original log and every decompressed log
       archive, and every other text record under stage1/ that is committed,
       searched for access tokens (GitHub, cloud, generic bearer / API keys),
       private-key blocks, passwords, credentials inside URLs, proxy
       credentials, environment-variable dumps and e-mail addresses
    2  integrity of the archives: original files, archives and both
       manifests agree one to one (sha256 and size), no file outside a
       manifest, every archive decompresses to its original
    3  core code sha256, lambda / lambda2, and every committed record of
       gates 1-4 unchanged (working tree equal to b72a404); the ignored
       originals equal their manifests
    4  the stage-1 ledger: total 11,735.693 s, 20 closed intervals, the 15 s supplement
"""

import glob
import gzip
import hashlib
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
S1 = os.path.join(HERE, "stage1")
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
APPROVED_HEAD = "b72a404971e671c17267638b52daedf045227613"
CORE = {"train_e2c.py": "83751ca2cbbc9da172b7b06dcd78bcd1cfdd51e3a4f1f427d5cd8297b024ad7b",
        "e2c_common.py": "8f694b5fe4174968aabe86187a1da4119205442688f48faabef6407410c70440",
        "d2c.py": "000d30cb155c3094ff00280556b435b0114767bffcdeaaa33f552caf50136ea9",
        "s1_gate4.py": "1c73baf576900487e62b5f8b6b6d91ab1fbbc8f2650080aa6de87c09afa9d5b8",
        "s1_budget.py": "2fc9af21a8987ab82dedb9292acb97ce66793a4b64b038ceb79f1b6c5e65a8df"}
PATTERNS = {
    "github_token": r"\b(gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})",
    "aws_key": r"\bAKIA[0-9A-Z]{16}\b",
    "google_api_key": r"\bAIza[0-9A-Za-z_\-]{30,}",
    "slack_token": r"\bxox[abpr]-[A-Za-z0-9-]{10,}",
    "anthropic_or_openai_key": r"\bsk-(ant-)?[A-Za-z0-9_\-]{20,}",
    "private_key_block": r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    "bearer_or_auth_header": r"(?i)(\bauthorization\s*[:=]\s*\S+|\bbearer\s+[A-Za-z0-9._~+/\-]{8,})",
    "password_assignment": r"(?i)\b(password|passwd|pwd|secret|api[_-]?key|access[_-]?token)\s*[:=]\s*\S{4,}",
    "credentials_in_url": r"[a-z][a-z0-9+.\-]*://[^/\s:@]+:[^/\s@]+@",
    "proxy_variable": r"(?i)\b(https?_proxy|no_proxy)\s*=",
    "env_dump_line": r"(?m)^(PATH|HOME|USER|HOSTNAME|PYTHONPATH|GIT_[A-Z_]+|ANTHROPIC_[A-Z_]+|GH_[A-Z_]+|GITHUB_[A-Z_]+)=",
    "email_address": r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b",
}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def scan(text):
    hits = {}
    for name, pat in PATTERNS.items():
        m = re.findall(pat, text)
        if m:
            hits[name] = len(m)
    return hits


SELFTEST = {"github_token": "token ghp_" + "A" * 36, "aws_key": "AKIA" + "B" * 16, "google_api_key": "AIza" + "c" * 35,
            "slack_token": "xoxb-1234567890-abc", "anthropic_or_openai_key": "sk-ant-" + "x" * 30,
            "private_key_block": "-----BEGIN RSA PRIVATE KEY-----", "bearer_or_auth_header": "Authorization: Bearer abcdefghijk",
            "password_assignment": "password=hunter2xyz", "credentials_in_url": "https://user:pa55@github.com/x",
            "proxy_variable": "HTTPS_PROXY=http://p", "env_dump_line": "PATH=/usr/bin", "email_address": "someone@example.com"}


def main():
    out = {"0_pattern_selftest": {k: k in scan(v) for k, v in SELFTEST.items()}}
    if not all(out["0_pattern_selftest"].values()):
        print("pattern self-test failed", out)
        sys.exit(3)
    # 1 sensitive content
    files = {}
    for p in glob.glob(os.path.join(S1, "**", "*"), recursive=True):
        rel = os.path.relpath(p, HERE)
        if (not os.path.isfile(p) or "/lfs_e1/" in p or p.endswith((".pt", ".lock")) or "/ckpt/" in p
                or "/r2ckpt/" in p or "/fresh/" in p):
            continue
        data = open(p, "rb").read()
        if p.endswith(".gz"):
            data = gzip.decompress(data)
        try:
            files[rel] = data.decode("utf-8")
        except UnicodeDecodeError:
            files[rel] = data.decode("latin-1")
    hits = {f: scan(t) for f, t in files.items()}
    hits = {f: h for f, h in hits.items() if h}
    # context of each hit kind (first occurrences), so a reviewer can judge false positives
    contexts = {}
    for f, h in hits.items():
        for name in h:
            m = re.search(PATTERNS[name], files[f])
            s = max(0, m.start() - 60)
            contexts.setdefault(name, []).append({"file": f, "context": files[f][s:m.end() + 60]})
    logs = [f for f in files if f.endswith(".log") or f.endswith(".log.gz")]
    out["1_sensitive"] = {"text_files_scanned": len(files), "of_which_logs_and_log_archives": len(logs),
                          "patterns": list(PATTERNS), "files_with_hits": hits,
                          "hit_contexts": {k: v[:5] for k, v in contexts.items()},
                          "pass": not hits}
    # 2 archives against manifests
    integ = {}
    for man_path in (os.path.join(S1, "gate4", "run_archive", "MANIFEST_SHA256.json"), os.path.join(S1, "log_archive", "MANIFEST_SHA256.json")):
        man = json.load(open(man_path))
        bad = []
        for x in man["files"]:
            o, a = os.path.join(HERE, x["original"]), os.path.join(HERE, x["archive"])
            ob, ab = open(o, "rb").read(), open(a, "rb").read()
            if not (sha(ob) == x["original_sha256"] and len(ob) == x["original_bytes"] and sha(ab) == x["archive_sha256"]
                    and len(ab) == x["archive_bytes"] and gzip.decompress(ab) == ob):
                bad.append(x["original"])
        adir = os.path.dirname(man_path)
        in_dir = sorted(f for f in os.listdir(adir) if f.endswith(".gz"))
        listed = sorted(os.path.basename(x["archive"]) for x in man["files"])
        integ[os.path.relpath(man_path, HERE)] = {"entries": len(man["files"]), "mismatches": bad,
                                                  "archives_not_in_manifest": sorted(set(in_dir) - set(listed)),
                                                  "manifest_entries_without_archive": sorted(set(listed) - set(in_dir))}
    all_logs = sorted(glob.glob(os.path.join(S1, "gate*", "logs", "*.log")) + glob.glob(os.path.join(S1, "*.log"))
                      + glob.glob(os.path.join(S1, "dev", "*.log")))
    log_man = json.load(open(os.path.join(S1, "log_archive", "MANIFEST_SHA256.json")))
    integ["logs_on_disk_not_in_manifest"] = sorted(set(os.path.relpath(p, HERE) for p in all_logs) - {x["original"] for x in log_man["files"]})
    runs_on_disk = sorted(os.path.relpath(p, HERE) for p in glob.glob(os.path.join(S1, "gate4", "runs", "*")))
    run_man = json.load(open(os.path.join(S1, "gate4", "run_archive", "MANIFEST_SHA256.json")))
    integ["gate4_runs_on_disk_not_in_manifest"] = sorted(set(runs_on_disk) - {x["original"] for x in run_man["files"]})
    out["2_archives"] = dict(integ, pass_=all(not v["mismatches"] and not v["archives_not_in_manifest"] and not v["manifest_entries_without_archive"]
                                               for k, v in integ.items() if isinstance(v, dict))
                             and not integ["logs_on_disk_not_in_manifest"] and not integ["gate4_runs_on_disk_not_in_manifest"])
    # 3 code, lambda, records
    sh = lambda *a: subprocess.run(a, cwd=ROOT, capture_output=True, text=True).stdout.strip()  # noqa: E731
    sel = json.load(open(os.path.join(S1, "gate4", "lambda_selected.json")))
    out["3_unchanged"] = {
        "head": sh("git", "rev-parse", "HEAD"), "remote": sh("git", "rev-parse", "origin/claude/openmythos-research"),
        "working_tree_changes": sh("git", "status", "--porcelain", "--untracked-files=no").splitlines(),
        "untracked_new_files": sh("git", "status", "--porcelain").splitlines(),
        "core_code_sha256_equal": {f: sha(open(os.path.join(HERE, f), "rb").read()) == h for f, h in CORE.items()},
        "lambda": sel["lambda"], "lambda2": sel["lambda2"],
        "lambda_as_approved": sel["lambda"] == {"openmythos": 0.1, "transformer": 1.0}
                              and sel["lambda2"] == {"openmythos": 0.1410908280349954, "transformer": 1.402479419033934},
        "tracked_files_differ_from_HEAD": sh("git", "diff", "--name-only", "HEAD", "--", "experiments/gate_e").splitlines(),
        "freeze_file_exists": os.path.exists(os.path.join(HERE, "e2c_workload_freeze.json"))}
    u = out["3_unchanged"]
    u["pass"] = (u["head"] == u["remote"] == APPROVED_HEAD and not u["working_tree_changes"] and all(u["core_code_sha256_equal"].values())
                 and u["lambda_as_approved"] and not u["tracked_files_differ_from_HEAD"] and not u["freeze_file_exists"])
    # 4 ledger
    led = json.load(open(os.path.join(S1, "budget_ledger_s1.json")))
    sys.path.insert(0, HERE)
    from s1_budget import union_seconds
    out["4_ledger"] = {"total_seconds": led["total_seconds"], "union_seconds": union_seconds(led["intervals"]),
                       "intervals": len(led["intervals"]), "open": [i["label"] for i in led["intervals"] if i["open"]],
                       "supplements": [(x["label"], x["seconds"]) for x in led.get("supplements", [])],
                       "closed_after_interruption_kept": len(led["closed_after_interruption"]),
                       "pass": abs(led["total_seconds"] - 11735.692931175232) < 1e-6 and len(led["intervals"]) == 20
                       and not any(i["open"] for i in led["intervals"])
                       and [(x["label"], x["seconds"]) for x in led.get("supplements", [])] == [("gate2_launch1_after_last_heartbeat", 15.0)]}
    out["pass"] = all(out["0_pattern_selftest"].values()) and out["1_sensitive"]["pass"] and out["2_archives"]["pass_"] and out["3_unchanged"]["pass"] and out["4_ledger"]["pass"]
    json.dump(out, open(os.path.join(S1, "gate5_precheck.json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps({"sensitive_hits": out["1_sensitive"]["files_with_hits"], "scanned": out["1_sensitive"]["text_files_scanned"],
                      "logs": out["1_sensitive"]["of_which_logs_and_log_archives"], "archives": out["2_archives"]["pass_"],
                      "unchanged": out["3_unchanged"]["pass"], "ledger": out["4_ledger"], "pass": out["pass"]}, indent=1))
    sys.exit(0 if out["pass"] else 3)


if __name__ == "__main__":
    main()
