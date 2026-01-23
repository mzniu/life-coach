"""
Life Coach 核心功能测试套件
测试API、录音、转写、存储等功能
"""

import unittest
import sys
import os
import time
import json
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import *
from src.display_controller import DisplayController
from src.button_handler import ButtonHandler
from src.audio_recorder import AudioRecorder
from src.asr_engine import ASREngine
from src.file_storage import FileStorage


class TestDisplayController(unittest.TestCase):
    """测试显示控制器"""
    
    def setUp(self):
        self.display = DisplayController()
    
    def test_show_status(self):
        """测试状态显示"""
        self.display.show_status("idle", "就绪")
        self.display.show_status("recording", "录音中")
        self.assertEqual(self.display.left_screen["text"], "RECORDING\n录音中")
    
    def test_update_timer(self):
        """测试计时器更新"""
        self.display.update_timer(65)  # 1分5秒
        # 验证显示正常
    
    def test_update_progress(self):
        """测试进度条更新"""
        for i in range(0, 101, 10):
            self.display.update_progress(i, "转写中")
            time.sleep(0.1)


class TestButtonHandler(unittest.TestCase):
    """测试按键处理器"""
    
    def setUp(self):
        self.buttons = ButtonHandler()
    
    def test_k1_press(self):
        """测试K1按键"""
        self.assertFalse(self.buttons.k1_pressed())
        
        # 模拟按下
        self.buttons.simulate_k1_press()
        self.assertTrue(self.buttons.k1_pressed())
        
        # 只触发一次
        self.assertFalse(self.buttons.k1_pressed())
    
    def test_k4_long_press(self):
        """测试K4长按"""
        self.assertFalse(self.buttons.k4_long_pressed())
        
        # 模拟按下
        self.buttons.simulate_k4_press()
        
        # 短时间内不触发
        self.assertFalse(self.buttons.k4_long_pressed())
        
        # 3秒后触发
        time.sleep(3.1)
        self.assertTrue(self.buttons.k4_long_pressed())


class TestAudioRecorder(unittest.TestCase):
    """测试音频录制器"""
    
    def setUp(self):
        self.recorder = AudioRecorder()
    
    def test_recording_lifecycle(self):
        """测试录音完整流程"""
        # 开始录音
        self.recorder.start()
        self.assertTrue(self.recorder.is_recording)
        
        # 录制2秒
        time.sleep(2)
        duration = self.recorder.get_duration()
        self.assertGreaterEqual(duration, 1)
        
        # 停止录音
        audio_data = self.recorder.stop()
        self.assertFalse(self.recorder.is_recording)
        self.assertGreater(len(audio_data), 0)
    
    def test_cancel_recording(self):
        """测试取消录音"""
        self.recorder.start()
        time.sleep(1)
        
        self.recorder.cancel()
        self.assertFalse(self.recorder.is_recording)
        self.assertEqual(len(self.recorder.audio_data), 0)


class TestASREngine(unittest.TestCase):
    """测试ASR转写引擎"""
    
    def setUp(self):
        self.asr = ASREngine()
    
    def test_transcribe_stream(self):
        """测试流式转写"""
        # 生成模拟音频数据
        audio_chunks = [[0] * 1024 for _ in range(10)]
        
        # 转写
        progress_updates = []
        def callback(percent, text):
            progress_updates.append(percent)
        
        result = self.asr.transcribe_stream(audio_chunks, callback=callback)
        
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)
        self.assertEqual(len(progress_updates), len(audio_chunks))
        self.assertIn(100, progress_updates)
    
    def test_transcribe_file(self):
        """测试文件转写"""
        result = self.asr.transcribe_file("test.wav")
        
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 10)


class TestFileStorage(unittest.TestCase):
    """测试文件存储"""
    
    def setUp(self):
        # 使用临时测试目录
        import tempfile
        self.test_storage_path = Path(tempfile.mkdtemp(prefix="lifecoach_test_"))
        
        # 临时修改存储路径
        import src.config as config_module
        self.original_path = config_module.STORAGE_BASE
        config_module.STORAGE_BASE = str(self.test_storage_path)
        
        self.storage = FileStorage()
    
    def tearDown(self):
        # 恢复原路径
        import src.config as config_module
        config_module.STORAGE_BASE = self.original_path
        
        # 清理测试文件
        import shutil
        if self.test_storage_path.exists():
            shutil.rmtree(self.test_storage_path)
    
    def test_save_and_query(self):
        """测试保存和查询"""
        # 保存录音
        recording_id = "2026-01-21/15-30"
        content = "这是一段测试录音的转写内容。"
        metadata = {"duration": 120, "word_count": len(content)}
        
        self.storage.save(recording_id, content, metadata)
        
        # 查询
        recordings = self.storage.query()
        self.assertEqual(len(recordings), 1)
        self.assertEqual(recordings[0]['id'], recording_id)
    
    def test_get_recording_detail(self):
        """测试获取详情"""
        # 保存
        recording_id = "2026-01-21/16-00"
        content = "详细内容测试。"
        self.storage.save(recording_id, content)
        
        # 获取
        detail = self.storage.get(recording_id)
        self.assertIsNotNone(detail)
        self.assertEqual(detail['id'], recording_id)
        self.assertIn("详细内容", detail['content'])
    
    def test_delete_recording(self):
        """测试删除"""
        # 保存
        recording_id = "2026-01-21/17-00"
        self.storage.save(recording_id, "测试删除")
        
        # 删除
        result = self.storage.delete(recording_id)
        self.assertTrue(result)
        
        # 验证已删除
        detail = self.storage.get(recording_id)
        self.assertIsNone(detail)
    
    def test_get_today_count(self):
        """测试获取今日录音数"""
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 保存3条录音
        for i in range(3):
            recording_id = f"{today}/{14+i:02d}-00"
            self.storage.save(recording_id, f"第{i+1}条")
        
        count = self.storage.get_today_count()
        self.assertEqual(count, 3)


class TestIntegration(unittest.TestCase):
    """集成测试"""
    
    def test_full_recording_flow(self):
        """测试完整录音流程"""
        print("\n=== 测试完整录音流程 ===")
        
        # 1. 初始化模块
        display = DisplayController()
        recorder = AudioRecorder()
        asr = ASREngine()
        
        # 2. 开始录音
        print("开始录音...")
        recorder.start()
        display.show_status("recording", "录音中")
        
        # 3. 录制2秒
        for i in range(2):
            time.sleep(1)
            duration = recorder.get_duration()
            display.update_timer(duration)
            print(f"录音时长: {duration}秒")
        
        # 4. 停止录音
        print("停止录音...")
        audio_data = recorder.stop()
        display.show_status("processing", "转写中")
        
        # 5. 转写
        print("开始转写...")
        def callback(percent, text):
            display.update_progress(percent, "转写中")
            print(f"转写进度: {percent}%")
        
        text = asr.transcribe_stream(audio_data, callback=callback)
        
        # 6. 完成
        print(f"转写完成: {text}")
        display.show_status("done", f"已保存 {len(text)}字")
        
        self.assertGreater(len(text), 0)


def run_tests():
    """运行所有测试"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestDisplayController))
    suite.addTests(loader.loadTestsFromTestCase(TestButtonHandler))
    suite.addTests(loader.loadTestsFromTestCase(TestAudioRecorder))
    suite.addTests(loader.loadTestsFromTestCase(TestASREngine))
    suite.addTests(loader.loadTestsFromTestCase(TestFileStorage))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 返回测试结果
    return result.wasSuccessful()


if __name__ == '__main__':
    print("=" * 60)
    print("  Life Coach 测试套件")
    print("=" * 60)
    print()
    
    success = run_tests()
    
    print()
    print("=" * 60)
    if success:
        print("✅ 所有测试通过")
    else:
        print("❌ 部分测试失败")
    print("=" * 60)
    
    sys.exit(0 if success else 1)
