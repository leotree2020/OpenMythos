# Stage 0 summary

Replicas per window: 2. NLL in nats/token (lower is better). Primary scope t[65..255]; early scope t[1..64]. Identical duplicate rows ignored: 3.

## c4

| condition | windows | mean NLL | ppl | early NLL |
|---|---:|---:|---:|---:|
| bos1_d8 | 100 | 3.3953 | 29.82 | 4.2594 |
| bos1_d16 | 100 | 3.3942 | 29.79 | 4.2626 |
| bos1_d32 | 100 | 3.3943 | 29.79 | 4.2634 |
| bos0_d8 | 100 | 3.3169 | 27.57 | 3.7764 |
| bos0_d16 | 100 | 3.3142 | 27.50 | 3.7767 |
| bos0_d32 | 100 | 3.3141 | 27.50 | 3.7769 |

| contrast | mean | 95% CI | median | neg/pos | mean w/o largest | ppl change |
|---|---:|---|---:|---:|---:|---:|
| bos1_d16_minus_d8 | -0.0011 | [-0.0034, +0.0012] | -0.0003 | 53/47 | -0.0007 | -0.11% |
| bos1_d32_minus_d8 | -0.0010 | [-0.0040, +0.0020] | -0.0007 | 52/48 | -0.0003 | -0.10% |
| bos0_d16_minus_d8 | -0.0027 | [-0.0044, -0.0010] | -0.0020 | 63/37 | -0.0025 | -0.27% |
| bos0_d32_minus_d8 | -0.0028 | [-0.0048, -0.0007] | -0.0020 | 59/41 | -0.0032 | -0.28% |
| d8_primary_bos_minus_nobos | +0.0784 | [+0.0668, +0.0905] | +0.0743 | 9/91 | +0.0764 | +8.16% |
| d8_early_bos_minus_nobos | +0.4830 | [+0.4217, +0.5432] | +0.5338 | 6/94 | +0.4759 | +62.10% |
| d16_primary_bos_minus_nobos | +0.0801 | [+0.0681, +0.0918] | +0.0754 | 9/91 | +0.0780 | +8.34% |
| d16_early_bos_minus_nobos | +0.4858 | [+0.4233, +0.5478] | +0.5334 | 8/92 | +0.4783 | +62.55% |
| d32_primary_bos_minus_nobos | +0.0803 | [+0.0685, +0.0921] | +0.0802 | 11/89 | +0.0782 | +8.36% |
| d32_early_bos_minus_nobos | +0.4865 | [+0.4244, +0.5491] | +0.5365 | 9/91 | +0.4791 | +62.66% |

Oracle (BOS on, upper bound): cheapest depth within 0.01 nats of the best -> mean NLL 3.3909 vs fixed max depth 3.3943 at 36% of its cost; choices {'8': 77, '16': 21, '32': 2}.

## fineweb

| condition | windows | mean NLL | ppl | early NLL |
|---|---:|---:|---:|---:|
| bos1_d8 | 100 | 2.9410 | 18.93 | 3.5462 |
| bos1_d16 | 100 | 2.9401 | 18.92 | 3.5463 |
| bos1_d32 | 100 | 2.9402 | 18.92 | 3.5458 |
| bos0_d8 | 100 | 2.8734 | 17.70 | 3.1660 |
| bos0_d16 | 100 | 2.8726 | 17.68 | 3.1655 |
| bos0_d32 | 100 | 2.8727 | 17.69 | 3.1658 |

| contrast | mean | 95% CI | median | neg/pos | mean w/o largest | ppl change |
|---|---:|---|---:|---:|---:|---:|
| bos1_d16_minus_d8 | -0.0009 | [-0.0028, +0.0010] | -0.0007 | 53/47 | -0.0013 | -0.09% |
| bos1_d32_minus_d8 | -0.0008 | [-0.0030, +0.0014] | -0.0011 | 51/49 | -0.0011 | -0.08% |
| bos0_d16_minus_d8 | -0.0008 | [-0.0023, +0.0006] | -0.0010 | 51/49 | -0.0006 | -0.08% |
| bos0_d32_minus_d8 | -0.0007 | [-0.0024, +0.0009] | -0.0003 | 50/50 | -0.0005 | -0.07% |
| d8_primary_bos_minus_nobos | +0.0676 | [+0.0569, +0.0786] | +0.0692 | 8/92 | +0.0660 | +6.99% |
| d8_early_bos_minus_nobos | +0.3802 | [+0.3243, +0.4352] | +0.4035 | 7/93 | +0.3740 | +46.25% |
| d16_primary_bos_minus_nobos | +0.0675 | [+0.0569, +0.0784] | +0.0652 | 10/90 | +0.0656 | +6.98% |
| d16_early_bos_minus_nobos | +0.3808 | [+0.3248, +0.4366] | +0.3988 | 6/94 | +0.3753 | +46.34% |
| d32_primary_bos_minus_nobos | +0.0675 | [+0.0568, +0.0787] | +0.0644 | 11/89 | +0.0656 | +6.98% |
| d32_early_bos_minus_nobos | +0.3800 | [+0.3235, +0.4365] | +0.4065 | 7/93 | +0.3746 | +46.23% |

Oracle (BOS on, upper bound): cheapest depth within 0.01 nats of the best -> mean NLL 2.9383 vs fixed max depth 2.9402 at 34% of its cost; choices {'8': 82, '16': 18, '32': 0}.

## wikitext

| condition | windows | mean NLL | ppl | early NLL |
|---|---:|---:|---:|---:|
| bos1_d8 | 100 | 3.3258 | 27.82 | 4.0839 |
| bos1_d16 | 100 | 3.3240 | 27.77 | 4.0782 |
| bos1_d32 | 100 | 3.3240 | 27.77 | 4.0764 |
| bos0_d8 | 100 | 3.2267 | 25.20 | 3.6070 |
| bos0_d16 | 100 | 3.2245 | 25.14 | 3.6039 |
| bos0_d32 | 100 | 3.2245 | 25.14 | 3.6028 |

| contrast | mean | 95% CI | median | neg/pos | mean w/o largest | ppl change |
|---|---:|---|---:|---:|---:|---:|
| bos1_d16_minus_d8 | -0.0018 | [-0.0044, +0.0008] | -0.0013 | 57/43 | -0.0014 | -0.18% |
| bos1_d32_minus_d8 | -0.0018 | [-0.0047, +0.0013] | -0.0018 | 56/44 | -0.0012 | -0.18% |
| bos0_d16_minus_d8 | -0.0022 | [-0.0035, -0.0009] | -0.0027 | 69/31 | -0.0019 | -0.22% |
| bos0_d32_minus_d8 | -0.0022 | [-0.0037, -0.0007] | -0.0024 | 66/34 | -0.0019 | -0.22% |
| d8_primary_bos_minus_nobos | +0.0991 | [+0.0848, +0.1135] | +0.1010 | 17/83 | +0.0973 | +10.42% |
| d8_early_bos_minus_nobos | +0.4768 | [+0.4213, +0.5314] | +0.5160 | 6/94 | +0.4712 | +61.10% |
| d16_primary_bos_minus_nobos | +0.0995 | [+0.0850, +0.1134] | +0.0964 | 16/84 | +0.0979 | +10.46% |
| d16_early_bos_minus_nobos | +0.4743 | [+0.4187, +0.5296] | +0.5116 | 5/95 | +0.4683 | +60.70% |
| d32_primary_bos_minus_nobos | +0.0995 | [+0.0851, +0.1136] | +0.0990 | 16/84 | +0.0978 | +10.46% |
| d32_early_bos_minus_nobos | +0.4736 | [+0.4191, +0.5271] | +0.5092 | 5/95 | +0.4676 | +60.58% |

Oracle (BOS on, upper bound): cheapest depth within 0.01 nats of the best -> mean NLL 3.3213 vs fixed max depth 3.3240 at 36% of its cost; choices {'8': 74, '16': 26, '32': 0}.

## wikitext_old32

| condition | windows | mean NLL | ppl | early NLL |
|---|---:|---:|---:|---:|
| bos1_d8 | 32 | 3.3731 | 29.17 | 4.2710 |
| bos1_d16 | 32 | 3.3670 | 28.99 | 4.2671 |
| bos1_d32 | 32 | 3.3679 | 29.02 | 4.2668 |
| bos0_d8 | 32 | 3.3775 | 29.30 | 4.5419 |
| bos0_d16 | 32 | 3.3460 | 28.39 | 4.2721 |
| bos0_d32 | 32 | 3.3406 | 28.24 | 4.2553 |

| contrast | mean | 95% CI | median | neg/pos | mean w/o largest | ppl change |
|---|---:|---|---:|---:|---:|---:|
| bos1_d16_minus_d8 | -0.0061 | [-0.0119, -0.0004] | -0.0050 | 20/12 | -0.0047 | -0.61% |
| bos1_d32_minus_d8 | -0.0052 | [-0.0117, +0.0012] | -0.0043 | 20/12 | -0.0036 | -0.52% |
| bos0_d16_minus_d8 | -0.0315 | [-0.0498, -0.0182] | -0.0267 | 28/4 | -0.0241 | -3.10% |
| bos0_d32_minus_d8 | -0.0369 | [-0.0613, -0.0201] | -0.0280 | 28/4 | -0.0271 | -3.62% |
| d8_primary_bos_minus_nobos | -0.0044 | [-0.0366, +0.0218] | +0.0107 | 13/19 | +0.0074 | -0.44% |
| d8_early_bos_minus_nobos | -0.2708 | [-0.7699, +0.0380] | -0.0060 | 17/15 | -0.0526 | -23.73% |
| d16_primary_bos_minus_nobos | +0.0210 | [-0.0029, +0.0439] | +0.0302 | 9/23 | +0.0260 | +2.12% |
| d16_early_bos_minus_nobos | -0.0049 | [-0.1397, +0.1238] | +0.0601 | 14/18 | +0.0272 | -0.49% |
| d32_primary_bos_minus_nobos | +0.0273 | [+0.0037, +0.0502] | +0.0323 | 8/24 | +0.0228 | +2.77% |
| d32_early_bos_minus_nobos | +0.0114 | [-0.1247, +0.1410] | +0.0655 | 14/18 | +0.0449 | +1.15% |

Oracle (BOS on, upper bound): cheapest depth within 0.01 nats of the best -> mean NLL 3.3640 vs fixed max depth 3.3679 at 40% of its cost; choices {'8': 18, '16': 14, '32': 0}.

## Verdict (BOS on; frozen three-way statement)

- depth 16 not significantly better than 8
- depth 32 not significantly better than 8

## Timing (median seconds per 256-token forward)

- bos0_d8: 1.293 s over 664 forwards
- bos0_d16: 2.173 s over 664 forwards
- bos0_d32: 3.936 s over 664 forwards
- bos1_d8: 1.290 s over 664 forwards (ratio_to_d8 1.00x), 198 tokens/s
- bos1_d16: 2.178 s over 664 forwards (ratio_to_d8 1.69x), 118 tokens/s
- bos1_d32: 3.937 s over 664 forwards (ratio_to_d8 3.05x), 65 tokens/s
