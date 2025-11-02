#!/bin/bash

# ============================================
# DocChat AI - 生产环境一键部署脚本
# 域名: doc-ai.chat
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

# 检查Docker是否安装
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装，请先安装Docker"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose未安装，请先安装Docker Compose"
        exit 1
    fi
    
    log_success "Docker和Docker Compose已安装"
}

# 检查环境配置文件
check_env_files() {
    if [ ! -f ".env.production" ]; then
        log_warning "生产环境配置文件 .env.production 不存在"
        log_info "正在从模板创建 .env.production 文件..."
        cp .env.example .env.production
        log_warning "请编辑 .env.production 文件，配置生产环境参数"
        log_warning "特别是OAuth客户端ID和密钥等敏感信息"
        read -p "按回车键继续部署，或Ctrl+C退出编辑配置文件..."
    fi
    
    # 检查关键配置是否已设置
    if grep -q "your_production" .env.production; then
        log_warning "检测到 .env.production 中存在未配置的占位符"
        log_warning "部署前请确保以下配置已正确设置："
        log_warning "- Google OAuth客户端ID和密钥"
        log_warning "- 微信OAuth AppID和密钥" 
        log_warning "- 数据库连接字符串"
        log_warning "- API密钥等敏感信息"
        read -p "按回车键继续部署（配置不完整可能导致功能异常）..."
    fi
    
    log_success "环境配置文件检查完成"
}

# 创建生产环境Docker Compose文件
create_production_compose() {
    cat > docker-compose.production.yml << 'EOF'
version: '3.8'

services:
  # Nginx反向代理
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/production.conf:/etc/nginx/conf.d/default.conf:ro
      - ./ssl:/etc/nginx/ssl:ro  # SSL证书目录
      - ./logs/nginx:/var/log/nginx
    depends_on:
      - docchat-app
    restart: unless-stopped
    networks:
      - docchat-network

  # DocChat应用
  docchat-app:
    build: 
      context: .
      dockerfile: Dockerfile.production
    ports:
      - "8000"  # 内部端口，不暴露到宿主机
      - "8501"  # 内部端口，不暴露到宿主机
    volumes:
      - docchat-data:/app/data  # 使用命名卷持久化数据
      - docchat-logs:/app/logs  # 使用命名卷持久化日志
    environment:
      - DOCCHAT_ENV=production
    env_file:
      - .env.production
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - docchat-network

  # 数据库（可选，如果使用PostgreSQL）
  # postgres:
  #   image: postgres:13-alpine
  #   environment:
  #     POSTGRES_DB: docchat_prod
  #     POSTGRES_USER: docchat
  #     POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-docchat_prod_password}
  #   volumes:
  #     - postgres-data:/var/lib/postgresql/data
  #   restart: unless-stopped
  #   networks:
  #     - docchat-network

volumes:
  docchat-data:
  docchat-logs:
  # postgres-data:

networks:
  docchat-network:
    driver: bridge
EOF

    log_success "生产环境Docker Compose文件已创建"
}

# 创建生产环境Nginx配置
create_nginx_config() {
    mkdir -p nginx ssl logs/nginx
    
    cat > nginx/production.conf << 'EOF'
server {
    listen 80;
    server_name doc-ai.chat www.doc-ai.chat;
    
    # 重定向HTTP到HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name doc-ai.chat www.doc-ai.chat;
    
    # SSL证书配置（需要提前配置）
    ssl_certificate /etc/nginx/ssl/doc-ai.chat.crt;
    ssl_certificate_key /etc/nginx/ssl/doc-ai.chat.key;
    
    # SSL安全配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # 安全头
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";
    
    # 前端应用代理
    location / {
        proxy_pass http://docchat-app:8501;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    # 后端API代理
    location /api/ {
        proxy_pass http://docchat-app:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # 认证回调代理
    location /auth/ {
        proxy_pass http://docchat-app:8000/auth/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # 健康检查端点
    location /health {
        proxy_pass http://docchat-app:8000/health;
        access_log off;
    }
    
    # 静态文件缓存
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # 文件上传大小限制
    client_max_body_size 50M;
}
EOF

    log_success "Nginx配置文件已创建"
    log_warning "请将SSL证书文件放置到 ./ssl/ 目录："
    log_warning "- doc-ai.chat.crt (证书文件)"
    log_warning "- doc-ai.chat.key (私钥文件)"
}

# 创建生产环境Dockerfile
create_production_dockerfile() {
    cat > Dockerfile.production << 'EOF'
# 多阶段构建：构建阶段
FROM python:3.11-slim as builder

WORKDIR /app

# 安装构建依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装依赖到虚拟环境
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir -r requirements.txt

# 生产阶段
FROM python:3.11-slim

# 安装运行时依赖
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 创建非root用户
RUN useradd --create-home --shell /bin/bash docchat

# 设置工作目录
WORKDIR /app

# 从构建阶段复制虚拟环境
COPY --from=builder /opt/venv /opt/venv

# 复制项目文件
COPY app/ ./app/
COPY frontend/ ./frontend/
COPY pyproject.toml .
COPY requirements.txt .

# 设置环境变量
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 创建数据目录并设置权限
RUN mkdir -p data logs && chown -R docchat:docchat /app

# 切换到非root用户
USER docchat

# 暴露端口
EXPOSE 8000 8501

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动应用（后端和前端）
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 & streamlit run frontend/streamlit_app.py --server.port 8501 --server.address 0.0.0.0"]
EOF

    log_success "生产环境Dockerfile已创建"
}

# 部署应用
deploy_application() {
    log_info "开始构建Docker镜像..."
    docker-compose -f docker-compose.production.yml build
    
    log_info "启动服务..."
    docker-compose -f docker-compose.production.yml up -d
    
    # 等待服务启动
    log_info "等待服务启动..."
    sleep 10
    
    # 检查服务状态
    if docker-compose -f docker-compose.production.yml ps | grep -q "Up"; then
        log_success "服务启动成功！"
    else
        log_error "服务启动失败，请检查日志"
        docker-compose -f docker-compose.production.yml logs
        exit 1
    fi
}

# 显示部署信息
show_deployment_info() {
    log_success "============================================"
    log_success "🎉 DocChat AI 生产环境部署完成！"
    log_success "============================================"
    echo ""
    log_info "📊 服务状态："
    docker-compose -f docker-compose.production.yml ps
    echo ""
    log_info "🌐 访问地址："
    log_info "- 主站: https://doc-ai.chat"
    log_info "- API文档: https://doc-ai.chat/docs"
    log_info "- 健康检查: https://doc-ai.chat/health"
    echo ""
    log_info "🔧 管理命令："
    log_info "- 查看日志: docker-compose -f docker-compose.production.yml logs"
    log_info "- 停止服务: docker-compose -f docker-compose.production.yml down"
    log_info "- 重启服务: docker-compose -f docker-compose.production.yml restart"
    log_info "- 更新部署: ./deploy-production.sh --update"
    echo ""
    log_warning "⚠️  重要提醒："
    log_warning "1. 确保域名 doc-ai.chat 已正确解析到服务器IP"
    log_warning "2. 确保SSL证书文件已正确配置在 ./ssl/ 目录"
    log_warning "3. 检查 .env.production 中的OAuth配置是否正确"
    echo ""
}

# 更新部署
update_deployment() {
    log_info "停止现有服务..."
    docker-compose -f docker-compose.production.yml down
    
    log_info "拉取最新代码..."
    git pull origin main
    
    log_info "重新构建镜像..."
    docker-compose -f docker-compose.production.yml build --no-cache
    
    log_info "启动服务..."
    docker-compose -f docker-compose.production.yml up -d
    
    log_success "应用更新完成！"
}

# 主函数
main() {
    log_info "开始部署 DocChat AI 生产环境..."
    
    case "${1:-}" in
        --update)
            update_deployment
            ;;
        --help)
            echo "用法: $0 [选项]"
            echo "选项:"
            echo "  --update    更新现有部署"
            echo "  --help     显示帮助信息"
            exit 0
            ;;
        *)
            check_docker
            check_env_files
            create_production_dockerfile
            create_production_compose
            create_nginx_config
            deploy_application
            show_deployment_info
            ;;
    esac
}

# 执行主函数
main "$@"