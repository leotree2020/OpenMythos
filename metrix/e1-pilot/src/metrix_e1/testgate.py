"""The two hard preconditions of TEST evaluation in METRIX E1-PILOT: ST10 from committed records, and "TEST is
evaluated once".

Protocol v1.1 section 8 step 8 (freeze record -> test_qa.jsonl, general_test.jsonl -> L3-L5 on TEST -> L6 TEST part by
the Executor and by the data-auditor, results must agree -> ST10 -> TEST evaluated once), section 3 (L6 TEST part),
section 11 ST10. Owner's stage-C message (tasks/IMPL_C_OWNER_MESSAGE.md): stage-B ruling item 7 and Review Gate
supplementary rulings 3-5 of 2026-11-24. Review Gate's ruling on C1 of 2026-11-25 (tasks/IMPL_C1_RULING.md, "C1
ruling" below).

What the gates guard against (C1 ruling): an Executor who follows the rules and the RUNBOOK evaluating TEST twice by
accident, or evaluating TEST while ST10 does not hold. Deliberate tampering by someone with write access to the
repository (rewritten history, forged records) is left to GitHub's branch protection and the review records.

The pilot's checkout (check_checkout; C1 ruling 1). Every TEST path runs in a clone whose remote PILOT_REMOTE is the
pilot's repository (CANONICAL_REPO: the owner/name of its fetch URL; the host is not compared), with PILOT_BRANCH
checked out, not shallow, and HEAD equal to the latest commit of PILOT_BRANCH on the remote, fetched now; otherwise
BLOCKED. A record "exists" when it is in the working tree or in the file tree of that latest commit; no other commit,
ref, reflog entry or tag is searched (C1 ruling 1). On GitHub the branch refuses force-pushes and deletion and accepts
direct pushes (C1 ruling 6; RUNBOOK_A100.md).

The commit and push preconditions (check_commit_preconditions; C1 ruling 2), checked before the ST10 record, the
marker or the result is written: the pilot's checkout, nothing staged, a committer identity, `git push --dry-run`
accepted. commit_paths then commits exactly the record's path and pushes it (no tags, no force) and checks the remote
ref. A push the remote still refuses (a dry run runs no server-side hook) is BLOCKED; the record stays in the working
tree and refuses the step again.

ST10 record, results/st10_record.json, written by the step 8 TEST driver (test_data.main) right after the TEST files and
the TEST part of the leakage checks (st10_record, write_st10_record):
    kind "st10", mode "formal", label null, frozen_commit, authorization {gate0_record_sha256,
    selection_record_sha256}, test_files_sha256 {test_qa.jsonl, general_test.jsonl}, code_commit (HEAD when the TEST
    files were generated; the package and run_pilot.py had no uncommitted change: checked before generation), counts
    {L3a, L3b, L4, L5, L6}: the raw counts of the TEST part, no limit, no flag, no result word.
    Before it generates anything the driver checks the commit and push preconditions and refuses when an ST10 record
    exists (refuse_if_st10_record: TEST is generated once); afterwards it commits and pushes the record. A push refused
    after generation: TEST counts as generated, no second run (the record in the working tree refuses it), BLOCKED,
    report to the Owner, who decides whether this one file is committed by hand (C1 ruling 2).
data-auditor's count, audit/st10_l6_test_count.json, written by the data-auditor with its own script and committed:
    kind "st10_auditor_l6", frozen_commit, general_test_sha256 (of the file it counted), l6_test_count (integer).
ST10 gate (st10_check), before the TEST evaluation starts and again before every TEST evaluation call: both files are
committed (HEAD blob = working tree); the record is bound to the TestAuthorization (frozen commit, the two record
hashes) and to the TEST rows about to be evaluated (their sha256); its code commit is an ancestor of HEAD; every count
is an integer, re-judged against the frozen limit (SPLIT_MANIFEST.json, leakage._rules) by stops.st10; the
data-auditor's file names the same general_test.jsonl and its count must equal the Executor's L6 count (stops.st10).
A missing or unbound record refuses the TEST path (ImplementationFail, as leakage.verify_authorization); a count over
its limit or two different L6 counts stop with ST10 (BLOCKED, report to the Owner).

TEST evaluated once, marker results/test_evaluation_marker.json:
  - begin_test_evaluation refuses while a marker or a result exists (refuse_if_marker). Otherwise it checks the
    authorization, the ST10 gate and the commit and push preconditions, writes the marker (frozen commit,
    authorization, remote URL and branch, sha256 of the ST10 record and of the data-auditor's count, TEST file hashes,
    every checkpoint hash of the committed freeze record plus N, the models TEST evaluates, code commit, a random
    session id), commits that one path, pushes it, and only then returns the TestSession. A commit or push that fails
    after the marker was written is BLOCKED.
  - evaluate.evaluate_model(split="test") calls require_test_session (no claim), then evaluate.require_gpu, then
    claim_checkpoint, then the scorers. require_test_session: the session was returned by begin_test_evaluation in
    this process; PILOT_BRANCH is checked out at the marker commit, so the committed marker and records are the
    ones begin checked and wrote (when begin returned, the marker commit was the remote branch's latest commit: begin
    fetched and compared before writing and checked the pushed ref after; the calls do not fetch again); the TEST
    rows are the files of the marker; the ST10 gate holds for them; the checkpoint is one of the marker's models not
    yet claimed in the session; the model's state sha256 (train.state_sha256, interpretation B25) is the marker's
    hash of that checkpoint.
  - finish_test_evaluation, once every model was claimed: the checkout still at the marker commit, the commit and
    push preconditions, then it commits and pushes results/test_evaluation_result.json; the session ends.
  - A marker without a result: the evaluation started and did not finish; it counts as evaluated; BLOCKED; report to
    the Owner. A result (with or without a marker): TEST was evaluated (TestAlreadyEvaluated).
Statuses of the refusals (C1 ruling 4): caused by the environment (the checkout, the fetch, staged changes, the commit
and push preconditions, a commit or push that fails) BLOCKED; a missing or unbound record, a model whose state hash is
not the marker's, a second TEST generation, a failing git command that reads the repository ImplementationFail;
TestAlreadyEvaluated carries no section 9 status. URLs are written and reported without user information
(credentials). Python cannot stop other code from writing these files or building these objects; the checks hold for
the package's own paths.
"""
import json
import re
import secrets
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import data as D
from . import frozen as FZ
from . import leakage as LK
from . import record as R
from . import stops as STP
from .errors import ImplementationFail, ProtocolStop

ST10_RECORD_REL = R.FORMAL_RESULTS_REL + "/st10_record.json"
AUDITOR_L6_REL = FZ.PILOT_REL + "/audit/st10_l6_test_count.json"
MARKER_REL = R.FORMAL_RESULTS_REL + "/test_evaluation_marker.json"
RESULT_REL = R.FORMAL_RESULTS_REL + "/test_evaluation_result.json"
CODE_PATHS = (FZ.PILOT_REL + "/src", FZ.PILOT_REL + "/run_pilot.py")
BASE_MODEL = "N"
HEX40 = re.compile(r"[0-9a-f]{40}")
CANONICAL_REPO = "leotree2020/OpenMythos"            # protocol section 0, base repository
PILOT_REMOTE = "origin"                                # the clone's remote that points at it (RUNBOOK_A100.md)
PILOT_BRANCH = "metrix-e1-pilot-protocol-v1"           # metrix/CLAUDE.md section 2
_USERINFO = re.compile(r"([A-Za-z][A-Za-z0-9+.-]*://)[^/@\s]*@")


class TestAlreadyEvaluated(Exception):
    """TEST was evaluated (marker and result exist): any further TEST evaluation is refused. Carries no section 9
    status: the pilot's status is the one of its result."""
    __test__ = False        # not a pytest test class


def _git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=False)


def _refuse(message):
    return ImplementationFail("TEST path refused: %s" % message)


def scrub(text):
    """`text` without the user information of any URL in it (https://user:token@host/... -> https://host/...)."""
    return _USERINFO.sub(r"\1", text)


def _blocked(message):
    return ProtocolStop(None, "BLOCKED", scrub("TEST path refused: %s; report to the Owner" % message))


def _count(v):
    return type(v) is int and v >= 0


def _counts_ok(counts):
    """One non-negative integer (not a bool, not a float) per check of the TEST part."""
    return (isinstance(counts, dict) and sorted(counts) == sorted(LK.TEST_CHECKS)
            and all(_count(v) for v in counts.values()))


def _is_ancestor(root, commit):
    """`commit` is a full 40-hex commit id that is an ancestor of (or equal to) HEAD."""
    return (isinstance(commit, str) and HEX40.fullmatch(commit) is not None
            and _git(root, "merge-base", "--is-ancestor", commit, "HEAD").returncode == 0)


def auth_fields(authorization):
    return {"gate0_record_sha256": authorization.gate0_record_sha256,
            "selection_record_sha256": authorization.selection_record_sha256}


def rows_sha256(rows):
    """SHA-256 of the canonical JSONL bytes of parsed rows: equal to the file-byte hash of a TEST file written by
    test_data (FZ.jsonl_bytes) and read back (FZ.read_jsonl)."""
    return FZ.sha256_hex(FZ.jsonl_bytes(rows))


def rows_hashes_of(data):
    """{TEST file name: rows_sha256} of the TEST rows in `data` (parsed files, as evaluate.evaluate_model gets them)."""
    missing = [n for n in D.TEST_FILES if n not in data]
    if missing:
        raise _refuse("no rows for %s" % missing)
    return {n: rows_sha256(data[n]) for n in D.TEST_FILES}


def test_limits(fz):
    """The frozen limits of the TEST part's checks (SPLIT_MANIFEST.json leakage_checks)."""
    limits = LK._rules(fz.split_manifest)["limits"]
    return {c: limits[c] for c in LK.TEST_CHECKS}


def over_limit(fz, counts):
    """Checks of the TEST part whose raw count is above its frozen limit."""
    limits = test_limits(fz)
    return sorted(c for c in LK.TEST_CHECKS if counts[c] > limits[c])


# ------------------------------------------------------------------------------------------------- git helpers

def remote_url(root, remote):
    """The fetch URL of `remote` (a remote name) without user information."""
    r = _git(root, "remote", "get-url", remote)
    return scrub(r.stdout.strip() if r.returncode == 0 else remote)


def repo_id(url):
    """'<owner>/<name>' of a repository URL or path: its last two path components, '.git' removed."""
    name = "/".join([x for x in re.split(r"[/:]", scrub(url).rstrip("/")) if x][-2:])
    return name[:-4] if name.endswith(".git") else name


def check_checkout(repo_root):
    """C1 ruling 1 (see the module docstring): BLOCKED unless PILOT_REMOTE is the pilot's repository, PILOT_BRANCH is
    checked out, the clone is not shallow, and HEAD is the latest commit of PILOT_BRANCH on the remote, fetched now
    (no tags; FETCH_HEAD and the remote-tracking ref are written). Returns that commit."""
    root = Path(repo_root)
    got = repo_id(remote_url(root, PILOT_REMOTE))
    if got != CANONICAL_REPO:
        raise _blocked("remote %s is repository %r, not the pilot's %r" % (PILOT_REMOTE, got, CANONICAL_REPO))
    local = _git(root, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    if local != PILOT_BRANCH:
        raise _blocked("the checked-out branch %r is not the pilot's %r" % (local, PILOT_BRANCH))
    if _git(root, "rev-parse", "--is-shallow-repository").stdout.strip() == "true":
        raise _blocked("the clone is shallow")
    f = _git(root, "fetch", "-q", "--no-tags", PILOT_REMOTE, "refs/heads/%s" % PILOT_BRANCH)
    if f.returncode != 0:
        raise _blocked("cannot fetch %s %s: %s" % (PILOT_REMOTE, PILOT_BRANCH, f.stderr.strip()))
    tip = _git(root, "rev-parse", "--verify", "-q", "FETCH_HEAD^{commit}").stdout.strip()
    head = _git(root, "rev-parse", "--verify", "-q", "HEAD^{commit}").stdout.strip()
    if not HEX40.fullmatch(tip) or head != tip:
        raise _blocked("HEAD %s is not the latest commit %r of %s %s: bring the checkout to it (fast-forward pull, "
                       "or push the local commits) first" % (head, tip, PILOT_REMOTE, PILOT_BRANCH))
    return tip


def _where(root, rel, tip):
    """Where `rel` exists (C1 ruling 1): the working tree, the file tree of `tip`."""
    found = ["working tree"] if (Path(root) / rel).exists() else []
    if _git(root, "cat-file", "-e", "%s:%s" % (tip, rel)).returncode == 0:
        found.append("commit %s" % tip)
    return found


def check_commit_preconditions(repo_root, what):
    """C1 ruling 2: before a record (`what`: the ST10 record, the TEST marker, the TEST result) is written, the
    pilot's checkout (check_checkout), nothing staged, a committer identity and `git push --dry-run` accepted. Any
    failure is BLOCKED and nothing is written."""
    root = Path(repo_root)
    check_checkout(root)
    if _git(root, "diff", "--cached", "--quiet").returncode != 0:
        raise _blocked("the git index holds staged changes; the commit of %s holds that path only" % what)
    if _git(root, "var", "GIT_COMMITTER_IDENT").returncode != 0:
        raise _blocked("no git committer identity (user.name, user.email)")
    dry = _git(root, "push", "--dry-run", "--no-follow-tags", PILOT_REMOTE, "HEAD:refs/heads/%s" % PILOT_BRANCH)
    if dry.returncode != 0:
        raise _blocked("a dry-run push to %s %s fails: %s" % (PILOT_REMOTE, PILOT_BRANCH, dry.stderr.strip()))


def _push(root, retries, sleep, what):
    """Push HEAD to PILOT_REMOTE PILOT_BRANCH (a plain push: fast-forward only; --no-follow-tags) and check the remote
    ref; retried `retries` times with 2, 4, 8, ... s pauses. BLOCKED when the remote ref is not HEAD at the end."""
    head = _git(root, "rev-parse", "HEAD").stdout.strip()
    last = ""
    for i in range(retries):
        r = _git(root, "push", "--no-follow-tags", PILOT_REMOTE, "HEAD:refs/heads/%s" % PILOT_BRANCH)
        ls = _git(root, "ls-remote", PILOT_REMOTE, "refs/heads/%s" % PILOT_BRANCH)
        if r.returncode == 0 and ls.returncode == 0 and ls.stdout.split()[:1] == [head]:
            return head
        last = (r.stderr + ls.stderr).strip()
        if i + 1 < retries:
            sleep(2 ** (i + 1))
    raise ProtocolStop(None, "BLOCKED", scrub("%s is committed (%s) but was not pushed to %s %s (%s); report to the "
                                              "Owner" % (what, head, PILOT_REMOTE, PILOT_BRANCH, last)))


def commit_paths(repo_root, rels, message, what, retries=4, sleep=time.sleep):
    """Commit exactly the repository paths `rels` and push them (the caller checked check_commit_preconditions before
    it wrote them): refused (BLOCKED) when anything is staged before; `git add --` of those paths only; the staged
    paths must be exactly them; commit; push and remote-ref check (_push). A staging, commit or push failure is
    BLOCKED (report to the Owner). Returns the commit."""
    root = Path(repo_root)
    if _git(root, "diff", "--cached", "--quiet").returncode != 0:
        raise _blocked("the git index holds staged changes; the commit of %s holds its own paths only" % what)
    add = _git(root, "add", "--", *rels)
    staged = sorted(_git(root, "diff", "--cached", "--name-only").stdout.split())
    if add.returncode != 0 or staged != sorted(rels):
        raise ProtocolStop(None, "BLOCKED", scrub("staging %s failed (%s; staged %s, expected %s); report to the "
                                                  "Owner" % (what, add.stderr.strip(), staged, sorted(rels))))
    c = _git(root, "commit", "-q", "-m", message)
    if c.returncode != 0:
        raise ProtocolStop(None, "BLOCKED", scrub("committing %s failed (%s); report to the Owner" % (
            what, (c.stdout + c.stderr).strip())))
    return _push(root, retries, sleep, what)


# ------------------------------------------------------------------------------------------------- ST10 record

def code_commit(repo_root):
    """HEAD of the repository; refused while the code (CODE_PATHS) has uncommitted or untracked changes, so that the
    commit names the code that ran."""
    st = _git(repo_root, "status", "--porcelain", "--untracked-files=all", "--", *CODE_PATHS)
    head = _git(repo_root, "rev-parse", "--verify", "HEAD^{commit}")
    if st.returncode != 0 or head.returncode != 0:
        raise ImplementationFail("cannot read the git state of %s: %s%s" % (repo_root, st.stderr, head.stderr))
    if st.stdout.strip():
        raise ImplementationFail("uncommitted changes in the code (%s):\n%s" % (", ".join(CODE_PATHS), st.stdout))
    return head.stdout.strip()


def refuse_if_st10_record(repo_root):
    """TEST is generated once: refused when an ST10 record exists (the working tree, the file tree of the remote
    branch's latest commit; check_checkout first). The TEST driver calls this before it generates anything."""
    root = Path(repo_root)
    where = _where(root, ST10_RECORD_REL, check_checkout(root))
    if where:
        raise ImplementationFail("%s exists (%s): TEST is generated once" % (ST10_RECORD_REL, ", ".join(where)))


def st10_record(fz, authorization, report, test_files, repo_root=None):
    """The ST10 record (Review Gate supplementary ruling 3): the raw counts of the TEST part (`report` from
    leakage.run_test_part: only checks[c]["value"] is read), the sha256 of the two TEST files (`test_files`:
    {name: bytes as written}), the code commit, bound to the authorization."""
    if sorted(report["checks"]) != sorted(LK.TEST_CHECKS):
        raise ImplementationFail("TEST part checks %s, expected %s" % (sorted(report["checks"]),
                                                                        sorted(LK.TEST_CHECKS)))
    counts = {c: report["checks"][c]["value"] for c in LK.TEST_CHECKS}
    bad = [c for c, v in counts.items() if not _count(v)]
    if bad:
        raise ImplementationFail("TEST part counts are not non-negative integers: %s" % {c: counts[c] for c in bad})
    if sorted(test_files) != sorted(D.TEST_FILES):
        raise ImplementationFail("TEST files %s, expected %s" % (sorted(test_files), sorted(D.TEST_FILES)))
    root = Path(repo_root) if repo_root is not None else fz.repo_root
    return {"kind": "st10", "mode": "formal", "label": None, "frozen_commit": authorization.frozen_commit,
            "authorization": auth_fields(authorization),
            "test_files_sha256": {n: FZ.sha256_hex(test_files[n]) for n in D.TEST_FILES},
            "code_commit": code_commit(root), "counts": counts}


def write_st10_record(fz, authorization, report, test_files, repo_root=None):
    """Write the ST10 record to ST10_RECORD_REL (refused if one exists: TEST is generated once). The caller commits it;
    st10_check reads only the committed version."""
    root = Path(repo_root) if repo_root is not None else fz.repo_root
    rec = st10_record(fz, authorization, report, test_files, root)
    path = root / ST10_RECORD_REL
    if path.exists():
        raise ImplementationFail("%s exists; TEST is generated once" % ST10_RECORD_REL)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rec, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return path, rec


def auditor_count_record(fz, general_test_sha256, l6_test_count):
    """The layout of the data-auditor's file AUDITOR_L6_REL (written by the data-auditor; given here for the RUNBOOK
    and the tests)."""
    return {"kind": "st10_auditor_l6", "frozen_commit": fz.record.commit, "general_test_sha256": general_test_sha256,
            "l6_test_count": l6_test_count}


def _committed(root, rel, what):
    """(object, sha256) of a committed JSON object (record.committed_json: a list or a scalar is NotCommitted)."""
    try:
        return R.committed_json(root, rel)
    except R.NotCommitted as e:
        raise _refuse("%s: %s" % (what, e)) from e


def st10_check(fz, authorization, rows_hashes, repo_root=None):
    """The ST10 gate from the committed records (see the module docstring). `rows_hashes`: {TEST file name: sha256}
    of the TEST rows about to be evaluated. Returns (sha256 of the ST10 record, sha256 of the data-auditor's file).
    Raises ImplementationFail (refused) or stops.Stop ST10 (BLOCKED)."""
    root = Path(repo_root) if repo_root is not None else fz.repo_root
    rec, rec_sha = _committed(root, ST10_RECORD_REL, "ST10 record")
    if rec.get("kind") != "st10" or rec.get("mode") != "formal" or rec.get("label") is not None:
        raise _refuse("%s is not a formal-mode ST10 record (kind %r, mode %r, label %r)" % (
            ST10_RECORD_REL, rec.get("kind"), rec.get("mode"), rec.get("label")))
    if rec.get("frozen_commit") != authorization.frozen_commit:
        raise _refuse("ST10 record for frozen commit %r, authorization %s" % (rec.get("frozen_commit"),
                                                                             authorization.frozen_commit))
    if rec.get("authorization") != auth_fields(authorization):
        raise _refuse("ST10 record is not bound to this authorization (%r, authorization %r)" % (
            rec.get("authorization"), auth_fields(authorization)))
    files = rec.get("test_files_sha256")
    if files != rows_hashes:
        raise _refuse("TEST files of the ST10 record %r differ from the TEST rows given %r" % (files, rows_hashes))
    cc = rec.get("code_commit")
    if not _is_ancestor(root, cc):
        raise _refuse("code commit %r of the ST10 record is not an ancestor of HEAD" % (cc,))
    counts = rec.get("counts")
    if not _counts_ok(counts):
        raise _refuse("ST10 record counts %r are not one non-negative integer per check %s" % (
            counts, list(LK.TEST_CHECKS)))
    aud, aud_sha = _committed(root, AUDITOR_L6_REL, "data-auditor's L6 TEST count")
    if aud.get("kind") != "st10_auditor_l6" or aud.get("frozen_commit") != authorization.frozen_commit:
        raise _refuse("%s is not the data-auditor's L6 TEST count for frozen commit %s (kind %r, frozen commit %r)" % (
            AUDITOR_L6_REL, authorization.frozen_commit, aud.get("kind"), aud.get("frozen_commit")))
    if aud.get("general_test_sha256") != files["general_test.jsonl"]:
        raise _refuse("the data-auditor counted general_test.jsonl %r, the ST10 record names %s" % (
            aud.get("general_test_sha256"), files["general_test.jsonl"]))
    if not _count(aud.get("l6_test_count")):
        raise _refuse("the data-auditor's l6_test_count %r is not a non-negative integer" % (aud.get("l6_test_count"),))
    STP.st10(fz, counts, test_limits(fz), aud["l6_test_count"])
    return rec_sha, aud_sha


# ------------------------------------------------------------------------------------------------ TEST once

def refuse_if_marker(repo_root):
    """Returns when neither a marker nor a result exists (the working tree, the file tree of the remote branch's
    latest commit; check_checkout first). Else raises: a result -> TestAlreadyEvaluated; a marker without a result ->
    the evaluation started and did not finish: it counts as evaluated, BLOCKED (Review Gate supplementary ruling 4)."""
    root = Path(repo_root)
    tip = check_checkout(root)
    where, result = _where(root, MARKER_REL, tip), _where(root, RESULT_REL, tip)
    if result:
        raise TestAlreadyEvaluated("TEST was already evaluated (marker %s in %s; result %s in %s): TEST is evaluated "
                                   "once" % (MARKER_REL, ", ".join(where) or "nowhere", RESULT_REL, ", ".join(result)))
    if not where:
        return
    raise ProtocolStop(None, "BLOCKED", "TEST evaluation was already started (marker %s in %s) and no result was "
                       "committed: it counts as evaluated; no further TEST evaluation; report to the Owner" % (
                           MARKER_REL, ", ".join(where)))


def evaluated_models(contract, selected):
    """The models TEST evaluates: N and the final checkpoints of the trained arms with every training seed (F, L, A
    with their selected configuration, the search seed's run included; S and Y)."""
    from .train import training_plan
    plan = training_plan(contract, selected)
    searched = ("F", "L", "A")
    names = [s.name for s in plan if s.arm in contract.arms.inheriting
             or (s.arm in searched and s.config_id == selected[s.arm])]
    want = len(contract.training.training_seeds) * (len(searched) + len(contract.arms.inheriting))
    if len(names) != want:
        raise ImplementationFail("%d trained models for TEST, expected %d" % (len(names), want))
    return [BASE_MODEL] + names


@dataclass
class TestSession:
    __test__ = False        # not a pytest test class
    session_id: str
    marker_commit: str
    evaluated: set = field(default_factory=set)


_LIVE = {}                  # session_id -> TestSession, only those returned by begin_test_evaluation in this process


def begin_test_evaluation(fz, authorization, data, base_model_sha256, repo_root=None, retries=4, sleep=time.sleep):
    """Start the single TEST evaluation (Review Gate supplementary ruling 4): checks (no marker or result:
    refuse_if_marker; the authorization; the ST10 gate for the TEST rows in `data`; check_commit_preconditions),
    writes the marker with every checkpoint hash of the committed freeze record plus N (`base_model_sha256`,
    train.state_sha256 of the loaded base model), commits only the marker and pushes it. Returns the TestSession."""
    from . import contract as C
    root = Path(repo_root) if repo_root is not None else fz.repo_root
    refuse_if_marker(root)
    recs = LK.verify_authorization(authorization, fz, root)
    rows_hashes = rows_hashes_of(data)
    st10_sha, aud_sha = st10_check(fz, authorization, rows_hashes, root)
    if not isinstance(base_model_sha256, str) or not FZ.HEX64.fullmatch(base_model_sha256):
        raise _refuse("base model hash %r" % (base_model_sha256,))
    freeze = recs["selection_freeze"]
    checkpoints = dict(freeze["checkpoints"], **{BASE_MODEL: base_model_sha256})
    models = evaluated_models(C.load(fz), freeze["selected"])
    check_commit_preconditions(root, "the TEST marker")
    session_id = secrets.token_hex(16)
    marker = {"kind": "test_evaluation_marker", "mode": "formal", "frozen_commit": authorization.frozen_commit,
              "authorization": auth_fields(authorization), "remote": remote_url(root, PILOT_REMOTE),
              "branch": PILOT_BRANCH, "st10_record_sha256": st10_sha, "auditor_count_sha256": aud_sha,
              "test_files_sha256": rows_hashes, "checkpoints": checkpoints, "models": models,
              "code_commit": code_commit(root), "session_id": session_id,
              "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    path = root / MARKER_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    blob = (json.dumps(marker, ensure_ascii=False, indent=1, sort_keys=True) + "\n").encode("utf-8")
    path.write_bytes(blob)
    head = commit_paths(root, [MARKER_REL], "metrix: E1-PILOT TEST evaluation marker (section 8 step 8: TEST is "
                        "evaluated once; every checkpoint hash)",
                        "the TEST marker (TEST not evaluated; the marker refuses any later evaluation)", retries, sleep)
    session = TestSession(session_id, head)
    _LIVE[session_id] = session
    return session


def _check_session_checkout(root, session):
    """PILOT_BRANCH is checked out at the session's marker commit (no fetch: see the module docstring). So the
    committed marker, Gate 0, freeze and ST10 records are the ones begin_test_evaluation checked and wrote."""
    local = _git(root, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    head = _git(root, "rev-parse", "--verify", "-q", "HEAD^{commit}").stdout.strip()
    if local != PILOT_BRANCH or head != session.marker_commit:
        raise _blocked("the checkout is %r at %s, not the pilot's %r at the TEST marker commit %s" % (
            local, head, PILOT_BRANCH, session.marker_commit))


def require_test_session(fz, authorization, session, checkpoint_name, data, model, repo_root=None):
    """Called by evaluate.evaluate_model(split="test") after leakage.verify_authorization and before anything is
    evaluated (see the module docstring). Claims nothing (claim_checkpoint, after the GPU check). The model's state
    sha256 is computed last, after the cheaper checks."""
    from .train import state_sha256
    root = Path(repo_root) if repo_root is not None else fz.repo_root
    if not isinstance(session, TestSession) or _LIVE.get(session.session_id) is not session:
        raise _refuse("no TEST session of this process (begin_test_evaluation)")
    _check_session_checkout(root, session)
    marker, _ = _committed(root, MARKER_REL, "TEST marker")
    rows_hashes = rows_hashes_of(data)
    if marker.get("test_files_sha256") != rows_hashes:
        raise _refuse("the TEST rows %r are not the files of the marker %r" % (rows_hashes,
                                                                              marker.get("test_files_sha256")))
    st10_check(fz, authorization, rows_hashes, root)
    if checkpoint_name not in marker["models"]:
        raise _refuse("%r is not a model TEST evaluates (%s)" % (checkpoint_name, marker["models"]))
    if checkpoint_name in session.evaluated:
        raise _refuse("%s was already evaluated on TEST in this session" % checkpoint_name)
    got = state_sha256(model)
    if got != marker["checkpoints"][checkpoint_name]:
        raise _refuse("the model's state sha256 %s is not the marker's %s for %s" % (
            got, marker["checkpoints"][checkpoint_name], checkpoint_name))


def claim_checkpoint(session, checkpoint_name):
    """Right before the evaluation of `checkpoint_name` starts (after require_test_session and the GPU check): the
    checkpoint is evaluated at most once in the session."""
    if _LIVE.get(getattr(session, "session_id", None)) is not session:
        raise _refuse("no TEST session of this process (begin_test_evaluation)")
    if checkpoint_name in session.evaluated:
        raise _refuse("%s was already evaluated on TEST in this session" % checkpoint_name)
    session.evaluated.add(checkpoint_name)


def finish_test_evaluation(fz, session, result, repo_root=None, retries=4, sleep=time.sleep):
    """After every model of the marker was claimed (PILOT_BRANCH checked out at the marker commit) and the commit and
    push preconditions hold: write `result` (the TEST results, JSON values only) to RESULT_REL, commit only that path,
    push it; the session ends."""
    root = Path(repo_root) if repo_root is not None else fz.repo_root
    if _LIVE.get(getattr(session, "session_id", None)) is not session:
        raise _refuse("no TEST session of this process")
    _check_session_checkout(root, session)
    marker, _ = _committed(root, MARKER_REL, "TEST marker")
    left = [m for m in marker["models"] if m not in session.evaluated]
    if left:
        raise _refuse("models not evaluated on TEST: %s" % left)
    check_commit_preconditions(root, "the TEST result")
    path = root / RESULT_REL
    path.write_text(json.dumps(dict(result, session_id=session.session_id, marker_commit=session.marker_commit),
                               ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    head = commit_paths(root, [RESULT_REL], "metrix: E1-PILOT TEST evaluation result (section 8 step 8)",
                        "the TEST result", retries, sleep)
    del _LIVE[session.session_id]
    return head
