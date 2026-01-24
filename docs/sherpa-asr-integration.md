# Sherpa-ONNX Paraformer ASR 集成指南

## 概述

本文档描述如何将 Sherpa-ONNX 的 Paraformer 流式 ASR 引擎集成到 Life Coach 项目中，作为 faster-whisper 的替代方案。

## 架构变更

### 双引擎架构

系统现在支持两种 ASR 引擎，通过环境变量切换：

```
┌─────────────────┐
│ audio_recorder  │
│  + Silero VAD   │
└────────┬────────┘
         │
         │ 音频段
         ▼
┌─────────────────┐      ┌──────────────┐
│ asr_engine_real │◄─────┤ ASR_ENGINE   │ 环境变量
│                 │      │ = whisper/   │
│  ┌──────────┐  │      │   sherpa     │
│  │ Whisper  │  │      └──────────────┘
│  │ (faster- │  │
│  │ whisper) │  │
│  └──────────┘  │
│                 │
│  ┌──────────┐  │
│  │Paraformer│  │
│  │(sherpa-  │  │
│  │ onnx)    │  │
│  └──────────┘  │
└─────────────────┘
```

### 引擎选择

- **Whisper (默认)**：`ASR_ENGINE=whisper` 或不设置
- **Paraformer**：`ASR_ENGINE=sherpa`

## 安装部署

### Windows 部署

#### 1. 下载 Paraformer 模型

```powershell
cd d:\git\life-coach\models\sherpa
Invoke-WebRequest `
  -Uri "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-streaming-paraformer-bilingual-zh-en.tar.bz2" `
  -OutFile "paraformer.tar.bz2"
```

预期下载大小：~45-50MB

#### 2. 解压并安装模型

```powershell
cd d:\git\life-coach
.\deploy_paraformer.ps1
```

脚本将自动：
- 验证下载文件
- 解压 `.tar.bz2` 归档
- 组织模型文件到 `models/sherpa/paraformer/`
- 验证必需文件（encoder.int8.onnx, decoder.int8.onnx, tokens.txt）

### Raspberry Pi 部署

#### 1. 在 Windows 上下载并解压

```powershell
# 在 Windows 上执行
cd d:\git\life-coach
.\deploy_paraformer.ps1
```

#### 2. 打包模型文件

```powershell
cd models\sherpa
tar -czf paraformer.tar.gz paraformer/
```

#### 3. 传输到 Raspberry Pi

```bash
scp paraformer.tar.gz cmit@192.168.1.28:~/
ssh cmit@192.168.1.28 "cd ~/LifeCoach/models/sherpa && tar -xzf ~/paraformer.tar.gz"
```

#### 4. 上传代码文件

```bash
scp src/asr_sherpa.py cmit@192.168.1.28:~/LifeCoach/src/
scp src/asr_engine_real.py cmit@192.168.1.28:~/LifeCoach/src/
```

## 测试验证

### 基本功能测试

```bash
# 测试 Paraformer ASR
python test_sherpa_asr.py

# 使用真实音频测试
python test_sherpa_asr.py --real-audio
```

### 引擎切换测试

#### 测试 Whisper（默认）
```bash
# Windows
$env:ASR_ENGINE = "whisper"
python src/main_real.py

# Linux
export ASR_ENGINE=whisper
python src/main_real.py
```

#### 测试 Paraformer
```bash
# Windows
$env:ASR_ENGINE = "sherpa"
python src/main_real.py

# Linux
export ASR_ENGINE=sherpa
python src/main_real.py
```

## 性能对比

| 指标 | Whisper Tiny INT4 | Paraformer INT8 | 备注 |
|------|-------------------|-----------------|------|
| 模型大小 | ~40MB | ~46MB | Paraformer 稍大 |
| 准确率 | 高（已验证） | 待验证 | 需实际测试 |
| 延迟 | 1-2s | 待测 | 流式处理可能更低 |
| CPU 使用 | 中 | 待测 | 需要实测 |
| 内存占用 | ~150MB | 待测 | 需要实测 |
| 流式支持 | 否 | 是 | Paraformer 原生流式 |

## API 接口

### asr_sherpa.py

#### SherpaASR 类

```python
from src.asr_sherpa import SherpaASR

# 初始化
asr = SherpaASR(
    model_dir="models/sherpa/paraformer",
    sample_rate=16000,
    num_threads=2,
    decoding_method="greedy_search"
)

# 识别完整音频
text = asr.transcribe(audio_data)  # numpy array, float32 [-1, 1]

# 流式识别
stream = asr.recognizer.create_stream()
text, is_endpoint, stream = asr.transcribe_stream(audio_chunk, stream)

# 识别音频文件
text = asr.transcribe_file("test.wav")
```

#### ParaformerModel 类（兼容接口）

```python
from src.asr_sherpa import ParaformerModel

# 兼容 WhisperModel 接口
model = ParaformerModel(
    model_path="models/sherpa/paraformer",
    device="cpu",
    compute_type="int8"
)

segments, info = model.transcribe(audio_data)
```

### asr_engine_real.py

ASREngine 类自动根据 `ASR_ENGINE` 环境变量选择引擎：

```python
from src.asr_engine_real import ASREngine

# 初始化（自动选择引擎）
engine = ASREngine()

# 转写（接口相同）
result = engine.transcribe_stream(audio_chunks, callback=progress_callback)
```

## 配置文件

`src/config.py` 中的 ASR 配置对两种引擎都有效：

```python
# ASR 引擎类型（通过环境变量设置）
# ASR_ENGINE = "whisper"  # 默认
# ASR_ENGINE = "sherpa"   # Paraformer

# Whisper 配置
ASR_MODEL_SIZE = "small"        # 模型大小
ASR_COMPUTE_TYPE = "int8"       # 计算类型
ASR_BEAM_SIZE = 5               # Beam search 大小
ASR_VAD_FILTER = True           # VAD 过滤

# Paraformer 配置
# 模型路径: models/sherpa/paraformer/
# 线程数: 2（硬编码在 asr_sherpa.py）
# 解码方法: greedy_search
```

## 故障排查

### 问题 1：模型文件未找到

**错误信息**：
```
[ASR警告] Paraformer 模型不存在: models/sherpa/paraformer
```

**解决方案**：
1. 检查模型目录是否存在：`ls models/sherpa/paraformer/`
2. 确认必需文件：`encoder.int8.onnx`, `decoder.int8.onnx`, `tokens.txt`
3. 重新运行部署脚本：`.\deploy_paraformer.ps1`

### 问题 2：文件名不匹配

某些 Paraformer 模型的文件名可能不同（`model.int8.onnx` vs `encoder.int8.onnx`）。

**解决方案**：
1. 检查实际文件名：`ls models/sherpa/paraformer/*.onnx`
2. 修改 `asr_sherpa.py` 中的文件名：
   ```python
   # 修改 _create_recognizer() 方法
   paraformer=sherpa_onnx.OnlineParaformerModelConfig(
       encoder=str(self.model_dir / "实际的encoder文件名.onnx"),
       decoder=str(self.model_dir / "实际的decoder文件名.onnx"),
   ),
   ```

### 问题 3：内存不足（Raspberry Pi）

**症状**：程序崩溃或 OOM killer 终止进程。

**解决方案**：
1. 关闭其他服务释放内存
2. 降低 `num_threads` 参数（`asr_sherpa.py` 中）
3. 如果仍不够，考虑使用 Whisper tiny + INT4

### 问题 4：识别结果为空

**可能原因**：
- 音频格式不正确（需要 float32, [-1, 1]）
- 采样率不匹配（需要 16kHz）
- 模型加载失败

**调试步骤**：
```python
# 检查音频格式
print(f"音频类型: {audio.dtype}")
print(f"音频范围: [{audio.min()}, {audio.max()}]")

# 检查模型状态
print(f"模型目录: {asr.model_dir}")
print(f"识别器: {asr.recognizer}")
```

## 回滚到 Whisper

如果 Paraformer 出现问题，立即回滚：

### Windows
```powershell
$env:ASR_ENGINE = "whisper"
# 或删除环境变量
Remove-Item Env:\ASR_ENGINE
```

### Linux / Raspberry Pi
```bash
export ASR_ENGINE=whisper
# 或取消设置
unset ASR_ENGINE
```

重启服务：
```bash
sudo systemctl restart lifecoach
```

## 下一步工作

### 待测试项

- [ ] Paraformer 准确率测试（与 Whisper 对比）
- [ ] Raspberry Pi 性能测试（CPU、内存、延迟）
- [ ] 长时间运行稳定性测试
- [ ] 噪声环境识别效果测试
- [ ] 中英文混合识别测试

### 待优化项

- [ ] 调整 beam size 优化准确率/速度
- [ ] 调整线程数适配 Pi 硬件
- [ ] 实现真正的流式处理（逐块返回结果）
- [ ] 集成到 VAD 回调中实现端到端流式

### 文档待补充

- [ ] 详细性能测试报告
- [ ] 准确率对比数据
- [ ] 最佳实践和参数调优指南

## 参考资料

- [sherpa-onnx GitHub](https://github.com/k2-fsa/sherpa-onnx)
- [Paraformer 模型文档](https://github.com/k2-fsa/sherpa-onnx/blob/master/docs/source/onnx/pretrained_models/online-paraformer/index.rst)
- [sherpa-onnx Python API](https://k2-fsa.github.io/sherpa/onnx/python-api/index.html)
