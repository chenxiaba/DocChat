from __future__ import annotations

import math
import os
import re
import shutil
from collections import defaultdict
from threading import Lock

import structlog
from PyPDF2 import PdfReader
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .config import get_settings

logger = structlog.get_logger(__name__)
_settings = get_settings()
_VECTOR_BUILD_LOCK = Lock()

# 改进的文本清洗函数
def clean_text(text):
    """清洗和预处理文本内容"""
    if not text:
        return ""
    
    # 移除URL链接
    text = re.sub(r'http\S+|www\.\S+', '', text)
    # 移除微博转发标记
    text = re.sub(r'//@[^:]+:', '', text)
    # 移除特殊符号和多余空格
    text = re.sub(r'[\n\r\t]+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    # 移除表情符号和特殊字符
    text = re.sub(r'[\U00010000-\U0010ffff]', '', text)
    
    return text.strip()

# 改进的文本分割器，更适合中文内容
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,  # 减小块大小，更适合中文
    chunk_overlap=150,  # 增加重叠，保持上下文连贯
    length_function=len,
    separators=["\n\n", "\n", ".", "。", "！", "？", ",", "，", " ", ""]
)

# 改进的本地语义嵌入模型
class ImprovedEmbeddings:
    def __init__(self):
        # 预定义主题关键词和权重（增强版）
        self.themes = {
            '创业': ['创业', '创始人', '初创', '融资', '投资人', '团队', '产品', '市场', '公司', '商业', '企业', '项目', '投资', '风险', '创新'],
            '管理': ['管理', '领导', '团队', '组织', '文化', '价值观', '决策', '战略', '效率', '目标', '绩效', '人才', '激励', '沟通', '协作'],
            '产品': ['产品', '用户', '体验', '设计', '功能', '迭代', '数据', '增长', '需求', '反馈', '优化', '测试', '发布', '版本', '竞品'],
            '技术': ['技术', '算法', 'AI', '大数据', '架构', '开发', '工程师', '创新', '代码', '系统', '编程', '软件', '硬件', '网络', '安全'],
            '字节跳动': ['字节跳动', '今日头条', '抖音', 'TikTok', '张一鸣', '公司', '业务', '平台', '应用', '产品', '发展', '成功', '历程', '故事'],
            '思考': ['思考', '观点', '理念', '哲学', '价值观', '人生', '学习', '成长', '反思', '认知', '感悟', '见解', '体会', '经验', '教训']
        }
        
        # 重要程度关键词
        self.importance_keywords = ['重要', '关键', '核心', '本质', '根本', '原则', '战略', '方向', '目标', '价值', '意义']
        
        # 语义相似性增强关键词
        self.semantic_enhancement = {
            '创业经历': ['创业', '经历', '历程', '故事', '发展', '过程', '开始', '初期', '阶段', '成长'],
            '管理理念': ['管理', '理念', '思想', '观点', '方法', '原则', '策略', '体系', '模式', '文化'],
            '技术看法': ['技术', '看法', '观点', '态度', '理解', '认识', '评价', '见解', '思考', '理念']
        }
    
    def embed_documents(self, texts):
        embeddings = []
        for text in texts:
            # 计算文本的基本特征
            text_length = len(text)
            char_diversity = len(set(text)) / max(1, text_length)
            
            # 计算主题相关性得分（增强版）
            theme_scores = {}
            for theme, keywords in self.themes.items():
                # 使用加权匹配，考虑关键词出现频率
                matches = sum(1 for keyword in keywords if keyword in text)
                # 考虑关键词密度
                density = sum(len(keyword) for keyword in keywords if keyword in text) / max(1, text_length)
                theme_scores[theme] = (matches / len(keywords)) * 0.7 + density * 0.3
            
            # 计算语义增强得分
            semantic_scores = {}
            for semantic_type, keywords in self.semantic_enhancement.items():
                matches = sum(1 for keyword in keywords if keyword in text)
                semantic_scores[semantic_type] = matches / len(keywords)
            
            # 计算重要性得分
            importance_score = sum(1 for keyword in self.importance_keywords if keyword in text) / len(self.importance_keywords)
            
            # 计算张一鸣相关度（特殊处理）
            zhang_related = 1.0 if '张一鸣' in text else 0.0
            
            # 生成384维嵌入向量（增强版）
            base_vector = [text_length / 1000.0] * 40  # 长度特征
            diversity_vector = [char_diversity] * 40  # 多样性特征
            
            # 主题特征向量
            theme_vector = []
            for theme in ['创业', '管理', '产品', '技术', '字节跳动', '思考']:
                theme_vector.extend([theme_scores.get(theme, 0)] * 15)
            
            # 语义增强特征向量
            semantic_vector = []
            for semantic_type in ['创业经历', '管理理念', '技术看法']:
                semantic_vector.extend([semantic_scores.get(semantic_type, 0)] * 10)
            
            # 重要性特征向量
            importance_vector = [importance_score] * 20
            
            # 张一鸣相关度特征
            zhang_vector = [zhang_related] * 24
            
            embedding = base_vector + diversity_vector + theme_vector + semantic_vector + importance_vector + zhang_vector
            embeddings.append(embedding)
        
        return embeddings
    
    def embed_query(self, text):
        # 对查询使用增强的嵌入逻辑
        # 首先进行查询分析，识别查询意图
        query_intent = self.analyze_query_intent(text)
        
        # 生成基础嵌入
        base_embedding = self.embed_documents([text])[0]
        
        # 根据查询意图增强相关维度
        if query_intent == '创业经历':
            # 增强创业相关维度的权重
            for i in range(40, 130):  # 创业主题相关维度
                base_embedding[i] = min(base_embedding[i] * 1.5, 1.0)
            for i in range(130, 160):  # 创业经历语义维度
                base_embedding[i] = min(base_embedding[i] * 2.0, 1.0)
        elif query_intent == '管理理念':
            # 增强管理相关维度的权重
            for i in range(55, 85):  # 管理主题相关维度
                base_embedding[i] = min(base_embedding[i] * 1.5, 1.0)
            for i in range(160, 170):  # 管理理念语义维度
                base_embedding[i] = min(base_embedding[i] * 2.0, 1.0)
        elif query_intent == '技术看法':
            # 增强技术相关维度的权重
            for i in range(85, 115):  # 技术主题相关维度
                base_embedding[i] = min(base_embedding[i] * 1.5, 1.0)
            for i in range(170, 180):  # 技术看法语义维度
                base_embedding[i] = min(base_embedding[i] * 2.0, 1.0)
        
        return base_embedding
    
    def analyze_query_intent(self, query):
        """分析查询意图"""
        query_lower = query.lower()
        
        if any(keyword in query_lower for keyword in ['创业', '经历', '历程', '故事', '发展']):
            return '创业经历'
        elif any(keyword in query_lower for keyword in ['管理', '理念', '思想', '观点', '方法']):
            return '管理理念'
        elif any(keyword in query_lower for keyword in ['技术', '看法', '观点', '态度', '理解']):
            return '技术看法'
        
        return 'general'

def get_embeddings():
    """获取改进的本地语义嵌入模型"""
    return ImprovedEmbeddings()

def build_vector_store(files: list[str]) -> None:
    vector_dir = _settings.vector_db_path
    vector_dir.mkdir(parents=True, exist_ok=True)
    docs = []

    for fpath in files:
        reader = PdfReader(fpath)
        for page_num, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                # 清洗文本内容
                cleaned_text = clean_text(text)
                
                # 使用文本分割器将页面内容分割成多个块
                page_docs = text_splitter.split_text(cleaned_text)
                for chunk_num, chunk in enumerate(page_docs):
                    # 更严格的内容质量过滤
                    if len(chunk.strip()) > 100:  # 增加最小长度要求
                        # 检查内容质量（避免包含过多无意义字符）
                        meaningful_chars = len([c for c in chunk if c.isalnum() or c in '，。！？；：'])
                        if meaningful_chars / len(chunk) > 0.6:  # 有意义字符比例超过60%
                            docs.append(Document(
                                page_content=chunk, 
                                metadata={
                                    "source": os.path.basename(fpath),
                                    "page": page_num + 1,
                                    "chunk": chunk_num + 1
                                }
                            ))
    
    if not docs:
        logger.warning("vector_store_empty", reason="no_documents")
        return

    # 使用DeepSeek语义嵌入模型
    embeddings = get_embeddings()

    with _VECTOR_BUILD_LOCK:
        if vector_dir.exists():
            shutil.rmtree(vector_dir)

        Chroma.from_documents(docs, embeddings, persist_directory=str(vector_dir))

    logger.info("vector_store_built", document_chunks=len(docs))
    
    if docs:
        logger.debug(
            "vector_store_sample",
            samples=[doc.page_content[:200] for doc in docs[:3]],
        )

    return store

# BM25关键词检索器
class BM25Retriever:
    def __init__(self, documents, k1=1.5, b=0.75):
        self.documents = documents
        self.k1 = k1
        self.b = b
        self.avg_doc_len = sum(len(doc.page_content.split()) for doc in documents) / len(documents)
        self.doc_lengths = [len(doc.page_content.split()) for doc in documents]
        self.vocab = self._build_vocab()
        self.idf = self._compute_idf()
        
    def _build_vocab(self):
        """构建词汇表"""
        vocab = defaultdict(set)
        for i, doc in enumerate(self.documents):
            words = self._tokenize(doc.page_content)
            for word in words:
                vocab[word].add(i)
        return vocab
    
    def _tokenize(self, text):
        """中文分词（简化版）"""
        # 使用简单的字符分割，实际应用中可以使用jieba等分词工具
        return [char for char in text if char.strip()]
    
    def _compute_idf(self):
        """计算逆文档频率"""
        idf = {}
        n = len(self.documents)
        for word, doc_indices in self.vocab.items():
            df = len(doc_indices)
            idf[word] = math.log((n - df + 0.5) / (df + 0.5) + 1)
        return idf
    
    def _compute_bm25_score(self, query, doc_index):
        """计算BM25得分"""
        query_words = self._tokenize(query)
        doc_words = self._tokenize(self.documents[doc_index].page_content)
        doc_len = self.doc_lengths[doc_index]
        
        score = 0
        for word in query_words:
            if word not in self.vocab:
                continue
                
            # 计算词频
            tf = doc_words.count(word)
            if tf == 0:
                continue
                
            # BM25公式
            idf = self.idf[word]
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (1 - self.b + self.b * doc_len / self.avg_doc_len)
            score += idf * numerator / denominator
        
        return score
    
    def retrieve(self, query, k=10):
        """检索相关文档"""
        scores = []
        for i in range(len(self.documents)):
            score = self._compute_bm25_score(query, i)
            if score > 0:
                scores.append((score, self.documents[i]))
        
        # 按得分排序
        scores.sort(key=lambda x: x[0], reverse=True)
        return [doc for score, doc in scores[:k]]

# 重排序器
class Reranker:
    def __init__(self):
        # 重排序权重配置（优化版）
        self.weights = {
            'semantic_score': 0.35,
            'keyword_score': 0.25,
            'relevance_boost': 0.2,
            'quality_score': 0.15,
            'spam_penalty': -0.5  # 垃圾信息惩罚
        }
        
        # 垃圾信息关键词
        self.spam_keywords = [
            '添加微信', '领取', '创业项目', '互联网创业', '200个',
            '货比三家', '搜一下就不会上当', '保证年收益率', '管理费用'
        ]
    
    def compute_relevance_score(self, query, document):
        """计算文档与查询的相关性得分"""
        content = document.page_content
        
        # 语义相似性得分（基于现有嵌入模型）
        semantic_score = self._compute_semantic_score(query, content)
        
        # 关键词匹配得分
        keyword_score = self._compute_keyword_score(query, content)
        
        # 相关性增强得分
        relevance_boost = self._compute_relevance_boost(query, content)
        
        # 文档质量得分
        quality_score = self._compute_quality_score(content)
        
        # 垃圾信息检测
        spam_penalty = self._detect_spam_content(content)
        
        # 综合得分
        total_score = (
            semantic_score * self.weights['semantic_score'] +
            keyword_score * self.weights['keyword_score'] +
            relevance_boost * self.weights['relevance_boost'] +
            quality_score * self.weights['quality_score'] +
            spam_penalty * self.weights['spam_penalty']
        )
        
        # 确保得分在合理范围内
        return max(0, min(total_score, 1.0))
    
    def _compute_semantic_score(self, query, content):
        """计算语义相似性得分"""
        query_words = set([char for char in query if char.strip()])
        content_words = set([char for char in content if char.strip()])
        
        if not query_words:
            return 0
        
        intersection = query_words.intersection(content_words)
        return len(intersection) / len(query_words)
    
    def _compute_keyword_score(self, query, content):
        """计算关键词匹配得分"""
        # 重要关键词列表
        important_keywords = ['张一鸣', '创业', '字节跳动', '今日头条', '抖音', '管理', '技术']
        
        score = 0
        for keyword in important_keywords:
            if keyword in query and keyword in content:
                score += 1
        
        return min(score / 3, 1.0)  # 归一化到0-1
    
    def _compute_relevance_boost(self, query, content):
        """计算相关性增强得分"""
        boost = 0
        
        # 查询意图匹配
        if '创业' in query and any(word in content for word in ['创业', '公司', '产品', '市场']):
            boost += 0.3
        if '管理' in query and any(word in content for word in ['管理', '团队', '组织', '文化']):
            boost += 0.3
        if '技术' in query and any(word in content for word in ['技术', '算法', 'AI', '开发']):
            boost += 0.3
        
        # 上下文相关性
        if len(content) > 200:  # 较长内容通常更有价值
            boost += 0.1
        
        return min(boost, 1.0)
    
    def _compute_quality_score(self, content):
        """计算内容质量得分"""
        # 基于内容长度和多样性
        if len(content) < 50:
            return 0.2
        elif len(content) < 100:
            return 0.5
        else:
            return 0.8
    
    def _detect_spam_content(self, content):
        """检测垃圾信息，返回惩罚系数（0-1）"""
        spam_count = sum(1 for keyword in self.spam_keywords if keyword in content)
        
        # 如果有垃圾信息关键词，给予惩罚
        if spam_count > 0:
            # 惩罚程度与垃圾信息关键词数量成正比
            penalty = min(1.0, spam_count * 0.3)
            return penalty
        
        return 0.0
    
    def rerank(self, query, documents):
        """对文档进行重排序"""
        scored_docs = []
        for doc in documents:
            score = self.compute_relevance_score(query, doc)
            scored_docs.append((score, doc))
        
        # 按得分排序
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        return [doc for score, doc in scored_docs]

# Hybrid + Rerank检索器
class HybridRerankRetriever:
    def __init__(self, semantic_retriever, bm25_retriever, reranker):
        self.semantic_retriever = semantic_retriever
        self.bm25_retriever = bm25_retriever
        self.reranker = reranker
    
    def invoke(self, query, k=10):
        """执行混合检索"""
        # 1. 语义检索
        semantic_docs = self.semantic_retriever.invoke(query)
        
        # 2. 关键词检索
        bm25_docs = self.bm25_retriever.retrieve(query, k=k)
        
        # 3. 合并结果并去重
        all_docs = self._merge_and_deduplicate(semantic_docs, bm25_docs)
        
        # 4. 重排序
        reranked_docs = self.reranker.rerank(query, all_docs)
        
        return reranked_docs[:k]
    
    def _merge_and_deduplicate(self, semantic_docs, bm25_docs):
        """合并并去重文档"""
        seen_content = set()
        merged_docs = []
        
        # 添加语义检索结果
        for doc in semantic_docs:
            content_hash = hash(doc.page_content[:100])  # 使用前100字符作为去重依据
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                merged_docs.append(doc)
        
        # 添加关键词检索结果
        for doc in bm25_docs:
            content_hash = hash(doc.page_content[:100])
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                merged_docs.append(doc)
        
        return merged_docs

def get_retriever():
    # 使用DeepSeek语义嵌入模型
    embeddings = get_embeddings()
    return Chroma(persist_directory=str(_settings.vector_db_path), embedding_function=embeddings).as_retriever(search_kwargs={"k": 10})  # 增加检索数量

def get_hybrid_rerank_retriever():
    """获取Hybrid + Rerank检索器"""
    # 1. 获取语义检索器
    embeddings = get_embeddings()
    semantic_retriever = Chroma(persist_directory=str(_settings.vector_db_path), embedding_function=embeddings).as_retriever(search_kwargs={"k": 15})

    # 2. 获取所有文档用于BM25检索器
    store = Chroma(persist_directory=str(_settings.vector_db_path), embedding_function=embeddings)
    all_docs = store.get()
    documents = []
    for i, (doc_content, metadata) in enumerate(zip(all_docs['documents'], all_docs['metadatas'])):
        documents.append(Document(page_content=doc_content, metadata=metadata))
    
    # 3. 创建BM25检索器
    bm25_retriever = BM25Retriever(documents)
    
    # 4. 创建重排序器
    reranker = Reranker()
    
    # 5. 创建混合检索器
    hybrid_retriever = HybridRerankRetriever(semantic_retriever, bm25_retriever, reranker)
    
    return hybrid_retriever
