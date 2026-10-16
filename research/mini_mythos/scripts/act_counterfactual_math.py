"""Exact 2x2 same-weight counterfactual bookkeeping for ACT-002.

Rows: parameter state (original-training, forced-training).
Columns: ACT policy (original, force-final-remainder).

Four forward passes on the SAME batch distinguish the instantaneous policy
contrast from parameter-history differences. Interaction means the contrasts
depend on parameter state; their norm magnitudes are NOT additive shares.
"""
import torch
import torch.nn.functional as F


def _metrics(x):
    x = x.detach().float()
    return {
        'max_abs': float(x.abs().max()),
        'mean_abs': float(x.abs().mean()),
        'l2': float(torch.linalg.vector_norm(x)),
    }


def factorial_effects(logits_oo, logits_fo, logits_of, logits_ff, labels):
    """Return an exact factorial decomposition of logits and CE loss.

    oo: original ACT at original-trained weights
    fo: forced ACT at original-trained weights
    of: original ACT at forced-trained weights
    ff: forced ACT at forced-trained weights

    Total ff-oo = (fo-oo) + (of-oo) + (ff-of-fo+oo).
    This is a baseline-anchored decomposition with an explicit interaction.
    """
    tensors = (logits_oo, logits_fo, logits_of, logits_ff)
    if logits_oo.ndim != 3 or any(t.shape != logits_oo.shape for t in tensors):
        raise ValueError('All logits must share shape [batch, tokens, vocabulary]')
    if labels.shape != logits_oo.shape[:2]:
        raise ValueError('labels must have shape [batch, tokens]')
    if not all(bool(torch.isfinite(t).all()) for t in tensors):
        raise ValueError('Nonfinite logits')

    with torch.no_grad():
        oo, fo, of, ff = (t.detach().float() for t in tensors)
        mechanism = fo - oo
        history = of - oo
        interaction = (ff - of) - mechanism
        total = ff - oo
        logit_reconstruction_error = (total - (mechanism + history + interaction)).abs().max()
        if float(logit_reconstruction_error) > 1e-5:
            raise RuntimeError('Logit decomposition did not reconstruct total difference')

        losses = {}
        for name, tensor in (('oo', oo), ('fo', fo), ('of', of), ('ff', ff)):
            losses[name] = float(F.cross_entropy(
                tensor.reshape(-1, tensor.shape[-1]), labels.reshape(-1)))

        loss_mechanism = losses['fo'] - losses['oo']
        loss_history = losses['of'] - losses['oo']
        loss_interaction = losses['ff'] - losses['of'] - losses['fo'] + losses['oo']
        loss_total = losses['ff'] - losses['oo']
        loss_error = abs(loss_total - (loss_mechanism + loss_history + loss_interaction))
        return {
            'logits': {
                'total_deployed': _metrics(total),
                'direct_mechanism_same_original_weights': _metrics(mechanism),
                'parameter_history_under_original_act': _metrics(history),
                'policy_parameter_interaction': _metrics(interaction),
                'reconstruction_max_abs_error': float(logit_reconstruction_error),
            },
            'loss': {
                'original_weights_original_act': losses['oo'],
                'original_weights_forced_act': losses['fo'],
                'forced_weights_original_act': losses['of'],
                'forced_weights_forced_act': losses['ff'],
                'total_deployed_delta': loss_total,
                'direct_mechanism_same_original_weights_delta': loss_mechanism,
                'parameter_history_under_original_act_delta': loss_history,
                'policy_parameter_interaction_delta': loss_interaction,
                'reconstruction_abs_error': loss_error,
            },
        }
