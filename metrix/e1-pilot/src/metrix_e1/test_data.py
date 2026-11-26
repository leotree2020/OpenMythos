"""TEST generator of METRIX E1-PILOT (protocol v1.1 section 8 step 8; sections 2.3, 2.7, 2.8, 3).

Implementation Task Order V1, section 5: before anything is generated, all three conditions must hold:
  1. PROTOCOL_FROZEN is valid and ST12 passes (frozen.load: the current section, the four frozen files by git
     cat-file; data.verify: the inputs' file hashes, the four content hashes, every data file equal to its
     regeneration);
  2. a Gate 0 record with status PASS exists (results/gate0_record.json, formal mode, committed: the working-tree
     bytes equal the blob of HEAD);
  3. the freeze record of the selected configurations has been committed (results/selection_freeze_record.json,
     formal mode, committed; selected F, L, A configurations of SEARCH_SPACE.json; data content hashes equal to the
     ones just checked; a 64-hex checkpoint hash for every one of the 30 training runs of the plan; bound to the
     committed Gate 0 record by its SHA-256).
  Beyond the task order (kept by Review Gate 2026-11-24): every interpretation of interpretations.py has been ruled.
The two records are built by record.gate0_record and record.selection_freeze_record.
If any condition fails: the reason is printed, then "RESULT: FAIL", exit 1; no directory or file is created and no
TEST row is read (eval_sets.jsonl test rows are only parsed by generate_test(), after the checks).

When all hold: test_qa.jsonl (every fact x the TEST templates of its relation) and general_test.jsonl (first windows
per domain with the TEST split, as the DEV windows) are written to --out, which must lie outside the repository (no
TEST content is committed), and the TEST part of the leakage checks runs (leakage.run_test_part; its L6 count is the
Executor's). Then this command, the step 8 TEST driver, writes the ST10 record (testgate.write_st10_record:
results/st10_record.json with the raw counts, the sha256 of the two TEST files and the code commit; Review Gate
supplementary ruling 3), judges the counts against the frozen limits, and commits and pushes the record (that path
only, testgate.commit_paths), so that another clone sees it before TEST could be generated there again. The
data-auditor's own L6 count (testgate.AUDITOR_L6_REL) and the TEST evaluation (once: testgate.begin_test_evaluation)
follow outside this command; the evaluation re-judges ST10 from the committed records.

  python -m metrix_e1.test_data --inputs DIR --data DIR --out DIR
Before anything is generated: --out outside the repository, no TEST file in it, the code committed (the ST10 record's
code commit, testgate.code_commit), the commit and push preconditions of the record
(testgate.check_commit_preconditions: the pilot's checkout at the remote branch's latest commit, nothing staged, a
committer identity, a dry-run push accepted), and no ST10 record (testgate.refuse_if_st10_record: the working tree and
the remote branch's latest commit). A push the remote still refuses after generation is BLOCKED: TEST counts as
generated, the record in the working tree refuses any further generation, and the Owner decides whether this one
file is committed by hand (Review Gate's ruling on C1 of 2026-11-25, item 2; RUNBOOK_A100.md).
"""
import argparse
import dataclasses
import json
import sys
from pathlib import Path

from . import contract as C
from . import data as D
from . import frozen as FZ
from . import interpretations as INT
from . import leakage as LK
from . import record as R
from . import stops as STP
from . import testgate as TG
from ._cli import run_guarded
from .errors import ImplementationFail, ProtocolStop

__test__ = False            # the module name is fixed by the task order; it holds no pytest tests


class PreconditionFailed(Exception):
    pass


def _committed(repo_root, rel, kind, fz):
    try:
        return R.committed_record(repo_root, rel, kind, fz.record.commit)
    except R.NotCommitted as e:
        raise PreconditionFailed(str(e)) from e


def check_gate0_record(fz, repo_root):
    """Condition 2: the committed Gate 0 record (record.gate0_record) of formal mode with status PASS
    (record.gate0_record_problem)."""
    rec, sha = _committed(repo_root, R.GATE0_RECORD_REL, "gate0", fz)
    problem = R.gate0_record_problem(rec)
    if problem:
        raise PreconditionFailed("%s: %s" % (R.GATE0_RECORD_REL, problem))
    return sha


def check_selection_record(fz, contract, repo_root, content_hashes, gate0_sha):
    """Condition 3: the committed freeze record (record.selection_freeze_record) of formal mode whose content meets
    record.freeze_record_problem: selected F, L, A configurations of SEARCH_SPACE.json; data content hashes equal to
    the data directory's; a 64-hex checkpoint hash for every one of the 30 runs of the plan; bound to the committed
    Gate 0 record by its SHA-256."""
    rec, sha = _committed(repo_root, R.SELECTION_FREEZE_REL, "selection_freeze", fz)
    problem = R.freeze_record_problem(rec, contract, content_hashes, gate0_sha)
    if problem:
        raise PreconditionFailed("%s: %s" % (R.SELECTION_FREEZE_REL, problem))
    return sha


def check_interpretations_ruled():
    """Beyond the three conditions of the task order (kept by Review Gate 2026-11-24, stage-B ruling item 3): no TEST
    while an interpretation of interpretations.py is still pending (B19 decides what the TEST part of the leakage
    checks counts; the others decide how the runs whose checkpoints TEST evaluates were made)."""
    problem = INT.pending_problem()
    if problem:
        raise PreconditionFailed(problem)


def check_preconditions(repo_root, inputs_dir, data_dir):
    """The three conditions, in order, then check_interpretations_ruled(). Returns (Frozen, TestAuthorization);
    raises PreconditionFailed or a protocol stop (ST12) on the first condition that fails."""
    fz = STP.st12(repo_root, inputs_dir, data_dir)                    # condition 1 (raises ST12Error)
    contract = C.load(fz)
    content = fz.check_data_dir(data_dir)
    g_sha = check_gate0_record(fz, fz.repo_root)                     # condition 2
    s_sha = check_selection_record(fz, contract, fz.repo_root, content, g_sha)   # condition 3
    check_interpretations_ruled()
    return fz, LK.TestAuthorization(fz.record.commit, g_sha, s_sha)


# ------------------------------------------------------------------------------------------- generation (2.3, 2.7)

def params_for_test(fz):
    """TEST questions per fact (contract.Accounting, from SPLIT_MANIFEST splits.TEST) and the TEST windows of the
    general text, from the frozen manifests."""
    per_fact = C.load(fz).accounting.test_questions_per_fact
    n, split = C.fullmatch_frozen(r"first (\d+) windows per domain with split == '(\w+)', file order; final TEST "
                                  r"evaluation only", fz.data_manifest["general_text"]["test"], "general_text.test").groups()
    return per_fact, int(n), split


def build_test_qa(fz, facts, per_fact):
    """Every fact x the TEST templates of its relation, fact order then template order. Rows {fact_id, template_id,
    question} (the layout of dev_qa.jsonl)."""
    tpl = D.templates_by(fz)
    out = []
    for f in facts:
        ts = tpl.get((f["relation"], "TEST"), [])
        if len(ts) != per_fact:
            raise ImplementationFail("%s: %d TEST templates, the manifest says %d" % (f["relation"], len(ts), per_fact))
        out += [{"fact_id": f["fact_id"], "template_id": t["template_id"], "question": D.fill(t, f)} for t in ts]
    return out


def generate_test(fz, authorization, inputs_dir, data_dir):
    """test_qa.jsonl and general_test.jsonl in memory ({file name: bytes}, info). Only with a TestAuthorization whose
    hashes match the committed Gate 0 and freeze records (leakage.verify_authorization), checked before anything is
    read. main() is the only caller: it checks the pilot's checkout, the commit and push preconditions and that no
    ST10 record exists before it calls this (run_pilot.py runs main as a subprocess)."""
    LK.verify_authorization(authorization, fz)
    p = D.params(fz)
    paths = D.check_inputs(fz, p, inputs_dir)
    tok = D.load_qwen_tokenizer(p, paths)
    per_fact, n_windows, split = params_for_test(fz)
    facts = FZ.read_jsonl(Path(data_dir) / "facts.jsonl")
    test_qa = build_test_qa(fz, facts, per_fact)
    pt = dataclasses.replace(p, general_dev_split=split, general_dev_per_domain=n_windows)
    general_test, stats = D.build_general_dev(pt, tok, paths["eval_sets"], paths["parcae_tokenizer"])
    files = {"test_qa.jsonl": FZ.jsonl_bytes(test_qa), "general_test.jsonl": FZ.jsonl_bytes(general_test)}
    if tuple(files) != D.TEST_FILES:
        raise ImplementationFail("TEST files %s differ from %s" % (tuple(files), D.TEST_FILES))
    return files, {"test_qa": test_qa, "general_test": general_test, "eval_sets_rows": stats}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m metrix_e1.test_data")
    ap.add_argument("--inputs", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    try:
        fz, auth = check_preconditions(None, a.inputs, a.data)
    except (PreconditionFailed, ProtocolStop) as e:
        print("TEST generator refused: %s" % e)
        print("no TEST content was generated, read or written")
        print("RESULT: FAIL")
        sys.exit(1)
    out = Path(a.out)
    root = fz.repo_root.resolve()
    if out.resolve() == root or root in out.resolve().parents:
        raise ImplementationFail("--out %s is inside the repository %s; TEST content is never committed" % (out, root))
    present = [n for n in D.TEST_FILES if (out / n).exists()]
    if present:
        raise ImplementationFail("%s already holds %s; TEST is generated once" % (out, present))
    TG.code_commit(root)                                # the code that generates TEST is committed (ST10 record)
    TG.check_commit_preconditions(root, "the ST10 record")
    TG.refuse_if_st10_record(root)
    files, info = generate_test(fz, auth, a.inputs, a.data)
    out.mkdir(parents=True, exist_ok=True)
    for name, blob in files.items():
        (out / name).write_bytes(blob)
        print("%-18s byte_sha256 %s" % (name, FZ.sha256_hex(blob)))
    report = LK.run_test_part(fz, LK.load_data(a.data), info["test_qa"], info["general_test"], auth)
    (out / "leakage_test_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                                                  encoding="utf-8")       # outside the repository: L4 details may quote TEST
    path, rec = TG.write_st10_record(fz, auth, report, files)
    limits = TG.test_limits(fz)
    over = TG.over_limit(fz, rec["counts"])
    for c in LK.TEST_CHECKS:
        print("%-4s TEST part count %r frozen limit %r %s" % (c, rec["counts"][c], limits[c],
                                                              "OVER LIMIT" if c in over else "within limit"))
    head = TG.commit_paths(root, [TG.ST10_RECORD_REL], "metrix: E1-PILOT formal step 8 ST10 record (raw TEST-part "
                           "counts, TEST file hashes, code commit)",
                           "the ST10 record (TEST counts as generated: no second generation; the Owner decides whether "
                           "this one file is committed by hand)")
    print("ST10 record written, committed and pushed: %s, commit %s (raw counts, TEST file sha256 %s, code commit %s)"
          % (path, head, rec["test_files_sha256"], rec["code_commit"]))
    print("L6 TEST count (Executor): %d -- the data-auditor counts with its own script and commits %s before any TEST "
          "evaluation (ST10)" % (rec["counts"]["L6"], TG.AUDITOR_L6_REL))
    if over:
        print("ST10: TEST part over limit %s -> stop; TEST is not evaluated; BLOCKED; report to the Owner" % over)
    print("RESULT: %s" % ("FAIL" if over else "PASS"))
    sys.exit(1 if over else 0)


if __name__ == "__main__":
    run_guarded(main)
