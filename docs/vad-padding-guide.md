# VAD 首尾截断优化指南

## 📋 问题描述

在使用 Silero VAD 进行实时语音分段时，可能会出现音频首尾被截断的问题：
- **首部截断**：说话的第一个字或音节缺失（如"今天天气"变成"天天气"）
- **尾部截断**：说话的最后一个字或音节缺失（如"怎么样啊"变成"怎么样"）

## 🔍 原因分析

### 1. VAD 检测延迟（首部截断）
- VAD 需要一定的音频数据才能判断是否为语音
- 在检测到语音之前的音频会被丢弃
- 典型延迟：50-200ms

### 2. 静音判断过早（尾部截断）
- `min_silence_duration` 设置过短，说话停顿会被认为是结束
- VAD 判断为静音后立即停止录制，尾音可能未完全捕获

### 3. 缺少音频缓冲区
- 未保留 VAD 检测前的音频（前缓冲）
- 未保留 VAD 检测结束后的音频（后缓冲）

## ✅ 优化方案

### 1. 添加音频前后填充（Speech Padding）

**核心参数：`speech_pad_ms`**
- **作用**：在检测到的语音段前后各添加指定毫秒的音频
- **默认值**：300ms（推荐值，在保护首尾和避免过多噪音之间平衡）
- **工作原理**：
  ```
  原始检测：  [----静音----][语音开始]======语音======[语音结束][----静音----]
  添加填充：  [--前填充--][语音开始]======语音======[语音结束][--后填充--]
  ```

**调优建议：**
- **保守值**：200ms - 最少填充，适合安静环境
- **推荐值**：300ms - 平衡值，适合大多数场景
- **激进值**：500ms - 更多填充，适合快速说话或嘈杂环境

### 2. 优化 VAD 参数

#### `min_silence_duration` (最小静音时长)
- **旧值**：1.2秒（过长，导致频繁分段）
- **新值**：0.8秒（更合理，允许自然停顿）
- **效果**：减少因停顿导致的不必要分段

#### `min_speech_duration` (最小语音时长)
- **旧值**：0.25秒（可能过滤掉"啊"、"嗯"等短语音）
- **新值**：0.1秒（捕获更短的语音）
- **效果**：不会漏掉简短应答

#### `threshold` (VAD 阈值)
- **旧值**：0.5（较保守）
- **新值**：0.35（更灵敏）
- **效果**：更早检测到语音，减少首部截断

#### `window_size` (窗口大小)
- **旧值**：512 samples
- **新值**：256 samples
- **效果**：更快响应，减少检测延迟

## 📊 参数对比表

| 参数 | 旧值 | 新值 | 改进说明 |
|------|------|------|---------|
| `speech_pad_ms` | 无 | 300ms | **新增**：前后各填充300ms |
| `min_silence_duration` | 1.2s | 0.8s | 允许更长停顿不分段 |
| `min_speech_duration` | 0.25s | 0.1s | 捕获更短语音 |
| `threshold` | 0.5 | 0.35 | 更早检测语音 |
| `window_size` | 512 | 256 | 更快响应 |

## 🧪 测试方法

### 1. 快速测试句子

测试以下容易被截断的句子：

**首部截断测试：**
- "今天天气怎么样" → 检查是否有"今"
- "我们去哪里玩" → 检查是否有"我"
- "苹果很好吃" → 检查是否有"苹"

**尾部截断测试：**
- "你好啊" → 检查是否有"啊"
- "对不对呀" → 检查是否有"呀"
- "是这样的" → 检查是否有"的"

**停顿测试：**
- "今天...天气很好" → 检查是否分成两段
- "我觉得...应该可以" → 检查是否保持一段

### 2. 检查日志输出

部署后查看日志：
```bash
ssh cmit@192.168.1.28 "sudo journalctl -u lifecoach -f --no-pager | grep 'VAD'"
```

关注以下信息：
```
[VAD] Silero VAD 已初始化
  模型: models/sherpa/silero_vad.onnx
  min_silence: 0.8s          ← 确认新值
  min_speech: 0.1s           ← 确认新值
  threshold: 0.35            ← 确认新值
  speech_pad: 300ms（防止首尾截断） ← 关键！
```

### 3. 检查分段输出

```bash
ssh cmit@192.168.1.28 "sudo journalctl -u lifecoach -f --no-pager | grep 'VAD分段'"
```

预期看到：
```
[VAD分段] 第 1 段: duration=2.35s, samples=37600, RMS=0.1234, Peak=0.8567
```

**验证要点：**
- `duration` 应该比实际说话时间多约 0.6 秒（前后各 300ms）
- `samples` 应该对应 `(duration * 16000)` 个采样点

## 🔧 进一步调优

### 场景 1：仍然有首部截断

**原因**：说话非常突然，VAD 反应不够快

**方案**：
1. 增加 `speech_pad_ms`：从 300ms → 400ms 或 500ms
2. 降低 `threshold`：从 0.35 → 0.3（更灵敏但可能误检）
3. 减小 `window_size`：从 256 → 128（更快但可能不稳定）

**配置示例**：
```python
REALTIME_SPEECH_PAD_MS = 400  # 增加到400ms
REALTIME_VAD_THRESHOLD = 0.3  # 降低阈值
```

### 场景 2：仍然有尾部截断

**原因**：说话有拖音或尾音较弱

**方案**：
1. 增加 `speech_pad_ms`：特别是后填充
2. 增加 `min_silence_duration`：从 0.8s → 1.0s

**配置示例**：
```python
REALTIME_SPEECH_PAD_MS = 500  # 增加到500ms
REALTIME_MIN_SILENCE_DURATION = 1.0  # 更宽容的静音判断
```

### 场景 3：包含太多噪音

**原因**：`speech_pad_ms` 过大，或环境噪音多

**方案**：
1. 减小 `speech_pad_ms`：从 300ms → 200ms
2. 提高 `threshold`：从 0.35 → 0.4
3. 确保环境安静

### 场景 4：频繁分段

**原因**：说话有停顿，`min_silence_duration` 过短

**方案**：
1. 增加 `min_silence_duration`：从 0.8s → 1.0s 或 1.2s
2. 增加 `max_segment_duration`：从 10s → 15s（如需要更长连续录音）

## 📝 配置文件说明

所有参数在 `src/config.py` 中定义，支持通过环境变量覆盖：

```python
# VAD参数
REALTIME_MIN_SILENCE_DURATION = float(os.getenv('REALTIME_MIN_SILENCE_DURATION', '0.8'))
REALTIME_MIN_SPEECH_DURATION = float(os.getenv('REALTIME_MIN_SPEECH_DURATION', '0.1'))
REALTIME_VAD_THRESHOLD = float(os.getenv('REALTIME_VAD_THRESHOLD', '0.35'))

# 音频填充（防止截断）
REALTIME_SPEECH_PAD_MS = int(os.getenv('REALTIME_SPEECH_PAD_MS', '300'))
```

### 运行时修改

通过环境变量临时调整参数（不需要修改代码）：

```bash
# 在 start.sh 中添加
export REALTIME_SPEECH_PAD_MS=400
export REALTIME_MIN_SILENCE_DURATION=1.0
```

## 📈 性能影响

### 计算开销
- `speech_pad_ms` 增加 **不会** 显著增加计算量
- 仅增加内存使用：`300ms * 16000Hz * 2字节 ≈ 9.6KB`

### 延迟影响
- 前填充不影响实时性（使用历史缓冲）
- 后填充可能增加 `speech_pad_ms` 的延迟
- 300ms 填充的影响可忽略

### 存储影响
- 每个分段增加约 `speech_pad_ms * 2` 的音频长度
- 300ms 双向填充 = 600ms 额外音频
- 对于10秒分段：`(10s + 0.6s) / 10s = 6%` 增长

## 🎯 推荐配置

### 默认场景（已应用）
```python
REALTIME_SPEECH_PAD_MS = 300           # 前后各300ms
REALTIME_MIN_SILENCE_DURATION = 0.8    # 0.8秒静音触发
REALTIME_MIN_SPEECH_DURATION = 0.1     # 最短0.1秒语音
REALTIME_VAD_THRESHOLD = 0.35          # 中等灵敏度
window_size = 256                       # 快速响应
```

**适用于**：大多数日常对话场景

### 安静环境
```python
REALTIME_SPEECH_PAD_MS = 200
REALTIME_VAD_THRESHOLD = 0.4
```

### 嘈杂环境
```python
REALTIME_SPEECH_PAD_MS = 400
REALTIME_MIN_SILENCE_DURATION = 1.0
REALTIME_VAD_THRESHOLD = 0.3
```

### 快速说话
```python
REALTIME_SPEECH_PAD_MS = 400
REALTIME_MIN_SILENCE_DURATION = 0.6
window_size = 128
```

## 🚀 部署测试

1. **提交代码**
```bash
git add -A
git commit -m "feat: 优化VAD参数，添加speech_pad防止首尾截断"
```

2. **部署到树莓派**
```bash
scp d:\git\life-coach\src\config.py d:\git\life-coach\src\vad_silero.py d:\git\life-coach\src\audio_recorder_real.py cmit@192.168.1.28:~/LifeCoach/tmp_deploy/
ssh cmit@192.168.1.28 "cd ~/LifeCoach && cp tmp_deploy/*.py src/ && sudo systemctl restart lifecoach"
```

3. **验证日志**
```bash
ssh cmit@192.168.1.28 "sudo journalctl -u lifecoach --no-pager -n 50 | grep 'VAD'"
```

4. **实际测试**
- 打开网页界面
- 按 K1 开始录音
- 说测试句子（特别是首尾测试句）
- 检查实时转录结果是否完整

## 📚 参考资料

- [Silero VAD 官方文档](https://github.com/snakers4/silero-vad)
- [sherpa-onnx VAD 配置](https://k2-fsa.github.io/sherpa/onnx/vad/index.html)
- Speech Padding 原理：在语音段前后添加缓冲音频，确保不漏掉任何语音内容

## ❓ 常见问题

**Q: speech_pad_ms 会导致重复音频吗？**
A: 不会。前后填充使用的是相邻的真实音频，不会重复。

**Q: 为什么不直接设置很大的 speech_pad_ms？**
A: 过大会包含更多噪音，影响 ASR 准确性。300ms 是平衡值。

**Q: 能否对前后填充使用不同值？**
A: sherpa-onnx 的 Silero VAD 对前后使用相同填充。如需不同，需要修改库代码。

**Q: 调整后仍有截断怎么办？**
A: 检查是否：
1. 麦克风质量问题（拾音不足）
2. 说话过于突然（尝试增加 speech_pad_ms）
3. VAD 阈值过高（尝试降低 threshold）
4. 采样率不匹配（确认使用 16kHz）
