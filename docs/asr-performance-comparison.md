# Whisper vs Paraformer ASR 性能对比报告

**测试日期**: 2026-01-24  
**测试环境**: Windows 11, Python 3.9, 虚拟环境  
**硬件**: (待补充)

## 测试配置

### Whisper (faster-whisper)
- **模型**: small
- **量化**: INT8
- **设备**: CPU
- **包**: faster-whisper

### Paraformer (sherpa-onnx)
- **模型**: sherpa-onnx-streaming-paraformer-bilingual-zh-en
- **量化**: INT8
- **设备**: CPU
- **线程**: 2
- **包**: sherpa-onnx 1.12.23

## 性能对比总结

| 指标 | Whisper Small INT8 | Paraformer INT8 | 改进 |
|------|-------------------|-----------------|------|
| 模型加载时间 | 2.75 - 4.04s | 1.99 - 2.15s | **快 27-47%** |
| 内存占用 | 275-276 MB | 282-283 MB | 多 3% |
| 识别速度（RTF） | 0.29 - 0.57x | 0.08x | **快 3.6-7.1x** |
| 准确率 | 高 | 中-高 | - |

**RTF (Real-Time Factor)**: 值越小越好，0.08x 表示处理 10 秒音频只需 0.8 秒

## 详细测试结果

### 测试 1: 中英文混合（0.wav, 10.05s）

**音频内容**: "昨天是 Monday. Today is 礼拜二. The day after tomorrow 是星期三"

| 引擎 | 识别耗时 | RTF | 识别结果 | 评价 |
|------|---------|-----|---------|------|
| **Whisper** | 2.943s | 0.29x | 昨天是 Monday. Today is 禮拜二. The day after tomorrow 是星期三 | ✓ 完整准确，有标点 |
| **Paraformer** | 0.817s | 0.08x | 昨天是 monday today day is 礼拜二 the day after tomorrow 是星期 | △ 基本准确，缺少标点和"三" |

**性能**: Paraformer **快 3.6x**  
**准确率**: Whisper 更好（85.2% 相似度）

---

### 测试 2: 中文为主（1.wav, 5.10s）

**音频内容**: "这是第一种,第二种就要与OS,OS是什么意思"

| 引擎 | 识别耗时 | RTF | 识别结果 | 评价 |
|------|---------|-----|---------|------|
| **Whisper** | 2.581s | 0.51x | 这是第一种,第二种就要与OS,OS是什么意思 | ✓ 准确，有标点 |
| **Paraformer** | 0.411s | 0.08x | 这是第一种第二种种叫嗯与 always o s 什 | ✗ 识别错误较多 |

**性能**: Paraformer **快 6.3x**  
**准确率**: Whisper 明显更好（44% 相似度表示 Paraformer 识别不准）

---

### 测试 3: 中英混合（2.wav, 4.69s）

**音频内容**: "就是平凡的不然是接下来 frequently 平凡的"

| 引擎 | 识别耗时 | RTF | 识别结果 | 评价 |
|------|---------|-----|---------|------|
| **Whisper** | 2.651s | 0.57x | 就是平凡的不然是接下来frequently平凡的 | ✓ 准确 |
| **Paraformer** | 0.364s | 0.08x | 这个是频繁的啊不认识接下来 frequently 苹凡的 | △ 部分错误 |

**性能**: Paraformer **快 7.3x**  
**准确率**: Whisper 更好（71.4% 相似度）

## 性能分析

### 速度优势

**Paraformer** 在所有测试中都表现出显著的速度优势：
- ✅ **模型加载**: 快 27-47%（1.99-2.15s vs 2.75-4.04s）
- ✅ **识别速度**: 快 3.6-7.3x（RTF 0.08x vs 0.29-0.57x）
- ✅ **实时性**: 优秀（0.08x RTF 表示可以处理 12.5x 实时速度）

### 准确率分析

**Whisper** 在准确率上整体更好：
- ✅ 中英文混合识别更准确
- ✅ 标点符号处理更好
- ✅ 专业术语（如 "OS"）识别更准
- ✅ 语境理解更好

**Paraformer** 准确率表现：
- △ 简单中英混合场景表现尚可（测试1: 85% 相似度）
- ✗ 复杂场景或快速语音识别较差（测试2: 44% 相似度）
- △ 容易出现同音字错误（"频繁"→"苹凡"）
- ✗ 缺少标点符号输出

### 内存占用

两者内存占用相近：
- Whisper: 275-276 MB
- Paraformer: 282-283 MB
- 差异: +3% (可忽略)

## 结论与建议

### 当前结论

**速度优先场景（推荐 Paraformer）**:
- ✅ 实时转录要求高（需要低延迟）
- ✅ 处理大量音频文件
- ✅ 简单的中英混合对话
- ✅ 对标点符号要求不高

**准确率优先场景（推荐 Whisper）**:
- ✅ 需要高准确率的场合
- ✅ 复杂语音内容
- ✅ 需要标点符号
- ✅ 专业术语识别
- ✅ 语境理解要求高

### 综合评分

| 维度 | Whisper | Paraformer | 权重 |
|------|---------|-----------|------|
| 识别准确率 | ⭐⭐⭐⭐⭐ (9/10) | ⭐⭐⭐ (6/10) | 40% |
| 识别速度 | ⭐⭐⭐ (6/10) | ⭐⭐⭐⭐⭐ (10/10) | 30% |
| 实时性 | ⭐⭐⭐ (6/10) | ⭐⭐⭐⭐⭐ (10/10) | 20% |
| 资源占用 | ⭐⭐⭐⭐ (8/10) | ⭐⭐⭐⭐ (8/10) | 10% |
| **加权总分** | **7.4/10** | **7.6/10** | - |

### 项目建议

**Life Coach 项目推荐策略**:

1. **默认使用 Whisper Small**（当前策略）
   - 理由: 准确率更高，用户体验更好
   - 适合: 日常对话记录，需要准确转录

2. **可选 Paraformer**（实验性）
   - 理由: 速度快，适合实时场景
   - 适合: 实时字幕、快速预览
   - 建议: 作为"快速模式"选项

3. **树莓派部署**
   - 优先测试 Paraformer（速度优势可能更明显）
   - 如果准确率可接受，推荐使用
   - 否则保持 Whisper Tiny/Small

### 下一步测试

**树莓派性能测试（待完成）**:
- [ ] CPU 使用率对比
- [ ] 实际延迟测试
- [ ] 长时间运行稳定性
- [ ] 温度和功耗
- [ ] 内存压力测试

**准确率改进方向**:
- [ ] 测试 Paraformer FP32 模型（更大但更准）
- [ ] 调整解码参数（beam_size 等）
- [ ] 后处理标点符号补全
- [ ] 语言模型融合

## 附录

### 测试命令

```bash
# 单文件对比测试
python compare_asr.py test_audio.wav

# 只测试 Whisper
python compare_asr.py test_audio.wav --whisper-only

# 只测试 Paraformer
python compare_asr.py test_audio.wav --paraformer-only
```

### 环境切换

```powershell
# 切换到 Paraformer
$env:ASR_ENGINE = "sherpa"

# 切换回 Whisper
$env:ASR_ENGINE = "whisper"
# 或
Remove-Item Env:\ASR_ENGINE
```

### 参考资料

- [sherpa-onnx GitHub](https://github.com/k2-fsa/sherpa-onnx)
- [faster-whisper GitHub](https://github.com/SYSTRAN/faster-whisper)
- [Paraformer 模型文档](https://k2-fsa.github.io/sherpa/onnx/pretrained_models/online-paraformer/paraformer-models.html)
