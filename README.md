# DocChat AI

[![Version](https://img.shields.io/badge/version-0.0.1-blue.svg)](VERSION)
[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.37+-red.svg)](https://streamlit.io/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

一个基于 AI 的智能文档问答系统，具备强大的文档分析、知识检索和智能对话能力。

**版本**: v0.0.1 - 初始发布版本

## ✨ 特性

- 📚 **智能文档问答** - 支持多PDF文档上传和语义检索
- 💬 **流式对话体验** - 实时响应，支持多轮对话
- 🧠 **记忆管理** - 自动保存对话历史，支持记忆重置
- 🔍 **向量化搜索** - 基于ChromaDB的语义相似度搜索
- 📱 **移动端支持** - 完整的RESTful API，支持移动端对接
- 🎨 **现代化UI** - 基于Streamlit的响应式Web界面
- 🔧 **自动化部署** - 完善的脚本工具，一键部署

## 🚀 快速开始

### 环境要求

- Python 3.9+
- OpenAI API密钥（或其他兼容的LLM API）

### 安装步骤

1. **克隆项目**
   ```bash
   git clone https://github.com/your-username/docchat-ai.git
   cd docchat-ai
   ```

2. **环境初始化**
   ```bash
   bash scripts/setup.sh
   ```

3. **配置环境变量**
   ```bash
   # 复制环境配置文件
   cp .env.example .env
   # 编辑.env文件，添加你使用的llm服务
   # 修改.streamlit/secrets.toml里的api_key
   ```
   `.env` 关键变量说明：

   - `DEEPSEEK_API_KEY`：DeepSeek/兼容OpenAI接口的访问密钥。
   - `OPENAI_API_BASE`：LLM 接口地址，默认指向 DeepSeek。
   - `DB_PATH`：对话记忆 SQLite 数据库路径。
   - `VECTOR_DB_PATH`：向量数据库持久化目录。
   - `CHAT_HISTORY_PATH`：聊天历史缓存文件路径。

4. **启动服务**
   ```bash
   bash scripts/start.sh
   ```
   启动脚本会自动读取 `.env` 中的配置。

5. **访问应用**
   - 前端界面: http://localhost:8501
   - API文档: http://localhost:8000/docs

## 📖 详细文档

- [项目介绍](PROJECT_INTRODUCTION.md) - 项目架构和设计理念
- [API手册](API_MANUAL.md) - 完整的API接口文档
- [使用指南](scripts/USAGE_GUIDE.md) - 详细脚本使用说明

## 📊 技术栈

### 后端技术
- **FastAPI** - 现代化Python Web框架
- **LangChain** - AI应用开发框架
- **ChromaDB** - 向量数据库
- **SQLite** - 轻量级数据库

### 前端技术
- **Streamlit** - 数据应用开发框架
- **React** - 现代化UI组件

### AI技术
- **DeepSeek AI** - 大语言模型
- **语义检索** - 向量相似度搜索
- **流式响应** - Server-Sent Events

## 🎯 应用场景

### 企业知识管理
- 内部文档智能问答
- 培训材料分析
- 技术文档检索

### 教育科研
- 学术论文分析
- 教材内容问答
- 研究资料管理

### 个人使用
- 个人文档管理
- 学习助手
- 信息检索工具

## 🤝 贡献

欢迎提交Issue和Pull Request来改进项目！

### 开发环境设置

项目提供完善的脚本工具，推荐使用脚本进行开发环境管理：

```bash
# 1. 环境初始化（首次使用）
bash scripts/setup.sh

# 2. 启动开发服务
bash scripts/start.sh

# 3. 开发过程中常用命令
# 检查服务状态
bash scripts/status.sh

# 重启服务（代码修改后）
bash scripts/restart.sh

# 停止服务
bash scripts/stop.sh
```

#### 手动开发模式（高级用户）
如果需要手动控制开发服务器，可以使用以下命令：

```bash
# 激活虚拟环境
source scripts/venv/bin/activate

# 启动后端服务（带热重载）
python -m uvicorn app.main:app --reload --port 8000

# 启动前端服务（新终端）
streamlit run frontend/streamlit_app.py --server.port 8501
```

## 📄 许可证

本项目基于 MIT 许可证开源 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📞 支持

- 提交Issue: [GitHub Issues](<repository-url>/issues)
- 查看文档: [项目文档](PROJECT_INTRODUCTION.md)
- API参考: [API手册](API_MANUAL.md)

---

**DocChat AI** - 让文档问答更智能，让知识检索更高效！ 🚀
