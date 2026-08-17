from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from llm_models.all_llm import llm


# 数据模型 - 文档相关性评分
class GradeDocuments(BaseModel):
    """对检索到的文档进行相关性评分的二元判断"""

    binary_score: str = Field(
        description="文档是否与问题相关，取值为'yes'或'no'"
    )


# 带函数调用的LLM初始化
structured_llm_grader = llm.with_structured_output(GradeDocuments)  # 绑定结构化输出到评分模型

# 提示词模板
system = """你是一个评估检索文档与用户问题相关性的评分器。\n 
    如果文档包含与用户问题相关的关键词或语义含义，则评为相关。\n
    不需要非常严格的测试，目的是过滤掉错误的检索结果。\n
    给出'yes'或'no'的二元评分来表示文档是否与问题相关。"""
grade_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),  # 系统角色提示
        ("human", "Retrieved document: \n\n {document} \n\n User question: {question}"),  # 用户输入模板
    ]
)

# 构建检索评分器工作流
retrieval_grader_chain = grade_prompt | structured_llm_grader  # 组合提示模板和LLM评分器
