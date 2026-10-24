# 发布状态与兼容性复核

复核日期：2026-10-25（北京时间）。本次仅在本地隔离环境验证，不连接生产实例，不使用真实 Key、聊天、QQ 发送或模型请求。

## 当前发布状态

- [v0.1.0 Release](https://github.com/Toyaspio/maibot-baidu-search/releases/tag/v0.1.0) 已公开发布，其标签源码保持首次发布快照。
- main 的 `.gitignore`、插件分类、文档及本次兼容性修正位于 CHANGELOG 的“未发布”部分，需要后续新版本发布才会进入 Release。此处“未发布”不指 v0.1.0。
- TEST_REPORT、LIVE_API_TEST、VALIDATION、ACCEPTANCE_RESULT 记录不同历史验证阶段。其日期、次数和历史布尔值不作为当前仓库发布状态；真人验收结论见 ACCEPTANCE_REPORT。
- 原有 dist/delivery 文件属于旧交付快照，不能用新文档替换后继续声称其哈希或内容相同。新包应在新版本发布时重新构建。

## 测试矩阵

| Host 源码 | 实际导入 SDK | 本次隔离测试 | 真人搜索及回复 |
| --- | --- | --- | --- |
| MaiBot 1.3.5 的原验收源码快照 | 2.10.0 | 117 通过，0 失败、0 跳过 | 原验收已确认；本次未重复 |
| 官方 MaiBot v1.3.15 标签源码 | 2.16.0（PyPI wheel） | 117 通过，0 失败、0 跳过 | 本次未执行 |

本次解释器为 Windows Python 3.12.14；httpx 0.28.1、pydantic 2.14.1。原服务器验收的 Python 3.13.16 / SDK 2.10.0 结果仍为历史记录。未在生产安装测试依赖。

测试使用未修改的 Host PluginLoader、Runner、RPC、TCP/MsgPack、鉴权、组件注册表及选取的工具结果解析方法。HTTP 搜索由 MockTransport 模拟，send.text 只记录到内存。日志、版本读取和配置辅助设施隔离，未启动完整机器人或真实 LLM。覆盖默认配置、工具可见性、成功及失败结果、命令、重载和预算持久化；117 项通过不代表所有宿主功能或每个中间版本都已实测。

新版 Loader 会跳过已禁用插件的入口。测试在重载前通过真实 Runner 保存启用配置，以匹配管理员更新流程；没有删除重载、配额或停搜断言。测试也分别断言旧版 SDK 越界拒绝和新版 SDK 越界告警放行的实际规则。

## 兼容范围与校验规则

Manifest 声明 MaiBot 1.3.5–1.3.15 / SDK 2.10.0–2.16.0。上下界组合已测试，中间版本未逐一测试，更高版本不作兼容保证。

已核对的 Host 1.3.5 和 1.3.15 校验器均允许高于声明上限、但主次版本相同的 Host 补丁版本以警告方式加载。因此“主程序一更新必然被挡住”不适用于这些校验器。跨主次版本仍可能拒绝。旧 Host 对 SDK 越界报错，新 Host 1.3.15 则告警放行；不能把新规则倒推为所有旧版本的行为。详见 [官方 Manifest 文档](https://docs.mai-mai.org/plugin/manifest)。

## 复现

准备匹配版本源码和 SDK/测试依赖，按 README 设置 MAISEARCH_HOST_SOURCE 与 MAISEARCH_TOOLING_SOURCE。新组合额外设置：

```text
MAISEARCH_HOST_VERSION=1.3.15
MAISEARCH_SDK_VERSION=2.16.0
MAISEARCH_SDK_RANGE_POLICY=warn
python -m pytest -q
```

旧组合使用 1.3.5、2.10.0、reject。环境变量仅向测试的隔离版本设施提供准确版本，不会替换实际导入的 SDK，也不能将旧源码标成新版本。未提供 Host 源码时，相关测试明确跳过；应报告跳过数。

本次不修改旧标签，不自动创建 Release 或提交插件中心审核结论。发布新版本前应同步 Manifest 版本、构建脚本、变更记录与标签。

## 本次源码指纹（SHA-256）

- `_manifest.json`：`0843f12576ada8ce2dde7d4768edb6e830dbc4b4aa44e3448847967fd91c0173`
- `build_release.py`：`46c21c3de800445fc1705efb73308e5833eddf9c7515348e47dafc3fa980902c`
- `tests/test_runner_integration.py`：`d4c9e594adad28c5d35909eefc3a688a8040b50c1f71665f8cda427515be1e3f`
- `tests/test_wire_integration.py`：`adba48422ccb8a172a1d6c5ddab77aef29161431ca69375aba24a97a9aa3ab6c`

VALIDATION.json 中 code_sha256 保留原验收时的哈希；测试设施和构建白名单的本次变化以上述指纹为准，五个运行模块未改。
