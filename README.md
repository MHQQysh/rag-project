# RAG Project

本仓库包含可独立运行的 RAG 与经营分析子项目，采用并列目录，方便分别使用、部署与维护。

## 目录

| 目录 | 定位 | 主要入口 |
|---|---|---|
| [`rag-project/`](rag-project/README.md) | 完整网页知识库：FastAPI、文档上传、SQLite、DeepSeek 与 BGE-M3 | `rag-project/startup.py`、`rag-project/compose.yaml` |
| [`rag-project-langgraph/`](rag-project-langgraph/README.md) | LangGraph RAG 工作流：基础检索流程与自适应路由流程 | `graph.graph1`、`graph2.graph_2` |
| [`db-gpt-commerce/`](db-gpt-commerce/README.md) | 电商经营分析：DeepSeek SQL、明细核验、贡献分解；保留 DB-GPT 后端 | [在线体验](https://mhqqysh.github.io/rag-project/db-gpt-commerce/)、`web/`、`Start-DB-GPT.cmd` |

各子项目彼此独立，分别包含 README、依赖文件与启动方式。运行前请进入对应目录，不要在仓库根目录混装依赖。

## 推荐选择

- 需要浏览器页面、上传文件和持久化会话：使用 `rag-project/`。
- 需要研究 LangGraph 节点、路由、检索与生成流程：使用 `rag-project-langgraph/`。
- 需要网页版经营分析、输入自己的 DeepSeek Key 生成 SQL：使用 `db-gpt-commerce/`。基准模式无需 Key，Pages 版无需自建后端。

运行数据、模型缓存、虚拟环境、日志和 `.env` 均不提交到 GitHub；电商网页所附数据库为生成器重新生成的公开模拟样本。请根据各子目录的 `.env.example` 在部署机器上配置后端。
