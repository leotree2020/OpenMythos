"""Data-only normal-prefix preparation; no model imports, training or scores."""
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import struct
import sys
import traceback

CORPUS_SHA = "3ee89cd6a2ab912afd5d01e98867b46a67d9ec7a9eca0910e5e4c3cdd4cc1925"
TOKENIZER_SHA = "e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77"
PINS = {
    "corpus": {"bytes": 731216, "sha256": CORPUS_SHA},
    "tokenizer": {"sha256": TOKENIZER_SHA},
    "ledger": {"bytes": 407796, "sha256": "f5f7858b989451671e4c7ed27192642dec3f9b2a1ccd214cc9e3cc30bcebb5d3"},
    "partition": {"bytes": 1171400, "sha256": "95a217a815596c928a0b721837b567a08ed8c6f667839fdf6d4311113c253aa4"},
    "old_inputs": {"bytes": 167672, "sha256": "f38a1618d7904df7c530d9f0f322949a847befcb75e4177de2bc8e65bc53a315"},
    "corrected_inputs": {"bytes": 170230, "sha256": "3abb324ea2876abb78e18d86ec257a9e1d388f9501bd8cdd6c99011ac11cf41e"},
    "selection_change": {"bytes": 8076, "sha256": "7baab72fb993e2f49f806f99d70fb162441f994371136e52e42277fa361474f6"},
}
BUILDER_SHA = "34d15184c507a253b506a039576266705ac4666d68cb23ab551c7093929c6c7a"
PARSER_SHA = "e2df747fb88e64ad12fe6e9684560c542c77013ff5640a3b931cbea02a38420c"
PYTHON = "/workspaces/mythos-depth-data-cpu312/bin/python"
SPACE = "bookish-pancake-vwqx7rr9x5w3wxjr"
SELECTION = "First16 ascending article_id from the27 reviewed >=257-token sources remaining after the33-source oldV1/correctedV2 union exclusion; exact first128 body tokens; no special tokens"
ROLE = "New to the existing Parcae depth/routing inputs only; earlier R1 and pretraining overlap unknown; not fresh-test generalization"


class Stop(Exception):
    def __init__(self, status, reason, actual=None):
        super().__init__(reason)
        self.status, self.reason, self.actual = status, reason, actual


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def info(path):
    data = Path(path).read_bytes()
    return {"bytes": len(data), "sha256": sha(data)}


def save(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")


def require(okay, reason, actual=None, status="FAIL"):
    if not okay:
        raise Stop(status, reason, actual)


def forbidden_imports():
    return sorted(name for name in sys.modules if name.split(".")[0] in ("torch", "parcae_lm", "receval", "transformers"))


def load_module(name, path, expected):
    require(info(path)["sha256"] == expected, "Frozen source hash before import", str(path))
    require(name not in sys.modules, "Existing module shadows frozen import", name, "BLOCKED")
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, "Cannot construct frozen import", str(path), "BLOCKED")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def select_payloads(rows, partition, corrected, old, selection_change, tokenize):
    """Pure selection/accounting over already independently rebuilt source records."""
    articles = partition["articles"]
    require(len(articles) == 60, "Exactly60 reviewed sources", len(articles))
    for key in ("source_article_key", "article_id", "text_sha256", "heading_row"):
        require(len({a[key] for a in articles}) == 60, "Distinct complete partition " + key)
    by_key = {a["source_article_key"]: a for a in articles}
    roles = partition["row_roles"]
    require(len(roles) == len(rows) and all(r["row"] == i for i, r in enumerate(roles)), "Full ordered row-role coverage")
    old_samples, new_samples = old["samples"], corrected["samples"]
    require(len(old_samples) == len(new_samples) == 32, "Exact old/new32 sample counts")
    require([s["index"] for s in old_samples] == list(range(32)) and [s["index"] for s in new_samples] == list(range(32)), "Exact old/new ordered sample indices")
    historical_prefix_hashes = set()
    for sample in old_samples + new_samples:
        tokens = sample.get("tokens")
        require(isinstance(tokens, list) and len(tokens) == 257
                and all(type(v) is int and 0 <= v < 32768 for v in tokens), "Historical257-token window coverage")
        historical_prefix_hashes.add(sha(canonical(tokens[:128])))
    mapping = []
    for sample in old_samples:
        row = sample["heading_row"]
        require(type(row) is int and 0 <= row < len(roles), "Old sample row out of partition", row)
        role = roles[row]
        require(role["source_article_key"] in by_key and role["role"] in ("HEADING", "BODY"), "Old sample lacks reviewed source", row)
        mapping.append({"old_index": sample["index"], "old_heading_row": row,
                        "reviewed_heading_row": role["heading_row"], "source_article_key": role["source_article_key"]})
    for sample in new_samples:
        require(sample["source_article_key"] in by_key, "Corrected source missing")
        article = by_key[sample["source_article_key"]]
        require(all(sample[k] == article[k] for k in ("article_id", "heading_row", "body_rows", "text_sha256", "full_token_count")), "Corrected sample/source identity")
    old_keys = {m["source_article_key"] for m in mapping}
    new_keys = {s["source_article_key"] for s in new_samples}
    excluded = old_keys | new_keys
    counts = {"reviewed_sources": len(articles), "eligible_sources": sum(a["eligible"] is True for a in articles),
              "old_unique_sources": len(old_keys), "corrected_unique_sources": len(new_keys),
              "overlapping_sources": len(old_keys & new_keys), "excluded_union_sources": len(excluded)}
    expected = {"reviewed_sources": 60, "eligible_sources": 60, "old_unique_sources": 31,
                "corrected_unique_sources": 32, "overlapping_sources": 30, "excluded_union_sources": 33}
    require(counts == expected, "Frozen historical exclusion counts", {"actual": counts, "expected": expected})
    change = selection_change["Actual"]
    require(selection_change["Status"] == "PASS"
            and selection_change["Input"] == {"old_sha256": PINS["old_inputs"]["sha256"], "new_sha256": PINS["corrected_inputs"]["sha256"]}
            and change["old_sample_to_reviewed_source"] == mapping
            and change["new_selected_heading_rows"] == [s["heading_row"] for s in new_samples]
            and (change["old_distinct_reviewed_sources"], change["new_distinct_reviewed_sources"], change["overlapping_reviewed_sources"]) == (31, 32, 30),
            "Historical selection-change record independently reproduced")
    eligible = sorted((a for a in articles if a["eligible"] is True and a["full_token_count"] >= 257
                       and a["source_article_key"] not in excluded), key=lambda a: a["article_id"])
    require(len(eligible) == 27, "Exactly27 unselected reviewed eligible sources", len(eligible))
    chosen = eligible[:16]
    require(len(chosen) == 16, "At least16 eligible unexposed Parcae sources", len(chosen), "BLOCKED")
    samples = []
    for index, article in enumerate(chosen):
        body_rows = article["body_rows"]
        require(body_rows == list(range(article["heading_row"] + 1, article["heading_row"] + 1 + len(body_rows))), "Contiguous body rows")
        require(all(roles[r]["source_article_key"] == article["source_article_key"] and roles[r]["role"] == "BODY" for r in body_rows), "Selected body source binding")
        body = "".join(rows[r] for r in body_rows)
        require(sha(body.encode()) == article["text_sha256"], "Selected exact body hash")
        tokens = tokenize(body)
        require(isinstance(tokens, list) and len(tokens) == article["full_token_count"]
                and len(tokens) >= 257 and all(type(v) is int and 0 <= v < 32768 for v in tokens), "Exact full-body token coverage")
        prefix = tokens[:128]
        require(sha(canonical(prefix)) not in historical_prefix_hashes,
                "Selected prefix duplicates historical old/corrected128-token input")
        samples.append({"index": index, "tokens": prefix,
            **{key: article[key] for key in ("source_article_key", "article_id", "heading_row", "body_rows", "text_sha256", "full_token_count")},
            "title_sha256": sha(article["title"].encode()), "input_ids_sha256": sha(canonical(prefix)),
            "raw_input_sha256": sha(struct.pack("<" + "q" * 128, *prefix))})
    require(len({s["input_ids_sha256"] for s in samples}) == 16, "Distinct selected prefix token sequences")
    counts.update(remaining_eligible_sources=27, sample_count=16, context_tokens=128, call_budget=32)
    inputs = {"samples": samples, "context_tokens": 128, "seeds": [3101, 3202], "data_role": ROLE,
              "selection": SELECTION, "corpus_sha256": CORPUS_SHA, "rows_sha256": partition["rows_sha256"]}
    selection = {"selection": SELECTION, "data_role": ROLE, "counts": counts,
                 "old_sample_to_reviewed_source": mapping, "excluded_old_sources": sorted(old_keys),
                 "excluded_corrected_sources": sorted(new_keys), "excluded_union_sources": sorted(excluded),
                 "ordered_eligible_candidates": [{k: a[k] for k in ("source_article_key", "article_id", "heading_row", "full_token_count")} for a in eligible],
                 "selected": [{k: v for k, v in s.items() if k != "tokens"} for s in samples]}
    return inputs, selection


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if not args.spec.is_absolute() or not args.out.is_absolute():
        parser.error("spec and out must be absolute")
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    out = args.out.resolve()
    protected_paths = [Path(spec[k]).resolve() for k in PINS]
    repo = Path(spec["repo"]).resolve()
    if out == repo or out.is_relative_to(repo) or any(out == p or out.is_relative_to(p.parent) for p in protected_paths):
        parser.error("Output must be outside protected source and input trees")
    out.mkdir(parents=True, exist_ok=False)
    public, private = out / "public", out / "private"
    public.mkdir()
    private.mkdir()
    runtime, checks, before, artifacts, counts = {}, [], {}, {}, {}
    status, error = "NOT TESTED", None
    journal = (public / "checks.jsonl").open("x", encoding="utf-8", buffering=1)

    def check(name, okay, actual=None, expected=True, failure="FAIL"):
        row = {"Purpose": name, "Environment": runtime or "data-only preflight", "Input": str(args.spec),
               "Expected": expected, "Actual": actual, "Status": "PASS" if okay else failure}
        checks.append(row)
        journal.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
        require(okay, name, actual, failure)

    try:
        check("designated data-only interpreter", os.environ.get("CODESPACE_NAME") == SPACE
              and sys.executable == PYTHON and platform.python_version() == "3.12.3"
              and platform.system() == "Linux" and sys.flags.isolated and sys.dont_write_bytecode,
              {"executable": sys.executable, "version": sys.version, "codespace": os.environ.get("CODESPACE_NAME")}, failure="BLOCKED")
        check("no model imports before preparation", not forbidden_imports(), forbidden_imports())
        freeze = spec["freeze_commit"]
        check("freeze full commit", isinstance(freeze, str) and len(freeze) == 40 and all(c in "0123456789abcdef" for c in freeze))
        for key, pin in PINS.items():
            path = Path(spec[key])
            check("absolute frozen input " + key, path.is_absolute())
            actual = info(path)
            check("exact source pin " + key, all(actual[k] == v for k, v in pin.items()), actual, pin)
            before[str(path.resolve())] = actual
        source_root = repo / "research/mini_mythos/base_v01/boundary_repair_v1"
        parser_path, builder_path = source_root / "boundary_parser.py", source_root / "build_inputs.py"
        for path, digest in ((parser_path, PARSER_SHA), (builder_path, BUILDER_SHA)):
            actual = info(path)
            check("frozen data helper " + path.name, actual["sha256"] == digest, actual, digest)
            before[str(path)] = actual
        for path in (Path(__file__).resolve(), args.spec.resolve()):
            before[str(path)] = info(path)
        save(public / "sources_before.json", before)
        save(public / "spec.json", spec)
        frozen_parser = load_module("boundary_parser", parser_path, PARSER_SHA)
        builder = load_module("routing_frozen_boundary_builder", builder_path, BUILDER_SHA)
        import pyarrow
        import pyarrow.parquet as parquet
        import numpy
        import tokenizers
        runtime = {"python_version": platform.python_version(), "executable": sys.executable, "pid": os.getpid(),
                   "pyarrow_version": pyarrow.__version__, "numpy_version": numpy.__version__, "tokenizers_version": tokenizers.__version__,
                   "torch_imported": bool(forbidden_imports()), "freeze_commit": freeze,
                   "package_locations": {"pyarrow": pyarrow.__file__, "numpy": numpy.__file__, "tokenizers": tokenizers.__file__}}
        expected = {"python_version": "3.12.3", "pyarrow_version": "19.0.1", "numpy_version": "1.26.4", "tokenizers_version": "0.23.2", "torch_imported": False}
        check("frozen data environment", all(runtime[k] == v for k, v in expected.items()), runtime, expected, "BLOCKED")
        rows = parquet.read_table(spec["corpus"], columns=["text"]).column("text").to_pylist()
        check("complete corpus4358 rows", len(rows) == 4358, len(rows), 4358)
        ledger = json.loads(Path(spec["ledger"]).read_text(encoding="utf-8"))
        check("frozen semantic ledger reviews", builder.semantic_review_matches(ledger), failure="BLOCKED")
        tokenizer = tokenizers.Tokenizer.from_file(spec["tokenizer"])
        partition, corrected, rebuilt_counts = builder.build_payloads(rows, ledger, CORPUS_SHA, tokenizer)
        original_partition = json.loads(Path(spec["partition"]).read_text(encoding="utf-8"))
        original_corrected = json.loads(Path(spec["corrected_inputs"]).read_text(encoding="utf-8"))
        check("full historical partition re-extraction equality", partition == original_partition, rebuilt_counts)
        check("full corrected historical inputs reconstruction equality", corrected == original_corrected)
        old = json.loads(Path(spec["old_inputs"]).read_text(encoding="utf-8"))
        selection_change = json.loads(Path(spec["selection_change"]).read_text(encoding="utf-8"))
        inputs, selection = select_payloads(rows, partition, corrected, old, selection_change,
                                            lambda body: tokenizer.encode(body, add_special_tokens=False).ids)
        counts = selection["counts"]
        check("frozen16 normal-length source selection", counts["sample_count"] == 16 and counts["call_budget"] == 32, counts)
        save(private / "inputs.json", inputs)
        input_info = info(private / "inputs.json")
        selection.update(inputs_artifact={"path": "private/inputs.json", **input_info}, sources=before,
                         runtime=runtime, freeze_commit=freeze, source_pins=PINS)
        save(public / "selection.json", selection)
        artifacts = {name: info(out / name) for name in ("private/inputs.json", "public/selection.json")}
        check("no model imports after preparation", not forbidden_imports(), forbidden_imports())
        status = "PASS"
    except BaseException as exc:
        status = getattr(exc, "status", "BLOCKED" if isinstance(exc, (OSError, MemoryError, KeyboardInterrupt, SystemExit)) else "FAIL")
        error = {"type": type(exc).__name__, "reason": str(exc), "actual": getattr(exc, "actual", None), "traceback": traceback.format_exc()}
    preservation = {"changed": [], "unreadable": []}
    for path, expected in before.items():
        try:
            if info(path) != expected:
                preservation["changed"].append(path)
        except OSError as exc:
            preservation["unreadable"].append({"path": path, "error": repr(exc)})
    preservation["Status"] = "FAIL" if preservation["changed"] else "BLOCKED" if preservation["unreadable"] else "PASS" if before else "NOT TESTED"
    if preservation["Status"] == "FAIL":
        status = "FAIL"
    elif status == "PASS" and preservation["Status"] != "PASS":
        status = "BLOCKED"
    save(public / "preservation.json", preservation)
    journal.close()
    completion = {"Purpose": "Prepare frozen128-token inputs from16 new-to-Parcae-depth/routing source articles",
                  "Environment": runtime, "Input": spec, "Expected": "All source/selection/custody checks pass;16sources/32planned calls, no model imports",
                  "Actual": counts, "Status": status, "checks": checks, "error": error, "artifacts": artifacts,
                  "preservation": preservation, "data_role": ROLE, "formal_model_calls": 0,
                  "model_execution": "NOT TESTED", "quality": "NOT TESTED", "utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    save(public / "completion.json", completion)
    print(json.dumps({"Status": status, "Actual": counts, "error": error}), flush=True)
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
