# RAG Project

本仓库将两个可独立运行的 RAG 版本拆分在并列目录中，方便分别使用、部署与维护。

## 目录

| 目录 | 定位 | 主要入口 |
|---|---|---|
| [`rag-project/`](rag-project/README.md) | 完整网页知识库：FastAPI、文档上传、SQLite、DeepSeek 与 BGE-M3 | `rag-project/startup.py`、`rag-project/compose.yaml` |
| [`rag-project-langgraph/`](rag-project-langgraph/README.md) | LangGraph RAG 工作流：基础检索流程与自适应路由流程 | `graph.graph1`、`graph2.graph_2` |

两个版本彼此独立，各自包含 README、依赖文件与启动方式。运行前请进入对应目录，不要在仓库根目录混装依赖。

## 推荐选择

- 需要浏览器页面、上传文件和持久化会话：使用 `rag-project/`。
- 需要研究 LangGraph 节点、路由、检索与生成流程：使用 `rag-project-langgraph/`。

运行数据、模型缓存、虚拟环境、日志和 `.env` 均不提交到 GitHub；请根据各子目录的 `.env.example` 在部署机器上配置。
