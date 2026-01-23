# 文本纠错技术文档

## 概述

基于 Qwen2.5-0.5B-Instruct 的轻量级文本纠错系统，用于 ASR 后的错别字和标点符号修正。

## 技术栈

- **模型**: Qwen2.5-0.5B-Instruct-Q4_K_M.gguf (~330MB)
- **推理引擎**: llama-cpp-python 0.2.89
- **加速库**: OpenBLAS + ARM NEON SIMD
- **缓存策略**: LRU Cache (maxsize=50)
- **部署架构**: 懒加载 + 降级容错

## 性能指标（树莓派4）

| 指标 | 数值 |
|------|------|
| 模型大小 | 330MB |
| 内存占用峰值 | ~400MB |
| 推理速度 | 8-12 tokens/sec |
| 平均耗时 | 3-8秒（短文本） |
| 缓存命中 | <100ms |

## 架构设计

### 1. 模块结构

```
src/text_corrector.py
├── TextCorrector (主类)
│   ├── __init__()          # 配置初始化
│   ├── _load_model()       # 懒加载模型
│   ├── correct()           # 纠错入口（带缓存）
│   ├── _build_prompt()     # 提示词构建
│   └── get_stats()         # 统计信息
└── get_text_corrector()    # 全局单例
```

### 2. 调用流程

```
用户说话 → Whisper ASR → ASR文本
                ↓
        asr_engine_real.py
                ↓
        text_corrector.correct()  ← 检查缓存
                ↓
        [缓存未命中] → 加载模型 → LLM推理
                ↓
        返回 {text, text_original, changes, ...}
```

### 3. 降级策略

```python
try:
    corrected = corrector.correct(text)
except ModelNotLoadedError:
    # 模型加载失败，返回原文
    corrected = text
except TimeoutError:
    # 推理超时，返回原文
    corrected = text
```

## 配置参数

### 环境变量（.env）

| 变量 | 默认值 | 说明 |
|------|--------|------|
| TEXT_CORRECTION_ENABLED | false | 是否启用纠错功能 |
| TEXT_CORRECTION_MODEL | ~/LifeCoach/models/...gguf | 模型路径 |
| TEXT_CORRECTION_MAX_TOKENS | 512 | 最大生成token数 |
| TEXT_CORRECTION_TEMPERATURE | 0.3 | 生成温度（0.0-1.0） |
| TEXT_CORRECTION_TIMEOUT | 15 | 超时秒数 |

### 模型参数（代码硬编码）

```python
n_ctx=1024              # 上下文窗口
n_threads=4             # CPU线程数（树莓派4核心）
n_batch=128             # 批处理大小
use_mlock=True          # 锁定内存防止swap
verbose=False           # 静默模式
```

## 提示词工程

### Prompt模板

```
你是一个中文文本纠错助手。请纠正以下语音识别文本中的错别字和标点符号，只输出纠正后的文本，不要解释。

原始文本：{text}

纠正后的文本：
```

### 设计原则

1. **简洁明确**: 避免冗长的system prompt
2. **单一任务**: 只做纠错，不做摘要或改写
3. **格式规范**: 明确输出要求（"只输出...不要解释"）
4. **中文优化**: 针对中文语音识别特点

## API接口

### POST /api/correct_text

**请求：**
```json
{
  "text": "今天天气很好我们去公园玩吧"
}
```

**响应：**
```json
{
  "corrected": "今天天气很好，我们去公园玩吧。",
  "original": "今天天气很好我们去公园玩吧",
  "changes": [
    {"position": 6, "type": "punctuation", "value": "，"},
    {"position": -1, "type": "punctuation", "value": "。"}
  ],
  "processing_time_ms": 3245,
  "from_cache": false
}
```

**错误响应：**
- `400`: 请求参数错误（空文本或超长）
- `503`: 模型未加载
- `500`: 内部错误

### GET /api/correct_text/stats

**响应：**
```json
{
  "total_corrections": 42,
  "cache_hits": 18,
  "cache_misses": 24,
  "cache_hit_rate": 0.43,
  "average_time_ms": 3567,
  "model_loaded": true
}
```

## 缓存机制

### LRU Cache实现

```python
from functools import lru_cache

@lru_cache(maxsize=50)
def _correct_cached(self, text: str) -> str:
    # 实际推理逻辑
    pass
```

### 缓存策略

- **容量**: 最多50条记录
- **淘汰策略**: 最近最少使用（LRU）
- **缓存键**: 输入文本的MD5哈希
- **命中效果**: <100ms响应时间

### 适用场景

- 用户重复说相同的话
- 测试环境频繁使用固定测试用例
- 常见短语（"今天天气怎么样"）

## 部署指南

### 1. 下载模型

```bash
cd ~/LifeCoach
python deploy/download_qwen_model.py
```

**支持断点续传：**
- 使用 HTTP Range 头支持
- 自动检测已下载部分
- tqdm进度条显示

**可选SHA256校验：**
```bash
python deploy/download_qwen_model.py --verify-sha256
```

### 2. 编译llama-cpp-python（ARM优化）

`setup_pi.sh` 已自动配置：

```bash
# 安装OpenBLAS
apt-get install -y libopenblas-dev

# 编译llama-cpp-python（启用BLAS + NEON）
CMAKE_ARGS="-DLLAMA_BLAS=ON -DLLAMA_BLAS_VENDOR=OpenBLAS" \
pip install llama-cpp-python==0.2.89 --no-cache-dir
```

### 3. 启用功能

编辑 `.env`：

```bash
TEXT_CORRECTION_ENABLED=true
TEXT_CORRECTION_MODEL=/home/pi/LifeCoach/models/qwen2.5-0.5b/qwen2.5-0.5b-instruct-q4_k_m.gguf
```

### 4. 验证部署

```bash
# 重启服务
sudo systemctl restart lifecoach

# 查看日志
sudo journalctl -u lifecoach -f

# 应该看到：
# [INFO] Text correction enabled: /home/pi/LifeCoach/models/...
# [INFO] Model will be loaded on first use (lazy loading)
```

### 5. 测试纠错

```bash
curl -X POST http://localhost:5000/api/correct_text \
  -H "Content-Type: application/json" \
  -d '{"text": "今天天气很好我们去公园玩吧"}'
```

## 故障排查

### 问题1: 模型加载失败

**症状：** `ModelNotLoadedError: Failed to load model`

**排查步骤：**
1. 检查文件是否存在：`ls -lh $TEXT_CORRECTION_MODEL`
2. 检查内存是否充足：`free -h`（需要至少500MB可用）
3. 查看详细日志：`journalctl -u lifecoach -n 100`

**解决方案：**
- 确保模型文件完整下载（330MB）
- 重启树莓派释放内存
- 降低其他服务内存占用

### 问题2: 推理速度过慢

**症状：** 每次纠错耗时>10秒

**排查步骤：**
1. 检查CPU频率：`cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq`
2. 检查OpenBLAS是否生效：`ldd ~/.local/lib/python3.*/site-packages/llama_cpp/*.so | grep openblas`

**解决方案：**
- 确保树莓派未降频（散热充足）
- 重新编译llama-cpp-python（参考上文编译步骤）
- 降低 `TEXT_CORRECTION_MAX_TOKENS` 到256

### 问题3: 内存不足

**症状：** `MemoryError` 或服务崩溃

**排查步骤：**
1. 查看内存占用：`sudo systemctl status lifecoach`
2. 检查swap分区：`swapon --show`

**解决方案：**
- 关闭 Whisper 模型时再启用纠错（避免双模型）
- 增加swap分区：
  ```bash
  sudo dphys-swapfile swapoff
  sudo nano /etc/dphys-swapfile  # 设置CONF_SWAPSIZE=2048
  sudo dphys-swapfile setup
  sudo dphys-swapfile swapon
  ```

### 问题4: 纠错效果不佳

**症状：** 纠正后文本反而更差

**可能原因：**
- 温度参数过高（过于"创造性"）
- 输入文本过长导致上下文丢失
- 模型对特定领域词汇不熟悉

**解决方案：**
1. 降低温度：`TEXT_CORRECTION_TEMPERATURE=0.1`
2. 限制输入长度（<200字）
3. 考虑 Fine-tune 模型（针对特定领域）

## 性能优化建议

### 1. 硬件层面

- **树莓派散热**: 加装散热片/风扇，避免降频
- **存储优化**: 使用SSD代替SD卡（提升模型加载速度）
- **内存管理**: 关闭不必要的后台服务

### 2. 软件层面

- **批处理**: 如有多段文本，考虑批量纠错（减少模型加载次数）
- **缓存预热**: 将常见短语提前加载到缓存
- **异步处理**: 使用队列异步处理纠错请求（不阻塞ASR）

### 3. 模型层面

- **更小的量化**: 尝试 Q2_K 或 Q3_K_S（牺牲精度换速度）
- **模型裁剪**: 使用更小的基座模型（如 Qwen2-0.5B-Instruct）
- **蒸馏模型**: 训练专门针对纠错任务的小模型

## 监控指标

### 关键指标

```python
stats = corrector.get_stats()
```

**返回：**
- `correction_count`: 总纠错次数
- `cache_hits`: 缓存命中次数
- `cache_misses`: 缓存未命中次数
- `cache_hit_rate`: 命中率（0-1）
- `average_time_ms`: 平均耗时（毫秒）
- `model_loaded`: 模型是否已加载

### 告警阈值建议

- `cache_hit_rate < 0.2`: 缓存效果差，考虑增加缓存容量
- `average_time_ms > 10000`: 推理过慢，检查CPU降频或内存不足
- `correction_count > 1000 && model_loaded=false`: 模型加载失败但请求持续，需修复

## 进一步优化方向

### 短期（1-2周）

1. **前端集成**: 在Web界面显示纠错前后对比
2. **A/B测试**: 收集用户反馈，评估纠错质量
3. **日志分析**: 统计常见纠错场景，优化提示词

### 中期（1-2月）

1. **Fine-tune模型**: 收集ASR→纠错数据集，微调Qwen2.5-0.5B
2. **多模型支持**: 支持切换不同量化版本（Q2/Q3/Q4）
3. **流式纠错**: 边ASR边纠错，降低总延迟

### 长期（3月+）

1. **领域适配**: 针对不同场景（医疗、法律）训练专用模型
2. **联邦学习**: 用户端模型更新而不上传隐私数据
3. **端侧推理**: 使用树莓派 AI加速器（如Coral TPU）

---

**文档版本**: v1.0  
**最后更新**: 2025年1月  
**维护者**: Life Coach团队
