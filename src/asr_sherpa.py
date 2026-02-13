"""
Sherpa-ONNX ASR 引擎
使用流式 Paraformer 模型进行语音识别
"""

import numpy as np
import sherpa_onnx
import time
from pathlib import Path
from typing import Optional, Dict, Any


class SherpaASREngine:
    """Sherpa-ONNX ASR 引擎 - 使用流式 Paraformer 模型"""
    
    def __init__(
        self,
        model_dir: str = "models/sherpa/paraformer",
        use_int8: bool = True,
        sample_rate: int = 16000,
        num_threads: int = 4,
        provider: str = "cpu"
    ):
        """
        初始化 Sherpa-ONNX ASR 引擎
        
        Args:
            model_dir: Paraformer 模型目录
            use_int8: 是否使用 int8 量化模型（更快）
            sample_rate: 音频采样率
            num_threads: 推理线程数
            provider: 推理后端 ("cpu", "coreml", "cuda")
        """
        self.model_dir = Path(model_dir)
        self.sample_rate = sample_rate
        self.num_threads = num_threads
        self.provider = provider
        
        if use_int8:
            encoder_model = self.model_dir / "encoder.int8.onnx"
            decoder_model = self.model_dir / "decoder.int8.onnx"
        else:
            encoder_model = self.model_dir / "encoder.onnx"
            decoder_model = self.model_dir / "decoder.onnx"
        
        tokens_file = self.model_dir / "tokens.txt"
        
        if not encoder_model.exists():
            raise FileNotFoundError(f"Encoder model not found: {encoder_model}")
        if not decoder_model.exists():
            raise FileNotFoundError(f"Decoder model not found: {decoder_model}")
        if not tokens_file.exists():
            raise FileNotFoundError(f"Tokens file not found: {tokens_file}")
        
        print(f"[Sherpa-ONNX] 初始化流式 Paraformer 模型...")
        print(f"  Encoder: {encoder_model.name}")
        print(f"  Decoder: {decoder_model.name}")
        print(f"  Threads: {num_threads}")
        print(f"  Provider: {provider}")
        
        start_time = time.time()
        self.recognizer = sherpa_onnx.OnlineRecognizer.from_paraformer(
            tokens=str(tokens_file),
            encoder=str(encoder_model),
            decoder=str(decoder_model),
            num_threads=num_threads,
            sample_rate=sample_rate,
            provider=provider,
            enable_endpoint_detection=True,
            rule1_min_trailing_silence=3.0,
            rule2_min_trailing_silence=2.0,
            rule3_min_utterance_length=30.0
        )
        init_time = time.time() - start_time
        
        print(f"[Sherpa-ONNX] 流式 Paraformer 模型加载完成 ({init_time:.2f}s)")
        
        self.stats = {
            'total_audio_duration': 0.0,
            'total_transcribe_time': 0.0,
            'transcription_count': 0,
            'avg_rtf': 0.0
        }
    
    def transcribe(self, audio_data: np.ndarray) -> Dict[str, Any]:
        """
        转录音频数据
        
        Args:
            audio_data: 音频数据 (float32, 16kHz)
        
        Returns:
            转录结果字典
        """
        start_time = time.time()
        
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)
        
        max_val = np.abs(audio_data).max()
        if max_val > 1.0:
            audio_data = audio_data / 32768.0
        
        audio_duration = len(audio_data) / self.sample_rate
        
        stream = self.recognizer.create_stream()
        stream.accept_waveform(self.sample_rate, audio_data)
        
        text_parts = []
        while self.recognizer.is_ready(stream):
            self.recognizer.decode_stream(stream)
            if self.recognizer.is_endpoint(stream):
                text = self.recognizer.get_result(stream)
                if isinstance(text, str):
                    text_parts.append(text)
                elif hasattr(text, 'text'):
                    text_parts.append(text.text)
                self.recognizer.reset(stream)
        
        if not self.recognizer.is_endpoint(stream):
            text = self.recognizer.get_result(stream)
            if isinstance(text, str):
                text_parts.append(text)
            elif hasattr(text, 'text'):
                text_parts.append(text.text)
        
        result_text = ''.join(text_parts)
        transcribe_time = time.time() - start_time
        
        self.stats['total_audio_duration'] += audio_duration
        self.stats['total_transcribe_time'] += transcribe_time
        self.stats['transcription_count'] += 1
        self.stats['avg_rtf'] = self.stats['total_transcribe_time'] / max(self.stats['total_audio_duration'], 0.001)
        
        return {
            'text': result_text,
            'duration': audio_duration,
            'transcribe_time': transcribe_time,
            'rtf': transcribe_time / max(audio_duration, 0.001),
            'engine': 'sherpa-paraformer-streaming'
        }
    
    def transcribe_stream(self, audio_data: np.ndarray, **kwargs) -> str:
        """
        流式转录接口（兼容现有代码）
        """
        result = self.transcribe(audio_data)
        return result['text']
    
    def get_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        return self.stats.copy()
    
    def __str__(self):
        return f"SherpaASREngine(model=streaming-paraformer, threads={self.num_threads})"


if __name__ == "__main__":
    print("Testing Sherpa-ONNX Streaming Paraformer...")
    
    engine = SherpaASREngine(
        model_dir="models/sherpa/paraformer",
        use_int8=True,
        num_threads=4
    )
    
    print("\nTest 1: Silence...")
    audio = np.zeros(16000, dtype=np.float32)
    result = engine.transcribe(audio)
    print(f"  Result: '{result['text']}'")
    print(f"  Time: {result['transcribe_time']:.3f}s")
    
    print("\nTest 2: Random noise...")
    audio = np.random.randn(16000).astype(np.float32) * 0.1
    result = engine.transcribe(audio)
    print(f"  Result: '{result['text']}'")
    print(f"  Time: {result['transcribe_time']:.3f}s")
    
    print("\nAll tests passed!")
