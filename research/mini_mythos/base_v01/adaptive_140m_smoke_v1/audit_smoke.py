"""Independent stdlib-only audit of frozen smoke artifacts; never loads a model."""
import argparse
import collections
import datetime
import hashlib
import json
import math
from pathlib import Path
import statistics
import struct
import sys
import traceback


class Rejected(Exception):
    pass


class Incomplete(Exception):
    pass


INPUTS_SHA = "3abb324ea2876abb78e18d86ec257a9e1d388f9501bd8cdd6c99011ac11cf41e"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def file_info(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": digest(data)}


def safe_path(root, name):
    relative = Path(name)
    path = (root / relative).resolve()
    if relative.is_absolute() or not path.is_relative_to(root.resolve()) or path == root.resolve():
        raise Rejected("Artifact path escapes worker directory")
    return path


def fp32_values(data):
    if not data or len(data) % 4:
        raise Rejected("Invalid FP32 byte extent")
    values = [x[0] for x in struct.iter_unpack("<f", data)]
    if not all(math.isfinite(x) for x in values):
        raise Rejected("Nonfinite FP32 artifact")
    return values


def scalar_tv(left, right):
    if len(left) != len(right) or not left:
        raise Rejected("Mismatched TV vectors")
    def probabilities(values):
        maximum = max(values)
        exponents = [math.exp(x - maximum) for x in values]
        total = math.fsum(exponents)
        return [x / total for x in exponents]
    return math.fsum(abs(a - b) for a, b in zip(probabilities(left), probabilities(right))) / 2


class Audit:
    def __init__(self, root):
        self.root = root.resolve()
        self.checks = []
        self.finite_components = 0
        self.read_raw = {}

    def check(self, name, okay, actual=None, expected=True):
        self.checks.append({"Purpose": name, "Environment": "Independent Python stdlib; no torch/model imports",
                            "Input": str(self.root), "Expected": expected, "Actual": actual,
                            "Status": "PASS" if okay else "FAIL"})
        if not okay:
            raise Rejected(name)

    def read(self, name):
        return json.loads(safe_path(self.root, name).read_text(encoding="utf-8"))

    def raw(self, meta, shape, dtype="torch.float32"):
        key = meta["path"]
        data = safe_path(self.root, key).read_bytes()
        size = math.prod(shape) * (4 if dtype == "torch.float32" else 1)
        self.check("raw metadata/hash/extent " + key,
                   meta["shape"] == shape and meta["dtype"] == dtype and meta["byteorder"] == "little"
                   and meta["bytes"] == len(data) == size and digest(data) == meta["sha256"])
        if dtype == "torch.float32" and key not in self.read_raw:
            values = fp32_values(data)
            self.finite_components += len(values)
        self.read_raw[key] = data
        return data

    def run(self):
        completion = self.read("public/completion.json")
        if completion.get("Status") not in ("PASS", "FAIL"):
            raise Incomplete("Worker is incomplete/BLOCKED; an independent success audit is not established")
        actual = completion["Actual"]
        self.check("complete worker gate", completion["Status"] == "PASS" and completion["complete_coverage"] is True
                   and actual["calls_started"] == actual["calls_completed"] == 55
                   and actual["groups_completed"] == 6 and actual["loader_attempts"] == actual["loader_returns"] == 1
                   and actual["preservation"] == "PASS" and actual["error"] is None and not actual["save_errors"], actual)
        manifest = self.read("FULL_MANIFEST.json")
        names = {str(p.relative_to(self.root)).replace("\\", "/") for p in self.root.rglob("*") if p.is_file()}
        excluded = {"FULL_MANIFEST.json", "public/GIT_BUNDLE_MANIFEST.json"}
        self.check("exact artifact manifest coverage", set(manifest["excluded"]) == excluded
                   and set(manifest["entries"]) == names - excluded, len(names))
        for name, expected in manifest["entries"].items():
            self.check("artifact SHA/size " + name, file_info(safe_path(self.root, name)) == expected)
        public = self.read("public/GIT_BUNDLE_MANIFEST.json")
        self.check("public manifest coverage", public["entries"] == {
            k: v for k, v in manifest["entries"].items() if k.startswith("public/")})
        checks = [json.loads(line) for line in safe_path(self.root, "public/checks.jsonl").read_text().splitlines()]
        tally = dict(collections.Counter(row["Status"] for row in checks))
        self.check("all recorded worker checks complete and passing", bool(checks) and set(tally) == {"PASS"}
                   and actual["checks"] == {"PASS": len(checks), "FAIL": 0, "BLOCKED": 0}, tally)
        state = self.read("public/state_before.json")
        self.check("all63 state entries preserved", state == self.read("public/state_after.json")
                   and state["state_count"] == len(state["entries"]) == 63
                   and state["aggregate_sha256"] == digest(canonical(state["entries"])))
        for name, meta in state["entries"].items():
            self.check("state metadata " + name, meta["dtype"] == "torch.float32"
                       and meta["bytes"] == math.prod(meta["shape"]) * 4 and len(meta["sha256"]) == 64)
        for name in ("config", "packages"):
            self.check(name + " unchanged", self.read("public/" + name + "_before.json") == self.read("public/" + name + "_after.json"))
        before = self.read("public/protected_before.json")
        self.check("source/input/Git custody", before["files"] == self.read("public/protected_after.json")["files"]
                   and before["git"] == self.read("public/git_after.json")
                   and self.read("public/preservation.json")["Status"] == "PASS")
        spec = self.read("public/spec.json")
        input_path = Path(spec["inputs_path"])
        self.check("frozen original input artifact", input_path.is_absolute()
                   and file_info(input_path)["sha256"] == INPUTS_SHA
                   and before["files"][str(input_path)]["sha256"] == INPUTS_SHA)
        samples = json.loads(input_path.read_text(encoding="utf-8"))["samples"]
        source_tokens = samples[0]["tokens"]
        self.check("original sample0 input coverage", len(samples) == 32 and samples[0]["index"] == 0
                   and len(source_tokens) == 257 and all(type(v) is int and 0 <= v < 32768 for v in source_tokens))
        environment = self.read("public/environment.json")
        self.check("frozen CPU environment identity", environment["torch"] == "2.11.0+cpu"
                   and environment["executable"] == "/workspaces/mythos-base-v01-cpu312/bin/python"
                   and environment["library_sha256"] == "daa6b5b014f9d5f77cc47e2ba14a7027065c135b2cac7f6bcda58d0e6d6457b8"
                   and environment["upstream"] == "69284c13746e849104f738d6d1a347b1f457df76")
        rows = [json.loads(line) for line in safe_path(self.root, "public/calls.jsonl").read_text().splitlines()]
        groups = [(length, seed) for length in (1, 16, 64) for seed in (3101, 3202)]
        modes = [("native", d) for d in (8, 16, 32)] + [("fixed", d) for d in (8, 16, 32)] + [
            ("diagnostic", None), ("adaptive", None), ("adaptive_repeat", None)]
        plan = [(length, seed, mode, depth) for length, seed in groups for mode, depth in modes] + [(64, 3101, "causal_mutated", None)]
        self.check("exact55 ordered condition records", len(rows) == 55)
        output_data, pairing = {}, {}
        mapping = {"embedding": "embedding_calls", "prelude": "prelude_block_calls", "prelude_norm": "prelude_norm_calls",
                   "adapter": "adapter_calls", "core": "core_block_calls", "projection": "projection_calls",
                   "coda": "coda_block_calls", "final_norm": "final_norm_calls", "head": "head_calls",
                   "value_embedding": "value_embedding_calls"}
        for number, (row, (length, seed, mode, requested)) in enumerate(zip(rows, plan), 1):
            self.check("call record/JSONL/order " + str(number), row == self.read(f"public/call_{number:03d}.json")
                       and row["call"] == number and row["status"] == "PASS" and row["error"] is None
                       and not row["cleanup_errors"] and row["context"]["prefix_length"] == length
                       and row["context"]["seed"] == seed and row["mode"] == mode and row["requested_depth"] == requested
                       and row["input_shape"] == [1, length])
            expected_ids = source_tokens[:length]
            if number == 55:
                expected_ids = expected_ids[:32] + [(v + 1) % 32768 for v in expected_ids[32:]]
            input_bytes = struct.pack("<" + "q" * length, *expected_ids)
            self.check("exact original-prefix token identity " + str(number),
                       row["input_sha256"] == digest(input_bytes)
                       and row["input_ids_json_sha256"] == digest(canonical([expected_ids])))
            selected = row["selected_depth"]
            if mode in ("native", "fixed"):
                keys = [requested]
                self.check("fixed selected depth " + str(number), selected == requested)
            elif mode in ("diagnostic", "causal_mutated"):
                keys = [8, 16, 32]
                self.check("diagnostic full depth " + str(number), selected == 32)
            else:
                tv = row["tv_8_16"]
                self.check("frozen TV branch " + str(number), math.isfinite(tv) and 0 <= tv <= 1
                           and selected == (16 if tv <= 0.01 else 32))
                keys = [8, 16] if selected == 16 else [8, 16, 32]
            self.check("readout key order " + str(number), list(row["outputs"]) == [str(d) for d in keys])
            readouts = len(keys)
            counts = {"embedding": 1, "prelude": 2, "prelude_norm": 1, "adapter": selected, "core": 2 * selected,
                      "projection": readouts, "coda": 2 * readouts, "final_norm": readouts, "head": readouts,
                      "value_embedding": 1 + selected + readouts}
            self.check("independent exact operation counts " + str(number), row["actual_counts"] == counts, row["actual_counts"], counts)
            observed = row["observed"]
            self.check("actual h0/readout/head coverage " + str(number), len(observed["h0"]) == 1
                       and len(observed["readout_states"]) == len(observed["head_outputs"]) == readouts)
            h0 = self.raw(observed["h0"][0], [1, length, 768])
            rng = []
            for name in ("rng_before", "rng_after"):
                meta = row[name]
                self.check("RNG metadata " + str(number), len(meta["shape"]) == 1 and meta["shape"][0] > 0)
                data = self.raw(meta, meta["shape"], "torch.uint8")
                self.check("RNG hash annotation " + str(number), digest(data) == row[name + "_sha256"])
                rng.append(data)
            pairing[number] = (h0, *rng, observed["h0"][0]["rng_after_init_sha256"])
            output_data[number] = {d: self.raw(row["outputs"][str(d)], [1, 32768]) for d in keys}
            self.check("observed readout shape coverage " + str(number),
                       all(r["shape"] == [1, length, 768] for r in observed["readout_states"])
                       and all(r["shape"] == [1, length, 32768] and r["dtype"] == "torch.float32" for r in observed["head_outputs"]))
            if mode != "native":
                library = row["library_counts"]
                adaptive = mode in ("adaptive", "adaptive_repeat")
                self.check("library independent observation identity " + str(number),
                           all(library[b] == counts[a] for a, b in mapping.items())
                           and library["policy_evaluations"] == int(adaptive) and library["policy_softmax_calls"] == 2 * int(adaptive)
                           and row["library_h0_sha256"] == observed["h0"][0]["sha256"]
                           and row["library_rng_before_sha256"] == row["rng_before_sha256"]
                           and row["library_rng_after_sha256"] == row["rng_after_sha256"]
                           and row["library_state_sha256"] == {str(d): observed["readout_states"][i]["sha256"] for i, d in enumerate(keys)})
            self.check("finite descriptive timings " + str(number), all(math.isfinite(row[k]) and row[k] >= 0
                       for k in ("api_observed_seconds", "call_total_seconds")))
        tv_reports, exits = [], collections.Counter()
        for group, (length, seed) in enumerate(groups):
            start = 9 * group
            reference = {d: output_data[start + i + 1][d] for i, d in enumerate((8, 16, 32))}
            native_states = {str(d): rows[start + i]["observed"]["readout_states"][0]["sha256"] for i, d in enumerate((8, 16, 32))}
            for offset in range(1, 10):
                number, row = start + offset, rows[start + offset - 1]
                self.check("paired bytes/input " + str(number), pairing[number] == pairing[start + 1]
                           and row["input_sha256"] == rows[start]["input_sha256"]
                           and row["input_ids_json_sha256"] == rows[start]["input_ids_json_sha256"])
                self.check("all emitted logits independently match native bytes " + str(number),
                           all(data == reference[d] for d, data in output_data[number].items()))
                self.check("resumed recurrence state matches native " + str(number), all(
                    rec["sha256"] == native_states[d] for rec, d in zip(row["observed"]["readout_states"], row["outputs"])))
            adaptive, repeated = rows[start + 7], rows[start + 8]
            self.check("exact adaptive repeat " + str(group), all(adaptive[key] == repeated[key] for key in (
                "selected_depth", "tv_8_16", "library_counts", "library_state_sha256", "actual_counts"))
                and output_data[start + 8] == output_data[start + 9])
            independent_tv = scalar_tv(fp32_values(reference[8]), fp32_values(reference[16]))
            recorded_tv = adaptive["tv_8_16"]
            self.check("independent scalar TV " + str(group), abs(independent_tv - recorded_tv) <= 1e-12,
                       {"recorded": recorded_tv, "independent": independent_tv, "absolute_difference": abs(independent_tv - recorded_tv)}, "absolute <=1e-12; no gate relaxation")
            tv_reports.append({"prefix_length": length, "seed": seed, "recorded_tv": recorded_tv,
                               "scalar_tv": independent_tv, "selected_depth": adaptive["selected_depth"],
                               "scalar_predicate_disagreement": (independent_tv <= 0.01) != (recorded_tv <= 0.01),
                               "within_arithmetic_tolerance_of_threshold": abs(recorded_tv - 0.01) <= 1e-12})
            exits[adaptive["selected_depth"]] += 1
        base, changed = rows[42], rows[54]
        self.check("causal h0/RNG identity", pairing[43] == pairing[55])
        tokens = self.read("private/prefix_tokens.json")
        original, mutated = tokens["original64"], tokens["causal_mutated64"]
        self.check("exact suffix intervention input", len(original) == len(mutated) == 64 and original[:32] == mutated[:32]
                   and original == source_tokens[:64]
                   and mutated[32:] == [(x + 1) % 32768 for x in original[32:]]
                   and digest(canonical([original])) == base["input_ids_json_sha256"]
                   and digest(canonical([mutated])) == changed["input_ids_json_sha256"])
        for i in range(3):
            left = self.raw(base["observed"]["head_prefixes"][i], [1, 32, 32768])
            right = self.raw(changed["observed"]["head_prefixes"][i], [1, 32, 32768])
            self.check("causal raw prefix bytes at depth " + str((8, 16, 32)[i]), left == right)
        contrasts = [base["observed"]["head_suffixes"][i]["sha256"] != changed["observed"]["head_suffixes"][i]["sha256"] for i in range(3)]
        self.check("causal suffix sensitivity recorded", any(contrasts), contrasts)
        costs = []
        for mode, depth in modes:
            records = [r for r in rows[:54] if r["mode"] == mode and r["requested_depth"] == depth]
            costs.append({"mode": mode, "depth": depth, "groups": len(records),
                          "median_instrumented_api_seconds": statistics.median(r["api_observed_seconds"] for r in records),
                          "observed_core_calls": [r["actual_counts"]["core"] for r in records],
                          "observed_head_calls": [r["actual_counts"]["head"] for r in records]})
        return {"mechanism_results": {"identity": "PASS", "causal_prefix": "PASS", "state_preservation": "PASS",
                    "state_evidence_scope": "Worker compared all63 tensors against original weight bytes; independent audit verifies before/after digest inventories, not a second full-weight tensor comparison",
                    "forward_calls": 55, "groups": 6, "natural_exit_counts": {str(k): exits[k] for k in (16, 32)},
                    "natural_branch_coverage": {str(k): "PASS" if exits[k] else "NOT TESTED" for k in (16, 32)},
                    "tv_reports": tv_reports, "raw_finite_components_checked": self.finite_components,
                    "quality_improvement": "NOT TESTED", "training_recovery": "NOT TESTED"},
                "describe_cost": {"records": costs, "timing_scope": "Instrumented API including guards/hash/clones/readouts/policy/observers",
                    "benchmark_limit": "Fixed call order, shared CPU, six paired prefix/seed groups from one historical article. Not a hardware speedup benchmark.",
                    "extra_readouts_over_same_depth_native": {"adaptive16": 1, "adaptive32": 2},
                    "hardware_efficiency_superiority": "NOT TESTED"}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if not args.run.is_absolute() or not args.output.is_absolute() or args.output.resolve().is_relative_to(args.run.resolve()):
        parser.error("absolute paths required; audit output must be outside sealed worker tree")
    audit = Audit(args.run)
    status, result, error = "NOT TESTED", {}, None
    try:
        result = audit.run()
        status = "PASS"
    except BaseException as exc:
        status = "BLOCKED" if isinstance(exc, (OSError, Incomplete)) else "FAIL"
        error = {"type": type(exc).__name__, "reason": str(exc), "traceback": traceback.format_exc()}
    report = {"Purpose": "Independent complete raw-byte/count/TV artifact audit", "Environment": sys.version,
              "Input": str(args.run), "Expected": "Complete55 calls, all byte identities and frozen cost counts; no model invocation",
              "Actual": {**result, "checks": audit.checks, "error": error}, "Status": status,
              "utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"Status": status, "checks": len(audit.checks), "error": error}))
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
