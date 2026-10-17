# R2 Gate Q — Python 3.14 `spawn` 双 Worker 测试加固方案

**2026-10-17：测试修改已提交，尚未在用户 Codespaces 运行，因此 NOT VERIFIED。** 原 Gate Q 研究候选功能不变；用户已在上一版本测得专项 8/8、全量 241/241 PASS，且遭遇非致命 `fork()` multi-thread `DeprecationWarning`。完整原结果参见 [Gate Q Result](R2_GATE_Q_RESULT.md)。

## 根因

原 Q 双进程测试用 `multiprocessing_context="fork"`，并在父进程里 `patch.object(q,"load_dataset",return_value=local)`。`fork` 使子进程继承父进程的假 HF Dataset 实例与 monkeypatch，但 Python 3.14 的多线程状态下使用 `os.fork()` 有潜在死锁风险。不能只将 `"fork"` 字符串替换成 `"spawn"`：新解释器不会继承父进程内存中的 patch，而且局部定义的对象可能无法 pickle。

## 最小加固内容

- 新增 [脚本 `r2_pr27_spawn_local_fixture.py`](../scripts/r2_pr27_spawn_local_fixture.py)：`ToyTokenizer`、`WorkerPathProbe`、`install_local_source_in_spawn_worker`、`load_local_hf_dataset` 全部是可被新解释器导入的模块顶层类/函数。
- `install_local_source_in_spawn_worker` 由 PyTorch `worker_init_fn` 在**真正的每个 Worker 子进程内**调用，核对 `get_worker_info().num_workers==2`，安装 **本地合成 HF 来源工厂**。
- 工厂只接受固定 FineWeb Dataset/Config/Split/Revision 和 `streaming=True` 参数，仅返回 `Dataset.from_dict({"text": ["ID:0", ..., "ID:13"]}).to_iterable_dataset(num_shards=14)`；它从未下载 Parquet，也不访问 HF Hub。14 个 Arrow Shard 与 14 条合成记录一一对应。
- 原 Q 双 Worker 用例改为 `multiprocessing_context="spawn"`、`worker_init_fn=install_local_source_in_spawn_worker`。不再靠父进程传递 monkeypatch 或共享假数据对象，保留对真实两个 OS PID、每 Worker 7 条、全 14 条只出现一次和 EOS Target 的严格断言。
- 新增 `test_spawn_local_factory_fails_closed_on_source_and_revision`，主动拒绝浮动 `main` Revision 与错误来源。Q 专项现在计划由 8 增至 **9 项**，全量测试计划由 **241 增至 242 项**，不是已测成功值。

## 边界和常见失败

1. 要在真实 Codespaces Linux `python -m unittest discover ...` 中运行。`spawn` 会重新导入 Python 模块，发现 pickle / import 问题要保留 Traceback，不能自动降回 `fork` 或跳过真实 Worker 用例。
2. 源数据依旧是**本地合成文本** `ID:0...13`，不是原版 PR #27 的远程数据、文档或 Token 覆盖证明。
3. 研究候选 `r2_pr27_native_once_data_candidate.py` 的 loader 没有改动，原版 PR27 `experiments/data.py` 没有改动，数据来源 Git pin 没有改变。
4. 真正“多 Worker 远程训练可重启”还需要来源覆盖、消费 Cursor/Checkpoint 边界与故障恢复设计，不能因为该测试通过就声称生产正确。

## Codespaces 指令

```bash
git status --short
git pull --ff-only origin mini-mythos-research
python -m unittest discover -s research/mini_mythos/tests -p 'test_r2_pr27_native_once_data_candidate.py' -v
python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v
```

期待无 Python 3.14 `popen_fork` DeprecationWarning；如果依旧出现，检查具体测试名字和告警位置以确认是否是 Gate Q 或其他旧测试。无需运行远端 HF `freeze`、训练或安装额外软件。
