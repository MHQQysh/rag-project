from langchain_core.messages import AIMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from graph.get_human_message import get_last_human_message
from llm_models.all_llm import llm
from utils.log_utils import log


def generate(state):
    """
    生成答案

    参数:
        state (messages): 当前状态

    返回:
         dict: 包含重述问题的更新后状态
    """
    log.info("---生成最终的答案---")
    messages = state["messages"]
    question = get_last_human_message(messages).content
    last_message = messages[-1]

    docs = last_message.content

    # 提示模板
    prompt = PromptTemplate(
        template="你是一个问答任务助手。请根据以下检索到的上下文内容回答问题。如果不知道答案，请直接说明。回答保持简洁。\n问题：{question} \n上下文：{context} \n回答：",
        input_variables=["question", "context"],
    )
    # 处理链
    rag_chain = prompt | llm | StrOutputParser()
    # 执行
    response = rag_chain.invoke({"context": docs, "question": question})
    ai_message = AIMessage(content=response)
    return {"messages": [ai_message]}