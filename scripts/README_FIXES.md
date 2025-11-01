# DocChat AI 启动问题修复说明

## 修复的问题

基于之前启动时遇到的问题，我们对启动脚本进行了以下修复：

### 1. Python版本检查问题修复
- **问题**: 原脚本使用字符串比较 `[[ "$PYTHON_VERSION" < "3.9" ]]`，在Python 3.13时会出现错误判断
- **修复**: 改为使用数字比较 `[[ $PYTHON_MAJOR -eq 3 && $PYTHON_MINOR -lt 9 ]]`
- **文件**: `setup.sh`

### 2. 虚拟环境激活验证增强
- **问题**: 原脚本只检查虚拟环境目录存在，但未验证是否真正激活
- **修复**: 添加虚拟环境激活状态检查 `[[ -z "$VIRTUAL_ENV" ]]`
- **文件**: `setup.sh`, `start.sh`

### 3. 服务健康检查增强
- **问题**: 原脚本只检查进程是否存在，但未验证服务是否真正可用
- **修复**: 添加HTTP健康检查，确保服务可以正常访问
  - FastAPI: 检查 `/docs` 接口
  - Streamlit: 检查根路径
- **文件**: `start.sh`

### 4. API URL配置问题修复
- **问题**: 前端应用中使用 `127.0.0.1` 而服务绑定 `0.0.0.0`，可能导致连接问题
- **修复**: 将所有API URL改为使用 `localhost`
- **文件**: `frontend/streamlit_app.py`

## 新增脚本

### fix_issues.sh
专门用于检查和修复已知问题的脚本：
- 检查Python版本兼容性
- 验证虚拟环境激活状态
- 修复API URL配置
- 检查端口占用情况
- 验证依赖包完整性
- 检查文件权限

**使用方法**:
```bash
bash scripts/fix_issues.sh
```

## 启动流程优化

### 新的启动流程：
1. **环境检查** → 检查Python版本、虚拟环境
2. **端口检查** → 检查端口占用，自动清理
3. **服务启动** → 启动FastAPI和Streamlit服务
4. **健康检查** → 验证服务真正可用
5. **状态报告** → 显示服务状态和访问地址

### 改进的服务检查：
- **进程检查**: 确保进程正在运行
- **端口检查**: 确保端口被正确监听
- **HTTP检查**: 确保服务可以正常响应请求

## 脚本使用说明

### 启动服务
```bash
bash scripts/start.sh
```

### 停止服务
```bash
bash scripts/stop.sh
```

### 重启服务
```bash
bash scripts/restart.sh
```

### 修复问题
```bash
bash scripts/fix_issues.sh
```

## 服务访问地址

- **FastAPI后端**: http://localhost:8000
- **API文档**: http://localhost:8000/docs
- **Streamlit前端**: http://localhost:8501

## 故障排除

如果仍然遇到问题，请检查：

1. **查看日志**:
   ```bash
   tail -f logs/fastapi.log
   tail -f logs/streamlit.log
   ```

2. **检查端口占用**:
   ```bash
   lsof -i :8000
   lsof -i :8501
   ```

3. **手动启动测试**:
   ```bash
   # 激活虚拟环境
   source scripts/venv/bin/activate
   
   # 启动FastAPI
   uvicorn app.main:app --reload --port 8000 --host 0.0.0.0
   
   # 新终端启动Streamlit
   streamlit run frontend/streamlit_app.py --server.port 8501 --server.address 0.0.0.0
   ```

## 已知问题解决

所有之前报告的启动问题都已在最新脚本中得到修复。如果遇到新问题，请运行 `fix_issues.sh` 进行自动诊断和修复。