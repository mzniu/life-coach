"""
Sherpa-ONNX ASR 封装
使用 sherpa-onnx 的 Streaming Paraformer 进行语音识别
"""

import numpy as np
from pathlib import Path
from typing import Optional
import time
import os
import sys

# 导入配置
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from src.config import ASR_CONTEXT_SIZE, ASR_USE_CONTEXT
    USE_CONFIG = True
except ImportError:
    ASR_CONTEXT_SIZE = 2
    ASR_USE_CONTEXT = True
    USE_CONFIG = False


class SherpaASR:
    """Sherpa-ONNX Streaming Paraformer ASR 封装"""
    
    def __init__(
        self,
        model_dir: str = "models/sherpa/paraformer",
        sample_rate: int = 16000,
        num_threads: int = 2,
        context_size: int = None
    ):
        """
        初始化 Sherpa ASR
        
        Args:
            model_dir: 模型目录
            sample_rate: 音频采样率
            num_threads: 线程数
            context_size: 保留前N个分段的上下文（None则使用配置文件）
        """
        import sherpa_onnx
        
        self.model_dir = Path(model_dir)
        self.sample_rate = sample_rate
        self.num_threads = num_threads
        self.context_size = context_size if context_size is not None else ASR_CONTEXT_SIZE
        self.use_context = ASR_USE_CONTEXT
        
        # 上下文管理
        self.context_history = []  # 保存最近的识别结果
        
        # 检查模型文件
        self._check_model_files()
        
        # 创建在线识别器 - 使用 from_paraformer 工厂方法
        self.recognizer = sherpa_onnx.OnlineRecognizer.from_paraformer(
            encoder=str(self.model_dir / "encoder.int8.onnx"),
            decoder=str(self.model_dir / "decoder.int8.onnx"),
            tokens=str(self.model_dir / "tokens.txt"),
            num_threads=num_threads,
            sample_rate=sample_rate,
            feature_dim=80,
            decoding_method="greedy_search",
        )
        
        print(f"[ASR] Sherpa-ONNX Streaming Paraformer 已初始化")
        print(f"  模型: {self.model_dir}")
        print(f"  采样率: {sample_rate}Hz")
        print(f"  线程数: {num_threads}")
    
    def _check_model_files(self):
        """检查必需的模型文件"""
        required_files = [
            "encoder.int8.onnx",
            "decoder.int8.onnx", 
            "tokens.txt"
        ]
        
        # 如果是 paraformer 模型，文件名可能不同
        alt_files = [
            "model.int8.onnx",
            "encoder.onnx",
            "decoder.onnx"
        ]
        
        if not self.model_dir.exists():
            raise FileNotFoundError(f"模型目录不存在: {self.model_dir}")
        
        # 检查 tokens.txt 是否存在
        if not (self.model_dir / "tokens.txt").exists():
            raise FileNotFoundError(f"tokens.txt 不存在: {self.model_dir / 'tokens.txt'}")
        
        print(f"[ASR] 模型目录: {self.model_dir}")
        print(f"[ASR] 目录内容: {list(self.model_dir.glob('*'))}")
    
    def transcribe(self, audio_data: np.ndarray, use_context: bool = False) -> str:
        """
        识别完整音频（使用 Streaming Paraformer）
        
        Args:
            audio_data: 音频数据 (float32 或 int16)
            use_context: 是否使用上下文提示
        
        Returns:
            识别文本
        """
        import sherpa_onnx
        
        # 确保是 float32 格式
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)
        
        # 如果是 int16 范围，归一化
        if audio_data.max() > 1.0 or audio_data.min() < -1.0:
            audio_data = audio_data / 32768.0
        
        # 创建在线流
        stream = self.recognizer.create_stream()
        
        # 添加上下文提示（如果启用且有历史）
        if use_context and self.context_history:
            # 注意：Paraformer可能不直接支持hotwords，这里仅记录
            context_text = ' '.join(self.context_history[-self.context_size:])
            print(f"[ASR上下文] {context_text}")
        
        stream.accept_waveform(self.sample_rate, audio_data)
        
        # 流式解码
        while self.recognizer.is_ready(stream):
            self.recognizer.decode_stream(stream)
        
        # 获取结果（返回文本字符串）
        result = self.recognizer.get_result(stream)
        text = result.text if hasattr(result, 'text') else str(result)
        
        # 更新上下文历史
        if text.strip():
            self.context_history.append(text.strip())
            if len(self.context_history) > self.context_size:
                self.context_history.pop(0)
        
        return text
    
    def transcribe_stream(
        self,
        audio_chunk: np.ndarray,
        stream: Optional['sherpa_onnx.OnlineStream'] = None
    ) -> tuple:
        """
        流式识别音频块
        
        Args:
            audio_chunk: 音频数据 (float32, [-1, 1])
            stream: 流对象（如果为 None 则创建新流）
        
        Returns:
            (text, is_endpoint, stream)
        """
        import sherpa_onnx
        
        if stream is None:
            stream = self.recognizer.create_stream()
        
        # 确保是 float32 格式
        if audio_chunk.dtype != np.float32:
            audio_chunk = audio_chunk.astype(np.float32)
        
        # 如果是 int16 范围，归一化
        if audio_chunk.max() > 1.0 or audio_chunk.min() < -1.0:
            audio_chunk = audio_chunk / 32768.0
        
        # 送入流
        stream.accept_waveform(self.sample_rate, audio_chunk)
        
        # 解码
        while self.recognizer.is_ready(stream):
            self.recognizer.decode_stream(stream)
        
        # 获取结果（提取文本）
        result = self.recognizer.get_result(stream)
        text = result.text if hasattr(result, 'text') else str(result)
        is_endpoint = self.recognizer.is_endpoint(stream)
        
        # 如果是端点，重置流
        if is_endpoint:
            self.recognizer.reset(stream)
        
        return text, is_endpoint, stream
    
    def transcribe_file(self, audio_file: str) -> str:
        """
        识别音频文件
        
        Args:
            audio_file: 音频文件路径
        
        Returns:
            识别文本
        """
        import wave
        
        with wave.open(audio_file, 'rb') as wf:
            sample_rate = wf.getframerate()
            n_frames = wf.getnframes()
            audio_data = wf.readframes(n_frames)
            
            # 转换为 float32
            audio = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            
            if sample_rate != self.sample_rate:
                print(f"[ASR] 警告: 音频采样率 {sample_rate}Hz 与模型不匹配 {self.sample_rate}Hz")
            
            return self.transcribe(audio)


# 向后兼容：提供与 faster-whisper 类似的接口
class ParaformerModel:
    """兼容 faster-whisper 接口的封装"""
    
    def __init__(self, model_path: str, device: str = "cpu", compute_type: str = "int8"):
        """
        初始化模型（兼容 WhisperModel 接口）
        
        Args:
            model_path: 模型路径
            device: 设备（仅支持 cpu）
            compute_type: 计算类型（仅支持 int8）
        """
        self.asr = SherpaASR(model_dir=model_path)
    
    def transcribe(
        self,
        audio,
        language: str = "zh",
        task: str = "transcribe",
        beam_size: int = 5,
        best_of: int = 5,
        temperature: float = 0.0,
        **kwargs
    ):
        """
        识别音频（兼容 WhisperModel.transcribe 接口）
        
        Args:
            audio: 音频文件路径或音频数据
            language: 语言（忽略，Paraformer 自动检测）
            task: 任务（忽略）
            其他参数: 忽略
        
        Returns:
            (segments, info) 元组
        """
        # 如果是文件路径
        if isinstance(audio, str):
            text = self.asr.transcribe_file(audio)
        else:
            # 假设是 numpy 数组
            text = self.asr.transcribe(audio)
        
        # 构造兼容的返回格式
        class Segment:
            def __init__(self, text):
                self.text = text
                self.start = 0.0
                self.end = 0.0
        
        class Info:
            def __init__(self):
                self.language = "zh"
                self.language_probability = 1.0
                self.duration = 0.0
        
        segments = [Segment(text)]
        info = Info()
        
        return segments, info


def create_asr(model_path: str = "models/sherpa/paraformer", **kwargs):
    """
    创建 ASR 实例（工厂函数）
    
    Args:
        model_path: 模型路径
        **kwargs: 其他参数
    
    Returns:
        SherpaASR 实例
    """
    return SherpaASR(model_dir=model_path, **kwargs)
