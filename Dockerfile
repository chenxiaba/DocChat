# 多阶段构建：构建阶段
FROM python:3.11-slim as builder

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 创建虚拟环境
RUN python -m venv /opt/venv

# 确保pip是最新版本
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip

# 复制requirements文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 多阶段构建：生产阶段
FROM python:3.11-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 创建非root用户
RUN groupadd -r docchat && useradd -r -g docchat docchat

# 创建应用目录
WORKDIR /app

# 从构建阶段复制虚拟环境
COPY --from=builder /opt/venv /opt/venv

# 复制应用代码
COPY . .

# 设置环境变量
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH="/app"
ENV PYTHONUNBUFFERED="1"

# 创建必要的目录
RUN mkdir -p /app/data /app/logs

# 更改文件所有权
RUN chown -R docchat:docchat /app

# 切换到非root用户
USER docchat

# 暴露端口（内部使用，不直接暴露到宿主机）
EXPOSE 8000 8501

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 设置生产环境变量
ENV DOCCHAT_ENV=production

# 启动应用（使用生产环境配置）
CMD ["/bin/bash", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2 & sleep 10 && streamlit run frontend/streamlit_app.py --server.port 8501 --server.address 0.0.0.0"]