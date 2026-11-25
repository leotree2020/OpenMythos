"""Stage C, C1: one run of the black-box probe (c1_gate_probe.py) by the Executor, so that the committed probe is known
to work with the committed testgate interface (data-auditor C1 round 2). Builds a throw-away repository with a bare
remote under a temporary directory (outside the repository): the real PROTOCOL_FROZEN, Gate 0 and freeze records, an
ST10 record and a data-auditor count, synthetic TEST rows (not TEST data); then runs the probe as a subprocess, twice:
once without --interpretations-ruled (B25 pending: the TEST paths refuse) and once with it (the gates pass; begin
commits and pushes a marker in the throw-away repository; eval reaches the GPU check; gate claims; a second gate and
the marker check refuse). Prints the probe's output unchanged.
    python metrix/e1-pilot/reports/impl_c/c1_probe_run.py PYTHON
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

PILOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PILOT / "src"))

from metrix_e1 import contract as C  # noqa: E402
from metrix_e1 import frozen as FZ  # noqa: E402
from metrix_e1 import leakage as LK  # noqa: E402
from metrix_e1 import mode as M  # noqa: E402
from metrix_e1 import record as R  # noqa: E402
from metrix_e1 import testgate as TG  # noqa: E402
from metrix_e1 import train as T  # noqa: E402

PY = sys.argv[1]
SELECTED = {"F": "F3", "L": "L2", "A": "A5"}


def git(root, *args):
    r = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("git %s: %s" % (args, r.stderr))
    return r.stdout.strip()


def write(root, rel, obj):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    blob = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    p.write_bytes(blob)
    return FZ.sha256_hex(blob)


def probe(*args):
    r = subprocess.run([PY, "-I", str(PILOT / "reports/impl_c/c1_gate_probe.py"), *args], capture_output=True,
                       text=True)
    print("$ c1_gate_probe.py %s" % " ".join(args))
    print(r.stdout + r.stderr, end="")
    print("exit=%d" % r.returncode)


with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    fz = FZ.load()
    remote, root, test_dir = tmp / "remote.git", tmp / "repo", tmp / "synthetic_test_rows"
    git(tmp, "init", "-q", "--bare", "-b", "main", str(remote))
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    for k, v in (("user.name", "metrix-probe"), ("user.email", "metrix-probe@invalid"), ("commit.gpgsign", "false")):
        git(root, "config", k, v)
    git(root, "remote", "add", "origin", str(remote))
    (root / FZ.PROTOCOL_FROZEN_REL).parent.mkdir(parents=True)
    (root / FZ.PROTOCOL_FROZEN_REL).write_bytes((PILOT / "PROTOCOL_FROZEN").read_bytes())
    g0_sha = write(root, R.GATE0_RECORD_REL, R.gate0_record(fz, M.FORMAL_MODE, {"gate0_status": "PASS"}))
    ck = {s.name: "a" * 64 for s in T.training_plan(C.load(fz), SELECTED)}
    sel_sha = write(root, R.SELECTION_FREEZE_REL, R.selection_freeze_record(
        fz, M.FORMAL_MODE, SELECTED, {k: fz.data_hash(k) for k in FZ.CONTENT_HASH_KEYS}, ck, g0_sha))
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "records")
    test_dir.mkdir()
    rows = {"test_qa.jsonl": [{"fact_id": "synthetic-0", "template_id": "SYNTHETIC", "question": "Synthetic?"}],
            "general_test.jsonl": [{"domain": "synthetic", "doc_id": "s-0", "ids": [11, 12, 13], "text": "synthetic"}]}
    files = {n: FZ.jsonl_bytes(r) for n, r in rows.items()}
    for n, b in files.items():
        (test_dir / n).write_bytes(b)
    auth = LK.TestAuthorization(fz.record.commit, g0_sha, sel_sha)
    rec = TG.st10_record(fz, auth, {"checks": {c: {"value": 0} for c in LK.TEST_CHECKS}}, files, root)
    write(root, TG.ST10_RECORD_REL, rec)
    write(root, TG.AUDITOR_L6_REL, TG.auditor_count_record(fz, FZ.sha256_hex(files["general_test.jsonl"]), 0))
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "ST10 record and the data-auditor's count")
    git(root, "push", "-q", "origin", "HEAD:refs/heads/main")
    probe(str(root), str(test_dir), "st10", "marker", "tinysha:0", "begin:%s" % ("b" * 64), "eval:N:0")
    sha = None
    r = subprocess.run([PY, "-I", str(PILOT / "reports/impl_c/c1_gate_probe.py"), "--interpretations-ruled", str(root),
                        str(test_dir), "tinysha:0"], capture_output=True, text=True)
    for ln in r.stdout.splitlines():
        if ln.startswith("tinysha:0 ACCEPT "):
            sha = ln.split()[-1]
    probe("--interpretations-ruled", str(root), str(test_dir), "st10", "marker", "begin:%s" % sha, "eval:N:0",
          "eval:N:7", "gate:N:%s" % sha, "gate:N:%s" % sha, "eval:N:0", "marker")
    print("$ git -C <repo> log --format='%h %s' -3; ls-remote origin")
    print(git(root, "log", "--format=%h %s", "-3"))
    print(git(root, "ls-remote", "origin"))
    probe(str(PILOT.parents[1]), str(test_dir), "marker")                      # the probe refuses the real repository
