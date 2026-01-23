# Life Coach 快速部署脚本
# 用法: .\deploy.ps1

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "Life Coach 快速部署" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# 检查 deploy 目录
if (-not (Test-Path ".\deploy\deploy-once.ps1")) {
    Write-Host "错误: 找不到 deploy 目录或部署脚本" -ForegroundColor Red
    Write-Host "请确保在项目根目录运行此脚本" -ForegroundColor Yellow
    exit 1
}

Write-Host "正在启动自动部署..." -ForegroundColor Green
Write-Host ""

# 调用实际的部署脚本
& ".\deploy\deploy-once.ps1"
