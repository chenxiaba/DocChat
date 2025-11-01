from langgraph.graph import StateGraph
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from .retriever import get_retriever, get_hybrid_rerank_retriever
from .core.config import Settings, get_settings
from typing import TypedDict, List

try:
    import streamlit as st
except ModuleNotFoundError:  # pragma: no cover - optional in backend-only deployments
    st = None  # type: ignore


def _resolve_api_key(settings: Settings) -> str | None:
    if settings.deepseek_api_key:
        return settings.deepseek_api_key
    if st is None:
        return None
    try:
        return st.secrets["general"]["DEEPSEEK_API_KEY"]
    except Exception:  # pragma: no cover - optional runtime dependency
        return None

class AgentState(TypedDict):
    query: str
    docs: List
    summary: str
    reflection: str
    response: str

# 文档摘要生成器
def generate_document_summary(
    docs_text, settings: Settings | None = None
):
    """使用AI模型生成文档内容的智能摘要"""
    settings = settings or get_settings()
    if not docs_text:
        return ""

    # 初始化DeepSeek AI模型
    try:
        api_key = _resolve_api_key(settings)
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY is not configured")
        llm = ChatOpenAI(
            model="deepseek-chat",
            api_key=api_key,
            base_url=settings.openai_api_base,
            temperature=0.3  # 较低温度以获得更稳定的摘要
        )
        
        # 创建摘要提示模板
        summary_prompt = ChatPromptTemplate.from_template("""
请对以下文档内容进行智能摘要：

文档内容：
{docs_text}

摘要要求：
1. 提取关键信息和核心观点
2. 保持原文的主要内容和意图
3. 摘要要简洁明了，突出重点
4. 如果内容较多，可以分段摘要
5. 摘要长度控制在原文的20-30%左右

请生成文档摘要：
""")
        
        # 生成文档摘要
        summary_chain = summary_prompt | llm
        summary_response = summary_chain.invoke({"docs_text": docs_text})
        
        return summary_response.content
        
    except Exception as e:
        print(f"文档摘要生成失败: {e}")
        # 如果摘要失败，返回原始文档的前500个字符作为简单摘要
        return docs_text[:500] + "..." if len(docs_text) > 500 else docs_text

# AI模型智能响应生成器
def generate_ai_response(
    query, docs_text, settings: Settings | None = None
):
    """使用AI模型基于文档内容生成智能响应"""
    settings = settings or get_settings()
    if not docs_text:
        return "抱歉，知识库中暂无相关内容。请尝试上传相关文档或询问其他问题。"

    print(f"=== AI响应生成开始 ===")
    print(f"查询内容: {query}")
    print(f"文档长度: {len(docs_text)} 字符")

    # 初始化DeepSeek AI模型
    try:
        api_key = _resolve_api_key(settings)
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY is not configured")
        llm = ChatOpenAI(
            model="deepseek-chat",
            api_key=api_key,
            base_url=settings.openai_api_base,
            temperature=0.8  # 提高温度以获得更多样化的响应
        )
        
        # 根据查询类型定制化提示模板
        if "张一鸣" in query:
            prompt_template = """
你是一个专业的AI助手，专门分析张一鸣的创业思考和管理理念。

用户问题：{query}

相关文档内容：
{docs_text}

请基于张一鸣的微博内容，生成一个生动、有深度的回答。要求：
1. 回答要体现张一鸣的个人风格和思考深度
2. 重点突出创业思考、管理理念或技术观点
3. 使用自然的对话语气，避免模板化表达
4. 可以适当引用微博中的具体内容
5. **采用总分结构**：先给出总体观点或结论，然后分点详细阐述
6. **严格使用markdown格式**：必须使用标题(#, ##, ###)、粗体(**text**)、列表(- item)等markdown元素来增强可读性
7. **确保良好的段落结构**：使用空行分隔段落，让内容层次清晰
8. **避免文字过密**：确保段落之间有足够的间距，提高可读性
9. **格式示例**：
   # 主标题
   这是主标题的内容
   
   ## 子标题
   这是子标题的内容
   
   - 列表项1
   - 列表项2
   
   **重点内容**需要加粗

请严格按照以上格式生成回答：
"""
        elif "字节跳动" in query:
            prompt_template = """
你是一个专业的AI助手，专门分析字节跳动的企业文化和发展历程。

用户问题：{query}

相关文档内容：
{docs_text}

请基于文档内容，生成一个专业、有深度的回答。要求：
1. 重点分析字节跳动的管理理念、产品思维或技术创新
2. 回答要体现字节跳动的企业文化特点
3. 使用专业的商业分析语言
4. 可以结合具体案例或数据进行分析
5. **采用总分结构**：先给出总体观点或结论，然后分点详细阐述
6. **严格使用markdown格式**：必须使用标题(#, ##, ###)、粗体(**text**)、列表(- item)等markdown元素来增强可读性
7. **确保良好的段落结构**：使用空行分隔段落，让内容层次清晰
8. **避免文字过密**：确保段落之间有足够的间距，提高可读性
9. **格式示例**：
   # 主标题
   这是主标题的内容
   
   ## 子标题
   这是子标题的内容
   
   - 列表项1
   - 列表项2
   
   **重点内容**需要加粗

请严格按照以上格式生成回答：
"""
        else:
            prompt_template = """
你是一个专业的AI助手，需要基于提供的文档内容来回答用户的问题。

用户问题：{query}

相关文档内容：
{docs_text}

请根据以上文档内容，生成一个专业、准确、个性化的回答。要求：
1. 回答要直接针对用户的问题，避免通用模板
2. 根据查询内容调整回答风格和语气
3. 重点突出文档中的关键信息和独特观点
4. **采用总分结构**：先给出总体观点或结论，然后分点详细阐述
5. **严格使用markdown格式**：必须使用标题(#, ##, ###)、粗体(**text**)、列表(- item)等markdown元素来增强可读性
6. **确保良好的段落结构**：使用空行分隔段落，让内容层次清晰
7. 如果文档内容不足，可以适当说明但不要使用固定模板
8. **格式示例**：
   # 主标题
   这是主标题的内容
   
   ## 子标题
   这是子标题的内容
   
   - 列表项1
   - 列表项2
   
   **重点内容**需要加粗

请严格按照以上格式生成回答：
"""
        
        # 创建智能提示模板
        prompt = ChatPromptTemplate.from_template(prompt_template)
        
        # 生成AI响应
        chain = prompt | llm
        response = chain.invoke({"query": query, "docs_text": docs_text})
        
        # 直接使用AI模型生成的markdown格式内容
        response_content = response.content
        
        print(f"=== AI原始响应 ===")
        print(f"原始响应长度: {len(response_content)} 字符")
        print(f"原始响应内容: {response_content}")
        print(f"原始换行符数量: {response_content.count(chr(10))}")
        print(f"原始段落分隔数量: {response_content.count('\\n\\n')}")
        print(f"=== AI响应生成结束 ===")
        
        return response_content
        
    except Exception as e:
        # 如果AI模型调用失败，回退到本地响应生成器
        print(f"AI模型调用失败，使用本地响应生成器: {e}")
        return generate_local_response(query, docs_text)

# 流式AI模型智能响应生成器
async def generate_ai_response_stream(
    query, docs_text, settings: Settings | None = None
):
    """使用AI模型基于文档内容生成流式智能响应"""
    settings = settings or get_settings()
    if not docs_text:
        yield "抱歉，知识库中暂无相关内容。请尝试上传相关文档或询问其他问题。"
        return
    
    print(f"=== 流式AI响应生成开始 ===")
    print(f"查询内容: {query}")
    print(f"文档长度: {len(docs_text)} 字符")
    
    # 初始化DeepSeek AI模型（支持流式）
    try:
        api_key = _resolve_api_key(settings)
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY is not configured")
        llm = ChatOpenAI(
            model="deepseek-chat",
            api_key=api_key,
            base_url=settings.openai_api_base,
            temperature=0.8,  # 提高温度以获得更多样化的响应
            streaming=True  # 启用流式输出
        )
        
        # 根据查询类型定制化提示模板
        if "张一鸣" in query:
            prompt_template = """
你是一个专业的AI助手，专门分析张一鸣的创业思考和管理理念。

用户问题：{query}

相关文档内容：
{docs_text}

请基于张一鸣的微博内容，生成一个生动、有深度的回答。要求：
1. 回答要体现张一鸣的个人风格和思考深度
2. 重点突出创业思考、管理理念或技术观点
3. 使用自然的对话语气，避免模板化表达
4. 可以适当引用微博中的具体内容
5. **采用总分结构**：先给出总体观点或结论，然后分点详细阐述
6. **严格使用markdown格式**：必须使用标题(#, ##, ###)、粗体(**text**)、列表(- item)等markdown元素来增强可读性
7. **确保正确的换行格式**：每个markdown元素（如标题、列表项等）后必须添加换行符，确保前端能正确解析
8. **强制换行规则**：
   - 每个标题(#)后面必须紧跟一个换行符
   - 每个列表项(-)后面必须紧跟一个换行符
   - 每个段落结束后必须添加一个空行
   - 粗体(**)标记不需要额外换行，但其所在的句子结束后需要换行
9. **确保良好的段落结构**：使用空行分隔段落，让内容层次清晰
10. **避免文字过密**：确保段落之间有足够的间距，提高可读性
11. **格式示例**（严格按照此格式）：
    # 主标题
    
    这是主标题下的内容段落。
    
    ## 子标题
    
    这是子标题下的内容段落。
    
    - 列表项一
    
    - 列表项二
    
    **重点内容**需要加粗。
    
    另一个段落内容。

请严格按照以上格式生成回答，确保每个markdown元素后都有正确的换行：
"""
        elif "字节跳动" in query:
            prompt_template = """
你是一个专业的AI助手，专门分析字节跳动的企业文化和发展历程。

用户问题：{query}

相关文档内容：
{docs_text}

请基于文档内容，生成一个专业、有深度的回答。要求：
1. 重点分析字节跳动的管理理念、产品思维或技术创新
2. 回答要体现字节跳动的企业文化特点
3. 使用专业的商业分析语言
4. 可以结合具体案例或数据进行分析
5. **采用总分结构**：先给出总体观点或结论，然后分点详细阐述
6. **严格使用markdown格式**：必须使用标题(#, ##, ###)、粗体(**text**)、列表(- item)等markdown元素来增强可读性
7. **确保正确的换行格式**：每个markdown元素（如标题、列表项等）后必须添加换行符，确保前端能正确解析
8. **强制换行规则**：
   - 每个标题(#)后面必须紧跟一个换行符
   - 每个列表项(-)后面必须紧跟一个换行符
   - 每个段落结束后必须添加一个空行
   - 粗体(**)标记不需要额外换行，但其所在的句子结束后需要换行
9. **确保良好的段落结构**：使用空行分隔段落，让内容层次清晰
10. **避免文字过密**：确保段落之间有足够的间距，提高可读性
11. **格式示例**（严格按照此格式）：
    # 主标题
    
    这是主标题下的内容段落。
    
    ## 子标题
    
    这是子标题下的内容段落。
    
    - 列表项一
    
    - 列表项二
    
    **重点内容**需要加粗。
    
    另一个段落内容。

请严格按照以上格式生成回答，确保每个markdown元素后都有正确的换行：
"""
        else:
            prompt_template = """
你是一个专业的AI助手，需要基于提供的文档内容来回答用户的问题。

用户问题：{query}

相关文档内容：
{docs_text}

请根据以上文档内容，生成一个专业、准确、个性化的回答。要求：
1. 回答要直接针对用户的问题，避免通用模板
2. 根据查询内容调整回答风格和语气
3. 重点突出文档中的关键信息和独特观点
4. **采用总分结构**：先给出总体观点或结论，然后分点详细阐述
5. **严格使用markdown格式**：必须使用标题(#, ##, ###)、粗体(**text**)、列表(- item)等markdown元素来增强可读性
6. **确保正确的换行格式**：每个markdown元素（如标题、列表项等）后必须添加换行符，确保前端能正确解析
7. **强制换行规则**：
   - 每个标题(#)后面必须紧跟一个换行符
   - 每个列表项(-)后面必须紧跟一个换行符
   - 每个段落结束后必须添加一个空行
   - 粗体(**)标记不需要额外换行，但其所在的句子结束后需要换行
8. **确保良好的段落结构**：使用空行分隔段落，让内容层次清晰
9. 如果文档内容不足，可以适当说明但不要使用固定模板
10. **格式示例**（严格按照此格式）：
    # 主标题
    
    这是主标题下的内容段落。
    
    ## 子标题
    
    这是子标题下的内容段落。
    
    - 列表项一
    
    - 列表项二
    
    **重点内容**需要加粗。
    
    另一个段落内容。

请严格按照以上格式生成回答，确保每个markdown元素后都有正确的换行：
"""
        
        # 生成流式AI响应
        prompt = ChatPromptTemplate.from_template(prompt_template)
        chain = prompt | llm
        response_stream = chain.astream({"query": query, "docs_text": docs_text})
        
        # 流式输出响应内容，逐字显示（蹦字效果）
        full_response = ""
        chunk_count = 0
        
        async for chunk in response_stream:
            if hasattr(chunk, 'content'):
                full_response += chunk.content
                chunk_count += 1
                
                # 直接输出每个字符，实现蹦字效果
                if chunk.content:
                    yield chunk.content
                
                if chunk_count % 50 == 0:  # 每50个chunk打印一次进度
                    print(f"流式处理中 - 已接收 {chunk_count} 个chunk，当前响应长度: {len(full_response)} 字符")
        
        # 蹦字效果不需要处理剩余chunk，因为每个字符都已经直接输出了
        
        print(f"=== 流式响应收集完成 ===")
        print(f"总chunk数量: {chunk_count}")
        print(f"完整响应长度: {len(full_response)} 字符")
        print(f"原始响应内容: {full_response}")
        print(f"原始换行符数量: {full_response.count(chr(10))}")
        print(f"原始段落分隔数量: {full_response.count('\\n\\n')}")
        print(f"=== 流式AI响应生成结束 ===")
        
    except Exception as e:
        # 如果AI模型调用失败，回退到本地响应生成器
        print(f"AI模型流式调用失败，使用本地响应生成器: {e}")
        response = generate_local_response(query, docs_text)
        # 将本地响应分成小块流式输出
        chunk_size = 20
        for i in range(0, len(response), chunk_size):
            yield response[i:i+chunk_size]

# 本地响应生成器（备用方案）
def generate_local_response(query, docs_text):
    """基于文档内容生成本地响应"""
    if not docs_text:
        return "抱歉，知识库中暂无相关内容。请尝试上传相关文档或询问其他问题。"
    
    # 将文档内容分割成句子
    lines = docs_text.split('\n')
    
    # 提取有意义的句子
    meaningful_lines = [s for s in lines if len(s.strip()) > 20]
    
    if meaningful_lines:
        return f"根据文档内容，与您的问题相关的信息如下：\n\n{chr(10).join(meaningful_lines[:8])}\n\n如需更详细信息，请参考上传的文档。"
    else:
        return f"根据文档内容，相关信息如下：\n\n{docs_text}\n\n如需更详细信息，请参考上传的文档。"

def retrieve_node(state):
    settings = get_settings()
    retriever = get_hybrid_rerank_retriever(settings=settings)
    query = state["query"]
    docs = retriever.invoke(query)
    return {"docs": docs}

def summarize_node(state):
    docs_text = "\n".join([d.page_content for d in state["docs"][:3]])
    return {"summary": f"相关文档摘要：{docs_text[:300]}..."}

def reflect_node(state):
    return {"reflection": "基于文档内容进行回答。"}

def response_node(state):
    # 使用所有检索到的文档内容，不做限制
    docs_text = "\n".join([d.page_content for d in state["docs"]])
    settings = get_settings()
    response = generate_ai_response(state["query"], docs_text, settings=settings)
    return {"response": response}

def create_workflow(settings: Settings | None = None):
    settings = settings or get_settings()
    g = StateGraph(AgentState)
    g.add_node("retrieve", retrieve_node)
    g.add_node("summarize", summarize_node)
    g.add_node("reflect", reflect_node)
    g.add_node("response", response_node)
    g.add_edge("retrieve", "summarize")
    g.add_edge("summarize", "reflect")
    g.add_edge("reflect", "response")
    g.set_entry_point("retrieve")
    g.set_finish_point("response")
    return g.compile()

def create_simple_workflow(settings: Settings | None = None):
    """简化版工作流，使用AI模型生成智能响应"""
    settings = settings or get_settings()
    g = StateGraph(AgentState)

    def simple_response_node(state):
        """直接生成响应，使用AI模型"""
        retriever = get_hybrid_rerank_retriever(settings=settings)
        docs = retriever.invoke(state["query"])
        # 使用所有检索到的文档内容，不做限制
        docs_text = "\n".join([d.page_content for d in docs]) if docs else ""

        response = generate_ai_response(
            state["query"], docs_text, settings=settings
        )
        return {"response": response}
    
    g.add_node("simple_response", simple_response_node)
    g.set_entry_point("simple_response")
    g.set_finish_point("simple_response")
    return g.compile()
