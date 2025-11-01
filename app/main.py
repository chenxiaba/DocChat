from fastapi import FastAPI, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from .retriever import build_vector_store
from .agent import run_agentic_pipeline, run_agentic_pipeline_stream
from .memory import SQLiteMemory

app = FastAPI(title="DocChat AI API")
memory = SQLiteMemory()

class ChatRequest(BaseModel):
    query: str

@app.post("/chat")
async def chat(request: ChatRequest):
    memory.save("user", request.query)
    resp = run_agentic_pipeline(request.query)
    memory.save("assistant", resp)
    return {"response": resp}

@app.post("/chat_stream")
async def chat_stream(request: ChatRequest):
    """流式聊天接口"""
    memory.save("user", request.query)
    
    async def generate_response():
        # 保存完整的响应用于记忆
        full_response = ""
        
        async for chunk in run_agentic_pipeline_stream(request.query):
            if chunk.startswith("data: ") and not chunk.endswith("[DONE]\n\n"):
                content = chunk[6:-2]  # 移除 "data: " 和末尾的 "\n\n"
                full_response += content
            yield chunk
        
        # 保存完整的响应到记忆
        memory.save("assistant", full_response)
    
    return StreamingResponse(
        generate_response(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/plain; charset=utf-8"
        }
    )

@app.post("/upload_pdfs")
async def upload_pdfs(files: list[UploadFile]):
    paths = []
    for f in files:
        path = f"data/{f.filename}"
        with open(path, "wb") as out:
            out.write(await f.read())
        paths.append(path)
    build_vector_store(paths)
    return {"status": "知识库已更新", "count": len(paths)}

@app.post("/reset_memory")
async def reset_memory():
    memory.reset()
    return {"status": "记忆已清空"}

@app.get("/list_documents")
async def list_documents():
    """获取知识库中的文档列表"""
    import os
    
    data_dir = "data"
    documents = []
    
    if os.path.exists(data_dir):
        for filename in os.listdir(data_dir):
            if filename.endswith('.pdf'):
                file_path = os.path.join(data_dir, filename)
                file_size = os.path.getsize(file_path)
                documents.append({
                    "filename": filename,
                    "size": file_size,
                    "size_mb": round(file_size / (1024 * 1024), 2)
                })
    
    return {"documents": documents}

@app.post("/delete_document/{filename}")
async def delete_document(filename: str):
    """删除指定的文档"""
    import os
    import shutil
    from .config import VECTOR_DB_PATH
    
    # 安全检查：确保文件名只包含安全字符
    if not filename.endswith('.pdf') or '/' in filename or '\\' in filename:
        return {"status": "错误", "message": "无效的文件名"}
    
    file_path = os.path.join("data", filename)
    
    if not os.path.exists(file_path):
        return {"status": "错误", "message": "文件不存在"}
    
    # 删除PDF文件
    os.remove(file_path)
    
    # 如果向量数据库存在，也需要重建
    if os.path.exists(VECTOR_DB_PATH):
        shutil.rmtree(VECTOR_DB_PATH)
    
    return {"status": "成功", "message": f"文档 {filename} 已删除"}

@app.post("/clear_knowledge_base")
async def clear_knowledge_base():
    """清理知识库（删除向量数据库和PDF文档）"""
    import shutil
    import os
    from .config import VECTOR_DB_PATH
    
    deleted_files = []
    
    # 删除向量数据库
    if os.path.exists(VECTOR_DB_PATH):
        shutil.rmtree(VECTOR_DB_PATH)
        deleted_files.append("向量数据库")
    
    # 删除PDF文档
    data_dir = "data"
    if os.path.exists(data_dir):
        for filename in os.listdir(data_dir):
            if filename.endswith('.pdf'):
                file_path = os.path.join(data_dir, filename)
                os.remove(file_path)
                deleted_files.append(filename)
    
    if deleted_files:
        return {
            "status": "知识库已清空", 
            "message": f"已删除：{', '.join(deleted_files)}"
        }
    else:
        return {"status": "知识库为空", "message": "没有可删除的内容"}

@app.post("/clear_history")
async def clear_history():
    """清理对话历史（前端存储的对话历史）"""
    # 注意：这个接口主要用于前端调用，表示前端应该清理自己的对话历史存储
    # 后端记忆（SQLiteMemory）通过/reset_memory接口清理
    return {"status": "对话历史已清空", "message": "前端对话历史存储已清理"}
