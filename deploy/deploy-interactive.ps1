# Life Coach 交互式部署脚本（简化版）
# 使用方法: .\deploy-interactive.ps1 [-IdentityFile <path>]

param(
    [string]$IdentityFile = ""
)

# 加载配置文件
$ConfigFile = "$PSScriptRoot\config.ps1"
if (Test-Path $ConfigFile) {
    . $ConfigFile
} else {
    # 默认配置
    $PI_HOST = "192.168.1.100"
    $PI_USER = "pi"
    $PI_PATH = "/home/pi/LifeCoach"
}

$SSH_OPTS = @()
if ($IdentityFile -ne "" -and (Test-Path $IdentityFile)) {
    $SSH_OPTS += "-i"
    $SSH_OPTS += "$IdentityFile"
}

Write-Host "=====================================" -ForegroundColor Green
Write-Host "Life Coach 树莓派部署工具（交互式）" -ForegroundColor Green
Write-Host "目标: $PI_USER@$PI_HOST" -ForegroundColor Green
if ($IdentityFile) {
    Write-Host "SSH密钥: $IdentityFile" -ForegroundColor Cyan
}

# 测试SSH连接
Write-Host "[1/7] 测试SSH连接..." -ForegroundColor Cyan
Write-Host "执行: ssh $PI_USER@$PI_HOST 'echo Connection OK'" -ForegroundColor Gray

# 使用 splatting 或直接传参
$testResult = ssh $SSH_OPTS -o ConnectTimeout=5 "$PI_USER@$PI_HOST" "echo 'Connection OK'" 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "错误: 无法连接到树莓派" -ForegroundColor Red
    Write-Host "请检查:" -ForegroundColor Yellow
    Write-Host "  1. 树莓派IP: $PI_HOST 是否正确" -ForegroundColor Yellow
    Write-Host "  2. SSH服务是否已启动" -ForegroundColor Yellow
    Write-Host "  3. 防火墙是否允许SSH连接" -ForegroundColor Yellow
    exit 1
}

Write-Host "  ✓ SSH连接成功" -ForegroundColor Green
Write-Host ""

# 创建远程目录
Write-Host "[2/7] 创建远程目录..." -ForegroundColor Cyan
ssh $SSH_OPTS "$PI_USER@$PI_HOST" "mkdir -p $PI_PATH"
Write-Host "  ✓ 目录已创建: $PI_PATH" -ForegroundColor Green
Write-Host ""

# 传输文件
Write-Host "[3/7] 传输项目文件..." -ForegroundColor Cyan

# 获取项目根目录（deploy 的上级目录）
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Write-Host "  传输主程序..." -ForegroundColor Gray
scp $SSH_OPTS "$ProjectRoot\main.py" "${PI_USER}@${PI_HOST}:${PI_PATH}/"

Write-Host "  传输配置文件..." -ForegroundColor Gray
scp $SSH_OPTS "$PSScriptRoot\requirements-pi.txt" "${PI_USER}@${PI_HOST}:${PI_PATH}/"
scp $SSH_OPTS "$PSScriptRoot\setup_pi.sh" "${PI_USER}@${PI_HOST}:${PI_PATH}/"
scp $SSH_OPTS "$PSScriptRoot\lifecoach.service" "${PI_USER}@${PI_HOST}:${PI_PATH}/"

Write-Host "  传输src目录..." -ForegroundColor Gray
scp $SSH_OPTS -r "$ProjectRoot\src" "${PI_USER}@${PI_HOST}:${PI_PATH}/"

Write-Host "  传输static目录..." -ForegroundColor Gray
scp $SSH_OPTS -r "$ProjectRoot\static" "${PI_USER}@${PI_HOST}:${PI_PATH}/"

if (Test-Path "$ProjectRoot\models") {
    Write-Host "  传输models目录 (Whisper模型)..." -ForegroundColor Gray
    scp $SSH_OPTS -r "$ProjectRoot\models" "${PI_USER}@${PI_HOST}:${PI_PATH}/"
}

# 传输 deploy 目录（包含 Resilio Sync 脚本）
Write-Host "  传输deploy目录..." -ForegroundColor Gray
scp $SSH_OPTS -r "$PSScriptRoot" "${PI_USER}@${PI_HOST}:${PI_PATH}/"

Write-Host "  ✓ 文件传输完成" -ForegroundColor Green
Write-Host ""

# 清理Python缓存
Write-Host "  清理Python字节码缓存..." -ForegroundColor Gray
ssh $SSH_OPTS "$PI_USER@$PI_HOST" "cd $PI_PATH && find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null; find . -type f -name '*.pyc' -delete 2>/dev/null"
Write-Host "  ✓ Python缓存已清理" -ForegroundColor Green
Write-Host ""

# 执行安装脚本
Write-Host "[4/7] 安装系统依赖和Python包..." -ForegroundColor Cyan
Write-Host "  这可能需要5-10分钟，请耐心等待..." -ForegroundColor Yellow
ssh $SSH_OPTS "$PI_USER@$PI_HOST" "cd $PI_PATH && chmod +x setup_pi.sh && ./setup_pi.sh"

if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ 依赖安装完成" -ForegroundColor Green
} else {
    Write-Host "  警告: 安装过程中可能有错误，请检查日志" -ForegroundColor Yellow
}
Write-Host ""

# 配置systemd服务
Write-Host "[5/7] 配置系统服务..." -ForegroundColor Cyan
ssh $SSH_OPTS "$PI_USER@$PI_HOST" "cd $PI_PATH && sudo cp lifecoach.service /etc/systemd/system/ && sudo systemctl daemon-reload && sudo systemctl enable lifecoach.service"
Write-Host "  ✓ 服务已配置" -ForegroundColor Green
Write-Host ""

# 启动服务
Write-Host "[6/7] 启动Life Coach服务..." -ForegroundColor Cyan
Write-Host "  清理Python缓存并重启服务..." -ForegroundColor Gray
ssh $SSH_OPTS "$PI_USER@$PI_HOST" "cd $PI_PATH && find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null; find . -type f -name '*.pyc' -delete 2>/dev/null; sudo systemctl restart lifecoach.service"
Start-Sleep -Seconds 3
Write-Host "  ✓ 服务已启动" -ForegroundColor Green
Write-Host ""

# 检查服务状态
Write-Host "[7/7] 检查服务状态..." -ForegroundColor Cyan
ssh $SSH_OPTS "$PI_USER@$PI_HOST" "sudo systemctl status lifecoach.service --no-pager -l"
Write-Host ""

Write-Host "=====================================" -ForegroundColor Green
Write-Host "部署完成！" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green
Write-Host ""
Write-Host "访问地址: http://$PI_HOST`:5000" -ForegroundColor Cyan
Write-Host "声纹管理: http://$PI_HOST`:5000/static/voiceprint.html" -ForegroundColor Cyan
Write-Host ""
Write-Host "常用命令:" -ForegroundColor Yellow
Write-Host "  查看日志: ssh $PI_USER@$PI_HOST 'journalctl -u lifecoach -f'" -ForegroundColor Gray
Write-Host "  重启服务: ssh $PI_USER@$PI_HOST 'sudo systemctl restart lifecoach'" -ForegroundColor Gray
Write-Host "  停止服务: ssh $PI_USER@$PI_HOST 'sudo systemctl stop lifecoach'" -ForegroundColor Gray
Write-Host ""
