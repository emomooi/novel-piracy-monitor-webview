# 测试说明

在仓库根目录运行：

- 后端测试：`python -m unittest -v`
- 前端测试：`node tests/frontend_results_harness.js index.html`
- 手动联网冒烟：`python tests/network_smoke.py --run-network`

前端测试依赖 Node.js。没有 Node.js 时，前端 harness 对应的 unittest 用例会静默跳过。

## 测试文件

- `test_concurrency.py`：验证历史记录、白名单和书签在并发读写下保持安全与完整。
- `test_engine_diagnostics.py`：验证空页诊断会进入界面日志、正常命中不增加诊断日志。
- `test_engine_navigation.py`：用假页面验证导航目标状态等待可中断、超时总预算不变。
- `test_network_smoke.py`：验证联网冒烟默认关闭及报告格式；测试本身不访问网络。
- `test_engine_snapshots.py`：锁定各引擎搜索 URL 的构造和页码参数。
- `test_engine_wait.py`：验证随机等待可中断、等待时长保持不变，并可安全兼容未提供停止接口的假 app。
- `test_frontend_results.py`：比较前端增量插入结果与原有整表刷新行为。
- `test_history_whitelist.py`：验证历史记录加载时正确补充白名单状态。
- `test_serialization.py`：锁定白名单与搜索历史的 JSON 序列化结构。
- `test_source_registry.py`：锁定来源标签、引擎注册表及显示顺序。
- `frontend_results_harness.js`：在 Node.js 中运行真实前端结果行逻辑的测试桩。

网站改版本身不会让这些不访问网络的测试失败；但如果引擎 URL/页码构造、结果解析契约、序列化结构或前端结果处理逻辑发生变化，相关测试失败是预期的，需要确认变化符合预期并更新相应测试。

## 手动联网冒烟

只有显式添加 `--run-network` 才会启动浏览器并访问网站；普通 `python -m unittest -v` 不会触发联网。冒烟检查使用项目同款 Playwright Chromium `msedge` 通道、浏览器参数和 UA，在系统临时目录建立独立 profile，运行结束自动清理。需要本机已安装 Microsoft Edge。

覆盖头条 PC、头条移动、必应和搜狗 PC，各抓取前两页；每页要求至少 3 条结果、结果链接为站外真实地址，且第二页标题集合不同于第一页。头条两端用于覆盖本轮 URL/解析变更；必应较适合作为通用搜索基线；搜狗 PC 可能触发反爬验证，结果可能不稳定。每个页面导航在冒烟过程中最多等待 20 秒（总超时预算为 240 秒），页面默认操作超时为 10 秒；达到整体时限或页面超时会报告失败并继续后续来源。完整报告会列出来源、失败原因、每页条数和前两条标题。

失败表示本次环境或站点没有满足冒烟断言，不一定代表代码回归：也可能是网络不可达、Edge 不可用、验证码/登录拦截、站点暂时无结果或站点改版。该检查不进入 CI，因此网站改版不会被自动发现。
