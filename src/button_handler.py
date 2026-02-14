"""
按键处理器 - 支持树莓派GPIO和本地开发模拟
"""

import time
import threading
import platform

IS_RASPBERRY_PI = platform.machine().startswith('aarch') or platform.machine().startswith('arm')

GPIO_AVAILABLE = False
GPIO = None

try:
    import Hobot.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    try:
        if IS_RASPBERRY_PI:
            import RPi.GPIO as GPIO
            GPIO_AVAILABLE = True
    except ImportError:
        pass

GPIO_K1 = 4
GPIO_K4 = 24

class ButtonHandler:
    """GPIO按键处理器 - 使用轮询方式检测按钮"""
    
    def __init__(self, use_gpio=GPIO_AVAILABLE):
        self.use_gpio = use_gpio
        self.k1_pressed_flag = False
        self.k4_pressed_flag = False
        self.running = False
        self.monitor_thread = None
        
        self.k1_last_state = True
        self.k4_last_state = True
        self.debounce_time = 0.05
        self.last_k1_time = 0
        self.last_k4_time = 0
        
        if self.use_gpio:
            try:
                GPIO.setmode(GPIO.BCM)
                GPIO.setwarnings(False)
                
                if hasattr(GPIO, 'PUD_UP'):
                    GPIO.setup(GPIO_K1, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                    GPIO.setup(GPIO_K4, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                else:
                    GPIO.setup(GPIO_K1, GPIO.IN)
                    GPIO.setup(GPIO_K4, GPIO.IN)
                
                print("[GPIO按键] 初始化成功（K1=GPIO4 录音, K4=GPIO24 显示开关）")
                
                self.running = True
                self.monitor_thread = threading.Thread(target=self._poll_loop, daemon=True)
                self.monitor_thread.start()
                
            except Exception as e:
                print(f"[GPIO按键] 初始化失败: {e}，切换到模拟模式")
                self.use_gpio = False
        
        if not self.use_gpio:
            print("[模拟按键] 初始化GPIO按键（K1=录音, K4=显示开关）")
    
    def _poll_loop(self):
        """轮询检测按钮状态"""
        while self.running:
            try:
                current_time = time.time()
                
                k1_state = GPIO.input(GPIO_K1)
                if k1_state != self.k1_last_state:
                    time.sleep(0.01)
                    k1_state = GPIO.input(GPIO_K1)
                    
                    if k1_state == GPIO.LOW and self.k1_last_state == GPIO.HIGH:
                        if current_time - self.last_k1_time > self.debounce_time:
                            self.k1_pressed_flag = True
                            self.last_k1_time = current_time
                            print("[GPIO] K1 按下")
                    
                    self.k1_last_state = k1_state
                
                k4_state = GPIO.input(GPIO_K4)
                if k4_state != self.k4_last_state:
                    time.sleep(0.01)
                    k4_state = GPIO.input(GPIO_K4)
                    
                    if k4_state == GPIO.LOW and self.k4_last_state == GPIO.HIGH:
                        if current_time - self.last_k4_time > self.debounce_time:
                            self.k4_pressed_flag = True
                            self.last_k4_time = current_time
                            print("[GPIO] K4 按下 - 切换显示")
                    
                    self.k4_last_state = k4_state
                
                time.sleep(0.02)
                
            except Exception as e:
                print(f"[GPIO] 轮询错误: {e}")
                time.sleep(0.1)
    
    def k1_pressed(self):
        """检测K1按键是否按下（边缘触发，仅返回一次）"""
        if self.k1_pressed_flag:
            self.k1_pressed_flag = False
            return True
        return False
    
    def k4_pressed(self):
        """检测K4按键是否按下（边缘触发，仅返回一次）"""
        if self.k4_pressed_flag:
            self.k4_pressed_flag = False
            return True
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
        self.running = False
        
        if self.use_gpio:
            try:
                GPIO.cleanup([GPIO_K1, GPIO_K4])
                print("[GPIO按键] 清理完成")
            except Exception as e:
                print(f"[GPIO按键] 清理失败: {e}")
        else:
            print("[模拟按键] 清理资源")
