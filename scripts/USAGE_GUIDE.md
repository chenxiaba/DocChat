# DocChat AI 脚本使用指南

## 概述

本项目提供了一套完整的脚本工具，用于管理 DocChat AI 的安装、启动、停止和监控。

### 脚本文件列表

| 脚本文件 | 功能描述 | 使用场景 |
|---------|---------|---------|
| `setup.sh` | 环境初始化脚本 | 首次安装或重新初始化环境 |
| `start.sh` | 服务启动脚本 | 启动 FastAPI 后端和 Streamlit 前端 |
| `stop.sh` | 服务停止脚本 | 停止所有运行的服务 |
| `restart.sh` | 服务重启脚本 | 重启服务（先停止再启动） |
| `status.sh` | 服务状态检查脚本 | 检查服务运行状态和健康状况 |

## 🚀 快速开始

### 1. 环境初始化（首次使用）

```bash
# 进入脚本目录
cd scripts

# 运行环境初始化脚本
bash setup.sh
```

**执行结果：**
- 检查 Python 3.9+ 环境
- 创建虚拟环境
- 安装所有依赖包
- 初始化数据库
- 创建环境配置文件模板

### 2. 配置环境变量

```bash
# 复制环境配置文件模板
cp .env.example .env

# 编辑配置文件，填入你的 API 密钥
nano .env
```

**需要配置的项：**
- `DEEPSEEK_API_KEY`: 你的 DeepSeek API 密钥
# 修改.streamlit/secrets.toml里的api_key
- 其他配置项可根据需要调整

### 3. 启动服务

```bash
# 启动所有服务
bash scripts/start.sh
```

**启动的服务：**
- FastAPI 后端：http://localhost:8000
- Streamlit 前端：http://localhost:8501

### 4. 检查服务状态

```bash
# 检查服务运行状态
bash scripts/status.sh
```

## 📖 详细使用说明

### setup.sh - 环境初始化

**功能：**
- ✅ 检查 Python 3.9+ 环境
- ✅ 创建虚拟环境
- ✅ 安装依赖包
- ✅ 初始化数据库
- ✅ 验证关键模块
- ✅ 创建配置文件模板

**使用示例：**
```bash
# 完整初始化
bash scripts/setup.sh

# 如果遇到问题，可以查看详细日志
bash scripts/setup.sh 2>&1 | tee setup.log
```

### start.sh - 服务启动

**功能：**
- ✅ 检查端口占用情况
- ✅ 自动清理占用端口的进程
- ✅ 启动 FastAPI 后端服务
- ✅ 启动 Streamlit 前端服务
- ✅ 保存进程 ID 到文件
- ✅ 生成服务日志

**使用示例：**
```bash
# 正常启动
bash scripts/start.sh

# 查看实时日志
tail -f logs/fastapi.log
tail -f logs/streamlit.log
```

### stop.sh - 服务停止

**功能：**
- ✅ 优雅停止服务进程
- ✅ 检查并清理端口占用
- ✅ 强制停止顽固进程
- ✅ 验证服务完全停止

**使用示例：**
```bash
# 正常停止
bash scripts/stop.sh

# 如果服务无法停止，脚本会自动强制停止
```

### restart.sh - 服务重启

**功能：**
- ✅ 检查当前服务状态
- ✅ 智能重启（仅重启运行中的服务）
- ✅ 确保端口完全释放
- ✅ 验证重启结果

**使用示例：**
```bash
# 重启服务
bash scripts/restart.sh

# 重启后检查状态
bash scripts/status.sh
```

### status.sh - 状态检查

**功能：**
- ✅ 检查虚拟环境状态
- ✅ 检查服务进程状态
- ✅ 检查端口监听状态
- ✅ 检查健康状态
- ✅ 检查日志文件
- ✅ 检查数据文件

**使用示例：**
```bash
# 完整状态检查
bash scripts/status.sh

# 快速检查服务是否运行
pgrep -f "uvicorn app.main:app" && echo "FastAPI 运行中" || echo "FastAPI 未运行"
pgrep -f "streamlit run" && echo "Streamlit 运行中" || echo "Streamlit 未运行"
```

## 🔧 故障排除

### 常见问题

#### 1. 端口被占用

**症状：** 启动服务时报端口被占用错误

**解决方案：**
```bash
# 方法1：使用脚本自动清理
bash scripts/start.sh

# 方法2：手动检查并停止占用进程
lsof -i :8000
lsof -i :8501

# 停止相关进程
pkill -f "uvicorn"
pkill -f "streamlit"
```

#### 2. 虚拟环境问题

**症状：** 模块导入错误或命令找不到

**解决方案：**
```bash
# 重新激活虚拟环境
source scripts/venv/bin/activate

# 或者重新运行安装脚本
bash scripts/setup.sh
```

#### 3. API 密钥配置错误

**症状：** 服务启动但无法正常响应

**解决方案：**
```bash
# 检查配置文件
cat .env

# 确保 OPENAI_API_KEY 已正确设置
# 重新启动服务
bash scripts/restart.sh
```

### 日志文件位置

- **FastAPI 日志：** `logs/fastapi.log`
- **Streamlit 日志：** `logs/streamlit.log`
- **安装日志：** 运行 `bash scripts/setup.sh 2>&1 | tee setup.log` 生成

### 调试技巧

```bash
# 1. 检查服务是否真正运行
bash scripts/status.sh

# 2. 查看实时日志
tail -f logs/fastapi.log
tail -f logs/streamlit.log

# 3. 检查端口监听
netstat -tulpn | grep :8000
netstat -tulpn | grep :8501

# 4. 检查进程树
pstree -p | grep -E "(uvicorn|streamlit)"
```

## 🎯 最佳实践

### 开发环境

1. **使用虚拟环境：** 始终在虚拟环境中运行
2. **定期更新依赖：** 定期运行 `pip install -r requirements.txt`
3. **监控日志：** 开发时保持一个终端窗口查看日志
4. **使用重启脚本：** 代码修改后使用 `restart.sh` 而不是手动停止启动

### 生产环境

1. **配置环境变量：** 确保 `.env` 文件中的生产配置正确
2. **使用进程管理：** 考虑使用 systemd 或 supervisor 管理服务
3. **日志轮转：** 配置日志轮转避免日志文件过大
4. **监控健康状态：** 定期运行 `status.sh` 检查服务健康

### 移动端对接

1. **API 文档：** 查看 `API_MANUAL.md` 获取完整的移动端对接指南
2. **测试接口：** 使用 `http://localhost:8000/docs` 测试 API 接口
3. **流式响应：** 移动端优先使用 `/chat_stream` 接口获得更好体验

## 📞 技术支持

如果遇到无法解决的问题：

1. **查看日志：** 检查相关日志文件获取详细错误信息
2. **检查文档：** 查看本指南和 API 手册
3. **环境检查：** 运行 `bash scripts/status.sh` 进行完整诊断
4. **重新安装：** 如果问题持续，尝试重新运行 `bash scripts/setup.sh`

---

**最后更新：** 2024年  
**版本：** v2.0  
**适用系统：** macOS, Linux