# Thermo-B (rank expansion on Parcae-140M, LoRA r28, base frozen) summary

**Status: NOT TESTED (runs incomplete)**

- C (rank 28 from the start): chosen LR 0.0003 (sweep mean dev NLL: 0.0003 -> 3.2693)
- E (rank 1->28): chosen LR 0.0003 (sweep mean dev NLL: 0.0003 -> 3.2686)

Dev, change vs native (nats/token, mean [95% CI]):

| run | trainable | tok/s | loss first->last | books | c4 | fineweb | wikitext |
|---|---:|---:|---|---:|---:|---:|---:|
| expand_lr3e-4_s0 | 2325624 | 839 | 2.829->2.683 | +0.0002 [-0.0012,+0.0016] | -0.0005 [-0.0023,+0.0012] | -0.0000 [-0.0009,+0.0009] | -0.0000 [-0.0016,+0.0018] |
| full_lr3e-4_s0 | 2325624 | 868 | 2.829->2.683 | +0.0005 [-0.0016,+0.0026] | -0.0008 [-0.0030,+0.0013] | +0.0014 [-0.0001,+0.0029] | +0.0015 [-0.0001,+0.0032] |
| thermo_lr3e-4_s0 | 2325624 | 847 | 2.829->2.683 | +0.0001 [-0.0013,+0.0016] | -0.0005 [-0.0024,+0.0011] | -0.0001 [-0.0010,+0.0008] | +0.0001 [-0.0014,+0.0017] |

Dev gate (candidate X = argmin over {expand, thermo} of the seed-averaged OOD dev NLL; pass if for both seeds OOD dev NLL of X < C): incomplete
- missing: full_s1, expand_s1, thermo_s1

Learning curves (OOD dev mean NLL, replica 0; seed 0 of the chosen LR):

| arm | 0.0M | 0.2M | 0.3M | 0.5M | 0.7M | 0.8M | 1.0M |
|---|---:|---:|---:|---:|---:|---:|---:|
| full | 3.3626 | 3.3656 | 3.3652 | 3.3643 | 3.3631 | 3.3640 | 3.3630 |
| expand | 3.3626 | 3.3639 | 3.3642 | 3.3643 | 3.3637 | 3.3639 | 3.3625 |
| thermo | 3.3626 | 3.3637 | 3.3641 | 3.3642 | 3.3636 | 3.3638 | 3.3625 |

Geometry of the change dh = h - h_native (report only; seed 0). Columns: tokens, active rank, PR(dh) token level, TwoNN(dh) token level, PR(dh) window means, TwoNN(dh) window means, rms(dh), mean effective rank of the adapter updates

C (rank 28 from the start):

| tokens | rank | PR tok | TwoNN tok | PR win | TwoNN win | rms | adapter erank |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.0M | 28 | - | - | - | - | 0.0000 | 0.00 |
| 0.2M | 28 | 25.73 | 19.26 | 18.98 | 13.74 | 0.0050 | 23.21 |
| 0.3M | 28 | 23.23 | 19.08 | 17.14 | 12.42 | 0.0046 | 23.60 |
| 0.5M | 28 | 24.24 | 18.23 | 11.62 | 13.36 | 0.0052 | 23.84 |
| 0.7M | 28 | 23.30 | 19.95 | 12.89 | 16.82 | 0.0046 | 23.95 |
| 0.8M | 28 | 18.21 | 18.99 | 12.11 | 15.71 | 0.0046 | 24.00 |
| 1.0M | 28 | 14.87 | 19.14 | 13.32 | 16.99 | 0.0044 | 24.02 |

E (rank 1->28):

| tokens | rank | PR tok | TwoNN tok | PR win | TwoNN win | rms | adapter erank |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.0M | 1 | - | - | - | - | 0.0000 | 0.00 |
| 0.2M | 1 | 27.10 | 20.61 | 14.68 | 12.17 | 0.0035 | 1.00 |
| 0.3M | 2 | 46.70 | 19.89 | 21.32 | 15.30 | 0.0025 | 1.94 |
| 0.5M | 4 | 21.13 | 19.30 | 16.98 | 13.02 | 0.0033 | 3.64 |
| 0.7M | 8 | 23.06 | 19.95 | 19.34 | 14.91 | 0.0027 | 6.70 |
| 0.8M | 16 | 18.61 | 19.54 | 16.98 | 16.17 | 0.0029 | 11.49 |
| 1.0M | 28 | 15.05 | 19.08 | 17.10 | 15.13 | 0.0031 | 16.93 |

T (rank 1->28 + temperature):

| tokens | rank | PR tok | TwoNN tok | PR win | TwoNN win | rms | adapter erank |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.0M | 1 | - | - | - | - | 0.0000 | 0.00 |
| 0.2M | 1 | 27.37 | 20.26 | 14.19 | 12.56 | 0.0033 | 1.00 |
| 0.3M | 2 | 45.50 | 19.68 | 21.61 | 15.42 | 0.0025 | 1.94 |
| 0.5M | 4 | 21.69 | 19.38 | 17.15 | 12.59 | 0.0034 | 3.70 |
| 0.7M | 8 | 23.98 | 19.53 | 19.60 | 13.85 | 0.0027 | 6.84 |
| 0.8M | 16 | 19.36 | 19.61 | 17.05 | 15.29 | 0.0028 | 11.89 |
| 1.0M | 28 | 15.71 | 18.98 | 17.24 | 14.72 | 0.0031 | 17.70 |


Data dimension per domain, as Parcae sees it (native final hidden states; report only): books TwoNN 7.8 / PR 6.8 (window means), TwoNN 12.0 / PR 7.4 (tokens), c4 TwoNN 11.4 / PR 7.4 (window means), TwoNN 8.9 / PR 13.7 (tokens), fineweb TwoNN 12.1 / PR 7.6 (window means), TwoNN 8.5 / PR 16.4 (tokens), wikitext TwoNN 7.2 / PR 6.7 (window means), TwoNN 9.5 / PR 11.7 (tokens)
