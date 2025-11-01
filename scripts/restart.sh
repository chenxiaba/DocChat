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

log_info "🔄 重启 DocChat AI 服务..."

# 切换到脚本目录
cd "$(dirname "$0")" || error_exit "无法切换到脚本目录"

# 检查服务是否正在运行
check_service_running() {
    local pattern=$1
    local service_name=$2
    
    if pgrep -f "$pattern" > /dev/null; then
        log_info "$service_name 正在运行"
        return 0
    else
        log_warning "$service_name 未运行"
        return 1
    fi
}

# 检查服务状态
log_info "检查当前服务状态..."
FASTAPI_RUNNING=false
STREAMLIT_RUNNING=false

if check_service_running "uvicorn app.main:app" "FastAPI 后端"; then
    FASTAPI_RUNNING=true
fi

if check_service_running "streamlit run frontend/streamlit_app.py" "Streamlit 前端"; then
    STREAMLIT_RUNNING=true
fi

# 如果服务都在运行，先停止
if [ "$FASTAPI_RUNNING" = true ] || [ "$STREAMLIT_RUNNING" = true ]; then
    log_info "停止当前运行的服务..."
    ./stop.sh
    
    # 等待服务完全停止
    sleep 3
    
    # 确认服务已停止
    if pgrep -f "uvicorn app.main:app" > /dev/null || pgrep -f "streamlit run frontend/streamlit_app.py" > /dev/null; then
        log_error "服务停止失败，请手动检查"
        exit 1
    fi
    
    log_success "服务已成功停止"
else
    log_info "服务未运行，直接启动新服务"
fi

# 等待一段时间确保端口释放
sleep 2

# 启动服务
log_info "启动新服务..."
if ./start.sh; then
    log_success "✅ 服务重启成功！"
    echo ""
    echo "🌐 服务地址："
    echo "   - FastAPI 后端：http://localhost:8000"
    echo "   - Streamlit 前端：http://localhost:8501"
    echo ""
    echo "📝 查看日志："
    echo "   - tail -f logs/fastapi.log"
    echo "   - tail -f logs/streamlit.log"
else
    log_error "服务启动失败"
    exit 1
fi
