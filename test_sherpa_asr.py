"""
测试 Sherpa-ONNX Paraformer ASR
"""

import sys
import numpy as np
import wave
from pathlib import Path

# 添加 src 目录到路径
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

from asr_sherpa import SherpaASR, ParaformerModel


def generate_test_audio(duration=3.0, sample_rate=16000):
    """生成测试音频（静音）"""
    num_samples = int(duration * sample_rate)
    audio = np.zeros(num_samples, dtype=np.float32)
    return audio


def test_sherpa_asr():
    """测试 Sherpa ASR 基本功能"""
    print("=" * 60)
    print("测试 Sherpa-ONNX Paraformer ASR")
    print("=" * 60)
    
    # 模型路径
    model_dir = "models/sherpa/paraformer"
    
    print(f"\n1. 初始化 ASR...")
    try:
        asr = SherpaASR(model_dir=model_dir)
        print("   ✓ ASR 初始化成功")
    except Exception as e:
        print(f"   ✗ ASR 初始化失败: {e}")
        return False
    
    print(f"\n2. 测试空音频识别...")
    try:
        audio = generate_test_audio(duration=1.0)
        text = asr.transcribe(audio)
        print(f"   识别结果: '{text}'")
        print(f"   ✓ 空音频识别完成")
    except Exception as e:
        print(f"   ✗ 空音频识别失败: {e}")
        return False
    
    print(f"\n3. 测试流式识别...")
    try:
        stream = asr.recognizer.create_stream()
        
        # 模拟 3 个音频块
        for i in range(3):
            chunk = generate_test_audio(duration=0.5)
            text, is_endpoint, stream = asr.transcribe_stream(chunk, stream)
            print(f"   块 {i+1}: text='{text}', endpoint={is_endpoint}")
        
        print(f"   ✓ 流式识别完成")
    except Exception as e:
        print(f"   ✗ 流式识别失败: {e}")
        return False
    
    print(f"\n4. 测试兼容接口...")
    try:
        model = ParaformerModel(model_path=model_dir)
        audio = generate_test_audio(duration=1.0)
        segments, info = model.transcribe(audio)
        
        print(f"   语言: {info.language}")
        print(f"   语言概率: {info.language_probability}")
        print(f"   识别段数: {len(segments)}")
        if segments:
            print(f"   文本: '{segments[0].text}'")
        
        print(f"   ✓ 兼容接口测试完成")
    except Exception as e:
        print(f"   ✗ 兼容接口测试失败: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✓ 所有测试通过")
    print("=" * 60)
    return True


def test_with_real_audio():
    """使用真实音频测试"""
    print("\n" + "=" * 60)
    print("测试真实音频识别")
    print("=" * 60)
    
    # 查找测试音频文件
    test_audio_dir = Path("test_audio")
    if not test_audio_dir.exists():
        print(f"\n✗ 测试音频目录不存在: {test_audio_dir}")
        print("  请提供测试音频文件")
        return False
    
    audio_files = list(test_audio_dir.glob("*.wav"))
    if not audio_files:
        print(f"\n✗ 未找到测试音频文件: {test_audio_dir}/*.wav")
        return False
    
    # 初始化 ASR
    model_dir = "models/sherpa/paraformer"
    try:
        asr = SherpaASR(model_dir=model_dir)
    except Exception as e:
        print(f"\n✗ ASR 初始化失败: {e}")
        return False
    
    # 测试每个音频文件
    print(f"\n找到 {len(audio_files)} 个测试文件:")
    for audio_file in audio_files[:5]:  # 最多测试 5 个
        print(f"\n{audio_file.name}:")
        try:
            import time
            start = time.time()
            text = asr.transcribe_file(str(audio_file))
            elapsed = time.time() - start
            
            # 计算音频时长
            with wave.open(str(audio_file), 'rb') as wf:
                duration = wf.getnframes() / wf.getframerate()
            
            rtf = elapsed / duration if duration > 0 else 0
            
            print(f"  识别结果: {text}")
            print(f"  音频时长: {duration:.2f}s")
            print(f"  识别耗时: {elapsed:.3f}s")
            print(f"  实时因子: {rtf:.2f}x")
        except Exception as e:
            print(f"  ✗ 识别失败: {e}")
    
    return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="测试 Sherpa-ONNX ASR")
    parser.add_argument("--real-audio", action="store_true", help="使用真实音频测试")
    
    args = parser.parse_args()
    
    # 基本功能测试
    success = test_sherpa_asr()
    
    # 真实音频测试
    if args.real_audio and success:
        test_with_real_audio()
