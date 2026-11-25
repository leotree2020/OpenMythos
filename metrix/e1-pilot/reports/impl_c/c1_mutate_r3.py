"""Stage C, C1, round 3 (after the round-2 reviews): mutation check of the TEST gates and the BE fixes. Each mutation
removes or weakens one check in the working tree, runs the named tests and restores the file (byte-for-byte, checked).
A mutation is "caught" when the named tests fail. The scripts of rounds 1 and 2 (c1_mutate.py, c1_mutate_r2.py) are kept
as they ran (c1_02, c1_03, c1_04).
Run from the repository root:
    METRIX_INPUTS_DIR=DIR python metrix/e1-pilot/reports/impl_c/c1_mutate_r3.py PYTHON
Prints one line per mutation and, at the end, the sha256 of src/ and tests/ before and after (must be equal).
"""
import hashlib
import subprocess
import sys
from pathlib import Path

PY = sys.argv[1]
S = Path("metrix/e1-pilot/src/metrix_e1")
G = S / "testgate.py"
TG, TT, TE, TS, TH = ("tests/test_testgate.py", "tests/test_test_data.py", "tests/test_evaluate.py",
                      "tests/test_stops.py", "tests/test_data_hashes.py")
MUTS = [
    # st10_check
    ("st10: authorization binding", G, 'if rec.get("authorization") != auth_fields(authorization):', 'if False:', TG),
    ("st10: record frozen commit", G, 'if rec.get("frozen_commit") != authorization.frozen_commit:', 'if False:', TG),
    ("st10: record kind/mode", G,
     'if rec.get("kind") != "st10" or rec.get("mode") != "formal" or rec.get("label") is not None:', 'if False:', TG),
    ("st10: TEST file hashes", G, "    if files != rows_hashes:\n", "    if False:\n", TG),
    ("st10: code commit ancestor", G, "    if not _is_ancestor(root, cc):\n", "    if False:\n", TG),
    ("st10: ancestor test always true", G, '_git(root, "merge-base", "--is-ancestor", commit, "HEAD").returncode == 0)',
     '_git(root, "merge-base", "--is-ancestor", commit, "HEAD").returncode >= 0)', TG),
    ("st10: counts are integers", G, "    if not _counts_ok(counts):\n", "    if False:\n", TG),
    ("st10: auditor kind/commit", G,
     'if aud.get("kind") != "st10_auditor_l6" or aud.get("frozen_commit") != authorization.frozen_commit:', 'if False:', TG),
    ("st10: auditor counted the same file", G, 'if aud.get("general_test_sha256") != files["general_test.jsonl"]:',
     'if False:', TG),
    ("st10: auditor count is an integer", G, 'if not _count(aud.get("l6_test_count")):', 'if False:', TG),
    ("st10: auditor count replaced by Executor's", G, 'STP.st10(fz, counts, test_limits(fz), aud["l6_test_count"])',
     'STP.st10(fz, counts, test_limits(fz), counts["L6"])', TG),
    ("stops.st10: no over-limit judgement", S / "stops.py",
     "    over = sorted(c for c, v in counts.items() if v > limits[c])", "    over = []", TS + " " + TG),
    # ST10 record
    ("record: counts read from flags", G, 'counts = {c: report["checks"][c]["value"] for c in LK.TEST_CHECKS}',
     'counts = {c: 0 if report["checks"][c].get("within_limit") else 1 for c in LK.TEST_CHECKS}', TG),
    ("record: no integer check", G, '    if bad:\n        raise ImplementationFail("TEST part counts',
     '    if False:\n        raise ImplementationFail("TEST part counts', TG),
    ("record: code paths not checked", G, "    if st.stdout.strip():\n", "    if False:\n", TG),
    ("record: overwrite allowed", G, '    if path.exists():\n        raise ImplementationFail("%s exists',
     '    if False:\n        raise ImplementationFail("%s exists', TG),
    ("st10 record: history not searched", G,
     'where = _where(root, ST10_RECORD_REL, ["--all", "--reflog"] + remote_heads(root, remote))',
     'where = ["working tree"] if (root / ST10_RECORD_REL).exists() else []', TG),
    ("st10 record: remote not searched", G,
     'where = _where(root, ST10_RECORD_REL, ["--all", "--reflog"] + remote_heads(root, remote))',
     'where = _where(root, ST10_RECORD_REL, ["--all", "--reflog"])', TG),
    # history and remote search
    ("history: simplified (no --full-history)", G, '"log", "--full-history", *revs,', '"log", *revs,', TG),
    ("marker: working tree ignored", G, '    return (["working tree"] if (Path(root) / rel).exists() else []) + [',
     '    return [] + [', TG),
    ("marker: HEAD only, not --all", G, '    revs = ["--all", "--reflog"] + remote_heads(root, remote)\n    where, result',
     '    revs = ["HEAD", "--reflog"] + remote_heads(root, remote)\n    where, result', TG),
    ("marker: reflog not searched", G, '    revs = ["--all", "--reflog"] + remote_heads(root, remote)\n    where, result',
     '    revs = ["--all"] + remote_heads(root, remote)\n    where, result', TG),
    ("marker: remote branches not searched", G,
     '    revs = ["--all", "--reflog"] + remote_heads(root, remote)\n    where, result',
     '    revs = ["--all", "--reflog"]\n    where, result', TG),
    ("remote: another repository accepted", G, "    if got != CANONICAL_REPO:\n", "    if False:\n", TG),
    ("remote: another branch accepted", G, "        if branch != PILOT_BRANCH:\n", "        if False:\n", TG),
    ("remote: checked-out branch not checked", G, "        if local != PILOT_BRANCH:\n", "        if False:\n", TG),
    ("remote: shallow clone accepted", G,
     '    if _git(root, "rev-parse", "--is-shallow-repository").stdout.strip() == "true":', "    if False:", TG),
    ("remote: no check before listing", G, "        return []\n    check_remote(root, remote)\n",
     "        return []\n", TG),
    ("commit_paths: no remote check", G, "    root = Path(repo_root)\n    check_remote(root, remote, branch)\n",
     "    root = Path(repo_root)\n", TG),
    ("credentials: not scrubbed", G, '    return _USERINFO.sub(r"\\1", text)', "    return text", TG),
    ("remote: only the tips' refs, nothing fetched", G,
     '    f = _git(root, "fetch", "-q", "--no-tags", remote, *[ref for _, ref in heads])',
     '    f = _git(root, "rev-parse", "HEAD")', TG),
    ("marker: result ignored", G, "    if result:\n", "    if False:\n", TG),
    ("begin: no marker check", G, "    refuse_if_marker(root, remote)\n", "    pass\n", TG),
    ("begin: staged changes allowed", G,
     '    if _git(root, "diff", "--cached", "--quiet").returncode != 0:\n        raise _blocked("the git index holds staged '
     'changes; the marker', '    if False:\n        raise _blocked("the git index holds staged changes; the marker', TG),
    ("begin: no identity check", G, '    if _git(root, "var", "GIT_COMMITTER_IDENT").returncode != 0:', '    if False:', TG),
    ("begin: no fast-forward precheck", G, "    if tip and not _is_ancestor(root, tip[0]):", "    if False:", TG),
    ("begin: no ST10 gate", G, "    st10_sha, aud_sha = st10_check(fz, authorization, rows_hashes, root)\n    if not isinstance",
     "    st10_sha, aud_sha = None, None\n    if not isinstance", TG),
    ("commit_paths: staged paths not checked", G, "    if add.returncode != 0 or staged != sorted(rels):",
     "    if add.returncode != 0:", TG),
    ("commit_paths: commit failure ignored", G, "    c = _git(root, \"commit\", \"-q\", \"-m\", message)\n    if c.returncode != 0:",
     "    c = _git(root, \"commit\", \"-q\", \"-m\", message)\n    if False:", TG),
    ("push: remote ref not checked", G, 'if r.returncode == 0 and ls.returncode == 0 and ls.stdout.split()[:1] == [head]:',
     'if True:', TG),
    ("push: tags followed", G, '"push", "--no-follow-tags", remote, "HEAD:refs/heads/%s" % branch)\n        ls',
     '"push", "--follow-tags", remote, "HEAD:refs/heads/%s" % branch)\n        ls', TG),
    # require_test_session / claim / finish
    ("session: not checked against this process", G,
     "    if not isinstance(session, TestSession) or _LIVE.get(session.session_id) is not session:\n        raise _refuse(\"no TEST "
     "session of this process (begin_test_evaluation)\")\n    marker, sha",
     "    if not isinstance(session, TestSession):\n        raise _refuse(\"no TEST session of this process "
     "(begin_test_evaluation)\")\n    marker, sha", TG),
    ("session: marker bytes not checked", G, "    if sha != session.marker_sha256:                   # the bytes",
     "    if False:                   # the bytes", TG),
    ("session: marker bound to the authorization", G,
     "    if (marker.get(\"frozen_commit\") != authorization.frozen_commit\n            or marker.get(\"authorization\") != "
     "auth_fields(authorization)):", "    if False:", TG),
    ("session: rows not checked against marker", G, '    if marker.get("test_files_sha256") != rows_hashes:\n',
     '    if False:\n', TG),
    ("session: ST10 change after marker allowed", G,
     'if (st10_sha, aud_sha) != (marker.get("st10_record_sha256"), marker.get("auditor_count_sha256")):', 'if False:', TG),
    ("session: any model name", G, '    if checkpoint_name not in marker["models"]:\n', "    if False:\n", TG),
    ("session: model hash not checked", G, '    if got != marker["checkpoints"][checkpoint_name]:\n', "    if False:\n", TG),
    ("claim: a model twice", G, "    if checkpoint_name in session.evaluated:\n        raise _refuse(\"%s was already evaluated on "
     "TEST in this session\" % checkpoint_name)\n    session.evaluated.add",
     "    if False:\n        raise _refuse(\"%s was already evaluated on TEST in this session\" % checkpoint_name)\n    "
     "session.evaluated.add", TG),
    ("claim: any session", G, '''    if _LIVE.get(getattr(session, "session_id", None)) is not session:
        raise _refuse("no TEST session of this process (begin_test_evaluation)")
    if checkpoint_name in session.evaluated:''', '''    if False:
        raise _refuse("no TEST session of this process (begin_test_evaluation)")
    if checkpoint_name in session.evaluated:''', TG),
    ("finish: models left allowed", G, "    if left:\n", "    if False:\n", TG),
    ("finish: staged changes allowed", G,
     '    if _git(root, "diff", "--cached", "--quiet").returncode != 0:\n        raise _blocked("the git index holds staged changes; '
     'the result', '    if False:\n        raise _blocked("the git index holds staged changes; the result', TG),
    ("evaluate_model: no TEST session gate", S / "evaluate.py",
     "        TG.require_test_session(fz, test_authorization, test_session, checkpoint_name, data, model)", "        pass", TG),
    ("evaluate_model: claim before the GPU check", S / "evaluate.py",
     '''        require_gpu(mode, device)
        TG.claim_checkpoint(test_session, checkpoint_name)''', '''        TG.claim_checkpoint(test_session, checkpoint_name)
        require_gpu(mode, device)''', TG),
    ("evaluate_model: claim removed", S / "evaluate.py", "        TG.claim_checkpoint(test_session, checkpoint_name)\n",
     "", TG),
    ("finish: marker bytes not checked", G,
     '    if sha != session.marker_sha256 or not isinstance(marker.get("models"), list):',
     '    if not isinstance(marker.get("models"), list):', TG),
    ("record.committed_json: no object check", S / "record.py", "    if not isinstance(obj, dict):\n", "    if False:\n",
     TT + " " + TG),
    # TEST driver
    ("driver: --out inside the repository allowed", S / "test_data.py",
     "    if out.resolve() == root or root in out.resolve().parents:", "    if False:", TG),
    ("driver: verdict from the report's flags", S / "test_data.py", '    over = TG.over_limit(fz, rec["counts"])',
     '    over = sorted(c for c, v in report["checks"].items() if not v["within_limit"])', TG),
    ("driver: ST10 record existence not checked", S / "test_data.py", "    TG.refuse_if_st10_record(root, TG.PILOT_REMOTE)\n",
     "", TG),
    ("driver: ST10 record not committed and pushed", S / "test_data.py",
     '    head = TG.commit_paths(root, [TG.ST10_RECORD_REL],', '    head = "-" or TG.commit_paths(root, [TG.ST10_RECORD_REL],',
     TG),
    ("driver: code checked only after generation", S / "test_data.py",
     "    TG.code_commit(root)                                # the code that generates TEST is committed (ST10 record)\n",
     "", TG),
    # BE2, BE9, BE10, interpretations, B14
    ("BE2: PROTOCOL_FROZEN vs fz removed", S / "leakage.py", "    if current != fz.record.commit:\n", "    if False:\n", TT),
    ("BE2: authorization vs PROTOCOL_FROZEN removed", S / "leakage.py", "    if authorization.frozen_commit != current:",
     "    if False:", TT),
    ("BE9: pending_problem always None", S / "interpretations.py", "    if open_ids:\n        return \"interpretations",
     "    if False:\n        return \"interpretations", TT),
    ("BE9: content hashes from a literal key list", S / "frozen.py",
     "for key in CONTENT_HASH_KEYS}    # DEFERRED_MINORS BE9",
     'for key in ("facts", "train_S", "candidates", "anchor_texts")}', TH),
    ("BE10: fz is None check removed", S / "evaluate.py", "        if fz is None:\n", "        if False:\n", TE),
    ("B14: note changed", S / "gate.py", 'RECALIBRATION_NOTE = "需重新校准"', 'RECALIBRATION_NOTE = "recalibrate"',
     "tests/test_gate.py"),
    ("ruling: one entry pending", S / "interpretations.py", '{"id": "B7", "status": ACCEPTED,', '{"id": "B7",', TT),
    ("ruling: B25 marked accepted", S / "interpretations.py", '{"id": "B25", "where"', '{"id": "B25", "status": ACCEPTED, "where"',
     TT),
]


def tree_sha():
    h = hashlib.sha256()
    for p in sorted(Path("metrix/e1-pilot/src").rglob("*.py")) + sorted(Path("metrix/e1-pilot/tests").rglob("*.py")):
        h.update(str(p).encode() + b"\0" + p.read_bytes())
    return h.hexdigest()


before = tree_sha()
caught = 0
for name, path, old, new, tests in MUTS:
    orig = path.read_bytes()
    s = orig.decode("utf-8")
    if s.count(old) != 1:
        print("%-48s -> MUTATION NOT APPLICABLE (%d matches)" % (name, s.count(old)))
        continue
    path.write_text(s.replace(old, new), encoding="utf-8")
    try:
        r = subprocess.run([PY, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider"] +
                           ["metrix/e1-pilot/" + t for t in tests.split()], capture_output=True, text=True)
        last = r.stdout.strip().split("\n")[-1]
        failed = [ln for ln in r.stdout.split("\n") if ln.startswith("FAILED")]
        caught += r.returncode != 0
        print("%-48s -> %s exit %d | %s" % (name, "CAUGHT" if r.returncode else "NOT CAUGHT", r.returncode, last))
        for ln in failed[:2]:
            print("      ", ln[:170])
    finally:
        path.write_bytes(orig)
after = tree_sha()
print("mutations %d, caught %d" % (len(MUTS), caught))
print("src+tests sha256 before %s after %s %s" % (before, after, "EQUAL" if before == after else "DIFFERENT"))
print("RESULT: %s" % ("PASS" if caught == len(MUTS) and before == after else "FAIL"))
