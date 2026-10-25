# MaiSearch - 百度搜索插件

为 MaiBot 接入百度网页搜索，支持通过聊天命令查询信息，也可以让麦麦在需要时自主搜索。

插件使用百度千帆官方搜索 API，不需要爬取百度搜索页面。

## 功能

* **手动搜索**：发送 `/baidu 关键词`，获取网页标题、摘要和来源链接。
* **自主搜索**：启用 `baidu_web_search` 后，麦麦可以根据对话需要查询公开信息。
* **调用限制**：支持每日额度、独立的自主搜索额度及请求冷却。
* **后台配置**：可以设置 API Key、搜索结果数量、超时时间等。
* **搜索记录保护**：不主动读取聊天历史或长期记忆，仅向百度发送必要的搜索关键词。

自主搜索默认关闭，管理员可以按需启用。

### 自主搜索如何工作

启用后，麦麦在聊天中遇到需要查询最新公开信息的问题时，可以自行调用 `baidu_web_search` 搜索网页，再根据标题、摘要和来源链接组织回复，不需要用户手动发送 `/baidu` 命令。是否搜索由麦麦的规划器决定，并非每条消息都会联网。

使用前需要配置 API Key，同时开启插件总开关和 `search.llm_enabled`。自主搜索同样受到每日额度及请求冷却限制。

## 安装

从 [Releases](https://github.com/Toyaspio/maibot-baidu-search/releases) 获取发布版本，按照 MaiBot 插件管理流程安装。

安装完成后，在插件配置中填写百度 AppBuilder API Key，并开启插件。

API Key 可以通过配置文件填写，也支持使用 `MAISEARCH_API_KEY` 环境变量。请勿将密钥提交到公开仓库。

## 使用

手动搜索：

```text
/baidu 中国国家博物馆官网
/baidu 明朝内阁制度的形成
```

麦麦会返回相关网页的标题、摘要和来源地址。

如需自主联网搜索，在配置中开启 `search.llm_enabled`，并按宿主要求重新加载插件。

## 常用配置

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `plugin.enabled` | false | 插件总开关 |
| `search.llm_enabled` | false | 允许麦麦自主搜索 |
| `search.daily_limit` | 20 | 每日总请求额度 |
| `search.tool_daily_limit` | 5 | 每日自主搜索额度 |
| `search.max_results` | 5 | 单次最多返回的网页结果 |
| `search.timeout_seconds` | 10 | 请求超时秒数 |

配置由 MaiBot 插件系统生成，无需自行创建完整配置文件。

## 兼容性

当前 main 分支的声明范围为 MaiBot 1.3.5～1.3.15、SDK 2.10.0～2.16.0。已在部分版本组合上进行测试，中间版本未逐一验证。

已发布的 v0.1.0 标签仍使用最初的兼容范围。请以所安装版本的 Manifest 为准。

具体测试环境和结果见[兼容性报告](docs/COMPATIBILITY_REPORT.md)及[验收报告](docs/ACCEPTANCE_REPORT.md)。

## 注意事项

使用前需要自行申请百度千帆 AppBuilder API Key，并确认账号的调用权限和计费规则。插件内的每日额度只限制本插件请求，不能替代云平台账单限制。

网页摘要仅供参考，重要内容请打开原始来源核实。

## 开发与反馈

项目由 Toyaspio 维护，采用 MIT 许可证。

欢迎通过 [Issues](https://github.com/Toyaspio/maibot-baidu-search/issues) 反馈问题或提出改进建议。

相关资料：[MaiBot 文档](https://docs.mai-mai.org/plugin/) · [百度搜索 API](https://ai.baidu.com/ai-doc/AppBuilder/pmaxd1hvy) · [更新记录](CHANGELOG.md)
