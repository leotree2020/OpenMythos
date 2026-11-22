"""R8-7: general-text sources (DATA_MANIFEST general_text): file sha256 of the parcae tokenizer.json and of
research/mini_mythos/stage1/results/r1/eval_sets.jsonl. Data Auditor's own script; no Executor code is imported,
called or copied. Exceptions -> RESULT: FAIL (r6_guard).

eval_sets.jsonl is only hashed as a whole file (sha256 and git blob sha1 over the raw bytes, read in 1 MiB chunks);
no line is split, parsed, decoded, counted or otherwise used (protocol section 3, definition of reading TEST data).
  a. parcae tokenizer.json (downloaded by r8_fetch.py at SandyResearch/parcae-tokenizer@6247b5d0...) sha256 ==
     general_text.decode_tokenizer_json_sha256 of the freeze commit;
  b. eval_sets.jsonl: sha256 of the working-tree bytes, of the blob at the freeze commit and of the blob at the
     Metrix base commit 61d3c767 == general_text.source_file_sha256; the path is unchanged between base and freeze;
  c. the abbreviations in protocol 2.7 are prefix...suffix of the two full values; decode_with names the pinned
     parcae revision; Stage 1's own records (data_lock.json tokenizer_sha256, manifest.json eval_sets.jsonl entry)
     are printed for cross-reference (these two files are not TEST data).
Prints AUDIT_VALUE lines.
usage: python -I r8_general.py <repo_root> <commit> <parcae_tokenizer.json>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hashlib, json, re, subprocess
from r6_guard import run

BASE = "61d3c76705b28cc2ee334abc5bf1baaac4fc30dc"
EV = "research/mini_mythos/stage1/results/r1/eval_sets.jsonl"
PARCAE_REV = "SandyResearch/parcae-tokenizer@6247b5d0592876b73660f34c2dd16c9db9e9045c"


def git(repo, *a, check=True):
    r = subprocess.run(["git", "-C", repo, *a], capture_output=True)
    if check and r.returncode != 0:
        raise RuntimeError("git %s failed: %r" % (a, r.stderr))
    return r


def whole_file(path):
    h, n = hashlib.sha256(), os.path.getsize(path)
    g = hashlib.sha1(b"blob %d\0" % n)
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk); g.update(chunk)
    return n, h.hexdigest(), g.hexdigest()


def blob_sha256(repo, rev, path):
    p = subprocess.Popen(["git", "-C", repo, "cat-file", "blob", f"{rev}:{path}"], stdout=subprocess.PIPE)
    h, n = hashlib.sha256(), 0
    for chunk in iter(lambda: p.stdout.read(1 << 20), b""):
        h.update(chunk); n += len(chunk)
    assert p.wait() == 0
    return n, h.hexdigest()


def main():
    repo, commit, ptok = sys.argv[1:4]
    ok = True
    dm = json.loads(git(repo, "cat-file", "blob", f"{commit}:metrix/e1-pilot/DATA_MANIFEST.json").stdout)
    proto = git(repo, "cat-file", "blob", f"{commit}:metrix/e1-pilot/METRIX_E1_PROTOCOL.md").stdout.decode("utf-8")
    gt = dm["general_text"]
    print("freeze-commit general_text.source_file          :", gt["source_file"])
    print("freeze-commit general_text.source_file_sha256   :", gt["source_file_sha256"])
    print("freeze-commit general_text.decode_with          :", gt["decode_with"])
    print("freeze-commit general_text.decode_tokenizer_json_sha256:", gt["decode_tokenizer_json_sha256"])
    ok &= gt["source_file"] == EV and gt["decode_with"].startswith(PARCAE_REV)

    print("\n== a. parcae tokenizer.json")
    n, h, b = whole_file(ptok)
    m = h == gt["decode_tokenizer_json_sha256"]
    print(f"  {ptok}: bytes {n} | sha256 {h} | git blob {b} | manifest {gt['decode_tokenizer_json_sha256']} | MATCH {m}")
    print(f"AUDIT_VALUE parcae_tokenizer_json_sha256 {h}")
    ok &= m

    print("\n== b. eval_sets.jsonl (whole-file hashes only)")
    ls = git(repo, "ls-files", "-s", "--", EV).stdout.decode().strip()
    print("  git ls-files -s:", ls)
    n, h, b = whole_file(os.path.join(repo, EV))
    nb, hb = blob_sha256(repo, commit, EV)
    n0, h0 = blob_sha256(repo, BASE, EV)
    bid_c = git(repo, "rev-parse", f"{commit}:{EV}").stdout.decode().strip()
    bid_0 = git(repo, "rev-parse", f"{BASE}:{EV}").stdout.decode().strip()
    diffq = git(repo, "diff", "--quiet", BASE, commit, "--", EV, check=False).returncode
    wtq = git(repo, "diff", "--quiet", commit, "--", EV, check=False).returncode
    print(f"  working tree : bytes {n} | sha256 {h} | git blob {b}")
    print(f"  {commit[:8]} blob: bytes {nb} | sha256 {hb} | blob id {bid_c}")
    print(f"  base {BASE[:8]} blob: bytes {n0} | sha256 {h0} | blob id {bid_0}")
    print(f"  git diff --quiet base..freeze exit {diffq} | working tree vs freeze exit {wtq}")
    m = h == hb == h0 == gt["source_file_sha256"] and b == bid_c == bid_0 and diffq == 0 and wtq == 0
    print(f"  manifest {gt['source_file_sha256']} | MATCH {m}")
    print(f"AUDIT_VALUE eval_sets_jsonl_sha256 {h}")
    ok &= m

    print("\n== c. protocol 2.7 abbreviations and Stage 1 records")
    for full in (gt["source_file_sha256"], gt["decode_tokenizer_json_sha256"]):
        ab = f"{full[:8]}…{full[-4:]}"
        found = ab in proto
        print(f"  abbreviation {ab} in protocol: {found}")
        ok &= found
    s1 = "research/mini_mythos/stage1/results/r1/"
    for name in ("data_lock.json", "manifest.json"):
        r = git(repo, "cat-file", "blob", f"{commit}:{s1}{name}", check=False)
        if r.returncode != 0:
            print(f"  {s1}{name}: not in the commit")
            continue
        txt = r.stdout.decode("utf-8")
        hits = sorted(set(re.findall(r"[0-9a-f]{64}", txt)) & {gt["source_file_sha256"], gt["decode_tokenizer_json_sha256"]})
        print(f"  {s1}{name}: contains manifest values {hits}")
    return ok


run(main)
