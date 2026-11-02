"""Developer CPU fixtures for source MoDA integration; never loads Parcae weights."""
import argparse
import copy
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import subprocess
import struct
import hashlib
import unittest
from unittest import mock
from types import SimpleNamespace
import torch
from torch import nn
ROOT = Path(__file__).resolve().parent


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


lib = module("fixture_moda_model", "moda_model.py")
worker = module("fixture_moda_worker", "run_moda.py")
SOURCE = None


class Injection(nn.Module):
    def forward(self, x, embeds):
        return .9 * x + .1 * embeds


class Core(nn.Module):
    def __init__(self):
        super().__init__()
        self.linear = nn.Linear(4, 4, bias=False)
    def forward(self, x):
        return x + .01 * self.linear(torch.tanh(x))


class Toy(nn.Module):
    def __init__(self, steps=32):
        super().__init__()
        self.steps = steps
        self.gradient_checkpointing = False
        self.transformer = nn.ModuleDict({"core_block": nn.ModuleList([Core(), Core()]),
            "wte": nn.Embedding(11, 4), "adapter": Injection()})
        self.head = nn.Linear(4, 11, bias=False)
        self.eval()
        for p in self.parameters():
            p.requires_grad_(False)
    def initialize_state(self, embeds):
        return torch.randn_like(embeds) * .01
    def forward(self, ids, return_logits, num_steps_pair):
        assert return_logits and num_steps_pair.tolist() == [0, 32]
        self._current_input_ids = ids
        embeds = self.transformer.wte(ids)
        x = self.initialize_state(embeds)
        for _ in range(self.steps):
            x = self.transformer.adapter(x, embeds)
            for block in self.transformer.core_block:
                x = block(x)
        return {"logits": self.head(x)}


def rotate_explicit(x, cos, sin):
    half = x.shape[-1] // 2
    return torch.cat((x[..., :half] * cos[..., :half] - x[..., half:] * sin[..., :half],
                      x[..., half:] * cos[..., half:] + x[..., :half] * sin[..., half:]), -1)


def manual_forward(model, banks, ids, seed):
    torch.manual_seed(seed)
    embeds = model.transformer.wte(ids)
    x = model.initialize_state(embeds)
    keys, values = [], []
    cos, sin = banks.rope(ids.shape[1])
    for _ in range(32):
        x = model.transformer.adapter(x, embeds)
        delta = banks.attn(x, keys if banks.arm == "depth" else [], values if banks.arm == "depth" else [], cos, sin)
        x = x + delta
        for block in model.transformer.core_block:
            x = block(x)
        key = (x @ banks.k_write.weight.T).reshape(1, ids.shape[1], 1, banks.head_dim).transpose(1, 2)
        value = (x @ banks.v_write.weight.T).reshape(1, ids.shape[1], 1, banks.head_dim).transpose(1, 2)
        keys.append(rotate_explicit(key, cos, sin))
        values.append(value)
    return model.head(x)


class AdapterTests(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(123)
        self.model = Toy()
        self.runner = lib.NativeFixed32(self.model)
        self.ids = torch.tensor([[1, 2, 3, 4, 5]])
    def banks(self, arm="depth", seed=4101):
        return lib.MoDAResidual(arm, SOURCE, width=4, head_dim=2, seed=seed)

    def test_matched_parameter_budget_and_frozen_features(self):
        for arm in ("shared", "depth"):
            banks = lib.MoDAResidual(arm, SOURCE)
            self.assertEqual(sum(p.numel() for p in banks.trainable_parameters()), 12288)
            self.assertEqual(sum(p.numel() for p in banks.parameters()), 73728)
            self.assertEqual(sum(p.numel() for p in banks.parameters() if not p.requires_grad), 61440)
            self.assertEqual(int(torch.count_nonzero(banks.attn.o_proj.weight)), 0)
            self.assertEqual(len(banks.feature_hashes()), 8)
            self.assertIn("buffer.rope._cos", banks.feature_hashes())

    def test_feature_initialization_paired_and_global_rng_preserved(self):
        before = lib.raw(torch.get_rng_state())
        for seed in (4101, 4202):
            shared, depth = self.banks("shared", seed), self.banks("depth", seed)
            self.assertEqual(lib.state_hashes(shared), lib.state_hashes(depth))
            self.assertEqual(shared.feature_hashes(), depth.feature_hashes())
        self.assertEqual(before, lib.raw(torch.get_rng_state()))
        self.assertNotEqual(self.banks(seed=4101).feature_hashes(), self.banks(seed=4202).feature_hashes())

    def test_zero_output_native_bitwise_all_four_initializations(self):
        native, observer = self.runner.forward(self.ids, 5101)
        for seed in (4101, 4202):
            for arm in ("shared", "depth"):
                actual, observed = self.runner.forward(self.ids, 5101, self.banks(arm, seed))
                self.assertEqual(lib.raw(actual), lib.raw(native))
                self.assertEqual(observed, observer)
                self.assertEqual(self.runner.last_branch["writer_calls"], 32)
                self.assertEqual(self.runner.last_branch["read_lengths"], list(range(32)) if arm == "depth" else [0] * 32)

    def test_hook_matches_manual32_forward_and_gradient(self):
        for arm in ("shared", "depth"):
            banks = self.banks(arm)
            with torch.no_grad():
                banks.attn.o_proj.weight.copy_(torch.arange(8).reshape(4, 2) * .0005)
            other = copy.deepcopy(banks)
            actual, _ = self.runner.forward(self.ids, 5101, banks, training=True)
            expected = manual_forward(self.model, other, self.ids, 5101)
            torch.testing.assert_close(actual, expected, rtol=1e-5, atol=1e-6)
            actual.square().mean().backward()
            expected.square().mean().backward()
            torch.testing.assert_close(banks.attn.o_proj.weight.grad, other.attn.o_proj.weight.grad, rtol=1e-5, atol=1e-6)

    def test_full32_output_contributions_reconstruct_trainable_gradient(self):
        for arm in ("shared", "depth"):
            banks = self.banks(arm)
            values, _ = self.runner.forward(self.ids, 5101, banks, training=True)
            values.square().mean().backward()
            contributions = lib.depth_output_contributions(banks, self.runner.depth_deltas, self.runner.depth_features)
            self.assertTrue(all(lib.finite(x) and bool(x.abs().max() > 0) for x in contributions))
            torch.testing.assert_close(torch.stack(contributions).sum(0), banks.attn.o_proj.weight.grad, rtol=1e-5, atol=1e-6)
            self.assertTrue(all(p.grad is None for p in self.model.parameters()))
            self.assertTrue(all(p.grad is None for p in banks.parameters() if not p.requires_grad))

    def test_history_gradients_initial_zero_then_active_and_final_write_unused(self):
        banks = self.banks()
        before = banks.feature_hashes()
        optimizer = torch.optim.AdamW(banks.trainable_parameters(), lr=.001, weight_decay=0., foreach=False)
        values, _ = self.runner.forward(self.ids, 5101, banks, training=True)
        self.assertTrue(self.runner.depth_keys[0].requires_grad)
        self.assertTrue(self.runner.depth_values[0].requires_grad)
        values.square().mean().backward()
        first = worker.history_gradient_record(lib, self.runner)
        for kind in ("key", "value"):
            self.assertEqual(first[kind]["present"], [True] * 31 + [False])
            self.assertEqual(first[kind]["norms"], [0.] * 31 + [None])
        optimizer.step()
        optimizer.zero_grad(set_to_none=True)
        values, _ = self.runner.forward(self.ids, 5101, banks, training=True)
        values.square().mean().backward()
        second = worker.history_gradient_record(lib, self.runner)
        for kind in ("key", "value"):
            self.assertEqual(second[kind]["present"], [True] * 31 + [False])
            self.assertTrue(any(x is not None and x > 0 for x in second[kind]["norms"]))
        self.assertEqual(before, banks.feature_hashes())

    def test_shared_writers_computed_but_have_no_gradient_consumers(self):
        banks = self.banks("shared")
        with torch.no_grad():
            banks.attn.o_proj.weight.fill_(.01)
        values, _ = self.runner.forward(self.ids, 5101, banks, training=True)
        values.square().mean().backward()
        record = worker.history_gradient_record(lib, self.runner)
        for kind in ("key", "value"):
            self.assertEqual(record[kind]["present"], [False] * 32)
            self.assertEqual(record[kind]["norms"], [None] * 32)
        self.assertEqual(self.runner.last_branch["writer_calls"], 32)

    def test_new_reader_uses_history_only_in_depth_arm(self):
        x = torch.randn(1, 5, 4)
        key, val = torch.randn(1, 1, 5, 2), torch.randn(1, 1, 5, 2)
        for arm in ("shared", "depth"):
            banks = self.banks(arm)
            with torch.no_grad():
                banks.attn.o_proj.weight.fill_(.02)
            before, _ = banks.read(x, [key], [val])
            after, _ = banks.read(x, [key], [val + 2])
            if arm == "depth":
                self.assertFalse(torch.equal(before, after))
            else:
                self.assertEqual(lib.raw(before), lib.raw(after))

    def test_history_future_positions_do_not_change_prefix(self):
        x = torch.randn(1, 5, 4)
        key, val = torch.randn(1, 1, 5, 2), torch.randn(1, 1, 5, 2)
        banks = self.banks()
        with torch.no_grad():
            banks.attn.o_proj.weight.fill_(.02)
        before, _ = banks.read(x, [key], [val])
        changed_x, changed_key, changed_val = x.clone(), key.clone(), val.clone()
        changed_x[:, 3:] += 5
        changed_key[:, :, 3:] += 3
        changed_val[:, :, 3:] += 7
        after, _ = banks.read(changed_x, [changed_key], [changed_val])
        torch.testing.assert_close(before[:, :3], after[:, :3], rtol=1e-5, atol=1e-6)
        self.assertFalse(torch.equal(before[:, 3:], after[:, 3:]))

    def test_repeat_resets_all_history_and_restores_instance_attributes(self):
        banks = self.banks()
        original = self.model.initialize_state
        self.model.initialize_state = original
        self.model._current_input_ids = "sentinel"
        a, am = self.runner.forward(self.ids, 5101, banks)
        old_keys = self.runner.depth_keys
        b, bm = self.runner.forward(self.ids, 5101, banks)
        self.assertEqual(lib.raw(a), lib.raw(b))
        self.assertEqual(am, bm)
        self.assertIsNot(old_keys, self.runner.depth_keys)
        self.assertIs(self.model.initialize_state, original)
        self.assertEqual(self.model._current_input_ids, "sentinel")

    def test_error_removes_hooks_and_history(self):
        for steps in (31, 33):
            self.model.steps = steps
            with self.assertRaises(RuntimeError):
                self.runner.forward(self.ids, 5101, self.banks(), training=True)
            self.assertTrue(all(not m._forward_hooks and not m._forward_pre_hooks for m in self.model.modules()))
            self.assertEqual(self.runner.depth_keys, [])
            self.assertEqual(self.runner.depth_deltas, [])
            self.assertNotIn("initialize_state", self.model.__dict__)

    def test_nonfinite_output_fails_without_hook_leak(self):
        banks = self.banks()
        with torch.no_grad():
            banks.attn.o_proj.weight.fill_(float("nan"))
        with self.assertRaises(RuntimeError):
            self.runner.forward(self.ids, 5101, banks)
        self.assertTrue(all(not m._forward_hooks and not m._forward_pre_hooks for m in self.model.modules()))
        self.assertTrue(all(not m._forward_hooks and not m._forward_pre_hooks for m in banks.modules()))

    def test_checkpoint_regenerates_features_and_reloads_exact(self):
        banks = self.banks()
        with torch.no_grad():
            banks.attn.o_proj.weight.fill_(.01)
        before, observed = self.runner.forward(self.ids, 5101, banks)
        stream = io.BytesIO()
        torch.save(banks.state_dict(), stream)
        stream.seek(0)
        other = self.banks()
        self.assertEqual(other.feature_hashes(), banks.feature_hashes())
        other.load_state_dict(torch.load(stream, weights_only=True), strict=True)
        after, current = self.runner.forward(self.ids, 5101, other)
        self.assertEqual(lib.raw(before), lib.raw(after))
        self.assertEqual(observed, current)
        self.assertEqual(lib.state_hashes(banks), lib.state_hashes(other))

    def test_mode_base_grad_checkpoint_and_preexisting_hook_rejected(self):
        self.model.gradient_checkpointing = True
        with self.assertRaises(ValueError):
            lib.NativeFixed32(self.model)
        self.model.gradient_checkpointing = False
        self.model.train()
        with self.assertRaises(ValueError):
            lib.NativeFixed32(self.model)
        self.model.eval()
        next(self.model.parameters()).requires_grad_(True)
        with self.assertRaises(ValueError):
            lib.NativeFixed32(self.model)
        next(self.model.parameters()).requires_grad_(False)
        handle = self.model.head.register_forward_hook(lambda m, a, o: o)
        try:
            with self.assertRaises(RuntimeError):
                self.runner.forward(self.ids, 5101)
        finally:
            handle.remove()

    def test_invalid_shapes_and_missing_contributions_rejected(self):
        with self.assertRaises(ValueError):
            self.runner.forward(self.ids.float(), 5101)
        with self.assertRaises(ValueError):
            self.runner.forward(torch.ones(1, 129, dtype=torch.long), 5101)
        with self.assertRaises(ValueError):
            lib.MoDAResidual("unknown", SOURCE)
        with self.assertRaises(RuntimeError):
            lib.depth_output_contributions(self.banks(), [], [])

    def test_optimizer_state_and_four_checkpoint_byte_budget(self):
        sizes = []
        for seed in (4101, 4202):
            for arm in ("shared", "depth"):
                banks = lib.MoDAResidual(arm, SOURCE, seed=seed)
                optimizer = torch.optim.AdamW(banks.trainable_parameters(), lr=.001, weight_decay=0., foreach=False)
                banks.attn.o_proj.weight.grad = torch.ones_like(banks.attn.o_proj.weight)
                optimizer.step()
                self.assertTrue(worker.optimizer_state_valid(torch, optimizer.state_dict(), steps=1))
                optimizer.state[banks.attn.o_proj.weight]["step"].fill_(32)
                checkpoint = {"arm": arm, "train_seed": seed, "freeze_commit": "0" * 40,
                    "inputs_sha256": "0" * 64, "steps": 32, "state_dict": banks.state_dict(),
                    "optimizer": optimizer.state_dict(), "rng_state": torch.get_rng_state(), "head_dim": 16,
                    "rope_theta": 10000., "source_sha256": lib.SOURCE_SHA256}
                stream = io.BytesIO()
                torch.save(checkpoint, stream)
                sizes.append(len(stream.getvalue()))
        self.assertLess(sum(sizes), 2 * 1024 ** 2)
        type(self).checkpoint_sizes = sizes

    def test_disk_reserve_no_overwrite(self):
        payload, reserve = b"fixture raw", 256 * 1024 ** 2
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pending_row_000.bin"
            with mock.patch.object(worker.shutil, "disk_usage", return_value=SimpleNamespace(free=reserve)):
                with self.assertRaises(worker.Stop) as caught:
                    worker.save_raw_logits(path, payload)
                self.assertEqual(caught.exception.status, "BLOCKED")
                self.assertFalse(path.exists())
            with mock.patch.object(worker.shutil, "disk_usage", return_value=SimpleNamespace(free=reserve + len(payload))):
                worker.save_raw_logits(path, payload)
                with self.assertRaises(FileExistsError):
                    worker.save_raw_logits(path, payload)
                self.assertEqual(path.read_bytes(), payload)

    def test_remaining_budget_blocks_external_consumption_at_exact_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / "worker/private").mkdir(parents=True)
            raw = root / "worker/private/pending_row_000.bin"
            raw.write_bytes(b"rawbytes")
            (root / "metadata.json").write_bytes(b"metadata")
            remaining = worker.RAW_BUDGET + worker.METADATA_BUDGET - 16
            with mock.patch.object(worker, "BUDGET_ROOT", root), mock.patch.object(worker, "BUDGET_SALVAGE", False), mock.patch.object(worker, "BUDGET_TRIGGER", None):
                # Enough for a single8MiB write+reserve is deliberately NOT
                # enough for the whole declared remaining allocation.
                with mock.patch.object(worker.shutil, "disk_usage", return_value=SimpleNamespace(free=worker.DISK_RESERVE + 8388608)):
                    with self.assertRaises(worker.Stop) as caught:
                        worker.budget_guard(raw, 1)
                    self.assertEqual(caught.exception.status, "BLOCKED")
                    self.assertEqual(worker.BUDGET_TRIGGER["remaining_allocation_bytes"], remaining)
                with mock.patch.object(worker.shutil, "disk_usage", return_value=SimpleNamespace(free=remaining + worker.DISK_RESERVE - 1)):
                    with self.assertRaises(worker.Stop):
                        worker.budget_guard()
                with mock.patch.object(worker.shutil, "disk_usage", return_value=SimpleNamespace(free=remaining + worker.DISK_RESERVE)):
                    observed = worker.budget_guard(root / "new.json", 1)
                    self.assertEqual(observed["raw_bytes"], 8)
                    self.assertEqual(observed["metadata_bytes"], 8)

    def test_remaining_budget_enforces_each_category_and_confines_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / "worker/private").mkdir(parents=True)
            raw = root / "worker/private/pending_row_000.bin"
            raw.write_bytes(bytes(10))
            (root / "metadata").write_bytes(bytes(60))
            with mock.patch.object(worker, "BUDGET_ROOT", root), mock.patch.object(worker, "BUDGET_SALVAGE", False), mock.patch.object(worker, "BUDGET_TRIGGER", None), \
                 mock.patch.object(worker, "RAW_BUDGET", 40), mock.patch.object(worker, "METADATA_BUDGET", 64), mock.patch.object(worker, "DISK_RESERVE", 256), \
                 mock.patch.object(worker.shutil, "disk_usage", return_value=SimpleNamespace(free=1000)):
                worker.budget_guard(root / "new.json", 4)
                for target, amount in ((root / "new.json", 5), (raw, 31), (root.parent / "outside.json", 1)):
                    with self.assertRaises(worker.Stop):
                        worker.budget_guard(target, amount)

    def test_budget_salvage_only_writes_bounded_metadata_never_resumes_model(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / "worker/private").mkdir(parents=True)
            with mock.patch.object(worker, "BUDGET_ROOT", root), mock.patch.object(worker, "BUDGET_SALVAGE", True), mock.patch.object(worker, "BUDGET_TRIGGER", {"reason": "fixture"}), \
                 mock.patch.object(worker.shutil, "disk_usage", return_value=SimpleNamespace(free=64)):
                observed = worker.budget_guard(root / "error.json", 32)
                self.assertTrue(observed["salvage"])
                self.assertEqual(observed["required_free_bytes"], 32)
                with self.assertRaises(worker.Stop):
                    worker.budget_guard(root / "error.json", 65)
                with self.assertRaises(worker.Stop):
                    worker.budget_guard(root / "worker/private/pending_row_000.bin", 1)
                run = object.__new__(worker.Run)
                with self.assertRaises(worker.Stop):
                    run.call(None, None, 5101)

    def test_linux_peak_rss_kib_is_reported_as_bytes(self):
        fake = SimpleNamespace(RUSAGE_SELF=0, getrusage=lambda _: SimpleNamespace(ru_maxrss=12345))
        with mock.patch.object(worker.platform, "system", return_value="Linux"), mock.patch.dict(sys.modules, {"resource": fake}):
            self.assertEqual(worker.peak_rss_bytes(), 12345 * 1024)

    def pending_fixture(self, directory):
        out = Path(directory).resolve()
        (out / "private").mkdir()
        (out / "public/rows").mkdir(parents=True)
        (out / "public/row_audits").mkdir()
        raw = out / "private/pending_row_000.bin"
        raw.write_bytes(bytes(8388608))
        raw_pin = worker.info(raw)
        identity = {"arm": "depth", "train_seed": 4101, "eval_seed": 5202, "article_id": "fixture", "article_index": 0}
        row = out / "public/rows/row_000.json"
        receipt = out / "public/row_audits/row_000.json"
        worker.save(row, {"raw_path": str(raw), "logits_sha256": raw_pin["sha256"], "retention": "audited_then_discarded"})
        worker.save(receipt, {"Status": "PASS", "Input": {"identity": identity, "row_input": worker.info(row)},
                              "Actual": {"raw": raw_pin}})
        return out, raw, raw_pin, row, receipt, identity

    def test_temporary_delete_requires_bound_receipt_and_exact_own_path(self):
        with tempfile.TemporaryDirectory() as directory:
            out, raw, pin, row, receipt, identity = self.pending_fixture(directory)
            receipt_sha = worker.info(receipt)["sha256"]
            outside = out / "old_evidence.bin"
            outside.write_bytes(b"historical protected bytes")
            for wrong in (outside, out / "private/../private/pending_row_000.bin",
                          out / "private/sentinel_row_000.bin"):
                with self.assertRaises(worker.Stop):
                    worker.discard_audited_pending(out, wrong, 0, pin, row, receipt, receipt_sha, identity)
                self.assertTrue(raw.is_file())
                self.assertEqual(outside.read_bytes(), b"historical protected bytes")
            with mock.patch.object(Path, "is_symlink", return_value=True):
                with self.assertRaises(worker.Stop):
                    worker.discard_audited_pending(out, raw, 0, pin, row, receipt, receipt_sha, identity)
            self.assertTrue(raw.is_file())
            actual = worker.discard_audited_pending(out, raw, 0, pin, row, receipt, receipt_sha, identity)
            self.assertEqual(actual, pin)
            self.assertFalse(raw.exists())
            self.assertTrue(row.exists() and receipt.exists() and outside.exists())

    def test_temporary_tamper_or_unpassed_receipt_is_preserved(self):
        for mode in ("raw_tamper", "receipt_sha", "failed_receipt", "wrong_identity"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                out, raw, pin, row, receipt, identity = self.pending_fixture(directory)
                receipt_sha = worker.info(receipt)["sha256"]
                if mode == "raw_tamper":
                    with raw.open("r+b") as stream:
                        stream.write(b"changed")
                elif mode == "receipt_sha":
                    receipt_sha = "0" * 64
                else:
                    value = worker.load(receipt)
                    if mode == "failed_receipt":
                        value["Status"] = "FAIL"
                    else:
                        value["Input"]["identity"]["eval_seed"] = 9999
                    receipt.write_text(json.dumps(value), encoding="utf-8")
                    receipt_sha = worker.info(receipt)["sha256"]
                with self.assertRaises(worker.Stop):
                    worker.discard_audited_pending(out, raw, 0, pin, row, receipt, receipt_sha, identity)
                self.assertTrue(raw.is_file())

    def test_real_numpy_row_audit_to_owned_disposal_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory).resolve()
            (out / "private").mkdir()
            (out / "public/rows").mkdir(parents=True)
            (out / "public/row_audits").mkdir()
            data = {"eval": [{"id": "article" + str(i), "tokens": list(range(i, i + 129))} for i in range(16)]}
            data_path, spec_path = out / "fixture_inputs.json", out / "fixture_spec.json"
            worker.save(data_path, data)
            worker.save(spec_path, {"data_path": str(data_path), "inputs_sha256": worker.info(data_path)["sha256"], "output": str(out)})
            targets = data["eval"][1]["tokens"][65:129]
            target = torch.tensor(targets, dtype=torch.long)
            values = torch.zeros(64, 32768, dtype=torch.float32)
            values[torch.arange(64), target] = 1.
            values[torch.arange(64), target + 1] = 2.
            raw_path = out / "private/pending_row_000.bin"
            raw_path.write_bytes(lib.raw(values))
            raw_pin = worker.info(raw_path)
            double = values.double()
            peak = double.max(-1).values
            nll = peak - double.gather(1, target[:, None]).squeeze(1) + torch.exp(double - peak[:, None]).sum(-1).log()
            identity = {"arm": "depth", "train_seed": 4101, "eval_seed": 5101, "article_id": "article1", "article_index": 1}
            observer = {"h0_sha256": "a" * 64, "rng_before_sha256": "b" * 64, "rng_after_sha256": "c" * 64, "seed": 5101}
            row = {**identity, "raw_path": str(raw_path), "logits_sha256": raw_pin["sha256"],
                "shape": [64, 32768], "dtype": "float32-le", "retention": "audited_then_discarded",
                "targets_sha256": hashlib.sha256(struct.pack("<64q", *targets)).hexdigest(),
                "h0_sha256": observer["h0_sha256"], "observer": observer,
                "worker_per_token": {"nll": nll.tolist(), "predictions": values.argmax(-1).tolist()},
                **lib.score(values.unsqueeze(0), target, start=0)}
            row_path, receipt_path = out / "public/rows/row_000.json", out / "public/row_audits/row_000.json"
            worker.save(row_path, row)
            completed = subprocess.run([sys.executable, "-I", "-B", str(ROOT / "audit_row.py"),
                "--development", "--spec", str(spec_path), "--row", str(row_path), "--output", str(receipt_path)],
                capture_output=True, text=True, timeout=60)
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr + (receipt_path.read_text() if receipt_path.exists() else ""))
            receipt = worker.load(receipt_path)
            self.assertEqual(receipt["Status"], "PASS")
            self.assertIs(receipt["Environment"]["development_only"], True)
            self.assertEqual(receipt["Input"]["identity"], identity)
            self.assertEqual(receipt["Actual"]["raw"], raw_pin)
            self.assertEqual(receipt["Input"]["row_input"], worker.info(row_path))
            worker.discard_audited_pending(out, raw_path, 0, raw_pin, row_path, receipt_path,
                                          worker.info(receipt_path)["sha256"], identity)
            self.assertFalse(raw_path.exists())
            self.assertTrue(row_path.exists() and receipt_path.exists())


def test_ids(suite):
    return [name for item in suite for name in (test_ids(item) if isinstance(item, unittest.TestSuite) else [item.id()])]


def main():
    global SOURCE
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()
    SOURCE = lib.load_source(args.source)
    torch.set_num_threads(1)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(AdapterTests)
    ids = sorted(test_ids(suite))
    result = unittest.TextTestRunner(verbosity=2, failfast=True).run(suite)
    actual = {"test_ids": ids, "planned": len(ids), "run": result.testsRun,
        "failures": len(result.failures), "errors": len(result.errors), "skipped": len(result.skipped),
        "expected_failures": len(result.expectedFailures), "unexpected_successes": len(result.unexpectedSuccesses),
        "four_adapter_checkpoint_sizes": getattr(AdapterTests, "checkpoint_sizes", [])}
    okay = result.wasSuccessful() and result.testsRun == len(ids) and not result.skipped
    worker.save(args.report, {"Purpose": "Developer CPU toy MoDA source adapter/gradient/retention checks only",
        "Environment": {"torch": str(torch.__version__), "python": sys.version},
        "Input": {"source_sha256": lib.SOURCE_SHA256, "fixtures": "Random tiny fixtures, no real model/weights/data"},
        "Expected": "All planned checks PASS, no skips; fixed forward/gradient tolerance1e-6+1e-5*abs(reference)",
        "Actual": actual, "Status": "PASS" if okay else "FAIL",
        "failures": [(case.id(), text) for case, text in result.failures + result.errors]})
    return 0 if okay else 1


if __name__ == "__main__":
    sys.exit(main())
