#!/usr/bin/env python3
"""Publish a locally verified ACT-003 archive as a GitHub Release asset.

Runs in Codespaces, where the ZIP exists. Uses GitHub CLI authentication.
The repository is public: publication is irreversible from a privacy standpoint.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

from evidence_archive import sha256_file, verify_archive


def run(*args, check=True):
    result = subprocess.run(args, capture_output=True, text=True, check=False)
    if check and result.returncode:
        raise RuntimeError(
            f"Command failed: {args[0]} {args[1] if len(args) > 1 else ''}: "
            + result.stderr[-1200:]
        )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default="leotree2020/OpenMythos")
    parser.add_argument("--branch", default="mini-mythos-research")
    parser.add_argument("--archive", default="research/mini_mythos/archives/act001_act002_evidence.zip")
    parser.add_argument("--replay", default="research/mini_mythos/archives/act003_replay_summary.json")
    parser.add_argument("--tag", default="mini-mythos-act003-gate-a")
    parser.add_argument("--publish", action="store_true",
                        help="Explicitly publish assets to the public GitHub repository")
    args = parser.parse_args()
    archive = Path(args.archive).resolve()
    replay = Path(args.replay).resolve()
    if not archive.is_file() or not replay.is_file():
        parser.error("Both local evidence ZIP and replay JSON must exist")
    manifest = verify_archive(archive)
    if manifest["completeness"] != "complete":
        parser.error("Refusing to publish a partial evidence archive")
    report = json.loads(replay.read_text(encoding="utf-8"))
    if not report.get("all_passed") or {
        r.get("case") for r in report.get("cases", []) if r.get("status") == "PASS"
    } != {"gqa22", "mla22", "mla44"}:
        parser.error("All three ACT-002 replay cases must PASS before publication")
    if report.get("archive_sha256") != sha256_file(archive):
        parser.error("Replay report was generated from a different archive")
    if report.get("source_files_with_drift") or report.get("environment_with_drift"):
        parser.error("Refusing to publish a replay with source/environment drift")
    expected = "787ace0458d1a3e049291648d9a7111a0d12e5d1cc113882fbebf8ccbcbc417d"
    actual = sha256_file(archive)
    if actual != expected:
        parser.error(f"Archive differs from recorded Gate A SHA-256: {actual}")
    print("Archive verified:", actual)
    print("Replay verified: all three cases PASS")
    print("Destination: PUBLIC https://github.com/" + args.repo)
    if not args.publish:
        print("DRY RUN: no upload performed. Review archive contents before --publish.")
        return
    run("gh", "auth", "status")
    release = run("gh", "release", "view", args.tag, "--repo", args.repo, check=False)
    if release.returncode:
        notes = (
            "ACT-003 Gate A evidence: 14 JSON result files, verified SHA-256 "
            + actual + ". Controlled replay: gqa22, mla22, mla44 PASS. "
            "CPU synthetic experiments; not independent replication or model-quality proof. "
            "Source: mini-mythos-research branch."
        )
        run("gh", "release", "create", args.tag, "--repo", args.repo,
            "--target", args.branch, "--title", "Mini-Mythos ACT-003 Gate A Evidence",
            "--notes", notes)
    run("gh", "release", "upload", args.tag, str(archive), str(replay),
        "--repo", args.repo, "--clobber")
    print("PUBLISHED: https://github.com/" + args.repo + "/releases/tag/" + args.tag)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        raise SystemExit(f"FAIL: {exc}")
