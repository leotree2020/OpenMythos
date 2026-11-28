<!-- host vm (Claude Code cloud container, CPU only) ; 2026-11-28T08:13:30Z -->
<!-- $ python3 -I metrix/e1-pilot/reports/pilot_final/report_fragments.py 53800ef7ba5070fb1bb571c4a96a1130acebdf04 -->
<!-- FRAGMENT environment -->
| 项 | 值 | 出处 |
|---|---|---|
| 设备全名 | NVIDIA A100 80GB PCIe | experiment_record_formal_20261128T045921Z.json `environment.device`;同 test-evaluate 记录 `environment.device` = NVIDIA A100 80GB PCIe |
| 显存(torch total_memory) | 85094825984 字节 | step1_record.json `device.total_memory` |
| 主机名 | 9e51659ac3ff | experiment_record_formal… `environment.hostname`;test-evaluate 记录同字段 = 9e51659ac3ff |
| 平台 | Linux-6.8.0-138-generic-x86_64-with-glibc2.39 | `environment.platform` |
| Python | CPython 3.13.18 (main, Oct 26 2026, 15:28:15) [GCC 13.3.0] | `environment.python_implementation`、`environment.python` |
| torch | 2.11.0(`__version__` 2.11.0+cu130) | `environment.libraries.torch` |
| transformers | 5.22.2 | `environment.libraries.transformers.metadata` |
| tokenizers / huggingface_hub / safetensors / numpy / pyarrow / jinja2 | 0.23.3 / 2.4.0 / 0.8.0 / 2.5.4 / 26.0.1 / 3.1.6 | `environment.libraries.*.metadata` |
| CUDA(torch) / cuDNN | 13.0 / 91900 | `environment.cuda` |
| 确定性设置 | CUBLAS_WORKSPACE_CONFIG=:4096:8, cuda_matmul_allow_tf32=False, cudnn_allow_tf32=False, cudnn_benchmark=False, cudnn_deterministic=True, deterministic_algorithms=True, float32_matmul_precision=highest | `environment.determinism` |
| 分支 / 工作区 | metrix-e1-pilot-protocol-v1 / dirty=False | `environment.git.branch`、`environment.git.dirty` |
| 种子 | DATA_SEED 20261110, CANDIDATE_SEED 20261111, TRAIN_SEEDS [101, 202, 303], BOOTSTRAP_SEED 20261112 | `template["Environment (CPU/GPU, commit, seed)"].seeds` |
| rng_rule | `random.Random(int.from_bytes(sha256(f'{SEED}:{purpose}'.encode('utf-8')).digest()[:8], 'big'))` | 同上 `.seeds.rng_rule` |
<!-- END environment -->

<!-- FRAGMENT commits -->
| 项 | 提交 | 出处 |
|---|---|---|
| formal 的 code_commit | `0a67c2c4382847cdc8dff1bbc8b607551a2b58e4` | experiment_record_formal… `template["Environment (CPU/GPU, commit, seed)"].code_commit` |
| formal 实验记录写入时的 HEAD | `36106eefc2238cee77976e6afbd8632cbbab2257` | experiment_record_formal… `environment.git.head` |
| test-generate(ST10 记录)的 code_commit | `647a75d54603bfab112a80d89a9d14ed22aa1cbf` | st10_record.json `code_commit` |
| test-evaluate 的 code_commit | `a7b4f6fe60d046238a1dc9bc0d62239c01587517` | test_evaluation_marker.json `code_commit`;experiment_record_test-evaluate… `template["Environment …"].code_commit` = `a7b4f6fe60d046238a1dc9bc0d62239c01587517` |
| TEST 标记提交 | `b526312b79c498338020b62c72315e548cb80341` | test_evaluation_result.json `marker_commit` |
| TEST 结果提交 | `9fc7337b4791cb6fb1323885cc09ac158d87a3df` | experiment_record_test-evaluate… `template.Actual.result_commit` |
| test-evaluate 实验记录写入时的 HEAD | `9fc7337b4791cb6fb1323885cc09ac158d87a3df` | experiment_record_test-evaluate… `environment.git.head` |
| TEST 评测 session_id | `5c6d90438a4e5dbeb7bb5f239cbf4b4a` | test_evaluation_marker.json `session_id`;test_evaluation_result.json `session_id` = `5c6d90438a4e5dbeb7bb5f239cbf4b4a` |
<!-- END commits -->

<!-- FRAGMENT hashes -->
| 项 | 值 | 出处 |
|---|---|---|
| 冻结版本 / 冻结提交 | v1.1 / `87a244db28a901f9e89282b50df76778ab5c2887` | experiment_record_formal… `environment.protocol_frozen.version`、`.commit`;gate0_record.json、selection_freeze_record.json、st10_record.json、test_evaluation_result.json 的 `frozen_commit` 均为 `87a244db28a901f9e89282b50df76778ab5c2887` |
| PROTOCOL_FROZEN 文件 sha256 | `3f8a3bbaaafa0b451483bb88baa012c77e8b106dd3b157a152ffa675856906ff` | `environment.protocol_frozen.PROTOCOL_FROZEN_working_tree_bytes_sha256`(parsed / lf_normalized 两字段同值) |
| 冻结文件 `metrix/e1-pilot/DATA_MANIFEST.json` | `d1c32cdd297f70f418c4f7ad7b67742ac18482b4f0a57fd6b7bebe67b11ab911` | `environment.protocol_frozen.file_sha256` |
| 冻结文件 `metrix/e1-pilot/METRIX_E1_PROTOCOL.md` | `1e80ca31ed8bb95dca4c09bc74d424a92ed85417f1285512d521cf5315831308` | `environment.protocol_frozen.file_sha256` |
| 冻结文件 `metrix/e1-pilot/SEARCH_SPACE.json` | `aa59e2e7d6599d8605f40513d702f3c4b1ccb98ab0678155e91d65f243259462` | `environment.protocol_frozen.file_sha256` |
| 冻结文件 `metrix/e1-pilot/SPLIT_MANIFEST.json` | `8c2c46a1d012beb4afe4e0ed0466689297fb97caaee3cda4c55b4261338caf5f` | `environment.protocol_frozen.file_sha256` |
| 冻结数据哈希 `anchor_parquet` | `6a3450ea745ee6b6830c09819c0f2c72682eba443022de595bcb50ceb3092c22` | `environment.protocol_frozen.data_sha256` |
| 冻结数据哈希 `anchor_texts` | `8828bc4fcc5a3552778839f97909f072050431dd6f74dd08ef47602da11b2408` | `environment.protocol_frozen.data_sha256` |
| 冻结数据哈希 `candidates` | `e5d15c9952d8124f2b246ffc76e655be9bf3b0193f048bd8368671d71a6f3705` | `environment.protocol_frozen.data_sha256` |
| 冻结数据哈希 `eval_sets` | `8816fe5a39d8b89e8c4203bf7d660e798faa471d2b72b5ce43c411cf5925a155` | `environment.protocol_frozen.data_sha256` |
| 冻结数据哈希 `facts` | `406c8801c5b69ed235cbe516658ad9ee3e3a8cfe8e4e348a0c1fd7952f2e6b97` | `environment.protocol_frozen.data_sha256` |
| 冻结数据哈希 `parcae_tokenizer` | `e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77` | `environment.protocol_frozen.data_sha256` |
| 冻结数据哈希 `qwen:merges.txt` | `8831e4f1a044471340f7c0a83d7bd71306a5b867e95fd870f74d0c5308a904d5` | `environment.protocol_frozen.data_sha256` |
| 冻结数据哈希 `qwen:tokenizer.json` | `aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4` | `environment.protocol_frozen.data_sha256` |
| 冻结数据哈希 `qwen:tokenizer_config.json` | `d5d09f07b48c3086c508b30d1c9114bd1189145b74e982a265350c923acd8101` | `environment.protocol_frozen.data_sha256` |
| 冻结数据哈希 `qwen:vocab.json` | `ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910` | `environment.protocol_frozen.data_sha256` |
| 冻结数据哈希 `template_set` | `2b52411326c218e9c51d947b2f4e0d77b0cdd5d6237f9ce25b57a872c48ce28f` | `environment.protocol_frozen.data_sha256` |
| 冻结数据哈希 `train_S` | `686fdd2f62edc2115b74a8074a305ddd09b99f11d4f8a267bc80b61c7f73bc1e` | `environment.protocol_frozen.data_sha256` |
| 非 TEST 数据文件 `anchor_text.jsonl` | `2089e656819d1fe0f6ececcc26e5cade09ee80a92c50e7c8f607fa4e0ef46da5`(byte = canonical) | `template["Input (data SHA, split SHA)"].file_hashes` |
| 非 TEST 数据文件 `candidates.json` | `e5d15c9952d8124f2b246ffc76e655be9bf3b0193f048bd8368671d71a6f3705`(byte = canonical) | `template["Input (data SHA, split SHA)"].file_hashes` |
| 非 TEST 数据文件 `dev_qa.jsonl` | `9761eb60d6c9155c2f56394aa228b1e9dfea0ae3926ab50cb21d903108bc7fde`(byte = canonical) | `template["Input (data SHA, split SHA)"].file_hashes` |
| 非 TEST 数据文件 `facts.jsonl` | `e05561ac2d49dcc3c8f59743c5df64151983a540a32ae135fd1b10f5e0fdc828`(byte = canonical) | `template["Input (data SHA, split SHA)"].file_hashes` |
| 非 TEST 数据文件 `general_dev.jsonl` | `957666920c91ef5b9328984d26ed0628c8a80b439d461bea49b54c2235635e73`(byte = canonical) | `template["Input (data SHA, split SHA)"].file_hashes` |
| 非 TEST 数据文件 `train_F.jsonl` | `3aa9ab3ca313c0a1113b91e927af51342c915e3e40dd2f20992f3d9e59b0e373`(byte = canonical) | `template["Input (data SHA, split SHA)"].file_hashes` |
| 非 TEST 数据文件 `train_S.jsonl` | `686fdd2f62edc2115b74a8074a305ddd09b99f11d4f8a267bc80b61c7f73bc1e`(byte = canonical) | `template["Input (data SHA, split SHA)"].file_hashes` |
| 非 TEST 数据文件 `train_Y.jsonl` | `c7430cadb2b06dd5c144af381a8183d4c186f27f2b5acfa9d8d39da0b7626d15`(byte = canonical) | `template["Input (data SHA, split SHA)"].file_hashes` |
| 内容哈希 `anchor_texts` | `8828bc4fcc5a3552778839f97909f072050431dd6f74dd08ef47602da11b2408` | `…Input….content_hashes`;selection_freeze_record.json `data_content_hashes` = `8828bc4fcc5a3552778839f97909f072050431dd6f74dd08ef47602da11b2408` |
| 内容哈希 `candidates` | `e5d15c9952d8124f2b246ffc76e655be9bf3b0193f048bd8368671d71a6f3705` | `…Input….content_hashes`;selection_freeze_record.json `data_content_hashes` = `e5d15c9952d8124f2b246ffc76e655be9bf3b0193f048bd8368671d71a6f3705` |
| 内容哈希 `facts` | `406c8801c5b69ed235cbe516658ad9ee3e3a8cfe8e4e348a0c1fd7952f2e6b97` | `…Input….content_hashes`;selection_freeze_record.json `data_content_hashes` = `406c8801c5b69ed235cbe516658ad9ee3e3a8cfe8e4e348a0c1fd7952f2e6b97` |
| 内容哈希 `train_S` | `686fdd2f62edc2115b74a8074a305ddd09b99f11d4f8a267bc80b61c7f73bc1e` | `…Input….content_hashes`;selection_freeze_record.json `data_content_hashes` = `686fdd2f62edc2115b74a8074a305ddd09b99f11d4f8a267bc80b61c7f73bc1e` |
| 模型权重 `model-00001-of-00002.safetensors` | `169ad53ec313c3a34b06c0809216e4fc072cce444a5d4ff2b59690d064130ed5` | `…Input….model_files_sha256`;command_output/fetch.txt |
| 模型权重 `model-00002-of-00002.safetensors` | `912becff8d60672aa8628ef08c05898d9adf17c2ad4ae3caf99b065622fdeff9` | `…Input….model_files_sha256`;command_output/fetch.txt |
| TEST 文件 `general_test.jsonl` | `41e4ad29cadce84c02da6b8d469107804a2145b3eaa046a569125bf31a13ec44` | st10_record.json `test_files_sha256`;test_evaluation_marker.json 同字段 |
| TEST 文件 `test_qa.jsonl` | `da600cc14362efcdcac2df461b093c3416a6fef10c51299bdcad067ee930a25b` | st10_record.json `test_files_sha256`;test_evaluation_marker.json 同字段 |
<!-- END hashes -->

<!-- FRAGMENT checkpoints -->
| 模型 | state_sha256 | 出处 |
|---|---|---|
| N | `ecf6f12a3a3e32e4dd2a9e60957807efc5e32ab1f3d0daeaec4173ba40b781be` | step3_record.json `N.state_sha256`;test_evaluation_marker.json `checkpoints.N` |
| A-A1-seed101 | `76fece93d2fb07bb226eab6ba512a13663f2495119a262e91229a0c1f5aa46dd` | selection_freeze_record.json `checkpoints.A-A1-seed101` |
| A-A2-seed101 | `cd8f455638d10ec83a5e9b1fa2c5156da9adbe6236cbce6641bc6346ead6c752` | selection_freeze_record.json `checkpoints.A-A2-seed101` |
| A-A3-seed101 | `fc71e8c460e7ebcefd0ae3a98f2e5651be7016f3c52aa4d32c1c6b4b58899151` | selection_freeze_record.json `checkpoints.A-A3-seed101` |
| A-A4-seed101 | `478e1446a32f281bfeb08e0df2cb88c36717178b46ff5b2bebe2d9b52696a590` | selection_freeze_record.json `checkpoints.A-A4-seed101` |
| A-A5-seed101 | `b234b8f81e83fad9b5b8e72f327807223d784b3e0f587e18aecce7a5d4592104` | selection_freeze_record.json `checkpoints.A-A5-seed101` |
| A-A5-seed202 | `5a71476c5ed3a068f5f7bc338fcf277a8c26ffbb7437323d8afa66ad7d596cb0` | selection_freeze_record.json `checkpoints.A-A5-seed202` |
| A-A5-seed303 | `ea15b5e21c92a7f6ba9f7fb92f89eee0be0e3c4cb84654e0db705326098c6cb9` | selection_freeze_record.json `checkpoints.A-A5-seed303` |
| A-A6-seed101 | `0d4b892bcd1d961f9f3be595feb5d2d1a5c2075c23a6669611eab18ed507b7e7` | selection_freeze_record.json `checkpoints.A-A6-seed101` |
| F-F1-seed101 | `5cdd867b3dd9eae243fd16bcca1a7f36f7e559f752d8a79956b011168e6b639b` | selection_freeze_record.json `checkpoints.F-F1-seed101` |
| F-F2-seed101 | `1f00146392e1ad2340f54b280c3d2ef23a0e9e6bba88d2917456d02f1b501a73` | selection_freeze_record.json `checkpoints.F-F2-seed101` |
| F-F3-seed101 | `afb6c0634faf0ec8a7474ac3f63c47863802f8fc72eb2d5bec2ee5f28458973e` | selection_freeze_record.json `checkpoints.F-F3-seed101` |
| F-F3-seed202 | `ad41f101198aecf4164ab1de3233f06ada9dabfd2c64b390ddc71d8efef2a3ac` | selection_freeze_record.json `checkpoints.F-F3-seed202` |
| F-F3-seed303 | `5a22ec7e51d28000e5b63281ea6f4201ea9ee3b907dcf0851da8b2608a0805f4` | selection_freeze_record.json `checkpoints.F-F3-seed303` |
| F-F4-seed101 | `63d9601ab88613936194929b4fa98b768b527e3383ea04904d2add71313c6ecd` | selection_freeze_record.json `checkpoints.F-F4-seed101` |
| F-F5-seed101 | `f21f295657ee3eff1734f3e76fcb6d1d3d2eb45e583b049d10a2abbcfce3f7a2` | selection_freeze_record.json `checkpoints.F-F5-seed101` |
| F-F6-seed101 | `920479e77c1b4fe9bf2c3c470b02e3451ad8543287608b2fa55fc2c5cbb18e3c` | selection_freeze_record.json `checkpoints.F-F6-seed101` |
| L-L1-seed101 | `1e9098e2b930c822cd693ea14ec1f9c60f531d4a0a4e339dd5db63ae14a9e0e6` | selection_freeze_record.json `checkpoints.L-L1-seed101` |
| L-L2-seed101 | `74cd9ed0f6bcae7ee0ef084700f6b1dc6f510940d6176a500dc5313d8b3b4a70` | selection_freeze_record.json `checkpoints.L-L2-seed101` |
| L-L3-seed101 | `2ed32ffd352314b5e5d4f49232652924433fe5e7c1aabf3bb4e45d8d61a42596` | selection_freeze_record.json `checkpoints.L-L3-seed101` |
| L-L4-seed101 | `32f21dd900257c4a7ce2f85cae495eb4354b1a6c42ec34f4aa982b7afa34d263` | selection_freeze_record.json `checkpoints.L-L4-seed101` |
| L-L5-seed101 | `b9ab822f0b69b11da26fa60a7d49f376f888289f871cf660b767e157cc8ba8b6` | selection_freeze_record.json `checkpoints.L-L5-seed101` |
| L-L6-seed101 | `db187c84b2f15c5327692c5ee6e3ea73e24e4f09dd48ec6b1e0d6d0561508618` | selection_freeze_record.json `checkpoints.L-L6-seed101` |
| L-L6-seed202 | `f4f88e8e9577c702922986d667a9114ab3d059fbe168819bd95735793d9f193f` | selection_freeze_record.json `checkpoints.L-L6-seed202` |
| L-L6-seed303 | `6b079e2c70431be41a2463d0bf59af52b1bd0f34232f0e6bb8f5bad2676eba7f` | selection_freeze_record.json `checkpoints.L-L6-seed303` |
| S-F3-seed101 | `c770034ed5077002c172b0ff8b377eb045fc14403648eac98df98693d6bd5b65` | selection_freeze_record.json `checkpoints.S-F3-seed101` |
| S-F3-seed202 | `0894bc8afc66cae84e458cb582482f0f37e49d17ce687f0aea72728e973b7d74` | selection_freeze_record.json `checkpoints.S-F3-seed202` |
| S-F3-seed303 | `757be325be228767f6fd0f7c3b9e3dbc0fe2cc623e79d20775fe74dc66f9748b` | selection_freeze_record.json `checkpoints.S-F3-seed303` |
| Y-F3-seed101 | `1062fd84d8756518672b7136a1e3105e3eb08684e2e893d59fcb5b4568172631` | selection_freeze_record.json `checkpoints.Y-F3-seed101` |
| Y-F3-seed202 | `113e0ae3adb0ddf0d4f427f49ef11ba88b4b0251c3961e4589b6a60b87e52412` | selection_freeze_record.json `checkpoints.Y-F3-seed202` |
| Y-F3-seed303 | `40b594f326337870a02e4a3895eb5e06e2b5aa2eff791e4ab8645e8a20c4eaea` | selection_freeze_record.json `checkpoints.Y-F3-seed303` |
<!-- END checkpoints -->

<!-- FRAGMENT gate0 -->
| 编号 | 门槛(协议第 8 节) | 实测值 | 出处(results/) | 代码判定 |
|---|---|---|---|---|
| G0.1 | 泄漏检查 L1–L6 全部在上限内 | L1 0(上限 0); L2 0.2(上限 0.25); L3a 0(上限 0); L3b 0(上限 0); L4 0(上限 0); L5 0(上限 0); L6 0(上限 0);结果 PASS,over_limit [] | step2_record.json `leakage.checks.*`、`leakage.result`;step7_record.json `values.G0.1` | True |
| G0.2 | 所有损失、分数、NLL 为有限值 | all_finite True,nonfinite [] | step7_record.json `values.G0.2` | True |
| G0.3 | Acc(N, DEV-QA, learned) ∈ [0.15, 0.35];每个 stratum ∈ [0.10, 0.40];Acc(N, DEV-QA, unread) ∈ [0.10, 0.40];Acc_CB(N) ∈ [0.15, 0.35] | learned 0.2958;natural 0.2500;random 0.3417;unread 0.2750;Acc_CB 0.2750 | step7_record.json `values.G0.3` | True |
| G0.4 | Acc_CB(F) ≥ 0.90,3 个种子 | 101: 1.0000;202: 1.0000;303: 1.0000 | step7_record.json `values.G0.4.acc_cb_by_seed` | True |
| G0.5 | seed-average Acc(F, DEV-QA, learned) ≥ 0.70;seed-average Δ(F−N) 95% CI 下界 > 0;每个种子 Δ(F−N) > 0 | Acc 0.9236;Δ(F−N) avg 113/180 (0.6278) [0.5486, 0.7069];每个种子 0.6333 / 0.6333 / 0.6167 | step7_record.json `values.G0.5.acc_avg`、`.delta_avg`、`.delta_by_seed` | True |
| G0.6 | seed-average Δ(S−N) 点估计 ≤ +0.05 且 95% CI 上界 ≤ +0.12 | -4/45 (-0.0889) [-0.1722, -0.0056] | step7_record.json `values.G0.6.delta_avg` | True |
| G0.7 | seed-average Δ(Y−N) 点估计 ≤ +0.05 且 95% CI 上界 ≤ +0.12 | -19/720 (-0.0264) [-0.1153, 0.0625] | step7_record.json `values.G0.7.delta_avg` | True |
| G0.8 | 复现:候选分数差 ≤ 1e-4;预测相同(最高两候选差 ≤ 1e-4 时允许不同);通用窗口 NLL 差 ≤ 1e-5 | 种子 101:items 440,max_score_diff 0.0,max_nll_diff 0.0,允许的预测差 0,不允许的预测差 0 个; 种子 202:items 440,max_score_diff 0.0,max_nll_diff 0.0,允许的预测差 0,不允许的预测差 0 个; 种子 303:items 440,max_score_diff 0.0,max_nll_diff 0.0,允许的预测差 0,不允许的预测差 0 个 | step7_record.json `values.G0.8.checkpoints` | True |
| G0.9 | seed-average Acc(F, DEV-QA, learned) ≤ 0.95 | 0.9236 | step7_record.json `values.G0.9.acc_avg` | True |
| G0.10 | 能估计 E1-V1 的规模:σ_d 有限,按公式算出所需 fact 数 | L−F:σ_d 0.1782 [0.1400, 0.2116],n_max 141;A−F:σ_d 0.2320 [0.1898, 0.2709],n_max 231;planning_n 231(数值见下节) | step7_record.json `values.G0.10` | True |

Gate 0 状态:`PASS`(step7_record.json `gate0.gate0_status`;gate0_record.json `gate0.gate0_status` = `PASS`;`reasons` [])。
<!-- END gate0 -->

<!-- FRAGMENT test -->
| 编号 | 门槛(协议第 8 节) | 实测值 | 出处(results/test_evaluation_result.json) | 代码判定 |
|---|---|---|---|---|
| T1 | seed-average Acc(F, TEST-QA, learned) ≥ 0.70,且 seed-average Δ(F−N) 95% CI 下界 > 0 | Acc 0.9296;Δ(F−N) avg 719/1080 (0.6657) [0.5991, 0.7315] | `values.T1.acc_avg`、`values.T1.delta_avg` | True |
| T2 | S、Y 在 TEST-QA 上满足 G0.6、G0.7 的数值(点估计 ≤ +0.05 且 CI 上界 ≤ +0.12) | Δ(S−N) avg -53/1080 (-0.0491) [-0.1241, 0.0269];Δ(Y−N) avg -1/1080 (-0.0009) [-0.0806, 0.0796] | `values.T2.S.delta_avg`、`values.T2.Y.delta_avg` | True |
| T3 | N 在 TEST-QA 上满足 G0.3 的同样范围(含 Acc_CB(N),解释 B24) | learned 0.2639;natural 0.2222;random 0.3056;unread 0.3250;Acc_CB 0.2750 | `values.T3` | True |

最终状态:`PASS`(test_evaluation_result.json `final.final_status`;`final.reasons` [];experiment_record_test-evaluate_20261128T072505Z.json `template.Status` = `PASS`)。
<!-- END test -->

<!-- FRAGMENT comparisons -->
| 比较 | split | 101 | 202 | 303 | seed-average | 出处 |
|---|---|---|---|---|---|---|
| Δ(F−N) | DEV | 19/30 (0.6333) [0.5500, 0.7167] | 19/30 (0.6333) [0.5500, 0.7125] | 37/60 (0.6167) [0.5332, 0.6958] | 113/180 (0.6278) [0.5486, 0.7069] | step7_record.json `comparisons.F-N:<seed>` |
| Δ(F−N) | TEST | 27/40 (0.6750) [0.6056, 0.7417] | 2/3 (0.6667) [0.5972, 0.7361] | 59/90 (0.6556) [0.5833, 0.7306] | 719/1080 (0.6657) [0.5991, 0.7315] | test_evaluation_result.json `comparisons.F-N:<seed>` |
| Δ(S−N) | DEV | -5/48 (-0.1042) [-0.2083, 0.0000] | -9/80 (-0.1125) [-0.2000, -0.0208] | -1/20 (-0.0500) [-0.1500, 0.0500] | -4/45 (-0.0889) [-0.1722, -0.0056] | step7_record.json `comparisons.S-N:<seed>` |
| Δ(S−N) | TEST | -7/120 (-0.0583) [-0.1500, 0.0306] | -11/180 (-0.0611) [-0.1444, 0.0194] | -1/36 (-0.0278) [-0.1111, 0.0556] | -53/1080 (-0.0491) [-0.1241, 0.0269] | test_evaluation_result.json `comparisons.S-N:<seed>` |
| Δ(Y−N) | DEV | -1/24 (-0.0417) [-0.1417, 0.0583] | -1/80 (-0.0125) [-0.1042, 0.0833] | -1/40 (-0.0250) [-0.1167, 0.0708] | -19/720 (-0.0264) [-0.1153, 0.0625] | step7_record.json `comparisons.Y-N:<seed>` |
| Δ(Y−N) | TEST | -1/180 (-0.0056) [-0.0972, 0.0861] | 1/360 (0.0028) [-0.0862, 0.0917] | 0 (0.0000) [-0.0861, 0.0889] | -1/1080 (-0.0009) [-0.0806, 0.0796] | test_evaluation_result.json `comparisons.Y-N:<seed>` |
| Δ(L−F) | DEV | -13/240 (-0.0542) [-0.1167, 0.0042] | 1/20 (0.0500) [0.0125, 0.0917] | 1/20 (0.0500) [0.0000, 0.1042] | 11/720 (0.0153) [-0.0167, 0.0472] | step7_record.json `comparisons.L-F:<seed>` |
| Δ(L−F) | TEST | -7/120 (-0.0583) [-0.1167, -0.0028] | 19/360 (0.0528) [0.0111, 0.0972] | 1/15 (0.0667) [0.0194, 0.1167] | 11/540 (0.0204) [-0.0102, 0.0528] | test_evaluation_result.json `comparisons.L-F:<seed>` |
| Δ(A−F) | DEV | -1/30 (-0.0333) [-0.0875, 0.0167] | -7/48 (-0.1458) [-0.2083, -0.0875] | -1/8 (-0.1250) [-0.2042, -0.0500] | -73/720 (-0.1014) [-0.1444, -0.0611] | step7_record.json `comparisons.A-F:<seed>` |
| Δ(A−F) | TEST | -1/180 (-0.0056) [-0.0444, 0.0306] | -7/72 (-0.0972) [-0.1528, -0.0417] | -29/360 (-0.0806) [-0.1472, -0.0167] | -11/180 (-0.0611) [-0.0963, -0.0278] | test_evaluation_result.json `comparisons.A-F:<seed>` |
<!-- END comparisons -->

<!-- FRAGMENT spill -->
| arm | split | 101 | 202 | 303 | seed-average | 出处 |
|---|---|---|---|---|---|---|
| F | DEV | 1/40 (0.0250) [-0.1375, 0.1750] | 1/80 (0.0125) [-0.0875, 0.1250] | 0 (0.0000) [-0.1375, 0.1375] | 1/80 (0.0125) [-0.1000, 0.1292] | step7_record.json `comparisons.Spill-F:<seed>` |
| F | TEST | 0 (0.0000) [-0.1333, 0.1417] | -1/30 (-0.0333) [-0.1583, 0.0917] | -1/30 (-0.0333) [-0.1583, 0.0917] | -1/45 (-0.0222) [-0.1222, 0.0778] | test_evaluation_result.json `comparisons.Spill-F:<seed>` |
| L | DEV | 3/40 (0.0750) [-0.1000, 0.2500] | -1/80 (-0.0125) [-0.2125, 0.1750] | -1/20 (-0.0500) [-0.2000, 0.1000] | 1/240 (0.0042) [-0.1417, 0.1500] | step7_record.json `comparisons.Spill-L:<seed>` |
| L | TEST | 1/40 (0.0250) [-0.1500, 0.2000] | -7/120 (-0.0583) [-0.2250, 0.1167] | -7/60 (-0.1167) [-0.2667, 0.0333] | -1/20 (-0.0500) [-0.1861, 0.0778] | test_evaluation_result.json `comparisons.Spill-L:<seed>` |
| A | DEV | 1/40 (0.0250) [-0.1125, 0.1625] | 0 (0.0000) [-0.1250, 0.1250] | -1/40 (-0.0250) [-0.1625, 0.1000] | 0 (0.0000) [-0.1125, 0.1208] | step7_record.json `comparisons.Spill-A:<seed>` |
| A | TEST | -1/40 (-0.0250) [-0.1583, 0.1083] | -1/40 (-0.0250) [-0.1417, 0.1000] | -1/15 (-0.0667) [-0.1917, 0.0500] | -7/180 (-0.0389) [-0.1528, 0.0694] | test_evaluation_result.json `comparisons.Spill-A:<seed>` |
| S | DEV | 1/80 (0.0125) [-0.1250, 0.1500] | 1/10 (0.1000) [-0.0625, 0.2625] | -1/40 (-0.0250) [-0.1750, 0.1250] | 7/240 (0.0292) [-0.0958, 0.1583] | step7_record.json `comparisons.Spill-S:<seed>` |
| S | TEST | -1/20 (-0.0500) [-0.1833, 0.0833] | 1/40 (0.0250) [-0.1333, 0.1833] | -3/40 (-0.0750) [-0.2167, 0.0667] | -1/30 (-0.0333) [-0.1528, 0.0833] | test_evaluation_result.json `comparisons.Spill-S:<seed>` |
| Y | DEV | 3/80 (0.0375) [-0.0875, 0.1625] | 1/20 (0.0500) [-0.0875, 0.2000] | 1/20 (0.0500) [-0.1125, 0.2125] | 11/240 (0.0458) [-0.0792, 0.1708] | step7_record.json `comparisons.Spill-Y:<seed>` |
| Y | TEST | -7/120 (-0.0583) [-0.1833, 0.0667] | -1/120 (-0.0083) [-0.1500, 0.1333] | 1/60 (0.0167) [-0.1333, 0.1667] | -1/60 (-0.0167) [-0.1389, 0.1056] | test_evaluation_result.json `comparisons.Spill-Y:<seed>` |

Prior(DEV) = Acc(N, DEV-QA, unread) = 0.2750(step3_record.json `N.summary.acc_dev_unread`);Prior(TEST) = 0.3250(test_evaluation_result.json `summaries.N.acc_test_unread`)。
<!-- END spill -->

<!-- FRAGMENT per_model -->
| 模型 | DEV Acc learned | DEV Acc_CB | DEV EM learned | DEV EM unread | DEV FPR | TEST Acc learned | TEST EM learned | TEST EM unread | TEST FPR |
|---|---|---|---|---|---|---|---|---|---|
| N | 0.2958 | 0.2750 | 0.0000 | 0.0000 | 0.2000 | 0.2639 | 0.0000 | 0.0000 | 0.2000 |
| F-F3-seed101 | 0.9292 | 1.0000 | 0.4583 | 0.0000 | 0.2750 | 0.9389 | 0.5389 | 0.0000 | 0.2750 |
| F-F3-seed202 | 0.9292 | 1.0000 | 0.5000 | 0.0000 | 0.2000 | 0.9306 | 0.6333 | 0.0000 | 0.2250 |
| F-F3-seed303 | 0.9125 | 1.0000 | 0.7417 | 0.0000 | 0.2500 | 0.9194 | 0.7806 | 0.0000 | 0.2500 |
| L-L6-seed101 | 0.8750 | 1.0000 | 0.5333 | 0.0000 | 0.3500 | 0.8806 | 0.6278 | 0.0000 | 0.3500 |
| L-L6-seed202 | 0.9792 | 1.0000 | 0.8125 | 0.0000 | 0.2250 | 0.9833 | 0.8444 | 0.0000 | 0.2250 |
| L-L6-seed303 | 0.9625 | 1.0000 | 0.7417 | 0.0000 | 0.1500 | 0.9861 | 0.7750 | 0.0000 | 0.1750 |
| A-A5-seed101 | 0.8958 | 1.0000 | 0.0375 | 0.0000 | 0.3000 | 0.9333 | 0.1472 | 0.0000 | 0.2750 |
| A-A5-seed202 | 0.7833 | 1.0000 | 0.1375 | 0.0000 | 0.2250 | 0.8333 | 0.2472 | 0.0000 | 0.2500 |
| A-A5-seed303 | 0.7875 | 1.0000 | 0.1125 | 0.0000 | 0.2500 | 0.8389 | 0.2083 | 0.0000 | 0.2500 |
| S-F3-seed101 | 0.1917 | 0.1833 | 0.0000 | 0.0000 | 0.2250 | 0.2056 | 0.0000 | 0.0000 | 0.2000 |
| S-F3-seed202 | 0.1833 | 0.1583 | 0.0000 | 0.0000 | 0.3500 | 0.2028 | 0.0028 | 0.0000 | 0.3000 |
| S-F3-seed303 | 0.2458 | 0.1417 | 0.0000 | 0.0000 | 0.1750 | 0.2361 | 0.0000 | 0.0000 | 0.2250 |
| Y-F3-seed101 | 0.2542 | 0.2333 | 0.0000 | 0.0000 | 0.2750 | 0.2583 | 0.0028 | 0.0000 | 0.2000 |
| Y-F3-seed202 | 0.2833 | 0.2917 | 0.0000 | 0.0000 | 0.2750 | 0.2667 | 0.0000 | 0.0000 | 0.2750 |
| Y-F3-seed303 | 0.2708 | 0.2500 | 0.0000 | 0.0000 | 0.3000 | 0.2639 | 0.0000 | 0.0000 | 0.3000 |

出处:N 的 DEV 值为 step3_record.json `N.summary.*`;其余 DEV 值为 training_runs/<模型>.json `dev.*`(`acc_dev_learned`、`acc_cb`、`em_dev_learned`、`em_dev_unread`、`fpr_dev`);TEST 值为 test_evaluation_result.json `summaries.<模型>.*`(`acc_test_learned`、`em_test_learned`、`em_test_unread`、`fpr_test`)。

S 在它自己的置换映射上的正确率(step7_record.json `s_own_mapping`):种子 101:DEV learned 0.9375,TRAIN 闭卷 1.0000;种子 202:DEV learned 0.8292,TRAIN 闭卷 1.0000;种子 303:DEV learned 0.7542,TRAIN 闭卷 1.0000。
<!-- END per_model -->

<!-- FRAGMENT dnll -->
| run | 配置 | dNLL(DEV) | PPL_degradation%(DEV) |
|---|---|---|---|
| F-F1-seed101 | learning_rate=1e-05, weight_decay=0.0 | 1.33567 | 280.25 |
| F-F2-seed101 | learning_rate=1e-05, weight_decay=0.1 | 1.71853 | 457.63 |
| F-F3-seed101 | learning_rate=3e-05, weight_decay=0.0 | 1.32006 | 274.36 |
| F-F4-seed101 | learning_rate=3e-05, weight_decay=0.1 | 1.26318 | 253.67 |
| F-F5-seed101 | learning_rate=0.0001, weight_decay=0.0 | 3.88915 | 4786.94 |
| F-F6-seed101 | learning_rate=0.0001, weight_decay=0.1 | 5.55021 | 25629.11 |
| L-L1-seed101 | learning_rate=0.0001, rank=8, weight_decay=0.0 | 1.58846 | 389.62 |
| L-L2-seed101 | learning_rate=0.0001, rank=32, weight_decay=0.0 | 2.67704 | 1354.20 |
| L-L3-seed101 | learning_rate=0.0003, rank=8, weight_decay=0.0 | 2.45315 | 1062.49 |
| L-L4-seed101 | learning_rate=0.0003, rank=32, weight_decay=0.0 | 2.77005 | 1495.94 |
| L-L5-seed101 | learning_rate=0.001, rank=8, weight_decay=0.0 | 2.30738 | 904.80 |
| L-L6-seed101 | learning_rate=0.001, rank=32, weight_decay=0.0 | 3.54453 | 3362.36 |
| A-A1-seed101 | anchor_lambda=0.3, learning_rate=3e-05, weight_decay=0.0 | -0.08907 | -8.52 |
| A-A2-seed101 | anchor_lambda=1.0, learning_rate=3e-05, weight_decay=0.0 | -0.10387 | -9.87 |
| A-A3-seed101 | anchor_lambda=3.0, learning_rate=3e-05, weight_decay=0.0 | -0.08966 | -8.58 |
| A-A4-seed101 | anchor_lambda=0.3, learning_rate=0.0001, weight_decay=0.0 | 0.12509 | 13.32 |
| A-A5-seed101 | anchor_lambda=1.0, learning_rate=0.0001, weight_decay=0.0 | 0.20142 | 22.31 |
| A-A6-seed101 | anchor_lambda=3.0, learning_rate=0.0001, weight_decay=0.0 | 0.30221 | 35.28 |
| F-F3-seed202 | learning_rate=3e-05, weight_decay=0.0 | 1.08939 | 197.25 |
| F-F3-seed303 | learning_rate=3e-05, weight_decay=0.0 | 1.46587 | 333.13 |
| L-L6-seed202 | learning_rate=0.001, rank=32, weight_decay=0.0 | 3.38227 | 2843.75 |
| L-L6-seed303 | learning_rate=0.001, rank=32, weight_decay=0.0 | 3.95376 | 5113.11 |
| A-A5-seed202 | anchor_lambda=1.0, learning_rate=0.0001, weight_decay=0.0 | 0.22568 | 25.32 |
| A-A5-seed303 | anchor_lambda=1.0, learning_rate=0.0001, weight_decay=0.0 | 0.21353 | 23.80 |
| S-F3-seed101 | learning_rate=3e-05, weight_decay=0.0 | 1.52157 | 357.94 |
| S-F3-seed202 | learning_rate=3e-05, weight_decay=0.0 | 0.98188 | 166.95 |
| S-F3-seed303 | learning_rate=3e-05, weight_decay=0.0 | 0.99084 | 169.35 |
| Y-F3-seed101 | learning_rate=3e-05, weight_decay=0.0 | 2.14499 | 754.19 |
| Y-F3-seed202 | learning_rate=3e-05, weight_decay=0.0 | 1.45756 | 329.55 |
| Y-F3-seed303 | learning_rate=3e-05, weight_decay=0.0 | 1.98432 | 627.41 |

出处:training_runs/<run>.json `dnll`、`ppl_degradation_pct`、`config`(DEV 通用文本 general_dev.jsonl,协议第 5 节)。
<!-- END dnll -->

<!-- FRAGMENT g010 -->
| 比较 | σ_d 点估计 | σ_d p2.5 | σ_d p97.5 | n(δ=0.05),按 σ_d p2.5 / 点 / p97.5 | n(δ=0.10),同 | n(δ=0.15),同 | n_max | 半宽检查(n, 每 stratum, 半宽) |
|---|---|---|---|---|---|---|---|---|
| Δ(L−F) | 0.178169 | 0.140028 | 0.211630 | 62 / 100 / 141 | 16 / 25 / 36 | 7 / 12 / 16 | 141 | 231, 116, 0.022629 |
| Δ(A−F) | 0.232005 | 0.189821 | 0.270890 | 113 / 169 / 231 | 29 / 43 / 58 | 13 / 19 / 26 | 231 | 231, 116, 0.029813 |

planning_n = 231(step7_record.json `values.G0.10.planning_n`);各值出处 step7_record.json `values.G0.10.estimates.<比较>`(`sigma`、`n`、`n_max`、`halfwidth_at_planning_n`、`finite` = True / True)。
<!-- END g010 -->

<!-- FRAGMENT compute -->
| run | steps_run | fact_tokens | anchor_tokens | params_forward | train_flops | anchor_flops | 训练 wall_seconds | checkpoint 保存+哈希+重载 秒 |
|---|---|---|---|---|---|---|---|---|
| F-F1-seed101 | 300 | 37780 | — | 1720574976 | 3.9002e+14 | — | 75.89 | 43.56 |
| F-F2-seed101 | 300 | 37780 | — | 1720574976 | 3.9002e+14 | — | 76.19 | 43.81 |
| F-F3-seed101 | 300 | 37780 | — | 1720574976 | 3.9002e+14 | — | 75.06 | 44.47 |
| F-F4-seed101 | 300 | 37780 | — | 1720574976 | 3.9002e+14 | — | 76.27 | 44.02 |
| F-F5-seed101 | 300 | 37780 | — | 1720574976 | 3.9002e+14 | — | 75.25 | 43.37 |
| F-F6-seed101 | 300 | 37780 | — | 1720574976 | 3.9002e+14 | — | 78.49 | 43.14 |
| L-L1-seed101 | 300 | 37780 | — | 1729291264 | 3.9200e+14 | — | 77.16 | 46.81 |
| L-L2-seed101 | 300 | 37780 | — | 1755440128 | 3.9792e+14 | — | 72.41 | 60.09 |
| L-L3-seed101 | 300 | 37780 | — | 1729291264 | 3.9200e+14 | — | 85.87 | 47.59 |
| L-L4-seed101 | 300 | 37780 | — | 1755440128 | 3.9792e+14 | — | 87.05 | 59.90 |
| L-L5-seed101 | 300 | 37780 | — | 1729291264 | 3.9200e+14 | — | 84.57 | 47.21 |
| L-L6-seed101 | 300 | 37780 | — | 1755440128 | 3.9792e+14 | — | 84.41 | 59.98 |
| A-A1-seed101 | 300 | 37780 | 153590 | 1720574976 | 3.9002e+14 | 2.1141e+15 | 143.63 | 50.68 |
| A-A2-seed101 | 300 | 37780 | 153590 | 1720574976 | 3.9002e+14 | 2.1141e+15 | 144.11 | 44.59 |
| A-A3-seed101 | 300 | 37780 | 153590 | 1720574976 | 3.9002e+14 | 2.1141e+15 | 144.81 | 45.50 |
| A-A4-seed101 | 300 | 37780 | 153590 | 1720574976 | 3.9002e+14 | 2.1141e+15 | 143.74 | 44.89 |
| A-A5-seed101 | 300 | 37780 | 153590 | 1720574976 | 3.9002e+14 | 2.1141e+15 | 149.39 | 43.77 |
| A-A6-seed101 | 300 | 37780 | 153590 | 1720574976 | 3.9002e+14 | 2.1141e+15 | 142.39 | 44.86 |
| F-F3-seed202 | 300 | 37780 | — | 1720574976 | 3.9002e+14 | — | 79.81 | 45.37 |
| F-F3-seed303 | 300 | 37780 | — | 1720574976 | 3.9002e+14 | — | 79.92 | 45.39 |
| L-L6-seed202 | 300 | 37780 | — | 1755440128 | 3.9792e+14 | — | 86.78 | 59.68 |
| L-L6-seed303 | 300 | 37780 | — | 1755440128 | 3.9792e+14 | — | 86.24 | 59.09 |
| A-A5-seed202 | 300 | 37780 | 153590 | 1720574976 | 3.9002e+14 | 2.1141e+15 | 147.17 | 44.15 |
| A-A5-seed303 | 300 | 37780 | 153590 | 1720574976 | 3.9002e+14 | 2.1141e+15 | 143.53 | 44.34 |
| S-F3-seed101 | 300 | 37780 | — | 1720574976 | 3.9002e+14 | — | 81.40 | 42.22 |
| S-F3-seed202 | 300 | 37780 | — | 1720574976 | 3.9002e+14 | — | 80.33 | 44.97 |
| S-F3-seed303 | 300 | 37780 | — | 1720574976 | 3.9002e+14 | — | 81.48 | 43.66 |
| Y-F3-seed101 | 300 | 45200 | — | 1720574976 | 4.6662e+14 | — | 79.71 | 44.43 |
| Y-F3-seed202 | 300 | 45200 | — | 1720574976 | 4.6662e+14 | — | 76.92 | 44.52 |
| Y-F3-seed303 | 300 | 45200 | — | 1720574976 | 4.6662e+14 | — | 75.84 | 42.99 |
| 合计(30 次) | 9000 | 1155660 | 1228720 | — | 1.1976e+16 | 1.6913e+16 | 2915.84 | 1419.05 |

出处:training_runs/<run>.json `steps_run`、`accounting.*`(训练 FLOPs = 6·P·T,A 的锚文本算力单列 = 2·P·T_anchor + 6·P·T_anchor,协议第 10 节、解释 B18)、`checkpoint.seconds.*`(save、hash、reload、hash_after_reload 之和)。合计为本报告对 30 条记录求和(reports/pilot_final/report_tables.txt 第 3 节)。

| 量 | 值 | 出处 |
|---|---|---|
| 累计 GPU wall-clock(formal 结束时) | 6261.27 秒 | experiment_record_formal… `template["Compute accounting …"].gpu_wall_clock_seconds` |
| 累计 GPU wall-clock(test-evaluate 结束时,ST7 读这个量) | 7239.50 秒 = 2.0110 小时(上限 4 小时) | experiment_record_test-evaluate… 同字段 |
| formal 第 1 步耗时 | 3.68 秒 | experiment_record_formal… `…steps.1`;step1_record.json `step_info.seconds` |
| formal 第 2 步耗时 | 70.27 秒 | experiment_record_formal… `…steps.2`;step2_record.json `step_info.seconds` |
| formal 第 3 步耗时 | 45.01 秒 | experiment_record_formal… `…steps.3`;step3_record.json `step_info.seconds` |
| formal 第 4 步耗时 | 915.38 秒 | experiment_record_formal… `…steps.4`;step4_record.json `step_info.seconds` |
| formal 第 5 步耗时 | 2855.87 秒 | experiment_record_formal… `…steps.5`;step5_record.json `step_info.seconds` |
| formal 第 6 步耗时 | 2248.05 秒 | experiment_record_formal… `…steps.6`;step6_record.json `step_info.seconds` |
| formal 第 7 步耗时 | 88.89 秒 | experiment_record_formal… `…steps.7`;step7_record.json `step_info.seconds` |
| formal 第 8 步耗时 | 0.02 秒 | experiment_record_formal… `…steps.8`;step8_record.json `step_info.seconds` |
| 预检(F-F1-seed101 前 20 步)每步平均秒数(不含第 1 步) | 0.2507 | step2_record.json `preflight.summary.mean_seconds_per_step_excluding_first` |
| 预检 tokens/s | 505.27 | step2_record.json `preflight.summary.tokens_per_second` |
| 预检 DEV 评测一次 | 25.59 秒 | step2_record.json `preflight.dev_evaluation_seconds` |
| ST11 预估 | 2.5322 小时 = B17 1.9622 小时 + checkpoint 开销 2051.96 秒(上限 3.5 小时;within bound) | step2_record.json `preflight.st11_estimate_hours`、`.b17_estimate_hours`、`.checkpoint_overhead.seconds`、`.st11_bound_hours`、`.st11` |
| 第 2 步峰值显存 | 34535789568 字节 | step2_record.json `step_info.peak_memory_bytes`(CUDA max_memory_allocated of the step) |
| 第 3 步峰值显存 | 15391566848 字节 | step3_record.json `step_info.peak_memory_bytes`(CUDA max_memory_allocated of the step) |
| 第 4 步峰值显存 | 34535197696 字节 | step4_record.json `step_info.peak_memory_bytes`(CUDA max_memory_allocated of the step) |
| 第 5 步峰值显存 | 46235107328 字节 | step5_record.json `step_info.peak_memory_bytes`(CUDA max_memory_allocated of the step) |
| 第 6 步峰值显存 | 46236459008 字节 | step6_record.json `step_info.peak_memory_bytes`(CUDA max_memory_allocated of the step) |
| 第 7 步峰值显存 | 15391566848 字节 | step7_record.json `step_info.peak_memory_bytes`(CUDA max_memory_allocated of the step) |
| 第 8 步峰值显存 | 67108864 字节 | step8_record.json `step_info.peak_memory_bytes`(CUDA max_memory_allocated of the step) |
<!-- END compute -->

<!-- exit=0 -->
