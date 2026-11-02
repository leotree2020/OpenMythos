"""Independent MoDA+MoE numerical stream audit and quality aggregation.

Only standard library and NumPy are used. No worker/model module is imported.
Final run-directory verification awaits the separately frozen worker schema.
"""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import platform
import struct
import sys

SHAPE = (64, 32768)
RAW_BYTES = 64 * 32768 * 4
SEEDS = (4101, 4202)
EVAL_SEEDS = (5101, 5202)
DOMAIN_COUNTS = {"wiki": 16, "news": 20}
CONFIGS = (("F", None),) + tuple((c, s) for s in SEEDS for c in ("H", "Esolo", "HE", "EjointHoff"))
TOLERANCE = 1e-10
MAIN_COUNTS = {"model_loads": 1, "calls_started": 783, "calls_completed": 783,
    "identity_calls": 7, "train_steps": 128, "backward_calls": 128,
    "optimizer_steps": 128, "quality_rows": 648, "full_matrix_audits": 648}
RELOAD_COUNTS = {"model_loads": 1, "calls_started": 9, "calls_completed": 9,
    "reload_rows": 9, "full_matrix_audits": 9}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def object_pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, "Duplicate JSON key: " + key)
        result[key] = value
    return result


def loads(raw):
    def invalid(value):
        raise ValueError("Nonfinite JSON constant: " + value)
    return json.loads(raw, object_pairs_hook=object_pairs, parse_constant=invalid)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def validate_targets(targets):
    require(type(targets) is list and len(targets) == 64, "Exactly 64 target IDs")
    require(all(type(v) is int and 0 <= v < 32768 for v in targets), "Integer target IDs in vocabulary")
    return targets


def compute(raw, targets):
    """Reconstruct all scored logits independently in FP64, preserving FP32 input."""
    import numpy as np
    validate_targets(targets)
    require(type(raw) is bytes and len(raw) == RAW_BYTES, "Exactly 8388608 FP32LE matrix bytes")
    matrix = np.frombuffer(raw, dtype="<f4").reshape(SHAPE)
    require(bool(np.isfinite(matrix).all()), "All 2097152 logits finite")
    expanded = matrix.astype(np.float64)
    maximum = expanded.max(axis=1)
    gold = expanded[np.arange(64), np.asarray(targets)]
    shifted = np.log(np.exp(expanded - maximum[:, None]).sum(axis=1))
    nll = (maximum - gold) + shifted
    predictions = np.argmax(matrix, axis=1)
    top1 = expanded[np.arange(64), predictions].copy()
    expanded[np.arange(64), predictions] = -np.inf
    second = np.argmax(expanded, axis=1)
    top2 = expanded[np.arange(64), second].copy()
    columns = {"nll": nll.tolist(), "predictions": predictions.tolist(), "gold": gold.tolist(),
        "max": maximum.tolist(), "shifted_logsumexp": shifted.tolist(), "logsumexp": (maximum + shifted).tolist(),
        "top1": top1.tolist(), "top2": top2.tolist(), "top2_indices": second.tolist(), "margin": (top1 - top2).tolist()}
    chunks = []
    for index, start in enumerate(range(0, RAW_BYTES, 1024**2)):
        part = raw[start:start + 1024**2]
        values = np.frombuffer(part, dtype="<f4").astype(np.float64)
        chunks.append({"index": index, "offset": start, "bytes": len(part), "sha256": sha(part),
            "sum64": float(values.sum()), "sum_squares64": float((values * values).sum()),
            "min64": float(values.min()), "max64": float(values.max())})
    metrics = metrics_from_columns(columns, targets)
    return {"raw": {"bytes": RAW_BYTES, "sha256": sha(raw)}, "shape": list(SHAPE), "dtype": "float32-le",
        "targets_sha256": sha(struct.pack("<64q", *targets)), "finite_components": 64 * 32768,
        "columns": columns, "chunks": chunks, "metrics": metrics}


def metrics_from_columns(columns, targets):
    validate_targets(targets)
    required = {"nll", "predictions", "gold", "max", "shifted_logsumexp", "logsumexp", "top1", "top2", "top2_indices", "margin"}
    require(type(columns) is dict and set(columns) == required, "Complete independent token columns")
    require(all(type(v) is list and len(v) == 64 for v in columns.values()), "64 entries in each token column")
    for key, values in columns.items():
        if key in ("predictions", "top2_indices"):
            require(all(type(v) is int and 0 <= v < 32768 for v in values), "Valid token indices")
        else:
            require(all(type(v) in (int, float) and math.isfinite(v) for v in values), "Finite token columns")
    for i in range(64):
        require(abs(columns["nll"][i] - (columns["max"][i] - columns["gold"][i] + columns["shifted_logsumexp"][i])) <= TOLERANCE, "Stable token NLL identity")
        require(abs(columns["logsumexp"][i] - (columns["max"][i] + columns["shifted_logsumexp"][i])) <= TOLERANCE, "Token logsumexp identity")
        require(columns["predictions"][i] != columns["top2_indices"][i] and columns["top1"][i] == columns["max"][i], "Top-two identities")
        require(columns["margin"][i] >= 0 and abs(columns["margin"][i] - (columns["top1"][i] - columns["top2"][i])) <= TOLERANCE, "Top-two margin")
    total = math.fsum(columns["nll"])
    return {"nll_sum": total, "nll_mean": total / 64,
        "correct": sum(p == t for p, t in zip(columns["predictions"], targets)), "target_count": 64}


def close(actual, expected, message):
    require(type(actual) in (int, float) and math.isfinite(actual) and abs(actual - expected) <= TOLERANCE, message)


def same_tree(actual, expected, message):
    if type(expected) is dict:
        require(type(actual) is dict and set(actual) == set(expected), message + " keys")
        for key, value in expected.items():
            same_tree(actual[key], value, message + "." + key)
    elif type(expected) is list:
        require(type(actual) is list and len(actual) == len(expected), message + " list length")
        for index, (a, b) in enumerate(zip(actual, expected)):
            same_tree(a, b, message + "[%d]" % index)
    elif type(expected) is float:
        close(actual, expected, message)
    else:
        require(type(actual) is type(expected) and actual == expected, message + " exact value")


def row_metrics(row, targets=None):
    targets = validate_targets(row["targets"] if targets is None else targets)
    if "targets_sha256" in row:
        require(row["targets_sha256"] == sha(struct.pack("<64q", *targets)), "Retained row target-vector binding")
    values = row["worker_per_token"]
    nll, predictions = values["nll"], values["predictions"]
    require(type(nll) is list and type(predictions) is list and len(nll) == len(predictions) == 64, "64 retained worker observations")
    require(all(type(v) in (int, float) and math.isfinite(v) and v >= 0 for v in nll), "Finite nonnegative worker token NLL")
    require(all(type(v) is int and 0 <= v < 32768 for v in predictions), "Worker prediction IDs")
    total = math.fsum(nll)
    result = {"nll_sum": total, "nll_mean": total / 64,
        "correct": sum(p == t for p, t in zip(predictions, targets)), "target_count": 64}
    for key in ("nll_sum", "nll_mean"):
        close(row[key], result[key], "Retained row " + key)
    for key in ("correct", "target_count"):
        require(type(row[key]) is int and row[key] == result[key], "Retained row " + key)
    return result


def config_name(config, seed):
    return config if seed is None else config + "_" + str(seed)


def label(delta_nll, delta_accuracy):
    if delta_nll <= -0.01 and delta_accuracy >= -0.01:
        return "IMPROVEMENT"
    if delta_nll >= 0.01 or delta_accuracy < -0.01:
        return "WORSE"
    return "NO_QUALIFIED_IMPROVEMENT"


def aggregate(rows, targets_by_case=None):
    """Complete 648-row quality population only; reload calls never enter here.

    `targets` must be reconstructed from each frozen domain input by the caller,
    not trusted from a public worker report. Final wrapper enforces those pins.
    """
    require(type(rows) is list and len(rows) == 648, "648 unique quality rows; reloads are separate")
    by = {}
    domain_articles = {domain: set() for domain in DOMAIN_COUNTS}
    for row in rows:
        domain, config, seed = row["domain"], row["config"], row["train_seed"]
        require(domain in DOMAIN_COUNTS and (config, seed) in CONFIGS, "Frozen domain/config/seed")
        require(type(row["eval_seed"]) is int and row["eval_seed"] in EVAL_SEEDS, "Frozen h0 seed")
        require(type(row["article_id"]) is str and bool(row["article_id"]), "Article identity")
        require(type(row["logits_sha256"]) is str and len(row["logits_sha256"]) == 64 and all(c in "0123456789abcdef" for c in row["logits_sha256"]), "Matrix SHA256")
        require(all(type(row[k]) is int and row[k] > 0 for k in ("endpoint_wall_ns", "endpoint_cpu_ns")), "Positive endpoint durations")
        key = (domain, config, seed, row["eval_seed"], row["article_id"])
        require(key not in by, "Duplicate quality identity")
        targets = None if targets_by_case is None else targets_by_case[(domain, row["article_id"])]
        by[key] = {**row, **row_metrics(row, targets)}
        domain_articles[domain].add(row["article_id"])
    require(not (domain_articles["wiki"] & domain_articles["news"]), "Domains have distinct source article identities")
    output = {}
    for domain, count in DOMAIN_COUNTS.items():
        articles = sorted(domain_articles[domain])
        require(len(articles) == count, "Exact article count for " + domain)
        expected = {(domain, c, s, h, a) for c, s in CONFIGS for h in EVAL_SEEDS for a in articles}
        require({k for k in by if k[0] == domain} == expected, "Complete paired grid for " + domain)
        means, timing = {}, {}
        denominator = count * 2 * 64
        for config, seed in CONFIGS:
            group = [by[domain, config, seed, h, a] for a in articles for h in EVAL_SEEDS]
            correct = sum(r["correct"] for r in group)
            means[config_name(config, seed)] = {"mean_nll": math.fsum(r["nll_sum"] for r in group) / denominator,
                "correct": correct, "scored_observations": denominator, "accuracy": correct / denominator}
            durations = sorted(r["endpoint_wall_ns"] for r in group)
            n = len(durations)
            timing[config_name(config, seed)] = {"calls": n, "endpoint_total_seconds": sum(durations) / 1e9,
                "endpoint_mean_seconds": sum(durations) / (n * 1e9),
                "endpoint_median_seconds": (durations[n // 2 - 1] + durations[n // 2]) / 2e9,
                "endpoint_p95_seconds": durations[math.ceil(0.95 * n) - 1] / 1e9,
                "process_cpu_total_seconds": sum(r["endpoint_cpu_ns"] for r in group) / 1e9}
        comparisons, screens, secondary, interpretations = {}, {}, {}, {}
        definitions = {"HE_vs_F": (("HE", 1), ("F", -1)),
            "HE_vs_H": (("HE", 1), ("H", -1)),
            "HE_vs_Esolo": (("HE", 1), ("Esolo", -1)),
            "H_vs_F": (("H", 1), ("F", -1)),
            "Esolo_vs_F": (("Esolo", 1), ("F", -1)),
            "joint_E_inference_interaction": (("HE", 1), ("H", -1), ("EjointHoff", -1), ("F", 1))}
        for title, terms in definitions.items():
            seed_labels = {}
            for seed in SEEDS:
                per_article = []
                for article in articles:
                    nll_terms, correct_terms = [], []
                    for h0 in EVAL_SEEDS:
                        for config, coefficient in terms:
                            row = by[domain, config, None if config == "F" else seed, h0, article]
                            nll_terms.append(coefficient * row["nll_sum"])
                            correct_terms.append(coefficient * row["correct"])
                    per_article.append({"article_id": article, "delta_nll": math.fsum(nll_terms) / 128,
                        "delta_correct": sum(correct_terms)})
                dn = math.fsum(r["delta_nll"] for r in per_article) / count
                da = sum(r["delta_correct"] for r in per_article) / denominator
                interaction = title == "joint_E_inference_interaction"
                seed_labels[str(seed)] = "DESCRIPTIVE_NONADDITIVITY" if interaction else label(dn, da)
                comparisons[title + "_" + str(seed)] = {"delta_nll": dn, "delta_accuracy": da,
                    "per_article": per_article, "articles_nll_negative": sum(r["delta_nll"] < 0 for r in per_article),
                    "worst_article_delta_nll": max(r["delta_nll"] for r in per_article),
                    "screen": "NOT ASSESSED" if interaction else dn <= -0.01 and da >= -0.01, "interpretation": seed_labels[str(seed)],
                    "kind": "FIXED_JOINT_E_INFERENCE_NONADDITIVITY" if title == "joint_E_inference_interaction" else "PAIRED_CONFIGURATION_DIFFERENCE"}
            if title != "joint_E_inference_interaction":
                destination = screens if title in ("HE_vs_F", "HE_vs_H", "HE_vs_Esolo") else secondary
                destination[title] = "PASS" if all(comparisons[title + "_" + str(s)]["screen"] for s in SEEDS) else "FAIL"
            interpretations[title] = {"per_seed": seed_labels,
                "combined": seed_labels["4101"] if seed_labels["4101"] == seed_labels["4202"] else "MIXED"}
        ratios = {}
        for seed in SEEDS:
            for reference in ("F", "H_" + str(seed), "Esolo_" + str(seed)):
                ratios["HE_" + str(seed) + "_vs_" + reference] = timing["HE_" + str(seed)]["endpoint_total_seconds"] / timing[reference]["endpoint_total_seconds"]
        output[domain] = {"articles": count, "quality_rows": count * 2 * 9, "means": means,
            "comparisons": comparisons, "scientific_screens": screens, "secondary_screens": secondary, "result_interpretations": interpretations,
            "timing": {"models": timing, "ratios": ratios, "screen": "NOT ASSESSED"}}
    return {"domains": output, "total_quality_rows": 648, "reload_rows_added_to_quality": 0,
        "interaction_scope": "Fixed joint-trained E inference nonadditivity; not a training-causality or statistical confirmation claim",
        "domain_pooling": "NONE; wiki and news are development/regression sets"}


def file_pin(path):
    raw = Path(path).read_bytes()
    return {"bytes": len(raw), "sha256": sha(raw)}


def read_json(path, limit=64 * 1024**2):
    path = Path(path)
    require(path.is_absolute() and path.is_file() and not path.is_symlink(), "Absolute regular evidence file: " + str(path))
    require(path.stat().st_size <= limit, "Physical JSON read bound")
    if path.name.endswith(".gz"):
        with gzip.open(path, "rb") as stream:
            raw = stream.read(limit + 1)
    else:
        raw = path.read_bytes()
    require(len(raw) <= limit, "Expanded JSON read bound")
    return loads(raw)


def audit_final(run_dir, spec_path, development_only=False):
    """Validate retained live-audit receipts; never claim raw logits reconstruction."""
    run_dir, spec_path = Path(run_dir), Path(spec_path)
    require(run_dir.is_absolute() and spec_path.is_absolute(), "Absolute final audit paths")
    spec = read_json(spec_path)
    completion_pins = {}
    for directory, mode, expected in (("worker", "main", MAIN_COUNTS), ("reload", "reload", RELOAD_COUNTS)):
        completion_path = run_dir / directory / "public/completion.json"
        completion = read_json(completion_path)
        require(completion["Status"] == "PASS" and completion["preservation"] == "PASS", "Main/reload completion and preservation PASS")
        same_tree(completion["Actual"], expected, "Recorded " + mode + " exact counters")
        same_tree(completion["Expected"], expected, "Declared " + mode + " exact counters")
        require(completion["Input"]["freeze"] == spec["freeze_commit"] and completion["Input"]["mode"] == mode, "Main/reload frozen execution binding")
        completion_pins[mode] = file_pin(completion_path)
    targets_by_case, samples = {}, {}
    source_pins = {}
    for domain, count in DOMAIN_COUNTS.items():
        reference = spec[domain + "_data"]
        require(type(reference) is dict and set(reference) == {"path", "pin"}, "Exact frozen data reference")
        path = Path(reference["path"])
        data = read_json(path)
        observed = file_pin(path)
        require(observed == reference["pin"], "Frozen " + domain + " source pin")
        source_pins[str(path)] = observed
        require(data["context_tokens"] == 128 and data["scored_positions"] == [64, 128]
                and data["eval_seeds"] == list(EVAL_SEEDS), "Frozen domain score layout")
        require(type(data["eval"]) is list and len(data["eval"]) == count, "Frozen domain article count")
        for index, sample in enumerate(data["eval"]):
            key = domain, sample["id"]
            require(key not in samples, "Unique input article identity")
            require(type(sample["tokens"]) is list and len(sample["tokens"]) == 129
                    and all(type(v) is int and 0 <= v < 32768 for v in sample["tokens"]), "Frozen 129-token window")
            samples[key] = index
            targets_by_case[key] = sample["tokens"][65:129]
    public = run_dir / "worker/public"
    rows_path, results_path = public / "evaluation.json.gz", public / "results.json"
    rows = read_json(rows_path)["rows"]
    require(type(rows) is list and len(rows) == 648, "All 648 audit rows")
    audited_rows, receipt_pins, paired, balance = [], {}, {}, {}
    for number, row in enumerate(rows):
        case, slot = divmod(number, 9)
        domain = "wiki" if case < 32 else "news"
        local_case = case if domain == "wiki" else case - 32
        config_index = (case + slot) % 9
        config, train_seed = CONFIGS[config_index]
        planned = {"row_index": number, "case_index": case, "slot": slot, "domain": domain,
            "article_index": local_case // 2, "eval_seed": EVAL_SEEDS[local_case % 2], "config": config, "train_seed": train_seed}
        require(all(type(row[k]) is type(v) and row[k] == v for k, v in planned.items()), "Frozen 648-row cyclic schedule")
        key = row["domain"], row["article_id"]
        targets = targets_by_case[key]
        require(row["article_index"] == samples[key], "Independent domain article index")
        observer = row["observer"]
        state = {k: observer[k] for k in ("h0_sha256", "rng_before_sha256", "rng_after_sha256", "seed")}
        require(state["seed"] == row["eval_seed"] and all(type(state[k]) is str and len(state[k]) == 64
                and all(c in "0123456789abcdef" for c in state[k]) for k in ("h0_sha256", "rng_before_sha256", "rng_after_sha256")), "Actual initial-state seed/digests")
        pairing = domain, row["article_id"], row["eval_seed"]
        paired.setdefault(pairing, state)
        require(state == paired[pairing], "All nine configurations share actual h0/RNG")
        balance[config_index, slot] = balance.get((config_index, slot), 0) + 1
        require("targets" not in row, "No raw target vector in public quality rows")
        digest = sha(struct.pack("<64q", *targets))
        require(row["targets_sha256"] == digest, "Independent target slice/hash")
        relative = "audits/row_%03d.json.gz" % number
        require(row["audit_receipt"] == relative, "Exact confined row audit path")
        receipt_path = public / relative
        require(receipt_path.resolve().is_relative_to(public.resolve()), "Confined audit receipt")
        receipt = read_json(receipt_path)
        require(receipt["Status"] == "PASS", "Independent stream receipt PASS")
        actual = receipt["Actual"]
        require(receipt["Input"]["targets_sha256"] == actual["targets_sha256"] == digest, "Stream target digest binding")
        environment = receipt["Environment"]
        require(environment["model_imports"] == [], "Independent stream imports")
        if not development_only:
            require(environment["development_only"] is False and environment["python"] == "3.12.3"
                    and environment["numpy"] == "1.26.4", "Formal frozen stream environment")
        require(actual["raw"] == {"bytes": RAW_BYTES, "sha256": row["logits_sha256"]}
                and actual["shape"] == list(SHAPE) and actual["dtype"] == "float32-le"
                and actual["finite_components"] == 2097152, "Complete finite raw-matrix receipt binding")
        metrics = metrics_from_columns(actual["columns"], targets)
        worker = row_metrics(row, targets)
        for name in ("nll_sum", "nll_mean"):
            close(actual["metrics"][name], metrics[name], "Independent receipt token aggregate")
            close(worker[name], metrics[name], "Independent worker token aggregate")
        for name in ("correct", "target_count"):
            require(actual["metrics"][name] == worker[name] == metrics[name], "Independent integer score counts")
        require(row["worker_per_token"]["predictions"] == actual["columns"]["predictions"], "Independent exact token argmax")
        require(all(abs(a - b) <= TOLERANCE for a, b in zip(row["worker_per_token"]["nll"], actual["columns"]["nll"])), "Independent per-token NLL")
        chunks = actual["chunks"]
        require(type(chunks) is list and len(chunks) == 8, "Eight complete chunk descriptors")
        for index, chunk in enumerate(chunks):
            require(chunk["index"] == index and chunk["offset"] == index * 1048576 and chunk["bytes"] == 1048576,
                    "Chunk index/offset/size")
            require(type(chunk["sha256"]) is str and len(chunk["sha256"]) == 64 and all(c in "0123456789abcdef" for c in chunk["sha256"]), "Chunk SHA256")
            require(all(type(chunk[k]) in (int, float) and math.isfinite(chunk[k]) for k in ("sum64", "sum_squares64", "min64", "max64")), "Finite chunk descriptors")
        audited_rows.append({**row, **metrics, "worker_per_token": {
            "nll": actual["columns"]["nll"], "predictions": actual["columns"]["predictions"]}})
        receipt_pins[relative] = file_pin(receipt_path)
    computed = aggregate(audited_rows, targets_by_case)
    require(len(paired) == 72 and len(balance) == 81 and set(balance.values()) == {8}, "72 paired cases and balanced nine-slot schedule")
    saved = read_json(results_path)
    require(set(saved["domains"]) == set(DOMAIN_COUNTS), "Both independently aggregated domains")
    for domain, values in computed["domains"].items():
        expected = saved["domains"][domain]
        require(set(expected["means"]) == set(values["means"]), "Exact nine worker means")
        for name, mean in values["means"].items():
            require(set(expected["means"][name]) == set(mean), "Complete worker mean fields")
            for key, value in mean.items():
                if type(value) is int:
                    require(type(expected["means"][name][key]) is int and expected["means"][name][key] == value, "Exact pooled counts")
                else:
                    close(expected["means"][name][key], value, "Independent pooled mean")
        primary = {title + "_" + str(seed) for title in ("HE_vs_F", "HE_vs_H", "HE_vs_Esolo") for seed in SEEDS}
        require(set(expected["primary_comparisons"]) == primary, "Exact six primary seed contrasts")
        for key in primary:
            observed, reference = expected["primary_comparisons"][key], values["comparisons"][key]
            require(set(observed) == {"delta_nll", "delta_accuracy", "screen"}, "Primary worker fields")
            for name in ("delta_nll", "delta_accuracy"):
                close(observed[name], reference[name], "Independent primary delta")
            require(type(observed["screen"]) is bool and observed["screen"] == reference["screen"], "Independent primary boolean screen")
        require(expected["scientific_screens"] == values["scientific_screens"], "Independent both-seed primary screens")
    # Reloads are separate evidence; do not append them to audited_rows/aggregate.
    reload_public = run_dir / "reload/public"
    reload_path = reload_public / "reload.json"
    reloaded = read_json(reload_path)
    require(reloaded["Status"] == "PASS" and reloaded["quality_rows_added"] == 0 and reloaded["new_interpreter"] is True,
            "Reload success without extra quality observations")
    reload_rows = reloaded["rows"]
    require(type(reload_rows) is list and len(reload_rows) == 9, "Exactly nine reload configurations")
    reload_pins = {}
    final_receipt = None
    for index, (reload_row, (config, seed)) in enumerate(zip(reload_rows, CONFIGS)):
        require((reload_row["config"], reload_row["train_seed"], reload_row["eval_seed"]) == (config, seed, 5101), "Frozen reload configuration order")
        references = [r for r in rows if r["domain"] == "news" and r["article_index"] == 0 and r["eval_seed"] == 5101
            and (r["config"], r["train_seed"]) == (config, seed)]
        require(len(references) == 1, "One main reference per reload")
        reference = references[0]
        require(reload_row["article_id"] == reference["article_id"] and reload_row["reference_row_index"] == reference["row_index"]
            and reload_row["logits_sha256"] == reference["logits_sha256"] and reload_row["observer"] == reference["observer"],
            "New-process exact full-matrix digest and initial-state observer")
        targets = targets_by_case["news", reference["article_id"]]
        reload_metrics = row_metrics(reload_row, targets)
        for name in ("nll_sum", "nll_mean"):
            close(reload_metrics[name], reference[name], "Reload/reference NLL")
        for name in ("correct", "target_count"):
            require(reload_metrics[name] == reference[name], "Reload/reference exact counts")
        audit_path = reload_public / ("audits/reload_%d.json.gz" % index)
        audit = read_json(audit_path)
        require(audit["Status"] == "PASS", "Reload complete live stream audit PASS")
        environment = audit["Environment"]
        require(environment["model_imports"] == [], "Reload independent stream imports")
        if not development_only:
            require(environment["development_only"] is False and environment["python"] == "3.12.3"
                and environment["numpy"] == "1.26.4", "Reload frozen NumPy environment")
        actual = audit["Actual"]
        digest = sha(struct.pack("<64q", *targets))
        require(audit["Input"]["targets_sha256"] == actual["targets_sha256"] == digest, "Reload target binding")
        require(actual["raw"] == {"bytes": RAW_BYTES, "sha256": reload_row["logits_sha256"]}
            and actual["finite_components"] == 2097152 and actual["shape"] == list(SHAPE) and actual["dtype"] == "float32-le", "Reload complete matrix receipt")
        independent_metrics = metrics_from_columns(actual["columns"], targets)
        same_tree(actual["metrics"], independent_metrics, "Reload independent metrics")
        same_tree(reload_metrics, independent_metrics, "Reload worker metrics")
        same_tree(reload_row["worker_per_token"], {"nll": actual["columns"]["nll"], "predictions": actual["columns"]["predictions"]}, "Reload independent token columns")
        require(len(actual["chunks"]) == 8, "Reload complete chunk descriptors")
        for chunk_index, chunk in enumerate(actual["chunks"]):
            require(chunk["index"] == chunk_index and chunk["offset"] == chunk_index * 1048576 and chunk["bytes"] == 1048576,
                "Reload chunk index/offset/size")
            require(type(chunk["sha256"]) is str and len(chunk["sha256"]) == 64
                and all(c in "0123456789abcdef" for c in chunk["sha256"]), "Reload chunk digest")
            require(all(type(chunk[k]) in (int, float) and math.isfinite(chunk[k]) for k in ("sum64", "sum_squares64", "min64", "max64")), "Reload finite chunk descriptors")
        reload_pins[str(index)] = file_pin(audit_path)
        final_receipt = actual
    sentinel_path = reload_public / "sentinel.json"
    sentinel = read_json(sentinel_path)
    final_row = reload_rows[-1]
    require(sentinel["identity"] == {"phase": "reload", "config": "EjointHoff", "train_seed": 4202,
            "eval_seed": 5101, "article_id": final_row["article_id"]} and sentinel["audit"] == "audits/reload_8.json.gz", "Predeclared final sentinel identity")
    raw_path = run_dir / "reload/private/final_sentinel.bin"
    require(raw_path.is_file() and not raw_path.is_symlink() and raw_path.stat().st_size == RAW_BYTES, "Exactly one complete retained sentinel")
    raw = raw_path.read_bytes()
    require({"bytes": len(raw), "sha256": sha(raw)} == sentinel["raw"] == final_receipt["raw"], "Retained raw sentinel exact bytes")
    stored_raws = [p for directory in (run_dir / "worker/private", run_dir / "reload/private") for p in directory.rglob("*.bin") if p.is_file()]
    require(stored_raws == [raw_path], "Only the predeclared final raw matrix retained")
    recomputed_raw = compute(raw, targets_by_case["news", final_row["article_id"]])
    same_tree(recomputed_raw, final_receipt, "Retrospective full final-sentinel reconstruction")
    require(all(file_pin(path) == expected for path, expected in source_pins.items()), "Input bytes unchanged through final audit")
    return {**computed, "independent_stream_rows": len(audited_rows), "paired_actual_states": len(paired), "balanced_config_slots": len(balance), "input_pins": source_pins,
        "spec_pin": file_pin(spec_path), "evaluation_pin": file_pin(rows_path), "results_pin": file_pin(results_path),
        "receipt_pins": receipt_pins, "model_calls": 0, "completion_pins": completion_pins,
        "reload": {"exact_rows": 9, "new_quality_rows": 0, "reload_pin": file_pin(reload_path), "audit_pins": reload_pins,
            "sentinel_pin": file_pin(sentinel_path), "raw": sentinel["raw"], "retrospective_full_matrices_recomputed": 1},
        "coverage_limit": "648 unique quality matrices were live-audited; their raw bytes are not reconstructed here. Nine separate reloads exactly match main hashes/observers; the one last reload matrix is independently reread in full. Completion counters are checked records, not a substitute for separately operator-verified training/identity trajectories and old baseline bridges."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--stream", action="store_true")
    mode.add_argument("--final", action="store_true")
    target_options = parser.add_mutually_exclusive_group()
    target_options.add_argument("--targets", type=Path)
    target_options.add_argument("--targets-json")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--spec", type=Path)
    parser.add_argument("--development-only", action="store_true")
    args = parser.parse_args()
    report = {"Purpose": "Independent complete MoDA+MoE scored-matrix audit", "Environment": {}, "Input": {},
        "Expected": {"raw_bytes": RAW_BYTES, "shape": list(SHAPE), "model_imports": []}, "Actual": {}, "Status": "NOT TESTED"}
    try:
        require(sys.flags.isolated and sys.dont_write_bytecode, "Isolated Python -I -B required")
        import numpy as np
        report["Environment"] = {"python": platform.python_version(), "numpy": np.__version__, "executable": sys.executable,
            "development_only": args.development_only, "model_imports": []}
        if not args.development_only:
            require(platform.system() == "Linux" and platform.python_version() == "3.12.3" and np.__version__ == "1.26.4", "Frozen formal NumPy/Python environment")
        if args.final:
            require(args.run_dir is not None and args.spec is not None and args.targets is None and args.targets_json is None, "Final run-dir/spec interface")
            report["Purpose"] = "Independent retained-evidence MoDA+MoE final quality audit"
            report["Expected"] = {"quality_rows": 648, "paired_cases": 72, "new_model_calls": 0}
            report["Input"] = {"run_dir": str(args.run_dir), "spec": str(args.spec)}
            report["Actual"] = audit_final(args.run_dir, args.spec, args.development_only)
            require(not ({"torch", "parcae_lm", "receval", "transformers"} & {n.split(".")[0] for n in sys.modules}), "No model/worker imports")
            report["Status"] = "PASS"
            print(json.dumps(report, sort_keys=True, allow_nan=False))
            return 0
        require((args.targets is not None or args.targets_json is not None) and args.run_dir is None and args.spec is None, "Stream requires private targets only")
        if args.targets is not None:
            require(args.targets.is_absolute() and args.targets.is_file() and not args.targets.is_symlink(), "Absolute regular private targets file")
            require(args.targets.stat().st_size <= 8192, "Small target JSON bound")
            target_raw = args.targets.read_bytes()
        else:
            target_raw = args.targets_json.encode("utf-8")
            require(len(target_raw) <= 8192, "Small target JSON bound")
        targets = validate_targets(loads(target_raw))
        report["Input"] = {"targets_json_pin": {"bytes": len(target_raw), "sha256": sha(target_raw)},
            "targets_sha256": sha(struct.pack("<64q", *targets))}
        raw = sys.stdin.buffer.read(RAW_BYTES + 1)
        report["Actual"] = compute(raw, targets)
        require(not ({"torch", "parcae_lm", "receval", "transformers"} & {n.split(".")[0] for n in sys.modules}), "No model/worker imports")
        report["Status"] = "PASS"
    except BaseException as exc:
        report["Status"] = "BLOCKED" if isinstance(exc, (OSError, MemoryError, KeyboardInterrupt, NotImplementedError)) else "FAIL"
        report["error"] = {"type": type(exc).__name__, "message": str(exc)}
    print(json.dumps(report, sort_keys=True, allow_nan=False))
    return 0 if report["Status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
