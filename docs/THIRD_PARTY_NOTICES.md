# 第三方依赖及许可检查

检查日期：2026-10-24。插件代码原创，MIT；没有复制其他搜索插件、嵌入 SDK/Runner 源码或分发第三方依赖包。SDK 和宿主仅在忽略的私有开发目录/独立源码路径供接口核对与测试使用，不进入 Git 或交付 ZIP。

## 运行依赖

| 项目 | 本次版本 | 许可来源与注意事项 |
| --- | --- | --- |
| maibot-plugin-sdk | 2.10.0（现用源码） | [PyPI 2.10.0 元数据](https://pypi.org/project/maibot-plugin-sdk/2.10.0/) 与官方仓库声明 LGPL-3.0-only；[源码与许可证](https://github.com/Mai-with-u/maibot-plugin-sdk)。由宿主提供，MIT 不覆盖 SDK |
| httpx | 0.28.1 | BSD-3-Clause；[官方许可证](https://github.com/encode/httpx/blob/0.28.1/LICENSE.md) |
| httpcore | 1.0.9 | BSD-3-Clause，已安装分发元数据 |
| anyio | 4.15.1 | MIT，已安装分发元数据 |
| certifi | 2026.10.23 | MPL-2.0，已安装分发元数据；证书数据及其文件级许可单独保留 |
| idna | 3.20 | BSD-3-Clause，已安装分发元数据 |
| h11 | 0.16.0 | MIT，已安装分发元数据 |

SDK 自身依赖由宿主管理。本地用于导入 SDK 的版本：pydantic 2.14.1 / pydantic-core 2.50.1（MIT）、annotated-types 0.8.0（MIT）、typing-extensions 4.16.0（PSF-2.0）、typing-inspection 0.4.4（MIT）、msgpack 1.2.3（Apache-2.0）。这些是本地测试版本，不冒称与生产环境的全部依赖版本相同。

## 开发和隔离集成测试

pytest 8.4.2、ruff 0.17.2、tomlkit 0.15.2 均为 MIT；packaging 26.3 为 Apache-2.0 OR BSD-2-Clause，来自已安装分发元数据。它们不作为插件运行依赖打包。开发工具自身的其他依赖也不打包；本次不是对宿主全部依赖的许可证审计。

后续增加 jsonschema 作为真实 Host 组件注册表的隔离测试依赖；实装不更换宿主的该依赖，公开包仍只含本项目源码，不内嵌其实现或二进制。

未发现上述许可要求将本项目原创源码改为非 MIT。BSD/MIT/PSF/Apache 的通知要求、MPL 的对应文件义务、LGPL 对 SDK 本身的修改/再分发义务仍需分别遵守；不能把 MIT 文件当成第三方的重新授权。后续若改为分发依赖、打包可执行文件或修改 SDK，须重新检查所分发文件并附相应许可证和源代码获取说明。当前交付策略是只分发本项目源码和文档。

百度服务是外部服务，不因代码采用 MIT 就获得额度、付费权限或内容再分发授权；使用者还需遵守 [官方 API 文档](https://ai.baidu.com/ai-doc/AppBuilder/pmaxd1hvy) 和对应账号服务条款。搜索摘录和原网站内容不归本插件所有。
