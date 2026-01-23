"""
模拟的按键处理器（用于本地开发测试）
在非树莓派环境下模拟GPIO按键行为
"""

import time
import threading

class ButtonHandler:
    """模拟GPIO按键处理器"""
    
    def __init__(self):
        self.k1_pressed_flag = False
        self.k4_pressed_flag = False
        self.k4_long_press_start = None
        print("[模拟按键] 初始化GPIO按键（K1=录音, K4=退出）")
        
    def k1_pressed(self):
        """检测K1按键是否按下"""
        if self.k1_pressed_flag:
            self.k1_pressed_flag = False
            return True
        return False
        
    def k4_long_pressed(self):
        """检测K4长按（3秒）"""
        if self.k4_pressed_flag:
            current_time = time.time()
            if self.k4_long_press_start is None:
                self.k4_long_press_start = current_time
            elif current_time - self.k4_long_press_start >= 3.0:
                self.k4_pressed_flag = False
                self.k4_long_press_start = None
                return True
        else:
            self.k4_long_press_start = None
        return False
        
    def simulate_k1_press(self):
        """模拟K1按键按下（供测试使用）"""
        self.k1_pressed_flag = True
        print("[模拟按键] K1 按下")
        
    def simulate_k4_press(self):
        """模拟K4按键按下（供测试使用）"""
        self.k4_pressed_flag = True
        print("[模拟按键] K4 按下")
        
    def cleanup(self):
        """清理资源"""
        print("[模拟按键] 清理资源")
