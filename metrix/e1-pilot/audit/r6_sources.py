"""R6-D (round 6, item 1h): DATA_MANIFEST.json locks the sha256 of eval_sets.jsonl and of the parcae tokenizer.json.
Data Auditor's own script; no Executor code is imported, called or copied. Exceptions -> RESULT: FAIL (r6_guard).

Checks
  1. sha256 of the whole files (hashing a whole file is not "reading TEST data", protocol section 3, item 1g):
       eval_sets.jsonl       == DATA_MANIFEST general_text.source_file_sha256
       parcae tokenizer.json == DATA_MANIFEST general_text.decode_tokenizer_json_sha256
  2. cross-check with Stage 1's own records:
       research/mini_mythos/stage1/results/r1/manifest.json  key "eval_sets.jsonl"
       research/mini_mythos/stage1/results/r1/data_lock.json key "tokenizer_sha256"
     and git provenance of those Stage 1 files (tracked, working tree == HEAD object, last commit, untouched since
     the Metrix base commit 61d3c767).
  3. the manifest keys were added in this round (absent at f4d8e988, present at HEAD), the other general_text keys
     are unchanged, and the abbreviations in protocol section 2.7 are prefix...suffix of the full values.
usage: python -I r6_sources.py <repo_root> <eval_sets.jsonl> <parcae_tokenizer.json> [<old_rev> <new_rev>]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, re, subprocess
from common import sha
from r6_guard import run

BASE = "61d3c76705b28cc2ee334abc5bf1baaac4fc30dc"
R1 = "research/mini_mythos/stage1/results/r1/"


def git(repo, *a):
    return subprocess.check_output(["git", "-C", repo, *a])


def main():
    repo, ev, ptok = sys.argv[1:4]
    old_rev, new_rev = (sys.argv[4:6] if len(sys.argv) > 5 else
                        ("f4d8e988a31f99527cc0bc6be5ceacc709bda2f1", "599230f9e6069e8f7197a3717aafa789abb788f0"))
    ok = True
    dm = json.load(open(os.path.join(repo, "metrix/e1-pilot/DATA_MANIFEST.json"), encoding="utf-8"))
    gt = dm["general_text"]
    h_ev, h_pt = sha(open(ev, "rb").read()), sha(open(ptok, "rb").read())
    print("1. whole-file sha256")
    for label, got, key in (("eval_sets.jsonl", h_ev, "source_file_sha256"),
                            ("parcae tokenizer.json", h_pt, "decode_tokenizer_json_sha256")):
        m = got == gt.get(key)
        ok &= m
        print(f"   {label:22s} {got} | DATA_MANIFEST general_text.{key} {gt.get(key)} | equal {m}")
    print("   eval_sets.jsonl path given == DATA_MANIFEST general_text.source_file:",
          os.path.realpath(ev) == os.path.realpath(os.path.join(repo, gt["source_file"])))

    print("2. Stage 1 records")
    st_man = json.load(open(os.path.join(repo, R1 + "manifest.json"), encoding="utf-8"))
    st_lock = json.load(open(os.path.join(repo, R1 + "data_lock.json"), encoding="utf-8"))
    for label, rec, got in (("manifest.json[\"eval_sets.jsonl\"]", st_man.get("eval_sets.jsonl"), h_ev),
                            ("data_lock.json[\"tokenizer_sha256\"]", st_lock.get("tokenizer_sha256"), h_pt)):
        m = rec == got
        ok &= m
        print(f"   Stage 1 {label:34s} {rec} | == local file sha256 {m} | == DATA_MANIFEST {rec in (gt['source_file_sha256'], gt['decode_tokenizer_json_sha256'])}")
    for fn in ("eval_sets.jsonl", "manifest.json", "data_lock.json"):
        p = R1 + fn
        tracked = subprocess.run(["git", "-C", repo, "ls-files", "--error-unmatch", p], capture_output=True).returncode == 0
        b = open(os.path.join(repo, p), "rb").read()
        same_head = git(repo, "show", f"HEAD:{p}") == b
        same_base = git(repo, "show", f"{BASE}:{p}") == b
        last = git(repo, "log", "-1", "--format=%h %cI %s", "--", p).decode().strip()
        changed_since_base = git(repo, "diff", "--name-only", BASE, "HEAD", "--", p).decode().strip()
        ok &= tracked and same_head and same_base and not changed_since_base
        print(f"   {p}: sha256 {sha(b)} | tracked {tracked} | working tree == HEAD {same_head} | == base {BASE[:8]} {same_base} "
              f"| changed base..HEAD: {bool(changed_since_base)} | last commit {last}")

    print("3. manifest change and protocol abbreviations")
    old = json.loads(git(repo, "show", f"{old_rev}:metrix/e1-pilot/DATA_MANIFEST.json"))["general_text"]
    new = json.loads(git(repo, "show", f"{new_rev}:metrix/e1-pilot/DATA_MANIFEST.json"))["general_text"]
    added = sorted(set(new) - set(old)); removed = sorted(set(old) - set(new))
    changed = sorted(k for k in set(old) & set(new) if old[k] != new[k])
    print(f"   general_text keys {old_rev[:8]} -> {new_rev[:8]}: added {added} | removed {removed} | changed {changed}")
    ok &= {"source_file_sha256", "decode_tokenizer_json_sha256"} <= set(added) and not removed and not changed
    proto = open(os.path.join(repo, "metrix/e1-pilot/METRIX_E1_PROTOCOL.md"), encoding="utf-8").read()
    sec = proto.split("### 2.7")[1].split("### 2.8")[0]
    for full in (gt["source_file_sha256"], gt["decode_tokenizer_json_sha256"]):
        abbr = f"{full[:8]}…{full[-4:]}"
        found = abbr in sec
        others = [a for a in re.findall(r"([0-9a-f]{8})…([0-9a-f]{4})", sec)]
        ok &= found
        print(f"   protocol 2.7 contains `{abbr}`: {found} | all abbreviations in 2.7: {others}")
    print("   general_text now:", json.dumps(new, ensure_ascii=False))
    return bool(ok)


if __name__ == "__main__":
    run(main)
