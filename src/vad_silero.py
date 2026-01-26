"""
Silero VAD 封装
使用 sherpa-onnx 的 Silero VAD 进行语音活动检测
"""

import numpy as np
import sherpa_onnx
from pathlib import Path
from typing import Optional, Callable
import time


class SileroVAD:
    """Silero VAD 封装类"""
    
    def __init__(
        self,
        model_path: str = "models/sherpa/silero_vad.onnx",
        sample_rate: int = 16000,
        min_silence_duration: float = 0.8,
        min_speech_duration: float = 0.1,
        threshold: float = 0.35,
        max_segment_duration: float = 10.0,
        max_speech_duration: float = 30.0,
        speech_pad_ms: int = 300,
        on_segment_callback: Optional[Callable] = None
    ):
        """
        初始化 Silero VAD
        
        Args:
            model_path: VAD 模型路径
            sample_rate: 音频采样率
            min_silence_duration: 最小静音时长（秒），触发分段（推荐0.8s）
            min_speech_duration: 最小语音时长（秒），过滤短语音（推荐0.1s）
            threshold: VAD 阈值 (0.0-1.0)，推荐0.35平衡灵敏度
            max_segment_duration: 最大分段时长（秒），超过强制分段
            max_speech_duration: 最大语音时长（秒）
            speech_pad_ms: 语音段前后填充时长（毫秒），防止首尾截断（推荐300ms）
            on_segment_callback: 分段回调函数
        """
        self.model_path = Path(model_path)
        self.sample_rate = sample_rate
        self.min_silence_duration = min_silence_duration
        self.min_speech_duration = min_speech_duration
        self.threshold = threshold
        self.max_segment_duration = max_segment_duration
        self.max_speech_duration = max_speech_duration
        self.speech_pad_ms = speech_pad_ms
        self.on_segment_callback = on_segment_callback
        
        # 检查模型文件
        if not self.model_path.exists():
            raise FileNotFoundError(f"VAD 模型不存在: {self.model_path}")
        
        # 创建 VAD
        self._create_vad()
        
        # 分段管理
        self.segment_index = 0
        self.segment_start_time = time.time()
        
        print(f"[VAD] Silero VAD 已初始化")
        print(f"  模型: {self.model_path}")
        print(f"  min_silence: {min_silence_duration}s")
        print(f"  min_speech: {min_speech_duration}s")
        print(f"  threshold: {threshold}")
        print(f"  speech_pad: {speech_pad_ms}ms（防止首尾截断）")
    
    def _create_vad(self):
        """创建 Silero VAD 实例"""
        config = sherpa_onnx.VadModelConfig()
        config.silero_vad.model = str(self.model_path.absolute())
        config.sample_rate = self.sample_rate
        config.num_threads = 1
        config.provider = "cpu"
        config.silero_vad.min_silence_duration = self.min_silence_duration
        config.silero_vad.min_speech_duration = self.min_speech_duration
        config.silero_vad.max_speech_duration = self.max_speech_duration
        config.silero_vad.threshold = self.threshold
        
        # [优化] window_size 控制VAD的窗口大小，默认512
        # 较小的window_size可以更快响应，但可能增加误检
        # 使用256以更快响应语音开始，减少首部截断
        config.silero_vad.window_size = 256
        
        # [关键] speech_pad_ms: 在语音段前后各填充指定毫秒的音频
        # 这是防止首尾截断的核心参数
        config.silero_vad.speech_pad_ms = self.speech_pad_ms
        
        # buffer_size_in_seconds 设置为最大分段时长的 2 倍
        buffer_size = int(self.max_segment_duration * 2)
        self.vad = sherpa_onnx.VoiceActivityDetector(config, buffer_size_in_seconds=buffer_size)
    
    def process_chunk(self, audio_chunk: np.ndarray) -> None:
        """
        处理音频块
        
        Args:
            audio_chunk: 音频数据 (float32, shape: [samples])
        """
        # 确保是 float32 格式
        if audio_chunk.dtype != np.float32:
            audio_chunk = audio_chunk.astype(np.float32)
        
        # 如果是 int16 范围，归一化到 [-1, 1]
        if audio_chunk.max() > 1.0 or audio_chunk.min() < -1.0:
            audio_chunk = audio_chunk / 32768.0
        
        # 送入 VAD
        self.vad.accept_waveform(audio_chunk)
        
        # 检查是否有完整的语音段
        self._check_segments()
        
        # 检查是否超过最大分段时长
        self._check_max_duration()
    
    def _check_segments(self) -> None:
        """检查并处理完整的语音段"""
        while not self.vad.empty():
            segment = self.vad.front
            self.vad.pop()
            
            # 获取语音段信息
            start_time = segment.start / self.sample_rate
            duration = len(segment.samples) / self.sample_rate
            
            self.segment_index += 1
            
            print(f"[VAD] 第 {self.segment_index} 段: "
                  f"start={start_time:.2f}s, duration={duration:.2f}s, "
                  f"samples={len(segment.samples)}")
            
            # 调用回调
            if self.on_segment_callback:
                metadata = {
                    'segment_index': self.segment_index,
                    'start_time': start_time,
                    'duration': duration,
                    'sample_rate': self.sample_rate
                }
                # sherpa-onnx 的 segment.samples 已经是 numpy.ndarray[float32] 格式
                # 数据范围已经是 [-1, 1]，不需要额外转换
                samples_array = segment.samples
                
                # 验证数据类型和范围
                if not isinstance(samples_array, np.ndarray):
                    samples_array = np.array(samples_array, dtype=np.float32)
                elif samples_array.dtype != np.float32:
                    samples_array = samples_array.astype(np.float32)
                
                # 调试：输出实际的数据范围
                actual_min = samples_array.min()
                actual_max = samples_array.max()
                print(f"[VAD] 分段 #{self.segment_index} 数据范围: [{actual_min:.4f}, {actual_max:.4f}]")
                
                self.on_segment_callback(samples_array, metadata)
            
            # 重置分段开始时间
            self.segment_start_time = time.time()
    
    def _check_max_duration(self) -> None:
        """检查是否超过最大分段时长，超过则强制触发"""
        elapsed = time.time() - self.segment_start_time
        
        if elapsed >= self.max_segment_duration:
            print(f"[VAD] 达到最大分段时长 {self.max_segment_duration}s，强制分段")
            self.flush()
    
    def flush(self) -> None:
        """刷新 VAD，处理剩余的音频"""
        print(f"[VAD] 开始flush，当前队列是否为空: {self.vad.empty()}")
        self.vad.flush()
        print(f"[VAD] flush后队列是否为空: {self.vad.empty()}")
        self._check_segments()
        print(f"[VAD] 处理完所有分段")
    
    def reset(self) -> None:
        """重置 VAD 状态"""
        self.vad.reset()
        self.segment_index = 0
        self.segment_start_time = time.time()
        print("[VAD] 已重置")
    
    def is_speech(self) -> bool:
        """
        检查当前是否在语音段中
        
        Returns:
            True 如果检测到语音
        """
        return self.vad.is_speech_detected()


# 向后兼容：提供与旧接口相同的函数
def create_vad(
    sample_rate: int = 16000,
    min_silence_duration: float = 1.2,
    **kwargs
) -> SileroVAD:
    """
    创建 VAD 实例（向后兼容接口）
    
    Args:
        sample_rate: 采样率
        min_silence_duration: 最小静音时长
        **kwargs: 其他参数
    
    Returns:
        SileroVAD 实例
    """
    return SileroVAD(
        sample_rate=sample_rate,
        min_silence_duration=min_silence_duration,
        **kwargs
    )
