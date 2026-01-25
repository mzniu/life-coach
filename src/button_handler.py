"""
按键处理器 - 支持树莓派GPIO和本地开发模拟
"""

import time
import threading
import platform

# 检测是否在树莓派环境
IS_RASPBERRY_PI = platform.machine().startswith('aarch') or platform.machine().startswith('arm')

# 尝试导入RPi.GPIO
try:
    if IS_RASPBERRY_PI:
        import RPi.GPIO as GPIO
        GPIO_AVAILABLE = True
    else:
        GPIO_AVAILABLE = False
except ImportError:
    GPIO_AVAILABLE = False

# GPIO引脚定义
GPIO_K1 = 4   # 录音按键（Pin 7）
GPIO_K4 = 24  # 退出按键（Pin 18）

class ButtonHandler:
    """GPIO按键处理器（支持树莓派和模拟模式）"""
    
    def __init__(self, use_gpio=GPIO_AVAILABLE):
        self.use_gpio = use_gpio
        self.k1_pressed_flag = False
        self.k4_pressed_flag = False
        self.k4_long_press_start = None
        self.running = False
        self.monitor_thread = None
        
        if self.use_gpio:
            try:
                # 初始化GPIO
                GPIO.setmode(GPIO.BCM)
                GPIO.setwarnings(False)
                
                # 配置K1按键（上拉输入，按下时接地）
                GPIO.setup(GPIO_K1, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                # 配置K4按键
                GPIO.setup(GPIO_K4, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                
                # 添加边缘检测
                GPIO.add_event_detect(GPIO_K1, GPIO.FALLING, 
                                     callback=self._k1_callback, bouncetime=200)
                GPIO.add_event_detect(GPIO_K4, GPIO.FALLING,
                                     callback=self._k4_callback, bouncetime=200)
                
                print("[GPIO按键] 初始化成功（K1=GPIO4, K4=GPIO24）")
                
                # 启动监控线程（用于长按检测）
                self.running = True
                self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
                self.monitor_thread.start()
                
            except Exception as e:
                print(f"[GPIO按键] 初始化失败: {e}，切换到模拟模式")
                self.use_gpio = False
        
        if not self.use_gpio:
            print("[模拟按键] 初始化GPIO按键（K1=录音, K4=退出）")
    
    def _k1_callback(self, channel):
        """K1按键中断回调"""
        self.k1_pressed_flag = True
        print("[GPIO] K1 按下")
    
    def _k4_callback(self, channel):
        """K4按键中断回调"""
        self.k4_pressed_flag = True
        self.k4_long_press_start = time.time()
        print("[GPIO] K4 按下")
    
    def _monitor_loop(self):
        """监控线程 - 检测长按"""
        while self.running:
            try:
                # 检测K4长按
                if self.use_gpio and GPIO.input(GPIO_K4) == GPIO.LOW:
                    if self.k4_long_press_start is None:
                        self.k4_long_press_start = time.time()
                else:
                    self.k4_long_press_start = None
                
                time.sleep(0.1)
            except Exception as e:
                print(f"[GPIO] 监控线程错误: {e}")
                time.sleep(1)
        
    def k1_pressed(self):
        """检测K1按键是否按下（边缘触发，仅返回一次）"""
        if self.k1_pressed_flag:
            self.k1_pressed_flag = False
            return True
        return False
    
    def k4_long_pressed(self):
        """检测K4长按（3秒）"""
        if self.k4_long_press_start is not None:
            current_time = time.time()
            if current_time - self.k4_long_press_start >= 3.0:
                self.k4_long_press_start = None
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
