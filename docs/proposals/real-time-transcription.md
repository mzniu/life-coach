# 实时录音+实时转录实现方案

## 一、需求分析

**目标**：实现录音过程中实时显示转录文本，提升用户体验。

**当前系统状态**：
- ✅ Whisper small模型（准确度高）
- ✅ WebSocket通信（支持实时推送）
- ✅ VAD支持（faster-whisper内置）
- ⚠️ 性能限制：树莓派处理速度较慢
- ❌ 现状：录音完成后才开始转录

**核心挑战**：
1. Whisper不是流式模型，需要完整音频段
2. 树莓派性能有限，转录耗时较长
3. 需要平衡实时性和准确度
4. 避免在句子中间切断影响识别

---

## 二、推荐方案：基于VAD的智能分段实时转录

### 2.1 方案架构

```
┌─────────────────────────────────────────────────────────────┐
│                      录音+转录流程                           │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  [录音线程] ──→ [音频缓冲区] ──→ [VAD检测]                  │
│                                      │                        │
│                                      ↓                        │
│                             检测到语音段结束？                │
│                                      │                        │
│                                 是 ↓ ↓ 否→继续累积           │
│                                      │                        │
│                          [触发转录] ←┘                        │
│                               │                               │
│                               ↓                               │
│                    [异步转录线程（不阻塞录音）]              │
│                               │                               │
│                               ↓                               │
│                    [WebSocket推送结果]                       │
│                               │                               │
│                               ↓                               │
│                    [前端实时显示文本]                        │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 核心设计

**音频分段策略**（使用VAD）：
```python
# 基于静音检测的智能分段
参数：
  - min_speech_duration: 最小语音时长（0.5秒，避免噪音）
  - min_silence_duration: 静音阈值（0.8秒，触发转录）
  - max_segment_duration: 最大分段时长（10秒，避免等待太久）
  - speech_pad: 语音前后padding（0.2秒，避免切头切尾）

流程：
  1. 持续录音到缓冲区
  2. 检测到连续语音 > 0.5秒
  3. 检测到静音 > 0.8秒 → 触发转录
  4. 或累积时长 > 10秒 → 强制转录
```

**转录策略**（异步+队列）：
```python
# 异步转录，不阻塞录音
架构：
  [录音线程] → [分段队列] → [转录工作线程] → [结果队列] → [WebSocket推送]
  
优势：
  - 录音和转录并行，互不阻塞
  - 自动排队处理，避免资源竞争
  - 即使转录慢也不影响录音质量
```

---

## 三、详细实现计划

### 阶段1：核心功能实现（P0）

#### 1.1 扩展AudioRecorder类
```python
# src/audio_recorder.py 新增方法

class AudioRecorder:
    def __init__(self, vad_enabled=True):
        self.vad_enabled = vad_enabled
        self.current_segment = []  # 当前累积的音频段
        self.segment_queue = queue.Queue()  # 待转录队列
        self.last_speech_time = None
        self.min_silence_duration = 0.8  # 静音触发阈值
        self.max_segment_duration = 10.0  # 最大分段时长
        
    def _recording_loop(self):
        """录音循环（支持实时分段）"""
        while self.is_recording:
            chunk = self._read_audio_chunk()
            self.audio_data.append(chunk)  # 完整录音数据
            self.current_segment.append(chunk)  # 当前分段
            
            # VAD检测
            if self.vad_enabled:
                is_speech = self._detect_speech(chunk)
                segment_duration = self._get_segment_duration()
                
                # 触发条件：静音超过阈值 或 分段过长
                if (not is_speech and self._silence_duration() > self.min_silence_duration) \
                   or segment_duration > self.max_segment_duration:
                    # 将当前段放入队列，等待转录
                    if len(self.current_segment) > 0:
                        self.segment_queue.put(self.current_segment.copy())
                        self.current_segment = []
```

#### 1.2 创建异步转录管理器
```python
# src/realtime_transcriber.py (新建)

import threading
import queue

class RealtimeTranscriber:
    """实时转录管理器"""
    
    def __init__(self, asr_engine, callback):
        self.asr_engine = asr_engine
        self.callback = callback  # 结果回调函数
        self.segment_queue = queue.Queue()
        self.is_running = False
        self.worker_thread = None
        
    def start(self):
        """启动转录工作线程"""
        self.is_running = True
        self.worker_thread = threading.Thread(
            target=self._transcribe_worker,
            daemon=True
        )
        self.worker_thread.start()
        
    def stop(self):
        """停止转录"""
        self.is_running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
            
    def add_segment(self, audio_segment):
        """添加音频段到转录队列"""
        self.segment_queue.put(audio_segment)
        
    def _transcribe_worker(self):
        """转录工作线程（后台运行）"""
        while self.is_running:
            try:
                # 获取音频段（超时避免阻塞）
                segment = self.segment_queue.get(timeout=0.5)
                
                # 转录
                print(f"[实时转录] 开始转录音频段...")
                result = self.asr_engine.transcribe_stream(segment)
                
                # 回调推送结果
                if result and 'text' in result:
                    text = result['text'].strip()
                    if text:
                        self.callback(text)
                        print(f"[实时转录] 完成: {text}")
                        
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[实时转录错误] {e}")
```

#### 1.3 修改AppManager整合功能
```python
# src/app_manager.py

class AppManager:
    def __init__(self):
        self.realtime_transcriber = None
        self.accumulated_text = ""  # 累积文本
        
    def start_recording(self):
        """开始录音（支持实时转录）"""
        # 启动实时转录器
        self.realtime_transcriber = RealtimeTranscriber(
            self.asr,
            callback=self._on_segment_transcribed
        )
        self.realtime_transcriber.start()
        self.accumulated_text = ""
        
        # 将录音器的分段队列连接到转录器
        self.recorder.segment_queue = self.realtime_transcriber.segment_queue
        self.recorder.start()
        
    def _on_segment_transcribed(self, text):
        """转录结果回调"""
        self.accumulated_text += text
        # 通过WebSocket推送给前端
        socketio.emit('realtime_transcript', {
            'segment': text,
            'full_text': self.accumulated_text
        })
```

#### 1.4 前端实时显示
```javascript
// static/app.js

// 连接实时转录事件
socket.on('realtime_transcript', function(data) {
    console.log('[实时转录]', data.segment);
    
    // 显示在录音中的文本区域
    const transcriptDiv = document.getElementById('realtime-transcript');
    if (transcriptDiv) {
        // 新增片段高亮显示
        const segmentSpan = document.createElement('span');
        segmentSpan.textContent = data.segment;
        segmentSpan.className = 'new-segment';
        transcriptDiv.appendChild(segmentSpan);
        
        // 0.5秒后移除高亮
        setTimeout(() => {
            segmentSpan.className = '';
        }, 500);
        
        // 自动滚动到底部
        transcriptDiv.scrollTop = transcriptDiv.scrollHeight;
    }
});
```

---

### 阶段2：优化体验（P1）

#### 2.1 VAD参数调优
```python
# src/config.py 新增配置

# 实时转录VAD参数
REALTIME_VAD_ENABLED = True
REALTIME_MIN_SPEECH_DURATION = 0.5  # 最小语音时长（秒）
REALTIME_MIN_SILENCE_DURATION = 0.8  # 静音触发阈值（秒）
REALTIME_MAX_SEGMENT_DURATION = 10.0  # 最大分段时长（秒）
REALTIME_SPEECH_PAD = 0.2  # 语音前后padding（秒）

# 性能优化
REALTIME_TRANSCRIBE_BEAM_SIZE = 3  # 降低beam size加速（准确度略降）
REALTIME_USE_FAST_CORRECTION = False  # 实时模式关闭纠错（减少延迟）
```

#### 2.2 性能监控
```python
# 添加性能指标
class RealtimeTranscriber:
    def __init__(self):
        self.stats = {
            'segments_count': 0,
            'avg_transcribe_time': 0,
            'queue_size': 0,
            'longest_delay': 0
        }
        
    def get_stats(self):
        """获取性能统计"""
        return {
            **self.stats,
            'queue_size': self.segment_queue.qsize()
        }
```

#### 2.3 前端优化
```javascript
// 添加加载状态指示
function showTranscribingStatus(segmentIndex) {
    const status = document.createElement('span');
    status.className = 'transcribing-indicator';
    status.textContent = '转录中...';
    status.id = `status-${segmentIndex}`;
    document.getElementById('realtime-transcript').appendChild(status);
}

// 转录完成后移除指示器
socket.on('realtime_transcript', function(data) {
    // 移除"转录中"指示器
    const indicator = document.querySelector('.transcribing-indicator');
    if (indicator) indicator.remove();
    
    // 显示转录结果...
});
```

---

### 阶段3：高级功能（P2）

#### 3.1 实时纠错（可选）
```python
# 仅对完整句子纠错，避免延迟
def _on_segment_transcribed(self, text):
    # 判断是否为完整句子（有句号等）
    if text.endswith(('。', '！', '？', '.')):
        # 异步纠错
        threading.Thread(
            target=self._async_correct,
            args=(text,),
            daemon=True
        ).start()
    else:
        # 直接推送
        self._push_transcript(text)
```

#### 3.2 断点续传
```python
# 支持暂停/继续录音
def pause_recording(self):
    """暂停录音（保留缓冲区）"""
    self.is_paused = True
    
def resume_recording(self):
    """继续录音"""
    self.is_paused = False
```

#### 3.3 可配置开关
```python
# 允许用户选择是否启用实时转录
class AppManager:
    def start_recording(self, realtime_transcribe=True):
        if realtime_transcribe:
            # 启动实时转录
            self._start_realtime_transcriber()
        else:
            # 传统模式：录音完成后转录
            self.recorder.start()
```

---

## 四、关键技术要点

### 4.1 faster-whisper VAD配置
```python
# faster-whisper内置VAD参数
segments, info = model.transcribe(
    audio,
    vad_filter=True,  # 启用VAD
    vad_parameters={
        'threshold': 0.5,  # 语音检测阈值
        'min_speech_duration_ms': 250,  # 最小语音时长
        'max_speech_duration_s': 10,  # 最大语音时长
        'min_silence_duration_ms': 800,  # 静音触发时长
        'speech_pad_ms': 200  # 前后padding
    }
)
```

### 4.2 线程安全
```python
# 使用锁保护共享资源
import threading

class AudioRecorder:
    def __init__(self):
        self.segment_lock = threading.Lock()
        self.current_segment = []
        
    def _add_to_segment(self, chunk):
        with self.segment_lock:
            self.current_segment.append(chunk)
```

### 4.3 WebSocket事件定义
```python
# socketio事件命名规范
socketio.emit('realtime_transcript', {
    'segment': '这是一句话',  # 本次识别的片段
    'full_text': '累积的完整文本',  # 所有片段拼接
    'segment_index': 3,  # 片段序号
    'is_final': False  # 是否为最终结果
})
```

---

## 五、性能评估

### 5.1 延迟分析
```
录音延迟：    静音检测延迟（0.8秒）
转录延迟：    Whisper处理时长（1-3秒/句，取决于长度）
网络延迟：    WebSocket推送（<50ms）
总延迟：      约2-4秒/句

对比传统方式：
  传统：录音10秒 → 转录10秒 → 总计20秒才看到结果
  实时：第1句约3秒、第2句约6秒... → 体验提升明显
```

### 5.2 性能开销
```
CPU：        额外10-20%（转录线程）
内存：       额外50-100MB（音频缓冲区）
可接受性：   树莓派4可承受
```

---

## 六、实施建议

### 优先级排序
1. **P0（核心功能）**：阶段1 - 基本实时转录（1-2天）
2. **P1（体验优化）**：阶段2 - VAD调优+性能监控（0.5-1天）
3. **P2（高级功能）**：阶段3 - 实时纠错+可选开关（1天）

### 开发步骤
```bash
# 第1步：创建实时转录器
touch src/realtime_transcriber.py

# 第2步：扩展录音器
vim src/audio_recorder.py  # 添加VAD分段逻辑

# 第3步：整合到AppManager
vim src/app_manager.py  # 连接录音和转录

# 第4步：前端适配
vim static/app.js  # WebSocket事件处理

# 第5步：配置参数
vim src/config.py  # 添加VAD参数

# 第6步：测试验证
python test_realtime.py  # 创建测试脚本
```

### 测试计划
```python
# 测试用例
1. 正常说话（清晰语音）
2. 快速说话（无明显停顿）
3. 长停顿（>2秒静音）
4. 背景噪音场景
5. 多人同时说话
6. 极短语音（<0.5秒）
7. 长段语音（>10秒不停）
8. 网络延迟场景

# 性能测试
- 10分钟持续录音CPU/内存占用
- 转录延迟统计（P50/P90/P99）
- 并发录音场景（多用户）
```

---

## 七、风险与降级方案

### 风险识别
1. **性能不足**：树莓派处理慢导致积压
2. **准确度下降**：短音频段识别效果差
3. **用户体验**：频繁更新导致干扰

### 降级方案
```python
# 降级策略1：自动降级
if transcriber.get_stats()['queue_size'] > 3:
    # 队列积压，停用实时转录
    print('[降级] 队列积压，切换到传统模式')
    realtime_enabled = False

# 降级策略2：用户可选
config.REALTIME_TRANSCRIBE_ENABLED = False  # 配置文件关闭

# 降级策略3：智能合并
if segment_duration < 2.0:
    # 音频段太短，等待下一段再一起转录
    pending_segments.append(segment)
```

---

## 八、后续优化方向

1. **模型优化**：
   - 尝试使用Whisper tiny实时模式（速度更快）
   - 探索专用流式ASR模型（如Kaldi）

2. **算法优化**：
   - 智能预测：根据历史速度动态调整VAD参数
   - 优先级队列：重要语音段优先转录

3. **用户体验**：
   - 添加"转录进度"可视化
   - 支持实时编辑修正
   - 历史对话上下文分析

4. **架构演进**：
   - 分离转录服务（独立进程/服务器）
   - 支持云端转录（备用方案）

---

## 九、参考资源

- [faster-whisper文档](https://github.com/guillaumekln/faster-whisper)
- [WebRTC VAD](https://github.com/wiseman/py-webrtcvad)
- [实时语音识别最佳实践](https://www.assemblyai.com/blog/real-time-speech-recognition-best-practices/)

---

**预计工作量**：2-4天（取决于实现的功能范围）

**建议起步**：先实现阶段1（核心功能），验证效果后再考虑后续优化。
