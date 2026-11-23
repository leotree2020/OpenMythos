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

from conftest import SRC
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


def test_generation_needs_authorization(fz, inputs_dir, generated):
    with pytest.raises(ImplementationFail):
        TD.generate_test(fz, None, inputs_dir, generated["dir"])
    with pytest.raises(ImplementationFail):
        LK.run_test_part(fz.split_manifest, {}, [], [], None, fz.repo_root)


# ---------------------------------------------------------------- conditions 2 and 3 on throw-away repositories

def _repo(tmp_path, files, dirty=None):
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)
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
    from metrix_e1 import interpretations as INT
    assert INT.pending()                                     # current state: every entry awaits Review Gate
    with pytest.raises(TD.PreconditionFailed, match="B1"):
        TD.check_interpretations_ruled()
    monkeypatch.setattr(INT, "ENTRIES", tuple(dict(e, status="RULED") for e in INT.ENTRIES))
    TD.check_interpretations_ruled()


def test_run_test_part_rechecks_the_committed_records(fz, tmp_path):
    auth = LK.TestAuthorization(fz.record.commit, "a" * 64, "b" * 64)
    root = _repo(tmp_path, {})
    with pytest.raises(ImplementationFail, match="not committed"):
        LK.run_test_part(fz.split_manifest, {}, [], [], auth, root)
