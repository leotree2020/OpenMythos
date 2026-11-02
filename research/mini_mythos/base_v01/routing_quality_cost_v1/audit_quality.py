"""Independent no-Torch audit of true next-token quality and complete API time."""
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

INPUT_SHA = "ae5f8ad5fd53d25afaf29487a650dc0300528b0926c9883652475c4ca7db127f"
PINS = {
    "corpus": "3ee89cd6a2ab912afd5d01e98867b46a67d9ec7a9eca0910e5e4c3cdd4cc1925",
    "tokenizer": "e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77",
    "ledger": "f5f7858b989451671e4c7ed27192642dec3f9b2a1ccd214cc9e3cc30bcebb5d3",
    "partition": "95a217a815596c928a0b721837b567a08ed8c6f667839fdf6d4311113c253aa4",
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
    data = Path(path).read_bytes()
    return {"bytes": len(data), "sha256": sha(data)}


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def safe(root, name):
    p = Path(name)
    result = (root / p).resolve()
    if p.is_absolute() or result == root.resolve() or not result.is_relative_to(root.resolve()):
        raise Reject("Artifact path escape")
    return result


def values(data):
    if not data or len(data) % 4:
        raise Reject("Invalid FP32 extent")
    result = [v[0] for v in struct.iter_unpack("<f", data)]
    if not all(math.isfinite(v) for v in result):
        raise Reject("Nonfinite saved FP32")
    return result


def score(logits, target):
    if not logits or not all(math.isfinite(x) for x in logits) or type(target) is not int or not 0 <= target < len(logits):
        raise Reject("Invalid logits/target")
    peak = max(logits)
    nll = (peak - logits[target]) + math.log(math.fsum(math.exp(x - peak) for x in logits))
    top1 = max(range(len(logits)), key=lambda i: logits[i])
    if not math.isfinite(nll) or nll < -1e-12:
        raise Reject("Invalid NLL")
    return {"nll": nll, "top1": top1, "correct": top1 == target}


def tv(left, right):
    if len(left) != len(right) or not left:
        raise Reject("TV extent mismatch")
    def probs(x):
        peak = max(x)
        e = [math.exp(v - peak) for v in x]
        total = math.fsum(e)
        return [v / total for v in e]
    return math.fsum(abs(x-y) for x, y in zip(probs(left), probs(right))) / 2


def quality_summary(cases):
    if len(cases) != 32 or [(x["article_index"], x["seed"]) for x in cases] != [(i, s) for i in range(16) for s in (3101, 3202)]:
        raise Reject("Exact quality case coverage/order required")
    per_seed = {}
    for seed in (3101, 3202):
        group = [x for x in cases if x["seed"] == seed]
        delta = math.fsum(x["delta_nll"] for x in group) / 16
        adaptive_correct = sum(x["adaptive"]["correct"] for x in group)
        fixed_correct = sum(x["fixed32"]["correct"] for x in group)
        per_seed[str(seed)] = {"mean_delta_nll": delta, "adaptive_correct": adaptive_correct,
                               "fixed32_correct": fixed_correct, "cases": 16,
                               "screen": delta <= .01 and adaptive_correct >= fixed_correct}
    max_delta = max(x["delta_nll"] for x in cases)
    quality_pass = all(x["screen"] for x in per_seed.values()) and max_delta <= .1
    per_article = [{"article_index": i, "mean_delta_nll": math.fsum(x["delta_nll"] for x in cases[2*i:2*i+2])/2,
                    "adaptive_depths": [x["adaptive_depth"] for x in cases[2*i:2*i+2]]} for i in range(16)]
    return {"cases": cases, "per_seed": per_seed, "per_article": per_article,
            "mean_delta_nll": math.fsum(x["mean_delta_nll"] for x in per_article)/16,
            "mean_nll": {arm: math.fsum(x[arm]["nll"] for x in cases)/32 for arm in ("adaptive", "fixed32")},
            "top1_correct": {arm: sum(x[arm]["correct"] for x in cases) for arm in ("adaptive", "fixed32")},
            "prediction_disagreements": sum(x["adaptive"]["top1"] != x["fixed32"]["top1"] for x in cases),
            "max_case_delta_nll": max_delta, "min_case_delta_nll": min(x["delta_nll"] for x in cases),
            "early_exit_cases": [x for x in cases if x["adaptive_depth"] == 16],
            "screen": {"Status": "PASS" if quality_pass else "FAIL",
                       "Expected": "Both evaluation-seed mean delta NLL<=0.01 and correct count not lower; every case delta NLL<=0.1",
                       "meaning": "Exploratory engineering margin only; not statistical noninferiority or language-quality acceptance"}}


def expected_timing_order():
    order = [("warmup", None, 0, 0, "fixed32"), ("warmup", None, 0, 1, "adaptive")]
    for round_index in (0, 1):
        for case in range(32):
            arms = ("adaptive", "fixed32") if (case+round_index)%2 == 0 else ("fixed32", "adaptive")
            order.extend(("timed", round_index, case, i, arm) for i, arm in enumerate(arms))
    return order


def timing_summary(rows):
    actual_order = [(x["phase"], x["round"], x["case_index"], x["position"], x["arm"]) for x in rows]
    if actual_order != expected_timing_order() or any(not math.isfinite(x[k]) or x[k] <= 0 for x in rows for k in ("elapsed_seconds", "cpu_seconds")):
        raise Reject("Timing coverage/order/positive finite elapsed")
    rounds, pairs = [], []
    for round_index in (0, 1):
        group = [x for x in rows if x["phase"] == "timed" and x["round"] == round_index]
        sums = {arm: math.fsum(x["elapsed_seconds"] for x in group if x["arm"] == arm) for arm in ("adaptive", "fixed32")}
        cpu_sums = {arm: math.fsum(x["cpu_seconds"] for x in group if x["arm"] == arm) for arm in ("adaptive", "fixed32")}
        rounds.append({"round": round_index, "seconds": sums, "process_cpu_seconds": cpu_sums,
                       "adaptive_over_fixed32": sums["adaptive"]/sums["fixed32"]})
        for case in range(32):
            pair = [x for x in group if x["case_index"] == case]
            elapsed = {x["arm"]: x["elapsed_seconds"] for x in pair}
            pairs.append({"round": round_index, "case_index": case, "first_arm": pair[0]["arm"],
                          "seconds": elapsed, "adaptive_over_fixed32": elapsed["adaptive"]/elapsed["fixed32"]})
    summed = {arm: math.fsum(x["seconds"][arm] for x in rounds) for arm in ("adaptive", "fixed32")}
    cpu_summed = {arm: math.fsum(x["process_cpu_seconds"][arm] for x in rounds) for arm in ("adaptive", "fixed32")}
    descriptive = {}
    for arm in ("adaptive", "fixed32"):
        seconds = [x["elapsed_seconds"] for x in rows if x["phase"] == "timed" and x["arm"] == arm]
        descriptive[arm] = {"count": len(seconds), "min": min(seconds), "median": statistics.median(seconds), "max": max(seconds)}
    order_groups = {}
    for first in ("adaptive", "fixed32"):
        group = [x for x in pairs if x["first_arm"] == first]
        elapsed = {arm: math.fsum(x["seconds"][arm] for x in group) for arm in ("adaptive", "fixed32")}
        order_groups[first+"_first"] = {"pair_count": len(group), "seconds": elapsed,
                                         "adaptive_over_fixed32": elapsed["adaptive"]/elapsed["fixed32"]}
    cost_pass = all(x["adaptive_over_fixed32"] <= .95 for x in rounds)
    return {"warmup_calls": 2, "timed_calls": 128, "rounds": rounds, "pairs": pairs,
            "aggregate_seconds": summed, "aggregate_process_cpu_seconds": cpu_summed,
            "per_arm_seconds": descriptive, "order_groups": order_groups,
            "adaptive_over_fixed32": summed["adaptive"]/summed["fixed32"],
            "median_pair_ratio": statistics.median(x["adaptive_over_fixed32"] for x in pairs),
            "screen": {"Status": "PASS" if cost_pass else "FAIL", "Expected": "Adaptive/fixed32 aggregate elapsed<=0.95 in both rounds"},
            "scope": "Entire unchanged public CPU API including guards, hashing, readouts and policy; caller RNG setup, model loading, tokenization, external observer hooks and evidence IO excluded. No server or generation benchmark; two rounds descriptive, no confidence interval."}


class Audit:
    def __init__(self, root):
        self.root = root.resolve()
        self.worker = self.root / "worker"
        self.checks, self.raw_seen, self.finite_components = [], set(), 0

    def check(self, purpose, okay, actual=None, expected=True):
        self.checks.append({"Purpose": purpose, "Environment": "Pinned data-only Python; scalar arithmetic, no Torch/model",
                           "Input": str(self.root), "Expected": expected, "Actual": actual, "Status": "PASS" if okay else "FAIL"})
        if not okay:
            raise Reject(purpose)

    def raw(self, meta, shape, dtype="torch.float32"):
        data = safe(self.worker, meta["path"]).read_bytes()
        self.check("raw extent/type/hash " + meta["path"], meta["shape"] == shape and meta["dtype"] == dtype
                   and meta["byteorder"] == "little" and len(data) == meta["bytes"] == math.prod(shape)*(4 if dtype == "torch.float32" else 1)
                   and sha(data) == meta["sha256"])
        if dtype == "torch.float32" and meta["path"] not in self.raw_seen:
            self.finite_components += len(values(data))
            self.raw_seen.add(meta["path"])
        return data

    def audit_data(self):
        data = self.root / "data"
        completion = read(data / "public/completion.json")
        self.check("label data complete", completion["Status"] == "PASS" and completion["Actual"]["sample_count"] == 16
                   and completion["Actual"]["case_count"] == 32 and completion["error"] is None
                   and completion["preservation"]["Status"] == "PASS" and completion["formal_model_calls"] == 0)
        self.check("data artifact exact set", set(completion["artifacts"]) == {"private/inputs.json", "private/labels.json", "public/targets.json"})
        for name, expected in completion["artifacts"].items():
            self.check("data artifact hash " + name, info(safe(data, name)) == expected)
        checks = [json.loads(x) for x in (data / "public/checks.jsonl").read_text().splitlines()]
        self.check("data full check journal", checks == completion["checks"] and bool(checks) and all(x["Status"] == "PASS" for x in checks))
        spec = read(data / "public/spec.json")
        self.check("data spec identity", spec == completion["Input"])
        previous = Path(spec["previous_data"])
        old_spec = read(previous / "public/spec.json")
        self.check("exact unchanged worker input", info(data / "private/inputs.json") == info(previous / "private/inputs.json") == {"bytes": 58091, "sha256": INPUT_SHA})
        for path, expected in read(data / "public/sources_before.json").items():
            self.check("protected data bytes " + path, info(path) == expected)
        for key, digest in PINS.items():
            self.check("original source pin " + key, Path(old_spec[key]).is_absolute() and info(old_spec[key])["sha256"] == digest)
        self.check("audit interpreter", sys.executable == "/workspaces/mythos-depth-data-cpu312/bin/python" and sys.version_info[:3] == (3,12,3))
        import pyarrow
        import pyarrow.parquet as parquet
        import numpy
        import tokenizers
        self.check("audit dependency versions", (pyarrow.__version__, numpy.__version__, tokenizers.__version__) == ("19.0.1", "1.26.4", "0.23.2"))
        rows = parquet.read_table(old_spec["corpus"], columns=["text"]).column("text").to_pylist()
        partition, ledger = read(old_spec["partition"]), read(old_spec["ledger"])
        self.check("independent whole corpus identity", len(rows) == 4358 and sha(canonical(rows)) == partition["rows_sha256"] == ledger["rows_sha256"]
                   and partition["all_row_sha256"] == [sha(x.encode()) for x in rows])
        boundaries = sorted(x["row"] for x in ledger["decisions"] if x["decision"] == "ACCEPT_TITLE")
        self.check("independent reviewed boundaries", boundaries == ledger["accepted_heading_rows"] and len(set(boundaries)) == 60)
        inputs, labels = read(data / "private/inputs.json"), read(data / "private/labels.json")
        self.check("input/label exact coverage", inputs["context_tokens"] == labels["context_tokens"] == labels["target_offset"] == 128
                   and inputs["seeds"] == labels["seeds"] == [3101,3202] and len(inputs["samples"]) == len(labels["labels"]) == 16
                   and labels["prior_inputs_sha256"] == INPUT_SHA)
        tokenizer = tokenizers.Tokenizer.from_file(old_spec["tokenizer"])
        articles = {x["source_article_key"]: x for x in partition["articles"]}
        for index, (sample, label) in enumerate(zip(inputs["samples"], labels["labels"])):
            article = articles[sample["source_article_key"]]
            start = sample["heading_row"]
            later = [h for h in boundaries if h > start]
            stop = min(later) if later else len(rows)
            body, title = "".join(rows[start+1:stop]), rows[start].strip()
            key = sha(canonical({"corpus_sha256": PINS["corpus"], "heading_row": start, "title": title}))
            self.check("independent body reconstruction " + str(index), start in boundaries and sample["index"] == index
                       and sample["body_rows"] == article["body_rows"] == list(range(start+1,stop))
                       and sha(body.encode()) == sample["text_sha256"] == article["text_sha256"]
                       and key == sample["source_article_key"] == article["source_article_key"]
                       and sha((title+"\n"+body).encode()) == sample["article_id"] == article["article_id"])
            tokens = tokenizer.encode(body, add_special_tokens=False).ids
            self.check("independent full body tokenization " + str(index), len(tokens) == article["full_token_count"] == sample["full_token_count"]
                       and len(tokens) >= 257 and all(type(x) is int and 0 <= x < 32768 for x in tokens)
                       and tokens[:128] == sample["tokens"] and sample["input_ids_sha256"] == sha(canonical(tokens[:128]))
                       and sample["raw_input_sha256"] == sha(struct.pack("<128q", *tokens[:128])))
            expected = {"article_index": index, "source_article_key": key, "article_id": sample["article_id"],
                        "input_ids_sha256": sample["input_ids_sha256"], "target_offset": 128, "target_token": tokens[128],
                        "target_raw_sha256": sha(struct.pack("<q", tokens[128])), "body_text_sha256": article["text_sha256"], "full_token_count": len(tokens)}
            self.check("independent actual129th label " + str(index), label == expected)
        public = read(data / "public/targets.json")
        self.check("public labels metadata binding", public["Actual"] == [{k:v for k,v in x.items() if k != "target_token"} for x in labels["labels"]]
                   and public["labels_sha256"] == info(data / "private/labels.json")["sha256"] and public["inputs_sha256"] == INPUT_SHA
                   and public["worker_receives_labels"] is False and public["Status"] == "PASS")
        return inputs["samples"], labels["labels"]

    def audit_seal(self):
        w = self.worker
        completion = read(w / "public/completion.json")
        c = completion["Actual"]
        self.check("complete194 calls", completion["Status"] == "PASS" and completion["complete_coverage"] is True
                   and c["calls_started"] == c["calls_completed"] == 64 and c["groups_completed"] == 16
                   and c["warmup_calls_started"] == c["warmup_calls_completed"] == 2
                   and c["timed_calls_started"] == c["timed_calls_completed"] == 128
                   and c["total_model_calls_started"] == c["total_model_calls_completed"] == 194
                   and c["loader_attempts"] == c["loader_returns"] == 1 and c["error"] is None and not c["save_errors"]
                   and c["preservation"] == "PASS")
        seal = read(w / "FULL_MANIFEST.json")
        excluded = {"FULL_MANIFEST.json", "public/GIT_BUNDLE_MANIFEST.json"}
        actual = {str(p.relative_to(w)).replace("\\", "/") for p in w.rglob("*") if p.is_file()}
        self.check("complete worker artifact set", set(seal["excluded"]) == excluded and set(seal["entries"]) == actual-excluded)
        for name, expected in seal["entries"].items():
            self.check("worker artifact hash " + name, info(safe(w, name)) == expected)
        self.check("public subset manifest", read(w / "public/GIT_BUNDLE_MANIFEST.json")["entries"] == {k:v for k,v in seal["entries"].items() if k.startswith("public/")})
        checks = [json.loads(x) for x in (w / "public/checks.jsonl").read_text().splitlines()]
        self.check("worker check journal", checks and all(x["Status"] == "PASS" for x in checks) and c["checks"] == {"PASS":len(checks),"FAIL":0,"BLOCKED":0})
        before = read(w / "public/protected_before.json")
        self.check("worker preserved files/git", before["files"] == read(w / "public/protected_after.json")["files"]
                   and before["git"] == read(w / "public/git_after.json") and read(w / "public/preservation.json")["Status"] == "PASS")
        spec = read(w / "public/spec.json")
        self.check("worker spec identity", spec == read(self.root / "operator/spec.json") == completion["Input"]["spec"])
        source_manifest = self.root / "operator/source_manifest.json"
        self.check("worker exact source binding", Path(spec["source_manifest_path"]).resolve() == source_manifest.resolve()
                   and info(source_manifest)["sha256"] == spec["source_manifest_sha256"]
                   and before["files"][str(source_manifest)] == info(source_manifest)
                   and all(before["files"].get(k) == v for k,v in read(source_manifest).items()))
        self.check("worker exact prepared prefix binding", Path(spec["inputs_path"]).resolve() == (self.root / "data/private/inputs.json").resolve()
                   and spec["inputs_sha256"] == INPUT_SHA and Path(spec["data_manifest_path"]).resolve() == (self.root / "data/public/completion.json").resolve()
                   and spec["data_manifest_sha256"] == info(spec["data_manifest_path"])["sha256"])
        state = read(w / "public/state_before.json")
        self.check("all63 state entries preserved", state == read(w / "public/state_after.json") and state["state_count"] == len(state["entries"]) == 63
                   and state["aggregate_sha256"] == sha(canonical(state["entries"])))
        for name in ("config", "packages"):
            self.check(name+" preserved", read(w / ("public/"+name+"_before.json")) == read(w / ("public/"+name+"_after.json")))
        self.check("unit model logit scale", read(w / "public/config_before.json")["init_logit_scale"] == 1.0)

    def run(self):
        samples, labels = self.audit_data()
        self.audit_seal()
        w = self.worker
        rows = [json.loads(x) for x in (w / "public/calls.jsonl").read_text().splitlines()]
        self.check("64 quality records", len(rows) == 64)
        by_seed, references, totals = {}, {}, {arm:collections.Counter() for arm in ("adaptive","fixed32")}
        mapping = {"embedding":"embedding_calls","prelude":"prelude_block_calls","prelude_norm":"prelude_norm_calls",
                   "adapter":"adapter_calls","core":"core_block_calls","projection":"projection_calls","coda":"coda_block_calls",
                   "final_norm":"final_norm_calls","head":"head_calls","value_embedding":"value_embedding_calls"}
        for number, row in enumerate(rows,1):
            case, position = (number-1)//2, (number-1)%2
            article, seed = case//2, (3101,3202)[case%2]
            arms = ("adaptive","fixed32") if case%2 == 0 else ("fixed32","adaptive")
            arm, sample = arms[position], samples[article]
            self.check("quality identity/order "+str(number), row == read(w / f"public/call_{number:03d}.json") and row["call"] == number
                       and row["status"] == "PASS" and not row["cleanup_errors"] and row["error"] is None
                       and row["context"]["case_index"] == case and row["context"]["article_index"] == article
                       and row["context"]["seed"] == seed and row["context"]["arm"] == arm and row["context"]["phase"] == "quality"
                       and row["context"]["source_article_key"] == sample["source_article_key"] and row["input_shape"] == [1,128]
                       and row["input_sha256"] == sample["raw_input_sha256"] and row["input_ids_json_sha256"] == sha(canonical([sample["tokens"]])))
            depth = row["selected_depth"]
            if arm == "adaptive":
                self.check("adaptive frozen predicate "+str(number), row["mode"] == "adaptive" and row["requested_depth"] is None
                           and math.isfinite(row["tv_8_16"]) and 0 <= row["tv_8_16"] <= 1 and depth == (16 if row["tv_8_16"] <= .01 else 32))
                keys = [8,16] if depth == 16 else [8,16,32]
            else:
                self.check("fixed32 single readout "+str(number), row["mode"] == "fixed" and row["requested_depth"] == depth == 32 and row["tv_8_16"] is None)
                keys = [32]
            r = len(keys)
            counts = {"embedding":1,"prelude":2,"prelude_norm":1,"adapter":depth,"core":2*depth,"projection":r,"coda":2*r,"final_norm":r,"head":r,"value_embedding":1+depth+r}
            extra = {"h0_calls":1,"recurrent_updates":depth,"readouts":r,"readout_clone_elements":r*128*768,"total_block_calls":2+2*depth+2*r,
                     "policy_evaluations":int(arm=="adaptive"),"policy_softmax_calls":2*int(arm=="adaptive"),"policy_vocabulary_elements":65536*int(arm=="adaptive")}
            self.check("observed/bookkept operation counts "+str(number), row["actual_counts"] == counts and set(row["outputs"]) == {str(k) for k in keys}
                       and all(row["library_counts"][b] == counts[a] for a,b in mapping.items()) and all(row["library_counts"][k] == v for k,v in extra.items()))
            totals[arm].update(counts)
            obs = row["observed"]
            self.check("real h0/readout observations "+str(number), len(obs["h0"]) == 1 and len(obs["readout_states"]) == len(obs["head_outputs"]) == r)
            h0 = self.raw(obs["h0"][0],[1,128,768])
            rng = [self.raw(row[k],row[k]["shape"],"torch.uint8") for k in ("rng_before","rng_after")]
            identity = (h0,*rng,obs["h0"][0]["rng_after_init_sha256"])
            by_seed.setdefault(seed,identity)
            self.check("actual same-seed h0/RNG bytes "+str(number), identity == by_seed[seed]
                       and row["library_h0_sha256"] == sha(h0) and row["library_rng_before_sha256"] == row["rng_before_sha256"] == sha(rng[0])
                       and row["library_rng_after_sha256"] == row["rng_after_sha256"] == sha(rng[1]))
            outputs = {d:self.raw(row["outputs"][str(d)],[1,32768]) for d in keys}
            self.check("saved logits bind head observations "+str(number), all(x["shape"] == [1,128,32768] and x["dtype"] == "torch.float32"
                       and x["last_raw_sha256"] == sha(outputs[d]) for d,x in zip(keys,obs["head_outputs"]))
                       and all(x["shape"] == [1,128,768] for x in obs["readout_states"])
                       and row["library_state_sha256"] == {str(d):obs["readout_states"][i]["sha256"] for i,d in enumerate(keys)})
            scalar_tv = None
            if arm == "adaptive":
                scalar_tv = tv(values(outputs[8]),values(outputs[16]))
                self.check("independent scalar TV "+str(number), abs(scalar_tv-row["tv_8_16"]) <= 1e-12,
                           {"recorded":row["tv_8_16"],"independent":scalar_tv},"absolute<=1e-12; frozen decision unchanged")
            references[(case,arm)] = {"row":row,"raw":outputs[depth],"score":score(values(outputs[depth]),labels[article]["target_token"]),"scalar_tv":scalar_tv}
        pair_file = read(w / "public/quality_pairs.json")
        self.check("quality pairs complete", pair_file["Status"] == "PASS" and len(pair_file["Actual"]["pairs"]) == 32)
        cases = []
        for case, pair in enumerate(pair_file["Actual"]["pairs"]):
            a,f = references[(case,"adaptive")],references[(case,"fixed32")]
            ar,fr = a["row"],f["row"]
            article, seed = case//2,(3101,3202)[case%2]
            expected = {"case_index":case,"article_index":article,"seed":seed,"source_article_key":samples[article]["source_article_key"],
                        "order":["adaptive","fixed32"] if case%2==0 else ["fixed32","adaptive"],"adaptive_call":ar["call"],"fixed32_call":fr["call"],
                        "adaptive_depth":ar["selected_depth"],"tv_8_16":ar["tv_8_16"],"adaptive_logits":ar["outputs"][str(ar["selected_depth"])],
                        "fixed32_logits":fr["outputs"]["32"],"paired_h0_sha256":ar["library_h0_sha256"],
                        "paired_rng_before_sha256":ar["rng_before_sha256"],"paired_rng_after_sha256":ar["rng_after_sha256"]}
            self.check("quality pair exact record binding "+str(case), pair == expected)
            self.check("nonexit adaptive output identity "+str(case), ar["selected_depth"] != 32 or a["raw"] == f["raw"])
            cases.append({"case_index":case,"article_index":article,"seed":seed,"source_article_key":samples[article]["source_article_key"],
                          "adaptive_depth":ar["selected_depth"],"adaptive":a["score"],"fixed32":f["score"],"delta_nll":a["score"]["nll"]-f["score"]["nll"],
                          "tv_8_16":ar["tv_8_16"],"scalar_tv_8_16":a["scalar_tv"],
                          "scalar_predicate_disagreement":(a["scalar_tv"]<=.01)!=(ar["tv_8_16"]<=.01),"near_threshold":abs(ar["tv_8_16"]-.01)<=1e-12})
        timing_rows = [json.loads(x) for x in (w / "public/timing_calls.jsonl").read_text().splitlines()]
        self.check("130 warmup/timing rows", len(timing_rows)==130)
        for ordinal,row in enumerate(timing_rows,1):
            ref=references[(row["case_index"],row["arm"])]
            rr=ref["row"]
            self.check("timed identity/order annotations "+str(ordinal), row["ordinal"]==ordinal and row["status"]=="PASS" and row["error"] is None
                       and row["article_index"]==row["case_index"]//2 and row["seed"]==(3101,3202)[row["case_index"]%2]
                       and row["quality_reference_call"]==rr["call"] and row["selected_depth"]==rr["selected_depth"]
                       and row["tv_8_16"]==rr["tv_8_16"] and row["h0_sha256"]==rr["library_h0_sha256"]
                       and row["input_sha256"]==rr["input_sha256"] and row["rng_before_sha256"]==rr["rng_before_sha256"]
                       and row["rng_after_sha256"]==rr["rng_after_sha256"] and row["library_counts"]==rr["library_counts"])
            self.check("timed actual output byte identity "+str(ordinal), self.raw(row["selected_logits"],[1,32768])==ref["raw"])
        summary=read(w / "public/timing_summary.json")
        self.check("timing summary byte record correspondence", summary["Status"]=="PASS" and summary["Actual"]=={"warmup_calls":2,"timed_calls":128,"timing_rows":timing_rows})
        quality,timing=quality_summary(cases),timing_summary(timing_rows)
        screens={"quality":quality["screen"],"cpu_time":timing["screen"],"joint":{"Status":"PASS" if quality["screen"]["Status"]==timing["screen"]["Status"]=="PASS" else "FAIL","Expected":"Both quality and CPU time screens PASS"}}
        self.check("no model imports during audit", not any(x.split(".")[0] in ("torch","parcae_lm","receval","transformers") for x in sys.modules))
        return {"quality_results":quality,"timing_results":timing,"screens":screens,
                "mechanism_results":{"quality_results":quality,"timing_results":timing,"screens":screens},
                "describe_cost":{"timing":timing,"quality_phase_observed_totals":{k:dict(v) for k,v in totals.items()}},
                "finite_saved_fp32_components":self.finite_components,
                "scope":"16 selected source articles, two shared h0 seeds; one true next token per source. Exploratory sample screens, no fresh/generalization/statistical confirmation."}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--run",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    if not args.run.is_absolute() or not args.output.is_absolute() or any(args.output.resolve().is_relative_to(args.run.resolve()/x) for x in ("worker","data")):
        parser.error("Absolute paths; output outside sealed data/worker")
    audit,status,actual,error=Audit(args.run),"NOT TESTED",{},None
    try:
        actual=audit.run()
        status="PASS"
    except BaseException as exc:
        status="BLOCKED" if isinstance(exc,(OSError,Incomplete)) else "FAIL"
        error={"type":type(exc).__name__,"reason":str(exc),"traceback":traceback.format_exc()}
    result={"Purpose":"Independent true-next-token quality and complete CPU API timing audit","Environment":sys.version,
            "Input":str(args.run),"Expected":"194 calls; labels/source/bytes/pairs/counters/timing verified; scientific negative allowed",
            "Actual":{**actual,"checks":audit.checks,"error":error},"Status":status,"utc":datetime.datetime.now(datetime.timezone.utc).isoformat()}
    with args.output.open("x",encoding="utf-8",newline="\n") as f:
        json.dump(result,f,indent=2,ensure_ascii=False,allow_nan=False)
        f.write("\n")
    print(json.dumps({"Status":status,"checks":len(audit.checks),"error":error}))
    return 0 if status=="PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
