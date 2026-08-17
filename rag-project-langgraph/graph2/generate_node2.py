from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from llm_models.all_llm import llm


def generate(state):
    """
    生成回答
    Args:
        state (dict): 当前图状态，包含问题和检索结果
    Returns:
        state (dict): 更新后的状态，新增包含生成结果的generation字段
    """
    question = state["question"]  # 获取用户问题
    documents = state["documents"]  # 获取检索到的文档

    prompt = PromptTemplate(
        template="你是一个问答任务助手。请根据以下检索到的上下文内容回答问题。如果不知道答案，请直接说明。回答保持简洁。\n问题：{question} \n上下文：{context} \n回答：",
        input_variables=["question", "context"],
    )

    # 后处理函数 - 格式化检索到的文档
    def format_docs(docs):
        """将多个文档内容合并为一个字符串，用两个换行符分隔每个文档"""
        if isinstance(docs, list):
            return "\n\n".join(doc.page_content for doc in docs)  # 拼接所有文档内容
        else:
            return "\n\n" + docs.page_content

    # 构建RAG处理链
    rag_chain = (
            prompt |  # 第一步：使用提示模板
            llm |  # 第二步：调用语言模型
            StrOutputParser()  # 第三步：解析模型输出为字符串
    )

    # RAG生成过程
    generation = rag_chain.invoke({"context": format_docs(documents), "question": question})  # 调用RAG链生成回答
    return {"documents": documents, "question": question, "generation": generation}  # 返回更新后的状态