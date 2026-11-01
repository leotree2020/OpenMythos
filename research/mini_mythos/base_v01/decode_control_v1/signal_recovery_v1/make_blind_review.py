"""Create a complete 84-sample metadata-blind review pack using only stdlib.

The original completed run is read-only. Output is an exclusively created,
external operator directory. Reviewers read BLIND_SAMPLES.json only, never
MAPPING.json or the source generation records. This is metadata blinding, not
cryptographic anonymity or a claim of independence from project history.
"""

import argparse
import hashlib
import json
from pathlib import Path
import sys


EXPERIMENT = "MYTHOS-DECODE-CONTROL-V1"
POLICY_PANELS = {"G": (0,), "S": (1, 2, 3), "P": (1, 2, 3)}
EXPECTED = {(policy, panel, idx) for policy, panels in POLICY_PANELS.items()
            for panel in panels for idx in range(1, 13)}


class BlindPackBlocked(Exception):
    def __init__(self, reason, actual=None):
        super().__init__(reason)
        self.reason = reason
        self.actual = actual


def require(condition, reason, actual=None):
    if not condition:
        raise BlindPackBlocked(reason, actual)


def parse_json(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key: " + key)
            result[key] = value
        return result

    def bad_constant(value):
        raise ValueError("nonfinite JSON constant: " + value)

    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs,
                      parse_constant=bad_constant)


def digest(path):
    sha = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(block)
            size += len(block)
    return {"size": size, "sha256": sha.hexdigest()}


def write_json(path, value):
    raw = (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)
           + "\n").encode("utf-8")
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
    return {"size": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def valid_ids(ids):
    return isinstance(ids, list) and all(type(idx) is int and 0 <= idx < 32768 for idx in ids)


def create_records(run_dir):
    """Read a sealed PASS run; return blind rows, private mapping and provenance."""
    summary_path = run_dir / "public" / "summary.json"
    require(summary_path.is_file(), "terminal run summary is missing")
    summary = parse_json(summary_path)
    require(summary.get("experiment") == EXPERIMENT and summary.get("run_id") == run_dir.name,
            "terminal summary identifies a different experiment or run")
    require(summary.get("engineering_status") == "PASS", "run engineering acceptance is not PASS")
    manifest_path = run_dir / "FULL_MANIFEST.json"
    require(manifest_path.is_file(), "sealed FULL_MANIFEST.json is missing")
    manifest = parse_json(manifest_path)
    entries = manifest.get("files")
    require(isinstance(entries, list), "full manifest file list is invalid")
    manifest_by_path = {}
    for item in entries:
        require(isinstance(item, dict) and isinstance(item.get("path"), str),
                "manifest entry is malformed")
        rel = item["path"]
        require(rel not in manifest_by_path, "duplicate manifest path")
        manifest_by_path[rel] = item

    source_dir = run_dir / "first" / "generation" / "public"
    require(source_dir.is_dir() and source_dir.resolve().is_relative_to(run_dir),
            "expected first/generation/public directory is missing or external")
    sources = sorted(source_dir.glob("*generation.json"))
    require(len(sources) == 84, "expected exactly 84 generation files; no partial review pack",
            {"expected": 84, "actual": len(sources)})
    blind_rows, mapping, identities, anonymous_ids = [], [], set(), set()
    prompts_by_id = {}

    for source in sources:
        require(source.is_file() and not source.is_symlink()
                and source.resolve().is_relative_to(run_dir), "generation source path is invalid")
        relative = source.relative_to(run_dir).as_posix()
        require(relative in manifest_by_path, "generation source is absent from sealed manifest")
        fingerprint = digest(source)
        entry = manifest_by_path[relative]
        require(fingerprint == {"size": entry.get("size"), "sha256": entry.get("sha256")},
                "generation source does not match sealed bytes")
        document = parse_json(source)
        require(isinstance(document, dict), "generation record is not an object")
        policy, panel, idx = document.get("policy"), document.get("panel"), document.get("prompt_id")
        require(isinstance(policy, str) and policy in POLICY_PANELS,
                "generation policy is outside the frozen matrix")
        require(type(panel) is int and panel in POLICY_PANELS[policy]
                and type(idx) is int and 1 <= idx <= 12, "generation panel or prompt ID is invalid")
        identity = (policy, panel, idx)
        require(identity not in identities, "duplicate generation identity")
        identities.add(identity)
        require(source.name == "%s_panel%d_prompt%02d_generation.json" % identity,
                "generation filename and recorded identity disagree")
        quality = document.get("quality")
        require(isinstance(quality, dict) and type(quality.get("id")) is int and quality["id"] == idx,
                "quality record prompt identity differs")
        prompt, continuation = quality.get("prompt"), quality.get("text_continuation")
        require(isinstance(prompt, str) and bool(prompt), "prompt text is missing")
        require(isinstance(continuation, str) or continuation is None,
                "effective continuation must be a string or original null")
        require(idx not in prompts_by_id or prompts_by_id[idx] == prompt,
                "prompt text differs across frozen conditions")
        prompts_by_id[idx] = prompt
        automatic = quality.get("auto")
        require(isinstance(automatic, dict) and type(automatic.get("passed")) is bool,
                "automatic quality outcome is missing or malformed")
        if continuation is None:
            require(automatic.get("decode_error") is not None and automatic["passed"] is False,
                    "null continuation lacks its original decode-failure evidence")
        input_ids = quality.get("input_ids")
        raw_ids = quality.get("raw_new_ids")
        full_ids = quality.get("full_generated_ids")
        require(valid_ids(input_ids) and 0 < len(input_ids) <= 48
                and valid_ids(raw_ids) and len(raw_ids) == 64
                and valid_ids(full_ids) and full_ids == input_ids + raw_ids,
                "generation token coverage or prefix is invalid")
        eos = raw_ids.index(1) if 1 in raw_ids else None
        effective_ids = raw_ids[:eos] if eos is not None else raw_ids
        require(quality.get("eos_id") == 1 and quality.get("eos_position") == eos
                and quality.get("continuation_ids") == effective_ids,
                "effective token slice differs from the first-EOS rule")
        require(document.get("observed_steps") == 64, "generation was not completed for 64 steps")

        key = "%s:%s:%d:%d" % (EXPERIMENT, policy, panel, idx)
        anonymous_id = hashlib.sha256(key.encode("utf-8")).hexdigest()
        require(anonymous_id not in anonymous_ids, "anonymous identifier collision")
        anonymous_ids.add(anonymous_id)
        blind_rows.append({"anonymous_id": anonymous_id, "prompt": prompt,
                           "effective_continuation": continuation})
        mapping.append({"anonymous_id": anonymous_id, "policy": policy,
                        "panel": panel, "id": idx, "auto_pass": automatic["passed"],
                        "source": relative, "source_bytes": fingerprint})

    require(identities == EXPECTED and len(blind_rows) == 84,
            "the complete G12/S36/P36 matrix is required")
    blind_rows.sort(key=lambda row: row["anonymous_id"])
    mapping.sort(key=lambda row: row["anonymous_id"])
    return blind_rows, mapping, {
        "run_id": run_dir.name, "run_summary": digest(summary_path),
        "full_manifest": digest(manifest_path), "source_records": 84,
        "anonymous_id_formula": "sha256(UTF-8('MYTHOS-DECODE-CONTROL-V1:' + policy + ':' + panel_decimal + ':' + prompt_id_decimal))",
        "ordering": "ascending anonymous_id", "text_cleaning": False,
        "new_model_or_tokenizer_execution": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, help="Completed, sealed original run directory")
    parser.add_argument("--output", required=True, help="New operator directory outside the original run")
    args = parser.parse_args()
    run_dir = Path(args.run).resolve(strict=True)
    output_dir = Path(args.output).resolve()
    require(run_dir.is_dir(), "run path is not a directory")
    require(not output_dir.is_relative_to(run_dir), "output must be outside the immutable run")
    require(not output_dir.exists(), "output directory already exists; no overwrite")
    output_dir.mkdir(parents=True, exist_ok=False)
    try:
        blind, mapping, provenance = create_records(run_dir)
        mapping_info = write_json(output_dir / "MAPPING.json", mapping)
        blind_info = write_json(output_dir / "BLIND_SAMPLES.json", blind)
        result = {
            "Purpose": "Complete metadata-blind review export without new generation",
            "Environment": "standard library only; original run read-only",
            "Input": provenance,
            "Expected": "84 exact effective continuations, three fields each, deterministically anonymized and sorted",
            "Actual": {"sample_count": len(blind), "blind_file": blind_info,
                       "private_mapping_file": mapping_info},
            "Status": "PASS",
            "reviewer_instruction": "Read BLIND_SAMPLES.json only; do not read MAPPING.json or original generation metadata.",
        }
        write_json(output_dir / "PACK_STATUS.json", result)
        print(json.dumps({"Status": "PASS", "sample_count": 84,
                          "output": str(output_dir), "blind_sha256": blind_info["sha256"]}))
        return 0
    except Exception as exc:
        result = {"Purpose": "Complete metadata-blind review export", "Status": "BLOCKED",
                  "Expected": "Complete valid 84-sample matrix before review",
                  "Actual": {"reason": getattr(exc, "reason", str(exc)),
                             "detail": getattr(exc, "actual", None), "type": type(exc).__name__},
                  "reviewer_instruction": "Do not review any partial output from this directory."}
        write_json(output_dir / "PACK_STATUS.json", result)
        print(json.dumps({"Status": "BLOCKED", "reason": result["Actual"]["reason"]}))
        return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BlindPackBlocked as exc:
        print(json.dumps({"Status": "BLOCKED", "reason": exc.reason, "actual": exc.actual}))
        sys.exit(2)
    except Exception as exc:
        print(json.dumps({"Status": "BLOCKED", "reason": str(exc), "type": type(exc).__name__}))
        sys.exit(2)
