#!/bin/bash
# 树莓派环境安装脚本

set -e

SETUP_MARKER=".setup_complete"

echo "======================================"
echo "Life Coach 树莓派环境配置"
echo "======================================"
echo ""

# 检测系统
if [ -f /proc/cpuinfo ]; then
    if grep -q "Raspberry" /proc/cpuinfo || grep -q "BCM" /proc/cpuinfo; then
        echo "✓ 检测到树莓派设备"
    else
        echo "⚠ 警告: 可能不是树莓派设备"
    fi
fi

# 检查是否已经完整安装过
if [ -f "$SETUP_MARKER" ]; then
    echo "✓ 检测到已完成初始化标记"
    echo "如需重新安装，请删除 $SETUP_MARKER 文件"
    echo ""
    
    # 只检查关键组件
    if [ ! -d "venv" ]; then
        echo "⚠ 虚拟环境缺失，重新创建..."
    elif ! source venv/bin/activate 2>/dev/null; then
        echo "⚠ 虚拟环境损坏，重新创建..."
        rm -rf venv
    else
        echo "✓ 虚拟环境正常"
        
        # 快速检查依赖
        if ! python3 -c "import flask, faster_whisper, sounddevice" 2>/dev/null; then
            echo "⚠ Python依赖缺失，将重新安装..."
        else
            echo "✓ Python依赖正常"
            echo ""
            echo "环境检查完成，可以直接运行服务！"
            exit 0
        fi
    fi
    echo ""
fi

# 更新系统包列表
echo "[1/6] 更新系统包列表..."
sudo apt-get update -qq

# 安装系统依赖（检查是否已安装）
echo "[2/6] 检查系统依赖..."
PACKAGES_TO_INSTALL=""
for pkg in python3 python3-pip python3-venv python3-dev portaudio19-dev libsndfile1 ffmpeg git curl libopenblas-dev; do
    if ! dpkg -s $pkg >/dev/null 2>&1; then
        PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL $pkg"
    fi
done

if [ -n "$PACKAGES_TO_INSTALL" ]; then
    echo "  需要安装:$PACKAGES_TO_INSTALL"
    sudo apt-get install -y -qq $PACKAGES_TO_INSTALL
    echo "  ✓ 系统依赖安装完成"
else
    echo "  ✓ 系统依赖已全部安装"
fi

# 创建Python虚拟环境
echo "[3/6] 创建Python虚拟环境..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "  ✓ 虚拟环境已创建"
else
    echo "  ✓ 虚拟环境已存在"
fi

# 激活虚拟环境并安装Python依赖
echo "[4/6] 安装Python依赖..."
source venv/bin/activate

# 升级pip
pip install --upgrade pip -q -i https://mirrors.aliyun.com/pypi/simple/

# 安装依赖（排除 llama-cpp-python）
if [ -f "requirements-pi.txt" ]; then
    # 先安装除 llama-cpp-python 以外的依赖
    grep -v "llama-cpp-python" requirements-pi.txt > /tmp/requirements_temp.txt
    pip install -r /tmp/requirements_temp.txt -q -i https://mirrors.aliyun.com/pypi/simple/
    
    # 单独安装 llama-cpp-python，使用 ARM NEON 优化
    if grep -q "llama-cpp-python" requirements-pi.txt; then
        echo "  → 编译安装 llama-cpp-python（ARM 优化）..."
        CMAKE_ARGS="-DLLAMA_BLAS=ON -DLLAMA_BLAS_VENDOR=OpenBLAS" \
        pip install llama-cpp-python==0.2.89 --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ \
        || echo "  ⚠ llama-cpp-python 安装失败，文本纠错功能将不可用"
    fi
    
    echo "  ✓ Python依赖安装完成"
else
    echo "  ⚠ 未找到 requirements-pi.txt，跳过"
fi

# 下载Whisper模型
echo "[5/6] 检查Whisper模型..."

# 检查本地models目录是否有模型
if [ -d "models" ] && [ "$(ls -A models 2>/dev/null)" ]; then
    echo "  ✓ 检测到本地模型文件，跳过下载"
else
    echo "  本地模型不存在，开始下载..."
    # 设置HF镜像加速
    export HF_ENDPOINT=https://hf-mirror.com
    python3 -c "
import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
from faster_whisper import WhisperModel
print('  正在下载tiny模型，请稍候...')
try:
    model = WhisperModel('tiny', device='cpu', compute_type='int8', download_root='models')
    print('  ✓ 模型下载完成')
except Exception as e:
    print(f'  ⚠ 模型下载失败: {e}')
    print('  首次运行时会自动下载')
" 2>/dev/null || echo "  ⚠ 模型下载失败，首次运行时会自动下载"
fi

# 创建数据目录
echo "[6/6] 创建数据目录..."
mkdir -p recordings
mkdir -p voiceprints
mkdir -p models
mkdir -p logs

echo "  ✓ 数据目录已创建"

# 配置 USB 麦克风为默认音频设备
echo ""
echo "配置音频设备..."
if arecord -l 2>/dev/null | grep -q "USB"; then
    echo "  检测到 USB 音频设备"
    USB_CARD=$(arecord -l 2>/dev/null | grep "USB" | head -1 | sed -n 's/card \([0-9]\).*/\1/p')
    if [ -n "$USB_CARD" ]; then
        echo "  配置 USB 麦克风 (card $USB_CARD) 为默认录音设备..."
        echo "defaults.pcm.card $USB_CARD" > ~/.asoundrc
        echo "defaults.ctl.card $USB_CARD" >> ~/.asoundrc
        echo "  ✓ USB 麦克风已设置为默认设备"
    else
        echo "  ⚠ 无法确定 USB 音频卡号，跳过配置"
    fi
else
    echo "  未检测到 USB 音频设备，使用系统默认"
fi

# 设置权限
chmod +x deploy/start.sh 2>/dev/null || true
chmod +x main.py 2>/dev/null || true

# 创建完成标记
touch "$SETUP_MARKER"
echo "  ✓ 创建初始化完成标记"

echo ""
echo "======================================"
echo "环境配置完成！"
echo "======================================"
echo ""
echo "测试运行:"
echo "  cd $(pwd)"
echo "  source venv/bin/activate"
echo "  python main.py"
echo ""
echo "下次运行此脚本时将自动跳过已完成的步骤"
echo ""
