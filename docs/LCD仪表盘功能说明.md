# LCD 仪表盘功能说明

## 概述

LCD主屏现在支持仪表盘模式（方案3），实时显示系统统计信息和录音状态。

## 功能特性

### 1. 仪表盘布局

```
┌────────────────────────┐
│  Life Coach  00:15:32  │  ← 顶部：标题 + 当前时间
├──────────┬─────────────┤
│ 录音状态  │   待机      │  ← 状态区：左侧标签 + 右侧值
│ 持续时长  │   00:00     │
│ 字数统计  │   0字       │
│ CPU温度   │   45°C      │  ← 温度过高(>70°C)会变红
│ 内存使用  │   35%       │
├──────────┴─────────────┤
│ 最近一次转录:           │  ← 中部：最近转录预览
│ "你好，今天天气不错，   │     (最多显示2行)
│  我们去哪里玩呢？"      │
├────────────────────────┤
│ 今日 3次/15分钟         │  ← 底部：今日统计
└────────────────────────┘
```

### 2. 显示模式

#### 仪表盘模式（待机时）
- 自动刷新，默认每3秒更新一次
- 显示系统状态和统计信息
- 深蓝色背景，信息条理清晰

#### 转录模式（录音时）
- 录音时自动切换到转录模式
- 实时显示转录文本
- 录音结束后自动切回仪表盘

### 3. 数据来源

- **录音状态**: 从主程序状态机获取（待机/录音中/处理中/已完成）
- **持续时长**: 录音计时器，格式 MM:SS
- **字数统计**: 实时转录的字数
- **CPU温度**: 从 `/sys/class/thermal/thermal_zone0/temp` 读取（树莓派）
- **内存使用**: 通过 `psutil.virtual_memory()` 获取
- **今日统计**: 从文件存储中查询今日录音记录
- **最近转录**: 显示最后一次录音的前50个字符

### 4. 自动刷新机制

仪表盘有两种刷新方式：

1. **后台定时刷新**（display_controller.py）
   - LCD刷新线程每3秒自动更新一次
   - 更新当前时间、系统状态等

2. **主循环更新**（main.py）
   - 主循环每5秒更新统计数据
   - 调用 `display.update_dashboard(**stats)` 推送最新数据
   - 刷新今日统计、录音次数等

## 安装依赖

```bash
# 安装psutil用于系统监控
bash install_dashboard_deps.sh
```

或手动安装：
```bash
pip3 install psutil
```

## 使用方法

### 启动程序
```bash
python3 main.py
```

仪表盘会自动显示在LCD主屏上，无需额外配置。

### 按钮操作
- **K1 (GPIO4)**: 开始/停止录音
  - 待机时按下：开始录音，LCD切换到转录模式
  - 录音中按下：停止录音，LCD切换回仪表盘模式
  
- **K4 (GPIO24)**: 长按3秒退出程序

### API调用

也可以通过编程方式更新仪表盘：

```python
# 更新仪表盘数据
display.update_dashboard(
    recording_status='录音中',
    duration=125,  # 秒
    word_count=150,
    cpu_temp=55.5,
    memory_usage=42.3,
    today_count=5,
    today_duration=600,
    last_transcript='这是最近一次转录的内容...'
)

# 手动切换模式
display.switch_to_transcript_mode()  # 切换到转录模式
display.switch_to_dashboard_mode()   # 切换回仪表盘模式
```

## 代码结构

### 核心文件

1. **src/display_controller.py**
   - `update_dashboard(**stats)`: 更新仪表盘显示
   - `_lcd_refresh_loop()`: LCD后台刷新线程
   - `switch_to_dashboard_mode()`: 切换到仪表盘模式
   - `switch_to_transcript_mode()`: 切换到转录模式

2. **main.py**
   - `_get_system_stats()`: 采集系统统计信息
   - `_update_today_stats()`: 从存储更新今日统计
   - `run()`: 主循环中每5秒更新仪表盘

## 性能说明

- LCD刷新频率：3秒/次（后台线程）
- 统计更新频率：5秒/次（主循环）
- CPU占用：< 5%
- 内存占用：约增加 10MB（psutil）

## 故障排除

### 仪表盘不更新
1. 检查LCD是否正常初始化
2. 查看日志：`[LCD] 刷新线程已启动`
3. 确认 `display.enabled` 为 True

### CPU温度显示为0
- 非树莓派系统可能不支持
- 检查 `/sys/class/thermal/thermal_zone0/temp` 是否存在

### 内存使用率为0
- 确认已安装 psutil：`pip3 list | grep psutil`
- 检查日志是否有 psutil 相关警告

### 今日统计不准确
- 检查文件存储是否正常工作
- 查看 `storage_path` 配置是否正确

## 配置参数

在 `display_controller.py` 中可以调整：

```python
# LCD刷新间隔（秒）
self.lcd_refresh_interval = 3

# 最近转录显示行数
lines[:2]  # update_dashboard() 中修改
```

在 `main.py` 中可以调整：

```python
# 统计更新间隔（秒）
if current_time - last_stats_update >= 5:
```

## 未来改进

- [ ] 支持手动切换不同仪表盘页面
- [ ] 添加磁盘使用率显示
- [ ] 显示网络状态（Wi-Fi信号强度）
- [ ] 本周/本月统计信息
- [ ] 可配置的刷新间隔（通过config.py）

## 相关文件

- `src/display_controller.py`: 显示控制器
- `main.py`: 主程序
- `install_dashboard_deps.sh`: 依赖安装脚本
- `docs/概要设计-MVP.md`: 硬件设计文档
