"""Source MoDA mathematics only; no Parcae model or pretrained weights."""
from pathlib import Path
import copy
import io
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from shared_helpers import Case, config, main
import torch

ATOL, RTOL = 1e-10, 1e-9


def rotate(value, cos, sin):
    half = value.shape[-1] // 2
    first = value[..., :half] * cos[..., :half] - value[..., half:] * sin[..., :half]
    second = value[..., half:] * cos[..., half:] + value[..., :half] * sin[..., half:]
    return torch.cat((first, second), dim=-1)


def reference(attn, x, keys, values, cos, sin):
    """Per-query enumerated legal keys; no masked dense matrix or einsum path."""
    batch, tokens, _ = x.shape
    hq, hk, d = attn.n_heads_q, attn.n_heads_kv, attn.head_dim
    q = rotate((x @ attn.q_proj.weight.T).reshape(batch, tokens, hq, d).transpose(1, 2), cos, sin)
    k = rotate((x @ attn.k_proj.weight.T).reshape(batch, tokens, hk, d).transpose(1, 2), cos, sin)
    v = (x @ attn.v_proj.weight.T).reshape(batch, tokens, hk, d).transpose(1, 2)
    by_batch = []
    for b in range(batch):
        by_head = []
        for h in range(hq):
            kvhead = h // (hq // hk)
            by_token = []
            for t in range(tokens):
                legal_keys = [k[b, kvhead, u] for u in range(t + 1)] + [z[b, kvhead, t] for z in keys]
                legal_values = [v[b, kvhead, u] for u in range(t + 1)] + [z[b, kvhead, t] for z in values]
                scores = torch.stack([torch.dot(q[b, h, t], key) / d ** .5 for key in legal_keys])
                weights = torch.softmax(scores, dim=0)
                by_token.append(sum((weight * value for weight, value in zip(weights, legal_values)),
                                    torch.zeros(d, dtype=x.dtype)))
            by_head.append(torch.stack(by_token))
        by_batch.append(torch.stack(by_head))
    result = torch.stack(by_batch).transpose(1, 2).reshape(batch, tokens, hq * d)
    return result @ attn.o_proj.weight.T


class MoDATests(Case):
    SEED = 7101
    PURPOSE = "Tiny CPU mathematical acceptance of frozen OpenMythos MoDA source"

    def setup_attention(self, history=2, **changes):
        cfg = config(self.source, **changes)
        attn = self.source.MoDAAttention(cfg).double().eval()
        x = torch.randn(1, 5, cfg.d_model, dtype=torch.float64, requires_grad=True)
        rope = self.source.RotaryEmbedding(cfg.head_dim, 8)
        cos, sin = (v.double() for v in rope(5))
        keys = [torch.randn(1, cfg.n_heads_kv, 5, cfg.head_dim, dtype=torch.float64, requires_grad=True) for _ in range(history)]
        values = [torch.randn_like(key, requires_grad=True) for key in keys]
        return cfg, attn, x, keys, values, cos, sin

    def test_m01_single_softmax_matches_enumerated_legal_keys(self):
        """L=2 joint sequence/depth softmax equals explicit legal-key enumeration."""
        _, attn, x, keys, values, cos, sin = self.setup_attention()
        actual = attn(x, keys, values, cos, sin)
        expected = reference(attn, x, keys, values, cos, sin)
        self.close(actual, expected, "joint attention", ATOL, RTOL)

    def test_m02_query_key_value_history_vjp_matches_reference(self):
        """Q/K/V/O, input and both history depths receive reference-matching VJPs."""
        _, attn, x, keys, values, cos, sin = self.setup_attention()
        other = copy.deepcopy(attn)
        xx = x.detach().clone().requires_grad_()
        kk = [k.detach().clone().requires_grad_() for k in keys]
        vv = [v.detach().clone().requires_grad_() for v in values]
        upstream = torch.randn_like(x)
        (attn(x, keys, values, cos, sin) * upstream).sum().backward()
        (reference(other, xx, kk, vv, cos, sin) * upstream).sum().backward()
        pairs = [(x.grad, xx.grad, "input")]
        pairs += [(k.grad, z.grad, "depth key " + str(i)) for i, (k, z) in enumerate(zip(keys, kk))]
        pairs += [(v.grad, z.grad, "depth value " + str(i)) for i, (v, z) in enumerate(zip(values, vv))]
        pairs += [(p.grad, dict(other.named_parameters())[name].grad, name) for name, p in attn.named_parameters()]
        for actual, expected, label in pairs:
            self.active(actual, label)
            self.close(actual, expected, label + " gradient", ATOL, RTOL)

    def test_m03_empty_depth_sdpa_matches_causal_reference(self):
        """L=0 native SDPA branch equals the causal attention equation."""
        _, attn, x, keys, values, cos, sin = self.setup_attention(history=0)
        self.close(attn(x, keys, values, cos, sin), reference(attn, x, keys, values, cos, sin),
                   "empty history", ATOL, RTOL)

    def test_m04_gqa_head_mapping_and_invalid_group_rejection(self):
        """GQA maps query head h to KV head floor(h/group), including depth axes."""
        _, attn, _, _, _, _, _ = self.setup_attention()
        for shape in ((1, 2, 5, 4), (1, 2, 5, 2, 4)):
            kv = torch.arange(torch.tensor(shape).prod().item(), dtype=torch.float64).reshape(shape)
            expected = torch.stack([kv[:, h // 2] for h in range(4)], dim=1)
            self.exact(attn._expand_kv(kv), expected, "GQA expansion " + str(shape))
        with self.assertRaises(ValueError):
            self.source.MoDAAttention(config(self.source, n_heads_q=3, n_heads_kv=2))

    def test_m05_multilayer_future_tokens_do_not_change_prefix(self):
        """Two source blocks write only prior-layer history and retain causal prefixes."""
        cfg = config(self.source)
        blocks = torch.nn.ModuleList([self.source.MoDABlock(cfg).double().eval() for _ in range(2)])
        cos, sin = (v.double() for v in self.source.RotaryEmbedding(4, 8)(5))
        x = torch.randn(1, 5, 16, dtype=torch.float64)
        changed = x.clone()
        changed[:, 3:] += torch.arange(32, dtype=torch.float64).reshape(1, 2, 16) / 3
        def traverse(value):
            keys, values, outputs = [], [], []
            for depth, block in enumerate(blocks):
                self.assertEqual(len(keys), depth)
                value, key, val, _ = block(value, keys, values, cos, sin)
                keys.append(key)
                values.append(val)
                outputs.append(value)
            return outputs
        first, second = traverse(x), traverse(changed)
        for depth, (a, b) in enumerate(zip(first, second)):
            # Source MoDABlock includes FP32 gate scores even after .double().
            # Future routing can also change expert GEMM batch shapes. Use the
            # frozen mixed-path bound, not bitwise equality as a causal test.
            self.close(a[:, :3], b[:, :3], "mixed-path causal prefix depth " + str(depth), 2e-6, 2e-5)
            self.assertFalse(torch.equal(a[:, 3:], b[:, 3:]))

    def test_m06_writer_from_post_ffn_and_gradients_through_history(self):
        """Writer uses post-FFN block output; later reader gradients reach both writers."""
        cfg = config(self.source)
        block = self.source.MoDABlock(cfg).double().eval()
        reader = self.source.MoDAAttention(cfg).double().eval()
        cos, sin = (v.double() for v in self.source.RotaryEmbedding(4, 8)(5))
        x = torch.randn(1, 5, 16, dtype=torch.float64, requires_grad=True)
        out, key, val, _ = block(x, [], [], cos, sin)
        expected_k = rotate((out @ block.k_write.weight.T).reshape(1, 5, 2, 4).transpose(1, 2), cos, sin)
        expected_v = (out @ block.v_write.weight.T).reshape(1, 5, 2, 4).transpose(1, 2)
        self.close(key, expected_k, "post FFN key writer", ATOL, RTOL)
        self.close(val, expected_v, "post FFN value writer", ATOL, RTOL)
        reader(out, [key], [val], cos, sin).square().mean().backward()
        self.active(block.k_write.weight.grad, "key writer gradient")
        self.active(block.v_write.weight.grad, "value writer gradient")
        self.active(x.grad, "source input gradient through two depths")

    def test_m07_independent_calls_have_fresh_local_depth_caches(self):
        """Source model has new depth lists per call and no stale autograd graph."""
        model = self.source.MoDAModel(config(self.source)).double().eval()
        first = torch.tensor([[1, 2, 3, 4, 5]])
        second = torch.tensor([[6, 7, 8, 9, 10]])
        seen = []
        handles = [block.register_forward_pre_hook(lambda module, args: seen.append((args[1], args[2], len(args[1]))))
                   for block in model.blocks]
        try:
            a, _ = model(first)
            a.square().mean().backward()
            model.zero_grad(set_to_none=True)
            b, _ = model(second)
            b.square().mean().backward()
            model.zero_grad(set_to_none=True)
            c, _ = model(first)
            self.exact(a, c, "independent forward identity")
            self.assertEqual([row[2] for row in seen], [0, 1, 0, 1, 0, 1])
            self.assertIs(seen[0][0], seen[1][0])
            self.assertIsNot(seen[0][0], seen[2][0])
            self.assertIsNot(seen[2][0], seen[4][0])
            self.assertFalse(hasattr(model, "depth_k_cache"))
        finally:
            for handle in handles:
                handle.remove()

    def test_m08_zero_output_projection_is_external_residual_identity(self):
        """Zero attention output leaves x+attention(x) exact; postnorm block is not asserted identical."""
        _, attn, x, keys, values, cos, sin = self.setup_attention()
        with torch.no_grad():
            attn.o_proj.weight.zero_()
        self.exact(x + attn(x, keys, values, cos, sin), x, "external residual identity")

    def test_m09_low_width_reader_math_and_gradient(self):
        """D16 with one four-dimensional Q/KV head projects back to D16 correctly."""
        _, attn, x, keys, values, cos, sin = self.setup_attention(n_heads_q=1, n_heads_kv=1)
        actual = attn(x, keys, values, cos, sin)
        self.close(actual, reference(attn, x, keys, values, cos, sin), "low-width output", ATOL, RTOL)
        other = copy.deepcopy(attn)
        xx = x.detach().clone().requires_grad_()
        kk = [k.detach().clone().requires_grad_() for k in keys]
        vv = [v.detach().clone().requires_grad_() for v in values]
        actual.square().mean().backward()
        reference(other, xx, kk, vv, cos, sin).square().mean().backward()
        self.close(x.grad, xx.grad, "low-width input gradient", ATOL, RTOL)
        for name, p in attn.named_parameters():
            self.active(p.grad, "low-width " + name)
            self.close(p.grad, dict(other.named_parameters())[name].grad, "low-width " + name + " gradient", ATOL, RTOL)
        for i in range(2):
            self.close(keys[i].grad, kk[i].grad, "low-width history key gradient " + str(i), ATOL, RTOL)
            self.close(values[i].grad, vv[i].grad, "low-width history value gradient " + str(i), ATOL, RTOL)

    def test_m10_new_instance_state_reload_exact(self):
        """Source tiny model state_dict reload in a new instance preserves logits exactly."""
        cfg = config(self.source)
        model = self.source.MoDAModel(cfg).double().eval()
        ids = torch.tensor([[1, 2, 3, 4, 5]])
        before, _ = model(ids)
        stream = io.BytesIO()
        torch.save(model.state_dict(), stream)
        stream.seek(0)
        other = self.source.MoDAModel(cfg).double().eval()
        other.load_state_dict(torch.load(stream, weights_only=True), strict=True)
        self.assertEqual(set(other.state_dict()), set(model.state_dict()))
        for name, value in model.state_dict().items():
            self.exact(other.state_dict()[name], value, "reloaded state " + name)
        after, _ = other(ids)
        self.exact(after, before, "new-instance state reload")

    def test_m11_explicit_history_immutability_causality_and_empty_after_history(self):
        """Supplied depth caches stay immutable and cannot leak future positions or prior calls."""
        _, attn, x, keys, values, cos, sin = self.setup_attention()
        saved = [z.detach().clone() for z in [x, *keys, *values]]
        first = attn(x, keys, values, cos, sin)
        repeat = attn(x, keys, values, cos, sin)
        self.exact(first, repeat, "same arguments repeat")
        for index, (before, after) in enumerate(zip(saved, [x, *keys, *values])):
            self.exact(after, before, "unchanged explicit input/cache " + str(index))
        xx = x.detach().clone()
        kk, vv = [z.detach().clone() for z in keys], [z.detach().clone() for z in values]
        xx[:, 3:] += 5
        for z in [*kk, *vv]:
            z[:, :, 3:] += 7
        changed = attn(xx, kk, vv, cos, sin)
        self.close(first[:, :3], changed[:, :3], "explicit cache future-position isolation", ATOL, RTOL)
        self.assertFalse(torch.equal(first[:, 3:], changed[:, 3:]))
        empty = attn(x, [], [], cos, sin)
        self.close(empty, reference(attn, x, [], [], cos, sin), "empty after history call", ATOL, RTOL)
        self.assertEqual(len(keys), 2)
        self.assertEqual(len(values), 2)


if __name__ == "__main__":
    sys.exit(main(MoDATests))
