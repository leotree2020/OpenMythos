"""metrix_e1.record (protocol v1.1 section 10; Implementation Task Order V1 section 7): every template field, read from
the frozen protocol; no field can be dropped; library versions with and without the local build tag; PROTOCOL_FROZEN
hashed as read and LF-normalized; smoke records labelled and kept out of the formal results directory."""
import json

import pytest

from metrix_e1 import mode as M
from metrix_e1 import record as R
from metrix_e1.errors import ImplementationFail


def _values(fields, eid="E1P-TEST-RECORD"):
    v = {f: "x" for f in fields}
    v["Experiment ID"] = eid
    return v


def test_template_fields_from_the_protocol(fz):
    fields = R.template_fields(fz.protocol_text)
    assert fields[0] == "Experiment ID" and fields[-1] == "Next (single)" and len(fields) == 20
    assert "Compute accounting (tokens / steps / FLOPs / wall-clock)" in fields


def test_no_field_can_be_dropped(fz):
    fields = R.template_fields(fz.protocol_text)
    env = {}
    v = _values(fields)
    del v["Non-claims"]
    with pytest.raises(ImplementationFail):
        R.new_record(fz, M.FORMAL_MODE, "E1P-TEST-RECORD", v, env)
    with pytest.raises(ImplementationFail):
        R.new_record(fz, M.FORMAL_MODE, "E1P-TEST-RECORD", dict(_values(fields), Extra="y"), env)
    rec = R.new_record(fz, M.FORMAL_MODE, "E1P-TEST-RECORD", _values(fields), env)
    assert list(rec["template"]) == fields and rec["label"] is None


def test_smoke_records_are_labelled_and_kept_apart(fz, tmp_path):
    fields = R.template_fields(fz.protocol_text)
    smoke = R.new_record(fz, M.smoke_mode(3), "E1P-SMOKE", _values(fields, "E1P-SMOKE"), {})
    formal = R.new_record(fz, M.FORMAL_MODE, "E1P-F", _values(fields, "E1P-F"), {})
    assert smoke["label"] == M.SMOKE_LABEL == "SMOKE — NOT A RESULT"
    with pytest.raises(ImplementationFail):                       # smoke into the formal results directory
        R.write_record(smoke, fz.repo_root / R.FORMAL_RESULTS_REL / "x.json", fz.repo_root)
    with pytest.raises(ImplementationFail):                       # formal outside it
        R.write_record(formal, tmp_path / "x.json", fz.repo_root)
    p = R.write_record(smoke, tmp_path / "smoke" / "x.json", fz.repo_root)
    assert json.loads(p.read_text(encoding="utf-8"))["label"] == "SMOKE — NOT A RESULT"
    assert R.render_text(smoke).split("\n")[0] == "SMOKE — NOT A RESULT"
    assert not (fz.repo_root / R.FORMAL_RESULTS_REL).exists()


def test_environment_block(fz):
    env = R.environment(fz)
    libs = env["libraries"]
    assert libs["torch"]["metadata"] == "2.11.0" and libs["torch"]["__version__"].startswith("2.11.0")
    assert libs["transformers"]["metadata"] == libs["transformers"]["__version__"] == "5.22.2"
    pf = env["protocol_frozen"]
    raw = (fz.repo_root / "metrix/e1-pilot/PROTOCOL_FROZEN").read_bytes()
    import hashlib
    assert pf["PROTOCOL_FROZEN_working_tree_bytes_sha256"] == hashlib.sha256(raw).hexdigest()
    assert pf["PROTOCOL_FROZEN_lf_normalized_sha256"] == hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()
    assert pf["commit"] == fz.record.commit and len(pf["data_sha256"]) == 12
    assert env["git"]["head"] and isinstance(env["git"]["dirty"], bool)
    assert [e["id"] for e in env["interpretations"]] == ["B%d" % i for i in range(1, len(env["interpretations"]) + 1)]


def test_record_constructors_and_committed_json(fz, tmp_path):
    import subprocess
    g = R.gate0_record(fz, M.FORMAL_MODE, {"gate0_status": "PIPELINE_NOT_QUALIFIED"})
    assert (g["kind"], g["mode"], g["label"], g["frozen_commit"]) == ("gate0", "formal", None, fz.record.commit)
    s = R.selection_freeze_record(fz, M.smoke_mode(3), {"F": "F1"}, {"facts": "x"}, {"r": "y"}, "z")
    assert s["kind"] == "selection_freeze" and s["label"] == M.SMOKE_LABEL and s["gate0_record_sha256"] == "z"
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)
    (root / "a.json").write_text(json.dumps(g), encoding="utf-8")
    with pytest.raises(R.NotCommitted):
        R.committed_json(root, "a.json")
    subprocess.run(["git", "-C", str(root), "add", "a.json"], check=True)
    subprocess.run(["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@invalid", "-c", "commit.gpgsign=false",
                    "commit", "-q", "-m", "r"], check=True)
    obj, sha = R.committed_json(root, "a.json")
    assert obj == g
    (root / "a.json").write_text("{}", encoding="utf-8")
    with pytest.raises(R.NotCommitted):
        R.committed_json(root, "a.json")


def test_environment_records_the_parsed_protocol_frozen(fz):
    pf = R.environment(fz)["protocol_frozen"]
    assert pf["PROTOCOL_FROZEN_parsed_bytes_sha256"] == fz.record.source_sha256
    import dataclasses
    from metrix_e1.errors import ST12Error
    changed = dataclasses.replace(fz, record=dataclasses.replace(fz.record, source_sha256="0" * 64))
    with pytest.raises(ST12Error):                                  # PROTOCOL_FROZEN differs from what was loaded
        R.environment(changed)
