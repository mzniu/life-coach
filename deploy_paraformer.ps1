# Paraformer ASR 模型部署脚本

Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "Sherpa-ONNX Paraformer ASR 模型部署" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

# 设置路径
$ProjectRoot = "d:\git\life-coach"
$ModelsDir = Join-Path $ProjectRoot "models\sherpa"
$ArchiveFile = Join-Path $ModelsDir "paraformer.tar.bz2"
$TempExtractDir = Join-Path $ModelsDir "temp_extract"
$TargetDir = Join-Path $ModelsDir "paraformer"

# 步骤 1: 检查归档文件
Write-Host "[1/5] 检查下载的归档文件..." -ForegroundColor Yellow
if (-Not (Test-Path $ArchiveFile)) {
    Write-Host "✗ 归档文件不存在: $ArchiveFile" -ForegroundColor Red
    Write-Host "请先运行下载命令：" -ForegroundColor Red
    Write-Host 'Invoke-WebRequest -Uri "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-streaming-paraformer-bilingual-zh-en.tar.bz2" -OutFile "paraformer.tar.bz2"' -ForegroundColor Yellow
    exit 1
}

$FileSize = (Get-Item $ArchiveFile).Length / 1MB
Write-Host "✓ 归档文件存在: $ArchiveFile" -ForegroundColor Green
Write-Host "  大小: $([math]::Round($FileSize, 2)) MB" -ForegroundColor Green

if ($FileSize -lt 40) {
    Write-Host "✗ 文件大小异常（预期 ~45-50MB），可能下载未完成" -ForegroundColor Red
    exit 1
}

# 步骤 2: 创建临时解压目录
Write-Host ""
Write-Host "[2/5] 准备解压目录..." -ForegroundColor Yellow
if (Test-Path $TempExtractDir) {
    Write-Host "  清理旧的临时目录..." -ForegroundColor Gray
    Remove-Item -Path $TempExtractDir -Recurse -Force
}
New-Item -ItemType Directory -Path $TempExtractDir -Force | Out-Null
Write-Host "✓ 临时目录创建: $TempExtractDir" -ForegroundColor Green

# 步骤 3: 解压归档文件 (.tar.bz2)
Write-Host ""
Write-Host "[3/5] 解压归档文件（.tar.bz2）..." -ForegroundColor Yellow
Write-Host "  这可能需要几分钟，请耐心等待..." -ForegroundColor Gray

try {
    # 检查是否有 tar 命令（Windows 10 1803+ 内置）
    $hasTar = Get-Command tar -ErrorAction SilentlyContinue
    
    if ($hasTar) {
        Write-Host "  使用系统 tar 命令解压..." -ForegroundColor Gray
        cd $ModelsDir
        tar -xjf $ArchiveFile -C $TempExtractDir
        if ($LASTEXITCODE -ne 0) {
            throw "tar 解压失败，退出码: $LASTEXITCODE"
        }
    } else {
        # 备用方案：使用 7-Zip（如果已安装）
        $7zipPaths = @(
            "C:\Program Files\7-Zip\7z.exe",
            "C:\Program Files (x86)\7-Zip\7z.exe",
            "$env:ProgramFiles\7-Zip\7z.exe",
            "$env:ProgramW6432\7-Zip\7z.exe"
        )
        
        $7zip = $null
        foreach ($path in $7zipPaths) {
            if (Test-Path $path) {
                $7zip = $path
                break
            }
        }
        
        if ($7zip) {
            Write-Host "  使用 7-Zip 解压..." -ForegroundColor Gray
            & $7zip x $ArchiveFile -o"$TempExtractDir" -y
            # 如果是 .tar 文件，再解压一次
            $tarFile = Get-ChildItem -Path $TempExtractDir -Filter "*.tar" | Select-Object -First 1
            if ($tarFile) {
                & $7zip x $tarFile.FullName -o"$TempExtractDir" -y
                Remove-Item $tarFile.FullName -Force
            }
        } else {
            throw "未找到解压工具（tar 或 7-Zip）"
        }
    }
    
    Write-Host "✓ 解压完成" -ForegroundColor Green
} catch {
    Write-Host "✗ 解压失败: $_" -ForegroundColor Red
    Write-Host "请确保已安装 tar (Windows 10 1803+) 或 7-Zip" -ForegroundColor Red
    exit 1
}

# 步骤 4: 查找并移动模型文件
Write-Host ""
Write-Host "[4/5] 组织模型文件..." -ForegroundColor Yellow

# 查找解压出的目录
$ExtractedDirs = Get-ChildItem -Path $TempExtractDir -Directory
if ($ExtractedDirs.Count -eq 0) {
    Write-Host "✗ 未找到解压的模型目录" -ForegroundColor Red
    exit 1
}

$SourceDir = $ExtractedDirs[0].FullName
Write-Host "  模型源目录: $SourceDir" -ForegroundColor Gray

# 列出文件
Write-Host "  模型文件列表:" -ForegroundColor Gray
Get-ChildItem -Path $SourceDir -File | ForEach-Object {
    $size = $_.Length / 1KB
    Write-Host "    - $($_.Name) ($([math]::Round($size, 2)) KB)" -ForegroundColor Gray
}

# 移动到目标目录
if (Test-Path $TargetDir) {
    Write-Host "  清理旧的模型目录..." -ForegroundColor Gray
    Remove-Item -Path $TargetDir -Recurse -Force
}

Move-Item -Path $SourceDir -Destination $TargetDir -Force
Write-Host "✓ 模型文件已安装到: $TargetDir" -ForegroundColor Green

# 步骤 5: 清理
Write-Host ""
Write-Host "[5/5] 清理临时文件..." -ForegroundColor Yellow
Remove-Item -Path $TempExtractDir -Recurse -Force
Write-Host "✓ 临时文件已清理" -ForegroundColor Green

# 验证模型文件
Write-Host ""
Write-Host "验证模型文件..." -ForegroundColor Cyan
$RequiredFiles = @("encoder.int8.onnx", "decoder.int8.onnx", "tokens.txt")
$AllFilesExist = $true

foreach ($file in $RequiredFiles) {
    $filePath = Join-Path $TargetDir $file
    if (Test-Path $filePath) {
        Write-Host "  ✓ $file" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $file (未找到)" -ForegroundColor Red
        $AllFilesExist = $false
    }
}

# 检查可能的替代文件名
if (-Not $AllFilesExist) {
    Write-Host ""
    Write-Host "检查替代文件名..." -ForegroundColor Yellow
    Get-ChildItem -Path $TargetDir -Filter "*.onnx" | ForEach-Object {
        Write-Host "  找到: $($_.Name)" -ForegroundColor Gray
    }
}

# 完成
Write-Host ""
Write-Host "=" * 60 -ForegroundColor Cyan
if ($AllFilesExist) {
    Write-Host "✓ 部署完成！" -ForegroundColor Green
    Write-Host ""
    Write-Host "下一步：" -ForegroundColor Cyan
    Write-Host "  1. 测试 ASR: python test_sherpa_asr.py" -ForegroundColor Yellow
    Write-Host "  2. 切换引擎: `$env:ASR_ENGINE='sherpa'" -ForegroundColor Yellow
    Write-Host "  3. 启动服务: python src/main_real.py" -ForegroundColor Yellow
} else {
    Write-Host "⚠ 部署完成，但部分文件缺失" -ForegroundColor Yellow
    Write-Host "  请检查模型文件是否正确解压" -ForegroundColor Yellow
}
Write-Host "=" * 60 -ForegroundColor Cyan
