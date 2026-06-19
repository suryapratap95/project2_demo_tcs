from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import FewShotChatMessagePromptTemplate
from .model import IntentResult
from dotenv import load_dotenv

from .prompts import FEW_SHOT_EXAMPLES, SYSTEM_PROMT
from .tools import classify_intent

load_dotenv()


llm = ChatOpenAI(model ="gpt-4o-mini", temperature=0.1)

example_prompt = ChatPromptTemplate.from_messages([("human", "{input}"), ("ai", "{output}")])


few_shot = FewShotChatMessagePromptTemplate(
    example_prompt=example_prompt,
    examples=FEW_SHOT_EXAMPLES,
)


strcutured_llm = llm.with_structured_output(IntentResult)

prompt =ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMT),
    few_shot,
    ("human", "{input}"),
])

strcutured_prompt = ChatPromptTemplate.from_template("Classify this banking message: {message}")


strcutured_chain = strcutured_prompt | strcutured_llm

# result = strcutured_chain.invoke({"message": "I was charged twice for 1 card transaction"})
# print("Structured Chain Result:", result)

# Bind the tool to the LLM
llm_with_tools = llm.bind_tools([classify_intent])
# tool_result = llm_with_tools.invoke("i get invalid fees charge on my card")
# print("Tool Call Result:", tool_result.tool_calls)

parser = StrOutputParser()

chain = prompt | llm | parser

def chat(session_id: str, message: str) -> str:
    return chain.invoke({"input": message})

# response = chain.invoke({"input": " Tell me about yourelf"})
# print("Normal Chain Result:", response)
