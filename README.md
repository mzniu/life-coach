# Life Coach - 对话记录助手

AI驱动的对话记录与智能梳理工具，支持语音转写、实时转录、本地存储、Web远程控制。

**当前版本：** 阶段0 - MVP核心功能已完成

## ✨ 最新更新

- ✅ **双OLED+LCD显示屏**：实时显示系统状态、统计信息和转录文本
- ✅ **实时转录功能**：录音过程中实时显示转录文本，无需等待
- ✅ **Paraformer ASR引擎**：高性能流式语音识别，支持中英文双语
- ✅ **Silero VAD集成**：智能语音活动检测，精准分段
- ✅ **音频数据优化**：修复数据归一化问题，提升转录质量
- ✅ **自动缓存清理**：部署时自动清理Python字节码缓存

---

## 快速开始

> **详细步骤请查看**: [QUICKSTART.md](QUICKSTART.md)

### 1. 硬件要求

- **树莓派**: 4B/5（内存≥2GB，推荐4GB）
- **显示屏**: OLED-LCD-HAT-A 扩展板
  - 2英寸 IPS LCD主屏 (240×320, ST7789驱动)
  - 双0.96英寸 OLED副屏 (128×64, SSD1306驱动)
- **麦克风**: USB麦克风（推荐绿联USB声卡+麦克风）
- **存储**: TF卡 ≥16GB（Class 10）

> 📘 **显示屏部署指南**: [docs/显示屏部署指南.md](docs/显示屏部署指南.md)

### 2. 一键部署（Windows）

```powershell
# 在项目根目录运行
.\deploy.ps1
```

首次部署会提示输入树莓派密码一次，后续自动免密部署。

### 3. 配置文件同步（Resilio Sync）

**树莓派端**：
```bash
ssh pi@192.168.1.100
cd ~/LifeCoach/deploy
bash setup-resilio-sync.sh
```

**Windows 端**：
- 下载安装 [Resilio Sync](https://www.resilio.com/individuals/)
- 使用树莓派生成的密钥添加同步文件夹

详细步骤见 [QUICKSTART.md](QUICKSTART.md) 或 [deploy/README.md](deploy/README.md)

### 4. （可选）下载文本纠错模型

如需启用ASR后的文本纠错功能：

```bash
# SSH登录到树莓派
cd ~/LifeCoach
python deploy/download_qwen_model.py
```

下载完成后，在 `.env` 中设置：
```bash
TEXT_CORRECTION_ENABLED=true
```

模型文件约330MB，下载支持断点续传。

### 5. 访问Web监控面板

打开浏览器访问：http://192.168.1.100:5000

---

## 功能特性

### 阶段0（已完成核心功能）

#### 语音识别
- ✅ **实时转录**：录音过程中即时显示转录文本（WebSocket推送）
- ✅ **Paraformer ASR**：流式语音识别引擎，支持中英文双语
- ✅ **Silero VAD**：智能语音活动检测，自动分段（0.5秒静音检测）
- ✅ **音频优化**：自动归一化、降噪处理

#### 文本处理
- ✅ **文本纠错**：ASR后自动修正错别字和标点（可选）
- ✅ **Qwen2.5模型**：轻量级0.5B模型，3-8秒完成纠错
- ✅ **智能缓存**：LRU缓存机制，重复文本秒级返回

#### Web服务
- ✅ **监控面板**：实时查看录音状态、字数、时长
- ✅ **RESTful API**：完整的录音、转录、纠错接口
- ✅ **WebSocket通信**：实时状态推送、转录文本推送
- ✅ **录音管理**：查看、删除历史录音记录

#### 显示屏幕
- ✅ **OLED状态屏**：显示系统状态、录音时长、字数统计（I2C 0x3C）
- ✅ **OLED统计屏**：显示录音次数、总时长、CPU/内存使用率（I2C 0x3D）
- ✅ **LCD主屏**：240x320彩屏，实时滚动显示转录文本（SPI）
- ✅ **中文支持**：文泉驿微米黑字体，完美显示中英文混合内容

#### 部署与维护
- ✅ **一键部署**：Windows PowerShell脚本，自动配置SSH免密
- ✅ **自动缓存清理**：每次部署自动清理Python字节码缓存
- ✅ **Systemd服务**：开机自启动，自动重启

#### 待实现功能
- 🔲 GPIO按键控制（K1录音/K4退出）
- 🔲 OLED双屏显示（状态/统计）

### 阶段1（规划中）
- AI智能整理（结构化/关键词/总结）
- 录音检索功能
- 待办事项提取
- 多用户声纹识别

---

## API 接口

### 基础URL
`http://树莓派IP:5000/api`

### 核心接口

#### 获取状态
```bash
GET /api/status
```

#### 录音控制
```bash
POST /api/recording/start   # 开始录音
POST /api/recording/stop    # 停止录音
POST /api/recording/cancel  # 取消录音
```

#### 录音记录
```bash
GET  /api/recordings         # 获取列表
GET  /api/recordings/:id     # 获取详情
DELETE /api/recordings/:id   # 删除
```

#### 文本纠错（可选）
```bash
POST /api/correct_text       # 纠正文本错别字和标点
# 请求体: {"text": "要纠正的文本"}
# 返回: {"corrected": "纠正后的文本", "changes": [...]}

GET /api/correct_text/stats  # 获取纠错统计信息
# 返回: {"total_corrections": 10, "cache_hits": 5, ...}
```

完整API文档：[docs/proposals/API接口设计.md](docs/proposals/API接口设计.md)

---

## 硬件接线

### 扩展板安装
1. 树莓派断电
2. 对齐40PIN GPIO接口，垂直插入扩展板
3. 确保插紧（无松动）

### USB麦克风
直接插入树莓派任意USB口即可（免驱动）

### 引脚占用情况

| 功能 | 物理引脚 | GPIO编号 |
|------|---------|---------|
| K**实时查看**：
   - 录音进度和时长
   - 实时转录文本（边录边显示）
   - 已转录字数统计
4. 点击 "停止录音" 完成转写
5. 等待文本纠错完成（可选）
6. 在"最近录音"列表查看/删除记录

> **提示**：实时转录功能会在录音过程中自动识别语音并显示文字，无需等待录音结束。3 | GPIO2 |
| 左OLED（SCL） | Pin 5 | GPIO3 |

---

## 使用说明

### 方式1：硬件按键

1. 按下 **K1** 开始录音（红色OLED显示"录音中"）
2. 再次按下 **K1** 停止录音（开始转写）
3. 长按 **K4** 3秒退出程序

### 方式2：Web界面

1. 浏览器访问 `http://树莓派IP:5000`
2. 点击 "开始录音" 按钮
3. 实时查看录音进度、转写字数
4. 点击 "停止录音" 完成转写
5. 在"最近录音"列表查看/删除记录

---   # 主程序入口
├── requirements.txt            # Python依赖
├── deploy.ps1                  # Windows部署脚本
├── src/                        # 源代码
│   ├── config.py              # 配置文件
│   ├── api_server.py          # Web API服务
│   ├── audio_recorder_real.py # 音频录制（已实现）
│   ├── asr_paraformer.py      # Paraformer ASR引擎（已实现）
│   ├── realtime_transcriber.py # 实时转录（已实现）
│   ├── vad_silero.py          # Silero VAD（已实现）
│   ├── text_corrector.py      # 文本纠错（已实现）
│   ├── file_storage.py        # 文件存储（已实现）
│   ├── display_controller.py  # OLED显示（待实现）
│   └── button_handler.py      # GPIO按键（待实现）
├── static/                     # Web前端
│   ├── index.html             # 监控页面
│   ├── style.css              # 样式
│   └── app.js                 # 前端逻辑
├── models/                     # AI模型
│   ├── sherpa/                # Paraformer模型
│   │   └── paraformer/        # 流式ASR模型文件
│   └── qwen2.5-0.5b/          # Qwen文本纠错模型
├── deploy/                     # 部署工具
│   ├── deploy-once.ps1        # 一键部署脚本
│   ├── deploy-interactive.ps1 # 交互式部署
│   ├── setup_pi.sh            # 树莓派环境配置
│   └── lifecoach.service      # Systemd服务配置
├── docs/                       # 文档
│   ├── PRD.md                 # 产品需求
│   ├── 概要设计-MVP.md         # 技术设计
│   └── proposals/             # 方案文档
└── recordings/   ss           # 样式
│   └── app.js              # 前端逻辑
├── docs/                    # 文档
│   ├── PRD.md              # 产品需求
│   ├── 概要设计-MVP.md      # 技术设计
│   └── proposals/          # 方案文档
└── recordings/              # 录音存储（自动创建）
```

---

## 常见问题

### 1. Web页面无法访问？

**检查防火墙：**
```bash
sudo ufw allow 5000/tcp
```

**检查树莓派IP：**
```bash
hostname -I
```

### 2. 麦克风无法识别？

**查看音频设备：**
```bash
arecord -l
```

应该看到类似 `card 1: Device [USB Audio Device]`

### 3. 依赖安装失败？

**更新pip：**
```bash
pip3 install --upgrade pip
```

**使用国内镜像：**
```bash
pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 4. OLED屏幕无显示？

**检查I2C是否启用：**
```bash实时转录不工作？

**检查日志查看VAD和ASR状态：**
```bash
sudo journalctl -u lifecoach -f | grep -E 'VAD|ASR|实时转录'
```

**常见问题：**
- 音量过低：调整麦克风音量或降低 `AUDIO_MIN_RMS_THRESHOLD`
- VAD太敏感/不敏感：调整 `REALTIME_VAD_THRESHOLD`（0.2-0.5）
- 分段太快：增加 `REALTIME_MIN_SILENCE_DURATION`

### 6. 文本纠错功能无效？

**确认模型已下载：**
```bash
ls -lh ~/LifeCoach/models/qwen2.5-0.5b/
```

**检查配置：**
```bash
# src/config.py 中确认
TEXT_CORRECTION_ENABLED = True
```

**查看启动日志：**
```bash
sudo journalctl -u lifecoach -f
# 应该看到 "Text correction enabled"
```

### 7. 部署后代码不生效？

这是Python字节码缓存问题，已在最新部署脚本中自动解决。

**手动清理缓存：**
```bash
cd ~/LifeCoach
find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null
find . -type f -name '*.pyc' -delete 2>/dev/null
sudo systemctl restart lifecoach5-0.5b/
```src/config.py）

核心配置项：

```python
# === 实时转录配置 ===
REALTIME_MIN_SILENCE_DURATION = 0.5          # VAD静音检测时长（秒）
REALTIME_VAD_THRESHOLD = 0.3                 # VAD阈值（0-1，越低越敏感）
REALTIME_MIN_SPEECH_DURATION = 0.25          # 最小语音时长（秒）
AUDIO_MIN_RMS_THRESHOLD = 0.01               # 音频RMS阈值（过滤静音）

# === ASR引擎配置 ===
ASR_ENGINE = 'paraformer'                    # 使用Paraformer引擎
PARAFORMER_MODEL_PATH = 'models/sherpa/paraformer'
PARAFORMER_TOKENS_PATH = 'models/sherpa/paraformer/tokens.txt'

# === 文本纠错（可选） ===
TEXT_CORRECTION_ENABLED = False               # 是否启用纠错功能
TEXT_CORRECTION_MODEL = 'models/qwen2.5-0.5b/...'  # 模型路径
TEXT_CORRECTION_TEMPERATURE = 0.3             # 生成温度（0-1，越低越保守）
TEXT_CORRECTION_TIMEOUT = 15                  # 超时秒数

# === 音频设置 ===
AUDIO_DEVICE_INDEX = 2                        # USB麦克风设备编号
AUDIO_SAMPLE_RATE = 16000                     # 采样率
AUDIO_CHANNELS = 1                            # 单声道
```

### 性能指标

**树莓派 4B（4GB）实测性能：**

| 功能 | 延迟 | 说明 |
|-----|------|------|
| VAD语音检测 | <50ms | 实时检测语音活动 |
| 实时转录 | 0.5-2秒/段 | Paraformer流式识别 |
| 文本纠错 | 3-8秒 | Qwen2.5-0.5B模型 |
| 批量转录 | 1-3秒/10秒音频 | 录音结束后完整转录 |

**内存占用：**
- 基础服务：~200MB
- Paraformer ASR：~400MB
- Qwen纠错模型：~400MB
- 峰值总计：~1GB

**优化技术：**
- ✅ sherpa-onnx ONNX推理加速
- ✅ OpenBLAS数学库加速
- ✅ LRU缓存（文本纠错最多50条）
- ✅ 音频预处理（降噪、归一化）N_MAX_TOKENS=512                                   # 最大生成token数
TEXT_CORRECTION_TEMPERATURE=0.3                                  # 生成温度（0-1，越低越保守）
TEXT_CORRECTION_TIMEOUT=15                                       # 超时秒数

# === 音频设置 ===
AUDIO_DEVICE_INDEX=2                                             # USB麦克风设备编号
AUDIO_SAMPLE_RATE=16000
```

### 性能调优

**树莓派4（4GB/8GB）：**
- Whisper Tiny模型：ASR延迟约1-2秒/句话
- Qwen2.5-0.5B模型：纠错耗时3-8秒（已启用OpenBLAS加速）
- 峰值内存占用：约800MB（Whisper）+ 400MB（Qwen）

**缓存策略：**
- 文本纠错启用LRU缓存（最多50条）
## 技术栈

- **后端**：Python 3.9 + Flask + SocketIO
- **ASR引擎**：sherpa-onnx + Paraformer流式模型
- **VAD**：Silero VAD（语音活动检测）
- **文本纠错**：llama-cpp-python + Qwen2.5-0.5B
- **前端**：原生JavaScript + WebSocket
- **部署**：Systemd + PowerShell自动化

---

**当前状态：** ✅ 阶段0核心功能完成（实时转录、Web服务、文本纠错）  
**下一步：** 实现OLED显示 + GPIO按键 + AI智能整理
---

## 开发指南

### 本地调试（非树莓派环境）

1. 注释掉 `src/config.py` 中的GPIO相关依赖
2. 使用模拟模式运行：
```bash
python3 main.py --debug
```

### 前端开发

前端文件在 `static/` 目录，修改后刷新浏览器即可看到效果。

**热重载：**
```bash
python3 main.py --debug
```

### 添加新API接口

在 `src/api_server.py` 中添加路由：
```python
@app.route('/api/your-endpoint', methods=['POST'])
def your_function():
    # 你的逻辑
    return jsonify({"success": True})
```

---

## 许可证

待定

---

## 联系方式

项目仓库：<待补充>

---

**当前状态：** 🔲 阶段0代码框架（Web服务可用，硬件功能待实现）  
**下一步：** 实现OLED显示 + GPIO按键 + 音频录制 + Whisper转写
