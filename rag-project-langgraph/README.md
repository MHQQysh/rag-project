# RAG Project

基于 LangGraph、LangChain 和 Milvus 的企业知识库 RAG 示例项目。

## 项目结构

- `agent/`：RAG Agent 示例
- `graph/`：基础 LangGraph RAG 流程
- `graph2/`：带路由、查询改写、文档评分和幻觉检查的流程
- `documents/`：Markdown 解析及 Milvus 写入、检索逻辑
- `llm_models/`：LLM 与 Embedding 配置
- `datas/md/`：知识库 Markdown 文档
- `datas/output/`：文档解析结果
- `docs/`：项目配套文档

## 安装

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

在 `.env` 中配置所需的 API Key：

```dotenv
OPENAI_API_KEY=
DEEPSEEK_API_KEY=
MILVUS_URI=http://127.0.0.1:19530
MILVUS_COLLECTION_NAME=t_collection01
```

导入知识文档前，还需要根据本机路径调整 `documents/write_milvus.py` 中的 `md_dir`。

## 运行示例

```powershell
python -m graph.graph1
python -m graph2.graph_2
```

没有 API Key 或 Milvus 时，可以直接使用仓库内 Markdown 数据运行本地离线模式：

```powershell
$env:RAG_OFFLINE_MODE="1"
python -m graph.graph1
python -m graph2.graph_2
```

离线模式使用确定性的本地关键词检索和抽取式回答，不会调用外部模型，适合先验证两个 LangGraph 流程是否能够启动和完成一次问答。

Windows 下也可以直接运行 `run-basic-offline.ps1`、`run-adaptive-offline.ps1`，或执行下面的命令同时打开两个交互窗口：

```powershell
.\start-both-offline.ps1
```

本项目的 Python 运行时、虚拟环境与模型缓存均可放在 D 盘项目目录中的 `.python/`、`.venv/` 和 `.cache/`，不依赖系统盘 Python。

`main.py` 是 IDE 创建的示例文件，不是 RAG 程序入口。
