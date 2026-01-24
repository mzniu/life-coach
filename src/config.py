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

# I2C地址（双OLED屏幕）
I2C_OLED_LEFT = 0x3C   # 左副屏（状态显示）
I2C_OLED_RIGHT = 0x3D  # 右副屏（统计信息）

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

# ==================== 显示参数 ====================
# 中文字体路径（需安装 fonts-wqy-zenhei）
FONT_PATH = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
FONT_SIZE_TITLE = 12    # 标题字体大小
FONT_SIZE_STATUS = 14   # 状态字体大小
FONT_SIZE_DETAIL = 10   # 详细信息字体大小

# OLED刷新频率
OLED_REFRESH_IDLE = 5.0      # 待机状态刷新间隔（秒）
OLED_REFRESH_RECORDING = 1.0  # 录音中刷新间隔（秒）
OLED_REFRESH_PROCESSING = 0.1 # 转写中刷新间隔（秒）

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
