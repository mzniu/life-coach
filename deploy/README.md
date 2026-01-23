# Life Coach 部署指南

本目录包含 Life Coach 项目的所有部署和同步脚本。

## 目录结构

```
deploy/
├── README.md                      # 本文件
├── deploy-once.ps1                # 一键部署脚本（Windows）
├── deploy-interactive.ps1         # 交互式部署脚本（Windows）
├── setup-resilio-sync.sh          # Resilio Sync 安装脚本（树莓派）
└── setup-resilio-windows.md       # Resilio Sync Windows 安装指南
```

## 快速开始

### 1. 部署 Life Coach 到树莓派

**Windows 上运行**：
```powershell
cd deploy
.\deploy-once.ps1
```

**功能**：
- 自动配置 SSH 免密登录
- 传输项目文件到树莓派
- 安装依赖和配置环境
- 启动 systemd 服务
- 验证服务运行状态

**首次部署需要输入一次 SSH 密码，后续无需密码。**

### 2. 配置文件同步（Resilio Sync）

#### 树莓派端

SSH 登录树莓派后：
```bash
cd ~/LifeCoach/deploy
bash setup-resilio-sync.sh
```

安装完成后：
1. 浏览器打开 `http://192.168.1.100:8888`
2. 添加文件夹: `/home/pi/LifeCoach/recordings`
3. 生成密钥并复制

#### Windows 端

参考: [setup-resilio-windows.md](setup-resilio-windows.md)

1. 下载安装 Resilio Sync: https://www.resilio.com/individuals/
2. 打开 Web 界面（自动启动）
3. 输入树莓派生成的密钥
4. 选择本地文件夹（如 `D:\LifeCoach-Recordings`）
5. 等待自动同步

## 部署流程图

```
┌─────────────────┐
│ 1. 运行部署脚本  │
│ deploy-once.ps1 │
└────────┬────────┘
         ↓
┌─────────────────────┐
│ 2. Life Coach 运行  │
│ http://192.168.1.100 │
└────────┬────────────┘
         ↓
┌──────────────────────┐
│ 3. 安装 Resilio Sync │
│ setup-resilio-sync.sh│
└────────┬─────────────┘
         ↓
┌───────────────────────┐
│ 4. 配置 Windows 客户端 │
│ 自动同步录音文件       │
└───────────────────────┘
```

## 同步架构

```
┌─────────────┐
│   树莓派     │  录音设备
│  (Pi 4B)    │  始终开机
└──────┬──────┘
       │ P2P 同步
       ↓
┌──────────────┐
│  Windows PC  │  主力工作电脑
│  (台式机)     │  整理和处理录音
└──────┬───────┘
       │
       ↓
┌──────────────┐
│   笔记本      │  外出查看
│  (可选)       │  只读模式
└──────────────┘
```

## 文件组织

### 树莓派端
```
/home/pi/LifeCoach/
├── main.py                 # 主程序
├── recordings/             # 录音文件（同步目录）
│   ├── 20260123_143022.wav
│   ├── 20260123_143022.txt
│   └── ...
├── voiceprints/            # 声纹数据
├── models/                 # AI 模型
└── deploy/                 # 部署脚本
```

### Windows 端
```
D:\LifeCoach-Recordings/    # Resilio Sync 同步目录
├── 20260123_143022.wav
├── 20260123_143022.txt
└── ...
```

## 网络要求

### 局域网内（推荐）
- 树莓派和电脑在同一 WiFi
- 同步速度: 100MB/s+
- 延迟: 几秒内完成

### 外网同步
- 树莓派连接手机热点或公共 WiFi
- 自动 P2P 或加密中继
- 同步速度: 取决于上传带宽（1-5MB/s）

## 故障排查

### Life Coach 服务问题

**查看日志**：
```bash
ssh pi@192.168.1.100 'journalctl -u lifecoach -f'
```

**重启服务**：
```bash
ssh pi@192.168.1.100 'sudo systemctl restart lifecoach'
```

**查看状态**：
```bash
ssh pi@192.168.1.100 'sudo systemctl status lifecoach'
```

### Resilio Sync 同步问题

**树莓派端**：
```bash
# 查看服务状态
sudo systemctl status resilio-sync

# 查看日志
sudo journalctl -u resilio-sync -f

# 重启服务
sudo systemctl restart resilio-sync
```

**Windows 端**：
- 检查系统托盘 Resilio Sync 图标
- 打开 Web 界面查看连接状态
- 检查 Windows 防火墙是否阻止

### 常见问题

**Q: 设备连接不上？**
- 检查两边服务都在运行
- 等待几分钟，设备发现需要时间
- 检查防火墙设置

**Q: 同步速度慢？**
- 局域网内应该很快，检查 WiFi 信号
- 外网受限于带宽，属于正常

**Q: 文件冲突？**
- Resilio 会保留两个版本，文件名添加 `.conflict` 后缀
- 手动选择需要的版本

## 安全说明

### SSH 密钥
- 密钥位置: `C:\Users\{你的用户名}\.ssh\id_rsa`
- 仅用于部署，请妥善保管
- 如需重置，删除密钥文件重新运行 deploy-once.ps1

### Resilio Sync
- 端到端加密，中继服务器看不到内容
- 密钥即权限，请勿公开分享
- 只读密钥可以安全分享给其他人查看

### 网络
- Life Coach Web 界面无认证，仅局域网访问
- 如需公网访问，建议配置 nginx 反向代理 + HTTPS

## 备份策略

### 多重保护
1. **树莓派本地**：原始数据
2. **Windows PC**：实时同步副本
3. **笔记本**：移动副本
4. **可选 NAS**：只读备份

### 数据恢复
- 任意一台设备数据完整即可恢复
- Resilio Sync 存档功能保留删除文件 30 天

## 维护建议

### 定期检查
- 每周检查磁盘空间（`df -h`）
- 每月检查日志文件大小
- 定期测试同步是否正常

### 更新
- Life Coach: 运行 `deploy-once.ps1` 自动更新
- Resilio Sync: 客户端会自动提示更新

## 支持

如有问题，请查看：
- Life Coach 日志: `journalctl -u lifecoach -f`
- Resilio Sync 日志: `journalctl -u resilio-sync -f`
- 项目文档: `../docs/`

---

最后更新: 2026-01-23
