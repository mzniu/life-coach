#!/bin/bash
# Life Coach 启动脚本 - 自动配置音频设备

set -e

# 获取项目根目录（start.sh 在 deploy/ 子目录中）
PROJECT_DIR="/home/cmit/LifeCoach"

echo "======================================"
echo "Life Coach 启动检查"
echo "======================================"

# 1. 自动检测并配置 USB 麦克风
echo ""
echo "[1/3] 检测音频设备..."

if command -v arecord >/dev/null 2>&1; then
    # 检查是否有 USB 音频设备
    if arecord -l 2>/dev/null | grep -q "USB"; then
        USB_CARD=$(arecord -l 2>/dev/null | grep "USB" | head -1 | sed -n 's/card \([0-9]\).*/\1/p')
        
        if [ -n "$USB_CARD" ]; then
            echo "  ✓ 检测到 USB 音频设备 (card $USB_CARD)"
            
            # 检查当前配置
            CURRENT_CARD=""
            if [ -f ~/.asoundrc ]; then
                CURRENT_CARD=$(grep "defaults.pcm.card" ~/.asoundrc 2>/dev/null | awk '{print $2}')
            fi
            
            if [ "$CURRENT_CARD" != "$USB_CARD" ]; then
                echo "  → 更新音频配置为 card $USB_CARD"
                echo "defaults.pcm.card $USB_CARD" > ~/.asoundrc
                echo "defaults.ctl.card $USB_CARD" >> ~/.asoundrc
                echo "  ✓ 音频设备配置已更新"
            else
                echo "  ✓ 音频设备配置正确"
            fi
            
            # 设置麦克风音量为 100%
            if command -v amixer >/dev/null 2>&1; then
                echo "  → 设置麦克风音量..."
                amixer -c $USB_CARD sset Mic 100% >/dev/null 2>&1 && echo "  ✓ 麦克风音量已设置为 100%" || echo "  ⚠ 无法设置麦克风音量"
            fi
        else
            echo "  ⚠ 检测到 USB 音频但无法获取卡号"
        fi
    else
        echo "  → 未检测到 USB 音频设备，使用系统默认"
        # 清除可能存在的配置，使用系统默认
        if [ -f ~/.asoundrc ]; then
            rm -f ~/.asoundrc
            echo "  ✓ 已清除自定义音频配置"
        fi
    fi
else
    echo "  ⚠ arecord 命令不可用，跳过音频检测"
fi

# 2. 检查虚拟环境
echo ""
echo "[2/3] 检查 Python 环境..."
cd "$PROJECT_DIR"

if [ ! -d "venv" ]; then
    echo "  ✗ 虚拟环境不存在"
    echo "  请先运行: cd $PROJECT_DIR && ./deploy/setup_pi.sh"
    exit 1
fi

if ! source venv/bin/activate 2>/dev/null; then
    echo "  ✗ 虚拟环境损坏"
    echo "  请重新运行: cd $PROJECT_DIR && ./deploy/setup_pi.sh"
    exit 1
fi

echo "  ✓ Python 环境正常"

# 3. 检查必要目录
echo ""
echo "[3/3] 检查数据目录..."
mkdir -p recordings voiceprints models logs
echo "  ✓ 数据目录已就绪"

echo ""
echo "======================================"
echo "启动 Life Coach 服务..."
echo "======================================"
echo ""

# 启动主程序
exec python main.py
