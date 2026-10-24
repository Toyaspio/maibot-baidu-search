# V0.1 测试报告

最新状态：2026-10-25 的 117 项实际环境测试与指定会话实装功能验收见 [ACCEPTANCE_REPORT.md](ACCEPTANCE_REPORT.md)。v0.1.0 Release 已公开。下文仅保留 2026-10-24 前两个阶段的历史记录，不表示当前尚未发布或尚未完成验收；新增版本兼容测试见 [COMPATIBILITY_REPORT.md](COMPATIBILITY_REPORT.md)。

历史执行日期：2026-10-24，北京时间。初次离线验证与后续真实测试分开记录：本地实现和隔离验证通过，23:50 单次真实 API 测试通过；当时完整宿主链路待验收；此限制已由后续验收报告更新。

## 环境与来源

- 工作区原有根 Git 仓库无提交、无远端，含其他 MaiBot 维护文件；本项目另建独立 `maibot-baidu-search` 仓库，分支 `codex/maisearch-v0.1`，当时未提交、未连接远端、未公开推送；后来已公开并发布 v0.1.0。
- 只读 SSH 核对现用容器 Python 3.13.16、SDK 2.10.0；读取核心 pyproject 声明版本 1.3.5。取回仅 SDK 和 `src/plugin_runtime` 等程序源码，不读取生产配置、密钥、用户数据库或聊天。
- 本地 Python 3.12.14，真实 SDK 2.10.0 源码；httpx 0.28.1、pytest 8.4.2、ruff 0.17.2；其他本地依赖版本见 [VALIDATION.json](VALIDATION.json)。没有在生产环境安装依赖。
- 查阅 [MaiBot 插件文档](https://docs.mai-mai.org/plugin/)、[官方 SDK](https://github.com/Mai-with-u/maibot-plugin-sdk)、[百度搜索 API](https://ai.baidu.com/ai-doc/AppBuilder/pmaxd1hvy)；官方 SDK 主分支取回源码 pyproject 为 2.16.0，实际插件按现场 2.10.0 实现并锁定兼容范围。也核对了 PyPI 的 SDK 2.10.0 版本和 LGPL-3.0-only 元数据。
- Host `ToolExecutionResult` 使用先前维护任务保留的本地只读源码快照；本轮后续 SSH 连接被关闭，未重新取回该单文件，不声称是本轮最新现场副本。Tool bridge 来自本轮取回源码。参与验证的源码哈希已记录。

## 实际执行结果

最终一轮：**116 passed，0 failed，0 errors，0 skipped，10.60 秒**。

| 检查 | 结果与边界 |
| --- | --- |
| Python AST / py_compile | 全部本项目及测试 Python 文件通过 |
| Manifest JSON | 解析通过；真实 Host v2 校验器接受 Host 1.3.5 / SDK 2.10.0 / httpx 依赖 |
| Ruff lint | `ruff check .` 通过 |
| Ruff 格式 | `ruff format --check .` 通过 |
| Client 单元测试 | 受控 MockTransport；固定 POST 地址、单轮 messages、web top_k、两种单一鉴权头；无重定向/重试 |
| 错误场景 | 401/403/429/400/500/301、业务错误、超时、网络/DNS 类连接错误、非 JSON、错误类型、过大流、压缩响应、无密钥/非法密钥 |
| 搜索服务 | 正常/空结果、异常响应字段、标题/摘要/日期、重复 URL、HTTP(S) URL 筛选、控制字符/CQ 码清理、密钥回显移除 |
| 隐私和必要性 | 空/超长/多行/控制字符、凭证模式、长数字、邮件、URL/路径、JSON 上下文；Tool purpose 校验，其他上下文参数不发送 |
| 持久化配额 | 北京时间跨日、失败/取消占额、重建管理对象后不重置、降低限额不重置、损坏/锁超时拒绝、时钟回退 |
| 并发 | 多个配额实例 80 次竞争只接受 20 次；40 个并发搜索只调用 Mock Client 5 次；6 个进程共竞争 72 次只接受 7 次；Tool 并发只接受 1 次，其他冷却拒绝 |
| SDK | 真正的配置模型/Schema、Command/Tool 元数据、生命周期、环境变量优先级、配置更新、发送 RPC 替身、缺 stream 不搜索、发送失败不重试 |
| Runner 组件集成 | 未修改的真实 PluginLoader / ManifestValidator / PluginRunner：发现、加载、配置文件生成、组件注册 payload、处理器解析、生命周期、配置更新、完整模块 purge/reload，持久化额度保留 |
| Host 返回契约 | 从源文件 AST 选取并执行真实 bridge 方法和 ToolExecutionResult：来源 URL 实际进入 Planner history；拒绝搜索与“工具已处理”分别表达，停止字段可解析 |

测试本轮所有搜索均为 Mock 或直接拒绝，真实百度请求为 **0 次**，真实模型请求为 **0 次**。自动 fixture 阻止真实 httpx HTTPTransport / AsyncHTTPTransport 发送；Windows asyncio 的内部 loopback self-pipe 正常保留。

隔离 Runner 测试仅替换日志、宿主版本/配置比较辅助模块及 IPC 收件端；插件 SDK、加载器、配置生成、注册业务方法均为真实实现。返回契约测试是 AST 方法级测试，不等于完整 Host 执行。SDK 集成不能简化描述成“只用了 SDK Mock”，也不能夸大成已完成 QQ / Planner 真人验收。

## 测试中发现并处理的问题

- 首轮测试文件有一处括号语法错误，已修正并重新执行；未忽略收集失败。
- SDK 实际组件类型为 `COMMAND` / `TOOL`。原测试错误地使用首字母大写值，已依据真实源码和返回值修正为精确断言。
- 曾将网络防护放在底层 socket.connect，导致 Windows asyncio 自建 self-pipe 失败。改到真实 HTTP 传输边界，保留禁止真实 HTTP 的测试保护；没有移除相关安全验证。
- 并发回归发现时间采样早于数据库锁，正常排队可能误报时间回退。移动到 `BEGIN IMMEDIATE` 后取时间，新增锁内时间采样回归断言。
- Host 优先将 `content` 写入历史，仅在结构化字段放来源会让模型只看到“搜索完成”。现在 `content` 携带完整搜索 JSON，源方法契约测试确认 URL 进入历史。
- Host 停止当轮继续规划要求工具执行已处理成功且 `stop_after_execution=true`。外层表示工具处理状态，内层明确真实搜索成败；拒绝/错误触发停止，成功允许组织回答。测试确认不会把拒绝伪报成搜索成功。

最终结果保留所有相关测试，没有删除测试、放宽限额断言或将 skip 当作通过。

## 复现

安装 `requirements-dev.txt`，使用 SDK 2.10.0。常规 `python -m pytest -q` 会在缺少真实宿主源码时明确跳过 5 个集成/契约测试；其余为离线测试。

要复现本轮全部 116 项，设置：

```text
MAISEARCH_HOST_SOURCE=<匹配版本宿主源码根目录，包含 src/plugin_runtime>
MAISEARCH_TOOLING_SOURCE=<匹配版本 src/core/tooling.py 的路径>
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
```

本轮本地将开发依赖和 SDK 源码路径加入 `PYTHONPATH`，分别位于忽略的 `.dev/deps`、`.dev/runtime/.venv/lib/python3.13/site-packages`。无需这些私有目录也可按 requirements 安装真实 SDK 后测试。源快照、JUnit XML 和完整本机输出不进入公开包；可公开的检查摘要、依赖版本及源码哈希在 `docs/VALIDATION.json`。

```text
python -m ruff check .
python -m ruff format --check .
python -m pytest -q --junitxml=test-results.xml
python build_release.py
```

## 初次离线验证时未执行项和风险（最新 API 状态见末尾补记）

1. **T4 真实 API 未验证**：未读取或索取真实 Key，也未获真实计费测试批准；百度权限、账号权益、鉴权 Header、实际响应/来源尚待受控验收。官方文档两种 Header 的差异已记录，禁止自动轮换或重试。
2. **历史 T3 阶段的完整链路未验证项（后续已验收）**：未启动完整隔离 Host IPC、真实 Planner 或 QQ 发送；停止信号的实际调度、真实长结果可发送性、真人收到结果仍待验收。现场 Python 3.13 未运行本插件测试，本次实际测试解释器是 3.12。
3. 本地限额约束同一插件数据目录，无法封顶账号其他请求费用；删除/回退预算文件或另起独立部署会破坏共享计数，禁止这样测试。
4. 隐私正则/必要性标记不能保证识别所有私人语义；网页来源和日期也不能保证正确。外部数据只作为资料，不执行指令，不做结果页或任意 URL 抓取。
5. `.gitignore` 和白名单/窄模式检查降低误打包风险，不是绝对无敏感信息证明；公开前仍需用户审查。

## 发布与生产隔离结论

- V0.1 实现和当前可执行离线/隔离测试已完成；**未达到完整正式发布标准**，不创建正式 Release。
- 尚无远端和 PR，未公开推送；Manifest 仓库 URL 为预期目标地址，不能据此宣称仓库已创建。
- 本次未修改/部署生产核心、现有好感度插件、生产配置或数据；未重启 MaiBot、QQ、NapCat、Xvfb，未修改网络和云计费。
- 本地新增源码，无旧版本插件需要恢复，也无生产备份点。以后安装/部署必须在单独批准范围内建立完整可恢复备份；本包不携带任何生产回滚脚本。
- 本机任务收尾另按维护规则追加主日志、同步技能根日志并更新对应已验证经验，这些维护资料不放入公开插件包。

## 23:50 受控真实 API 测试补记

用户本轮明确授权使用提供的 Key 做少量测试。Key 通过 stdin 传给隔离子进程，仅在内存中使用；未写入项目文件、命令行参数、环境变量、报告、维护日志或交付包。没有安装/启用生产插件，也没有调用真实模型。

- 搜索词：`中国国家博物馆官网`，最多 3 条结果，单请求超时 10 秒，独立持久化测试额度上限 2 次。
- **实际只发出 1 次 HTTP 请求，无自动重试，无第二种 Header 请求。**默认 `X-Appbuilder-Authorization` 鉴权返回 HTTP 200。
- 实际调用本项目 BaiduClient、SearchService、SQLite 预留和 Command handler；搜索成功，解析 3 条网页结果，含 `https://www.chnmuseum.cn/` 和 `https://en.chnmuseum.cn/`。命令格式化及 SDK send.text 返回路径通过，发送端为隔离替身，未向 QQ 发消息。
- 真实返回的第三条摘要是 HTTP 504 错误页面片段，不能作为实质来源证据。API 成功不保证每条摘要有用，时间字段也只是服务返回值，未核验网页真实发布时间。
- 终端采集存在 CP936/UTF-8 显示不一致，中文输出显示损坏；报告保留结构化状态、已知输入词和未受影响的 ASCII URL/英文标题，没有猜测或重建损坏摘要。已把私有探测脚本输出固定为 UTF-8，没有为排版问题额外消耗真实调用。
- 本次证明当前 Key 对默认 Header 和该接口的单次调用可用；**未验证另一种 Header、账户免费权益或账单实际收费**。
- 完整 Host IPC、真实 QQ 收发、真实 Planner 调度及现场 Python 3.13 执行当时继续待验收、属于候选阶段，后续已完成验收并正式发布。

可公开脱敏数据见 [LIVE_API_TEST.json](LIVE_API_TEST.json)。此前“真实 API 未验证/真实请求 0 次”为首次离线阶段历史记录，本补记将累计实际请求更新为 1 次。插件运行源码未改，只更新验证文档、候选包文件白名单和检查摘要，因此没有重复运行 116 项运行逻辑测试；本轮重新执行 Ruff、差异、包完整性及解包/哈希检查。
