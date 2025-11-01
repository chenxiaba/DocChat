#!/bin/bash

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

# 错误处理函数
error_exit() {
    log_error "$1"
    exit 1
}

echo "======================================"
echo "🚀 DocChat AI 环境初始化开始"
echo "======================================"

# 切换到项目根目录（脚本所在目录的父目录）
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT" || error_exit "无法切换到项目根目录"

# Step 1. 检查 Python 环境
log_info "检查 Python 环境..."
if ! command -v python3 &> /dev/null; then
    error_exit "未检测到 Python3，请先安装 Python 3.9+"
fi

# 检查 Python 版本
PYTHON_VERSION=$(python3 -c "import sys; print('.'.join(map(str, sys.version_info[:3])))")
PYTHON_MAJOR=$(python3 -c "import sys; print(sys.version_info[0])")
PYTHON_MINOR=$(python3 -c "import sys; print(sys.version_info[1])")

# 检查Python版本是否兼容（3.9+）
if [[ $PYTHON_MAJOR -eq 3 && $PYTHON_MINOR -lt 9 ]]; then
    error_exit "Python 版本过低 ($PYTHON_VERSION)，需要 Python 3.9+"
fi
log_success "Python $PYTHON_VERSION 检测通过"

# Step 2. 创建虚拟环境
if [ ! -d "venv" ]; then
    log_info "创建虚拟环境 (包含系统依赖)..."
    python3 -m venv --system-site-packages venv || error_exit "虚拟环境创建失败"
    log_success "虚拟环境创建完成"
else
    log_success "虚拟环境已存在"
fi

# Step 3. 激活环境
log_info "激活虚拟环境..."
source venv/bin/activate || error_exit "虚拟环境激活失败"

# 验证虚拟环境激活
if [[ -z "$VIRTUAL_ENV" ]]; then
    error_exit "虚拟环境激活失败，请检查虚拟环境路径"
fi
log_success "虚拟环境激活成功"

# Step 4. 升级 pip
log_info "升级 pip 和包管理工具..."
if pip install --upgrade pip setuptools wheel; then
    log_success "pip 及工具升级完成"
else
    log_warning "pip 升级失败，可能处于离线环境，将继续使用现有版本"
fi

# Step 5. 安装依赖
if [ -f "requirements.txt" ]; then
    log_info "安装依赖包..."
    if pip install -r requirements.txt; then
        log_success "依赖安装完成"
    else
        log_warning "依赖安装失败，尝试验证系统环境中是否已存在所需模块..."
        python3 - <<'EOF'
import importlib
import sys

modules = {
    "langchain": "langchain",
    "langgraph": "langgraph",
    "openai": "openai",
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "streamlit": "streamlit",
    "python-dotenv": "dotenv",
    "chromadb": "chromadb",
    "PyPDF2": "PyPDF2",
    "tiktoken": "tiktoken",
    "requests": "requests",
    "langchain-chroma": "langchain_chroma",
    "langchain-openai": "langchain_openai",
    "langchain-text-splitters": "langchain_text_splitters",
}

missing = []
for package, module_name in modules.items():
    try:
        importlib.import_module(module_name)
    except ModuleNotFoundError:
        missing.append(package)

if missing:
    print("❌ 以下依赖未能安装且在系统环境中缺失:\n - " + "\n - ".join(missing))
    sys.exit(1)
else:
    print("✅ 所需依赖已在系统环境中可用，跳过安装")
EOF
        if [ $? -ne 0 ]; then
            error_exit "依赖安装失败且系统中缺失必要模块"
        fi
        log_success "系统环境已包含所需依赖"
    fi
else
    error_exit "未找到 requirements.txt，请确认项目完整"
fi

# Step 6. 验证关键模块
log_info "验证关键模块..."
python3 - <<'EOF' || error_exit "模块验证失败"
try:
    import langchain, fastapi, streamlit, langchain_openai, chromadb, langchain_text_splitters
    print("✅ 模块检测通过 (LangChain / FastAPI / Streamlit)")
except ImportError as e:
    print(f"❌ 模块导入失败: {e}")
    exit(1)
except Exception as e:
    print(f"❌ 模块检测异常: {e}")
    exit(1)
EOF

# Step 7. 初始化数据库与数据目录
log_info "初始化数据库..."
mkdir -p data/vector_store || error_exit "数据目录创建失败"
python3 - <<'EOF'
import sqlite3, os

try:
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect("data/memory.sqlite")
    conn.execute("""
    CREATE TABLE IF NOT EXISTS memory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        role TEXT,
        content TEXT
    )
    """)
    conn.commit()
    conn.close()
    print("✅ SQLite 数据库初始化完成：data/memory.sqlite")
except Exception as e:
    print(f"❌ 数据库初始化失败: {e}")
    exit(1)
EOF

# Step 8. 创建环境配置文件（如果不存在）
log_info "检查环境配置文件..."
if [ ! -f ".env.example" ]; then
    cat > .env.example << 'EOL'
# DeepSeek API Configuration
DEEPSEEK_API_KEY=your_deepseek_api_key_here
OPENAI_API_BASE=https://api.deepseek.com/v1
VECTOR_BACKEND=chroma
DEEPSEEK_MODEL=deepseek-chat

# Optional: Alternative endpoint configuration
# DEEPSEEK_ENDPOINT=https://api.deepseek.com/v1/completions
EOL
    log_success "环境配置文件模板已创建"
else
    log_success "环境配置文件模板已存在"
fi

# Step 9. 完成提示
echo "======================================"
log_success "环境初始化完成！"
echo ""
echo "📋 下一步操作："
echo "   1. 配置 API 密钥：编辑 .env 文件"
echo "   2. 激活环境：source venv/bin/activate"
echo "   3. 启动服务：bash scripts/start.sh"
echo ""
echo "🌐 服务地址："
echo "   - FastAPI 后端：http://localhost:8000"
echo "   - Streamlit 前端：http://localhost:8501"
echo ""
echo "📚 API 文档：查看 API_MANUAL.md 获取移动端对接指南"
echo "======================================"