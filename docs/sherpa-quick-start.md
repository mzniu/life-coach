# Sherpa-ONNX ASR 快速启动指南

## 当前状态

✅ **已完成**：
- Silero VAD 集成（替换能量+FFT VAD）
- Paraformer ASR 代码封装（asr_sherpa.py）
- ASR 引擎双引擎架构（asr_engine_real.py）
- 测试脚本（test_sherpa_asr.py, compare_asr.py）
- 部署脚本（deploy_paraformer.ps1）
- 集成文档（docs/sherpa-asr-integration.md）

⏳ **进行中**：
- Paraformer 模型下载（~45-50MB）

❌ **待完成**：
- 模型解压和部署
- ASR 功能测试
- 性能对比（Whisper vs Paraformer）
- Raspberry Pi 部署

## 下一步操作

### 1. 等待模型下载完成

检查下载进度：
```powershell
# Windows
Get-Job

# 或检查文件大小
(Get-Item "models\sherpa\paraformer.tar.bz2").Length / 1MB
```

预期大小：~45-50MB

### 2. 部署模型

下载完成后运行部署脚本：
```powershell
cd d:\git\life-coach
.\deploy_paraformer.ps1
```

脚本将自动：
- 验证下载文件
- 解压 tar.bz2 归档
- 组织模型文件到 `models/sherpa/paraformer/`
- 验证必需文件

### 3. 测试 ASR

```bash
# 基本功能测试
python test_sherpa_asr.py

# 使用真实音频测试（需要 test_audio/ 目录）
python test_sherpa_asr.py --real-audio
```

### 4. 性能对比

如果有测试音频：
```bash
python compare_asr.py test_audio/sample.wav
```

### 5. 切换引擎

#### 使用 Paraformer
```powershell
# Windows
$env:ASR_ENGINE = "sherpa"
python src/main_real.py
```

```bash
# Linux / Raspberry Pi
export ASR_ENGINE=sherpa
python src/main_real.py
```

#### 使用 Whisper（默认）
```powershell
# Windows
$env:ASR_ENGINE = "whisper"
# 或删除变量
Remove-Item Env:\ASR_ENGINE
```

```bash
# Linux / Raspberry Pi
export ASR_ENGINE=whisper
# 或取消设置
unset ASR_ENGINE
```

### 6. 部署到 Raspberry Pi

**在 Windows 上打包模型**：
```powershell
cd d:\git\life-coach\models\sherpa
tar -czf paraformer.tar.gz paraformer/
```

**传输到 Pi**：
```bash
scp paraformer.tar.gz cmit@192.168.1.28:~/
scp src/asr_sherpa.py cmit@192.168.1.28:~/LifeCoach/src/
scp src/asr_engine_real.py cmit@192.168.1.28:~/LifeCoach/src/

ssh cmit@192.168.1.28
cd ~/LifeCoach/models/sherpa
tar -xzf ~/paraformer.tar.gz
```

**配置环境变量**（在 systemd 服务中）：
```bash
sudo vi /etc/systemd/system/lifecoach.service

# 添加
Environment="ASR_ENGINE=sherpa"

sudo systemctl daemon-reload
sudo systemctl restart lifecoach
```

**验证部署**：
```bash
ssh cmit@192.168.1.28 "sudo journalctl -u lifecoach -n 50"
```

查找日志：
```
[ASR] 使用 Sherpa-ONNX Paraformer 引擎
[ASR] Paraformer 模型加载完成: /home/cmit/LifeCoach/models/sherpa/paraformer
```

## 回滚方案

如果 Paraformer 出现问题：

### Windows
```powershell
$env:ASR_ENGINE = "whisper"
# 或
Remove-Item Env:\ASR_ENGINE
```

### Raspberry Pi
```bash
# 编辑 systemd 服务
sudo vi /etc/systemd/system/lifecoach.service

# 注释掉或删除
# Environment="ASR_ENGINE=sherpa"

sudo systemctl daemon-reload
sudo systemctl restart lifecoach
```

## 故障排查

### 模型下载失败

**症状**：文件大小 < 40MB

**解决**：
```powershell
cd d:\git\life-coach\models\sherpa
Remove-Item "paraformer.tar.bz2" -Force
Invoke-WebRequest `
  -Uri "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-streaming-paraformer-bilingual-zh-en.tar.bz2" `
  -OutFile "paraformer.tar.bz2"
```

### 模型解压失败

**症状**：tar 或 7-Zip 错误

**解决**：
1. Windows 10 1803+ 内置 tar 命令
2. 或安装 7-Zip: https://www.7-zip.org/

### 模型文件未找到

**症状**：
```
[ASR警告] Paraformer 模型不存在: models/sherpa/paraformer
```

**解决**：
```bash
# 检查目录
ls models/sherpa/paraformer/

# 应该有文件
encoder.int8.onnx
decoder.int8.onnx
tokens.txt
```

### 识别结果为空

**症状**：text = ""

**可能原因**：
1. 音频格式不正确
2. 采样率不匹配
3. 模型加载失败

**调试**：
```python
# 添加调试日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 检查音频
print(f"音频类型: {audio.dtype}")
print(f"音频范围: [{audio.min()}, {audio.max()}]")
print(f"音频长度: {len(audio)} 采样点")
```

## 技术支持

- GitHub Issues: https://github.com/k2-fsa/sherpa-onnx/issues
- 评估文档: [docs/sherpa-onnx-evaluation.md](sherpa-onnx-evaluation.md)
- 集成文档: [docs/sherpa-asr-integration.md](sherpa-asr-integration.md)
- VAD 测试文档: [docs/silero-vad-test-guide.md](silero-vad-test-guide.md)

## 性能基准（待测试）

| 指标 | Whisper Tiny INT4 | Paraformer INT8 | 目标 |
|------|-------------------|-----------------|------|
| 模型大小 | ~40MB | ~46MB | < 100MB |
| 首次加载 | 3-5s | 待测 | < 5s |
| 识别延迟 | 1-2s | 待测 | < 2s |
| CPU 使用 | 50-80% | 待测 | < 80% |
| 内存占用 | ~150MB | 待测 | < 200MB |
| 准确率 | 高 | 待测 | ≥ Whisper |

**测试环境**：Raspberry Pi 4B, 4GB RAM, 4 cores

## 开发计划

### Phase 1: VAD 集成 ✅
- [x] Silero VAD 封装
- [x] 集成到 audio_recorder
- [x] Pi 部署和测试
- [x] 文档完善

### Phase 2: ASR 集成 ⏳
- [x] Paraformer 封装
- [x] 双引擎架构
- [ ] 模型下载和部署
- [ ] 功能测试
- [ ] 性能测试
- [ ] 准确率对比
- [ ] Pi 部署

### Phase 3: 优化和稳定 ❌
- [ ] 参数调优
- [ ] 长时间稳定性测试
- [ ] 错误处理增强
- [ ] 监控和日志

## 参考资料

- [sherpa-onnx 项目](https://github.com/k2-fsa/sherpa-onnx)
- [Paraformer 模型](https://github.com/k2-fsa/sherpa-onnx/blob/master/docs/source/onnx/pretrained_models/online-paraformer/index.rst)
- [sherpa-onnx Python API](https://k2-fsa.github.io/sherpa/onnx/python-api/index.html)
