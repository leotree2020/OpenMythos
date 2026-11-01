"""Data-only corpus-bound input builder; never imports Torch or loads a model."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import sys
import traceback

# -I intentionally ignores the working directory; only this frozen sibling
# source directory is made importable, never a caller-supplied search path.
sys.path.insert(0, str(Path(__file__).resolve().parent))


CORPUS_SHA = "3ee89cd6a2ab912afd5d01e98867b46a67d9ec7a9eca0910e5e4c3cdd4cc1925"
TOKENIZER_SHA = "e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77"
SELECTION = "first32 by ascending SHA256(stripped title + newline + exact concatenated body), after >=257-token filter"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_info(path):
    digest, size = hashlib.sha256(), 0
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return {"bytes": size, "sha256": digest.hexdigest()}


def save(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")


def forbidden_imports():
    return sorted(name for name in sys.modules if name.split(".")[0] in ("torch", "parcae_lm", "receval", "transformers"))


def semantic_review_matches(ledger):
    if not isinstance(ledger, dict) or not isinstance(ledger.get("decisions"), list):
        return False
    decisions = ledger["decisions"]
    if any(not isinstance(item, dict) or type(item.get("row")) is not int for item in decisions):
        return False
    accepted = sorted(item["row"] for item in decisions if item.get("decision") == "ACCEPT_TITLE")
    review = ledger.get("semantic_review")
    if (not isinstance(review, dict) or review.get("agreement") is not True
            or review.get("unresolved_rows") != []
            or review.get("not_human_or_external_independent_review") is not True
            or ledger.get("accepted_heading_rows") != accepted):
        return False
    for reviewer in ("root", "independent"):
        result = review.get(reviewer)
        if (not isinstance(result, dict) or result.get("verdict") != "APPROVE"
                or result.get("accepted_heading_rows") != accepted):
            return False
    return True


def build_payloads(rows, ledger, corpus_sha256, tokenizer, selection_count=32):
    """Small synthetic fixtures may set selection_count; main always uses 32."""
    from boundary_parser import BoundaryStop, prepare_partition
    if type(selection_count) is not int or selection_count <= 0:
        raise BoundaryStop("FAIL", "Invalid selection count")
    original = prepare_partition(rows, ledger, corpus_sha256)
    partition = {key: value for key, value in original.items()
                 if key not in ("articles", "leading_parts")}
    partition["all_row_sha256"] = [sha(raw.encode("utf-8")) for raw in rows]
    partition["articles"] = []
    eligible = []
    for article in original["articles"]:
        token_ids = tokenizer.encode("".join(article["parts"]), add_special_tokens=False).ids
        if (not isinstance(token_ids, list)
                or any(type(token) is not int or not 0 <= token < 32768 for token in token_ids)):
            raise BoundaryStop("FAIL", "Tokenizer returned invalid token IDs", article["heading_row"])
        metadata = {key: value for key, value in article.items() if key not in ("parts", "heading_text")}
        metadata.update(full_token_count=len(token_ids), eligible=len(token_ids) >= 257)
        partition["articles"].append(metadata)
        if metadata["eligible"]:
            eligible.append((metadata, token_ids[:257]))
    eligible.sort(key=lambda item: item[0]["article_id"])
    if len(eligible) < selection_count:
        raise BoundaryStop("BLOCKED", "Insufficient eligible reviewed source articles",
                           {"eligible": len(eligible), "required": selection_count})
    chosen = eligible[:selection_count]
    for key in ("source_article_key", "article_id", "text_sha256"):
        if len({metadata[key] for metadata, _ in chosen}) != selection_count:
            raise BoundaryStop("FAIL", "Selected source/content identity is not distinct", key)
    samples = []
    for index, (metadata, tokens) in enumerate(chosen):
        samples.append({"index": index, **{key: metadata[key] for key in
                       ("article_id", "title", "heading_row", "body_rows", "source_article_key",
                        "text_sha256", "full_token_count")}, "tokens": tokens,
                        "input_ids_sha256": sha(canonical(tokens[:256])),
                        "target_ids_sha256": sha(canonical(tokens[1:257])),
                        "scored_target_ids_sha256": sha(canonical(tokens[65:257])),
                        "window_sha256": sha(canonical(tokens))})
    inputs = {"samples": samples, "selection": SELECTION if selection_count == 32 else
              "synthetic-fixture count override; not formal inputs",
              "context_tokens": 256, "window_tokens": 257,
              "scored_logit_positions": [64, 256], "scored_tokens_per_sample": 192,
              "corpus_sha256": corpus_sha256, "rows_sha256": original["rows_sha256"],
              "data_role": "historical development; not fresh-test"}
    counts = {"row_count": len(rows), "source_article_count": len(partition["articles"]),
              "eligible_article_count": len(eligible), "selected_sample_count": len(samples),
              "scored_tokens_per_sample": 192}
    return partition, inputs, counts


def main():
    from boundary_parser import BoundaryStop
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True, type=Path)
    args = parser.parse_args()
    if not args.spec.is_absolute():
        parser.error("--spec must be absolute")
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    output = Path(spec["output_dir"])
    if not output.is_absolute():
        parser.error("output_dir must be absolute")
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    checks, status, error, runtime, counts, manifest_sha = [], "NOT TESTED", None, {}, {}, None
    journal = (output / "checks.jsonl").open("x", encoding="utf-8", buffering=1)
    def check(name, okay, actual, expected=True, failure="FAIL"):
        record = {"Purpose": name, "Environment": runtime or "data-only environment not yet validated",
                  "Input": {"spec": str(args.spec)}, "Expected": expected, "Actual": actual,
                  "Status": "PASS" if okay else failure}
        checks.append(record)
        journal.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
        if not okay:
            raise BoundaryStop(failure, name, actual)
    try:
        check("no model imports before data preparation", not forbidden_imports(), forbidden_imports())
        paths = {}
        for key in ("corpus", "tokenizer", "ledger"):
            path = Path(spec[key])
            if not path.is_absolute():
                raise BoundaryStop("BLOCKED", "Input path must be absolute", key)
            paths[key] = path.resolve(strict=True)
        check("frozen source identity requested", spec.get("expected_corpus_sha256") == CORPUS_SHA,
              spec.get("expected_corpus_sha256"), CORPUS_SHA)
        frozen = spec.get("frozen_commit")
        check("implementation freeze identity", isinstance(frozen, str) and len(frozen) == 40
              and all(c in "0123456789abcdef" for c in frozen), frozen, "40-character Git commit")
        sources = {str(path): file_info(path) for path in [*paths.values(), args.spec.resolve()]}
        check("original corpus hash", sources[str(paths["corpus"])]["sha256"] == CORPUS_SHA,
              sources[str(paths["corpus"])], {"sha256": CORPUS_SHA, "bytes": 731216})
        check("original corpus bytes", sources[str(paths["corpus"])]["bytes"] == 731216,
              sources[str(paths["corpus"])]["bytes"], 731216)
        check("original tokenizer hash", sources[str(paths["tokenizer"])]["sha256"] == TOKENIZER_SHA,
              sources[str(paths["tokenizer"])], {"sha256": TOKENIZER_SHA})
        code_root = Path(__file__).resolve().parent
        source_files = {str(path): file_info(path) for path in sorted(code_root.iterdir())
                        if path.is_file() and path.suffix in (".py", ".md")}
        import pyarrow
        import pyarrow.parquet as parquet
        import numpy
        import tokenizers
        runtime = {"python_version": platform.python_version(), "executable": sys.executable, "prefix": sys.prefix,
                   "pid": os.getpid(),
                   "pyarrow_version": pyarrow.__version__, "numpy_version": numpy.__version__,
                   "tokenizers_version": tokenizers.__version__, "torch_imported": bool(forbidden_imports()),
                   "package_locations": {"pyarrow": pyarrow.__file__, "numpy": numpy.__file__, "tokenizers": tokenizers.__file__}}
        expected_runtime = {"python_version": "3.12.3", "pyarrow_version": "19.0.1",
                            "numpy_version": "1.26.4", "tokenizers_version": "0.23.2", "torch_imported": False}
        check("frozen data-only runtime", all(runtime[key] == value for key, value in expected_runtime.items()),
              runtime, expected_runtime, failure="BLOCKED")
        table = parquet.read_table(paths["corpus"], columns=["text"])
        rows = table.column("text").to_pylist()
        check("complete original source row count", len(rows) == 4358, len(rows), 4358)
        ledger = json.loads(paths["ledger"].read_text(encoding="utf-8"))
        check("two recorded semantic reviews agree with ledger", semantic_review_matches(ledger),
              {"accepted_heading_rows": ledger.get("accepted_heading_rows") if isinstance(ledger, dict) else None,
               "semantic_review": ledger.get("semantic_review") if isinstance(ledger, dict) else None},
              "Root and separate internal reviewer APPROVE the same accepted rows; no unresolved decisions", failure="BLOCKED")
        tokenizer = tokenizers.Tokenizer.from_file(str(paths["tokenizer"]))
        partition, inputs, counts = build_payloads(rows, ledger, CORPUS_SHA, tokenizer, selection_count=32)
        check("reviewed source partition and fixed selection", counts["selected_sample_count"] == 32,
              counts, {"selected_sample_count": 32, "row_count": 4358})
        save(output / "partition.json", partition)
        save(output / "inputs.json", inputs)
        check("source files unchanged", all(file_info(path) == info for path, info in source_files.items()),
              {"source_file_count": len(source_files)})
        check("corpus tokenizer ledger and spec unchanged", all(file_info(path) == info for path, info in sources.items()),
              {"source_count": len(sources)})
        check("no model imports after data preparation", not forbidden_imports(), forbidden_imports())
        journal.close()
        artifacts = {name: file_info(output / name) for name in ("partition.json", "inputs.json", "checks.jsonl")}
        manifest = {"status": "PASS", "protocol": "MYTHOS-DATA-BOUNDARY-REPAIR-V1", "frozen_commit": frozen,
                    "runtime": runtime, "counts": counts, "accepted_heading_rows": [a["heading_row"] for a in partition["articles"]],
                    "sources": sources, "source_files": source_files, "artifacts": artifacts,
                    "rows_sha256": partition["rows_sha256"], "corpus_utf8_sha256": partition["corpus_utf8_sha256"],
                    "ledger_sha256": sources[str(paths["ledger"])]["sha256"], "selection": SELECTION,
                    "torch_imported": False, "model_execution": "NOT TESTED", "scientific_performance_evidence": "NOT TESTED"}
        save(output / "manifest.json", manifest)
        manifest_sha = file_info(output / "manifest.json")["sha256"]
        status = "PASS"
    except BaseException as exc:
        status = getattr(exc, "status", "BLOCKED" if isinstance(exc, (OSError, MemoryError, KeyboardInterrupt, SystemExit)) else "FAIL")
        error = {"type": type(exc).__name__, "reason": getattr(exc, "reason", str(exc)),
                 "actual": getattr(exc, "actual", None), "traceback": traceback.format_exc()}
    cleanup_errors = []
    try:
        journal.close()
    except BaseException as exc:
        cleanup_errors.append(repr(exc))
        if status == "PASS":
            status = "BLOCKED"
    completion = {"status": status, "Status": status, "Purpose": "Freeze reviewed exact source partitions and 32 data windows",
                  "process_id": os.getpid(),
                  "Environment": runtime, "Input": spec, "Expected": "All data-only gates PASS; exactly32 distinct reviewed source articles",
                  "Actual": counts, "error": error, "cleanup_errors": cleanup_errors, "checks": checks,
                  "manifest_sha256": manifest_sha, "torch_imported": bool(forbidden_imports()),
                  "model_execution": "NOT TESTED", "scientific_performance_evidence": "NOT TESTED"}
    try:
        save(output / "completion.json", completion)
    except BaseException as exc:
        print(json.dumps({"completion": completion, "sealing_error": repr(exc)}, allow_nan=False), file=sys.stderr, flush=True)
        return 2
    print(json.dumps({"status": status, "counts": counts, "error": error}, allow_nan=False), flush=True)
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
