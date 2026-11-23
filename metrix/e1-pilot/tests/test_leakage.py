"""Leakage checks L1-L6, Gate 0 part (protocol v1.1 section 3): each check detects a planted violation (the checks
are not vacuous), and the command of the protocol's interface prints RESULT: FAIL and exits non-zero when a check is
over its limit (Implementation Task Order V1, section 5 "检查脚本"). No TEST question is instantiated."""
import copy
import json
import os
import shutil
import subprocess
import sys

import pytest

from metrix_e1 import frozen as FZ
from metrix_e1 import leakage as LK

from conftest import PILOT, SRC


@pytest.fixture
def loaded(generated):
    return LK.load_data(generated["dir"])


def _over(fz, data, split_manifest=None):
    report = LK.run_gate0(split_manifest or fz.split_manifest, data)
    return {c for c, v in report["checks"].items() if not v["within_limit"]}, report


def test_clean_data_passes(fz, loaded):
    assert _over(fz, loaded)[0] == set()


def _first(facts, exposure, field):
    return next(f[field] for f in facts if f["exposure"] == exposure)


def test_l3a_unread_entity_in_train_Y(fz, loaded):
    d = copy.deepcopy(loaded)
    d["train_Y"][0]["text"] += " " + _first(d["facts"], "unread", "entity").upper()      # case-insensitive
    assert _over(fz, d)[0] == {"L3a"}


def test_l3a_and_l3b_answers_in_anchor(fz, loaded):
    d = copy.deepcopy(loaded)
    d["anchor_text"][7]["text"] += " " + _first(d["facts"], "unread", "answer") + " " + _first(d["facts"], "learned", "answer")
    over, report = _over(fz, d)
    assert over == {"L3a", "L3b"}
    assert report["checks"]["L3b"]["value"] == 1


def test_l4_dev_question_in_train_F(fz, loaded):
    d = copy.deepcopy(loaded)
    d["train_F"][3]["text"] += " " + d["dev_qa"][5]["question"]
    assert _over(fz, d)[0] == {"L4"}


def test_l5_duplicate_string_and_fact_id(fz, loaded):
    d = copy.deepcopy(loaded)
    d["facts"][1]["answer"] = d["facts"][0]["answer"]
    over, report = _over(fz, d)
    assert "L5" in over and report["checks"]["L5"]["detail"]["duplicate_strings"] == 1
    d = copy.deepcopy(loaded)
    unread = next(f for f in d["facts"] if f["exposure"] == "unread")
    unread["fact_id"] = d["facts"][0]["fact_id"]
    assert _over(fz, d)[1]["checks"]["L5"]["detail"]["fact_id_overlap"] == 1


def test_l6_shared_13gram_counted_within_documents(fz, loaded):
    d = copy.deepcopy(loaded)
    words = d["general_dev"][0]["text"].split()[:13]
    assert len(words) == 13
    d["anchor_text"][0]["text"] += " " + " ".join(words)
    over, report = _over(fz, d)
    assert over == {"L6"} and report["checks"]["L6"]["value"] >= 1
    # 13 words split across two anchor documents (6 + 7) do not form a shared 13-gram
    d = copy.deepcopy(loaded)
    d["anchor_text"][0]["text"] += " " + " ".join(words[:6])
    d["anchor_text"][1]["text"] = " ".join(words[6:]) + " " + d["anchor_text"][1]["text"]
    assert _over(fz, d)[0] == set()


def test_l1_l2_templates(fz, loaded):
    sm = copy.deepcopy(fz.split_manifest)
    dev = next(t for t in sm["templates"] if t["set"] == "DEV")
    train = next(t for t in sm["templates"] if t["set"] == "TRAIN" and t["relation"] == dev["relation"])
    dev["text"] = train["text"].rstrip(".") + "!"                 # same normalized form as a TRAIN template
    over, report = _over(fz, loaded, sm)
    assert {"L1", "L2"} <= over and report["checks"]["L2"]["value"] == 1.0


def _leakage_cli(d, split_manifest, out):
    env = dict(os.environ, PYTHONPATH=str(SRC))
    args = ["--data", d, "--split-manifest", split_manifest, "--out", out]
    return subprocess.run([sys.executable, "-m", "metrix.e1_pilot.check_leakage", *map(str, args)], capture_output=True,
                          text=True, env=env, cwd=PILOT.parents[1])


def test_cli_fail_exit(generated, tmp_path):
    """python -m metrix.e1_pilot.check_leakage (the protocol's command) on data with a planted L4 violation in
    train_F (a file without a frozen hash, so the ST12 range (1) check passes and the leakage check decides)."""
    d = tmp_path / "data"
    shutil.copytree(generated["dir"], d)
    rows = FZ.read_jsonl(d / "train_F.jsonl")
    rows[0]["text"] += " " + FZ.read_jsonl(d / "dev_qa.jsonl")[0]["question"]
    (d / "train_F.jsonl").write_bytes(FZ.jsonl_bytes(rows))
    r = _leakage_cli(d, PILOT / "SPLIT_MANIFEST.json", d / "leakage_report.json")
    assert r.returncode == 1 and r.stdout.rstrip().endswith("RESULT: FAIL"), r.stdout + r.stderr
    report = json.loads((d / "leakage_report.json").read_text(encoding="utf-8"))
    assert report["checks"]["L4"]["value"] == 1 and report["result"] == "FAIL"


def test_cli_bad_split_manifest(generated, tmp_path):
    r = _leakage_cli(generated["dir"], generated["dir"] / "candidates.json", tmp_path / "x.json")
    assert r.returncode != 0 and r.stdout.rstrip().endswith("RESULT: FAIL"), r.stdout + r.stderr
    assert "ST12" in r.stderr and not (tmp_path / "x.json").exists()


def test_cli_st12_on_tampered_frozen_data(generated, tmp_path):
    """A one-byte change of train_S.jsonl (frozen content hash) stops the command with ST12 before any check."""
    d = tmp_path / "data"
    shutil.copytree(generated["dir"], d)
    raw = bytearray((d / "train_S.jsonl").read_bytes())
    i = raw.index(b'"text":"') + len(b'"text":"')
    raw[i] = raw[i] + 1
    (d / "train_S.jsonl").write_bytes(bytes(raw))
    r = _leakage_cli(d, PILOT / "SPLIT_MANIFEST.json", d / "leakage_report.json")
    assert r.returncode != 0 and r.stdout.rstrip().endswith("RESULT: FAIL"), r.stdout + r.stderr
    assert "ST12 -> BLOCKED: train_S: content sha256" in r.stderr
    assert not (d / "leakage_report.json").exists()
