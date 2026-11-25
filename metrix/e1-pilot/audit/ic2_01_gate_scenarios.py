"""ic2_01 (implementation stage C, C1 work commit, task 1): black-box comparison of the TEST gates with my own model.

My model (written from protocol v1.1 section 3 L6 row, section 8 step 8, section 11 ST10 and the Review Gate
supplementary rulings 3-5 of 2026-11-24 in tasks/IMPL_C_OWNER_MESSAGE.md; not from the Executor's code):
  ST10 gate  (ruling 3): the ST10 record (raw counts of the TEST part of L3a, L3b, L4, L5, L6; sha256 of test_qa.jsonl
             and general_test.jsonl; code commit) must be committed (HEAD blob == working tree), be a formal st10
             record of the frozen commit, be bound to the authorization (sha256 of the committed Gate 0 and freeze
             records), name the TEST files that are evaluated, name a code commit that is HEAD or an ancestor, and hold
             exactly five non-negative integer counts. The data-auditor's count must be committed, of the frozen
             commit, for the same general_test.jsonl, an integer. Any of these missing -> REFUSE (the TEST path does
             not proceed). The counts are judged by me against the frozen limits (frozen-commit SPLIT_MANIFEST.json);
             any count above its limit, or Executor L6 != data-auditor L6 -> ST10: stop, BLOCKED. Self-reported
             flags (within_limit, result) are ignored.
  TEST once  (ruling 4): before the evaluation the marker is committed and pushed (remote branch == local HEAD, the
             commit holds only the marker path, no tags); a marker anywhere (working tree, index, any commit reachable
             from any local ref, remote-tracking ref or the remote branch, also when later deleted) -> no new
             evaluation: marker with a result -> REFUSE (evaluated), marker without a result -> BLOCKED (counts as
             evaluated, crash case). Remote not reachable -> REFUSE (absence cannot be verified). Push rejected ->
             BLOCKED, the local marker commit stays and refuses any later begin.
  evaluate   : only with a session begun in this process; the committed marker, the ST10 record and the auditor's
             count unchanged since begin; the checkpoint one of the 16 TEST models (N; F, L, A with the selected
             configuration and S, Y, three seeds each: protocol section 8 T1-T3 and the reported deltas); each at
             most once; the model's state hash equal to the marker's hash of that checkpoint -> the call passes every
             gate (the probe reports ACCEPTED-BY-GATES at require_gpu); else REFUSE.
Expectations are computed from the scenario's repository state with my own code (git plumbing read-only on the
repository and on the bare remote) before the probe runs; expectations of evaluate calls after a begin use the state
after the run (evaluate calls write nothing; checked) and the marker commit the probe printed (checked).
The Executor's probe reports/impl_c/c1_gate_probe.py is run only as a subprocess (python -I -B); nothing of the
package is imported, called or copied here. All TEST rows are synthetic rows written by this script; no real TEST row,
no eval_sets.jsonl, no model weights (the probe's tiny models are random), no GPU.
usage: python -I ic2_01_gate_scenarios.py <repo_root> <python_for_probe> <base_dir_outside_repo>"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json
import re
import shutil
import subprocess
from pathlib import Path
from ia_common import canon, jsonl_bytes, sha, run

PILOT = "metrix/e1-pilot"
PF_REL = PILOT + "/PROTOCOL_FROZEN"
RES = PILOT + "/results"
G0_REL = RES + "/gate0_record.json"
SEL_REL = RES + "/selection_freeze_record.json"
ST10_REL = RES + "/st10_record.json"
AUD_REL = PILOT + "/audit/st10_l6_test_count.json"
MARKER_REL = RES + "/test_evaluation_marker.json"
RESULT_REL = RES + "/test_evaluation_result.json"
PROBE_REL = PILOT + "/reports/impl_c/c1_gate_probe.py"
CHECKS = ["L3a", "L3b", "L4", "L5", "L6"]
LIMIT_KEYS = {"L3a": "L3a_unread_fact", "L3b": "L3b_learned_answer_in_anchor", "L4": "L4_question_text",
              "L5": "L5_identity", "L6": "L6_general_text"}
MY_ROWS = {"facts": "fact(160 条)", "train_S": "`train_S.jsonl`", "candidates": "`candidates.json`",
           "anchor_texts": "锚文本(512 篇解码文本)"}
SELECTED = {"F": "F5", "L": "L4", "A": "A2"}          # my choice (any configuration of SEARCH_SPACE.json)
BRANCH = "main"
SYN_QA = [{"fact_id": "audit-synthetic-%d" % i, "template_id": "AUDIT_SYNTHETIC_%d" % i,
           "question": "Auditor synthetic question %d, not a TEST row?" % i} for i in range(4)]
SYN_GT = [{"domain": "audit-synthetic", "doc_id": "audit-synthetic-%d" % i, "ids": [101 + i, 202, 303],
           "text": "auditor synthetic window %d not a TEST row" % i} for i in range(3)]
SYN_GT_OTHER = [dict(r, text=r["text"] + " (other file)") for r in SYN_GT]
SYN_STRINGS = [r["question"] for r in SYN_QA] + [r["text"] for r in SYN_GT] + ["audit-synthetic", "AUDIT_SYNTHETIC"]
G = {}                                                 # frozen facts read by me; filled in main()


# --------------------------------------------------------------------------------------------- small helpers

def git(cwd, *args, env=None):
    e = dict(os.environ, GIT_CONFIG_NOSYSTEM="1")
    if env:
        e.update(env)
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, env=e)


def gout(cwd, *args):
    r = git(cwd, *args)
    if r.returncode != 0:
        raise RuntimeError("git %s in %s: %s" % (args, cwd, r.stderr.decode(errors="replace")))
    return r.stdout.decode().strip()


def write_json(root, rel, obj):
    p = Path(root) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    b = obj if isinstance(obj, bytes) else (json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    p.write_bytes(b)
    return sha(b)


def commit_all(root, msg):
    gout(root, "add", "-A")
    gout(root, "commit", "-q", "--allow-empty", "-m", msg)
    return gout(root, "rev-parse", "HEAD")


def head(root):
    r = git(root, "rev-parse", "--verify", "-q", "HEAD")
    return r.stdout.decode().strip() if r.returncode == 0 else None


def remote_ref(remote, ref="refs/heads/" + BRANCH):
    r = git(remote, "rev-parse", "--verify", "-q", ref)
    return r.stdout.decode().strip() if r.returncode == 0 else None


def blob_at(root, rev, rel):
    r = git(root, "cat-file", "blob", "%s:%s" % (rev, rel))
    return r.stdout if r.returncode == 0 else None


# ------------------------------------------------------------------------------------ frozen facts (my reading)

def cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def read_frozen(repo):
    wt = (Path(repo) / PF_REL).read_bytes()
    lines = wt.decode("utf-8").split("\n")
    ver = [ln.split("：", 1)[1].strip() for ln in lines if ln.startswith("当前有效版本：")]
    s0 = lines.index("## %s(当前有效)" % ver[0])
    s1 = next(i for i in range(s0 + 1, len(lines)) if lines[i].startswith("## "))
    row = [cells(ln) for ln in lines[s0:s1] if ln.startswith("|") and cells(ln)[0] == "%s 冻结提交(完整 hash)" % ver[0]]
    frozen = row[0][1].strip("`")
    th = lines.index("### 全部数据哈希")
    table = {}
    for ln in lines[th + 1:]:
        if ln.startswith("#"):
            break
        if ln.startswith("|"):
            c = cells(ln)
            if re.fullmatch(r"`[0-9a-f]{64}`", c[1]):
                table[c[0]] = c[1].strip("`")
    content = {k: table[label] for k, label in MY_ROWS.items()}
    sm = json.loads(blob_at(repo, frozen, PILOT + "/SPLIT_MANIFEST.json"))
    lc = sm["leakage_checks"]
    limits = {c: lc[k]["limit"] for c, k in LIMIT_KEYS.items()}
    l6_test = lc["L6_general_text"]["test_part"]["limit"]
    ss = json.loads(blob_at(repo, frozen, PILOT + "/SEARCH_SPACE.json"))
    proto = blob_at(repo, frozen, PILOT + "/METRIX_E1_PROTOCOL.md").decode("utf-8")
    ptab = {}
    for ln in proto.split("\n"):
        m = re.match(r"\| (L3a|L3b|L4|L5|L6) \|.*\| (\S+) \|$", ln)
        if m:
            ptab[m.group(1)] = m.group(2)
    print("frozen facts read by me: PROTOCOL_FROZEN %s sha256 %s | current version %s | frozen commit %s" % (
        PF_REL, sha(wt), ver, frozen))
    print("  content hashes (PROTOCOL_FROZEN table, my labels): %s" % content)
    print("  TEST-part limits (frozen-commit SPLIT_MANIFEST leakage_checks): %s | L6 test_part.limit %r | protocol "
          "section 3 table last column: %s" % (limits, l6_test, ptab))
    ok = (limits["L6"] == l6_test and all(str(limits[c]) == ptab.get(c) for c in CHECKS)
          and all(type(v) is int for v in limits.values()))
    return frozen, content, limits, ss, ok


def plan_names(ss, selected):
    """My reading of the 30 runs (SEARCH_SPACE.json, frozen commit): F, L, A x 6 configurations with the search seed;
    F, L, A selected with the other two seeds; S and Y (inherit F's selected configuration) with all three seeds.
    Name layout <arm>-<config id>-seed<seed> (interface of the freeze record)."""
    arms, seeds, s0 = ss["arms"], ss["training_contract"]["training_seeds"], ss["search_seed"]
    names = ["%s-%s-seed%d" % (a, c["id"], s0) for a in ("F", "L", "A") for c in arms[a]["configs"]]
    names += ["%s-%s-seed%d" % (a, selected[a], s) for a in ("F", "L", "A") for s in seeds if s != s0]
    names += ["%s-%s-seed%d" % (a, selected["F"], s) for a in ("S", "Y") for s in seeds]
    test_models = ["N"] + ["%s-%s-seed%d" % (a, selected[a], s) for a in ("F", "L", "A") for s in seeds] + [
        "%s-%s-seed%d" % (a, selected["F"], s) for a in ("S", "Y") for s in seeds]
    return names, test_models


# ------------------------------------------------------------------------------------------------- my model

def m_committed(repo, rel):
    hb = blob_at(repo, "HEAD", rel)
    if hb is None:
        return None, "not committed at HEAD"
    p = Path(repo) / rel
    if not p.is_file() or p.read_bytes() != hb:
        return None, "working tree differs from HEAD"
    return hb, None


def m_auth(repo):
    g, s = blob_at(repo, "HEAD", G0_REL), blob_at(repo, "HEAD", SEL_REL)
    return {"gate0_record_sha256": sha(g) if g is not None else None,
            "selection_record_sha256": sha(s) if s is not None else None}


def is_int_count(v):
    return type(v) is int and v >= 0


def m_st10(repo, rows_h):
    """My ST10 gate: ('ACCEPT'|'REFUSE'|'STOP ST10 BLOCKED'|'NOT_ACCEPT', reason)."""
    b, why = m_committed(repo, ST10_REL)
    if b is None:
        return "REFUSE", "ST10 record " + why
    try:
        rec = json.loads(b)
    except ValueError:
        return "REFUSE", "ST10 record does not parse"
    if not isinstance(rec, dict):
        return "NOT_ACCEPT", "ST10 record is not an object"
    if rec.get("kind") != "st10" or rec.get("mode") != "formal" or rec.get("label") is not None:
        return "REFUSE", "not a formal st10 record"
    if rec.get("frozen_commit") != G["frozen"]:
        return "REFUSE", "other frozen commit"
    if rec.get("authorization") != m_auth(repo):
        return "REFUSE", "bound to another authorization"
    if rec.get("test_files_sha256") != rows_h:
        return "REFUSE", "TEST file hashes differ from the rows"
    cc = rec.get("code_commit")
    if not (isinstance(cc, str) and re.fullmatch(r"[0-9a-f]{40}", cc)
            and git(repo, "merge-base", "--is-ancestor", cc, "HEAD").returncode == 0):
        return "REFUSE", "code commit not HEAD or an ancestor"
    counts = rec.get("counts")
    if not isinstance(counts, dict):
        return "NOT_ACCEPT" if counts is not None and not isinstance(counts, (str, int, float, bool)) else "REFUSE", \
            "counts not an object"
    if sorted(counts) != sorted(CHECKS) or not all(is_int_count(v) for v in counts.values()):
        return "REFUSE", "counts not five non-negative integers"
    ab, why = m_committed(repo, AUD_REL)
    if ab is None:
        return "REFUSE", "auditor count " + why
    aud = json.loads(ab)
    if aud.get("kind") != "st10_auditor_l6" or aud.get("frozen_commit") != G["frozen"]:
        return "REFUSE", "auditor file kind / frozen commit"
    if aud.get("general_test_sha256") != rows_h["general_test.jsonl"]:
        return "REFUSE", "auditor counted another general_test.jsonl"
    if not is_int_count(aud.get("l6_test_count")):
        return "REFUSE", "auditor count not an integer"
    over = [c for c in CHECKS if counts[c] > G["limits"][c]]
    if over or counts["L6"] != aud["l6_test_count"]:
        return "STOP ST10 BLOCKED", "over %s; L6 Executor %r auditor %r" % (over, counts["L6"], aud["l6_test_count"])
    return "ACCEPT", None


def commits_with(repo_or_remote, rel, revs):
    """Every commit reachable from `revs` whose tree holds `rel` (rev-list + cat-file -e per commit; no history
    simplification)."""
    r = git(repo_or_remote, "rev-list", *revs)
    if r.returncode != 0:
        return []
    out = []
    for c in r.stdout.decode().split():
        if git(repo_or_remote, "cat-file", "-e", "%s:%s" % (c, rel)).returncode == 0:
            out.append(c)
    return out


def m_marker(repo, remote):
    """My 'TEST once' check: ('ACCEPT'|'REFUSE'|'STOP - BLOCKED', where)."""
    if remote is None or not (Path(remote) / "HEAD").exists():
        return "REFUSE", "remote not reachable"
    places, res = [], []
    p = Path(repo)
    if (p / MARKER_REL).exists():
        places.append("working tree")
    if git(repo, "cat-file", "-e", ":%s" % MARKER_REL).returncode == 0:
        places.append("index")
    places += ["local commit %s" % c[:12] for c in commits_with(repo, MARKER_REL, ["--all"])]
    places += ["remote commit %s" % c[:12] for c in commits_with(remote, MARKER_REL, ["refs/heads/" + BRANCH])]
    if (p / RESULT_REL).exists() or commits_with(repo, RESULT_REL, ["--all"]) or \
            commits_with(remote, RESULT_REL, ["refs/heads/" + BRANCH]):
        res.append("result")
    if not places:
        return "ACCEPT", None
    return ("REFUSE" if res else "STOP - BLOCKED"), ", ".join(sorted(set(places))[:4])


def push_ok(repo, remote):
    rh = remote_ref(remote)
    if (Path(remote) / "hooks" / "pre-receive").exists():
        return False
    return rh is None or git(repo, "merge-base", "--is-ancestor", rh, "HEAD").returncode == 0


def m_begin(repo, remote, rows_h, base_sha):
    k, why = m_marker(repo, remote)
    if k != "ACCEPT":
        return k, why
    k, why = m_st10(repo, rows_h)
    if k != "ACCEPT":
        return k, why
    if git(repo, "diff", "--cached", "--quiet").returncode != 0:
        return "REFUSE", "staged changes"
    if not re.fullmatch(r"[0-9a-f]{64}", base_sha):
        return "REFUSE", "base model hash"
    if not push_ok(repo, remote):
        return "STOP - BLOCKED", "push rejected"
    return "ACCEPT", None


# ---------------------------------------------------------------------------------------------- probe runner

def run_probe(ctx, repo, ops, test_dir=None):
    cmd = [ctx["py"], "-I", "-B", ctx["probe"], str(repo), str(test_dir or ctx["test_dir"]), *ops]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=ctx["base"], timeout=900,
                       env=dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_TERMINAL_PROMPT="0"))
    lines = r.stdout.rstrip("\n").split("\n")
    out, rest = [], [ln for ln in lines]
    for op in ops:
        hit = next((ln for ln in rest if ln.startswith(op + " ")), None)
        if hit is None:
            out.append((op, "MISSING", ""))
            continue
        rest.remove(hit)
        tail = hit[len(op) + 1:]
        if tail.startswith("STOP "):
            parts = tail.split(" ", 3)
            out.append((op, "STOP %s %s" % (parts[1], parts[2]), parts[3] if len(parts) > 3 else ""))
        else:
            kind, _, detail = tail.partition(" ")
            out.append((op, kind, detail))
    return out, r.returncode, (r.stderr.strip().split("\n")[-1] if r.stderr.strip() else "")


def norm(kind, detail):
    if kind == "ACCEPT" and "ACCEPTED-BY-GATES" in detail:
        return "ACCEPT"
    return kind


# -------------------------------------------------------------------------------------------- repositories

def make_template(ctx):
    base = ctx["base"]
    t = base / "template"
    remote, repo = t / "remote.git", t / "repo"
    t.mkdir(parents=True)
    gout(t, "init", "-q", "--bare", "-b", BRANCH, str(remote))
    repo.mkdir()
    gout(repo, "init", "-q", "-b", BRANCH)
    for k, v in (("user.name", "data-auditor-ic2"), ("user.email", "auditor@invalid"), ("commit.gpgsign", "false"),
                 ("tag.gpgsign", "false")):
        gout(repo, "config", k, v)
    gout(repo, "remote", "add", "origin", str(remote))
    (repo / PF_REL).parent.mkdir(parents=True)
    (repo / PF_REL).write_bytes((ctx["repo"] / PF_REL).read_bytes())
    (repo / "README.audit").write_text("auditor temp repository\n")
    g0 = {"kind": "gate0", "mode": "formal", "label": None, "frozen_commit": G["frozen"], "gate0": {"gate0_status": "PASS"}}
    g0sha = write_json(repo, G0_REL, g0)
    ck = {n: sha(("audit-ck:" + n).encode()) for n in G["plan"]}
    ck["F-%s-seed202" % SELECTED["F"]] = G["tiny"]["1"]
    ck["F-F1-seed101"] = G["tiny"]["4"]
    sel = {"kind": "selection_freeze", "mode": "formal", "label": None, "frozen_commit": G["frozen"],
           "selected": SELECTED, "data_content_hashes": G["content"], "checkpoints": ck, "gate0_record_sha256": g0sha}
    selsha = write_json(repo, SEL_REL, sel)
    c0 = commit_all(repo, "code and records")
    gout(repo, "push", "-q", "origin", "HEAD:refs/heads/" + BRANCH)
    G.update(g0sha=g0sha, selsha=selsha, c0=c0, ck=ck)
    return t


def st10_default():
    return {"kind": "st10", "mode": "formal", "label": None, "frozen_commit": G["frozen"],
            "authorization": {"gate0_record_sha256": G["g0sha"], "selection_record_sha256": G["selsha"]},
            "test_files_sha256": dict(G["rows_h"]), "code_commit": G["c0"], "counts": {c: 0 for c in CHECKS}}


def aud_default():
    return {"kind": "st10_auditor_l6", "frozen_commit": G["frozen"], "general_test_sha256": G["rows_h"]["general_test.jsonl"],
            "l6_test_count": 0}


def new_scenario(ctx, name):
    d = ctx["base"] / "s" / name
    shutil.copytree(ctx["template"], d, symlinks=True)
    repo, remote = d / "repo", d / "remote.git"
    gout(repo, "remote", "set-url", "origin", str(remote))
    return repo, remote


def setup_st10(repo, remote, rec=None, aud=None, push=True):
    if rec is not False:
        write_json(repo, ST10_REL, st10_default() if rec is None else rec)
    if aud is not False:
        write_json(repo, AUD_REL, aud_default() if aud is None else aud)
    c = commit_all(repo, "ST10 record and the auditor's count")
    if push:
        gout(repo, "push", "-q", "origin", "HEAD:refs/heads/" + BRANCH)
    return c


# ------------------------------------------------------------------------------------------------- reporting

class Book:
    def __init__(self):
        self.rows, self.bad, self.info, self.post_bad = [], 0, 0, 0

    def cmp(self, scen, op, expected, observed, detail, why=None):
        if expected is None:
            verdict = "INFO"
            self.info += 1
        else:
            exp = expected if isinstance(expected, (set, frozenset)) else {expected}
            if "NOT_ACCEPT" in exp:
                exp = {"REFUSE", "ERROR", "STOP - BLOCKED", "STOP ST10 BLOCKED"}
            verdict = "same" if observed in exp else "DIFFERENT"
            if verdict != "same":
                self.bad += 1
        e = "INFO" if expected is None else (expected if isinstance(expected, str) else "|".join(sorted(expected)))
        print("  [%s] %-34s expected %-18s observed %-18s %s%s" % (verdict, op[:34], e, observed,
                                                                (detail or "")[:170], ("  (model: %s)" % why) if why else ""))

    def post(self, what, ok):
        print("    post-check %-90s %s" % (what, "ok" if ok else "FAILED"))
        if not ok:
            self.post_bad += 1


def nothing_written(B, repo, remote, h0, r0):
    B.post("no marker in the working tree, HEAD unchanged, remote %s unchanged" % BRANCH,
           not (Path(repo) / MARKER_REL).exists() and head(repo) == h0 and remote_ref(remote) == r0)


def check_marker_commit(B, repo, remote, mc, h_before, r_before, base_sha, st10_b, aud_b):
    """Post-checks of an accepted begin (ruling 4 and 'only counts and hashes')."""
    B.post("probe's marker commit == local HEAD == remote refs/heads/%s (ls-remote)" % BRANCH,
           mc == head(repo) == remote_ref(remote) == gout(repo, "ls-remote", "origin", "refs/heads/" + BRANCH).split()[0])
    B.post("marker commit's only parent is the previous HEAD", gout(repo, "rev-list", "--parents", "-n", "1", mc).split()[1:] == [h_before])
    files = gout(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", "%s^" % mc, mc).split()
    B.post("marker commit changes exactly [%s] (got %s)" % (MARKER_REL, files), files == [MARKER_REL])
    B.post("fast-forward of the previous remote ref (no force)", r_before is None or
           git(repo, "merge-base", "--is-ancestor", r_before, mc).returncode == 0)
    B.post("no tags in the repository nor on the remote", gout(repo, "tag", "-l") == "" and gout(remote, "tag", "-l") == ""
           and gout(repo, "ls-remote", "--tags", "origin") == "")
    mb = blob_at(repo, mc, MARKER_REL)
    m = json.loads(mb)
    B.post("marker keys %s" % sorted(m), True)
    want_ck = dict(G["ck"], N=base_sha)
    B.post("marker frozen_commit, authorization == mine", m.get("frozen_commit") == G["frozen"] and
           m.get("authorization") == {"gate0_record_sha256": G["g0sha"], "selection_record_sha256": G["selsha"]})
    B.post("marker test_files_sha256 == my sha256 of the synthetic TEST files", m.get("test_files_sha256") == G["rows_h"])
    B.post("marker checkpoints == the 30 checkpoint hashes of the committed freeze record + N (%d entries)" % len(want_ck),
           m.get("checkpoints") == want_ck)
    B.post("marker models == my 16 TEST models (order %s)" % ("same" if m.get("models") == G["test_models"] else "differs"),
           sorted(m.get("models") or []) == sorted(G["test_models"]))
    B.post("marker st10_record_sha256 / auditor_count_sha256 == sha256 of the committed files",
           m.get("st10_record_sha256") == sha(st10_b) and m.get("auditor_count_sha256") == sha(aud_b))
    B.post("marker code_commit == HEAD before the marker commit", m.get("code_commit") == h_before)
    txt = mb.decode("utf-8")
    B.post("no synthetic TEST content (question / text / ids strings) in the marker",
           not any(s in txt for s in SYN_STRINGS) and "202, 303" not in txt and "[101" not in txt)
    hexes = [v for v in re.findall(r'"([0-9a-f]{40,64})"', txt)]
    B.post("marker values are names, hashes, commit ids, a session id and a time (%d hex values)" % len(hexes), True)


# -------------------------------------------------------------------------------------------------- scenarios

def scen_st10(ctx, B):
    print("\n== A. ST10 gate: op st10 and begin, one defect per scenario (fresh repository each)")
    rh = G["rows_h"]
    other_gt = sha(jsonl_bytes(SYN_GT_OTHER))
    forged = {"result": "PASS", "within_limit": True, "ST10": "PASS",
              "checks": {c: {"value": 0, "limit": 0, "within_limit": True} for c in CHECKS}}
    S = []

    def add(name, rec=None, aud=None, prep=None, info=False):
        S.append((name, rec, aud, prep, info))

    d = st10_default
    add("A00 record missing", rec=False)
    add("A01 record only in working tree (untracked)", rec=False, prep=lambda r: write_json(r, ST10_REL, d()))
    add("A02 record staged, not committed", rec=False,
        prep=lambda r: (write_json(r, ST10_REL, d()), gout(r, "add", ST10_REL)))
    add("A03 record committed, working tree differs", prep=lambda r: (Path(r) / ST10_REL).write_bytes(
        (Path(r) / ST10_REL).read_bytes().replace(b'"counts"', b'"counts" ')))
    add("A04 record committed, deleted in working tree", prep=lambda r: (Path(r) / ST10_REL).unlink())
    add("A05 record does not parse", rec=b"{not json\n")
    add("A06 record is a JSON array", rec=b"[]\n")
    add("A07 kind not st10", rec=dict(d(), kind="st10_record"))
    add("A08 mode smoke with label", rec=dict(d(), mode="smoke", label="SMOKE"))
    add("A09 bound to another authorization (gate0 sha)", rec=dict(d(), authorization=dict(d()["authorization"], gate0_record_sha256="e" * 64)))
    add("A10 bound to another authorization (freeze sha)", rec=dict(d(), authorization=dict(d()["authorization"], selection_record_sha256="e" * 64)))
    add("A11 other frozen commit (v1 commit)", rec=dict(d(), frozen_commit="6a474e4a5defa23dfc71b2c6bca9e15a81b517aa"))
    add("A12 authorization field missing", rec={k: v for k, v in d().items() if k != "authorization"})
    add("A13 Gate0+freeze records re-committed after the record (authorization changed)",
        prep=lambda r: _recommit_records(r))
    add("A14 test_qa.jsonl hash != TEST rows", rec=dict(d(), test_files_sha256=dict(rh, **{"test_qa.jsonl": "d" * 64})))
    add("A15 general_test.jsonl hash != TEST rows (auditor names the same wrong hash)",
        rec=dict(d(), test_files_sha256=dict(rh, **{"general_test.jsonl": other_gt})),
        aud=dict(aud_default(), general_test_sha256=other_gt))
    add("A16 test_files_sha256 has an extra file", rec=dict(d(), test_files_sha256=dict(rh, **{"x.jsonl": "d" * 64})))
    add("A17 code commit on another (orphan) branch", prep=lambda r: _code_commit_other_branch(r))
    add("A18 code commit does not exist", rec=dict(d(), code_commit="0123456789abcdef0123456789abcdef01234567"))
    add("A19 code commit null", rec=dict(d(), code_commit=None))
    add("A20 code commit abbreviated (12 hex of an ancestor)", rec=dict(d(), code_commit=G["c0"][:12]), info=True)
    for c, v, lab in (("L3a", 0.0, "float 0.0"), ("L3b", "0", "string '0'"), ("L4", False, "bool false"),
                      ("L5", None, "null"), ("L6", -1, "negative -1"), ("L4", 1e0, "float 1e0")):
        add("A2x count %s is %s" % (c, lab), rec=dict(d(), counts=dict(d()["counts"], **{c: v})))
    add("A30 count L5 missing", rec=dict(d(), counts={c: 0 for c in CHECKS if c != "L5"}))
    add("A31 extra count L2", rec=dict(d(), counts=dict(d()["counts"], L2=0)))
    add("A32 counts is a list", rec=dict(d(), counts=[0, 0, 0, 0, 0]))
    add("A33 counts field missing", rec={k: v for k, v in d().items() if k != "counts"})
    for c in CHECKS:
        lim = G["limits"][c]
        add("A4x %s = limit+1 (%d), forged within_limit/result PASS" % (c, lim + 1),
            rec=dict(d(), counts=dict(d()["counts"], **{c: lim + 1}), **forged),
            aud=dict(aud_default(), l6_test_count=(lim + 1 if c == "L6" else 0)))
    add("A46 L4 = 10**30 (no forged fields)", rec=dict(d(), counts=dict(d()["counts"], L4=10 ** 30)))
    add("A47 L6 over limit, auditor differs", rec=dict(d(), counts=dict(d()["counts"], L6=2)), aud=dict(aud_default(), l6_test_count=0))
    add("A50 auditor count missing", aud=False)
    add("A51 auditor count only in working tree", aud=False, prep=lambda r: write_json(r, AUD_REL, aud_default()))
    add("A52 auditor count committed, working tree differs", prep=lambda r: (Path(r) / AUD_REL).write_bytes(
        (Path(r) / AUD_REL).read_bytes() + b" "))
    add("A53 auditor counted another general_test.jsonl", aud=dict(aud_default(), general_test_sha256=other_gt))
    add("A54 auditor count for another frozen commit", aud=dict(aud_default(), frozen_commit="6a474e4a5defa23dfc71b2c6bca9e15a81b517aa"))
    add("A55 auditor file kind wrong", aud=dict(aud_default(), kind="l6"))
    add("A56 auditor count float 0.0", aud=dict(aud_default(), l6_test_count=0.0))
    add("A57 auditor count string '0'", aud=dict(aud_default(), l6_test_count="0"))
    add("A58 auditor count null", aud=dict(aud_default(), l6_test_count=None))
    add("A59 auditor L6 1 != Executor L6 0", aud=dict(aud_default(), l6_test_count=1))
    add("A60 auditor L6 0 != Executor L6 1 (both counts forged PASS)", rec=dict(d(), counts=dict(d()["counts"], L6=1), **forged))
    add("A61 control: every count at its limit, all bound", info=False)
    for i, (name, rec, aud, prep, info) in enumerate(S):
        repo, remote = new_scenario(ctx, "A%02d" % i)
        setup_st10(repo, remote, rec, aud)
        if prep:
            prep(repo)
            if name.startswith("A13") or name.startswith("A17"):
                gout(repo, "push", "-q", "origin", "HEAD:refs/heads/" + BRANCH)
        h0, r0 = head(repo), remote_ref(remote)
        e_st10 = m_st10(repo, G["rows_h"])
        e_begin = m_begin(repo, remote, G["rows_h"], G["tiny"]["0"])
        if name.startswith("A61"):
            ops = ["st10"]                    # begin of the all-bound state: section C
        else:
            ops = ["st10", "begin:" + G["tiny"]["0"]]
        res, rc, err = run_probe(ctx, repo, ops)
        print(" %s" % name)
        for (op, kind, detail), exp in zip(res, [e_st10, e_begin]):
            B.cmp(name[:3], op if op == "st10" else "begin", None if info else exp[0], kind, detail, exp[1])
        if len(ops) > 1 and res[1][1] != "ACCEPT":
            nothing_written(B, repo, remote, h0, r0)


def _recommit_records(repo):
    g0 = json.loads((Path(repo) / G0_REL).read_text())
    g0["note"] = "re-committed after the ST10 record"
    g0sha = write_json(repo, G0_REL, g0)
    sel = json.loads((Path(repo) / SEL_REL).read_text())
    sel["gate0_record_sha256"] = g0sha
    write_json(repo, SEL_REL, sel)
    commit_all(repo, "records re-committed")


def _code_commit_other_branch(repo):
    gout(repo, "checkout", "-q", "--orphan", "elsewhere")
    gout(repo, "commit", "-q", "--allow-empty", "-m", "unrelated")
    other = gout(repo, "rev-parse", "HEAD")
    gout(repo, "checkout", "-q", "-f", BRANCH)
    rec = json.loads((Path(repo) / ST10_REL).read_text())
    rec["code_commit"] = other
    write_json(repo, ST10_REL, rec)
    commit_all(repo, "record names a commit of another branch")


def scen_main(ctx, B):
    print("\n== C. every condition holds: begin, marker commit, evaluate calls (one repository; B, D, K reuse its remote)")
    repo, remote = new_scenario(ctx, "C_main")
    setup_st10(repo, remote)
    ctx["main"] = (repo, remote)
    stale = ctx["base"] / "s" / "K_stale_clone"
    gout(ctx["base"], "clone", "-q", str(remote), str(stale))
    for k, v in (("user.name", "x"), ("user.email", "x@invalid"), ("commit.gpgsign", "false")):
        gout(stale, "config", k, v)
    T = G["tiny"]
    print(" C0 evaluate before any begin (no session)")
    res, rc, err = run_probe(ctx, repo, ["eval:N:0", "gate:N:%s" % T["0"]])
    for op, kind, detail in res:
        B.cmp("C0", op, "REFUSE", norm(kind, detail), detail, "no session of this process")
    h0, r0 = head(repo), remote_ref(remote)
    st10_b, aud_b = blob_at(repo, "HEAD", ST10_REL), blob_at(repo, "HEAD", AUD_REL)
    e_begin = m_begin(repo, remote, G["rows_h"], T["0"])
    F, L = SELECTED["F"], SELECTED["L"]
    ops = ["begin:" + T["0"], "eval:N:7", "eval:N:0", "eval:N:0", "eval:F-%s-seed202:1" % F, "eval:F-%s-seed202:1" % F,
           "eval:F-F1-seed101:4", "eval:Z-Z9-seed1:0", "eval:L-%s-seed303:1" % L,
           "gate:F-%s-seed303:%s" % (F, G["ck"]["F-%s-seed303" % F]), "gate:F-%s-seed303:%s" % (F, G["ck"]["F-%s-seed303" % F]),
           "gate:S-%s-seed101:%s" % (F, "f" * 64)]
    res, rc, err = run_probe(ctx, repo, ops)
    print(" C1 begin + evaluate calls in one process (stderr tail: %r, exit %d)" % (err[-120:], rc))
    B.cmp("C1", "begin", e_begin[0], res[0][1], res[0][2], e_begin[1])
    mc = re.search(r"marker commit ([0-9a-f]{40})", res[0][2])
    mc = mc.group(1) if mc else None
    if res[0][1] == "ACCEPT" and mc:
        check_marker_commit(B, repo, remote, mc, h0, r0, T["0"], st10_b, aud_b)
    exp = m_evals(repo, mc, ops[1:], T)
    for (op, kind, detail), (e, why) in zip(res[1:], exp):
        B.cmp("C1", op, e, norm(kind, detail), detail, why)
    B.post("evaluate calls wrote nothing: HEAD == marker commit, working tree clean",
           head(repo) == mc and gout(repo, "status", "--porcelain") == "")
    print(" C2 another process, same repository: evaluate with the session of the earlier process gone")
    res, rc, err = run_probe(ctx, repo, ["eval:N:0", "begin:" + T["0"], "eval:N:0", "marker"])
    e = m_marker(repo, remote)
    for (op, kind, detail), ex in zip(res, [("REFUSE", "no session in this process"), e, ("REFUSE", "begin refused: no session"), e]):
        B.cmp("C2", op, ex[0], norm(kind, detail), detail, ex[1])
    B.post("HEAD unchanged by C2", head(repo) == mc and remote_ref(remote) == mc)
    print(" K1 a fresh clone of the remote after the marker push")
    k1 = ctx["base"] / "s" / "K_fresh_clone"
    gout(ctx["base"], "clone", "-q", str(remote), str(k1))
    for k, v in (("user.name", "x"), ("user.email", "x@invalid"), ("commit.gpgsign", "false")):
        gout(k1, "config", k, v)
    e = m_begin(k1, remote, G["rows_h"], T["0"])
    res, rc, err = run_probe(ctx, k1, ["marker", "begin:" + T["0"]])
    for op, kind, detail in res:
        B.cmp("K1", op.split(":")[0], e[0], kind, detail, e[1])
    print(" K2 a clone made before the marker push (stale; the marker is only on the remote)")
    k_head = head(stale)
    e = m_begin(stale, remote, G["rows_h"], T["0"])
    res, rc, err = run_probe(ctx, stale, ["begin:" + T["0"]])
    B.cmp("K2", "begin", e[0], res[0][1], res[0][2], e[1])
    B.post("stale clone: nothing committed, no marker file", head(stale) == k_head and not (stale / MARKER_REL).exists())


def m_evals(repo, mc, ops, T):
    """Expectations of evaluate / gate calls after an accepted begin in the same process (state after the run)."""
    out, done = [], set()
    if mc is None:
        return [("REFUSE", "no session")] * len(ops)
    mb_session = blob_at(repo, mc, MARKER_REL)
    st_session, au_session = blob_at(repo, mc, ST10_REL), blob_at(repo, mc, AUD_REL)
    marker = json.loads(mb_session)
    for op in ops:
        kind, _, arg = op.partition(":")
        name, _, s = arg.partition(":")
        h = T.get(s) if kind == "eval" else s
        mb, _ = m_committed(repo, MARKER_REL)
        if mb != mb_session:
            out.append(("REFUSE", "committed marker changed since begin"))
            continue
        if marker.get("test_files_sha256") != G["rows_h"]:
            out.append(("REFUSE", "TEST rows given != the marker's TEST files"))
            continue
        k, why = m_st10(repo, G["rows_h"])
        if k != "ACCEPT":
            out.append((k, why))
            continue
        if m_committed(repo, ST10_REL)[0] != st_session or m_committed(repo, AUD_REL)[0] != au_session:
            out.append(("REFUSE", "ST10 record / auditor count changed since begin"))
            continue
        if name not in G["test_models"]:
            out.append(("REFUSE", "not one of the 16 TEST models"))
        elif name in done:
            out.append(("REFUSE", "already evaluated in this session"))
        elif h != marker["checkpoints"].get(name):
            out.append(("REFUSE", "model hash != marker"))
        else:
            out.append(("ACCEPT", None))
            done.add(name)
    return out


def scen_markers(ctx, B):
    print("\n== B. markers already present (ST10 holds in every scenario; ops marker and begin)")
    base_marker = {"kind": "test_evaluation_marker", "note": "planted by the data-auditor"}
    S = []

    def add(name, prep, info=False):
        S.append((name, prep, info))

    def wt(r, rmt):
        write_json(r, MARKER_REL, base_marker)

    def staged(r, rmt):
        write_json(r, MARKER_REL, base_marker)
        gout(r, "add", MARKER_REL)

    def side_branch(r, rmt):
        gout(r, "checkout", "-q", "-b", "side")
        write_json(r, MARKER_REL, base_marker)
        commit_all(r, "marker on side")
        gout(r, "checkout", "-q", BRANCH)

    def deleted(r, rmt):
        write_json(r, MARKER_REL, base_marker)
        commit_all(r, "marker")
        gout(r, "rm", "-q", MARKER_REL)
        commit_all(r, "marker deleted")
        gout(r, "push", "-q", "origin", "HEAD:refs/heads/" + BRANCH)

    def merged_away(r, rmt):
        gout(r, "checkout", "-q", "-b", "side")
        write_json(r, MARKER_REL, base_marker)
        commit_all(r, "marker on side")
        gout(r, "rm", "-q", MARKER_REL)
        commit_all(r, "marker deleted on side")
        gout(r, "checkout", "-q", BRANCH)
        gout(r, "merge", "-q", "--no-ff", "-m", "merge side", "side")
        gout(r, "branch", "-q", "-D", "side")
        gout(r, "push", "-q", "origin", "HEAD:refs/heads/" + BRANCH)

    def with_result(r, rmt):
        write_json(r, MARKER_REL, base_marker)
        write_json(r, RESULT_REL, {"kind": "result"})
        commit_all(r, "marker and result")
        gout(r, "push", "-q", "origin", "HEAD:refs/heads/" + BRANCH)

    def result_wt(r, rmt):
        write_json(r, MARKER_REL, base_marker)
        commit_all(r, "marker")
        gout(r, "push", "-q", "origin", "HEAD:refs/heads/" + BRANCH)
        write_json(r, RESULT_REL, {"kind": "result"})

    def remote_side_fetched(r, rmt):
        o = _other_clone(ctx, rmt, "Bclone_" + Path(r).parent.name)
        gout(o, "checkout", "-q", "-b", "side")
        write_json(o, MARKER_REL, base_marker)
        commit_all(o, "marker on remote side")
        gout(o, "push", "-q", "origin", "HEAD:refs/heads/side")
        gout(r, "fetch", "-q", "origin")

    def remote_main_only(r, rmt):
        o = _other_clone(ctx, rmt, "Bclone_" + Path(r).parent.name)
        write_json(o, MARKER_REL, base_marker)
        commit_all(o, "marker pushed from another clone")
        gout(o, "push", "-q", "origin", "HEAD:refs/heads/" + BRANCH)

    def remote_side_unfetched(r, rmt):
        o = _other_clone(ctx, rmt, "Bclone_" + Path(r).parent.name)
        gout(o, "checkout", "-q", "-b", "side")
        write_json(o, MARKER_REL, base_marker)
        commit_all(o, "marker on remote side")
        gout(o, "push", "-q", "origin", "HEAD:refs/heads/side")

    def tag_only(r, rmt):
        write_json(r, MARKER_REL, base_marker)
        commit_all(r, "marker")
        gout(r, "tag", "kept-marker")
        gout(r, "reset", "-q", "--hard", "HEAD~1")

    def result_only(r, rmt):
        write_json(r, RESULT_REL, {"kind": "result"})
        commit_all(r, "result without marker")
        gout(r, "push", "-q", "origin", "HEAD:refs/heads/" + BRANCH)

    add("B01 marker only in the working tree (untracked)", wt)
    add("B02 marker staged only", staged)
    add("B03 marker committed on another local branch", side_branch)
    add("B04 marker committed, then deleted (linear history)", deleted)
    add("B05 marker committed and deleted on a side branch merged --no-ff, side ref deleted", merged_away)
    add("B06 marker and result committed", with_result)
    add("B07 marker committed, result only in the working tree", result_wt)
    add("B08 marker on a remote branch 'side', fetched (remote-tracking ref)", remote_side_fetched)
    add("B09 marker on the remote branch main only (local not fetched)", remote_main_only)
    add("B10 marker reachable only from a local tag", tag_only)
    add("B11 marker on a remote branch 'side', never fetched", remote_side_unfetched, info=True)
    add("B12 result without any marker", result_only, info=True)
    for i, (name, prep, info) in enumerate(S):
        repo, remote = new_scenario(ctx, "B%02d" % (i + 1))
        setup_st10(repo, remote)
        prep(repo, remote)
        h0, r0 = head(repo), remote_ref(remote)
        em = m_marker(repo, remote)
        eb = m_begin(repo, remote, G["rows_h"], G["tiny"]["0"])
        res, rc, err = run_probe(ctx, repo, ["marker", "begin:" + G["tiny"]["0"]])
        print(" %s" % name)
        for (op, kind, detail), ex in zip(res, [em, eb]):
            B.cmp(name[:3], op.split(":")[0], None if info else ex[0], kind, detail, ex[1])
        if res[1][1] != "ACCEPT":
            B.post("no marker commit, HEAD and remote main unchanged", head(repo) == h0 and remote_ref(remote) == r0)


def _other_clone(ctx, remote, name):
    o = ctx["base"] / "s" / name
    gout(ctx["base"], "clone", "-q", str(remote), str(o))
    for k, v in (("user.name", "x"), ("user.email", "x@invalid"), ("commit.gpgsign", "false")):
        gout(o, "config", k, v)
    return o


def scen_begin_misc(ctx, B):
    print("\n== D. begin: again in the same process, push rejected, remote unreachable, staged changes, base hash, dirty tree")
    T = G["tiny"]
    repo, remote = new_scenario(ctx, "D1_twice")
    setup_st10(repo, remote)
    e = m_begin(repo, remote, G["rows_h"], T["0"])
    res, rc, err = run_probe(ctx, repo, ["begin:" + T["0"], "begin:" + T["0"]])
    print(" D1 begin twice in one process")
    B.cmp("D1", "begin#1", e[0], res[0][1], res[0][2], e[1])
    B.cmp("D1", "begin#2", m_marker(repo, remote)[0], res[1][1], res[1][2], "marker committed by begin#1, no result")
    B.post("one marker commit only", gout(repo, "rev-list", "--count", "HEAD") == "3")

    for name, prep in (("D2 push rejected: remote main diverged (another clone pushed)", "diverged"),
                       ("D3 push rejected: remote pre-receive hook refuses", "hook")):
        repo, remote = new_scenario(ctx, name[:2])
        setup_st10(repo, remote)
        if prep == "diverged":
            o = _other_clone(ctx, remote, "D2_other")
            (o / "other.txt").write_text("diverging commit\n")
            commit_all(o, "diverging")
            gout(o, "push", "-q", "origin", "HEAD:refs/heads/" + BRANCH)
        else:
            hk = remote / "hooks" / "pre-receive"
            hk.write_text("#!/bin/sh\necho 'auditor: pushes refused' >&2\nexit 1\n")
            hk.chmod(0o755)
        h0, r0 = head(repo), remote_ref(remote)
        e = m_begin(repo, remote, G["rows_h"], T["0"])
        res, rc, err = run_probe(ctx, repo, ["begin:" + T["0"], "eval:N:0"])
        print(" " + name)
        B.cmp(name[:2], "begin", e[0], res[0][1], res[0][2], e[1])
        B.cmp(name[:2], "eval:N:0", "REFUSE", norm(res[1][1], res[1][2]), res[1][2], "begin did not return a session")
        h1 = head(repo)
        files = gout(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", "%s^" % h1, h1).split() if h1 != h0 else []
        B.post("marker committed locally on top of the previous HEAD (only the marker path), remote unchanged",
               h1 != h0 and files == [MARKER_REL] and remote_ref(remote) == r0)
        e2 = m_begin(repo, remote, G["rows_h"], T["0"])
        res2, rc, err = run_probe(ctx, repo, ["begin:" + T["0"]])
        B.cmp(name[:2], "begin again", e2[0], res2[0][1], res2[0][2], e2[1])

    repo, remote = new_scenario(ctx, "D4_unreachable")
    setup_st10(repo, remote)
    gout(repo, "remote", "set-url", "origin", str(ctx["base"] / "s" / "no-such-remote.git"))
    h0 = head(repo)
    res, rc, err = run_probe(ctx, repo, ["marker", "begin:" + T["0"]])
    print(" D4 remote unreachable")
    for op, kind, detail in res:
        B.cmp("D4", op.split(":")[0], "REFUSE", kind, detail, "absence of a marker on the remote cannot be verified")
    B.post("nothing written", head(repo) == h0 and not (repo / MARKER_REL).exists())

    repo, remote = new_scenario(ctx, "D5_staged")
    setup_st10(repo, remote)
    (repo / "staged.txt").write_text("staged\n")
    gout(repo, "add", "staged.txt")
    h0, r0 = head(repo), remote_ref(remote)
    e = m_begin(repo, remote, G["rows_h"], T["0"])
    res, rc, err = run_probe(ctx, repo, ["begin:" + T["0"]])
    print(" D5 staged change in the index")
    B.cmp("D5", "begin", e[0], res[0][1], res[0][2], e[1])
    nothing_written(B, repo, remote, h0, r0)

    repo, remote = new_scenario(ctx, "D6_basehash")
    setup_st10(repo, remote)
    h0, r0 = head(repo), remote_ref(remote)
    res, rc, err = run_probe(ctx, repo, ["begin:xyz", "begin:" + "A" * 64])
    print(" D6 base model hash not 64 lower-case hex")
    B.cmp("D6", "begin:xyz", m_begin(repo, remote, G["rows_h"], "xyz")[0], res[0][1], res[0][2], "base model hash")
    B.cmp("D6", "begin:AAAA..", None, res[1][1], res[1][2], "upper-case hex: no rule in the rulings")
    nothing_written(B, repo, remote, h0, r0)

    repo, remote = new_scenario(ctx, "D7_dirty")
    setup_st10(repo, remote)
    (repo / "README.audit").write_text("modified, not staged\n")
    (repo / "untracked.txt").write_text("untracked\n")
    h0, r0 = head(repo), remote_ref(remote)
    st10_b, aud_b = blob_at(repo, "HEAD", ST10_REL), blob_at(repo, "HEAD", AUD_REL)
    e = m_begin(repo, remote, G["rows_h"], T["0"])
    res, rc, err = run_probe(ctx, repo, ["begin:" + T["0"]])
    print(" D7 unstaged modification and an untracked file outside the code paths")
    B.cmp("D7", "begin", e[0], res[0][1], res[0][2], e[1])
    mc = re.search(r"marker commit ([0-9a-f]{40})", res[0][2])
    if mc:
        check_marker_commit(B, repo, remote, mc.group(1), h0, r0, T["0"], st10_b, aud_b)
        B.post("modified and untracked files left as they were (not committed)",
               sorted(git(repo, "status", "--porcelain").stdout.decode().splitlines()) == [" M README.audit", "?? untracked.txt"])


HOOK = """#!/bin/sh
[ -f "{flag}" ] && exit 0
touch "{flag}"
unset GIT_DIR GIT_INDEX_FILE GIT_WORK_TREE GIT_PREFIX
cat > /dev/null
exec /usr/bin/env python3 -I "{action}" "{repo}" "{mode}"
"""

ACTION = r'''import json, subprocess, sys, pathlib
repo, mode = pathlib.Path(sys.argv[1]), sys.argv[2]
def g(*a):
    subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True)
def rw(rel, fn):
    p = repo / rel
    o = json.loads(p.read_text())
    fn(o)
    p.write_text(json.dumps(o, indent=2, sort_keys=True) + "\n")
if mode == "noop":
    sys.exit(0)
if mode == "st10_wt":
    p = repo / "%(st10)s"
    p.write_bytes(p.read_bytes() + b"\n")
    sys.exit(0)
if mode == "st10_commit":
    rw("%(st10)s", lambda o: o.update(note="changed after the marker"))
elif mode == "marker_commit":
    rw("%(marker)s", lambda o: o["test_files_sha256"].update({"test_qa.jsonl": "c" * 64}))
elif mode == "aud_commit":
    rw("%(aud)s", lambda o: o.update(note="changed after the marker"))
g("add", "-A")
g("commit", "-q", "-m", "changed by the auditor's pre-push hook")
''' % {"st10": ST10_REL, "marker": MARKER_REL, "aud": AUD_REL}


def scen_hooks(ctx, B):
    print("\n== E. changes between begin and evaluate in the same process (a pre-push hook of the temp repository acts "
          "once, during begin's push, after the marker commit)")
    T = G["tiny"]
    act = ctx["base"] / "ic2_hook_action.py"
    act.write_text(ACTION)
    for code, mode, label in (("E0", "noop", "control: hook runs, changes nothing"),
                              ("E1", "st10_wt", "ST10 record changed in the working tree after the marker"),
                              ("E2", "st10_commit", "ST10 record changed and committed after the marker (still valid)"),
                              ("E3", "marker_commit", "marker's TEST file hashes changed and committed (TEST rows != marker)"),
                              ("E4", "aud_commit", "auditor's count file changed and committed after the marker")):
        repo, remote = new_scenario(ctx, code + "_" + mode)
        setup_st10(repo, remote)
        flag = repo.parent / ("hook_ran_" + mode)
        hk = repo / ".git" / "hooks" / "pre-push"
        hk.write_text(HOOK.format(flag=flag, action=act, repo=repo, mode=mode))
        hk.chmod(0o755)
        h0, r0 = head(repo), remote_ref(remote)
        e = m_begin(repo, remote, G["rows_h"], T["0"])
        ops = ["begin:" + T["0"], "eval:N:0", "eval:F-%s-seed202:1" % SELECTED["F"]]
        res, rc, err = run_probe(ctx, repo, ops)
        print(" %s %s (hook ran: %s)" % (code, label, flag.exists()))
        B.cmp(code, "begin", e[0], res[0][1], res[0][2], e[1])
        mc = re.search(r"marker commit ([0-9a-f]{40})", res[0][2])
        mc = mc.group(1) if mc else None
        for (op, kind, detail), (ex, why) in zip(res[1:], m_evals(repo, mc, ops[1:], T)):
            B.cmp(code, op, ex, norm(kind, detail), detail, why)
        B.post("hook ran exactly during begin's push; remote main == marker commit", flag.exists() and remote_ref(remote) == mc)


def main():
    repo, py, base = Path(sys.argv[1]).resolve(), sys.argv[2], Path(sys.argv[3]).resolve()
    if base == repo or repo in base.parents:
        raise SystemExit("base dir must be outside the repository")
    if base.exists():
        shutil.rmtree(base)
    base.mkdir(parents=True)
    ctx = {"repo": repo, "py": py, "base": base, "probe": str(repo / PROBE_REL)}
    print("probe %s sha256 %s | HEAD %s | staged tree %s" % (PROBE_REL, sha((repo / PROBE_REL).read_bytes()),
                                                            gout(repo, "rev-parse", "HEAD"), gout(repo, "write-tree")))
    frozen, content, limits, ss, ok = read_frozen(repo)
    names, test_models = plan_names(ss, SELECTED)
    print("my training plan: %d runs | my TEST models: %d %s" % (len(names), len(test_models), test_models))
    ok &= len(names) == 30 and len(set(names)) == 30 and len(test_models) == 16
    G.update(frozen=frozen, content=content, limits=limits, plan=names, test_models=test_models)
    td = base / "test_dir"
    td.mkdir()
    (td / "test_qa.jsonl").write_bytes(jsonl_bytes(SYN_QA))
    (td / "general_test.jsonl").write_bytes(jsonl_bytes(SYN_GT))
    G["rows_h"] = {n: sha((td / n).read_bytes()) for n in ("test_qa.jsonl", "general_test.jsonl")}
    print("synthetic TEST files (written by me, outside the repository): %s" % G["rows_h"])
    ctx["test_dir"] = td
    scratch = base / "s" / "tiny"
    scratch.mkdir(parents=True)
    gout(scratch, "init", "-q")
    res, rc, err = run_probe(ctx, scratch, ["tinysha:0", "tinysha:1", "tinysha:4", "tinysha:7"])
    G["tiny"] = {op.split(":")[1]: detail for op, kind, detail in res}
    print("tiny model state hashes from the probe (random 2-layer models, seeds 0 1 4 7): %s" % G["tiny"])
    ok &= all(re.fullmatch(r"[0-9a-f]{64}", v) for v in G["tiny"].values()) and len(set(G["tiny"].values())) == 4
    ctx["template"] = make_template(ctx)
    print("template repository: code commit %s | gate0 sha256 %s | freeze sha256 %s" % (G["c0"], G["g0sha"], G["selsha"]))
    B = Book()
    scen_st10(ctx, B)
    scen_main(ctx, B)
    scen_markers(ctx, B)
    scen_begin_misc(ctx, B)
    scen_hooks(ctx, B)
    print("\nsummary: compared operations DIFFERENT %d | INFO (no expectation) %d | post-checks FAILED %d" % (
        B.bad, B.info, B.post_bad))
    return bool(ok and B.bad == 0 and B.post_bad == 0)


run(main)
