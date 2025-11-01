# Docker 部署指南

本文档介绍如何使用 Docker 部署 DocChat AI 系统。

## 前提条件

- Docker 已安装
- Docker Compose 已安装
- 至少 2GB 可用内存

## 快速开始

### 1. 克隆项目

```bash
git clone <repository-url>
cd DocChat_AI
```

### 2. 使用脚本启动（推荐）

```bash
# 启动服务
./docker-run.sh

# 停止服务
./docker-stop.sh
```

### 3. 手动启动

```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

## 服务访问

启动成功后，可以通过以下地址访问：

- **前端界面**: http://localhost:8501
- **API文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/docs

## 数据持久化

- `./data` 目录用于存储上传的PDF文档
- `./logs` 目录用于存储应用日志
- 这些目录会自动创建并挂载到容器中

## 环境配置

### 环境变量

在运行容器前，可以设置以下环境变量：

```bash
export DEEPSEEK_API_KEY="your-api-key"
export OPENAI_API_KEY="your-openai-key"
```

或者创建 `.env` 文件：

```env
DEEPSEEK_API_KEY=your-api-key
OPENAI_API_KEY=your-openai-key
```

### 配置文件

- 复制 `.env.example` 为 `.env` 并配置API密钥
- 复制 `.streamlit/secrets.toml.example` 为 `.streamlit/secrets.toml`

## 故障排除

### 端口冲突

如果端口 8000 或 8501 已被占用，可以修改 `docker-compose.yml` 中的端口映射：

```yaml
ports:
  - "8080:8000"  # 修改前端端口
  - "8502:8501"  # 修改API端口
```

### 内存不足

如果遇到内存不足的问题，可以：

1. 增加Docker内存限制
2. 减少同时处理的文档数量
3. 清理不需要的文档

### 查看日志

```bash
# 查看所有服务日志
docker-compose logs

# 实时查看日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs docchat-ai
```

## 开发模式

对于开发环境，可以使用以下命令：

```bash
# 开发模式（带文件监控）
docker-compose -f docker-compose.dev.yml up
```

## 生产部署

### 1. 构建生产镜像

```bash
docker build -t docchat-ai:latest .
```

### 2. 运行生产容器

```bash
docker run -d \
  --name docchat-ai \
  -p 8000:8000 \
  -p 8501:8501 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  docchat-ai:latest
```

## 安全建议

1. 使用非root用户运行容器
2. 定期更新基础镜像
3. 使用HTTPS代理
4. 配置防火墙规则
5. 定期备份数据

## 性能优化

1. 使用多阶段构建减小镜像大小
2. 配置适当的资源限制
3. 使用缓存优化构建过程
4. 定期清理不需要的镜像和容器

## 常见问题

### Q: 如何重置系统？
A: 停止容器后删除 `data` 和 `logs` 目录，然后重新启动。

### Q: 如何更新到新版本？
A: 拉取最新代码，重新构建镜像并重启容器。

### Q: 如何备份数据？
A: 备份 `data` 目录中的所有文件。

### Q: 如何扩展系统？
A: 可以添加更多的后端实例，使用负载均衡器分发请求。