# 纠错按钮Bug修复说明

## 问题描述

用户报告"重新纠正"按钮存在严重bug：
- 点击"重新纠正"按钮时，使用的是已纠正过的文本，而不是原始ASR识别文本
- 导致多次纠正产生级联文件：`21-52.corrected.corrected.corrected.txt`
- 纠错结果变成无意义的重复标点符号：`；；；；；；...`

## 根本原因

### 1. 文件存储层（`src/file_storage.py`）

原实现使用 `glob(f"{time_str}*.txt")` 查找文件，会匹配：
- `21-52.txt` （原始文本）
- `21-52.corrected.txt` （纠正后文本）

返回的 `content` 字段内容不确定，可能是原始文本或纠正后文本。

### 2. 前端层（`static/app.js`）

`recorrectRecording()` 函数使用：
```javascript
const originalText = recording.content;  // ⚠️ Bug: 可能是纠正后文本
```

## 解决方案

### 1. 文件存储层修改

**文件**: [src/file_storage.py](../src/file_storage.py#L251-L315)

**修改内容**:
- 明确查找 `{time_str}.txt` （原始文件）
- 单独查找 `{time_str}.corrected.txt` （纠正文件）
- 返回三个字段：
  - `original_content`: 原始ASR识别文本（始终从 `.txt` 文件读取）
  - `corrected_content`: 纠正后文本（从 `.corrected.txt` 文件读取，可能为 `None`）
  - `content`: 向后兼容字段，优先返回纠正后文本

**代码示例**:
```python
# 查找原始文件
original_file = date_dir / f"{time_str}.txt"
if not original_file.exists():
    return None

# 读取原始文本
original_text = ...

# 查找纠错后的文本
corrected_file = date_dir / f"{time_str}.corrected.txt"
corrected_text = None
if corrected_file.exists():
    corrected_text = ...

return {
    'id': recording_id,
    'original_content': original_text,      # 新增
    'corrected_content': corrected_text,    # 新增
    'content': corrected_text if corrected_text else original_text,  # 兼容
    ...
}
```

### 2. 前端层修改

**文件**: [static/app.js](../static/app.js#L575-L660)

**修改内容**:
```javascript
// 【修复前】使用 content（可能是纠正后文本）
const originalText = recording.content;

// 【修复后】明确使用 original_content（始终是原始ASR文本）
const originalText = recording.original_content;
```

## 测试验证

### 测试步骤

1. **清理测试环境**:
   ```bash
   # 删除旧的纠错文件
   rm ~/LifeCoach/data/2026-01-23/21-52.corrected*.txt
   ```

2. **部署修复**:
   ```bash
   # 上传修改后的文件
   scp src/file_storage.py cmit@192.168.1.28:~/LifeCoach/src/
   scp static/app.js cmit@192.168.1.28:~/LifeCoach/static/
   
   # 重启服务
   ssh cmit@192.168.1.28 "sudo systemctl restart lifecoach"
   ```

3. **功能测试**:
   - 打开前端页面
   - 点击录音的"重新纠正"按钮
   - 验证：
     - 第一次纠正：生成 `21-52.corrected.txt`
     - 第二次纠正：覆盖 `21-52.corrected.txt`（不再生成 `.corrected.corrected.txt`）
     - 纠正结果正确（不再出现重复标点符号）

4. **日志验证**:
   ```bash
   ssh cmit@192.168.1.28 "sudo journalctl -u lifecoach -f"
   ```
   查看日志应显示：
   ```
   [09:XX:XX] 开始重新纠正录音: 2026-01-23/21-52
   [09:XX:XX] 原始文本: 开始测试 开始测试 尊敬的...
   [09:XX:XX] ✓ 纠正文本已保存: 2026-01-23/21-52.corrected.txt
   [09:XX:XX] ✓ 纠正完成: ...
   ```

### 预期结果

- ✅ 每次点击"重新纠正"都使用原始ASR文本
- ✅ 只生成/覆盖 `.corrected.txt` 文件，不会产生 `.corrected.corrected.txt`
- ✅ 纠正结果正确，不会出现乱码或重复标点
- ✅ 向后兼容：未修改的地方仍可使用 `content` 字段

## API变更说明

### GET `/api/recordings/<recording_id>`

**响应变更**（向后兼容）:
```json
{
  "success": true,
  "recording": {
    "id": "2026-01-23/21-52",
    "date": "2026-01-23",
    "time": "21:52:00",
    "duration": 15.5,
    "word_count": 120,
    "original_content": "开始测试 开始测试 尊敬的客户...",  // 新增：原始ASR文本
    "corrected_content": "开始测试，尊敬的客户...",        // 新增：纠正后文本（可能为null）
    "content": "开始测试，尊敬的客户...",                  // 兼容：优先返回纠正后文本
    "audio_path": "/path/to/audio.wav"
  }
}
```

### 字段说明

| 字段 | 说明 | 来源文件 |
|------|------|----------|
| `original_content` | 原始ASR识别文本，始终存在 | `{recording_id}.txt` |
| `corrected_content` | 纠正后文本，可能为 `null` | `{recording_id}.corrected.txt` |
| `content` | 向后兼容字段，优先返回纠正后文本 | 优先使用 `corrected_content`，回退到 `original_content` |

## 影响范围

### 修改文件
1. [src/file_storage.py](../src/file_storage.py) - `get()` 方法
2. [static/app.js](../static/app.js) - `recorrectRecording()` 函数

### 不影响的功能
- 查看录音：仍使用 `content` 字段（优先显示纠正后文本）
- 录音列表：仍使用 `text_corrected` 和 `text_original` 字段
- 音频播放：不受影响
- 删除录音：不受影响

## 回滚方案

如果需要回滚：
```bash
# 恢复旧版本（从git）
git checkout HEAD~1 -- src/file_storage.py static/app.js

# 或手动恢复
scp backup/file_storage.py cmit@192.168.1.28:~/LifeCoach/src/
scp backup/app.js cmit@192.168.1.28:~/LifeCoach/static/

# 重启服务
ssh cmit@192.168.1.28 "sudo systemctl restart lifecoach"
```

## 后续改进建议

1. **文件命名规范**：
   - 考虑使用版本号：`21-52.txt`, `21-52.corrected.v1.txt`, `21-52.corrected.v2.txt`
   - 或时间戳：`21-52.corrected.20260123-092638.txt`

2. **UI改进**：
   - 显示纠正历史（如果有多个版本）
   - 添加"比对"功能，并排显示原始文本和纠正文本
   - 添加"撤销纠正"按钮，删除 `.corrected.txt` 文件

3. **数据模型**：
   - 考虑使用SQLite存储元数据
   - 记录纠正时间、引擎版本、置信度等信息

4. **API增强**：
   - 添加 `/api/recordings/<id>/history` 获取纠正历史
   - 添加 `/api/recordings/<id>/diff` 获取原始与纠正的差异

---

**修复时间**: 2026-01-23  
**修复人**: GitHub Copilot  
**测试状态**: 待测试
