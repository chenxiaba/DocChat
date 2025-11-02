# DocChat AI 生产环境部署指南

## 🎯 部署目标
- 域名：`doc-ai.chat`
- 环境：生产环境
- 协议：HTTPS

## 📋 前置条件

### 1. 域名和SSL证书
- 已注册域名：`doc-ai.chat`
- 已获取SSL证书（Let's Encrypt或商业证书）
- DNS解析已配置

### 2. 服务器要求
- 操作系统：Ubuntu 20.04+ / CentOS 8+
- 内存：至少2GB
- 存储：至少20GB可用空间
- Python 3.9+

### 3. 第三方服务配置
- [Google Cloud Console](https://console.cloud.google.com/) - 生产环境OAuth凭据
- [微信开放平台](https://open.weixin.qq.com/) - 生产环境微信登录凭据

## 🚀 部署步骤

### 步骤1：服务器准备

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装基础依赖
sudo apt install -y python3-pip python3-venv nginx certbot

# 创建应用用户
sudo useradd -r -s /bin/false docchat
sudo mkdir -p /var/lib/docchat/{data,logs}
sudo chown -R docchat:docchat /var/lib/docchat
```

### 步骤2：配置生产环境凭据

#### Google OAuth 生产环境配置
1. 访问 [Google Cloud Console](https://console.cloud.google.com/)
2. 进入您的项目 → API和服务 → 凭据
3. 创建OAuth 2.0客户端ID：
   - 应用类型：Web应用
   - 名称：DocChat AI Production
   - 授权重定向URI：`https://doc-ai.chat/auth/google/callback`
4. 复制Client ID和Client Secret

#### 个人微信登录生产环境配置
1. 访问 [微信开放平台](https://open.weixin.qq.com/)
2. 进入**网站应用**管理（注意不是小程序、公众号或企业微信应用）
3. 设置授权回调域名：`doc-ai.chat`
4. 复制AppID和AppSecret
5. 在 `.env.production` 中配置：
   ```
   DOCCHAT_WECHAT_APP_ID=your_production_wechat_app_id
   DOCCHAT_WECHAT_APP_SECRET=your_production_wechat_app_secret
   DOCCHAT_WECHAT_REDIRECT_URI=https://doc-ai.chat/auth/wechat/callback
   ```

### 步骤3：应用部署

```bash
# 克隆代码（或上传代码到服务器）
git clone https://github.com/chenxiaba/DocChat.git /opt/docchat
cd /opt/docchat

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置生产环境变量
cp .env.production .env
# 编辑.env文件，填入真实的凭据
```

### 步骤4：配置Nginx反向代理

创建Nginx配置文件 `/etc/nginx/sites-available/doc-ai.chat`：

```nginx
server {
    listen 80;
    server_name doc-ai.chat;
    
    # 重定向HTTP到HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name doc-ai.chat;
    
    # SSL证书配置
    ssl_certificate /etc/letsencrypt/live/doc-ai.chat/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/doc-ai.chat/privkey.pem;
    
    # SSL安全配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    
    # 反向代理配置
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # WebSocket支持（用于流式响应）
    location /chat_stream {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
    
    # 静态文件缓存
    location /static/ {
        alias /opt/docchat/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

启用站点：
```bash
sudo ln -s /etc/nginx/sites-available/doc-ai.chat /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### 步骤5：获取SSL证书

```bash
# 使用Certbot获取Let's Encrypt证书
sudo certbot --nginx -d doc-ai.chat

# 设置自动续期
sudo crontab -e
# 添加：0 12 * * * /usr/bin/certbot renew --quiet
```

### 步骤6：配置系统服务

创建systemd服务文件 `/etc/systemd/system/docchat.service`：

```ini
[Unit]
Description=DocChat AI Backend
After=network.target

[Service]
Type=exec
User=docchat
Group=docchat
WorkingDirectory=/opt/docchat
Environment=PATH=/opt/docchat/venv/bin
ExecStart=/opt/docchat/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
sudo systemctl daemon-reload
sudo systemctl enable docchat
sudo systemctl start docchat
```

### 步骤7：配置Streamlit前端

创建Streamlit服务文件 `/etc/systemd/system/docchat-frontend.service`：

```ini
[Unit]
Description=DocChat AI Frontend
After=network.target docchat.service

[Service]
Type=exec
User=docchat
Group=docchat
WorkingDirectory=/opt/docchat
Environment=PATH=/opt/docchat/venv/bin
ExecStart=/opt/docchat/venv/bin/streamlit run frontend/streamlit_app.py --server.port 8501 --server.address 127.0.0.1
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

配置Nginx代理Streamlit（添加到之前的配置中）：

```nginx
# Streamlit前端代理
location /app/ {
    proxy_pass http://127.0.0.1:8501/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

## 🔧 生产环境优化

### 数据库优化
```bash
# 如果使用PostgreSQL
sudo -u postgres createdb docchat_prod
sudo -u postgres psql -c "CREATE USER docchat WITH PASSWORD 'secure_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE docchat_prod TO docchat;"
```

### 性能调优
```bash
# 调整系统参数
echo 'net.core.somaxconn = 1024' | sudo tee -a /etc/sysctl.conf
echo 'vm.overcommit_memory = 1' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

### 监控配置
```bash
# 安装监控工具
sudo apt install -y htop iotop nethogs

# 配置日志轮转
sudo cp /opt/docchat/scripts/logrotate.conf /etc/logrotate.d/docchat
```

## 🧪 部署后测试

### 功能测试清单
- [ ] 访问 https://doc-ai.chat/ 检查主页
- [ ] 测试Google登录功能
- [ ] 测试微信登录功能
- [ ] 测试文档上传功能
- [ ] 测试智能对话功能
- [ ] 测试流式响应功能
- [ ] 检查SSL证书有效性
- [ ] 验证CORS配置

### 性能测试
```bash
# 使用ab进行压力测试
ab -n 1000 -c 10 https://doc-ai.chat/health

# 检查响应时间
curl -w "@curl-format.txt" -o /dev/null -s https://doc-ai.chat/
```

## 🔒 安全配置

### 防火墙配置
```bash
# 只开放必要端口
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```

### 文件权限
```bash
# 保护敏感文件
sudo chmod 600 /opt/docchat/.env
sudo chown docchat:docchat /opt/docchat/.env
```

## 📞 故障排除

### 常见问题
1. **SSL证书错误**：检查证书路径和权限
2. **OAuth回调失败**：验证回调URL配置
3. **数据库连接失败**：检查连接字符串和网络
4. **内存不足**：增加swap空间或优化配置

### 日志查看
```bash
# 查看应用日志
sudo journalctl -u docchat -f

# 查看Nginx日志
sudo tail -f /var/log/nginx/error.log
```

## 🎉 部署完成

成功部署后，您的DocChat AI将可以通过以下地址访问：
- 主站点：https://doc-ai.chat/
- API文档：https://doc-ai.chat/docs
- 健康检查：https://doc-ai.chat/health

记得定期备份数据和更新系统！