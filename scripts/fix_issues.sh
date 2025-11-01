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
echo "🔧 DocChat AI 问题修复脚本"
echo "======================================"

# 切换到项目根目录
cd "$(dirname "$0")/.." || error_exit "无法切换到项目根目录"

log_info "检查当前环境..."

# 检查Python版本
PYTHON_VERSION=$(python3 -c "import sys; print('.'.join(map(str, sys.version_info[:3])))")
log_success "当前Python版本: $PYTHON_VERSION"

# 检查虚拟环境
if [ ! -d "scripts/venv" ]; then
    log_error "虚拟环境不存在，请先运行 setup.sh"
    exit 1
fi

# 激活虚拟环境
source scripts/venv/bin/activate || error_exit "虚拟环境激活失败"

# 验证虚拟环境激活
if [[ -z "$VIRTUAL_ENV" ]]; then
    error_exit "虚拟环境激活失败"
fi
log_success "虚拟环境激活成功"

log_info "修复API URL配置问题..."

# 检查前端应用中的API URL配置
if [ -f "frontend/streamlit_app.py" ]; then
    # 检查是否已经修复了API URL
    if grep -q "http://localhost:8000" frontend/streamlit_app.py; then
        log_success "API URL配置已正确设置为localhost"
    else
        log_warning "检测到API URL配置问题，正在修复..."
        
        # 备份原文件
        cp frontend/streamlit_app.py frontend/streamlit_app.py.backup
        
        # 替换127.0.0.1为localhost
        sed -i '' 's/http:\/\/127\.0\.0\.1:8000/http:\/\/localhost:8000/g' frontend/streamlit_app.py
        
        if grep -q "http://localhost:8000" frontend/streamlit_app.py; then
            log_success "API URL配置修复完成"
        else
            log_error "API URL配置修复失败"
            # 恢复备份
            mv frontend/streamlit_app.py.backup frontend/streamlit_app.py
        fi
    fi
else
    log_error "未找到前端应用文件"
fi

log_info "检查服务端口配置..."

# 检查端口占用情况
check_port() {
    local port=$1
    local service=$2
    
    if lsof -i :$port > /dev/null 2>&1; then
        log_warning "$service 端口 $port 被占用"
        return 1
    else
        log_success "$service 端口 $port 可用"
        return 0
    fi
}

check_port 8000 "FastAPI"
check_port 8501 "Streamlit"

log_info "检查依赖包..."

# 检查关键依赖包
python3 - <<'EOF'
try:
    import langchain, fastapi, streamlit, langchain_openai, langchain_chroma, langchain_text_splitters
    print("✅ 关键依赖包检测通过")
except ImportError as e:
    print(f"❌ 依赖包导入失败: {e}")
    exit(1)
EOF

log_info "检查数据库和文件权限..."

# 检查数据目录
mkdir -p data/vector_store 2>/dev/null || log_warning "无法创建数据目录"

# 检查数据库文件权限
if [ -f "data/memory.sqlite" ]; then
    if [ -w "data/memory.sqlite" ]; then
        log_success "数据库文件可写"
    else
        log_warning "数据库文件不可写，可能需要修复权限"
    fi
else
    log_info "数据库文件不存在，将在首次启动时创建"
fi

log_info "检查日志目录..."

# 检查日志目录
mkdir -p logs 2>/dev/null || log_warning "无法创建日志目录"

# 清理旧的日志文件（可选）
if [ -f "logs/fastapi.log" ]; then
    log_info "清理旧的FastAPI日志..."
    echo "" > logs/fastapi.log
fi

if [ -f "logs/streamlit.log" ]; then
    log_info "清理旧的Streamlit日志..."
    echo "" > logs/streamlit.log
fi

echo ""
log_success "✅ 问题检查完成！"
echo ""
echo "📋 修复建议："
echo "   1. 如果API URL配置已修复，服务应该可以正常连接"
echo "   2. 如果端口被占用，请先运行 stop.sh 停止服务"
echo "   3. 运行 start.sh 重新启动服务"
echo ""
echo "🚀 启动服务：bash scripts/start.sh"
echo "🛑 停止服务：bash scripts/stop.sh"
echo "🔄 重启服务：bash scripts/restart.sh"
echo ""
echo "🌐 服务地址："
echo "   - FastAPI 后端：http://localhost:8000"
echo "   - Streamlit 前端：http://localhost:8501"
echo ""