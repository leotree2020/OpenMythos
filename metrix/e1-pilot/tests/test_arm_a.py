"""Arm A: F's loss plus lambda * KL(p_base || p_theta) on 4 anchor documents per step (protocol v1.1 section 4).

Implementation Task Order V1, section 6 item 5: at step 0 the KL is 0; no parameter of the base copy has
requires_grad; the base copy's parameter hash is unchanged after training.
Owner, stage B item 6: the KL is KL(p_base || p_theta) (not the reverse) and token-weighted over all KL tokens of the
step's documents (one division by sum (n_x - 1), not a mean of per-document means), as protocol section 4 states.
Random-initialisation models only.
"""
import copy

import torch

from conftest import tiny_model
from metrix_e1 import mode as M
from metrix_e1 import train as T


def _logits(rows):
    """[batch, positions, vocab] tensor from nested lists of per-position probability vectors (as logits = log p)."""
    return torch.log(torch.tensor(rows, dtype=torch.float64))


def test_kl_direction_is_base_to_theta():
    p = [0.98, 0.01, 0.01]       # p_base
    q = [0.4, 0.3, 0.3]          # p_theta
    # one document of 2 tokens: one KL position (t = 2); the second position has no next token
    lb = _logits([[p, [1 / 3] * 3]])
    lt = _logits([[q, [1 / 3] * 3]])
    mask = torch.tensor([[1, 1]])
    got = float(T.anchor_kl(lt, lb, mask))
    kl_pq = sum(a * (torch.log(torch.tensor(a)) - torch.log(torch.tensor(b))) for a, b in zip(p, q))
    kl_qp = sum(b * (torch.log(torch.tensor(b)) - torch.log(torch.tensor(a))) for a, b in zip(p, q))
    assert abs(got - float(kl_pq)) < 1e-6
    assert abs(float(kl_pq) - float(kl_qp)) > 0.1            # the two directions differ here
    assert abs(got - float(kl_qp)) > 0.1


def test_kl_is_token_weighted_over_documents():
    """Document 1: 2 tokens (1 KL position, KL k1); document 2: 5 tokens (4 KL positions, KL k2 each). Token-weighted:
    (k1 + 4 k2) / 5. A mean of per-document means would be (k1 + k2) / 2."""
    u = [1 / 3] * 3
    p1, q1 = [0.9, 0.05, 0.05], [0.1, 0.45, 0.45]
    p2, q2 = [0.5, 0.3, 0.2], [0.4, 0.3, 0.3]
    lb = _logits([[p1, u, u, u, u], [p2, p2, p2, p2, u]])
    lt = _logits([[q1, u, u, u, u], [q2, q2, q2, q2, u]])
    mask = torch.tensor([[1, 1, 0, 0, 0], [1, 1, 1, 1, 1]])

    def kl(p, q):
        return sum(a * (torch.log(torch.tensor(a)) - torch.log(torch.tensor(b))) for a, b in zip(p, q)).item()
    k1, k2 = kl(p1, q1), kl(p2, q2)
    got = float(T.anchor_kl(lt, lb, mask))
    assert abs(got - (k1 + 4 * k2) / 5) < 1e-6
    assert abs(got - (k1 + k2) / 2) > 0.05
    # padded positions of document 1 (different distributions there) do not enter
    lt2 = lt.clone()
    lt2[0, 2:] = _logits([[q1, q1, q1]])[0]
    assert float(T.anchor_kl(lt2, lb, mask)) == got


def test_kl_positions_are_t2_to_n():
    """KL positions are logits 0..n-2 (distributions of tokens 2..n): changing the logits at position n-1 (which
    predicts a token after the document) changes nothing."""
    p, q = [0.6, 0.3, 0.1], [0.3, 0.3, 0.4]
    lb = _logits([[p, p, p]])
    lt = _logits([[q, q, q]])
    mask = torch.tensor([[1, 1, 1]])
    a = float(T.anchor_kl(lt, lb, mask))
    lt[0, 2] = torch.log(torch.tensor([0.98, 0.01, 0.01], dtype=torch.float64))
    assert float(T.anchor_kl(lt, lb, mask)) == a


def test_base_copy_is_frozen():
    m = tiny_model()
    m.requires_grad_(True)
    b = T.make_base_copy(m)
    assert all(not p.requires_grad for p in b.parameters())
    assert not b.training
    assert T.count_trainable(b) == 0
    assert all(p.data_ptr() != q.data_ptr() for p, q in zip(m.parameters(), b.parameters()))


def test_step0_kl_zero_base_unchanged_after_training(tok, data_rows, contract):
    m = tiny_model()
    before = T.state_sha256(copy.deepcopy(m))
    spec = [s for s in T.search_runs(contract, "A") if s.config_id == "A6"][0]      # lr 1e-4, lambda 3
    res = T.train_run(m, tok, data_rows, spec, contract, M.smoke_mode(3), "cpu")
    assert res.log[0]["kl"] == 0.0                                  # step 1 starts from theta = base: KL exactly 0
    assert res.log[0]["anchor_docs"] == [4, 5, 6, 7]                # B1: step 1 uses documents 4..7
    assert res.base_trainable == 0
    assert res.frozen_sha256_before == before                       # the copy is the untrained model
    assert res.frozen_sha256_after == res.frozen_sha256_before      # and unchanged after training
    assert T.state_sha256(m) != before                              # while the trained model moved
    assert res.log[1]["kl"] > 0
    assert res.anchor_tokens == sum(e["anchor_tokens"] for e in res.log)
    for e in res.log:
        assert abs(e["loss"] - (e["ce"] + spec.cfg["anchor_lambda"] * e["kl"])) < 1e-4
