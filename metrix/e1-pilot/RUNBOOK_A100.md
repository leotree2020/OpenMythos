# METRIX · E1-PILOT · A100 操作手册(RUNBOOK_A100.md)

依据:`tasks/IMPLEMENTATION_TASK_ORDER_V1.md` 第 8 节;协议 v1.1(冻结提交 `87a244db28a901f9e89282b50df76778ab5c2887`,`PROTOCOL_FROZEN`)第 0、7、8、10、11 节;Owner 下达阶段 C 的消息(`tasks/IMPL_C_OWNER_MESSAGE.md`:补充裁决 6,上次阶段 C 指令第 9 项);Review Gate 对 C1 的裁决(2026-11-25,`tasks/IMPL_C1_RULING.md`)第 2、6 项;Review Gate 2026-11-27 的裁决(`tasks/IMPL_C2_OWNER_MESSAGE.md`,记入 `reports/IMPL_C_REPORT.md`)第 1 项;Review Gate 2026-11-27 对 C2、C3 报告所列事项的裁决(`tasks/IMPL_C4_RULING.md`,作用范围:E1 Pilot 直至结束;下称“C4 裁决”)第 1、3–7 项。

本手册只写怎样执行。门槛、超参、种子、哈希一律由代码从冻结文件读取,手册中出现的哈希只用于下载后的人工核对。手册不指定租用平台,由 Owner 选择。

**开始之前必须有 Owner 的指令**:租用 GPU(metrix/CLAUDE.md 第 7 节)。第 3.6 节的 TEST 生成与第 3.8 节的 TEST 评测各需 Owner 另行批准。

**与 metrix/CLAUDE.md 第 4 节的关系**(“环境、下载、冒烟测试先在 CPU 环境完成;租卡后只跑正式流程”):A100 上的依赖安装、输入与权重下载属于正式流程;“租卡后只跑正式流程”指不在租用机器上开发调试(C4 裁决第 3 项)。依赖锁定、输入文件的哈希核对、数据生成与四个冻结哈希、CPU 冒烟测试都已在 CPU 环境完成(`reports/IMPL_A_REPORT.md`、`IMPL_C_REPORT.md`);A100 主机是另一台机器,第 3.1–3.4 节在该机器上按锁定文件安装依赖、下载输入与模型权重,由代码再次核对(模型权重只能在 A100 主机下载:Task Order 红线 2;`run_pilot.py fetch-model` 先做设备检查 ST8)。在租用的机器上只执行本手册的命令:不改代码、不改冻结内容、不做试跑或调试;出现问题时停下,报告 Owner。

**此前裁决的效力**:C4 裁决第 4 项:此前各项“作用范围:本阶段”的裁决(补充裁决 1–6、C1 裁决、Review Gate 2026-11-27 的裁决(`tasks/IMPL_C2_OWNER_MESSAGE.md`)等,本手册引用者)在 A100 运行期间继续有效。

---

## 1. 环境要求

**只租 `nvidia-smi` 显示 CUDA ≥ 13.0(驱动 580 系列及以上)的单张 A100 80GB 机器**(Review Gate 补充裁决 6)。租用前查看平台给出的驱动版本;开机后第一条命令是下面的 `nvidia-smi` 检查,不满足即停止、退租,报告 Owner(不装驱动、不换 CUDA 构建)。

| 项 | 要求 | 检查命令 |
|---|---|---|
| GPU | 一张 NVIDIA A100 80GB:`torch.cuda.get_device_name(0)` 以 `NVIDIA A100` 开头,且 `total_memory ≥ 79 GiB`(协议第 7 节;不满足由 run_pilot.py 判为 ST8 BLOCKED) | `nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv` |
| 驱动与 CUDA | `requirements.lock` 中的 torch 2.11.0(PyPI 的 Linux wheel)基于 CUDA 13.0(`cuda-toolkit 13.0.2`、`nvidia-*-cu13`),主机驱动须支持 CUDA 13.0:`nvidia-smi` 右上角的 “CUDA Version” ≥ 13.0(驱动 580 系列及以上;以 NVIDIA CUDA 13.0 Release Notes 的最低驱动表为准)。不另装 CUDA toolkit,由 wheel 提供(补充裁决 6:不另锁 CUDA 12.x 构建) | `nvidia-smi`;安装后 `python -c "import torch; print(torch.version.cuda, torch.cuda.is_available())"` 应为 `13.0 True` |
| 同一台机器 | 从第一次加载模型到 TEST 评测结束都在同一张卡上:设备全名在第一次加载模型时写入 `<work>/device_ledger.json`,此后每次训练或评测开始时比对(ST9,整批作废)。formal 与 test-evaluate 之间不要换机器;checkpoint 也只在这台机器上 | — |
| 系统 | Linux x86_64,glibc ≥ 2.28(锁定文件按 manylinux_2_28 解析) | `ldd --version` |
| Python | CPython **3.13.18**(锁定文件第 2 行;`tests/test_environment.py` 核对)。主机没有这个精确版本时,用 uv 安装它(C4 裁决第 6 项;第 3.2 节的 3.2a);uv 装不到即停下报告 Owner,不用其他版本 | `python3.13 --version`;没有时见 3.2a |
| 磁盘 | `<work>` 所在分区至少 **300 GB** 可用:30 个最终 checkpoint 各约 6.9 GB(FP32 全模型,约 207 GB;一个都不删,metrix/CLAUDE.md 第 7 节)+ 预检 checkpoint 6.9 GB + 模型 4.1 GB + 依赖约 6 GB | `df -h <work>` |
| 内存 | 建议 ≥ 64 GB(加载模型与 checkpoint 时在 CPU 上暂存一份 float32 权重) | `free -g` |
| 网络 | github.com(克隆、推送)、huggingface.co(分词器、锚文本 parquet、模型)、pypi.org / files.pythonhosted.org(依赖;3.2a 的 uv);只在 3.2a 时:uv 下载 CPython 3.13.18 的主机(`uv python list 3.13.18 --only-downloads --show-urls` 显示;本阶段为 releases.astral.sh)及其重定向目标。Claude Code 本身所需的网络另见下文 | — |
| Git | 非浅克隆;能向 `leotree2020/OpenMythos` 的 `metrix-e1-pilot-protocol-v1` 直接推送(快进)的凭据;提交者身份 `user.name`、`user.email` | `git config user.name; git config user.email` |
| 终端 | 长命令在 `tmux`(或 `screen`)会话中运行:SSH 断开时前台进程会被 SIGHUP 结束,不会写实验记录 | `tmux -V` |

**GitHub 上的分支设置(C1 裁决第 6 项)**:Owner 已为 `metrix-e1-pilot-protocol-v1` 设置禁止 force push、禁止删除、允许直接推送。TEST 闸门的“只评一次”以此为前提(远端分支不丢提交)。开始前 Owner 确认该设置仍在。metrix/CLAUDE.md 第 6 节的“受保护分支”指 main;在本分支直接快进推送是既定做法。

**在 A100 主机上运行 Claude Code(C4 裁决第 7 项)**:Executor(Claude Code)在 A100 主机上从仓库根目录(第 3.1 节克隆的 `OpenMythos/`)、在 `metrix-e1-pilot-protocol-v1` 的检出上启动,使 `CLAUDE.md`、`metrix/CLAUDE.md` 与两个 agent 定义 `.claude/agents/code-reviewer.md`、`.claude/agents/data-auditor.md` 在会话开始时直接加载。

- 前提:Claude Code 已在该主机安装并登录(由 Owner 完成;它本身所需的网络以 Claude Code 的文档为准,不在上表“网络”一行之内)。
- 顺序:由 Owner(或 Owner 指定的人)在 `tmux new -s metrix` 建立的 tmux 会话中做第 3.0 节(含建立变量文件 `~/metrix-vars.sh`)与第 3.1 节的克隆、检出和提交者身份;然后在同一个 tmux 会话中 `source ~/metrix-vars.sh && cd "$REPO"`,启动 Claude Code。Claude Code 若是在别的目录或别的分支上启动的,退出后按此重新启动(agent 定义只在会话开始时加载)。
- 启动后先核对并把输出追加到 `env.txt`:`pwd` 与 `git rev-parse --show-toplevel` 相同,`git branch --show-current` 为 `metrix-e1-pilot-protocol-v1`,`ls .claude/agents/` 列出两个文件;两个 agent 出现在会话的 agent 列表中,其 tools 行与仓库文件 frontmatter 的 tools 行相同。不一致即停下,报告 Owner。每次调用审查 subagent 之前仍按 metrix/CLAUDE.md 第 5 节第 6 条比对 frontmatter,调用文字第一句用固定句。
- 变量:第 3 节的命令用到的 `WORK`、`INPUTS`、`E`、`REPO`、`PY313`、`PY` 都写在 `~/metrix-vars.sh` 中(第 3.0–3.2 节逐步追加)。不依赖上一条命令留下的 shell 状态:Claude Code 的每一次命令调用、每个 tmux 窗口中的命令,都以 `source ~/metrix-vars.sh && cd "$REPO" && ` 开头(第 3.1 节追加 `REPO` 之前只 `source`)。
- 长命令:可能超过工具超时的命令(第 3.2 节整段,含 3.2a;第 3.4 节的下载;`formal`、`test-generate`、`test-evaluate`)不作为有超时的前台命令运行,而在 tmux 的单独窗口中运行。不把含引号或多行的命令拼进 `send-keys`:先把要运行的命令原样写入脚本文件 `$WORK/command_output/<名称>.sh`,第一行为 `set -o pipefail; source ~/metrix-vars.sh && cd "$REPO" || exit 1`;再只发送一行,例如 `source ~/metrix-vars.sh && tmux new-window -d -t metrix -n <名称> -c "$REPO" && tmux send-keys -t metrix:<名称> "bash $WORK/command_output/<名称>.sh; echo exit=\$? >> $WORK/command_output/<名称>.end" Enter`。`<名称>` 各不相同(如 `s3_2`、`s3_4`、`formal`、`test_generate`、`test_evaluate`)。Claude Code 读取 `tee` 写出的输出文件(第 3.2 节写在 `env.txt`)跟踪进度,也可 `tmux capture-pane -p -t metrix:<名称>`;`<名称>.end` 出现才表示命令已结束,其中是脚本的退出码(`pipefail` 下即被 `tee` 的命令的退出码)。`.end` 不存在时视为仍在运行或状态不明。每个长命令只发送一次;中断、失败或状态不明之后是否重发,都由 Owner 决定,Executor 不自行重发;`test-generate` 与 `test-evaluate` 不得重跑(第 4 节)。

## 2. 需要下载的内容及其哈希

前 6 项由第 3.4 节的命令下载;第 7 项是仓库内文件。这 7 项是冻结值(`DATA_MANIFEST.json`),由代码核对:第 1 步由 `metrix_e1.data` 的 generate 核对输入,第 2 步起每一步开始时的 ST12(`data.verify`)再核对;不一致即 ST12 BLOCKED。模型的 `config.json` 与两个 safetensors 不是冻结值,代码核对的是下载元数据中的 revision(`pilot.check_model_dir`),表中的哈希供人工复核。

| 内容 | 位置 | SHA-256 | 核对方式 |
|---|---|---|---|
| Qwen/Qwen3-1.7B @ `70d244cc86ccca08cf5af4e1e306ecf908b1ad5e` 的 `tokenizer.json` | `<inputs>/qwen_tokenizer/` | `aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4` | `metrix_e1.data fetch` 下载并核对(DATA_MANIFEST.json model.tokenizer) |
| 同上 `tokenizer_config.json`(含 chat template) | 同上 | `d5d09f07b48c3086c508b30d1c9114bd1189145b74e982a265350c923acd8101` | 同上 |
| 同上 `vocab.json` | 同上 | `ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910` | 同上 |
| 同上 `merges.txt` | 同上 | `8831e4f1a044471340f7c0a83d7bd71306a5b867e95fd870f74d0c5308a904d5` | 同上 |
| parcae 分词器 `SandyResearch/parcae-tokenizer@6247b5d0592876b73660f34c2dd16c9db9e9045c` 的 `tokenizer.json` | `<inputs>/parcae_tokenizer/` | `e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77` | 同上(DATA_MANIFEST.json general_text) |
| 锚文本 `SandyResearch/fineweb-edu-shuffled@4d1138c0e4d51d98813997ce3560e05a32bf91de` 的 `data/sample-100BT/train/shard_00000.parquet` | `<inputs>/anchor_source/…` | `6a3450ea745ee6b6830c09819c0f2c72682eba443022de595bcb50ceb3092c22` | 同上(DATA_MANIFEST.json anchor_text) |
| 通用文本 `research/mini_mythos/stage1/results/r1/eval_sets.jsonl` | 仓库内(不下载) | `8816fe5a39d8b89e8c4203bf7d660e798faa471d2b72b5ce43c411cf5925a155` | 第 1 步由 `metrix_e1.data` 的 generate 核对,第 2 步起每步开始时的 ST12(`data.verify`)核对(DATA_MANIFEST.json general_text) |
| 模型 `config.json` | `<inputs>/qwen_model/` | `1ddb5b89ebc90dcb417a45c213d818577e65976454d29385c8f6140771d95197` | `metrix_e1.train fetch-config` 打印实际值;表中的值是本阶段在 CPU 环境两次下载时打印的值(`reports/impl_c/c1_01_env_fetch.txt`、`c2_01_env_fetch.txt`),不是冻结值,代码不比对;下载元数据中的 revision 由 run_pilot 核对 |
| 模型 `model-00001-of-00002.safetensors`(3,441,185,608 字节) | `<inputs>/qwen_model/` | `169ad53ec313c3a34b06c0809216e4fc072cce444a5d4ff2b59690d064130ed5` | `run_pilot.py fetch-model` 打印实际值;run_pilot 核对每个 safetensors 的下载元数据 revision = 冻结 revision,并把实际 SHA-256 写入实验记录 |
| 模型 `model-00002-of-00002.safetensors`(622,329,984 字节) | 同上 | `912becff8d60672aa8628ef08c05898d9adf17c2ad4ae3caf99b065622fdeff9` | 同上 |

两个 safetensors 的值取自 Hugging Face API 中该 revision 的 LFS 元数据(`reports/impl_c/c3_hf_tree_70d244cc.txt`;录制 `c3_03_hf_tree_logged.txt`;没有下载权重)。`config.json` 与两个 safetensors 都不是冻结值,冻结的是 revision。下载后与上表不同:停下报告 Owner,不运行。表中 7 个冻结值与 `DATA_MANIFEST.json` 的核对:`reports/impl_c/c3_02_runbook_hashes.txt`。

## 3. 执行命令(从克隆仓库到运行完毕)

以下 `<work>`、`<inputs>` 都在仓库之外(run_pilot 拒绝仓库内的 `--work`)。**整个 Pilot 只用这一个克隆、这一个 `<work>`**(formal、test-generate、data-auditor 的计数、test-evaluate 都在这里)。每条命令的完整输出用 `tee` 保存在 `<work>/command_output/` 下(formal、test-generate、test-evaluate 的文件名带开始时间,重跑时不覆盖),在第 5 节的时机提交。长命令在 tmux 会话中运行。

```bash
# 3.0 先确认驱动(第 1 节):CUDA Version >= 13.0,一张 A100 80GB;否则停止、退租、报告 Owner
nvidia-smi
tmux new -s metrix            # 之后的命令都在这个 tmux 会话中运行
df -h                         # 选一个至少 300 GB 可用的分区,<work> 与 <inputs> 放在那里
# 变量文件(第 1 节“在 A100 主机上运行 Claude Code”):之后每条命令先 source 它。尖括号处换成所选分区上的目录
cat > ~/metrix-vars.sh <<'EOF'
export WORK=<该分区上的目录>/metrix-work INPUTS=<该分区上的目录>/metrix-inputs
export E="$WORK/command_output/env.txt"
EOF
source ~/metrix-vars.sh
mkdir -p "$WORK/command_output"
{ nvidia-smi; nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv; ldd --version | head -1; python3.13 --version; df -h "$WORK"; free -g; tmux -V; } 2>&1 | tee "$E"
#     核对:CUDA Version >= 13.0、NVIDIA A100 80GB、可用空间 >= 300 GB;任一不满足即停下报告 Owner
#     Python:不是 3.13.18(或没有 python3.13)时不停,第 3.2 节的 3.2a 用 uv 安装(代码不核对 Python 的补丁版本)

# 3.1 仓库(非浅克隆)与身份
git clone https://github.com/leotree2020/OpenMythos.git && cd OpenMythos
git checkout metrix-e1-pilot-protocol-v1
echo "export REPO=$(pwd)" >> ~/metrix-vars.sh
git config user.name "<Executor 账户>" && git config user.email "<Executor 邮箱>"
{ git rev-parse HEAD; git config user.name; git config user.email; } 2>&1 | tee -a "$E"   # 所有命令在这个检出上运行

# 3.2 Python 与依赖(只用 requirements.lock;pip 本身固定为本阶段 CPU 环境所用的 26.3)
# 3.2a(C4 裁决第 6 项)主机没有 CPython 3.13.18 时,用 uv 安装这个精确版本。uv 固定为本阶段核对过的 0.13.10
#      (reports/impl_c/c4_04_uv_check.txt:容器预装的 uv 0.11.32 不列出 3.13.18,0.13.10 列出、下载并装成)。uv 只装
#      解释器;依赖仍由下面的 pip 按 requirements.lock 逐个核对哈希安装。主机已有 3.13.18 且能建 venv(有 ensurepip)
#      时只记下它的路径;否则用 uv 装。UV_* 变量只记名字,不记值(env.txt 会提交)
if [ "$(python3.13 --version 2>&1)" = "Python 3.13.18" ] && python3.13 -c 'import ensurepip, venv' 2>/dev/null; then
  echo "export PY313=$(command -v python3.13)" >> ~/metrix-vars.sh
else
  python3 -m venv ~/uv-tool && ~/uv-tool/bin/python -m pip install uv==0.13.10 \
  && { ~/uv-tool/bin/uv --version; env | grep '^UV_' | sed 's/=.*/=<set>/'; ~/uv-tool/bin/uv python list 3.13.18 --only-downloads --show-urls; ~/uv-tool/bin/uv python install 3.13.18; } 2>&1 | tee -a "$E" \
  && echo "export PY313=$(~/uv-tool/bin/uv python find --managed-python 3.13.18)" >> ~/metrix-vars.sh
fi
source ~/metrix-vars.sh
{ echo "PY313=$PY313"; "$PY313" -c 'import platform, sys; print(platform.python_implementation(), platform.python_version()); print(sys.version)'; } 2>&1 | tee -a "$E"
#      核对:倒数第二行必须是 “CPython 3.13.18”。任一步失败、uv 的列表中没有 3.13.18 或版本不符:停下报告 Owner(不用
#      其他版本,不从源码编译)。主机缺少 venv 模块(python3 -m venv 失败)同样停下报告。uv 下载的主机以 --show-urls
#      显示的为准(本阶段为 releases.astral.sh;没有设置 UV_PYTHON_INSTALL_MIRROR,c4_04)
# 3.2 续
"$PY313" -m venv ~/metrix-venv
echo 'export PY=~/metrix-venv/bin/python' >> ~/metrix-vars.sh && source ~/metrix-vars.sh
{ $PY -m pip install pip==26.3 && $PY -m pip install --require-hashes --no-deps -r metrix/e1-pilot/requirements.lock && $PY -m pip check; } 2>&1 | tee -a "$E"

# 3.3 设备与库(只读)
$PY -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available(), torch.cuda.get_device_name(0), torch.cuda.get_device_properties(0).total_memory / 2**30)" 2>&1 | tee -a "$E"

# 3.4 下载(分词器、parquet、config、模型)
PYTHONPATH=metrix/e1-pilot/src $PY -m metrix_e1.data fetch --inputs "$INPUTS" 2>&1 | tee "$WORK/command_output/fetch.txt"
PYTHONPATH=metrix/e1-pilot/src $PY -m metrix_e1.train fetch-config --inputs "$INPUTS" 2>&1 | tee -a "$WORK/command_output/fetch.txt"
$PY metrix/e1-pilot/run_pilot.py fetch-model --inputs "$INPUTS" 2>&1 | tee -a "$WORK/command_output/fetch.txt"

# 3.5 第 1-7 步与冻结记录(Gate 0 PASS 时)
$PY metrix/e1-pilot/run_pilot.py formal --inputs "$INPUTS" --work "$WORK" 2>&1 | tee "$WORK/command_output/formal_$(date -u +%Y%m%dT%H%M%SZ).txt"
```

pip 不在锁定文件中;`--require-hashes --no-deps` 逐个核对所装包的哈希,pip 的版本不改变装入的内容。固定为 26.3 只是为了与 CPU 环境一致(`reports/impl_c/c2_01_env_fetch.txt`)。

`formal` 依次执行:设备检查(ST8)→ 代码已提交(记录写明代码 commit)与连续性检查 → 第 1 步(生成数据,四个冻结哈希,写入两个 manifest 的第 1 步字段并提交)→ 第 2 步(泄漏检查 L1–L6;预检)→ 第 3 步(N)→ 第 4 步(F 的 6 个配置,选定,阳性对照 ST3)→ 第 5 步(L、A 的搜索与选定)→ 第 6 步(F、L、A 的另两个种子;S、Y 各三个种子)→ 第 7 步(G0.8 复评,Gate 0 判定,Gate 0 记录)→ Gate 0 PASS 时提交冻结记录(选定配置、数据哈希、30 个 checkpoint 哈希)。每一步开始前执行 ST12,每一步的记录在该步结束时提交并推送;最后提交第 10 节的实验记录。最后一行 `RESULT: PASS` 表示 Gate 0 PASS 且冻结记录已推送。

`formal` 结束后:无论结果如何,停下,把结果报告 Owner。命令输出的处理分两种:

- 第 1 步开始之后的结束或停止(实验记录在 `results/` 并已提交):按第 5 节提交 `env.txt`、`fetch.txt` 与这次的 `formal_<时间>.txt`。
- 第 1 步开始之前的停止(输出中有 “the run stopped before step 1: not committed”,记录在 `<work>/experiment_record_formal_<开始时间>.json`):说明这台机器或这个检出不是 Pilot 的,不提交任何文件,连同 `<work>` 中的记录与命令输出报告 Owner。

Gate 0 不是 PASS 时到此为止(第 8 节:TEST 不生成、不评测)。

```bash
# 3.6 第 8 步:TEST 生成(Owner 批准之后)
git pull --ff-only
$PY metrix/e1-pilot/run_pilot.py test-generate --inputs "$INPUTS" --work "$WORK" 2>&1 | tee "$WORK/command_output/test_generate_$(date -u +%Y%m%dT%H%M%SZ).txt"
```

`test-generate` 先核对代码已提交、`<work>` 是 formal 运行的那一个(其中有 `device_ledger.json`),再以子进程运行 `python -m metrix_e1.test_data`:生成前核对三个前提(PROTOCOL_FROZEN 与 ST12、已提交的 Gate 0 PASS 记录、已提交的冻结记录)、解释全部已裁决、检出与推送前提;然后把 `test_qa.jsonl`、`general_test.jsonl` 写到 `<work>/test/`(仓库外),对 TEST 运行 L3–L6,写入并推送 ST10 记录(`results/st10_record.json`:原始计数、两个 TEST 文件的 SHA-256、代码 commit),并打印一行 `L6 TEST count (Executor): <整数>`。任何一项 TEST 部分超限:ST10,停止,BLOCKED,写并提交实验记录,报告 Owner。

**3.7 data-auditor 的 L6 TEST 计数**(协议第 8 节第 8 步;ST10)。

1. 调用前按 metrix/CLAUDE.md 第 5 节第 6 条比对仓库中 `.claude/agents/data-auditor.md` 与已加载定义的 frontmatter;tools 行不一致即停下,报告 Owner。调用文字第一句固定为「先读仓库中的 .claude/agents/data-auditor.md，以它为你的完整定义；它与你已加载的定义冲突时，以仓库文件为准。」,并写明“执行协议第 8 节第 8 步 L6 TEST 部分,只输出计数”、C1 裁决的防范对象原文,以及:不得用 Read、cat 等任何会显示 TEST 文件内容的方式打开 TEST 文件,脚本只打印计数、哈希与行数,不打印任何行的文字。
2. data-auditor 用自写脚本,以 `<work>/data/anchor_text.jsonl` 与 `<work>/test/general_test.jsonl` 按协议第 3 节 L6 的口径计数,脚本放在 `metrix/e1-pilot/audit/`,完整 stdout 放在 `metrix/e1-pilot/audit/stdout/`(metrix/CLAUDE.md 第 9 节),并写出 `metrix/e1-pilot/audit/st10_l6_test_count.json`:

```json
{"kind": "st10_auditor_l6", "frozen_commit": "87a244db28a901f9e89282b50df76778ab5c2887",
 "general_test_sha256": "<它计数的 general_test.jsonl 的 SHA-256>", "l6_test_count": <整数>}
```

3. 提交之前,Executor 逐行查看 audit 的完整 stdout、data-auditor 的原文与转录,确认不含 TEST 题目、答案或通用文本的文字;有疑问不提交,报告 Owner。然后提交计数文件、audit 脚本与完整 stdout(只 `git add` 这些明确路径,提交前 `git diff --cached --stat` 只含 `metrix/e1-pilot/audit/` 下的路径)并推送;data-auditor 的原始输出、调用文字与 frontmatter 核对存入 `metrix/e1-pilot/reviews/<该提交>/`,作为下一个提交推送。两者都在第 3.8 节之前完成(begin 到 finish 之间不得推送)。这些提交的审查方式见第 5 节。
4. Executor 比较 `command_output/test_generate_<时间>.txt` 中 `L6 TEST count (Executor)` 一行与计数文件的 `l6_test_count`。相同:报告 Owner,等待 TEST 评测的批准。不同:ST10,BLOCKED,不运行第 3.8 节(C4 裁决第 5 项);Executor 按第 5 项手写实验记录,作为证据提交并推送,报告 Owner。
5. **两份计数不同时的实验记录**(C4 裁决第 5 项)。run_pilot 不写这次停止的记录,由 Executor 按协议第 10 节模板手写一份,路径 `metrix/e1-pilot/results/experiment_record_l6-compare_<比较时的 UTC 时间,格式同 date -u +%Y%m%dT%H%M%SZ>.txt`。20 个字段一个不减、顺序同模板,每个字段一行 `字段: 值`(与 run_pilot 写的 `.txt` 相同);内容只有计数、哈希、提交号、设备名与路径,不含 TEST 题目、答案或通用文本的文字。尖括号处照实填写:

```
Experiment ID: METRIX-E1-PILOT-l6-compare-<同一时间>
Hypothesis: 无:E1-PILOT 没有机制假设(协议第 1、9 节),它检验训练与评测系统
Purpose: 协议第 8 节第 8 步:L6 的 TEST 部分,Executor 与 data-auditor 两份计数的比较
Independent Variable: 不适用(未训练、未评测)
Controls: 不适用(未训练、未评测)
Environment (CPU/GPU, commit, seed): 主机 <hostname>;GPU <device_ledger.json 中的设备全名>;HEAD <git rev-parse HEAD>;ST10 记录的提交 <提交>;计数文件的提交 <提交>;种子不适用
Input (data SHA, split SHA): test_qa.jsonl <SHA-256>、general_test.jsonl <SHA-256>(results/st10_record.json);data-auditor 计数的 general_test.jsonl <SHA-256>(audit/st10_l6_test_count.json);split SHA:HEAD 中 SPLIT_MANIFEST.json 的 split_sha256 <照抄该对象>;冻结提交 87a244db28a901f9e89282b50df76778ab5c2887
Hyperparameter budget: 不适用(未训练)
Compute accounting (tokens / steps / FLOPs / wall-clock): 本次比较不使用 GPU;到此为止的累计 GPU wall-clock <秒数>(由 <work>/gpu_clock.json 算出,见下)
Expected (pre-registered): 两份计数相同(协议第 8 节第 8 步)
Acceptance (quantified): Executor 的计数 = data-auditor 的计数
Stop Conditions: ST10(L6 的 TEST 部分 Executor 与 data-auditor 的结果不一致):停止;不评测 TEST;BLOCKED;报告 Owner
Positive control result: 不适用(未评测)
Negative control result: 不适用(未评测)
Statistical plan: 不适用(未评测)
Actual: Executor <整数>(command_output/test_generate_<时间>.txt);data-auditor <整数>(audit/st10_l6_test_count.json)
Status: BLOCKED
Interpretation: 两份 L6 TEST 计数不同,ST10;TEST 未评测。本记录由 Executor 手写(C4 裁决第 5 项),不是 run_pilot 的输出
Non-claims: 协议第 1 节 Non-claims;本记录不含 TEST 内容
Next (single): 报告 Owner;不运行 test-evaluate
```

   累计 GPU 秒数(与代码 `compute.GpuClock.used()` 同一口径:已关闭的段之和,有未关闭的段时计到当时):`source ~/metrix-vars.sh && cd "$REPO" && PYTHONPATH=metrix/e1-pilot/src "$PY" -c "import sys; from metrix_e1.compute import GpuClock; c = GpuClock(sys.argv[1]); print(c.used(), c._state()['open'])" "$WORK/gpu_clock.json"`。第二个值应为 `None`;不是时(有进程异常退出留下未关闭的段)在记录中照实写明“含自 <open> 起未关闭的一段,计到 <时间>”,并报告 Owner。
   提交:只 `git add` 这一个路径,提交前 `git diff --cached --stat` 只含这一个文件;按证据提交处理,不经 code-reviewer(C4 裁决第 4、5 项;第 5 节)。

```bash
# 3.8 第 8 步:TEST 评测,只评一次(Owner 批准之后)
git pull --ff-only
$PY metrix/e1-pilot/run_pilot.py test-evaluate --inputs "$INPUTS" --work "$WORK" 2>&1 | tee "$WORK/command_output/test_evaluate_$(date -u +%Y%m%dT%H%M%SZ).txt"
```

`test-evaluate` 的顺序(`pilot.test_evaluate`):代码已提交、`<work>` 是 formal 运行的那一个(连续性检查);TEST 尚未评过(只看工作区与 HEAD:已有 TEST 结果则拒绝,TestAlreadyEvaluated;已有标记而没有结果则 BLOCKED;都不写记录);再次核对生成器的前提(ST12、两个已提交记录)得到授权;设备检查(ST8);核对 15 个 checkpoint 文件与各自训练记录中的文件 SHA-256(不符则 BLOCKED,此时还没有写标记,TEST 未评);ST9 与 ST7(按整个 TEST 评测做事前判断);加载基座模型,核对其 `state_sha256` 与第 3 步记录中 N 的相同(不符则 BLOCKED,TEST 未评);`begin`(fetch,核对 ST10 记录与 data-auditor 计数,写入并推送标记 `results/test_evaluation_marker.json`,含全部 checkpoint 哈希与 N 的哈希);N 与 15 个 checkpoint 各评测一次(每个模型评测前重新计算 `state_sha256` 与标记比对);T1–T3;`finish`(fetch 核对后提交并推送 `results/test_evaluation_result.json`:聚合值与每个 fact 的分数,不含题目文字;逐题明细留在 `<work>/test_details/`,不提交);最后提交实验记录。

**begin 到 finish 之间任何人不得推送本分支**(本分支即 `metrix-e1-pilot-protocol-v1`;Review Gate 2026-11-27 的裁决第 1 项,`tasks/IMPL_C2_OWNER_MESSAGE.md`)。评测调用只在本地核对“检出本分支且 HEAD 等于标记提交”,不 fetch;begin 与 finish 会 fetch。期间若有推送,finish 判为 BLOCKED,TEST 视为已评。期间不要提交命令输出或其它文件,也不要在本克隆中做任何 git 操作;不启动、不重启 Claude Code(它在会话开始时会读取仓库的 git 状态),需要重启时等 test-evaluate 结束。

输出的倒数第二行 `test-evaluate completed: <状态>` 表示 TEST 已评完、结果已推送,`<状态>` 是第 9 节的最终状态;最后一行 `RESULT` 只表示该状态是否为 PASS(例如 HYPOTHESIS_FAIL 时为 `RESULT: FAIL`),不表示评测失败。`test-evaluate stopped or refused: …` 表示停止或拒绝。

标记一旦存在,TEST 就视为已评:无论结果如何,不得重跑 test-evaluate(第二次运行被拒绝:有标记无结果为 BLOCKED,有结果为 TestAlreadyEvaluated)。

## 4. 预检(ST11)与停止条件出现时的操作

**预检**在 `formal` 的第 2 步自动进行:第一个配置(F1,种子 101)的前 20 步(协议给定的步数),记录每步耗时、tokens/s、峰值显存;另测一次 DEV 评测、一次模型加载、一次 `state_sha256`、一次 checkpoint 保存、重载与文件哈希。ST11 读解释 B17 的估算(`b17_estimate_hours`;A 的每步时间按 FLOP 比例 `a_factor` 放大,本数据约 6.75)与 checkpoint 开销(`preflight.checkpoint_overhead.seconds`,`pilot.checkpoint_overhead_seconds`)之和,即第 2 步记录中的 `preflight.st11_estimate_hours`(C4 裁决第 1 项;B17 已相应修订):超过 3.5 小时即停止,BLOCKED,报告 Owner(不得删减步骤或改配置来压缩时间;第 6 节给出预期区间)。预检测得的耗时还用于 ST7 的事前判断(C4 裁决第 1 项:不变):每次训练前按“基座模型加载 + 训练 + 两次 `state_sha256`、保存、文件哈希、重载 + 一次 DEV 评测”,每次评测前按“加载 + 评测”,TEST 评测开始之前按整个 TEST 评测(16 个模型的加载、哈希与评测,不加余量)判断累计 GPU 时间是否会超过 4 小时;会超过即 ST7,TEST 不开始。

**一般规则**:除下列情形外,任何停止都由 run_pilot 写出实验记录(`results/experiment_record_<命令>_<开始时间>.json` 与 `.txt`,状态为停止条件规定的状态),最后一行 `RESULT: FAIL`。一步之中的停止先写并提交该步的记录(含该步算出的数值);停止时已写出未提交的记录随实验记录一起提交。第 1 步开始之后的停止,记录提交并推送到 `results/`。例外(现行实现;C4 裁决第 2 项接受):

- `formal` 在第 1 步开始之前停止(设备检查 ST8、代码有未提交的改动、连续性检查、第 1 步开始时的 ST12 / ST13 或提交前提不成立),说明这台机器或这个检出不是 Pilot 的:记录只写在 `<work>/experiment_record_formal_<开始时间>.json` 与 `.txt`,不写入仓库、不推送,由 Executor 连同命令输出报告 Owner。`Pilot()` 本身的 ST12(读冻结文件时)没有记录,run_pilot.py 以回溯退出。
- `test-generate`:生成之前的拒绝不写记录;只在 ST10 超限时写 BLOCKED 记录并提交;成功时不写实验记录(ST10 记录即其输出)。两份 L6 计数不同的 ST10 由 Executor 手写记录(第 3.7 节第 5 项)。
- `test-evaluate` 在本进程写入标记之前:没有停止码的拒绝(TEST 已评或已开始、生成器的前提、连续性检查、已提交记录或文件缺失、checkpoint 文件或 N 的哈希不符、begin 中的检出与提交前提)不写记录(TEST 未评),带停止码的协议停止(ST7、ST8、ST9、ST10、ST12)写记录并提交;本进程写入标记之后的任何停止或崩溃都写记录并提交(BLOCKED)。

**确定性模式下的 CUDA 算子报错**(上次阶段 C 指令第 9 项):run_pilot 在 CUDA 初始化之前设置协议第 0 节的确定性(`torch.use_deterministic_algorithms(True)`、关闭 TF32、`CUBLAS_WORKSPACE_CONFIG` 取冻结值;`compute.set_determinism`),并把设置写入实验记录。某个算子在确定性模式下报错(例如 `RuntimeError: ... does not have a deterministic implementation`,或要求设置 `CUBLAS_WORKSPACE_CONFIG`):**立即停下,报告 Owner。不得关闭确定性,不得修改 `CUBLAS_WORKSPACE_CONFIG`、TF32、cuDNN 设置或环境变量,不得改代码、换算子、换库版本,不得重跑。** run_pilot 按崩溃处理:`formal` 写 NOT_TESTED 实验记录并提交(第 1 步开始之后),原样抛出;`test-evaluate` 在本进程写入标记之后为 BLOCKED 记录,TEST 视为已评,之前则不写记录。Executor 把命令输出(含回溯)与提交号报告 Owner,由 Review Gate 决定如何处理。设置确定性本身失败(`compute.set_determinism` 在 `Pilot()` 中运行,可能报 “CUDA already initialised …” 或 “determinism settings did not take effect”)时,与 `Pilot()` 的 ST12 一样没有实验记录,run_pilot.py 以回溯退出;同样停下,不得改设置,连同命令输出报告 Owner。

**重跑与恢复**:一次 Pilot 是同一台机器、同一个 `<work>` 上的一串命令。formal 已提交步记录之后,`<work>` 中没有设备记录(`device_ledger.json`)的 formal 与 test-evaluate 被拒绝;冻结记录提交之后 formal 被拒绝;同一个 `<work>` 中已有某次训练的 checkpoint 时,该次训练拒绝再训。崩溃或停止之后是否、从哪一步重新开始,由 Owner 决定(ST9 的“从第 8 节第 3 步重新开始”同样需要 Owner 指令),Executor 不自行重跑。Executor 不重跑、不修补、不换机器,把 `<work>/command_output/` 中该命令的完整输出与提交号报告 Owner。

| 停止 | 何时出现 | 动作(协议第 11 节)与操作 |
|---|---|---|
| ST1 | 第 2 步任一泄漏检查超限 | 停;不训练;IMPLEMENTATION_FAIL。报告 Owner |
| ST2 | 第 3 步 N 不满足 G0.3 | 停;不训练;PIPELINE_NOT_QUALIFIED(重新校准)。报告 Owner |
| ST3 | 第 4 步 F 选定配置(种子 101)的阳性对照未过 | 停;不跑 L、A、S、Y。报告 Owner |
| ST4 / ST5 | 第 7 步 Y 不满足 G0.7 / S 不满足 G0.6 | Gate 0 记录照常提交;停;不生成 TEST。报告 Owner |
| ST6 | 任一次训练或评测出现非有限值 | 搜索中的非选定配置:该配置从选择中剔除,运行继续(记入第 6 步记录 `excluded`);选定配置或对照:IMPLEMENTATION_FAIL,停。报告 Owner |
| ST7 | 累计 GPU wall-clock 超过 4 小时,或下一次训练 / 评测会超过 | 停并报告进度;延长上限、换硬件或降级由 Owner 决定。GPU 时间记在 `<work>/gpu_clock.json`(跨进程累计;进程异常退出时,下一个进程把未关闭的一段计到当时为止) |
| ST8 | 设备或库版本不满足第 0 节 | BLOCKED,`formal` 在第 1 步之前就停下。检查第 1 节各项 |
| ST9 | 某次运行开始时设备全名与首次记录不同 | 整批作废,BLOCKED。由 Owner 决定:在设备全名一致的机器上从第 8 节第 3 步重新开始 |
| ST10 | TEST 部分超限,或两份 L6 计数不同 | 停止;不评测 TEST;BLOCKED;报告 Owner。超限由 test-generate 写记录;两份计数不同由 Executor 手写记录(第 3.7 节第 5 项) |
| ST11 | 预检预估(B17 估算 + checkpoint 开销,第 2 步记录的 `preflight.st11_estimate_hours`)> 3.5 小时 | 停止;BLOCKED;报告 Owner |
| ST12 | 数据、manifest、模板、候选、模型或分词器版本与冻结值不同 | 停止;BLOCKED。不得改动冻结文件来通过 |
| ST13 | 冻结记录提交前出现 TEST 文件 | IMPLEMENTATION_FAIL;本次 Pilot 作废 |

**TEST 路径上的特殊情况**(C1 裁决第 2 项;DEFERRED_MINORS 1.30 CD10):

- `test-generate` 生成 TEST 之后推送 ST10 记录被拒:TEST 视为已生成,禁止重跑,BLOCKED,报告 Owner;由 Owner 决定是否批准把 ST10 记录这一个文件手工提交。
- `test-generate` 在写出 TEST 文件之后、写入 ST10 记录之前崩溃:同样按 BLOCKED 报告 Owner,不得换 `--out` 或换机器再次生成。
- `test-evaluate` 在本进程写出标记之后的任何失败(推送失败、崩溃、Ctrl-C、某个模型的哈希与标记不符、finish 被拒):TEST 视为已评,实验记录 BLOCKED 并提交,报告 Owner。SSH 断开导致进程被结束时不会写记录,所以第 3.8 节必须在 tmux 中运行。
- 推送被拒时 run_pilot 不会自动重做;本地留下的提交(ST10 记录、标记、结果)只在 Owner 决定后推送。

## 5. 结果与记录如何提交回仓库

- **由 run_pilot 自动提交并推送**(`testgate.commit_paths`:只提交该步的路径,快进推送,不推送标签,核对远端分支):两个 manifest 的第 1 步字段;`metrix/e1-pilot/results/` 下每一步的记录 `stepN_record.json`、每次训练的记录 `training_runs/<run>.json`(含训练日志、算力、checkpoint 的 `state_sha256` 与文件 SHA-256、DEV 汇总)、DEV 逐题明细 `details/`、Gate 0 记录、冻结记录、ST10 记录、TEST 标记与结果、实验记录 `experiment_record_<命令>_<开始时间>.json/.txt`。每次提交前核对:本分支的检出、HEAD 等于远端最新提交、暂存区为空、有提交者身份、`push --dry-run` 通过。
- **由 Executor 手工提交**:
  - `<work>/command_output/` 中的命令输出(第 1 步开始之前停止的 formal 除外,见第 3.5 节之后),复制到 `metrix/e1-pilot/results/command_output/<名称>.txt`(该路径与 `.txt` 扩展名不被仓库的 `.gitignore` 忽略;不要用 `logs/` 目录或 `.log` 扩展名,它们被忽略),只 `git add` 这些明确路径,提交前 `git diff --cached --stat` 核对。时机:`formal` 结束后、`test-generate` 之前一次;`test-generate` 之后、第 3.8 节之前一次;`test-evaluate` 结束后一次。**不在 begin 与 finish 之间提交。**
  - 提交 `test_generate_<时间>.txt`、`test_evaluate_<时间>.txt`,以及第 3.7 节 data-auditor 的 stdout、原文与转录之前,逐行查看,确认不含 TEST 题目、答案或通用文本的文字(异常回溯或工具结果可能带出行内容);有疑问不提交,报告 Owner。
  - data-auditor 的计数文件、audit 脚本与 stdout,及其原始输出(第 3.7 节)。
  - 两份 L6 计数不同时 Executor 手写的实验记录(第 3.7 节第 5 项)。
  - **审查方式**(C4 裁决第 4、5 项):这些手工提交只含输出(`results/command_output/`、`audit/`、`reviews/`,以及上一项的手写记录),不含 `src/`、`tests/`、`run_pilot.py`,按证据提交处理,不经 code-reviewer。只 `git add` 明确路径,提交前 `git diff --cached --stat` 核对只含这些路径;含其他路径的提交不是证据提交,按 metrix/CLAUDE.md 第 5 节送审。所有这些推送都不在 begin 与 finish 之间。
- **不提交**:模型权重、checkpoint(`<work>/checkpoints/`)、数据目录、`<work>/test/` 下的所有文件(TEST 文件与 `leakage_test_report.json`,后者的 L4 明细可能引用 TEST)、TEST 逐题明细(`<work>/test_details/`)。这些都在 `<work>` 中;`<work>` 在仓库之外。checkpoint 在 Pilot 结束之前不删(删除需 Owner 指令)。
- 全部结束后,Executor 写阶段报告,调用审查,按 metrix/CLAUDE.md 第 5、9 节提交。

## 6. 预计时长与费用(规划估计,正式数值以预检为准)

单价按 A100 80GB **每小时 1.8 美元**(Implementation Task Order V1 第 8 节)。

**依据**(实际 wall-clock 的规划估计):
- 训练:每次 300 步(Y 也是 300 步),每步 8 条(Y 16 条)短句,每条约 16 个 token(F 语料共 1,889 token,协议第 2.6 节),一次训练的事实 token 约 3.8 万。按协议第 10 节的 6·P·T,一次训练约 6 × 1.72e9 × 3.8e4 ≈ 3.9e14 FLOPs,在 A100 上计算本身只需数秒;每步的耗时主要来自 1.72e9 个 float32 参数的 AdamW 更新、bf16 autocast 的权重转换与梯度裁剪(每步读写约 50–70 GB 显存),按 0.1–0.3 秒/步估计。A 另有每步 4 篇锚文档(约 512 token)在两个模型上的前向与 KL;按 FLOP 计,锚文本部分约为事实部分的 5.75 倍(即 a_factor − 1),但在每步由参数更新主导、bf16 autocast 的吞吐下,实际 wall-clock 按约 1.5 倍估计(未实测)。预检只测 F1,不含 A;A 的实际步时在第 5 步第一次 A 训练的记录中才可见,ST7 的事前判断与 ST11 都按 a_factor 放大 A(偏保守)。30 次训练约 34 个“普通训练”当量 × 300 步 × 0.1–0.3 秒 ≈ 17–51 分钟。
- 评测:一次 DEV 评测为 1,280 个候选序列、480 个 TRAIN 闭卷序列、320 个贪心生成(至多 16 个新 token)、100 个通用窗口(至多 256 token),float32、不用 TF32,约 0.5–1 分钟;解释 B17 计 58 个 DEV 评测单位(N、30 次训练、G0.8 的 3 次复评;TEST 的 16 个模型按 1.5 倍),约 29–58 分钟。
- checkpoint 开销(计数见 `pilot.evaluation_plan`):基座模型加载 32 次(N、每次训练、TEST 的 N);30 个 checkpoint 各保存一次、保存后重载一次、`state_sha256` 两次、文件 SHA-256 一次;另外的 checkpoint 重载 18 次(G0.8 的 3 次、TEST 的 15 次);TEST 的 `state_sha256` 17 次与 checkpoint 文件 SHA-256 15 次(后者在 GPU 计时开始之前)。合计 80 次加载、77 次 `state_sha256`、45 次文件 SHA-256、30 次保存,每次处理约 6.9 GB;按加载 10–20 秒、哈希与保存各 5–20 秒估计:80 × (10–20) + 152 × (5–20) 秒 ≈ 26–77 分钟,其中 GPU 计时之内约 25–72 分钟。
- 预检约 3–5 分钟。

| 项 | 估计 |
|---|---|
| 协议意义上的累计 GPU wall-clock(第一次加载模型到 TEST 评测结束;ST7 读这个量) | 17–51 + 29–58 + 25–72 + 3–5 分钟 ≈ **1.2–3.1 小时**(ST7 上限 4 小时) |
| 预检时 ST11 读到的估算:B17 估算 + checkpoint 开销(C4 裁决第 1 项) | B17 估算 = 每步时间 × 300 × (22 + 8 × a_factor) + DEV 评测时间 × 58 + 已用 GPU 时间;a_factor ≈ 6.75(本数据的锚文本与事实 token 数,冒烟记录 `c2d_smoke_records/step2_record.json`),即 76 个“普通训练”当量。按上面的单项区间:0.63–1.90 + 0.48–0.97 + 0.05–0.08 小时 ≈ 1.2–3.0 小时。checkpoint 开销按代码公式(`pilot.checkpoint_overhead_seconds`)0.43–1.29 小时。两者之和 ≈ **1.6–4.2 小时**(ST11 上限 3.5 小时):单项区间的上端超过 3.5 小时,会触发 ST11(停止;BLOCKED;报告 Owner)。它按 FLOP 比例放大 A,并计入 TEST 前在 GPU 计时之外的 15 次 checkpoint 文件哈希,高于上一行的实际估计 |
| 租用时长(另加环境安装与下载约 0.5 小时、等待 Owner 两次批准与 data-auditor 计数的时间) | 约 2–5 小时 |
| 费用(1.8 美元/小时) | GPU wall-clock 部分约 2.2–5.6 美元;按租用时长约 3.6–9.0 美元;等待批准期间机器不能退租(checkpoint 与设备全名都在这台机器上),等待时间按小时计费 |

预检之后,以第 2 步记录中的实测值为准:ST11 读 `preflight.st11_estimate_hours`(= `preflight.b17_estimate_hours` + `preflight.checkpoint_overhead.seconds` / 3600,与第二行比较),超过 3.5 小时即 ST11;实际 GPU wall-clock 记在 `<work>/gpu_clock.json`(与第一行比较)。
