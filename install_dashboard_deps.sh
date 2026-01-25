#!/bin/bash
# 安装仪表盘所需的依赖包

echo "正在安装仪表盘功能所需的依赖..."

# 安装psutil用于系统监控
echo "1. 安装psutil..."
pip3 install psutil

echo "依赖安装完成！"
echo "说明："
echo "  - psutil: 用于获取CPU温度、内存使用率等系统信息"
echo ""
echo "现在可以运行 python3 main.py 来查看仪表盘了"
