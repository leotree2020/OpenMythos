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
  Beyond the task order (for Review Gate): every interpretation of interpretations.py has been ruled.
The two records are built by record.gate0_record and record.selection_freeze_record.
If any condition fails: the reason is printed, then "RESULT: FAIL", exit 1; no directory or file is created and no
TEST row is read (eval_sets.jsonl test rows are only parsed by generate_test(), after the checks).

When all hold: test_qa.jsonl (every fact x the TEST templates of its relation) and general_test.jsonl (first windows
per domain with the TEST split, as the DEV windows) are written to --out, and the TEST part of the leakage checks
runs (leakage.run_test_part; its L6 count is the Executor's; the data-auditor's own count and the comparison of ST10
follow outside this command). TEST is evaluated once afterwards (not by this module).

  python -m metrix_e1.test_data --inputs DIR --data DIR --out DIR
"""
import argparse
import dataclasses
import json
import re
import sys
from pathlib import Path

from . import contract as C
from . import data as D
from . import frozen as FZ
from . import interpretations as INT
from . import leakage as LK
from . import record as R
from . import stops as STP
from . import train as T
from ._cli import run_guarded
from .errors import ImplementationFail, ProtocolStop

__test__ = False            # the module name is fixed by the task order; it holds no pytest tests


class PreconditionFailed(Exception):
    pass


def _committed(repo_root, rel, kind, fz):
    try:
        rec, sha = R.committed_json(repo_root, rel)
    except R.NotCommitted as e:
        raise PreconditionFailed(str(e)) from e
    if rec.get("kind") != kind or rec.get("mode") != "formal" or rec.get("label") is not None:
        raise PreconditionFailed("%s is not a formal-mode %s record (kind %r, mode %r)" % (rel, kind, rec.get("kind"), rec.get("mode")))
    if rec.get("frozen_commit") != fz.record.commit:
        raise PreconditionFailed("%s names frozen commit %r, PROTOCOL_FROZEN %s" % (rel, rec.get("frozen_commit"), fz.record.commit))
    return rec, sha


def check_gate0_record(fz, repo_root):
    """Condition 2: the committed Gate 0 record (record.gate0_record) of formal mode with status PASS."""
    rec, sha = _committed(repo_root, R.GATE0_RECORD_REL, "gate0", fz)
    status = (rec.get("gate0") or {}).get("gate0_status")
    if status != "PASS":
        raise PreconditionFailed("%s: Gate 0 status %r, not PASS" % (R.GATE0_RECORD_REL, status))
    return sha


def check_selection_record(fz, contract, repo_root, content_hashes, gate0_sha):
    """Condition 3: the committed freeze record (record.selection_freeze_record) of formal mode: selected F, L, A
    configurations of SEARCH_SPACE.json; data content hashes equal to the data directory's; a 64-hex checkpoint hash
    for every one of the 30 runs of the plan; bound to the committed Gate 0 record by its SHA-256."""
    rel = R.SELECTION_FREEZE_REL
    rec, sha = _committed(repo_root, rel, "selection_freeze", fz)
    selected = rec.get("selected") or {}
    try:
        plan = T.training_plan(contract, selected)
    except (ValueError, KeyError, AttributeError) as e:
        raise PreconditionFailed("%s: selected configurations %r are not configurations of SEARCH_SPACE.json (%s)" % (
            rel, selected, e)) from e
    if rec.get("data_content_hashes") != content_hashes:
        raise PreconditionFailed("%s: data content hashes differ from the data directory" % rel)
    ck = rec.get("checkpoints") or {}
    hexes = re.compile(r"[0-9a-f]{64}")
    missing = [s.name for s in plan if not isinstance(ck.get(s.name), str) or not hexes.fullmatch(ck[s.name])]
    if missing:
        raise PreconditionFailed("%s: no checkpoint hash for %d runs (first %s)" % (rel, len(missing), missing[0]))
    if rec.get("gate0_record_sha256") != gate0_sha:
        raise PreconditionFailed("%s is not bound to the committed Gate 0 record (sha256 %r, committed %s)" % (
            rel, rec.get("gate0_record_sha256"), gate0_sha))
    return sha


def check_interpretations_ruled():
    """Beyond the three conditions of the task order (listed for Review Gate): no TEST while an interpretation of
    interpretations.py is still pending (B19 decides what the TEST part of the leakage checks counts; the others
    decide how the runs whose checkpoints TEST evaluates were made)."""
    open_ids = INT.pending()
    if open_ids:
        raise PreconditionFailed("interpretations not yet ruled by Review Gate: %s" % ", ".join(open_ids))


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
    """test_qa.jsonl and general_test.jsonl in memory ({file name: bytes}, info). Only with a TestAuthorization."""
    if not isinstance(authorization, LK.TestAuthorization):
        raise ImplementationFail("TEST is generated only after the preconditions")
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
    present = [n for n in D.TEST_FILES if (out / n).exists()]
    if present:
        raise ImplementationFail("%s already holds %s; TEST is generated once" % (out, present))
    files, info = generate_test(fz, auth, a.inputs, a.data)
    out.mkdir(parents=True, exist_ok=True)
    for name, blob in files.items():
        (out / name).write_bytes(blob)
        print("%-18s byte_sha256 %s" % (name, FZ.sha256_hex(blob)))
    report = LK.run_test_part(fz.split_manifest, LK.load_data(a.data), info["test_qa"], info["general_test"], auth,
                              fz.repo_root)
    (out / "leakage_test_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                                                  encoding="utf-8")
    for c, v in report["checks"].items():
        print("%-4s TEST part value %r limit %r %s" % (c, v["value"], v["limit"], "within limit" if v["within_limit"] else "OVER LIMIT"))
    print("L6 TEST count (Executor): %d -- compare with the data-auditor's count before any TEST evaluation (ST10)"
          % report["checks"]["L6"]["value"])
    print("RESULT: %s" % report["result"])
    sys.exit(0 if report["result"] == "PASS" else 1)


if __name__ == "__main__":
    run_guarded(main)
