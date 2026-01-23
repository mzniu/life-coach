"""
模拟的显示控制器（用于本地开发测试）
在非树莓派环境下模拟OLED显示行为
"""

import sys
import time

class DisplayController:
    """模拟OLED显示控制器"""
    
    def __init__(self):
        self.left_screen = {"text": "", "last_update": time.time()}
        self.right_screen = {"text": "", "last_update": time.time()}
        print("[模拟显示] 初始化OLED双屏")
        
    def show_status(self, state, detail=""):
        """显示状态（左屏）"""
        text = f"{state.upper()}\n{detail}"
        self.left_screen["text"] = text
        self.left_screen["last_update"] = time.time()
        print(f"[左屏] {state} | {detail}")
        
    def update_timer(self, seconds):
        """更新计时器"""
        mins = seconds // 60
        secs = seconds % 60
        text = f"{mins:02d}:{secs:02d}"
        print(f"[左屏] 计时: {text}")
        
    def update_progress(self, percent, message=""):
        """更新进度条"""
        bar = "█" * (percent // 10) + "░" * (10 - percent // 10)
        print(f"[左屏] {message} {bar} {percent}%")
        
    def update_stats(self, today_count, storage_gb):
        """更新统计信息（右屏）"""
        text = f"今日: {today_count}\n存储: {storage_gb:.1f}GB"
        self.right_screen["text"] = text
        self.right_screen["last_update"] = time.time()
        print(f"[右屏] 今日录音: {today_count} | 存储: {storage_gb:.1f}GB")
        
    def clear(self):
        """清空显示"""
        self.left_screen["text"] = ""
        self.right_screen["text"] = ""
        print("[模拟显示] 清空屏幕")
        
    def cleanup(self):
        """清理资源"""
        print("[模拟显示] 清理资源")
