#!/usr/bin/env python3
"""Read-only five-module inventory: tracked files, exact text LOC, and SHA-256.

Never modifies source. Outputs only to explicit --output path (optional).
Classification v1 is exclusive and matches PROJECT_MAP.md's frozen baseline.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

CATEGORIES = ("核心模型", "训练", "实验与工具", "测试", "文档与证据")
TEXT_EXTS = {".py", ".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".sh", ".patch", ".gitignore"}


def classify(p):
    if p.startswith("open_mythos/"):
        return CATEGORIES[0]
    if p.startswith("training/") or p == "research/mini_mythos/scripts/pilot_train.py":
        return CATEGORIES[1]
    if (p.startswith("research/mini_mythos/docs/")
            or p.startswith("research/mini_mythos/backup/")
            or p.endswith(".md") or p in ("README.md", "LICENSE")
            or p.startswith("research/mini_mythos/gate2_2/evidence/")
            or p.startswith("research/mini_mythos/docs/p1b/ci/")):
        return CATEGORIES[4]
    if ("/test_" in p or p.startswith("tests/")
            or p.startswith("research/mini_mythos/tests/")
            or p.startswith("research/mini_mythos/interfaces/test_")
            or p.startswith(".github/")):
        return CATEGORIES[3]
    return CATEGORIES[2]


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args])


def inventory(root):
    head = git(root, "rev-parse", "HEAD").decode().strip()
    status = git(root, "status", "--porcelain=v1").decode("utf-8", "replace").splitlines()
    names = [x.decode("utf-8") for x in git(root, "ls-files", "-z").split(b"\0") if x]
    summary = {c: {"files": 0, "python_files": 0, "bytes": 0,
                   "physical_lines": 0, "nonempty_lines": 0,
                   "python_comment_lines": 0, "loc_measured_files": 0}
               for c in CATEGORIES}
    rows = []
    for name in names:
        path = root / name
        cat = classify(name)
        row = {"path": name, "module": cat, "status": "OK"}
        if not path.is_file():
            row["status"] = "MISSING_IN_WORKTREE"
            rows.append(row)
            continue
        raw = path.read_bytes()
        row["bytes"] = len(raw)
        row["sha256"] = hashlib.sha256(raw).hexdigest()
        s = summary[cat]
        s["files"] += 1
        s["bytes"] += len(raw)
        if path.suffix == ".py":
            s["python_files"] += 1
        if path.suffix in TEXT_EXTS or path.name == ".gitignore":
            try:
                lines = raw.decode("utf-8").splitlines()
            except UnicodeDecodeError:
                row["status"] = "NOT_MEASURED_NON_UTF8"
            else:
                row["physical_lines"] = len(lines)
                row["nonempty_lines"] = sum(bool(line.strip()) for line in lines)
                row["python_comment_lines"] = (
                    sum(line.lstrip().startswith("#") for line in lines)
                    if path.suffix == ".py" else None)
                s["physical_lines"] += row["physical_lines"]
                s["nonempty_lines"] += row["nonempty_lines"]
                s["python_comment_lines"] += row["python_comment_lines"] or 0
                s["loc_measured_files"] += 1
        else:
            row["status"] = "NOT_MEASURED_NON_TEXT"
        rows.append(row)
    return {"schema": "openmythos-project-map/v1", "git_head": head,
            "git_status_porcelain": status, "classification": "exclusive-v1",
            "loc_definition": "UTF-8 physical lines (splitlines), nonempty lines, Python lines beginning with #; not AST logical SLOC",
            "summary": summary, "files": rows}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo", type=Path, default=Path("."))
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    root = a.repo.resolve()
    result = inventory(root)
    encoded = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if a.output:
        dest = a.output.resolve()
        if dest.is_relative_to(root) and dest.relative_to(root).as_posix() in {
                x["path"] for x in result["files"]}:
            raise SystemExit("Refusing to overwrite any tracked file")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(encoded, encoding="utf-8")
        print(f"Wrote {dest}")
    else:
        print(encoded, end="")


if __name__ == "__main__":
    main()
