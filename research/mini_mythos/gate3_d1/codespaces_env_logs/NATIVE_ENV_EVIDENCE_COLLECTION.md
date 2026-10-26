# Codespaces 原生环境证据采集命令（只读，由项目负责人在 Codespaces 执行）

**状态：原生证据 BLOCKED（尚未采集/回传）。** Claude 会话无法访问你的 Codespaces（`gh codespace list` 返回 HTTP 403，沙箱里没有 `/workspaces`）。本文件不含任何环境快照，也不会用沙箱数据代替。已归档的 `selftest_py3138.txt` 保持原样。

目标解释器：`/workspaces/.venvs/openmythos-d1-py3138/bin/python`。目标环境是你实际使用的 Codespaces。

## 命令

在 Codespaces 终端、仓库根目录运行。只读：除了最后把结果复制成一个新证据文件外，不改动任何已跟踪文件，不安装、不下载。

```bash
PY=/workspaces/.venvs/openmythos-d1-py3138/bin/python
OUT=$(mktemp)
{
echo "# Codespaces native environment evidence (read-only capture)"
echo "generated_utc: $(date -u +%FT%TZ)"
echo "## git (captured BEFORE this file is copied into the tree)"
echo "head: $(git rev-parse HEAD)"; echo "branch: $(git branch --show-current)"
echo "status_porcelain_v1:"; git status --porcelain=v1; echo "(end status)"
echo "## interpreter"
echo "target: $PY"; ls -l "$PY"
"$PY" -VV
"$PY" -c "import sys;print('executable',sys.executable);print('prefix',sys.prefix);print('base_prefix',sys.base_prefix);print('full','%d.%d.%d'%sys.version_info[:3])"
echo "venv_path: $(dirname "$(dirname "$PY")")"
echo "## pinned libraries (importlib.metadata)"
"$PY" -c "import importlib.metadata as m
for k in ('tokenizers','pyarrow','huggingface_hub'):
    try: print(k, m.version(k))
    except Exception as e: print(k,'NOT INSTALLED',e)"
echo "## pip freeze"; "$PY" -m pip freeze
echo "## pip check"; "$PY" -m pip check; echo "pip_check_exit: $?"
echo "## CPU / OS / memory"
nproc; (lscpu 2>/dev/null | head -20) || true
uname -a; cat /etc/os-release 2>/dev/null | head -6
grep -E 'MemTotal|MemAvailable' /proc/meminfo; df -h . | tail -1
echo "## frozen-code integrity at this HEAD"
(cd research/mini_mythos/gate3_d1 && sha256sum -c D1_CODE_SHA256SUMS)
echo "## selected environment variables"
env | grep -E '^(CUDA_VISIBLE_DEVICES|TOKENIZERS_PARALLELISM|PYTHONHASHSEED|VIRTUAL_ENV)=' || echo "(none of those set)"
} > "$OUT" 2>&1
cat "$OUT"
cp "$OUT" research/mini_mythos/gate3_d1/codespaces_env_logs/native_env_evidence_py3138.txt
```

## 回传后的核对（审核方）

| 项 | 期望 | 不符时 |
|---|---|---|
| `full` / `-VV` | `3.13.8` | 配置固定值要更新或换环境，需新的冻结提交 |
| `executable` / `prefix` | 位于 `/workspaces/.venvs/openmythos-d1-py3138` | 说明不是目标虚拟环境，证据作废 |
| tokenizers / pyarrow / huggingface_hub | `0.23.3` / `26.0.0` / `2.2.0` | 同上 |
| `pip check` | `No broken requirements found.`，`pip_check_exit: 0` | BLOCKED |
| `sha256sum -c` | 10/10 OK（需在含最新清单的提交上采集） | 说明代码与清单不一致 |
| Git `head`/`branch`/`status` | 记录实际值；采集前工作区应干净 | 记录差异 |
| CPU/OS/内存 | 仅记录（检查点称 2 CPU） | — |

采集到的文件应作为**新增**证据提交，不覆盖 `selftest_py3138.txt`。
