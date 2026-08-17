from tools.retriever_tools import retriever
from utils.log_utils import log


def retrieve(state):
    """
    检索相关文档
    Args:
        state (dict): 当前图状态，包含用户问题

    Returns:
        state (dict): 更新后的状态，新增包含检索结果的documents字段
    """
    log.info("---去知识库中检索文档---")  # 打印当前阶段标识
    question = state["question"]  # 从状态中获取用户问题
    # 文档检索
    documents = retriever.invoke(question)  # 调用检索器获取相关文档
    return {"documents": documents, "question": question}  # 返回更新后的状态
