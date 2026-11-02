"""Source MoE mathematics only, with its explicit FP32 routing score casts."""
from pathlib import Path
import copy
import io
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from shared_helpers import Case, config, main
import torch
from torch.nn import functional as F

ATOL, RTOL = 2e-6, 2e-5


def expert_reference(expert, x):
    gate = x @ expert.w1.weight.T
    up = x @ expert.w3.weight.T
    return ((gate * torch.sigmoid(gate)) * up) @ expert.w2.weight.T


def gate_reference(gate, x):
    logits = x @ gate.weight.T
    scores = torch.softmax(logits, dim=-1, dtype=torch.float32) if gate.score_func == "softmax" else torch.sigmoid(logits).float()
    # This fixture exercises no bias/groups; ranking uses full argsort rather
    # than the source topk operation. Stable margins are checked separately.
    indices = torch.argsort(scores, dim=-1, descending=True)[:, :gate.n_activated]
    weights = torch.gather(scores, 1, indices)
    if gate.score_func == "sigmoid":
        weights = weights / weights.sum(-1, keepdim=True).clamp(min=1e-9)
    return (weights * gate.route_scale).to(x.dtype), indices, scores


def dense_reference(moe, x):
    flat = x.reshape(-1, x.shape[-1])
    weights, indices, scores = gate_reference(moe.gate, flat)
    all_outputs = torch.stack([expert_reference(expert, flat) for expert in moe.experts], dim=1)
    selected = torch.zeros_like(scores).scatter(1, indices, weights)
    routed = (all_outputs * selected[:, :, None]).sum(1)
    shared = expert_reference(moe.shared_experts, flat)
    return (routed + shared).reshape_as(x), indices, scores


class MoETests(Case):
    SEED = 7201
    PURPOSE = "Tiny CPU mathematical acceptance of frozen OpenMythos MoE source"

    def setup_moe(self, **changes):
        cfg = config(self.source, **changes)
        model = self.source.DeepSeekMoE(cfg).float().train()
        # Stable top2=experts0/1; no ties, no dependence on random routing luck.
        with torch.no_grad():
            model.gate.weight.zero_()
            model.gate.weight[:, 0] = torch.tensor([.5, .2, -.3, -.7])
        x = torch.randn(1, 5, 16, dtype=torch.float32)
        x[0, :, 0] = torch.linspace(1., 1.4, 5)
        return cfg, model, x.requires_grad_()

    def test_e01_expert_matches_explicit_swiglu(self):
        """Each source expert is w2(SiLU(w1(x))*w3(x))."""
        _, model, x = self.setup_moe()
        for i, expert in enumerate([model.shared_experts, *model.experts]):
            self.close(expert(x), expert_reference(expert, x), "SwiGLU " + str(i), ATOL, RTOL)

    def test_e02_softmax_and_sigmoid_weight_semantics(self):
        """Softmax selected weights stay unnormalised; sigmoid weights normalise then scale."""
        for score in ("softmax", "sigmoid"):
            _, model, x = self.setup_moe(moe_score_func=score, moe_route_scale=1.3)
            flat = x.reshape(-1, 16)
            weights, indices, scores = model.gate(flat)
            rw, ri, rs = gate_reference(model.gate, flat)
            self.exact(indices, ri, score + " selected indices")
            self.close(weights, rw, score + " selected weights", ATOL, RTOL)
            self.close(scores, rs, score + " original scores", ATOL, RTOL)
            self.assertEqual(scores.dtype, torch.float32)
            sorted_scores = scores.sort(descending=True).values
            margin = float((sorted_scores[:, 1] - sorted_scores[:, 2]).min())
            self.observations.append({"label": score + " top2 boundary margin", "value": margin})
            self.assertGreater(margin, .01)
            if score == "softmax":
                self.assertTrue(bool((weights.sum(-1) < 1.3).all()))
            else:
                self.close(weights.sum(-1), torch.full((5,), 1.3), "sigmoid scale", ATOL, RTOL)

    def test_e03_sparse_dispatch_matches_dense_all_expert_reference(self):
        """Sparse selected-token dispatch equals dense all-expert masked evaluation."""
        _, model, x = self.setup_moe()
        actual, balance = model(x)
        expected, indices, _ = dense_reference(model, x)
        self.close(actual, expected, "sparse vs dense experts", ATOL, RTOL)
        self.assertIsNotNone(balance)
        counts = torch.bincount(indices.flatten(), minlength=4)
        self.assertEqual(counts.tolist(), [5, 5, 0, 0])
        self.observations.append({"label": "routing token counts", "counts": counts.tolist()})

    def test_e04_dispatch_input_router_and_expert_vjp(self):
        """Away from routing ties, input/router/shared/selected expert gradients match dense reference."""
        _, model, x = self.setup_moe()
        other = copy.deepcopy(model)
        xx = x.detach().clone().requires_grad_()
        probe = torch.randn_like(x)
        actual, _ = model(x)
        expected, indices, _ = dense_reference(other, xx)
        (actual * probe).sum().backward()
        (expected * probe).sum().backward()
        self.close(x.grad, xx.grad, "input VJP", ATOL, RTOL)
        self.active(x.grad, "input path")
        for name, p in model.named_parameters():
            reference_grad = dict(other.named_parameters())[name].grad
            actual_grad = torch.zeros_like(p) if p.grad is None else p.grad
            self.assertIsNotNone(reference_grad)
            self.close(actual_grad, reference_grad, name + " VJP", ATOL, RTOL)
            if name.startswith(("shared_experts.", "experts.0.", "experts.1.", "gate.")):
                self.active(actual_grad, name)
            else:
                self.assertEqual(int(torch.count_nonzero(actual_grad)), 0)

    def test_e05_zero_token_experts_not_called_or_differentiated(self):
        """Experts with no assigned tokens are skipped; shared and selected experts execute."""
        _, model, x = self.setup_moe()
        calls = {"shared": 0, **{i: 0 for i in range(4)}}
        def count(label):
            def hook(module, args):
                calls[label] += 1
            return hook
        handles = [model.shared_experts.register_forward_pre_hook(count("shared"))]
        handles += [expert.register_forward_pre_hook(count(i)) for i, expert in enumerate(model.experts)]
        try:
            output, _ = model(x)
            output.square().sum().backward()
            self.assertEqual(calls, {"shared": 1, 0: 1, 1: 1, 2: 0, 3: 0})
            for i in (2, 3):
                self.assertTrue(all(p.grad is None for p in model.experts[i].parameters()))
            self.observations.append({"label": "expert execution counts", "counts": {str(k): v for k, v in calls.items()}})
        finally:
            for handle in handles:
                handle.remove()

    def test_e06_balance_formula_and_gradient_direction(self):
        """Minimising balance loss decreases overloaded expert scores, contrary to source prose."""
        _, model, _ = self.setup_moe()
        logits = torch.tensor([[.5, .2, -.3, -.7]] * 5, requires_grad=True)
        scores = torch.softmax(logits, dim=-1)
        indices = torch.tensor([[0, 1]] * 5)
        actual = model._balance_loss(indices, scores, 5)
        frequency = torch.tensor([2., 2., 0., 0.])
        expected = (scores.mean(0) * frequency).sum()
        self.close(actual, expected, "balance equation", ATOL, RTOL)
        actual.backward()
        expected_grad = scores.detach() * (frequency - (scores.detach() * frequency).sum(-1, keepdim=True)) / 5
        self.close(logits.grad, expected_grad, "balance softmax derivative", ATOL, RTOL)
        self.assertTrue(bool((logits.grad[:, :2] > 0).all()))
        self.assertTrue(bool((logits.grad[:, 2:] < 0).all()))
        changed_scores = torch.softmax(logits.detach() - .01 * logits.grad, dim=-1)
        self.assertLess(float(changed_scores[:, :2].sum(-1).mean()), float(scores[:, :2].sum(-1).mean()))
        self.observations.append({"label": "overloaded total score before/after descent",
            "before": float(scores.detach()[:, :2].sum(-1).mean()), "after": float(changed_scores[:, :2].sum(-1).mean())})

    def test_e07_alpha_applied_once_at_model_loss_boundary(self):
        """Tiny full-model loss is CE plus alpha times mean raw block balance, not alpha squared."""
        cfg = config(self.source, moe_balance_alpha=.07)
        model = self.source.MoDAModel(cfg).float().train()
        ids = torch.tensor([[1, 2, 3, 4, 5]])
        labels = torch.tensor([[2, 3, 4, 5, 6]])
        raw_balances = []
        handles = [block.moe.register_forward_hook(lambda module, args, output: raw_balances.append(output[1]))
                   for block in model.blocks]
        try:
            logits, total = model(ids, labels)
            self.assertEqual(len(raw_balances), 2)
            self.assertTrue(all(x is not None for x in raw_balances))
            ce = F.cross_entropy(logits.reshape(-1, 31), labels.reshape(-1))
            raw = torch.stack(raw_balances).mean()
            expected = ce + .07 * raw
            self.close(total, expected, "alpha once", ATOL, RTOL)
            self.assertGreater(float((total - (ce + .07 ** 2 * raw)).abs()), .01)
            # Verify gradient accounting too, rather than only scalar arithmetic.
            parameter = model.blocks[0].moe.gate.weight
            actual_grad = torch.autograd.grad(total, parameter, retain_graph=True)[0]
            expected_grad = torch.autograd.grad(expected, parameter)[0]
            self.close(actual_grad, expected_grad, "alpha once gradient", ATOL, RTOL)
        finally:
            for handle in handles:
                handle.remove()

    def test_e08_zero_output_is_external_residual_identity(self):
        """Zero expert output projections give exact x+MoE(x) identity and finite gate-only balance gradient."""
        _, model, x = self.setup_moe()
        with torch.no_grad():
            for expert in [model.shared_experts, *model.experts]:
                expert.w2.weight.zero_()
        output, balance = model(x)
        self.exact(x + output, x, "external MoE residual identity")
        self.assertTrue(bool(torch.isfinite(balance)))
        balance.backward()
        self.active(model.gate.weight.grad, "balance-only router gradient")

    def test_e09_eval_balance_none_and_state_reload_exact(self):
        """Eval omits auxiliary balance; new-instance state reload preserves MoE outputs exactly."""
        cfg, model, x = self.setup_moe()
        model.eval()
        before, balance = model(x)
        self.assertIsNone(balance)
        model(x.detach() + .2)
        repeated, _ = model(x)
        self.exact(repeated, before, "repeat after independent MoE input")
        stream = io.BytesIO()
        torch.save(model.state_dict(), stream)
        stream.seek(0)
        other = self.source.DeepSeekMoE(cfg).float().eval()
        other.load_state_dict(torch.load(stream, weights_only=True), strict=True)
        self.assertEqual(set(other.state_dict()), set(model.state_dict()))
        for name, value in model.state_dict().items():
            self.exact(other.state_dict()[name], value, "reloaded MoE state " + name)
        after, other_balance = other(x)
        self.assertIsNone(other_balance)
        self.exact(after, before, "MoE new-instance state reload")


if __name__ == "__main__":
    sys.exit(main(MoETests))
