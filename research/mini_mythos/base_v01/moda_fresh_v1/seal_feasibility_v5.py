"""Read-only receipt/custody audit; never prepares data or imports model code."""
import argparse
from collections import Counter
import datetime
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import traceback

BASE = "b32b63e43ca0ad5c35aeb26904979f769e31bfbe"
SPACE = "bookish-pancake-vwqx7rr9x5w3wxjr"
REPO = Path("/workspaces/mythos-moda-fresh-cpu-v1")
PACKAGE = "research/mini_mythos/base_v01/moda_fresh_v1/"
FRESH = Path("/workspaces/mythos-evidence/base_v01/moda_fresh")
DATA = FRESH / "preparation-v2/data"
CORPUS = dict(bytes=1234829, sha256="71de87ec66bc5737752a2502204dfa6d7fe9856ade3ea444dc6317789a4f13fb")
SPEC_SHA = "6185f5dee8c9f95e35a967c3f8abd5754221ed02207c68244ce3d2bdc4dcb8e9"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8") + b"\n"


def pin(path):
    digest, size = hashlib.sha256(), 0
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 ** 2), b""):
            digest.update(block)
            size += len(block)
    return dict(bytes=size, sha256=digest.hexdigest())


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key: " + key)
        result[key] = value
    return result


def decode(raw):
    return json.loads(raw, object_pairs_hook=unique, parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))


def read(path):
    return decode(Path(path).read_bytes())


def git(*args, repo=REPO):
    # Match the normalization used by the frozen TARGET_DISCOVERY recorder.
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def save(path, value):
    with Path(path).open("xb") as stream:
        stream.write(canonical(value))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-head", required=True)
    args = parser.parse_args()
    assert sys.flags.isolated and sys.dont_write_bytecode
    assert os.environ.get("CODESPACE_NAME") == SPACE
    assert git("rev-parse", "HEAD") == args.expected_head
    assert not git("status", "--porcelain")
    out = FRESH / "feasibility-v5"
    out.mkdir(exist_ok=False)
    report = dict(Purpose="Audit retained v2 candidate upper bounds and preserve the new quota BLOCKED without further preparation", Environment=dict(codespace=SPACE, python=sys.version, executable=sys.executable), Input=dict(base=BASE, seal_source=args.expected_head), Expected=dict(source_rows=7600, total_selected=20, per_class=5, tokenizer_calls=0, model_calls=0), Actual={}, Status="NOT TESTED")
    checks = []
    report["Actual"]["checks"] = checks

    def require(name, okay, actual=None):
        checks.append(dict(Purpose=name, Expected=True, Actual=actual, Status="PASS" if okay else "FAIL"))
        if not okay:
            raise RuntimeError(name)

    try:
        v2_manifest = DATA / "manifest.json"
        frozen = subprocess.check_output(["git", "-C", str(REPO), "show", BASE + ":" + PACKAGE + "continuation_v2_evidence/preparation-v2/data/manifest.json"])
        require("Original v2 receipt byte-identical to committed baseline", frozen == v2_manifest.read_bytes(), pin(v2_manifest))
        manifest = decode(frozen)
        require("Frozen selection quota", manifest["Expected"]["records"] == 20 and manifest["Expected"]["per_class"] == 5 and manifest["Expected"]["tokens"] == 129, manifest["Expected"])
        quota = manifest["Expected"]["per_class"]
        require("Original history spec still pinned", manifest["Input"]["spec_sha256"] == SPEC_SHA and pin(FRESH / "specification-v1/DATA_SPEC.json")["sha256"] == SPEC_SHA)
        require("Original corpus byte-identical", pin(DATA / "corpus.parquet") == CORPUS and manifest["artifacts"]["corpus.parquet"] == CORPUS, CORPUS)
        expected = manifest["artifacts"]["candidates.json.gz"]
        require("Candidate physical bytes/SHA match old committed receipt", pin(DATA / "candidates.json.gz") == expected["physical"], expected["physical"])
        with gzip.GzipFile(fileobj=io.BytesIO((DATA / "candidates.json.gz").read_bytes())) as stream:
            raw = stream.read(8 * 1024 ** 2 + 1)
        require("Candidate expansion bounded", len(raw) <= 8 * 1024 ** 2, len(raw))
        require("Candidate canonical bytes/SHA match old committed receipt", dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()) == expected["canonical"], expected["canonical"])
        rows = decode(raw)
        require("Original canonical encoding", canonical(rows) == raw)
        require("Complete 7600-row ledger", isinstance(rows, list) and len(rows) == 7600)
        allowed = {"ELIGIBLE_PENDING_HISTORY", "EXCLUDE_LITERAL_BACKSLASH", "EXCLUDE_NO_SENTENCE_PUNCTUATION", "EXCLUDE_SHORT"}
        valid = all(type(r.get("row")) is int and type(r.get("label")) is int and r["label"] in range(4) and r.get("decision") in allowed for r in rows)
        require("Complete known eligibility decisions and typed labels", valid)
        require("Exact row permutation and unique identities", sorted(r["row"] for r in rows) == list(range(7600)) and len({r["id"] for r in rows}) == 7600)
        identities = all(r["id"] == hashlib.sha256(canonical(dict(corpus_sha256=CORPUS["sha256"], row=r["row"], text_sha256=r["text_sha256"]))).hexdigest() for r in rows)
        require("Every row ID binds fixed corpus/row/text hash", identities)
        labels = Counter(r["label"] for r in rows)
        require("1900 original rows per source label", all(labels[label] == 1900 for label in range(4)), dict(labels))
        eligible = [r for r in rows if r["decision"] == "ELIGIBLE_PENDING_HISTORY"]
        require("Length classifications remain explicit", all(type(r.get("full_token_count")) is int and r["full_token_count"] >= 129 for r in eligible) and all(type(r.get("full_token_count")) is int and r["full_token_count"] < 129 for r in rows if r["decision"] == "EXCLUDE_SHORT"))
        counts = {str(label): sum(r["label"] == label for r in eligible) for label in range(4)}
        deficient = {label: quota - count for label, count in counts.items() if count < quota}
        report["Actual"].update(source_rows=len(rows), eligible_before_history=len(eligible), eligible_upper_bound_per_label=counts, decision_counts=dict(Counter(r["decision"] for r in rows)), missing_per_label=deficient, necessary_quota_condition=not deficient, history_scan_complete=False, new_preparation_started=False, tokenizer_calls=0, source_acquisitions=0, model_calls=0, training_steps=0, quality="NOT TESTED", complete_cpu_timing="NOT TESTED", eligibility_retokenized=False)
        require("Retained receipt proves insufficient fixed-quota upper bound", bool(deficient), counts)
        require("No V5 preparation/model attempt exists", not (FRESH / "preparation-v5").exists() and not (FRESH / "attempt-v1").exists())
        protected = Path("/workspaces/mythos-evidence/base_v01/moda_residual/attempt-v2/protected_before.json.gz")
        require("Original protected map pin", pin(protected) == dict(bytes=1181241, sha256="6358e3bc273953d4a48f0a233ed2aa32cb118aedb4b3cfc76bf6e89dc9549a02"))
        mapping = decode(gzip.decompress(protected.read_bytes()))

        def merge(addition):
            require("Custody maps agree on shared paths", all(mapping[k] == addition[k] for k in mapping.keys() & addition.keys()))
            mapping.update(addition)

        merge(read("/workspaces/mythos-moda-residual-cpu-v2/research/mini_mythos/base_v01/moda_residual_v2/EXTERNAL_EVIDENCE_MANIFEST.json"))
        require("Full original protected union", len(mapping) == 25986, len(mapping))
        merge(read(FRESH / "preparation-v4/old_fresh_before.json"))
        v4_manifest_path = FRESH / "stop-v4/EXTERNAL_MANIFEST.json"
        v4_frozen = subprocess.check_output(["git", "-C", str(REPO), "show", BASE + ":" + PACKAGE + "continuation_v4_evidence/EXTERNAL_MANIFEST.json"])
        require("V4 external manifest matches committed baseline", v4_frozen == v4_manifest_path.read_bytes())
        merge(decode(v4_frozen))
        merge({str(v4_manifest_path): pin(v4_manifest_path)})
        maintenance = read(REPO / "research/mini_mythos/maintenance/storage_20261102/EXPORT_MANIFEST.json")
        merge({row["source"]: {k: row[k] for k in ("bytes", "sha256")} for row in maintenance.values()})
        changed = []
        for index, (path, expected_pin) in enumerate(sorted(mapping.items())):
            try:
                if pin(path) != expected_pin:
                    changed.append(path)
            except OSError:
                changed.append(path)
            if index % 6000 == 0:
                print("Custody", index, "/", len(mapping), flush=True)
        require("All protected and prior fresh artifacts unchanged", not changed, dict(rehashed=len(mapping), changed=changed))
        before = read(REPO / PACKAGE / "TARGET_DISCOVERY.json")["Actual"]
        for key, path in (("upstream", "/workspaces/mythos-parcae-pinned"), ("old_repo", "/workspaces/mythos-moda-residual-cpu-v2")):
            actual = dict(head=git("rev-parse", "HEAD", repo=path), status=git("status", "--porcelain", repo=path))
            require(key + " HEAD/status unchanged", actual == before[key], actual)
        require("Main checkout HEAD/status unchanged", git("rev-parse", "HEAD", repo="/workspaces/OpenMythos") == before["main_head"] and git("status", "--porcelain=v1", "--untracked-files=all", repo="/workspaces/OpenMythos") == before["main_status"])
        active = []
        names = {"prepare_once.py", "prepare_once_v2.py", "prepare_once_v4.py", "prepare_once_v5.py", "data_prepare.py", "execute_once.py", "run_fresh.py", "audit_stream.py"}
        for path in Path("/proc").glob("[0-9]*/cmdline"):
            try:
                argv = path.read_bytes().decode(errors="replace").split(chr(0))
            except OSError:
                continue
            if any(Path(x).name in names for x in argv if x):
                active.append(path.parent.name)
        require("No active experiment workers", not active, active)
        require("Candidate/corpus/spec after-pin unchanged", pin(DATA / "candidates.json.gz") == manifest["artifacts"]["candidates.json.gz"]["physical"] and pin(DATA / "corpus.parquet") == CORPUS and pin(FRESH / "specification-v1/DATA_SPEC.json")["sha256"] == SPEC_SHA)
        report["Status"] = "PASS"
        report["experiment_status"] = "BLOCKED"
        report["scientific_conclusion"] = "UNRESOLVED"
        report["limitation"] = "Counts are independently recomputed from the original byte-bound v2 eligibility receipt; tokenizer eligibility itself is not recomputed. History/new-new dedup only removes candidates and remains incomplete."
        report["next_unique_instruction"] = "Separately pre-register a new source protocol with the same sample size, window, filters and scientific thresholds; verify model-blind per-label eligibility feasibility before full historical dedup or model execution. Never retry this infeasible source protocol."
    except BaseException as exc:
        report["Status"] = "FAIL"
        report["experiment_status"] = "BLOCKED"
        report["error"] = dict(type=type(exc).__name__, message=str(exc), traceback=traceback.format_exc())
    finally:
        report["utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        report["Actual"]["free_bytes_after"] = shutil.disk_usage(FRESH).free
        report["FORMAL_ACCEPTANCE_READY"] = False
        save(out / "feasibility.json", report)
        inputs = {str(path): pin(path) for path in (DATA / "manifest.json", DATA / "candidates.json.gz", DATA / "corpus.parquet", FRESH / "specification-v1/DATA_SPEC.json", FRESH / "continuation-v5-restore.json", Path(__file__))}
        save(out / "INPUT_MANIFEST.json", inputs)
        print(json.dumps(dict(audit=report["Status"], experiment=report["experiment_status"], counts=report["Actual"].get("eligible_upper_bound_per_label"), model_calls=0)), flush=True)
    return 0 if report["Status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
