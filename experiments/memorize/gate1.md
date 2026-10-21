## Gate 1：32 道固定 1 跳题

通过条件（每个种子）：最终在全部 32 题上答对 ≥ 31 题，且 loss ≤ 0.1

| 组 | 种子 | 答对 | 准确率 | loss | 预测落在根数字内 | 首次全对的步数 | 实际步数 | 数据未变 | 训练块计算量 | 留出集准确率（仅参考） | 通过 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| openmythos | 1 | 32/32 | 100.0% | 0.0003 | 100.0% | 50 | 2000 | 是 | 13.42M | 10.8% | ✓ |
| openmythos | 2 | 32/32 | 100.0% | 0.0003 | 100.0% | 100 | 2000 | 是 | 13.42M | 9.6% | ✓ |
| openmythos | 3 | 32/32 | 100.0% | 0.0003 | 100.0% | 100 | 2000 | 是 | 9.62M | 9.6% | ✓ |
| transformer | 1 | 32/32 | 100.0% | 0.0003 | 100.0% | 50 | 2000 | 是 | 6.72M | 12.2% | ✓ |
| transformer | 2 | 32/32 | 100.0% | 0.0003 | 100.0% | 50 | 2000 | 是 | 6.72M | 12.0% | ✓ |
| transformer | 3 | 32/32 | 100.0% | 0.0003 | 100.0% | 50 | 2000 | 是 | 6.72M | 12.0% | ✓ |

## 训练过程摘要（每个种子：第 1 / 500 / 1000 / 最后一次记录）

- openmythos 种子 1：step 1 loss 5.552 acc 3.1% 梯度 4.29 无梯度参数 6；step 500 loss 0.001 acc 100.0% 梯度 0.00 无梯度参数 0；step 1000 loss 0.001 acc 100.0% 梯度 0.00 无梯度参数 0；step 2000 loss 0.000 acc 100.0% 梯度 0.00 无梯度参数 0
- openmythos 种子 2：step 1 loss 5.428 acc 21.9% 梯度 4.33 无梯度参数 3；step 500 loss 0.001 acc 100.0% 梯度 0.00 无梯度参数 0；step 1000 loss 0.001 acc 100.0% 梯度 0.00 无梯度参数 0；step 2000 loss 0.000 acc 100.0% 梯度 0.00 无梯度参数 0
- openmythos 种子 3：step 1 loss 5.542 acc 0.0% 梯度 4.26 无梯度参数 3；step 500 loss 0.001 acc 100.0% 梯度 0.00 无梯度参数 0；step 1000 loss 0.001 acc 100.0% 梯度 0.00 无梯度参数 0；step 2000 loss 0.000 acc 100.0% 梯度 0.00 无梯度参数 0
- transformer 种子 1：step 1 loss 5.547 acc 0.0% 梯度 8.22 无梯度参数 0；step 500 loss 0.001 acc 100.0% 梯度 0.00 无梯度参数 0；step 1000 loss 0.000 acc 100.0% 梯度 0.00 无梯度参数 0；step 2000 loss 0.000 acc 100.0% 梯度 0.00 无梯度参数 0
- transformer 种子 2：step 1 loss 5.461 acc 0.0% 梯度 8.81 无梯度参数 0；step 500 loss 0.001 acc 100.0% 梯度 0.00 无梯度参数 0；step 1000 loss 0.000 acc 100.0% 梯度 0.00 无梯度参数 0；step 2000 loss 0.000 acc 100.0% 梯度 0.00 无梯度参数 0
- transformer 种子 3：step 1 loss 5.454 acc 0.0% 梯度 8.92 无梯度参数 0；step 500 loss 0.001 acc 100.0% 梯度 0.00 无梯度参数 0；step 1000 loss 0.000 acc 100.0% 梯度 0.00 无梯度参数 0；step 2000 loss 0.000 acc 100.0% 梯度 0.00 无梯度参数 0

## 梯度范数分部（最后一次记录，种子均值）

- openmythos：embed/head 0.001，first block 0.000，middle block 0.000，loop-only (injection/ACT/LoRA/norm) 0.000，last block 0.000，final norm 0.000
- transformer：embed/head 0.001，first block 0.000，middle block 0.000，last block 0.000，final norm 0.000

训练块计算量：openmythos / transformer = 1.81×

## 判定

- **openmythos**：通过
- **transformer**：通过

**按预登记的解读：两组都通过 Gate 1：按预登记进入 Gate 2（512 题）。**
