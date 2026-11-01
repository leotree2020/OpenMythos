"""Independent, read-only decoding evidence audit (Python standard library only).

Does not import or execute Torch, NumPy, tokenizers, model or experiment modules.
The output JSON must be outside both immutable input directories.
"""

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import struct
import sys
import traceback


VOCAB = 32768
STEPS = 64
LAST_BYTES = VOCAB * 4
PANELS = {"G": (0,), "S": (1, 2, 3), "P": (1, 2, 3)}
CHUNK = 1024 * 1024
OBSERVATION_KEYS = (
    "policy", "panel", "prompt_id", "model_seed", "sampler_seed", "step",
    "prefix_ids", "prefix_ids_sha256", "prefix_hash_encoding", "input_length",
    "full_logits_shape", "dtype", "cache_none", "num_steps", "all_logits_finite",
    "full_logits", "last_logits", "last_logits_file", "default_rng_before_forward",
    "default_rng_after_forward", "sampler_rng_before_forward", "sampler_rng_after_forward",
)
RNG_KEYS = (
    "default_rng_before_forward", "default_rng_after_forward",
    "default_rng_before_selector", "default_rng_after_selector",
    "sampler_rng_before_forward", "sampler_rng_after_forward",
    "sampler_rng_before_selector", "sampler_rng_after_selector",
)


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def object_unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key: " + key)
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError("nonfinite JSON constant: " + value)


def parse(text):
    return json.loads(text, object_pairs_hook=object_unique, parse_constant=reject_constant)


def digest_bytes(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def valid_digest(value, size=None):
    return (isinstance(value, dict) and type(value.get("bytes")) is int and value["bytes"] >= 0
            and (size is None or value["bytes"] == size)
            and isinstance(value.get("sha256"), str) and len(value["sha256"]) == 64
            and all(char in "0123456789abcdef" for char in value["sha256"]))


def valid_ids(values):
    return isinstance(values, list) and all(type(value) is int and 0 <= value < VOCAB for value in values)


class Audit:
    def __init__(self, root, history, expected_identity):
        self.root, self.history = root, history
        self.expected_identity = expected_identity
        self.failures, self.blockers = [], []
        self.counts, self.check_statuses = Counter(), Counter()
        self.digests = {}
        self.sealed = (root / "FULL_MANIFEST.json").is_file() and (root / "public/summary.json").is_file()
        self.summary = {}
        self.worker = {}
        self.generation_summary = {}
        self.greedy_traces = {}
        self.prompt_inputs = {}
        self.sampler_initial = {}
        self.generations = []
        self.expected_manifest = {}
        self.actual_members = set()
        self.complete_counts = False
        self.sealed_run_file_integrity = "NOT TESTED"

    def issue(self, reason, path=None, actual=None, expected=None, blocked=False):
        item = {"reason": reason}
        if path is not None:
            item["path"] = str(path)
        if actual is not None:
            item["actual"] = actual
        if expected is not None:
            item["expected"] = expected
        (self.blockers if blocked else self.failures).append(item)

    def check(self, ok, reason, path=None, actual=None, expected=None):
        self.counts["assertions"] += 1
        if not ok:
            self.issue(reason, path, actual, expected)
        return bool(ok)

    def section(self, name, callback):
        try:
            callback()
        except Exception as exc:
            self.issue("Audit section could not finish: " + name, actual={"type": type(exc).__name__,
                       "error": str(exc), "traceback": traceback.format_exc()}, blocked=True)

    def load(self, path, jsonl=False, required=True):
        try:
            if path.is_symlink():
                self.issue("Evidence file is a symlink", path)
                return None
            text = path.read_text(encoding="utf-8")
            return [parse(line) for line in text.splitlines()] if jsonl else parse(text)
        except FileNotFoundError:
            if required:
                self.issue("Required evidence missing", path, blocked=not self.sealed)
        except (OSError, UnicodeError) as exc:
            self.issue("Evidence cannot be read", path, str(exc), blocked=True)
        except (ValueError, TypeError) as exc:
            self.issue("Malformed evidence JSON", path, str(exc), blocked=not self.sealed)
        return None

    def digest(self, path):
        key = str(path)
        if key in self.digests:
            return self.digests[key]
        try:
            if path.is_symlink():
                self.issue("Hashed file is a symlink", path)
                return None
            before = path.stat()
            sha = hashlib.sha256()
            total = 0
            with path.open("rb") as stream:
                for block in iter(lambda: stream.read(CHUNK), b""):
                    sha.update(block)
                    total += len(block)
            after = path.stat()
            self.check(before.st_size == after.st_size == total and before.st_mtime_ns == after.st_mtime_ns,
                       "File changed while being audited", path)
            result = {"size": total, "sha256": sha.hexdigest()}
            self.digests[key] = result
            return result
        except OSError as exc:
            self.issue("Cannot hash required file", path, str(exc), blocked=True)
            return None

    def safe_member(self, root, relative):
        if not isinstance(relative, str):
            self.issue("Manifest path is not a string", actual=relative)
            return None
        parts = PurePosixPath(relative)
        if (parts.is_absolute() or not parts.parts or ".." in parts.parts or "\\" in relative
                or parts.as_posix() != relative):
            self.issue("Unsafe or noncanonical manifest path", actual=relative)
            return None
        path = root.joinpath(*parts.parts)
        if not path.resolve().is_relative_to(root):
            self.issue("Manifest path escapes evidence root", path)
            return None
        return path

    def byte_equal(self, left, right, size):
        try:
            if left.is_symlink() or right.is_symlink():
                self.issue("Byte comparison contains symlink", left, str(right))
                return False
            if left.stat().st_size != size or right.stat().st_size != size:
                self.issue("Raw comparison length differs", left,
                           {"left": left.stat().st_size, "right": right.stat().st_size}, size)
                return False
            with left.open("rb") as a, right.open("rb") as b:
                while True:
                    x, y = a.read(CHUNK), b.read(CHUNK)
                    if x != y:
                        self.issue("Raw evidence bytes differ", left, str(right))
                        return False
                    if not x:
                        return True
        except OSError as exc:
            self.issue("Cannot compare raw evidence", left, {"other": str(right), "error": str(exc)}, blocked=True)
            return False

    def manifest(self):
        initial_failures, initial_blockers = len(self.failures), len(self.blockers)
        full = self.load(self.root / "FULL_MANIFEST.json")
        public = self.load(self.root / "public/GIT_BUNDLE_MANIFEST.json")
        if not isinstance(full, dict) or not isinstance(full.get("files"), list):
            self.issue("Complete full manifest unavailable", blocked=True)
            return
        self.check(full.get("excluded") == ["FULL_MANIFEST.json", "public/GIT_BUNDLE_MANIFEST.json"],
                   "Only the two declared self-reference exclusions are allowed")
        for item in full["files"]:
            if not isinstance(item, dict):
                self.issue("Manifest row is not an object", actual=item)
                continue
            relative = item.get("path")
            path = self.safe_member(self.root, relative)
            if path is None:
                continue
            self.check(relative not in self.expected_manifest, "Duplicate manifest path", relative)
            self.expected_manifest[relative] = item
            expected_class = "public" if "public" in PurePosixPath(relative).parts else "private"
            self.check(item.get("class") == expected_class, "Manifest classification differs", relative)
            actual = self.digest(path)
            if self.check(actual == {"size": item.get("size"), "sha256": item.get("sha256")},
                          "Full manifest file hash/size differs", relative, actual,
                          {"size": item.get("size"), "sha256": item.get("sha256")}):
                self.counts["manifest_files_verified"] += 1
        for path in self.root.rglob("*"):
            if path.is_symlink():
                self.issue("Symlink inside run evidence", path)
            if path.is_file():
                self.actual_members.add(path.relative_to(self.root).as_posix())
        expected = set(self.expected_manifest) | {"FULL_MANIFEST.json", "public/GIT_BUNDLE_MANIFEST.json"}
        self.check(self.actual_members == expected, "Run file membership differs from manifest",
                   actual={"unlisted": sorted(self.actual_members - expected),
                           "missing": sorted(expected - self.actual_members)})
        self.counts["actual_run_files"] = len(self.actual_members)
        if isinstance(public, dict):
            self.check(public.get("files") == [item for item in full["files"] if item.get("class") == "public"],
                       "Public bundle manifest does not match full manifest")
            self.check(public.get("excluded") == ["public/GIT_BUNDLE_MANIFEST.json"]
                       and public.get("raw_logits_exported") is False,
                       "Public manifest exclusions or private-logit declaration differ")
        self.sealed_run_file_integrity = ("FAIL" if len(self.failures) > initial_failures else
                                          "BLOCKED" if len(self.blockers) > initial_blockers else "PASS")
        # Verify this immutable history against its published full manifest too,
        # without importing any of its code or requiring a rerun.
        historical_root = self.history.parent.parent
        history_manifest = self.load(historical_root / "FULL_MANIFEST.json")
        if isinstance(history_manifest, dict):
            prefix = self.history.relative_to(historical_root).as_posix() + "/"
            for item in history_manifest.get("files", []):
                if item.get("path", "").startswith(prefix):
                    path = self.safe_member(historical_root, item["path"])
                    if path is not None:
                        self.check(self.digest(path) == {"size": item["size"], "sha256": item["sha256"]},
                                   "Historical reference file differs from its manifest", path)
                        self.counts["historical_reference_manifest_files"] += 1

    def statuses(self):
        summary = self.load(self.root / "public/summary.json")
        self.summary = summary if isinstance(summary, dict) else {}
        if self.summary:
            for key, expected in self.expected_identity.items():
                self.check(self.summary.get(key) == expected, "Frozen run identity differs",
                           actual={"field": key, "value": self.summary.get(key)}, expected=expected)
        expected_gates = {"D%d" % index: "PASS" for index in range(5)}
        if self.summary.get("engineering_status") != "PASS" or self.summary.get("gates") != expected_gates:
            self.issue("Experiment has not established complete engineering acceptance",
                       actual={"status": self.summary.get("engineering_status"), "gates": self.summary.get("gates")},
                       blocked=True)
        self.check(self.summary.get("run_id") == self.root.name, "Run ID differs from evidence directory")
        if self.summary:
            self.check(self.summary.get("historical_B1_A5") == "BLOCKED" and self.summary.get("A5_threshold") == 1e-6
                       and self.summary.get("FORMAL_ACCEPTANCE_READY") is False,
                       "Protected historical interpretation changed")
        for path in sorted(self.root.rglob("*.json")):
            if path.name.startswith(("check_", "worker_check_")):
                row = self.load(path)
                if isinstance(row, dict):
                    self.check_record(row, path)
        for path in sorted(self.root.rglob("checks.jsonl")):
            rows = self.load(path, jsonl=True)
            if rows is not None:
                for index, row in enumerate(rows):
                    self.check_record(row, str(path) + ":" + str(index + 1))
        if self.summary.get("engineering_status") == "PASS":
            self.check(set(self.check_statuses) == {"PASS"}, "Engineering PASS contains non-PASS checks",
                       actual=dict(self.check_statuses))
            self.clean_terminal(self.summary, "coordinator")
            exceptional = sorted(name for name in self.actual_members
                                 if "emergency" in name.lower() or PurePosixPath(name).name == "exception.json")
            self.check(not exceptional, "Complete PASS contains emergency/exception evidence", actual=exceptional)
        worker = self.load(self.root / "first/public/summary.json", required=self.summary.get("engineering_status") == "PASS")
        if isinstance(worker, dict):
            self.check(worker.get("implementation_commit") == self.expected_identity["implementation_commit"],
                       "Worker implementation commit differs", actual=worker.get("implementation_commit"),
                       expected=self.expected_identity["implementation_commit"])
            calls, returned = worker.get("official_loader_calls"), worker.get("official_loader_returned")
            if worker.get("status") == "PASS":
                self.check(calls == returned == 1, "Official model loader count is not exactly one")
            else:
                self.check(type(calls) is int and type(returned) is int and 0 <= returned <= calls <= 1,
                           "Partial worker loader accounting is impossible", actual={"attempted": calls, "returned": returned})
            if self.summary.get("engineering_status") == "PASS":
                self.check(worker.get("status") == "PASS" and worker.get("gates") == {"D1": "PASS", "D2": "PASS", "D3": "PASS"},
                           "Worker gates contradict complete run")
                self.clean_terminal(worker, "worker")
            self.check(self.summary.get("workers", {}).get("first") == worker,
                       "Coordinator's worker summary differs from worker file")
        self.worker = worker if isinstance(worker, dict) else {}
        if not self.worker:
            self.issue("Complete worker evidence unavailable", blocked=True)
        token_report = self.load(self.root / "first/public/tokenizer.json",
                                 required=self.summary.get("engineering_status") == "PASS")
        if isinstance(token_report, dict):
            rows = token_report.get("prompts", [])
            self.check(token_report.get("status") == "PASS"
                       and [row.get("id") for row in rows] == list(range(1, 13)),
                       "Frozen tokenizer/prompt acceptance differs")
            self.prompt_inputs = {row["id"]: row for row in rows}

    def clean_terminal(self, value, path):
        """A complete PASS cannot conceal a stop or cleanup failure."""
        if isinstance(value, dict):
            for key, child in value.items():
                child_path = path + "." + key
                if key in ("stop", "stop_reason"):
                    self.check(child is None, "Complete PASS contains non-null stop", child_path, child)
                elif key in ("cleanup_errors", "terminal_save_error", "evidence_save_error",
                             "emergency", "emergency_error", "emergency_stop"):
                    self.check(not child, "Complete PASS contains cleanup/emergency failure", child_path, child)
                self.clean_terminal(child, child_path)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                self.clean_terminal(child, path + "[%d]" % index)

    def check_record(self, row, path):
        if not isinstance(row, dict):
            self.issue("Check record is not an object", path)
            return
        required = {"Purpose", "Environment", "Input", "Expected", "Actual", "Status"}
        self.check(required <= set(row), "Acceptance record missing required fields", path)
        self.check(row.get("Status") in ("PASS", "FAIL", "BLOCKED", "NOT TESTED"),
                   "Unknown acceptance status", path, row.get("Status"))
        self.check_statuses[row.get("Status", "MISSING")] += 1
        self.counts["recorded_checks"] += 1

    def state_and_invariance(self):
        worker = self.root / "first/public"
        complete_claim = self.summary.get("engineering_status") == "PASS"
        normalization = self.load(worker / "normalization.json", required=complete_claim)
        names = set(normalization.values()) if isinstance(normalization, dict) else set()
        if normalization is not None:
            self.check(len(names) == 63 and isinstance(normalization, dict) and len(normalization) == 63,
                       "Normalized complete state key coverage differs")
        collected = {}
        for phase in ("before", "after"):
            path = worker / ("state_" + phase + ".json")
            state = self.load(path, required=complete_claim)
            if not isinstance(state, dict):
                continue
            report, rows = state.get("report", {}), state.get("rows", [])
            self.check(report.get("byte_order") == "little", "Recorded CPU byte order differs from FP32 audit encoding", path)
            self.check(report.get("status") == "PASS" and report.get("errors") == [] and len(rows) == 63,
                       "State evidence is incomplete or failed", path)
            row_map = {row["name"]: row for row in rows}
            self.check(len(row_map) == len(rows) == 63 and set(row_map) == names,
                       "State row key coverage differs", path)
            inventory = {row["name"]: row for row in report.get("inventory", [])}
            for name, row in row_map.items():
                expected = math.prod(row["shape"]) * 4
                self.check(row.get("status") == "PASS" and row.get("bytewise_equal") is True
                           and row.get("hash_complete") is True and row.get("dtype") == "torch.float32"
                           and row.get("numel") == math.prod(row["shape"])
                           and row.get("expected_bytes") == expected
                           and all(row.get(key) == expected for key in ("bytes_hashed", "source_bytes_hashed", "model_bytes_hashed"))
                           and row.get("source_sha256") == row.get("model_sha256")
                           and row.get("source_finite") is True and row.get("model_finite") is True,
                           "State row equality/coverage/finite evidence differs", str(path) + ":" + name)
                self.check(valid_digest({"bytes": expected, "sha256": row.get("source_sha256")}),
                           "Invalid state digest", str(path) + ":" + name)
                if name in inventory:
                    item = inventory[name]
                    self.check(all(item[key].get("device") == "cpu" and item[key].get("dtype") == "torch.float32"
                                   and item[key].get("shape") == row["shape"]
                                   for key in ("metadata", "state_metadata", "source_metadata")),
                               "State metadata inconsistent", str(path) + ":" + name)
                else:
                    self.issue("State entry missing inventory", str(path) + ":" + name)
                self.counts["state_rows_verified"] += 1
            for field in ("object_id", "data_ptr", "storage_data_ptr", "storage_offset", "shape", "stride"):
                left = inventory.get("transformer.wte.weight", {}).get("metadata", {})
                right = inventory.get("lm_head.weight", {}).get("metadata", {})
                self.check(field in left and left.get(field) == right.get(field),
                           "Tied embedding/head metadata differs", path, field)
            collected[phase] = row_map
        if set(collected) == {"before", "after"}:
            for name in sorted(names):
                self.check(collected["before"].get(name, {}).get("model_sha256") == collected["after"].get(name, {}).get("model_sha256"),
                           "Model state changed across decoding", name)
        invariant = self.load(self.root / "public/invariance.json")
        before = self.load(self.root / "private/protected_before.json", required=complete_claim)
        if not isinstance(invariant, dict) or not isinstance(before, dict):
            self.issue("Complete protected-state baseline unavailable", blocked=True)
            return
        if complete_claim:
            self.check(invariant.get("complete_baseline") is True and invariant.get("changes") == []
                       and invariant.get("unavailable") == [] and invariant.get("file_integrity_status") == "PASS"
                       and invariant.get("worker_completed_post_generation_state_check") is True,
                       "Protected-state terminal acceptance not established")
        else:
            self.check(not invariant.get("changes"), "Protected-state record reports changed files", actual=invariant.get("changes"))
            if (invariant.get("complete_baseline") is not True or invariant.get("unavailable")
                    or invariant.get("worker_completed_post_generation_state_check") is not True):
                self.issue("Only partial protected-state verification is available", blocked=True)
        self.check(set(invariant.get("files", {})) == set(before.get("files", {})),
                   "Protected file inventory differs from baseline")
        for name, entry in invariant.get("files", {}).items():
            self.check(entry.get("unchanged") is True and entry.get("actual") == entry.get("expected") == before["files"].get(name),
                       "Recorded protected file differs", name)
            # Re-read bytes independently. These exact absolute paths were part
            # of the explicitly protected baseline; do not discover new targets.
            path = Path(name)
            if not path.is_absolute():
                self.issue("Protected file path is not absolute", name)
                continue
            actual = self.digest(path)
            self.check(actual == entry.get("expected"), "Current protected bytes differ", name, actual, entry.get("expected"))
            self.counts["protected_files_rehashed"] += 1
        for name, entry in invariant.get("git", {}).items():
            self.check(entry.get("unchanged") is True and entry.get("actual") == entry.get("expected") == before.get("git", {}).get(name),
                       "Recorded Git invariance differs", name)
        for name, entry in invariant.get("trees", {}).items():
            self.check(entry.get("added") == [] and entry.get("removed") == [], "Recorded protected tree membership differs", name)
            path = Path(name)
            if path.is_dir():
                actual = sorted(item.relative_to(path).as_posix() for item in path.rglob("*") if item.is_file())
                self.check(actual == before.get("trees", {}).get(name), "Current protected tree membership differs", name)
            else:
                self.issue("Protected directory unavailable for independent membership check", name, blocked=True)

    def quality(self, quality, path):
        raw, full, inputs = quality.get("raw_new_ids"), quality.get("full_generated_ids"), quality.get("input_ids")
        if not self.check(valid_ids(raw) and valid_ids(full) and valid_ids(inputs) and bool(inputs),
                          "Invalid token lists", path):
            return
        self.check(len(raw) == STEPS and full == inputs + raw and quality.get("raw_new_token_count") == STEPS,
                   "Raw continuation coverage differs", path)
        eos_positions = [i for i, token in enumerate(raw) if token == 1]
        first_eos = eos_positions[0] if eos_positions else None
        effective = raw[:first_eos] if first_eos is not None else raw
        self.check(quality.get("eos_id") == 1 and quality.get("eos_position") == first_eos
                   and quality.get("eos_positions_all_64") == eos_positions and quality.get("continuation_ids") == effective,
                   "EOS or effective continuation arithmetic differs", path)
        grams = Counter(tuple(effective[i:i + 4]) for i in range(max(0, len(effective) - 3)))
        run_length = longest = 0
        previous = None
        for token in effective:
            run_length = run_length + 1 if token == previous else 1
            longest = max(longest, run_length)
            previous = token
        auto = quality.get("auto", {})
        text = quality.get("text_continuation")
        self.check(text is None or isinstance(text, str), "Stored continuation text has invalid type", path)
        rules = {"min_16_new_tokens": len(effective) >= 16,
                 "no_4gram_3x": max(grams.values(), default=0) < 3,
                 "no_token_run_6": longest < 6,
                 "decodes_without_error": auto.get("decode_error") is None,
                 "no_u_fffd": text is not None and "\ufffd" not in text}
        self.check(auto.get("rules") == rules and auto.get("passed") is all(rules.values())
                   and auto.get("length") == len(effective) and auto.get("max_4gram_count") == max(grams.values(), default=0)
                   and auto.get("longest_token_run") == longest
                   and auto.get("ends_with_u_fffd_note") == (bool(text) and text.endswith("\ufffd")),
                   "Automatic token/text screen recomputation differs", path)
        self.counts["automatic_quality_rows_recomputed"] += 1

    def conditions(self):
        base = self.root / "first/generation"
        doc = self.load(base / "public/summary.json", required=self.summary.get("engineering_status") == "PASS")
        self.generation_summary = doc if isinstance(doc, dict) else {}
        for policy, panels in PANELS.items():
            for panel in panels:
                for prompt_id in range(1, 13):
                    self.section("condition %s/%d/%d" % (policy, panel, prompt_id),
                                 lambda p=policy, n=panel, i=prompt_id: self.condition(base, p, n, i))
        expected = {"generation_rows": 84, "trace_steps": 5376, "observation_rows": 5376,
                    "last_vectors_verified": 5376, "greedy_history_byte_pairs": 768,
                    "sampling_initial_byte_pairs": 72, "G_rng_states_verified": 1536,
                    "automatic_quality_rows_recomputed": 84, "state_rows_verified": 126}
        self.complete_counts = all(self.counts[name] == value for name, value in expected.items())
        if not self.complete_counts:
            self.issue("Required complete evidence coverage has not been established",
                       actual={name: self.counts[name] for name in expected}, expected=expected, blocked=True)
        expected_files = set()
        for policy, panels in PANELS.items():
            for panel in panels:
                for prompt_id in range(1, 13):
                    stem = "%s_panel%d_prompt%02d" % (policy, panel, prompt_id)
                    expected_files.add(stem + "_generation.json")
        actual_files = {path.name for path in (base / "public").glob("*_generation.json")}
        self.check(not (actual_files - expected_files), "Unexpected extra generation conditions", actual=sorted(actual_files - expected_files))
        if doc:
            if self.complete_counts:
                self.check(doc.get("conditions") == self.generations, "Generation summary rows/order differ from evidence files")
                self.check(self.worker.get("inference") == doc, "Worker inference summary differs from generation summary")
                self.check(doc.get("official_generate_calls") == 0 and doc.get("official_forward_calls") == self.counts["trace_steps"],
                           "Forward call count differs from complete traces")
            else:
                accepted = doc.get("conditions", [])
                self.check(accepted == self.generations[:len(accepted)],
                           "Partial accepted conditions differ from available evidence")
                calls = doc.get("official_forward_calls")
                self.check(doc.get("official_generate_calls") == 0 and type(calls) is int
                           and self.counts["trace_steps"] <= calls <= 5376,
                           "Partial forward-call accounting is impossible", actual=calls)
            if self.complete_counts:
                self.check(doc.get("status") == "PASS" and doc.get("gates") == {"D2": "PASS", "D3": "PASS"}
                           and doc.get("conditions_expected") == 84 and doc.get("forward_calls_expected") == 5376,
                           "Generation terminal acceptance differs")
                self.clean_terminal(doc, "generation")
            if self.complete_counts:
                for policy, panels in PANELS.items():
                    for panel in panels:
                        rows = [row for row in self.generations if row["policy"] == policy and row["panel"] == panel]
                        passed = sum(row["quality"]["auto"]["passed"] for row in rows)
                        self.check(doc.get("automatic_panels", {}).get(policy, {}).get(str(panel), {}).get("passed") == passed,
                                   "Automatic panel total differs", actual={"policy": policy, "panel": panel, "count": passed})

    def condition(self, base, policy, panel, prompt_id):
        stem = "%s_panel%d_prompt%02d" % (policy, panel, prompt_id)
        path = base / "public" / (stem + "_generation.json")
        generation = self.load(path, required=self.summary.get("engineering_status") == "PASS")
        if not isinstance(generation, dict):
            self.issue("Planned generation is incomplete", path, blocked=True)
            return
        self.generations.append(generation)
        self.counts["generation_rows"] += 1
        sampler_seed = None if policy == "G" else 841000 + 100 * panel + prompt_id
        identity = {"policy": policy, "panel": panel, "prompt_id": prompt_id,
                    "model_seed": 731000 + prompt_id, "sampler_seed": sampler_seed}
        self.check(all(generation.get(key) == value for key, value in identity.items()), "Condition identity/seed differs", path)
        quality = generation["quality"]
        frozen_prompt = self.prompt_inputs.get(prompt_id, {})
        self.check(quality.get("id") == prompt_id and quality.get("seed") == 731000 + prompt_id
                   and quality.get("input_ids") == frozen_prompt.get("input_ids")
                   and quality.get("prompt") == frozen_prompt.get("text"),
                   "Generation input differs from accepted frozen prompt", path)
        self.quality(quality, path)
        trace_path = base / "public" / (stem + "_trace.jsonl")
        trace = self.load(trace_path, jsonl=True)
        if trace is None:
            return
        actual_trace_digest = self.digest(trace_path)
        self.check(actual_trace_digest is not None and generation.get("trace") == {
            "bytes": actual_trace_digest["size"], "sha256": actual_trace_digest["sha256"]},
                   "Generation trace digest differs", path)
        self.check(len(trace) == generation.get("observed_steps") == STEPS
                   and [row.get("step") for row in trace] == list(range(STEPS)), "Ordered 64-step trace coverage differs", trace_path)
        historical = None
        if policy == "G":
            historical = self.load(self.history / "public" / ("pass1_prompt%02d_trace.jsonl" % prompt_id), jsonl=True)
            history_generation = self.load(self.history / "public" / ("pass1_prompt%02d_generation.json" % prompt_id))
            if isinstance(history_generation, dict):
                self.check(quality == history_generation.get("quality"), "Greedy complete quality/token/text/EOS differs from history", path)
            self.greedy_traces[prompt_id] = trace
        for step, row in enumerate(trace):
            self.section(stem + " step " + str(step), lambda s=step, r=row: self.step(
                base, stem, policy, prompt_id, identity, quality, s, r, historical))
        if policy == "G":
            rng_path = base / "private" / (stem + "_default_rng.bin")
            try:
                with rng_path.open("rb") as stream:
                    for row in trace:
                        for key in ("default_rng_before_forward", "default_rng_after_forward"):
                            item = row[key]
                            if not valid_digest(item) or not (0 < item["bytes"] <= CHUNK):
                                self.issue("Invalid recorded G RNG block length", rng_path, item)
                                return
                            block = stream.read(item["bytes"])
                            if self.check(digest_bytes(block) == item, "Private G RNG block hash differs", rng_path,
                                          {"step": row["step"], "field": key}):
                                self.counts["G_rng_states_verified"] += 1
                    self.check(stream.read(1) == b"", "Private G RNG evidence has trailing bytes", rng_path)
            except OSError as exc:
                self.issue("Cannot read G RNG evidence", rng_path, str(exc), blocked=True)

    def step(self, base, stem, policy, prompt_id, identity, quality, step, row, historical):
        tag = stem + ":step" + str(step)
        self.counts["trace_steps"] += 1
        self.check(all(row.get(key) == value for key, value in identity.items()) and row.get("step") == step,
                   "Trace condition identity differs", tag)
        prefix = quality["input_ids"] + quality["raw_new_ids"][:step]
        self.check(row.get("prefix_ids") == prefix and row.get("input_length") == len(prefix)
                   and row.get("prefix_ids_sha256") == hashlib.sha256(json_bytes(prefix)).hexdigest(),
                   "Full prefix/token/hash differs", tag)
        self.check(row.get("selected_token_id") == quality["raw_new_ids"][step], "Selected token differs from saved generation", tag)
        self.check(row.get("full_logits_shape") == [1, len(prefix), VOCAB] and row.get("dtype") == "torch.float32"
                   and row.get("cache_none") is True and row.get("num_steps") == 8 and row.get("all_logits_finite") is True
                   and valid_digest(row.get("full_logits"), len(prefix) * LAST_BYTES)
                   and valid_digest(row.get("last_logits"), LAST_BYTES), "Logit trace metadata/digests differ", tag)
        observation_path = base / "public" / (stem + "_step%02d_observation.json" % step)
        observation = self.load(observation_path)
        if isinstance(observation, dict):
            self.check(set(observation) == set(OBSERVATION_KEYS)
                       and all(observation.get(key) == row.get(key) for key in OBSERVATION_KEYS),
                       "Pre-selection observation differs from final trace", observation_path)
            self.counts["observation_rows"] += 1
        last_name = stem + "_step%02d_last.bin" % step
        last_path = base / "private" / last_name
        self.check(row.get("last_logits_file") == "private/" + last_name, "Last-vector relative path differs", tag)
        try:
            raw = last_path.read_bytes()
            bytes_ok = self.check(digest_bytes(raw) == row["last_logits"] and len(raw) == LAST_BYTES,
                                  "Last-vector raw hash/length differs", last_path)
            if len(raw) == LAST_BYTES:
                # IEEE-754 FP32 exponent 255 encodes Inf/NaN. This is a byte
                # classification audit, not a forward or numerical re-evaluation.
                finite = all((bits[0] & 0x7f800000) != 0x7f800000 for bits in struct.iter_unpack("<I", raw))
                self.check(finite, "Raw last vector contains nonfinite FP32 values", last_path)
                if bytes_ok and finite:
                    self.counts["last_vectors_verified"] += 1
                if policy == "G" and finite:
                    maximum = max(enumerate(value[0] for value in struct.iter_unpack("<f", raw)), key=lambda pair: pair[1])[0]
                    self.check(maximum == row["selected_token_id"], "Greedy argmax independently differs from raw last vector", tag)
        except OSError as exc:
            self.issue("Cannot read raw last vector", last_path, str(exc), blocked=True)
        if policy == "G" and historical is not None and step < len(historical):
            old = historical[step]
            keys = ("prefix_ids_sha256", "input_length", "full_logits_shape", "dtype", "cache_none", "num_steps", "full_logits", "last_logits")
            self.check(all(row.get(key) == old.get(key) for key in keys)
                       and row.get("selected_token_id") == old.get("expected_greedy_token_id"),
                       "G trace/full-logit SHA differs from history", tag)
            old_path = self.history / "private" / ("pass1_prompt%02d_step%02d_last.bin" % (prompt_id, step))
            if self.byte_equal(last_path, old_path, LAST_BYTES):
                self.counts["greedy_history_byte_pairs"] += 1
        elif policy != "G" and step == 0:
            greedy = self.greedy_traces.get(prompt_id, [])
            self.check(bool(greedy) and row["full_logits"] == greedy[0]["full_logits"],
                       "Sampling initial full logits differ from G", tag)
            control = base / "private" / ("G_panel0_prompt%02d_step00_last.bin" % prompt_id)
            if self.byte_equal(last_path, control, LAST_BYTES):
                self.counts["sampling_initial_byte_pairs"] += 1
        for key in RNG_KEYS:
            value = row.get(key)
            self.check(value is None if policy == "G" and key.startswith("sampler") else valid_digest(value),
                       "Invalid RNG trace digest", tag, key)
        self.check(row.get("default_rng_after_forward") == row.get("default_rng_before_selector") == row.get("default_rng_after_selector"),
                   "Observation/selector consumed default model RNG", tag)
        self.check(row.get("sampler_rng_before_forward") == row.get("sampler_rng_after_forward") == row.get("sampler_rng_before_selector"),
                   "Model/observer consumed sampling RNG", tag)
        if step:
            previous = self._active_trace_previous.get(stem)
            if previous is not None:
                self.check(row["default_rng_before_forward"] == previous["default_rng_after_selector"]
                           and row["sampler_rng_before_forward"] == previous["sampler_rng_after_selector"],
                           "RNG stream discontinuity between steps", tag)
        self._active_trace_previous[stem] = row
        if policy != "G":
            greedy = self.greedy_traces.get(prompt_id, [])
            self.check(step < len(greedy) and all(row.get(key) == greedy[step].get(key) for key in
                       ("default_rng_before_forward", "default_rng_after_forward")),
                       "Sampling model RNG trajectory differs from G", tag)
            self.check(row.get("sampler_rng_before_selector") != row.get("sampler_rng_after_selector"),
                       "Recorded sampling RNG did not advance", tag)
            if step == 0:
                identity_key = (identity["panel"], prompt_id)
                if policy == "S":
                    self.sampler_initial[identity_key] = row.get("sampler_rng_before_forward")
                else:
                    self.check(row.get("sampler_rng_before_forward") == self.sampler_initial.get(identity_key),
                               "S/P shared sampling seed has different initial RNG evidence", tag)
        selection = row.get("selection", {})
        if policy == "G":
            expected = {"method": "argmax", "temperature": 1.0, "top_p": None, "filtered_tokens": 0, "sampler_used": False}
            self.check(selection == expected, "Greedy selector settings differ", tag)
        else:
            total = selection.get("probability_sum_fp64")
            removed = selection.get("filtered_tokens")
            self.check(selection.get("method") == "multinomial" and selection.get("sampler_used") is True
                       and selection.get("temperature") == (1.0 if policy == "S" else 0.8)
                       and selection.get("top_p") == (None if policy == "S" else 0.9)
                       and type(removed) is int and 0 <= removed < VOCAB
                       and selection.get("retained_tokens") == VOCAB - removed
                       and (policy != "S" or removed == 0)
                       and type(total) in (int, float) and math.isfinite(total) and abs(total - 1.0) <= 1e-6
                       and valid_digest(selection.get("probabilities"), LAST_BYTES),
                       "Sampling probability/selector metadata differs", tag)

    def execute(self):
        self._active_trace_previous = {}
        for name, callback in (("manifest", self.manifest), ("statuses", self.statuses),
                               ("state and invariance", self.state_and_invariance), ("conditions", self.conditions)):
            self.section(name, callback)
        complete = (self.sealed and self.complete_counts and self.summary.get("engineering_status") == "PASS"
                    and self.summary.get("gates") == {"D%d" % i: "PASS" for i in range(5)})
        status = "FAIL" if self.failures else "BLOCKED" if self.blockers or not complete else "PASS"
        panels = {}
        for policy, numbers in PANELS.items():
            panels[policy] = {}
            for panel in numbers:
                rows = [row for row in self.generations if row.get("policy") == policy and row.get("panel") == panel]
                panels[policy][str(panel)] = {"available": len(rows), "expected": 12,
                    "automatic_passes": sum(row.get("quality", {}).get("auto", {}).get("passed") is True for row in rows),
                    "automatic_pass_ids": [row["prompt_id"] for row in rows if row.get("quality", {}).get("auto", {}).get("passed") is True],
                    "joint_quality": "NOT ASSESSED"}
        return {"Purpose": "Independent post-run read-only decoding evidence audit",
                "Environment": {"python": sys.version, "libraries": "standard library only"},
                "Input": {"run": str(self.root), "history": str(self.history)},
                "Expected": "All immutable evidence complete, hashes/bytes/controls consistent; no model execution",
                "Actual": {"recorded_engineering_status": self.summary.get("engineering_status"),
                           "recorded_gates": self.summary.get("gates"), "complete": complete,
                           "full_acceptance_established": complete and status == "PASS",
                           "coverage_status": "COMPLETE" if complete else "PARTIAL / BLOCKED",
                           "sealed_run_file_integrity": self.sealed_run_file_integrity,
                           "expected_identity": self.expected_identity,
                           "recorded_stop_reason": self.summary.get("stop_reason"),
                           "worker_stop": self.worker.get("stop"),
                           "counts": dict(self.counts), "check_statuses": dict(self.check_statuses),
                           "automatic_panels": panels},
                "Status": status, "utc": datetime.now(timezone.utc).isoformat(),
                "failures": self.failures, "blockers": self.blockers,
                "limitations": ["No model, sampling, tokenizer decoding or original weight deserialization is rerun.",
                    "Full logits arrays are not retained: their hashes are checked across trace/observation/history, not independently recomputed.",
                    "All retained last vectors are independently hashed and scanned for nonfinite FP32 values; G and first-step pairs are compared as actual bytes.",
                    "Sampling probabilities and RNG transitions are recorded evidence; multinomial outcomes are not replayed.",
                    "G RNG raw blocks are rehashed; S/P RNG trajectory comparisons use their saved digests because their raw RNG states were not retained.",
                    "Token repetition/EOS rules are recomputed; text rules use stored decoded strings, not a fresh tokenizer decode.",
                    "State rows are checked for internal completeness and before/after hash identity; model tensors are not reloaded.",
                    "Protected file bytes/tree membership are re-read; Git-state equality is audited from saved before/after records, without running Git.",
                    "Check schemas/statuses are enumerated; their exact execution ordering is not independently reconstructed.",
                    "Engineering audit PASS is not language-quality or scientific superiority PASS."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True)
    parser.add_argument("--history", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--expected-implementation", required=True)
    parser.add_argument("--expected-execution", required=True)
    parser.add_argument("--expected-branch", required=True)
    args = parser.parse_args()
    root, history, output = Path(args.run).resolve(), Path(args.history).resolve(), Path(args.output).resolve()
    if output.is_relative_to(root) or output.is_relative_to(history.parent.parent):
        raise ValueError("Audit output must be outside immutable run and history")
    if output.exists():
        raise FileExistsError("Audit output already exists; no overwrite")
    for value in (args.expected_implementation, args.expected_execution):
        if len(value) != 40 or any(char not in "0123456789abcdef" for char in value):
            raise ValueError("Expected commit identities must be full 40-character lowercase SHA values")
    expected_identity = {"experiment": "MYTHOS-DECODE-CONTROL-V1",
                         "implementation_commit": args.expected_implementation,
                         "execution_head": args.expected_execution, "branch": args.expected_branch}
    result = Audit(root, history, expected_identity).execute()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as stream:
        stream.write((json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8"))
    compact = {"status": result["Status"], "complete": result["Actual"]["complete"],
               "coverage_status": result["Actual"]["coverage_status"],
               "sealed_run_file_integrity": result["Actual"]["sealed_run_file_integrity"],
               "recorded_gates": result["Actual"]["recorded_gates"],
               "worker_stop": result["Actual"]["worker_stop"],
               "counts": result["Actual"]["counts"], "check_statuses": result["Actual"]["check_statuses"],
               "automatic_panels": result["Actual"]["automatic_panels"],
               "failure_count": len(result["failures"]), "blocker_count": len(result["blockers"]), "output": str(output)}
    print(json.dumps(compact, ensure_ascii=False, allow_nan=False), flush=True)
    return 0 if result["Status"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
