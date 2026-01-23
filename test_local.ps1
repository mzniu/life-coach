# Life Coach 本地测试启动脚本（使用虚拟环境）
# Windows PowerShell

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Life Coach - 本地测试环境"
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查虚拟环境
if (-not (Test-Path "venv")) {
    Write-Host "❌ 虚拟环境未找到" -ForegroundColor Red
    Write-Host "请先运行: .\setup_venv.ps1" -ForegroundColor Yellow
    exit 1
}

# 激活虚拟环境
Write-Host "[1/4] 激活虚拟环境..." -ForegroundColor Green
& .\venv\Scripts\Activate.ps1
Write-Host "✓ 虚拟环境已激活" -ForegroundColor Green
Write-Host ""

# 检查依赖
Write-Host "[2/4] 检查依赖..." -ForegroundColor Green
$flaskInstalled = pip show Flask 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "依赖未安装，开始安装..." -ForegroundColor Yellow
    pip install -r requirements-local.txt --quiet
}
Write-Host "✓ 依赖检查完成" -ForegroundColor Green
Write-Host ""

# 创建必要目录
Write-Host "[3/4] 创建存储目录..." -ForegroundColor Green
New-Item -ItemType Directory -Force -Path "recordings" | Out-Null
New-Item -ItemType Directory -Force -Path "logs" | Out-Null
New-Item -ItemType Directory -Force -Path "tests\test_recordings" | Out-Null
Write-Host "✓ 目录创建完成" -ForegroundColor Green
Write-Host ""

# 运行核心测试
Write-Host "[4/4] 运行核心测试..." -ForegroundColor Green
python tests\test_core.py
$testResult = $LASTEXITCODE
Write-Host ""

if ($testResult -eq 0) {
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "✅ 测试通过，环境准备就绪！" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "📌 下一步:" -ForegroundColor Yellow
    Write-Host "  1. 启动服务:"
    Write-Host "     python main.py"
    Write-Host ""
    Write-Host "  2. 打开浏览器访问:"
    Write-Host "     http://localhost:5000"
    Write-Host ""
    Write-Host "  3. 运行API测试（需先启动服务）:"
    Write-Host "     python tests\test_api.py"
    Write-Host ""
    Write-Host "  4. 退出虚拟环境:"
    Write-Host "     deactivate"
    Write-Host ""
} else {
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "❌ 测试失败，请检查错误信息" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    exit 1
}
