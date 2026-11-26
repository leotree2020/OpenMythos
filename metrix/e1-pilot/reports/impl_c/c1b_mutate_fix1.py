"""Stage C, C1, second submission, fix commit after the round-1 reviews (c1b_mutate.py of the work commit ae60e0f is
kept as it ran for c1b_02; this copy adds the mutations of the fixes and follows the changed session guards): mutation
check of the TEST gates, the B25 ruling and the BE fixes. Each mutation removes or weakens one check in the working
tree (one or more exact replacements), runs the tests named for it (no -x: every named test runs; DEFERRED_MINORS
1.29 CC7) and restores the file (byte-for-byte, checked). A mutation is "caught" when every named test fails; the
outcome of each named test is printed. The scripts of the first submission (c1_mutate.py, c1_mutate_r2.py,
c1_mutate_r3.py) are kept as they ran.
Run from the repository root:
    METRIX_INPUTS_DIR=DIR python metrix/e1-pilot/reports/impl_c/c1b_mutate_fix1.py PYTHON
Prints one block per mutation and, at the end, the sha256 of src/ and tests/ before and after (must be equal).
"""
import hashlib
import subprocess
import sys
from pathlib import Path

PY = sys.argv[1]
S = Path("metrix/e1-pilot/src/metrix_e1")
G = S / "testgate.py"
EV = S / "evaluate.py"
TD = S / "test_data.py"
T = "tests/test_testgate.py::"
TT = "tests/test_test_data.py::"
DRIVER = T + "test_driver_writes_the_st10_record_and_judges_raw_counts"
DRIVER_PRE = T + "test_driver_checks_the_commit_preconditions_before_generating"
DRIVER_PUSH = T + "test_driver_push_refused_after_generation_counts_as_generated"
REFUSALS = T + "test_evaluate_model_refusals"
GPU = T + "test_evaluate_model_passes_every_gate_then_stops_at_the_gpu_check"
CLAIM = T + "test_evaluate_model_claims_after_the_gpu_check"
FINISH = T + "test_finish_commits_the_result_after_every_model"
CRED = T + "test_credentials_in_the_remote_url_are_not_written"
BEGIN_REFUSES = T + "test_begin_refuses_before_writing_anything"
MOVED = T + "test_evaluate_and_finish_are_blocked_when_the_checkout_left_the_marker_commit[%s]"
CHECKOUT = T + "test_every_test_path_needs_the_pilots_checkout_at_the_remote_tip[%s-%s]"


def checkout(fns, cases):
    return " ".join(CHECKOUT % (f, c) for f in fns.split() for c in cases.split())


ALL_FNS = "begin check_commit_preconditions refuse_if_marker refuse_if_st10_record"

MUTS = [
    # st10_check (unchanged since the first submission)
    ("st10: authorization binding", G, 'if rec.get("authorization") != auth_fields(authorization):', 'if False:',
     T + "test_st10_check_refuses[unbound]"),
    ("st10: record frozen commit", G, 'if rec.get("frozen_commit") != authorization.frozen_commit:', 'if False:',
     T + "test_st10_check_refuses[frozen_commit]"),
    ("st10: record kind/mode", G,
     'if rec.get("kind") != "st10" or rec.get("mode") != "formal" or rec.get("label") is not None:', 'if False:',
     T + "test_st10_check_refuses[record_kind] " + T + "test_st10_check_refuses[record_smoke]"),
    ("st10: TEST file hashes", G, "    if files != rows_hashes:\n", "    if False:\n", T + "test_st10_check_refuses[files]"),
    ("st10: code commit ancestor", G, "    if not _is_ancestor(root, cc):\n", "    if False:\n",
     T + "test_st10_check_refuses_a_code_commit_off_the_history " + T + "test_st10_check_refuses[code_commit]"),
    ("st10: ancestor test always true", G, '_git(root, "merge-base", "--is-ancestor", commit, "HEAD").returncode == 0)',
     '_git(root, "merge-base", "--is-ancestor", commit, "HEAD").returncode >= 0)',
     T + "test_st10_check_refuses_a_code_commit_off_the_history"),
    ("st10: counts are integers", G, "    if not _counts_ok(counts):\n", "    if False:\n",
     T + "test_st10_check_refuses[count_bool] " + T + "test_st10_check_refuses[count_missing]"),
    ("st10: auditor kind/commit", G,
     'if aud.get("kind") != "st10_auditor_l6" or aud.get("frozen_commit") != authorization.frozen_commit:', 'if False:',
     T + "test_st10_check_refuses[auditor_kind] " + T + "test_st10_check_refuses[auditor_frozen_commit]"),
    ("st10: auditor counted the same file", G, 'if aud.get("general_test_sha256") != files["general_test.jsonl"]:',
     'if False:', T + "test_st10_check_refuses[auditor_other_file]"),
    ("st10: auditor count is an integer", G, 'if not _count(aud.get("l6_test_count")):', 'if False:',
     T + "test_st10_check_refuses[auditor_not_int]"),
    ("st10: auditor count replaced by Executor's", G, 'STP.st10(fz, counts, test_limits(fz), aud["l6_test_count"])',
     'STP.st10(fz, counts, test_limits(fz), counts["L6"])', T + "test_st10_stops_when_the_l6_counts_differ"),
    ("stops.st10: no over-limit judgement", S / "stops.py",
     "    over = sorted(c for c, v in counts.items() if v > limits[c])", "    over = []",
     "tests/test_stops.py::test_st10 " + T + "test_st10_stops_on_a_count_over_its_frozen_limit[L4]"),
    # ST10 record
    ("record: counts read from flags", G, 'counts = {c: report["checks"][c]["value"] for c in LK.TEST_CHECKS}',
     'counts = {c: 0 if report["checks"][c].get("within_limit") else 1 for c in LK.TEST_CHECKS}',
     T + "test_st10_record_holds_raw_counts_hashes_and_code_commit " + DRIVER),
    ("record: no integer check", G, '    if bad:\n        raise ImplementationFail("TEST part counts',
     '    if False:\n        raise ImplementationFail("TEST part counts',
     T + "test_st10_record_refuses_counts_that_are_not_integers[bad0] "
     + T + "test_st10_record_refuses_counts_that_are_not_integers[bad1]"),
    ("record: code paths not checked", G, "    if st.stdout.strip():\n", "    if False:\n",
     T + "test_st10_record_refuses_uncommitted_code"),
    ("record: overwrite allowed", G, '    if path.exists():\n        raise ImplementationFail("%s exists',
     '    if False:\n        raise ImplementationFail("%s exists', T + "test_st10_record_holds_raw_counts_hashes_and_code_commit"),
    ("st10 record: existence ignored", G, '    if where:\n        raise ImplementationFail("%s exists (%s): TEST is',
     '    if False:\n        raise ImplementationFail("%s exists (%s): TEST is', DRIVER),
    ("st10 record: no checkout check", G, "    where = _where(root, ST10_RECORD_REL, check_checkout(root))",
     '    where = _where(root, ST10_RECORD_REL, _git(root, "rev-parse", "HEAD").stdout.strip())',
     checkout("refuse_if_st10_record", "ahead behind other_branch") + " " + DRIVER),
    # where a record exists (ruling 1)
    ("where: working tree ignored", G, '    found = ["working tree"] if (Path(root) / rel).exists() else []',
     "    found = []", T + "test_marker_in_the_working_tree_only_refuses " + T + "test_a_failing_commit_is_blocked"),
    ("where: remote's latest commit ignored", G,
     '    if _git(root, "cat-file", "-e", "%s:%s" % (tip, rel)).returncode == 0:', "    if False:",
     T + "test_a_marker_pushed_from_another_clone_refuses"),
    # the pilot's checkout (ruling 1)
    ("checkout: another repository accepted", G,
     "    got = repo_id(remote_url(root, PILOT_REMOTE))\n    if got != CANONICAL_REPO:\n",
     "    got = repo_id(remote_url(root, PILOT_REMOTE))\n    if False:\n", checkout(ALL_FNS, "other_repository")),
    ("checkout: another branch accepted", G, "    if local != PILOT_BRANCH:\n        raise _blocked(\"the checked-out",
     "    if False:\n        raise _blocked(\"the checked-out", checkout(ALL_FNS, "other_branch detached")),
    ("checkout: shallow clone accepted", G,
     '    if _git(root, "rev-parse", "--is-shallow-repository").stdout.strip() == "true":', "    if False:",
     T + "test_a_shallow_clone_is_blocked"),
    ("checkout: fetch failure ignored", G, "    if f.returncode != 0:\n", "    if False:\n",
     T + "test_a_remote_that_cannot_be_fetched_is_blocked " + checkout("begin refuse_if_marker", "unreachable")),
    ("checkout: HEAD not compared", G, "    if not HEX40.fullmatch(tip) or head != tip:",
     "    if not HEX40.fullmatch(tip):", checkout(ALL_FNS, "ahead behind")
     + " " + T + "test_a_push_that_fails_is_blocked_and_the_marker_refuses_later_runs " + DRIVER_PUSH),
    ("checkout: tip from the local HEAD, no fetch", G,
     '    tip = _git(root, "rev-parse", "--verify", "-q", "FETCH_HEAD^{commit}").stdout.strip()',
     '    tip = _git(root, "rev-parse", "--verify", "-q", "HEAD^{commit}").stdout.strip()',
     checkout(ALL_FNS, "behind") + " " + T + "test_a_marker_pushed_from_another_clone_refuses"),
    ("marker: no checkout check", G, "    tip = check_checkout(root)\n    where, result",
     '    tip = _git(root, "rev-parse", "HEAD").stdout.strip()\n    where, result',
     checkout("refuse_if_marker", "ahead behind other_branch")),   # begin checks the checkout again (preconditions)
    ("marker: result ignored", G, "    if result:\n", "    if False:\n",
     T + "test_a_result_without_a_marker_refuses " + T + "test_marker_with_a_result_is_refused_as_evaluated"),
    ("begin: no marker check", G, "    refuse_if_marker(root)\n    recs", "    recs",
     T + "test_begin_twice_is_refused_as_already_started"),
    ("begin: no ST10 gate", G, "    st10_sha, aud_sha = st10_check(fz, authorization, rows_hashes, root)\n    if not isinstance",
     "    st10_sha, aud_sha = None, None\n    if not isinstance", BEGIN_REFUSES),
    # the commit and push preconditions (ruling 2) and their callers
    ("preconditions: no checkout check", G, '    root = Path(repo_root)\n    check_checkout(root)\n    if _git(root, "diff"',
     '    root = Path(repo_root)\n    if _git(root, "diff"', checkout("check_commit_preconditions", "ahead behind other_branch")
     + " " + DRIVER_PRE),
    ("preconditions: staged changes allowed", G,
     '    if _git(root, "diff", "--cached", "--quiet").returncode != 0:\n        raise _blocked("the git index holds staged '
     'changes; the commit of %s holds that', '    if False:\n        raise _blocked("the git index holds staged changes; '
     'the commit of %s holds that', BEGIN_REFUSES + " " + DRIVER_PRE + " " + FINISH),
    ("preconditions: no identity check", G, '    if _git(root, "var", "GIT_COMMITTER_IDENT").returncode != 0:',
     '    if False:', T + "test_begin_refuses_without_a_committer_identity " + DRIVER_PRE),
    ("preconditions: dry-run push not checked", G, "    if dry.returncode != 0:\n", "    if False:\n",
     T + "test_a_failing_dry_run_push_is_blocked_before_writing " + DRIVER_PRE),
    ("begin: preconditions not checked", G, '    check_commit_preconditions(root, "the TEST marker")\n', "",
     BEGIN_REFUSES + " " + T + "test_begin_refuses_without_a_committer_identity"),
    ("finish: preconditions not checked", G, '    check_commit_preconditions(root, "the TEST result")\n', "", FINISH),
    ("driver: preconditions not checked", TD, '    TG.check_commit_preconditions(root, "the ST10 record")\n', "",
     DRIVER_PRE),
    ("driver: preconditions after generation", TD, [
        ('    TG.check_commit_preconditions(root, "the ST10 record")\n', ""),
        ("    files, info = generate_test(fz, auth, a.inputs, a.data)\n",
         "    files, info = generate_test(fz, auth, a.inputs, a.data)\n"
         '    TG.check_commit_preconditions(root, "the ST10 record")\n')], DRIVER_PRE),
    ("begin: parent marker not checked", G,
     'if _blob(root, "%s:%s" % (head, MARKER_REL)) != blob or _blob(root, "%s^:%s" % (head, MARKER_REL)) is not None:',
     'if _blob(root, "%s:%s" % (head, MARKER_REL)) != blob:', T + "test_a_second_begin_in_the_same_clone_is_blocked"),
    ("begin: pushed marker bytes not checked", G,
     'if _blob(root, "%s:%s" % (head, MARKER_REL)) != blob or _blob(root, "%s^:%s" % (head, MARKER_REL)) is not None:',
     'if _blob(root, "%s^:%s" % (head, MARKER_REL)) is not None:',
     T + "test_a_marker_file_overwritten_before_the_commit_is_blocked"),
    ("evaluate_model: s_mapping checked after the claim", EV, [
        ('    if with_s_mapping and split != "dev":           # checked before the TEST gate claims a checkpoint\n'
         '        raise ValueError("S\'s own-mapping accuracy is reported on DEV only (protocol section 8)")\n', ""),
        ("    if with_s_mapping:\n        qa, cb = score_s_mapping(",
         "    if with_s_mapping:\n        if split != \"dev\":\n            raise ValueError(\"S's own-mapping accuracy is "
         "reported on DEV only\")\n        qa, cb = score_s_mapping(")], T + "test_s_mapping_on_test_is_refused_before_the_gate"),
    # commit_paths and the push
    ("commit_paths: staged changes allowed", G,
     '    if _git(root, "diff", "--cached", "--quiet").returncode != 0:\n        raise _blocked("the git index holds staged '
     'changes; the commit of %s holds its own', '    if False:\n        raise _blocked("the git index holds staged changes; '
     'the commit of %s holds its own', T + "test_commit_paths_stages_exactly_the_named_paths"),
    ("commit_paths: staged paths not checked", G, "    if add.returncode != 0 or staged != sorted(rels):",
     "    if add.returncode != 0:", T + "test_commit_paths_stages_exactly_the_named_paths"),
    ("commit_paths: commit failure ignored", G, "    c = _git(root, \"commit\", \"-q\", \"-m\", message)\n    if c.returncode != 0:",
     "    c = _git(root, \"commit\", \"-q\", \"-m\", message)\n    if False:", T + "test_a_failing_commit_is_blocked"),
    ("push: remote ref not checked", G, 'if r.returncode == 0 and ls.returncode == 0 and ls.stdout.split()[:1] == [head]:',
     'if True:', T + "test_a_push_that_fails_is_blocked_and_the_marker_refuses_later_runs " + DRIVER_PUSH),
    ("push: tags followed", G, '"push", "--no-follow-tags", PILOT_REMOTE, "HEAD:refs/heads/%s" % PILOT_BRANCH)\n        ls',
     '"push", "--follow-tags", PILOT_REMOTE, "HEAD:refs/heads/%s" % PILOT_BRANCH)\n        ls',
     T + "test_begin_commits_and_pushes_the_marker_only"),
    ("credentials: not scrubbed", G, '    return _USERINFO.sub(r"\\1", text)', "    return text", CRED),
    # require_test_session / claim / finish
    ("session: not checked against this process", G,
     "    if not isinstance(session, TestSession) or _LIVE.get(session.session_id) is not session:\n        raise _refuse(\"no TEST "
     "session of this process (begin_test_evaluation)\")\n    _check_session_checkout",
     "    if not isinstance(session, TestSession):\n        raise _refuse(\"no TEST session of this process "
     "(begin_test_evaluation)\")\n    _check_session_checkout", REFUSALS),
    ("session: checkout not checked", G,
     '    _check_session_checkout(root, session)\n    marker, _ = _committed(root, MARKER_REL, "TEST marker")\n    rows_hashes',
     '    marker, _ = _committed(root, MARKER_REL, "TEST marker")\n    rows_hashes',
     " ".join(MOVED % c for c in ("a_commit_after_begin", "another_branch", "the_marker_rewritten"))),
    ("session checkout: branch only", G, "    if local != PILOT_BRANCH or head != session.marker_commit:",
     "    if local != PILOT_BRANCH:", " ".join(MOVED % c for c in ("a_commit_after_begin", "the_marker_rewritten"))),
    ("session: rows not checked against marker", G, '    if marker.get("test_files_sha256") != rows_hashes:\n',
     '    if False:\n', REFUSALS),
    ("session: no ST10 gate", G, "    st10_check(fz, authorization, rows_hashes, root)\n    if checkpoint_name",
     "    if checkpoint_name", REFUSALS),
    ("session: any model name", G, '    if checkpoint_name not in marker["models"]:\n', "    if False:\n", REFUSALS),
    ("session: model hash not checked", G, '    if got != marker["checkpoints"][checkpoint_name]:\n', "    if False:\n",
     REFUSALS),
    ("claim: a model twice", G, "    if checkpoint_name in session.evaluated:\n        raise _refuse(\"%s was already evaluated on "
     "TEST in this session\" % checkpoint_name)\n    session.evaluated.add",
     "    if False:\n        raise _refuse(\"%s was already evaluated on TEST in this session\" % checkpoint_name)\n    "
     "session.evaluated.add", GPU),
    ("claim: any session", G, '''    if not isinstance(session, TestSession) or _LIVE.get(session.session_id) is not session:
        raise _refuse("no TEST session of this process (begin_test_evaluation)")
    if checkpoint_name in session.evaluated:''', '''    if False:
        raise _refuse("no TEST session of this process (begin_test_evaluation)")
    if checkpoint_name in session.evaluated:''', GPU),
    ("finish: any session", G, '''    if not isinstance(session, TestSession) or _LIVE.get(session.session_id) is not session:
        raise _refuse("no TEST session of this process")
    _check_session_checkout''', '''    if not isinstance(session, TestSession):
        raise _refuse("no TEST session of this process")
    _check_session_checkout''', FINISH),
    ("finish: checkout not checked", G,
     '    _check_session_checkout(root, session)\n    marker, _ = _committed(root, MARKER_REL, "TEST marker")\n    left',
     '    marker, _ = _committed(root, MARKER_REL, "TEST marker")\n    left',
     " ".join(MOVED % c for c in ("a_commit_after_begin", "the_marker_rewritten"))),
    ("finish: models left allowed", G, "    if left:\n", "    if False:\n", FINISH),
    ("evaluate_model: no TEST session gate", EV,
     "        TG.require_test_session(fz, test_authorization, test_session, checkpoint_name, data, model)", "        pass", GPU),
    ("evaluate_model: claim before the GPU check", EV,
     '''        require_gpu(mode, device)
        TG.claim_checkpoint(test_session, checkpoint_name)''', '''        TG.claim_checkpoint(test_session, checkpoint_name)
        require_gpu(mode, device)''', GPU),
    ("evaluate_model: claim removed", EV, "        TG.claim_checkpoint(test_session, checkpoint_name)\n", "", CLAIM),
    ("evaluate_model: claim after the scorers", EV, [
        ("        TG.claim_checkpoint(test_session, checkpoint_name)\n", ""),
        ('        out["s_mapping_dev_qa"], out["s_mapping_cb"] = qa, cb\n    return out\n',
         '        out["s_mapping_dev_qa"], out["s_mapping_cb"] = qa, cb\n    if split == "test":\n'
         "        TG.claim_checkpoint(test_session, checkpoint_name)\n    return out\n")], CLAIM),
    ("record.committed_json: no object check", S / "record.py", "    if not isinstance(obj, dict):\n", "    if False:\n",
     TT + "test_a_committed_record_that_is_not_an_object_is_not_committed"),
    # TEST driver
    ("driver: --out inside the repository allowed", TD,
     "    if out.resolve() == root or root in out.resolve().parents:", "    if False:", DRIVER),
    ("driver: verdict from the report's flags", TD, '    over = TG.over_limit(fz, rec["counts"])',
     '    over = sorted(c for c, v in report["checks"].items() if not v["within_limit"])', DRIVER),
    ("driver: ST10 record existence not checked", TD, "    TG.refuse_if_st10_record(root)\n", "", DRIVER),
    ("driver: ST10 record not committed and pushed", TD,
     '    head = TG.commit_paths(root, [TG.ST10_RECORD_REL],', '    head = "-" or TG.commit_paths(root, [TG.ST10_RECORD_REL],',
     DRIVER + " " + DRIVER_PUSH),
    ("driver: code checked only after generation", TD,
     "    TG.code_commit(root)                                # the code that generates TEST is committed (ST10 record)\n",
     "", DRIVER),
    # B25 (ruling 3), the interpretations, BE2, BE9, BE10, B14
    ("B25: pending again", S / "interpretations.py", '{"id": "B25", "status": ACCEPTED_C1, "ruling": RULING_REF_C1,',
     '{"id": "B25", "ruling": RULING_REF_C1,', TT + "test_interpretations_ruled_by_review_gate"),
    ("B25: state_sha256 without the dtype", S / "train.py",
     'h.update(name.encode("utf-8") + b"\\0" + str(t.dtype).encode() + b"\\0" + str(tuple(t.shape)).encode() + b"\\0")',
     'h.update(name.encode("utf-8") + b"\\0" + str(tuple(t.shape)).encode() + b"\\0")',
     TT + "test_b25_definition_is_the_code_of_state_sha256"),
    ("ruling: one entry pending", S / "interpretations.py", '{"id": "B7", "status": ACCEPTED,', '{"id": "B7",',
     TT + "test_interpretations_ruled_by_review_gate"),
    ("BE2: PROTOCOL_FROZEN vs fz removed", S / "leakage.py", "    if current != fz.record.commit:\n", "    if False:\n",
     TT + "test_verify_authorization_frozen_commit_comparisons"),
    ("BE2: authorization vs PROTOCOL_FROZEN removed", S / "leakage.py", "    if authorization.frozen_commit != current:",
     "    if False:", TT + "test_generation_needs_authorization"),
    ("BE9: pending_problem always None", S / "interpretations.py", "    if open_ids:\n        return \"interpretations",
     "    if False:\n        return \"interpretations", TT + "test_pending_interpretations_block_test"),
    ("BE9: content hashes from a literal key list", S / "frozen.py",
     "for key in CONTENT_HASH_KEYS}    # DEFERRED_MINORS BE9",
     'for key in ("facts", "train_S", "candidates", "anchor_texts")}',
     "tests/test_data_hashes.py::test_content_hashes_are_built_from_content_hash_keys"),
    ("BE10: fz is None check removed", EV, "        if fz is None:\n", "        if False:\n",
     "tests/test_evaluate.py::test_test_split_needs_the_authorization"),
    ("B14: note changed", S / "gate.py", 'RECALIBRATION_NOTE = "需重新校准"', 'RECALIBRATION_NOTE = "recalibrate"',
     "tests/test_gate.py::test_reasons_follow_section_9"),
]


def tree_sha():
    h = hashlib.sha256()
    for p in sorted(Path("metrix/e1-pilot/src").rglob("*.py")) + sorted(Path("metrix/e1-pilot/tests").rglob("*.py")):
        h.update(str(p).encode() + b"\0" + p.read_bytes())
    return h.hexdigest()


def parse(m):
    name, path, *rest = m
    pairs, tests = (rest[0], rest[1]) if isinstance(rest[0], list) else ([(rest[0], rest[1])], rest[2])
    return name, path, pairs, ["metrix/e1-pilot/" + t for t in tests.split()]


if __name__ == "__main__":
    before = tree_sha()
    caught = 0
    for m in MUTS:
        name, path, pairs, nodes = parse(m)
        orig = path.read_bytes()
        s = orig.decode("utf-8")
        bad = [s.count(old) for old, _ in pairs if s.count(old) != 1]
        if bad:
            print("%-48s -> MUTATION NOT APPLICABLE (%s matches)" % (name, bad))
            continue
        for old, new in pairs:
            s = s.replace(old, new)
        path.write_text(s, encoding="utf-8")
        try:
            r = subprocess.run([PY, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-rf"] + nodes, capture_output=True,
                               text=True)
            last = r.stdout.strip().split("\n")[-1]
            failed = {ln.split(" ")[1] for ln in r.stdout.split("\n") if ln.startswith("FAILED ")}
            ok = r.returncode == 1 and all(n in failed for n in nodes)
            caught += ok
            print("%-48s -> %s exit %d | %s" % (name, "CAUGHT" if ok else "NOT CAUGHT", r.returncode, last))
            for n in nodes:
                print("       %s %s" % ("FAILED" if n in failed else "passed", n.split("::", 1)[1]))
        finally:
            path.write_bytes(orig)
    after = tree_sha()
    print("mutations %d, caught %d" % (len(MUTS), caught))
    print("src+tests sha256 before %s after %s %s" % (before, after, "EQUAL" if before == after else "DIFFERENT"))
    print("RESULT: %s" % ("PASS" if caught == len(MUTS) and before == after else "FAIL"))
