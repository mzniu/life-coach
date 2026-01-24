"""
Sherpa-ONNX ASR 封装
使用 sherpa-onnx 的流式 Paraformer 进行语音识别
"""

import numpy as np
import sherpa_onnx
from pathlib import Path
from typing import Optional, Callable
import time


class SherpaASR:
    """Sherpa-ONNX 流式 ASR 封装"""
    
    def __init__(
        self,
        model_dir: str = "models/sherpa/paraformer",
        sample_rate: int = 16000,
        num_threads: int = 2,
        decoding_method: str = "greedy_search"
    ):
        """
        初始化 Sherpa ASR
        
        Args:
            model_dir: 模型目录
            sample_rate: 音频采样率
            num_threads: 线程数
            decoding_method: 解码方法 (greedy_search 或 modified_beam_search)
        """
        self.model_dir = Path(model_dir)
        self.sample_rate = sample_rate
        self.num_threads = num_threads
        self.decoding_method = decoding_method
        
        # 检查模型文件
        self._check_model_files()
        
        # 创建识别器
        self._create_recognizer()
        
        print(f"[ASR] Sherpa-ONNX Paraformer 已初始化")
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
    
    def _create_recognizer(self):
        """创建流式识别器"""
        # 配置 Paraformer 模型
        config = sherpa_onnx.OnlineRecognizerConfig(
            model_config=sherpa_onnx.OnlineModelConfig(
                paraformer=sherpa_onnx.OnlineParaformerModelConfig(
                    encoder=str(self.model_dir / "encoder.int8.onnx"),
                    decoder=str(self.model_dir / "decoder.int8.onnx"),
                ),
                tokens=str(self.model_dir / "tokens.txt"),
                num_threads=self.num_threads,
                provider="cpu",
                debug=False,
            ),
            decoding_method=self.decoding_method,
            max_active_paths=4,
        )
        
        self.recognizer = sherpa_onnx.OnlineRecognizer(config)
    
    def transcribe_stream(
        self,
        audio_chunk: np.ndarray,
        stream: Optional[sherpa_onnx.OnlineStream] = None
    ) -> tuple:
        """
        流式识别音频块
        
        Args:
            audio_chunk: 音频数据 (float32, [-1, 1])
            stream: 流对象（如果为 None 则创建新流）
        
        Returns:
            (text, is_endpoint, stream)
        """
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
        
        # 获取结果
        text = self.recognizer.get_result(stream).text
        is_endpoint = self.recognizer.is_endpoint(stream)
        
        # 如果是端点，重置流
        if is_endpoint:
            self.recognizer.reset(stream)
        
        return text, is_endpoint, stream
    
    def transcribe(self, audio_data: np.ndarray) -> str:
        """
        识别完整音频（非流式，兼容接口）
        
        Args:
            audio_data: 音频数据 (float32 或 int16)
        
        Returns:
            识别文本
        """
        # 确保是 float32 格式
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)
        
        # 如果是 int16 范围，归一化
        if audio_data.max() > 1.0 or audio_data.min() < -1.0:
            audio_data = audio_data / 32768.0
        
        # 创建流
        stream = self.recognizer.create_stream()
        
        # 分块处理（每次 0.1 秒）
        chunk_size = int(0.1 * self.sample_rate)
        num_chunks = len(audio_data) // chunk_size + 1
        
        for i in range(num_chunks):
            start = i * chunk_size
            end = min((i + 1) * chunk_size, len(audio_data))
            
            if start >= len(audio_data):
                break
            
            chunk = audio_data[start:end]
            stream.accept_waveform(self.sample_rate, chunk)
            
            while self.recognizer.is_ready(stream):
                self.recognizer.decode_stream(stream)
        
        # 获取最终结果
        result = self.recognizer.get_result(stream)
        return result.text
    
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
