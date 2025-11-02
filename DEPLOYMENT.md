# DocChat AI 生产环境部署指南

## 快速开始

### 一键部署
```bash
# 执行一键部署脚本
./deploy-production.sh

# 或者指定域名（可选）
./deploy-production.sh doc-ai.chat
```

### 手动部署
```bash
# 1. 构建并启动服务
docker-compose up -d

# 2. 检查服务状态
docker-compose ps

# 3. 查看日志
docker-compose logs -f
```

## 服务访问

- **前端应用**: http://localhost:8501 (或指定域名)
- **后端API**: http://localhost:8000
- **API文档**: http://localhost:8000/docs

## 环境配置

### 必需的环境变量
在 `.env.production` 文件中配置：
```bash
DOCCHAT_ENV=production
DATABASE_URL=postgresql://user:password@host:port/database
GOOGLE_OAUTH_CLIENT_ID=your_google_client_id
GOOGLE_OAUTH_CLIENT_SECRET=your_google_client_secret
GOOGLE_OAUTH_REDIRECT_URI=https://your-domain.com/auth/google/callback
```

### 可选配置
- `UVICORN_PORT`: 后端服务端口 (默认: 8000)
- `STREAMLIT_PORT`: 前端服务端口 (默认: 8501)
- `LOG_LEVEL`: 日志级别 (默认: INFO)

## 管理命令

```bash
# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 更新服务（重新构建）
docker-compose up -d --build

# 查看服务状态
docker-compose ps

# 查看服务日志
docker-compose logs -f
```

## 健康检查

部署脚本会自动配置健康检查：
- 后端健康检查: `http://localhost:8000/health`
- 前端健康检查: `http://localhost:8501/healthz`

## 故障排除

### 常见问题

1. **端口冲突**
   - 检查端口 8000 和 8501 是否被占用
   - 修改 `docker-compose.yml` 中的端口映射

2. **数据库连接失败**
   - 检查 `DATABASE_URL` 配置是否正确
   - 确保数据库服务可访问

3. **OAuth 配置错误**
   - 验证 Google OAuth 客户端 ID 和密钥
   - 检查回调 URL 与域名匹配

### 日志查看
```bash
# 查看所有服务日志
docker-compose logs

# 查看特定服务日志
docker-compose logs docchat-ai

# 实时查看日志
docker-compose logs -f
```

## 备份与恢复

### 数据备份
```bash
# 备份数据库
docker-compose exec db pg_dump -U postgres docchat > backup.sql

# 备份应用数据
tar -czf backup.tar.gz data/
```

### 数据恢复
```bash
# 恢复数据库
docker-compose exec -T db psql -U postgres docchat < backup.sql

# 恢复应用数据
tar -xzf backup.tar.gz
```

## 监控与维护

### 资源监控
```bash
# 查看容器资源使用
docker stats

# 查看磁盘使用
df -h

# 查看内存使用
free -h
```

### 定期维护
- 定期更新 Docker 镜像
- 清理无用的容器和镜像
- 备份重要数据
- 检查日志文件大小

## 技术支持

如有问题，请检查：
1. 部署脚本输出日志
2. Docker 容器状态
3. 服务访问日志
4. 环境变量配置