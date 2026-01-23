"""
真实的音频录制器（使用 sounddevice，支持 Windows/Mac/Linux）
"""

import time
import threading
import numpy as np

try:
    import sounddevice as sd
    REAL_AUDIO = True
except ImportError:
    REAL_AUDIO = False
    print("[音频录制] 警告: sounddevice 未安装，将使用模拟模式")
    print("[音频录制] 安装方法: pip install sounddevice")

class AudioRecorder:
    """音频录制器（真实采集）"""
    
    def __init__(self, sample_rate=16000, channels=1):
        global REAL_AUDIO
        self.sample_rate = sample_rate
        self.channels = channels
        self.is_recording = False
        self.start_time = None
        self.audio_data = []
        self.recording_thread = None
        
        if REAL_AUDIO:
            try:
                print(f"[音频录制] 初始化真实音频录制器 ({sample_rate}Hz, {channels}声道)")
                # 列出可用设备
                # devices = sd.query_devices() # 可能会很长
                default_input = sd.query_devices(kind='input')
                print(f"[音频录制] 默认输入设备: {default_input['name']}")
            except Exception as e:
                print(f"[音频录制] 错误: 无法初始化音频设备 ({e})")
                print("[音频录制] 可能原因: 未插入麦克风或声卡驱动未加载")
                print("请检查: lsusb (如果是USB麦克风) 或 arecord -l")
                # 抛出异常让上层知道或者降级为模拟？
                # 这里我们选择降级为模拟模式，以免 crashing loop
                REAL_AUDIO = False
        else:
            print("[音频录制] 初始化模拟音频录制器")
        
    def start(self):
        """开始录音"""
        if self.is_recording:
            raise Exception("录音已在进行中")
            
        self.is_recording = True
        self.start_time = time.time()
        self.audio_data = []
        
        if REAL_AUDIO:
            print("[音频录制] 开始录音（真实采集）")
            self.recording_thread = threading.Thread(target=self._real_recording_loop, daemon=True)
        else:
            print("[音频录制] 开始录音（模拟采集）")
            self.recording_thread = threading.Thread(target=self._mock_recording_loop, daemon=True)
        
        self.recording_thread.start()
        
    def stop(self):
        """停止录音"""
        if not self.is_recording:
            raise Exception("未在录音")
            
        self.is_recording = False
        
        # 等待录音线程结束
        if self.recording_thread:
            self.recording_thread.join(timeout=2.0)
        
        duration = time.time() - self.start_time
        print(f"[音频录制] 停止录音（时长: {duration:.1f}秒, 采样数: {len(self.audio_data)}）")
        return self.audio_data
        
    def cancel(self):
        """取消录音"""
        self.is_recording = False
        self.audio_data = []
        print("[音频录制] 取消录音")
        
    def get_duration(self):
        """获取录音时长"""
        if self.start_time:
            return time.time() - self.start_time
        return 0
    
    def _real_recording_loop(self):
        """真实录音循环"""
        chunk_duration = 0.1  # 100ms 每块
        
        # 尝试确定可用的采样率
        device_rate = self.sample_rate
        try:
            # 检查16000是否被支持
            sd.check_input_settings(device=None, channels=self.channels, dtype='int16', extra_settings=None, samplerate=self.sample_rate)
        except Exception as e:
            print(f"[音频录制] 警告: 设备不支持 {self.sample_rate}Hz ({e})")
            # 尝试获取设备默认采样率
            try:
                dev_info = sd.query_devices(kind='input')
                default_rate = int(dev_info['default_samplerate'])
                print(f"[音频录制] 尝试使用设备默认采样率: {default_rate}Hz")
                device_rate = default_rate
            except:
                print("[音频录制] 无法获取默认采样率，将尝试 48000Hz")
                device_rate = 48000

        print(f"[音频录制] 实际使用采样率: {device_rate}Hz")
        
        # 计算每次读取的帧数
        chunk_samples = int(device_rate * chunk_duration)
        
        try:
            with sd.InputStream(
                samplerate=device_rate,
                channels=self.channels,
                dtype='int16',
                blocksize=chunk_samples
            ) as stream:
                while self.is_recording:
                    # 读取音频数据
                    audio_chunk, overflowed = stream.read(chunk_samples)
                    
                    if overflowed:
                        print("[音频录制] 警告: 音频缓冲区溢出")
                    
                    # 如果采样率不匹配，进行简单的降采样 (仅支持 48k -> 16k)
                    if device_rate == 48000 and self.sample_rate == 16000:
                         # 简单的隔点采样 (3倍降采样)
                         # audio_chunk是 (samples, channels) 的numpy数组
                         downsampled = audio_chunk[::3] 
                         self.audio_data.append(downsampled.flatten())
                    elif device_rate != self.sample_rate:
                        # 其他情况暂时原样保存（ASR可能会不准）
                        self.audio_data.append(audio_chunk.flatten())
                    else:
                        # 16k -> 16k
                        self.audio_data.append(audio_chunk.flatten())
                    
        except Exception as e:
            print(f"[音频录制] 错误: {e}")
            self.is_recording = False
    
    def _mock_recording_loop(self):
        """模拟录音循环（当 sounddevice 不可用时）"""
        while self.is_recording:
            # 生成100ms的模拟数据
            chunk_samples = int(self.sample_rate * 0.1)
            mock_chunk = [int(np.random.randint(-1000, 1000)) for _ in range(chunk_samples)]
            self.audio_data.append(mock_chunk)
            time.sleep(0.1)
    
    def cleanup(self):
        """清理资源"""
        if self.is_recording:
            self.cancel()
        print("[音频录制] 清理完成")
