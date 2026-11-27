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
from metrix_e1.errors import ImplementationFail, ProtocolStop, ST12Error

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
    (path,) = p.work.glob("experiment_record_formal_*.json")
    rec = json.loads(path.read_text(encoding="utf-8"))
    assert rec["mode"] == "formal" and rec["template"]["Status"] == "BLOCKED"
    assert rec["template"]["Stop Conditions"]["stop"]["code"] == "ST8"
    assert path.with_suffix(".txt").is_file()
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
            + ["%s/experiment_record_%s_20261127T000000Z.%s" % (res, c, x) for c in ("formal", "test-generate",
                                                                                       "test-evaluate")
               for x in ("json", "txt")]
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
    other = tmp_path / "other_repo"                    # a repository root of the test's own: nothing written here
    with pytest.raises(ImplementationFail):            # the formal results directory refuses smoke records
        R.write_record(dict(rec), other / R.FORMAL_RESULTS_REL / "x.json", other)
    assert not other.exists()


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
    assert n == {"loads": 1 + 30 + 3 + 16, "checkpoints": 30, "test_state_hashes": 17, "test_file_hashes": 15,
                 "test_models": 16}
    seconds, counts = P.checkpoint_overhead_seconds(contract, 1.0, 2.0, 3.0, 4.0, 5.0)
    assert counts == n and seconds == 50 * 1.0 + 30 * (2 * 2.0 + 3.0 + 4.0 + 5.0) + 17 * 2.0 + 15 * 5.0
    pre = {"dev_evaluation_seconds": 10.0, "load_s": 1.0, "reload_s": 3.0, "hash_s": 2.0, "file_hash_s": 5.0}
    assert P.test_evaluation_seconds(contract, pre) == 1.0 + 15 * 3.0 + 16 * 10.0 * 3 / 2 + 17 * 2.0 + 15 * 5.0


def test_st7_look_ahead_of_a_run(inputs_dir, tmp_path, contract):
    """run_seconds: the A factor only for arm A (B17); eval_seconds by what is loaded first (code-reviewer MAJOR 1 of
    the fix commit's round 1)."""
    p = P.Pilot(M.FORMAL_MODE, inputs_dir, tmp_path / "w", "cpu")
    f, a = T.search_runs(contract, "F")[0], T.search_runs(contract, "A")[0]
    assert p.run_seconds(f) == 0.0 and p.eval_seconds("load") == 0.0           # before the preflight
    p.pre = {"mean_step_s": 0.1, "a_factor": 5.0, "dev_evaluation_seconds": 7.0, "load_s": 1.0, "hash_s": 2.0,
             "save_s": 3.0, "reload_s": 4.0, "file_hash_s": 6.0}
    rest = 1.0 + 2 * 2.0 + 3.0 + 6.0 + 4.0 + 7.0
    assert p.run_seconds(f) == pytest.approx(0.1 * 300 + rest)
    assert p.run_seconds(a) == pytest.approx(0.1 * 300 * 5.0 + rest)
    assert (p.eval_seconds("load"), p.eval_seconds("reload"), p.eval_seconds(None)) == (8.0, 11.0, 7.0)


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


def clone_with_remote(fz, tmp_path, monkeypatch):
    """shared_clone on branch main with a throw-away bare repository as origin; the bare repository stands for the
    pilot's remote and main for the pilot's branch (testgate.CANONICAL_REPO, PILOT_BRANCH)."""
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
    return remote, root


@pytest.fixture
def eval_clone(fz, inputs_dir, generated, tmp_path, monkeypatch):
    """A clone of this repository (objects shared, so the frozen commit is there) whose origin is a throw-away bare
    repository standing for the pilot's remote, branch main standing for the pilot's branch; a formal Pilot on it
    with the generated data, tiny models, committed Gate 0 / freeze / run records, checkpoints, synthetic TEST rows,
    the ST10 record and an auditor count."""
    remote, root = clone_with_remote(fz, tmp_path, monkeypatch)
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
    write(root, "%s/step2_record.json" % R.FORMAL_RESULTS_REL, {"kind": "step2", "mode": "formal", "label": None,
          "preflight": {"timing": {"mean_step_s": 0.1, "a_factor": 1.0, "dev_evaluation_seconds": 1.0, "load_s": 1.0,
                                   "hash_s": 0.1, "save_s": 0.1, "reload_s": 0.1, "file_hash_s": 0.1}}})
    write(root, "%s/step3_record.json" % R.FORMAL_RESULTS_REL, {"kind": "step3", "mode": "formal", "label": None,
          "N": {"state_sha256": T.state_sha256(tiny_model(0))}})
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
    real_base = p.base_model
    p.base_model = lambda: tiny_model(1)               # not N's weights of the step 3 record: refused before the marker
    assert P.run_test_evaluate(p) == (False, "BLOCKED") and not (root / TG.MARKER_REL).exists()
    p.base_model = real_base
    ckpt = p.ckpt_dir / ("%s.pt" % c["models"][1])
    good = ckpt.read_bytes()
    ckpt.write_bytes(good + b"x")                      # a changed checkpoint file: refused before the marker
    assert P.run_test_evaluate(p) == (False, "BLOCKED")
    assert not (root / TG.MARKER_REL).exists() and git(remote, "ls-tree", "-r", "--name-only", "main").count(
        "test_evaluation_marker") == 0
    assert not list((root / R.FORMAL_RESULTS_REL).glob("experiment_record_test-evaluate_*"))
    ckpt.write_bytes(good)
    looks = []
    p.before_run = lambda next_seconds=0.0: looks.append(next_seconds)
    ok, status = P.run_test_evaluate(p)
    timing = json.loads((root / R.FORMAL_RESULTS_REL / "step2_record.json").read_text(encoding="utf-8"))
    assert looks[0] == P.test_evaluation_seconds(p.contract, timing["preflight"]["timing"]) > 0    # before the begin
    assert ok and status in ("PASS", "PIPELINE_NOT_QUALIFIED")
    tree = git(remote, "ls-tree", "-r", "--name-only", "main").split("\n")
    assert TG.MARKER_REL in tree and TG.RESULT_REL in tree
    (exp,) = [x for x in tree if x.startswith(R.FORMAL_RESULTS_REL + "/experiment_record_test-evaluate_")
              and x.endswith(".json")]
    exp_blob = git(remote, "show", "main:%s" % exp)
    assert "Synthetic question" not in exp_blob and "synthetic window" not in exp_blob
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
    tip = git(remote, "rev-parse", "main")
    with pytest.raises(TG.TestAlreadyEvaluated):       # TEST is evaluated once
        P.run_test_evaluate(p)
    assert git(remote, "rev-parse", "main") == tip     # and that refusal writes no record


def test_test_evaluate_refuses_outside_formal_mode(inputs_dir, tmp_path):
    p = P.Pilot(M.smoke_mode(1), inputs_dir, tmp_path / "w", "cpu")
    with pytest.raises(ImplementationFail):
        P.test_evaluate(p)
    with pytest.raises(ImplementationFail):
        P.run_test_generate(p)


# ------------------------------------------------------------------------------- round-1 review of 5219ff77

def test_a_stop_inside_a_step_writes_the_step_record_first(inputs_dir, tmp_path, generated):
    """Pilot.stop_in_step: a stop that propagates (ST1 also stops a smoke run) writes the step's record with what the
    step computed and the stop, then raises again (code-reviewer MAJOR 3 of round 1)."""
    p = P.Pilot(M.smoke_mode(1), inputs_dir, tmp_path / "w", "cpu")
    D.write(generated["files"], p.data_dir)
    p.step_start(2)
    leak = {"checks": {"L1": {"within_limit": False}}, "result": "FAIL"}
    with pytest.raises(STP.Stop):
        p.stop_in_step(2, {"leakage": leak}, [], STP.st1, p.fz, leak)
    rec = json.loads((p.records / "step2_record.json").read_text(encoding="utf-8"))
    assert rec["stopped"]["code"] == "ST1" and rec["leakage"] == leak and rec["label"] == M.SMOKE_LABEL


def test_continuity_checks_before_anything(fz, inputs_dir, tmp_path):
    """start_checks: a --work without the device ledger after a formal run committed step records, and formal after a
    freeze record, are refused (BLOCKED) before anything is written."""
    root = shared_clone(fz, tmp_path)
    for k, v in (("user.name", "metrix-test"), ("user.email", "metrix-test@invalid"), ("commit.gpgsign", "false")):
        git(root, "config", k, v)
    p = P.Pilot(M.FORMAL_MODE, inputs_dir, tmp_path / "work", "cpu", repo_root=root)
    p.start_checks("formal")                            # nothing committed yet: passes
    write(root, P.STEP1_RECORD_REL, {"kind": "step1"})
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "a step 1 record")
    with pytest.raises(ProtocolStop, match="device ledger"):
        p.start_checks("test-evaluate")
    p.ledger.path.parent.mkdir(parents=True)
    p.ledger.record_first("test device")
    p.start_checks("formal")
    q = P.Pilot(M.FORMAL_MODE, inputs_dir, tmp_path / "work2", "cpu", repo_root=root)
    q.ckpt_dir.mkdir(parents=True)
    q.ledger.record_first("test device")
    (q.ckpt_dir / "F-F1-seed101.pt").write_bytes(b"a checkpoint of an earlier run")
    with pytest.raises(ProtocolStop, match="already holds checkpoints"):    # no freeze record yet
        q.start_checks("formal")
    write(root, R.SELECTION_FREEZE_REL, {"kind": "selection_freeze"})
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "a freeze record")
    with pytest.raises(ProtocolStop, match="freeze record"):
        p.start_checks("formal")
    p.start_checks("test-evaluate")                     # TEST evaluation follows the freeze


def test_smoke_step8_refuses_where_formal_records_exist(fz, inputs_dir, generated, tmp_path):
    """On a checkout holding a Gate 0, freeze or ST10 record the generator's preconditions may hold: the smoke run's
    refusal test does not start the generator there (code-reviewer MAJOR 9 of round 1)."""
    root = shared_clone(fz, tmp_path)
    for k, v in (("user.name", "metrix-test"), ("user.email", "metrix-test@invalid"), ("commit.gpgsign", "false")):
        git(root, "config", k, v)
    write(root, R.GATE0_RECORD_REL, {"kind": "gate0"})
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "a Gate 0 record")
    p = P.Pilot(M.smoke_mode(1), inputs_dir, tmp_path / "w", "cpu", repo_root=root)
    D.write(generated["files"], p.data_dir)
    with pytest.raises(ImplementationFail, match="formal records"):
        P.step8_smoke_refusal(p)
    assert not (p.work / "step8_refused_out").exists()


def test_test_evaluate_records_after_the_marker_and_for_st10(fz, inputs_dir, tmp_path, monkeypatch):
    """run_test_evaluate: before the marker a refusal writes no record (ST10 excepted); after it every stop and a
    crash write one (BLOCKED) and a crash is raised again (code-reviewer MAJOR 2, 4; data-auditor IC7-M1)."""
    root = shared_clone(fz, tmp_path)
    p = P.Pilot(M.FORMAL_MODE, inputs_dir, tmp_path / "work", "cpu", repo_root=root)
    seen = []
    monkeypatch.setattr(P, "final_record", lambda p_, command, status, actual, nxt, runs, stop: seen.append(
        (command, status, stop)))
    marker = root / TG.MARKER_REL

    def run(exc, with_marker):
        def fake(p_):
            if with_marker:                             # as test_evaluate: begin called, the marker written
                p_.marker_before_begin, p_.begin_called = False, True
                marker.parent.mkdir(parents=True, exist_ok=True)
                marker.write_text("{}", encoding="utf-8")
            raise exc
        monkeypatch.setattr(P, "test_evaluate", fake)
        seen.clear()
        p.begin_called, p.marker_before_begin = False, None
        try:
            return P.run_test_evaluate(p)
        finally:
            if marker.exists():
                marker.unlink()
    assert run(ProtocolStop(None, "BLOCKED", "refused"), False) == (False, "BLOCKED") and seen == []
    with pytest.raises(RuntimeError):
        run(RuntimeError("injected crash"), False)
    assert seen == []
    assert run(STP.Stop("ST10", "BLOCKED", "a", "injected ST10"), False) == (False, "BLOCKED")
    assert seen[0][0] == "test-evaluate" and seen[0][2]["code"] == "ST10"
    assert run(ProtocolStop(None, "BLOCKED", "after the marker"), True) == (False, "BLOCKED") and len(seen) == 1
    with pytest.raises(RuntimeError):
        run(RuntimeError("injected crash"), True)
    assert seen[0][1] == "BLOCKED" and "injected crash" in seen[0][2]["message"]
    with pytest.raises(KeyboardInterrupt):
        run(KeyboardInterrupt(), True)
    assert seen[0][1] == "BLOCKED"
    assert run(STP.Stop("ST7", "BLOCKED", "a", "injected ST7 look-ahead"), False) == (False, "BLOCKED")
    assert seen[0][2]["code"] == "ST7"                  # a protocol stop before the begin is recorded

    def already(p_):                                    # an earlier run evaluated TEST: the marker was there before
        p_.marker_before_begin, p_.begin_called = True, True
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("{}", encoding="utf-8")
        raise TG.TestAlreadyEvaluated("evaluated")
    monkeypatch.setattr(P, "test_evaluate", already)
    seen.clear()
    with pytest.raises(TG.TestAlreadyEvaluated):
        P.run_test_evaluate(p)
    assert seen == []
    marker.unlink()

    def started_earlier(p_):                            # an earlier run began TEST and left no result: begin refuses
        p_.marker_before_begin, p_.begin_called = True, True        # (BLOCKED, no stop code); this run began nothing
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("{}", encoding="utf-8")
        raise ProtocolStop(None, "BLOCKED", "TEST evaluation was already started and no result was committed")
    monkeypatch.setattr(P, "test_evaluate", started_earlier)
    seen.clear()
    assert P.run_test_evaluate(p) == (False, "BLOCKED") and seen == []
    marker.unlink()


def test_formal_commit_chain_through_the_freeze_record(fz, inputs_dir, generated, tmp_path, monkeypatch):
    """The formal command's own paths (code-reviewer MAJOR 12 of round 1) on a clone with a bare remote: steps 1-8 commit
    and push their records, the manifests get the step-1 fields, the freeze record is committed and the TEST
    generator's preconditions then hold (test_data.check_preconditions; nothing is generated). Replaced: the device
    (CPU), the model (the smoke run's small model), train.train_run (1 smoke step in place of the formal steps; one
    search run made non-finite: ST6 excludes it and its stop state is hashed), evaluate.evaluate_model (copies of one
    real evaluation with random correctness), the stops that read result values and Gate 0's verdict (PASS)."""
    import copy
    import itertools
    import random
    from metrix_e1 import gate as G
    from metrix_e1 import test_data as TD
    remote, root = clone_with_remote(fz, tmp_path, monkeypatch)
    s = P.Pilot(M.smoke_mode(1), inputs_dir, tmp_path / "smoke_work", "cpu")
    D.write(generated["files"], s.data_dir)
    s.load_data()
    base_ev = s.evaluate(s.base_model(), with_em=True)
    p = P.Pilot(M.FORMAL_MODE, inputs_dir, tmp_path / "work", "cpu", repo_root=root)
    p.contract = dataclasses.replace(p.contract, arms=dataclasses.replace(p.contract.arms, lora_layers=2))
    p.device_check = lambda: {"name": "test (CPU)", "total_memory": 0}
    p.first_load = lambda: None
    looks = []
    p.before_run = lambda next_seconds=0.0: looks.append(next_seconds)
    p.base_model = s.base_model
    calls = itertools.count()

    def fake_eval(model, tok, data, templates, ev, mode, device, split="dev", with_em=True, with_s_mapping=False, **kw):
        out = copy.deepcopy(base_ev)
        rng = random.Random(next(calls))
        for row in out["dev_qa"]:
            row["correct"] = rng.random() < 0.5
        if not with_em:
            del out["em_dev"]
        if with_s_mapping:
            out["s_mapping_dev_qa"], out["s_mapping_cb"] = copy.deepcopy(out["dev_qa"]), copy.deepcopy(out["train_cb"])
        return out
    monkeypatch.setattr(E, "evaluate_model", fake_eval)
    real_train = T.train_run

    def train(model, tok, data, spec, contract, mode, device, log_fn=None):
        if spec.name == "F-F6-seed101" and mode.formal:
            raise T.NonFinite("injected for the test", [float("nan")])
        return real_train(model, tok, data, spec, contract, M.smoke_mode(1), device, log_fn)
    monkeypatch.setattr(T, "train_run", train)
    for name in ("st2", "st3", "st4", "st5"):
        monkeypatch.setattr(STP, name, lambda *a, **k: None)
    monkeypatch.setattr(G, "judge", lambda values, contract, mode: {
        "conditions": {c: {"satisfied": True, "reason": None, "note": None} for c in G.CONDITIONS},
        "gate0_status": "PASS", "reasons": [], "note": None})
    ok, status = P.run_gate(p, "formal")
    assert (ok, status) == (True, "PASS")
    assert git(root, "status", "--porcelain") == "" and git(root, "rev-parse", "HEAD") == git(remote, "rev-parse", "main")
    plan = T.training_plan(p.contract, {"F": "F1", "L": "L1", "A": "A1"})
    expected = [p.run_seconds(sp) for sp in plan if sp.phase == "search" and sp.arm == "F"]
    assert p.pre is not None and expected[0] > 0 and expected[0] in looks      # the ST7 look-ahead reaches before_run
    a_look = p.run_seconds(T.search_runs(p.contract, "A")[0])
    assert a_look in looks and a_look > expected[0]
    tree = git(remote, "ls-tree", "-r", "--name-only", "main").split("\n")
    res = R.FORMAL_RESULTS_REL
    for k in range(1, 9):
        assert "%s/step%d_record.json" % (res, k) in tree
    runs = [x for x in tree if x.startswith("%s/%s/" % (res, P.RUNS_DIR))]
    assert len(runs) == 30 and R.GATE0_RECORD_REL in tree and R.SELECTION_FREEZE_REL in tree
    (exp,) = [x for x in tree if x.startswith(res + "/experiment_record_formal_") and x.endswith(".json")]
    assert json.loads(git(remote, "show", "main:%s" % exp))["template"]["Status"] == "NOT_TESTED"
    dm = json.loads(git(remote, "show", "main:%s" % FZ.DATA_MANIFEST_REL))
    assert all(dm["files"][n]["status"] == P.GENERATED for n in D.DATA_FILES)
    freeze = json.loads(git(remote, "show", "main:%s" % R.SELECTION_FREEZE_REL))
    f6 = json.loads(git(remote, "show", "main:%s/%s/F-F6-seed101.json" % (res, P.RUNS_DIR)))
    assert f6["finite"] is False and freeze["checkpoints"]["F-F6-seed101"] == f6["checkpoint"]["state_sha256"]
    assert freeze["selected"]["F"] != "F6" and len(freeze["checkpoints"]) == 30
    fz2, auth = TD.check_preconditions(root, inputs_dir, p.data_dir)      # the TEST generator's preconditions hold
    assert auth.selection_record_sha256 == FZ.sha256_hex((root / R.SELECTION_FREEZE_REL).read_bytes())
    assert p.commit([root / P.STEP1_RECORD_REL], "unchanged", "an unchanged record") is None
    with pytest.raises(ProtocolStop, match="device ledger"):        # first_load was replaced: no ledger was written
        p.start_checks("formal")
    p.ledger.record_first("test device")
    with pytest.raises(ProtocolStop, match="freeze record"):
        p.start_checks("formal")


def _formal_on_clone(fz, inputs_dir, generated, tmp_path, monkeypatch):
    """The replacements of test_formal_commit_chain_through_the_freeze_record (device, model, 1 smoke step, copies of
    one real evaluation, Gate 0 verdict); the stops that read result values are left to the caller."""
    import copy
    import itertools
    import random
    remote, root = clone_with_remote(fz, tmp_path, monkeypatch)
    s = P.Pilot(M.smoke_mode(1), inputs_dir, tmp_path / "smoke_work", "cpu")
    D.write(generated["files"], s.data_dir)
    s.load_data()
    base_ev = s.evaluate(s.base_model(), with_em=True)
    p = P.Pilot(M.FORMAL_MODE, inputs_dir, tmp_path / "work", "cpu", repo_root=root)
    p.contract = dataclasses.replace(p.contract, arms=dataclasses.replace(p.contract.arms, lora_layers=2))
    p.device_check = lambda: {"name": "test (CPU)", "total_memory": 0}
    p.first_load = lambda: None
    p.before_run = lambda next_seconds=0.0: None
    p.base_model = s.base_model
    calls = itertools.count()

    def fake_eval(model, tok, data, templates, ev, mode, device, split="dev", with_em=True, with_s_mapping=False, **kw):
        out = copy.deepcopy(base_ev)
        rng = random.Random(next(calls))
        for row in out["dev_qa"]:
            row["correct"] = rng.random() < 0.5
        return out
    monkeypatch.setattr(E, "evaluate_model", fake_eval)
    return remote, root, p


@pytest.mark.parametrize("how", ["st3", "crash"])
def test_formal_stop_and_crash_commit_what_was_written(fz, inputs_dir, generated, tmp_path, monkeypatch, how):
    """Formal on a clone with a bare remote (code-reviewer MAJOR 4 of the fix commit's round 1): ST3 at step 4 (the real
    stop: the small model's positive control fails) commits the step 4 record with the stop and the six F runs; a crash
    in the third F run commits the two finished runs' records with the experiment record (Pilot.uncommitted). The
    clone is left clean and the remote holds everything."""
    remote, root, p = _formal_on_clone(fz, inputs_dir, generated, tmp_path, monkeypatch)
    monkeypatch.setattr(STP, "st2", lambda *a, **k: None)
    real_train = T.train_run

    def train(model, tok, data, spec, contract, mode, device, log_fn=None):
        if how == "crash" and spec.name == "F-F3-seed101":
            raise RuntimeError("injected crash")
        return real_train(model, tok, data, spec, contract, M.smoke_mode(1), device, log_fn)
    monkeypatch.setattr(T, "train_run", train)
    res = R.FORMAL_RESULTS_REL
    if how == "st3":
        assert P.run_gate(p, "formal") == (False, "PIPELINE_NOT_QUALIFIED")
    else:
        with pytest.raises(RuntimeError, match="injected crash"):
            P.run_gate(p, "formal")
    assert git(root, "status", "--porcelain") == "" and git(root, "rev-parse", "HEAD") == git(remote, "rev-parse", "main")
    tree = git(remote, "ls-tree", "-r", "--name-only", "main").split("\n")
    runs = sorted(x.rsplit("/", 1)[1] for x in tree if x.startswith("%s/%s/" % (res, P.RUNS_DIR)))
    (exp,) = [x for x in tree if x.startswith(res + "/experiment_record_formal_") and x.endswith(".json")]
    rec = json.loads(git(remote, "show", "main:%s" % exp))
    if how == "st3":
        step4 = json.loads(git(remote, "show", "main:%s/step4_record.json" % res))
        assert step4["stopped"]["code"] == "ST3" and "acc_cb" in step4["positive_control"]
        assert runs == ["F-F%d-seed101.json" % i for i in range(1, 7)]
        assert rec["template"]["Stop Conditions"]["stop"]["code"] == "ST3"
    else:
        assert "%s/step4_record.json" % res not in tree
        assert runs == ["F-F1-seed101.json", "F-F2-seed101.json"]
        assert "%s/%s/F-F2-seed101_dev.json" % (res, P.DETAILS_DIR) in tree
        assert "injected crash" in rec["template"]["Stop Conditions"]["stop"]["message"]


def test_test_generate_records_an_st10_stop_of_its_own_run(fz, inputs_dir, tmp_path, monkeypatch):
    """run_test_generate (code-reviewer MAJOR 2 of round 1, MINOR of the fix commit): an over-limit ST10 record
    committed by this run gives an experiment record (BLOCKED, ST10); one already committed before the run, or none,
    gives none. pilot's subprocess module is replaced (the generator is not started; nothing is generated)."""
    import types
    remote, root = clone_with_remote(fz, tmp_path, monkeypatch)
    p = P.Pilot(M.FORMAL_MODE, inputs_dir, tmp_path / "work", "cpu", repo_root=root)
    seen = []
    monkeypatch.setattr(P, "final_record", lambda p_, command, status, actual, nxt, runs, stop: seen.append(
        (command, status, stop)))
    over = {"kind": "st10", "counts": {c: 0 for c in LK.TEST_CHECKS}}
    over["counts"]["L4"] = 1

    def generator(commits):
        def run(cmd, **kw):
            if commits:
                write(root, TG.ST10_RECORD_REL, over)
                commit_all(root, "ST10 record (test)")
            return types.SimpleNamespace(returncode=1)
        return run
    monkeypatch.setattr(P, "subprocess", types.SimpleNamespace(run=generator(False)))
    assert P.run_test_generate(p) == 1 and seen == []
    monkeypatch.setattr(P, "subprocess", types.SimpleNamespace(run=generator(True)))
    assert P.run_test_generate(p) == 1
    assert seen[0][:2] == ("test-generate", "BLOCKED") and seen[0][2]["code"] == "ST10"
    seen.clear()
    monkeypatch.setattr(P, "subprocess", types.SimpleNamespace(run=generator(False)))
    assert P.run_test_generate(p) == 1 and seen == []       # the earlier run's ST10 record is not this run's stop
