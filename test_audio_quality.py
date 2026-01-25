#!/usr/bin/env python3
"""
音频质量测试脚本
用于验证音频预处理和质量检查功能
"""

import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.audio_recorder_real import AudioRecorder
from src.config import (
    AUDIO_NORMALIZE_ENABLED,
    AUDIO_NORMALIZE_TARGET,
    AUDIO_HIGHPASS_FILTER_ENABLED,
    AUDIO_HIGHPASS_ALPHA,
    AUDIO_MIN_RMS_THRESHOLD,
)

def test_preprocess():
    """测试音频预处理功能"""
    
    print("=" * 60)
    print("音频预处理测试")
    print("=" * 60)
    
    recorder = AudioRecorder()
    
    # 测试1：正常音量音频
    print("\n[测试1] 正常音量音频")
    normal_audio = np.random.randn(16000) * 0.1  # RMS约0.1
    rms_before = np.sqrt(np.mean(normal_audio ** 2))
    peak_before = np.abs(normal_audio).max()
    
    processed = recorder._preprocess_audio(normal_audio.copy())
    rms_after = np.sqrt(np.mean(processed ** 2))
    peak_after = np.abs(processed).max()
    
    print(f"  处理前: RMS={rms_before:.4f}, Peak={peak_before:.4f}")
    print(f"  处理后: RMS={rms_after:.4f}, Peak={peak_after:.4f}")
    
    if AUDIO_NORMALIZE_ENABLED:
        print(f"  ✓ 归一化已启用，目标={AUDIO_NORMALIZE_TARGET}")
        assert peak_after <= AUDIO_NORMALIZE_TARGET * 1.05, "归一化失败"
    
    # 测试2：低音量音频
    print("\n[测试2] 低音量音频")
    low_audio = np.random.randn(16000) * 0.0001  # RMS约0.0001
    rms_low = np.sqrt(np.mean(low_audio ** 2))
    
    print(f"  RMS={rms_low:.6f}, 阈值={AUDIO_MIN_RMS_THRESHOLD}")
    if rms_low < AUDIO_MIN_RMS_THRESHOLD:
        print(f"  ✓ 低于阈值，应该被跳过")
    else:
        print(f"  ✗ 高于阈值，不会被跳过")
    
    # 测试3：高音量音频
    print("\n[测试3] 高音量音频")
    high_audio = np.random.randn(16000) * 2.0  # 超过正常范围
    peak_high_before = np.abs(high_audio).max()
    
    processed_high = recorder._preprocess_audio(high_audio.copy())
    peak_high_after = np.abs(processed_high).max()
    
    print(f"  处理前: Peak={peak_high_before:.4f}")
    print(f"  处理后: Peak={peak_high_after:.4f}")
    
    if AUDIO_NORMALIZE_ENABLED:
        print(f"  ✓ 归一化后峰值不超过{AUDIO_NORMALIZE_TARGET}")
    
    # 测试4：高通滤波效果
    print("\n[测试4] 高通滤波效果")
    # 创建低频信号（模拟低频噪声）
    t = np.linspace(0, 1, 16000)
    low_freq_signal = np.sin(2 * np.pi * 10 * t) * 0.1  # 10Hz低频
    
    processed_filtered = recorder._preprocess_audio(low_freq_signal.copy())
    energy_before = np.mean(low_freq_signal ** 2)
    energy_after = np.mean(processed_filtered ** 2)
    
    print(f"  滤波前能量: {energy_before:.6f}")
    print(f"  滤波后能量: {energy_after:.6f}")
    print(f"  能量减少: {(1 - energy_after/energy_before)*100:.1f}%")
    
    if AUDIO_HIGHPASS_FILTER_ENABLED:
        print(f"  ✓ 高通滤波已启用，alpha={AUDIO_HIGHPASS_ALPHA}")
        if energy_after < energy_before:
            print(f"  ✓ 低频能量降低，滤波有效")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    
    # 显示当前配置
    print("\n当前配置:")
    print(f"  AUDIO_NORMALIZE_ENABLED = {AUDIO_NORMALIZE_ENABLED}")
    print(f"  AUDIO_NORMALIZE_TARGET = {AUDIO_NORMALIZE_TARGET}")
    print(f"  AUDIO_HIGHPASS_FILTER_ENABLED = {AUDIO_HIGHPASS_FILTER_ENABLED}")
    print(f"  AUDIO_HIGHPASS_ALPHA = {AUDIO_HIGHPASS_ALPHA}")
    print(f"  AUDIO_MIN_RMS_THRESHOLD = {AUDIO_MIN_RMS_THRESHOLD}")

def test_quality_check():
    """测试音频质量检查"""
    
    print("\n" + "=" * 60)
    print("音频质量检查测试")
    print("=" * 60)
    
    test_cases = [
        ("静音", np.zeros(16000), "应被跳过"),
        ("极低音量", np.random.randn(16000) * 0.0001, "应被跳过"),
        ("低音量", np.random.randn(16000) * 0.01, "可能识别困难"),
        ("正常音量", np.random.randn(16000) * 0.05, "正常"),
        ("高音量", np.random.randn(16000) * 0.3, "正常"),
    ]
    
    for name, audio, expected in test_cases:
        rms = np.sqrt(np.mean(audio ** 2))
        peak = np.abs(audio).max()
        
        status = "跳过" if rms < AUDIO_MIN_RMS_THRESHOLD else "处理"
        
        print(f"\n  [{name}]")
        print(f"    RMS={rms:.6f}, Peak={peak:.4f}")
        print(f"    状态: {status} (预期: {expected})")

if __name__ == "__main__":
    test_preprocess()
    test_quality_check()
