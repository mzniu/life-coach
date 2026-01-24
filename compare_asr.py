"""
对比 Whisper 和 Paraformer ASR 性能
"""

import sys
import time
import numpy as np
from pathlib import Path
import wave
import psutil
import os

# 添加 src 目录到路径
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))


def get_memory_usage():
    """获取当前进程内存使用（MB）"""
    process = psutil.Process()
    return process.memory_info().rss / 1024 / 1024


def load_test_audio(audio_file):
    """加载测试音频"""
    with wave.open(audio_file, 'rb') as wf:
        sample_rate = wf.getframerate()
        n_frames = wf.getnframes()
        audio_data = wf.readframes(n_frames)
        
        # 转换为 float32
        audio = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
        duration = n_frames / sample_rate
        
        return audio, sample_rate, duration


def test_whisper(audio, audio_file):
    """测试 Whisper ASR"""
    print("\n" + "=" * 60)
    print("测试 Whisper (faster-whisper)")
    print("=" * 60)
    
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("✗ faster-whisper 未安装")
        return None
    
    # 测试结果
    results = {
        "engine": "Whisper",
        "model": "small",
        "compute_type": "int8"
    }
    
    # 加载模型
    print("\n[1/3] 加载模型...")
    mem_before = get_memory_usage()
    start_time = time.time()
    
    try:
        model = WhisperModel("small", device="cpu", compute_type="int8")
        load_time = time.time() - start_time
        mem_after = get_memory_usage()
        
        results["load_time"] = load_time
        results["memory_usage"] = mem_after - mem_before
        
        print(f"  加载耗时: {load_time:.2f}s")
        print(f"  内存增加: {mem_after - mem_before:.1f}MB")
    except Exception as e:
        print(f"  ✗ 模型加载失败: {e}")
        return None
    
    # 识别音频
    print("\n[2/3] 识别音频...")
    start_time = time.time()
    
    try:
        segments, info = model.transcribe(audio, language="zh")
        text = "".join([seg.text for seg in segments])
        infer_time = time.time() - start_time
        
        results["text"] = text
        results["inference_time"] = infer_time
        results["language"] = info.language
        results["language_prob"] = info.language_probability
        
        print(f"  识别耗时: {infer_time:.3f}s")
        print(f"  语言: {info.language} (概率: {info.language_probability:.2f})")
        print(f"  文本: {text}")
    except Exception as e:
        print(f"  ✗ 识别失败: {e}")
        return None
    
    # 总结
    print("\n[3/3] 总结")
    print(f"  模型: {results['model']} ({results['compute_type']})")
    print(f"  文本长度: {len(text)} 字符")
    
    return results


def test_paraformer(audio, audio_file):
    """测试 Paraformer ASR"""
    print("\n" + "=" * 60)
    print("测试 Paraformer (sherpa-onnx)")
    print("=" * 60)
    
    try:
        from asr_sherpa import SherpaASR
    except ImportError:
        print("✗ asr_sherpa 模块未找到")
        return None
    
    # 测试结果
    results = {
        "engine": "Paraformer",
        "model": "streaming-bilingual",
        "compute_type": "int8"
    }
    
    # 加载模型
    print("\n[1/3] 加载模型...")
    mem_before = get_memory_usage()
    start_time = time.time()
    
    try:
        asr = SherpaASR(model_dir="models/sherpa/paraformer")
        load_time = time.time() - start_time
        mem_after = get_memory_usage()
        
        results["load_time"] = load_time
        results["memory_usage"] = mem_after - mem_before
        
        print(f"  加载耗时: {load_time:.2f}s")
        print(f"  内存增加: {mem_after - mem_before:.1f}MB")
    except Exception as e:
        print(f"  ✗ 模型加载失败: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # 识别音频
    print("\n[2/3] 识别音频...")
    start_time = time.time()
    
    try:
        text = asr.transcribe(audio)
        infer_time = time.time() - start_time
        
        results["text"] = text
        results["inference_time"] = infer_time
        
        print(f"  识别耗时: {infer_time:.3f}s")
        print(f"  文本: {text}")
    except Exception as e:
        print(f"  ✗ 识别失败: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # 总结
    print("\n[3/3] 总结")
    print(f"  模型: {results['model']} ({results['compute_type']})")
    print(f"  文本长度: {len(text)} 字符")
    
    return results


def compare_results(whisper_results, paraformer_results, audio_duration):
    """对比两个引擎的结果"""
    print("\n" + "=" * 60)
    print("对比结果")
    print("=" * 60)
    
    if whisper_results is None and paraformer_results is None:
        print("两个引擎都未成功")
        return
    
    # 对比表格
    print("\n性能指标对比：")
    print("-" * 60)
    print(f"{'指标':<20} {'Whisper':<20} {'Paraformer':<20}")
    print("-" * 60)
    
    # 模型加载
    if whisper_results:
        w_load = f"{whisper_results['load_time']:.2f}s"
        w_mem = f"{whisper_results['memory_usage']:.1f}MB"
    else:
        w_load = "N/A"
        w_mem = "N/A"
    
    if paraformer_results:
        p_load = f"{paraformer_results['load_time']:.2f}s"
        p_mem = f"{paraformer_results['memory_usage']:.1f}MB"
    else:
        p_load = "N/A"
        p_mem = "N/A"
    
    print(f"{'模型加载时间':<20} {w_load:<20} {p_load:<20}")
    print(f"{'内存占用':<20} {w_mem:<20} {p_mem:<20}")
    
    # 识别性能
    if whisper_results:
        w_infer = f"{whisper_results['inference_time']:.3f}s"
        w_rtf = f"{whisper_results['inference_time'] / audio_duration:.2f}x"
        w_text_len = f"{len(whisper_results['text'])} 字符"
    else:
        w_infer = "N/A"
        w_rtf = "N/A"
        w_text_len = "N/A"
    
    if paraformer_results:
        p_infer = f"{paraformer_results['inference_time']:.3f}s"
        p_rtf = f"{paraformer_results['inference_time'] / audio_duration:.2f}x"
        p_text_len = f"{len(paraformer_results['text'])} 字符"
    else:
        p_infer = "N/A"
        p_rtf = "N/A"
        p_text_len = "N/A"
    
    print(f"{'识别耗时':<20} {w_infer:<20} {p_infer:<20}")
    print(f"{'实时因子 (RTF)':<20} {w_rtf:<20} {p_rtf:<20}")
    print(f"{'文本长度':<20} {w_text_len:<20} {p_text_len:<20}")
    print("-" * 60)
    
    # 识别结果对比
    if whisper_results and paraformer_results:
        print("\n识别文本对比：")
        print("-" * 60)
        print(f"Whisper:   {whisper_results['text']}")
        print(f"Paraformer: {paraformer_results['text']}")
        print("-" * 60)
        
        # 简单相似度（字符级）
        w_text = whisper_results['text']
        p_text = paraformer_results['text']
        
        if len(w_text) == 0 or len(p_text) == 0:
            print("相似度: N/A (有一方为空)")
        else:
            # 计算字符匹配率
            common_chars = sum(1 for c in w_text if c in p_text)
            similarity = common_chars / max(len(w_text), len(p_text))
            print(f"\n字符相似度: {similarity:.1%}")
    
    # 推荐
    print("\n推荐：")
    if whisper_results and paraformer_results:
        w_rtf_val = whisper_results['inference_time'] / audio_duration
        p_rtf_val = paraformer_results['inference_time'] / audio_duration
        
        if p_rtf_val < w_rtf_val * 0.8:
            print("  ✓ Paraformer 显著更快，推荐使用")
        elif p_rtf_val < w_rtf_val:
            print("  ≈ Paraformer 略快，可以尝试")
        else:
            print("  ✓ Whisper 更快或相近，继续使用")
        
        print("\n  注意：准确率需要通过大量测试数据验证")
    elif whisper_results:
        print("  ✓ 只有 Whisper 可用，继续使用")
    elif paraformer_results:
        print("  ✓ 只有 Paraformer 可用，使用该引擎")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="对比 Whisper 和 Paraformer ASR")
    parser.add_argument("audio_file", help="测试音频文件路径 (.wav)")
    parser.add_argument("--whisper-only", action="store_true", help="只测试 Whisper")
    parser.add_argument("--paraformer-only", action="store_true", help="只测试 Paraformer")
    
    args = parser.parse_args()
    
    # 检查音频文件
    if not Path(args.audio_file).exists():
        print(f"✗ 音频文件不存在: {args.audio_file}")
        return
    
    # 加载音频
    print("加载音频文件...")
    audio, sample_rate, duration = load_test_audio(args.audio_file)
    print(f"  文件: {args.audio_file}")
    print(f"  采样率: {sample_rate}Hz")
    print(f"  时长: {duration:.2f}s")
    print(f"  数据: {len(audio)} 采样点")
    
    # 测试
    whisper_results = None
    paraformer_results = None
    
    if not args.paraformer_only:
        whisper_results = test_whisper(audio, args.audio_file)
    
    if not args.whisper_only:
        paraformer_results = test_paraformer(audio, args.audio_file)
    
    # 对比
    compare_results(whisper_results, paraformer_results, duration)
    
    print("\n完成！")


if __name__ == "__main__":
    main()
