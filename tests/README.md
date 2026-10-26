# 测试说明

在仓库根目录运行：

- 后端测试：`python -m unittest -v`
- 前端测试：`node tests/frontend_results_harness.js index.html`

前端测试依赖 Node.js。没有 Node.js 时，前端 harness 对应的 unittest 用例会静默跳过。

## 测试文件

- `test_concurrency.py`：验证历史记录、白名单和书签在并发读写下保持安全与完整。
- `test_engine_diagnostics.py`：验证空页诊断会进入界面日志、正常命中不增加诊断日志。
- `test_engine_snapshots.py`：锁定各引擎搜索 URL 的构造和页码参数。
- `test_frontend_results.py`：比较前端增量插入结果与原有整表刷新行为。
- `test_history_whitelist.py`：验证历史记录加载时正确补充白名单状态。
- `test_serialization.py`：锁定白名单与搜索历史的 JSON 序列化结构。
- `test_source_registry.py`：锁定来源标签、引擎注册表及显示顺序。
- `frontend_results_harness.js`：在 Node.js 中运行真实前端结果行逻辑的测试桩。

网站改版本身不会让这些不访问网络的测试失败；但如果引擎 URL/页码构造、结果解析契约、序列化结构或前端结果处理逻辑发生变化，相关测试失败是预期的，需要确认变化符合预期并更新相应测试。
