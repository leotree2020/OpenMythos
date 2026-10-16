#!/usr/bin/env python3
"""ACT-003: offline, integrity-checked archive of ACT-001/ACT-002 JSON evidence.

Only an explicit allowlist of experiment result JSONs is collected. The
archive is written LOCALLY, never uploaded to GitHub or another service.
SHA-256 detects accidental changes, but does not authenticate the publisher.
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path, PurePosixPath
import platform
import subprocess
import sys
import zipfile

FORMAT_VERSION = 1
RESULTS_ROOT = "research/mini_mythos/results"
DEFAULT_ARCHIVE = "research/mini_mythos/archives/act001_act002_evidence.zip"
REQUIRED = (
    "act_gqa.json",
    "act_mla.json",
    "act002_gqa_seed22.json",
    "act002_mla_seed22.json",
    "act002_mla_seed44.json",
    *(f"multiseed/act_ab_seed_{seed}.json" for seed in (11, 22, 33, 44, 55)),
)
OPTIONAL = (
    "act_ab.json", "act_dynamics_seed22.json",
    "smoke.json", "smoke_gqa.json", "smoke_mla.json",
    "provenance.json", "static_audit.json", "pilot.json",
)
SOURCES = (
    "open_mythos/main.py",
    "research/mini_mythos/scripts/common.py",
    "research/mini_mythos/scripts/act_math.py",
    "research/mini_mythos/scripts/act_remainder.py",
    "research/mini_mythos/scripts/act_dynamics.py",
    "research/mini_mythos/scripts/act_ab.py",
    "research/mini_mythos/scripts/act_counterfactual.py",
    "research/mini_mythos/scripts/act_counterfactual_math.py",
    "research/mini_mythos/scripts/evidence_archive.py",
    "research/mini_mythos/scripts/evidence_replay.py",
)
MAX_ITEM_BYTES = 15 * 1024 * 1024
MAX_TOTAL_BYTES = 75 * 1024 * 1024


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git(repo, *args):
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else None


def package_version(name):
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def validate_result(name, document):
    """Verify identity and basic schema, not scientific correctness."""
    if not isinstance(document, dict):
        raise ValueError(f"{name}: expected JSON object")
    if name in ("act_gqa.json", "act_mla.json"):
        expected = name.removeprefix("act_").removesuffix(".json")
        if document.get("attention") != expected or not isinstance(document.get("depth_results"), list):
            raise ValueError(f"{name}: wrong attention or missing depth_results")
    elif name.startswith("act002_"):
        expected_attention = name.split("_")[1]
        expected_seed = int(name.split("seed")[1].split(".")[0])
        matches = document.get("results", [])
        if (document.get("experiment") != "ACT-002_same_weight_counterfactual"
                or document.get("seed") != expected_seed
                or not isinstance(matches, list) or len(matches) != 1
                or matches[0].get("attention") != expected_attention
                or matches[0].get("requested_depth") != 2
                or not isinstance(matches[0].get("train_trace"), list)
                or not isinstance(matches[0].get("heldout"), dict)):
            raise ValueError(f"{name}: ACT-002 identity/schema mismatch")
    elif name.startswith("multiseed/act_ab_seed_"):
        expected_seed = int(name.split("_seed_")[1].split(".")[0])
        matches = document.get("results", [])
        if (document.get("experiment") != "act_final_remainder_ab"
                or document.get("seed") != expected_seed
                or not isinstance(matches, list) or len(matches) != 4
                or {(r.get("attention"), r.get("requested_depth")) for r in matches}
                != {("gqa", 1), ("gqa", 2), ("mla", 1), ("mla", 2)}):
            raise ValueError(f"{name}: ACT-001 seed/configuration mismatch")


def selected_artifacts(repo, *, partial=False):
    results = (repo / RESULTS_ROOT)
    if not results.is_dir() or results.is_symlink():
        raise FileNotFoundError(f"Expected an ordinary results directory: {results}")
    missing = [name for name in REQUIRED if not (results / name).is_file()]
    if missing and not partial:
        raise FileNotFoundError(
            "Missing required results: " + ", ".join(missing)
            + ". Run the documented ACT-001/002 cases, or explicitly choose --allow-partial."
        )
    names = [name for name in REQUIRED + OPTIONAL if (results / name).is_file()]
    if not names:
        raise ValueError("No allowlisted result JSON files available")
    files = []
    payloads = {}
    total_size = 0
    for name in names:
        path = results / name
        if path.is_symlink() or not path.resolve().is_relative_to(results.resolve()):
            raise ValueError(f"Symlink/path escape is forbidden: {name}")
        if path.stat().st_size > MAX_ITEM_BYTES:
            raise ValueError(f"Result file too large: {name}")
        raw = path.read_bytes()
        total_size += len(raw)
        if total_size > MAX_TOTAL_BYTES:
            raise ValueError("Collected JSON exceeds size limit")
        try:
            document = json.loads(raw)
        except (ValueError, UnicodeError) as exc:
            raise ValueError(f"Unreadable JSON {name}: {exc}") from exc
        validate_result(name, document)
        stored = f"results/{name}"
        files.append({
            "path": stored,
            "bytes": len(raw),
            "sha256": digest(raw),
            "reported_upstream_commit": document.get("upstream_commit"),
            "reported_seed": document.get("seed"),
            "reported_attention": document.get("attention"),
            "experiment": document.get("experiment"),
        })
        payloads[stored] = raw
    return files, payloads, missing


def archive_manifest(repo, records, missing):
    source_hashes = {}
    for name in SOURCES:
        source = repo / name
        if not source.is_file() or source.is_symlink():
            raise FileNotFoundError(f"Source file missing or symlink: {source}")
        source_hashes[name] = sha256_file(source)
    return {
        "format_version": FORMAT_VERSION,
        "purpose": "ACT-001/ACT-002 exploratory CPU research evidence; no model quality claims",
        "completeness": "partial" if missing else "complete",
        "missing_required_results": missing,
        "snapshot": {
            "git_commit_at_pack_time": git(repo, "rev-parse", "HEAD"),
            "branch_at_pack_time": git(repo, "branch", "--show-current"),
            "worktree_has_changes_at_pack_time": bool(git(repo, "status", "--porcelain")),
            "source_sha256_at_pack_time": source_hashes,
            "python": sys.version.split()[0],
            "torch_distribution": package_version("torch"),
            "transformers_distribution": package_version("transformers"),
            "system": platform.system(),
            "machine": platform.machine(),
        },
        "warning": (
            "Snapshot SHA and source hashes are recorded at ARCHIVING time, not at each "
            "experiment's run time. Per-result reported_upstream_commit is retained. "
            "A SHA-256 manifest detects corruption but is not a digital signature."
        ),
        "artifacts": records,
    }


def _safe_name(name):
    if not isinstance(name, str) or "\\" in name or name.startswith("/"):
        return False
    segments = PurePosixPath(name).parts
    return bool(segments) and all(p not in ("", ".", "..") for p in segments)


def verify_archive(path):
    """Verify internal integrity without extraction or trusting ZIP paths."""
    path = Path(path)
    with zipfile.ZipFile(path, "r") as archive:
        members = archive.infolist()
        names = [m.filename for m in members]
        if len(names) != len(set(names)) or any(not _safe_name(name) for name in names):
            raise ValueError("Duplicate or unsafe ZIP paths")
        if "manifest.json" not in names:
            raise ValueError("Missing manifest.json")
        if len(names) > len(REQUIRED) + len(OPTIONAL) + 1:
            raise ValueError("Unexpected number of ZIP entries")
        if sum(m.file_size for m in members) > MAX_TOTAL_BYTES:
            raise ValueError("Uncompressed ZIP exceeds size limit")
        for m in members:
            if m.is_dir() or m.file_size > MAX_ITEM_BYTES:
                raise ValueError("Directory or oversized member in archive")
        raw_manifest = archive.read("manifest.json")
        if len(raw_manifest) > 1024 * 1024:
            raise ValueError("Manifest is too large")
        manifest = json.loads(raw_manifest)
        if manifest.get("format_version") != FORMAT_VERSION:
            raise ValueError("Unsupported manifest format")
        records = manifest.get("artifacts")
        if not isinstance(records, list) or not records:
            raise ValueError("Empty or invalid manifest artifacts")
        expected = set()
        for record in records:
            if not isinstance(record, dict):
                raise ValueError("Invalid manifest entry")
            name = record.get("path")
            if (not _safe_name(name) or not name.startswith("results/")
                    or name.removeprefix("results/") not in REQUIRED + OPTIONAL
                    or name in expected):
                raise ValueError(f"Unexpected or duplicated artifact path: {name}")
            expected.add(name)
            if name not in names:
                raise ValueError(f"Missing archived evidence: {name}")
            raw = archive.read(name)
            if len(raw) != record.get("bytes") or digest(raw) != record.get("sha256"):
                raise ValueError(f"SHA-256/size mismatch: {name}")
            document = json.loads(raw)
            validate_result(name.removeprefix("results/"), document)
            if document.get("upstream_commit") != record.get("reported_upstream_commit"):
                raise ValueError(f"Recorded experiment commit mismatch: {name}")
        if set(names) != expected | {"manifest.json"}:
            raise ValueError("Unlisted file in ZIP archive")
        missing = [name for name in REQUIRED if f"results/{name}" not in expected]
        if manifest.get("completeness") != ("partial" if missing else "complete"):
            raise ValueError("Manifest completeness flag mismatch")
        if manifest.get("missing_required_results") != missing:
            raise ValueError("Manifest missing_required_results mismatch")
    return manifest


def pack(repo, output, allow_partial=False):
    repo = Path(repo).resolve()
    if not (repo / "open_mythos/main.py").is_file():
        raise FileNotFoundError("Must run inside the OpenMythos checkout")
    records, payloads, missing = selected_artifacts(repo, partial=allow_partial)
    manifest = archive_manifest(repo, records, missing)
    output = Path(output).resolve()
    if output.is_relative_to((repo / RESULTS_ROOT).resolve()):
        raise ValueError("Archive must not be written inside the results folder")
    if output.is_symlink():
        raise ValueError("Refusing to overwrite symlink archive")
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_name(output.name + ".tmp")
    try:
        with zipfile.ZipFile(temp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            z.writestr("manifest.json", json.dumps(
                manifest, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8"))
            for name in sorted(payloads):
                z.writestr(name, payloads[name])
        verify_archive(temp)
        os.replace(temp, output)
    finally:
        if temp.exists():
            temp.unlink()
    print(f"Archived {len(records)} JSON files; completeness={manifest['completeness']}")
    print(f"Archive: {output}")
    print(f"Archive SHA-256: {sha256_file(output)}")
    print("No files were uploaded to GitHub.")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    p_pack = subs.add_parser("pack", help="Collect a local ZIP with SHA-256 manifest")
    p_pack.add_argument("--repo", default=".")
    p_pack.add_argument("--out", default=DEFAULT_ARCHIVE)
    p_pack.add_argument("--allow-partial", action="store_true")
    p_verify = subs.add_parser("verify", help="Verify archive hashes and JSON identities")
    p_verify.add_argument("archive", nargs="?", default=DEFAULT_ARCHIVE)
    args = parser.parse_args()
    try:
        if args.command == "pack":
            pack(args.repo, args.out, allow_partial=args.allow_partial)
        else:
            manifest = verify_archive(args.archive)
            print(f"PASS: verified {len(manifest['artifacts'])} JSON files")
            print("Completeness:", manifest["completeness"])
            print("SHA-256:", sha256_file(args.archive))
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile) as exc:
        parser.exit(1, f"FAIL: {exc}\n")


if __name__ == "__main__":
    main()
