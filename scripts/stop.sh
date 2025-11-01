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

# 检查进程是否存在并停止
stop_service() {
    local service_name=$1
    local pattern=$2
    local pid_file=$3
    
    # 从PID文件读取进程ID
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            log_info "停止 $service_name (PID: $pid)..."
            kill "$pid" 2>/dev/null
            sleep 2
            
            # 检查是否成功停止
            if ps -p "$pid" > /dev/null 2>&1; then
                log_warning "$service_name 进程仍在运行，强制停止..."
                kill -9 "$pid" 2>/dev/null
            fi
            
            # 删除PID文件
            rm -f "$pid_file"
            log_success "$service_name 已停止"
        else
            log_warning "$service_name 进程不存在 (PID: $pid)"
            rm -f "$pid_file"
        fi
    else
        # 如果没有PID文件，尝试通过模式匹配停止
        if pgrep -f "$pattern" > /dev/null; then
            log_info "通过模式匹配停止 $service_name..."
            pkill -f "$pattern" 2>/dev/null
            sleep 2
            
            # 检查是否还有相关进程
            if pgrep -f "$pattern" > /dev/null; then
                log_warning "仍有 $service_name 进程运行，强制停止..."
                pkill -9 -f "$pattern" 2>/dev/null
            fi
            log_success "$service_name 已停止"
        else
            log_info "$service_name 未运行"
        fi
    fi
}

# 检查端口是否被释放
check_port_released() {
    local port=$1
    local service_name=$2
    
    if lsof -i :$port > /dev/null 2>&1; then
        log_warning "端口 $port 仍被占用，尝试清理..."
        pkill -f ".*:$port" 2>/dev/null || true
        sleep 2
        
        if lsof -i :$port > /dev/null 2>&1; then
            log_error "端口 $port 仍被占用，请手动检查"
            return 1
        fi
    fi
    return 0
}

log_info "🛑 停止 DocChat AI 服务..."

# 切换到脚本目录
cd "$(dirname "$0")" || exit 1

# 停止 FastAPI 服务
stop_service "FastAPI 后端" "uvicorn app.main:app" "logs/fastapi.pid"

# 停止 Streamlit 服务
stop_service "Streamlit 前端" "streamlit run frontend/streamlit_app.py" "logs/streamlit.pid"

# 检查端口是否释放
log_info "检查端口释放情况..."
check_port_released 8000 "FastAPI"
check_port_released 8501 "Streamlit"

# 清理可能残留的进程
log_info "清理残留进程..."
pkill -f "uvicorn" 2>/dev/null || true
pkill -f "streamlit" 2>/dev/null || true

# 等待进程完全停止
sleep 2

log_success "✅ 所有服务已停止"
echo ""
echo "📊 服务状态检查："
if pgrep -f "uvicorn app.main:app" > /dev/null; then
    log_error "FastAPI 服务仍在运行"
else
    log_success "FastAPI 服务已停止"
fi

if pgrep -f "streamlit run frontend/streamlit_app.py" > /dev/null; then
    log_error "Streamlit 服务仍在运行"
else
    log_success "Streamlit 服务已停止"
fi

echo ""
echo "🚀 重新启动服务：bash scripts/start.sh"
echo "🔄 重启服务：bash scripts/restart.sh"
