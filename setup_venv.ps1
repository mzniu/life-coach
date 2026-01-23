# Life Coach 虚拟环境设置脚本
# Windows PowerShell

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Life Coach - 虚拟环境设置"
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查Python
Write-Host "[1/3] 检查Python环境..." -ForegroundColor Green
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ 错误: 未找到Python" -ForegroundColor Red
    Write-Host "请先安装Python 3.8+: https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}
Write-Host ""

# 创建虚拟环境
Write-Host "[2/3] 创建虚拟环境..." -ForegroundColor Green
if (Test-Path "venv") {
    Write-Host "✓ 虚拟环境已存在" -ForegroundColor Yellow
} else {
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ 虚拟环境创建失败" -ForegroundColor Red
        exit 1
    }
    Write-Host "✓ 虚拟环境创建成功" -ForegroundColor Green
}
Write-Host ""

# 激活虚拟环境并安装依赖
Write-Host "[3/3] 安装依赖..." -ForegroundColor Green
& .\venv\Scripts\Activate.ps1
pip install -r requirements-local.txt --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 依赖安装失败" -ForegroundColor Red
    exit 1
}
Write-Host "✓ 依赖安装完成" -ForegroundColor Green
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "✅ 虚拟环境设置完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📌 下一步:" -ForegroundColor Yellow
Write-Host "  1. 激活虚拟环境:"
Write-Host "     .\venv\Scripts\Activate.ps1"
Write-Host ""
Write-Host "  2. 运行测试:"
Write-Host "     python tests\test_core.py"
Write-Host ""
Write-Host "  3. 启动服务:"
Write-Host "     python main.py"
Write-Host ""
Write-Host "  4. 退出虚拟环境:"
Write-Host "     deactivate"
Write-Host ""
