#!/bin/bash

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;34m'
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

# 切换到项目根目录
cd "$PROJECT_ROOT" || error_exit "无法切换到项目根目录"

# 加载环境变量
if [ -f ".env" ]; then
    log_info "加载 .env 环境变量..."
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
    log_success "环境变量加载完成"
else
    log_warning ".env 文件未找到，将使用当前环境变量"
fi

# 检查端口是否被占用
check_port() {
    if lsof -i :$1 &> /dev/null; then
        # 检查是否有活跃的监听进程
        if lsof -i :$1 | grep -q "LISTEN"; then
            log_warning "端口 $1 已被占用，尝试停止相关进程..."
            pkill -f "uvicorn.*$1" 2>/dev/null || true
            pkill -f "streamlit.*$1" 2>/dev/null || true
            sleep 2
            
            # 再次检查
            if lsof -i :$1 | grep -q "LISTEN"; then
                log_error "端口 $1 仍被占用，请手动停止相关进程"
                return 1
            fi
        else
            # 只有CLOSED状态的连接，可能是残留连接，允许继续
            log_warning "端口 $1 有残留连接，但无活跃监听进程，继续启动..."
            return 0
        fi
    fi
    return 0
}

# 检查虚拟环境
if [ ! -d "venv" ]; then
    log_error "虚拟环境不存在，请先运行 setup.sh 进行初始化"
    exit 1
fi

# 激活虚拟环境
source venv/bin/activate || error_exit "虚拟环境激活失败"

# 验证虚拟环境激活
if [[ -z "$VIRTUAL_ENV" ]]; then
    error_exit "虚拟环境激活失败，请检查虚拟环境路径"
fi
log_success "虚拟环境激活成功"

# 检查端口
log_info "检查端口占用情况..."
check_port 8000 || error_exit "FastAPI 端口 8000 被占用"
check_port 8501 || error_exit "Streamlit 端口 8501 被占用"

# 创建日志目录
mkdir -p logs

log_info "🚀 启动 DocChat AI 服务..."

# 启动 FastAPI 后端服务（后台运行）
log_info "启动 FastAPI 后端服务 (端口 8000)..."
uvicorn app.main:app --reload --port 8000 --host 0.0.0.0 > logs/fastapi.log 2>&1 &
FASTAPI_PID=$!

# 等待后端服务启动
sleep 5

# 检查后端服务是否正常启动
if ! ps -p $FASTAPI_PID > /dev/null 2>&1; then
    log_error "FastAPI 服务启动失败，请检查 logs/fastapi.log"
    exit 1
fi

# 检查后端服务健康状态
log_info "检查 FastAPI 服务健康状态..."
MAX_RETRIES=3
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:8000/docs > /dev/null; then
        log_success "FastAPI 服务启动成功"
        break
    fi
    
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
        log_error "FastAPI 服务无法访问，请检查日志"
        kill $FASTAPI_PID 2>/dev/null || true
        exit 1
    fi
    
    log_warning "FastAPI 服务启动较慢，等待额外时间... (尝试 $RETRY_COUNT/$MAX_RETRIES)"
    sleep 5

done

# 启动 Streamlit 前端服务
log_info "启动 Streamlit 前端服务 (端口 8501)..."
streamlit run frontend/streamlit_app.py --server.port 8501 --server.address localhost > logs/streamlit.log 2>&1 &
STREAMLIT_PID=$!

# 等待前端服务启动
sleep 8

# 检查前端服务是否正常启动
if ! ps -p $STREAMLIT_PID > /dev/null 2>&1; then
    log_error "Streamlit 服务启动失败，请检查 logs/streamlit.log"
    kill $FASTAPI_PID 2>/dev/null || true
    exit 1
fi

# 检查前端服务健康状态
log_info "检查 Streamlit 服务健康状态..."
MAX_RETRIES=3
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:8501 > /dev/null; then
        log_success "Streamlit 服务启动成功"
        break
    fi
    
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
        log_error "Streamlit 服务无法访问，请检查日志"
        kill $FASTAPI_PID 2>/dev/null || true
        kill $STREAMLIT_PID 2>/dev/null || true
        exit 1
    fi
    
    log_warning "Streamlit 服务启动较慢，等待额外时间... (尝试 $RETRY_COUNT/$MAX_RETRIES)"
    sleep 5
done

# 保存进程ID到文件
echo "$FASTAPI_PID" > logs/fastapi.pid
echo "$STREAMLIT_PID" > logs/streamlit.pid

log_success "✅ 服务启动成功！"
echo ""
echo "🌐 服务地址："
echo "   - FastAPI 后端：http://localhost:8000"
echo "   - Streamlit 前端：http://localhost:8501"
echo ""
echo "📊 服务状态："
echo "   - FastAPI 进程ID: $FASTAPI_PID"
echo "   - Streamlit 进程ID: $STREAMLIT_PID"
echo ""
echo "📝 日志文件："
echo "   - FastAPI 日志: logs/fastapi.log"
echo "   - Streamlit 日志: logs/streamlit.log"
echo ""
echo "🛑 停止服务：bash scripts/stop.sh"
echo "🔄 重启服务：bash scripts/restart.sh"
echo ""

# 显示服务启动日志的最后几行
log_info "FastAPI 启动日志："
tail -5 logs/fastapi.log
log_info "Streamlit 启动日志："
tail -5 logs/streamlit.log
