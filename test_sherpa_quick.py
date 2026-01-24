"""
快速测试 sherpa-onnx 的流式VAD功能
"""

import sherpa_onnx
import numpy as np
import time

def test_vad():
    """测试 Silero VAD"""
    print("=" * 60)
    print("测试 Silero VAD")
    print("=" * 60)
    
    try:
        from pathlib import Path
        
        # 检查模型文件
        model_path = Path("models/sherpa/silero_vad.onnx")
        if not model_path.exists():
            print(f"✗ VAD 模型不存在: {model_path.absolute()}")
            print("  请先下载模型")
            return False
        
        print(f"✓ 找到 VAD 模型: {model_path}")
        
        # 创建 VAD 配置
        config = sherpa_onnx.VadModelConfig()
        config.silero_vad.model = str(model_path.absolute())
        config.sample_rate = 16000
        config.num_threads = 1
        config.provider = "cpu"
        
        vad = sherpa_onnx.VoiceActivityDetector(config, buffer_size_in_seconds=60)
        
        print("✓ Silero VAD 创建成功")
        
        # 生成测试音频（模拟）
        # 0.5秒静音 + 1秒语音（模拟） + 0.5秒静音
        sample_rate = 16000
        silence = np.zeros(int(0.5 * sample_rate), dtype=np.float32)
        speech = np.random.randn(int(1.0 * sample_rate)).astype(np.float32) * 0.3
        test_audio = np.concatenate([silence, speech, silence])
        
        print(f"\n测试音频: {len(test_audio)/sample_rate:.1f}秒")
        
        # 处理音频（分块）
        chunk_size = int(0.1 * sample_rate)  # 100ms chunks
        num_chunks = len(test_audio) // chunk_size
        
        segments = []
        in_speech = False
        segment_start = 0
        
        for i in range(num_chunks):
            chunk = test_audio[i*chunk_size:(i+1)*chunk_size]
            vad.accept_waveform(chunk)
            
            if vad.is_speech():
                if not in_speech:
                    segment_start = i * 0.1
                    in_speech = True
                    print(f"  [{segment_start:.1f}s] 检测到语音开始")
            else:
                if in_speech:
                    segment_end = i * 0.1
                    in_speech = False
                    segments.append((segment_start, segment_end))
                    print(f"  [{segment_end:.1f}s] 检测到语音结束 (时长: {segment_end-segment_start:.1f}s)")
        
        print(f"\n✓ 检测到 {len(segments)} 个语音段")
        
        return True
        
    except Exception as e:
        print(f"✗ VAD 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("\nsherpa-onnx 快速功能测试\n")
    
    print("当前支持的功能:")
    print("1. ✓ Silero VAD (语音活动检测)")
    print("2. ✓ 流式ASR (实时语音识别)")
    print("3. ✓ 非流式ASR (离线语音识别)")
    print("4. ✓ TTS (语音合成)")
    print("5. ✓ 关键词检测")
    print()
    
    # 测试 VAD
    test_vad()
    
    print("\n" + "=" * 60)
    print("下载所需文件")
    print("=" * 60)
    print("""
1. Silero VAD 模型:
   https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/silero_vad.onnx
   下载到: models/sherpa/
   
2. 中文 ASR 模型（Paraformer 流式）:
   https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-streaming-paraformer-bilingual-zh-en.tar.bz2
   下载并解压到: models/sherpa/
   
3. 或使用 Python 自动下载:
   python -m sherpa_onnx.download --vad
""")


if __name__ == "__main__":
    main()
