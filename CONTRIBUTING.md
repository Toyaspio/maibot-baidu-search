# 贡献指南

感谢帮助改进 MaiSearch。提交前请先阅读 [README](README.md) 和 [验收报告](docs/ACCEPTANCE_REPORT.md)。

## 报告问题

请提供插件、MaiBot、SDK 和 Python 版本，说明实际行为、预期行为和使用公开关键词的最小复现步骤。仅附脱敏后的错误类别及必要日志，不提交 API Key、鉴权头、config.toml、环境变量、聊天正文或身份数据。配额错误不要通过删除 SQLite 数据库复现或解决。

## 提交修改

从 main 创建工作分支，一个 PR 解决一个具体问题。说明变更原因、行为影响、测试结果以及未验证项。运行代码改动应在隔离环境验证，不直接修改生产实例。

```text
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
```

测试不需要真实 API Key。Host/Runner 集成测试需要 README 中指定的匹配宿主源码；缺少条件时记录 skip 数量，不能把跳过写成通过。不为修复测试而删除断言，不使用真实群消息或付费接口作为默认测试数据。

仅文档变更可检查事实、相对链接及示例一致性，不需要重启机器人。新增待分发文件时应审查 build_release.py 的固定白名单，避免把配置、数据库或开发目录装入源码包。本贡献指南供仓库协作使用，不要求进入插件安装包。

## 维护者发布前清单

1. 确认 main 中源码、README、CHANGELOG 和 Manifest 的版本一致；只声明已经验证的兼容范围。
2. 在匹配环境完成相关测试，记录通过、失败、跳过及未验证项；不得把历史验收当作新版本的测试结果。
3. 运行 `python build_release.py` 生成白名单源码包，检查 ZIP 目录结构、文件内容和 SHA256SUMS.txt。不要直接压缩开发目录；文档变化后如使用自建附件，应重新构建，旧 ZIP 不会自动更新。
4. 由维护者手动创建与 Manifest 版本对应的标签和 GitHub Release，核对所选提交，再附发布说明及所需源码包。发布插件中心前必须有已发布的 Release，草稿和单独标签不能替代。
5. 按 [官方贡献说明](https://github.com/Mai-with-u/plugin-repo/blob/main/CONTRIBUTING.md) 通过 [插件申请入口](https://github.com/Mai-with-u/plugin-repo/issues/new/choose) 提交，填写 Manifest 中的插件 ID 和公开仓库地址。

这些步骤不会自动创建标签、发布 Release、部署插件或调用搜索 API。发布后修复请递增版本并发布新标签，不移动已被插件中心索引的标签。

## 协议

贡献代码按仓库 [MIT 协议](LICENSE) 提交。引入第三方内容时注明来源和许可证，更新 [第三方说明](docs/THIRD_PARTY_NOTICES.md)，不要把第三方协议改写为 MIT。
