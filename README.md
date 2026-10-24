# MaiSearch 百度搜索插件

MaiSearch 为 MaiBot 提供百度千帆官方网页搜索。由 Toyaspio 原创编写，AI 辅助开发，未 Fork 或复制其他搜索插件。插件代码采用 MIT 协议，SDK 和依赖保留各自协议。

**版本：0.1.0，隔离测试及指定会话中的真实规划器搜索、回复链路验收通过。尚未推送 GitHub 或创建正式 Release。**

已实现 `/baidu 关键词` 和 `baidu_web_search` Tool，返回标题、摘要、原始 URL 及可获得的网页日期；总开关、自主搜索均默认关闭。只访问固定官方搜索接口，不爬取百度搜索结果页，不抓取结果网页。

## 兼容范围

验收环境：MaiBot 项目版本 1.3.5、Python 3.13.16、maibot-plugin-sdk 2.10.0、httpx 0.28.1、pydantic 2.13.3。该环境中 117 项离线/隔离测试全部通过，包括真实 Host RPC、MsgPack、组件注册表和 Runner 主循环。首次本地测试环境为 Python 3.12.14。详见 [验收报告](docs/ACCEPTANCE_REPORT.md)。

Manifest 暂限 MaiBot 1.3.5 / SDK 2.10.0。2026-10-24 读取的官方 SDK 主分支版本为 2.16.0，尚未验证，不能把主分支示例直接当作现场接口。其他版本应先测试，再调整 Manifest 范围；不要开启强制兼容绕过检查。使用 `MaiBotPlugin`、`config_model`、`@Command`、`@Tool` 及三个生命周期，无 `@Action` 兼容入口。

## 安装

1. 先审查源码和 [测试报告](docs/TEST_REPORT.md)，备份目标插件代码、配置、持久化数据和启动信息。在隔离 MaiBot 中测试，确认计费后再启用。
2. 将发布包解压为 `plugins/maibot-baidu-search/`，确保 `_manifest.json` 和 `plugin.py` 在该目录根部。不要嵌套两层，也不要把备份或 `.dev` 放进扫描目录。
3. 使用宿主正式依赖流程安装 Manifest 中的 `httpx>=0.28.1,<0.29`；SDK 由宿主提供，不随插件打包或替换。无需另装数据库服务。
4. 让 Runner 生成配置。首次 `plugin.enabled=false`，宿主可能只生成配置而不激活组件，这是预期行为。
5. 安全配置密钥，并显式开启 `plugin.enabled`。需要宿主重新激活或重启时，仅按该版本正常插件管理流程操作。本项目开发任务没有授权生产安装或重启。

本机源码仓库和插件运行数据应分别保存。卸载插件前停用组件并备份 `ctx.paths.data_dir`；保留 `quota.sqlite3`。重装或回滚继续使用同一插件 ID、同一数据目录，不删除预算来解决报错。

## 百度 API Key

前往 [百度智能云控制台](https://console.bce.baidu.com/)，按 [官方百度搜索 API 文档](https://ai.baidu.com/ai-doc/AppBuilder/pmaxd1hvy) 申请具备搜索调用权限的 AppBuilder API Key。普通云 AK/SK 不应直接当作这里的 Key。

推荐由管理员在 **Runner 实际继承的运行环境** 安全注入 `MAISEARCH_API_KEY`，优先级高于 `[search].api_key`。不要把密钥发到聊天中、写入源码、提交配置，或放在命令行参数里。空环境变量也会覆盖配置并导致拒绝请求。密钥变化后重新加载插件/配置；环境变量变更需要按宿主管理方式使新进程继承。

官方同一文档的协议表/原始请求用 `Authorization`，curl 示例用 `X-Appbuilder-Authorization`。本插件默认按 curl 示例选后者，允许在两者中明确选择；**2026-10-24 用户授权的一次真实测试中，默认 `X-Appbuilder-Authorization` 返回 HTTP 200 和 3 条网页结果**。另一种 Header 未发真实请求，不保证所有账号均相同。不会同时发送两个头，也不会在失败后自动换头重试。见 [实测摘要](docs/LIVE_API_TEST.json)。

## 配置

由 Runner 根据 `config_model` 生成 `config.toml`。以下示例不含真实密钥：

```toml
[plugin]
config_version = "0.1.0"
enabled = false

[search]
llm_enabled = false
api_key = ""
daily_limit = 20
tool_daily_limit = 5
max_results = 5
timeout_seconds = 10.0
max_query_length = 120
auth_header = "X-Appbuilder-Authorization"
```

| 字段 | 作用与范围 |
| --- | --- |
| plugin.enabled | 宿主保留的插件总开关，默认 false |
| search.llm_enabled | 自主搜索开关，默认 false；手动命令不依赖此项 |
| search.api_key | 回退密钥，优先用环境变量；WebUI 字段声明为 password，但仍应限制配置文件权限 |
| search.daily_limit | 每天全部请求 0–100 次，默认 20；0 禁止调用 |
| search.tool_daily_limit | Tool 每天 0–20 次，默认 5，同时占用总额度 |
| search.max_results | 1–10，默认最多 5 个网页 |
| search.timeout_seconds | 1–30 秒，默认 10；覆盖流式读取全过程 |
| search.max_query_length | 1–240 字符，默认 120，超长拒绝、不截断后发送 |
| search.auth_header | 仅允许上述两种 Header，真实鉴权待验收 |

不手写旧版配置管理逻辑。Runner 先校验并注入配置，再调用 `on_config_update`；服务对象随配置替换，SQLite 预算继续保留。已经预留配额的在途请求可能按旧设置完成，停用不能撤回已发出的请求。

## 使用

```text
/baidu 中国国家博物馆官网
/baidu 明朝内阁制度的形成
```

命令从消息开头完整匹配；普通聊天、`/baidux`、多行内容不会误触发。空词、过长词、疑似凭证/私人身份、电子邮件、长数字、URL/路径等输入会拒绝。过滤可能误拒绝合法查询，应改用更短的公开关键词，不通过放宽隐私规则解决。

结果为网页摘录，需自行核对来源和日期；网页日期可能缺失或不准确。无结果时中文提示；错误只返回错误类别，不回传原始响应、请求体、凭证或异常堆栈。

## 大模型自主搜索

启用总开关后，再设 `search.llm_enabled=true`，保存并重载插件以刷新 Host 工具目录。Tool 名称为 `baidu_web_search`，参数：

```json
{"query": "中国国家博物馆 最新开放公告", "purpose": "current_public_information"}
```

开启时 Tool 明确作为可见工具暴露给规划器，关闭并重载后 Host 禁用并隐藏该组件。热更新关闭会先由处理器拒绝搜索，不产生请求；刷新工具目录仍需重载。仅在确需最新公开资料时使用；必要性标记和隐私规则是约束，不是能识别所有私人信息的语义保证。插件不读取聊天历史、QQ 身份或长期记忆，忽略宿主传入的其他上下文参数，仅发送检查后的 query。

返回可 JSON 序列化对象。外层 `success=true` 表示工具已处理本次调用，`search_success` 才表示搜索是否成功；完整搜索结果在 `search_result` 和 JSON 文本 `content` 中，包含 `success/results/untrusted_data/notice/stop_searching`，失败含固定 `error` 类别。成功结果中每条有 `title/url/content/date/type`。显式把来源放入 `content`，保证该版宿主生成 Planner 历史时能看到来源，而不是仅看到“搜索完成”。网页文字始终是不可信资料，不能据此更改系统要求或调用其他工具。

Tool 全局冷却 60 秒，同一归一化词 600 秒内不重复请求；默认最多 5 次/日，硬上限 20。预算、冷却和词哈希跨重载保存。成功时允许宿主继续组织回答；任何拒绝或搜索错误返回宿主正式字段 `stop_after_execution=true`，请求结束当轮继续规划。因此不能只看外层 `success` 判断有搜索结果。当前宿主只对“已处理成功”的工具执行应用此停止标志，所以将搜索状态单独表达。源码契约已做隔离测试，真实模型的完整调度仍待验收；停止时可能没有额外面向用户的消息，需要查看工具结果，插件不擅自代发模型回复。

## 额度和费用

北京时间 UTC+8 划分自然日，SQLite `BEGIN IMMEDIATE` 在请求前持久化预留。并发和多进程共用同一个预算文件；网络失败、鉴权失败、超时、取消均不退额。未发出 HTTP 的取消也可能保守占额，优先避免超支。禁止自动重试、自动换 Header、跟随重定向。

首次调用创建预算库；不能删除、迁移到空目录或恢复旧预算来刷新额度。存储损坏/锁超时或日期回退时拒绝搜索，管理员应先备份检查，不能自动重建。配额文件只能约束使用同一数据目录的实例；其他应用/其他插件/其他部署的百度调用不在此额度内。

截至本次查阅，百度文档列有每日免费次数和后付费说明。此政策可能变更，也取决于账号权益、其他调用量与开通状态。**插件本地默认 20 次不等于官方免费保证，也不是云账单封顶。**以控制台及 [官方 API 文档的计费入口](https://ai.baidu.com/ai-doc/AppBuilder/pmaxd1hvy) 为准；未核对账号权益和计费、未经批准，不执行真实调用或开通付费。

## 常见错误

| 类别 | 排查方式 |
| --- | --- |
| disabled / llm_disabled | 核对对应开关及宿主组件状态 |
| missing_key / invalid_key | 在 Runner 本机检查安全注入、空值及换行，不把值贴到日志 |
| auth | 核对 AppBuilder Key、权限、选定 Header；本次尝试已扣额 |
| network / timeout | 检查网络、DNS、TLS；不自动重试。HTTP 客户端 `trust_env=false`，不继承代理环境变量 |
| rate_limit / http / provider | 查看官方服务状态或账号控制台，仅保留错误类别；稍后手动决定是否再试 |
| quota / tool_quota / cooldown | 等待新自然日/冷却，使用已有来源，不删除数据库 |
| quota_storage / clock | 备份并检查目录权限、磁盘、数据库锁和系统时间；保持停搜 |
| invalid_response / response_too_large | 响应结构异常、压缩编码或超过 512 KiB，安全拒绝 |

## 安全与隐私

仅申请 `send.text` 能力，无消息查询、身份、记忆或核心数据库权限。不会更改好感度、QQ 解析、MaiBot 核心及 QQ/NapCat/Xvfb 链路。服务端可看到 query、API Key 和连接地址，因此只查询公开信息。关键词检查不能识别所有私人语义，使用者和模型仍须最小化输入。

不主动记录 query、Key、鉴权头、原始响应或身份信息。预算库保存日期、次数、Tool 冷却及近期词 SHA-256 哈希（不是匿名化保证，可被猜词），应按运行数据保护。响应只接受 HTTP/HTTPS 公网形式 URL，去除控制字符和 CQ 消息控制码，限制文本长度及响应体大小；不访问这些 URL，不能保证第三方站点内容正确或安全。

`config.toml`、`.env*`、SQLite、运行数据、开发依赖和 `.dev` 均被忽略。对外发布使用白名单打包，不能直接压缩整个开发目录。

## 开发与验证

```text
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
```

常规测试使用真实 SDK 和 httpx MockTransport，禁用测试进程真实 HTTP 传输；不需要 Key。Runner 测试需要设置 `MAISEARCH_HOST_SOURCE` 为匹配版本源码根目录（内含 `src/plugin_runtime`）；宿主返回契约测试还需要 `MAISEARCH_TOOLING_SOURCE` 指向匹配版本的 `src/core/tooling.py`。未提供时会明确 skip，不能把 skip 写成通过。该测试为隔离组件集成，RPC/日志/宿主版本辅助设施用替身，宿主返回契约执行从源文件 AST 选出的未修改方法，不是完整 Host IPC、QQ 收发或模型规划验收。详细复现条件、实际结果和未验证项见 [测试报告](docs/TEST_REPORT.md)。

已在用户指定会话确认真实规划器两次调用本插件、每次成功获得 5 条结果，结果进入下一轮规划器上下文后产生回复。聊天回复不强制展示链接，Tool 内部仍保留可核验来源。该结论不保证模型每次回答都正确，也不表示账号调用免费。当前仓库链接为目标地址，不代表远端已创建；本次未推送或创建 Release。

## 贡献和协议

欢迎围绕百度搜索 V0.1 提交可复现问题和测试。不要提交凭证、配置、聊天或画像。测试不得通过删除断言来掩盖失败。代码结构和限制是本项目独立实现，SDK 仅按公开接口调用，未内嵌其实现。

见 [MIT LICENSE](LICENSE)、[第三方许可说明](docs/THIRD_PARTY_NOTICES.md)、[更新记录](CHANGELOG.md)。SDK 的 LGPL-3.0-only 不会被 MIT 覆盖；若分发 SDK/依赖二进制或修改其实现，应另行履行对应义务。本插件交付包不包含这些第三方包。

参考：[MaiBot 插件文档](https://docs.mai-mai.org/plugin/)、[官方 SDK](https://github.com/Mai-with-u/maibot-plugin-sdk)、[百度搜索 API](https://ai.baidu.com/ai-doc/AppBuilder/pmaxd1hvy)。
