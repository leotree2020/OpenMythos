"""Independent full-logit NumPy audit before declared temporary-row disposal."""
from __future__ import annotations
import argparse
import datetime
import hashlib
import json
import math
from pathlib import Path
import platform
import struct
import sys
import traceback

RAW_BYTES = 64 * 32768 * 4
DATA_PYTHON = "/workspaces/mythos-depth-data-cpu312/bin/python"
STABLE_OBSERVER = ("h0_sha256", "rng_before_sha256", "rng_after_sha256", "seed")


def sha(value):
    return hashlib.sha256(value).hexdigest()


def info(path):
    digest, size = hashlib.sha256(), 0
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            digest.update(block)
            size += len(block)
    return {"bytes": size, "sha256": digest.hexdigest()}


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        stream.write("\n")


def require(okay, reason):
    if not okay:
        raise ValueError(reason)


def identity(row):
    return {k: row[k] for k in ("arm", "train_seed", "eval_seed", "article_id", "article_index")}


def expected_retention(row, data):
    if row["arm"] == "fixed32":
        return "historical_bridge"
    if row["article_id"] == data["eval"][0]["id"] and row["eval_seed"] == 5101:
        return "sentinel"
    return "audited_then_discarded"


def compute(np, raw, targets):
    require(len(raw) == RAW_BYTES, "Exact scored raw byte count")
    require(len(targets) == 64 and all(type(x) is int and 0 <= x < 32768 for x in targets), "Scored targets")
    values = np.frombuffer(raw, dtype="<f4").reshape(64, 32768)
    require(bool(np.isfinite(values).all()), "All scored logits finite")
    x = values.astype(np.float64)
    maximum = x.max(axis=1)
    gold = x[np.arange(64), np.asarray(targets)]
    shifted_lse = np.log(np.exp(x - maximum[:, None]).sum(axis=1))
    nll = (maximum - gold) + shifted_lse
    predictions = np.argmax(values, axis=1)
    top1 = x[np.arange(64), predictions].copy()
    x[np.arange(64), predictions] = -np.inf
    second = np.argmax(x, axis=1)
    top2 = x[np.arange(64), second].copy()
    columns = {"nll": nll.tolist(), "predictions": predictions.tolist(), "gold": gold.tolist(),
               "max": maximum.tolist(), "shifted_logsumexp": shifted_lse.tolist(),
               "logsumexp": (maximum + shifted_lse).tolist(), "top1": top1.tolist(),
               "top2": top2.tolist(), "top2_indices": second.tolist(), "margin": (top1 - top2).tolist()}
    chunks = []
    for index, start in enumerate(range(0, len(raw), 1048576)):
        chunk = raw[start:start + 1048576]
        c = np.frombuffer(chunk, dtype="<f4").astype(np.float64)
        chunks.append({"index": index, "offset": start, "bytes": len(chunk), "sha256": sha(chunk),
                       "sum64": float(c.sum()), "sum_squares64": float((c * c).sum()),
                       "min64": float(c.min()), "max64": float(c.max())})
    return {"metrics": {"nll_mean": float(nll.mean()), "nll_sum": float(nll.sum()),
                        "correct": int((predictions == np.asarray(targets)).sum()), "target_count": 64},
            "columns": columns, "chunks": chunks, "finite_components": 64 * 32768,
            "raw": {"bytes": len(raw), "sha256": sha(raw)}}


def compare_worker(row, result):
    observed = row["worker_per_token"]
    actual = result["columns"]
    require(len(observed["nll"]) == 64 and len(observed["predictions"]) == 64, "64 worker token metrics")
    require(all(type(x) in (int, float) and math.isfinite(x) for x in observed["nll"]), "Finite worker token NLL")
    require(max(abs(a - b) for a, b in zip(observed["nll"], actual["nll"])) <= 1e-10, "Independent token NLL")
    require(observed["predictions"] == actual["predictions"], "Independent token argmax exact")
    for field in ("nll_mean", "nll_sum"):
        require(math.isfinite(row[field]) and abs(row[field] - result["metrics"][field]) <= 1e-10,
                "Independent aggregate " + field)
    require(row["correct"] == result["metrics"]["correct"] and row["target_count"] == 64, "Independent top1 count")


def historical_bridge(spec, row, result):
    evaluation_path = Path(spec["baseline_evaluation_path"])
    require(info(evaluation_path) == spec["baseline_evaluation_pin"], "Historical evaluation pin")
    matches = [r for r in read(evaluation_path)["rows"] if identity(r) == identity(row)]
    require(len(matches) == 1, "Unique historical F32 row")
    old = matches[0]
    require(old["arm"] == "fixed32" and old["train_seed"] is None, "Historical native baseline")
    require(old["shape"] == row["shape"] == [64, 32768] and old["dtype"] == row["dtype"] == "float32-le", "Historical shape/dtype")
    require(old["logits_sha256"] == row["logits_sha256"] == result["raw"]["sha256"], "Historical full-logit bitwise hash")
    require(old["targets_sha256"] == row["targets_sha256"] and old["h0_sha256"] == row["h0_sha256"], "Historical target/h0")
    require({k: old["observer"][k] for k in STABLE_OBSERVER} ==
            {k: row["observer"][k] for k in STABLE_OBSERVER}, "Historical h0/RNG bridge")
    root = evaluation_path.parents[1].resolve()
    original = (root / old["logits_file"]).resolve()
    require(original.is_relative_to(root) and not Path(old["logits_file"]).is_absolute(), "Historical raw confined")
    require(info(original) == result["raw"], "Historical retained raw exact")
    return {"path": str(original), "pin": result["raw"], "evaluation_pin": spec["baseline_evaluation_pin"],
            "observer_stable": {k: old["observer"][k] for k in STABLE_OBSERVER}}


def validate_columns(columns, targets):
    names = {"nll", "predictions", "gold", "max", "shifted_logsumexp", "logsumexp", "top1", "top2", "top2_indices", "margin"}
    require(set(columns) == names and all(isinstance(v, list) and len(v) == 64 for v in columns.values()), "Compact64-column schema")
    for key, values in columns.items():
        if key in ("predictions", "top2_indices"):
            require(all(type(x) is int and 0 <= x < 32768 for x in values), "Vocabulary index column")
        else:
            require(all(type(x) in (int, float) and math.isfinite(x) for x in values), "Finite compact column")
    for i in range(64):
        require(abs(columns["nll"][i] - ((columns["max"][i] - columns["gold"][i]) + columns["shifted_logsumexp"][i])) <= 1e-10,
                "Stable stored NLL identity")
        require(abs(columns["logsumexp"][i] - (columns["max"][i] + columns["shifted_logsumexp"][i])) <= 1e-10, "Stored logsumexp identity")
        require(columns["top1"][i] == columns["max"][i] and columns["margin"][i] >= 0
                and columns["margin"][i] == columns["top1"][i] - columns["top2"][i]
                and columns["predictions"][i] != columns["top2_indices"][i], "Top2 margin identity")
    return {"nll_mean": math.fsum(columns["nll"]) / 64, "nll_sum": math.fsum(columns["nll"]),
            "correct": sum(a == b for a, b in zip(columns["predictions"], targets)), "target_count": 64}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--row", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--development", action="store_true")
    args = parser.parse_args()
    report = {"Purpose": "Independent full-logit per-row audit before any temporary disposal",
              "Environment": {"python": sys.version, "executable": sys.executable, "torch_imported": False,
                              "development_only":args.development},
              "Input": {"row_path": str(args.row.resolve())},
              "Expected": "64 exact targets; full finite FP32 logits; independent FP64 token/aggregate metrics; exact argmax",
              "Actual": {}, "Status": "NOT TESTED", "utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    bridge_phase = False
    try:
        import numpy as np
        if not args.development:
            if not (platform.system() == "Linux" and platform.python_version() == "3.12.3" and
                    sys.executable == DATA_PYTHON and np.__version__ == "1.26.4" and
                    bool(sys.flags.isolated) and sys.dont_write_bytecode):
                raise OSError("Frozen independent NumPy environment unavailable")
        require(not any(n.split(".")[0] in ("torch", "parcae_lm", "receval") for n in sys.modules), "No model or Torch import")
        spec, row = read(args.spec), read(args.row)
        report["Input"].update(row_input=info(args.row), spec_sha256=info(args.spec)["sha256"], identity=identity(row))
        data_path = Path(spec["data_path"])
        require(info(data_path)["sha256"] == spec["inputs_sha256"], "Frozen data payload")
        data = read(data_path)
        matches = [s for s in data["eval"] if s["id"] == row["article_id"]]
        require(len(matches) == 1 and len(matches[0]["tokens"]) == 129, "Unique129-token evaluation article")
        require(type(row["article_index"]) is int and 0 <= row["article_index"] < 16
                and data["eval"][row["article_index"]]["id"] == row["article_id"], "Frozen article index")
        targets = matches[0]["tokens"][65:129]
        require(sha(struct.pack("<64q", *targets)) == row["targets_sha256"], "Scored targets SHA")
        require(row["shape"] == [64, 32768] and row["dtype"] == "float32-le", "Raw scored tensor layout")
        require(row["retention"] == expected_retention(row, data), "Predeclared retention selection")
        requested_raw = Path(row["raw_path"])
        require(requested_raw.is_absolute() and requested_raw.is_file() and not requested_raw.is_symlink(), "New regular raw file, never symlink")
        raw_path = requested_raw.resolve()
        private = (Path(spec["output"]) / "private").resolve()
        require(raw_path.is_relative_to(private) and raw_path.parent == private, "New raw confined to attempt private directory")
        require(info(raw_path) == {"bytes": RAW_BYTES, "sha256": row["logits_sha256"]}, "Complete raw bytes/SHA")
        require(row["observer"]["h0_sha256"] == row["h0_sha256"] and row["observer"]["seed"] == row["eval_seed"], "Actual initial-state identity")
        result = compute(np, raw_path.read_bytes(), targets)
        report["Actual"] = result
        require(result["raw"] == {"bytes": RAW_BYTES, "sha256": row["logits_sha256"]}, "Raw unchanged during audit read")
        compare_worker(row, result)
        result["baseline_reference"] = None
        if row["arm"] == "fixed32":
            bridge_phase = True
            result["baseline_reference"] = historical_bridge(spec, row, result)
            bridge_phase = False
        report["Actual"] = result
        report["Status"] = "PASS"
    except BaseException as exc:
        report["Status"] = "BLOCKED" if bridge_phase or isinstance(exc, (OSError, MemoryError)) else "FAIL"
        report["error"] = {"type": type(exc).__name__, "reason": str(exc), "traceback": traceback.format_exc(),
                           "scope": "historical baseline equivalence not established" if bridge_phase else "live row audit"}
    save(args.output, report)
    return 0 if report["Status"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
