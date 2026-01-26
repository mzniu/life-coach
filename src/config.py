"""
Life Coach 配置文件
包含所有可配置参数
"""

import os
import sys
import platform

# 平台检测
def is_raspberry_pi():
    """检测是否在树莓派上运行"""
    try:
        with open('/proc/cpuinfo', 'r') as f:
            cpuinfo = f.read()
            return 'BCM' in cpuinfo or 'Raspberry' in cpuinfo
    except:
        return False

IS_RASPBERRY_PI = is_raspberry_pi()

# Platform-aware配置
if IS_RASPBERRY_PI:
    # 树莓派配置
    WHISPER_MODEL = "small"
    ASR_MODEL_SIZE = "small"
    ASR_COMPUTE_TYPE = "int8"
    ASR_BEAM_SIZE = 3
    ASR_VAD_FILTER = True
    # 动态获取当前用户目录 (e.g. /home/cmit)
    STORAGE_BASE = os.path.join(os.path.expanduser("~"), "LifeCoach/recordings")
    WEB_HOST = "0.0.0.0"
    WEB_PORT = 5000
    MAX_RECORDING_DURATION = 600  # 10分钟
else:
    # Windows/Mac 配置
    WHISPER_MODEL = "small"
    ASR_MODEL_SIZE = "small"
    ASR_COMPUTE_TYPE = "int8"
    ASR_BEAM_SIZE = 5
    ASR_VAD_FILTER = True
    STORAGE_BASE = os.path.join(os.path.expanduser("~"), "LifeCoach", "recordings").replace("\\", "/")
    WEB_HOST = "0.0.0.0"
    WEB_PORT = 8080
    MAX_RECORDING_DURATION = 3600  # 1小时

WHISPER_DEVICE = "cpu"
STORAGE_BASE_PATH = STORAGE_BASE

print(f"[配置] Platform: {'Raspberry Pi' if IS_RASPBERRY_PI else 'Windows/Mac'}, WEB_PORT={WEB_PORT}, MODEL={WHISPER_MODEL}")

# ==================== GPIO 引脚定义 ====================
# 基于扩展板实际物理引脚映射
GPIO_K1 = 4   # 录音按键（Pin 7）
GPIO_K4 = 24  # 退出按键（Pin 18）

# ==================== 显示屏配置 ====================
# 是否启用显示功能
DISPLAY_ENABLED = os.getenv('DISPLAY_ENABLED', 'true' if IS_RASPBERRY_PI else 'false').lower() == 'true'

# OLED 屏幕配置（双屏，I2C接口）
OLED_I2C_PORT = 1          # I2C端口号（树莓派默认为1）
OLED_STATUS_ADDRESS = 0x3C  # OLED #1地址 - 状态屏（左屏）
OLED_STATS_ADDRESS = 0x3D   # OLED #2地址 - 统计屏（右屏）
OLED_WIDTH = 128            # OLED分辨率宽度
OLED_HEIGHT = 64            # OLED分辨率高度

# LCD 主屏配置（SPI接口）
LCD_SPI_PORT = 0           # SPI端口号
LCD_SPI_DEVICE = 0         # SPI设备号
LCD_GPIO_DC = 15           # 数据/命令选择引脚（Pin 15）
LCD_GPIO_RST = 13          # 复位引脚（Pin 13）
LCD_WIDTH = 240            # LCD分辨率宽度
LCD_HEIGHT = 320           # LCD分辨率高度
LCD_ROTATE = 0             # 旋转角度：0/1/2/3 对应 0°/90°/180°/270°
LCD_BGR = True             # 颜色模式（ST7789芯片需要设置为True）

# 中文字体路径（优先级顺序）
DISPLAY_FONT_PATHS = [
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",       # 文泉驿微米黑（推荐）
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",      # DejaVu Sans
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"  # Liberation Sans
]

# 字体大小配置
DISPLAY_FONT_SIZE_OLED_SMALL = 10   # OLED小字号
DISPLAY_FONT_SIZE_OLED_MEDIUM = 12  # OLED中字号
DISPLAY_FONT_SIZE_OLED_LARGE = 14   # OLED大字号
DISPLAY_FONT_SIZE_LCD_SMALL = 16    # LCD小字号
DISPLAY_FONT_SIZE_LCD_MEDIUM = 20   # LCD中字号
DISPLAY_FONT_SIZE_LCD_LARGE = 24    # LCD大字号

# LCD文本显示配置
LCD_MAX_TRANSCRIPT_LINES = 10       # 最多显示行数
LCD_MAX_CHARS_PER_LINE = 12         # 每行最多显示字符数（约12个汉字）
LCD_LINE_HEIGHT = 28                # 行高（像素）

print(f"[配置] 显示功能: {'启用' if DISPLAY_ENABLED else '禁用'}, OLED: 0x{OLED_STATUS_ADDRESS:02X}/0x{OLED_STATS_ADDRESS:02X}, LCD: {LCD_WIDTH}x{LCD_HEIGHT}")

# ==================== 音频参数 ====================
SAMPLE_RATE = 16000      # 采样率（Whisper最优）
CHANNELS = 1             # 单声道
CHUNK_SIZE = 1024        # 缓冲区大小
FORMAT = 'paInt16'       # 16位采样深度
AUDIO_DEVICE_INDEX = None  # None=自动检测，或指定设备序号

# ==================== Whisper 模型配置 ====================
WHISPER_MODEL = "tiny"   # tiny/base/small（tiny最快）
WHISPER_LANGUAGE = "zh"  # 中文优先
WHISPER_DEVICE = "cpu"   # 树莓派只支持CPU

# 流式转写参数
STREAM_CHUNK_SECONDS = 3  # 每3秒音频进行一次转写

# ==================== 存储路径 ====================
# STORAGE_BASE已从根目录config.py导入
LOG_PATH = os.path.join(os.path.dirname(STORAGE_BASE), "logs", "app.log")  # 日志文件路径
MODEL_CACHE = os.path.join(os.path.dirname(STORAGE_BASE), "models")  # 模型缓存目录

# ==================== 文本纠错配置 ====================
# 是否启用文本纠错功能（默认关闭，需手动启用）
TEXT_CORRECTION_ENABLED = os.getenv('TEXT_CORRECTION_ENABLED', 'false').lower() == 'true'

# 纠错模型路径（GGUF 格式）
TEXT_CORRECTION_MODEL = os.getenv(
    'TEXT_CORRECTION_MODEL',
    os.path.join(MODEL_CACHE, "qwen2.5-0.5b", "qwen2.5-0.5b-instruct-q4_k_m.gguf")
)

# 最大生成 token 数（控制输出长度）
TEXT_CORRECTION_MAX_TOKENS = int(os.getenv('TEXT_CORRECTION_MAX_TOKENS', '512'))

# 温度参数（0-1，越低越确定，推荐 0.3）
TEXT_CORRECTION_TEMPERATURE = float(os.getenv('TEXT_CORRECTION_TEMPERATURE', '0.3'))

# 推理超时时间（秒）
TEXT_CORRECTION_TIMEOUT = int(os.getenv('TEXT_CORRECTION_TIMEOUT', '15'))

# ==================== 实时转录配置 ====================
# 是否启用实时转录功能（录音时实时显示识别文本）
REALTIME_TRANSCRIBE_ENABLED = os.getenv('REALTIME_TRANSCRIBE_ENABLED', 'true').lower() == 'true'

# VAD（语音活动检测）参数 - 优化减少尾部截断
REALTIME_SILENCE_THRESHOLD = int(os.getenv('REALTIME_SILENCE_THRESHOLD', '300'))  # 静音阈值（音频能量）
REALTIME_MIN_SILENCE_DURATION = float(os.getenv('REALTIME_MIN_SILENCE_DURATION', '1.5'))  # 静音触发时长（秒）- 增加以减少截断
REALTIME_MIN_SPEECH_DURATION = float(os.getenv('REALTIME_MIN_SPEECH_DURATION', '0.5'))  # 最小语音时长（秒）
REALTIME_VAD_THRESHOLD = float(os.getenv('REALTIME_VAD_THRESHOLD', '0.5'))  # VAD阈值 - 降低以捕获更弱的尾音
REALTIME_MAX_SPEECH_DURATION = float(os.getenv('REALTIME_MAX_SPEECH_DURATION', '30.0'))  # 最大语音时长（秒）
REALTIME_MAX_SEGMENT_DURATION = float(os.getenv('REALTIME_MAX_SEGMENT_DURATION', '10.0'))  # 最大分段时长（秒）
REALTIME_MIN_SEGMENT_DURATION = float(os.getenv('REALTIME_MIN_SEGMENT_DURATION', '0.5'))  # 最小分段时长（秒）

# 音频前后缓冲区（防止首尾截断）
REALTIME_SPEECH_PAD_MS = int(os.getenv('REALTIME_SPEECH_PAD_MS', '500'))  # 语音段前后各填充300ms

# 人声检测（过滤非人声噪音）
REALTIME_VOICE_DETECTION_ENABLED = os.getenv('REALTIME_VOICE_DETECTION_ENABLED', 'true').lower() == 'true'  # 是否启用人声检测
REALTIME_VOICE_FREQ_MIN = int(os.getenv('REALTIME_VOICE_FREQ_MIN', '85'))  # 人声最低频率（Hz）
REALTIME_VOICE_FREQ_MAX = int(os.getenv('REALTIME_VOICE_FREQ_MAX', '3400'))  # 人声最高频率（Hz）

# 实时转录队列大小（避免内存溢出）
REALTIME_QUEUE_MAX_SIZE = int(os.getenv('REALTIME_QUEUE_MAX_SIZE', '10'))

# 实时转录性能优化
REALTIME_BEAM_SIZE = int(os.getenv('REALTIME_BEAM_SIZE', '3'))  # 降低beam size加速转录（准确度略降）

# ==================== 音频预处理配置 ====================
# 音频归一化
AUDIO_NORMALIZE_ENABLED = os.getenv('AUDIO_NORMALIZE_ENABLED', 'true').lower() == 'true'  # 是否启用音量归一化
AUDIO_NORMALIZE_TARGET = float(os.getenv('AUDIO_NORMALIZE_TARGET', '0.95'))  # 归一化目标幅度（0-1）

# 音频降噪
AUDIO_HIGHPASS_FILTER_ENABLED = os.getenv('AUDIO_HIGHPASS_FILTER_ENABLED', 'true').lower() == 'true'  # 是否启用高通滤波
AUDIO_HIGHPASS_ALPHA = float(os.getenv('AUDIO_HIGHPASS_ALPHA', '0.95'))  # 高通滤波系数（0.9-0.99）

# 音频质量检查
AUDIO_MIN_RMS_THRESHOLD = float(os.getenv('AUDIO_MIN_RMS_THRESHOLD', '0.001'))  # 最小RMS阈值，低于此值视为静音
AUDIO_MIN_PEAK_THRESHOLD = float(os.getenv('AUDIO_MIN_PEAK_THRESHOLD', '0.01'))  # 最小峰值阈值

# ASR上下文配置
ASR_CONTEXT_SIZE = int(os.getenv('ASR_CONTEXT_SIZE', '2'))  # 保留前N个分段的上下文
ASR_USE_CONTEXT = os.getenv('ASR_USE_CONTEXT', 'true').lower() == 'true'  # 是否使用上下文提示

print(f"[配置] 实时转录: {'启用' if REALTIME_TRANSCRIBE_ENABLED else '禁用'}, 静音阈值={REALTIME_SILENCE_THRESHOLD}, 触发时长={REALTIME_MIN_SILENCE_DURATION}s, 人声检测={'启用' if REALTIME_VOICE_DETECTION_ENABLED else '禁用'}")
print(f"[配置] 音频处理: 归一化={'启用' if AUDIO_NORMALIZE_ENABLED else '禁用'}, 降噪={'启用' if AUDIO_HIGHPASS_FILTER_ENABLED else '禁用'}, 上下文大小={ASR_CONTEXT_SIZE}")

# ==================== Web服务配置 ====================
# WEB_HOST和WEB_PORT已从根目录config.py导入
WEB_DEBUG = True         # 开启调试模式（显示详细错误和HTTP日志）
CORS_ORIGINS = "*"       # 跨域允许来源（*表示允许所有）

# ==================== 系统参数 ====================
# 按键防抖时间（秒）
BUTTON_DEBOUNCE_TIME = 0.05  # 50ms

# K4长按触发时间（秒）
BUTTON_LONG_PRESS_TIME = 3.0  # 长按3秒触发退出

# 存储空间告警阈值（GB）
STORAGE_WARNING_THRESHOLD = 1.0  # 剩余<1GB时警告

# 内存占用告警阈值（百分比）
MEMORY_WARNING_THRESHOLD = 0.8  # 超过80%时警告

# 日志配置
LOG_LEVEL = "INFO"       # DEBUG/INFO/WARNING/ERROR
LOG_MAX_SIZE = 10        # 单个日志文件最大大小（MB）
LOG_BACKUP_COUNT = 3     # 保留日志文件数量

# ==================== 状态常量 ====================
class AppState:
    """应用状态枚举"""
    IDLE = "idle"                # 待机
    RECORDING = "recording"      # 录音中
    PROCESSING = "processing"    # 转写中
    DONE = "done"                # 完成
    ERROR = "error"              # 错误

class ErrorCode:
    """错误码定义"""
    MIC_DISCONNECTED = "MIC_DISCONNECTED"
    STORAGE_FULL = "STORAGE_FULL"
    INVALID_STATE = "INVALID_STATE"
    RECORDING_NOT_FOUND = "RECORDING_NOT_FOUND"
    INTERNAL_ERROR = "INTERNAL_ERROR"
