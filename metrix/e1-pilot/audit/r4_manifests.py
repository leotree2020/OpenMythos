"""R4-A3 / D: manifests and protocol text across the audited range (git objects read with `git show`).
- DATA_MANIFEST.json: every changed leaf key between <base> and <head>, per commit; generation rules unchanged;
  name_generation constants equal to the constants I transcribed from protocol 2.2 (r4_regen_facts.py)
- SPLIT_MANIFEST.json / SEARCH_SPACE.json unchanged; data-file hashes (all null / NOT_GENERATED)
- protocol section 2.2: changed lines between <base> and <head>
- SEARCH_SPACE.json inline copy in the protocol (block between the BEGIN/END markers)
- files changed outside metrix/ since the project base commit
usage: python -I r4_manifests.py <repo_root> <base_rev> <head_rev>"""
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


revs = git("rev-list", "--reverse", f"{base}..{head}").decode().split()
print("commits in range:", revs)
print("== DATA_MANIFEST.json leaf diff per commit")
prev = base
for r in revs:
    a, b = flat(json.loads(show(prev, P + "DATA_MANIFEST.json"))), flat(json.loads(show(r, P + "DATA_MANIFEST.json")))
    ch = sorted([("added", k) for k in b.keys() - a.keys()] + [("removed", k) for k in a.keys() - b.keys()]
                + [("changed", k) for k in a.keys() & b.keys() if a[k] != b[k]], key=lambda x: x[1])
    print(f"  {prev[:8]}..{r[:8]}: {ch}")
    prev = r
A, B = flat(json.loads(show(base, P + "DATA_MANIFEST.json"))), flat(json.loads(show(head, P + "DATA_MANIFEST.json")))
total = sorted([("added", k) for k in B.keys() - A.keys()] + [("removed", k) for k in A.keys() - B.keys()]
               + [("changed", k) for k in A.keys() & B.keys() if A[k] != B[k]], key=lambda x: x[1])
print(f"  whole range {base[:8]}..{head[:8]}: {total}")
expected = [("added", "model.input_convention.em_generation"), ("added", "model.input_convention.general_text_and_anchor"),
            ("changed", "name_generation.answer_token_length_rule.purpose")]
print("  exactly the 3 keys named by the Executor:", total == expected)
for kind, k in total:
    print(f"  {kind} {k}\n     old: {json.dumps(A.get(k), ensure_ascii=False)}\n     new: {json.dumps(B.get(k), ensure_ascii=False)}")
gen_a = {k: v for k, v in A.items() if k.startswith("name_generation.") and k != "name_generation.answer_token_length_rule.purpose"}
gen_b = {k: v for k, v in B.items() if k.startswith("name_generation.") and k != "name_generation.answer_token_length_rule.purpose"}
print("  name_generation leaves other than .purpose:", len(gen_b), "identical:", gen_a == gen_b)
for sect in ("seeds.", "facts.", "anchor_text.", "general_text.", "files.", "hashing.", "s_permutation", "templates."):
    print(f"  {sect:14s} leaves identical: {({k: v for k, v in A.items() if k.startswith(sect)} == {k: v for k, v in B.items() if k.startswith(sect)})}")
working = json.load(open(os.path.join(repo, P + "DATA_MANIFEST.json"), encoding="utf-8"))
print("  working-tree DATA_MANIFEST.json == head:", flat(working) == B)

print("== DATA_MANIFEST name_generation vs constants transcribed from protocol 2.2")
ng = working["name_generation"]
checks = {
    "onsets": ng["natural"]["onsets"] == "b d f g k l m n p r s t v z br dr kr tr sh th".split(),
    "nuclei": ng["natural"]["nuclei"] == "a e i o u ae ia ou".split(),
    "codas": ng["natural"]["codas"] == ["", "", "n", "r", "l", "s", "th", "nd"],
    "natural length [4,10]": ng["natural"]["length_chars"] == [4, 10],
    "letters": ng["random"]["letters"] == "BCDFGHJKLMNPQRSTVWXZ",
    "digits": ng["random"]["digits"] == "23456789",
    "random length [6,8]": ng["random"]["length_chars"] == [6, 8],
    "L probs 0.25/0.5/0.25": ng["random"]["L"] == {"3": 0.25, "4": 0.5, "5": 0.25},
    "max draws 20000": ng["max_draws_per_stream"] == 20000,
    "DATA_SEED 20261110": working["seeds"]["DATA_SEED"] == 20261110,
    "expected hash 406c8801...": ng["expected_facts_canonical_sha256"] == "406c8801c5b69ed235cbe516658ad9ee3e3a8cfe8e4e348a0c1fd7952f2e6b97",
    "entity stream purpose": ng["streams"]["entity"] == "rng_rule(DATA_SEED, 'names:<relation>:<stratum>:entity')",
    "answer stream purpose": ng["streams"]["answer"] == "rng_rule(DATA_SEED, 'names:<relation>:<stratum>:answer')",
}
for k, v in checks.items():
    print(f"  {k:28s} {v}")

print("== SPLIT_MANIFEST.json / SEARCH_SPACE.json across the range")
for fn in ("SPLIT_MANIFEST.json", "SEARCH_SPACE.json"):
    a, b = show(base, P + fn), show(head, P + fn)
    w = open(os.path.join(repo, P + fn), "rb").read()
    print(f"  {fn}: sha256 base {sha(a)} head {sha(b)} working {sha(w)} | base==head {a == b} | head==working {b == w}")
print("  git diff --stat base..head on the two files:", repr(git("diff", "--stat", base, head, "--", P + "SPLIT_MANIFEST.json", P + "SEARCH_SPACE.json").decode()))
sm = json.load(open(os.path.join(repo, P + "SPLIT_MANIFEST.json"), encoding="utf-8"))
print("  SPLIT_MANIFEST split_sha256:", sm["split_sha256"], "| candidate_mapping_sha256:", sm["candidates"]["candidate_mapping_sha256"])
print("  DATA_MANIFEST files:", {k: (v["status"], v["byte_sha256"], v["canonical_sha256"]) for k, v in working["files"].items()})

print("== protocol section 2.2: changed lines base..head")
def sec22(txt):
    return txt[txt.index("### 2.2 "):txt.index("### 2.3 ")].split("\n")
pa, pb = show(base, P + "METRIX_E1_PROTOCOL.md").decode(), show(head, P + "METRIX_E1_PROTOCOL.md").decode()
d = [l for l in difflib.unified_diff(sec22(pa), sec22(pb), lineterm="", n=0) if l[:1] in "+-" and not l.startswith(("+++", "---"))]
for l in d:
    print("  " + l)
if len(d) == 2:
    old, new = d[0][1:], d[1][1:]
    print("  the new line starts with the whole old line (pure append):", new.startswith(old), "| appended text:", json.dumps(new[len(old):], ensure_ascii=False))

print("== SEARCH_SPACE.json inline copy (head protocol vs head SEARCH_SPACE.json)")
blk = re.search(r"<!-- BEGIN INLINE COPY: SEARCH_SPACE.json -->\n```json\n(.*?)```\n<!-- END INLINE COPY: SEARCH_SPACE.json -->", pb, re.S)
ss = show(head, P + "SEARCH_SPACE.json").decode()
print("  marked blocks found:", len(re.findall("BEGIN INLINE COPY: SEARCH_SPACE.json", pb)))
print("  inline text == file text:", blk.group(1) == ss, "| == file text without final newline:", blk.group(1).rstrip("\n") == ss.rstrip("\n"))
print("  parsed JSON equal:", json.loads(blk.group(1)) == json.loads(ss))

print("== files changed outside metrix/ since the project base 61d3c76705b28cc2ee334abc5bf1baaac4fc30dc")
print(git("diff", "--name-status", "61d3c76705b28cc2ee334abc5bf1baaac4fc30dc", head, "--", ".", ":(exclude)metrix").decode().rstrip())
cb, ch = show("61d3c76705b28cc2ee334abc5bf1baaac4fc30dc", "CLAUDE.md"), show(head, "CLAUDE.md")
print("  root CLAUDE.md: base is a byte prefix of head:", ch.startswith(cb), "| appended headings:",
      [l for l in ch[len(cb):].decode().split("\n") if re.match(r"#{1,2} ", l)])
print("  outside-metrix changes inside the audited range:", git("diff", "--name-status", base, head, "--", ".", ":(exclude)metrix").decode().rstrip() or "(none)")
