"""ic4_01 (implementation stage C, C1 work commit, round 3, task 1): black-box comparison of the TEST gates with my own
model. Successor of my ic3_01_gate_scenarios.py (round 2): the same scenarios, the expectations updated to the round-3
semantics, and the scenarios the round-3 instruction adds. The probe run is the staged one
(reports/impl_c/c1_gate_probe.py as in the index; no other probe can be given).

My model (protocol v1.1 section 3 L6 row, section 8 step 8, section 11 ST10; Review Gate supplementary rulings 3-5 of
2026-11-24, tasks/IMPL_C_OWNER_MESSAGE.md; outcome classes and environment conditions as listed by the caller for
rounds 2 and 3; not taken from the Executor's code):
  ST10 gate  (ruling 3): the ST10 record (raw counts of the TEST part of L3a, L3b, L4, L5, L6; sha256 of test_qa.jsonl
             and general_test.jsonl; code commit) must be committed (HEAD blob == working tree), be a JSON object and a
             formal st10 record of the frozen commit, bound to the authorization (sha256 of the committed Gate 0 and
             freeze records), name the TEST files that are evaluated, name a code commit that is HEAD or an ancestor,
             and hold exactly five non-negative integer counts. The data-auditor's count must be committed, a JSON
             object of the frozen commit, for the same general_test.jsonl, an integer. Any of these missing -> REFUSE.
             Counts judged by me against the frozen limits (frozen-commit SPLIT_MANIFEST.json); a count above its limit,
             or Executor L6 != data-auditor L6 -> ST10 stop, BLOCKED. Self-reported flags are ignored.
  records    : every TEST path (begin, evaluate) re-reads the committed Gate 0 and freeze records; a record that is not
             a committed JSON object of its kind (e.g. a JSON array, a string, null) -> REFUSE (round 3).
  TEST once  (ruling 4): a marker anywhere (working tree, index, any commit reachable from any local ref -- branches,
             remote-tracking refs, tags -- or from any reflog entry (round 3), any commit reachable from any branch of
             the remote, also when deleted later, also on a side branch merged back) -> no new evaluation: a result
             anywhere -> EVALUATED (refused, TestAlreadyEvaluated; also a result without a marker); a marker without a
             result -> BLOCKED (crash case). Environment (round 3, as stated by the caller): a shallow clone, a
             checked-out branch other than the pilot's (here main; stated for op marker and for begin), a remote that
             cannot be reached -> BLOCKED, nothing written. Before writing the marker: nothing staged (BLOCKED), a
             commit can be made (committer identity; BLOCKED, nothing written), the push will be a fast-forward
             (remote branch tip absent or an ancestor of HEAD; BLOCKED, nothing written), a dry-run push is accepted
             (a local pre-push hook that refuses every push: BLOCKED, nothing written). A push rejected only when it is
             really made (remote pre-receive hook, or a pre-push hook that refuses the second push) is only seen after
             the marker commit: BLOCKED, the local marker commit stays and refuses any later begin. Pushed without
             tags. The marker's remote field and every refusal text hold no user information of the URL (a secret
             in the URL never appears in the marker or in the probe's output).
  B25        : while an interpretation is pending, every TEST path (begin, evaluate) refuses (probe without
             --interpretations-ruled).
  evaluate   : session begun in this process; committed marker, ST10 record and auditor's count unchanged since
             begin; checkpoint one of the 16 TEST models (N; F, L, A with the selected configuration and S, Y, three
             seeds each); model state hash == the marker's hash of that checkpoint -> passes every gate (probe:
             ACCEPTED-BY-GATES at require_gpu). On the CPU the call stops at require_gpu before the checkpoint is
             claimed, so the same eval passes again; a checkpoint claimed by op gate (require_test_session then
             claim_checkpoint) is refused afterwards (eval and gate).
  probe guard: the probe refuses this repository and any clone whose origin is leotree2020/OpenMythos (exit != 0,
             no operation line, nothing written); otherwise it prints the repository id it set as CANONICAL_REPO,
             which must equal my own reading of origin's URL (last two path components, user information and .git
             removed).
Expectations whose only source is the caller's round-3 description (not the protocol or the rulings) are marked
"(stated r3)" in the model column.
All expectations are computed before the probe runs (repository state read with git plumbing, read-only; for evaluate
calls after a begin in the same run: from my expected marker -- my 30 checkpoint hashes + N, my 16 TEST models -- and
the scenario's planned change); for the scenarios new in round 3 they are also printed ("pre-registered") before the
probe is started. The state after the run is checked against what the expectation assumed.
The Executor's probe reports/impl_c/c1_gate_probe.py is run only as a subprocess (python -I -B); nothing of the
package is imported, called or copied. All TEST rows are synthetic rows written by this script; no real TEST row, no
eval_sets.jsonl, no model weights (the probe's tiny models are random), no GPU.
Probe outcome classes: ACCEPT | REFUSE | STOP <code> <status> | EVALUATED (= "ERROR TestAlreadyEvaluated") | ERROR.
usage: python -I ic4_01_gate_scenarios.py <repo_root> <python_for_probe> <base_dir_outside_repo>"""
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
RULED_LINE = "probe: interpretations.pending replaced by a function returning [] (--interpretations-ruled)"
CANON_PREFIX = "probe: testgate.CANONICAL_REPO = "
SECRET = "s3cr3t-auditor-token-ic4"
BASE_ENV = {"GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0"}
G = {}                                                 # frozen facts read by me; filled in main()


# --------------------------------------------------------------------------------------------- small helpers

def git(cwd, *args, env=None):
    e = dict(os.environ, **BASE_ENV)
    if env:
        e.update(env)
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, env=e)


def gout(cwd, *args, env=None):
    r = git(cwd, *args, env=env)
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
    if remote is None or not (Path(remote) / "HEAD").exists():
        return None
    r = git(remote, "rev-parse", "--verify", "-q", ref)
    return r.stdout.decode().strip() if r.returncode == 0 else None


def blob_at(root, rev, rel):
    r = git(root, "cat-file", "blob", "%s:%s" % (rev, rel))
    return r.stdout if r.returncode == 0 else None


def has_path(root, rev, rel):
    return git(root, "cat-file", "-e", "%s:%s" % (rev, rel)).returncode == 0


def set_identity(repo):
    for k, v in (("user.name", "data-auditor-ic4"), ("user.email", "auditor@invalid"), ("commit.gpgsign", "false"),
                 ("tag.gpgsign", "false")):
        gout(repo, "config", k, v)


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


def m_json_object(b):
    try:
        o = json.loads(b)
    except ValueError:
        return None
    return o if isinstance(o, dict) else None


def m_st10(repo, rows_h):
    """My ST10 gate: ('ACCEPT'|'REFUSE'|'STOP ST10 BLOCKED', reason)."""
    b, why = m_committed(repo, ST10_REL)
    if b is None:
        return "REFUSE", "ST10 record " + why
    rec = m_json_object(b)
    if rec is None:
        return "REFUSE", "ST10 record is not a JSON object"
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
    if not isinstance(counts, dict) or sorted(counts) != sorted(CHECKS) or \
            not all(is_int_count(v) for v in counts.values()):
        return "REFUSE", "counts not five non-negative integers"
    ab, why = m_committed(repo, AUD_REL)
    if ab is None:
        return "REFUSE", "auditor count " + why
    aud = m_json_object(ab)
    if aud is None:
        return "REFUSE", "auditor count is not a JSON object"
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
    return [c for c in r.stdout.decode().split() if has_path(repo_or_remote, c, rel)]


def remote_ok(remote):
    return remote is not None and (Path(remote) / "HEAD").exists()


def head_ref(repo):
    """The checked-out branch, read from .git/HEAD (None when HEAD is detached)."""
    t = (Path(repo) / ".git" / "HEAD").read_text().strip()
    return t[len("ref: refs/heads/"):] if t.startswith("ref: refs/heads/") else None


def is_shallow(repo):
    return (Path(repo) / ".git" / "shallow").exists()


def my_strip_userinfo(url):
    """My own: the URL without the user information of its authority (scheme://user:pw@host/p -> scheme://host/p)."""
    if "://" not in url:
        return url
    scheme, rest = url.split("://", 1)
    host, sep, path = rest.partition("/")
    if "@" in host:
        host = host.rsplit("@", 1)[1]
    return scheme + "://" + host + sep + path


def my_repo_id(url):
    """My own reading of '<owner>/<name>' of a remote: the last two path components, user information and .git removed."""
    u = url.strip()
    if "://" in u:
        u = u.split("://", 1)[1].partition("/")[2]
    elif re.match(r"^[^/@]+@[^/:]+:", u):
        u = u.split(":", 1)[1]
    parts = [p for p in u.replace(":", "/").split("/") if p]
    name = "/".join(parts[-2:])
    return name[:-4] if name.endswith(".git") else name


def m_env(repo, remote):
    """Round-3 environment conditions: shallow clone; checked-out branch not main (stated r3, op marker and begin);
    remote not reachable. -> ('STOP - BLOCKED', why) or None."""
    if is_shallow(repo):
        return "STOP - BLOCKED", "shallow clone: history incomplete"
    if head_ref(repo) != BRANCH:
        return "STOP - BLOCKED", "checked-out branch %r is not %s (stated r3)" % (head_ref(repo), BRANCH)
    if not remote_ok(remote):
        return "STOP - BLOCKED", "remote not reachable: its content is unknown"
    return None


def m_records(repo):
    """The committed Gate 0 and freeze records must be committed JSON objects of their kind. -> (REFUSE, why) or None."""
    for rel, kind in ((G0_REL, "gate0"), (SEL_REL, "selection_freeze")):
        b, why = m_committed(repo, rel)
        if b is None:
            return "REFUSE", "%s %s" % (rel.split("/")[-1], why)
        o = m_json_object(b)
        if o is None:
            return "REFUSE", "%s is not a JSON object" % rel.split("/")[-1]
        if o.get("kind") != kind or o.get("mode") != "formal" or o.get("frozen_commit") != G["frozen"]:
            return "REFUSE", "%s is not a formal %s record of the frozen commit" % (rel.split("/")[-1], kind)
    return None


def m_found(repo, remote, rel):
    p = Path(repo)
    out = []
    if (p / rel).exists():
        out.append("working tree")
    if git(repo, "cat-file", "-e", ":%s" % rel).returncode == 0:
        out.append("index")
    out += ["local commit %s" % c[:12] for c in commits_with(repo, rel, ["--all", "--reflog"])]
    out += ["remote commit %s" % c[:12] for c in commits_with(remote, rel, ["--branches"])]
    return out


def m_marker(repo, remote):
    """My 'TEST once' check: ('ACCEPT'|'EVALUATED'|'STOP - BLOCKED', where)."""
    env = m_env(repo, remote)
    if env:
        return env
    places, res = m_found(repo, remote, MARKER_REL), m_found(repo, remote, RESULT_REL)
    if res:
        return "EVALUATED", "result in %s" % ", ".join(sorted(set(res))[:3])
    if places:
        return "STOP - BLOCKED", "marker without result in %s" % ", ".join(sorted(set(places))[:3])
    return "ACCEPT", None


def can_commit(repo, env=None):
    """A commit object can be made (committer identity): git commit-tree (writes a dangling object only)."""
    t = gout(repo, "rev-parse", "HEAD^{tree}")
    r = git(repo, "commit-tree", t, "-p", "HEAD", "-m", "auditor identity check", env=env)
    return r.returncode == 0, " ".join(r.stderr.decode(errors="replace").split())[:160]


def m_begin(repo, remote, rows_h, base_sha, ruled=True, env=None, hook=None):
    """('ACCEPT'|..., why, written) with written in {'none', 'local', 'pushed'}. hook: None | 'dry' (a local pre-push
    hook refuses every push, the dry run included) | 'real' (it accepts the first push, the dry run, and refuses the
    next one, the real push)."""
    k, why = m_marker(repo, remote)
    if k != "ACCEPT":
        return k, why, "none"
    rr = m_records(repo)
    if rr:
        return rr[0], rr[1], "none"
    if not ruled:
        return "REFUSE", "interpretation B25 pending", "none"
    k, why = m_st10(repo, rows_h)
    if k != "ACCEPT":
        return k, why, "none"
    if not re.fullmatch(r"[0-9a-f]{64}", base_sha):
        return "REFUSE", "base model hash", "none"
    if git(repo, "diff", "--cached", "--quiet").returncode != 0:
        return "STOP - BLOCKED", "staged changes", "none"
    ok, err = can_commit(repo, env)
    if not ok:
        return "STOP - BLOCKED", "no commit possible (%s)" % err, "none"
    rh = remote_ref(remote)
    if rh is not None and git(repo, "merge-base", "--is-ancestor", rh, "HEAD").returncode != 0:
        return "STOP - BLOCKED", "push would not be a fast-forward", "none"
    if hook == "dry":
        return "STOP - BLOCKED", "the dry-run push is refused (local pre-push hook)", "none"
    if (Path(remote) / "hooks" / "pre-receive").exists() or hook == "real":
        return "STOP - BLOCKED", "the push is refused (seen only when really pushing)", "local"
    return "ACCEPT", None, "pushed"


def m_evals_pre(ops, T, begin_ok, ruled=True, changed=None, base_sha=None):
    """Expectations of evaluate / gate calls after a begin in the same run, computed before the run from my expected
    marker (my checkpoint hashes + N = base_sha, my 16 TEST models) and the planned change after the marker."""
    out, claimed = [], set()
    ck = dict(G["ck"], N=base_sha)
    for op in ops:
        kind, _, arg = op.partition(":")
        name, _, s = arg.partition(":")
        h = T.get(s) if kind == "eval" else s
        if not ruled:
            out.append(("REFUSE", "interpretation B25 pending"))
        elif not begin_ok:
            out.append(("REFUSE", "no session of this process"))
        elif changed:
            out.append(("REFUSE", "%s after the marker" % changed))
        elif name not in G["test_models"]:
            out.append(("REFUSE", "not one of the 16 TEST models"))
        elif name in claimed:
            out.append(("REFUSE", "already claimed in this session"))
        elif h != ck.get(name):
            out.append(("REFUSE", "model hash != marker"))
        else:
            out.append(("ACCEPT", "passes every gate; CPU stops at require_gpu" + (", claimed" if kind == "gate" else "")))
            if kind == "gate":
                claimed.add(name)
    return out


# ---------------------------------------------------------------------------------------------- probe runner

def classify(op, kind, detail):
    if kind == "ERROR":
        if detail.startswith("TestAlreadyEvaluated:"):
            return "EVALUATED"
    if kind == "ACCEPT" and "ACCEPTED-BY-GATES" in detail:
        return "ACCEPT"
    return kind


def origin_url(repo):
    r = git(repo, "config", "--get", "remote.origin.url")
    return r.stdout.decode().strip() if r.returncode == 0 else None


def run_probe(ctx, repo, ops, ruled=True, env=None, test_dir=None, expect=None):
    """Runs the staged probe; returns ([(op, class, detail)], exit code, stderr tail). The complete stdout+stderr of the
    last run is kept in ctx['last_text']. expect: [(op, (expected, why))] printed before the probe is started."""
    if expect:
        for op, (e, why) in expect:
            print("    pre-registered: %-34s -> %-18s (%s)" % (op[:34], "INFO" if e is None else e, why))
        sys.stdout.flush()
    cmd = [ctx["py"], "-I", "-B", ctx["probe"]] + (["--interpretations-ruled"] if ruled else []) + [
        str(repo), str(test_dir or ctx["test_dir"]), *ops]
    e = dict(os.environ, **BASE_ENV)
    if env:
        e.update(env)
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=ctx["base"], timeout=900, env=e)
    ctx["last_text"] = r.stdout + r.stderr
    ctx["runs"] = ctx.get("runs", 0) + 1
    ctx["secret_seen"] = ctx.get("secret_seen", 0) + (SECRET in r.stdout + r.stderr)
    lines = r.stdout.rstrip("\n").split("\n")
    ctx["ruled_line_ok"] = ctx.get("ruled_line_ok", True) and ((lines[:1] == [RULED_LINE]) == ruled)
    canon = [ln[len(CANON_PREFIX):] for ln in lines if ln.startswith(CANON_PREFIX)]
    ou = origin_url(repo)
    if ou is not None and canon:
        got = canon[0].split(" (REPO's origin)")[0].strip("'")
        if got != my_repo_id(ou):
            ctx.setdefault("canon_bad", []).append((str(repo), ou, got, my_repo_id(ou)))
        ctx["canon_checked"] = ctx.get("canon_checked", 0) + 1
    elif ou is not None and not canon:
        ctx.setdefault("canon_bad", []).append((str(repo), ou, None, my_repo_id(ou)))
    out, rest = [], list(lines)
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
            out.append((op, classify(op, kind, detail), detail))
    return out, r.returncode, (r.stderr.strip().split("\n")[-1] if r.stderr.strip() else "")


def introduced_marker(repo, h0):
    """Commits after h0 (reachable from HEAD) that add the marker path: (marker commit or None, list)."""
    r = git(repo, "rev-list", "--reverse", "HEAD" if h0 is None else "%s..HEAD" % h0)
    cs = [c for c in r.stdout.decode().split() if has_path(repo, c, MARKER_REL)
          and not (git(repo, "rev-parse", "-q", "--verify", c + "^").returncode == 0 and has_path(repo, c + "^", MARKER_REL))]
    return (cs[0] if len(cs) == 1 else None), cs


# -------------------------------------------------------------------------------------------- repositories

def make_template(ctx):
    base = ctx["base"]
    t = base / "template"
    remote, repo = t / "remote.git", t / "repo"
    t.mkdir(parents=True)
    gout(t, "init", "-q", "--bare", "-b", BRANCH, str(remote))
    repo.mkdir()
    gout(repo, "init", "-q", "-b", BRANCH)
    set_identity(repo)
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


def other_clone(ctx, remote, name, args=()):
    o = ctx["base"] / "s" / name
    gout(ctx["base"], "clone", "-q", *args, str(remote), str(o))
    set_identity(o)
    return o


# ------------------------------------------------------------------------------------------------- reporting

class Book:
    def __init__(self):
        self.bad, self.info, self.post_bad, self.defect, self.same = 0, 0, 0, 0, 0

    def cmp(self, scen, op, expected, observed, detail, why=None):
        exp = None if expected is None else (expected if isinstance(expected, (set, frozenset)) else {expected})
        if observed in ("ERROR", "MISSING"):
            self.defect += 1
        if exp is None:
            verdict = "INFO"
            self.info += 1
        else:
            verdict = "same" if observed in exp else "DIFFERENT"
            if verdict == "same":
                self.same += 1
            else:
                self.bad += 1
        e = "INFO" if exp is None else "|".join(sorted(exp))
        print("  [%s] %-34s expected %-18s observed %-18s %s%s" % (verdict, op[:34], e, observed,
                                                                (detail or "")[:320], ("  (model: %s)" % why) if why else ""))

    def post(self, what, ok):
        print("    post-check %-100s %s" % (what, "ok" if ok else "FAILED"))
        if not ok:
            self.post_bad += 1


def nothing_written(B, repo, remote, h0, r0, marker_before=False):
    B.post("nothing written: marker file %s, HEAD unchanged, remote %s unchanged" % (
        "as before" if marker_before else "absent", BRANCH),
        (Path(repo) / MARKER_REL).exists() == marker_before and head(repo) == h0 and remote_ref(remote) == r0)


def begin_result(B, scen, repo, remote, h0, res0, expected):
    """Compare a begin outcome. Returns the marker commit the probe printed (ACCEPT), else None; for ACCEPT the
    probe's model count (read by the probe from the committed marker) must be 16."""
    op, kind, detail = res0
    B.cmp(scen, "begin", expected[0], kind, detail, expected[1])
    mc = None
    if kind == "ACCEPT":
        m = re.search(r"marker commit ([0-9a-f]{40}) models (\d+)", detail)
        mc = m.group(1) if m else None
        B.post("probe printed the marker commit and 'models 16' (%s)" % ((m.groups() if m else None),),
               m is not None and m.group(2) == str(len(G["test_models"])))
        mc2, cs = introduced_marker(repo, h0)
        B.post("exactly one new commit adds the marker and it is the printed one (%s)" % [c[:12] for c in cs], mc2 == mc)
    return mc


def check_marker_commit(B, repo, remote, mc, h_before, r_before, base_sha, st10_b, aud_b, local_tags=False,
                        want_url=None):
    """Post-checks of an accepted begin (ruling 4 and 'only counts and hashes'). want_url: the remote field I expect
    (default: the remote's path, as origin is set in my scenarios)."""
    want_url = str(remote) if want_url is None else want_url
    B.post("marker commit == local HEAD == remote refs/heads/%s (ls-remote)" % BRANCH,
           mc == head(repo) == remote_ref(remote) == gout(repo, "ls-remote", "origin", "refs/heads/" + BRANCH).split()[0])
    B.post("marker commit's only parent is the previous HEAD", gout(repo, "rev-list", "--parents", "-n", "1", mc).split()[1:] == [h_before])
    files = gout(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", "%s^" % mc, mc).split()
    B.post("marker commit changes exactly [%s] (got %s)" % (MARKER_REL, files), files == [MARKER_REL])
    B.post("fast-forward of the previous remote ref (no force)", r_before is None or
           git(repo, "merge-base", "--is-ancestor", r_before, mc).returncode == 0)
    B.post("no tags on the remote%s" % ("" if local_tags else " nor in the repository"),
           gout(remote, "tag", "-l") == "" and gout(repo, "ls-remote", "--tags", "origin") == ""
           and (local_tags or gout(repo, "tag", "-l") == ""))
    mb = blob_at(repo, mc, MARKER_REL)
    m = json.loads(mb)
    B.post("marker keys %s" % sorted(m), True)
    want_ck = dict(G["ck"], N=base_sha)
    B.post("marker frozen_commit, authorization == mine", m.get("frozen_commit") == G["frozen"] and
           m.get("authorization") == {"gate0_record_sha256": G["g0sha"], "selection_record_sha256": G["selsha"]})
    B.post("marker remote == %r (got %r), branch == %s" % (want_url, m.get("remote"), BRANCH),
           m.get("remote") == want_url and m.get("branch") == BRANCH)
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


# -------------------------------------------------------------------------------------------------- scenarios

def scen_st10(ctx, B):
    print("\n== A. ST10 gate: op st10 and begin, one defect per scenario (fresh repository each; probe with "
          "--interpretations-ruled)")
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
    add("A06b record is a JSON string", rec=b"\"st10\"\n")
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
    add("A58b auditor file is a JSON array", aud=b"[0]\n")
    add("A58c auditor file does not parse", aud=b"{l6\n")
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
        ops = ["st10"] if name.startswith("A61") else ["st10", "begin:" + G["tiny"]["0"]]
        res, rc, err = run_probe(ctx, repo, ops)
        print(" %s" % name)
        B.cmp(name[:4], "st10", None if info else e_st10[0], res[0][1], res[0][2], e_st10[1])
        if len(ops) > 1:
            B.cmp(name[:4], "begin", None if info else e_begin[0], res[1][1], res[1][2], e_begin[1])
            if res[1][1] != "ACCEPT":
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
    print("\n== C. every condition holds: begin, marker commit, evaluate / gate calls (one repository); K: other clones")
    repo, remote = new_scenario(ctx, "C_main")
    setup_st10(repo, remote)
    stale = other_clone(ctx, remote, "K2_stale_clone")
    stale_sb = other_clone(ctx, remote, "K3_stale_single_branch_clone", ("--single-branch", "-b", BRANCH))
    T = G["tiny"]
    print(" C0 evaluate and gate before any begin (no session)")
    ops0 = ["eval:N:0", "gate:N:%s" % T["0"]]
    exp0 = m_evals_pre(ops0, T, begin_ok=False)
    res, rc, err = run_probe(ctx, repo, ops0)
    for (op, kind, detail), (e, why) in zip(res, exp0):
        B.cmp("C0", op, e, kind, detail, why)
    h0, r0 = head(repo), remote_ref(remote)
    st10_b, aud_b = blob_at(repo, "HEAD", ST10_REL), blob_at(repo, "HEAD", AUD_REL)
    e_begin = m_begin(repo, remote, G["rows_h"], T["0"])
    F, L = SELECTED["F"], SELECTED["L"]
    ck303 = G["ck"]["F-%s-seed303" % F]
    ops = ["eval:N:7", "eval:N:0", "eval:N:0", "eval:F-%s-seed202:1" % F, "eval:F-%s-seed202:1" % F,
           "eval:F-F1-seed101:4", "eval:Z-Z9-seed1:0", "eval:L-%s-seed303:1" % L,
           "gate:F-%s-seed303:%s" % (F, ck303), "gate:F-%s-seed303:%s" % (F, ck303), "eval:F-%s-seed303:1" % F,
           "gate:S-%s-seed101:%s" % (F, "f" * 64), "gate:N:%s" % T["0"], "eval:N:0", "gate:N:%s" % T["0"],
           "eval:F-%s-seed202:1" % F]
    exp = m_evals_pre(ops, T, begin_ok=e_begin[0] == "ACCEPT", base_sha=T["0"])
    res, rc, err = run_probe(ctx, repo, ["begin:" + T["0"]] + ops)
    print(" C1 begin + evaluate / gate calls in one process (stderr tail: %r, exit %d)" % (err[-120:], rc))
    mc = begin_result(B, "C1", repo, remote, h0, res[0], e_begin)
    if mc:
        check_marker_commit(B, repo, remote, mc, h0, r0, T["0"], st10_b, aud_b)
    for (op, kind, detail), (e, why) in zip(res[1:], exp):
        B.cmp("C1", op, e, kind, detail, why)
    B.post("evaluate / gate calls wrote nothing: HEAD == marker commit, working tree clean",
           mc is not None and head(repo) == mc and gout(repo, "status", "--porcelain") == "")
    print(" C2 another process, same repository: the session of the earlier process is gone")
    ops2 = ["eval:N:0", "begin:" + T["0"], "eval:N:0", "marker"]
    e = m_marker(repo, remote)
    exp2 = [("REFUSE", "no session in this process"), e, ("REFUSE", "begin refused: no session"), e]
    res, rc, err = run_probe(ctx, repo, ops2)
    for (op, kind, detail), ex in zip(res, exp2):
        B.cmp("C2", op.split(":")[0] if op.startswith("begin") else op, ex[0], kind, detail, ex[1])
    B.post("HEAD and remote unchanged by C2", head(repo) == mc and remote_ref(remote) == mc)
    print(" K1 a fresh clone of the remote after the marker push")
    k1 = other_clone(ctx, remote, "K1_fresh_clone")
    e = m_begin(k1, remote, G["rows_h"], T["0"])
    k1h = head(k1)
    res, rc, err = run_probe(ctx, k1, ["marker", "begin:" + T["0"]])
    for op, kind, detail in res:
        B.cmp("K1", op.split(":")[0], e[0], kind, detail, e[1])
    B.post("fresh clone: nothing committed", head(k1) == k1h)
    for code, k in (("K2", stale), ("K3", stale_sb)):
        lab = "a clone made before the marker push (stale; the marker only on the remote)" if code == "K2" else \
            "a --single-branch clone of %s made before the marker push (its origin/%s lags)" % (BRANCH, BRANCH)
        print(" %s %s" % (code, lab))
        k_head = head(k)
        e = m_begin(k, remote, G["rows_h"], T["0"])
        res, rc, err = run_probe(ctx, k, ["begin:" + T["0"]])
        B.cmp(code, "begin", e[0], res[0][1], res[0][2], e[1])
        B.post("stale clone: nothing committed, no marker file", head(k) == k_head and not (k / MARKER_REL).exists())


def scen_markers(ctx, B):
    print("\n== B. markers or results already present (ST10 holds in every scenario; ops marker and begin)")
    base_marker = {"kind": "test_evaluation_marker", "note": "planted by the data-auditor"}
    result = {"kind": "test_evaluation_result", "note": "planted by the data-auditor"}
    S = []

    def add(name, prep, info=False, repo_fn=None):
        S.append((name, prep, info, repo_fn))

    def push(r):
        gout(r, "push", "-q", "origin", "HEAD:refs/heads/" + BRANCH)

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
        push(r)

    def merged_away(rel, obj):
        def f(r, rmt):
            gout(r, "checkout", "-q", "-b", "side")
            write_json(r, rel, obj)
            commit_all(r, "%s on side" % rel)
            gout(r, "rm", "-q", rel)
            commit_all(r, "%s deleted on side" % rel)
            gout(r, "checkout", "-q", BRANCH)
            gout(r, "merge", "-q", "--no-ff", "-m", "merge side", "side")
            gout(r, "branch", "-q", "-D", "side")
            push(r)
        return f

    def merged_ours(r, rmt):
        gout(r, "checkout", "-q", "-b", "side")
        write_json(r, MARKER_REL, base_marker)
        commit_all(r, "marker on side")
        gout(r, "checkout", "-q", BRANCH)
        gout(r, "merge", "-q", "-s", "ours", "-m", "merge side, strategy ours", "side")
        gout(r, "branch", "-q", "-D", "side")
        push(r)

    def marker_main_result_merged(r, rmt):
        write_json(r, MARKER_REL, base_marker)
        commit_all(r, "marker")
        merged_away(RESULT_REL, result)(r, rmt)

    def both_merged(r, rmt):
        gout(r, "checkout", "-q", "-b", "side")
        write_json(r, MARKER_REL, base_marker)
        commit_all(r, "marker on side")
        write_json(r, RESULT_REL, result)
        commit_all(r, "result on side")
        gout(r, "rm", "-q", MARKER_REL, RESULT_REL)
        commit_all(r, "both deleted on side")
        gout(r, "checkout", "-q", BRANCH)
        gout(r, "merge", "-q", "--no-ff", "-m", "merge side", "side")
        gout(r, "branch", "-q", "-D", "side")
        push(r)

    def with_result(r, rmt):
        write_json(r, MARKER_REL, base_marker)
        write_json(r, RESULT_REL, result)
        commit_all(r, "marker and result")
        push(r)

    def result_wt(r, rmt):
        write_json(r, MARKER_REL, base_marker)
        commit_all(r, "marker")
        push(r)
        write_json(r, RESULT_REL, result)

    def remote_side(fetch, rel=MARKER_REL, obj=None):
        def f(r, rmt):
            o = other_clone(ctx, rmt, "Bclone_%s_%s" % (Path(r).parent.name, Path(r).name))
            gout(o, "checkout", "-q", "-b", "side")
            write_json(o, rel, obj or base_marker)
            commit_all(o, "%s on remote side" % rel)
            gout(o, "push", "-q", "origin", "HEAD:refs/heads/side")
            if fetch:
                gout(r, "fetch", "-q", "origin")
        return f

    def remote_main_only(r, rmt):
        o = other_clone(ctx, rmt, "Bclone_%s_%s" % (Path(r).parent.name, Path(r).name))
        write_json(o, MARKER_REL, base_marker)
        commit_all(o, "marker pushed from another clone")
        gout(o, "push", "-q", "origin", "HEAD:refs/heads/" + BRANCH)

    def tag_only(r, rmt):
        write_json(r, MARKER_REL, base_marker)
        commit_all(r, "marker")
        gout(r, "tag", "kept-marker")
        gout(r, "reset", "-q", "--hard", "HEAD~1")

    def reflog_only(r, rmt):
        write_json(r, MARKER_REL, base_marker)
        commit_all(r, "marker, then reset away (never pushed)")
        gout(r, "reset", "-q", "--hard", "HEAD~1")

    def result_only(r, rmt):
        write_json(r, RESULT_REL, result)
        commit_all(r, "result without marker")
        push(r)

    def remote_tag_only(r, rmt):
        o = other_clone(ctx, rmt, "Bclone_%s_%s" % (Path(r).parent.name, Path(r).name))
        write_json(o, MARKER_REL, base_marker)
        commit_all(o, "marker reachable from a remote tag only")
        gout(o, "push", "-q", "origin", "HEAD:refs/tags/kept-marker")

    def single_branch_clone(r, rmt):
        """the scenario's repository is replaced by a --single-branch clone (see repo_fn); then another clone
        pushes a marker to the remote branch 'side'"""
        remote_side(False)(r, rmt)

    def single_branch_lagging(r, rmt):
        remote_main_only(r, rmt)

    add("B01 marker only in the working tree (untracked)", wt)
    add("B02 marker staged only", staged)
    add("B03 marker committed on another local branch", side_branch)
    add("B04 marker committed, then deleted (linear history)", deleted)
    add("B05 marker committed and deleted on a side branch merged --no-ff, side ref deleted", merged_away(MARKER_REL, base_marker))
    add("B05s marker on a side branch merged with -s ours (merge TREESAME to main), side ref deleted", merged_ours)
    add("B05r marker committed on main; result committed and deleted on a side branch merged --no-ff", marker_main_result_merged)
    add("B05x no marker; result committed and deleted on a side branch merged --no-ff", merged_away(RESULT_REL, result))
    add("B05m marker and result committed and deleted on a side branch merged --no-ff", both_merged)
    add("B06 marker and result committed", with_result)
    add("B07 marker committed, result only in the working tree", result_wt)
    add("B08 marker on a remote branch 'side', fetched (remote-tracking ref)", remote_side(True))
    add("B09 marker on the remote branch main only (local not fetched)", remote_main_only)
    add("B10 marker reachable only from a local tag", tag_only)
    add("B11 marker on a remote branch 'side', never fetched", remote_side(False))
    add("B12 result without any marker", result_only)
    add("B16 result only on a remote branch 'side', never fetched", remote_side(False, RESULT_REL, result))
    add("B14 --single-branch clone of main; marker pushed to remote branch 'side' afterwards", single_branch_clone,
        repo_fn="single")
    add("B15 --single-branch clone of main, lagging: marker pushed to remote main afterwards", single_branch_lagging,
        repo_fn="single")
    def reflog_side_deleted(r, rmt):
        gout(r, "checkout", "-q", "-b", "side")
        write_json(r, MARKER_REL, base_marker)
        commit_all(r, "marker on side")
        gout(r, "checkout", "-q", BRANCH)
        gout(r, "branch", "-q", "-D", "side")

    def reflog_result(r, rmt):
        write_json(r, MARKER_REL, base_marker)
        write_json(r, RESULT_REL, result)
        commit_all(r, "marker and result, then reset away (never pushed)")
        gout(r, "reset", "-q", "--hard", "HEAD~1")

    add("B13 marker commit reachable only from the reflog (reset --hard, never pushed)", reflog_only)
    add("B13b marker committed on a side branch, branch deleted (-D): only HEAD's reflog reaches it", reflog_side_deleted)
    add("B13r marker and result committed, reset --hard (never pushed): only the reflog reaches them", reflog_result)
    add("B17 marker reachable on the remote only from a tag (no branch), never fetched [stated r3: outside the "
        "search, ACCEPT]", remote_tag_only, info=True)
    for i, (name, prep, info, repo_fn) in enumerate(S):
        repo, remote = new_scenario(ctx, "B%02d" % (i + 1))
        setup_st10(repo, remote)
        if repo_fn == "single":
            repo = other_clone(ctx, remote, "B%02d_single" % (i + 1), ("--single-branch", "-b", BRANCH))
        prep(repo, remote)
        h0, r0 = head(repo), remote_ref(remote)
        mf0 = (Path(repo) / MARKER_REL).exists()
        em = m_marker(repo, remote)
        eb = m_begin(repo, remote, G["rows_h"], G["tiny"]["0"])
        res, rc, err = run_probe(ctx, repo, ["marker", "begin:" + G["tiny"]["0"]])
        print(" %s" % name)
        for (op, kind, detail), ex in zip(res, [em, eb]):
            B.cmp(name.split()[0], op.split(":")[0], None if info else ex[0], kind, detail, ex[1])
        if res[1][1] != "ACCEPT":
            nothing_written(B, repo, remote, h0, r0, marker_before=mf0)


def scen_begin_misc(ctx, B):
    print("\n== D. begin: twice in one process, fast-forward precheck, push refused by the remote, remote unreachable, "
          "staged changes, base hash, dirty tree, no identity, tags, empty remote")
    T = G["tiny"]
    repo, remote = new_scenario(ctx, "D1_twice")
    setup_st10(repo, remote)
    h0 = head(repo)
    e = m_begin(repo, remote, G["rows_h"], T["0"])
    e2 = ("STOP - BLOCKED", "marker committed by begin#1, no result") if e[0] == "ACCEPT" else e
    res, rc, err = run_probe(ctx, repo, ["begin:" + T["0"], "begin:" + T["0"]])
    print(" D1 begin twice in one process")
    begin_result(B, "D1", repo, remote, h0, res[0], e)
    B.cmp("D1", "begin#2", e2[0], res[1][1], res[1][2], e2[1])
    B.post("one marker commit only", gout(repo, "rev-list", "--count", "HEAD") == "3")

    for code, label, prep in (("D2", "remote main diverged (another clone pushed a commit)", "diverged"),
                              ("D2b", "remote main ahead of HEAD (another clone pushed; HEAD is its ancestor)", "ahead"),
                              ("D3", "remote pre-receive hook refuses every push", "hook")):
        repo, remote = new_scenario(ctx, code)
        setup_st10(repo, remote)
        if prep == "diverged":
            o = other_clone(ctx, remote, code + "_other")
            (o / "other.txt").write_text("diverging commit\n")
            commit_all(o, "diverging")
            gout(o, "push", "-q", "origin", "HEAD:refs/heads/" + BRANCH)
            (repo / "local.txt").write_text("local commit\n")
            commit_all(repo, "local commit, not pushed")
        elif prep == "ahead":
            o = other_clone(ctx, remote, code + "_other")
            (o / "other.txt").write_text("remote ahead\n")
            commit_all(o, "remote ahead")
            gout(o, "push", "-q", "origin", "HEAD:refs/heads/" + BRANCH)
        else:
            hk = remote / "hooks" / "pre-receive"
            hk.write_text("#!/bin/sh\necho 'auditor: pushes refused' >&2\nexit 1\n")
            hk.chmod(0o755)
        h0, r0 = head(repo), remote_ref(remote)
        e = m_begin(repo, remote, G["rows_h"], T["0"])
        res, rc, err = run_probe(ctx, repo, ["begin:" + T["0"], "eval:N:0"])
        print(" %s %s" % (code, label))
        B.cmp(code, "begin", e[0], res[0][1], res[0][2], e[1])
        B.cmp(code, "eval:N:0", "REFUSE", res[1][1], res[1][2], "begin did not return a session")
        h1 = head(repo)
        if e[2] == "none":
            nothing_written(B, repo, remote, h0, r0)
        else:
            files = gout(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", "%s^" % h1, h1).split() if h1 != h0 else []
            B.post("marker committed locally on top of the previous HEAD (only the marker path), remote unchanged",
                   h1 != h0 and files == [MARKER_REL] and remote_ref(remote) == r0)
        e2 = m_begin(repo, remote, G["rows_h"], T["0"])
        h1, r1 = head(repo), remote_ref(remote)
        res2, rc, err = run_probe(ctx, repo, ["begin:" + T["0"]])
        B.cmp(code, "begin again", e2[0], res2[0][1], res2[0][2], e2[1])
        B.post("begin again wrote nothing", head(repo) == h1 and remote_ref(remote) == r1)

    repo, remote = new_scenario(ctx, "D4_unreachable")
    setup_st10(repo, remote)
    gone = ctx["base"] / "s" / "no-such-remote.git"
    gout(repo, "remote", "set-url", "origin", str(gone))
    h0 = head(repo)
    e = m_begin(repo, gone, G["rows_h"], T["0"])
    res, rc, err = run_probe(ctx, repo, ["marker", "begin:" + T["0"]])
    print(" D4 remote unreachable")
    for op, kind, detail in res:
        B.cmp("D4", op.split(":")[0], e[0], kind, detail, e[1])
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
    e = m_begin(repo, remote, G["rows_h"], "xyz")
    B.cmp("D6", "begin:xyz", e[0], res[0][1], res[0][2], e[1])
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
    mc = begin_result(B, "D7", repo, remote, h0, res[0], e)
    if mc:
        check_marker_commit(B, repo, remote, mc, h0, r0, T["0"], st10_b, aud_b)
        B.post("modified and untracked files left as they were (not committed)",
               sorted(git(repo, "status", "--porcelain").stdout.decode().splitlines()) == [" M README.audit", "?? untracked.txt"])

    repo, remote = new_scenario(ctx, "D8_no_identity")
    setup_st10(repo, remote)
    gout(repo, "config", "--unset", "user.name")
    gout(repo, "config", "--unset", "user.email")
    gout(repo, "config", "user.useConfigOnly", "true")
    empty = ctx["base"] / "empty_gitconfig"
    empty.write_text("")
    env = {"GIT_CONFIG_GLOBAL": str(empty)}
    h0, r0 = head(repo), remote_ref(remote)
    e = m_begin(repo, remote, G["rows_h"], T["0"], env=env)
    res, rc, err = run_probe(ctx, repo, ["begin:" + T["0"]], env=env)
    print(" D8 no committer identity (repository: user.useConfigOnly true, no user.name / user.email; empty global config)")
    B.cmp("D8", "begin", e[0], res[0][1], res[0][2], e[1])
    nothing_written(B, repo, remote, h0, r0)

    repo, remote = new_scenario(ctx, "D9_follow_tags")
    setup_st10(repo, remote)
    gout(repo, "config", "push.followTags", "true")
    gout(repo, "tag", "-a", "-m", "annotated tag of the auditor", "audit-annotated", "HEAD")
    h0, r0 = head(repo), remote_ref(remote)
    st10_b, aud_b = blob_at(repo, "HEAD", ST10_REL), blob_at(repo, "HEAD", AUD_REL)
    e = m_begin(repo, remote, G["rows_h"], T["0"])
    res, rc, err = run_probe(ctx, repo, ["begin:" + T["0"]])
    print(" D9 push.followTags=true and an annotated tag on HEAD")
    mc = begin_result(B, "D9", repo, remote, h0, res[0], e)
    if mc:
        check_marker_commit(B, repo, remote, mc, h0, r0, T["0"], st10_b, aud_b, local_tags=True)
    B.post("local annotated tag still there, remote has no tag (ls-remote --tags: %r)" % gout(repo, "ls-remote", "--tags", "origin"),
           gout(repo, "tag", "-l") == "audit-annotated" and gout(repo, "ls-remote", "--tags", "origin") == "")

    repo, remote = new_scenario(ctx, "D10_empty_remote")
    setup_st10(repo, remote, push=False)
    empty_remote = repo.parent / "empty_remote.git"
    gout(repo.parent, "init", "-q", "--bare", "-b", BRANCH, str(empty_remote))
    gout(repo, "remote", "set-url", "origin", str(empty_remote))
    h0, r0 = head(repo), remote_ref(empty_remote)
    st10_b, aud_b = blob_at(repo, "HEAD", ST10_REL), blob_at(repo, "HEAD", AUD_REL)
    e = m_begin(repo, empty_remote, G["rows_h"], T["0"])
    res, rc, err = run_probe(ctx, repo, ["begin:" + T["0"]])
    print(" D10 the remote has no branch yet (empty bare repository)")
    mc = begin_result(B, "D10", repo, empty_remote, h0, res[0], e)
    if mc:
        check_marker_commit(B, repo, empty_remote, mc, h0, r0, T["0"], st10_b, aud_b)

    repo, remote = new_scenario(ctx, "D11_code_untracked")
    setup_st10(repo, remote)
    (repo / PILOT / "src").mkdir(parents=True, exist_ok=True)
    (repo / PILOT / "src" / "untracked_code.py").write_text("# untracked code file\n")
    h0, r0 = head(repo), remote_ref(remote)
    res, rc, err = run_probe(ctx, repo, ["begin:" + T["0"]])
    print(" D11 an untracked file under metrix/e1-pilot/src (the marker names the code commit)")
    B.cmp("D11", "begin", None, res[0][1], res[0][2], "no ruling on the marker's code commit")
    if res[0][1] != "ACCEPT":
        nothing_written(B, repo, remote, h0, r0)

    repo, remote = new_scenario(ctx, "D12_ignored_results")
    setup_st10(repo, remote)
    (repo / ".gitignore").write_text(RES + "/\n")
    commit_all(repo, "results ignored")
    gout(repo, "push", "-q", "origin", "HEAD:refs/heads/" + BRANCH)
    h0, r0 = head(repo), remote_ref(remote)
    e = m_begin(repo, remote, G["rows_h"], T["0"])
    e = ("STOP - BLOCKED", "the marker path is ignored: the marker commit fails after the marker is written", "wt") \
        if e[0] == "ACCEPT" else e
    res, rc, err = run_probe(ctx, repo, ["begin:" + T["0"]])
    print(" D12 the results directory is ignored (.gitignore): the marker cannot be added")
    B.cmp("D12", "begin", e[0], res[0][1], res[0][2], e[1])
    B.post("nothing committed or pushed (HEAD, remote unchanged)", head(repo) == h0 and remote_ref(remote) == r0)
    e2 = m_begin(repo, remote, G["rows_h"], T["0"])
    res2, rc, err = run_probe(ctx, repo, ["begin:" + T["0"]])
    B.cmp("D12", "begin again", e2[0], res2[0][1], res2[0][2], e2[1])


HOOK = """#!/bin/sh
unset GIT_DIR GIT_INDEX_FILE GIT_WORK_TREE GIT_PREFIX
echo "pre-push invoked" >> "{log}"
input=$(cat)
[ -f "{flag}" ] && exit 0
for s in $(printf '%s\\n' "$input" | awk '{{print $2}}'); do
  if git -C "{repo}" cat-file -e "$s:{marker}" 2>/dev/null; then
    touch "{flag}"
    echo "acting on $s" >> "{log}"
    exec /usr/bin/env python3 -I "{action}" "{repo}" "{mode}"
  fi
done
exit 0
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
          "once, when the commit being pushed holds the marker, i.e. during begin's real push after the marker commit)")
    T = G["tiny"]
    act = ctx["base"] / "ic4_hook_action.py"
    act.write_text(ACTION)
    for code, mode, label in (("E0", "noop", "control: hook acts, changes nothing"),
                              ("E1", "st10_wt", "ST10 record changed in the working tree after the marker"),
                              ("E2", "st10_commit", "ST10 record changed and committed after the marker (still valid)"),
                              ("E3", "marker_commit", "marker's TEST file hashes changed and committed (TEST rows != marker)"),
                              ("E4", "aud_commit", "auditor's count file changed and committed after the marker")):
        repo, remote = new_scenario(ctx, code + "_" + mode)
        setup_st10(repo, remote)
        flag, log = repo.parent / ("hook_acted_" + mode), repo.parent / ("hook_log_" + mode)
        hk = repo / ".git" / "hooks" / "pre-push"
        hk.write_text(HOOK.format(flag=flag, log=log, action=act, repo=repo, mode=mode, marker=MARKER_REL))
        hk.chmod(0o755)
        h0, r0 = head(repo), remote_ref(remote)
        e = m_begin(repo, remote, G["rows_h"], T["0"])
        ops = ["eval:N:0", "eval:F-%s-seed202:1" % SELECTED["F"], "gate:N:%s" % T["0"]]
        exp = m_evals_pre(ops, T, begin_ok=e[0] == "ACCEPT", changed=None if mode == "noop" else label, base_sha=T["0"])
        res, rc, err = run_probe(ctx, repo, ["begin:" + T["0"]] + ops)
        lg = log.read_text().strip().split("\n") if log.exists() else []
        print(" %s %s (hook log: %s)" % (code, label, lg))
        mc = begin_result(B, code, repo, remote, h0, res[0], e)
        for (op, kind, detail), (ex, why) in zip(res[1:], exp):
            B.cmp(code, op, ex, kind, detail, why)
        B.post("hook acted once, on the marker commit; remote main == marker commit; the change is %s" % (
            "none" if mode == "noop" else "in place after the marker commit"),
            flag.exists() and mc is not None and remote_ref(remote) == mc and any(ln == "acting on " + mc for ln in lg)
            and ((head(repo) == mc) == (mode in ("noop", "st10_wt"))))


def scen_b25(ctx, B):
    print("\n== F. control without --interpretations-ruled (B25 pending): begin and evaluate refuse")
    T = G["tiny"]
    repo, remote = new_scenario(ctx, "F1_b25_pending")
    setup_st10(repo, remote)
    h0, r0 = head(repo), remote_ref(remote)
    e_st10 = m_st10(repo, G["rows_h"])
    e_begin = m_begin(repo, remote, G["rows_h"], T["0"], ruled=False)
    ops = ["eval:N:0", "gate:N:%s" % T["0"]]
    exp = m_evals_pre(ops, T, begin_ok=False, ruled=False)
    res, rc, err = run_probe(ctx, repo, ["st10", "begin:" + T["0"]] + ops, ruled=False)
    B.cmp("F1", "st10", None, res[0][1], res[0][2], "ST10 gate alone: %s (no rule on whether it checks B25)" % e_st10[0])
    B.cmp("F1", "begin", e_begin[0], res[1][1], res[1][2], e_begin[1])
    B.post("begin refusal names B25: %r" % res[1][2][-80:], "B25" in res[1][2])
    B.cmp("F1", res[2][0], exp[0][0], res[2][1], res[2][2], exp[0][1])
    B.post("eval refusal names B25", "B25" in res[2][2])
    B.cmp("F1", res[3][0], exp[1][0], res[3][1], res[3][2], exp[1][1])
    nothing_written(B, repo, remote, h0, r0)
    print(" F2 the same repository, probe with --interpretations-ruled (control of the control)")
    e2 = m_begin(repo, remote, G["rows_h"], T["0"])
    res, rc, err = run_probe(ctx, repo, ["begin:" + T["0"], "eval:N:0"])
    begin_result(B, "F2", repo, remote, h0, res[0], e2)
    ex = m_evals_pre(["eval:N:0"], T, begin_ok=e2[0] == "ACCEPT", base_sha=T["0"])[0]
    B.cmp("F2", res[1][0], ex[0], res[1][1], res[1][2], ex[1])


def scen_branch(ctx, B):
    print("\n== N. the checked-out branch is not the pilot's branch (round 3; probe sets PILOT_BRANCH = main): ops marker "
          "and begin; N1c control: the same repository back on main")
    T = G["tiny"]
    for code, how in (("N1", "branch 'work' checked out (same commit as main)"), ("N2", "detached HEAD at main's tip")):
        repo, remote = new_scenario(ctx, code)
        setup_st10(repo, remote)
        if code == "N1":
            gout(repo, "checkout", "-q", "-b", "work")
        else:
            gout(repo, "checkout", "-q", "--detach")
        h0, r0 = head(repo), remote_ref(remote)
        em, eb = m_marker(repo, remote), m_begin(repo, remote, G["rows_h"], T["0"])
        print(" %s %s (HEAD file: %r)" % (code, how, (repo / ".git" / "HEAD").read_text().strip()))
        res, rc, err = run_probe(ctx, repo, ["marker", "begin:" + T["0"]],
                                 expect=[("marker", em), ("begin", eb[:2])])
        B.cmp(code, "marker", em[0], res[0][1], res[0][2], em[1])
        B.cmp(code, "begin", eb[0], res[1][1], res[1][2], eb[1])
        B.post("begin's refusal names the checked-out branch: %r" % res[1][2][-110:], "checked-out branch" in res[1][2])
        nothing_written(B, repo, remote, h0, r0)
        if code == "N1":
            gout(repo, "checkout", "-q", BRANCH)
            h0, r0 = head(repo), remote_ref(remote)
            st10_b, aud_b = blob_at(repo, "HEAD", ST10_REL), blob_at(repo, "HEAD", AUD_REL)
            em, eb = m_marker(repo, remote), m_begin(repo, remote, G["rows_h"], T["0"])
            print(" N1c control: the same repository, main checked out again")
            res, rc, err = run_probe(ctx, repo, ["marker", "begin:" + T["0"]],
                                     expect=[("marker", em), ("begin", eb[:2])])
            B.cmp("N1c", "marker", em[0], res[0][1], res[0][2], em[1])
            mc = begin_result(B, "N1c", repo, remote, h0, res[1], eb)
            if mc:
                check_marker_commit(B, repo, remote, mc, h0, r0, T["0"], st10_b, aud_b)


def scen_shallow(ctx, B):
    print("\n== S. shallow clone (round 3): ops st10, marker, begin in a --depth 1 clone; S1u: the same clone after "
          "git fetch --unshallow")
    T = G["tiny"]
    repo, remote = new_scenario(ctx, "S0_source")
    setup_st10(repo, remote)
    sh = ctx["base"] / "s" / "S1_shallow_clone"
    url = "file://%s" % remote
    gout(ctx["base"], "clone", "-q", "--depth", "1", url, str(sh))
    set_identity(sh)
    print(" S1 --depth 1 clone of %s: shallow file present %s, commits %s, HEAD branch %r" % (
        url, is_shallow(sh), gout(sh, "rev-list", "--count", "HEAD"), head_ref(sh)))
    h0, r0 = head(sh), remote_ref(remote)
    e_st10, em, eb = m_st10(sh, G["rows_h"]), m_marker(sh, remote), m_begin(sh, remote, G["rows_h"], T["0"])
    res, rc, err = run_probe(ctx, sh, ["st10", "marker", "begin:" + T["0"]],
                             expect=[("st10", e_st10), ("marker", em), ("begin", eb[:2])])
    for (op, kind, detail), ex in zip(res, [e_st10, em, eb[:2]]):
        B.cmp("S1", op.split(":")[0], ex[0], kind, detail, ex[1])
    B.post("marker and begin refusals name the shallow clone", all("shallow" in r[2] for r in res[1:]))
    nothing_written(B, sh, remote, h0, r0)
    gout(sh, "fetch", "-q", "--unshallow")
    h0, r0 = head(sh), remote_ref(remote)
    st10_b, aud_b = blob_at(sh, "HEAD", ST10_REL), blob_at(sh, "HEAD", AUD_REL)
    print(" S1u the same clone after fetch --unshallow: shallow file present %s, commits %s" % (
        is_shallow(sh), gout(sh, "rev-list", "--count", "HEAD")))
    e_st10, em, eb = m_st10(sh, G["rows_h"]), m_marker(sh, remote), m_begin(sh, remote, G["rows_h"], T["0"])
    res, rc, err = run_probe(ctx, sh, ["st10", "marker", "begin:" + T["0"]],
                             expect=[("st10", e_st10), ("marker", em), ("begin", eb[:2])])
    B.cmp("S1u", "st10", e_st10[0], res[0][1], res[0][2], e_st10[1])
    B.cmp("S1u", "marker", em[0], res[1][1], res[1][2], em[1])
    mc = begin_result(B, "S1u", sh, remote, h0, res[2], eb)
    if mc:
        check_marker_commit(B, sh, remote, mc, h0, r0, T["0"], st10_b, aud_b, want_url=url)


PREPUSH = """#!/bin/sh
cat > /dev/null
echo "invoked url=$2" >> "{log}"
if [ "{mode}" = "real" ] && [ ! -f "{flag}" ]; then
  touch "{flag}"
  exit 0
fi
echo "auditor pre-push hook refuses this push: url=$2" >&2
exit 1
"""


def scen_secret(ctx, B):
    print("\n== U. the remote URL holds user information (file://auditor:%s@<path>): the secret must appear neither in "
          "the marker nor in any refusal (round 3)" % SECRET)
    T = G["tiny"]

    def secret_url(remote):
        return "file://auditor:%s@%s" % (SECRET, remote)

    repo, remote = new_scenario(ctx, "U1_secret_url")
    setup_st10(repo, remote)
    gout(repo, "remote", "set-url", "origin", secret_url(remote))
    want_url = my_strip_userinfo(secret_url(remote))
    h0, r0 = head(repo), remote_ref(remote)
    st10_b, aud_b = blob_at(repo, "HEAD", ST10_REL), blob_at(repo, "HEAD", AUD_REL)
    em, eb = m_marker(repo, remote), m_begin(repo, remote, G["rows_h"], T["0"])
    ex_eval = m_evals_pre(["eval:N:0"], T, begin_ok=eb[0] == "ACCEPT", base_sha=T["0"])[0]
    print(" U1 every condition holds; origin %s" % secret_url(remote).replace(SECRET, "<SECRET>"))
    res, rc, err = run_probe(ctx, repo, ["marker", "begin:" + T["0"], "eval:N:0"],
                             expect=[("marker", em), ("begin", eb[:2]), ("eval:N:0", ex_eval)])
    text = ctx["last_text"]
    B.cmp("U1", "marker", em[0], res[0][1], res[0][2], em[1])
    mc = begin_result(B, "U1", repo, remote, h0, res[1], eb)
    if mc:
        check_marker_commit(B, repo, remote, mc, h0, r0, T["0"], st10_b, aud_b, want_url=want_url)
    B.cmp("U1", "eval:N:0", ex_eval[0], res[2][1], res[2][2], ex_eval[1])
    mb = blob_at(repo, "HEAD", MARKER_REL) or b""
    B.post("secret not in the committed marker, not in the probe's output", SECRET.encode() not in mb and SECRET not in text)
    rlog = gout(remote, "log", "--all", "-p", "--format=%H %s")
    B.post("secret not in any commit or diff of the remote (git log --all -p)", SECRET not in rlog)
    fh = repo / ".git" / "FETCH_HEAD"
    print("    info: .git/FETCH_HEAD (local, not committed) holds the secret: %s" % (
        SECRET in fh.read_text() if fh.exists() else "no FETCH_HEAD"))

    for code, mode, label in (("U2", "dry", "a local pre-push hook prints its URL argument and refuses every push "
                                            "(the dry run included)"),
                              ("U3", "real", "a local pre-push hook accepts the first push (the dry run) and refuses "
                                             "the next one (the real push), printing its URL argument")):
        repo, remote = new_scenario(ctx, code + "_secret_hook")
        setup_st10(repo, remote)
        gout(repo, "remote", "set-url", "origin", secret_url(remote))
        flag, log = repo.parent / "prepush_flag", repo.parent / "prepush_log"
        hk = repo / ".git" / "hooks" / "pre-push"
        hk.write_text(PREPUSH.format(log=log, flag=flag, mode=mode))
        hk.chmod(0o755)
        h0, r0 = head(repo), remote_ref(remote)
        eb = m_begin(repo, remote, G["rows_h"], T["0"], hook=mode)
        ex_eval = m_evals_pre(["eval:N:0"], T, begin_ok=eb[0] == "ACCEPT", base_sha=T["0"])[0]
        print(" %s %s" % (code, label))
        res, rc, err = run_probe(ctx, repo, ["begin:" + T["0"], "eval:N:0"],
                                 expect=[("begin", eb[:2]), ("eval:N:0", ex_eval)])
        text = ctx["last_text"]
        B.cmp(code, "begin", eb[0], res[0][1], res[0][2], eb[1])
        B.cmp(code, "eval:N:0", ex_eval[0], res[1][1], res[1][2], ex_eval[1])
        lg = log.read_text() if log.exists() else ""
        B.post("the hook got the URL with the secret (%d invocations), so git's stderr held it" % lg.count("invoked"),
               SECRET in lg)
        B.post("the refusal reports the hook's line with the URL scrubbed (%r)" % (
            re.findall(r"url=\S+", res[0][2])[:1]), ("url=" + want_url_of(remote)) in res[0][2])
        B.post("secret not in the probe's output", SECRET not in text)
        if eb[2] == "none":
            nothing_written(B, repo, remote, h0, r0)
        else:
            h1 = head(repo)
            files = gout(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", "%s^" % h1, h1).split() if h1 != h0 else []
            mb = blob_at(repo, "HEAD", MARKER_REL) or b""
            B.post("marker committed locally on top of the previous HEAD (only the marker path), remote unchanged, "
                   "secret not in the local marker", h1 != h0 and files == [MARKER_REL] and remote_ref(remote) == r0
                   and SECRET.encode() not in mb and (json.loads(mb).get("remote") if mb else None) == want_url_of(remote))

    repo, remote = new_scenario(ctx, "U4_secret_unreachable")
    setup_st10(repo, remote)
    gone = ctx["base"] / "s" / "U4_no-such-remote.git"
    gout(repo, "remote", "set-url", "origin", secret_url(gone))
    h0 = head(repo)
    em, eb = m_marker(repo, gone), m_begin(repo, gone, G["rows_h"], T["0"])
    print(" U4 origin with the secret points at a path that does not exist")
    res, rc, err = run_probe(ctx, repo, ["marker", "begin:" + T["0"]], expect=[("marker", em), ("begin", eb[:2])])
    text = ctx["last_text"]
    B.cmp("U4", "marker", em[0], res[0][1], res[0][2], em[1])
    B.cmp("U4", "begin", eb[0], res[1][1], res[1][2], eb[1])
    B.post("secret not in the probe's output; nothing written", SECRET not in text and head(repo) == h0
           and not (repo / MARKER_REL).exists())


def want_url_of(remote):
    return "file://" + str(remote)


def scen_nonobject(ctx, B):
    print("\n== G. the committed Gate 0 or freeze record is valid JSON but not an object (round 3): ops st10 (INFO), "
          "begin, eval")
    T = G["tiny"]
    for code, which, make, label in (("G1", "gate0", lambda o: [o], "Gate 0 record is a JSON array [record]"),
                                     ("G2", "freeze", lambda o: [o], "freeze record is a JSON array [record]"),
                                     ("G3", "gate0", lambda o: "PASS", "Gate 0 record is a JSON string"),
                                     ("G4", "freeze", lambda o: None, "freeze record is JSON null")):
        repo, remote = new_scenario(ctx, code + "_nonobject")
        g0 = json.loads((repo / G0_REL).read_text())
        sel = json.loads((repo / SEL_REL).read_text())
        if which == "gate0":
            g0sha = write_json(repo, G0_REL, make(g0))
            sel["gate0_record_sha256"] = g0sha
            selsha = write_json(repo, SEL_REL, sel)
            rel = G0_REL
        else:
            g0sha = G["g0sha"]
            selsha = write_json(repo, SEL_REL, make(sel))
            rel = SEL_REL
        commit_all(repo, "auditor: %s" % label)
        gout(repo, "push", "-q", "origin", "HEAD:refs/heads/" + BRANCH)
        rec = dict(st10_default(), authorization={"gate0_record_sha256": g0sha, "selection_record_sha256": selsha})
        setup_st10(repo, remote, rec)
        h0, r0 = head(repo), remote_ref(remote)
        e_st10 = m_st10(repo, G["rows_h"])
        eb = m_begin(repo, remote, G["rows_h"], T["0"])
        rr = m_records(repo)
        ex_eval = rr if rr else m_evals_pre(["eval:N:0"], T, begin_ok=False)[0]
        print(" %s %s (committed bytes: %r)" % (code, label, (blob_at(repo, "HEAD", rel) or b"")[:40]))
        res, rc, err = run_probe(ctx, repo, ["st10", "begin:" + T["0"], "eval:N:0"],
                                 expect=[("st10", (None, "ST10 gate alone: %s (it does not read the records' "
                                                         "content)" % e_st10[0])), ("begin", eb[:2]), ("eval:N:0", ex_eval)])
        B.cmp(code, "st10", None, res[0][1], res[0][2], "ST10 gate alone, my model: %s" % e_st10[0])
        B.cmp(code, "begin", eb[0], res[1][1], res[1][2], eb[1])
        B.cmp(code, "eval:N:0", ex_eval[0], res[2][1], res[2][2], ex_eval[1])
        B.post("begin and eval refusals name %s and 'not an object'" % rel.split("/")[-1],
               all(rel in r[2] and "not an object" in r[2] for r in res[1:]))
        B.post("no AttributeError / ERROR line", all(r[1] != "ERROR" for r in res))
        nothing_written(B, repo, remote, h0, r0)


def scen_probe_guard(ctx, B):
    print("\n== P. the probe's own guard: it refuses the pilot's repository and any clone whose origin is "
          "leotree2020/OpenMythos, before any operation (round 3)")
    T = G["tiny"]

    def raw(repo, ops):
        cmd = [ctx["py"], "-I", "-B", ctx["probe"], "--interpretations-ruled", str(repo), str(ctx["test_dir"]), *ops]
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=ctx["base"], timeout=900,
                           env=dict(os.environ, **BASE_ENV))
        ctx["runs"] = ctx.get("runs", 0) + 1
        ctx["secret_seen"] = ctx.get("secret_seen", 0) + (SECRET in r.stdout + r.stderr)
        return r

    def refused(code, r, ops):
        op_lines = [ln for ln in r.stdout.splitlines() if any(ln.startswith(op + " ") for op in ops)]
        msg = (r.stderr.strip().splitlines() or [""])[-1]
        ok = r.returncode != 0 and msg.startswith("probe refused:") and op_lines == []
        B.cmp(code, "probe", "REFUSED", "REFUSED" if ok else "RAN (exit %d, %d op lines)" % (r.returncode, len(op_lines)),
              msg, "my model: origin %s is the pilot's repository" % code)
        return ok

    d = ctx["base"] / "s" / "P1"
    repo, remote = new_scenario(ctx, "P1")
    canon_remote = d / "leotree2020" / "OpenMythos.git"
    canon_remote.parent.mkdir(parents=True)
    gout(d, "init", "-q", "--bare", "-b", BRANCH, str(canon_remote))
    gout(repo, "remote", "set-url", "origin", str(canon_remote))
    setup_st10(repo, canon_remote)
    h0, r0 = head(repo), remote_ref(canon_remote)
    ops = ["marker", "begin:" + T["0"]]
    print(" P1 throw-away clone whose origin is %s (my repo id %r); ops %s" % (
        canon_remote, my_repo_id(str(canon_remote)), ["marker", "begin"]))
    r = raw(repo, ops)
    refused("P1", r, ops)
    B.post("P1 nothing written and nothing fetched: HEAD, remote main unchanged, no marker, no .git/FETCH_HEAD",
           head(repo) == h0 and remote_ref(canon_remote) == r0 and not (repo / MARKER_REL).exists()
           and not (repo / ".git" / "FETCH_HEAD").exists())
    for code, url in (("P2", "https://auditor:%s@github.com/leotree2020/OpenMythos.git" % SECRET),
                      ("P3", "git@github.com:leotree2020/OpenMythos.git")):
        gout(repo, "remote", "set-url", "origin", url)
        print(" %s origin %s (my repo id %r); no operation (nothing could reach the network)" % (
            code, url.replace(SECRET, "<SECRET>"), my_repo_id(url)))
        r = raw(repo, [])
        refused(code, r, [])
        B.post("%s secret not in the probe's output" % code, SECRET not in r.stdout + r.stderr)
    pilot = ctx["repo"]
    fh = pilot / ".git" / "FETCH_HEAD"
    before = (gout(pilot, "rev-parse", "HEAD"), gout(pilot, "write-tree"), fh.stat().st_mtime_ns if fh.exists() else None,
              git(pilot, "status", "--porcelain", "--untracked-files=all").stdout)
    print(" P4 REPO = the pilot's repository %s; no operation" % pilot)
    r = raw(pilot, [])
    refused("P4", r, [])
    after = (gout(pilot, "rev-parse", "HEAD"), gout(pilot, "write-tree"), fh.stat().st_mtime_ns if fh.exists() else None,
             git(pilot, "status", "--porcelain", "--untracked-files=all").stdout)
    B.post("P4 the pilot's repository unchanged (HEAD, index tree, FETCH_HEAD mtime, status)", before == after)


def scen_history(ctx, B):
    print("\n== H. git level (not black box): the history search of 'TEST generated once' (ST10 record) and of the result "
          "file in a side branch merged back. refuse_if_st10_record has no probe operation and the TEST driver cannot be "
          "pointed at a temporary repository without generating real TEST; its search is the same _where / _ever_committed "
          "as the marker's (ic4_03 g), whose behaviour B05 / B05s / B05r / B05x / B05m test black box. Here: my "
          "rev-list + cat-file search vs the git command form the code uses (ic4_03 g: git log --full-history <revs> "
          "--format=%H -- <path>) vs the round-1 form without --full-history.")
    for code, rel, how in (("H1", ST10_REL, "no-ff"), ("H2", ST10_REL, "ours"), ("H3", RESULT_REL, "no-ff"),
                           ("H4", RESULT_REL, "ours"), ("H5", MARKER_REL, "ours")):
        repo, remote = new_scenario(ctx, code + "_history")
        gout(repo, "checkout", "-q", "-b", "side")
        write_json(repo, rel, {"kind": "planted by the data-auditor"})
        commit_all(repo, "%s on side" % rel)
        if how == "no-ff":
            gout(repo, "rm", "-q", rel)
            commit_all(repo, "%s deleted on side" % rel)
        gout(repo, "checkout", "-q", BRANCH)
        if how == "no-ff":
            gout(repo, "merge", "-q", "--no-ff", "-m", "merge side", "side")
        else:
            gout(repo, "merge", "-q", "-s", "ours", "-m", "merge side (ours)", "side")
        gout(repo, "branch", "-q", "-D", "side")
        mine = commits_with(repo, rel, ["--all"])
        full = gout(repo, "log", "--full-history", "--all", "--format=%H", "--", rel).split()
        plain = gout(repo, "log", "--all", "--format=%H", "--", rel).split()
        print(" %s %s, side branch merged (%s), side ref deleted: mine (commits whose tree holds it) %s | "
              "git log --full-history %s | git log (no --full-history) %s" % (
                  code, rel.split("/")[-1], how, [c[:12] for c in mine], [c[:12] for c in full], [c[:12] for c in plain]))
        B.post("%s found by the code's form iff found by mine (%s / %s)" % (code, bool(full), bool(mine)), bool(full) == bool(mine))
    for code, rel in (("H6", ST10_REL), ("H7", RESULT_REL), ("H8", MARKER_REL)):
        repo, remote = new_scenario(ctx, code + "_reflog")
        write_json(repo, rel, {"kind": "planted by the data-auditor"})
        commit_all(repo, "%s, then reset away (never pushed)" % rel)
        gout(repo, "reset", "-q", "--hard", "HEAD~1")
        mine = commits_with(repo, rel, ["--all", "--reflog"])
        r3 = gout(repo, "log", "--full-history", "--all", "--reflog", "--format=%H", "--", rel).split()
        r2 = gout(repo, "log", "--full-history", "--all", "--format=%H", "--", rel).split()
        print(" %s %s committed then reset --hard: mine (rev-list --all --reflog) %s | round-3 form (git log "
              "--full-history --all --reflog) %s | round-2 form (no --reflog) %s" % (
                  code, rel.split("/")[-1], [c[:12] for c in mine], [c[:12] for c in r3], [c[:12] for c in r2]))
        B.post("%s found by mine and by the round-3 form (%s / %s); not by the round-2 form (%s)" % (
            code, bool(mine), bool(r3), bool(r2)), bool(mine) and bool(r3) and set(r3) == set(mine) and not r2)


def main():
    repo, py, base = Path(sys.argv[1]).resolve(), sys.argv[2], Path(sys.argv[3]).resolve()
    if base == repo or repo in base.parents:
        raise SystemExit("base dir must be outside the repository")
    if base.exists():
        shutil.rmtree(base)
    base.mkdir(parents=True)
    if len(sys.argv) != 4:
        raise SystemExit("usage: ic4_01_gate_scenarios.py <repo_root> <python_for_probe> <base_dir_outside_repo>")
    probe = repo / PROBE_REL
    ctx = {"repo": repo, "py": py, "base": base, "probe": str(probe)}
    staged = git(repo, "cat-file", "blob", ":" + PROBE_REL).stdout
    same = probe.read_bytes() == staged
    print("probe run: %s sha256 %s | staged probe (index) sha256 %s | the probe run is the staged one: %s | HEAD %s | "
          "staged tree %s" % (probe, sha(probe.read_bytes()), sha(staged), same,
                              gout(repo, "rev-parse", "HEAD"), gout(repo, "write-tree")))
    if not same:
        raise SystemExit("the working-tree probe differs from the staged one")
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
    scen_b25(ctx, B)
    scen_branch(ctx, B)
    scen_shallow(ctx, B)
    scen_secret(ctx, B)
    scen_nonobject(ctx, B)
    scen_probe_guard(ctx, B)
    scen_history(ctx, B)
    print("\nprobe's first line is the --interpretations-ruled line exactly when the flag is given (every run): %s" %
          ctx["ruled_line_ok"])
    ok &= ctx["ruled_line_ok"]
    print("probe's CANONICAL_REPO line == my reading of origin's URL: checked in %d runs, mismatches %s" % (
        ctx.get("canon_checked", 0), ctx.get("canon_bad", [])))
    ok &= not ctx.get("canon_bad")
    print("probe runs %d; runs whose stdout+stderr contain the URL secret: %d" % (ctx.get("runs", 0), ctx.get("secret_seen", 0)))
    ok &= ctx.get("secret_seen", 0) == 0
    print("\nsummary: compared operations same %d | DIFFERENT %d | INFO (no expectation) %d | ERROR or unparsable "
          "probe output among them: %d | post-checks FAILED %d" % (B.same, B.bad, B.info, B.defect, B.post_bad))
    print("gates (my model vs the code through the staged probe): %s" % (
        "consistent" if B.bad == 0 and B.post_bad == 0 else "NOT consistent"))
    return bool(ok and B.bad == 0 and B.post_bad == 0 and B.defect == 0)


run(main)
