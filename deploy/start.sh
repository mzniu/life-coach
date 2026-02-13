#!/bin/bash
# Life Coach 启动脚本 - 自动配置音频设备

set -e

# 获取项目根目录（动态获取当前用户）
PROJECT_DIR="$HOME/LifeCoach"

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

# 3. 加载环境变量
echo ""
echo "[3/4] 加载环境配置..."
if [ -f ".env" ]; then
    # 导出.env中的环境变量
    set -a
    source .env
    set +a
    echo "  ✓ 环境变量已加载"
else
    echo "  → 未找到 .env 文件，使用默认配置"
fi

# 4. 检查必要目录
echo ""
echo "[4/5] 检查数据目录..."
mkdir -p recordings voiceprints models logs
echo "  ✓ 数据目录已就绪"

# 5. 预热文本纠错器（如果启用）
echo ""
echo "[5/5] 预热文本纠错器..."
if [ "${TEXT_CORRECTION_ENABLED}" = "true" ]; then
    if [ "${TEXT_CORRECTOR_ENGINE}" = "macro-correct" ]; then
        echo "  → macro-correct 引擎需要预热..."
        
        # 设置使用国内镜像
        export HF_ENDPOINT="https://hf-mirror.com"
        
        # 检查是否已预热过（通过检查缓存目录）
        CACHE_DIR="${HOME}/.cache/huggingface/hub"
        if [ -d "$CACHE_DIR" ] && [ "$(ls -A $CACHE_DIR 2>/dev/null)" ]; then
            echo "  ✓ 模型已缓存，跳过预热"
        else
            echo "  → 首次运行，下载模型（约 20MB，需要 30-60 秒）..."
            if python deploy/warmup_corrector.py; then
                echo "  ✓ 模型预热成功"
            else
                echo "  ⚠ 模型预热失败，首次请求可能较慢"
            fi
        fi
    else
        echo "  → 使用 ${TEXT_CORRECTOR_ENGINE} 引擎，无需预热"
    fi
else
    echo "  → 文本纠错未启用，跳过预热"
fi

echo ""
echo "======================================"
echo "启动 Life Coach 服务..."
echo "======================================"
echo ""

# 设置使用国内镜像（用于运行时下载模型）
export HF_ENDPOINT="https://hf-mirror.com"

# 添加系统 Python 路径（用于地瓜派RDK的Hobot.GPIO）
export PYTHONPATH="/usr/local/lib/python3.10/dist-packages/Hobot.GPIO-0.0.2-py3.10.egg:$PYTHONPATH"

# 启动主程序
exec python main.py
