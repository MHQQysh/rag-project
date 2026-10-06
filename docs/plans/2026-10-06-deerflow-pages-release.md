# DeerFlow Web 发布记录

日期：2026-10-06（Asia/Shanghai）。用户已授权 GitHub 上传与 Pages 部署。

- 发布代码：`73bdaa3e455809a6f05fbeb5c93ff19791716a23`。
- Actions：[37438690945](https://github.com/MHQQysh/rag-project/actions/runs/37438690945)，build / deploy 成功。
- 线上入口：https://shihongyuan.cn/rag-project/deerflow-web/ 。仓库继承账号自定义域名，原 github.io 链接转向此域名。
- 项目目录：https://github.com/MHQQysh/rag-project/tree/main/deerflow-web 。没有复制完整上游框架，也没有上传本机密钥、数据库和用户资料。

## 验证

新项目 8 项 Node 测试、原 commerce 10 项测试通过。覆盖分块、双语关键词检索、无命中、上下文限制、导出内容、UTF-8/SSE 分片、401、异常结束、取消和超时。现有真实 DeepSeek Key 经新 model.mjs 完成最小流式调用，返回 OK；凭据未打印或写入新项目。

本地浏览器检查：示例载入、来源预览、未填 Key、实际无效 Key 错误、停止生成与按钮恢复、刷新清空 Key/资料、移动/桌面布局、讲解入口。导出点击成功触发页面下载逻辑，但内置浏览器下载事件等待超时，未确认下载文件落盘；导出文本的内容与凭据排除由纯函数测试验证。

线上 HTML 和 app.mjs 返回 200，app.mjs SHA256 与发布源码相同；根页包含新项目入口，原 commerce 仍返回 200。在线内置浏览器导航检查遇到工具超时，线上真实付费 Key 的完整 UI 路径未宣称已经验证。本地真实接口流式模块测试与在线静态资源核验是分开的证据。

## 使用

打开网页 → 输入自己的 Key → 可选载入 TXT/Markdown 或示例 → 提问。没有 Key 可用“只看检索”。不需要本地 WSL/Python，也不需要把模型 Key 配进 GitHub Secrets。
