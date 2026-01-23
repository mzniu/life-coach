#!/bin/bash
# Resilio Sync 自动安装和配置脚本（树莓派）
# 用法: bash setup-resilio-sync.sh
# 可通过环境变量配置：
#   RESILIO_USERNAME - Web 界面用户名（默认：admin）
#   RESILIO_PASSWORD - Web 界面密码（默认：生成随机密码）

# 不使用 set -e，手动检查每个关键步骤
SYNC_DIR="$HOME/LifeCoach/recordings"
INSTALL_DIR="$HOME/.resilio-sync"
WEB_PORT=8888

# 读取配置，提供默认值
RESILIO_USERNAME="${RESILIO_USERNAME:-admin}"
RESILIO_PASSWORD="${RESILIO_PASSWORD:-$(openssl rand -base64 12 2>/dev/null || echo "lifecoach$(date +%s)")}"

echo "========================================"
echo "Resilio Sync 安装脚本（树莓派）"
echo "========================================"

# 检测架构
ARCH=$(uname -m)
if [[ "$ARCH" == "aarch64" ]]; then
    DOWNLOAD_URL="https://download-cdn.resilio.com/stable/linux/arm64/0/resilio-sync_arm64.tar.gz"
    PACKAGE="resilio-sync_arm64.tar.gz"
elif [[ "$ARCH" == "armv7l" || "$ARCH" == "armv6l" ]]; then
    DOWNLOAD_URL="https://download-cdn.resilio.com/stable/linux/arm/0/resilio-sync_arm.tar.gz"
    PACKAGE="resilio-sync_arm.tar.gz"
else
    echo "错误: 不支持的架构 $ARCH"
    exit 1
fi

echo "[1/6] 检测架构: $ARCH"

# 创建安装目录
echo "[2/6] 创建安装目录..."
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

# 下载 Resilio Sync
if [ ! -f "rslsync" ]; then
    echo "[3/6] 准备 Resilio Sync 安装包..."
    
    # 先检查 deploy 目录是否有本地文件
    LOCAL_FILE="$HOME/LifeCoach/deploy/$PACKAGE"
    if [ -f "$LOCAL_FILE" ]; then
        echo "  ✓ 检测到本地安装包，直接使用"
        echo "  文件: $LOCAL_FILE"
        cp "$LOCAL_FILE" "$PACKAGE"
    else
        echo "  本地文件不存在，开始下载..."
        echo "  下载地址: $DOWNLOAD_URL"
        echo "  这可能需要几分钟，请耐心等待..."
        
        # 尝试下载，带超时和重试
        DOWNLOAD_SUCCESS=0
        for i in {1..3}; do
            echo "  尝试下载 (第 $i 次)..."
            if wget --timeout=120 --tries=2 --show-progress "$DOWNLOAD_URL" -O "$PACKAGE" 2>&1; then
                DOWNLOAD_SUCCESS=1
                break
            else
                echo "  下载失败，等待 5 秒后重试..."
                rm -f "$PACKAGE"
                sleep 5
            fi
        done
        
        if [ $DOWNLOAD_SUCCESS -eq 0 ]; then
            echo ""
            echo "✗ 下载失败！可能原因："
            echo "  1. 网络连接问题"
            echo "  2. 树莓派无法访问国外服务器"
            echo "  3. DNS 解析失败"
            echo ""
            echo "解决方案："
            echo "  1. 检查网络连接: ping -c 3 8.8.8.8"
            echo "  2. 手动下载并安装（推荐）:"
            echo "     - 在电脑上下载: $DOWNLOAD_URL"
            echo "     - 保存到: D:\\git\\life-coach\\deploy\\$PACKAGE"
            echo "     - 运行: .\\deploy.ps1 (会自动传输)"
            echo "     - 或手动传输: scp $PACKAGE cmit@192.168.1.28:~/LifeCoach/deploy/"
            echo "     - 重新运行此脚本"
            echo "  3. 查看详细文档: ~/LifeCoach/deploy/setup-resilio-manual.md"
            echo ""
            exit 1
        fi
        
        echo "  ✓ 下载完成"
    fi
    
    echo "  正在解压..."
    if ! tar -xzf "$PACKAGE" 2>&1; then
        echo "✗ 解压失败，文件可能损坏"
        rm -f "$PACKAGE"
        exit 1
    fi
    
    rm "$PACKAGE"
    chmod +x rslsync
    
    if [ ! -f "rslsync" ]; then
        echo "✗ 未找到 rslsync 可执行文件"
        exit 1
    fi
    
    echo "  ✓ 安装完成"
else
    echo "[3/6] Resilio Sync 已存在，跳过安装"
fi

# 创建配置文件
echo "[4/6] 创建配置文件..."

# 确保数据目录存在
mkdir -p "$INSTALL_DIR/data"

cat > "$INSTALL_DIR/sync.conf" <<EOF
{
  "storage_path": "$INSTALL_DIR/data",
  "pid_file": "$INSTALL_DIR/sync.pid",
  "webui": {
    "listen": "0.0.0.0:$WEB_PORT",
    "login": "$RESILIO_USERNAME",
    "password": "$RESILIO_PASSWORD"
  }
}
EOF

echo "  ✓ 配置文件已创建"
echo "  用户名: $RESILIO_USERNAME"
echo "  密码: $RESILIO_PASSWORD"
echo ""
echo "  重要：请保存上述密码，或通过环境变量重新设置："
echo "  export RESILIO_USERNAME=your_username"
echo "  export RESILIO_PASSWORD=your_password"

# 创建 systemd 服务
echo "[5/6] 配置系统服务..."
sudo tee /etc/systemd/system/resilio-sync.service > /dev/null <<EOF
[Unit]
Description=Resilio Sync Service
After=network.target

[Service]
Type=simple
User=$USER
ExecStart=$INSTALL_DIR/rslsync --nodaemon --config $INSTALL_DIR/sync.conf
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 启动服务
echo "[6/6] 启动 Resilio Sync..."
sudo systemctl daemon-reload
sudo systemctl enable resilio-sync
sudo systemctl restart resilio-sync

# 等待服务启动
sleep 3

if sudo systemctl is-active --quiet resilio-sync; then
    echo "  ✓ 服务已启动"
else
    echo "  ✗ 服务启动失败，查看日志："
    sudo journalctl -u resilio-sync -n 20
    exit 1
fi

echo ""
echo "========================================"
echo "安装完成！"
echo "========================================"
echo ""
echo "Web 管理界面: http://$(hostname -I | awk '{print $1}'):$WEB_PORT"
echo "或: http://192.168.1.28:$WEB_PORT"
echo ""
echo "下一步操作："
echo "1. 在浏览器打开上述地址"
echo "2. 点击「添加文件夹」"
echo "3. 选择文件夹路径: $SYNC_DIR"
echo "4. 复制生成的密钥（用于添加其他设备）"
echo ""
echo "常用命令:"
echo "  查看状态: sudo systemctl status resilio-sync"
echo "  查看日志: sudo journalctl -u resilio-sync -f"
echo "  重启服务: sudo systemctl restart resilio-sync"
echo "  停止服务: sudo systemctl stop resilio-sync"
echo ""
