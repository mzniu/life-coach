# Life Coach 部署和同步快速指南

## 一、首次部署（5分钟）

### Windows 电脑上

1. **克隆项目**（如果还没有）
   ```powershell
   cd D:\git
   git clone <your-repo-url> life-coach
   cd life-coach
   ```

2. **运行一键部署**
   ```powershell
   .\deploy.ps1
   ```
   
   首次运行会提示输入树莓派密码一次，后续自动免密部署。

3. **验证部署**
   - 浏览器打开: http://192.168.1.100:5000
   - 看到 Life Coach 监控面板即成功

## 二、配置文件同步（10分钟）

### 树莓派端（SSH 操作）

1. **SSH 登录树莓派**
   ```powershell
   ssh pi@192.168.1.100
   ```

2. **运行 Resilio Sync 安装脚本**
   ```bash
   cd ~/LifeCoach/deploy
   bash setup-resilio-sync.sh
   ```

3. **获取同步密钥**
   - 浏览器打开: http://192.168.1.100:8888
   - 点击「+ 添加文件夹」
   - 文件夹路径: `/home/pi/LifeCoach/recordings`
   - 点击「生成密钥」
   - 复制生成的密钥（类似：`BXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX`）

### Windows 端

1. **下载 Resilio Sync**
   - 访问: https://www.resilio.com/individuals/
   - 下载并安装 Windows 版本
   - 安装后会自动启动并打开浏览器

2. **添加同步文件夹**
   - 在 Resilio Sync 界面点击「+」
   - 选择「输入密钥或链接」
   - 粘贴树莓派生成的密钥
   - 选择本地文件夹（如 `D:\LifeCoach-Recordings`）
   - 点击「连接」

3. **等待同步**
   - 设备会自动发现并连接
   - 局域网内同步速度极快（100MB/s+）
   - 可在界面查看实时进度

## 三、日常使用

### 录音流程

1. **开始录音**
   - 按树莓派上的 K1 按钮（GPIO2）
   - 或在网页点击「开始录音」
   - 红色 LED 亮起

2. **停止录音**
   - 再次按 K1 按钮
   - 或在网页点击「停止录音」
   - 自动转写，显示进度

3. **查看结果**
   - 转写完成后自动保存
   - 文件自动同步到 Windows 电脑
   - 在 `D:\LifeCoach-Recordings` 查看

### 文件自动同步

- **在家时**：局域网高速同步，几秒完成
- **外出时**：通过互联网 P2P 自动同步
- **多设备**：所有配置了 Resilio 的设备都会同步

## 四、更新部署

### 代码更新后重新部署

```powershell
cd D:\git\life-coach
git pull
.\deploy.ps1
```

自动更新树莓派上的所有文件并重启服务。

## 五、常用命令

### 查看日志
```powershell
ssh pi@192.168.1.100 'journalctl -u lifecoach -f'
```

### 重启服务
```powershell
ssh pi@192.168.1.100 'sudo systemctl restart lifecoach'
```

### 查看同步状态
- Life Coach: http://192.168.1.100:5000
- Resilio Sync: http://192.168.1.100:8888

## 六、故障排查

### 部署失败
- 检查树莓派 IP 是否正确（192.168.1.100）
- 确认 SSH 服务已启动
- 查看错误日志输出

### 同步不工作
- 检查 Resilio Sync 服务是否运行
- Windows: 系统托盘查看图标
- 树莓派: `sudo systemctl status resilio-sync`
- 防火墙是否阻止连接

### 录音无声音
- 检查麦克风是否连接
- 查看日志：`journalctl -u lifecoach -f`
- 测试麦克风：`arecord -l`

## 详细文档

更多信息请查看：
- [完整部署文档](deploy/README.md)
- [Resilio Sync Windows 指南](deploy/setup-resilio-windows.md)
- [产品需求文档](docs/PRD.md)
- [概要设计](docs/概要设计-MVP.md)

---

最后更新: 2026-01-23
