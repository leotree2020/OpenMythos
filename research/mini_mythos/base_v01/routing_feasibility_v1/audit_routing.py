"""Independent data-token and saved-output audit. Never imports Torch or a worker."""
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

PINS = {
    "corpus": "3ee89cd6a2ab912afd5d01e98867b46a67d9ec7a9eca0910e5e4c3cdd4cc1925",
    "tokenizer": "e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77",
    "ledger": "f5f7858b989451671e4c7ed27192642dec3f9b2a1ccd214cc9e3cc30bcebb5d3",
    "partition": "95a217a815596c928a0b721837b567a08ed8c6f667839fdf6d4311113c253aa4",
    "old_inputs": "f38a1618d7904df7c530d9f0f322949a847befcb75e4177de2bc8e65bc53a315",
    "corrected_inputs": "3abb324ea2876abb78e18d86ec257a9e1d388f9501bd8cdd6c99011ac11cf41e",
    "selection_change": "7baab72fb993e2f49f806f99d70fb162441f994371136e52e42277fa361474f6",
}


class Reject(Exception):
    pass


class Incomplete(Exception):
    pass


def canonical(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def sha(x):
    return hashlib.sha256(x).hexdigest()


def info(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": sha(data)}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def safe(root, name):
    p = Path(name)
    result = (root / p).resolve()
    if p.is_absolute() or not result.is_relative_to(root.resolve()) or result == root.resolve():
        raise Reject("Artifact path escape")
    return result


def values(data):
    if not data or len(data) % 4:
        raise Reject("Invalid FP32 extent")
    result = [x[0] for x in struct.iter_unpack("<f", data)]
    if not all(math.isfinite(x) for x in result):
        raise Reject("Nonfinite FP32 bytes")
    return result


def tv(left, right):
    if len(left) != len(right) or not left:
        raise Reject("TV vector extent mismatch")
    def probabilities(x):
        maximum = max(x)
        e = [math.exp(v - maximum) for v in x]
        total = math.fsum(e)
        return [v / total for v in e]
    return math.fsum(abs(a - b) for a, b in zip(probabilities(left), probabilities(right))) / 2


def choose(partition, old, corrected):
    """Independent source-union selection, no producer helpers or score access."""
    roles, articles = partition["row_roles"], partition["articles"]
    old_keys = {roles[s["heading_row"]]["source_article_key"] for s in old["samples"]}
    new_keys = {s["source_article_key"] for s in corrected["samples"]}
    if (len(articles), len(old["samples"]), len(corrected["samples"]), len(old_keys), len(new_keys), len(old_keys & new_keys), len(old_keys | new_keys)) != (60, 32, 32, 31, 32, 30, 33):
        raise Reject("Historical source exclusion counts differ")
    eligible = sorted((a for a in articles if a["eligible"] is True and a["full_token_count"] >= 257 and a["source_article_key"] not in old_keys | new_keys), key=lambda a: a["article_id"])
    if len(eligible) != 27 or sum(a["eligible"] is True for a in articles) != 60:
        raise Reject("Historical eligible source coverage differs")
    return eligible[:16], sorted(old_keys | new_keys)


def decision_summary(rows):
    if len(rows) != 32:
        raise Reject("Exact32 routing rows required")
    pairs, seeds = [], {"3101": 0, "3202": 0}
    for index in range(16):
        pair = rows[2 * index:2 * index + 2]
        for seed, row in zip((3101, 3202), pair):
            if row["context"]["article_index"] != index or row["context"]["seed"] != seed:
                raise Reject("Article/seed ordering differs")
            if row["selected_depth"] == 16:
                seeds[str(seed)] += 1
        exits = [r["selected_depth"] for r in pair]
        pairs.append({"article_index": index, "source_article_key": pair[0]["context"]["source_article_key"],
                      "depths": exits, "pattern": "both16" if exits == [16, 16] else "both32" if exits == [32, 32] else "discordant"})
    early = sum(seeds.values())
    return {"early_exit_counts": {"16": early, "32": 32 - early}, "per_seed_early_exits": seeds,
            "article_pairs": pairs, "article_pair_counts": dict(collections.Counter(p["pattern"] for p in pairs)),
            "early_exit_screen": {"Status": "PASS" if early else "FAIL", "Expected": "At least one16-depth exit among32valid calls",
                                  "Actual": early, "meaning": "EARLY_EXIT_OBSERVED_ON_THIS_SAMPLE" if early else "NO_EARLY_EXIT_ON_THIS_SAMPLE"},
            "quality_improvement": "NOT TESTED", "net_acceleration": "NOT TESTED", "independent_source_units": 16}


class Audit:
    def __init__(self, root):
        self.root = root.resolve()
        self.worker = self.root / "worker"
        self.checks, self.raw_seen, self.finite_components = [], set(), 0

    def check(self, purpose, okay, actual=None, expected=True):
        self.checks.append({"Purpose": purpose, "Environment": "Pinned data-only Python; independent scalar arithmetic; no Torch/model",
                            "Input": str(self.root), "Expected": expected, "Actual": actual, "Status": "PASS" if okay else "FAIL"})
        if not okay:
            raise Reject(purpose)

    def raw(self, meta, shape, dtype="torch.float32"):
        path = safe(self.worker, meta["path"])
        data = path.read_bytes()
        self.check("raw extent/type/hash " + meta["path"], meta["shape"] == shape and meta["dtype"] == dtype
                   and meta["byteorder"] == "little" and len(data) == meta["bytes"] == math.prod(shape) * (4 if dtype == "torch.float32" else 1)
                   and sha(data) == meta["sha256"])
        if dtype == "torch.float32" and meta["path"] not in self.raw_seen:
            self.finite_components += len(values(data))
            self.raw_seen.add(meta["path"])
        return data

    def audit_data(self):
        out = self.root / "data"
        completion = read(out / "public/completion.json")
        if completion.get("Status") not in ("PASS", "FAIL"):
            raise Incomplete("Data stage incomplete")
        self.check("data completion coverage", completion["Status"] == "PASS" and completion["Actual"]["sample_count"] == 16
                   and completion["Actual"]["call_budget"] == 32 and completion["error"] is None
                   and completion["preservation"]["Status"] == "PASS" and completion["formal_model_calls"] == 0)
        data_checks = [json.loads(x) for x in (out / "public/checks.jsonl").read_text().splitlines()]
        self.check("recorded data checks", bool(data_checks) and data_checks == completion["checks"] and all(x["Status"] == "PASS" for x in data_checks))
        self.check("data artifact coverage", set(completion["artifacts"]) == {"private/inputs.json", "public/selection.json"})
        for name, expected in completion["artifacts"].items():
            self.check("data artifact hash " + name, info(safe(out, name)) == expected)
        spec = read(out / "public/spec.json")
        self.check("data spec completion binding", spec == completion["Input"])
        for key, pin in PINS.items():
            self.check("original data source hash " + key, Path(spec[key]).is_absolute() and info(Path(spec[key]))["sha256"] == pin)
        for path, expected in read(out / "public/sources_before.json").items():
            self.check("data source unchanged " + path, info(Path(path)) == expected)
        self.check("data interpreter", sys.executable == "/workspaces/mythos-depth-data-cpu312/bin/python" and sys.version_info[:3] == (3, 12, 3))
        import pyarrow
        import pyarrow.parquet as parquet
        import numpy
        import tokenizers
        self.check("data audit package versions", (pyarrow.__version__, numpy.__version__, tokenizers.__version__) == ("19.0.1", "1.26.4", "0.23.2"))
        rows = parquet.read_table(spec["corpus"], columns=["text"]).column("text").to_pylist()
        partition, ledger, old, corrected, change = [read(Path(spec[key])) for key in ("partition", "ledger", "old_inputs", "corrected_inputs", "selection_change")]
        self.check("whole decoded corpus identity", len(rows) == 4358 and sha(canonical(rows)) == partition["rows_sha256"] == ledger["rows_sha256"]
                   and partition["all_row_sha256"] == [sha(row.encode()) for row in rows])
        headings = sorted(x["row"] for x in ledger["decisions"] if x["decision"] == "ACCEPT_TITLE")
        self.check("reviewed ledger boundaries", headings == ledger["accepted_heading_rows"] and len(headings) == 60)
        selected, excluded = choose(partition, old, corrected)
        inputs, selection = read(out / "private/inputs.json"), read(out / "public/selection.json")
        self.check("selected metadata artifact binding", selection["inputs_artifact"] == {"path": "private/inputs.json", **info(out / "private/inputs.json")}
                   and selection["excluded_union_sources"] == excluded and len(selection["selected"]) == 16)
        self.check("input header and sample coverage", inputs["context_tokens"] == 128 and inputs["seeds"] == [3101, 3202]
                   and len(inputs["samples"]) == 16)
        roles = partition["row_roles"]
        mapping = [{"old_index": s["index"], "old_heading_row": s["heading_row"], "reviewed_heading_row": roles[s["heading_row"]]["heading_row"],
                    "source_article_key": roles[s["heading_row"]]["source_article_key"]} for s in old["samples"]]
        self.check("old formula source mapping independently matches", mapping == change["Actual"]["old_sample_to_reviewed_source"] == selection["old_sample_to_reviewed_source"])
        tokenizer = tokenizers.Tokenizer.from_file(spec["tokenizer"])
        prior_prefixes = {sha(canonical(s["tokens"][:128])) for s in old["samples"] + corrected["samples"]}
        observed_prefixes = set()
        for index, (article, sample) in enumerate(zip(selected, inputs["samples"])):
            h = article["heading_row"]
            position = headings.index(h)
            end = headings[position + 1] if position + 1 < len(headings) else len(rows)
            body_rows = list(range(h + 1, end))
            body, title = "".join(rows[h + 1:end]), rows[h].strip()
            key = sha(canonical({"corpus_sha256": PINS["corpus"], "heading_row": h, "title": title}))
            self.check("independent source partition " + str(index), body_rows == article["body_rows"] == sample["body_rows"]
                       and key == article["source_article_key"] == sample["source_article_key"]
                       and sha((title + "\n" + body).encode()) == article["article_id"] == sample["article_id"]
                       and sha(body.encode()) == article["text_sha256"] == sample["text_sha256"] and sample["index"] == index
                       and key not in excluded)
            tokens = tokenizer.encode(body, add_special_tokens=False).ids
            prefix = tokens[:128]
            self.check("independent exact128 retokenization " + str(index), len(tokens) == article["full_token_count"] == sample["full_token_count"]
                       and len(prefix) == 128 and all(type(t) is int and 0 <= t < 32768 for t in prefix)
                       and sample["tokens"] == prefix and sample["input_ids_sha256"] == sha(canonical(prefix))
                       and sample["raw_input_sha256"] == sha(struct.pack("<128q", *prefix))
                       and selection["selected"][index] == {k: v for k, v in sample.items() if k != "tokens"})
            self.check("prefix novelty against prior and selected inputs " + str(index), sample["input_ids_sha256"] not in prior_prefixes | observed_prefixes)
            observed_prefixes.add(sample["input_ids_sha256"])
        self.check("no numerical model import during data audit", not any(k.split(".")[0] in ("torch", "parcae_lm", "receval", "transformers") for k in sys.modules))
        return inputs["samples"]

    def run(self):
        samples = self.audit_data()
        w = self.worker
        completion = read(w / "public/completion.json")
        if completion.get("Status") not in ("PASS", "FAIL"):
            raise Incomplete("Model worker incomplete")
        c = completion["Actual"]
        self.check("worker exact32 complete", completion["Status"] == "PASS" and completion["complete_coverage"] is True
                   and c["calls_started"] == c["calls_completed"] == 32 and c["groups_completed"] == 16
                   and c["loader_attempts"] == c["loader_returns"] == 1 and c["error"] is None and not c["save_errors"]
                   and c["preservation"] == "PASS")
        manifest = read(w / "FULL_MANIFEST.json")
        excluded = {"FULL_MANIFEST.json", "public/GIT_BUNDLE_MANIFEST.json"}
        actual_names = {str(p.relative_to(w)).replace("\\", "/") for p in w.rglob("*") if p.is_file()}
        self.check("complete worker artifact set", set(manifest["excluded"]) == excluded and set(manifest["entries"]) == actual_names - excluded)
        for name, expected in manifest["entries"].items():
            self.check("worker file hash " + name, info(safe(w, name)) == expected)
        self.check("worker public manifest", read(w / "public/GIT_BUNDLE_MANIFEST.json")["entries"] == {k: v for k, v in manifest["entries"].items() if k.startswith("public/")})
        checks = [json.loads(line) for line in (w / "public/checks.jsonl").read_text().splitlines()]
        self.check("worker checks full coverage", bool(checks) and all(x["Status"] == "PASS" for x in checks)
                   and c["checks"] == {"PASS": len(checks), "FAIL": 0, "BLOCKED": 0})
        before = read(w / "public/protected_before.json")
        self.check("protected files/Git preserved", before["files"] == read(w / "public/protected_after.json")["files"]
                   and before["git"] == read(w / "public/git_after.json") and read(w / "public/preservation.json")["Status"] == "PASS")
        spec = read(w / "public/spec.json")
        self.check("worker/operator/completion spec identity", spec == read(self.root / "operator/spec.json") == completion["Input"]["spec"])
        source_manifest = self.root / "operator/source_manifest.json"
        self.check("source manifest bound to protected files", Path(spec["source_manifest_path"]).resolve() == source_manifest.resolve()
                   and info(source_manifest)["sha256"] == spec["source_manifest_sha256"]
                   and before["files"][str(source_manifest)] == info(source_manifest)
                   and all(before["files"].get(path) == expected for path, expected in read(source_manifest).items()))
        self.check("worker consumed exact prepared data", Path(spec["inputs_path"]).resolve() == (self.root / "data/private/inputs.json").resolve()
                   and info(Path(spec["inputs_path"]))["sha256"] == spec["inputs_sha256"]
                   and Path(spec["data_manifest_path"]).resolve() == (self.root / "data/public/completion.json").resolve()
                   and info(Path(spec["data_manifest_path"]))["sha256"] == spec["data_manifest_sha256"])
        state = read(w / "public/state_before.json")
        self.check("full63 state inventory preserved", state == read(w / "public/state_after.json") and state["state_count"] == len(state["entries"]) == 63
                   and state["aggregate_sha256"] == sha(canonical(state["entries"])))
        for key in ("config", "packages"):
            self.check(key + " unchanged", read(w / ("public/" + key + "_before.json")) == read(w / ("public/" + key + "_after.json")))
        self.check("original unit logit scale permits direct head-byte binding", read(w / "public/config_before.json")["init_logit_scale"] == 1.0)
        rows = [json.loads(line) for line in (w / "public/calls.jsonl").read_text().splitlines()]
        self.check("32 condition rows", len(rows) == 32)
        by_seed, scalar_results = {}, []
        mapping = {"embedding": "embedding_calls", "prelude": "prelude_block_calls", "prelude_norm": "prelude_norm_calls",
                   "adapter": "adapter_calls", "core": "core_block_calls", "projection": "projection_calls", "coda": "coda_block_calls",
                   "final_norm": "final_norm_calls", "head": "head_calls", "value_embedding": "value_embedding_calls"}
        for number, row in enumerate(rows, 1):
            article, seed = (number - 1) // 2, (3101, 3202)[(number - 1) % 2]
            sample = samples[article]
            self.check("call order/evidence identity " + str(number), row == read(w / f"public/call_{number:03d}.json")
                       and row["call"] == number and row["status"] == "PASS" and not row["cleanup_errors"] and row["error"] is None
                       and row["mode"] == "adaptive" and row["requested_depth"] is None and row["input_shape"] == [1, 128]
                       and row["context"]["seed"] == seed and row["context"]["article_index"] == article
                       and row["context"]["source_article_key"] == sample["source_article_key"]
                       and row["input_sha256"] == sample["raw_input_sha256"]
                       and row["input_ids_json_sha256"] == sha(canonical([sample["tokens"]])))
            depth, recorded_tv = row["selected_depth"], row["tv_8_16"]
            self.check("frozen branch " + str(number), math.isfinite(recorded_tv) and 0 <= recorded_tv <= 1
                       and depth == (16 if recorded_tv <= .01 else 32))
            keys = [8, 16] if depth == 16 else [8, 16, 32]
            r = len(keys)
            expected_counts = {"embedding": 1, "prelude": 2, "prelude_norm": 1, "adapter": depth, "core": 2 * depth,
                               "projection": r, "coda": 2 * r, "final_norm": r, "head": r, "value_embedding": 1 + depth + r}
            self.check("complete readout/operation counts " + str(number), set(row["outputs"]) == {str(d) for d in keys}
                       and row["actual_counts"] == expected_counts
                       and all(row["library_counts"][b] == expected_counts[a] for a, b in mapping.items())
                       and row["library_counts"]["policy_evaluations"] == 1 and row["library_counts"]["policy_softmax_calls"] == 2)
            extra_counts = {"h0_calls": 1, "recurrent_updates": depth, "readouts": r,
                            "policy_vocabulary_elements": 65536, "readout_clone_elements": r * 128 * 768,
                            "total_block_calls": 2 + 2 * depth + 2 * r}
            self.check("complete controller bookkeeping counts " + str(number),
                       all(row["library_counts"][k] == v for k, v in extra_counts.items()))
            obs = row["observed"]
            self.check("observed initialization and readouts " + str(number), len(obs["h0"]) == 1
                       and len(obs["readout_states"]) == len(obs["head_outputs"]) == r)
            h0 = self.raw(obs["h0"][0], [1, 128, 768])
            rng = [self.raw(row[k], row[k]["shape"], "torch.uint8") for k in ("rng_before", "rng_after")]
            self.check("observed/library state and RNG annotations " + str(number),
                       row["library_h0_sha256"] == sha(h0) and row["library_rng_before_sha256"] == row["rng_before_sha256"] == sha(rng[0])
                       and row["library_rng_after_sha256"] == row["rng_after_sha256"] == sha(rng[1])
                       and row["library_state_sha256"] == {str(d): obs["readout_states"][i]["sha256"] for i, d in enumerate(keys)})
            identity = (h0, *rng, obs["h0"][0]["rng_after_init_sha256"])
            by_seed.setdefault(seed, identity)
            self.check("same-seed real h0/RNG pairing " + str(number), identity == by_seed[seed])
            outputs = {d: self.raw(row["outputs"][str(d)], [1, 32768]) for d in keys}
            self.check("readout observer shapes and saved last logits " + str(number),
                       all(x["shape"] == [1, 128, 768] for x in obs["readout_states"])
                       and all(x["shape"] == [1, 128, 32768] and x["dtype"] == "torch.float32"
                               and x["last_raw_sha256"] == sha(outputs[d])
                               for d, x in zip(keys, obs["head_outputs"])))
            independent = tv(values(outputs[8]), values(outputs[16]))
            self.check("independent scalar TV " + str(number), abs(independent - recorded_tv) <= 1e-12,
                       {"recorded": recorded_tv, "independent": independent}, "absolute<=1e-12,rtol0; frozen decision unchanged")
            scalar_results.append({"call": number, "article_index": article, "seed": seed, "tv": recorded_tv,
                                   "scalar_tv": independent, "selected_depth": depth,
                                   "scalar_predicate_disagreement": (independent <= .01) != (recorded_tv <= .01),
                                   "near_threshold": abs(recorded_tv - .01) <= 1e-12})
            self.check("finite descriptive timing " + str(number), all(math.isfinite(row[k]) and row[k] >= 0
                       for k in ("api_observed_seconds", "call_total_seconds", "policy_seconds")))
        result = decision_summary(rows)
        routing = read(w / "public/routing_results.json")
        self.check("worker scientific count agrees", c["routing"]["selected_depth_counts"] == result["early_exit_counts"]
                   and routing["Status"] == "PASS" and routing["Actual"]["routing"] == c["routing"])
        reported = routing["Actual"]["records"]
        self.check("all public routing rows consistent", len(reported) == 32 and all(
            z["call"] == x["call"] and z["article_index"] == x["context"]["article_index"] and z["seed"] == x["context"]["seed"]
            and z["selected_depth"] == x["selected_depth"] and z["tv_8_16"] == x["tv_8_16"]
            and z["actual_counts"] == x["actual_counts"] for z, x in zip(reported, rows)))
        result.update(tv_reports=scalar_results, finite_saved_fp32_components=self.finite_components,
                      engineering_status="PASS", state_evidence_scope="Worker restored all63 original tensors by bytes; independent audit verifies saved before/after state inventories")
        totals = {key: sum(row["actual_counts"][key] for row in rows) for key in rows[0]["actual_counts"]}
        baseline = {"embedding": 32, "prelude": 64, "prelude_norm": 32, "adapter": 1024, "core": 2048,
                    "projection": 32, "coda": 64, "final_norm": 32, "head": 32, "value_embedding": 1088}
        timings = [r["api_observed_seconds"] for r in rows]
        return {"mechanism_results": result, "describe_cost": {"observed_totals": totals, "analytic_fixed32_totals": baseline,
                    "observed_minus_analytic_fixed32": {k: totals[k] - baseline[k] for k in totals},
                    "instrumented_api_seconds": {"min": min(timings), "median": statistics.median(timings), "max": max(timings)},
                    "limit": "Fixed32 counts are analytic, not new measured forwards or FLOPs; times include instrumentation; no acceleration/quality claim"}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if not args.run.is_absolute() or not args.output.is_absolute() or any(args.output.resolve().is_relative_to(args.run.resolve() / n) for n in ("data", "worker")):
        parser.error("Absolute paths required; output outside sealed data/worker")
    audit, status, actual, error = Audit(args.run), "NOT TESTED", {}, None
    try:
        actual = audit.run()
        status = "PASS"
    except BaseException as exc:
        status = "BLOCKED" if isinstance(exc, (OSError, Incomplete)) else "FAIL"
        error = {"type": type(exc).__name__, "reason": str(exc), "traceback": traceback.format_exc()}
    report = {"Purpose": "Independent original-token, raw-byte, count and scalar-TV audit", "Environment": sys.version,
              "Input": str(args.run), "Expected": "Complete valid32calls16sources; data/custody/decisions verified independently",
              "Actual": {**actual, "checks": audit.checks, "error": error}, "Status": status,
              "utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"Status": status, "checks": len(audit.checks), "error": error}))
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
