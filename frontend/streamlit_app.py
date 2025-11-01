import streamlit as st
import requests
import time
import os
import pickle
from datetime import datetime
import base64

API_URL = "http://localhost:8000/chat"
STREAM_API_URL = "http://localhost:8000/chat_stream"
UPLOAD_URL = "http://localhost:8000/upload_pdfs"
RESET_URL = "http://localhost:8000/reset_memory"
CLEAR_KB_URL = "http://localhost:8000/clear_knowledge_base"
LIST_DOCS_URL = "http://localhost:8000/list_documents"
DELETE_DOC_URL = "http://localhost:8000/delete_document"
CLEAR_HISTORY_URL = "http://localhost:8000/clear_history"

st.set_page_config(page_title="DocChat AI - 智能文档问答", page_icon="📚", layout="wide")

# 添加基本的CSS样式确保文本换行
st.markdown("""
<style>
    /* 确保文本换行 */
    .stMarkdown, .stMarkdown * {
        word-wrap: break-word !important;
        word-break: break-word !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("📚 DocChat AI - 智能文档问答")

# 对话历史存储文件路径 - 统一到data目录
HISTORY_FILE = "data/chat_history.pkl"

# 保存对话历史到持久化存储的函数
def save_history_to_storage(history):
    """保存对话历史到持久化存储"""
    try:
        # 确保data目录存在
        os.makedirs("data", exist_ok=True)
        # 保存到文件
        with open(HISTORY_FILE, "wb") as f:
            pickle.dump(history, f)
        # 同时更新session state
        st.session_state["history"] = history
    except Exception as e:
        st.error(f"保存对话历史失败: {str(e)}")

# 从持久化存储加载对话历史的函数
def load_history_from_storage():
    """从持久化存储加载对话历史"""
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "rb") as f:
                return pickle.load(f)
        return []
    except:
        return []

# 初始化对话历史 - 从持久化存储加载
if "history" not in st.session_state:
    st.session_state["history"] = load_history_from_storage()

with st.sidebar:
    # 知识库文档展示 - 移到最上面
    st.header("📚 知识库文档")
    
    # 获取文档列表
    try:
        response = requests.get(LIST_DOCS_URL)
        if response.status_code == 200:
            data = response.json()
            documents = data.get("documents", [])
            
            if documents:
                st.write(f"📄 当前知识库中有 {len(documents)} 个文档：")
                
                for doc in documents:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"• {doc['filename']} ({doc['size_mb']} MB)")
                    with col2:
                        if st.button("🗑️", key=f"delete_{doc['filename']}", help=f"删除 {doc['filename']}"):
                            try:
                                delete_response = requests.post(f"{DELETE_DOC_URL}/{doc['filename']}")
                                if delete_response.status_code == 200:
                                    result = delete_response.json()
                                    st.success(f"{result['status']}: {result['message']}")
                                    st.rerun()  # 刷新页面
                                else:
                                    st.error(f"删除失败: {delete_response.status_code}")
                            except Exception as e:
                                st.error(f"删除文档时发生错误: {str(e)}")
            else:
                st.info("📭 知识库为空，请上传PDF文档")
        else:
            st.error("获取文档列表失败")
    except Exception as e:
        st.error(f"获取文档列表时发生错误: {str(e)}")
    
    st.divider()
    
    # 上传PDF功能
    st.header("📂 上传PDF文档")
    files = st.file_uploader("上传文件", type=["pdf"], accept_multiple_files=True)
    if st.button("📘 构建知识库") and files:
        payload = []
        for file in files:
            try:
                encoded = base64.b64encode(file.read()).decode("utf-8")
                payload.append({"filename": file.name, "content": encoded})
            except Exception as exc:
                st.error(f"文件 {file.name} 编码失败: {exc}")
                continue  # 继续处理其他文件而不是返回

        if payload:  # 只有在有有效文件时才上传
            resp = requests.post(UPLOAD_URL, json=payload)
            if resp.status_code == 200:
                st.success(resp.json().get("status", "知识库已更新"))
            else:
                st.error(f"上传失败: {resp.status_code}")
        else:
            st.error("没有有效的文件可以上传")

    st.divider()
    
    # 清理功能
    st.header("🧹 清理功能")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🧹 清空记忆"):
            requests.post(RESET_URL)
            st.success("记忆已清空")
    with col2:
        if st.button("🗑️ 清理对话历史"):
            # 调用后端API
            try:
                response = requests.post(CLEAR_HISTORY_URL)
                if response.status_code == 200:
                    st.success("对话历史已清理")
                else:
                    st.error("清理对话历史失败")
            except Exception as e:
                st.error(f"调用API失败: {str(e)}")
            
            # 清空前端存储（包括文件存储）
            save_history_to_storage([])
            st.rerun()
    
    st.divider()
    
    # 知识库管理
    st.subheader("🗑️ 知识库管理")
    if st.button("🗂️ 清理知识库", type="secondary", help="删除所有上传的PDF文档和向量数据库"):
        try:
            response = requests.post(CLEAR_KB_URL)
            if response.status_code == 200:
                result = response.json()
                st.success(f"{result['status']}: {result['message']}")
                st.rerun()  # 刷新页面
            else:
                st.error(f"清理失败: {response.status_code}")
        except Exception as e:
            st.error(f"清理知识库时发生错误: {str(e)}")

st.subheader("💬 对话区")
query = st.chat_input("请输入问题...")

# 显示所有历史消息
for i, msg in enumerate(st.session_state["history"]):
    if msg["role"] == "user":
        with st.chat_message("user"):
            # 使用原生的markdown渲染器
            content = msg['content']
            st.markdown(content)
    else:
        with st.chat_message("assistant"):
            # 使用原生的markdown渲染器
            content = msg['content']
            st.markdown(content)


def process_sse_stream(buffer, data_buffer=""):
    """
    处理实时生成的 SSE 流式数据，确保有效数据不丢失，并保留换行符。
    :param buffer: 当前实时接收的数据片段
    :param data_buffer: 之前接收到的数据缓冲区，初始为空
    :return: 返回有效的解析数据列表，并更新data_buffer为剩余部分
    """
    data_buffer += buffer  # 将当前接收到的数据追加到已有的数据缓冲区
    result = []  # 存储有效的解析数据
    is_done = False  # 标记是否遇到结束标记 'DONE'

    # 检查数据缓冲区，提取每个有效的数据块
    while True:
        start_index = data_buffer.find("data: ")  # 查找数据块的开始标记
        end_index = data_buffer.find("data: DONE")  # 查找结束标记

        if start_index == -1:  # 没有找到数据块的开始，退出循环，等待更多数据
            break
        
        # 找到有效数据块的开始位置
        start_index += len("data: ")  # 从 'data: ' 后开始
        
        # 如果没有找到 'DONE'，就提取到当前缓冲区的结尾
        if end_index == -1:
            end_index = len(data_buffer)-2
        
        # 提取有效数据
        valid_data = data_buffer[start_index:end_index]

        if valid_data:
            result.append(valid_data)

        # 清除已经处理过的数据
        data_buffer = data_buffer[end_index+2 + len("data: DONE"):]

        # 如果找到 'data: DONE' 标记，结束处理
        if "data: DONE" in data_buffer:
            is_done = True
            break

    # 返回有效数据，并将剩余的部分继续保存到 data_buffer
    return result, data_buffer, is_done


if query:
    # 立即显示用户消息
    with st.chat_message("user"):
        # 使用原生的markdown渲染器
        st.markdown(query)
    
    # 保存用户消息到历史记录
    st.session_state["history"].append({"role": "user", "content": query})
    # 保存到持久化存储
    save_history_to_storage(st.session_state["history"])
    
    # 使用流式API
    full_response = ""
    try:
        response = requests.post(STREAM_API_URL, json={"query": query}, stream=True)
        
        if response.status_code == 200:
            # 创建Markdown渲染器
            with st.chat_message("assistant"):
                # 创建占位符用于流式渲染
                markdown_placeholder = st.empty()
                
                # 初始化Markdown缓冲区
                markdown_buffer = ""
                
                # 处理流式响应（按照SSE协议正确解析）
                buffer = ""
                data_buffer = ""
                for chunk in response.iter_content(chunk_size=1024):  # 增大chunk_size
                    if not chunk:
                        continue

                    try:
                        buffer = chunk.decode("utf-8")
                    except UnicodeDecodeError:
                        # 如果解码失败，尝试忽略错误并继续累积
                        buffer = chunk.decode("utf-8", errors="ignore")

                    # 每次接收到的缓冲区数据是流式的
                    results, data_buffer, is_done = process_sse_stream(buffer, data_buffer)

                    # 实时更新显示
                    markdown_buffer = "".join(results)
                    full_response += markdown_buffer
                    markdown_placeholder.markdown(full_response)

                    # 如果遇到 DONE 结束标志，退出循环
                    if is_done:
                        print("数据接收完成。")
                        break
        else:
            # 处理非200状态码
            full_response = f"API请求失败，状态码：{response.status_code}"
            with st.chat_message("assistant"):
                st.markdown(full_response)
    
    except Exception as e:
        full_response = f"抱歉，发生错误：{str(e)}"
        with st.chat_message("assistant"):
            st.markdown(full_response)
    
    # 保存助手消息到历史记录
    if full_response and full_response.strip():
        st.session_state["history"].append({"role": "assistant", "content": full_response})
    else:
        # 如果响应为空，添加默认提示
        default_response = "抱歉，未能生成有效响应，请重试。"
        st.session_state["history"].append({"role": "assistant", "content": default_response})
    
    # 保存到持久化存储
    save_history_to_storage(st.session_state["history"])
