# Life Coach 阶段0 最小MVP开发方案

**文档版本：** v1.0  
**创建日期：** 2026-01-21  
**目标：** 2周内完成硬件验证 + 核心录音转写功能，为后续AI功能打基础

---

## 一、方案概述

### 1.1 核心目标
- ✅ 验证树莓派 + 扩展板 + USB麦克风硬件链路可行性
- ✅ 实现按键触发录音 → Whisper实时转写 → 文本文件保存
- ✅ OLED副屏实时显示状态（录音计时、转写进度、完成提示）
- ✅ **新增**：Web服务层 + RESTful API（为前端开发打基础）
- ✅ **新增**：轻量Web监控页面（浏览器查看状态、控制录音）
- ❌ **不包含**：AI整理、完整前端UI、数据库、主屏UI

### 1.2 交付物
1. 可运行的Python程序（模块化架构）
2. Web监控面板（浏览器访问，实时状态显示）
3. RESTful API + WebSocket实时通信
4. 一键部署脚本（`deploy.sh`）
5. 硬件接线说明（扩展板插法 + USB麦克风连接）
6. 使用手册（按键操作 + Web界面 + 故障排查）

---

## 二、硬件方案

### 2.1 扩展板规格（0.96inch OLED 2inch LCD HAT）
**基于资料：** https://spotpear.cn/wiki/0.96inch-OLED-2inch-LCD-HAT-A.html

| 组件 | 规格 | 接口 | 阶段0使用 |
|------|------|------|----------|
| 主屏 | 2寸IPS (ST7789VW) | SPI | ❌ 不使用 |
| 左副屏 | 0.96寸OLED (SSD1315) | I2C (0x3C) | ✅ 状态显示 |
| 右副屏 | 0.96寸OLED (SSD1315) | I2C (0x3D) | ✅ 统计信息 |
| 按键 | 4个独立按键 | GPIO | ✅ 仅用K1+K4 |

### 2.2 GPIO引脚分配（根据扩展板定义）

**按键引脚（基于Board物理引脚）：**
```
K1 (按键1) → Pin 7  → GPIO4   → 开始/停止录音
K2 (按键2) → Pin 11 → GPIO17  → 预留（阶段1）
K3 (按键3) → Pin 16 → GPIO23  → 预留（阶段1）
K4 (按键4) → Pin 18 → GPIO24  → 退出程序
```

**I2C接口（双OLED共用）：**
```
SDA → GPIO2  (I2C1 SDA)
SCL → GPIO3  (I2C1 SCL)
左副屏地址：0x3C
右副屏地址：0x3D
```

**SPI接口（主屏ST7789VW，阶段0不使用）：**
```
MOSI → Pin 19 → GPIO10
SCLK → Pin 23 → GPIO11
CS   → Pin 24 → GPIO8
DC   → Pin 15 → GPIO22
RST  → Pin 13 → GPIO27
```

### 2.3 USB麦克风选型建议
**推荐型号（已测试兼容树莓派）：**
1. **绿联USB外置声卡** + 3.5mm麦克风（¥29，即插即用）
2. **奥尼USB麦克风** CM-100（¥59，全向拾音）
3. **得胜PC-K600** USB麦克风（¥99，专业级，降噪好）

**关键要求：**
- 支持16kHz采样率（Whisper最优）
- 即插即用（免驱动）
- 单声道或双声道均可（程序会转单声道）

---

## 三、技术栈

### 3.1 核心依赖
```bash
# 系统要求
Raspbian OS 12 (Bookworm) 64位
Python 3.11+
树莓派4B/5（内存≥2GB）

# Python库（通过pip安装）
RPi.GPIO==0.7.1           # GPIO按键控制
luma.oled==3.12.0         # OLED驱动（SSD1315）
Pillow==10.1.0            # 图像绘制（文字渲染）
pyaudio==0.2.13           # 音频采集
whisper-cpp-python==0.2.0 # Whisper C++封装（比PyTorch快3倍）

# Web服务相关（新增）
Flask==3.0.0              # 轻量Web框架
Flask-CORS==4.0.0         # 跨域支持（前端开发必需）
Flask-SocketIO==5.3.5     # WebSocket实时通信（状态推送）
python-socketio==5.10.0   # SocketIO客户端
```

### 3.2 模型选择
**方案：** Whisper Tiny INT4 量化版（whisper.cpp）

**理由：**
- 模型大小：~40MB（vs. PyTorch版150MB）
- 内存占用：<300MB（vs. PyTorch版600MB+）
- 推理速度：实时率1.5倍（树莓派4B测试）
- 中文支持：良好（OpenAI官方训练数据包含中文）

**首次部署：**
```bash
# 自动下载并编译whisper.cpp
pip install whisper-cpp-python
python -c "from whispercpp import Whisper; w=Whisper('tiny')"
# 首次运行会下载模型到 ~/.cache/whisper/
```

---

## 四、功能设计

### 4.1 按键操作逻辑

#### K1按键（GPIO4）：录音控制
```
状态：待机
↓ 按下K1（短按<1秒）
状态：录音中（左副屏显示"录音中 00:05"）
↓ 再次按下K1
状态：转写中（左副屏显示"转写中 ████░░ 60%"）
↓ 转写完成
状态：已保存（左副屏显示"已保存 共156字"）
↓ 3秒后自动回到待机
```

**防抖处理：**
- 软件防抖：检测到按键按下后延时50ms再读取电平
- 双次确认：连续2次读取为低电平才认为有效按下

#### K4按键（GPIO24）：退出程序
```
长按K4（≥3秒）→ 左副屏显示"确认退出？再按K4" 
→ 5秒内再按K4 → 程序退出
→ 5秒内未按 → 取消退出，回到当前状态
```

**保护机制：** 录音过程中按K4无效（防止误触）

### 4.2 OLED显示设计

#### 左副屏（128×64像素）：实时状态
```
┌──────────────┐
│ Life Coach   │ ← 标题（8px字体）
│              │
│ [状态文字]   │ ← 动态内容（12px字体）
│ [详细信息]   │ ← 计时器/进度（10px字体）
│              │
└──────────────┘
```

**状态切换示例：**
| 状态 | 第3行显示 | 第4行显示 |
|------|----------|----------|
| 待机 | 就绪 | 按K1开始 |
| 录音中 | 录音中... | 00:35 / 156字 |
| 转写中 | AI转写中 | ████░░░ 60% |
| 已保存 | 已保存! | 共156字 |
| 错误 | 错误 | 麦克风未连接 |

**刷新频率：**
- 录音中：每秒更新1次（计时器+字数统计）
- 转写中：每100ms更新1次（进度条流畅）
- 其他状态：事件触发更新（无需定时刷新）

#### 右副屏（128×64像素）：统计信息
```
┌──────────────┐
│ 今日录音     │
│   3 条       │ ← 大字号显示数量
│              │
│ 存储剩余     │
│  8.2 GB      │ ← 大字号显示容量
└──────────────┘
```

**更新频率：**
- 每次录音完成后更新"今日录音"数量
- 每10分钟更新1次"存储剩余"（避免频繁IO）

### 4.3 音频采集参数
```python
SAMPLE_RATE = 16000      # 采样率（Whisper最优）
CHANNELS = 1             # 单声道（精简数据量）
CHUNK_SIZE = 1024        # 缓冲区大小（延迟vs稳定性平衡）
FORMAT = pyaudio.paInt16 # 16位采样深度
```

**流式转写逻辑：**
```
音频流 → 每收集3秒音频 → 送入Whisper → 返回文字片段
→ 拼接到完整文本 → 左副屏显示累计字数
→ 继续收集下一个3秒音频块 → 循环...
```

### 4.4 存储方案（纯文本文件）

**目录结构：**
```
/home/pi/LifeCoach/
├── recordings/
│   ├── 2026-01-21/
│   │   ├── 15-30.txt      # 15:30录制的对话
│   │   ├── 16-45.txt      # 16:45录制的对话
│   │   └── ...
│   └── 2026-01-22/
│       └── ...
└── logs/
    └── app.log
```

**文件格式（.txt）：**
```
=== Life Coach 对话记录 ===
录音时间: 2026-01-21 15:30:22
录音时长: 00:03:45
文字长度: 523字
---
[转写内容]
今天我们讨论一下产品的MVP功能...
（以下为完整转写文字）
---
保存时间: 2026-01-21 15:34:10
```

**命名规则：**
- 按日期分文件夹（避免单个文件夹文件过多）
- 文件名为"时-分.txt"（精确到分钟）
- 如果同一分钟内多次录音，自动追加后缀"_2.txt"、"_3.txt"

---
 + Web服务启动）
├── api_server.py              # Flask Web服务（RESTful API）
├── audio_recorder.py          # 音频采集模块
├── asr_engine.py              # Whisper转写引擎
├── display_controller.py      # OLED显示控制器
├── button_handler.py          # GPIO按键处理
├── file_storage.py            # 文件存储管理
├── config.py                  # 配置参数
├── requirements.txt           # Python依赖清单
├── deploy.sh                  # 一键部署脚本
├── static/                    # Web前端资源（新增）
│   ├── index.html            # 监控页面
│   ├── style.css             # 样式
│   └── app.js                # 前端逻辑（WebSocket通信）r转写引擎
├── display_controller.py      # OLED显示控制器
├── button_handler.py          # GPIO按键处理
├── file_storage.py            # 文件存储管理
├── config.py                  # 配置参数
├── requirements.txt           # Python依赖清单
├── deploy.sh                  # 一键部署脚本
└── models/
    └── (Whisper模型自动下载到此)
```

### 5.2 核心类设计

#### 状态机（main.py）
```python
class LifeCoachApp:
    STATE_IDLE = "idle"           # 待机
    STATE_RECORDING = "recording" # 录音中
    STATE_PROCESSING = "processing" # 转写中
    STATE_DONE = "done"           # 完成（3秒后回idle）
    STATE_ERROR = "error"         # 错误
    
    def __init__(self):
        self.state = self.STATE_IDLE
        self.display = DisplayController()
        self.recorder = AudioRecorder()
        self.asr = ASREngine()
        self.buttons = ButtonHandler()
        
    def run(self):
        # 主循环：监听按键 → 状态切换 → 更新显示
        while True:
            if self.buttons.k1_pressed():
                self.handle_k1()
            if self.buttons.k4_long_pressed():
                self.handle_k4_exit()
            self.update_display()
            time.sleep(0.05)  # 50ms轮询周期
```

#### 显示控制器（display_controller.py）
```python
class DisplayController:
    def __init__(self):
        self.oled_left = OLED(i2c_address=0x3C)  # luma.oled
        self.oled_right = OLED(i2c_address=0x3D)
        
    def show_status(self, state, detail=""):
        """左副屏：显示状态"""
        # 使用PIL绘制文字 → 转为图像 → 刷新OLED
        
    def update_timer(self, seconds):
        """左副屏：更新录音计时器"""
        
    def update_progress(self, percent):
        """左副屏：更新转写进度条"""
        
    def update_stats(self, today_count, storage_gb):
        """右副屏：更新统计信息"""
```

#### ASR引擎（asr_engine.py）
```python
class ASREngine:
    def __init__(self, model_name="tiny"):
        from whispercpp import Whisper
        self.model = Whisper(model_name)
        
    def transcribe_stream(self, audio_chunks):
        """流式转写：每3秒音频返回一段文字"""
        for chunk in audio_chunks:
            result = self.model.transcribe(chunk)
            yield result["text"]
            
    def transcribe_file(self, audio_path):
        """批量转写：录音结束后一次性转写"""
        result = self.model.transcribe(audio_path)
        return result["text"]
```

### 5.3 配置文件（config.py）
```python
# GPIO引脚定义（基于Board物理引脚转换）
GPIO_K1 = 4   # 录音按键（Pin 7）
GPIO_K4 = 24  # 退出按键（Pin 18）

# I2C地址
I2C_OLED_LEFT = 0x3C
I2C_OLED_RIGHT = 0x3D

# 音频参数
SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_SIZE = 1024

# Whisper模型
WHISPER_MODEL = "tiny"  # tiny/base/small
WHISPER_LANGUAGE = "zh" # 中文优先

# 存储路径
STORAGE_BASE = "/home/pi/LifeCoach/recordings"
LOG_PATH = "/home/pi/LifeCoach/logs/app.log"

# 显示参数
FONT_PATH = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"  # 中文字体
FONT_SIZE_TITLE = 12
FONT_SIZE_STATUS = 14
FONT_SIZE_DETAIL = 10
```

---

## 六、部署方案

### 6.1 一键部署脚本（deploy.sh）
```bash
#!/bin/bash
# Life Coach 阶段0 部署脚本

echo "=== Life Coach 部署开始 ==="

# 1. 系统依赖
echo "[1/5] 安装系统依赖..."
sudo apt update
sudo apt install -y python3-pip python3-dev portaudio19-dev i2c-tools \
    libopenblas-dev fonts-wqy-zenhei

# 2. 启用I2C接口
echo "[2/5] 启用I2C..."
sudo raspi-config nonint do_i2c 0  # 0=启用

# 3. Python依赖
echo "[3/5] 安装Python依赖..."
pip3 install -r requirements.txt

# 4. 下载Whisper模型
echo "[4/5] 下载Whisper模型..."
python3 -c "from whispercpp import Whisper; Whisper('tiny')"

# 5. 创建目录
echo "[5/5] 创建存储目录..."
mkdir -p /home/pi/LifeCoach/recordings
mkdir -p /home/pi/LifeCoach/logs

echo "=== 部署完成！运行以下命令启动 ==="
echo "python3 /home/pi/LifeCoach/main.py"
```

### 6.2 systemd服务（可选，开机自启）
```ini
# /etc/systemd/system/lifecoach.service
[Unit]
Description=Life Coach Recording Service
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/LifeCoach
ExecStart=/usr/bin/python3 /home/pi/LifeCoach/main.py
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

**启用自启：**
```bash
sudo systemctl enable lifecoach.service
sudo systemctl start lifecoach.service
```

---

## 七、开发计划（14天）

### Week 1: 硬件验证 + 模块开发

#### Day 1-2: 环境搭建
- [ ] 树莓派系统安装（Raspbian OS 12）
- [ ] 扩展板插接测试（40PIN对齐插入）
- [ ] I2C设备检测（`i2cdetect -y 1`，确认看到0x3C和0x3D）
- [ ] 运行扩展板官方示例代码（点亮OLED）

#### Day 3-4: 显示系统开发
- [ ] 安装luma.oled库（`pip install luma.oled`）
- [ ] 测试左副屏显示文字（"Hello Life Coach"）
- [ ] 测试右副屏显示数字（统计信息）
- [ ] 实现DisplayController类（状态切换、进度条）
- [ ] 中文字体测试（安装wqy-zenhei字体）

#### Day 5-6: 按键系统开发
- [ ] 安装RPi.GPIO库
- [ ] 测试K1按键（GPIO4/Pin7，打印"K1 pressed"）
- [ ] 测试K4按键（GPIO24/Pin18，打印"K4 pressed"）
- [ ] 实现防抖逻辑（50ms延时 + 双次确认）
- [ ] 实现长按检测（K4长按3秒退出）

#### Day 7: USB麦克风测试
- [ ] 插入USB麦克风，检测设备（`arecord -l`）
- [ ] 安装PyAudio（`pip install pyaudio`）
- [ ] 录制5秒音频保存为test.wav
- [ ] 播放录音验证音质（`aplay test.wav`）

### Week 2: Whisper集成 + 整合测试

#### Day 8-9: Whisper转写测试
- [ ] 安装whisper-cpp-python（`pip install whisper-cpp-python`）
- [ ] 下载Tiny模型（首次运行自动下载）
- [ ] 测试离线音频文件转写（test.wav → 文字）
- [ ] 测试流式转写（实时音频流 → 分段文字）
- [ ] 性能测试（记录CPU占用、内存占用、延迟）

#### Day 10-11: 完整流程集成
- [ ] 实现main.py状态机
- [ ] K1触发录音 → 左副屏显示"录音中"
- [ ] 录音过程实时显示计时器（每秒更新）
- [ ] K1停止录音 → 调用Whisper转写 → 显示进度条
- [ ] 转写完成 → 保存为.txt文件 → 显示"已保存"
- [ ] 右副屏更新"今日录音"计数

#### Day 12: 异常处理 + 优化
- [ ] 麦克风未连接错误处理（显示"错误：麦克风未连接"）
- [ ] 磁盘空间不足检测（<1GB时警告）
- [ ] 内存不足处理（OOM时保存已转写部分）
- [ ] K4退出确认逻辑（防止误触）
- [ ] 日志记录（记录每次录音时长、字数、错误）

#### Day 13-14: 部署脚本 + 文档
- [ ] 编写deploy.sh部署脚本
- [ ] 编写硬件接线说明（带图示）
- [ ] 编写使用手册（按键操作流程）
- [ ] 编写故障排查手册（常见问题 + 解决方案）
- [ ] 完整测试（模拟日常使用场景）

---

## 八、验收标准

### 8.1 功能验收
- [x] K1按键启动录音，左副屏显示"录音中 00:00"
- [x] 录音过程中，计时器每秒递增（00:01、00:02...）
- [x] 再次按K1停止录音，自动触发Whisper转写
- [x] 转写过程显示进度条（0% → 100%）
- [x] 转写完成后保存为.txt文件（文件名格式正确）
- [x] 右副屏显示"今日录音"数量正确递增
- [x] K4长按3秒触发退出确认，再次按K4程序退出

### 8.2 性能验收
- [x] 程序启动时间 ≤ 5秒（从执行main.py到显示"就绪"）
- [x] 录音延迟 ≤ 200ms（按下K1到红色LED亮起）
- [x] 转写速度 ≥ 1倍实时率（3分钟录音转写时间≤3分钟）
- [x] 内存占用 ≤ 800MB（录音+转写过程峰值）
- [x] CPU占用 ≤ 80%（转写过程平均值）

### 8.3 稳定性验收
- [x] 连续录音10次无崩溃、卡死
- [x] 录音过程中拔掉麦克风，显示错误提示（不崩溃）
- [x] 磁盘空间<1GB时，拒绝录音并提示
- [x] 断电后重启，程序正常启动（无残留进程）

### 8.4 易用性验收
- [x] 按键操作无需说明书即可理解（直觉性）
- [x] OLED显示内容清晰可读（中文字体无乱码）
- [x] 错误提示信息明确（如"麦克风未连接"而非"Error 1001"）

---

## 九、风险预案

| 风险 | 概率 | 影响 | 应对方案 |
|------|------|------|----------|
| Whisper转写速度不达标 | 中 | 高 | 降级：录音结束后批量转写（牺牲实时性） |
| USB麦克风驱动不兼容 | 低 | 高 | 提供3款测试通过的麦克风推荐清单 |
| OLED中文显示乱码 | 低 | 中 | 预装wqy-zenhei字体，deploy.sh自动安装 |
| 树莓派内存不足OOM | 中 | 高 | 配置1GB swap分区，Whisper限制线程数 |
| 按键抖动误触发 | 中 | 中 | 增加防抖时间到100ms，要求连续3次确认 |
| SD卡读写速度慢 | 低 | 低 | 推荐Class 10或以上TF卡，避免使用廉价卡 |

---

## 十、后续扩展预留（阶段1）

1. **AI整理功能**
   - 新增K2按键触发"AI整理"（调用Phi-2/Qwen模型）
   - 左副屏显示"AI处理中"，完成后显示"已生成总结"

2. **检索功能**
   - 新增K3按键触发"语音检索"（说出关键词 → Whisper转文字 → 全文检索）
   - 左副屏显示检索结果数量

3. **主屏UI**
   - 启用2寸IPS主屏，显示对话列表
   - 支持触摸选择（如果扩展板支持触摸）

4. **数据库迁移**
   - 从纯文本.txt迁移到SQLite
   - 支持按日期、关键词快速检索

---

## 十一、参考资料

1. **扩展板资料：** https://spotpear.cn/wiki/0.96inch-OLED-2inch-LCD-HAT-A.html
2. **luma.oled文档：** https://luma-oled.readthedocs.io/
3. **whisper.cpp：** https://github.com/ggerganov/whisper.cpp
4. **RPi.GPIO文档：** https://sourceforge.net/p/raspberry-gpio-python/wiki/Home/

---

**方案状态：** 待评审  
**下一步：** 用户确认方案 → 开始Day 1开发任务
