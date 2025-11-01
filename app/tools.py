from langchain.tools import tool
import requests, math
from .retriever import get_retriever
from .core.config import get_settings

@tool
def calculator(expression: str) -> str:
    try:
        result = eval(expression, {"__builtins__": {"abs": abs, "round": round, "math": math}})
        return f"结果是：{result}"
    except Exception as e:
        return f"计算错误: {e}"

@tool
def weather(city: str) -> str:
    url = f"https://wttr.in/{city}?format=3"
    try:
        return requests.get(url, timeout=5).text
    except:
        return "天气服务暂不可用。"

@tool
def doc_search(query: str) -> str:
    settings = get_settings()
    retriever = get_retriever(settings=settings)
    docs = retriever.invoke(query)
    if not docs:
        return "知识库中暂无相关内容。"
    return "\n".join([d.page_content for d in docs[:2]])
