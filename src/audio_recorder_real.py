"""
真实的音频录制器（使用 sounddevice，支持 Windows/Mac/Linux）
"""

import time
import threading
import numpy as np
import sys
import os

# 导入配置参数
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from src.config import (
        REALTIME_SILENCE_THRESHOLD,
        REALTIME_MIN_SILENCE_DURATION,
        REALTIME_MAX_SEGMENT_DURATION,
        REALTIME_MIN_SEGMENT_DURATION,
        REALTIME_VOICE_DETECTION_ENABLED,
        REALTIME_VOICE_FREQ_MIN,
        REALTIME_VOICE_FREQ_MAX
    )
    USE_CONFIG = True
except ImportError:
    # 默认值
    REALTIME_SILENCE_THRESHOLD = 500
    REALTIME_MIN_SILENCE_DURATION = 1.2
    REALTIME_MAX_SEGMENT_DURATION = 10.0
    REALTIME_MIN_SEGMENT_DURATION = 0.5
    REALTIME_VOICE_DETECTION_ENABLED = True
    REALTIME_VOICE_FREQ_MIN = 85
    REALTIME_VOICE_FREQ_MAX = 3400
    USE_CONFIG = False

try:
    import sounddevice as sd
    REAL_AUDIO = True
except ImportError:
    REAL_AUDIO = False
    print("[音频录制] 警告: sounddevice 未安装，将使用模拟模式")
    print("[音频录制] 安装方法: pip install sounddevice")

class AudioRecorder:
    """音频录制器（真实采集 + 实时分段支持）"""
    
    def __init__(self, sample_rate=16000, channels=1, 
                 realtime_transcribe=False, segment_callback=None):
        """
        初始化录音器
        
        Args:
            sample_rate: 采样率
            channels: 声道数
            realtime_transcribe: 是否启用实时转录分段
            segment_callback: 分段回调函数 callback(audio_segment, metadata)
        """
        global REAL_AUDIO
        self.sample_rate = sample_rate
        self.channels = channels
        self.is_recording = False
        self.start_time = None
        self.audio_data = []
        self.recording_thread = None
        
        # 实时转录支持（使用配置参数）
        self.realtime_transcribe = realtime_transcribe
        self.segment_callback = segment_callback
        self.current_segment = []  # 当前累积的音频段
        self.segment_start_time = None  # 分段开始时间
        self.last_audio_time = None  # 最后一次音频时间
        self.silence_threshold = REALTIME_SILENCE_THRESHOLD  # 从配置读取
        self.min_silence_duration = REALTIME_MIN_SILENCE_DURATION  # 从配置读取
        self.max_segment_duration = REALTIME_MAX_SEGMENT_DURATION  # 从配置读取
        self.min_segment_duration = REALTIME_MIN_SEGMENT_DURATION  # 从配置读取
        self.segment_count = 0
        self.consecutive_silence_chunks = 0  # 连续静音块计数
        self.has_voice_in_segment = False  # 当前分段是否有有效语音
        
        # 人声检测配置
        self.voice_detection_enabled = REALTIME_VOICE_DETECTION_ENABLED
        self.voice_freq_min = REALTIME_VOICE_FREQ_MIN
        self.voice_freq_max = REALTIME_VOICE_FREQ_MAX
        
        if REAL_AUDIO:
            try:
                print(f"[音频录制] 初始化真实音频录制器 ({sample_rate}Hz, {channels}声道)")
                # 列出可用设备
                # devices = sd.query_devices() # 可能会很长
                default_input = sd.query_devices(kind='input')
                print(f"[音频录制] 默认输入设备: {default_input['name']}")
            except Exception as e:
                print(f"[音频录制] 错误: 无法初始化音频设备 ({e})")
                print("[音频录制] 可能原因: 未插入麦克风或声卡驱动未加载")
                print("请检查: lsusb (如果是USB麦克风) 或 arecord -l")
                # 抛出异常让上层知道或者降级为模拟？
                # 这里我们选择降级为模拟模式，以免 crashing loop
                REAL_AUDIO = False
        else:
            print("[音频录制] 初始化模拟音频录制器")
        
    def start(self):
        """开始录音"""
        if self.is_recording:
            raise Exception("录音已在进行中")
            
        self.is_recording = True
        self.start_time = time.time()
        self.audio_data = []
        
        # 重置实时分段状态
        self.current_segment = []
        self.segment_start_time = time.time()
        self.last_audio_time = time.time()
        self.segment_count = 0
        
        if REAL_AUDIO:
            print("[音频录制] 开始录音（真实采集）")
            self.recording_thread = threading.Thread(target=self._real_recording_loop, daemon=True)
        else:
            print("[音频录制] 开始录音（模拟采集）")
            self.recording_thread = threading.Thread(target=self._mock_recording_loop, daemon=True)
        
        self.recording_thread.start()
        
    def stop(self):
        """停止录音"""
        if not self.is_recording:
            raise Exception("未在录音")
            
        self.is_recording = False
        
        # 等待录音线程结束
        if self.recording_thread:
            self.recording_thread.join(timeout=2.0)
        
        # 处理剩余的分段（如果有）
        if self.realtime_transcribe and len(self.current_segment) > 0:
            print("[音频分段] 处理最后一段...")
            self._trigger_segment()
        
        duration = time.time() - self.start_time
        print(f"[音频录制] 停止录音（时长: {duration:.1f}秒, 采样数: {len(self.audio_data)}）")
        if self.realtime_transcribe:
            print(f"[音频分段] 共产生 {self.segment_count} 个分段")
        return self.audio_data
        
    def cancel(self):
        """取消录音"""
        self.is_recording = False
        self.audio_data = []
        print("[音频录制] 取消录音")
        
    def get_duration(self):
        """获取录音时长"""
        if self.start_time:
            return time.time() - self.start_time
        return 0
    
    def _check_silence(self, audio_chunk):
        """检测音频块是否为静音"""
        if len(audio_chunk) == 0:
            return True
        # 计算音频能量（平均绝对值）
        energy = np.mean(np.abs(audio_chunk))
        return energy < self.silence_threshold
    
    def _is_voice(self, audio_chunk):
        """检测音频块是否为人声（基于频谱特征）"""
        if not self.voice_detection_enabled or len(audio_chunk) < 256:
            return True  # 禁用或数据太短，默认认为是人声
        
        try:
            # 使用FFT分析频谱
            fft_result = np.fft.rfft(audio_chunk)
            fft_freq = np.fft.rfftfreq(len(audio_chunk), 1.0 / self.sample_rate)
            fft_magnitude = np.abs(fft_result)
            
            # 计算人声频段的能量占比
            voice_mask = (fft_freq >= self.voice_freq_min) & (fft_freq <= self.voice_freq_max)
            voice_energy = np.sum(fft_magnitude[voice_mask])
            total_energy = np.sum(fft_magnitude)
            
            if total_energy == 0:
                return False  # 无能量，认为不是人声
            
            # 人声频段能量占比（通常>30%认为是人声）
            voice_ratio = voice_energy / total_energy
            return voice_ratio > 0.3
            
        except Exception as e:
            # FFT失败，降级为能量检测
            return True
    
    def _should_trigger_segment(self):
        """判断是否应该触发分段"""
        if not self.realtime_transcribe or not self.segment_callback:
            return False
            
        if len(self.current_segment) == 0:
            return False
            
        segment_duration = time.time() - self.segment_start_time
        
        # 触发条件1: 连续静音chunk达到1.2秒 且 当前分段有有效语音
        # 这样确保只有真正说话后的停顿才会触发，过滤纯噪音
        min_silence_chunks = int(self.min_silence_duration / 0.1)  # 1.2s / 0.1s = 12
        if self.consecutive_silence_chunks >= min_silence_chunks and self.has_voice_in_segment:
            return True
            
        # 触发条件2: 分段时长超过最大限制（强制分割）
        if segment_duration >= self.max_segment_duration:
            return True
            
        return False
    
    def _trigger_segment(self):
        """触发分段回调"""
        if len(self.current_segment) == 0:
            return
            
        try:
            segment_duration = time.time() - self.segment_start_time
            self.segment_count += 1
            
            # 合并音频块
            segment_audio = np.concatenate(self.current_segment)
            
            # 检查是否为纯静音（优化：跳过无效音频段）
            avg_energy = np.mean(np.abs(segment_audio))
            # 如果平均能量低于阈值的20%，认为是纯静音，跳过转录
            silence_skip_threshold = self.silence_threshold * 0.2
            
            if avg_energy < silence_skip_threshold:
                print(f"[音频分段] 跳过第 {self.segment_count} 段（纯静音，能量: {avg_energy:.1f} < {silence_skip_threshold:.1f}）")
                
                # 广播到前端日志
                try:
                    from src.api_server import broadcast_log
                    broadcast_log(f"[VAD] 跳过第 {self.segment_count} 段（纯静音）", 'info')
                except Exception:
                    pass
                
                # 重置分段状态（关键：必须完整重置，避免状态泄漏到下一个分段）
                self.current_segment = []
                self.segment_start_time = time.time()
                self.last_audio_time = time.time()
                self.consecutive_silence_chunks = 0
                self.has_voice_in_segment = False
                return
            
            log_msg = f"[音频分段] 触发第 {self.segment_count} 段（时长: {segment_duration:.2f}秒，{len(self.current_segment)} 块，能量: {avg_energy:.1f}）"
            print(log_msg)
            
            # 广播到前端日志
            try:
                from src.api_server import broadcast_log
                broadcast_log(f"[VAD] 检测到语音停顿，触发第 {self.segment_count} 段分割", 'info')
            except Exception:
                pass
            
            # 调用回调函数
            metadata = {
                'segment_index': self.segment_count,
                'duration': segment_duration,
                'timestamp': self.segment_start_time,
                'sample_count': len(segment_audio),
                'avg_energy': float(avg_energy)
            }
            self.segment_callback(segment_audio.copy(), metadata)
            
            # 重置分段状态
            self.current_segment = []
            self.segment_start_time = time.time()
            self.last_audio_time = time.time()  # 重置，避免累积
            self.consecutive_silence_chunks = 0  # 重置静音计数
            self.has_voice_in_segment = False  # 重置语音标记
            
        except Exception as e:
            print(f"[音频分段错误] {e}")
            import traceback
            traceback.print_exc()
    
    def _real_recording_loop(self):
        """真实录音循环"""
        chunk_duration = 0.1  # 100ms 每块
        
        # 尝试确定可用的采样率
        device_rate = self.sample_rate
        try:
            # 检查16000是否被支持
            sd.check_input_settings(device=None, channels=self.channels, dtype='int16', extra_settings=None, samplerate=self.sample_rate)
        except Exception as e:
            print(f"[音频录制] 警告: 设备不支持 {self.sample_rate}Hz ({e})")
            # 尝试获取设备默认采样率
            try:
                dev_info = sd.query_devices(kind='input')
                default_rate = int(dev_info['default_samplerate'])
                print(f"[音频录制] 尝试使用设备默认采样率: {default_rate}Hz")
                device_rate = default_rate
            except:
                print("[音频录制] 无法获取默认采样率，将尝试 48000Hz")
                device_rate = 48000

        print(f"[音频录制] 实际使用采样率: {device_rate}Hz")
        
        # 计算每次读取的帧数
        chunk_samples = int(device_rate * chunk_duration)
        
        try:
            with sd.InputStream(
                samplerate=device_rate,
                channels=self.channels,
                dtype='int16',
                blocksize=chunk_samples
            ) as stream:
                while self.is_recording:
                    # 读取音频数据
                    audio_chunk, overflowed = stream.read(chunk_samples)
                    
                    if overflowed:
                        print("[音频录制] 警告: 音频缓冲区溢出")
                    
                    # 如果采样率不匹配，进行简单的降采样 (仅支持 48k -> 16k)
                    processed_chunk = None
                    if device_rate == 48000 and self.sample_rate == 16000:
                         # 简单的隔点采样 (3倍降采样)
                         downsampled = audio_chunk[::3] 
                         processed_chunk = downsampled.flatten()
                    elif device_rate != self.sample_rate:
                        # 其他情况暂时原样保存（ASR可能会不准）
                        processed_chunk = audio_chunk.flatten()
                    else:
                        # 16k -> 16k
                        processed_chunk = audio_chunk.flatten()
                    
                    # 保存到完整音频数据
                    self.audio_data.append(processed_chunk)
                    
                    # 实时分段逻辑
                    if self.realtime_transcribe and self.segment_callback:
                        # 添加到当前分段
                        self.current_segment.append(processed_chunk)
                        
                        # 检测是否为静音
                        is_silence = self._check_silence(processed_chunk)
                        
                        # 检测是否为人声（过滤非人声噪音）
                        is_voice = self._is_voice(processed_chunk) if not is_silence else False
                        
                        if not is_silence and is_voice:
                            # 有声音且是人声
                            self.last_audio_time = time.time()
                            self.consecutive_silence_chunks = 0  # 有声音，重置静音计数
                            self.has_voice_in_segment = True  # 标记当前分段有有效语音
                        else:
                            # 静音或非人声噪音
                            self.consecutive_silence_chunks += 1  # 静音，增加计数
                        
                        # 检查是否应触发分段
                        if self._should_trigger_segment():
                            self._trigger_segment()
                    
        except Exception as e:
            print(f"[音频录制] 错误: {e}")
            self.is_recording = False
    
    def _mock_recording_loop(self):
        """模拟录音循环（当 sounddevice 不可用时）"""
        while self.is_recording:
            # 生成100ms的模拟数据
            chunk_samples = int(self.sample_rate * 0.1)
            mock_chunk = [int(np.random.randint(-1000, 1000)) for _ in range(chunk_samples)]
            self.audio_data.append(mock_chunk)
            time.sleep(0.1)
    
    def cleanup(self):
        """清理资源"""
        if self.is_recording:
            self.cancel()
        print("[音频录制] 清理完成")
