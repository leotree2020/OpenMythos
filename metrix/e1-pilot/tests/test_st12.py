"""Implementation Task Order V1, section 6 item 10: change one byte of any frozen file or data file and the run
stops at once with ST12 (protocol v1.1 section 11; Task Order section 3 items 1-2).

Covered, each with the message of the check that must fire:
  - the four frozen files at the frozen commit (range (2)): a one-byte change in the commit named by PROTOCOL_FROZEN;
  - the working-tree copies of the four frozen files (beyond range (2), see frozen.py);
  - PROTOCOL_FROZEN: one hex digit of a listed file hash, and of a value of the data-hash table (the prose of
    PROTOCOL_FROZEN is not covered: a byte changed there and nowhere else changes no value the run uses);
  - the input files with frozen file-byte hashes (range (1)): eval_sets.jsonl, the four Qwen tokenizer files, the
    parcae tokenizer.json, the anchor parquet;
  - the eight generated data files: the four with frozen content hashes (range (1)) and the four without one
    (regeneration check of data.verify).
Frozen files are tampered inside a throw-away git repository built in a temporary directory from the bytes of the real
frozen commit, so the real repository is never touched. Input files and data files are tampered in temporary copies.
"""
import json
import os
import shutil
import subprocess
import sys

import pytest

from metrix_e1 import data as D
from metrix_e1 import frozen as FZ
from metrix_e1.errors import ST12Error

from conftest import PILOT, SRC

GIT_ID = ["-c", "user.name=metrix-test", "-c", "user.email=metrix-test@invalid", "-c", "commit.gpgsign=false"]


def flip(path, pos=None):
    """Change one byte of a file (the middle byte by default) to a different value; return the position."""
    b = bytearray(path.read_bytes())
    pos = len(b) // 2 if pos is None else pos
    b[pos] = b[pos] + 1 if b[pos] < 0x7e else b[pos] - 1
    path.write_bytes(bytes(b))
    return pos


def value_byte(path):
    """Position of a byte inside a JSON string value (first character of the "protocol" value)."""
    return path.read_bytes().index(b'"METRIX-E1-PILOT"') + 1


def git(repo, *args):
    r = subprocess.run(["git", "-C", str(repo), *GIT_ID, *args], capture_output=True, text=True, check=True)
    return r.stdout.strip()


@pytest.fixture
def mini_repo(fz, tmp_path):
    """A git repository holding the four frozen files (bytes of the real frozen commit) in one commit, the real
    eval_sets.jsonl in the working tree, and a PROTOCOL_FROZEN whose frozen commit is the mini repository's commit
    (every listed hash unchanged). Returns (root, commit, protocol_frozen_text)."""
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q")
    for rel in FZ.FROZEN_FILES:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_bytes(fz.blobs[rel])
    git(root, "add", ".")
    git(root, "commit", "-q", "-m", "frozen files")
    commit = git(root, "rev-parse", "HEAD")
    src = (fz.repo_root / FZ.PROTOCOL_FROZEN_REL).read_text(encoding="utf-8")
    assert src.count(fz.record.commit) >= 1
    text = src.replace(fz.record.commit, commit)
    (root / FZ.PROTOCOL_FROZEN_REL).write_text(text, encoding="utf-8")
    ev = D.params(fz).general_source
    (root / ev).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(fz.repo_root / ev, root / ev)
    return root, commit, text


def test_mini_repo_positive_control(mini_repo):
    root, commit, _ = mini_repo
    assert FZ.load(repo_root=root).record.commit == commit


@pytest.mark.parametrize("rel", FZ.FROZEN_FILES)
def test_frozen_commit_file_one_byte(mini_repo, rel):
    """Range (2): the file at the commit named by PROTOCOL_FROZEN differs by one byte from the listed hash."""
    root, commit, text = mini_repo
    flip(root / rel)
    git(root, "commit", "-q", "-am", "one byte changed")
    tampered = git(root, "rev-parse", "HEAD")
    (root / FZ.PROTOCOL_FROZEN_REL).write_text(text.replace(commit, tampered), encoding="utf-8")
    with pytest.raises(ST12Error, match="ST12 -> BLOCKED: %s at the frozen commit %s has sha256" % (rel, tampered)):
        FZ.load(repo_root=root)


@pytest.mark.parametrize("rel", FZ.FROZEN_FILES)
def test_working_tree_file_one_byte(mini_repo, rel):
    """The working-tree copy differs by one byte from the frozen commit (JSON: a byte inside a string value)."""
    root, _, _ = mini_repo
    path = root / rel
    flip(path, value_byte(path) if rel.endswith(".json") else None)
    with pytest.raises(ST12Error, match="ST12 -> BLOCKED: working-tree %s differs from the frozen commit" % rel):
        FZ.load(repo_root=root)


def test_working_tree_line_endings_and_step1_fields(mini_repo, fz):
    """Not a change: CRLF line endings of a checkout (PROTOCOL_FROZEN: git cat-file is authoritative), and the
    fields protocol section 8 step 1 writes (ST12 leaves them out), including new keys in them."""
    root, _, _ = mini_repo
    for rel in (FZ.PROTOCOL_REL, FZ.SEARCH_SPACE_REL):
        (root / rel).write_bytes(fz.blobs[rel].replace(b"\n", b"\r\n"))
    dm = json.loads(fz.blobs[FZ.DATA_MANIFEST_REL])
    dm["files"]["facts.jsonl"].update(status="GENERATED", byte_sha256="0" * 64, canonical_sha256="0" * 64)
    dm["files"]["facts.jsonl"]["rows"] = 160
    (root / FZ.DATA_MANIFEST_REL).write_text(json.dumps(dm, ensure_ascii=False, indent=2), encoding="utf-8")
    sm = json.loads(fz.blobs[FZ.SPLIT_MANIFEST_REL])
    sm["split_sha256"]["train_F.jsonl"] = "0" * 64
    sm["split_sha256"]["extra.jsonl"] = "0" * 64
    (root / FZ.SPLIT_MANIFEST_REL).write_text(json.dumps(sm, ensure_ascii=False, indent=2), encoding="utf-8")
    FZ.load(repo_root=root)


@pytest.mark.parametrize("which", ["file", "data"])
def test_protocol_frozen_hash_one_byte(mini_repo, fz, which):
    """One hex digit of a hash listed in PROTOCOL_FROZEN changed: a file hash of the current section (no longer the
    hash of the frozen-commit blob), or a value of the data-hash table (no longer the frozen-commit manifest value)."""
    root, commit, text = mini_repo
    sha = fz.record.file_sha256[FZ.DATA_MANIFEST_REL] if which == "file" else fz.data_hash("facts")
    assert text.count(sha) == 1
    other = sha[:10] + ("0" if sha[10] != "0" else "1") + sha[11:]
    (root / FZ.PROTOCOL_FROZEN_REL).write_text(text.replace(sha, other), encoding="utf-8")
    expected = ("%s at the frozen commit %s has sha256 %s, PROTOCOL_FROZEN %s" % (FZ.DATA_MANIFEST_REL, commit, sha, other)
                if which == "file" else "PROTOCOL_FROZEN row 'fact\\(160 条\\)' \\(%s\\) differs from" % other)
    with pytest.raises(ST12Error, match=expected):
        FZ.load(repo_root=root)


def test_eval_sets_one_byte(mini_repo, inputs_dir):
    root, _, _ = mini_repo
    fzm = FZ.load(repo_root=root)
    p = D.params(fzm)
    D.check_inputs(fzm, p, inputs_dir)                           # positive control
    flip(root / p.general_source)
    with pytest.raises(ST12Error, match="ST12 -> BLOCKED: eval_sets: file .* has sha256"):
        D.check_inputs(fzm, p, inputs_dir)


@pytest.fixture
def inputs_copy(fz, inputs_dir, tmp_path):
    dst = tmp_path / "inputs"
    for path in D.input_paths(D.params(fz), inputs_dir).values():
        target = dst / path.relative_to(inputs_dir)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    return dst


@pytest.mark.parametrize("key", ["qwen:tokenizer.json", "qwen:tokenizer_config.json", "qwen:vocab.json",
                                 "qwen:merges.txt", "parcae_tokenizer", "anchor_parquet"])
def test_input_file_one_byte(fz, inputs_copy, key, generated):
    p = D.params(fz)
    D.check_inputs(fz, p, inputs_copy)                            # positive control
    flip(D.input_paths(p, inputs_copy)[key])
    expected = "ST12 -> BLOCKED: %s: file .* has sha256" % key
    with pytest.raises(ST12Error, match=expected):
        D.check_inputs(fz, p, inputs_copy)
    with pytest.raises(ST12Error, match=expected):
        D.verify(fz, inputs_copy, generated["dir"])


@pytest.fixture
def data_copy(generated, tmp_path):
    dst = tmp_path / "data"
    shutil.copytree(generated["dir"], dst)
    return dst


# the check that must fire for a one-byte change of each data file (middle byte)
DATA_FILE_MESSAGE = {
    "facts.jsonl": "facts: content sha256|cannot read the generated data",
    "train_S.jsonl": "train_S: content sha256|cannot read the generated data",
    "candidates.json": "candidates: content sha256|cannot read the generated data",
    "anchor_text.jsonl": "anchor_texts: content sha256|cannot read the generated data|anchor_text.jsonl in .* differs",
    "train_F.jsonl": "train_F.jsonl in .* differs from its regeneration",
    "train_Y.jsonl": "train_Y.jsonl in .* differs from its regeneration",
    "dev_qa.jsonl": "dev_qa.jsonl in .* differs from its regeneration",
    "general_dev.jsonl": "general_dev.jsonl in .* differs from its regeneration",
}


def test_data_file_message_table_complete():
    assert sorted(DATA_FILE_MESSAGE) == sorted(D.DATA_FILES)


@pytest.mark.parametrize("name", D.DATA_FILES)
def test_data_file_one_byte(fz, inputs_dir, data_copy, name):
    flip(data_copy / name)
    with pytest.raises(ST12Error, match="ST12 -> BLOCKED: (%s)" % DATA_FILE_MESSAGE[name]):
        D.verify(fz, inputs_dir, data_copy)


def test_verify_positive_control(fz, inputs_dir, generated):
    assert D.verify(fz, inputs_dir, generated["dir"]) == fz.check_data_dir(generated["dir"])


def _cli(*args):
    env = dict(os.environ, PYTHONPATH=str(SRC))
    return subprocess.run([sys.executable, "-m", "metrix_e1.data", *map(str, args)], capture_output=True, text=True,
                          env=env, cwd=PILOT)


def test_cli_stops_on_tampered_data(inputs_dir, data_copy):
    """At the command level: `data verify` prints RESULT: FAIL and exits non-zero after a one-byte change."""
    ok = _cli("verify", "--inputs", inputs_dir, "--data", data_copy)
    assert ok.returncode == 0 and ok.stdout.rstrip().endswith("RESULT: PASS"), ok.stdout + ok.stderr
    flip(data_copy / "dev_qa.jsonl")
    bad = _cli("verify", "--inputs", inputs_dir, "--data", data_copy)
    assert bad.returncode != 0 and bad.stdout.rstrip().endswith("RESULT: FAIL"), bad.stdout + bad.stderr
    assert "ST12 -> BLOCKED: dev_qa.jsonl in" in bad.stderr


def test_cli_stops_on_tampered_input(inputs_copy, generated):
    flip(inputs_copy / "qwen_tokenizer" / "tokenizer_config.json")
    bad = _cli("verify", "--inputs", inputs_copy, "--data", generated["dir"])
    assert bad.returncode != 0 and bad.stdout.rstrip().endswith("RESULT: FAIL"), bad.stdout + bad.stderr
    assert "ST12 -> BLOCKED: qwen:tokenizer_config.json: file" in bad.stderr


def test_parse_jsonl_splits_on_newline_only():
    """Review MINOR: JSONL is split on b"\\n" only; U+2028 / U+0085 inside a value (unescaped by
    json.dumps(ensure_ascii=False)) do not break a line."""
    rows = [{"text": "a b\u0085c"}, {"text": "d"}]
    assert FZ.parse_jsonl(FZ.jsonl_bytes(rows)) == rows
    with pytest.raises(ValueError):
        FZ.parse_jsonl(FZ.jsonl_bytes(rows)[:-1])
