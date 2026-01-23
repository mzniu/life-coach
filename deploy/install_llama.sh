#!/bin/bash
# 安装 llama-cpp-python with OpenBLAS 优化

set -e

echo "开始安装 llama-cpp-python (OpenBLAS + ARM NEON)..."
echo "此过程需要约 10-15 分钟，请耐心等待..."
echo ""

cd ~/LifeCoach
source venv/bin/activate

export CMAKE_ARGS="-DLLAMA_BLAS=ON -DLLAMA_BLAS_VENDOR=OpenBLAS"

echo "开始编译安装..."
pip install llama-cpp-python==0.2.89 --no-cache-dir

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ llama-cpp-python 安装成功!"
    echo ""
    echo "验证安装:"
    python -c "from llama_cpp import Llama; print('导入成功!')"
else
    echo ""
    echo "✗ 安装失败，请检查错误信息"
    exit 1
fi
