"""Stage C, C1: mutation check of the TEST gates and the BE fixes. Each mutation removes or weakens one check in the
working tree, runs the named tests and restores the file (byte-for-byte, checked). A mutation is "caught" when the
named tests fail. Run from the repository root:
    METRIX_INPUTS_DIR=DIR python metrix/e1-pilot/reports/impl_c/c1_mutate.py PYTHON
Prints one line per mutation and, at the end, the sha256 of src/ and tests/ before and after (must be equal).
"""
import hashlib
import subprocess
import sys
from pathlib import Path

PY = sys.argv[1]
S = Path("metrix/e1-pilot/src/metrix_e1")
TG, TT, TD, TE, TS, TH = ("tests/test_testgate.py", "tests/test_test_data.py", "tests/test_test_data.py",
                          "tests/test_evaluate.py", "tests/test_stops.py", "tests/test_data_hashes.py")
MUTS = [
    # testgate.st10_check
    ("st10: authorization binding", S / "testgate.py", 'if rec.get("authorization") != auth_fields(authorization):',
     'if False:', TG),
    ("st10: record frozen commit", S / "testgate.py", 'if rec.get("frozen_commit") != authorization.frozen_commit:',
     'if False:', TG),
    ("st10: record kind/mode", S / "testgate.py",
     'if rec.get("kind") != "st10" or rec.get("mode") != "formal" or rec.get("label") is not None:', 'if False:', TG),
    ("st10: TEST file hashes", S / "testgate.py", "    if files != rows_hashes:\n", "    if False:\n", TG),
    ("st10: code commit ancestor", S / "testgate.py", "    if not _is_ancestor(root, cc):\n", "    if False:\n", TG),
    ("st10: ancestor test always true", S / "testgate.py", '.returncode == 0)\n\n\ndef auth_fields', ' >= 0)\n\n\ndef auth_fields', TG),
    ("st10: counts are integers", S / "testgate.py", "    if not _counts_ok(counts):\n", "    if False:\n", TG),
    ("st10: auditor kind/commit", S / "testgate.py",
     'if aud.get("kind") != "st10_auditor_l6" or aud.get("frozen_commit") != authorization.frozen_commit:', 'if False:', TG),
    ("st10: auditor counted the same file", S / "testgate.py",
     'if aud.get("general_test_sha256") != files["general_test.jsonl"]:', 'if False:', TG),
    ("st10: auditor count is an integer", S / "testgate.py", 'if not _count(aud.get("l6_test_count")):', 'if False:', TG),
    ("st10: auditor count replaced by Executor's", S / "testgate.py",
     'STP.st10(fz, counts, test_limits(fz), aud["l6_test_count"])', 'STP.st10(fz, counts, test_limits(fz), counts["L6"])', TG),
    ("stops.st10: no over-limit judgement", S / "stops.py", "    over = sorted(c for c, v in counts.items() if v > limits[c])",
     "    over = []", TS + " " + TG),
    ("record: counts read from flags", S / "testgate.py", 'counts = {c: report["checks"][c]["value"] for c in LK.TEST_CHECKS}',
     'counts = {c: 0 if report["checks"][c].get("within_limit") else 1 for c in LK.TEST_CHECKS}', TG),
    ("record: no integer check", S / "testgate.py",
     "    if bad:\n        raise ImplementationFail(\"TEST part counts", "    if False:\n        raise ImplementationFail(\"TEST part counts", TG),
    ("record: code paths not checked", S / "testgate.py", "    if st.stdout.strip():\n", "    if False:\n", TG),
    ("record: overwrite allowed", S / "testgate.py", "    if path.exists():\n        raise ImplementationFail(\"%s exists",
     "    if False:\n        raise ImplementationFail(\"%s exists", TG),
    ("driver: ST10 record existence not checked", S / "test_data.py", "    TG.refuse_if_st10_record(root)\n", "", TG),
    ("st10 record: history not searched", S / "testgate.py",
     '"commit %s" % c for c in _ever_committed(root, ST10_RECORD_REL, ["--all"])]', '"commit %s" % c for c in []]', TG),
    # marker
    ("marker: working tree ignored", S / "testgate.py", 'where = (["working tree"] if (root / MARKER_REL).exists() else []) + [',
     'where = [] + [', TG),
    ("marker: HEAD only, not --all", S / "testgate.py", '    revs = ["--all"]\n', '    revs = ["HEAD"]\n', TG),
    ("marker: remote not fetched", S / "testgate.py", '        revs.append("FETCH_HEAD")\n', '        pass\n', TG),
    ("marker: result ignored", S / "testgate.py",
     "    if (root / RESULT_REL).exists() or _ever_committed(root, RESULT_REL, revs):", "    if False:", TG),
    ("begin: no marker check", S / "testgate.py", "    refuse_if_marker(root, remote, branch)\n", "    pass\n", TG),
    ("begin: staged changes allowed", S / "testgate.py",
     '    if _git(root, "diff", "--cached", "--quiet").returncode != 0:\n        raise _refuse("the git index holds staged changes; the marker',
     '    if False:\n        raise _refuse("the git index holds staged changes; the marker', TG),
    ("begin: no push", S / "testgate.py", '    head = _push(root, remote, branch, retries, sleep, "the TEST marker',
     '    head = _git(root, "rev-parse", "HEAD").stdout.strip() or _push(root, remote, branch, retries, sleep, "the TEST marker', TG),
    ("begin: no ST10 gate", S / "testgate.py", "    st10_sha, aud_sha = st10_check(fz, authorization, rows_hashes, root)\n    try:",
     "    st10_sha, aud_sha = None, None\n    try:", TG),
    ("push: remote ref not checked", S / "testgate.py",
     'if r.returncode == 0 and ls.returncode == 0 and ls.stdout.split()[:1] == [head]:', 'if True:', TG),
    # require_test_session
    ("session: not checked against this process", S / "testgate.py",
     "if not isinstance(session, TestSession) or _LIVE.get(session.session_id) is not session:",
     "if not isinstance(session, TestSession):", TG),
    ("session: marker id not checked", S / "testgate.py",
     'if marker.get("session_id") != session.session_id or sha != session.marker_sha256:', 'if False:', TG),
    ("session: marker bound to the authorization", S / "testgate.py",
     'if marker.get("frozen_commit") != authorization.frozen_commit or marker.get("authorization") != auth_fields(authorization):',
     'if False:', TG),
    ("session: rows not checked against marker", S / "testgate.py",
     '    if marker.get("test_files_sha256") != rows_hashes:\n', '    if False:\n', TG),
    ("session: ST10 change after marker allowed", S / "testgate.py",
     'if (st10_sha, aud_sha) != (marker.get("st10_record_sha256"), marker.get("auditor_count_sha256")):', 'if False:', TG),
    ("session: any model name", S / "testgate.py", "    if checkpoint_name not in session.models:\n", "    if False:\n", TG),
    ("session: a model twice", S / "testgate.py", "    if checkpoint_name in session.evaluated:\n", "    if False:\n", TG),
    ("session: model hash not checked", S / "testgate.py",
     "    if model_sha256 != session.checkpoints[checkpoint_name]:\n", "    if False:\n", TG),
    ("finish: models left allowed", S / "testgate.py", "    if left:\n", "    if False:\n", TG),
    ("evaluate_model: no TEST session gate", S / "evaluate.py",
     "        TG.require_test_session(fz, test_authorization, test_session, checkpoint_name, data, state_sha256(model))",
     "        pass", TG),
    # TEST driver
    ("driver: --out inside the repository allowed", S / "test_data.py",
     "    if out.resolve() == root or root in out.resolve().parents:", "    if False:", TG),
    ("driver: verdict from the report's flags", S / "test_data.py", "    over = TG.over_limit(fz, rec[\"counts\"])",
     "    over = sorted(c for c, v in report[\"checks\"].items() if not v[\"within_limit\"])", TG),
    # BE2, BE9, BE10, interpretations
    ("BE2: PROTOCOL_FROZEN vs fz removed", S / "leakage.py", "    if current != fz.record.commit:\n", "    if False:\n", TT),
    ("BE2: authorization vs PROTOCOL_FROZEN removed", S / "leakage.py", "    if authorization.frozen_commit != current:", "    if False:", TT),
    ("BE9: pending_problem always None", S / "interpretations.py", "    if open_ids:\n        return \"interpretations",
     "    if False:\n        return \"interpretations", TT),
    ("BE9: content_hashes key check removed", S / "frozen.py", "        if tuple(got) != CONTENT_HASH_KEYS:", "        if False:", TH),
    ("BE10: fz is None check removed", S / "evaluate.py", "        if fz is None:\n", "        if False:\n", TE),
    ("B14: note changed", S / "gate.py", 'RECALIBRATION_NOTE = "需重新校准"', 'RECALIBRATION_NOTE = "recalibrate"', "tests/test_gate.py"),
    ("ruling: one entry pending", S / "interpretations.py", '{"id": "B7", "status": ACCEPTED,', '{"id": "B7",', TT),
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
