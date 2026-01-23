# Life Coach - 对话记录助手

AI驱动的对话记录与智能梳理工具，支持语音转写、本地存储、Web远程控制。

**当前版本：** 阶段0 - 最小MVP（代码框架）

---

## 快速开始

> **详细步骤请查看**: [QUICKSTART.md](QUICKSTART.md)

### 1. 硬件要求

- 树莓派 4B/5（内存≥2GB，推荐4GB）
- 0.96inch OLED 2inch LCD HAT 扩展板
- USB麦克风（推荐绿联USB声卡+麦克风）
- TF卡 ≥16GB（Class 10）

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

### 阶段0（当前）
- ✅ Web监控面板（浏览器实时查看状态）
- ✅ RESTful API（支持前端开发）
- ✅ WebSocket实时通信（状态推送）
- ✅ 文本纠错（ASR后自动修正错别字和标点，可选）
- 🔲 GPIO按键控制（K1录音/K4退出）
- 🔲 OLED双屏显示（状态/统计）
- 🔲 USB麦克风录音
- 🔲 Whisper实时转写

### 阶段1（规划中）
- AI智能整理（结构化/关键词/总结）
- 录音检索功能
- 待办事项提取

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
| K1按键（录音） | Pin 7 | GPIO4 |
| K4按键（退出） | Pin 18 | GPIO24 |
| 左OLED（SDA） | Pin 3 | GPIO2 |
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

---

## 文件结构

```
LifeCoach/
├── main.py                  # 主程序入口
├── requirements.txt         # Python依赖
├── deploy.sh                # 部署脚本（待创建）
├── src/                     # 源代码
│   ├── config.py           # 配置文件
│   ├── api_server.py       # Web API服务
│   ├── display_controller.py   # OLED显示（待实现）
│   ├── button_handler.py       # GPIO按键（待实现）
│   ├── audio_recorder.py       # 音频录制（待实现）
│   ├── asr_engine.py           # Whisper转写（待实现）
│   └── file_storage.py         # 文件存储（待实现）
├── static/                  # Web前端
│   ├── index.html          # 监控页面
│   ├── style.css           # 样式
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
```bash
sudo raspi-config
# 选择 Interface Options → I2C → Enable
```

**检测I2C设备：**
```bash
i2cdetect -y 1
```

应该看到 `3c` 和 `3d` 地址

### 5. 文本纠错功能无效？

**确认模型已下载：**
```bash
ls -lh ~/LifeCoach/models/qwen2.5-0.5b/
```

**检查环境变量：**
```bash
# .env 文件中确认
TEXT_CORRECTION_ENABLED=true
```

**查看启动日志：**
```bash
sudo journalctl -u lifecoach -f
# 应该看到 "Text correction enabled"
```

---

## 配置说明

### 环境变量（.env）

核心配置项（其他配置见 `.env.example`）：

```bash
# === 文本纠错（可选） ===
TEXT_CORRECTION_ENABLED=false                                    # 是否启用纠错功能
TEXT_CORRECTION_MODEL=/home/pi/LifeCoach/models/qwen2.5-0.5b/...gguf  # 模型路径
TEXT_CORRECTION_MAX_TOKENS=512                                   # 最大生成token数
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
- 重复输入直接返回缓存结果

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
