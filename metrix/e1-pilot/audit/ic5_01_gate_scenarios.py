"""ic5_01 (implementation stage C, C1 second submission, round 1, task 1): black-box comparison of the TEST gates with my
own model, through the staged probe reports/impl_c/c1b_gate_probe.py run as a driver subprocess (Review Gate's ruling
on C1, item 5). Successor of my ic4_01_gate_scenarios.py; the model is updated to the ruling's semantics.

My model (protocol v1.1 section 3 L6 row, section 8 step 8, section 11 ST10; Review Gate supplementary rulings 3-5 of
2026-11-24 (tasks/IMPL_C_OWNER_MESSAGE.md); Review Gate's ruling on C1 of 2026-11-25 items 1, 2, 4
(tasks/IMPL_C1_RULING.md); the Executor's description items 1-4 of this submission where the ruling leaves the
mechanics open. Not taken from the Executor's code):
  checkout (ruling 1) : every TEST path needs: origin's repository (last two path components of its fetch URL, user
             information and .git removed; the host is not compared, ruling 6) equal to the pilot's (the probe sets the
             pilot's to origin's at its start), the pilot branch (the probe: main) checked out (a detached HEAD is
             not), a clone that is not shallow, a fetch of origin's main that works (remote reachable, branch present)
             and HEAD equal to origin's main. Otherwise STOP BLOCKED and nothing is written.
  where (ruling 1)    : a record exists when it is in the working tree or in the file tree of origin's latest main
             commit. Nothing else is searched (earlier commits, other branches, reflog, tags, the index): such
             records are "not searched by the ruling" and do not refuse.
  st10rec             : checkout; then an ST10 record in either place -> REFUSE (TEST is generated once); else ACCEPT.
  marker              : checkout; a result in either place -> EVALUATED (also without a marker); a marker in either
             place -> STOP BLOCKED (started, not finished: counts as evaluated); else ACCEPT.
  pre (ruling 2)      : checkout; nothing staged; a committer identity (a commit object can be made); a dry-run push to
             origin main accepted (a dry run runs no server-side hook) -> ACCEPT, else STOP BLOCKED.
  ST10 gate (suppl. 3): the ST10 record committed (HEAD blob == working tree), a JSON object, formal st10 of the
             frozen commit, bound to the authorization (sha256 of the committed Gate 0 and freeze records), naming the
             TEST files evaluated, a code commit that is HEAD or an ancestor, exactly five non-negative integer counts;
             the data-auditor's count committed, a JSON object of the frozen commit for the same general_test.jsonl,
             a non-negative integer. Missing / unbound -> REFUSE. Counts judged by me against the frozen limits; over a
             limit, or L6 != the data-auditor's -> STOP ST10 BLOCKED. Self-reported flags are ignored.
  begin (suppl. 4)    : marker check (with the checkout) -> records (committed JSON objects of their kind) -> ST10 gate
             -> base hash 64 hex -> pre -> marker written, committed (only its path) and pushed. A failure after the
             marker is written (path cannot be added; real push refused) -> STOP BLOCKED; the marker stays (in the
             working tree, or in a local commit) and refuses later.
  eval / gate         : the session was begun in this process and not finished; the pilot branch is checked out at
             the session's marker commit (Executor's description item 2: no fetch here) else STOP BLOCKED; the
             committed marker, the TEST rows == the marker's files, the ST10 gate; the checkpoint one of the 16 TEST
             models, not yet claimed, its state hash == the marker's. On the CPU an accepted eval stops at
             require_gpu (probe: ACCEPTED-BY-GATES) before claiming; gate claims.
  finish              : session live; checkout at the marker commit (else BLOCKED); every model claimed (else REFUSE);
             pre (with the fetch); then the result is committed and pushed; the session ends.
Expectations are computed before each probe run from the repository state (git plumbing, read-only) and the planned
change, and printed ("pre-registered") before the probe is started. Ops that only serve as a vehicle for a hook are
compared as INFO.
Changes between operations of one probe process are made by pre-push hooks of the throw-away clone (they run during
a push the probe makes: begin's real push, or the dry run of op pre); each hook acts once.
All TEST rows are synthetic rows written by this script; no real TEST row, no eval_sets.jsonl, no model weights (the
probe's tiny models are random), no GPU. Nothing of the package is imported, called or copied by this script.
Probe outcome classes: ACCEPT | REFUSE | STOP <code> <status> | EVALUATED | ERROR.
usage: python -I ic5_01_gate_scenarios.py <repo_root> <python_for_probe> <base_dir_outside_repo>"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json
import re
import shutil
import subprocess
from pathlib import Path
from ia_common import jsonl_bytes, sha, run

PILOT = "metrix/e1-pilot"
PF_REL = PILOT + "/PROTOCOL_FROZEN"
RES = PILOT + "/results"
G0_REL = RES + "/gate0_record.json"
SEL_REL = RES + "/selection_freeze_record.json"
ST10_REL = RES + "/st10_record.json"
AUD_REL = PILOT + "/audit/st10_l6_test_count.json"
MARKER_REL = RES + "/test_evaluation_marker.json"
RESULT_REL = RES + "/test_evaluation_result.json"
PROBE_REL = PILOT + "/reports/impl_c/c1b_gate_probe.py"
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
CANON_PREFIX = "probe: testgate.CANONICAL_REPO = "
SECRET = "s3cr3t-auditor-token-ic5"
BASE_ENV = {"GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0"}
G = {}                                                 # frozen facts read by me; filled in main()
BLK = "STOP - BLOCKED"
NOT_SEARCHED = "[not searched by the ruling]"


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


def push(root, ref=BRANCH):
    gout(root, "push", "-q", "origin", "HEAD:refs/heads/" + ref)


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
    for k, v in (("user.name", "data-auditor-ic5"), ("user.email", "auditor@invalid"), ("commit.gpgsign", "false"),
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
    Name layout <arm>-<config id>-seed<seed> (interface of the freeze record). TEST models: N, F, L, A selected and
    S, Y, three seeds each (16)."""
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


def head_ref(repo):
    """The checked-out branch, read from .git/HEAD (None when HEAD is detached)."""
    t = (Path(repo) / ".git" / "HEAD").read_text().strip()
    return t[len("ref: refs/heads/"):] if t.startswith("ref: refs/heads/") else None


def is_shallow(repo):
    return (Path(repo) / ".git" / "shallow").exists()


def origin_url(repo):
    r = git(repo, "config", "--get", "remote.origin.url")
    return r.stdout.decode().strip() if r.returncode == 0 else None


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


def m_checkout(repo, remote, canon=None, url=None):
    """Ruling 1. remote: the bare repository the fetch URL reaches (None / missing: unreachable). canon: the pilot's
    repository as the probe sets it at its start (default: origin's now); url: origin's URL when the checkout is
    checked (default: now). -> (BLK, why, keyword) or None."""
    url = origin_url(repo) if url is None else url
    canon = my_repo_id(origin_url(repo)) if canon is None else canon
    if url is None or my_repo_id(url) != canon:
        return BLK, "origin is repository %r, not the pilot's %r" % (url and my_repo_id(url), canon), "repository"
    if head_ref(repo) != BRANCH:
        return BLK, "checked-out branch %r is not %s" % (head_ref(repo), BRANCH), "branch"
    if is_shallow(repo):
        return BLK, "shallow clone", "shallow"
    tip = remote_ref(remote)
    if tip is None:
        return BLK, "cannot fetch origin %s (unreachable or no such branch)" % BRANCH, "fetch"
    if head(repo) != tip:
        return BLK, "HEAD %s is not origin's %s %s" % (head(repo)[:12], BRANCH, tip[:12]), "latest commit"
    return None


def m_where(repo, remote, rel):
    out = []
    if (Path(repo) / rel).exists():
        out.append("working tree")
    tip = remote_ref(remote)
    if tip is not None and has_path(remote, tip, rel):
        out.append("tip %s" % tip[:12])
    return out


def m_marker(repo, remote, **kw):
    """('ACCEPT'|'EVALUATED'|BLK, why, keyword)."""
    c = m_checkout(repo, remote, **kw)
    if c:
        return c
    places, res = m_where(repo, remote, MARKER_REL), m_where(repo, remote, RESULT_REL)
    if res:
        return "EVALUATED", "result in %s" % ", ".join(res), "already evaluated"
    if places:
        return BLK, "marker without result in %s" % ", ".join(places), "already started"
    return "ACCEPT", None, None


def m_st10rec(repo, remote, **kw):
    c = m_checkout(repo, remote, **kw)
    if c:
        return c
    places = m_where(repo, remote, ST10_REL)
    if places:
        return "REFUSE", "ST10 record in %s: TEST is generated once" % ", ".join(places), "generated once"
    return "ACCEPT", None, None


def can_commit(repo, env=None):
    """A commit object can be made (committer identity): git commit-tree (writes a dangling object only)."""
    t = gout(repo, "rev-parse", "HEAD^{tree}")
    r = git(repo, "commit-tree", t, "-p", "HEAD", "-m", "auditor identity check", env=env)
    return r.returncode == 0, " ".join(r.stderr.decode(errors="replace").split())[:160]


def m_pre(repo, remote, env=None, dry_ok=True, **kw):
    """Ruling 2. dry_ok: whether a dry-run push is accepted in this scenario (False: the push URL is not a
    repository, or a local pre-push hook refuses the dry run)."""
    c = m_checkout(repo, remote, **kw)
    if c:
        return c
    if git(repo, "diff", "--cached", "--quiet").returncode != 0:
        return BLK, "staged changes", "staged"
    ok, err = can_commit(repo, env)
    if not ok:
        return BLK, "no commit possible (%s)" % err, "identity"
    if not dry_ok:
        return BLK, "the dry-run push is refused", "dry-run"
    return "ACCEPT", None, None


def m_records(repo):
    """The committed Gate 0 and freeze records must be committed JSON objects of their kind. -> (REFUSE, why) or None."""
    for rel, kind in ((G0_REL, "gate0"), (SEL_REL, "selection_freeze")):
        b, why = m_committed(repo, rel)
        if b is None:
            return "REFUSE", "%s %s" % (rel.split("/")[-1], why), None
        o = m_json_object(b)
        if o is None:
            return "REFUSE", "%s is not a JSON object" % rel.split("/")[-1], "not an object"
        if o.get("kind") != kind or o.get("mode") != "formal" or o.get("frozen_commit") != G["frozen"]:
            return "REFUSE", "%s is not a formal %s record of the frozen commit" % (rel.split("/")[-1], kind), None
    return None


def m_begin(repo, remote, rows_h, base_sha, env=None, dry_ok=True, add_ok=True, real_ok=True, **kw):
    """-> (outcome, why, keyword, written) with written in {'none', 'wt', 'local', 'pushed'}."""
    k = m_marker(repo, remote, **kw)
    if k[0] != "ACCEPT":
        return k + ("none",)
    rr = m_records(repo)
    if rr:
        return rr + ("none",)
    s = m_st10(repo, rows_h)
    if s[0] != "ACCEPT":
        return s + (None, "none")
    if not re.fullmatch(r"[0-9a-f]{64}", base_sha):
        return "REFUSE", "base model hash", None, "none"
    p = m_pre(repo, remote, env=env, dry_ok=dry_ok, **kw)
    if p[0] != "ACCEPT":
        return p + ("none",)
    if not add_ok:
        return BLK, "the marker path cannot be added: the marker stays in the working tree", "staging", "wt"
    if not real_ok:
        return BLK, "the real push is refused: the marker commit stays local", "not pushed", "local"
    return "ACCEPT", None, None, "pushed"


def m_session_ops(ops, T, begin_ok, change=None, base_sha=None, rows_ok=True, st10_ok=True):
    """Expectations of eval / gate / finish after a begin in the same run, computed before the run from my expected
    marker (my checkpoint hashes + N = base_sha, my 16 TEST models) and the planned change after begin.
    change: None | ('checkout', why): HEAD or branch moved off the marker commit | ('st10', why): ST10 record changed
    in the working tree | ('remote', why): origin's main moved on, local HEAD still the marker commit (eval and gate
    do not fetch; finish does). Vehicle ops (pre) are INFO."""
    out, claimed, live = [], set(), begin_ok
    ck = dict(G["ck"], N=base_sha)
    for op in ops:
        kind, _, arg = op.partition(":")
        name, _, s = arg.partition(":")
        h = T.get(s) if kind == "eval" else s
        if kind == "pre":
            out.append((None, "vehicle for the hook", None))
            continue
        if not live:
            out.append(("REFUSE", "no live session of this process", "session"))
            continue
        if change and change[0] == "checkout":
            out.append((BLK, "%s; not at the marker commit" % change[1], "marker commit"))
            continue
        if change and change[0] == "st10" and kind in ("eval", "gate"):
            out.append(("REFUSE", "ST10 record %s" % change[1], "differs"))
            continue
        if kind == "finish":
            left = [m for m in G["test_models"] if m not in claimed]
            if left:
                out.append(("REFUSE", "%d models not claimed" % len(left), "not evaluated"))
            elif change and change[0] == "remote":
                out.append((BLK, "finish fetches: %s" % change[1], "latest commit"))
            else:
                out.append(("ACCEPT", "result committed and pushed; the session ends", None))
                live = False
            continue
        if name not in G["test_models"]:
            out.append(("REFUSE", "not one of the 16 TEST models", None))
        elif name in claimed:
            out.append(("REFUSE", "already claimed in this session", "already evaluated"))
        elif h != ck.get(name):
            out.append(("REFUSE", "model hash != marker", "state sha256"))
        elif change and change[0] == "remote":
            out.append((None, "eval does not fetch (Executor's reading): ACCEPT; a fetch per call (literal reading of "
                              "ruling 1): BLOCKED", None))
            if kind == "gate":
                claimed.add(name)
        else:
            out.append(("ACCEPT", "passes every gate; CPU stops at require_gpu" + (", claimed" if kind == "gate" else ""),
                        None))
            if kind == "gate":
                claimed.add(name)
    return out


# ---------------------------------------------------------------------------------------------- probe runner

def run_probe(ctx, repo, ops, env=None, test_dir=None, expect=None):
    """Runs the staged probe; returns ([(op, class, detail)], exit code, stderr tail). The complete stdout+stderr of the
    run is kept in ctx['last_text']. expect: [(op, expectation tuple)] printed before the probe is started."""
    if expect:
        for op, e in expect:
            print("    pre-registered: %-34s -> %-18s (%s)" % (op[:34], "INFO" if e[0] is None else e[0], e[1]))
        sys.stdout.flush()
    cmd = [ctx["py"], "-I", "-B", ctx["probe"], str(repo), str(test_dir or ctx["test_dir"]), *ops]
    e = dict(os.environ, **BASE_ENV)
    if env:
        e.update(env)
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=ctx["base"], timeout=900, env=e)
    ctx["last_text"] = r.stdout + r.stderr
    ctx["runs"] = ctx.get("runs", 0) + 1
    ctx["secret_seen"] = ctx.get("secret_seen", 0) + (SECRET in r.stdout + r.stderr)
    lines = r.stdout.rstrip("\n").split("\n")
    canon = [ln[len(CANON_PREFIX):] for ln in lines if ln.startswith(CANON_PREFIX)]
    ou = ctx.pop("url_at_start", None) or origin_url(repo)
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
            out.append((op, kind, detail))
    if r.returncode != 0:
        print("    probe exit %d; stderr tail: %r" % (r.returncode, r.stderr.strip()[-300:]))
    return out, r.returncode, (r.stderr.strip().split("\n")[-1] if r.stderr.strip() else "")


def introduced(repo, h0, rel, tip="HEAD"):
    """Commits after h0 (reachable from `tip`) that add `rel`."""
    r = git(repo, "rev-list", "--reverse", tip if h0 is None else "%s..%s" % (h0, tip))
    return [c for c in r.stdout.decode().split() if has_path(repo, c, rel)
            and not (git(repo, "rev-parse", "-q", "--verify", c + "^").returncode == 0 and has_path(repo, c + "^", rel))]


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
    push(repo)
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


def setup_st10(repo, remote, rec=None, aud=None, do_push=True):
    if rec is not False:
        write_json(repo, ST10_REL, st10_default() if rec is None else rec)
    if aud is not False:
        write_json(repo, AUD_REL, aud_default() if aud is None else aud)
    c = commit_all(repo, "ST10 record and the auditor's count")
    if do_push:
        push(repo)
    return c


def other_clone(ctx, remote, name, args=()):
    o = ctx["base"] / "s" / name
    gout(ctx["base"], "clone", "-q", *args, str(remote), str(o))
    set_identity(o)
    return o


HOOK = """#!/bin/sh
unset GIT_DIR GIT_INDEX_FILE GIT_WORK_TREE GIT_PREFIX GIT_QUARANTINE_PATH
cat > /dev/null
exec /usr/bin/env python3 -I "{action}" "{repo}" "{mode}" "{state}" "{arg}"
"""

ACTION = r'''import json, subprocess, sys, pathlib
repo, mode, state, arg = pathlib.Path(sys.argv[1]), sys.argv[2], pathlib.Path(sys.argv[3]), sys.argv[4]
MARKER, ST10 = "%(marker)s", "%(st10)s"
def g(*a, cwd=None):
    return subprocess.run(["git", "-C", str(cwd or repo), *a], capture_output=True, text=True, check=True).stdout.strip()
st = json.loads(state.read_text()) if state.exists() else {"n": 0, "m": 0, "acted": False, "log": []}
st["n"] += 1
holds = subprocess.run(["git", "-C", str(repo), "cat-file", "-e", "HEAD:" + MARKER], capture_output=True).returncode == 0
st["m"] += holds
st["log"].append("invocation %%d (marker-holding %%d) HEAD %%s holds marker %%s" %% (st["n"], st["m"], g("rev-parse", "HEAD"), holds))
want, _, at = mode.partition("@")
act = not st["acted"] and ((at == "first" and st["n"] == 1) or (at.isdigit() and holds and st["m"] == int(at)))
code = 0
if want == "refuse_all":
    code = 1
elif want == "refuse_after_first":
    code = 0 if st["n"] == 1 else 1
elif act:
    st["acted"] = True
    state.write_text(json.dumps(st))
    if want == "seturl":
        g("remote", "set-url", "origin", arg)
    elif want in ("commit_local", "commit_push"):
        (repo / "after_marker.txt").write_text("a commit made after the marker\n")
        g("add", "after_marker.txt")
        g("commit", "-q", "-m", "auditor: a commit after the marker")
        if want == "commit_push":
            g("push", "-q", "origin", "HEAD:refs/heads/main")
    elif want == "branch":
        g("checkout", "-q", "-b", "other")
    elif want == "detach":
        g("checkout", "-q", "--detach")
    elif want == "reset":
        g("reset", "-q", "--hard", "HEAD~1")
    elif want == "remote_moves":
        o = pathlib.Path(arg)
        subprocess.run(["git", "clone", "-q", g("config", "--get", "remote.origin.url"), str(o)], check=True, capture_output=True)
        for k, v in (("user.name", "auditor-other"), ("user.email", "o@invalid"), ("commit.gpgsign", "false")):
            g("config", k, v, cwd=o)
        (o / "other_clone.txt").write_text("pushed by another clone after the marker\n")
        g("add", "other_clone.txt", cwd=o)
        g("commit", "-q", "-m", "auditor: another clone pushes after the marker", cwd=o)
        g("push", "-q", "origin", "HEAD:refs/heads/main", cwd=o)
    elif want == "st10_wt":
        p = repo / ST10
        p.write_bytes(p.read_bytes() + b"\n")
    st["log"].append("acted: %%s, HEAD now %%s" %% (want, g("rev-parse", "HEAD")))
state.write_text(json.dumps(st))
sys.exit(code)
''' % {"marker": MARKER_REL, "st10": ST10_REL}


def install_hook(ctx, repo, mode, arg=""):
    act = ctx["base"] / "ic5_hook_action.py"
    if not act.exists():
        act.write_text(ACTION)
    state = repo.parent / ("hook_state_%s.json" % mode.replace("@", "_"))
    hk = repo / ".git" / "hooks" / "pre-push"
    hk.write_text(HOOK.format(action=act, repo=repo, mode=mode, state=state, arg=arg))
    hk.chmod(0o755)
    return state


def hook_log(state):
    return json.loads(state.read_text())["log"] if state.exists() else []


# ------------------------------------------------------------------------------------------------- reporting

class Book:
    def __init__(self):
        self.bad, self.info, self.post_bad, self.defect, self.same = 0, 0, 0, 0, 0

    def cmp(self, scen, op, expected, observed, detail, why=None, kw=None):
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
                                                                (detail or "")[:300], ("  (model: %s)" % why) if why else ""))
        if kw and exp is not None and verdict == "same":
            self.post("%s %s: the message names the reason (%r)" % (scen, op[:20], kw), kw.lower() in (detail or "").lower())

    def cmpx(self, scen, res_item, ex):
        """res_item: (op, class, detail); ex: (expected, why, keyword, ...)."""
        op, kind, detail = res_item
        self.cmp(scen, op, ex[0], kind, detail, ex[1], ex[2] if len(ex) > 2 else None)

    def post(self, what, ok):
        print("    post-check %-100s %s" % (what, "ok" if ok else "FAILED"))
        if not ok:
            self.post_bad += 1


def nothing_written(B, repo, remote, h0, r0, marker_before=False, result_before=False):
    B.post("nothing written: marker file %s, result file %s, HEAD unchanged, origin %s unchanged" % (
        "as before" if marker_before else "absent", "as before" if result_before else "absent", BRANCH),
        (Path(repo) / MARKER_REL).exists() == marker_before and (Path(repo) / RESULT_REL).exists() == result_before
        and head(repo) == h0 and remote_ref(remote) == r0)


def begin_result(B, scen, repo, remote, h0, res0, expected):
    """Compare a begin outcome. Returns the marker commit the probe printed (ACCEPT), else None."""
    B.cmpx(scen, (res0[0].split(":")[0], res0[1], res0[2]), expected)
    mc = None
    if res0[1] == "ACCEPT":
        m = re.search(r"marker commit ([0-9a-f]{40}) models (\d+)", res0[2])
        mc = m.group(1) if m else None
        B.post("probe printed the marker commit and 'models 16' (%s)" % ((m.groups() if m else None),),
               m is not None and m.group(2) == str(len(G["test_models"])))
        cs = introduced(repo, h0, MARKER_REL, mc or "HEAD")
        B.post("exactly one commit between the previous HEAD and the printed marker commit adds the marker, the printed "
               "one (%s)" % [c[:12] for c in cs], len(cs) == 1 and cs[0] == mc)
    return mc


def check_marker_commit(B, repo, remote, mc, h_before, r_before, base_sha, st10_b, aud_b, local_tags=False,
                        want_url=None, at_head=True, remote_tags=()):
    want_url = str(remote) if want_url is None else want_url
    if at_head:
        B.post("marker commit == local HEAD == origin main (ls-remote)",
               mc == head(repo) == remote_ref(remote) == gout(repo, "ls-remote", "origin", "refs/heads/" + BRANCH).split()[0])
    else:
        B.post("marker commit is an ancestor of origin main", git(remote, "merge-base", "--is-ancestor", mc, BRANCH).returncode == 0)
    B.post("marker commit's only parent is the previous HEAD", gout(repo, "rev-list", "--parents", "-n", "1", mc).split()[1:] == [h_before])
    files = gout(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", "%s^" % mc, mc).split()
    B.post("marker commit changes exactly [%s] (got %s)" % (MARKER_REL, files), files == [MARKER_REL])
    B.post("fast-forward of the previous origin main (no force)", r_before is None or
           git(repo, "merge-base", "--is-ancestor", r_before, mc).returncode == 0)
    B.post("tags on the remote %s (none pushed)%s" % (list(remote_tags), "" if local_tags else ", none in the repository"),
           gout(remote, "tag", "-l").split() == list(remote_tags) and (local_tags or gout(repo, "tag", "-l") == ""))
    mb = blob_at(repo, mc, MARKER_REL)
    m = json.loads(mb)
    want_ck = dict(G["ck"], N=base_sha)
    B.post("marker frozen_commit, authorization == mine", m.get("frozen_commit") == G["frozen"] and
           m.get("authorization") == {"gate0_record_sha256": G["g0sha"], "selection_record_sha256": G["selsha"]})
    B.post("marker remote == %r (got %r), branch == %s" % (want_url, m.get("remote"), BRANCH),
           m.get("remote") == want_url and m.get("branch") == BRANCH)
    B.post("marker test_files_sha256 == my sha256 of the synthetic TEST files", m.get("test_files_sha256") == G["rows_h"])
    B.post("marker checkpoints == the 30 checkpoint hashes of the committed freeze record + N (%d entries)" % len(want_ck),
           m.get("checkpoints") == want_ck)
    B.post("marker models == my 16 TEST models", sorted(m.get("models") or []) == sorted(G["test_models"]))
    B.post("marker st10_record_sha256 / auditor_count_sha256 == sha256 of the committed files",
           m.get("st10_record_sha256") == sha(st10_b) and m.get("auditor_count_sha256") == sha(aud_b))
    B.post("marker code_commit == HEAD before the marker commit", m.get("code_commit") == h_before)
    B.post("marker session_id is 32 lower-case hex", isinstance(m.get("session_id"), str)
           and re.fullmatch(r"[0-9a-f]{32}", m["session_id"]) is not None)
    txt = mb.decode("utf-8")
    B.post("no synthetic TEST content (question / text / ids strings) in the marker",
           not any(s in txt for s in SYN_STRINGS) and "202, 303" not in txt and "[101" not in txt)
    return m


# -------------------------------------------------------------------------------------------------- scenarios

def scen_checkout(ctx, B):
    print("\n== X. ruling 1, the pilot's checkout: ops marker, st10rec, pre, begin (in that order, one probe run per "
          "condition; each must be BLOCKED and write nothing). X0: control (every condition holds).")
    T = G["tiny"]
    S = []

    def add(code, label, prep, vehicle=False, canon_from_start=True):
        S.append((code, label, prep, vehicle))

    def other_branch(ctx, r, rmt, d):
        gout(r, "checkout", "-q", "-b", "work")

    def detached(ctx, r, rmt, d):
        gout(r, "checkout", "-q", "--detach")

    def ahead(ctx, r, rmt, d):
        (r / "local.txt").write_text("a local commit, not pushed\n")
        commit_all(r, "local commit, not pushed")

    def behind(ctx, r, rmt, d):
        o = other_clone(ctx, rmt, d.name + "_other")
        (o / "other.txt").write_text("pushed by another clone\n")
        commit_all(o, "another clone pushes")
        push(o)

    def diverged(ctx, r, rmt, d):
        behind(ctx, r, rmt, d)
        ahead(ctx, r, rmt, d)

    def renamed(ctx, r, rmt, d):
        link = d / "OtherOwner" / "OtherName.git"
        link.parent.mkdir()
        link.symlink_to(rmt)
        ctx["x6_state"] = install_hook(ctx, r, "seturl@first", str(link))

    def unreachable(ctx, r, rmt, d):
        gout(r, "remote", "set-url", "origin", str(d / "no-such-remote.git"))

    def no_branch(ctx, r, rmt, d):
        gout(rmt, "branch", "-m", BRANCH, "other")

    def empty_remote(ctx, r, rmt, d):
        e = d / "empty_remote.git"
        gout(d, "init", "-q", "--bare", "-b", BRANCH, str(e))
        gout(r, "remote", "set-url", "origin", str(e))

    add("X0", "control: every condition holds", None)
    add("X1", "another branch 'work' checked out (same commit as main)", other_branch)
    add("X2", "detached HEAD at main's tip", detached)
    add("X3", "HEAD ahead of origin main (a local commit not pushed)", ahead)
    add("X4", "HEAD behind origin main (another clone pushed a commit)", behind)
    add("X5", "HEAD and origin main diverged", diverged)
    add("X6", "origin is another repository (a pre-push hook sets origin's URL to .../OtherOwner/OtherName.git, a "
              "symlink to the same remote, during the dry run of a first op pre, after the probe set CANONICAL_REPO)",
        renamed, vehicle=True)
    add("X7", "origin unreachable (its path does not exist)", unreachable)
    add("X8", "origin reachable, branch main absent (renamed to 'other' on the remote)", no_branch)
    add("X9", "origin is an empty repository", empty_remote)
    for code, label, prep, vehicle in S:
        repo, remote = new_scenario(ctx, code)
        setup_st10(repo, remote)
        d = repo.parent
        if prep:
            prep(ctx, repo, remote, d)
        fetch_remote = {"X7": None, "X9": d / "empty_remote.git"}.get(code, remote)
        h0, r0 = head(repo), remote_ref(remote)
        st10_b, aud_b = blob_at(repo, "HEAD", ST10_REL), blob_at(repo, "HEAD", AUD_REL)
        kw = {}
        ops = ["marker", "st10rec", "pre", "begin:" + T["0"]]
        if vehicle:
            canon = my_repo_id(origin_url(repo))
            kw = {"canon": canon, "url": str(d / "OtherOwner" / "OtherName.git")}
            ctx["url_at_start"] = origin_url(repo)
            ev = ("ACCEPT", "vehicle: checkout ok at the start; the hook changes origin's URL during its dry run", None)
            ops = ["pre"] + ops
        em, es = m_marker(repo, fetch_remote, **kw), m_st10rec(repo, fetch_remote, **kw)
        ep, eb = m_pre(repo, fetch_remote, **kw), m_begin(repo, fetch_remote, G["rows_h"], T["0"], **kw)
        exps = [em, es, ep, eb[:3]]
        if vehicle:
            exps = [(None,) + ev[1:]] + exps
        print(" %s %s" % (code, label))
        res, rc, err = run_probe(ctx, repo, ops, expect=list(zip(ops, exps)))
        n_cmp = len(res) - 1 if code == "X0" else len(res)
        for item, ex in zip(res[:n_cmp], exps[:n_cmp]):
            B.cmpx(code, (item[0].split(":")[0], item[1], item[2]), ex)
        if vehicle:
            lg = hook_log(ctx["x6_state"])
            B.post("X6 the hook acted once, during the first op's dry run: %s" % lg,
                   any(x.startswith("acted: seturl") for x in lg) and lg[0].startswith("invocation 1"))
            B.post("X6 origin's URL is now the other name (%s)" % origin_url(repo),
                   origin_url(repo) == str(d / "OtherOwner" / "OtherName.git"))
        if code == "X0":
            mc = begin_result(B, code, repo, remote, h0, res[3], eb)
            if mc:
                check_marker_commit(B, repo, remote, mc, h0, r0, T["0"], st10_b, aud_b)
        else:
            nothing_written(B, repo, remote, h0, r0)
    print(" X10 shallow clone (--depth 1 of file://<remote>), then the same clone after fetch --unshallow (control)")
    repo, remote = new_scenario(ctx, "X10_source")
    setup_st10(repo, remote)
    sh = ctx["base"] / "s" / "X10_shallow_clone"
    url = "file://%s" % remote
    gout(ctx["base"], "clone", "-q", "--depth", "1", url, str(sh))
    set_identity(sh)
    print("    shallow file present %s, commits %s, HEAD branch %r" % (
        is_shallow(sh), gout(sh, "rev-list", "--count", "HEAD"), head_ref(sh)))
    h0, r0 = head(sh), remote_ref(remote)
    ops = ["marker", "st10rec", "pre", "begin:" + T["0"]]
    exps = [m_marker(sh, remote), m_st10rec(sh, remote), m_pre(sh, remote), m_begin(sh, remote, G["rows_h"], T["0"])[:3]]
    res, rc, err = run_probe(ctx, sh, ops, expect=list(zip(ops, exps)))
    for item, ex in zip(res, exps):
        B.cmpx("X10", (item[0].split(":")[0], item[1], item[2]), ex)
    nothing_written(B, sh, remote, h0, r0)
    gout(sh, "fetch", "-q", "--unshallow")
    h0, r0 = head(sh), remote_ref(remote)
    st10_b, aud_b = blob_at(sh, "HEAD", ST10_REL), blob_at(sh, "HEAD", AUD_REL)
    print("    X10u after fetch --unshallow: shallow file present %s, commits %s" % (
        is_shallow(sh), gout(sh, "rev-list", "--count", "HEAD")))
    exps = [m_marker(sh, remote), m_st10rec(sh, remote), m_pre(sh, remote), m_begin(sh, remote, G["rows_h"], T["0"])]
    res, rc, err = run_probe(ctx, sh, ops, expect=list(zip(ops, exps)))
    for item, ex in zip(res[:3], exps[:3]):
        B.cmpx("X10u", item, ex)
    mc = begin_result(B, "X10u", sh, remote, h0, res[3], exps[3])
    if mc:
        check_marker_commit(B, sh, remote, mc, h0, r0, T["0"], st10_b, aud_b, want_url=url)


def scen_where(ctx, B):
    print("\n== W. ruling 1, where a marker / result is looked for: the working tree and origin main's latest file tree "
          "(ops marker, begin). Every condition of the checkout holds. Group W-n: places the ruling no longer searches, "
          "expected ACCEPT, marked %s; there begin commits a new marker." % NOT_SEARCHED)
    T = G["tiny"]
    marker = {"kind": "test_evaluation_marker", "note": "planted by the data-auditor"}
    result = {"kind": "test_evaluation_result", "note": "planted by the data-auditor"}
    S = []

    def add(code, label, prep, ns=False):
        S.append((code, label, prep, ns))

    def wt(rel, obj):
        return lambda ctx, r, rmt: write_json(r, rel, obj)

    def committed(*pairs, delete_wt=()):
        def f(ctx, r, rmt):
            for rel, obj in pairs:
                write_json(r, rel, obj)
            commit_all(r, "planted %s" % [p[0].split("/")[-1] for p in pairs])
            push(r)
            for rel in delete_wt:
                (r / rel).unlink()
        return f

    def marker_and_result_wt(ctx, r, rmt):
        committed((MARKER_REL, marker))(ctx, r, rmt)
        write_json(r, RESULT_REL, result)

    def earlier_history(rel, obj):
        def f(ctx, r, rmt):
            write_json(r, rel, obj)
            commit_all(r, "planted")
            gout(r, "rm", "-q", rel)
            commit_all(r, "deleted")
            push(r)
        return f

    def local_side(ctx, r, rmt):
        gout(r, "checkout", "-q", "-b", "side")
        write_json(r, MARKER_REL, marker)
        commit_all(r, "marker on side")
        gout(r, "checkout", "-q", BRANCH)

    def remote_side(fetch):
        def f(ctx, r, rmt):
            o = other_clone(ctx, rmt, "W_clone_%s" % r.parent.name)
            gout(o, "checkout", "-q", "-b", "side")
            write_json(o, MARKER_REL, marker)
            commit_all(o, "marker on remote side")
            push(o, "side")
            if fetch:
                gout(r, "fetch", "-q", "origin")
        return f

    def reflog_only(ctx, r, rmt):
        write_json(r, MARKER_REL, marker)
        write_json(r, RESULT_REL, result)
        commit_all(r, "marker and result, then reset away (never pushed)")
        gout(r, "reset", "-q", "--hard", "HEAD~1")

    def local_tag(ctx, r, rmt):
        write_json(r, MARKER_REL, marker)
        commit_all(r, "marker")
        gout(r, "tag", "kept-marker")
        gout(r, "reset", "-q", "--hard", "HEAD~1")

    def remote_tag(ctx, r, rmt):
        o = other_clone(ctx, rmt, "W_clone_%s" % r.parent.name)
        write_json(o, MARKER_REL, marker)
        commit_all(o, "marker reachable from a remote tag only")
        gout(o, "push", "-q", "origin", "HEAD:refs/tags/kept-marker")

    def merged(how):
        def f(ctx, r, rmt):
            gout(r, "checkout", "-q", "-b", "side")
            write_json(r, MARKER_REL, marker)
            write_json(r, RESULT_REL, result)
            commit_all(r, "marker and result on side")
            if how == "no-ff":
                gout(r, "rm", "-q", MARKER_REL, RESULT_REL)
                commit_all(r, "deleted on side")
            gout(r, "checkout", "-q", BRANCH)
            if how == "no-ff":
                gout(r, "merge", "-q", "--no-ff", "-m", "merge side", "side")
            else:
                gout(r, "merge", "-q", "-s", "ours", "-m", "merge side (ours)", "side")
            gout(r, "branch", "-q", "-D", "side")
            push(r)
        return f

    def index_only(ctx, r, rmt):
        write_json(r, MARKER_REL, marker)
        gout(r, "add", MARKER_REL)
        (r / MARKER_REL).unlink()

    add("W01", "marker only in the working tree (untracked)", wt(MARKER_REL, marker))
    add("W02", "marker only in origin main's latest tree (committed, pushed; working-tree copy deleted)",
        committed((MARKER_REL, marker), delete_wt=(MARKER_REL,)))
    add("W03", "marker in both places", committed((MARKER_REL, marker)))
    add("W04", "result only in the working tree, no marker anywhere", wt(RESULT_REL, result))
    add("W05", "result only in origin main's latest tree, no marker (working-tree copy deleted)",
        committed((RESULT_REL, result), delete_wt=(RESULT_REL,)))
    add("W06", "result committed without a marker (both places)", committed((RESULT_REL, result)))
    add("W07", "marker and result committed (both places)", committed((MARKER_REL, marker), (RESULT_REL, result)))
    add("W08", "marker committed, result only in the working tree", marker_and_result_wt)
    add("W09", "marker and result only in origin main's latest tree (working-tree copies deleted)",
        committed((MARKER_REL, marker), (RESULT_REL, result), delete_wt=(MARKER_REL, RESULT_REL)))
    add("W-n1", "marker only in earlier history (a later pushed commit deleted it)", earlier_history(MARKER_REL, marker), True)
    add("W-n2", "result only in earlier history (a later pushed commit deleted it)", earlier_history(RESULT_REL, result), True)
    add("W-n3", "marker only on another local branch 'side'", local_side, True)
    add("W-n4", "marker only on origin's branch 'side' (fetched)", remote_side(True), True)
    add("W-n5", "marker only on origin's branch 'side' (never fetched)", remote_side(False), True)
    add("W-n6", "marker and result only in the reflog (committed, reset --hard, never pushed)", reflog_only, True)
    add("W-n7", "marker only reachable from a local tag", local_tag, True)
    add("W-n8", "marker only reachable from a tag on origin (never fetched)", remote_tag, True)
    add("W-n9", "marker and result on a side branch, deleted there, merged --no-ff", merged("no-ff"), True)
    add("W-n10", "marker and result on a side branch merged with -s ours (not in main's tree)", merged("ours"), True)
    add("W-n11", "marker only in the index (staged, working-tree copy deleted): marker not searched; begin stops at "
                 "'nothing staged'", index_only, True)
    for code, label, prep, ns in S:
        repo, remote = new_scenario(ctx, code)
        setup_st10(repo, remote)
        prep(ctx, repo, remote)
        h0, r0 = head(repo), remote_ref(remote)
        mf0, rf0 = (repo / MARKER_REL).exists(), (repo / RESULT_REL).exists()
        st10_b, aud_b = blob_at(repo, "HEAD", ST10_REL), blob_at(repo, "HEAD", AUD_REL)
        em, eb = m_marker(repo, remote), m_begin(repo, remote, G["rows_h"], T["0"])
        print(" %s %s%s" % (code, label, (" " + NOT_SEARCHED) if ns else ""))
        res, rc, err = run_probe(ctx, repo, ["marker", "begin:" + T["0"]], expect=[("marker", em), ("begin", eb)])
        B.cmpx(code, res[0], em)
        if eb[0] == "ACCEPT":
            mc = begin_result(B, code, repo, remote, h0, res[1], eb)
            if mc:
                check_marker_commit(B, repo, remote, mc, h0, r0, T["0"], st10_b, aud_b, local_tags=code == "W-n7",
                                    remote_tags=("kept-marker",) if code == "W-n8" else ())
        else:
            B.cmpx(code, (res[1][0].split(":")[0], res[1][1], res[1][2]), eb)
            nothing_written(B, repo, remote, h0, r0, marker_before=mf0, result_before=rf0)


def scen_st10rec(ctx, B):
    print("\n== T. ruling 1, 'TEST is generated once': op st10rec on a repository without an ST10 record except where "
          "planted (checkout holds). Group T-n: places not searched by the ruling, expected ACCEPT, marked %s."
          % NOT_SEARCHED)
    rec = st10_default()
    S = []

    def add(code, label, prep, ns=False):
        S.append((code, label, prep, ns))

    def wt(ctx, r, rmt):
        write_json(r, ST10_REL, rec)

    def tip_only(ctx, r, rmt):
        write_json(r, ST10_REL, rec)
        commit_all(r, "st10")
        push(r)
        (r / ST10_REL).unlink()

    def both(ctx, r, rmt):
        write_json(r, ST10_REL, rec)
        commit_all(r, "st10")
        push(r)

    def earlier(ctx, r, rmt):
        write_json(r, ST10_REL, rec)
        commit_all(r, "st10")
        gout(r, "rm", "-q", ST10_REL)
        commit_all(r, "st10 deleted")
        push(r)

    def side(ctx, r, rmt):
        gout(r, "checkout", "-q", "-b", "side")
        write_json(r, ST10_REL, rec)
        commit_all(r, "st10 on side")
        gout(r, "checkout", "-q", BRANCH)

    def remote_side(ctx, r, rmt):
        o = other_clone(ctx, rmt, "T_clone_%s" % r.parent.name)
        gout(o, "checkout", "-q", "-b", "side")
        write_json(o, ST10_REL, rec)
        commit_all(o, "st10 on remote side")
        push(o, "side")

    def reflog(ctx, r, rmt):
        write_json(r, ST10_REL, rec)
        commit_all(r, "st10, reset away")
        gout(r, "reset", "-q", "--hard", "HEAD~1")

    def tag(ctx, r, rmt):
        write_json(r, ST10_REL, rec)
        commit_all(r, "st10")
        gout(r, "tag", "kept-st10")
        gout(r, "reset", "-q", "--hard", "HEAD~1")

    def index_only(ctx, r, rmt):
        write_json(r, ST10_REL, rec)
        gout(r, "add", ST10_REL)
        (r / ST10_REL).unlink()

    add("T00", "control: no ST10 record anywhere", lambda ctx, r, rmt: None)
    add("T01", "ST10 record only in the working tree (untracked)", wt)
    add("T02", "ST10 record only in origin main's latest tree (working-tree copy deleted)", tip_only)
    add("T03", "ST10 record in both places", both)
    add("T-n1", "ST10 record only in earlier history (deleted by a later pushed commit)", earlier, True)
    add("T-n2", "ST10 record only on another local branch", side, True)
    add("T-n3", "ST10 record only on origin's branch 'side' (never fetched)", remote_side, True)
    add("T-n4", "ST10 record only in the reflog", reflog, True)
    add("T-n5", "ST10 record only reachable from a local tag", tag, True)
    add("T-n6", "ST10 record only in the index (working-tree copy deleted)", index_only, True)
    for code, label, prep, ns in S:
        repo, remote = new_scenario(ctx, code)
        prep(ctx, repo, remote)
        h0, r0 = head(repo), remote_ref(remote)
        e = m_st10rec(repo, remote)
        print(" %s %s%s" % (code, label, (" " + NOT_SEARCHED) if ns else ""))
        res, rc, err = run_probe(ctx, repo, ["st10rec"], expect=[("st10rec", e)])
        B.cmpx(code, res[0], e)
        B.post("%s HEAD and origin unchanged" % code, head(repo) == h0 and remote_ref(remote) == r0)


def scen_st10(ctx, B):
    print("\n== A. ST10 gate (supplementary ruling 3): op st10 and begin, one defect per scenario (fresh repository each)")
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
    add("A61 control: every count at its limit, all bound",
        rec=dict(d(), counts={c: G["limits"][c] for c in CHECKS}), aud=dict(aud_default(), l6_test_count=G["limits"]["L6"]))
    for i, (name, rec, aud, prep, info) in enumerate(S):
        repo, remote = new_scenario(ctx, "A%02d" % i)
        setup_st10(repo, remote, rec, aud)
        if prep:
            prep(repo)
            if name.startswith("A13") or name.startswith("A17"):
                push(repo)
        h0, r0 = head(repo), remote_ref(remote)
        e_st10 = m_st10(repo, G["rows_h"])
        e_begin = m_begin(repo, remote, G["rows_h"], G["tiny"]["0"])
        ops = ["st10"] if (name.startswith("A61") or name.startswith("A20")) else ["st10", "begin:" + G["tiny"]["0"]]
        print(" %s" % name)
        res, rc, err = run_probe(ctx, repo, ops, expect=list(zip(ops, [e_st10, e_begin]))[:len(ops)])
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
    print("\n== C. every condition holds: begin, evaluate / gate calls, finish once every model is claimed, then marker "
          "(one repository, one process); C2 another process; K other clones")
    repo, remote = new_scenario(ctx, "C_main")
    setup_st10(repo, remote)
    stale = other_clone(ctx, remote, "K2_stale_clone")
    T = G["tiny"]
    print(" C0 evaluate, gate and finish before any begin (no session)")
    ops0 = ["eval:N:0", "gate:N:%s" % T["0"], "finish"]
    exp0 = m_session_ops(ops0, T, begin_ok=False)
    res, rc, err = run_probe(ctx, repo, ops0, expect=list(zip(ops0, exp0)))
    for item, ex in zip(res, exp0):
        B.cmpx("C0", item, ex)
    h0, r0 = head(repo), remote_ref(remote)
    st10_b, aud_b = blob_at(repo, "HEAD", ST10_REL), blob_at(repo, "HEAD", AUD_REL)
    e_begin = m_begin(repo, remote, G["rows_h"], T["0"])
    F, L = SELECTED["F"], SELECTED["L"]
    rest = [m for m in G["test_models"] if m != "N"]
    ops = ["eval:N:7", "eval:N:0", "eval:N:0", "eval:F-%s-seed202:1" % F, "eval:F-F1-seed101:4", "eval:Z-Z9-seed1:0",
           "finish", "gate:N:%s" % T["0"], "gate:N:%s" % T["0"], "eval:N:0", "gate:S-%s-seed101:%s" % (F, "f" * 64)]
    ops += ["gate:%s:%s" % (m, G["ck"][m]) for m in rest]
    ops += ["finish"]
    exp = m_session_ops(ops, T, begin_ok=e_begin[0] == "ACCEPT", base_sha=T["0"])
    after = ["finish", "marker", "st10rec", "begin:" + T["0"], "eval:N:0", "gate:N:%s" % T["0"]]
    all_ops = ["begin:" + T["0"]] + ops + after
    print(" C1 begin + %d evaluate / gate / finish calls + %s in one process" % (len(ops), [a.split(":")[0] for a in after]))
    pre_after = [("REFUSE", "the session ended with finish", "session"),
                 ("EVALUATED", "result committed and pushed by finish", "already evaluated"),
                 ("REFUSE", "the ST10 record exists", "generated once"),
                 ("EVALUATED", "result exists", "already evaluated"),
                 ("REFUSE", "no live session", "session"), ("REFUSE", "no live session", "session")]
    res, rc, err = run_probe(ctx, repo, all_ops, expect=list(zip(all_ops, [e_begin] + exp + pre_after)))
    mc = begin_result(B, "C1", repo, remote, h0, res[0], e_begin)
    if mc:
        check_marker_commit(B, repo, remote, mc, h0, r0, T["0"], st10_b, aud_b, at_head=False)
    for item, ex in zip(res[1:1 + len(ops)], exp):
        B.cmpx("C1", item, ex)
    fin = res[len(ops)]
    rc_m = re.search(r"result commit ([0-9a-f]{40})", fin[2])
    rcm = rc_m.group(1) if rc_m else None
    if rcm:
        B.post("result commit == HEAD == origin main; its only parent is the marker commit",
               rcm == head(repo) == remote_ref(remote) and gout(repo, "rev-list", "--parents", "-n", "1", rcm).split()[1:] == [mc])
        files = gout(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", "%s^" % rcm, rcm).split()
        B.post("result commit changes exactly [%s] (got %s)" % (RESULT_REL, files), files == [RESULT_REL])
        rj = json.loads(blob_at(repo, rcm, RESULT_REL))
        mj = json.loads(blob_at(repo, mc, MARKER_REL))
        B.post("result == the probe's synthetic result + session_id (== the marker's) + marker_commit (%s)" % sorted(rj),
               rj == {"probe": "synthetic result", "session_id": mj["session_id"], "marker_commit": mc})
        B.post("no tags on the remote", gout(remote, "tag", "-l") == "")
    for item, ex in zip(res[1 + len(ops):], pre_after):
        B.cmpx("C1", (item[0].split(":")[0], item[1], item[2]), ex)
    print(" C2 another process, same repository after finish")
    h1, r1 = head(repo), remote_ref(remote)
    ops2 = ["marker", "st10rec", "pre", "begin:" + T["0"], "eval:N:0", "finish"]
    exp2 = [m_marker(repo, remote), m_st10rec(repo, remote), m_pre(repo, remote),
            m_begin(repo, remote, G["rows_h"], T["0"])[:3], ("REFUSE", "no session in this process", "session"),
            ("REFUSE", "no session in this process", "session")]
    res, rc, err = run_probe(ctx, repo, ops2, expect=list(zip(ops2, exp2)))
    for item, ex in zip(res, exp2):
        B.cmpx("C2", (item[0].split(":")[0], item[1], item[2]), ex)
    B.post("C2 wrote nothing", head(repo) == h1 and remote_ref(remote) == r1)
    print(" K1 a fresh clone of the remote after finish")
    k1 = other_clone(ctx, remote, "K1_fresh_clone")
    k1h = head(k1)
    exk = [m_marker(k1, remote), m_begin(k1, remote, G["rows_h"], T["0"])[:3]]
    res, rc, err = run_probe(ctx, k1, ["marker", "begin:" + T["0"]], expect=list(zip(["marker", "begin"], exk)))
    for item, ex in zip(res, exk):
        B.cmpx("K1", (item[0].split(":")[0], item[1], item[2]), ex)
    B.post("K1 nothing committed", head(k1) == k1h)
    print(" K2 a clone made before begin (behind origin main), then the same clone after git pull --ff-only")
    k2h = head(stale)
    exk = [m_marker(stale, remote), m_begin(stale, remote, G["rows_h"], T["0"])[:3]]
    res, rc, err = run_probe(ctx, stale, ["marker", "begin:" + T["0"]], expect=list(zip(["marker", "begin"], exk)))
    for item, ex in zip(res, exk):
        B.cmpx("K2", (item[0].split(":")[0], item[1], item[2]), ex)
    B.post("K2 nothing committed, no marker file", head(stale) == k2h and not (stale / MARKER_REL).exists())
    gout(stale, "pull", "-q", "--ff-only", "origin", BRANCH)
    exk = [m_marker(stale, remote), m_begin(stale, remote, G["rows_h"], T["0"])[:3]]
    res, rc, err = run_probe(ctx, stale, ["marker", "begin:" + T["0"]], expect=list(zip(["marker", "begin"], exk)))
    for item, ex in zip(res, exk):
        B.cmpx("K2p", (item[0].split(":")[0], item[1], item[2]), ex)
    print(" C3 begin twice in one process (fresh repository)")
    repo, remote = new_scenario(ctx, "C3_twice")
    setup_st10(repo, remote)
    h0 = head(repo)
    e = m_begin(repo, remote, G["rows_h"], T["0"])
    e2 = (BLK, "the marker begin#1 committed and pushed, no result", "already started") if e[0] == "ACCEPT" else e
    res, rc, err = run_probe(ctx, repo, ["begin:" + T["0"], "begin:" + T["0"]],
                             expect=[("begin", e), ("begin#2", e2)])
    begin_result(B, "C3", repo, remote, h0, res[0], e)
    B.cmpx("C3", ("begin#2", res[1][1], res[1][2]), e2)
    B.post("one marker commit only", len(introduced(repo, h0, MARKER_REL)) == 1 and gout(repo, "rev-list", "--count", "HEAD") == "3")


def scen_after_begin(ctx, B):
    print("\n== E. changes after begin in the same process (a pre-push hook of the clone acts once: '@1' during begin's "
          "real push of the marker commit, '@2' during the dry run of a following op pre, used as a vehicle). "
          "Ops after begin: eval, gate, finish, marker.")
    T = G["tiny"]
    S = [("E0", "noop@1", None, "control: the hook acts and changes nothing"),
         ("E1", "commit_local@1", ("checkout", "HEAD moved on by a local commit (not pushed)"),
          "a local commit after the marker commit, not pushed"),
         ("E2", "commit_push@2", ("checkout", "HEAD moved on by a commit that was pushed"),
          "a commit after the marker commit, pushed to origin main"),
         ("E3", "branch@1", ("checkout", "branch 'other' checked out at the marker commit"),
          "another branch 'other' checked out at the marker commit"),
         ("E4", "detach@1", ("checkout", "detached HEAD at the marker commit"), "detached HEAD at the marker commit"),
         ("E5", "reset@2", ("checkout", "HEAD reset to the commit before the marker"),
          "git reset --hard HEAD~1 after the marker commit (local only)"),
         ("E6", "remote_moves@2", ("remote", "another clone pushed a commit after the marker; local HEAD still the "
                                             "marker commit"),
          "origin main moves on (another clone pushes); local HEAD stays the marker commit"),
         ("E7", "st10_wt@1", ("st10", "changed in the working tree after the marker"),
          "the ST10 record changed in the working tree after the marker (not committed)")]
    for code, mode, change, label in S:
        repo, remote = new_scenario(ctx, code + "_" + mode.split("@")[0])
        setup_st10(repo, remote)
        arg = str(repo.parent / "E_other_clone") if mode.startswith("remote_moves") else ""
        state = install_hook(ctx, repo, mode, arg)
        h0, r0 = head(repo), remote_ref(remote)
        st10_b, aud_b = blob_at(repo, "HEAD", ST10_REL), blob_at(repo, "HEAD", AUD_REL)
        e = m_begin(repo, remote, G["rows_h"], T["0"])
        vehicle = mode.endswith("@2")
        if code == "E6":            # every model claimed, so that finish reaches its preconditions (with the fetch)
            gates = ["gate:N:%s" % T["0"]] + ["gate:%s:%s" % (m, G["ck"][m]) for m in G["test_models"] if m != "N"]
        else:
            gates = ["gate:N:%s" % T["0"]]
        ops = (["pre"] if vehicle else []) + ["eval:N:0"] + gates + ["finish"]
        exp = m_session_ops(ops, T, begin_ok=e[0] == "ACCEPT", change=change, base_sha=T["0"])
        # the final op marker: after the change, from my model of the checkout and the two places
        if change is None or change[0] == "st10":
            em = (BLK, "marker committed and pushed, no result", "already started")
        elif mode.startswith("commit_local") or mode.startswith("reset"):
            em = (BLK, "HEAD is not origin main", "latest commit")
        elif mode.startswith("branch") or mode.startswith("detach"):
            em = (BLK, "the checked-out branch is not main", "branch")
        elif mode.startswith("commit_push"):
            em = (BLK, "HEAD == origin main (the pushed commit); the marker in both places, no result", "already started")
        else:
            em = (BLK, "HEAD (marker commit) behind origin main", "latest commit")
        all_ops = ["begin:" + T["0"]] + ops + ["marker"]
        print(" %s %s" % (code, label))
        res, rc, err = run_probe(ctx, repo, all_ops, expect=list(zip(all_ops, [e] + exp + [em])))
        lg = hook_log(state)
        print("    hook log: %s" % lg)
        mc = begin_result(B, code, repo, remote, h0, res[0], e)
        for item, ex in zip(res[1:1 + len(ops)], exp):
            B.cmpx(code, item, ex)
        B.cmpx(code, res[-1], em)
        B.post("%s the hook acted once, as planned" % code, sum(x.startswith("acted:") for x in lg) == 1)
        if mc:
            B.post("%s origin main == %s" % (code, "a commit after the marker" if mode.split("@")[0] in
                                             ("commit_push", "remote_moves") else "the marker commit"),
                   (remote_ref(remote) != mc and git(remote, "merge-base", "--is-ancestor", mc, BRANCH).returncode == 0)
                   if mode.split("@")[0] in ("commit_push", "remote_moves") else remote_ref(remote) == mc)
            B.post("%s no result file anywhere (finish wrote nothing)" % code, not (repo / RESULT_REL).exists()
                   and not has_path(remote, BRANCH, RESULT_REL))


def scen_preconditions(ctx, B):
    print("\n== D. ruling 2, commit and push preconditions: ops pre and begin; nothing written when they fail before "
          "the marker; a push refused only for real leaves the local marker commit, and later ops are BLOCKED")
    T = G["tiny"]
    empty = ctx["base"] / "empty_gitconfig"
    empty.write_text("")

    def staged(ctx, r, rmt):
        (r / "staged.txt").write_text("staged\n")
        gout(r, "add", "staged.txt")
        return {}

    def no_identity(ctx, r, rmt):
        gout(r, "config", "--unset", "user.name")
        gout(r, "config", "--unset", "user.email")
        gout(r, "config", "user.useConfigOnly", "true")
        return {"env": {"GIT_CONFIG_GLOBAL": str(empty)}}

    def bad_pushurl(ctx, r, rmt):
        gout(r, "config", "remote.origin.pushurl", str(r.parent / "no-such-push-target.git"))
        return {"dry_ok": False}

    def hook_refuses_all(ctx, r, rmt):
        install_hook(ctx, r, "refuse_all@0")
        return {"dry_ok": False}

    for code, label, prep in (("D1", "a staged change in the index", staged),
                              ("D2", "no committer identity (user.useConfigOnly, no user.name / user.email, empty "
                                     "global config)", no_identity),
                              ("D3", "push URL not pushable (remote.origin.pushurl names a path that does not exist; "
                                     "the fetch URL works)", bad_pushurl),
                              ("D3b", "a local pre-push hook refuses every push (the dry run included)", hook_refuses_all)):
        repo, remote = new_scenario(ctx, code)
        setup_st10(repo, remote)
        kw = prep(ctx, repo, remote)
        env = kw.get("env")
        h0, r0 = head(repo), remote_ref(remote)
        ep = m_pre(repo, remote, env=env, dry_ok=kw.get("dry_ok", True))
        eb = m_begin(repo, remote, G["rows_h"], T["0"], env=env, dry_ok=kw.get("dry_ok", True))
        print(" %s %s" % (code, label))
        res, rc, err = run_probe(ctx, repo, ["pre", "begin:" + T["0"]], env=env, expect=[("pre", ep), ("begin", eb)])
        B.cmpx(code, res[0], ep)
        B.cmpx(code, (res[1][0].split(":")[0], res[1][1], res[1][2]), eb)
        nothing_written(B, repo, remote, h0, r0)

    for code, label in (("D4", "origin's pre-receive hook refuses every push (a dry run runs no server-side hook)"),
                        ("D4b", "a local pre-push hook accepts its first invocation (begin's dry run) and refuses the "
                                "next (begin's real push)")):
        repo, remote = new_scenario(ctx, code)
        setup_st10(repo, remote)
        if code == "D4":
            hk = remote / "hooks" / "pre-receive"
            hk.write_text("#!/bin/sh\necho 'auditor: pushes refused' >&2\nexit 1\n")
            hk.chmod(0o755)
        else:
            install_hook(ctx, repo, "refuse_after_first@0")
        h0, r0 = head(repo), remote_ref(remote)
        eb = m_begin(repo, remote, G["rows_h"], T["0"], real_ok=False)
        ee = m_session_ops(["eval:N:0"], T, begin_ok=False)[0]
        print(" %s %s" % (code, label))
        res, rc, err = run_probe(ctx, repo, ["begin:" + T["0"], "eval:N:0"], expect=[("begin", eb), ("eval:N:0", ee)])
        B.cmpx(code, (res[0][0].split(":")[0], res[0][1], res[0][2]), eb)
        B.cmpx(code, res[1], ee)
        h1 = head(repo)
        files = gout(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", "%s^" % h1, h1).split() if h1 != h0 else []
        B.post("%s the marker is committed locally on top of the previous HEAD (only its path); origin unchanged" % code,
               h1 != h0 and files == [MARKER_REL] and remote_ref(remote) == r0)
        ops = ["marker", "st10rec", "pre", "begin:" + T["0"]]
        exps = [m_marker(repo, remote), m_st10rec(repo, remote), m_pre(repo, remote),
                m_begin(repo, remote, G["rows_h"], T["0"])[:3]]
        print(" %s, later: a new process" % code)
        res, rc, err = run_probe(ctx, repo, ops, expect=list(zip(ops, exps)))
        for item, ex in zip(res, exps):
            B.cmpx(code + "+", (item[0].split(":")[0], item[1], item[2]), ex)
        B.post("%s later ops wrote nothing" % code, head(repo) == h1 and remote_ref(remote) == r0)

    repo, remote = new_scenario(ctx, "D5_ignored_results")
    setup_st10(repo, remote)
    (repo / ".gitignore").write_text(RES + "/\n")
    commit_all(repo, "results ignored")
    push(repo)
    h0, r0 = head(repo), remote_ref(remote)
    eb = m_begin(repo, remote, G["rows_h"], T["0"], add_ok=False)
    print(" D5 the results directory is ignored (.gitignore): the marker is written, cannot be added")
    res, rc, err = run_probe(ctx, repo, ["begin:" + T["0"]], expect=[("begin", eb)])
    B.cmpx("D5", (res[0][0].split(":")[0], res[0][1], res[0][2]), eb)
    B.post("D5 marker file in the working tree, nothing committed or pushed",
           (repo / MARKER_REL).exists() and head(repo) == h0 and remote_ref(remote) == r0
           and git(repo, "diff", "--cached", "--quiet").returncode == 0)
    ops = ["marker", "begin:" + T["0"]]
    exps = [m_marker(repo, remote), m_begin(repo, remote, G["rows_h"], T["0"])[:3]]
    res, rc, err = run_probe(ctx, repo, ops, expect=list(zip(ops, exps)))
    for item, ex in zip(res, exps):
        B.cmpx("D5+", (item[0].split(":")[0], item[1], item[2]), ex)

    repo, remote = new_scenario(ctx, "D6_basehash")
    setup_st10(repo, remote)
    h0, r0 = head(repo), remote_ref(remote)
    eb = m_begin(repo, remote, G["rows_h"], "xyz")
    print(" D6 base model hash not 64 hex")
    res, rc, err = run_probe(ctx, repo, ["begin:xyz"], expect=[("begin:xyz", eb)])
    B.cmpx("D6", res[0], eb)
    nothing_written(B, repo, remote, h0, r0)

    repo, remote = new_scenario(ctx, "D7_dirty")
    setup_st10(repo, remote)
    (repo / "README.audit").write_text("modified, not staged\n")
    (repo / "untracked.txt").write_text("untracked\n")
    h0, r0 = head(repo), remote_ref(remote)
    st10_b, aud_b = blob_at(repo, "HEAD", ST10_REL), blob_at(repo, "HEAD", AUD_REL)
    eb = m_begin(repo, remote, G["rows_h"], T["0"])
    print(" D7 an unstaged modification and an untracked file outside the code paths (nothing staged)")
    res, rc, err = run_probe(ctx, repo, ["begin:" + T["0"]], expect=[("begin", eb)])
    mc = begin_result(B, "D7", repo, remote, h0, res[0], eb)
    if mc:
        check_marker_commit(B, repo, remote, mc, h0, r0, T["0"], st10_b, aud_b)
        B.post("modified and untracked files left as they were (not committed)",
               sorted(git(repo, "status", "--porcelain").stdout.decode().splitlines()) == [" M README.audit", "?? untracked.txt"])

    repo, remote = new_scenario(ctx, "D9_follow_tags")
    setup_st10(repo, remote)
    gout(repo, "config", "push.followTags", "true")
    gout(repo, "tag", "-a", "-m", "annotated tag of the auditor", "audit-annotated", "HEAD")
    h0, r0 = head(repo), remote_ref(remote)
    st10_b, aud_b = blob_at(repo, "HEAD", ST10_REL), blob_at(repo, "HEAD", AUD_REL)
    eb = m_begin(repo, remote, G["rows_h"], T["0"])
    print(" D9 push.followTags=true and an annotated tag on HEAD")
    res, rc, err = run_probe(ctx, repo, ["begin:" + T["0"]], expect=[("begin", eb)])
    mc = begin_result(B, "D9", repo, remote, h0, res[0], eb)
    if mc:
        check_marker_commit(B, repo, remote, mc, h0, r0, T["0"], st10_b, aud_b, local_tags=True)
    B.post("local annotated tag still there, remote has no tag", gout(repo, "tag", "-l") == "audit-annotated"
           and gout(remote, "tag", "-l") == "")


def scen_nonobject(ctx, B):
    print("\n== G. the committed Gate 0 or freeze record is valid JSON but not an object: begin and eval refuse")
    T = G["tiny"]
    for code, which, make, label in (("G1", "gate0", lambda o: [o], "Gate 0 record is a JSON array [record]"),
                                     ("G2", "freeze", lambda o: None, "freeze record is JSON null")):
        repo, remote = new_scenario(ctx, code + "_nonobject")
        g0 = json.loads((repo / G0_REL).read_text())
        sel = json.loads((repo / SEL_REL).read_text())
        if which == "gate0":
            g0sha = write_json(repo, G0_REL, make(g0))
            sel["gate0_record_sha256"] = g0sha
            selsha = write_json(repo, SEL_REL, sel)
        else:
            g0sha = G["g0sha"]
            selsha = write_json(repo, SEL_REL, make(sel))
        commit_all(repo, "auditor: %s" % label)
        push(repo)
        rec = dict(st10_default(), authorization={"gate0_record_sha256": g0sha, "selection_record_sha256": selsha})
        setup_st10(repo, remote, rec)
        h0, r0 = head(repo), remote_ref(remote)
        eb = m_begin(repo, remote, G["rows_h"], T["0"])
        ee = m_records(repo) or m_session_ops(["eval:N:0"], T, begin_ok=False)[0]
        print(" %s %s" % (code, label))
        res, rc, err = run_probe(ctx, repo, ["begin:" + T["0"], "eval:N:0"], expect=[("begin", eb), ("eval:N:0", ee)])
        B.cmpx(code, (res[0][0].split(":")[0], res[0][1], res[0][2]), eb)
        B.cmpx(code, res[1], ee)
        B.post("no ERROR line", all(r[1] != "ERROR" for r in res))
        nothing_written(B, repo, remote, h0, r0)


def scen_secret(ctx, B):
    print("\n== U. origin's URL holds user information (file://auditor:<SECRET>@<path>): neither the marker nor the "
          "probe's output may hold the secret")
    T = G["tiny"]
    repo, remote = new_scenario(ctx, "U1_secret_url")
    setup_st10(repo, remote)
    url = "file://auditor:%s@%s" % (SECRET, remote)
    gout(repo, "remote", "set-url", "origin", url)
    want_url = my_strip_userinfo(url)
    h0, r0 = head(repo), remote_ref(remote)
    st10_b, aud_b = blob_at(repo, "HEAD", ST10_REL), blob_at(repo, "HEAD", AUD_REL)
    em, eb = m_marker(repo, remote), m_begin(repo, remote, G["rows_h"], T["0"])
    print(" U1 every condition holds")
    res, rc, err = run_probe(ctx, repo, ["marker", "begin:" + T["0"]], expect=[("marker", em), ("begin", eb)])
    text = ctx["last_text"]
    B.cmpx("U1", res[0], em)
    mc = begin_result(B, "U1", repo, remote, h0, res[1], eb)
    if mc:
        check_marker_commit(B, repo, remote, mc, h0, r0, T["0"], st10_b, aud_b, want_url=want_url)
    B.post("secret not in the committed marker, not in the probe's output",
           SECRET.encode() not in (blob_at(repo, "HEAD", MARKER_REL) or b"") and SECRET not in text)
    repo, remote = new_scenario(ctx, "U4_secret_unreachable")
    setup_st10(repo, remote)
    gone = repo.parent / "no-such-remote.git"
    gout(repo, "remote", "set-url", "origin", "file://auditor:%s@%s" % (SECRET, gone))
    h0 = head(repo)
    ops = ["marker", "st10rec", "pre", "begin:" + T["0"]]
    exps = [m_marker(repo, None), m_st10rec(repo, None), m_pre(repo, None), m_begin(repo, None, G["rows_h"], T["0"])[:3]]
    print(" U4 origin with the secret points at a path that does not exist")
    res, rc, err = run_probe(ctx, repo, ops, expect=list(zip(ops, exps)))
    for item, ex in zip(res, exps):
        B.cmpx("U4", (item[0].split(":")[0], item[1], item[2]), ex)
    B.post("secret not in the probe's output; nothing written", SECRET not in ctx["last_text"] and head(repo) == h0
           and not (repo / MARKER_REL).exists())


def scen_probe_guard(ctx, B):
    print("\n== P. the probe's own guard: it refuses the pilot's repository and any clone whose origin is "
          "leotree2020/OpenMythos, before any operation")
    T = G["tiny"]

    def raw(repo, ops):
        cmd = [ctx["py"], "-I", "-B", ctx["probe"], str(repo), str(ctx["test_dir"]), *ops]
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=ctx["base"], timeout=900,
                           env=dict(os.environ, **BASE_ENV, GIT_OPTIONAL_LOCKS="0"))
        ctx["runs"] = ctx.get("runs", 0) + 1
        return r

    def refused(code, r, ops):
        op_lines = [ln for ln in r.stdout.splitlines() if any(ln.startswith(op + " ") for op in ops)]
        msg = (r.stderr.strip().splitlines() or [""])[-1]
        ok = r.returncode != 0 and msg.startswith("probe refused:") and op_lines == []
        B.cmp(code, "probe", "REFUSED", "REFUSED" if ok else "RAN (exit %d, %d op lines)" % (r.returncode, len(op_lines)),
              msg, "origin is the pilot's repository")

    d = ctx["base"] / "s" / "P1"
    repo, remote = new_scenario(ctx, "P1")
    canon_remote = d / "leotree2020" / "OpenMythos.git"
    canon_remote.parent.mkdir(parents=True)
    gout(d, "init", "-q", "--bare", "-b", BRANCH, str(canon_remote))
    gout(repo, "remote", "set-url", "origin", str(canon_remote))
    setup_st10(repo, canon_remote)
    h0, r0 = head(repo), remote_ref(canon_remote)
    ops = ["marker", "begin:" + T["0"]]
    print(" P1 throw-away clone whose origin is %s (my repo id %r); ops marker, begin" % (canon_remote, my_repo_id(str(canon_remote))))
    refused("P1", raw(repo, ops), ops)
    B.post("P1 nothing written and nothing fetched: HEAD, remote main unchanged, no marker, no .git/FETCH_HEAD",
           head(repo) == h0 and remote_ref(canon_remote) == r0 and not (repo / MARKER_REL).exists()
           and not (repo / ".git" / "FETCH_HEAD").exists())
    pilot = ctx["repo"]
    fh = pilot / ".git" / "FETCH_HEAD"
    pe = {"GIT_OPTIONAL_LOCKS": "0"}
    state = lambda: (gout(pilot, "rev-parse", "HEAD", env=pe), gout(pilot, "write-tree", env=pe),
                     fh.stat().st_mtime_ns if fh.exists() else None,
                     git(pilot, "status", "--porcelain", "--untracked-files=all", env=pe).stdout)
    before = state()
    print(" P4 REPO = the pilot's repository %s; no operation" % pilot)
    refused("P4", raw(pilot, []), [])
    B.post("P4 the pilot's repository unchanged (HEAD, index tree, FETCH_HEAD mtime, status)", before == state())


def main():
    if len(sys.argv) != 4:
        raise SystemExit("usage: ic5_01_gate_scenarios.py <repo_root> <python_for_probe> <base_dir_outside_repo>")
    repo, py, base = Path(sys.argv[1]).resolve(), sys.argv[2], Path(sys.argv[3]).resolve()
    if base == repo or repo in base.parents:
        raise SystemExit("base dir must be outside the repository")
    if base.exists():
        shutil.rmtree(base)
    base.mkdir(parents=True)
    probe = repo / PROBE_REL
    ctx = {"repo": repo, "py": py, "base": base, "probe": str(probe)}
    pe = {"GIT_OPTIONAL_LOCKS": "0"}
    staged = git(repo, "cat-file", "blob", ":" + PROBE_REL, env=pe).stdout
    same = probe.read_bytes() == staged
    print("probe run: %s sha256 %s | staged probe (index) sha256 %s | the probe run is the staged one: %s | HEAD %s | "
          "staged tree %s" % (probe, sha(probe.read_bytes()), sha(staged), same,
                              gout(repo, "rev-parse", "HEAD", env=pe), gout(repo, "write-tree", env=pe)))
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
    scen_checkout(ctx, B)
    scen_where(ctx, B)
    scen_st10rec(ctx, B)
    scen_st10(ctx, B)
    scen_main(ctx, B)
    scen_after_begin(ctx, B)
    scen_preconditions(ctx, B)
    scen_nonobject(ctx, B)
    scen_secret(ctx, B)
    scen_probe_guard(ctx, B)
    print("\nprobe's CANONICAL_REPO line == my reading of origin's URL at the probe's start: checked in %d runs, "
          "mismatches %s" % (ctx.get("canon_checked", 0), ctx.get("canon_bad", [])))
    ok &= not ctx.get("canon_bad")
    print("probe runs %d; runs whose stdout+stderr contain the URL secret: %d" % (ctx.get("runs", 0), ctx.get("secret_seen", 0)))
    ok &= ctx.get("secret_seen", 0) == 0
    print("\nsummary: compared operations same %d | DIFFERENT %d | INFO (no expectation) %d | ERROR or unparsable "
          "probe output among them: %d | post-checks FAILED %d" % (B.same, B.bad, B.info, B.defect, B.post_bad))
    print("gates (my model vs the code through the staged probe): %s" % (
        "consistent" if B.bad == 0 and B.post_bad == 0 else "NOT consistent"))
    return bool(ok and B.bad == 0 and B.post_bad == 0 and B.defect == 0)


run(main)
