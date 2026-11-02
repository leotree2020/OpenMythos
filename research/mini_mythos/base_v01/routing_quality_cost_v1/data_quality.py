"""Attach true next-token labels without changing the frozen prefix cohort.

Only the independent auditor reads labels; the model worker reads the exact old
inputs.json bytes. No model, Torch, generation, score or selector is imported.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import struct
import sys
import traceback

SPACE = "bookish-pancake-vwqx7rr9x5w3wxjr"
PYTHON = "/workspaces/mythos-depth-data-cpu312/bin/python"
INPUT_SHA = "ae5f8ad5fd53d25afaf29487a650dc0300528b0926c9883652475c4ca7db127f"
COMPLETION_SHA = "001841616f4139873f9057fb92df86fb366bc4e66d98f6230da59be9d689075d"
PINS = {
    "corpus": "3ee89cd6a2ab912afd5d01e98867b46a67d9ec7a9eca0910e5e4c3cdd4cc1925",
    "tokenizer": "e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77",
    "ledger": "f5f7858b989451671e4c7ed27192642dec3f9b2a1ccd214cc9e3cc30bcebb5d3",
    "partition": "95a217a815596c928a0b721837b567a08ed8c6f667839fdf6d4311113c253aa4",
    "old_inputs": "f38a1618d7904df7c530d9f0f322949a847befcb75e4177de2bc8e65bc53a315",
    "corrected_inputs": "3abb324ea2876abb78e18d86ec257a9e1d388f9501bd8cdd6c99011ac11cf41e",
    "selection_change": "7baab72fb993e2f49f806f99d70fb162441f994371136e52e42277fa361474f6",
}


class Stop(Exception):
    def __init__(self, status, reason):
        super().__init__(reason)
        self.status = status


def canonical(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def sha(x):
    return hashlib.sha256(x).hexdigest()


def info(path):
    b = Path(path).read_bytes()
    return {"bytes": len(b), "sha256": sha(b)}


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(path, obj):
    with Path(path).open("x", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        f.write("\n")


def require(okay, reason):
    if not okay:
        raise Stop("FAIL", reason)


def forbidden():
    return sorted(x for x in sys.modules if x.split(".")[0] in ("torch", "parcae_lm", "receval", "transformers"))


def derive_labels(rows, partition, ledger, inputs, tokenize):
    """Pure exact-body reconstruction; uses the existing sample order only."""
    require(inputs["context_tokens"] == 128 and inputs["seeds"] == [3101, 3202]
            and len(inputs["samples"]) == 16, "Frozen input header/count")
    require(sha(canonical(rows)) == partition["rows_sha256"] == ledger["rows_sha256"]
            and partition["all_row_sha256"] == [sha(x.encode()) for x in rows], "Whole decoded corpus identity")
    headings = sorted(x["row"] for x in ledger["decisions"] if x["decision"] == "ACCEPT_TITLE")
    require(headings == ledger["accepted_heading_rows"] and len(headings) == 60
            and len(set(headings)) == 60, "Exact reviewed heading boundaries")
    articles = {x["source_article_key"]: x for x in partition["articles"]}
    require(len(articles) == len(partition["articles"]) == 60, "Distinct reviewed source articles")
    labels = []
    for index, sample in enumerate(inputs["samples"]):
        article = articles[sample["source_article_key"]]
        h = article["heading_row"]
        ordinal = headings.index(h)
        end = headings[ordinal + 1] if ordinal + 1 < len(headings) else len(rows)
        body_rows = list(range(h + 1, end))
        body, title = "".join(rows[h + 1:end]), rows[h].strip()
        key = sha(canonical({"corpus_sha256": PINS["corpus"], "heading_row": h, "title": title}))
        require(sample["index"] == index and sample["heading_row"] == h
                and body_rows == article["body_rows"] == sample["body_rows"]
                and key == article["source_article_key"] == sample["source_article_key"]
                and sha(body.encode()) == article["text_sha256"] == sample["text_sha256"]
                and sha((title + "\n" + body).encode()) == article["article_id"] == sample["article_id"],
                "Exact reviewed source/body identity")
        tokens = tokenize(body)
        require(isinstance(tokens, list) and len(tokens) == article["full_token_count"] == sample["full_token_count"]
                and len(tokens) >= 257 and all(type(t) is int and 0 <= t < 32768 for t in tokens), "Exact full body tokenization")
        prefix = tokens[:128]
        require(prefix == sample["tokens"] and sha(canonical(prefix)) == sample["input_ids_sha256"]
                and sha(struct.pack("<128q", *prefix)) == sample["raw_input_sha256"], "Frozen prefix exact before label extraction")
        labels.append({"article_index": index, "source_article_key": key, "article_id": sample["article_id"],
                       "input_ids_sha256": sample["input_ids_sha256"], "target_offset": 128,
                       "target_token": tokens[128], "target_raw_sha256": sha(struct.pack("<q", tokens[128])),
                       "body_text_sha256": article["text_sha256"], "full_token_count": len(tokens)})
    require(len({x["source_article_key"] for x in labels}) == 16, "Distinct source labels")
    return labels


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if not args.spec.is_absolute() or not args.out.is_absolute():
        parser.error("spec/out must be absolute")
    spec = read(args.spec)
    previous, repo, out = Path(spec["previous_data"]).resolve(), Path(spec["repo"]).resolve(), args.out.resolve()
    if out == previous or out.is_relative_to(previous) or out == repo or out.is_relative_to(repo):
        parser.error("Output must be outside old data/repository")
    out.mkdir(parents=True, exist_ok=False)
    public, private = out / "public", out / "private"
    public.mkdir()
    private.mkdir()
    checks, before, environment, artifacts, actual = [], {}, {}, {}, {}
    status, error = "NOT TESTED", None
    journal = (public / "checks.jsonl").open("x", encoding="utf-8", buffering=1)

    def check(purpose, okay, observed=None, expected=True, failure="FAIL"):
        row = {"Purpose": purpose, "Environment": environment or "data-only preflight", "Input": str(args.spec),
               "Expected": expected, "Actual": observed, "Status": "PASS" if okay else failure}
        checks.append(row)
        journal.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
        if not okay:
            raise Stop(failure, purpose)

    try:
        check("designated data-only runtime", os.environ.get("CODESPACE_NAME") == SPACE and sys.executable == PYTHON
              and platform.system() == "Linux" and platform.python_version() == "3.12.3"
              and sys.flags.isolated and sys.dont_write_bytecode, failure="BLOCKED")
        check("no model imports", not forbidden(), forbidden())
        freeze = spec["freeze_commit"]
        check("full freeze SHA", isinstance(freeze, str) and len(freeze) == 40 and all(x in "0123456789abcdef" for x in freeze))
        prior_completion = previous / "public/completion.json"
        prior_inputs = previous / "private/inputs.json"
        check("exact previous completion", info(prior_completion)["sha256"] == COMPLETION_SHA)
        check("exact previous prefix bytes", info(prior_inputs) == {"bytes": 58091, "sha256": INPUT_SHA}, info(prior_inputs))
        prior = read(prior_completion)
        prior_spec = read(previous / "public/spec.json")
        check("previous data PASS/binding", prior["Status"] == "PASS" and prior["Input"] == prior_spec
              and prior["artifacts"]["private/inputs.json"] == info(prior_inputs)
              and prior["artifacts"]["public/selection.json"] == info(previous / "public/selection.json"))
        for name, digest in PINS.items():
            path = Path(prior_spec[name])
            check("frozen original source " + name, path.is_absolute() and info(path)["sha256"] == digest)
            before[str(path)] = info(path)
        for path in sorted(previous.rglob("*")):
            if path.is_file():
                before[str(path)] = info(path)
        for path in (args.spec.resolve(), Path(__file__).resolve()):
            before[str(path)] = info(path)
        save(public / "sources_before.json", before)
        save(public / "spec.json", spec)
        import pyarrow
        import pyarrow.parquet as parquet
        import numpy
        import tokenizers
        environment = {"python": sys.version, "executable": sys.executable, "pyarrow": pyarrow.__version__,
                       "numpy": numpy.__version__, "tokenizers": tokenizers.__version__, "torch_imported": bool(forbidden())}
        check("frozen dependency versions", (pyarrow.__version__, numpy.__version__, tokenizers.__version__) == ("19.0.1", "1.26.4", "0.23.2"), environment, failure="BLOCKED")
        rows = parquet.read_table(prior_spec["corpus"], columns=["text"]).column("text").to_pylist()
        check("4358 original corpus rows", len(rows) == 4358, len(rows), 4358)
        tokenizer = tokenizers.Tokenizer.from_file(prior_spec["tokenizer"])
        labels = derive_labels(rows, read(prior_spec["partition"]), read(prior_spec["ledger"]), read(prior_inputs),
                               lambda body: tokenizer.encode(body, add_special_tokens=False).ids)
        check("all16 true129th tokens derived", len(labels) == 16, len(labels), 16)
        shutil.copyfile(prior_inputs, private / "inputs.json")
        check("worker input remains exact original bytes", info(private / "inputs.json") == info(prior_inputs))
        label_payload = {"context_tokens": 128, "target_offset": 128, "seeds": [3101, 3202],
                         "prior_inputs_sha256": INPUT_SHA, "labels": labels}
        save(private / "labels.json", label_payload)
        save(public / "targets.json", {"Purpose": "Label provenance only; no token IDs or source text",
             "Expected": "Each unchanged128-token prefix is scored against its actual129th body token",
             "Actual": [{k: v for k, v in x.items() if k != "target_token"} for x in labels],
             "Status": "PASS", "labels_sha256": info(private / "labels.json")["sha256"],
             "inputs_sha256": INPUT_SHA, "worker_receives_labels": False})
        artifacts = {name: info(out / name) for name in ("private/inputs.json", "private/labels.json", "public/targets.json")}
        check("no model imports after extraction", not forbidden(), forbidden())
        actual = {"sample_count": 16, "case_count": 32, "context_tokens": 128, "target_offset": 128,
                  "prefix_selection_changed": False, "labels_passed_to_worker": False}
        status = "PASS"
    except BaseException as exc:
        status = getattr(exc, "status", "BLOCKED" if isinstance(exc, (OSError, MemoryError, KeyboardInterrupt, SystemExit)) else "FAIL")
        error = {"type": type(exc).__name__, "reason": str(exc), "traceback": traceback.format_exc()}
    custody = {"changed": [], "unreadable": []}
    for name, expected in before.items():
        try:
            if info(name) != expected:
                custody["changed"].append(name)
        except OSError as exc:
            custody["unreadable"].append({"path": name, "error": repr(exc)})
    custody["Status"] = "FAIL" if custody["changed"] else "BLOCKED" if custody["unreadable"] else "PASS" if before else "NOT TESTED"
    if custody["Status"] == "FAIL" or status == "PASS" and custody["Status"] != "PASS":
        status = custody["Status"]
    save(public / "preservation.json", custody)
    journal.close()
    completion = {"Purpose": "Derive auditor-only labels for unchanged prior routing prefixes", "Environment": environment,
                  "Input": spec, "Expected": "16 labels, exact original worker inputs, no model imports or reselection",
                  "Actual": actual, "Status": status, "checks": checks, "error": error, "artifacts": artifacts,
                  "preservation": custody, "formal_model_calls": 0, "utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    save(public / "completion.json", completion)
    print(json.dumps({"Status": status, "Actual": actual, "error": error}), flush=True)
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
