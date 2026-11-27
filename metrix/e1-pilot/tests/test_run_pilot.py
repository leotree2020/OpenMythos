"""run_pilot.py and metrix_e1.pilot (Implementation Task Order V1 sections 5, 7, 11 items 3-5; Review Gate's ruling on
C1 of 2026-11-25 item 3; DEFERRED_MINORS 1.27 CA20, CA21; 1.30 CD13).

  - the formal mode cannot take smoke's shortened step count (acceptance 5): the formal commands have no step option,
    every command but smoke builds the formal mode, and a formal pilot on the CPU stops with ST8 before anything is
    generated, written or committed;
  - smoke outputs are labelled and stay in the work directory; the stops that read smoke values are recorded, not
    raised; the work directory is never inside the repository;
  - step 1 writes only the manifest fields ST12 leaves out;
  - every checkpoint is saved and reloaded with an unchanged train.state_sha256 (B25; C1 ruling 3);
  - the model directory is checked against the frozen revision;
  - the TEST evaluation command end to end (testgate.begin / evaluate_model(split="test") / finish) in a throw-away
    clone with a bare remote, synthetic TEST rows written by the test (not TEST rows: Review Gate supplementary
    ruling 5), random tiny models, evaluate.require_gpu replaced (the only GPU dependency on this path).
No model weights, no GPU, no TEST data.
"""
import dataclasses
import importlib.util
import json
import os
import subprocess
import sys

import pytest
import torch

from conftest import PILOT, tiny_model
from metrix_e1 import data as D
from metrix_e1 import evaluate as E
from metrix_e1 import frozen as FZ
from metrix_e1 import leakage as LK
from metrix_e1 import mode as M
from metrix_e1 import pilot as P
from metrix_e1 import record as R
from metrix_e1 import stops as STP
from metrix_e1 import testgate as TG
from metrix_e1 import train as T
from metrix_e1.errors import ImplementationFail, ST12Error

RUN_PILOT = PILOT / "run_pilot.py"


def run_pilot_module():
    spec = importlib.util.spec_from_file_location("run_pilot_under_test", RUN_PILOT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def git(root, *args):
    r = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=False)
    if r.returncode != 0:
        raise AssertionError("git %s: %s" % (args, r.stderr))
    return r.stdout.strip()


def shared_clone(fz, tmp_path):
    """A clone of this repository under tmp_path (objects shared, so the frozen commit is there; the checkout is
    HEAD's tree), its origin set to a path that is no repository: a formal Pilot on it cannot write into this clone or
    reach the pilot's remote."""
    root = tmp_path / "repo"
    git(tmp_path, "clone", "-q", "--shared", str(fz.repo_root), str(root))
    git(root, "remote", "set-url", "origin", str(tmp_path / "no-remote.git"))
    return root


# ------------------------------------------------------------------------------- formal vs smoke (acceptance 5)

def test_formal_commands_have_no_step_option(tmp_path):
    """GIT_DIR names no repository: should the option be accepted, the command stops at its first git command
    (frozen.load) and cannot write into or push from this clone."""
    env = dict(os.environ, GIT_DIR=str(tmp_path / "no-repository"))
    for cmd in ("formal", "test-generate", "test-evaluate"):
        r = subprocess.run([sys.executable, str(RUN_PILOT), cmd, "--steps", "3", "--inputs", str(tmp_path),
                            "--work", str(tmp_path / "w")], capture_output=True, text=True, check=False, env=env)
        assert r.returncode != 0 and r.stdout.strip().split("\n")[-1] == "RESULT: FAIL", (cmd, r.stdout, r.stderr)
        assert "unrecognized arguments: --steps 3" in r.stderr
        assert not (tmp_path / "w").exists()


def test_only_smoke_builds_a_shortened_mode():
    rp = run_pilot_module()
    ap = rp.parser()
    smoke = rp.build_mode(ap.parse_args(["smoke", "--steps", "3", "--inputs", "i", "--work", "w"]))
    assert smoke == M.smoke_mode(3) and smoke.steps(300) == 3
    for cmd in ("formal", "test-generate", "test-evaluate"):
        mode = rp.build_mode(ap.parse_args([cmd, "--inputs", "i", "--work", "w"]))
        assert mode is M.FORMAL_MODE and mode.steps(300) == 300
    with pytest.raises(ValueError):
        M.RunMode(M.FORMAL, 3)
    with pytest.raises(SystemExit):                    # smoke needs its step count
        ap.parse_args(["smoke", "--inputs", "i", "--work", "w"])


def test_formal_on_the_cpu_stops_with_st8_before_anything(fz, inputs_dir, tmp_path, monkeypatch):
    """ST8 (the device check) comes before step 1: no data, no manifest change, no git command that commits or
    pushes, nothing in the repository; the experiment record of the stopped run is written to <work> only."""
    def no_git(*a, **k):
        raise AssertionError("no commit precondition, commit or push before step 1")
    monkeypatch.setattr(TG, "check_commit_preconditions", no_git)
    monkeypatch.setattr(TG, "commit_paths", no_git)
    p = P.Pilot(M.FORMAL_MODE, inputs_dir, tmp_path / "work", "cpu", repo_root=shared_clone(fz, tmp_path))
    before = {rel: (p.root / rel).read_bytes() for rel in (FZ.DATA_MANIFEST_REL, FZ.SPLIT_MANIFEST_REL)}
    ok, status = P.run_gate(p, "formal")
    assert (ok, status) == (False, "BLOCKED")
    rec = json.loads((p.work / "experiment_record_formal.json").read_text(encoding="utf-8"))
    assert rec["mode"] == "formal" and rec["template"]["Status"] == "BLOCKED"
    assert rec["template"]["Stop Conditions"]["stop"]["code"] == "ST8"
    assert (p.work / "experiment_record_formal.txt").is_file()
    assert not p.data_dir.exists() and not (p.root / R.FORMAL_RESULTS_REL).exists()
    assert {rel: (p.root / rel).read_bytes() for rel in before} == before
    assert git(p.root, "status", "--porcelain") == ""


def test_no_formal_record_path_is_ignored_by_git(fz, contract):
    """Every path a formal command commits (git add of an ignored path fails; "runs" is in the repository's
    .gitignore)."""
    res = R.FORMAL_RESULTS_REL
    names = [s.name for s in T.training_plan(contract, {"F": "F1", "L": "L1", "A": "A1"})] + ["N"]
    rels = ([FZ.DATA_MANIFEST_REL, FZ.SPLIT_MANIFEST_REL, R.GATE0_RECORD_REL, R.SELECTION_FREEZE_REL, TG.ST10_RECORD_REL,
             TG.AUDITOR_L6_REL, TG.MARKER_REL, TG.RESULT_REL]
            + ["%s/step%d_record.json" % (res, k) for k in range(1, 9)]
            + ["%s/experiment_record_%s.%s" % (res, c, x) for c in ("formal", "test-evaluate") for x in ("json", "txt")]
            + ["%s/%s/%s.json" % (res, P.RUNS_DIR, n) for n in names]
            + ["%s/%s/%s_dev%s.json" % (res, P.DETAILS_DIR, n, x) for n in names for x in ("", "_g08")])
    r = subprocess.run(["git", "-C", str(fz.repo_root), "check-ignore", "--no-index", "--", *rels], capture_output=True,
                       text=True, check=False)
    assert r.returncode == 1 and r.stdout == "", r.stdout              # 1: none of them is ignored


def test_work_directory_inside_the_repository_is_refused(fz, inputs_dir):
    for mode in (M.smoke_mode(1), M.FORMAL_MODE):
        with pytest.raises(ImplementationFail):
            P.Pilot(mode, inputs_dir, fz.repo_root / "metrix" / "e1-pilot" / "work", "cpu")


def test_smoke_outputs_are_labelled_and_stay_in_the_work_directory(inputs_dir, tmp_path):
    p = P.Pilot(M.smoke_mode(1), inputs_dir, tmp_path / "w", "cpu")
    assert p.records == (tmp_path / "w" / P.SMOKE_RECORDS_DIR).resolve()
    path = p.write(P.RUNS_DIR + "/x.json", {"kind": "x", "value": P.Fraction(1, 4)})
    rec = json.loads(path.read_text(encoding="utf-8"))
    assert rec["label"] == M.SMOKE_LABEL and rec["mode"] == "smoke" and rec["value"] == 0.25
    p.label_dir(p.data_dir)
    assert (p.data_dir / P.LABEL_FILE).read_text(encoding="utf-8").strip() == M.SMOKE_LABEL
    assert p.commit([path], "message", "what") is None
    with pytest.raises(ImplementationFail):            # the formal results directory refuses smoke records
        R.write_record(dict(rec), p.root / R.FORMAL_RESULTS_REL / "x.json", p.root)


def test_smoke_records_the_value_stops_and_formal_raises_them(inputs_dir, tmp_path):
    s = P.Pilot(M.smoke_mode(1), inputs_dir, tmp_path / "s", "cpu")
    assert s.stop_check(STP.st2, s.fz, False) is False
    assert s.smoke_stops[0]["stop"] == "ST2" and s.smoke_stops[0]["label"] == M.SMOKE_LABEL
    assert s.stop_check(STP.st2, s.fz, True) is True and len(s.smoke_stops) == 1
    leak = {"checks": {"L1": {"within_limit": False}}, "result": "FAIL"}
    with pytest.raises(STP.Stop) as e:                 # ST1 reads the real data: it stops the smoke run as well
        s.stop_check(STP.st1, s.fz, leak)
    assert e.value.stop == "ST1"
    f = P.Pilot(M.FORMAL_MODE, inputs_dir, tmp_path / "f", "cpu")
    for fn, args in ((STP.st2, (False,)), (STP.st11, (f.contract, 99.0))):
        with pytest.raises(STP.Stop):
            f.stop_check(fn, f.fz, *args)
    assert set(P.SMOKE_RECORDED_STOPS) == {"ST2", "ST3", "ST4", "ST5", "ST11"}


# ------------------------------------------------------------------------------------------- step 1 manifests

def test_step1_writes_only_the_fields_st12_leaves_out(fz, generated):
    current = {rel: (fz.repo_root / rel).read_bytes() for rel in (FZ.DATA_MANIFEST_REL, FZ.SPLIT_MANIFEST_REL)}
    for rel, blob in current.items():
        assert P.manifest_bytes(json.loads(blob)) == blob            # the repository's layout
    hashes = D.file_hashes(generated["dir"])
    new = P.step1_manifests(fz, current, hashes)
    for rel, blob in new.items():
        assert FZ.strip_step1_fields(rel, json.loads(blob)) == FZ.strip_step1_fields(rel, json.loads(fz.blobs[rel]))
    dm, sm = json.loads(new[FZ.DATA_MANIFEST_REL]), json.loads(new[FZ.SPLIT_MANIFEST_REL])
    for n in D.DATA_FILES:
        assert dm["files"][n]["status"] == P.GENERATED
        assert dm["files"][n]["byte_sha256"] == hashes[n]["byte_sha256"]
        assert dm["files"][n]["canonical_sha256"] == hashes[n]["canonical_sha256"]
    for n in D.TEST_FILES:
        assert dm["files"][n]["status"] == "NOT_GENERATED" and dm["files"][n]["byte_sha256"] is None
    assert sm["split_sha256"]["train_Y.jsonl"] == hashes["train_Y.jsonl"]["canonical_sha256"]    # B3 ruling note
    assert sm["split_sha256"]["test_qa.jsonl"] is None
    assert P.step1_manifests(fz, new, hashes) == new                 # a second run writes the same bytes
    bad = json.loads(current[FZ.DATA_MANIFEST_REL])
    bad["model"]["revision"] = "0" * 40
    with pytest.raises(ST12Error):
        P.step1_manifests(fz, dict(current, **{FZ.DATA_MANIFEST_REL: P.manifest_bytes(bad)}), hashes)


# ---------------------------------------------------------------------------------- checkpoints (B25; C1 ruling 3)

def test_every_checkpoint_reloads_with_the_same_state_hash(inputs_dir, tmp_path, generated):
    p = P.Pilot(M.smoke_mode(2), inputs_dir, tmp_path / "w", "cpu")
    D.write(generated["files"], p.data_dir)
    p.load_data()
    base_sha = T.state_sha256(p.base_model())
    assert T.state_sha256(p.base_model()) == base_sha                # every run starts from the same weights
    for arm in ("F", "L", "A"):
        spec = T.search_runs(p.contract, arm)[0]
        model = p.base_model()
        T.train_run(model, p.tok, p.rows, spec, p.contract, p.mode, p.device)
        trained = T.state_sha256(model)
        reloaded, info = p.save_checkpoint(spec, model)
        assert info["state_sha256"] == info["reloaded_state_sha256"] == trained == T.state_sha256(reloaded)
        assert info["file_sha256"] == FZ.file_sha256(p.ckpt_dir / ("%s.pt" % spec.name))
        again = p.load_checkpoint(spec, p.ckpt_dir / ("%s.pt" % spec.name))
        assert T.state_sha256(again) == trained and trained != base_sha
        assert torch.load(p.ckpt_dir / ("%s.pt" % spec.name), weights_only=True)["label"] == M.SMOKE_LABEL
    assert (p.ckpt_dir / P.LABEL_FILE).is_file()
    with pytest.raises(ImplementationFail):            # a run is saved once
        p.save_checkpoint(spec, reloaded)


def test_a_checkpoint_that_does_not_reload_identically_is_refused(inputs_dir, tmp_path, monkeypatch):
    p = P.Pilot(M.smoke_mode(2), inputs_dir, tmp_path / "w", "cpu")
    spec = T.search_runs(p.contract, "F")[0]
    real = p.load_checkpoint

    def changed(spec_, path):
        m = real(spec_, path)
        with torch.no_grad():
            next(m.parameters()).view(-1)[0] += 1.0
        return m
    monkeypatch.setattr(p, "load_checkpoint", changed)
    with pytest.raises(ImplementationFail, match="after saving and reloading"):
        p.save_checkpoint(spec, p.base_model())
    other = P.Pilot(M.FORMAL_MODE, p.inputs, tmp_path / "f", "cpu")
    with pytest.raises(ImplementationFail, match="label"):            # a smoke checkpoint is not a formal one
        other.load_checkpoint(spec, p.ckpt_dir / ("%s.pt" % spec.name))


def test_model_directory_against_the_frozen_revision(fz, tmp_path):
    rev = fz.data_manifest["model"]["revision"]
    d = tmp_path / "qwen_model"
    meta = d / ".cache" / "huggingface" / "download"
    meta.mkdir(parents=True)
    (d / "config.json").write_text("{}", encoding="utf-8")
    (meta / "config.json.metadata").write_text(rev + "\netag\n1\n", encoding="utf-8")
    assert P.check_model_dir(fz, d, weights=False) == {}
    with pytest.raises(ST12Error, match="no \\*.safetensors"):
        P.check_model_dir(fz, d, weights=True)
    (d / "model.safetensors").write_bytes(b"weights")
    (meta / "model.safetensors.metadata").write_text("0" * 40 + "\n", encoding="utf-8")
    with pytest.raises(ST12Error, match="revision"):
        P.check_model_dir(fz, d, weights=True)
    (meta / "model.safetensors.metadata").write_text(rev + "\n", encoding="utf-8")
    assert P.check_model_dir(fz, d, weights=True) == {"model.safetensors": FZ.sha256_hex(b"weights")}
    (meta / "config.json.metadata").unlink()
    with pytest.raises(ST12Error, match="metadata"):
        P.check_model_dir(fz, d, weights=False)


def test_preflight_overhead_counts(contract):
    n = P.evaluation_plan(contract)
    assert n == {"loads": 1 + 30 + 3 + 16, "checkpoints": 30, "test_hashes": 16}
    seconds, counts = P.checkpoint_overhead_seconds(contract, 1.0, 2.0, 3.0, 4.0)
    assert counts == n and seconds == 50 * 1.0 + 30 * (2 * 2.0 + 3.0 + 4.0) + 16 * 2.0


# ------------------------------------------------------------------------------- TEST evaluation end to end

SELECTED = {"F": "F3", "L": "L2", "A": "A5"}


def synthetic_test_rows(facts):
    """One synthetic question per fact (not a TEST template, not a TEST row) and four synthetic windows."""
    qa = [{"fact_id": f["fact_id"], "template_id": "SYNTHETIC_T", "question": "Synthetic question %d (not a TEST "
           "row)?" % i} for i, f in enumerate(facts)]
    general = [{"domain": "synthetic", "doc_id": "synthetic-%d" % i, "ids": [11 + i, 12, 13, 14],
                "text": "synthetic window %d" % i} for i in range(4)]
    return {"test_qa.jsonl": FZ.jsonl_bytes(qa), "general_test.jsonl": FZ.jsonl_bytes(general)}


def write(root, rel, obj):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    blob = (json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=True) + "\n").encode("utf-8")
    path.write_bytes(blob)
    return FZ.sha256_hex(blob)


def commit_all(root, msg):
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", msg)
    git(root, "push", "-q", "origin", "HEAD:refs/heads/main")
    return git(root, "rev-parse", "HEAD")


@pytest.fixture
def eval_clone(fz, inputs_dir, generated, tmp_path, monkeypatch):
    """A clone of this repository (objects shared, so the frozen commit is there) whose origin is a throw-away bare
    repository standing for the pilot's remote, branch main standing for the pilot's branch; a formal Pilot on it
    with the generated data, tiny models, committed Gate 0 / freeze / run records, checkpoints, synthetic TEST rows,
    the ST10 record and an auditor count."""
    remote = tmp_path / "remote.git"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(remote))
    root = shared_clone(fz, tmp_path)
    git(root, "checkout", "-q", "-B", "main")
    for k, v in (("user.name", "metrix-test"), ("user.email", "metrix-test@invalid"), ("commit.gpgsign", "false")):
        git(root, "config", k, v)
    git(root, "remote", "set-url", "origin", str(remote))
    git(root, "push", "-q", "origin", "HEAD:refs/heads/main")
    monkeypatch.setattr(TG, "CANONICAL_REPO", TG.repo_id(str(remote)))
    monkeypatch.setattr(TG, "PILOT_BRANCH", "main")
    monkeypatch.setattr(E, "require_gpu", lambda mode, device: None)
    p = P.Pilot(M.FORMAL_MODE, inputs_dir, tmp_path / "work", "cpu", repo_root=root)
    p.contract = dataclasses.replace(p.contract, arms=dataclasses.replace(p.contract.arms, lora_layers=2))
    p.base_model = lambda: tiny_model(0)
    p.before_run = lambda next_seconds=0.0: None
    p.device_check = lambda: "test: device check replaced (CPU)"
    D.write(generated["files"], p.data_dir)
    facts = FZ.read_jsonl(p.data_dir / "facts.jsonl")
    plan = T.training_plan(p.contract, SELECTED)
    models = TG.evaluated_models(p.contract, SELECTED)
    checkpoints = {s.name: "b" * 64 for s in plan}
    p.ckpt_dir.mkdir(parents=True)
    for i, spec in enumerate(s for s in plan if s.name in models):
        m = p.model_for(spec)
        torch.manual_seed(100 + i)
        with torch.no_grad():
            for q in m.parameters():
                q.add_(0.01 * torch.randn_like(q))
        sha = T.state_sha256(m)
        path = p.ckpt_dir / ("%s.pt" % spec.name)
        torch.save({"label": None, "run": spec.name, "state_sha256": sha, "state_dict": m.state_dict()}, path)
        checkpoints[spec.name] = sha
        write(root, "%s/%s/%s.json" % (R.FORMAL_RESULTS_REL, P.RUNS_DIR, spec.name), {
            "kind": "training_run", "mode": "formal", "label": None, "run": spec.name,
            "checkpoint": {"state_sha256": sha, "file_sha256": FZ.file_sha256(path)}})
    g0_sha = write(root, R.GATE0_RECORD_REL, R.gate0_record(p.fz, M.FORMAL_MODE, {"gate0_status": "PASS"}))
    content = p.fz.check_data_dir(p.data_dir)
    sel_sha = write(root, R.SELECTION_FREEZE_REL, R.selection_freeze_record(p.fz, M.FORMAL_MODE, SELECTED, content,
                                                                             checkpoints, g0_sha))
    commit_all(root, "records of steps 1-8 (test)")
    files = synthetic_test_rows(facts)
    (p.work / P.TEST_DIR).mkdir(parents=True)
    for n, b in files.items():
        (p.work / P.TEST_DIR / n).write_bytes(b)
    auth = LK.TestAuthorization(p.fz.record.commit, g0_sha, sel_sha)
    TG.write_st10_record(p.fz, auth, {"checks": {c: {"value": 0} for c in LK.TEST_CHECKS}}, files)
    write(root, TG.AUDITOR_L6_REL, TG.auditor_count_record(p.fz, FZ.sha256_hex(files["general_test.jsonl"]), 0))
    commit_all(root, "ST10 record and the auditor's count (test)")
    return {"p": p, "root": root, "remote": remote, "models": models, "files": files}


def test_test_evaluate_end_to_end_once(eval_clone):
    c = eval_clone
    p, root, remote = c["p"], c["root"], c["remote"]
    ckpt = p.ckpt_dir / ("%s.pt" % c["models"][1])
    good = ckpt.read_bytes()
    ckpt.write_bytes(good + b"x")                      # a changed checkpoint file: refused before the marker
    assert P.run_test_evaluate(p) == (False, "BLOCKED")
    assert not (root / TG.MARKER_REL).exists() and git(remote, "ls-tree", "-r", "--name-only", "main").count(
        "test_evaluation_marker") == 0
    assert not (root / R.FORMAL_RESULTS_REL / "experiment_record_test-evaluate.json").exists()
    ckpt.write_bytes(good)
    ok, status = P.run_test_evaluate(p)
    assert ok and status in ("PASS", "PIPELINE_NOT_QUALIFIED")
    tree = git(remote, "ls-tree", "-r", "--name-only", "main").split("\n")
    for rel in (TG.MARKER_REL, TG.RESULT_REL, R.FORMAL_RESULTS_REL + "/experiment_record_test-evaluate.json"):
        assert rel in tree
    blob = git(remote, "show", "main:%s" % TG.RESULT_REL)
    result = json.loads(blob)
    assert sorted(result["summaries"]) == sorted(c["models"]) and result["final"]["final_status"] == status
    assert "Synthetic question" not in blob and "synthetic window" not in blob          # no TEST text (CD13)
    assert not any(k.startswith("general_") for s in result["summaries"].values() for k in s)
    marker = json.loads(git(remote, "show", "main:%s" % TG.MARKER_REL))
    assert marker["models"] == c["models"] and result["marker_commit"] == git(remote, "log", "-1", "--format=%H",
                                                                               "main", "--", TG.MARKER_REL)
    assert sorted(x.name for x in (p.work / P.TEST_DETAILS_DIR).iterdir()) == sorted(
        "%s_test.json" % m for m in c["models"])
    git(root, "pull", "-q", "--ff-only", "origin", "main")
    with pytest.raises(TG.TestAlreadyEvaluated):       # TEST is evaluated once
        P.run_test_evaluate(p)


def test_test_evaluate_refuses_outside_formal_mode(inputs_dir, tmp_path):
    p = P.Pilot(M.smoke_mode(1), inputs_dir, tmp_path / "w", "cpu")
    with pytest.raises(ImplementationFail):
        P.test_evaluate(p)
    with pytest.raises(ImplementationFail):
        P.run_test_generate(p)
