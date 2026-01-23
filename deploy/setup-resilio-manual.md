# Resilio Sync 手动安装指南（网络受限环境）

如果自动下载脚本失败，可以按以下步骤手动安装。

## 适用场景

- 树莓派无法访问国外服务器
- 网络环境不稳定
- 下载速度太慢或超时

## 安装步骤

### 1. 在 Windows 电脑上下载

根据你的树莓派型号选择：

**树莓派 4/5 (64位系统)**
```
https://download-cdn.resilio.com/stable/linux/arm64/0/resilio-sync_arm64.tar.gz
```

**树莓派 3/4 (32位系统)**
```
https://download-cdn.resilio.com/stable/linux/arm/0/resilio-sync_arm.tar.gz
```

不确定系统架构？SSH 登录树莓派运行：
```bash
uname -m
# aarch64 = 64位，下载 arm64 版本
# armv7l = 32位，下载 arm 版本
```

### 2. 传输到树莓派

**使用 SCP (推荐)**
```powershell
# Windows PowerShell
scp resilio-sync_arm64.tar.gz pi@192.168.1.100:/home/pi/.resilio-sync/
```

**或使用 WinSCP**
- 下载 WinSCP: https://winscp.net/
- 连接到 192.168.1.100
- 上传到 `/home/pi/.resilio-sync/`

### 3. SSH 登录树莓派

```bash
ssh pi@192.168.1.100
```

### 4. 手动安装

```bash
# 进入安装目录
cd ~/.resilio-sync

# 解压（根据你下载的文件名调整）
tar -xzf resilio-sync_arm64.tar.gz

# 删除压缩包
rm resilio-sync_arm64.tar.gz

# 设置可执行权限
chmod +x rslsync

# 验证安装
./rslsync --help
```

看到帮助信息即表示安装成功。

### 5. 创建配置文件

```bash
cat > ~/.resilio-sync/sync.conf <<'EOF'
{
  "storage_path": "/home/pi/.resilio-sync/data",
  "pid_file": "/home/pi/.resilio-sync/sync.pid",
  "webui": {
    "listen": "0.0.0.0:8888",
    "login": "",
    "password": ""
  }
}
EOF
```

### 6. 配置 systemd 服务

```bash
sudo tee /etc/systemd/system/resilio-sync.service > /dev/null <<'EOF'
[Unit]
Description=Resilio Sync Service
After=network.target

[Service]
Type=simple
User=cmit
ExecStart=/home/pi/.resilio-sync/rslsync --nodaemon --config /home/pi/.resilio-sync/sync.conf
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

### 7. 启动服务

```bash
# 重载 systemd 配置
sudo systemctl daemon-reload

# 启用开机自启
sudo systemctl enable resilio-sync

# 启动服务
sudo systemctl start resilio-sync

# 检查状态
sudo systemctl status resilio-sync
```

### 8. 访问 Web 界面

浏览器打开: http://192.168.1.100:8888

## 故障排查

### 查看日志
```bash
sudo journalctl -u resilio-sync -f
```

### 重启服务
```bash
sudo systemctl restart resilio-sync
```

### 检查进程
```bash
ps aux | grep rslsync
```

### 测试手动启动
```bash
cd ~/.resilio-sync
./rslsync --config sync.conf
# Ctrl+C 停止
```

## 常见问题

**Q: 下载很慢怎么办？**
- 使用迅雷或 IDM 等下载工具加速
- 或搜索 "resilio sync arm64 镜像下载"

**Q: 解压失败？**
- 检查下载的文件是否完整：`ls -lh resilio-sync_*.tar.gz`
- 重新下载文件

**Q: 权限不足？**
```bash
sudo chown -R cmit:cmit ~/.resilio-sync
chmod +x ~/.resilio-sync/rslsync
```

**Q: 端口 8888 被占用？**
修改配置文件中的端口号：
```bash
nano ~/.resilio-sync/sync.conf
# 修改 "listen": "0.0.0.0:8888" 为其他端口
```

## 替代方案

如果 Resilio Sync 实在无法安装，可以考虑：

1. **Syncthing** (更轻量，国内访问好)
```bash
sudo apt install syncthing
```

2. **rclone + 坚果云**
```bash
curl https://rclone.org/install.sh | sudo bash
```

详细配置见主文档。

---

最后更新: 2026-01-23
