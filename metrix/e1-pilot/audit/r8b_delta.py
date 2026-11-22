"""R8b-D: what changed between the superseded freeze candidate 92df1a60 (audited earlier, stdout/92df1a60.../) and the
freeze commit under audit, as far as the frozen hashes are concerned. Data Auditor's own script; no Executor code is
imported, called or copied (the Executor's delta file reviews/<commit>/delta_vs_92df1a60.diff is NOT read; the delta
is recomputed from git objects). Standard library + git only. Exceptions -> RESULT: FAIL (r6_guard).

  a. both commits exist, have the same single parent, and the files that differ between them (git diff --name-status);
  b. DATA_MANIFEST.json and SEARCH_SPACE.json: blob ids identical in both commits;
  c. SPLIT_MANIFEST.json: parsed JSON of the new commit with candidates.pool_too_small removed == parsed JSON of the
     old commit (i.e. the only JSON-level change is that one added key); key order of "candidates" printed;
  d. every 64-hex value in the two manifests (data hashes) is the same set in both commits;
  e. METRIX_E1_PROTOCOL.md: changed lines (unified diff, 0 context) and the section ("## " heading) each change
     falls in; the sentences that carry data hash values (2.2 facts, 2.5 candidates, 2.6 train_S, 2.7 abbreviations)
     are unchanged;
  f. the Executor raw outputs t0_env.txt and t1d_data_hashes.txt: blob ids identical in both commits (so the data
     recomputation they record is the same one audited before); t1_protocol_checks.txt changed (rerun);
  g. informational: the untracked working-tree file metrix/e1-pilot/PROTOCOL_FROZEN (if present): which commit hash
     it names, and whether its four file sha256 values are those of <new> or of <old>. It is read as text only.
PASS iff a (changed files within the expected set), b, c, d, e (hash sentences unchanged), f hold.
usage: python -I r8b_delta.py <repo_root> <old_commit> <new_commit>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hashlib, json, re, subprocess
from r6_guard import run

D = "metrix/e1-pilot/"
EXPECTED_CHANGED = {D + "METRIX_E1_PROTOCOL.md", D + "SPLIT_MANIFEST.json", D + "reports/round8/t1_protocol_checks.txt",
                    D + "tasks/ROUND8_TASKS.md"}


def git(repo, *a, check=True):
    r = subprocess.run(["git", "-C", repo, *a], capture_output=True)
    if check and r.returncode != 0:
        raise RuntimeError("git %s failed: %r" % (a, r.stderr))
    return r


def blob(repo, c, p):
    return git(repo, "cat-file", "blob", f"{c}:{p}").stdout


def main():
    repo, old, new = sys.argv[1:4]
    ok = True
    old = git(repo, "rev-parse", old + "^{commit}").stdout.decode().strip()
    new = git(repo, "rev-parse", new + "^{commit}").stdout.decode().strip()
    po = git(repo, "log", "-1", "--format=%P", old).stdout.decode().split()
    pn = git(repo, "log", "-1", "--format=%P", new).stdout.decode().split()
    print("old", old, "parents", po)
    print("new", new, "parents", pn)
    same_parent = len(po) == 1 and po == pn
    print("same single parent:", same_parent)
    ok &= same_parent
    anc = git(repo, "merge-base", "--is-ancestor", old, new, check=False).returncode == 0
    print("old is an ancestor of new (expected False, old was superseded):", anc)

    print("\n== a. files that differ old..new")
    ns = git(repo, "diff", "--name-status", old, new).stdout.decode().strip().splitlines()
    for l in ns:
        print("  ", l)
    changed = {l.split("\t", 1)[1] for l in ns}
    print("changed set == expected {protocol, SPLIT_MANIFEST, t1_protocol_checks, ROUND8_TASKS}:", changed == EXPECTED_CHANGED)
    ok &= changed == EXPECTED_CHANGED

    print("\n== b. byte identity of DATA_MANIFEST.json and SEARCH_SPACE.json")
    for name in ("DATA_MANIFEST.json", "SEARCH_SPACE.json"):
        bo = git(repo, "rev-parse", f"{old}:{D}{name}").stdout.decode().strip()
        bn = git(repo, "rev-parse", f"{new}:{D}{name}").stdout.decode().strip()
        print(f"  {name}: blob old {bo} | new {bn} | identical {bo == bn} | sha256 new {hashlib.sha256(blob(repo, new, D + name)).hexdigest()}")
        ok &= bo == bn

    print("\n== c. SPLIT_MANIFEST.json: JSON-level difference")
    so = json.loads(blob(repo, old, D + "SPLIT_MANIFEST.json"))
    sn = json.loads(blob(repo, new, D + "SPLIT_MANIFEST.json"))
    added = sn["candidates"].get("pool_too_small")
    print("  new candidates.pool_too_small:", added)
    print("  old has candidates.pool_too_small:", "pool_too_small" in so["candidates"])
    print("  new candidates key order:", list(sn["candidates"]))
    sn2 = json.loads(blob(repo, new, D + "SPLIT_MANIFEST.json"))
    del sn2["candidates"]["pool_too_small"]
    eq = sn2 == so
    print("  new minus candidates.pool_too_small == old (parsed JSON):", eq)
    ok &= eq and isinstance(added, str) and "pool_too_small" not in so["candidates"]
    rd = json.dumps(sn, indent=2, ensure_ascii=False) + "\n"
    print("  new file == json.dumps(indent=2, ensure_ascii=False) + newline:", rd.encode("utf-8") == blob(repo, new, D + "SPLIT_MANIFEST.json"))

    print("\n== d. 64-hex values in the two manifests")
    for name in ("DATA_MANIFEST.json", "SPLIT_MANIFEST.json"):
        ho = set(re.findall(r"[0-9a-f]{64}", blob(repo, old, D + name).decode("utf-8")))
        hn = set(re.findall(r"[0-9a-f]{64}", blob(repo, new, D + name).decode("utf-8")))
        print(f"  {name}: old {len(ho)} distinct | new {len(hn)} distinct | same set {ho == hn}")
        ok &= ho == hn

    print("\n== e. METRIX_E1_PROTOCOL.md changed lines")
    po_txt = blob(repo, old, D + "METRIX_E1_PROTOCOL.md").decode("utf-8")
    pn_txt = blob(repo, new, D + "METRIX_E1_PROTOCOL.md").decode("utf-8")
    heads_new = [(i + 1, l) for i, l in enumerate(pn_txt.splitlines()) if l.startswith("## ")]
    heads_old = [(i + 1, l) for i, l in enumerate(po_txt.splitlines()) if l.startswith("## ") or l.startswith("### ")]

    def section(lines_heads, n):
        s = None
        for ln, h in lines_heads:
            if ln <= n:
                s = h
        return s

    heads_new_all = [(i + 1, l) for i, l in enumerate(pn_txt.splitlines()) if l.startswith("## ") or l.startswith("### ")]
    diff = git(repo, "diff", "-U0", old, new, "--", D + "METRIX_E1_PROTOCOL.md").stdout.decode("utf-8")
    hunks = re.findall(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", diff, flags=re.M)
    print("  hunks:", len(hunks))
    for a, b, c, d in hunks:
        b = 1 if b == "" else int(b)
        d = 1 if d == "" else int(d)
        where_new = section(heads_new_all, int(c)) if d else None
        where_old = section(heads_old, int(a)) if b else None
        print(f"   -{a},{b} +{c},{d} | section (new) {where_new!r} | section (old) {where_old!r}")
    minus = [l for l in diff.splitlines() if l.startswith("-") and not l.startswith("---")]
    plus = [l for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++")]
    print("  removed lines", len(minus), "| added lines", len(plus))
    hex_removed = sorted({h for l in minus for h in re.findall(r"[0-9a-f]{64}", l)})
    hex_added = sorted({h for l in plus for h in re.findall(r"[0-9a-f]{64}", l)})
    print("  64-hex values on removed lines:", hex_removed, "| on added lines:", hex_added)
    ok &= not hex_removed and not hex_added
    pats = [r"规范化 SHA-256 必须等于 `([0-9a-f]{64})`。参考实现 `reports/round2/names.py`",
            r"`candidates\.json` 的规范化 SHA-256 必须等于 `([0-9a-f]{64})`",
            r"`train_S\.jsonl` 的规范化 SHA-256 必须等于 `([0-9a-f]{64})`"]
    for p in pats:
        mo, mn = re.search(p, po_txt), re.search(p, pn_txt)
        same = bool(mo and mn) and mo.group(0) == mn.group(0)
        print(f"  hash sentence {p[:40]!r}...: old {mo and mo.group(1)} | new {mn and mn.group(1)} | unchanged {same}")
        ok &= same
    ab_o = sorted(set(re.findall(r"[0-9a-f]{8}…[0-9a-f]{4}", po_txt)))
    ab_n = sorted(set(re.findall(r"[0-9a-f]{8}…[0-9a-f]{4}", pn_txt)))
    print("  abbreviated hashes (8…4) old == new:", ab_o == ab_n, "| new:", ab_n)
    ok &= ab_o == ab_n
    st = [l for l in pn_txt.splitlines() if l.startswith("| 状态")]
    print("  new status line:", st)
    new_sentence = "干扰项的池少于 4 个答案即 IMPLEMENTATION_FAIL,不生成合成干扰项。"
    print("  new 2.5 sentence present:", new_sentence in pn_txt, "| section:",
          section(heads_new_all, next((i + 1 for i, l in enumerate(pn_txt.splitlines()) if new_sentence in l), 0)))

    print("\n== f. Executor raw outputs in both commits")
    for name in ("t0_env.txt", "t1d_data_hashes.txt", "t1_protocol_checks.txt", "t0_copy_check.txt"):
        p = D + "reports/round8/" + name
        bo = git(repo, "rev-parse", f"{old}:{p}").stdout.decode().strip()
        bn = git(repo, "rev-parse", f"{new}:{p}").stdout.decode().strip()
        print(f"  {name}: old blob {bo} | new blob {bn} | identical {bo == bn}")
        if name in ("t0_env.txt", "t1d_data_hashes.txt"):
            ok &= bo == bn

    print("\n== g. informational: untracked working-tree PROTOCOL_FROZEN")
    pf = os.path.join(repo, D, "PROTOCOL_FROZEN")
    in_new = git(repo, "cat-file", "-e", f"{new}:{D}PROTOCOL_FROZEN", check=False).returncode == 0
    tracked = git(repo, "ls-files", "--error-unmatch", D + "PROTOCOL_FROZEN", check=False).returncode == 0
    print("  in new commit:", in_new, "| tracked in index:", tracked, "| exists in working tree:", os.path.exists(pf))
    if os.path.exists(pf):
        t = open(pf, encoding="utf-8").read()
        commits = sorted(set(re.findall(r"\b[0-9a-f]{40}\b", t)))
        print("  40-hex values named:", commits)
        print("  names new commit:", new in t, "| names old commit:", old in t)
        for name in ("METRIX_E1_PROTOCOL.md", "DATA_MANIFEST.json", "SPLIT_MANIFEST.json", "SEARCH_SPACE.json"):
            m = re.search(r"([0-9a-f]{64})  metrix/e1-pilot/" + re.escape(name), t)
            v = m.group(1) if m else None
            hn = hashlib.sha256(blob(repo, new, D + name)).hexdigest()
            ho = hashlib.sha256(blob(repo, old, D + name)).hexdigest()
            print(f"  {name}: PROTOCOL_FROZEN value {v} | == sha256@new {v == hn} | == sha256@old {v == ho}")
    return ok


run(main)
