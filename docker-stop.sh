#!/bin/bash

# Docker停止脚本
set -e

echo "🛑 停止 DocChat AI Docker 容器..."

# 检查docker-compose是否安装
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose未安装"
    exit 1
fi

# 停止并移除容器
docker-compose down

echo "✅ 容器已停止并移除"
echo ""
echo "💾 数据文件仍然保留在 ./data 目录中"