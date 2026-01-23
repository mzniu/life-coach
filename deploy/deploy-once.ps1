# 一次输入密码完成部署（先配置SSH免密）
# 用法: .\deploy-once.ps1

# 加载配置文件
$ConfigFile = "$PSScriptRoot\config.ps1"
if (Test-Path $ConfigFile) {
    . $ConfigFile
    Write-Host "已加载配置文件: config.ps1" -ForegroundColor Green
} else {
    Write-Host "警告: 未找到 config.ps1，使用默认配置" -ForegroundColor Yellow
    Write-Host "请复制 config.example.ps1 为 config.ps1 并修改配置" -ForegroundColor Yellow
    
    # 默认配置
    $PI_HOST = "192.168.1.100"
    $PI_USER = "pi"
    $PI_PATH = "/home/pi/LifeCoach"
}

Write-Host "=====================================" -ForegroundColor Green
Write-Host "Life Coach 一键部署（仅需一次密码）" -ForegroundColor Green
Write-Host "目标: $PI_USER@$PI_HOST" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green

# 1) 生成SSH密钥（如果不存在）
$sshDir = "$env:USERPROFILE\.ssh"
$keyPath = "$sshDir\id_rsa"
$pubPath = "$keyPath.pub"
$sshKeygen = "$env:WINDIR\System32\OpenSSH\ssh-keygen.exe"

if (-not (Test-Path $sshDir)) {
    New-Item -ItemType Directory -Path $sshDir | Out-Null
}

if (-not (Test-Path $keyPath)) {
    Write-Host "[1/3] 生成SSH密钥..." -ForegroundColor Cyan
    if (-not (Test-Path $sshKeygen)) {
        Write-Host "错误: 未找到 OpenSSH 客户端 (ssh-keygen)" -ForegroundColor Red
        Write-Host "请安装 Windows OpenSSH 客户端后重试" -ForegroundColor Yellow
        exit 1
    }
    # 使用 Start-Process 和参数字符串来避免解析问题
    $argStr = "-q -t ed25519 -N `"`" -f `"$keyPath`""
    $proc = Start-Process -FilePath $sshKeygen -ArgumentList $argStr -NoNewWindow -Wait -PassThru
    
    if ($proc.ExitCode -ne 0 -or -not (Test-Path $pubPath)) {
        Write-Host "警告: ed25519 生成失败，尝试 RSA" -ForegroundColor Yellow
        $argStrRsa = "-q -t rsa -b 2048 -N `"`" -f `"$keyPath`""
        $proc2 = Start-Process -FilePath $sshKeygen -ArgumentList $argStrRsa -NoNewWindow -Wait -PassThru
        
        if ($proc2.ExitCode -ne 0 -or -not (Test-Path $pubPath)) {
            Write-Host "错误: SSH密钥生成失败" -ForegroundColor Red
            Write-Host "调试信息: $sshKeygen $argStrRsa" -ForegroundColor Gray
            exit 1
        }
    }
    Write-Host "  ✓ SSH密钥已生成" -ForegroundColor Green
} else {
    Write-Host "[1/3] SSH密钥已存在，跳过生成" -ForegroundColor Green
}

# 1.5) 检查是否已经免密
Write-Host "检查 SSH 连接状态..." -ForegroundColor Cyan
ssh -i "$keyPath" -o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=accept-new "$PI_USER@$PI_HOST" "echo OK" | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ 检测到已配置免密登录，跳过公钥写入" -ForegroundColor Green
} else {
    # 2) 将公钥写入树莓派（需要输入一次密码）
    Write-Host "[2/3] 写入公钥到树莓派（会提示输入一次密码）..." -ForegroundColor Cyan
    Write-Host "执行: ssh $PI_USER@$PI_HOST 'mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys'" -ForegroundColor Gray
    if (-not (Test-Path $pubPath)) {
        Write-Host "错误: 未找到公钥文件 $pubPath" -ForegroundColor Red
        exit 1
    }

    Get-Content $pubPath | ssh "$PI_USER@$PI_HOST" "mkdir -p ~/.ssh && chmod 700 ~/.ssh && chmod g-w ~ && touch ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && echo '' >> ~/.ssh/authorized_keys && cat >> ~/.ssh/authorized_keys"

    if ($LASTEXITCODE -ne 0) {
        Write-Host "警告: 写入公钥时遇到错误，尝试使用 SCP 方式..." -ForegroundColor Yellow
        # 备选方案: 使用 SCP 传输 (可能需要第二次密码)
        scp "$pubPath" "${PI_USER}@${PI_HOST}:/tmp/tmp_key.pub"
        if ($LASTEXITCODE -eq 0) {
            ssh "${PI_USER}@${PI_HOST}" "mkdir -p ~/.ssh && chmod 700 ~/.ssh && chmod g-w ~ && touch ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && echo '' >> ~/.ssh/authorized_keys && cat /tmp/tmp_key.pub >> ~/.ssh/authorized_keys && rm /tmp/tmp_key.pub"
        } else {
            Write-Host "错误: 写入公钥失败，请检查密码或SSH连接" -ForegroundColor Red
            exit 1
        }
    }
    Write-Host "  ✓ 公钥写入成功" -ForegroundColor Green
}

# 3) 运行部署脚本（使用指定 IdentityFile）
Write-Host "[3/3] 开始免密部署..." -ForegroundColor Cyan
& "$PSScriptRoot\deploy-interactive.ps1" -IdentityFile "$keyPath"

