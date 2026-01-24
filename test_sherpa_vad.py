"""
sherpa-onnx Silero VAD 实际测试
"""

import sherpa_onnx
import numpy as np
import wave
from pathlib import Path

def test_vad_with_file(audio_file=None):
    """使用真实音频测试 VAD"""
    print("=" * 60)
    print("Silero VAD 测试")
    print("=" * 60)
    
    # 检查模型
    model_path = Path("models/sherpa/silero_vad.onnx")
    if not model_path.exists():
        print(f"✗ VAD 模型不存在: {model_path.absolute()}")
        return False
    
    print(f"✓ VAD 模型: {model_path}\n")
    
    # 创建 VAD
    config = sherpa_onnx.VadModelConfig()
    config.silero_vad.model = str(model_path.absolute())
    config.sample_rate = 16000
    config.num_threads = 1
    config.provider = "cpu"
    config.silero_vad.min_silence_duration = 0.5
    config.silero_vad.min_speech_duration = 0.25
    config.silero_vad.threshold = 0.5
    
    vad = sherpa_onnx.VoiceActivityDetector(config, buffer_size_in_seconds=60)
    print("✓ VAD 创建成功")
    print(f"  配置: min_silence={config.silero_vad.min_silence_duration}s, ")
    print(f"        min_speech={config.silero_vad.min_speech_duration}s, ")
    print(f"        threshold={config.silero_vad.threshold}\n")
    
    # 如果提供了音频文件
    if audio_file and Path(audio_file).exists():
        print(f"测试音频: {audio_file}")
        
        # 读取音频
        with wave.open(audio_file, 'rb') as wf:
            sample_rate = wf.getframerate()
            n_channels = wf.getnchannels()
            n_frames = wf.getnframes()
            audio_data = wf.readframes(n_frames)
            
            # 转换为 float32
            audio = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            
            # 如果是双声道，取第一声道
            if n_channels == 2:
                audio = audio[::2]
            
            # 重采样到 16kHz（如果需要）
            if sample_rate != 16000:
                print(f"  ⚠ 音频采样率 {sample_rate}Hz，需要重采样到 16000Hz")
                # TODO: 实现重采样
                return False
            
            duration = len(audio) / sample_rate
            print(f"  时长: {duration:.2f}秒")
            print(f"  采样率: {sample_rate}Hz")
            print(f"  声道数: {n_channels}\n")
        
        # 分块处理
        chunk_size = int(0.1 * sample_rate)  # 100ms
        num_chunks = len(audio) // chunk_size
        
        print("VAD 检测结果:")
        print("-" * 60)
        
        segments = []
        for i in range(num_chunks):
            chunk = audio[i*chunk_size:(i+1)*chunk_size]
            vad.accept_waveform(chunk)
            
            # 检查是否有语音段检测完成
            while not vad.empty():
                segment = vad.front()
                vad.pop()
                
                start_time = segment.start / sample_rate
                duration = len(segment.samples) / sample_rate
                
                print(f"  [{start_time:6.2f}s - {start_time+duration:6.2f}s] "
                      f"语音段 (时长: {duration:.2f}s, 样本数: {len(segment.samples)})")
                
                segments.append({
                    'start': start_time,
                    'duration': duration,
                    'samples': len(segment.samples)
                })
        
        # 处理剩余的
        vad.flush()
        while not vad.empty():
            segment = vad.front()
            vad.pop()
            
            start_time = segment.start / sample_rate
            duration = len(segment.samples) / sample_rate
            
            print(f"  [{start_time:6.2f}s - {start_time+duration:6.2f}s] "
                  f"语音段 (时长: {duration:.2f}s)")
            
            segments.append({
                'start': start_time,
                'duration': duration,
                'samples': len(segment.samples)
            })
        
        print("-" * 60)
        print(f"\n✓ 共检测到 {len(segments)} 个语音段")
        
        if segments:
            total_speech = sum(s['duration'] for s in segments)
            print(f"  总语音时长: {total_speech:.2f}秒 ({total_speech/duration*100:.1f}%)")
            print(f"  平均段长: {np.mean([s['duration'] for s in segments]):.2f}秒")
        
        return True
    
    else:
        print("⚠ 未提供测试音频")
        print("\n用法: python test_sherpa_vad.py <音频文件.wav>")
        print("示例: python test_sherpa_vad.py test_audio.wav")
        return False


def compare_with_current_vad():
    """对比当前 VAD 实现"""
    print("\n" + "=" * 60)
    print("Silero VAD vs. 当前 VAD (能量+FFT) 对比")
    print("=" * 60)
    
    comparison = [
        ["特性", "当前VAD", "Silero VAD", "优势"],
        ["算法", "能量阈值 + FFT", "深度学习模型", "Silero"],
        ["准确度", "中等（启发式）", "高（训练数据）", "Silero"],
        ["误触发", "中（噪音影响大）", "低（鲁棒性强）", "Silero"],
        ["延迟", "<10ms", "~30ms", "当前"],
        ["CPU占用", "极低", "中等", "当前"],
        ["内存", "0MB", "~20MB", "当前"],
        ["代码复杂度", "高（378行）", "低（几十行）", "Silero"],
        ["维护成本", "高（自己维护）", "低（成熟项目）", "Silero"],
        ["适应性", "固定阈值", "自适应", "Silero"]
    ]
    
    # 打印表格
    col_widths = [max(len(row[i]) for row in comparison) + 2 for i in range(4)]
    
    for i, row in enumerate(comparison):
        line = "|"
        for j, cell in enumerate(row):
            line += f" {cell:<{col_widths[j]}} |"
        print(line)
        
        if i == 0:  # 表头后加分隔线
            print("|" + "|".join(["-" * (w + 2) for w in col_widths]) + "|")
    
    print("\n建议:")
    print("1. Silero VAD 准确度和鲁棒性明显更好")
    print("2. CPU/内存开销可接受（Pi 可以承受）")
    print("3. 可以减少大量自维护代码")
    print("4. 可保留 faster-whisper ASR，只替换 VAD 部分")


def main():
    import sys
    
    print("\nsherpa-onnx Silero VAD 测试\n")
    
    audio_file = sys.argv[1] if len(sys.argv) > 1 else None
    
    success = test_vad_with_file(audio_file)
    
    compare_with_current_vad()
    
    print("\n" + "=" * 60)
    print("下一步建议")
    print("=" * 60)
    print("""
1. [P0] 在 Pi 上测试 Silero VAD
   - 安装: pip install sherpa-onnx
   - 下载模型: silero_vad.onnx (~1.8MB)
   - 测试 CPU 占用和延迟

2. [P1] 集成到项目（只替换 VAD）
   - 保留 faster-whisper ASR
   - 用 Silero VAD 替换当前的能量+FFT VAD
   - 简化 audio_recorder_real.py

3. [P2] 性能调优
   - 调整 min_silence_duration (0.5s → 1.2s)
   - 调整 threshold (0.5 → 0.3-0.7)
   - 测试不同场景

4. [可选] 测试 sherpa-onnx ASR
   - 下载 Paraformer 中文模型
   - 对比 Whisper 的准确度
   - 如果更好则考虑完整替换
""")


if __name__ == "__main__":
    main()
