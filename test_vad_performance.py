"""
VAD 性能压力测试 - 对比 Silero VAD 在 Pi 上的 CPU/内存占用
"""

import time
import psutil
import numpy as np
import sherpa_onnx
from pathlib import Path

def measure_vad_performance():
    """测量 VAD 处理音频的性能"""
    print("=" * 60)
    print("Silero VAD 性能测试 (Raspberry Pi)")
    print("=" * 60)
    
    # 检查模型
    model_path = Path("models/sherpa/silero_vad.onnx")
    if not model_path.exists():
        print(f"✗ 模型不存在: {model_path}")
        return
    
    # 创建 VAD
    config = sherpa_onnx.VadModelConfig()
    config.silero_vad.model = str(model_path.absolute())
    config.sample_rate = 16000
    config.num_threads = 1
    config.provider = "cpu"
    config.silero_vad.min_silence_duration = 1.2  # 匹配当前配置
    config.silero_vad.min_speech_duration = 0.25
    config.silero_vad.threshold = 0.5
    
    print(f"✓ VAD 配置: min_silence={config.silero_vad.min_silence_duration}s")
    
    # 记录初始资源使用
    process = psutil.Process()
    mem_before = process.memory_info().rss / 1024 / 1024
    
    print(f"✓ 创建前内存: {mem_before:.1f}MB")
    
    # 创建 VAD
    start_create = time.time()
    vad = sherpa_onnx.VoiceActivityDetector(config, buffer_size_in_seconds=60)
    create_time = time.time() - start_create
    
    mem_after_create = process.memory_info().rss / 1024 / 1024
    mem_vad = mem_after_create - mem_before
    
    print(f"✓ VAD 创建耗时: {create_time:.3f}秒")
    print(f"✓ VAD 内存占用: {mem_vad:.1f}MB (总计: {mem_after_create:.1f}MB)\n")
    
    # 模拟连续音频处理（10秒音频）
    sample_rate = 16000
    chunk_duration = 0.1  # 100ms chunks
    chunk_size = int(chunk_duration * sample_rate)
    total_duration = 10.0  # 10秒测试
    num_chunks = int(total_duration / chunk_duration)
    
    print(f"测试配置:")
    print(f"  音频时长: {total_duration}秒")
    print(f"  Chunk大小: {chunk_duration}秒 ({chunk_size} 样本)")
    print(f"  总Chunk数: {num_chunks}")
    print()
    
    # 生成测试音频（模拟：2秒静音 + 3秒语音 + 2秒静音 + 3秒语音）
    print("生成测试音频...")
    test_audio = []
    
    # 2秒静音
    test_audio.extend([np.zeros(chunk_size, dtype=np.float32) for _ in range(20)])
    
    # 3秒"语音"（随机噪声模拟）
    for _ in range(30):
        speech = np.random.randn(chunk_size).astype(np.float32) * 0.3
        test_audio.append(speech)
    
    # 2秒静音
    test_audio.extend([np.zeros(chunk_size, dtype=np.float32) for _ in range(20)])
    
    # 3秒"语音"
    for _ in range(30):
        speech = np.random.randn(chunk_size).astype(np.float32) * 0.3
        test_audio.append(speech)
    
    print(f"✓ 生成了 {len(test_audio)} 个 chunks\n")
    
    # 开始处理
    print("开始处理音频...")
    print("-" * 60)
    
    cpu_samples = []
    segment_count = 0
    
    start_time = time.time()
    
    for i, chunk in enumerate(test_audio):
        # 记录 CPU
        cpu_before = process.cpu_percent()
        
        # 处理音频
        vad.accept_waveform(chunk)
        
        # 检查是否有完整的语音段
        while not vad.empty():
            segment = vad.front()
            vad.pop()
            segment_count += 1
            
            seg_start = segment.start / sample_rate
            seg_duration = len(segment.samples) / sample_rate
            
            print(f"  [{seg_start:6.2f}s] 检测到语音段 (时长: {seg_duration:.2f}s)")
        
        # 记录 CPU
        cpu_after = process.cpu_percent()
        if cpu_after > 0:
            cpu_samples.append(cpu_after)
        
        # 每秒输出一次进度
        if (i + 1) % 10 == 0:
            progress = (i + 1) / len(test_audio) * 100
            elapsed = time.time() - start_time
            avg_cpu = np.mean(cpu_samples[-10:]) if cpu_samples else 0
            print(f"  进度: {progress:.0f}% (用时: {elapsed:.2f}s, CPU: {avg_cpu:.1f}%)")
    
    # 处理剩余
    vad.flush()
    while not vad.empty():
        segment = vad.front()
        vad.pop()
        segment_count += 1
        
        seg_start = segment.start / sample_rate
        seg_duration = len(segment.samples) / sample_rate
        print(f"  [{seg_start:6.2f}s] 检测到语音段 (时长: {seg_duration:.2f}s)")
    
    total_time = time.time() - start_time
    
    print("-" * 60)
    print()
    
    # 统计结果
    avg_cpu = np.mean(cpu_samples) if cpu_samples else 0
    max_cpu = np.max(cpu_samples) if cpu_samples else 0
    
    mem_final = process.memory_info().rss / 1024 / 1024
    
    print("=" * 60)
    print("性能测试结果")
    print("=" * 60)
    print(f"处理时长: {total_duration}秒音频")
    print(f"实际耗时: {total_time:.2f}秒 (实时率: {total_duration/total_time:.2f}x)")
    print(f"检测语音段: {segment_count} 个")
    print()
    print(f"CPU 使用:")
    print(f"  平均: {avg_cpu:.1f}%")
    print(f"  峰值: {max_cpu:.1f}%")
    print()
    print(f"内存使用:")
    print(f"  VAD占用: {mem_vad:.1f}MB")
    print(f"  总计: {mem_final:.1f}MB")
    print()
    
    # 评估
    print("=" * 60)
    print("评估结论")
    print("=" * 60)
    
    if total_duration / total_time >= 1.0:
        print("✓ 实时处理: 满足实时要求")
    else:
        print("✗ 实时处理: 无法满足实时要求")
    
    if avg_cpu < 50:
        print(f"✓ CPU占用: {avg_cpu:.1f}% < 50%，可接受")
    else:
        print(f"⚠ CPU占用: {avg_cpu:.1f}% > 50%，偏高")
    
    if mem_vad < 50:
        print(f"✓ 内存占用: {mem_vad:.1f}MB < 50MB，可接受")
    else:
        print(f"⚠ 内存占用: {mem_vad:.1f}MB，较高")
    
    print()
    
    # 对比当前方案
    print("=" * 60)
    print("与当前 VAD 对比")
    print("=" * 60)
    print(f"{'指标':<20} {'当前VAD':<15} {'Silero VAD':<15} {'评价'}")
    print("-" * 60)
    print(f"{'实时率':<20} {'1.0x':<15} {f'{total_duration/total_time:.2f}x':<15} {'✓' if total_duration/total_time >= 1.0 else '✗'}")
    print(f"{'平均CPU':<20} {'<5%':<15} {f'{avg_cpu:.1f}%':<15} {'⚠' if avg_cpu > 10 else '✓'}")
    print(f"{'内存占用':<20} {'0MB':<15} {f'{mem_vad:.1f}MB':<15} {'✓' if mem_vad < 50 else '⚠'}")
    print(f"{'准确度':<20} {'中等':<15} {'高':<15} {'✓'}")
    print(f"{'鲁棒性':<20} {'中':<15} {'优':<15} {'✓'}")
    print(f"{'代码复杂度':<20} {'378行':<15} {'~50行':<15} {'✓'}")
    print()


def main():
    print("\nSilero VAD 性能测试 (Raspberry Pi)\n")
    
    try:
        measure_vad_performance()
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n结论:")
    print("如果上述测试显示:")
    print("- 实时率 >= 1.0x (能处理实时音频)")
    print("- CPU < 50% (不影响其他功能)")
    print("- 内存 < 50MB (Pi可承受)")
    print("\n则建议:")
    print("✓ 用 Silero VAD 替换当前的能量+FFT VAD")
    print("✓ 保留 faster-whisper ASR 引擎")
    print("✓ 可减少 ~300 行 VAD 代码")
    print()


if __name__ == "__main__":
    main()
