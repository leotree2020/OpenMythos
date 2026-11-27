"""ic11_05 (implementation stage C, C4 code commit, round 1; task 2 of the invocation): static reading of the staged code
(index blobs, `git cat-file blob :path`) against the parent 3bc761ea (`HEAD:path`), by my own AST walk. Nothing of the
Executor is imported or executed.
  A. which top-level functions / methods of pilot.py, stops.py, compute.py, interpretations.py changed between HEAD and
     the index, with and without docstrings (expected code changes: pilot.preflight, pilot.step2, new
     pilot.st11_estimate_hours; docstring-only: the module, checkpoint_overhead_seconds, test_evaluation_seconds; stops.py
     and compute.py byte-identical; interpretations: ENTRIES and two new constants).
  B. step2: the call that passes STP.st11 is p.stop_in_step(2, ..., STP.st11, p.fz, p.contract, <arg>) with <arg> ==
     pre["st11_estimate_hours"]; it is the only reference to STP.st11 / stops.st11 in src/ and run_pilot.py; the parent
     passed pre["b17_estimate_hours"].
  C. st11_estimate_hours: parameters (b17_hours, overhead_seconds), body (docstring aside) `return b17_hours +
     overhead_seconds / 3600.0`; called once in src/ (preflight), with (hours, overhead) where hours is the first value
     of CP.estimate_total_hours(...) and overhead the first value of checkpoint_overhead_seconds(...), each name assigned
     once in preflight; the record's "st11_estimate_hours" is st11_hours, "b17_estimate_hours" is hours,
     "checkpoint_overhead" is {"seconds": overhead, "counts": counts}.
  D. stops.st11: the condition `not math.isfinite(estimate_hours) or estimate_hours > contract.stops.st11_hours`
     (stop strictly above the bound), unchanged from HEAD.
  E. ST7: Pilot.run_seconds, Pilot.eval_seconds, test_evaluation_seconds identical to HEAD with docstrings removed
     (also evaluation_plan, checkpoint_overhead_seconds and compute.estimate_total_hours / evaluation_units).
  F. the two renamed record fields (checkpoint_overhead_report_only, b17_plus_checkpoint_overhead_hours_report_only):
     no string constant naming them in the staged src/, tests/, run_pilot.py; readers of the step 2 record in src/
     (string constants containing "step2_record") and every subscript ["preflight"] / .get("preflight"): only
     test_evaluate's step2["preflight"]["timing"].
  G. B17 (interpretations.ENTRIES resolved from the AST): status == "ACCEPTED（Review Gate 2026-11-27 修订）", which is
     the wording of tasks/IMPL_C4_RULING.md item 1; ruling == "tasks/IMPL_C4_RULING.md 第 1 项" and the file's item 1
     is the ST11 ruling; the text states ST11 = B17's estimate + the checkpoint overhead with the counts 32 / 30 / 18 /
     17 / 15, the ST7 look-ahead unchanged and no margin on the TEST look-ahead; B17's own formula is the parent's text
     unchanged; every other entry B1-B25 identical to HEAD.
  H. informational (for the invocation's question on ruling item 2): the "for Review Gate" phrases left in pilot.py,
     with whether each line is unchanged from HEAD.
usage: python -I -B ic11_05_static.py <repo_root>"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ast
import re
import subprocess
from ia_common import run

SRC = "metrix/e1-pilot/src/metrix_e1/"
FILES = ["pilot.py", "stops.py", "compute.py", "interpretations.py"]
OLD_FIELDS = ("checkpoint_overhead_report_only", "b17_plus_checkpoint_overhead_hours_report_only")
RULING = "metrix/e1-pilot/tasks/IMPL_C4_RULING.md"


def blob(repo, spec):
    r = subprocess.run(["git", "-C", repo, "cat-file", "blob", spec], capture_output=True, env=dict(os.environ, GIT_OPTIONAL_LOCKS="0"))
    return r.stdout.decode("utf-8") if r.returncode == 0 else None


def ls(repo, rev, *paths):
    r = subprocess.run(["git", "-C", repo, "ls-tree", "-r", "--name-only", rev, "--", *paths], capture_output=True, text=True)
    return [x for x in r.stdout.split("\n") if x.endswith(".py")]


def strip_doc(node):
    node = ast.parse(ast.unparse(node)).body[0]
    for n in ast.walk(node):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)) and n.body \
                and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant) \
                and isinstance(n.body[0].value.value, str):
            n.body = n.body[1:] or [ast.Pass()]
    return ast.dump(node)


def defs(tree):
    out = {}
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out[n.name] = n
        elif isinstance(n, ast.ClassDef):
            out[n.name] = n
            for m in n.body:
                if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    out["%s.%s" % (n.name, m.name)] = m
        elif isinstance(n, (ast.Assign, ast.AnnAssign)):
            tg = n.targets[0] if isinstance(n, ast.Assign) else n.target
            if isinstance(tg, ast.Name):
                out["=" + tg.id] = n
    return out


def module_doc(tree):
    return ast.get_docstring(tree)


def resolve_entries(tree):
    consts = {}
    for n in tree.body:
        if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and isinstance(n.value, ast.Constant):
            consts[n.targets[0].id] = n.value.value
    ent = [n for n in tree.body if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id == "ENTRIES"][0]

    def val(v):
        if isinstance(v, ast.Constant):
            return v.value
        if isinstance(v, ast.Name):
            return consts[v.id]
        raise ValueError(ast.unparse(v))
    return consts, [{val(k): val(v) for k, v in zip(d.keys, d.values)} for d in ent.value.elts]


def main():
    repo = sys.argv[1]
    ok = True
    trees = {}
    print("== A. changed definitions (HEAD -> index)")
    for f in FILES:
        h, i = blob(repo, "HEAD:" + SRC + f), blob(repo, ":" + SRC + f)
        th, ti = ast.parse(h), ast.parse(i)
        trees[f] = (th, ti, h, i)
        dh, di = defs(th), defs(ti)
        added = sorted(set(di) - set(dh))
        removed = sorted(set(dh) - set(di))
        code = sorted(k for k in set(dh) & set(di) if strip_doc(dh[k]) != strip_doc(di[k]))
        doc = sorted(k for k in set(dh) & set(di) if ast.dump(dh[k]) != ast.dump(di[k]) and k not in code)
        print("  %-20s bytes identical %s | module docstring changed %s | added %s | removed %s | code changed %s | "
              "docstring-only changed %s" % (f, h == i, module_doc(th) != module_doc(ti), added, removed, code, doc))
        if f == "pilot.py":
            ok &= added == ["st11_estimate_hours"] and not removed and code == ["preflight", "step2"]
            ok &= doc == ["checkpoint_overhead_seconds", "test_evaluation_seconds"]
        elif f in ("stops.py", "compute.py"):
            ok &= h == i
        else:
            ok &= added == ["=ACCEPTED_C4", "=RULING_REF_C4"] and not removed and code == ["=ENTRIES"]

    th, ti, ph, pi = trees["pilot.py"]
    dh, di = defs(th), defs(ti)
    print("\n== B. step2: the ST11 call")
    for label, d in (("HEAD", dh), ("index", di)):
        calls = [c for c in ast.walk(d["step2"]) if isinstance(c, ast.Call)
                 and any(ast.unparse(a) == "STP.st11" for a in c.args)]
        for c in calls:
            print("  %-5s %s | last argument %s" % (label, ast.unparse(c), ast.unparse(c.args[-1])))
        if label == "index":
            ok &= len(calls) == 1 and ast.unparse(calls[0].func) == "p.stop_in_step" and \
                [ast.unparse(a) for a in calls[0].args[2:]] == ["[]", "STP.st11", "p.fz", "p.contract", "pre['st11_estimate_hours']"] \
                and ast.unparse(calls[0].args[0]) == "2"
        else:
            ok &= len(calls) == 1 and ast.unparse(calls[0].args[-1]) == "pre['b17_estimate_hours']"
    refs = []
    for rel in ls(repo, "HEAD", "metrix/e1-pilot/src", "metrix/e1-pilot/run_pilot.py"):
        t = blob(repo, ":" + rel)
        for n in ast.walk(ast.parse(t)):
            if isinstance(n, ast.Attribute) and n.attr == "st11" and not (isinstance(n.value, ast.Name) and n.value.id in ("contract",)):
                refs.append((rel.split("/")[-1], n.lineno, ast.unparse(n)))
    print("  references to an attribute named st11 in the staged src/ and run_pilot.py: %s" % refs)
    ok &= [r for r in refs if r[2] in ("STP.st11", "stops.st11")] == [r for r in refs if r[0] == "pilot.py" and r[2] == "STP.st11"] \
        and len([r for r in refs if r[2] == "STP.st11"]) == 1
    asg = [ast.unparse(n) for n in ast.walk(di["step2"]) if isinstance(n, ast.Assign)]
    print("  step2 assignments: %s" % asg)

    print("\n== C. st11_estimate_hours and preflight")
    fn = di["st11_estimate_hours"]
    body = [b for b in fn.body if not (isinstance(b, ast.Expr) and isinstance(b.value, ast.Constant))]
    print("  def st11_estimate_hours(%s): %s" % (", ".join(a.arg for a in fn.args.args), [ast.unparse(b) for b in body]))
    ok &= [a.arg for a in fn.args.args] == ["b17_hours", "overhead_seconds"] and not fn.args.defaults
    ok &= [ast.unparse(b) for b in body] == ["return b17_hours + overhead_seconds / 3600.0"]
    callers = []
    for rel in ls(repo, "HEAD", "metrix/e1-pilot/src", "metrix/e1-pilot/run_pilot.py"):
        t = ast.parse(blob(repo, ":" + rel))
        for top in t.body:
            for n in ast.walk(top):
                if isinstance(n, ast.Call) and ast.unparse(n.func).split(".")[-1] == "st11_estimate_hours":
                    callers.append((rel.split("/")[-1], getattr(top, "name", "?"), ast.unparse(n)))
    print("  callers in src/ and run_pilot.py: %s" % callers)
    ok &= callers == [("pilot.py", "preflight", "st11_estimate_hours(hours, overhead)")]
    pf = di["preflight"]
    assigns = {}
    for n in ast.walk(pf):
        if isinstance(n, ast.Assign):
            for tg in n.targets:
                for nm in ([tg] if isinstance(tg, ast.Name) else [e for e in getattr(tg, "elts", []) if isinstance(e, ast.Name)]):
                    assigns.setdefault(nm.id, []).append(ast.unparse(n))
    for k in ("hours", "overhead", "counts", "st11_hours"):
        print("  preflight: %s assigned by %s" % (k, assigns.get(k)))
    ok &= assigns.get("hours") == [x for x in assigns.get("hours", []) if x.startswith("hours, parts = CP.estimate_total_hours(")] \
        and len(assigns["hours"]) == 1
    ok &= len(assigns.get("overhead", [])) == 1 and assigns["overhead"][0].startswith(
        "overhead, counts = checkpoint_overhead_seconds(p.contract, load_s, hash_s, save_s, reload_s, file_hash_s)")
    ok &= assigns.get("st11_hours") == ["st11_hours = st11_estimate_hours(hours, overhead)"]
    outd = [n.value for n in ast.walk(pf) if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
            and n.targets[0].id == "out" and isinstance(n.value, ast.Dict)][0]
    kv = {k.value: ast.unparse(v) for k, v in zip(outd.keys, outd.values)}
    for k in ("b17_estimate_hours", "checkpoint_overhead", "st11_estimate_hours", "st11_reads", "st11_bound_hours", "timing"):
        print("  out[%r] = %s" % (k, kv.get(k)))
    ok &= kv.get("b17_estimate_hours") == "hours" and kv.get("st11_estimate_hours") == "st11_hours"
    ok &= kv.get("checkpoint_overhead") == "{'seconds': overhead, 'counts': counts}"
    ok &= kv.get("st11_bound_hours") == "p.contract.stops.st11_hours" and kv.get("timing") == "p.pre"
    ok &= not any(k in kv for k in OLD_FIELDS)
    logc = [ast.unparse(n) for n in ast.walk(pf) if isinstance(n, ast.Call) and ast.unparse(n.func) == "p.log"]
    print("  preflight log call(s): %s" % logc)

    print("\n== D. stops.st11")
    sh, si = defs(trees["stops.py"][0])["st11"], defs(trees["stops.py"][1])["st11"]
    ifs = [n for n in ast.walk(si) if isinstance(n, ast.If)]
    print("  condition %s | raise %s | identical to HEAD: %s" % (
        [ast.unparse(n.test) for n in ifs], [ast.unparse(r.exc) for n in ifs for r in n.body if isinstance(r, ast.Raise)],
        ast.dump(sh) == ast.dump(si)))
    ok &= [ast.unparse(n.test) for n in ifs] == ["not math.isfinite(estimate_hours) or estimate_hours > contract.stops.st11_hours"]
    ok &= ast.dump(sh) == ast.dump(si)

    print("\n== E. ST7 look-ahead and the plan, docstrings removed, HEAD vs index")
    for k in ("Pilot.run_seconds", "Pilot.eval_seconds", "test_evaluation_seconds", "evaluation_plan",
              "checkpoint_overhead_seconds", "Pilot.before_run", "Pilot.stop_in_step", "Pilot.stop_check"):
        same = strip_doc(dh[k]) == strip_doc(di[k])
        print("  pilot.%-28s code identical: %s | docstring identical: %s" % (k, same, ast.get_docstring(dh[k]) == ast.get_docstring(di[k])))
        ok &= same
    tes = di["test_evaluation_seconds"]
    print("  test_evaluation_seconds body (docstring aside): %s" % [ast.unparse(b) for b in tes.body[1:]])
    print("  its docstring now: %r" % ast.get_docstring(tes))

    print("\n== F. the renamed record fields and the readers of the step 2 record")
    hits, readers, pre_reads = [], [], []
    for rel in ls(repo, "HEAD", "metrix/e1-pilot/src", "metrix/e1-pilot/tests", "metrix/e1-pilot/run_pilot.py"):
        t = blob(repo, ":" + rel)
        if t is None:
            continue
        tree = ast.parse(t)
        for top in tree.body:
            for n in ast.walk(top):
                if isinstance(n, ast.Constant) and isinstance(n.value, str):
                    if any(o in n.value for o in OLD_FIELDS):
                        hits.append((rel.split("/")[-1], n.lineno, n.value))
                    if "step2_record" in n.value and rel.startswith("metrix/e1-pilot/src"):
                        readers.append((rel.split("/")[-1], getattr(top, "name", "?"), n.lineno, n.value))
                if rel.startswith("metrix/e1-pilot/src") and (
                        (isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Constant) and n.slice.value == "preflight")
                        or (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "get"
                            and n.args and isinstance(n.args[0], ast.Constant) and n.args[0].value == "preflight")):
                    pre_reads.append((rel.split("/")[-1], getattr(top, "name", "?"), n.lineno, ast.unparse(n)))
    print("  string constants naming the old fields in staged src/, tests/, run_pilot.py: %s" % hits)
    print("  string constants with 'step2_record' in src/: %s" % readers)
    print("  ['preflight'] / .get('preflight') in src/: %s" % pre_reads)
    ok &= not hits
    ok &= [(r[0], r[1]) for r in readers] == [("pilot.py", "test_evaluate")]
    ok &= [(r[0], r[1], r[3]) for r in pre_reads] == [("pilot.py", "test_evaluate", "step2['preflight']")]
    te = ast.unparse(di["test_evaluate"])
    print("  test_evaluate reads from step2: %s" % sorted(set(re.findall(r"step2\[[^\n]*?\]\[[^\n]*?\]", te))))
    ok &= sorted(set(re.findall(r"step2\[[^\n]*?\]\[[^\n]*?\]", te))) == ["step2['preflight']['timing']"]

    print("\n== G. B17")
    ch, eh = resolve_entries(trees["interpretations.py"][0])
    ci, ei = resolve_entries(trees["interpretations.py"][1])
    b_h = {e["id"]: e for e in eh}
    b_i = {e["id"]: e for e in ei}
    print("  ids %s" % [e["id"] for e in ei])
    ok &= [e["id"] for e in ei] == ["B%d" % k for k in range(1, 26)] == [e["id"] for e in eh]
    diff = [k for k in b_i if b_i[k] != b_h[k]]
    print("  entries different from HEAD: %s" % diff)
    ok &= diff == ["B17"]
    b17 = b_i["B17"]
    ruling = blob(repo, ":" + RULING)
    item1 = [ln for ln in ruling.split("\n") if ln.startswith("1. ")]
    print("  B17 status %r ruling %r | keys %s" % (b17["status"], b17.get("ruling"), sorted(b17)))
    print("  IMPL_C4_RULING.md item 1: %s" % item1)
    ok &= b17["status"] == "ACCEPTED（Review Gate 2026-11-27 修订）" and ("status 记为 %s。" % b17["status"]) in item1[0]
    ok &= b17.get("ruling") == "tasks/IMPL_C4_RULING.md 第 1 项" and len(item1) == 1
    ok &= item1[0].startswith("1. ST11 改为读「B17 估算 + checkpoint 开销」之和，超过 3.5 小时即停。")
    print("  B17 where %r" % b17["where"])
    ok &= "pilot.st11_estimate_hours" in b17["where"] and "pilot.checkpoint_overhead_seconds" in b17["where"]
    text = b17["text"]
    print("  B17 text: %s" % text)
    pats = [r"Preflight estimate \(the value ST11 compares with 3\.5 hours; Review Gate 2026-11-27 revision\) = B17's estimate \+ the checkpoint overhead\.",
            r"load x 32 base-model loads \(N, the 30 runs, N at TEST\)",
            r"\+ 30 checkpoints x \(2 x hash \+ save \+ reload \+ file hash\)",
            r"\+ reload x 18 further checkpoint reloads \(the 3 G0\.8 re-evaluations, the 15 TEST checkpoints\)",
            r"\+ hash x 17 TEST state hashes \(the 16 TEST models and N once more at the TEST begin\)",
            r"\+ file hash x 15 TEST checkpoint files",
            r"The ST7 look-ahead is not changed by this revision; the look-ahead before the TEST evaluation adds no margin\."]
    for pt in pats:
        print("    %-5s %s" % (bool(re.search(pt, text)), pt))
        ok &= bool(re.search(pt, text))
    old = b_h["B17"]["text"]
    old_formula = old[len("Preflight estimate = "):] if old.startswith("Preflight estimate = ") else None
    new_formula = re.search(r"B17's estimate = (.*?the GPU time already used\.)", text)
    same_formula = old_formula is not None and new_formula is not None and \
        re.sub(r"\s+", " ", old_formula) == re.sub(r"\s+", " ", new_formula.group(1))
    print("  B17's own formula: the parent's text after 'Preflight estimate = ' == the new text after \"B17's estimate = \" "
          "up to 'the GPU time already used.': %s" % same_formula)
    ok &= same_formula
    print("  parent B17 status %r (ruling %r)" % (b_h["B17"]["status"], b_h["B17"].get("ruling")))

    print("\n== H. 'for Review Gate' phrases left in pilot.py (informational)")
    hl = ph.split("\n")
    for no, ln in enumerate(pi.split("\n"), 1):
        if re.search(r"for Review Gate|Review Gate reviews", ln):
            print("  pilot.py:%d (line present in HEAD: %s) %s" % (no, ln in hl, ln.strip()))
    return bool(ok)


run(main)
