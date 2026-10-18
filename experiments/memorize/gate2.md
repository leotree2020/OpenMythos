## Gate 2：512 道固定 1 跳题

通过条件（每个种子）：最终在全部 512 题上答对 ≥ 502 题，且 loss ≤ 0.1

| 组 | 种子 | 答对 | 准确率 | loss | 预测落在根数字内 | 首次全对的步数 | 实际步数 | 数据未变 | 训练块计算量 | 留出集准确率（仅参考） | 通过 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| openmythos | 1 | 512/512 | 100.0% | 0.0005 | 100.0% | 1050 | 3000 | 是 | 32.24M | 26.6% | ✓ |
| openmythos | 2 | 512/512 | 100.0% | 0.0004 | 100.0% | 950 | 3000 | 是 | 33.29M | 31.0% | ✓ |
| openmythos | 3 | 512/512 | 100.0% | 0.0005 | 100.0% | 1000 | 3000 | 是 | 36.98M | 26.8% | ✓ |
| transformer | 1 | 512/512 | 100.0% | 0.0003 | 100.0% | 750 | 3000 | 是 | 20.16M | 26.8% | ✓ |
| transformer | 2 | 512/512 | 100.0% | 0.0004 | 100.0% | 1100 | 3000 | 是 | 20.16M | 27.4% | ✓ |
| transformer | 3 | 512/512 | 100.0% | 0.0003 | 100.0% | 800 | 3000 | 是 | 20.16M | 27.2% | ✓ |

## 训练过程摘要（每个种子：第 1 / 500 / 1000 / 最后一次记录）

- openmythos 种子 1：step 1 loss 5.587 acc 7.8% 梯度 4.05 无梯度参数 6；step 500 loss 0.105 acc 96.7% 梯度 2.32 无梯度参数 0；step 1000 loss 0.008 acc 99.8% 梯度 0.28 无梯度参数 0；step 3000 loss 0.000 acc 100.0% 梯度 0.00 无梯度参数 0
- openmythos 种子 2：step 1 loss 5.495 acc 10.5% 梯度 3.88 无梯度参数 0；step 500 loss 0.100 acc 96.7% 梯度 6.37 无梯度参数 0；step 1000 loss 0.001 acc 100.0% 梯度 0.01 无梯度参数 0；step 3000 loss 0.000 acc 100.0% 梯度 0.00 无梯度参数 0
- openmythos 种子 3：step 1 loss 5.503 acc 0.0% 梯度 3.92 无梯度参数 3；step 500 loss 0.070 acc 98.6% 梯度 1.30 无梯度参数 0；step 1000 loss 0.008 acc 100.0% 梯度 0.16 无梯度参数 0；step 3000 loss 0.000 acc 100.0% 梯度 0.00 无梯度参数 0
- transformer 种子 1：step 1 loss 5.548 acc 0.0% 梯度 7.63 无梯度参数 0；step 500 loss 0.036 acc 98.8% 梯度 6.23 无梯度参数 0；step 1000 loss 0.001 acc 100.0% 梯度 0.00 无梯度参数 0；step 3000 loss 0.000 acc 100.0% 梯度 0.00 无梯度参数 0
- transformer 种子 2：step 1 loss 5.462 acc 0.0% 梯度 7.88 无梯度参数 0；step 500 loss 0.035 acc 99.2% 梯度 3.52 无梯度参数 0；step 1000 loss 0.005 acc 99.8% 梯度 0.02 无梯度参数 0；step 3000 loss 0.000 acc 100.0% 梯度 0.00 无梯度参数 0
- transformer 种子 3：step 1 loss 5.483 acc 0.0% 梯度 7.45 无梯度参数 0；step 500 loss 0.065 acc 98.4% 梯度 2.66 无梯度参数 0；step 1000 loss 0.021 acc 99.2% 梯度 1.69 无梯度参数 0；step 3000 loss 0.000 acc 100.0% 梯度 0.00 无梯度参数 0

## 梯度范数分部（最后一次记录，种子均值）

- openmythos：embed/head 0.002，first block 0.001，middle block 0.000，loop-only (injection/ACT/LoRA/norm) 0.000，last block 0.000，final norm 0.000
- transformer：embed/head 0.001，first block 0.000，middle block 0.000，last block 0.000，final norm 0.000

训练块计算量：openmythos / transformer = 1.70×

## 判定

- **openmythos**：通过
- **transformer**：通过

**按预登记的解读：两组都记住 512 题：停止。下一步设计独立的泛化实验。**
