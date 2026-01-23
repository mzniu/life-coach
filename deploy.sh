#!/bin/bash
# Life Coach 阶段0 一键部署脚本
# 支持 Raspberry Pi 4B/5 + Raspbian OS 12

set -e  # 遇到错误立即退出

echo "========================================"
echo "  Life Coach 部署脚本"
echo "  版本: 阶段0 - 最小MVP"
echo "========================================"
echo ""

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 工作目录
WORK_DIR="/home/pi/LifeCoach"

# 检查是否在树莓派上运行
if [ ! -f /proc/cpuinfo ] || ! grep -q "Raspberry Pi" /proc/cpuinfo; then
    echo -e "${YELLOW}[警告] 未检测到树莓派环境，部分功能可能不可用${NC}"
fi

# ==================== 步骤1: 更新系统 ====================
echo -e "${GREEN}[1/6] 更新系统软件包...${NC}"
sudo apt update
echo ""

# ==================== 步骤2: 安装系统依赖 ====================
echo -e "${GREEN}[2/6] 安装系统依赖...${NC}"
sudo apt install -y \
    python3-pip \
    python3-dev \
    portaudio19-dev \
    i2c-tools \
    libopenblas-dev \
    fonts-wqy-zenhei \
    git

echo ""

# ==================== 步骤3: 启用I2C接口 ====================
echo -e "${GREEN}[3/6] 启用I2C接口（OLED屏幕）...${NC}"
if ! grep -q "^dtparam=i2c_arm=on" /boot/config.txt; then
    echo "dtparam=i2c_arm=on" | sudo tee -a /boot/config.txt
    echo -e "${YELLOW}[提示] I2C已启用，需要重启生效${NC}"
else
    echo "[✓] I2C已启用"
fi

# 加载I2C内核模块
sudo modprobe i2c-dev || echo "[警告] I2C模块加载失败，可能需要重启"
echo ""

# ==================== 步骤4: 安装Python依赖 ====================
echo -e "${GREEN}[4/6] 安装Python依赖（可能需要10分钟）...${NC}"

# 升级pip
pip3 install --upgrade pip

# 安装依赖（使用清华镜像加速）
pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

echo ""

# ==================== 步骤5: 下载Whisper模型 ====================
echo -e "${GREEN}[5/6] 下载Whisper Tiny模型（约40MB）...${NC}"
python3 -c "
try:
    from whispercpp import Whisper
    print('[提示] 正在下载模型，首次运行需要3-5分钟...')
    w = Whisper('tiny')
    print('[✓] Whisper模型下载完成')
except Exception as e:
    print(f'[警告] Whisper模型下载失败: {e}')
    print('[提示] 可以稍后手动运行: python3 -c \"from whispercpp import Whisper; Whisper(\\\"tiny\\\")\"')
"
echo ""

# ==================== 步骤6: 创建必要目录 ====================
echo -e "${GREEN}[6/6] 创建存储目录...${NC}"
mkdir -p "$WORK_DIR/recordings"
mkdir -p "$WORK_DIR/logs"
mkdir -p "$WORK_DIR/models"

echo ""

# ==================== 权限设置 ====================
echo -e "${GREEN}[权限] 设置GPIO访问权限...${NC}"
if groups | grep -q gpio; then
    echo "[✓] 当前用户已在gpio组"
else
    sudo usermod -a -G gpio $USER
    echo -e "${YELLOW}[提示] GPIO权限已设置，需要重新登录生效${NC}"
fi

echo ""

# ==================== 硬件检测 ====================
echo -e "${GREEN}[硬件检测] 检查I2C设备...${NC}"
if command -v i2cdetect &> /dev/null; then
    echo "扫描I2C总线（应该看到地址 3c 和 3d）:"
    sudo i2cdetect -y 1 || echo "[警告] I2C扫描失败，请检查扩展板是否正确安装"
else
    echo "[跳过] i2c-tools未安装"
fi

echo ""

echo -e "${GREEN}[硬件检测] 检查音频设备...${NC}"
if command -v arecord &> /dev/null; then
    echo "音频录制设备列表:"
    arecord -l || echo "[警告] 未检测到录音设备，请插入USB麦克风"
else
    echo "[跳过] arecord命令不可用"
fi

echo ""

# ==================== 部署完成 ====================
echo "========================================"
echo -e "${GREEN}✅ 部署完成！${NC}"
echo "========================================"
echo ""
echo "📌 下一步:"
echo "  1. 插入扩展板（40PIN GPIO对齐插入）"
echo "  2. 连接USB麦克风"
echo "  3. 运行程序:"
echo ""
echo "     cd $WORK_DIR"
echo "     python3 main.py"
echo ""
echo "  4. 在浏览器访问: http://$(hostname -I | awk '{print $1}'):5000"
echo ""

# 检查是否需要重启
if ! grep -q "^dtparam=i2c_arm=on" /boot/config.txt 2>/dev/null || ! groups | grep -q gpio; then
    echo -e "${YELLOW}⚠️  需要重启以应用以下更改:${NC}"
    echo "   - I2C接口启用"
    echo "   - GPIO权限设置"
    echo ""
    echo "   执行: sudo reboot"
    echo ""
fi

echo "📖 完整文档: $WORK_DIR/README.md"
echo "🐛 问题反馈: <待补充>"
echo ""
