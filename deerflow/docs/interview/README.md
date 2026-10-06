# DeerFlow × RAG 项目面试题解

120 道题，12 个主题；每题包含口述回答、原理、追问、边界和源码依据。不是只列问题的题单。

- [在线阅读与练习](https://shihongyuan.cn/rag-project/deerflow-interview/)：搜索、章节和难度筛选、随机抽题、已掌握标记。
- [先读项目总述](overview.md)：架构、请求链路、个人改动与七天学习顺序。
- [完整 Markdown 题解](complete-guide.md)：适合 GitHub 阅读与版本比较。
- [打印版 HTML](print.html)：下载后离线打开，可使用浏览器打印为 PDF。

代码依据为本次导入快照，路径以 deerflow/ 为根；../ 开头指向并列子项目。源码链接指向主分支，后续代码升级应同步复核题解。部署事实以 2026-10-06 文档为准；设计建议不代表已经实现。

| 章 | 主题 | 题号 |
| --- | --- | --- |
| 01 | [项目定位与个人贡献](chapter-01.md) | Q001—Q010 |
| 02 | [总体架构与代码导航](chapter-02.md) | Q011—Q020 |
| 03 | [请求、会话与运行状态](chapter-03.md) | Q021—Q030 |
| 04 | [Agent 与模型调用](chapter-04.md) | Q031—Q040 |
| 05 | [工具、技能、MCP 与沙箱](chapter-05.md) | Q041—Q050 |
| 06 | [子 Agent、任务分解与并发](chapter-06.md) | Q051—Q060 |
| 07 | [上下文、记忆与多模态](chapter-07.md) | Q061—Q070 |
| 08 | [RAG 原理与同仓库整合](chapter-08.md) | Q071—Q080 |
| 09 | [前端、流式响应与交互](chapter-09.md) | Q081—Q090 |
| 10 | [持久化、可靠性与测试](chapter-10.md) | Q091—Q100 |
| 11 | [部署、资源、域名与 GitHub](chapter-11.md) | Q101—Q110 |
| 12 | [演示登录、安全与面试压轴](chapter-12.md) | Q111—Q120 |

## 维护

修改 questions.json 与 overview.md，再执行 `python -X utf8 deerflow/docs/interview/build.py` 生成章节、完整版和交互页。打印版由 render-html 技能脚本离线渲染；生成记录见 review.json。

传入 `--renderer /path/to/render_html.py` 可同时更新打印版并展开全部答案。未提供该参数时不会更新 print.html。

交互页是无外部依赖的单文件 HTML，练习标记只保存于当前浏览器，不上传、不调用模型、不收集账号或 API Key。GitHub Pages 只发布阅读页面；完整 Agent 仍需要后端服务。
