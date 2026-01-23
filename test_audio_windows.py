# 测试真实音频录制
# 运行此脚本测试 Windows 音频采集

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    from src.audio_recorder_real import AudioRecorder
    
    print("=" * 60)
    print("  音频录制测试 - Windows")
    print("=" * 60)
    print()
    
    # 创建录制器
    recorder = AudioRecorder()
    
    print("准备录制3秒音频...")
    print("请对着麦克风说话...")
    input("按回车开始录音...")
    
    # 开始录音
    recorder.start()
    
    import time
    for i in range(3):
        time.sleep(1)
        print(f"  录音中... {i+1}秒")
    
    # 停止录音
    audio_data = recorder.stop()
    
    print()
    print(f"✅ 录音完成！")
    print(f"   时长: {recorder.get_duration():.2f}秒")
    print(f"   数据块数: {len(audio_data)}")
    
    if len(audio_data) > 0:
        total_samples = sum(len(chunk) for chunk in audio_data)
        print(f"   总采样数: {total_samples}")
        print(f"   预期采样数: {int(16000 * 3)} (16kHz × 3秒)")
        
        # 计算音量（简单的RMS）
        import numpy as np
        all_samples = []
        for chunk in audio_data:
            all_samples.extend(chunk)
        
        if len(all_samples) > 0:
            rms = np.sqrt(np.mean(np.array(all_samples, dtype=float)**2))
            print(f"   音量 (RMS): {rms:.1f}")
            
            if rms > 100:
                print("   🎤 检测到声音输入！")
            else:
                print("   ⚠️  音量较低，请检查麦克风")
    
    print()
    print("=" * 60)
    
except ImportError as e:
    print("=" * 60)
    print("  需要安装 sounddevice 库")
    print("=" * 60)
    print()
    print("请在虚拟环境中运行:")
    print()
    print("  .\\venv\\Scripts\\Activate.ps1")
    print("  pip install sounddevice numpy")
    print()
    print(f"错误: {e}")
    print()
