"""R9-1: protocol v1.1 freeze commit - file-byte sha256 of the protocol and the three JSON, identity of the working
tree with the commit, comparison with the Executor's t5 output, and the v1 -> v1.1 difference of the three JSON.
Data Auditor's own script (round 9 item 5); no Executor code is imported, called or copied (in particular not
reports/round9/v11_checks.py, which was not opened). The Executor's t5 file is read as text only (regular
expressions over its printed lines). Exceptions -> RESULT: FAIL (r6_guard).

For each of METRIX_E1_PROTOCOL.md, DATA_MANIFEST.json, SPLIT_MANIFEST.json, SEARCH_SPACE.json (metrix/e1-pilot/):
  a. bytes of `git cat-file blob <commit>:<path>` and of `git show <commit>:<path>` (identical), size, sha256, git blob
     id recomputed from the bytes == `git rev-parse <commit>:<path>`;
  b. working-tree bytes == (a); HEAD blob == (a); `git diff --quiet <commit> -- <path>` exit 0; gitattributes;
  c. the same for the v1 freeze commit, compared with the sha256 block of metrix/e1-pilot/PROTOCOL_FROZEN
     (read from the commit under audit and from the working tree; both must be identical);
  d. Executor t5_frozen_hashes_<commit[:8]>.txt (working tree, untracked): its "<sha256>  <path>" lines for the
     commit under audit and its "(v1 freeze commit ...)" lines == (a) / (c).
For each JSON: parsed with duplicate-key detection; recursive structural diff v1 -> v1.1 (dict keys, key order, list
items, value types and values) must be exactly [/version: "v1" -> "v1.1"]; byte check: v1 bytes with the single
occurrence of '"version": "v1",' replaced by '"version": "v1.1",' == v1.1 bytes; status / frozen unchanged.
Informational: protocol line diff v1 -> v1.1 (counts only), every 64-hex string of the v1 protocol still present in
v1.1 and no new 64-hex value introduced; the section-7 inline copy of SEARCH_SPACE.json == the file (parsed).
Prints "AUDIT_VALUE file_sha256:<name> <sha256>" and "AUDIT_VALUE v1_file_sha256:<name> <sha256>" lines.
PASS iff a, b, c, d hold and each JSON differs from v1 only in version v1 -> v1.1.
usage: python -I r9_files.py <repo_root> <commit> <expected_parent_prefix> <v1_commit> <executor_t5_file>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import difflib, hashlib, json, re, subprocess
from r6_guard import run

FILES = ["METRIX_E1_PROTOCOL.md", "DATA_MANIFEST.json", "SPLIT_MANIFEST.json", "SEARCH_SPACE.json"]
D = "metrix/e1-pilot/"


def git(repo, *a, check=True):
    r = subprocess.run(["git", "-C", repo, *a], capture_output=True)
    if check and r.returncode != 0:
        raise RuntimeError("git %s failed: %r" % (a, r.stderr))
    return r


def sha(b):
    return hashlib.sha256(b).hexdigest()


def strict_json(b):
    def hook(pairs):
        keys = [k for k, _ in pairs]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate keys: %r" % sorted(k for k in set(keys) if keys.count(k) > 1))
        return dict(pairs)
    return json.loads(b.decode("utf-8"), object_pairs_hook=hook)


def jdiff(a, b, path=""):
    out = []
    if type(a) is not type(b):
        return [(path or "/", "type", type(a).__name__, type(b).__name__)]
    if isinstance(a, dict):
        if list(a) != list(b) and set(a) == set(b):
            out.append((path or "/", "key order", list(a), list(b)))
        for k in a:
            if k not in b:
                out.append((f"{path}/{k}", "removed", a[k], None))
        for k in b:
            if k not in a:
                out.append((f"{path}/{k}", "added", None, b[k]))
        for k in a:
            if k in b:
                out += jdiff(a[k], b[k], f"{path}/{k}")
        return out
    if isinstance(a, list):
        if len(a) != len(b):
            out.append((path, "list length", len(a), len(b)))
        for i, (x, y) in enumerate(zip(a, b)):
            out += jdiff(x, y, f"{path}[{i}]")
        return out
    if a != b:
        out.append((path, "value", a, b))
    return out


def main():
    repo, commit, parent_prefix, v1, t5path = sys.argv[1:6]
    ok = True
    full = git(repo, "rev-parse", commit + "^{commit}").stdout.decode().strip()
    v1 = git(repo, "rev-parse", v1 + "^{commit}").stdout.decode().strip()
    head = git(repo, "rev-parse", "HEAD").stdout.decode().strip()
    meta = git(repo, "log", "-1", "--format=%H%n%P%n%aI%n%cI%n%s", full).stdout.decode().splitlines()
    print("commit", full, "| parents", meta[1], "| author date", meta[2], "| committer date", meta[3])
    print("subject:", meta[4])
    print("HEAD", head, "| HEAD == commit", head == full)
    ok &= head == full
    pars = meta[1].split()
    par_ok = len(pars) == 1 and pars[0].startswith(parent_prefix)
    print("single parent starting with", parent_prefix, ":", par_ok)
    ok &= par_ok
    print("v1 freeze commit", v1, "| ancestor of commit:",
          git(repo, "merge-base", "--is-ancestor", v1, full, check=False).returncode == 0)
    changed = git(repo, "diff", "--name-status", v1, full, "--", *[D + f for f in FILES]).stdout.decode().strip()
    print("git diff --name-status v1..commit (the four files):", changed.replace("\n", " ; "))
    touched = git(repo, "log", "--format=%H", f"{v1}..{full}", "--", *[D + f for f in FILES]).stdout.decode().split()
    print("commits after v1 that touch the four files:", touched, "| only the commit under audit:", touched == [full])
    ok &= touched == [full]

    # PROTOCOL_FROZEN (v1 block) from the commit and from the working tree
    pf_c = git(repo, "cat-file", "blob", f"{full}:{D}PROTOCOL_FROZEN").stdout
    pf_w = open(os.path.join(repo, D, "PROTOCOL_FROZEN"), "rb").read()
    print("PROTOCOL_FROZEN: commit blob sha256", sha(pf_c), "| working tree identical:", pf_c == pf_w)
    ok &= pf_c == pf_w
    pf_text = pf_c.decode("utf-8")
    pf_commit = re.search(r"\| 冻结提交\(完整 hash\) \| `([0-9a-f]{40})` \|", pf_text)
    print("PROTOCOL_FROZEN names v1 freeze commit:", pf_commit and pf_commit.group(1), "| == v1:", bool(pf_commit) and pf_commit.group(1) == v1)
    ok &= bool(pf_commit) and pf_commit.group(1) == v1
    pf_files = dict((p, h) for h, p in re.findall(r"^([0-9a-f]{64})  (metrix/e1-pilot/\S+)$", pf_text, flags=re.M))
    print("PROTOCOL_FROZEN file-sha256 lines:", len(pf_files))

    t5 = open(t5path, encoding="utf-8").read() if os.path.exists(t5path) else ""
    print("Executor t5 file:", t5path, "| present:", bool(t5), "| sha256", sha(t5.encode("utf-8")) if t5 else None)
    ok &= bool(t5)
    ex_new = re.findall(r"^([0-9a-f]{64})  (metrix/e1-pilot/\S+)$", t5, flags=re.M)
    ex_v1 = re.findall(r"^([0-9a-f]{64})  (metrix/e1-pilot/\S+) \(v1 freeze commit ([0-9a-f]{8})\)$", t5, flags=re.M)
    print("Executor t5 lines: commit-under-audit", len(ex_new), "| v1", len(ex_v1))

    blobs = {}
    for name in FILES:
        path = D + name
        b_cat = git(repo, "cat-file", "blob", f"{full}:{path}").stdout
        b_show = git(repo, "show", f"{full}:{path}").stdout
        blob_id = git(repo, "rev-parse", f"{full}:{path}").stdout.decode().strip()
        my_blob = hashlib.sha1(b"blob %d\0" % len(b_cat) + b_cat).hexdigest()
        b_head = git(repo, "cat-file", "blob", f"HEAD:{path}").stdout
        b_wt = open(os.path.join(repo, path), "rb").read()
        diffq = git(repo, "diff", "--quiet", full, "--", path, check=False).returncode
        attrs = git(repo, "check-attr", "-a", "--", path).stdout.decode().strip() or "(no attributes)"
        v1b = git(repo, "cat-file", "blob", f"{v1}:{path}").stdout
        h, hv1 = sha(b_cat), sha(v1b)
        blobs[name] = (v1b, b_cat)
        same = b_show == b_cat and b_wt == b_cat and b_head == b_cat and my_blob == blob_id and diffq == 0
        exn = [x for x, p in ex_new if p == path]
        exv = [x for x, p, c in ex_v1 if p == path and v1.startswith(c)]
        pfv = pf_files.get(path)
        e_ok = len(exn) >= 1 and all(x == h for x in exn)
        v_ok = pfv == hv1 and len(exv) >= 1 and all(x == hv1 for x in exv)
        ok &= same and e_ok and v_ok
        print(f"== {path}")
        print(f"   {full[:8]} blob: bytes {len(b_cat)} | sha256 {h} | git blob id {blob_id} (recomputed {my_blob})")
        print(f"   git show bytes == cat-file bytes: {b_show == b_cat} | working tree bytes {len(b_wt)} sha256 {sha(b_wt)} "
              f"== blob: {b_wt == b_cat} | HEAD blob == blob: {b_head == b_cat} | git diff --quiet exit {diffq}")
        print(f"   gitattributes: {attrs}")
        print(f"   Executor t5 value(s) {sorted(set(exn))} | == auditor: {e_ok}")
        print(f"   v1 {v1[:8]} blob: bytes {len(v1b)} | sha256 {hv1} | PROTOCOL_FROZEN {pfv} | Executor t5 v1 {sorted(set(exv))} "
              f"| all equal: {v_ok}")
        print(f"   v1.1 bytes == v1 bytes: {b_cat == v1b} (must be False: the version changed)")
        ok &= b_cat != v1b
        print(f"AUDIT_VALUE file_sha256:{name} {h}")
        print(f"AUDIT_VALUE v1_file_sha256:{name} {hv1}")
    extra_ex = sorted({p for _, p in ex_new} - {D + f for f in FILES})
    print("Executor t5 file-sha256 paths outside the four files (not audited here):", extra_ex)

    print("\n== the three JSON: v1 -> v1.1")
    for name in FILES[1:]:
        v1b, nb = blobs[name]
        a, b = strict_json(v1b), strict_json(nb)
        d = jdiff(a, b)
        only = d == [("/version", "value", "v1", "v1.1")]
        print(f"-- {name}: parsed without duplicate keys | structural differences: {d} | only /version v1 -> v1.1: {only}")
        pat_old, pat_new = b'"version": "v1",', b'"version": "v1.1",'
        n_old = v1b.count(pat_old)
        repl = v1b.replace(pat_old, pat_new, 1) == nb
        print(f"   v1 bytes contain {pat_old.decode()!r} {n_old} time(s); replacing it by {pat_new.decode()!r} gives the "
              f"v1.1 bytes exactly: {repl} | v1.1 contains {pat_new.decode()!r} {nb.count(pat_new)} time(s)")
        ld = [l for l in difflib.unified_diff(v1b.decode("utf-8").splitlines(), nb.decode("utf-8").splitlines(), "v1", "v1.1", n=0, lineterm="")]
        print("   line diff:", ld)
        print(f"   status v1 {a.get('status')!r} -> v1.1 {b.get('status')!r} | frozen v1 {a.get('frozen')!r} -> v1.1 {b.get('frozen')!r} "
              f"| protocol {b.get('protocol')!r}")
        ok &= only and n_old == 1 and repl and a.get("status") == b.get("status") == "PROTOCOL_FROZEN" and a.get("frozen") == b.get("frozen")

    print("\n== protocol v1 -> v1.1 (informational except the hash-value check)")
    pv1, pv11 = (x.decode("utf-8") for x in blobs["METRIX_E1_PROTOCOL.md"])
    sm = difflib.SequenceMatcher(None, pv1.splitlines(), pv11.splitlines(), autojunk=False)
    ops = [(t, i2 - i1, j2 - j1, i1 + 1, j1 + 1) for t, i1, i2, j1, j2 in sm.get_opcodes() if t != "equal"]
    print("non-equal line blocks (tag, v1 lines, v1.1 lines, v1 start, v1.1 start):", ops)
    hx1, hx11 = set(re.findall(r"(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])", pv1)), set(re.findall(r"(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])", pv11))
    print(f"distinct 64-hex values: v1 {len(hx1)} | v1.1 {len(hx11)} | in v1 not in v1.1 {sorted(hx1 - hx11)} | new in v1.1 {sorted(hx11 - hx1)}")
    ok &= not (hx1 - hx11) and not (hx11 - hx1)
    m = re.search(r"<!-- BEGIN INLINE COPY: SEARCH_SPACE\.json -->\n```json\n(.*?)\n```\n<!-- END INLINE COPY: SEARCH_SPACE\.json -->", pv11, flags=re.S)
    if m:
        inl = strict_json(m.group(1).encode("utf-8"))
        ssf = strict_json(blobs["SEARCH_SPACE.json"][1])
        print("section-7 inline copy of SEARCH_SPACE.json parses; == SEARCH_SPACE.json (parsed):", inl == ssf,
              "| text == file text (trailing newline stripped):", m.group(1) == blobs["SEARCH_SPACE.json"][1].decode("utf-8").rstrip("\n"),
              "| inline version:", inl.get("version"))
    else:
        print("section-7 inline copy: markers / fence not found with the expected layout")
    return ok


run(main)
