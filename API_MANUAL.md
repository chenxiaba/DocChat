# DocChat AI API - 移动端对接手册

## 概述

DocChat AI API 是一个基于FastAPI构建的智能文档问答系统，支持PDF文档上传、知识库构建、智能问答和流式对话功能。本手册专门为移动端开发者提供API对接指南。

## 基础信息

- **API地址**: `http://127.0.0.1:8000` (开发环境)
- **生产环境**: 请根据实际部署地址调整
- **协议**: HTTP/HTTPS
- **数据格式**: JSON
- **字符编码**: UTF-8

## 认证方式

当前版本API无需认证，生产环境建议添加API密钥认证。

## API端点列表

### 1. 普通聊天接口

**端点**: `POST /chat`

**描述**: 发送用户问题并获取一次性完整响应

**请求参数**:
```json
{
    "query": "用户的问题内容"
}
```

**响应示例**:
```json
{
    "response": "AI助手的完整回答"
}
```

**移动端调用示例**:
```javascript
// JavaScript示例
const response = await fetch('http://127.0.0.1:8000/chat', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        query: "请解释一下人工智能的基本概念"
    })
});

const data = await response.json();
console.log(data.response);
```

### 2. 流式聊天接口

**端点**: `POST /chat_stream`

**描述**: 发送用户问题并获取流式响应（推荐用于移动端）

**请求参数**:
```json
{
    "query": "用户的问题内容"
}
```

**响应格式**: Server-Sent Events (SSE)

**数据格式**:
```
data: 响应内容片段\n\n
data: [DONE]\n\n
```

**移动端调用示例**:
```javascript
// JavaScript流式处理示例
const response = await fetch('http://127.0.0.1:8000/chat_stream', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        query: "请解释一下人工智能的基本概念"
    })
});

const reader = response.body.getReader();
const decoder = new TextDecoder('utf-8');
let buffer = '';

while (true) {
    const { done, value } = await reader.read();
    
    if (done) break;
    
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    
    // 保留最后一行（可能不完整）
    buffer = lines.pop() || '';
    
    for (const line of lines) {
        if (line.startsWith('data: ')) {
            const content = line.slice(6); // 移除 "data: "
            
            if (content === '[DONE]') {
                console.log('流式响应结束');
                break;
            }
            
            // 处理响应内容
            console.log('收到内容:', content);
            // 更新UI显示
            updateChatUI(content);
        }
    }
}
```

### 3. 上传PDF文档

**端点**: `POST /upload_pdfs`

**描述**: 上传PDF文档到知识库

**请求格式**: `multipart/form-data`

**参数**:
- `files`: PDF文件列表（支持多文件上传）

**响应示例**:
```json
{
    "status": "知识库已更新",
    "count": 2
}
```

**移动端调用示例**:
```javascript
// JavaScript文件上传示例
const formData = new FormData();

// 添加PDF文件
formData.append('files', pdfFile1);
formData.append('files', pdfFile2);

const response = await fetch('http://127.0.0.1:8000/upload_pdfs', {
    method: 'POST',
    body: formData
    // 注意：不要设置Content-Type，浏览器会自动设置multipart/form-data
});

const result = await response.json();
console.log(result.status);
```

### 4. 获取文档列表

**端点**: `GET /list_documents`

**描述**: 获取知识库中的文档列表

**响应示例**:
```json
{
    "documents": [
        {
            "filename": "document1.pdf",
            "size": 1048576,
            "size_mb": 1.0
        },
        {
            "filename": "document2.pdf", 
            "size": 2097152,
            "size_mb": 2.0
        }
    ]
}
```

### 5. 删除指定文档

**端点**: `POST /delete_document/{filename}`

**描述**: 删除知识库中的指定文档

**参数**:
- `filename`: 要删除的文件名（必须包含.pdf扩展名）

**响应示例**:
```json
{
    "status": "成功",
    "message": "文档 document1.pdf 已删除"
}
```

### 6. 清理知识库

**端点**: `POST /clear_knowledge_base`

**描述**: 清理整个知识库（删除所有PDF文档和向量数据库）

**响应示例**:
```json
{
    "status": "知识库已清空",
    "message": "已删除：向量数据库, document1.pdf, document2.pdf"
}
```

### 7. 重置记忆

**端点**: `POST /reset_memory`

**描述**: 重置对话记忆（不影响知识库）

**响应示例**:
```json
{
    "status": "记忆已清空"
}
```

### 8. 清理对话历史

**端点**: `POST /clear_history`

**描述**: 清理对话历史（主要用于前端调用）

**响应示例**:
```json
{
    "status": "对话历史已清空",
    "message": "前端对话历史存储已清理"
}
```

## 错误处理

### 常见HTTP状态码

- `200`: 请求成功
- `400`: 请求参数错误
- `404`: 接口不存在
- `500`: 服务器内部错误

### 错误响应格式

```json
{
    "status": "错误",
    "message": "详细的错误信息"
}
```

## 移动端最佳实践

### 1. 网络请求优化

- **使用流式接口**: 优先使用 `/chat_stream` 接口，提升用户体验
- **设置超时**: 建议设置合理的请求超时时间（如30秒）
- **错误重试**: 实现网络错误时的重试机制
- **离线处理**: 考虑网络不可用时的降级方案

### 2. 文件上传优化

- **分片上传**: 对于大文件，考虑实现分片上传
- **进度显示**: 显示文件上传进度
- **文件大小限制**: 注意PDF文件大小限制

### 3. 用户体验优化

- **加载状态**: 显示清晰的加载状态
- **流式显示**: 实时显示AI响应内容
- **错误提示**: 友好的错误提示信息

## 示例代码

### Android (Kotlin) 示例

```kotlin
// 流式聊天请求
suspend fun chatStream(query: String): Flow<String> = flow {
    val client = OkHttpClient()
    val request = Request.Builder()
        .url("http://127.0.0.1:8000/chat_stream")
        .post(RequestBody.create(
            "application/json".toMediaType(),
            "{\"query\": \"$query\"}"
        ))
        .build()

    client.newCall(request).execute().use { response ->
        if (!response.isSuccessful) throw IOException("Unexpected code $response")
        
        val source = response.body!!.source()
        val buffer = Buffer()
        
        while (!source.exhausted()) {
            source.read(buffer, 8192)
            val content = buffer.readString(Charsets.UTF_8)
            
            // 解析SSE格式
            content.split("\\n").forEach { line ->
                if (line.startsWith("data: ")) {
                    val data = line.substring(6)
                    if (data != "[DONE]") {
                        emit(data)
                    }
                }
            }
        }
    }
}
```

### iOS (Swift) 示例

```swift
// 流式聊天请求
func chatStream(query: String) async throws -> AsyncStream<String> {
    let url = URL(string: "http://127.0.0.1:8000/chat_stream")!
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.setValue("application/json", forHTTPHeaderField: "Content-Type")
    
    let body = ["query": query]
    request.httpBody = try? JSONSerialization.data(withJSONObject: body)
    
    let (bytes, _) = try await URLSession.shared.bytes(for: request)
    
    return AsyncStream { continuation in
        Task {
            var buffer = ""
            for try await byte in bytes {
                let char = String(bytes: [byte], encoding: .utf8)!
                buffer.append(char)
                
                if char == "\n" {
                    let line = buffer.trimmingCharacters(in: .whitespacesAndNewlines)
                    buffer = ""
                    
                    if line.hasPrefix("data: ") {
                        let content = String(line.dropFirst(6))
                        if content != "[DONE]" {
                            continuation.yield(content)
                        } else {
                            continuation.finish()
                            break
                        }
                    }
                }
            }
            continuation.finish()
        }
    }
}
```

### React Native 示例

```javascript
// 使用axios进行流式请求
import axios from 'axios';

const chatStream = async (query) => {
    const response = await axios.post(
        'http://127.0.0.1:8000/chat_stream',
        { query },
        {
            responseType: 'stream',
            timeout: 30000
        }
    );

    return new Promise((resolve, reject) => {
        let buffer = '';
        let fullResponse = '';

        response.data.on('data', (chunk) => {
            buffer += chunk.toString('utf-8');
            const lines = buffer.split('\n');
            
            buffer = lines.pop() || '';
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const content = line.slice(6);
                    
                    if (content === '[DONE]') {
                        resolve(fullResponse);
                        return;
                    }
                    
                    fullResponse += content;
                    // 更新UI
                    onStreamData(content);
                }
            }
        });

        response.data.on('error', reject);
        response.data.on('end', () => {
            if (buffer) {
                resolve(fullResponse);
            }
        });
    });
};
```

## 性能优化建议

1. **连接复用**: 使用HTTP连接池
2. **请求合并**: 避免频繁的小请求
3. **缓存策略**: 合理使用本地缓存
4. **压缩传输**: 启用GZIP压缩
5. **异步处理**: 使用异步非阻塞调用

## 安全注意事项

1. **生产环境**: 使用HTTPS加密传输
2. **API密钥**: 实现API密钥认证机制
3. **输入验证**: 验证用户输入内容
4. **文件类型**: 限制上传文件类型
5. **大小限制**: 设置合理的文件大小限制

## 版本信息

- **当前版本**: v2.0
- **更新日期**: 2024年
- **兼容性**: 向后兼容v1.x版本

## 技术支持

如有技术问题，请联系开发团队或查看项目文档。

---

*本API手册最后更新于 2024年*