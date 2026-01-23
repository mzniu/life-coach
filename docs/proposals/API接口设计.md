# Life Coach API 接口设计（阶段0）

**版本：** v1.0  
**基础URL：** `http://树莓派IP:5000/api`  
**WebSocket：** `ws://树莓派IP:5000/socket.io`

---

## 一、RESTful API 接口

### 1.1 系统状态查询

#### GET /api/status
获取当前系统状态

**响应示例：**
```json
{
  "status": "idle",              // idle/recording/processing/done/error
  "recording": {
    "duration": 0,               // 录音时长（秒）
    "word_count": 0              // 已转写字数
  },
  "processing": {
    "progress": 0                // 转写进度（0-100）
  },
  "stats": {
    "today_count": 3,            // 今日录音数
    "storage_gb": 8.2            // 剩余存储（GB）
  },
  "hardware": {
    "mic_connected": true,       // 麦克风连接状态
    "oled_left": true,           // 左副屏状态
    "oled_right": true           // 右副屏状态
  }
}
```

---

### 1.2 录音控制

#### POST /api/recording/start
开始录音

**请求体：** 无

**响应：**
```json
{
  "success": true,
  "message": "录音已开始",
  "recording_id": "2026-01-21/15-30"
}
```

#### POST /api/recording/stop
停止录音并开始转写

**请求体：** 无

**响应：**
```json
{
  "success": true,
  "message": "录音已停止，开始转写",
  "recording_id": "2026-01-21/15-30"
}
```

#### POST /api/recording/cancel
取消当前录音

**请求体：** 无

**响应：**
```json
{
  "success": true,
  "message": "录音已取消"
}
```

---

### 1.3 录音记录查询

#### GET /api/recordings
获取录音列表

**查询参数：**
- `date`: 日期过滤（格式：2026-01-21）
- `limit`: 返回数量限制（默认20）

**响应示例：**
```json
{
  "success": true,
  "count": 3,
  "recordings": [
    {
      "id": "2026-01-21/15-30",
      "date": "2026-01-21",
      "time": "15:30:22",
      "duration": 225,           // 秒
      "word_count": 523,
      "preview": "今天我们讨论一下产品的MVP功能..."  // 前50字
    },
    // ...更多记录
  ]
}
```

#### GET /api/recordings/:id
获取单条录音详情

**路径参数：** `id` 格式为 `2026-01-21/15-30`

**响应示例：**
```json
{
  "success": true,
  "recording": {
    "id": "2026-01-21/15-30",
    "date": "2026-01-21",
    "time": "15:30:22",
    "duration": 225,
    "word_count": 523,
    "content": "今天我们讨论一下产品的MVP功能...\n（完整转写内容）"
  }
}
```

#### DELETE /api/recordings/:id
删除录音

**响应：**
```json
{
  "success": true,
  "message": "录音已删除"
}
```

---

### 1.4 系统控制

#### POST /api/system/shutdown
关闭程序

**请求体：**
```json
{
  "confirm": true  // 必须为true
}
```

**响应：**
```json
{
  "success": true,
  "message": "程序即将关闭"
}
```

---

## 二、WebSocket 实时通信

### 2.1 连接地址
```javascript
const socket = io('http://树莓派IP:5000');
```

### 2.2 服务端推送事件

#### status_update
状态变化通知

**推送数据：**
```json
{
  "event": "status_update",
  "data": {
    "status": "recording",
    "detail": "录音中 00:35"
  }
}
```

#### recording_progress
录音进度更新（每秒推送）

**推送数据：**
```json
{
  "event": "recording_progress",
  "data": {
    "duration": 35,
    "word_count": 126
  }
}
```

#### processing_progress
转写进度更新（每100ms推送）

**推送数据：**
```json
{
  "event": "processing_progress",
  "data": {
    "progress": 60,
    "message": "AI转写中"
  }
}
```

#### recording_complete
录音完成通知

**推送数据：**
```json
{
  "event": "recording_complete",
  "data": {
    "recording_id": "2026-01-21/15-30",
    "word_count": 523,
    "duration": 225
  }
}
```

#### error_occurred
错误通知

**推送数据：**
```json
{
  "event": "error_occurred",
  "data": {
    "error": "麦克风未连接",
    "code": "MIC_DISCONNECTED"
  }
}
```

### 2.3 客户端发送事件

#### request_status
请求当前状态

**发送数据：** 无

**响应：** 服务端推送 `status_update` 事件

---

## 三、错误响应格式

所有API错误统一返回格式：

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "错误描述"
  }
}
```

**常见错误码：**
- `INVALID_STATE`: 当前状态不允许此操作（如录音中无法开始新录音）
- `MIC_DISCONNECTED`: 麦克风未连接
- `STORAGE_FULL`: 存储空间不足
- `RECORDING_NOT_FOUND`: 录音记录不存在
- `INTERNAL_ERROR`: 内部错误

---

## 四、前端示例代码

### 4.1 启动录音
```javascript
// REST API方式
fetch('http://树莓派IP:5000/api/recording/start', {
  method: 'POST'
})
.then(res => res.json())
.then(data => console.log(data));

// 监听实时进度
socket.on('recording_progress', (data) => {
  document.getElementById('timer').textContent = 
    `${Math.floor(data.duration / 60)}:${data.duration % 60}`;
  document.getElementById('word-count').textContent = 
    `${data.word_count}字`;
});
```

### 4.2 获取录音列表
```javascript
fetch('http://树莓派IP:5000/api/recordings?limit=10')
  .then(res => res.json())
  .then(data => {
    data.recordings.forEach(rec => {
      console.log(rec.id, rec.preview);
    });
  });
```

---

## 五、部署说明

### 5.1 启动Web服务
```bash
# 默认端口5000
python3 main.py

# 自定义端口
python3 main.py --port 8080

# 允许外网访问（默认仅本地）
python3 main.py --host 0.0.0.0
```

### 5.2 访问地址
- **Web监控页面：** http://树莓派IP:5000
- **API基础路径：** http://树莓派IP:5000/api
- **WebSocket：** ws://树莓派IP:5000/socket.io

### 5.3 防火墙配置
```bash
# 开放5000端口（如果启用防火墙）
sudo ufw allow 5000/tcp
```

---

**下一步：** 参考此API文档开发前端页面或移动端App
