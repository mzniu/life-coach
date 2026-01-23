# Life Coach 测试目录

本目录包含 Life Coach 的所有测试用例。

## 测试文件

### test_core.py
核心功能单元测试，包括：
- 显示控制器测试
- 按键处理测试
- 音频录制测试
- ASR转写测试
- 文件存储测试
- 集成测试

**运行方式：**
```bash
python tests/test_core.py
```

### test_api.py
API接口测试，包括：
- 状态查询测试
- 录音控制测试
- 录音列表查询测试

**运行方式：**
```bash
# 先启动服务
python main.py

# 在另一个终端运行测试
python tests/test_api.py
```

## 快速运行所有测试

### Windows (PowerShell)
```powershell
# 运行核心测试
python tests\test_core.py

# 运行API测试（需要先启动服务）
python main.py  # 在第一个终端
python tests\test_api.py  # 在第二个终端
```

### Linux/Mac
```bash
# 运行核心测试
python3 tests/test_core.py

# 运行API测试
python3 main.py &  # 后台启动服务
sleep 3  # 等待服务启动
python3 tests/test_api.py
```

## 测试覆盖

- ✅ 模块初始化
- ✅ 显示状态更新
- ✅ 按键模拟
- ✅ 录音流程
- ✅ 转写流程
- ✅ 文件保存/读取/删除
- ✅ API接口调用
- ✅ 完整流程集成

## 注意事项

1. **核心测试**不需要启动Web服务，可以直接运行
2. **API测试**需要先启动服务（`python main.py`）
3. 测试会在 `tests/test_recordings/` 目录创建临时文件，测试完成后自动清理
4. 模拟模式下的测试使用假数据，不依赖硬件

## 测试结果示例

```
======================================================
  Life Coach 测试套件
======================================================

test_cancel_recording (test_core.TestAudioRecorder) ... ok
test_recording_lifecycle (test_core.TestAudioRecorder) ... ok
test_transcribe_file (test_core.TestASREngine) ... ok
test_transcribe_stream (test_core.TestASREngine) ... ok
...

------------------------------------------------------
Ran 15 tests in 12.345s

OK

======================================================
✅ 所有测试通过
======================================================
```
