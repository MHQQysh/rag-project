# 源码来源与维护边界

本目录是原版 DeerFlow 的完整可追踪源码快照，作为 `MHQQysh/rag-project` 的独立子项目维护。不是子模块；克隆主仓库后即可获得这里的代码。

- 上游：[bytedance/deer-flow](https://github.com/bytedance/deer-flow)。
- 上游基础提交：`a58ab484a641fd5928ae512ad21c5c7fd7a18c18`。
- 导入的个人版本提交：`b062c4b428da98cbbe759cf332a9814d3dcfb5f1`。
- 导入日期：2026-10-06。
- 保留原 [MIT 许可证](../LICENSE) 和上游署名。此仓库不冒充官方项目。
- 快照没有携带上游完整 Git 历史；后续更新需要比较基线并审查个人补丁。

个人改动包括 ECS 部署配置、沙箱 readiness 等待从 60 秒调整到 180 秒、首页到登录页的代理跳转，以及独立普通用户的演示登录。具体说明和验收范围见 [部署文档](../deploy/ecs/README.md)。Agent 核心、多 Agent、记忆、MCP 与技能系统主要来自上游。

本次导入另修正了一个部署说明文件的乱码文件名，添加面试题解和主仓库导航，并将沙箱清理说明中写死的旧超时注释改为引用配置语义。没有携带真实 API Key、登录密钥、证书私钥、用户数据库、聊天数据、运行环境或构建包。按模板自行配置这些运行依赖，才可启动应用。

## 仓库和部署的关系

`rag-project/deerflow/` 是后续个人版本的源码入口。根目录的 Pages 工作流只发布静态导航、已有工作台和面试阅读页，不会运行这个 Python 后端，也不会自动更新 ECS 应用。

`deerflow/.github/workflows/` 保留上游工作流供参考。GitHub 只发现仓库根 `.github/workflows/` 中的工作流，因此嵌套工作流不会自动运行。需要启用 DeerFlow CI 时，应明确迁移并适配工作目录，而不是声称导入后所有上游 CI 已生效。

当前 RAG 与 DeerFlow 是并列运行的子项目。将 RAG 包装为 DeerFlow 的检索工具是后续设计，尚未因目录整合而实现。
