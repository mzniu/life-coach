#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Life Coach - Display Controller
控制两个OLED屏幕和一个LCD主屏的显示逻辑

硬件配置:
- OLED #1 (0x3C): 128x64蓝色OLED，显示系统状态
- OLED #2 (0x3D): 128x64蓝色OLED，显示统计信息  
- LCD (SPI): 240x320 IPS彩屏，显示转录文本

引脚映射:
- SPI (LCD): MOSI=19, SCLK=23, CS=24, DC=15, RST=13
- I2C (OLED): SDA=3, SCL=5
"""

import os
import sys
import time
from datetime import datetime
from threading import Lock
from PIL import Image, ImageDraw, ImageFont

# 尝试导入显示库
try:
    from luma.core.interface.serial import i2c, spi
    from luma.core.render import canvas
    from luma.oled.device import ssd1306
    from luma.lcd.device import st7789
    try:
        # framebuffer可能在不同位置
        from luma.core.framebuffer import full_frame
        FRAMEBUFFER_AVAILABLE = True
    except ImportError:
        try:
            from PIL import Image
            import mmap
            FRAMEBUFFER_AVAILABLE = True
        except ImportError:
            FRAMEBUFFER_AVAILABLE = False
    DISPLAY_AVAILABLE = True
except ImportError:
    DISPLAY_AVAILABLE = False
    print("警告: luma显示库未安装，显示功能将被禁用")
    print("安装命令: sudo apt-get install luma.oled luma.lcd -y")


class DisplayController:
    """
    显示控制器 - 管理两个OLED屏幕和一个LCD主屏
    """
    
    def __init__(self, enable_display=True):
        """
        初始化显示控制器
        
        Args:
            enable_display: 是否启用显示功能（默认True）
        """
        self.enabled = enable_display and DISPLAY_AVAILABLE
        self.lock = Lock()
        
        # 设备对象
        self.oled_status = None      # OLED #1 (0x3C) - 状态屏
        self.oled_stats = None        # OLED #2 (0x3D) - 统计屏
        self.lcd_main = None          # LCD 主屏 - 转录文本
        
        # 字体缓存
        self.fonts = {}
        
        # 显示缓存
        self.status_text = ""
        self.stats_data = {}
        self.transcript_lines = []
        self.max_transcript_lines = 10  # LCD显示最多10行文本
        self.lcd_mode = "dashboard"  # dashboard=仪表盘模式, transcript=转录模式
        self.dashboard_stats = {}  # 仪表盘统计数据
        
        # LCD刷新定时器
        self.lcd_refresh_interval = 3  # 每3秒刷新一次
        self.lcd_refresh_thread = None
        self.running = False
        
        if self.enabled:
            self._init_displays()
            self._load_fonts()
            self._start_lcd_refresh()
        else:
            print("显示功能已禁用")
    
    def _init_displays(self):
        """初始化所有显示设备"""
        try:
            # 初始化OLED #1 (0x3C) - 状态屏
            print("正在初始化OLED状态屏 (0x3C)...")
            serial_status = i2c(port=1, address=0x3C)
            self.oled_status = ssd1306(serial_status, width=128, height=64)
            print("✓ OLED状态屏初始化成功")
            
            # 初始化OLED #2 (0x3D) - 统计屏
            print("正在初始化OLED统计屏 (0x3D)...")
            serial_stats = i2c(port=1, address=0x3D)
            self.oled_stats = ssd1306(serial_stats, width=128, height=64)
            print("✓ OLED统计屏初始化成功")
            
            # 初始化LCD主屏
            print("正在初始化LCD主屏...")
            try:
                # 方法1：尝试使用framebuffer方式 (fbtft驱动)
                if os.path.exists('/dev/fb1'):
                    print("检测到framebuffer设备，使用fbtft方式")
                    # 创建framebuffer类包装
                    class FramebufferDevice:
                        def __init__(self, device_path, width, height):
                            self.device_path = device_path
                            self.width = width
                            self.height = height
                            self.size = (width, height)
                            self.mode = 'RGB'
                            
                        def display(self, image):
                            """将PIL Image写入framebuffer (RGB565格式)"""
                            try:
                                # 转换为RGB格式
                                if image.mode != 'RGB':
                                    image = image.convert('RGB')
                                # 确保尺寸正确
                                if image.size != self.size:
                                    image = image.resize(self.size)
                                
                                # 转换为RGB565格式
                                # RGB888 (24位) -> RGB565 (16位)
                                pixels = image.load()
                                rgb565_data = bytearray()
                                for y in range(self.height):
                                    for x in range(self.width):
                                        r, g, b = pixels[x, y]
                                        # RGB888 -> RGB565: RRRRRGGGGGGBBBBB
                                        rgb565 = ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)
                                        # Little endian
                                        rgb565_data.append(rgb565 & 0xFF)
                                        rgb565_data.append((rgb565 >> 8) & 0xFF)
                                
                                # 写入framebuffer
                                with open(self.device_path, 'wb') as fb:
                                    fb.write(bytes(rgb565_data))
                            except Exception as e:
                                print(f"Framebuffer写入失败: {e}")
                    
                    self.lcd_main = FramebufferDevice('/dev/fb1', width=240, height=320)
                    print("✓ LCD主屏初始化成功 (framebuffer)")
                else:
                    # 方法2：使用标准SPI设备
                    print("使用标准SPI方式")
                    serial_lcd = spi(port=0, device=0, gpio_DC=15, gpio_RST=13)
                    self.lcd_main = st7789(
                        serial_lcd, 
                        width=240, 
                        height=320,
                        rotate=0,
                        bgr=True
                    )
                    print("✓ LCD主屏初始化成功 (SPI)")
            except Exception as e:
                print(f"LCD初始化失败: {e}")
                self.lcd_main = None
            
            # 显示启动画面
            self._show_startup_screens()
            
        except Exception as e:
            print(f"显示设备初始化失败: {e}")
            self.enabled = False
    
    def _load_fonts(self):
        """加载字体文件"""
        try:
            # 尝试加载常用中文字体
            font_paths = [
                "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",  # 文泉驿微米黑
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # DejaVu Sans
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"  # Liberation Sans
            ]
            
            # OLED字体 (小字号)
            for path in font_paths:
                if os.path.exists(path):
                    self.fonts['oled_small'] = ImageFont.truetype(path, 10)
                    self.fonts['oled_medium'] = ImageFont.truetype(path, 12)
                    self.fonts['oled_large'] = ImageFont.truetype(path, 14)
                    break
            
            # LCD字体 (大字号)
            for path in font_paths:
                if os.path.exists(path):
                    self.fonts['lcd_small'] = ImageFont.truetype(path, 16)
                    self.fonts['lcd_medium'] = ImageFont.truetype(path, 20)
                    self.fonts['lcd_large'] = ImageFont.truetype(path, 24)
                    break
            
            # 如果没有找到字体，使用默认字体
            if not self.fonts:
                print("警告: 未找到中文字体，使用默认字体")
                self.fonts = {
                    'oled_small': ImageFont.load_default(),
                    'oled_medium': ImageFont.load_default(),
                    'oled_large': ImageFont.load_default(),
                    'lcd_small': ImageFont.load_default(),
                    'lcd_medium': ImageFont.load_default(),
                    'lcd_large': ImageFont.load_default(),
                }
            
            print(f"✓ 字体加载成功: {len(self.fonts)} 种字体")
            
        except Exception as e:
            print(f"字体加载失败: {e}")
            # 使用默认字体
            self.fonts = {
                'oled_small': ImageFont.load_default(),
                'oled_medium': ImageFont.load_default(),
                'oled_large': ImageFont.load_default(),
                'lcd_small': ImageFont.load_default(),
                'lcd_medium': ImageFont.load_default(),
                'lcd_large': ImageFont.load_default(),
            }
    
    def _start_lcd_refresh(self):
        """启动LCD定时刷新线程"""
        import threading
        self.running = True
        self.lcd_refresh_thread = threading.Thread(target=self._lcd_refresh_loop, daemon=True)
        self.lcd_refresh_thread.start()
        print("[LCD] 刷新线程已启动")
    
    def _lcd_refresh_loop(self):
        """LCD定时刷新循环"""
        import time
        print("[LCD] 刷新循环已启动", flush=True)
        while self.running:
            try:
                if self.lcd_mode == "dashboard":
                    # 只刷新显示，不更新数据（数据由主循环更新）
                    self._refresh_dashboard_display()
                time.sleep(self.lcd_refresh_interval)
            except Exception as e:
                print(f"[LCD] 刷新错误: {e}", flush=True)
                import traceback
                traceback.print_exc()
                time.sleep(5)
    
    def _show_startup_screens(self):
        """显示启动画面"""
        try:
            # OLED #1 - 显示欢迎信息
            if self.oled_status:
                with canvas(self.oled_status) as draw:
                    draw.rectangle(self.oled_status.bounding_box, outline="white", fill="black")
                    draw.text((20, 10), "Life Coach", fill="white", font=self.fonts.get('oled_large'))
                    draw.text((15, 30), "对话记录助手", fill="white", font=self.fonts.get('oled_medium'))
                    draw.text((25, 50), "系统启动中...", fill="white", font=self.fonts.get('oled_small'))
            
            # OLED #2 - 显示版本信息
            if self.oled_stats:
                with canvas(self.oled_stats) as draw:
                    draw.rectangle(self.oled_stats.bounding_box, outline="white", fill="black")
                    draw.text((35, 15), "版本 MVP", fill="white", font=self.fonts.get('oled_medium'))
                    draw.text((10, 35), datetime.now().strftime("%Y-%m-%d"), 
                             fill="white", font=self.fonts.get('oled_small'))
                    draw.text((20, 50), datetime.now().strftime("%H:%M:%S"), 
                             fill="white", font=self.fonts.get('oled_small'))
            
            # LCD主屏 - 显示Logo和提示
            if self.lcd_main:
                img = Image.new('RGB', (self.lcd_main.width, self.lcd_main.height), color=(0, 0, 0))
                draw = ImageDraw.Draw(img)
                
                # 标题
                draw.text((60, 100), "Life Coach", fill=(255, 255, 255), 
                         font=self.fonts.get('lcd_large'))
                draw.text((50, 140), "对话记录助手", fill=(200, 200, 200), 
                         font=self.fonts.get('lcd_medium'))
                
                # 提示
                draw.text((30, 200), "按K1开始录音", fill=(100, 200, 255), 
                         font=self.fonts.get('lcd_medium'))
                draw.text((30, 230), "按K4退出程序", fill=(255, 100, 100), 
                         font=self.fonts.get('lcd_medium'))
                
                self.lcd_main.display(img)
            
            time.sleep(2)  # 显示2秒启动画面
            
        except Exception as e:
            print(f"显示启动画面失败: {e}")
    
    def update_status(self, status_text, **kwargs):
        """
        更新状态屏 (OLED #1)
        
        Args:
            status_text: 主要状态文本 (如 "录音中", "待机", "转录中")
            **kwargs: 额外的状态信息
                - recording: bool, 是否正在录音
                - transcribing: bool, 是否正在转录
                - duration: float, 录音时长(秒)
                - word_count: int, 当前字数
        """
        if not self.enabled or not self.oled_status:
            return
        
        try:
            with self.lock:
                self.status_text = status_text
                
                with canvas(self.oled_status) as draw:
                    # 清屏
                    draw.rectangle(self.oled_status.bounding_box, outline="white", fill="black")
                    
                    # 标题
                    draw.text((10, 5), "Life Coach", fill="white", 
                             font=self.fonts.get('oled_medium'))
                    
                    # 分隔线
                    draw.line([(0, 20), (128, 20)], fill="white", width=1)
                    
                    # 状态
                    status_y = 25
                    draw.text((10, status_y), f"状态: {status_text}", fill="white", 
                             font=self.fonts.get('oled_small'))
                    
                    # 录音时长
                    if kwargs.get('duration'):
                        duration = int(kwargs['duration'])
                        mins, secs = divmod(duration, 60)
                        draw.text((10, status_y + 12), f"时长: {mins:02d}:{secs:02d}", 
                                 fill="white", font=self.fonts.get('oled_small'))
                    
                    # 字数统计
                    if kwargs.get('word_count') is not None:
                        draw.text((10, status_y + 24), f"字数: {kwargs['word_count']}", 
                                 fill="white", font=self.fonts.get('oled_small'))
                    
                    # 时间
                    current_time = datetime.now().strftime("%H:%M:%S")
                    draw.text((10, 54), current_time, fill="white", 
                             font=self.fonts.get('oled_small'))
                    
        except Exception as e:
            print(f"更新状态屏失败: {e}")
    
    def update_stats(self, **stats):
        """
        更新统计屏 (OLED #2) - 显示实时转录文本
        
        Args:
            **stats: 统计信息（保留兼容性，但主要用于显示转录文本）
                - transcript_text: str, 实时转录文本
                - recording_count: int, 录音次数
        """
        if not self.enabled or not self.oled_stats:
            return
        
        try:
            with self.lock:
                self.stats_data.update(stats)
                
                # 获取转录文本
                transcript = self.stats_data.get('transcript_text', '')
                recording_count = self.stats_data.get('recording_count', 0)
                
                with canvas(self.oled_stats) as draw:
                    # 清屏
                    draw.rectangle(self.oled_stats.bounding_box, outline="white", fill="black")
                    
                    if transcript:
                        # 显示实时转录
                        draw.text((5, 2), "实时转录", fill="white", 
                                 font=self.fonts.get('oled_small'))
                        draw.line([(0, 14), (128, 14)], fill="white", width=1)
                        
                        # 文本自动换行显示
                        lines = self._wrap_text_oled(transcript, max_width=12)
                        y = 18
                        line_height = 12
                        max_lines = 4  # OLED只显示4行
                        
                        for i, line in enumerate(lines[-max_lines:]):
                            if y + line_height <= 64:
                                draw.text((2, y), line, fill="white", 
                                         font=self.fonts.get('oled_small'))
                                y += line_height
                    else:
                        # 无转录内容时显示提示
                        draw.text((10, 15), "等待转录...", fill="white", 
                                 font=self.fonts.get('oled_medium'))
                        
                        # 显示录音次数
                        if recording_count > 0:
                            draw.text((20, 40), f"已录音 {recording_count} 次", 
                                     fill="white", font=self.fonts.get('oled_small'))
                    
                    # 显示当前时间
                    current_time = datetime.now().strftime("%H:%M")
                    draw.text((88, 54), current_time, fill="white", 
                             font=self.fonts.get('oled_small'))
                    
        except Exception as e:
            print(f"更新转录屏失败: {e}")
    
    def _wrap_text_oled(self, text, max_width=12):
        """OLED文本自动换行（按字符数）"""
        lines = []
        current_line = ""
        
        for char in text:
            if len(current_line) >= max_width or char == '\n':
                if current_line:
                    lines.append(current_line)
                current_line = char if char != '\n' else ""
            else:
                current_line += char
        
        if current_line:
            lines.append(current_line)
        
        return lines
    
    def update_stats_old(self, **stats):
        """
        旧版本统计屏显示（备用）
        """
        if not self.enabled or not self.oled_stats:
            return
        
        try:
            with self.lock:
                self.stats_data.update(stats)
                
                with canvas(self.oled_stats) as draw:
                    # 清屏
                    draw.rectangle(self.oled_stats.bounding_box, outline="white", fill="black")
                    
                    # 标题
                    draw.text((30, 5), "系统统计", fill="white", 
                             font=self.fonts.get('oled_medium'))
                    
                    # 分隔线
                    draw.line([(0, 20), (128, 20)], fill="white", width=1)
                    
                    y = 25
                    line_height = 11
                    
                    # 录音统计
                    if stats.get('total_recordings') is not None:
                        draw.text((5, y), f"录音: {stats['total_recordings']}次", 
                                 fill="white", font=self.fonts.get('oled_small'))
                        y += line_height
                    
                    # 总时长
                    if stats.get('total_duration'):
                        duration = int(stats['total_duration'])
                        mins, secs = divmod(duration, 60)
                        draw.text((5, y), f"时长: {mins}分{secs}秒", 
                                 fill="white", font=self.fonts.get('oled_small'))
                        y += line_height
                    
                    # 总字数
                    if stats.get('total_words') is not None:
                        draw.text((5, y), f"字数: {stats['total_words']}", 
                                 fill="white", font=self.fonts.get('oled_small'))
                        y += line_height
                    
                    # CPU使用率
                    if stats.get('cpu_usage') is not None:
                        draw.text((5, y), f"CPU: {stats['cpu_usage']:.1f}%", 
                                 fill="white", font=self.fonts.get('oled_small'))
                    
                    # 内存使用率
                    if stats.get('memory_usage') is not None:
                        draw.text((70, y), f"内存: {stats['memory_usage']:.1f}%", 
                                 fill="white", font=self.fonts.get('oled_small'))
                        
        except Exception as e:
            print(f"更新统计屏失败: {e}")
    
    def update_transcript(self, text, append=True):
        """
        更新转录文本显示 (LCD主屏)
        
        Args:
            text: 转录文本
            append: True=追加文本, False=清空后显示新文本
        """
        if not self.enabled or not self.lcd_main:
            return        
        # 自动切换到转录模式
        if self.lcd_mode != "transcript":
            self.switch_to_transcript_mode()        
        try:
            with self.lock:
                if append:
                    # 追加文本
                    self.transcript_lines.append(text)
                    # 保留最近N行
                    if len(self.transcript_lines) > self.max_transcript_lines:
                        self.transcript_lines = self.transcript_lines[-self.max_transcript_lines:]
                else:
                    # 清空并显示新文本
                    self.transcript_lines = [text] if text else []
                
                # 渲染到LCD
                self._render_transcript()
                
        except Exception as e:
            print(f"更新转录文本失败: {e}")
    
    def _render_transcript(self):
        """渲染转录文本到LCD主屏"""
        try:
            # 创建图像
            img = Image.new('RGB', (self.lcd_main.width, self.lcd_main.height), 
                           color=(0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            # 标题栏
            draw.rectangle([(0, 0), (240, 30)], fill=(30, 30, 60))
            draw.text((10, 5), "实时转录", fill=(255, 255, 255), 
                     font=self.fonts.get('lcd_medium'))
            
            # 分隔线
            draw.line([(0, 30), (240, 30)], fill=(100, 100, 100), width=2)
            
            # 转录文本
            y = 40
            line_height = 28
            
            for line in self.transcript_lines:
                if y > self.lcd_main.height - line_height:
                    break  # 超出屏幕高度
                
                # 自动换行 (简单版本 - 每行最多显示约12个汉字)
                max_chars = 12
                if len(line) > max_chars:
                    # 长文本分多行显示
                    wrapped_lines = [line[i:i+max_chars] 
                                    for i in range(0, len(line), max_chars)]
                    for wrapped_line in wrapped_lines:
                        if y > self.lcd_main.height - line_height:
                            break
                        draw.text((5, y), wrapped_line, fill=(200, 255, 200), 
                                 font=self.fonts.get('lcd_small'))
                        y += line_height
                else:
                    draw.text((5, y), line, fill=(200, 255, 200), 
                             font=self.fonts.get('lcd_small'))
                    y += line_height
            
            # 如果没有文本，显示提示
            if not self.transcript_lines:
                draw.text((30, 150), "等待语音输入...", fill=(150, 150, 150), 
                         font=self.fonts.get('lcd_medium'))
            
            # 显示到屏幕
            self.lcd_main.display(img)
            
        except Exception as e:
            print(f"渲染转录文本失败: {e}")
    
    def clear_transcript(self):
        """清空转录文本"""
        if not self.enabled:
            return
        
        with self.lock:
            self.transcript_lines = []
            if self.lcd_main:
                self._render_transcript()
    
    def update_dashboard(self, **stats):
        """
        更新LCD仪表盘数据并刷新显示
        
        Args:
            **stats: 统计数据
                - recording_status: str, 录音状态
                - duration: int, 持续时长(秒)
                - word_count: int, 字数统计
                - cpu_temp: float, CPU温度
                - memory_usage: float, 内存使用率(%)
                - today_count: int, 今日录音次数
                - today_duration: int, 今日录音时长(秒)
                - last_transcript: str, 最近转录内容
        """
        if not self.enabled or not self.lcd_main:
            return
        
        # 更新统计数据
        with self.lock:
            self.dashboard_stats.update(stats)
        
        # 刷新显示
        self._refresh_dashboard_display()
    
    def _refresh_dashboard_display(self):
        """刷新仪表盘显示（使用当前缓存的数据）"""
        if not self.enabled or not self.lcd_main:
            return
        
        try:
            with self.lock:
                # 获取数据（使用缓存的数据）
                status = self.dashboard_stats.get('recording_status', '待机')
                duration = self.dashboard_stats.get('duration', 0)
                word_count = self.dashboard_stats.get('word_count', 0)
                cpu_temp = self.dashboard_stats.get('cpu_temp', 0)
                memory = self.dashboard_stats.get('memory_usage', 0)
                today_count = self.dashboard_stats.get('today_count', 0)
                today_duration = self.dashboard_stats.get('today_duration', 0)
                last_text = self.dashboard_stats.get('last_transcript', '')
            
            # 创建图像
            img = Image.new('RGB', (self.lcd_main.width, self.lcd_main.height), 
                           color=(0, 15, 30))  # 深蓝色背景
            draw = ImageDraw.Draw(img)
            
            # ===== 顶部标题栏 =====
            draw.rectangle([(0, 0), (240, 35)], fill=(20, 40, 80))
            draw.text((50, 8), "Life Coach", fill=(255, 255, 255), 
                     font=self.fonts.get('lcd_medium'))
            current_time = datetime.now().strftime("%H:%M:%S")
            draw.text((160, 12), current_time, fill=(200, 200, 200), 
                     font=self.fonts.get('lcd_small'))
            
            # ===== 左侧状态区 =====
            y = 45
            draw.text((10, y), "录音状态", fill=(150, 150, 150), 
                     font=self.fonts.get('lcd_small'))
            status_color = (100, 255, 100) if status == '录音中' else (200, 200, 200)
            draw.text((90, y), status, fill=status_color, 
                     font=self.fonts.get('lcd_small'))
            
            y += 22
            draw.text((10, y), "持续时长", fill=(150, 150, 150), 
                     font=self.fonts.get('lcd_small'))
            mins, secs = divmod(duration, 60)
            draw.text((90, y), f"{mins:02d}:{secs:02d}", fill=(200, 200, 200), 
                     font=self.fonts.get('lcd_small'))
            
            y += 22
            draw.text((10, y), "字数统计", fill=(150, 150, 150), 
                     font=self.fonts.get('lcd_small'))
            draw.text((90, y), f"{word_count}字", fill=(200, 200, 200), 
                     font=self.fonts.get('lcd_small'))
            
            y += 22
            draw.text((10, y), "CPU温度", fill=(150, 150, 150), 
                     font=self.fonts.get('lcd_small'))
            temp_color = (255, 100, 100) if cpu_temp > 70 else (200, 200, 200)
            draw.text((90, y), f"{cpu_temp:.1f}°C", fill=temp_color, 
                     font=self.fonts.get('lcd_small'))
            
            y += 22
            draw.text((10, y), "内存使用", fill=(150, 150, 150), 
                     font=self.fonts.get('lcd_small'))
            draw.text((90, y), f"{memory:.0f}%", fill=(200, 200, 200), 
                     font=self.fonts.get('lcd_small'))
            
            # ===== 分隔线 =====
            draw.line([(5, 175), (235, 175)], fill=(60, 80, 120), width=2)
            
            # ===== 中部最近转录 =====
            y = 185
            draw.text((10, y), "最近一次转录:", fill=(255, 200, 100), 
                     font=self.fonts.get('lcd_small'))
            
            if last_text:
                # 自动换行显示
                y += 18
                lines = self._wrap_text_lcd(last_text, max_chars=18)
                for i, line in enumerate(lines[:2]):  # 最多显示2行
                    draw.text((10, y + i*18), line, fill=(200, 200, 200), 
                             font=self.fonts.get('lcd_small'))
            else:
                y += 18
                draw.text((10, y), "暂无内容", fill=(150, 150, 150), 
                         font=self.fonts.get('lcd_small'))
            
            # ===== 底部统计栏 =====
            draw.rectangle([(0, 280), (240, 320)], fill=(20, 40, 80))
            today_mins = today_duration // 60
            draw.text((15, 290), f"今日 {today_count}次/{today_mins}分钟", 
                     fill=(100, 200, 255), font=self.fonts.get('lcd_small'))
            
            self.lcd_main.display(img)
                
        except Exception as e:
            print(f"[LCD] 刷新仪表盘显示失败: {e}", flush=True)
    
    def _wrap_text_lcd(self, text, max_chars=18):
        """LCD文本自动换行（按字符数）"""
        lines = []
        current_line = ""
        
        for char in text:
            if len(current_line) >= max_chars or char == '\n':
                if current_line:
                    lines.append(current_line)
                current_line = char if char != '\n' else ""
            else:
                current_line += char
        
        if current_line:
            lines.append(current_line)
        
        return lines
    
    def switch_to_transcript_mode(self):
        """切换到转录模式"""
        with self.lock:
            self.lcd_mode = "transcript"
            print("[LCD] 切换到转录模式")
    
    def switch_to_dashboard_mode(self):
        """切换到仪表盘模式"""
        with self.lock:
            self.lcd_mode = "dashboard"
            self.update_dashboard()  # 立即刷新
            print("[LCD] 切换到仪表盘模式")
    
    def show_message(self, title, message, duration=3):
        """
        在LCD主屏显示临时消息
        
        Args:
            title: 标题
            message: 消息内容
            duration: 显示时长(秒)
        """
        if not self.enabled or not self.lcd_main:
            return
        
        try:
            with self.lock:
                img = Image.new('RGB', (self.lcd_main.width, self.lcd_main.height), 
                               color=(0, 0, 0))
                draw = ImageDraw.Draw(img)
                
                # 标题
                draw.text((60, 120), title, fill=(255, 255, 255), 
                         font=self.fonts.get('lcd_large'))
                
                # 消息
                draw.text((40, 170), message, fill=(200, 200, 200), 
                         font=self.fonts.get('lcd_medium'))
                
                self.lcd_main.display(img)
                
            time.sleep(duration)
            # 恢复转录文本显示
            self._render_transcript()
            
        except Exception as e:
            print(f"显示消息失败: {e}")
    
    def clear(self):
        """清空所有屏幕"""
        self.clear_transcript()
        if self.oled_status:
            with canvas(self.oled_status) as draw:
                draw.rectangle(self.oled_status.bounding_box, outline="white", fill="black")
        if self.oled_stats:
            with canvas(self.oled_stats) as draw:
                draw.rectangle(self.oled_stats.bounding_box, outline="white", fill="black")
    
    def cleanup(self):
        """关闭显示设备 (别名)"""
        self.close()
    
    def toggle_display(self):
        """切换显示开关状态"""
        if not DISPLAY_AVAILABLE:
            print("[显示] 显示硬件不可用")
            return False
        
        self.enabled = not self.enabled
        
        if self.enabled:
            print("[显示] 已开启显示", flush=True)
            # 重新初始化显示设备
            try:
                self._init_displays()
                self._load_fonts()
                self._show_startup_screens()
                # 重启刷新线程
                if not self.running:
                    self._start_lcd_refresh()
            except Exception as e:
                print(f"[显示] 开启失败: {e}")
                self.enabled = False
                return False
        else:
            print("[显示] 已关闭显示", flush=True)
            # 清空屏幕
            try:
                if self.oled_status:
                    from luma.core.render import canvas
                    with canvas(self.oled_status) as draw:
                        draw.rectangle(self.oled_status.bounding_box, outline="black", fill="black")
                
                if self.oled_stats:
                    from luma.core.render import canvas
                    with canvas(self.oled_stats) as draw:
                        draw.rectangle(self.oled_stats.bounding_box, outline="black", fill="black")
                
                if self.lcd_main:
                    img = Image.new('RGB', (self.lcd_main.width, self.lcd_main.height), color=(0, 0, 0))
                    self.lcd_main.display(img)
            except Exception as e:
                print(f"[显示] 关闭时清空屏幕失败: {e}")
        
        return self.enabled
    
    def close(self):
        """关闭显示设备"""
        try:
            if self.oled_status:
                with canvas(self.oled_status) as draw:
                    draw.rectangle(self.oled_status.bounding_box, outline="white", fill="black")
                    draw.text((30, 25), "系统已关闭", fill="white", 
                             font=self.fonts.get('oled_medium'))
            
            if self.oled_stats:
                with canvas(self.oled_stats) as draw:
                    draw.rectangle(self.oled_stats.bounding_box, outline="white", fill="black")
                    draw.text((40, 25), "再见!", fill="white", 
                             font=self.fonts.get('oled_medium'))
            
            if self.lcd_main:
                img = Image.new('RGB', (self.lcd_main.width, self.lcd_main.height), 
                               color=(0, 0, 0))
                draw = ImageDraw.Draw(img)
                draw.text((70, 150), "系统已关闭", fill=(255, 255, 255), 
                         font=self.fonts.get('lcd_large'))
                self.lcd_main.display(img)
            
            time.sleep(1)
            
            # 关闭设备
            if self.oled_status:
                self.oled_status.cleanup()
            if self.oled_stats:
                self.oled_stats.cleanup()
            # LCD不需要特殊清理
            
            print("✓ 显示设备已关闭")
            
        except Exception as e:
            print(f"关闭显示设备失败: {e}")


# 全局单例
_display_instance = None
_display_lock = Lock()


def get_display_controller(enable_display=True):
    """
    获取显示控制器单例
    
    Args:
        enable_display: 是否启用显示功能
        
    Returns:
        DisplayController实例
    """
    global _display_instance
    
    with _display_lock:
        if _display_instance is None:
            _display_instance = DisplayController(enable_display=enable_display)
        return _display_instance


def close_display():
    """关闭全局显示控制器"""
    global _display_instance
    
    with _display_lock:
        if _display_instance:
            _display_instance.close()
            _display_instance = None


# 测试代码
if __name__ == "__main__":
    print("=== Display Controller 测试 ===")
    
    display = get_display_controller(enable_display=True)
    
    if not display.enabled:
        print("显示功能未启用，测试结束")
        sys.exit(0)
    
    try:
        # 测试状态屏
        print("\n测试状态屏...")
        display.update_status("待机", duration=0, word_count=0)
        time.sleep(2)
        
        display.update_status("录音中", recording=True, duration=10, word_count=45)
        time.sleep(2)
        
        display.update_status("转录中", transcribing=True, duration=15, word_count=120)
        time.sleep(2)
        
        # 测试统计屏
        print("\n测试统计屏...")
        display.update_stats(
            total_recordings=5,
            total_duration=300,
            total_words=1520,
            cpu_usage=45.5,
            memory_usage=62.3
        )
        time.sleep(2)
        
        # 测试转录文本
        print("\n测试转录文本...")
        display.clear_transcript()
        display.update_transcript("今天天气真不错。", append=True)
        time.sleep(1)
        
        display.update_transcript("我们去哪里玩呢？", append=True)
        time.sleep(1)
        
        display.update_transcript("要不要去公园走走？", append=True)
        time.sleep(1)
        
        # 测试消息显示
        print("\n测试消息显示...")
        display.show_message("提示", "录音已保存", duration=2)
        
        # 恢复文本显示
        time.sleep(1)
        
        print("\n✓ 所有测试完成")
        
    except KeyboardInterrupt:
        print("\n测试中断")
    
    finally:
        close_display()
        print("显示设备已关闭")
