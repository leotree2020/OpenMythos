"""R5-D: manifests and protocol text across the audited range (git objects read with `git show`).
- DATA_MANIFEST.json: every changed leaf key per commit and over the whole range (expected: only
  model.input_convention.em_generation); old / new value; every other leaf identical
- the new em_generation text vs the section-5 EM paragraph at HEAD (stop ids, skip_special_tokens, 16 tokens, context)
- SPLIT_MANIFEST.json / SEARCH_SPACE.json unchanged; SEARCH_SPACE inline copy equal; data-file hashes still null
- protocol: every changed line between base and head, labelled with the section heading it is in
- files changed in the range, and outside metrix/
usage: python -I r5_manifests.py <repo_root> <base_rev> <head_rev>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import difflib, json, re, subprocess
from common import sha

repo, base, head = sys.argv[1:4]
P = "metrix/e1-pilot/"


def git(*a):
    return subprocess.check_output(["git", "-C", repo, *a])


def show(rev, path):
    return git("show", f"{rev}:{path}")


def flat(o, p=""):
    out = {}
    if isinstance(o, dict):
        for k, v in o.items():
            out.update(flat(v, f"{p}.{k}" if p else k))
    else:
        out[p] = o
    return out


def leafdiff(a, b):
    return sorted([("added", k) for k in b.keys() - a.keys()] + [("removed", k) for k in a.keys() - b.keys()]
                  + [("changed", k) for k in a.keys() & b.keys() if a[k] != b[k]], key=lambda x: x[1])


revs = git("rev-list", "--reverse", f"{base}..{head}").decode().split()
print("commits in range:", [(r, git("log", "-1", "--format=%cI %s", r).decode().strip()) for r in revs])
print("== files changed in the range")
print(git("diff", "--name-status", base, head).decode().rstrip())
print("outside metrix/:", git("diff", "--name-status", base, head, "--", ".", ":(exclude)metrix").decode().rstrip() or "(none)")

print("== DATA_MANIFEST.json leaf diff")
prev = base
for r in revs:
    print(f"  {prev[:8]}..{r[:8]}:", leafdiff(flat(json.loads(show(prev, P + "DATA_MANIFEST.json"))), flat(json.loads(show(r, P + "DATA_MANIFEST.json")))))
    prev = r
A, B = flat(json.loads(show(base, P + "DATA_MANIFEST.json"))), flat(json.loads(show(head, P + "DATA_MANIFEST.json")))
tot = leafdiff(A, B)
print(f"  whole range {base[:8]}..{head[:8]}:", tot)
print("  only model.input_convention.em_generation changed:", tot == [("changed", "model.input_convention.em_generation")])
for kind, k in tot:
    print(f"  {kind} {k}\n     old: {json.dumps(A.get(k), ensure_ascii=False)}\n     new: {json.dumps(B.get(k), ensure_ascii=False)}")
print("  leaves:", len(B), "| leaves other than em_generation identical:",
      {k: v for k, v in A.items() if k != "model.input_convention.em_generation"} == {k: v for k, v in B.items() if k != "model.input_convention.em_generation"})
work = json.load(open(os.path.join(repo, P + "DATA_MANIFEST.json"), encoding="utf-8"))
print("  working tree == head:", flat(work) == B)
print("  data files:", {k: (v["status"], v["byte_sha256"], v["canonical_sha256"]) for k, v in work["files"].items()})
print("  expected_facts_canonical_sha256:", work["name_generation"]["expected_facts_canonical_sha256"])

proto = show(head, P + "METRIX_E1_PROTOCOL.md").decode("utf-8")
em_par = next(l for l in proto.split("\n") if l.startswith("**Free-generation exact match"))
em_new = B["model.input_convention.em_generation"]
print("== em_generation (head) vs protocol section 5 EM paragraph (head)")
for label, pat in (("stop id 151645", "151645"), ("stop id 151643", "151643"), ("skip_special_tokens=True", "skip_special_tokens=True"),
                   ("16 new tokens", "16"), ("context 'The answer is'", "The answer is"), ("greedy", "greedy|贪心")):
    print(f"  {label:26s} in manifest: {bool(re.search(pat, em_new))} | in protocol: {bool(re.search(pat, em_par))}")
row0 = next(l for l in proto.split("\n") if l.startswith("| 生成输入(EM)"))
print("  protocol section 0 row:", row0)

print("== SPLIT_MANIFEST.json / SEARCH_SPACE.json")
for fn in ("SPLIT_MANIFEST.json", "SEARCH_SPACE.json"):
    a, b = show(base, P + fn), show(head, P + fn)
    w = open(os.path.join(repo, P + fn), "rb").read()
    print(f"  {fn}: sha256 base {sha(a)} head {sha(b)} working {sha(w)} | base==head {a == b} | head==working {b == w}")
sm = json.loads(show(head, P + "SPLIT_MANIFEST.json"))
print("  split_sha256:", sm["split_sha256"], "| candidate_mapping_sha256:", sm["candidates"]["candidate_mapping_sha256"],
      "| template_set_sha256:", sm["template_freeze"]["template_set_sha256"])
print("  L6 entry:", json.dumps(sm["leakage_checks"].get("L6_general_text"), ensure_ascii=False))
blk = re.search(r"<!-- BEGIN INLINE COPY: SEARCH_SPACE.json -->\n```json\n(.*?)```\n<!-- END INLINE COPY: SEARCH_SPACE.json -->", proto, re.S)
ss = show(head, P + "SEARCH_SPACE.json").decode()
print("  SEARCH_SPACE inline copy: blocks", len(re.findall("BEGIN INLINE COPY: SEARCH_SPACE.json", proto)), "| text == file:", blk.group(1) == ss)

print("== protocol: changed lines base..head, with the section they are in")
pa = show(base, P + "METRIX_E1_PROTOCOL.md").decode("utf-8").split("\n")
pb = proto.split("\n")


def section_of(lines, i):
    for j in range(i, -1, -1):
        if re.match(r"#{2,3} ", lines[j]):
            return lines[j]
    return "(top)"


sm_ = difflib.SequenceMatcher(a=pa, b=pb, autojunk=False)
sections = set()
for tag, i1, i2, j1, j2 in sm_.get_opcodes():
    if tag == "equal":
        continue
    for i in range(i1, i2):
        s = section_of(pa, i); sections.add(s)
        print(f"  - [{s}] {pa[i][:220]}{' ...' if len(pa[i]) > 220 else ''}")
    for j in range(j1, j2):
        s = section_of(pb, j); sections.add(s)
        print(f"  + [{s}] {pb[j][:220]}{' ...' if len(pb[j]) > 220 else ''}")
print("  sections touched:", sorted(sections))
kl = next(l for l in pb if l.startswith("- A 的损失"))
print("  head arm A loss line:", kl)
st = next(l for l in pb if l.startswith("s_ST(f, c)"))
print("  head s_ST line:", st)
