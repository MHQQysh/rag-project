from langchain_core.prompts import ChatPromptTemplate
from pydantic import Field, BaseModel

from llm_models.all_llm import llm


# 数据模型 - 回答质量评分
class GradeAnswer(BaseModel):
    """评估回答是否解决用户问题的二元评分模型"""

    binary_score: str = Field(
        description="回答是否解决了问题，取值为'yes'或'no'"
    )


# 初始化带函数调用的LLM
structured_llm_grader = llm.with_structured_output(GradeAnswer)  # 绑定结构化输出到评分模型

# 提示词模板
system = """您是一个评估回答是否解决用户问题的评分器。\n
     给出'yes'或'no'的二元评分。'yes'表示:回答确实解决了该问题。"""
answer_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),  # 系统角色设定
        ("human", "用户问题: \n\n {question} \n\n 生成回答: {generation}"),  # 用户输入模板
    ]
)

# 构建回答质量评估工作流
answer_grader_chain = (
        answer_prompt  # 使用回答评估提示模板
        | structured_llm_grader  # 调用结构化评分的LLM
)
