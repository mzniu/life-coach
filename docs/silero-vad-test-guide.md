# Silero VAD 集成测试指南

## ✅ 集成完成

**改动内容**：
1. ✅ 创建 `src/vad_silero.py` - Silero VAD 封装
2. ✅ 修改 `src/audio_recorder_real.py` - 使用新 VAD
3. ✅ 删除 ~200行 旧 VAD 代码（能量检测 + FFT）
4. ✅ 更新 `requirements.txt` - 添加 sherpa-onnx
5. ✅ 在 Pi 上安装依赖并测试

**代码简化**：
- 删除了 5 个状态变量
- 删除了 `_check_silence()` 方法
- 删除了 `_is_voice()` FFT 检测方法
- 删除了 `_should_trigger_segment()` 复杂逻辑
- 删除了 `_trigger_segment()` 200+ 行实现
- 保留了录音核心逻辑和接口兼容性

---

## 🧪 测试步骤

### 1. 验证服务状态
```bash
ssh cmit@192.168.1.28 "sudo systemctl status lifecoach"
```
应显示：`Active: active (running)`

### 2. 查看实时日志
```bash
ssh cmit@192.168.1.28 "sudo journalctl -u lifecoach -f"
```

### 3. 打开网页测试

在浏览器访问：`http://192.168.1.28:5000` （或 Pi 的实际 IP）

**测试步骤**：
1. 点击"开始录音"按钮
2. 说一句话（例如："今天天气怎么样"）
3. **停顿 1.2 秒以上**（触发 VAD 分段）
4. 说第二句话（例如："我们去哪里玩"）
5. 停顿 1.2 秒
6. 点击"停止录音"

**期望结果**：
- ✅ 日志中显示 `[VAD] Silero VAD 已初始化`
- ✅ 每次停顿后显示 `[VAD] 第 X 段: start=...`
- ✅ 前端显示实时转录文本
- ✅ 无 "0.1秒分段" 等异常
- ✅ 分段准确（说话时不分段，停顿时分段）

---

## 📊 对比测试（可选）

### 旧 VAD（能量+FFT）vs. 新 VAD（Silero）

测试场景：
1. **正常说话**：一句话中间有短暂停顿
2. **环境噪音**：电风扇、键盘敲击、空调
3. **远距离**：距离麦克风 1-2 米说话
4. **低音量**：小声说话
5. **连续说话**：长句子不停顿（测试 10s 强制分段）

**评估指标**：
- 误触发率（静音时误分段）
- 漏检率（说话时未检测）
- 分段准确性（停顿位置是否合理）
- 抗噪能力（噪音环境下表现）

---

## 🐛 故障排查

### 问题 1：服务无法启动
```bash
# 查看错误日志
ssh cmit@192.168.1.28 "sudo journalctl -u lifecoach -n 50"

# 常见原因：sherpa-onnx 未安装
ssh cmit@192.168.1.28 "cd ~/LifeCoach && source venv/bin/activate && pip list | grep sherpa"

# 解决：安装依赖
ssh cmit@192.168.1.28 "cd ~/LifeCoach && source venv/bin/activate && pip install sherpa-onnx psutil"
```

### 问题 2：VAD 模型未找到
```bash
# 检查模型文件
ssh cmit@192.168.1.28 "ls -lh ~/LifeCoach/models/sherpa/"

# 如果不存在，重新上传
scp d:\git\life-coach\models\sherpa\silero_vad.onnx cmit@192.168.1.28:~/LifeCoach/models/sherpa/
```

### 问题 3：实时转录无输出
```bash
# 查看 VAD 日志
ssh cmit@192.168.1.28 "sudo journalctl -u lifecoach -f | grep -i vad"

# 检查回调是否被调用
ssh cmit@192.168.1.28 "sudo journalctl -u lifecoach -f | grep -i '检测到\|分段'"
```

### 问题 4：CPU 占用过高
```bash
# 查看 CPU 使用
ssh cmit@192.168.1.28 "top -b -n 1 | grep python"

# 如果 CPU > 90%，可能需要调整 VAD 参数
# 编辑 src/vad_silero.py，减少 buffer_size 或调整 threshold
```

---

## ⚙️ 配置调优

### 调整 VAD 灵敏度

编辑 `src/vad_silero.py`，修改以下参数：

```python
# 更宽松（减少误触发）
threshold=0.7          # 默认 0.5，越高越严格

# 更严格（减少漏检）
threshold=0.3          # 更容易触发

# 调整最小静音时长
min_silence_duration=1.5  # 默认 1.2s，增加避免过早分段
min_silence_duration=0.8  # 减少可更快响应

# 调整最小语音时长
min_speech_duration=0.1   # 默认 0.25s，减少过滤掉短语音
```

重启服务生效：
```bash
ssh cmit@192.168.1.28 "sudo systemctl restart lifecoach"
```

---

## 📝 性能指标

根据之前测试（Raspberry Pi 4B）：

| 指标 | 数值 | 评价 |
|------|------|------|
| 实时率 | 28.75x | ✅ 极优 |
| CPU 占用 | ~20% (4核总和) | ✅ 可接受 |
| 内存占用 | +19.6MB | ✅ 优秀 |
| 模型大小 | 1.8MB | ✅ 极小 |
| 启动时间 | 0.093s | ✅ 极快 |

---

## 🎯 成功标准

测试通过标准：
- ✅ 服务正常启动，无错误日志
- ✅ 录音时 VAD 成功初始化
- ✅ 说话后停顿能正确触发分段
- ✅ 静音环境下无误触发
- ✅ 噪音环境下仍能准确检测语音
- ✅ 转录结果正确显示在前端
- ✅ CPU 占用 < 50%
- ✅ 无卡顿或延迟

如果所有标准达成，说明 **Silero VAD 集成成功**！

---

## 🔄 回滚方案

如果测试失败需要回滚：

```bash
# 1. 回滚 Git 提交
cd d:\git\life-coach
git revert HEAD

# 2. 重新部署旧版本
scp src/audio_recorder_real.py cmit@192.168.1.28:~/LifeCoach/src/
ssh cmit@192.168.1.28 "sudo systemctl restart lifecoach"
```

---

## 📞 下一步

测试完成后，请反馈：
1. 是否有分段异常？
2. 噪音环境表现如何？
3. CPU/内存占用是否正常？
4. 与旧 VAD 相比，准确度如何？

根据反馈，我可以：
- 调优 VAD 参数
- 修复 Bug
- 或建议保持现状/回滚

---

**测试开始时间**: 2026-01-24 22:30  
**版本**: Silero VAD v1.0  
**测试人**: 待测试
