#!/bin/bash

# DocChat AI 部署脚本（包含Nginx）
# 作者: DocChat AI Team
# 描述: 使用Docker Compose部署完整的DocChat AI应用，包含Nginx反向代理

set -e

echo "🚀 开始部署 DocChat AI (包含Nginx)..."

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ Docker未安装，请先安装Docker"
    exit 1
fi

# 检查Docker Compose是否安装
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose未安装，请先安装Docker Compose"
    exit 1
fi

# 创建必要的目录
echo "📁 创建必要的目录..."
mkdir -p data logs/nginx

# 检查环境配置文件
if [ ! -f ".env.production" ]; then
    echo "⚠️  未找到.env.production文件，将使用默认配置"
    echo "📝 请在生产环境中配置正确的环境变量"
fi

# 停止现有服务（如果存在）
echo "🛑 停止现有服务..."
docker-compose down || true

# 构建镜像
echo "🔨 构建Docker镜像..."
docker-compose build

# 启动服务
echo "🚀 启动服务..."
docker-compose up -d

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 30

# 检查服务状态
echo "🔍 检查服务状态..."

# 检查Nginx服务
if docker-compose ps nginx | grep -q "Up"; then
    echo "✅ Nginx服务运行正常"
else
    echo "❌ Nginx服务启动失败"
    docker-compose logs nginx
    exit 1
fi

# 检查应用服务
if docker-compose ps docchat-app | grep -q "Up"; then
    echo "✅ DocChat应用服务运行正常"
else
    echo "❌ DocChat应用服务启动失败"
    docker-compose logs docchat-app
    exit 1
fi

# 测试健康检查
echo "🧪 测试健康检查..."
if curl -f http://localhost/health > /dev/null 2>&1; then
    echo "✅ 健康检查通过"
else
    echo "❌ 健康检查失败"
    exit 1
fi

# 测试API端点
echo "🧪 测试API端点..."
if curl -f http://localhost/api/health > /dev/null 2>&1; then
    echo "✅ API端点正常"
else
    echo "❌ API端点测试失败"
    exit 1
fi

# 显示部署信息
echo ""
echo "🎉 部署完成！"
echo ""
echo "📊 服务信息："
echo "   - 前端应用: http://localhost"
echo "   - API文档: http://localhost/docs"
echo "   - 健康检查: http://localhost/health"
echo ""
echo "🔧 管理命令："
echo "   - 查看日志: docker-compose logs -f"
echo "   - 停止服务: docker-compose down"
echo "   - 重启服务: docker-compose restart"
echo "   - 查看状态: docker-compose ps"
echo ""
echo "⚠️  生产环境注意事项："
echo "   - 配置真实的SSL证书到ssl/目录"
echo "   - 更新.env.production中的敏感信息"
echo "   - 配置域名解析到服务器IP"
echo "   - 设置防火墙规则"
echo ""

# 显示当前服务状态
echo "📈 当前服务状态："
docker-compose ps

echo ""
echo "✅ 部署完成！DocChat AI 现在可以通过 http://localhost 访问"