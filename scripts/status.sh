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

# 检查服务状态
check_service() {
    local pattern=$1
    local service_name=$2
    local port=$3
    local health_url=$4
    
    echo ""
    echo "=== $service_name 状态检查 ==="
    
    # 检查进程
    local pids=$(pgrep -f "$pattern")
    if [ -n "$pids" ]; then
        log_success "进程运行中 (PID: $pids)"
    else
        log_error "进程未运行"
        return 1
    fi
    
    # 检查端口
    if lsof -i :$port > /dev/null 2>&1; then
        log_success "端口 $port 监听正常"
    else
        log_error "端口 $port 未监听"
        return 1
    fi
    
    # 检查健康状态（如果有健康检查URL）
    if [ -n "$health_url" ]; then
        if command -v curl > /dev/null; then
            local response=$(curl -s -o /dev/null -w "%{http_code}" "$health_url" 2>/dev/null || echo "000")
            if [ "$response" = "200" ]; then
                log_success "健康检查通过 (HTTP 200)"
            else
                log_warning "健康检查失败 (HTTP $response)"
            fi
        else
            log_warning "curl 不可用，跳过健康检查"
        fi
    fi
    
    return 0
}

# 检查虚拟环境
check_virtual_env() {
    echo ""
    echo "=== 虚拟环境检查 ==="
    
    if [ -d "venv" ]; then
        log_success "虚拟环境存在"
        
        # 检查Python版本
        local python_version=$(venv/bin/python -c "import sys; print('.'.join(map(str, sys.version_info[:3])))" 2>/dev/null)
        if [ $? -eq 0 ]; then
            log_success "Python 版本: $python_version"
        else
            log_error "无法获取Python版本"
        fi
        
        # 检查关键模块
        local modules=("langchain" "fastapi" "streamlit" "langchain_openai" "langchain_chroma")
        local missing_modules=()
        
        for module in "${modules[@]}"; do
            if venv/bin/python -c "import $module" 2>/dev/null; then
                log_success "$module 模块正常"
            else
                missing_modules+=("$module")
                log_error "$module 模块缺失"
            fi
        done
        
        if [ ${#missing_modules[@]} -gt 0 ]; then
            log_warning "缺失模块: ${missing_modules[*]}"
        fi
    else
        log_error "虚拟环境不存在"
    fi
}

# 检查日志文件
check_logs() {
    echo ""
    echo "=== 日志文件检查 ==="
    
    local log_files=("logs/fastapi.log" "logs/streamlit.log")
    
    for log_file in "${log_files[@]}"; do
        if [ -f "$log_file" ]; then
            local size=$(du -h "$log_file" | cut -f1)
            local lines=$(wc -l < "$log_file" 2>/dev/null || echo "0")
            log_success "$log_file ($size, $lines 行)"
            
            # 显示最后错误（如果有）
            local last_error=$(grep -i "error\|exception\|failed" "$log_file" | tail -1 2>/dev/null)
            if [ -n "$last_error" ]; then
                log_warning "最后错误: $last_error"
            fi
        else
            log_warning "$log_file 不存在"
        fi
    done
}

# 检查数据文件
check_data() {
    echo ""
    echo "=== 数据文件检查 ==="
    
    local data_files=("data/memory.sqlite" "data/vector_store")
    
    for data_file in "${data_files[@]}"; do
        if [ -e "$data_file" ]; then
            if [ -d "$data_file" ]; then
                local size=$(du -sh "$data_file" 2>/dev/null | cut -f1 || echo "未知")
                log_success "$data_file 目录存在 ($size)"
            else
                local size=$(du -h "$data_file" 2>/dev/null | cut -f1 || echo "未知")
                log_success "$data_file 文件存在 ($size)"
            fi
        else
            log_warning "$data_file 不存在"
        fi
    done
}

# 主函数
main() {
    echo "======================================"
    echo "🔍 DocChat AI 服务状态检查"
    echo "======================================"
    
    # 切换到脚本目录
    cd "$(dirname "$0")" || {
        log_error "无法切换到脚本目录"
        exit 1
    }
    
    # 检查虚拟环境
    check_virtual_env
    
    # 检查服务状态
    check_service "uvicorn app.main:app" "FastAPI 后端" 8000 "http://localhost:8000/docs"
    local fastapi_status=$?
    
    check_service "streamlit run frontend/streamlit_app.py" "Streamlit 前端" 8501 "http://localhost:8501"
    local streamlit_status=$?
    
    # 检查日志文件
    check_logs
    
    # 检查数据文件
    check_data
    
    # 总结报告
    echo ""
    echo "======================================"
    echo "📊 服务状态总结"
    echo "======================================"
    
    if [ $fastapi_status -eq 0 ] && [ $streamlit_status -eq 0 ]; then
        log_success "✅ 所有服务运行正常"
        echo ""
        echo "🌐 服务地址："
        echo "   - FastAPI 后端：http://localhost:8000"
        echo "   - Streamlit 前端：http://localhost:8501"
        echo ""
        echo "📚 API 文档：http://localhost:8000/docs"
    else
        log_error "❌ 部分服务存在问题"
        echo ""
        if [ $fastapi_status -ne 0 ]; then
            echo "   - FastAPI 后端：异常"
        else
            echo "   - FastAPI 后端：正常"
        fi
        
        if [ $streamlit_status -ne 0 ]; then
            echo "   - Streamlit 前端：异常"
        else
            echo "   - Streamlit 前端：正常"
        fi
        echo ""
        echo "🔧 建议操作："
        echo "   - 重启服务：bash scripts/restart.sh"
        echo "   - 查看日志：bash scripts/status.sh"
    fi
    
    echo ""
    echo "🛠️  管理命令："
    echo "   - 启动服务：bash scripts/start.sh"
    echo "   - 停止服务：bash scripts/stop.sh"
    echo "   - 重启服务：bash scripts/restart.sh"
    echo "   - 状态检查：bash scripts/status.sh"
    echo "======================================"
}

# 执行主函数
main