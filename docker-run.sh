#!/bin/bash

# Docker运行脚本
set -e

echo "🚀 启动 DocChat AI Docker 容器..."

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ Docker未安装，请先安装Docker"
    exit 1
fi

# 检查docker-compose是否安装
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose未安装，请先安装docker-compose"
    exit 1
fi

# 创建必要的目录
mkdir -p data logs

echo "📦 构建Docker镜像..."
docker-compose build

echo "▶️ 启动服务..."
docker-compose up -d

echo "⏳ 等待服务启动..."
sleep 10

# 检查服务状态
echo "🔍 检查服务状态..."
if docker-compose ps | grep -q "Up"; then
    echo "✅ 服务启动成功！"
    echo ""
    echo "🌐 访问地址："
    echo "   - 前端界面: http://localhost:8501"
    echo "   - API文档: http://localhost:8000/docs"
    echo ""
    echo "📋 常用命令："
    echo "   - 查看日志: docker-compose logs -f"
    echo "   - 停止服务: docker-compose down"
    echo "   - 重启服务: docker-compose restart"
    echo ""
else
    echo "❌ 服务启动失败，请检查日志：docker-compose logs"
    exit 1
fi