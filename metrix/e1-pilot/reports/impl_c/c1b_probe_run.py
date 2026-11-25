"""Stage C, C1, second submission: one run of the black-box probe (c1b_gate_probe.py) by the Executor, so that the
committed probe is known to work with the committed testgate interface. Builds throw-away repositories with a bare
remote under a temporary directory (outside the repository): the real PROTOCOL_FROZEN, Gate 0 and freeze records, an
ST10 record and a data-auditor count, synthetic TEST rows (not TEST data). Then runs the probe as a subprocess:
  1. the first repository: st10, the ST10 record check (refused: it exists), marker, preconditions, begin (commits and
     pushes a marker), eval at the GPU check, eval with another model (refused), gate twice (claimed, then refused),
     eval again (refused), marker (BLOCKED: started);
  2. a clone of its remote made before begin, now behind the remote: marker BLOCKED (not the latest commit);
  3. a second repository: begin, gate for all 16 models, finish (commits and pushes the result), marker (EVALUATED);
  4. the probe's refusals: this repository, and two throw-away repositories whose origin is the pilot's repository by
     name (CANONICAL_REPO) or a local path to this repository (the second is DEFERRED_MINORS 1.29 CC5, registered:
     the probe does not refuse it; run without operations, so nothing is fetched or pushed).
Prints the probe's output unchanged.
    python metrix/e1-pilot/reports/impl_c/c1b_probe_run.py PYTHON
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
    r = subprocess.run([PY, "-I", str(PILOT / "reports/impl_c/c1b_gate_probe.py"), *args], capture_output=True,
                       text=True)
    print("$ c1b_gate_probe.py %s" % " ".join(args))
    print(r.stdout + r.stderr, end="")
    print("exit=%d" % r.returncode)
    return r.stdout


def make_repo(tmp, name, fz, files):
    """A throw-away repository with a bare remote: PROTOCOL_FROZEN, Gate 0 and freeze records, ST10 record and the
    data-auditor's count, committed and pushed to branch main. Returns (repo, remote, checkpoints)."""
    remote, root = tmp / name / "remote.git", tmp / name / "repo"
    root.mkdir(parents=True)
    git(tmp, "init", "-q", "--bare", "-b", "main", str(remote))
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
    auth = LK.TestAuthorization(fz.record.commit, g0_sha, sel_sha)
    rec = TG.st10_record(fz, auth, {"checks": {c: {"value": 0} for c in LK.TEST_CHECKS}}, files, root)
    write(root, TG.ST10_RECORD_REL, rec)
    write(root, TG.AUDITOR_L6_REL, TG.auditor_count_record(fz, FZ.sha256_hex(files["general_test.jsonl"]), 0))
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "ST10 record and the data-auditor's count")
    git(root, "push", "-q", "origin", "HEAD:refs/heads/main")
    return root, remote, ck


with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    fz = FZ.load()
    test_dir = tmp / "synthetic_test_rows"
    test_dir.mkdir()
    rows = {"test_qa.jsonl": [{"fact_id": "synthetic-0", "template_id": "SYNTHETIC", "question": "Synthetic?"}],
            "general_test.jsonl": [{"domain": "synthetic", "doc_id": "s-0", "ids": [11, 12, 13], "text": "synthetic"}]}
    files = {n: FZ.jsonl_bytes(r) for n, r in rows.items()}
    for n, b in files.items():
        (test_dir / n).write_bytes(b)
    sha = None
    root, remote, ck = make_repo(tmp, "first", fz, files)
    lag = tmp / "first" / "lagging"
    git(tmp, "clone", "-q", str(remote), str(lag))
    for ln in probe(str(root), str(test_dir), "tinysha:0").splitlines():
        if ln.startswith("tinysha:0 ACCEPT "):
            sha = ln.split()[-1]
    probe(str(root), str(test_dir), "st10", "st10rec", "marker", "pre", "begin:%s" % sha, "eval:N:0", "eval:N:7",
          "gate:N:%s" % sha, "gate:N:%s" % sha, "eval:N:0", "marker")
    print("$ git -C <first repo> log --format='%h %s' -3; ls-remote origin")
    print(git(root, "log", "--format=%h %s", "-3"))
    print(git(root, "ls-remote", "origin"))
    probe(str(lag), str(test_dir), "marker")                                   # behind the remote: BLOCKED
    root2, _, ck2 = make_repo(tmp, "second", fz, files)
    models = ["gate:N:%s" % sha] + ["gate:%s:%s" % (n, ck2[n]) for n in sorted(ck2)
                                    if n.startswith(("F-F3-", "L-L2-", "A-A5-", "S-", "Y-"))]
    probe(str(root2), str(test_dir), "begin:%s" % sha, *models, "finish", "marker")
    print("$ git -C <second repo> show --name-only --format='%h %s' HEAD; ls-remote origin")
    print(git(root2, "show", "--name-only", "--format=%h %s", "HEAD"))
    print(git(root2, "ls-remote", "origin"))
    probe(str(PILOT.parents[1]), str(test_dir), "marker")                      # the probe refuses the real repository
    for name, url in (("origin_by_name", "https://github.com/%s.git" % TG.CANONICAL_REPO),
                      ("origin_local_path", str(PILOT.parents[1]))):
        other = tmp / name
        git(tmp, "init", "-q", "-b", "main", str(other))
        git(other, "remote", "add", "origin", url)
        probe(str(other), str(test_dir))                                       # no operation: nothing fetched
