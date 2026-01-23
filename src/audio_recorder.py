"""
模拟的音频录制器（用于本地开发测试）
在非树莓派环境下模拟音频采集行为
"""

import time
import threading
import random

class AudioRecorder:
    """模拟音频录制器"""
    
    def __init__(self):
        self.is_recording = False
        self.start_time = None
        self.audio_data = []
        print("[模拟录音] 初始化音频录制器")
        
    def start(self):
        """开始录音"""
        if self.is_recording:
            raise Exception("录音已在进行中")
            
        self.is_recording = True
        self.start_time = time.time()
        self.audio_data = []
        print("[模拟录音] 开始录音（模拟音频采集）")
        
        # 启动模拟录音线程
        threading.Thread(target=self._recording_loop, daemon=True).start()
        
    def stop(self):
        """停止录音"""
        if not self.is_recording:
            raise Exception("未在录音")
            
        self.is_recording = False
        duration = time.time() - self.start_time
        print(f"[模拟录音] 停止录音（时长: {duration:.1f}秒）")
        return self.audio_data
        
    def cancel(self):
        """取消录音"""
        self.is_recording = False
        self.audio_data = []
        print("[模拟录音] 取消录音")
        
    def get_duration(self):
        """获取录音时长"""
        if self.start_time:
            return int(time.time() - self.start_time)
        return 0
        
    def _recording_loop(self):
        """模拟录音循环（生成随机音频数据）"""
        while self.is_recording:
            # 模拟音频数据（每秒生成一些）
            chunk = [random.randint(-100, 100) for _ in range(1024)]
            self.audio_data.append(chunk)
            time.sleep(0.1)  # 每100ms生成一次
            
    def cleanup(self):
        """清理资源"""
        if self.is_recording:
            self.cancel()
        print("[模拟录音] 清理资源")
