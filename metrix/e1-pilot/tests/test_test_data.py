"""Implementation Task Order V1, section 6 item 9: in the current state (no Gate 0 PASS record) the TEST generator
refuses to run: RESULT: FAIL, non-zero exit, no file produced. No test here generates, reads or counts TEST: every
run of the generator fails a precondition before generation, and the TEST split of eval_sets.jsonl is never parsed
(spied below). Conditions 2 and 3 are also tested one at a time (check_gate0_record, check_selection_record) with a
correct record as positive control, on throw-away git repositories under tmp_path; those calls never reach
generation (generate_test is never called with an authorization)."""
import json
import os
import subprocess
import sys

import pytest

from conftest import PILOT, SRC
from metrix_e1 import data as D
from metrix_e1 import leakage as LK
from metrix_e1 import record as R
from metrix_e1 import test_data as TD
from metrix_e1 import train as T
from metrix_e1.errors import ImplementationFail

GIT_ID = ["-c", "user.name=metrix-test", "-c", "user.email=metrix-test@invalid", "-c", "commit.gpgsign=false"]


def _tree(path):
    return sorted(str(p.relative_to(path)) for p in path.rglob("*"))


def _git_status(root):
    return subprocess.run(["git", "-C", str(root), "status", "--porcelain", "--untracked-files=all"],
                          capture_output=True, text=True, check=True).stdout


def test_refuses_in_the_current_state(fz, inputs_dir, generated, tmp_path):
    out = tmp_path / "test_out"
    data_before = {p.name: p.read_bytes() for p in generated["dir"].iterdir()}
    tmp_before = _tree(tmp_path)
    git_before = _git_status(fz.repo_root)
    env = dict(os.environ, PYTHONPATH=str(SRC))
    r = subprocess.run([sys.executable, "-m", "metrix_e1.test_data", "--inputs", str(inputs_dir), "--data",
                        str(generated["dir"]), "--out", str(out)], capture_output=True, text=True, env=env, cwd=str(tmp_path))
    lines = r.stdout.strip().split("\n")
    assert r.returncode != 0
    assert lines[-1] == "RESULT: FAIL"
    assert "gate0_record.json is not committed at HEAD" in r.stdout          # condition 2 is the one that fails
    assert not out.exists()
    assert _tree(tmp_path) == tmp_before
    assert {p.name: p.read_bytes() for p in generated["dir"].iterdir()} == data_before
    assert not any((generated["dir"] / n).exists() for n in D.TEST_FILES)
    assert _git_status(fz.repo_root) == git_before
    assert not (fz.repo_root / R.FORMAL_RESULTS_REL).exists()


def test_refusal_never_parses_test_rows(fz, inputs_dir, generated, tmp_path, monkeypatch, capsys):
    splits = []
    real = D.build_general_dev

    def spy(p, *a, **k):
        splits.append(p.general_dev_split)
        return real(p, *a, **k)
    monkeypatch.setattr(D, "build_general_dev", spy)
    with pytest.raises(SystemExit) as e:
        TD.main(["--inputs", str(inputs_dir), "--data", str(generated["dir"]), "--out", str(tmp_path / "o")])
    assert e.value.code == 1
    assert capsys.readouterr().out.strip().split("\n")[-1] == "RESULT: FAIL"
    assert splits and set(splits) == {"dev"}                 # condition 1 regenerates DEV data only
    assert not (tmp_path / "o").exists()


def test_refuses_without_data(fz, inputs_dir, tmp_path, capsys):
    (tmp_path / "empty").mkdir()
    with pytest.raises(SystemExit) as e:
        TD.main(["--inputs", str(inputs_dir), "--data", str(tmp_path / "empty"), "--out", str(tmp_path / "o")])
    assert e.value.code == 1
    out = capsys.readouterr().out
    assert "ST12" in out and out.strip().split("\n")[-1] == "RESULT: FAIL"
    assert not (tmp_path / "o").exists()


def test_generation_needs_authorization(fz, inputs_dir, generated, monkeypatch):
    """generate_test refuses a missing or hand-made authorization before it reads anything (readers spied)."""
    called = []
    for name in ("check_inputs", "load_qwen_tokenizer", "build_general_dev"):
        real = getattr(D, name)
        monkeypatch.setattr(D, name, lambda *a, _n=name, _r=real, **k: called.append(_n) or _r(*a, **k))
    real_read = TD.FZ.read_jsonl
    monkeypatch.setattr(TD.FZ, "read_jsonl", lambda *a, **k: called.append("read_jsonl") or real_read(*a, **k))
    with pytest.raises(ImplementationFail):
        TD.generate_test(fz, None, inputs_dir, generated["dir"])
    with pytest.raises(ImplementationFail, match="^IMPLEMENTATION_FAIL: TEST path refused: authorization for frozen "
                       "commit None, PROTOCOL_FROZEN names %s$" % fz.record.commit):   # a hand-made authorization
        TD.generate_test(fz, LK.TestAuthorization(None, None, None), inputs_dir, generated["dir"])
    with pytest.raises(ImplementationFail, match="not committed"):
        TD.generate_test(fz, LK.TestAuthorization(fz.record.commit, "a" * 64, "b" * 64), inputs_dir, generated["dir"])
    assert called == []
    with pytest.raises(ImplementationFail):
        LK.run_test_part(fz, {}, [], [], None)


# ---------------------------------------------------------------- conditions 2 and 3 on throw-away repositories

def _repo(tmp_path, files, dirty=None, protocol_frozen_commit=None):
    root = tmp_path / "repo"
    root.mkdir(parents=True)
    subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)
    pf = root / "metrix/e1-pilot/PROTOCOL_FROZEN"            # the real PROTOCOL_FROZEN (its frozen commit) ...
    pf.parent.mkdir(parents=True, exist_ok=True)
    blob = (PILOT / "PROTOCOL_FROZEN").read_bytes()
    if protocol_frozen_commit is not None:                   # ... or one whose current section names another commit
        from metrix_e1 import frozen as FZ
        blob = blob.replace(FZ.parse_protocol_frozen(blob).commit.encode(), protocol_frozen_commit.encode())
    pf.write_bytes(blob)
    for rel, obj in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(obj), encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), *GIT_ID, "commit", "-q", "--allow-empty", "-m", "records"], check=True)
    if dirty:
        (root / dirty).write_text("{}", encoding="utf-8")
    return root


G0, SEL = R.GATE0_RECORD_REL, R.SELECTION_FREEZE_REL
SELECTED = {"F": "F3", "L": "L2", "A": "A5"}


def _gate0(fz, status="PASS", mode=None, **kw):
    from metrix_e1 import mode as M
    rec = R.gate0_record(fz, mode or M.FORMAL_MODE, {"gate0_status": status})
    rec.update(kw)
    return rec


def _sha(obj):
    import hashlib
    return hashlib.sha256(json.dumps(obj).encode("utf-8")).hexdigest()


def test_gate0_record_condition_positive_control(fz, tmp_path):
    rec = _gate0(fz)
    root = _repo(tmp_path, {G0: rec})
    assert TD.check_gate0_record(fz, root) == _sha(rec)          # condition 2 alone holds for a correct record


@pytest.mark.parametrize("case", ["missing", "dirty", "smoke", "not_pass", "not_tested", "other_commit", "wrong_kind"])
def test_gate0_record_condition(fz, tmp_path, case):
    from metrix_e1 import mode as M
    rec = {"missing": None, "dirty": _gate0(fz), "smoke": _gate0(fz, mode=M.smoke_mode(3)),
           "not_pass": _gate0(fz, "PIPELINE_NOT_QUALIFIED"), "not_tested": _gate0(fz, "NOT_TESTED"),
           "other_commit": _gate0(fz, frozen_commit="0" * 40), "wrong_kind": _gate0(fz, kind="selection_freeze")}[case]
    root = _repo(tmp_path, {} if rec is None else {G0: rec}, dirty=G0 if case == "dirty" else None)
    with pytest.raises(TD.PreconditionFailed):
        TD.check_gate0_record(fz, root)


def _selection(fz, contract, content, gate0_sha, mode=None, selected=SELECTED, **kw):
    from metrix_e1 import mode as M
    ck = {s.name: "a" * 64 for s in T.training_plan(contract, SELECTED)}
    rec = R.selection_freeze_record(fz, mode or M.FORMAL_MODE, selected, content, ck, gate0_sha)
    rec.update(kw)
    return rec


def test_selection_record_condition_positive_control(fz, contract, generated, tmp_path):
    content = fz.check_data_dir(generated["dir"])
    rec = _selection(fz, contract, content, "b" * 64)
    root = _repo(tmp_path, {SEL: rec})
    assert TD.check_selection_record(fz, contract, root, content, "b" * 64) == _sha(rec)   # condition 3 alone holds


@pytest.mark.parametrize("case", ["missing", "smoke", "bad_selection", "S_selected", "data_hashes", "checkpoint",
                                  "unbound", "wrong_kind"])
def test_selection_record_condition(fz, contract, generated, tmp_path, case):
    from metrix_e1 import mode as M
    content = fz.check_data_dir(generated["dir"])
    good = _selection(fz, contract, content, "b" * 64)
    rec = {"missing": None, "smoke": _selection(fz, contract, content, "b" * 64, mode=M.smoke_mode(3)),
           "bad_selection": _selection(fz, contract, content, "b" * 64, selected={"F": "F9", "L": "L2", "A": "A5"}),
           "S_selected": _selection(fz, contract, content, "b" * 64, selected={"F": "S1", "L": "L2", "A": "A5"}),
           "data_hashes": _selection(fz, contract, dict(content, facts="0" * 64), "b" * 64),
           "checkpoint": dict(good, checkpoints=dict(list(good["checkpoints"].items())[:-1])),
           "unbound": _selection(fz, contract, content, "c" * 64),
           "wrong_kind": dict(good, kind="gate0")}[case]
    root = _repo(tmp_path, {} if rec is None else {SEL: rec})
    with pytest.raises(TD.PreconditionFailed):
        TD.check_selection_record(fz, contract, root, content, "b" * 64)


def test_pending_interpretations_block_test(monkeypatch):
    """Independent of the current rulings: one entry left pending blocks TEST; none pending lets the check pass."""
    from metrix_e1 import interpretations as INT
    ruled = tuple(dict(e, status="RULED") for e in INT.ENTRIES)
    monkeypatch.setattr(INT, "ENTRIES", ruled[:3] + (dict(ruled[3], status=INT.PENDING),) + ruled[4:])
    with pytest.raises(TD.PreconditionFailed, match="interpretations not yet ruled by Review Gate: %s$" % ruled[3]["id"]):
        TD.check_interpretations_ruled()
    monkeypatch.setattr(INT, "ENTRIES", ruled)
    TD.check_interpretations_ruled()


def test_interpretations_ruled_by_review_gate():
    """Review Gate 2026-11-24, stage-B ruling item 1: B1-B24 accepted; every record names the ruling; B3 and B14
    carry the ruling's notes; B19 no longer says it is to be ruled. Review Gate 2026-11-25, ruling on C1 item 3: B25
    accepted (status and reference of that ruling). Review Gate 2026-11-27, tasks/IMPL_C4_RULING.md item 1: B17
    revised (ST11 reads B17's estimate plus the checkpoint overhead), status and reference of that ruling. Nothing is
    pending."""
    from metrix_e1 import interpretations as INT
    assert [e["id"] for e in INT.ENTRIES] == ["B%d" % i for i in range(1, 26)]
    assert INT.pending() == [] and INT.pending_problem() is None
    assert INT.ACCEPTED == "ACCEPTED（Review Gate 2026-11-24）"
    assert INT.ACCEPTED_C1 == "ACCEPTED（Review Gate 2026-11-25）"
    assert INT.ACCEPTED_C4 == "ACCEPTED（Review Gate 2026-11-27 修订）"
    recs = INT.as_records()
    assert all(r["status"] == INT.ACCEPTED and r["ruling"] == INT.RULING_REF for r in recs[:24] if r["id"] != "B17")
    assert recs[16]["id"] == "B17" and recs[16]["status"] == INT.ACCEPTED_C4 and recs[16]["ruling"] == INT.RULING_REF_C4
    assert recs[24]["status"] == INT.ACCEPTED_C1 and recs[24]["ruling"] == INT.RULING_REF_C1
    assert "IMPL_C_REPORT.md「Review Gate 对阶段 B 的裁决」" in INT.RULING_REF
    assert INT.RULING_REF_C1.startswith("tasks/IMPL_C1_RULING.md 第 3 项")
    assert "3. B25 接受：checkpoint 哈希 = train.state_sha256。" in (PILOT / "tasks/IMPL_C1_RULING.md").read_text(
        encoding="utf-8")
    assert INT.RULING_REF_C4 == "tasks/IMPL_C4_RULING.md 第 1 项"
    c4 = (PILOT / "tasks/IMPL_C4_RULING.md").read_text(encoding="utf-8")
    assert "1. ST11 改为读「B17 估算 + checkpoint 开销」之和，超过 3.5 小时即停。" in c4
    assert "status 记为 ACCEPTED（Review Gate 2026-11-27 修订）" in c4
    assert "B17's estimate + the checkpoint overhead" in recs[16]["text"]
    assert "pilot.st11_estimate_hours" in recs[16]["where"]
    by_id = {r["id"]: r for r in recs}
    assert "train_Y.jsonl" in by_id["B3"]["ruling_note"] and "需重新校准" in by_id["B14"]["ruling_note"]
    assert "To be ruled" not in by_id["B19"]["text"]
    report = (PILOT / "reports/IMPL_C_REPORT.md").read_text(encoding="utf-8")
    assert report.count("## Review Gate 对阶段 B 的裁决") == 1 and report.count("## Review Gate 对 C1 的裁决") == 1


def test_b25_definition_is_the_code_of_state_sha256():
    """Review Gate's ruling on C1, item 3: the computation written in B25 (an independent implementation of its text
    here) gives train.state_sha256 of a model (random tiny Qwen3 models; no weights)."""
    import hashlib
    import torch
    from conftest import tiny_model
    from metrix_e1 import interpretations as INT
    from metrix_e1 import train as T
    text = {e["id"]: e for e in INT.ENTRIES}["B25"]["text"]
    assert "sorted order" in text and "str(t.dtype)" in text and "str(tuple(t.shape))" in text and "uint8" in text

    def from_text(module):
        h = hashlib.sha256()
        sd = module.state_dict()
        for k in sorted(sd):
            t = sd[k].detach().to("cpu").contiguous()
            h.update(k.encode("utf-8") + b"\0" + str(t.dtype).encode("utf-8") + b"\0"
                     + str(tuple(t.shape)).encode("utf-8") + b"\0")
            h.update(t.reshape(-1).view(torch.uint8).numpy().tobytes())
        return h.hexdigest()

    m = tiny_model(3)
    assert T.state_sha256(m) == from_text(m) and len(T.state_sha256(m)) == 64
    other = tiny_model(4)
    assert T.state_sha256(other) != T.state_sha256(m)


def test_a_committed_record_that_is_not_an_object_is_not_committed(fz, tmp_path):
    """record.committed_json refuses JSON that is not an object (round-2 code review; data-auditor C1 round 1 (a))."""
    root = _repo(tmp_path, {G0: [1, 2]})
    with pytest.raises(R.NotCommitted, match="gate0_record.json is a JSON list, not an object$"):
        R.committed_json(root, G0)
    with pytest.raises(ImplementationFail, match="TEST path refused: .*gate0_record.json is a JSON list"):
        LK.verify_authorization(LK.TestAuthorization(fz.record.commit, "a" * 64, "b" * 64), fz, root)


def test_run_test_part_rechecks_the_committed_records(fz, tmp_path):
    auth = LK.TestAuthorization(fz.record.commit, "a" * 64, "b" * 64)
    root = _repo(tmp_path, {})
    with pytest.raises(ImplementationFail, match="not committed"):
        LK.run_test_part(fz, {}, [], [], auth, root)


def test_check_preconditions_calls_the_interpretation_check(fz, generated, inputs_dir, monkeypatch):
    """With conditions 1-3 replaced by stubs that hold, check_preconditions refuses while an interpretation is
    pending, and (control) returns an authorization once none is pending. Only the authorization object is built;
    no TEST path is called."""
    from metrix_e1 import interpretations as INT
    monkeypatch.setattr(TD.STP, "st12", lambda *a, **k: fz)
    monkeypatch.setattr(TD, "check_gate0_record", lambda *a, **k: "a" * 64)
    monkeypatch.setattr(TD, "check_selection_record", lambda *a, **k: "b" * 64)
    monkeypatch.setattr(INT, "pending", lambda: ["B19"])
    with pytest.raises(TD.PreconditionFailed, match="interpretations not yet ruled by Review Gate: B19"):
        TD.check_preconditions(None, inputs_dir, generated["dir"])
    monkeypatch.setattr(INT, "pending", lambda: [])
    _, auth = TD.check_preconditions(None, inputs_dir, generated["dir"])
    assert (auth.frozen_commit, auth.gate0_record_sha256, auth.selection_record_sha256) == (fz.record.commit, "a" * 64, "b" * 64)


def _no_pending(monkeypatch, ids=()):
    from metrix_e1 import interpretations as INT
    monkeypatch.setattr(INT, "pending", lambda: list(ids))


def test_verify_authorization_branches(fz, contract, generated, tmp_path, monkeypatch):
    _no_pending(monkeypatch)
    content = fz.check_data_dir(generated["dir"])
    g = _gate0(fz)
    sel = _selection(fz, contract, content, _sha(g))
    root = _repo(tmp_path, {G0: g, SEL: sel})
    LK.verify_authorization(LK.TestAuthorization(fz.record.commit, _sha(g), _sha(sel)), fz, root)   # all checks hold
    with pytest.raises(ImplementationFail, match="^IMPLEMENTATION_FAIL: TEST path refused: committed %s has sha256 %s, "
                       "authorization f{64}$" % (SEL, _sha(sel))):
        LK.verify_authorization(LK.TestAuthorization(fz.record.commit, _sha(g), "f" * 64), fz, root)


def test_verify_authorization_frozen_commit_comparisons(fz, contract, tmp_path, monkeypatch):
    """BE2 (DEFERRED_MINORS 1.26): the three commits (authorization, PROTOCOL_FROZEN in the repository, the loaded
    frozen files) are compared in two checks with their own messages; each case below is refused by a different one,
    matched on the whole message."""
    import copy
    import dataclasses
    _no_pending(monkeypatch)
    real = fz.record.commit
    other = copy.copy(fz)                                    # frozen files loaded for another frozen commit
    other.record = dataclasses.replace(fz.record, commit="2" * 40)
    g = _gate0(fz)
    from metrix_e1 import frozen as FZ
    sel = _selection(fz, contract, {k: fz.data_hash(k) for k in FZ.CONTENT_HASH_KEYS}, _sha(g))
    root = _repo(tmp_path / "a", {G0: g, SEL: sel})
    auth = lambda c: LK.TestAuthorization(c, _sha(g), _sha(sel))                       # noqa: E731
    cases = [  # (authorization commit, frozen files, message)
        ("0" * 40, fz, "authorization for frozen commit 0{40}, PROTOCOL_FROZEN names %s" % real),   # auth only
        (real, other, "PROTOCOL_FROZEN names %s, the loaded frozen files 2{40}" % real),          # fz only
        ("2" * 40, other, "PROTOCOL_FROZEN names %s, the loaded frozen files 2{40}" % real),      # auth = fz
    ]
    for commit, f, msg in cases:
        with pytest.raises(ImplementationFail, match="^IMPLEMENTATION_FAIL: TEST path refused: %s$" % msg):
            LK.verify_authorization(auth(commit), f, root)
    # authorization = loaded frozen files, but the repository's PROTOCOL_FROZEN names another commit
    root3 = _repo(tmp_path / "b", {G0: g, SEL: sel}, protocol_frozen_commit="3" * 40)
    with pytest.raises(ImplementationFail, match="^IMPLEMENTATION_FAIL: TEST path refused: PROTOCOL_FROZEN names 3{40}, "
                       "the loaded frozen files %s$" % real):
        LK.verify_authorization(auth(real), fz, root3)
    LK.verify_authorization(auth(real), fz, root)            # control: all three equal


VERIFY_CASES = {"not_pass": "not PASS", "unbound": "not bound",
                "authorization_other_commit": "^IMPLEMENTATION_FAIL: TEST path refused: authorization for frozen commit "
                                              "1{40}, PROTOCOL_FROZEN names",
                "bad_selection": "not configurations of SEARCH_SPACE", "S_selected": "not configurations of SEARCH_SPACE",
                "checkpoint": "no checkpoint hash for 1 of the 30 runs", "checkpoint_not_hex": "no checkpoint hash",
                "data_hashes": "data content hashes", "pending": "interpretations not yet ruled by Review Gate: B19$"}


@pytest.mark.parametrize("case", sorted(VERIFY_CASES))
def test_verify_authorization_rechecks_what_the_generator_checked(fz, contract, generated, tmp_path, monkeypatch, case):
    """Each case breaks one thing the TEST generator's conditions 2 and 3 (and the interpretation check) require, in
    otherwise correct committed records with matching hashes; verify_authorization refuses with that reason."""
    _no_pending(monkeypatch, ["B19"] if case == "pending" else [])
    content = fz.check_data_dir(generated["dir"])
    commit = "1" * 40 if case == "authorization_other_commit" else fz.record.commit
    g = dict(_gate0(fz, "NOT_TESTED" if case == "not_pass" else "PASS"), frozen_commit=commit)
    selected = {"bad_selection": {"F": "F9", "L": "L2", "A": "A5"},
                "S_selected": {"F": "S1", "L": "L2", "A": "A5"}}.get(case, SELECTED)
    sel = _selection(fz, contract, dict(content, facts="0" * 64) if case == "data_hashes" else content,
                     "c" * 64 if case == "unbound" else _sha(g), selected=selected, frozen_commit=commit)
    ck = dict(sel["checkpoints"])
    if case == "checkpoint":
        ck.pop(sorted(ck)[0])
    if case == "checkpoint_not_hex":
        ck[sorted(ck)[0]] = "A" * 64
    sel["checkpoints"] = ck
    root = _repo(tmp_path, {G0: g, SEL: sel})
    with pytest.raises(ImplementationFail, match=VERIFY_CASES[case]):
        LK.verify_authorization(LK.TestAuthorization(commit, _sha(g), _sha(sel)), fz, root)
