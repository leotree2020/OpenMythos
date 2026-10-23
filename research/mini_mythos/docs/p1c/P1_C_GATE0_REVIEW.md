# P1-C Gate 0 Review

**HEAD at review**: `064543db46e565bebb97931f9220176e2364a2f5` (now updated)
**PR**: #6 (Draft, still open)
**Upstream**: Parcae `69284c13746e849104f738d6d1a347b1f457df76`

## Audit results

- **Gradient Accumulation**: VERIFIED. `scripts/train.py` prints and uses `cfg.gradient_accumulation_steps`, `micro_batch_size`, `world_batch_size`.
- **FLOPs**: Upstream contains `compute_flops_per_token_at_recurrence` and `estimate_flops_recurrent` that explicitly account for forward_only + backprop_depth. Our earlier range is consistent with this; not a precise measured value.
- **Checkpoint**: Uses Lightning Fabric / distributed checkpoint helpers. Expected to save model + optimizer. Exact contents to be confirmed in Gate 1 logs.
- **Config overrides**: Supported via CLI / YAML. Prefer official entry points.
- **Tokenizer license**: NOT VERIFIED. HF card for `SandyResearch/parcae-tokenizer` has no model card. Do not assume compatibility. BLOCKED for download until clarified.
- **Mean recurrence / backprop**: VERIFIED from HF config and YAML: 8 / 4.

## Budget confirmation (ESTIMATED)

Sources (Oct 2026):
- RunPod A100 PCIe 80GB Community ~$1.19/hr, Secure ~$1.79/hr.
- At 150 JPY/USD: ~180–270 JPY/hr.
- Storage: ~$0.07–0.10/GB/month (network volume / volume disk).
- No major egress fees noted in public docs.

Gate 1 target ≤ 1,000 JPY → recommend ≤ 3–4 hours on cheapest available A100 80GB.
Total hard cap: 5,000 JPY cumulative.

**Auto-stop**: User must set billing alerts / manually terminate pod and confirm in dashboard. This agent cannot control RunPod.

## Gate 0 status: PASS (planning only)

Ready for user to execute Gate 1 manually if budget and payment are confirmed.
