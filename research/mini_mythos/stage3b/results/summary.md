# Stage 3b (unfrozen: MoDA-P + Parcae vs LoRA-r28 + Parcae) summary

**Status: FAIL**

- lora short-run LR search (base-weight LR -> mean dev NLL): 3e-06 -> 3.3221, 1e-05 -> 3.3212, 3e-05 -> 3.3215; chosen lora_lr1e-5_s0
- moda short-run LR search (base-weight LR -> mean dev NLL): 3e-06 -> 3.3084, 1e-05 -> 3.3151, 3e-05 -> 3.3179; chosen moda_lr3e-6_s0
- lora: chosen LR 1e-05 (sweep mean dev NLL: 1e-05 -> 3.3171)
- moda: chosen LR 3e-06 (sweep mean dev NLL: 3e-06 -> 3.3121)

Dev, change vs native (nats/token, mean [95% CI]):

| run | trainable | tok/s | loss first->last | books | c4 | fineweb | wikitext |
|---|---:|---:|---|---:|---:|---:|---:|
| lora_lr1e-5_s0 | 146648760 | 36983 | 3.002->3.298 | +0.0683 [+0.0224,+0.1273] | -0.0045 [-0.0080,-0.0009] | +0.0044 [+0.0019,+0.0069] | +0.0042 [+0.0009,+0.0076] |
| lora_lr1e-5_s1 | 146648760 | 36845 | 2.953->3.298 | +0.0760 [+0.0270,+0.1369] | -0.0039 [-0.0075,-0.0003] | +0.0037 [+0.0013,+0.0061] | +0.0078 [+0.0044,+0.0113] |
| moda_lr3e-6_s0 | 146682444 | 32993 | 3.002->3.301 | +0.0506 [+0.0154,+0.0923] | -0.0050 [-0.0078,-0.0022] | +0.0027 [+0.0007,+0.0049] | +0.0042 [+0.0013,+0.0072] |
| moda_lr3e-6_s1 | 146682444 | 33001 | 2.953->3.300 | +0.0524 [+0.0185,+0.0936] | -0.0047 [-0.0076,-0.0018] | +0.0028 [+0.0007,+0.0050] | +0.0046 [+0.0017,+0.0077] |

Dev gate (both seeds: mean OOD dev NLL (books, c4, wikitext) of MoDA < C-LoRA-r28): PASS
- seed 0: MoDA 3.4552 vs C-LoRA 3.4613 (diff -0.0061)
- seed 1: MoDA 3.4561 vs C-LoRA 3.4653 (diff -0.0092)
- training noise floor (max over arms of |seed1-seed0|, OOD dev mean): 0.0040

Test set (moda_lr3e-6_s0 vs lora_lr1e-5_s0), mean [95% CI]:

| comparison | books | c4 | fineweb | wikitext |
|---|---:|---:|---:|---:|
| moda_minus_lora | -0.0314 [-0.0537,-0.0125] | +0.0001 [-0.0014,+0.0016] | +0.0000 [-0.0011,+0.0011] | -0.0006 [-0.0020,+0.0007] |
| moda_minus_native | +0.0394 [+0.0131,+0.0699] | -0.0034 [-0.0053,-0.0014] | +0.0018 [+0.0003,+0.0033] | +0.0020 [-0.0002,+0.0042] |
| lora_minus_native | +0.0709 [+0.0296,+0.1189] | -0.0035 [-0.0060,-0.0010] | +0.0018 [+0.0000,+0.0035] | +0.0026 [+0.0002,+0.0051] |

Criteria:
- 1_two_of_three_ood_improved: FAIL {"domains": ["books"]}
- 2_mean_ood_delta: PASS {"value": -0.0106509175}
- 3_no_domain_clearly_worse: PASS {"domains": []}
- 4_beyond_training_noise: PASS {"dev_deltas": [-0.006110488088792554, -0.009184327939113945], "noise_floor": 0.003957224219375721}

Depth 16, dev domain mean NLL (report only): {"native": {"books": 3.7641012085800156, "c4": 3.321251783732109, "fineweb": 2.878977166778681, "wikitext": 3.2245713071190494}, "moda": {"books": 3.814202033095224, "c4": 3.3164266849093993, "fineweb": 2.8819246097654694, "wikitext": 3.2287102648899286}, "lora": {"books": 3.8330460038717398, "c4": 3.3155302904620014, "fineweb": 2.882791758597224, "wikitext": 3.2275810536156895}}

Cost: {"price_per_hour": 0.897, "wall_hours": 9.1208, "usd": 8.1813576}
