# hw-chat
hw-chat 项目的后端服务，负责处理业务逻辑、数据存储和API接口的提供。采用稳健的后端技术，确保服务的稳定性和可扩展性。

## 使用示例

使用 Postman 或其他 HTTP 客户端工具访问 API 接口：

### POST 请求示例

```http
http://localhost:6006/api/chat/knowledge_base_chat

{
    "query":"什么是GLM4 多角色对话",
    "user_id":"admin",
    "conversation_id": "df221b2f-ea52-4200-82f5-fcfc011e6786", 
    "conversation_name":"新对话",
    "knowledge_base_name":"private",
    "top_k":"3",
    "score_threshold":"0.5",
    "history":[],
    "history_len": 3,
    "stream": false,
    "model_name":"chatglm3-6b",
    "prompt_name":"default"
}
```
# rag-project
