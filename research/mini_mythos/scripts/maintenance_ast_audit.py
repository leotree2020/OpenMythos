#!/usr/bin/env python3
"""Read-only AST maintenance audit for tracked-style source directories.

Never imports/executes project code. Metrics are triage signals, NOT
proof of dead code, a security exploit, or faulty runtime behavior.

Print a deterministic ranked summary; --out writes full JSON evidence
for manual review. No files are deleted, renamed, or auto-refactored.
"""
import argparse
import ast
from collections import Counter
import json
from pathlib import Path

SCAN_DIRS = ("open_mythos", "training", "examples", "tests",
             "research/mini_mythos/scripts", "research/mini_mythos/tests")
CONTROL = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try,
           ast.With, ast.AsyncWith, ast.IfExp, ast.Match)
FRAMEWORK_METHODS = frozenset((
    "__init__", "__iter__", "__getitem__", "__len__", "__call__",
    "__enter__", "__exit__", "__next__", "__getattr__", "__setattr__",
    "forward", "setup", "setUp", "tearDown", "main",
))


def py_files(root):
    roots = [root / "example.py"] + [root / p for p in SCAN_DIRS]
    found = []
    for loc in roots:
        if loc.is_file() and loc.suffix == ".py":
            found.append(loc)
        elif loc.is_dir():
            found.extend(loc.rglob("*.py"))
    return sorted(set(found))


def walk_own_body(node):
    """Yield node descendants but stop before separate function/class scopes."""
    stack = [node]
    while stack:
        here = stack.pop()
        yield here
        children = ast.iter_child_nodes(here)
        if here is not node:
            children = () if isinstance(here, (ast.FunctionDef, ast.AsyncFunctionDef,
                                               ast.ClassDef, ast.Lambda)) else children
        stack.extend(reversed(list(children)))


def complexity_of(node):
    """McCabe-like branch approximation within a single lexical function."""
    score = 1
    for child in walk_own_body(node):
        if child is node:
            continue
        if isinstance(child, (ast.If, ast.For, ast.AsyncFor, ast.While,
                              ast.IfExp, ast.ExceptHandler)):
            score += 1
        elif isinstance(child, ast.BoolOp):
            score += len(child.values) - 1
        elif isinstance(child, ast.Match):
            score += max(0, len(child.cases) - 1)
        elif isinstance(child, ast.comprehension):
            score += 1 + len(child.ifs)
    return score


def depth_of(node):
    """Maximum nested compound-statement depth, not lexical class nesting."""
    def recur(child, depth):
        if child is not node and isinstance(
            child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)
        ):
            return depth
        next_depth = depth + (child is not node and isinstance(child, CONTROL))
        return max([next_depth] + [
            recur(grandchild, next_depth) for grandchild in ast.iter_child_nodes(child)
        ])
    return recur(node, 0)


class Collector(ast.NodeVisitor):
    def __init__(self):
        self.scopes = []
        self.functions = []
        self.calls = Counter()
        self.names_used = Counter()
        self.exports = []
        self.declared = set()
        self.risk_patterns = []

    def visit_FunctionDef(self, node):
        self._function(node)

    def visit_AsyncFunctionDef(self, node):
        self._function(node)

    def _function(self, node):
        qual = ".".join([name for _, name in self.scopes] + [node.name])
        lexical_parent = self.scopes[-1][0] if self.scopes else "module"
        self.functions.append({
            "name": node.name, "qualname": qual, "line": node.lineno,
            "end_line": node.end_lineno,
            "lines": node.end_lineno - node.lineno + 1,
            "complexity_approx": complexity_of(node),
            "max_control_nesting": depth_of(node),
            "lexical_parent": lexical_parent,
            "decorated": bool(node.decorator_list),
        })
        if not self.scopes:
            self.declared.add(node.name)
        # Visit decorators/defaults outside the function scope too.
        for dec in node.decorator_list:
            self.visit(dec)
        for default in list(node.args.defaults) + list(node.args.kw_defaults):
            if default is not None:
                self.visit(default)
        self.scopes.append(("function", node.name))
        for statement in node.body:
            self.visit(statement)
        self.scopes.pop()

    def visit_ClassDef(self, node):
        if not self.scopes:
            self.declared.add(node.name)
        self.scopes.append(("class", node.name))
        for stmt in node.body:
            self.visit(stmt)
        self.scopes.pop()

    def visit_Import(self, node):
        if not self.scopes:
            self.declared.update((x.asname or x.name.split(".")[0]) for x in node.names)

    def visit_ImportFrom(self, node):
        if not self.scopes:
            self.declared.update((x.asname or x.name) for x in node.names)

    def visit_Assign(self, node):
        if not self.scopes:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.declared.add(target.id)
                    if target.id == "__all__" and isinstance(node.value, (ast.List, ast.Tuple)):
                        self.exports.extend(x.value for x in node.value.elts
                                            if isinstance(x, ast.Constant)
                                            and isinstance(x.value, str))
        self.generic_visit(node)

    def visit_Call(self, node):
        func = node.func
        if isinstance(func, (ast.Name, ast.Attribute)):
            self.calls[func.id if isinstance(func, ast.Name) else func.attr] += 1
        if isinstance(func, ast.Attribute) and func.attr == "load":
            if isinstance(func.value, ast.Name) and func.value.id == "torch":
                for keyword in node.keywords:
                    if keyword.arg == "weights_only" and isinstance(keyword.value, ast.Constant) and keyword.value.value is False:
                        self.risk_patterns.append({
                            "line": node.lineno, "kind": "torch.load_weights_only_false",
                            "detail": "Untrusted pickle checkpoint may execute code; manual review required",
                        })
        if isinstance(func, ast.Name) and func.id == "load_dataset":
            if not any(k.arg == "revision" for k in node.keywords):
                self.risk_patterns.append({
                    "line": node.lineno, "kind": "hf_load_dataset_unpinned_revision",
                    "detail": "Dataset revision is not explicit in this call; review provenance",
                })
        self.generic_visit(node)

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            self.names_used[node.id] += 1

    def visit_Attribute(self, node):
        if isinstance(node.ctx, ast.Load):
            self.names_used[node.attr] += 1
        self.generic_visit(node)


def scan(root):
    root = Path(root).resolve()
    records = []
    calls, references = Counter(), Counter()
    production_calls, test_calls = Counter(), Counter()
    patterns, missing_exports = [], []
    files = py_files(root)
    for file in files:
        rel = file.relative_to(root).as_posix()
        content = file.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=rel)
        finder = Collector()
        finder.visit(tree)
        calls.update(finder.calls)
        references.update(finder.names_used)
        if rel.startswith("tests/") or "/tests/" in rel:
            test_calls.update(finder.calls)
        else:
            production_calls.update(finder.calls)
        for func in finder.functions:
            func["file"] = rel
            func["in_test"] = rel.startswith("tests/") or "/tests/" in rel
            records.append(func)
        for risk in finder.risk_patterns:
            patterns.append(dict(risk, file=rel))
        for name in sorted(set(finder.exports) - finder.declared):
            missing_exports.append({"file": rel, "symbol": name,
                                    "finding": "__all__ missing binding"})
        if rel.startswith("training/"):
            # This is a REVIEW FLAG, not proof the two partitions overlap.
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or node.name != "__iter__":
                    continue
                own_calls = [x for x in walk_own_body(node) if isinstance(x, ast.Call)]
                if (any(isinstance(x.func, ast.Attribute) and x.func.attr == "shard"
                        for x in own_calls)
                    and any(isinstance(x.func, ast.Name) and x.func.id == "load_dataset"
                            for x in own_calls)):
                    patterns.append({
                        "file": rel, "line": node.lineno,
                        "kind": "hf_manual_shard_inside_iter",
                        "detail": "HF IterableDataset may auto-shard in PyTorch workers; trace exact policy",
                    })
    flags = []
    for func in records:
        # No claim that dynamic dispatch/callback/CLI entrypoints are unused.
        name = func["name"]
        if (name.startswith("_") and not name.startswith("__")
                and name not in FRAMEWORK_METHODS and not func["in_test"]
                and calls[name] == 0 and references[name] == 0
                and not func["decorated"]):
            flags.append({"file": func["file"], "qualname": func["qualname"],
                          "line": func["line"], "finding": "no_static_reference_candidate",
                          "confidence": "low: reflection, callbacks and external users not traced"})
    test_only = [
        {"file": f["file"], "qualname": f["qualname"],
         "line": f["line"], "finding": "test_only_static_call_candidate",
         "confidence": "low: name-based AST cannot see dynamic/external calls"}
        for f in records if not f["in_test"] and f["name"] not in FRAMEWORK_METHODS
        and not f["name"].startswith("__")
        and production_calls[f["name"]] == 0 and test_calls[f["name"]] > 0
    ]
    ranked = sorted((f for f in records if not f["in_test"]),
                    key=lambda f: (-f["complexity_approx"], -f["lines"],
                                   f["file"], f["line"]))
    hotspots = sorted((
        f for f in records if not f["in_test"] and
        (f["complexity_approx"] >= 12 or f["lines"] >= 70
         or f["max_control_nesting"] >= 4
         or f["lexical_parent"] == "function")
    ), key=lambda f: (-f["complexity_approx"], -f["lines"], f["file"], f["line"]))
    sizes = [{"file": p.relative_to(root).as_posix(),
              "lines": len(p.read_text(encoding="utf-8").splitlines())}
             for p in files]
    return {
        "protocol": "MYTHOS_READ_ONLY_AST_MAINTENANCE_AUDIT_V1",
        "limits": [
            "AST-only: no imports, no execution, no runtime instrumentation",
            "Complexity is McCabe-like heuristic, not Radon or a formal security test",
            "Call matching is name-based and incomplete; dynamic dispatch, plugins, public APIs can be missed",
            "Possible unused is NEVER permission to remove code",
            "Function/statement line counts include docstrings and comments",
        ],
        "summary": {
            "python_files": len(files),
            "functions_and_methods": len(records),
            "nested_function_definitions": sum(f["lexical_parent"] == "function" for f in records),
            "hotspot_count": len(hotspots),
            "low_confidence_unreferenced_private_candidates": len(flags),
            "test_only_static_call_candidates": len(test_only),
            "missing_declared_exports": len(missing_exports),
            "review_risk_patterns": len(patterns),
        },
        "long_files": sorted((x for x in sizes if x["lines"] >= 400),
                             key=lambda x: (-x["lines"], x["file"])),
        "complexity_hotspots": hotspots,
        "nested_function_definitions": [f for f in records
                                        if f["lexical_parent"] == "function"],
        "top_20_by_complexity": ranked[:20],
        "missing_exports": sorted(missing_exports,
                                  key=lambda x: (x["file"], x["symbol"])),
        "review_patterns": sorted(patterns,
                                  key=lambda x: (x["file"], x["line"], x["kind"])),
        "potential_unreferenced_private": sorted(
            flags, key=lambda x: (x["file"], x["line"])
        ),
        "test_only_static_call_candidates": sorted(
            test_only, key=lambda x: (x["file"], x["line"])
        ),
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", default=".")
    p.add_argument("--out", default=None,
                   help="Optional JSON report path (prefer Git-ignored results)")
    args = p.parse_args()
    result = scan(args.repo)
    print("Read-only AST audit:", json.dumps(result["summary"], sort_keys=True))
    print("Top complexity candidates (static approximation):")
    for f in result["top_20_by_complexity"][:12]:
        print(f"  {f['file']}:{f['line']} {f['qualname']} "
              f"lines={f['lines']} cc~{f['complexity_approx']} "
              f"nest={f['max_control_nesting']}")
    print("Risk patterns for manual review:")
    for f in result["review_patterns"]:
        print(f"  {f['file']}:{f['line']} {f['kind']}")
    print("Missing __all__ exports:")
    for f in result["missing_exports"]:
        print(f"  {f['file']}: {f['symbol']}")
    if args.out:
        target = Path(args.out)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result, indent=2, ensure_ascii=False,
                                     sort_keys=True) + "\n", encoding="utf-8")
        print("Saved JSON:", target)


if __name__ == "__main__":
    main()
