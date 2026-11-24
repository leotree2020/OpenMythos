"""Experiment records of METRIX E1-PILOT.

Protocol v1.1 section 10 (record template: one record per run, stopped runs included; no field may be dropped;
compute accounting), section 0 (library versions written into the record; environment and provenance), section 7
(device name), section 8 step 8 (the freeze record of the selected configurations, data hashes and checkpoint
hashes before TEST). The template's field names are read from the frozen protocol text, not written here.

Besides the template fields every record carries an "environment" block: interpreter, library versions (both the
distribution metadata version, which the ST8 check compares, and torch.__version__ with its local build tag:
DEFERRED_MINORS 1.19 AB2), CUDA / cuDNN, device, determinism settings, git state, PROTOCOL_FROZEN (SHA-256 of the
working-tree bytes as read, and of the same bytes with CRLF -> LF: DEFERRED_MINORS 1.20 AC2), the frozen commit and
file hashes, the data hashes, and the open interpretations (interpretations.py).

Formal records go to FORMAL_RESULTS_REL inside the repository; smoke and preflight records carry their label in
every file and are refused there (Implementation Task Order V1, section 7).
"""
import importlib.metadata
import json
import platform
import re
import socket
import subprocess
import sys
from pathlib import Path

import torch

from . import frozen as FZ
from . import interpretations as INT
from .errors import ImplementationFail, ST12Error

FORMAL_RESULTS_REL = FZ.PILOT_REL + "/results"
GATE0_RECORD = "gate0_record.json"
SELECTION_FREEZE_RECORD = "selection_freeze_record.json"
LIBRARIES = ("torch", "transformers", "tokenizers", "huggingface_hub", "safetensors", "numpy", "pyarrow", "jinja2")


def template_fields(protocol_text):
    """The field names of the section 10 template (the code block after '## 10. Experiment Record Template')."""
    m = re.search(r"## 10\. Experiment Record Template\n\n[^\n]*\n\n```\n(.*?)\n```", protocol_text, flags=re.DOTALL)
    if m is None:
        raise ImplementationFail("protocol section 10 template not found")
    fields = []
    for ln in m.group(1).split("\n"):
        f = re.fullmatch(r"([^:]+):", ln)
        if f is None:
            raise ImplementationFail("protocol section 10 template line %r is not 'Field:'" % ln)
        fields.append(f.group(1))
    return fields


def _git(repo_root, *args):
    r = subprocess.run(["git", "-C", str(repo_root), *args], capture_output=True, text=True, check=False)
    return r.stdout.strip() if r.returncode == 0 else None


def library_versions():
    out = {}
    for lib in LIBRARIES:
        try:
            out[lib] = {"metadata": importlib.metadata.version(lib)}
        except importlib.metadata.PackageNotFoundError:
            out[lib] = {"metadata": None}
    out["torch"]["__version__"] = torch.__version__
    import transformers
    out["transformers"]["__version__"] = transformers.__version__
    return out


def environment(fz, device=None, determinism=None, data_hashes=None):
    """The environment and provenance block of a record."""
    pf = (fz.repo_root / FZ.PROTOCOL_FROZEN_REL).read_bytes()
    if FZ.sha256_hex(pf) != fz.record.source_sha256:
        raise ST12Error("PROTOCOL_FROZEN changed after it was loaded (sha256 %s, loaded %s)" % (
            FZ.sha256_hex(pf), fz.record.source_sha256))
    root = fz.repo_root
    env = {
        "python": sys.version, "python_implementation": platform.python_implementation(),
        "platform": platform.platform(), "hostname": socket.gethostname(), "libraries": library_versions(),
        "cuda": {"torch_cuda": torch.version.cuda, "cudnn": torch.backends.cudnn.version(),
                 "available": torch.cuda.is_available()},
        "device": device, "determinism": determinism,
        "git": {"head": _git(root, "rev-parse", "HEAD"), "branch": _git(root, "rev-parse", "--abbrev-ref", "HEAD"),
                "status_porcelain": _git(root, "status", "--porcelain")},
        "protocol_frozen": {"version": fz.record.version, "commit": fz.record.commit,
                            "file_sha256": dict(fz.record.file_sha256), "data_sha256": dict(fz.record.data_sha256),
                            "PROTOCOL_FROZEN_parsed_bytes_sha256": fz.record.source_sha256,
                            "PROTOCOL_FROZEN_working_tree_bytes_sha256": FZ.sha256_hex(pf),
                            "PROTOCOL_FROZEN_lf_normalized_sha256": FZ.sha256_hex(pf.replace(b"\r\n", b"\n"))},
        "data_hashes": data_hashes,
        "interpretations": INT.as_records(),
    }
    env["git"]["dirty"] = bool(env["git"]["status_porcelain"])
    return env


def new_record(fz, mode, experiment_id, values, env):
    """A record with every template field (missing values are an error: the template's fields cannot be dropped)."""
    fields = template_fields(fz.protocol_text)
    missing = [f for f in fields if f not in values]
    extra = [k for k in values if k not in fields]
    if missing or extra:
        raise ImplementationFail("record %s: missing template fields %s, unknown fields %s" % (experiment_id, missing, extra))
    rec = {"label": mode.label, "mode": mode.name, "template": {f: values[f] for f in fields},
           "experiment_id": experiment_id, "environment": env}
    if values["Experiment ID"] != experiment_id:
        raise ImplementationFail("Experiment ID field %r differs from %r" % (values["Experiment ID"], experiment_id))
    return rec


def _is_formal_dir(path, repo_root):
    p = Path(path).resolve()
    formal = (Path(repo_root) / FORMAL_RESULTS_REL).resolve()
    return p == formal or formal in p.parents


def write_record(rec, path, repo_root):
    """Write a record as JSON. A smoke or preflight record (label set) is refused inside the formal results
    directory, and a formal record outside it is refused."""
    path = Path(path)
    formal_dir = _is_formal_dir(path.parent, repo_root)
    if rec["mode"] != "formal" and formal_dir:
        raise ImplementationFail("%s record refused in the formal results directory %s" % (rec["mode"], path.parent))
    if rec["mode"] == "formal" and not formal_dir:
        raise ImplementationFail("formal record must be written under %s, not %s" % (FORMAL_RESULTS_REL, path.parent))
    if rec["mode"] != "formal" and rec.get("label") is None:
        raise ImplementationFail("%s record without its label" % rec["mode"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rec, ensure_ascii=False, indent=1, sort_keys=True, default=str) + "\n", encoding="utf-8")
    return path


def render_text(rec):
    """The record in the order of the protocol template, one 'Field: value' block per field (plain text)."""
    lines = [rec["label"]] if rec.get("label") else []
    for k, v in rec["template"].items():
        lines.append("%s: %s" % (k, v if isinstance(v, str) else json.dumps(v, ensure_ascii=False, default=str)))
    return "\n".join(lines) + "\n"


GATE0_RECORD_REL = FORMAL_RESULTS_REL + "/" + GATE0_RECORD
SELECTION_FREEZE_REL = FORMAL_RESULTS_REL + "/" + SELECTION_FREEZE_RECORD


class NotCommitted(Exception):
    pass


def committed_json(repo_root, rel):
    """(parsed JSON, SHA-256 of the committed bytes) of a file committed at HEAD whose working-tree bytes equal the
    committed blob. Raises NotCommitted otherwise."""
    r = subprocess.run(["git", "-C", str(repo_root), "cat-file", "blob", "HEAD:%s" % rel], capture_output=True, check=False)
    if r.returncode != 0:
        raise NotCommitted("%s is not committed at HEAD" % rel)
    wt = Path(repo_root) / rel
    if not wt.is_file() or wt.read_bytes() != r.stdout:
        raise NotCommitted("%s in the working tree differs from its committed version" % rel)
    try:
        return json.loads(r.stdout), FZ.sha256_hex(r.stdout)
    except ValueError as e:
        raise NotCommitted("%s does not parse: %r" % (rel, e)) from e


def committed_record(repo_root, rel, kind, frozen_commit):
    """(record, sha256) of a committed formal-mode record of `kind` (gate0 / selection_freeze) naming
    `frozen_commit`; raises NotCommitted when the file is not committed as it is in the working tree, or is not
    such a record."""
    rec, sha = committed_json(repo_root, rel)
    if rec.get("kind") != kind or rec.get("mode") != "formal" or rec.get("label") is not None:
        raise NotCommitted("%s is not a formal-mode %s record (kind %r, mode %r)" % (rel, kind, rec.get("kind"), rec.get("mode")))
    if rec.get("frozen_commit") != frozen_commit:
        raise NotCommitted("%s names frozen commit %r, PROTOCOL_FROZEN %s" % (rel, rec.get("frozen_commit"), frozen_commit))
    return rec, sha


def gate0_record(fz, mode, gate0_result):
    """The Gate 0 record (section 8 step 7) whose committed form is precondition 2 of the TEST generator:
    gate0_result is gate.judge's output."""
    return {"kind": "gate0", "mode": mode.name, "label": mode.label, "frozen_commit": fz.record.commit,
            "gate0": gate0_result}


def selection_freeze_record(fz, mode, selected, data_content_hashes, checkpoints, gate0_record_sha256):
    """The freeze record of section 8 step 8 (selected configurations, data hashes, checkpoint hashes), bound to the
    committed Gate 0 record by its SHA-256; its committed form is precondition 3 of the TEST generator."""
    return {"kind": "selection_freeze", "mode": mode.name, "label": mode.label, "frozen_commit": fz.record.commit,
            "selected": dict(selected), "data_content_hashes": dict(data_content_hashes), "checkpoints": dict(checkpoints),
            "gate0_record_sha256": gate0_record_sha256}


# The content checks of the two committed records, shared by the TEST generator (test_data.check_gate0_record,
# check_selection_record) and by every TEST path (leakage.verify_authorization), so both check the same things.

def gate0_record_problem(rec):
    """None if the Gate 0 record's status is PASS (condition 2 of the TEST generator), else the reason."""
    status = (rec.get("gate0") or {}).get("gate0_status")
    return None if status == "PASS" else "Gate 0 status %r, not PASS" % (status,)


def freeze_record_problem(rec, contract, content_hashes, gate0_sha):
    """None if the content of a freeze record meets condition 3 of the TEST generator, else the first reason:
    selected F, L, A configurations of SEARCH_SPACE.json that form the training plan (train.training_plan); data
    content hashes equal to `content_hashes`; a 64-hex checkpoint hash for every one of the 30 runs of the plan;
    bound to the Gate 0 record whose SHA-256 is `gate0_sha`."""
    from .train import training_plan
    selected = rec.get("selected") or {}
    try:
        plan = training_plan(contract, selected)
    except (ValueError, KeyError, AttributeError) as e:
        return "selected configurations %r are not configurations of SEARCH_SPACE.json (%s)" % (selected, e)
    if rec.get("data_content_hashes") != content_hashes:
        return "data content hashes %r differ from %r" % (rec.get("data_content_hashes"), content_hashes)
    ck = rec.get("checkpoints") or {}
    missing = [s.name for s in plan if not isinstance(ck.get(s.name), str) or not FZ.HEX64.fullmatch(ck[s.name])]
    if missing:
        return "no checkpoint hash for %d of the %d runs (first %s)" % (len(missing), len(plan), missing[0])
    if rec.get("gate0_record_sha256") != gate0_sha:
        return "not bound to the committed Gate 0 record (sha256 %r, committed %s)" % (rec.get("gate0_record_sha256"),
                                                                                       gate0_sha)
    return None
