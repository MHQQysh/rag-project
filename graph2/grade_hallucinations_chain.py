from langchain_core.prompts import ChatPromptTemplate
from pydantic import Field, BaseModel

from llm_models.all_llm import llm


# 数据模型 - 生成内容幻觉评分
class GradeHallucinations(BaseModel):
    """对生成回答中是否存在幻觉进行二元评分"""

    binary_score: str = Field(
        description="回答是否基于事实，取值为'yes'或'no'"
    )


# 带函数调用的LLM初始化
structured_llm_grader = llm.with_structured_output(GradeHallucinations)  # 绑定结构化输出到评分模型

# 提示词模板
system = """您是一个评估生成内容是否基于检索事实的评分器。\n
     给出'yes'或'no'的二元评分。'yes'表示回答是基于/支持于给定事实集的。"""
hallucination_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),  # 系统角色设定
        ("human", "事实集: \n\n {documents} \n\n 生成内容: {generation}"),  # 用户输入模板
    ]
)

# 构建幻觉检测工作流
hallucination_grader_chain = (
        hallucination_prompt  # 使用幻觉检测提示模板
        | structured_llm_grader  # 调用结构化评分的LLM
)
