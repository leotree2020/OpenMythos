"""Development fixtures only: artificial tensors, never model artifacts or text."""
import contextlib
import importlib.util
import io
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

import torch


SPEC = importlib.util.spec_from_file_location("depth_runner_under_test", Path(__file__).with_name("run_depth_budget.py"))
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class Plus(torch.nn.Module):
    def forward(self, x):
        return x + 0.125


class FakeModel(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.transformer = torch.nn.Module()
        self.transformer.prelude = torch.nn.ModuleList([Plus(), Plus()])
        self.transformer.core_block = torch.nn.ModuleList([Plus(), Plus()])
        self.transformer.coda = torch.nn.ModuleList([Plus(), Plus()])
        self.raise_after_h0 = False

    def initialize_state(self, embeds):
        return torch.randn_like(embeds)

    def forward(self, input_ids, num_steps_pair=None, **kwargs):
        embeds = input_ids.unsqueeze(-1).float()
        for module in self.transformer.prelude:
            embeds = module(embeds)
        x = self.initialize_state(embeds)
        if self.raise_after_h0:
            raise RuntimeError("controlled fixture exception after h0")
        for _ in range(int(num_steps_pair[0])):
            for module in self.transformer.core_block:
                x = module(x + embeds)
        for module in self.transformer.coda:
            x = module(x)
        return {"logits": x.expand(1, 256, 32768).contiguous()}

    def forward_for_generation(self, input_ids, num_steps, **kwargs):
        return {**self.forward(input_ids, num_steps_pair=[num_steps, 0]), "past_key_values": None}


class HelperTests(unittest.TestCase):
    def test_shift_and_score_window_known_binary_distribution(self):
        log_two = float(torch.tensor(math.log(2), dtype=torch.float32))
        logits = torch.tensor([[[0.0, 9.0], [log_two, 0.0], [0.0, 0.0]]])
        token_ids = [0, 1, 0, 1]
        labels = torch.tensor(token_ids[1:], dtype=torch.long)
        values = runner.score_token_metrics(torch, logits, labels, score_start=1)
        expected = [math.log1p(math.exp(-log_two)), math.log(2)]
        self.assertEqual(values["target_logits"].tolist(), [log_two, 0.0])
        self.assertEqual(len(values["nll"]), 2)
        for actual, reference in zip(values["nll"].tolist(), expected):
            self.assertAlmostEqual(actual, reference, places=12)
        self.assertTrue(torch.allclose(values["nll"], values["independent"], atol=1e-10, rtol=0))
        with self.assertRaises(ValueError):
            runner.score_token_metrics(torch, logits, labels[:-1], score_start=1)

    def test_official_prefix_order_and_collision(self):
        value = object()
        normalized = runner.normalize_checkpoint({"module._orig_mod.model.x": value, "module.module.y": value})
        self.assertEqual(set(normalized), {"x", "module.y"})
        self.assertIs(normalized["x"], value)
        for raw in ({"module.x": value, "x": value}, {"": value}, {"model.": value}):
            with self.assertRaises(runner.Stop):
                runner.normalize_checkpoint(raw)

    def test_state_bytes_distinguish_signed_zero_and_key_mismatch(self):
        values = {"p%02d" % index: torch.tensor([0.0]) for index in range(63)}
        class StateOnly:
            def state_dict(self):
                return values
        original = {key: value.clone() for key, value in values.items()}
        snapshot = runner.state_snapshot(torch, StateOnly(), original)
        self.assertEqual(snapshot["state_count"], 63)
        original["p00"][0] = -0.0
        with self.assertRaises(runner.Stop):
            runner.state_snapshot(torch, StateOnly(), original)
        del original["p00"]
        with self.assertRaises(runner.Stop):
            runner.state_snapshot(torch, StateOnly(), original)

    def test_observer_preserves_forward_rng_and_causal_prefix(self):
        with tempfile.TemporaryDirectory() as folder:
            run = runner.Run({}, Path(folder))
            try:
                run.phase = "controls"
                model = FakeModel().eval()
                x = torch.arange(256, dtype=torch.long)[None]
                torch.manual_seed(17)
                rng = torch.get_rng_state().clone()
                with torch.no_grad():
                    bare, _, after_bare = run.forward(torch, model, x, 2, rng, False, control_name="bare")
                    observed, info, after_observed = run.forward(torch, model, x, 2, rng, True, control_name="observed")
                    changed_x = x.clone()
                    changed_x[:, 128:] += 1
                    changed, changed_info, after_changed = run.forward(torch, model, changed_x, 2, rng, True, control_name="changed")
                self.assertEqual(runner.tensor_bytes(bare), runner.tensor_bytes(observed))
                self.assertEqual(after_bare, after_observed)
                self.assertEqual(after_observed, after_changed)
                self.assertEqual(info["block_calls"], {"prelude": 2, "core": 4, "coda": 2})
                self.assertEqual(info["h0_sha256"], changed_info["h0_sha256"])
                self.assertEqual(runner.tensor_bytes(observed[:, :128]), runner.tensor_bytes(changed[:, :128]))
                self.assertNotEqual(runner.tensor_bytes(observed[:, 128:]), runner.tensor_bytes(changed[:, 128:]))
                self.assertEqual(run.total_forwards, 3)
            finally:
                run.rows.close()
                run.checks.close()

    def test_observer_cleanup_on_forward_exception(self):
        with tempfile.TemporaryDirectory() as folder:
            run = runner.Run({}, Path(folder))
            model = FakeModel().eval()
            model.raise_after_h0 = True
            profile = sys.getprofile()
            try:
                with torch.no_grad(), self.assertRaisesRegex(RuntimeError, "controlled fixture"):
                    run.forward(torch, model, torch.zeros((1, 256), dtype=torch.long), 2,
                                torch.get_rng_state().clone(), True, control_name="failing")
                self.assertIs(sys.getprofile(), profile)
                self.assertTrue(all(not module._forward_hooks for module in model.modules()))
                self.assertEqual(run.total_forwards, 1)
                self.assertEqual(run.control_forwards, 1)
                self.assertEqual(run.formal_rows, 0)
            finally:
                run.rows.close()
                run.checks.close()

    def test_terminal_evidence_keeps_first_failure_and_attempt_count(self):
        with tempfile.TemporaryDirectory() as folder:
            parent = Path(folder)
            spec = {key: str(parent / key) for key in
                    ("repo", "upstream", "model_dir", "tokenizer_path", "inputs_path", "source_manifest_path")}
            spec["run_dir"] = str(parent / "new_run")
            path = parent / "spec.json"
            path.write_text(json.dumps(spec))
            def failing(run):
                run.phase = "controls"
                run.total_forwards = run.control_forwards = 1
                raise runner.Stop("FAIL", "fixture first failure", {"expected": "retained"})
            with mock.patch.object(sys, "argv", ["runner", "--spec", str(path)]), \
                    mock.patch.object(runner, "execute", side_effect=failing), \
                    mock.patch.object(runner.signal, "signal"), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(runner.main(), 2)
            evidence = json.loads((Path(spec["run_dir"]) / "completion.json").read_text())
            self.assertEqual(evidence["status"], "FAIL")
            self.assertEqual(evidence["error"]["reason"], "fixture first failure")
            self.assertEqual(evidence["total_forwards"], 1)
            self.assertEqual(evidence["formal_rows"], 0)
            self.assertFalse(evidence["complete_coverage"])


if __name__ == "__main__":
    torch.set_num_threads(2)
    unittest.main()
