"""The two hard preconditions of TEST evaluation (testgate.py): ST10 from the committed records and "TEST is evaluated
once". Owner's stage-C message (tasks/IMPL_C_OWNER_MESSAGE.md): stage-B ruling item 7; Review Gate supplementary
rulings 3-5 of 2026-11-24.

Ruling 5: everything here runs on throw-away git repositories (with a bare repository as the remote) under tmp_path,
with synthetic TEST rows written by the tests themselves (SYNTHETIC_QA, SYNTHETIC_GENERAL). No real TEST row is
generated, read or counted: the TEST generator is never run with an authorization, eval_sets.jsonl is never opened,
and the TEST driver (test_data.main) runs with its generator and leakage functions replaced by stubs returning the
synthetic rows. No model weights: the models are random tiny Qwen3 models (conftest.tiny_model); formal-mode
evaluation on the CPU is refused by evaluate.require_gpu, which is where a call that passed every gate stops.
"""
import copy
import dataclasses
import json
import os
import re
import subprocess

import pytest

from conftest import PILOT, tiny_model
from metrix_e1 import evaluate as E
from metrix_e1 import frozen as FZ
from metrix_e1 import leakage as LK
from metrix_e1 import mode as M
from metrix_e1 import record as R
from metrix_e1 import stops as STP
from metrix_e1 import test_data as TD
from metrix_e1 import testgate as TG
from metrix_e1 import train as T
from metrix_e1.errors import ImplementationFail, ProtocolStop

SELECTED = {"F": "F3", "L": "L2", "A": "A5"}
SYNTHETIC_QA = [{"fact_id": "synthetic-%d" % i, "template_id": "SYNTHETIC_T%d" % i,
                 "question": "Synthetic question %d (not a TEST row)?" % i} for i in range(3)]
SYNTHETIC_GENERAL = [{"domain": "synthetic", "doc_id": "synthetic-%d" % i, "ids": [11 + i, 12, 13],
                      "text": "synthetic window %d" % i} for i in range(2)]
BRANCH = "main"


def git(root, *args, check=True):
    r = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=False)
    if check and r.returncode != 0:
        raise AssertionError("git %s: %s" % (args, r.stderr))
    return r.stdout.strip()


def write_json(root, rel, obj):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    blob = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    p.write_bytes(blob)
    return FZ.sha256_hex(blob)


def commit(root, msg="records", push=True):
    """Commit everything; on BRANCH also push it (the remote branch's latest commit stays HEAD)."""
    git(root, "add", "-A")
    git(root, "commit", "-q", "--allow-empty", "-m", msg)
    if push and git(root, "rev-parse", "--abbrev-ref", "HEAD") == BRANCH:
        git(root, "push", "-q", "origin", "HEAD:refs/heads/%s" % BRANCH)
    return git(root, "rev-parse", "HEAD")


class Env:
    """A repository holding PROTOCOL_FROZEN, committed Gate 0 and freeze records, a bare remote, synthetic TEST files
    outside the repository, and the frozen files `fz` re-rooted at the repository."""

    def __init__(self, fz, contract, tmp_path):
        self.contract = contract
        self.remote = tmp_path / "remote.git"
        git(tmp_path, "init", "-q", "--bare", "-b", BRANCH, str(self.remote))
        self.root = tmp_path / "repo"
        self.root.mkdir()
        git(self.root, "init", "-q", "-b", BRANCH)
        for k, v in (("user.name", "metrix-test"), ("user.email", "metrix-test@invalid"), ("commit.gpgsign", "false")):
            git(self.root, "config", k, v)
        git(self.root, "remote", "add", "origin", str(self.remote))
        pf = self.root / FZ.PROTOCOL_FROZEN_REL
        pf.parent.mkdir(parents=True)
        pf.write_bytes((PILOT / "PROTOCOL_FROZEN").read_bytes())
        self.fz = dataclasses.replace(fz, repo_root=self.root)
        self.base_model = tiny_model(0)
        self.f_model = tiny_model(1)
        self.base_sha = T.state_sha256(self.base_model)
        g0 = R.gate0_record(fz, M.FORMAL_MODE, {"gate0_status": "PASS"})
        self.g0_sha = write_json(self.root, R.GATE0_RECORD_REL, g0)
        self.ck = {s.name: "a" * 64 for s in T.training_plan(contract, SELECTED)}
        self.ck["F-F3-seed101"] = T.state_sha256(self.f_model)
        content = {k: fz.data_hash(k) for k in FZ.CONTENT_HASH_KEYS}
        sel = R.selection_freeze_record(fz, M.FORMAL_MODE, SELECTED, content, self.ck, self.g0_sha)
        self.sel_sha = write_json(self.root, R.SELECTION_FREEZE_REL, sel)
        self.code_commit = commit(self.root, "code and records")
        self.auth = LK.TestAuthorization(fz.record.commit, self.g0_sha, self.sel_sha)
        self.files = {"test_qa.jsonl": FZ.jsonl_bytes(SYNTHETIC_QA), "general_test.jsonl": FZ.jsonl_bytes(SYNTHETIC_GENERAL)}
        self.out = tmp_path / "test_out"                # outside the repository
        self.out.mkdir()
        for n, b in self.files.items():
            (self.out / n).write_bytes(b)
        self.data = {n: FZ.read_jsonl(self.out / n) for n in self.files}
        self.hashes = {n: FZ.sha256_hex(b) for n, b in self.files.items()}

    def report(self, **counts):
        return {"checks": {c: {"value": counts.get(c, 0)} for c in LK.TEST_CHECKS}}

    def st10(self, rec_change=None, aud_change=None, counts=None, auditor_l6=0, record=True, auditor=True):
        """Write and commit the ST10 record (through testgate.st10_record) and the data-auditor's count, each
        optionally changed by a function, then push."""
        if record:
            rec = TG.st10_record(self.fz, self.auth, self.report(**(counts or {})), self.files)
            if rec_change:
                rec_change(rec)
            write_json(self.root, TG.ST10_RECORD_REL, rec)
        if auditor:
            aud = TG.auditor_count_record(self.fz, self.hashes["general_test.jsonl"], auditor_l6)
            if aud_change:
                aud_change(aud)
            write_json(self.root, TG.AUDITOR_L6_REL, aud)
        return commit(self.root, "ST10 record and the data-auditor's count")

    def begin(self, **kw):
        return TG.begin_test_evaluation(self.fz, self.auth, self.data, kw.pop("base", self.base_sha),
                                        sleep=lambda s: None, **kw)


@pytest.fixture(autouse=True)
def no_pending_interpretation(monkeypatch):
    """The gates are tested independently of the current rulings (the refusal while an interpretation is pending is
    tested in test_test_data)."""
    from metrix_e1 import interpretations as INT
    monkeypatch.setattr(INT, "pending", lambda: [])


@pytest.fixture
def env(fz, contract, tmp_path, monkeypatch):
    """The throw-away bare repository stands for the pilot's remote repository and BRANCH for its branch (the
    remote is named origin, testgate.PILOT_REMOTE)."""
    e = Env(fz, contract, tmp_path)
    monkeypatch.setattr(TG, "CANONICAL_REPO", TG.repo_id(str(e.remote)))
    monkeypatch.setattr(TG, "PILOT_BRANCH", BRANCH)
    return e


def assert_started(msg):
    """The refusal of a marker without a result: BLOCKED, 'already started', found in a commit."""
    assert "already started" in msg and "commit " in msg and "counts as evaluated" in msg, msg


def no_identity(root, monkeypatch):
    """No committer identity: global and system configuration hidden, none in the repository, auto-detection off."""
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for k in ("GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL", "GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "EMAIL"):
        monkeypatch.delenv(k, raising=False)
    for k in ("user.name", "user.email"):
        git(root, "config", "--unset", k)
    git(root, "config", "user.useConfigOnly", "true")


def diverge(env, tmp_path):
    """Another clone pushes a commit to the remote branch: this clone is behind the remote's latest commit."""
    other = tmp_path / "diverging"
    git(tmp_path, "clone", "-q", str(env.remote), str(other))
    for k, v in (("user.name", "x"), ("user.email", "x@invalid"), ("commit.gpgsign", "false")):
        git(other, "config", k, v)
    return commit(other, "diverging")


def blocked(fn, *a, **k):
    with pytest.raises(ProtocolStop) as e:
        fn(*a, **k)
    assert e.value.status == "BLOCKED" and e.value.stop is None
    return str(e.value)


def refused(msg, fn, *a, **k):
    with pytest.raises(ImplementationFail) as e:
        fn(*a, **k)
    assert str(e.value).startswith("IMPLEMENTATION_FAIL: TEST path refused: ")
    assert re.search(msg, str(e.value)), str(e.value)
    return e.value


# ------------------------------------------------------------------------------------------------ ST10 record

def test_st10_record_holds_raw_counts_hashes_and_code_commit(env):
    path, rec = TG.write_st10_record(env.fz, env.auth, env.report(L4=2, L6=7), env.files)
    assert path == env.root / TG.ST10_RECORD_REL
    assert json.loads(path.read_text(encoding="utf-8")) == rec
    assert sorted(rec) == ["authorization", "code_commit", "counts", "frozen_commit", "kind", "label", "mode",
                           "test_files_sha256"]
    assert rec["counts"] == {"L3a": 0, "L3b": 0, "L4": 2, "L5": 0, "L6": 7}
    assert rec["test_files_sha256"] == env.hashes and rec["code_commit"] == env.code_commit
    assert rec["authorization"] == {"gate0_record_sha256": env.g0_sha, "selection_record_sha256": env.sel_sha}
    assert "within_limit" not in path.read_text(encoding="utf-8") and "result" not in rec
    with pytest.raises(ImplementationFail, match="exists; TEST is generated once"):
        TG.write_st10_record(env.fz, env.auth, env.report(), env.files)


def test_st10_record_refuses_uncommitted_code(env):
    (env.root / TG.CODE_PATHS[0]).mkdir(parents=True)
    (env.root / TG.CODE_PATHS[0] / "x.py").write_text("", encoding="utf-8")
    with pytest.raises(ImplementationFail, match="uncommitted changes in the code"):
        TG.st10_record(env.fz, env.auth, env.report(), env.files)


@pytest.mark.parametrize("bad", [{"L4": -1}, {"L4": True}, {"L4": 0.0}, {"L4": "0"}])
def test_st10_record_refuses_counts_that_are_not_integers(env, bad):
    with pytest.raises(ImplementationFail, match="not non-negative integers"):
        TG.st10_record(env.fz, env.auth, env.report(**bad), env.files)


def test_st10_check_control(env):
    env.st10()
    got = TG.st10_check(env.fz, env.auth, env.hashes)
    assert got == (FZ.sha256_hex((env.root / TG.ST10_RECORD_REL).read_bytes()),
                   FZ.sha256_hex((env.root / TG.AUDITOR_L6_REL).read_bytes()))


REFUSED = {
    "record_missing": (dict(record=False), "ST10 record: metrix/e1-pilot/results/st10_record.json is not committed at HEAD$"),
    "record_kind": (dict(rec_change=lambda r: r.update(kind="gate0")), "is not a formal-mode ST10 record"),
    "record_smoke": (dict(rec_change=lambda r: r.update(mode="smoke", label=M.SMOKE_LABEL)), "is not a formal-mode ST10"),
    "frozen_commit": (dict(rec_change=lambda r: r.update(frozen_commit="0" * 40)), "ST10 record for frozen commit '0{40}'"),
    "unbound": (dict(rec_change=lambda r: r["authorization"].update(gate0_record_sha256="c" * 64)),
                "ST10 record is not bound to this authorization"),
    "files": (dict(rec_change=lambda r: r["test_files_sha256"].update({"test_qa.jsonl": "d" * 64})),
              "TEST files of the ST10 record .* differ from the TEST rows given"),
    "code_commit": (dict(rec_change=lambda r: r.update(code_commit="f" * 40)), "code commit 'f{40}' .* not an ancestor of HEAD"),
    "count_flag": (dict(rec_change=lambda r: r["counts"].update(L4={"value": 0, "within_limit": True})),
                   "counts .* are not one non-negative integer per check"),
    "count_bool": (dict(rec_change=lambda r: r["counts"].update(L4=False)), "are not one non-negative integer per check"),
    "count_missing": (dict(rec_change=lambda r: r["counts"].pop("L5")), "are not one non-negative integer per check"),
    "auditor_missing": (dict(auditor=False), "data-auditor's L6 TEST count: metrix/e1-pilot/audit/st10_l6_test_count.json "
                                             "is not committed at HEAD$"),
    "auditor_kind": (dict(aud_change=lambda a: a.update(kind="st10")), "is not the data-auditor's L6 TEST count"),
    "auditor_frozen_commit": (dict(aud_change=lambda a: a.update(frozen_commit="0" * 40)),
                              "is not the data-auditor's L6 TEST count"),
    "auditor_other_file": (dict(aud_change=lambda a: a.update(general_test_sha256="e" * 64)),
                           "the data-auditor counted general_test.jsonl 'e{64}'"),
    "auditor_not_int": (dict(aud_change=lambda a: a.update(l6_test_count="0")), "l6_test_count '0' is not"),
}


@pytest.mark.parametrize("rel", [TG.ST10_RECORD_REL, TG.AUDITOR_L6_REL])
def test_st10_check_refuses_a_record_that_is_not_an_object(env, rel):
    """data-auditor C1 round 1, note (a): a committed JSON list is refused, not an AttributeError."""
    env.st10()
    (env.root / rel).write_text("[1, 2]", encoding="utf-8")
    commit(env.root)
    refused("%s is a JSON list, not an object$" % rel, TG.st10_check, env.fz, env.auth, env.hashes)


def test_st10_check_refuses_a_code_commit_off_the_history(env):
    """An existing commit on another branch (not an ancestor of HEAD) as the ST10 record's code commit."""
    git(env.root, "checkout", "-q", "-b", "elsewhere")
    off = commit(env.root, "off the pilot's history")
    git(env.root, "checkout", "-q", BRANCH)
    env.st10(rec_change=lambda r: r.update(code_commit=off))
    refused("code commit '%s' of the ST10 record is not an ancestor of HEAD" % off, TG.st10_check, env.fz, env.auth,
            env.hashes)


@pytest.mark.parametrize("case", sorted(REFUSED))
def test_st10_check_refuses(env, case):
    kw, msg = REFUSED[case]
    env.st10(**kw)
    refused(msg, TG.st10_check, env.fz, env.auth, env.hashes)


@pytest.mark.parametrize("rel", [TG.ST10_RECORD_REL, TG.AUDITOR_L6_REL])
def test_st10_check_reads_only_committed_files(env, rel):
    env.st10()
    p = env.root / rel
    p.write_bytes(p.read_bytes().replace(b'"L6": 0', b'"L6": 0 ').replace(b'"l6_test_count": 0', b'"l6_test_count": 0 '))
    refused("%s in the working tree differs from its committed version$" % rel, TG.st10_check, env.fz, env.auth,
            env.hashes)


@pytest.mark.parametrize("check", LK.TEST_CHECKS)
def test_st10_stops_on_a_count_over_its_frozen_limit(env, check):
    """The count is re-judged against the frozen limit; self-reported flags in the record are ignored."""
    limit = TG.test_limits(env.fz)[check]

    def lie(r):
        r.update(result="PASS", within_limit={c: True for c in LK.TEST_CHECKS})
    env.st10(counts={check: limit + 1}, rec_change=lie, auditor_l6=limit + 1 if check == "L6" else 0)
    with pytest.raises(STP.Stop) as e:
        TG.st10_check(env.fz, env.auth, env.hashes)
    assert e.value.stop == "ST10" and e.value.status == "BLOCKED" and "over limit ['%s']" % check in str(e.value)


def test_st10_stops_when_the_l6_counts_differ(env):
    env.st10(counts={"L6": 0}, auditor_l6=1)
    with pytest.raises(STP.Stop) as e:
        TG.st10_check(env.fz, env.auth, env.hashes)
    assert e.value.stop == "ST10" and "L6 TEST Executor 0, data-auditor 1" in str(e.value)


# ------------------------------------------------------------------------------------------------- TEST once

def test_begin_commits_and_pushes_the_marker_only(env):
    """Also: no tag reaches the remote although an annotated tag is reachable and push.followTags is set."""
    env.st10()
    git(env.root, "tag", "-a", "-m", "a tag", "a-local-tag")
    git(env.root, "config", "push.followTags", "true")
    before = git(env.root, "rev-parse", "HEAD")
    s = env.begin()
    head = git(env.root, "rev-parse", "HEAD")
    assert git(env.root, "rev-parse", "HEAD~1") == before and s.marker_commit == head
    assert git(env.root, "show", "--name-only", "--format=", "HEAD").split() == [TG.MARKER_REL]
    assert git(env.root, "ls-remote", "origin", "refs/heads/%s" % BRANCH).split()[0] == head
    assert git(env.root, "ls-remote", "--tags", "origin") == ""
    assert git(env.root, "status", "--porcelain") == ""
    marker = json.loads(git(env.root, "show", "HEAD:%s" % TG.MARKER_REL))
    assert marker["session_id"] == s.session_id and marker["checkpoints"] == dict(env.ck, N=env.base_sha)
    assert marker["remote"] == str(env.remote) and marker["branch"] == BRANCH
    models = marker["models"]
    assert len(marker["checkpoints"]) == 31 and models[0] == "N" and len(models) == 16 and sorted(models[1:]) == sorted(
        [n for n in env.ck if n.startswith(("F-F3-", "L-L2-", "A-A5-", "S-", "Y-"))])
    assert marker["test_files_sha256"] == env.hashes and marker["authorization"] == TG.auth_fields(env.auth)
    assert (marker["st10_record_sha256"], marker["auditor_count_sha256"]) == TG.st10_check(env.fz, env.auth, env.hashes)


def test_begin_twice_is_refused_as_already_started(env, tmp_path):
    env.st10()
    env.begin()
    msg = blocked(env.begin)
    assert "already started" in msg and "counts as evaluated" in msg and "Owner" in msg
    clone = tmp_path / "clone"                         # another machine: a fresh clone of the remote
    git(tmp_path, "clone", "-q", str(env.remote), str(clone))
    assert_started(blocked(TG.refuse_if_marker, clone))


def test_marker_in_the_working_tree_only_refuses(env):
    env.st10()
    (env.root / TG.MARKER_REL).write_text("{}", encoding="utf-8")
    head = git(env.root, "rev-parse", "HEAD")
    assert "marker %s in working tree)" % TG.MARKER_REL in blocked(env.begin)
    assert git(env.root, "rev-parse", "HEAD") == head


def test_a_marker_pushed_from_another_clone_refuses(env, tmp_path):
    """Another clone begins (its marker is the remote branch's latest commit): this clone is first BLOCKED as behind
    the remote; brought to the remote's latest commit, the marker in that commit's file tree refuses, also with the
    working-tree copy removed."""
    env.st10()
    other = tmp_path / "other"
    git(tmp_path, "clone", "-q", str(env.remote), str(other))
    write_json(other, TG.MARKER_REL, {"kind": "test_evaluation_marker"})
    for k, v in (("user.name", "x"), ("user.email", "x@invalid"), ("commit.gpgsign", "false")):
        git(other, "config", k, v)
    commit(other, "marker of another clone")
    assert "is not the latest commit" in blocked(env.begin)
    git(env.root, "merge", "-q", "--ff-only", "FETCH_HEAD")
    assert_started(blocked(env.begin))
    (env.root / TG.MARKER_REL).unlink()
    msg = blocked(env.begin)
    assert_started(msg)
    assert "working tree" not in msg
    assert not (env.root / TG.MARKER_REL).exists()


def test_a_result_without_a_marker_refuses(env):
    env.st10()
    write_json(env.root, TG.RESULT_REL, {"kind": "result"})
    commit(env.root)
    with pytest.raises(TG.TestAlreadyEvaluated, match="marker .* in nowhere; result .* in working tree, commit"):
        env.begin()


def test_marker_with_a_result_is_refused_as_evaluated(env):
    env.st10()
    write_json(env.root, TG.MARKER_REL, {"kind": "test_evaluation_marker"})
    write_json(env.root, TG.RESULT_REL, {"kind": "result"})
    commit(env.root)
    with pytest.raises(TG.TestAlreadyEvaluated, match="TEST was already evaluated .*TEST is evaluated once$"):
        env.begin()


def test_a_marker_deleted_in_a_later_commit_is_not_searched(env):
    """Review Gate's ruling on C1, item 1: only the working tree and the remote branch's latest commit are searched.
    A marker committed and deleted again in a later commit (an act outside the gates' scope) is not found."""
    env.st10()
    write_json(env.root, TG.MARKER_REL, {"kind": "test_evaluation_marker"})
    commit(env.root, "marker")
    git(env.root, "rm", "-q", TG.MARKER_REL)
    commit(env.root, "marker deleted")
    TG.refuse_if_marker(env.root)


def test_a_second_begin_in_the_same_clone_is_blocked(env, monkeypatch):
    """Round-1 code review of the C1 second submission, MAJOR 2: the same command started twice in one clone; the
    second passed refuse_if_marker before the first wrote its marker. Its commit (parent: the first marker commit) is
    pushed, then refused: BLOCKED, no second session; the first session is BLOCKED at its next call."""
    env.st10()
    s1 = env.begin()
    real = TG.refuse_if_marker
    monkeypatch.setattr(TG, "refuse_if_marker", lambda root: None)        # it looked before the first marker existed
    msg = blocked(env.begin)
    assert "does not hold this TEST marker alone (another TEST evaluation began at the same time)" in msg
    monkeypatch.setattr(TG, "refuse_if_marker", real)
    assert "at the TEST marker commit %s" % s1.marker_commit in blocked(evaluate, env, env.base_model, s1, "N")
    assert_started(blocked(TG.refuse_if_marker, env.root))


def test_a_commit_of_another_begin_between_commit_and_push_is_blocked(env, monkeypatch):
    """The other begin commits its marker after this one's commit and before its push: the pushed commit holds the
    other marker's bytes. BLOCKED, no session."""
    env.st10()
    real = TG._push

    def other_commits_first(root, retries, sleep, what):
        write_json(env.root, TG.MARKER_REL, {"kind": "test_evaluation_marker", "session_id": "other"})
        git(env.root, "add", "--", TG.MARKER_REL)
        git(env.root, "commit", "-q", "-m", "the other marker")
        return real(root, retries, sleep, what)
    monkeypatch.setattr(TG, "_push", other_commits_first)
    msg = blocked(env.begin)
    assert "does not hold this TEST marker alone" in msg
    assert git(env.root, "ls-remote", "origin", "refs/heads/%s" % BRANCH).split()[0] == git(env.root, "rev-parse",
                                                                                            "HEAD")


def test_a_marker_file_overwritten_before_the_commit_is_blocked(env, monkeypatch):
    """The other begin (same working tree) overwrites the marker file after this one wrote it and before it is staged:
    the pushed commit's parent holds no marker, but the commit holds the other marker's bytes. BLOCKED, no session."""
    env.st10()
    real = TG.commit_paths

    def overwritten_first(root, rels, message, what, retries=4, sleep=None):
        write_json(env.root, TG.MARKER_REL, {"kind": "test_evaluation_marker", "session_id": "other"})
        return real(root, rels, message, what, retries, sleep)
    monkeypatch.setattr(TG, "commit_paths", overwritten_first)
    head = git(env.root, "rev-parse", "HEAD")
    assert "does not hold this TEST marker alone" in blocked(env.begin)
    assert git(env.root, "rev-parse", "HEAD~1") == head                  # the parent holds no marker


# ------------------------------------------------------------------------------- the pilot's checkout (ruling 1)

def checkout_cases(env, tmp_path, case):
    """Bring the clone into one state that is not the pilot's checkout at the remote branch's latest commit."""
    if case == "other_branch":
        git(env.root, "checkout", "-q", "-b", "side")
        return "the checked-out branch 'side' is not the pilot's 'main'"
    if case == "detached":
        git(env.root, "checkout", "-q", "--detach")
        return "the checked-out branch 'HEAD' is not the pilot's 'main'"
    if case == "ahead":
        commit(env.root, "a local commit, not pushed", push=False)
        return "is not the latest commit"
    if case == "behind":
        diverge(env, tmp_path)
        return "is not the latest commit"
    if case == "other_repository":
        other = tmp_path / "other-repo.git"
        git(tmp_path, "init", "-q", "--bare", "-b", BRANCH, str(other))
        git(env.root, "remote", "set-url", "origin", str(other))
        return "remote origin is repository '[^']*/other-repo', not the pilot's"
    if case == "unreachable":
        git(env.root, "remote", "set-url", "origin", str(tmp_path / "gone" / tmp_path.name / "remote.git"))
        return "cannot fetch origin main"
    raise AssertionError(case)


CHECKOUT_CASES = ("other_branch", "detached", "ahead", "behind", "other_repository", "unreachable")
GATED = {"refuse_if_marker": lambda env: TG.refuse_if_marker(env.root),
         "refuse_if_st10_record": lambda env: TG.refuse_if_st10_record(env.root),
         "check_commit_preconditions": lambda env: TG.check_commit_preconditions(env.root, "x"),
         "begin": lambda env: env.begin()}


@pytest.mark.parametrize("case", CHECKOUT_CASES)
@pytest.mark.parametrize("fn", sorted(GATED))
def test_every_test_path_needs_the_pilots_checkout_at_the_remote_tip(env, tmp_path, case, fn):
    """Review Gate's ruling on C1, item 1: BLOCKED (nothing written) unless the pilot's branch is checked out and HEAD
    is the latest commit of the remote branch, fetched now."""
    env.st10()
    expect = checkout_cases(env, tmp_path, case)
    head = git(env.root, "rev-parse", "HEAD")
    assert re.search(expect, blocked(GATED[fn], env))
    assert git(env.root, "rev-parse", "HEAD") == head and not (env.root / TG.MARKER_REL).exists()


def test_a_shallow_clone_is_blocked(env, tmp_path):
    env.st10()
    shallow = tmp_path / "shallow"
    git(tmp_path, "clone", "-q", "--depth", "1", "file://%s" % env.remote, str(shallow))
    assert "the clone is shallow" in blocked(TG.refuse_if_marker, shallow)


def test_the_remote_repository_name(env):
    assert TG.repo_id("https://user:secret@github.com/leotree2020/OpenMythos.git") == "leotree2020/OpenMythos"
    assert TG.repo_id("git@github.com:leotree2020/OpenMythos.git") == "leotree2020/OpenMythos"
    assert TG.repo_id("http://proxy@127.0.0.1:9/git/leotree2020/OpenMythos") == "leotree2020/OpenMythos"


def test_credentials_in_the_remote_url_are_not_written(env):
    """A token in the clone's URL (https://user:token@host/...) is neither written into the marker nor reported."""
    env.st10()
    git(env.root, "remote", "set-url", "origin", "file://user:s3cr3t@%s" % env.remote)
    s = env.begin()
    blob = git(env.root, "show", "HEAD:%s" % TG.MARKER_REL)
    assert "s3cr3t" not in blob and json.loads(blob)["remote"] == "file://%s" % env.remote
    assert s.marker_commit == git(env.root, "rev-parse", "HEAD")
    assert "s3cr3t" not in TG.scrub("fatal: could not read from https://user:s3cr3t@host/x (and git://a:b@c/d)")
    hook = env.remote / "hooks" / "pre-receive"             # a push that fails: its message is reported scrubbed
    hook.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    hook.chmod(0o755)
    write_json(env.root, "metrix/e1-pilot/results/other.json", {"x": 1})
    msg = blocked(TG.commit_paths, env.root, ["metrix/e1-pilot/results/other.json"], "m", "the other record",
                  retries=1, sleep=lambda s: None)
    assert "the other record is committed" in msg and "was not pushed" in msg and "s3cr3t" not in msg


def test_a_remote_that_cannot_be_fetched_is_blocked(env, monkeypatch):
    env.st10()
    real = TG._git
    monkeypatch.setattr(TG, "_git", lambda root, *a: real(root, "fetch-does-not-exist") if a[:1] == ("fetch",)
                        else real(root, *a))
    assert "cannot fetch origin main" in blocked(env.begin)
    assert not (env.root / TG.MARKER_REL).exists()


def test_a_failing_dry_run_push_is_blocked_before_writing(env, tmp_path):
    """The push URL differs from the fetch URL and cannot be pushed to: the dry run fails, nothing is written."""
    env.st10()
    head = git(env.root, "rev-parse", "HEAD")
    git(env.root, "config", "remote.origin.pushurl", str(tmp_path / "no-such-remote.git"))
    assert "a dry-run push to origin main fails" in blocked(env.begin)
    assert git(env.root, "rev-parse", "HEAD") == head and not (env.root / TG.MARKER_REL).exists()


def test_begin_refuses_before_writing_anything(env):
    """Refusals of begin leave no marker and no commit: staged changes, ST10 over limit, a bad base-model hash, a
    missing data-auditor count, uncommitted code."""
    env.st10()
    head = git(env.root, "rev-parse", "HEAD")
    (env.root / "staged.txt").write_text("x", encoding="utf-8")
    git(env.root, "add", "staged.txt")
    assert "the git index holds staged changes; the commit of the TEST marker holds that path only" in blocked(
        env.begin)
    git(env.root, "reset", "-q")
    refused("base model hash 'x'", env.begin, base="x")
    assert git(env.root, "rev-parse", "HEAD") == head and not (env.root / TG.MARKER_REL).exists()
    (env.root / "staged.txt").unlink()
    env.st10(counts={"L4": 1})
    with pytest.raises(STP.Stop, match="ST10"):
        env.begin()
    env.st10(auditor=False)
    git(env.root, "rm", "-q", TG.AUDITOR_L6_REL)
    commit(env.root)
    refused("data-auditor's L6 TEST count", env.begin)
    env.st10()
    (env.root / TG.CODE_PATHS[0]).mkdir(parents=True)
    (env.root / TG.CODE_PATHS[0] / "x.py").write_text("", encoding="utf-8")
    with pytest.raises(ImplementationFail, match="uncommitted changes in the code"):
        env.begin()
    (env.root / TG.CODE_PATHS[0] / "x.py").unlink()
    assert not (env.root / TG.MARKER_REL).exists()
    assert not git(env.root, "log", "--all", "--format=%H", "--", TG.MARKER_REL)


def test_begin_refuses_without_a_committer_identity(env, monkeypatch):
    """No identity (no_identity): BLOCKED before anything is written."""
    env.st10()
    no_identity(env.root, monkeypatch)
    head = git(env.root, "rev-parse", "HEAD")
    assert "no git committer identity" in blocked(env.begin)
    assert git(env.root, "rev-parse", "HEAD") == head and not (env.root / TG.MARKER_REL).exists()


def test_a_push_that_fails_is_blocked_and_the_marker_refuses_later_runs(env):
    env.st10()
    hook = env.remote / "hooks" / "pre-receive"           # the remote refuses every push
    hook.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    hook.chmod(0o755)
    sleeps = []
    msg = blocked(TG.begin_test_evaluation, env.fz, env.auth, env.data, env.base_sha, retries=3, sleep=sleeps.append)
    assert "the TEST marker (TEST not evaluated" in msg and "is committed" in msg and "Owner" in msg
    assert sleeps == [2, 4]
    assert git(env.root, "show", "--name-only", "--format=", "HEAD").split() == [TG.MARKER_REL]
    hook.unlink()
    assert "is not the latest commit" in blocked(env.begin)      # the local marker commit is ahead of the remote
    git(env.root, "push", "-q", "origin", "HEAD:refs/heads/%s" % BRANCH)
    assert_started(blocked(env.begin))


def test_commit_paths_stages_exactly_the_named_paths(env):
    """A named path without a change stages nothing: BLOCKED at the staging check (not later at the commit)."""
    env.st10()
    head = git(env.root, "rev-parse", "HEAD")
    msg = blocked(TG.commit_paths, env.root, [TG.ST10_RECORD_REL], "m", "the unchanged record")
    assert "staging the unchanged record failed" in msg and "staged [], expected ['%s']" % TG.ST10_RECORD_REL in msg
    assert git(env.root, "rev-parse", "HEAD") == head
    (env.root / "staged.txt").write_text("x", encoding="utf-8")
    git(env.root, "add", "staged.txt")
    assert "the commit of the x holds its own paths only" in blocked(TG.commit_paths, env.root, ["staged.txt"], "m",
                                                                        "the x")


def test_a_failing_commit_is_blocked(env):
    """A commit that fails after the marker was written (here a pre-commit hook) is BLOCKED; the marker in the
    working tree then refuses any later run."""
    env.st10()
    hook = env.root / ".git" / "hooks" / "pre-commit"
    hook.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    hook.chmod(0o755)
    assert "committing the TEST marker (TEST not evaluated" in blocked(env.begin)
    hook.unlink()
    msg = blocked(env.begin)
    assert "already started (marker %s in working tree)" % TG.MARKER_REL in msg and "counts as evaluated" in msg


# ------------------------------------------------------------------------------- evaluate_model(split="test")

def evaluate(env, model, session, name, data=None, auth=None):
    return E.evaluate_model(model, None, data or env.data, None, env.contract.evaluation, M.FORMAL_MODE, "cpu",
                            split="test", test_authorization=auth or env.auth, fz=env.fz, test_session=session,
                            checkpoint_name=name)


GPU_REFUSAL = "^IMPLEMENTATION_FAIL: formal mode evaluates only on the GPU"


def test_evaluate_model_passes_every_gate_then_stops_at_the_gpu_check(env):
    """Control: with the session, the committed marker and ST10, the call reaches require_gpu (on this CPU host the
    formal evaluation itself is refused there) and nothing is claimed; each checkpoint is claimed once per session."""
    env.st10()
    s = env.begin()
    for name, model in (("N", env.base_model), ("F-F3-seed101", env.f_model)):
        with pytest.raises(ImplementationFail, match=GPU_REFUSAL):
            evaluate(env, model, s, name)
    assert s.evaluated == set()                        # refused by the GPU check: nothing claimed
    TG.claim_checkpoint(s, "N")
    refused("N was already evaluated on TEST in this session", TG.claim_checkpoint, s, "N")
    refused("N was already evaluated on TEST in this session", evaluate, env, env.base_model, s, "N")
    refused("no TEST session of this process", TG.claim_checkpoint, copy.copy(s), "F-F3-seed101")
    refused("no TEST session of this process", TG.claim_checkpoint, None, "N")        # data-auditor, MINOR-1
    assert s.evaluated == {"N"}


def test_evaluate_model_claims_after_the_gpu_check(env, monkeypatch):
    """The claim in evaluate_model's TEST path itself (round-2 code review): with the GPU check and the scorers
    replaced by stand-ins, a call that passes the gates claims its checkpoint before any scorer runs (DEFERRED_MINORS
    1.29 CC8); a second call is refused."""
    env.st10()
    s = env.begin()
    monkeypatch.setattr(E, "require_gpu", lambda mode, device: None)
    claimed = []

    def scorer(*a, **k):
        claimed.append("N" in s.evaluated)
        return []
    for name in ("score_qa", "score_cb", "general_nll", "em"):
        monkeypatch.setattr(E, name, scorer)
    data = dict(env.data, **{"facts.jsonl": [], "candidates.json": {}})
    out = evaluate(env, env.base_model, s, "N", data=data)
    assert sorted(out) == ["em_test", "general_test", "test_qa", "train_cb"] and s.evaluated == {"N"}
    assert claimed == [True] * 4
    refused("N was already evaluated on TEST in this session", evaluate, env, env.base_model, s, "N", data=data)


def test_evaluate_model_refusals(env):
    env.st10()
    s = env.begin()
    refused("no TEST session of this process", evaluate, env, env.base_model, None, "N")
    forged = copy.copy(s)                              # same id, not the session begin_test_evaluation returned
    refused("no TEST session of this process", evaluate, env, env.base_model, forged, "N")
    refused("'F-F1-seed101' is not a model TEST evaluates", evaluate, env, env.base_model, s, "F-F1-seed101")
    refused("the model's state sha256 .* is not the marker's .* for N", evaluate, env, env.f_model, s, "N")
    more = dict(env.data, **{"test_qa.jsonl": env.data["test_qa.jsonl"] + [dict(SYNTHETIC_QA[0], fact_id="extra")]})
    refused("are not the files of the marker", evaluate, env, env.base_model, s, "N", data=more)
    refused("committed metrix/e1-pilot/results/selection_freeze_record.json has sha256",
            evaluate, env, env.base_model, s, "N", auth=LK.TestAuthorization(env.auth.frozen_commit, env.g0_sha, "f" * 64))
    refused(r"no rows for \['general_test.jsonl'\]", evaluate, env, env.base_model, s, "N",
            data={"test_qa.jsonl": env.data["test_qa.jsonl"]})
    assert s.evaluated == set()                        # nothing was claimed by a refused call
    m = env.root / TG.MARKER_REL
    blob = m.read_bytes()
    m.write_bytes(blob + b" ")
    refused("TEST marker: .* differs from its committed version", evaluate, env, env.base_model, s, "N")
    m.write_bytes(blob)
    st10 = env.root / TG.ST10_RECORD_REL
    st10_blob = st10.read_bytes()
    st10.write_bytes(st10_blob + b" ")
    refused("ST10 record: .* differs from its committed version", evaluate, env, env.base_model, s, "N")
    st10.write_bytes(st10_blob)
    assert s.evaluated == set()


MOVED = {
    "a_commit_after_begin": lambda env: env.st10(rec_change=lambda r: r.update(extra="changed")),
    "the_marker_rewritten": lambda env: (write_json(env.root, TG.MARKER_REL, {"kind": "test_evaluation_marker"}),
                                         commit(env.root, "another marker", push=False)),
    "another_branch": lambda env: git(env.root, "checkout", "-q", "-b", "side"),
}


def test_evaluation_calls_do_not_fetch_finish_does(env, tmp_path, monkeypatch):
    """Executor's reading of ruling 1 for the evaluation calls (round-1 code review, MAJOR 1 and MINOR): the remote
    moves on after begin while this checkout stays at the marker commit; evaluation calls go on (no fetch), finish
    fetches and is BLOCKED (the TEST result is not written; it counts as evaluated)."""
    env.st10()
    s = env.begin()
    diverge(env, tmp_path)
    monkeypatch.setattr(E, "require_gpu", lambda mode, device: None)
    for name in ("score_qa", "score_cb", "general_nll", "em"):
        monkeypatch.setattr(E, name, lambda *a, **k: [])
    data = dict(env.data, **{"facts.jsonl": [], "candidates.json": {}})
    evaluate(env, env.base_model, s, "N", data=data)        # no fetch: the call goes on although the remote moved
    for name in json.loads(git(env.root, "show", "HEAD:%s" % TG.MARKER_REL))["models"][1:]:
        TG.claim_checkpoint(s, name)
    assert "N" in s.evaluated
    assert "is not the latest commit" in blocked(TG.finish_test_evaluation, env.fz, s, {"x": 1})
    assert not (env.root / TG.RESULT_REL).exists()


def test_s_mapping_on_test_is_refused_before_the_gate(env):
    """Round-1 code review, MINOR: with_s_mapping on TEST is refused before the TEST gate claims the checkpoint."""
    env.st10()
    s = env.begin()
    with pytest.raises(ValueError, match="S's own-mapping accuracy is reported on DEV only"):
        E.evaluate_model(env.base_model, None, env.data, None, env.contract.evaluation, M.FORMAL_MODE, "cpu",
                         split="test", with_s_mapping=True, test_authorization=env.auth, fz=env.fz, test_session=s,
                         checkpoint_name="N")
    assert s.evaluated == set()


@pytest.mark.parametrize("case", sorted(MOVED))
def test_evaluate_and_finish_are_blocked_when_the_checkout_left_the_marker_commit(env, case):
    """After begin, the checkout must stay PILOT_BRANCH at the marker commit (so the committed marker and records
    are the ones begin checked): a new commit (pushed or not) or another branch is BLOCKED; nothing is claimed or
    written."""
    env.st10()
    s = env.begin()
    MOVED[case](env)
    msg = blocked(evaluate, env, env.base_model, s, "N")
    assert "not the pilot's 'main' at the TEST marker commit %s" % s.marker_commit in msg
    for name in json.loads(git(env.root, "show", "%s:%s" % (s.marker_commit, TG.MARKER_REL)))["models"]:
        TG.claim_checkpoint(s, name)
    assert "at the TEST marker commit" in blocked(TG.finish_test_evaluation, env.fz, s, {"x": 1})
    assert not (env.root / TG.RESULT_REL).exists()


def test_finish_commits_the_result_after_every_model(env):
    env.st10()
    s = env.begin()
    refused("no TEST session of this process", TG.finish_test_evaluation, env.fz, None, {})   # data-auditor, MINOR-1
    refused("no TEST session of this process", TG.finish_test_evaluation, env.fz, copy.copy(s), {})
    refused("models not evaluated on TEST", TG.finish_test_evaluation, env.fz, s, {})
    marker = json.loads((env.root / TG.MARKER_REL).read_text(encoding="utf-8"))
    for name in marker["models"]:                      # claimed as evaluate_model does after the GPU check
        TG.claim_checkpoint(s, name)
    (env.root / "staged.txt").write_text("x", encoding="utf-8")
    git(env.root, "add", "staged.txt")
    assert "the commit of the TEST result holds that path only" in blocked(TG.finish_test_evaluation, env.fz, s, {})
    assert not (env.root / TG.RESULT_REL).exists()     # checked before the result is written
    git(env.root, "reset", "-q")
    (env.root / "staged.txt").unlink()
    with pytest.raises(TypeError):                     # JSON values only (no default=str)
        TG.finish_test_evaluation(env.fz, s, {"x": object()})
    assert not (env.root / TG.RESULT_REL).exists()
    head = TG.finish_test_evaluation(env.fz, s, {"final_status": "NOT_TESTED"}, sleep=lambda x: None)
    assert git(env.root, "show", "--name-only", "--format=", "HEAD").split() == [TG.RESULT_REL]
    assert git(env.root, "ls-remote", "origin", "refs/heads/%s" % BRANCH).split()[0] == head
    refused("no TEST session of this process", TG.require_test_session, env.fz, env.auth, s, "N", env.data,
            env.base_model)
    with pytest.raises(TG.TestAlreadyEvaluated):
        env.begin()


# ------------------------------------------------------------------------------ the step 8 TEST driver (main)

def test_driver_writes_the_st10_record_and_judges_raw_counts(env, monkeypatch, capsys, tmp_path):
    """test_data.main with its precondition, generation and leakage steps replaced by stubs (synthetic rows): it
    writes the ST10 record into the repository and judges the raw counts; the stub report claims every check within
    its limit and PASS, the counts say L4 is over it."""
    info = {"test_qa": SYNTHETIC_QA, "general_test": SYNTHETIC_GENERAL}
    lying = {"result": "PASS", "checks": {c: {"value": 1 if c == "L4" else 0, "limit": 0, "within_limit": True}
                                          for c in LK.TEST_CHECKS}}
    monkeypatch.setattr(TD, "check_preconditions", lambda *a: (env.fz, env.auth))
    monkeypatch.setattr(TD, "generate_test", lambda *a: (dict(env.files), info))
    monkeypatch.setattr(TD.LK, "load_data", lambda d: {})
    monkeypatch.setattr(TD.LK, "run_test_part", lambda *a: lying)
    lag = tmp_path / "lagging"                         # another machine's clone, made before TEST was generated
    git(tmp_path, "clone", "-q", str(env.remote), str(lag))
    with pytest.raises(ImplementationFail, match="is inside the repository"):
        TD.main(["--inputs", "unused", "--data", "unused", "--out", str(env.root / "inside")])
    assert not (env.root / "inside").exists() and not (env.root / TG.ST10_RECORD_REL).exists()
    out = tmp_path / "driver_out"
    with pytest.raises(SystemExit) as e:
        TD.main(["--inputs", "unused", "--data", "unused", "--out", str(out)])
    text = capsys.readouterr().out
    assert e.value.code == 1 and text.strip().split("\n")[-1] == "RESULT: FAIL"
    assert "L4   TEST part count 1 frozen limit 0 OVER LIMIT" in text and "BLOCKED" in text
    rec = json.loads((env.root / TG.ST10_RECORD_REL).read_text(encoding="utf-8"))
    assert rec["counts"] == {"L3a": 0, "L3b": 0, "L4": 1, "L5": 0, "L6": 0} and rec["test_files_sha256"] == env.hashes
    assert {n: (out / n).read_bytes() for n in env.files} == env.files
    head = git(env.root, "rev-parse", "HEAD")          # committed (that path only) and pushed by the driver
    assert git(env.root, "show", "--name-only", "--format=", "HEAD").split() == [TG.ST10_RECORD_REL]
    assert git(env.root, "ls-remote", "origin", "refs/heads/%s" % BRANCH).split()[0] == head
    generated = []                                     # a second run, other --out: refused before generating
    monkeypatch.setattr(TD, "generate_test", lambda *a: generated.append(1) or (dict(env.files), info))
    with pytest.raises(ImplementationFail, match="st10_record.json exists \\(working tree, commit [0-9a-f]{40}"):
        TD.main(["--inputs", "unused", "--data", "unused", "--out", str(tmp_path / "driver_out2")])
    assert "is not the latest commit" in blocked(TG.refuse_if_st10_record, lag)     # behind the remote ...
    git(lag, "merge", "-q", "--ff-only", "FETCH_HEAD")
    with pytest.raises(ImplementationFail, match="st10_record.json exists \\(working tree, commit %s\\)" % head):
        TG.refuse_if_st10_record(lag)                   # ... and at the remote's latest commit: found
    assert generated == [] and not (tmp_path / "driver_out2").exists()
    (env.root / TG.CODE_PATHS[0]).mkdir(parents=True)
    (env.root / TG.CODE_PATHS[0] / "x.py").write_text("", encoding="utf-8")
    with pytest.raises(ImplementationFail, match="uncommitted changes in the code"):
        TD.main(["--inputs", "unused", "--data", "unused", "--out", str(tmp_path / "driver_out4")])
    assert generated == [] and not (tmp_path / "driver_out4").exists()
    monkeypatch.setattr(TG, "PILOT_BRANCH", "another-branch")
    (env.root / TG.CODE_PATHS[0] / "x.py").unlink()
    assert "the checked-out branch 'main' is not the pilot's 'another-branch'" in blocked(
        TD.main, ["--inputs", "unused", "--data", "unused", "--out", str(tmp_path / "driver_out5")])
    assert generated == [] and not (tmp_path / "driver_out5").exists()


def stub_driver(env, monkeypatch, generated):
    """test_data.main with its precondition, generation and leakage steps replaced by stubs (synthetic rows)."""
    info = {"test_qa": SYNTHETIC_QA, "general_test": SYNTHETIC_GENERAL}
    monkeypatch.setattr(TD, "check_preconditions", lambda *a: (env.fz, env.auth))
    monkeypatch.setattr(TD, "generate_test", lambda *a: generated.append(1) or (dict(env.files), info))
    monkeypatch.setattr(TD.LK, "load_data", lambda d: {})
    monkeypatch.setattr(TD.LK, "run_test_part", lambda *a: env.report())


def run_driver(tmp_path, out):
    return TD.main(["--inputs", "unused", "--data", "unused", "--out", str(tmp_path / out)])


def test_driver_checks_the_commit_preconditions_before_generating(env, monkeypatch, tmp_path):
    """Review Gate's ruling on C1, item 2: staged changes, a push URL that cannot be pushed to, no committer identity,
    a clone behind the remote: BLOCKED before TEST is generated; no --out, no ST10 record, no commit."""
    generated = []
    stub_driver(env, monkeypatch, generated)
    head = git(env.root, "rev-parse", "HEAD")

    def refused_before_generating(expect, out):
        assert expect in blocked(run_driver, tmp_path, out)
        assert generated == [] and not (tmp_path / out).exists() and not (env.root / TG.ST10_RECORD_REL).exists()
        assert git(env.root, "rev-parse", "HEAD") == head

    (env.root / "staged.txt").write_text("x", encoding="utf-8")
    git(env.root, "add", "staged.txt")
    refused_before_generating("the git index holds staged changes; the commit of the ST10 record holds that path "
                              "only", "o1")
    git(env.root, "reset", "-q")
    (env.root / "staged.txt").unlink()
    git(env.root, "config", "remote.origin.pushurl", str(tmp_path / "no-such-remote.git"))
    refused_before_generating("a dry-run push to origin main fails", "o2")
    git(env.root, "config", "--unset", "remote.origin.pushurl")
    no_identity(env.root, monkeypatch)
    refused_before_generating("no git committer identity", "o3")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "x")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "x@invalid")
    diverge(env, tmp_path)
    refused_before_generating("is not the latest commit", "o4")


def test_driver_push_refused_after_generation_counts_as_generated(env, monkeypatch, tmp_path):
    """Review Gate's ruling on C1, item 2: the remote refuses the real push of the ST10 record (a dry run passes):
    BLOCKED, TEST counts as generated, the Owner decides about the one file; a second run is refused before
    generating (the local record commit is ahead of the remote)."""
    generated = []
    stub_driver(env, monkeypatch, generated)
    hook = env.remote / "hooks" / "pre-receive"
    hook.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    hook.chmod(0o755)
    monkeypatch.setattr(TG.time, "sleep", lambda s: None)                 # commit_paths reads time.sleep when called
    msg = blocked(run_driver, tmp_path, "o1")
    assert "the ST10 record (TEST counts as generated: no second generation; the Owner decides" in msg
    assert "is committed" in msg and "was not pushed" in msg and generated == [1]
    assert git(env.root, "show", "--name-only", "--format=", "HEAD").split() == [TG.ST10_RECORD_REL]
    hook.unlink()
    assert "is not the latest commit" in blocked(run_driver, tmp_path, "o2")
    assert generated == [1] and not (tmp_path / "o2").exists()
