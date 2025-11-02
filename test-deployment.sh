#!/bin/bash

# ============================================
# DocChat AI - 本地部署测试脚本
# 用于在没有Docker的环境中测试部署流程
# ============================================

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 模拟Docker检查（跳过实际检查）
check_docker_simulation() {
    log_warning "本地测试模式：跳过Docker检查"
    log_info "模拟Docker环境检查通过"
}

# 检查环境配置文件
check_env_files() {
    log_info "检查环境配置文件..."
    
    # 检查生产环境配置
    if [ -f ".env.production" ]; then
        log_success "找到生产环境配置文件 .env.production"
        echo "=== 生产环境配置预览 ==="
        grep -E "^(DOCCHAT_ENV|DATABASE_URL|GOOGLE_OAUTH|WECHAT_OAUTH|UVICORN_PORT|STREAMLIT_PORT)" .env.production | head -10
        echo "========================"
    else
        log_warning "生产环境配置文件 .env.production 不存在"
        log_info "正在从模板创建 .env.production 文件..."
        if [ -f ".env.example" ]; then
            cp .env.example .env.production
            log_success "已创建 .env.production 文件"
        else
            log_error "找不到 .env.example 模板文件"
            return 1
        fi
    fi
    
    # 检查本地环境配置
    if [ -f ".env.local" ]; then
        log_success "找到本地测试配置文件 .env.local"
        echo "=== 本地环境配置预览 ==="
        grep -E "^(DOCCHAT_ENV|DATABASE_URL|GOOGLE_OAUTH|WECHAT_OAUTH|UVICORN_PORT|STREAMLIT_PORT)" .env.local | head -10
        echo "======================"
    fi
    
    log_success "环境配置文件检查完成"
}

# 检查Dockerfile配置
check_dockerfile() {
    log_info "检查Docker配置..."
    
    if [ -f "Dockerfile" ]; then
        log_success "找到Dockerfile"
        echo "=== Dockerfile 基本信息 ==="
        echo "阶段数量: $(grep -c '^FROM' Dockerfile)"
        echo "暴露端口: $(grep 'EXPOSE' Dockerfile || echo '未明确暴露端口')"
        echo "启动命令: $(grep 'CMD' Dockerfile || echo '未找到CMD指令')"
        echo "=========================="
    else
        log_error "Dockerfile不存在"
        return 1
    fi
    
    if [ -f "docker-compose.yml" ]; then
        log_success "找到docker-compose.yml"
        echo "=== Docker Compose 服务配置 ==="
        echo "服务数量: $(grep -c '^  [a-zA-Z]' docker-compose.yml)"
        echo "端口映射: $(grep 'ports:' -A 5 docker-compose.yml | grep -o '[0-9]\{4,5\}:[0-9]\{4,5\}' || echo '无端口映射')"
        echo "=============================="
    else
        log_error "docker-compose.yml不存在"
        return 1
    fi
    
    log_success "Docker配置检查完成"
}

# 检查项目依赖
check_dependencies() {
    log_info "检查项目依赖..."
    
    if [ -f "requirements.txt" ]; then
        log_success "找到requirements.txt"
        echo "=== 主要依赖包 ==="
        grep -E "^(fastapi|streamlit|uvicorn|sqlalchemy|requests|httpx)" requirements.txt | head -10
        echo "================"
        echo "依赖包总数: $(wc -l < requirements.txt)"
    else
        log_error "requirements.txt不存在"
        return 1
    fi
    
    if [ -f "pyproject.toml" ]; then
        log_success "找到pyproject.toml"
        echo "=== 项目配置 ==="
        grep -E "^(name|version|description)" pyproject.toml | head -5
        echo "================"
    fi
    
    log_success "依赖检查完成"
}

# 检查应用代码结构
check_code_structure() {
    log_info "检查应用代码结构..."
    
    # 检查后端代码
    if [ -d "app" ]; then
        log_success "找到后端代码目录 app/"
        echo "后端文件数量: $(find app -name '*.py' | wc -l)"
        echo "主要模块: $(ls app/*.py | xargs -n 1 basename | tr '\n' ' ')"
    else
        log_error "后端代码目录 app/ 不存在"
        return 1
    fi
    
    # 检查前端代码
    if [ -d "frontend" ]; then
        log_success "找到前端代码目录 frontend/"
        echo "前端文件数量: $(find frontend -name '*.py' | wc -l)"
        echo "主要文件: $(ls frontend/*.py | xargs -n 1 basename | tr '\n' ' ')"
    else
        log_error "前端代码目录 frontend/ 不存在"
        return 1
    fi
    
    log_success "代码结构检查完成"
}

# 模拟部署流程
simulate_deployment() {
    log_info "模拟部署流程..."
    
    echo "=== 部署步骤模拟 ==="
    echo "1. ✅ 环境检查"
    echo "2. ✅ 配置文件验证"
    echo "3. ✅ 依赖检查"
    echo "4. 🔄 构建Docker镜像（模拟）"
    echo "5. 🔄 启动服务（模拟）"
    echo "6. 🔄 健康检查（模拟）"
    echo "7. ✅ 部署完成"
    echo "===================="
    
    log_success "部署流程模拟完成"
}

# 生成部署报告
generate_report() {
    log_info "生成部署测试报告..."
    
    cat > deployment-test-report.md << 'EOF'
# DocChat AI 部署测试报告

## 测试时间
$(date)

## 测试环境
- 操作系统: $(uname -s)
- 架构: $(uname -m)
- Python版本: $(python3 --version 2>/dev/null || echo "Python未安装")
- Docker状态: 未安装（本地测试模式）

## 测试结果

### ✅ 通过的项目
- 项目结构完整性
- 配置文件存在性
- 依赖文件完整性
- 代码结构完整性

### ⚠️ 需要注意的项目
- Docker环境未安装（生产部署需要）
- 生产环境配置需要完善
- OAuth回调URL需要配置

### 🔧 建议
1. 在生产服务器上安装Docker和Docker Compose
2. 完善 .env.production 中的敏感配置
3. 配置域名和SSL证书
4. 测试数据库连接（如使用外部数据库）

## 部署命令
生产环境部署命令：
```bash
./deploy-production.sh
```

本地开发启动命令：
```bash
# 后端服务
cd /Users/lee/workshop/mvp/DocChat_AI && source venv/bin/activate && uvicorn app.main:app --reload --port 8000 --host 0.0.0.0

# 前端服务
cd /Users/lee/workshop/mvp/DocChat_AI && source venv/bin/activate && streamlit run frontend/streamlit_app.py --server.port 8501 --server.address localhost
```
EOF

    log_success "部署测试报告已生成: deployment-test-report.md"
}

# 主函数
main() {
    echo "=========================================="
    echo "  DocChat AI - 本地部署测试"
    echo "=========================================="
    
    log_info "开始本地部署测试..."
    
    # 执行测试步骤
    check_docker_simulation
    check_env_files
    check_dockerfile
    check_dependencies
    check_code_structure
    simulate_deployment
    generate_report
    
    echo ""
    echo "=========================================="
    echo "  本地部署测试完成！"
    echo "=========================================="
    echo ""
    echo "📋 测试报告: deployment-test-report.md"
    echo "🚀 生产部署: ./deploy-production.sh"
    echo "💻 本地开发: 使用现有的启动脚本"
    echo ""
    echo "下一步建议："
    echo "1. 在生产服务器上安装Docker环境"
    echo "2. 完善生产环境配置文件"
    echo "3. 配置域名和SSL证书"
    echo "4. 运行生产部署脚本"
    echo ""
}

# 运行主函数
main "$@"