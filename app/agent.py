from .workflow import create_workflow, create_simple_workflow
from .retriever import get_retriever
import asyncio
from typing import AsyncGenerator

# 使用简化版工作流提高性能
graph = create_simple_workflow()

# 智能的本地响应生成器
def generate_local_response(query, docs_text):
    """基于文档内容生成智能响应"""
    if not docs_text:
        return "抱歉，知识库中暂无相关内容。请尝试上传相关文档或询问其他问题。"
    
    # 智能响应生成逻辑
    if "张一鸣" in query:
        # 提取关键信息并总结
        key_points = extract_key_points(docs_text, query)
        return f"根据张一鸣的微博内容，以下是相关信息：\n\n{key_points}\n\n这些内容来自张一鸣的微博记录，反映了他的创业思考和管理理念。"
    elif "字节跳动" in query:
        key_points = extract_key_points(docs_text, query)
        return f"关于字节跳动的相关信息：\n\n{key_points}\n\n这些内容体现了字节跳动的企业文化和发展历程。"
    else:
        key_points = extract_key_points(docs_text, query)
        return f"根据文档内容，相关信息如下：\n\n{key_points}\n\n如需更详细信息，请参考上传的文档。"

def extract_key_points(docs_text, query):
    """从文档内容中提取关键信息点"""
    # 按段落分割文档内容
    paragraphs = [p.strip() for p in docs_text.split('\n') if p.strip()]
    
    # 根据查询类型提取相关信息
    key_points = []
    
    # 先尝试提取与查询高度相关的内容
    for para in paragraphs:
        # 清理段落内容，移除垃圾信息
        cleaned_para = clean_paragraph(para)
        
        # 过滤掉过短的段落（可能是不完整的句子）
        if len(cleaned_para) < 20:
            continue
            
        # 根据查询类型提取相关信息
        if "创业" in query or "创业经历" in query:
            if any(word in cleaned_para for word in ['创业', '公司', '产品', '市场', '团队', '融资', '投资人']):
                # 进一步过滤，确保内容质量
                if is_quality_content(cleaned_para):
                    key_points.append(f"• {cleaned_para}")
        elif "技术" in query or "技术看法" in query:
            if any(word in cleaned_para for word in ['技术', '算法', '产品', '开发', '创新', '代码', '编程']):
                if is_quality_content(cleaned_para):
                    key_points.append(f"• {cleaned_para}")
        elif "管理" in query or "管理理念" in query:
            if any(word in cleaned_para for word in ['管理', '团队', '组织', '文化', '领导', '激励', '考核']):
                if is_quality_content(cleaned_para):
                    key_points.append(f"• {cleaned_para}")
        else:
            # 通用情况，提取包含张一鸣的段落
            if "张一鸣" in cleaned_para and is_quality_content(cleaned_para):
                key_points.append(f"• {cleaned_para}")
    
    # 如果提取到关键点，返回它们
    if key_points:
        return "\n".join(key_points[:8])  # 最多返回8个关键点
    
    # 如果没有提取到关键点，返回经过过滤的原始内容（放宽条件）
    fallback_points = []
    for para in paragraphs[:15]:
        # 清理段落内容
        cleaned_para = clean_paragraph(para)
        
        # 放宽长度限制，但确保内容质量
        if len(cleaned_para) >= 15 and is_quality_content(cleaned_para):
            fallback_points.append(f"• {cleaned_para}")
    
    return "\n".join(fallback_points[:5]) if fallback_points else "暂无相关信息。"

def is_quality_content(paragraph):
    """判断段落内容是否高质量"""
    # 排除垃圾信息
    spam_keywords = ['添加微信', '领取', '创业项目', '200个', '互联网创业', '货比三家']
    if any(spam in paragraph for spam in spam_keywords):
        return False
    
    # 排除过短的段落
    if len(paragraph) < 30:
        return False
    
    # 排除包含过多数字和符号的段落（可能是乱码）
    digit_ratio = sum(c.isdigit() for c in paragraph) / len(paragraph)
    if digit_ratio > 0.3:
        return False
    
    # 排除包含特殊符号过多的段落
    special_chars = ['@', '#', '$', '%', '&', '*', '+', '=', '<', '>']
    special_count = sum(paragraph.count(char) for char in special_chars)
    if special_count > 5:
        return False
    
    return True

def clean_paragraph(paragraph):
    """清理段落内容"""
    # 移除多余的空格和换行
    cleaned = ' '.join(paragraph.split())
    
    # 移除URL链接
    import re
    cleaned = re.sub(r'http\S+', '', cleaned)
    
    # 移除邮箱地址
    cleaned = re.sub(r'\S+@\S+', '', cleaned)
    
    # 移除垃圾信息关键词
    spam_keywords = ['添加微信', '领取', '创业项目', '200个', '互联网创业', '货比三家', '搜一下就不会上当']
    for spam in spam_keywords:
        cleaned = cleaned.replace(spam, '')
    
    # 移除数字编号（如88、113等）
    cleaned = re.sub(r'\b\d+\b', '', cleaned)
    
    # 移除多余的空格
    cleaned = ' '.join(cleaned.split())
    
    return cleaned.strip()

def run_agentic_pipeline(query: str):
    state = {"query": query}
    result = graph.invoke(state)
    return result["response"]

async def run_agentic_pipeline_stream(query: str) -> AsyncGenerator[str, None]:
    """优化的流式版本智能体管道，使用真正的流式AI调用"""
    from .workflow import generate_ai_response_stream
    
    retriever = get_retriever()
    docs = retriever.invoke(query)
    # 使用更多文档内容（最多10个片段）
    docs_text = "\n".join([d.page_content for d in docs[:10]]) if docs else ""
    
    # 使用流式AI模型生成响应
    async for chunk in generate_ai_response_stream(query, docs_text):
        yield f"data: {chunk}\n\n"
    
    yield "data: [DONE]\n\n"
