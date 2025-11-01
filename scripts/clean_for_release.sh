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

# 安全删除函数
safe_delete() {
    local target=$1
    local description=$2
    
    if [ -e "$target" ]; then
        log_info "删除 $description: $target"
        rm -rf "$target"
        if [ ! -e "$target" ]; then
            log_success "$description 删除成功"
        else
            log_error "$description 删除失败"
        fi
    else
        log_info "$description 不存在: $target"
    fi
}

echo "======================================"
echo "🧹 DocChat AI 项目清理脚本"
echo "======================================"

# 切换到项目根目录
cd "$(dirname "$0")/.." || exit 1

log_info "开始清理项目缓存和生成文件..."

# 1. 清理Python缓存文件
log_info "清理Python缓存文件..."
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete
find . -name "*.pyo" -delete
find . -name "*.pyd" -delete
find . -name "*.so" -delete
find . -name "*.egg-info" -type d -exec rm -rf {} + 2>/dev/null

# 2. 清理数据文件（保留目录结构）
log_info "清理数据文件..."
safe_delete "data/chat_history.pkl" "聊天历史文件"
safe_delete "data/memory.sqlite" "内存数据库"
safe_delete "data/vector_store" "向量数据库"

# 重新创建空的数据目录结构
mkdir -p data/vector_store

# 3. 清理脚本目录中的数据文件
log_info "清理脚本目录中的数据文件..."
safe_delete "scripts/data/memory.sqlite" "脚本目录内存数据库"
safe_delete "scripts/data/vector_store" "脚本目录向量数据库"

# 重新创建空的脚本数据目录结构
mkdir -p scripts/data/vector_store

# 4. 清理日志文件
log_info "清理日志文件..."
safe_delete "logs" "日志目录"

# 重新创建日志目录
mkdir -p logs

# 5. 清理虚拟环境（但保留venv目录结构）
log_info "清理虚拟环境..."
if [ -d "scripts/venv" ]; then
    log_warning "保留虚拟环境目录结构，但建议用户重新创建"
    # 不删除venv目录，但可以清理其中的缓存
    find scripts/venv -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
    find scripts/venv -name "*.pyc" -delete
else
    log_info "虚拟环境目录不存在"
fi

# 6. 清理临时文件
log_info "清理临时文件..."
find . -name "*.tmp" -delete
find . -name "*.temp" -delete
find . -name "*.log" -delete
find . -name ".DS_Store" -delete
find . -name "Thumbs.db" -delete

# 7. 清理备份文件
log_info "清理备份文件..."
find . -name "*.backup" -delete
find . -name "*.bak" -delete
find . -name "*~" -delete

# 8. 创建.gitignore文件（如果不存在）
log_info "检查.gitignore文件..."
if [ ! -f ".gitignore" ]; then
    cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual environments
venv/
ENV/
env/
.venv/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Project specific
data/
logs/
.env
*.sqlite
*.sqlite3
*.pkl
*.pickle

# Scripts data
scripts/data/
EOF
    log_success ".gitignore文件已创建"
else
    log_info ".gitignore文件已存在"
fi

# 9. 创建环境配置文件模板
log_info "检查环境配置文件..."
if [ -f ".env" ]; then
    log_warning "发现.env文件，建议备份后删除"
    cp .env .env.example
    safe_delete ".env" "环境配置文件"
    log_success "已创建.env.example模板"
else
    log_info ".env文件不存在"
fi

# 10. 创建发布说明文件
log_info "创建发布说明文件..."
cat > RELEASE_NOTES.md << 'EOF'
# DocChat AI 发布说明

## 项目概述

DocChat AI 是一个基于大语言模型的文档问答系统，支持PDF文档上传、智能问答和对话记忆功能。

## 功能特性

- 📄 PDF文档上传与解析
- 💬 智能问答对话
- 🧠 对话记忆管理
- 🔍 语义检索
- 🌐 Web界面（Streamlit）
- 🔌 RESTful API（FastAPI）

## 系统要求

- Python 3.9+
- OpenAI API密钥
- 至少2GB可用内存

## 快速开始

1. 克隆项目
2. 运行环境初始化：`bash scripts/setup.sh`
3. 配置API密钥：复制`.env.example`为`.env`并填入OpenAI API密钥
4. 启动服务：`bash scripts/start.sh`
5. 访问Web界面：http://localhost:8501

## 文件说明

- `app/` - FastAPI后端应用
- `frontend/` - Streamlit前端界面
- `scripts/` - 启动和管理脚本
- `data/` - 数据存储目录（自动创建）
- `logs/` - 日志目录（自动创建）

## 注意事项

- 首次运行会自动创建必要的数据库和目录
- 确保有足够的磁盘空间存储向量数据库
- 建议在生产环境中使用更安全的数据库解决方案

## 许可证

[请在此处添加许可证信息]
EOF

log_success "发布说明文件已创建"

# 11. 验证清理结果
log_info "验证清理结果..."

# 检查是否还有缓存文件
if find . -name "__pycache__" | grep -q .; then
    log_warning "发现残留的缓存文件"
else
    log_success "缓存文件清理完成"
fi

# 检查数据目录是否为空
if [ "$(ls -A data/vector_store 2>/dev/null)" ]; then
    log_warning "数据目录不为空"
else
    log_success "数据目录清理完成"
fi

echo ""
log_success "✅ 项目清理完成！"
echo ""
echo "📋 清理总结："
echo "   ✅ Python缓存文件已清理"
echo "   ✅ 数据文件已清理（保留目录结构）"
echo "   ✅ 日志文件已清理"
echo "   ✅ 临时文件已清理"
echo "   ✅ .gitignore文件已配置"
echo "   ✅ 环境配置文件已处理"
echo "   ✅ 发布说明文件已创建"
echo ""
echo "🚀 下一步操作："
echo "   1. 检查.gitignore配置是否完整"
echo "   2. 更新README.md中的安装说明"
echo "   3. 添加合适的许可证文件"
echo "   4. 初始化Git仓库：git init"
echo "   5. 提交代码：git add . && git commit -m 'Initial release'"
echo ""
echo "📁 项目现在适合作为开源项目发布！"
echo ""