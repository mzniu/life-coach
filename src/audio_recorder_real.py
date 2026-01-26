"""
真实的音频录制器（使用 sounddevice + Silero VAD）
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
        REALTIME_MIN_SILENCE_DURATION,
        REALTIME_MAX_SEGMENT_DURATION,
        AUDIO_NORMALIZE_ENABLED,
        AUDIO_NORMALIZE_TARGET,
        AUDIO_HIGHPASS_FILTER_ENABLED,
        AUDIO_HIGHPASS_ALPHA,
        AUDIO_MIN_RMS_THRESHOLD,
    )
    USE_CONFIG = True
except ImportError:
    # 默认值
    REALTIME_MIN_SILENCE_DURATION = 1.2
    REALTIME_MAX_SEGMENT_DURATION = 10.0
    AUDIO_NORMALIZE_ENABLED = True
    AUDIO_NORMALIZE_TARGET = 0.95
    AUDIO_HIGHPASS_FILTER_ENABLED = True
    AUDIO_HIGHPASS_ALPHA = 0.95
    AUDIO_MIN_RMS_THRESHOLD = 0.001
    USE_CONFIG = False

# 导入 Silero VAD
try:
    from src.vad_silero import SileroVAD
    HAS_SILERO_VAD = True
except ImportError:
    HAS_SILERO_VAD = False
    print("[音频录制] 警告: Silero VAD 不可用，请安装 sherpa-onnx")

try:
    import sounddevice as sd
    REAL_AUDIO = True
except ImportError:
    REAL_AUDIO = False
    print("[音频录制] 警告: sounddevice 未安装，将使用模拟模式")
    print("[音频录制] 安装方法: pip install sounddevice")

class AudioRecorder:
    """音频录制器（真实采集 + Silero VAD 实时分段）"""
    
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
        
        # 实时转录支持（使用 Silero VAD）
        self.realtime_transcribe = realtime_transcribe
        self.segment_callback = segment_callback
        self.vad = None
        self.segment_count = 0
        
        # 初始化 VAD（如果启用实时转录）
        if self.realtime_transcribe and HAS_SILERO_VAD:
            try:
                from src.config import (REALTIME_MIN_SPEECH_DURATION, REALTIME_VAD_THRESHOLD, 
                                       REALTIME_MAX_SPEECH_DURATION, REALTIME_SPEECH_PAD_MS)
                self.vad = SileroVAD(
                    sample_rate=sample_rate,
                    min_silence_duration=REALTIME_MIN_SILENCE_DURATION,
                    min_speech_duration=REALTIME_MIN_SPEECH_DURATION,
                    threshold=REALTIME_VAD_THRESHOLD,
                    max_segment_duration=REALTIME_MAX_SEGMENT_DURATION,
                    max_speech_duration=REALTIME_MAX_SPEECH_DURATION,
                    speech_pad_ms=REALTIME_SPEECH_PAD_MS,
                    on_segment_callback=self._on_vad_segment
                )
                print(f"[音频录制] Silero VAD 已启用")
            except Exception as e:
                print(f"[音频录制] 警告: Silero VAD 初始化失败: {e}")
                print(f"[音频录制] 将禁用实时转录")
                self.realtime_transcribe = False
        elif self.realtime_transcribe and not HAS_SILERO_VAD:
            print(f"[音频录制] 警告: Silero VAD 不可用，实时转录已禁用")
            self.realtime_transcribe = False
        
        if REAL_AUDIO:
            try:
                print(f"[音频录制] 初始化真实音频录制器 ({sample_rate}Hz, {channels}声道)")
                default_input = sd.query_devices(kind='input')
                print(f"[音频录制] 默认输入设备: {default_input['name']}")
            except Exception as e:
                print(f"[音频录制] 错误: 无法初始化音频设备 ({e})")
                print("[音频录制] 可能原因: 未插入麦克风或声卡驱动未加载")
                REAL_AUDIO = False
        else:
            print("[音频录制] 初始化模拟音频录制器")
        
    def _preprocess_audio(self, audio_samples: np.ndarray) -> np.ndarray:
        """音频预处理：仅保留归一化，暂时禁用高通滤波以确保稳定性"""
        if len(audio_samples) == 0:
            return audio_samples
        
        # 仅进行音量归一化
        if AUDIO_NORMALIZE_ENABLED:
            max_abs = np.abs(audio_samples).max()
            if max_abs > 0 and max_abs < 1e10:  # 防止数值异常
                # 归一化到配置的目标幅度
                target = min(AUDIO_NORMALIZE_TARGET, 0.95)  # 确保不超过0.95
                audio_samples = audio_samples * (target / max_abs)
        
        return audio_samples
    
    def _on_vad_segment(self, audio_samples: np.ndarray, metadata: dict):
        """VAD 分段回调"""
        self.segment_count += 1
        
        # [修复] 确保数据类型正确且在有效范围内
        try:
            # 转换为float32（如果不是）
            if audio_samples.dtype != np.float32:
                audio_samples = audio_samples.astype(np.float32)
            
            # VAD已经进行了归一化，这里只需要验证数据范围
            max_val = np.abs(audio_samples).max()
            
            # 音频质量检查
            rms = np.sqrt(np.mean(audio_samples ** 2))
            peak = max_val
            
            print(f"[VAD分段] 第 {self.segment_count} 段: "
                  f"duration={metadata.get('duration', 0):.2f}s, "
                  f"samples={len(audio_samples)}, "
                  f"RMS={rms:.4f}, Peak={peak:.4f}")
            
            # 过滤静音片段（RMS过低）
            if rms < AUDIO_MIN_RMS_THRESHOLD:
                print(f"[VAD分段] 警告: 音量过低 (RMS={rms:.4f})，跳过")
                return
            
            # 不再进行额外的预处理，VAD已经输出归一化后的数据
            processed_audio = audio_samples
            
            # 调用外部回调
            if self.segment_callback:
                metadata['segment_index'] = self.segment_count
                metadata['rms'] = rms
                metadata['peak'] = peak
                self.segment_callback(processed_audio, metadata)
                
        except Exception as e:
            print(f"[VAD分段错误] 处理第 {self.segment_count} 段失败: {e}")
            import traceback
            traceback.print_exc()
    
    def start(self):
        """开始录音"""
        if self.is_recording:
            raise Exception("录音已在进行中")
            
        self.is_recording = True
        self.start_time = time.time()
        self.audio_data = []
        self.segment_count = 0
        
        # 重置 VAD
        if self.vad:
            self.vad.reset()
        
        if REAL_AUDIO:
            print("[音频录制] 开始录音（真实采集 + Silero VAD）")
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
        
        # 刷新 VAD，处理剩余音频
        if self.vad:
            print(f"[音频录制] 停止录音，准备flush VAD（已产生 {self.segment_count} 个分段）")
            self.vad.flush()
            print(f"[音频录制] VAD flush完成（最终 {self.segment_count} 个分段）")
        
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
    
    def _real_recording_loop(self):
        """真实录音循环（使用 Silero VAD）"""
        chunk_duration = 0.1  # 100ms 每块
        
        # 尝试确定可用的采样率
        device_rate = self.sample_rate
        try:
            sd.check_input_settings(device=None, channels=self.channels, dtype='int16', 
                                   extra_settings=None, samplerate=self.sample_rate)
        except Exception as e:
            print(f"[音频录制] 警告: 设备不支持 {self.sample_rate}Hz ({e})")
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
                    
                    # 如果采样率不匹配，进行简单的降采样
                    processed_chunk = None
                    if device_rate == 48000 and self.sample_rate == 16000:
                        # 简单的隔点采样 (3倍降采样)
                        downsampled = audio_chunk[::3]
                        processed_chunk = downsampled.flatten()
                    elif device_rate != self.sample_rate:
                        # 其他情况暂时原样保存
                        processed_chunk = audio_chunk.flatten()
                    else:
                        # 16k -> 16k
                        processed_chunk = audio_chunk.flatten()
                    
                    # 保存到完整音频数据
                    self.audio_data.append(processed_chunk)
                    
                    # 送入 VAD 处理（如果启用）
                    if self.vad:
                        # 转换为 float32 并归一化
                        audio_float = processed_chunk.astype(np.float32) / 32768.0
                        self.vad.process_chunk(audio_float)
                    
        except Exception as e:
            print(f"[音频录制] 错误: {e}")
            import traceback
            traceback.print_exc()
            self.is_recording = False
    
    def _mock_recording_loop(self):
        """模拟录音循环（当 sounddevice 不可用时）"""
        while self.is_recording:
            # 生成100ms的模拟数据
            chunk_samples = int(self.sample_rate * 0.1)
            mock_chunk = np.random.randint(-1000, 1000, chunk_samples, dtype=np.int16)
            self.audio_data.append(mock_chunk)
            time.sleep(0.1)

    
    def cleanup(self):
        """清理资源"""
        if self.is_recording:
            self.cancel()
        print("[音频录制] 清理完成")
