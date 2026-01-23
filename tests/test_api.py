"""
API接口测试
测试Web服务的RESTful API和WebSocket通信
"""

import unittest
import sys
import time
import requests
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# API基础URL（需要先启动服务）
API_BASE = "http://localhost:5000/api"


class TestAPIEndpoints(unittest.TestCase):
    """测试API端点"""
    
    @classmethod
    def setUpClass(cls):
        """测试前检查服务是否运行"""
        try:
            response = requests.get(f"{API_BASE}/status", timeout=2)
            if response.status_code != 200:
                raise Exception("服务未正常响应")
        except Exception as e:
            print(f"\n❌ 错误: 服务未运行")
            print(f"请先在另一个终端运行: python main.py")
            print(f"然后再执行测试")
            raise unittest.SkipTest("服务未运行")
    
    def test_get_status(self):
        """测试获取状态"""
        response = requests.get(f"{API_BASE}/status")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn("status", data)
        self.assertIn("recording", data)
        self.assertIn("stats", data)
        print(f"✓ 状态: {data['status']}")
    
    def test_recording_flow(self):
        """测试录音完整流程"""
        print("\n=== 测试录音API流程 ===")
        
        # 1. 开始录音
        print("1. 开始录音...")
        response = requests.post(f"{API_BASE}/recording/start")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertTrue(data['success'])
        recording_id = data.get('recording_id')
        print(f"   录音ID: {recording_id}")
        
        # 2. 等待录音
        print("2. 录音中（等待3秒）...")
        for i in range(3):
            time.sleep(1)
            status = requests.get(f"{API_BASE}/status").json()
            print(f"   时长: {status['recording']['duration']}秒")
        
        # 3. 停止录音
        print("3. 停止录音...")
        response = requests.post(f"{API_BASE}/recording/stop")
        self.assertEqual(response.status_code, 200)
        
        # 4. 等待转写完成
        print("4. 等待转写完成...")
        time.sleep(3)
        
        # 5. 查询录音列表
        print("5. 查询录音列表...")
        response = requests.get(f"{API_BASE}/recordings")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertTrue(data['success'])
        print(f"   录音数量: {data['count']}")
    
    def test_cancel_recording(self):
        """测试取消录音"""
        # 开始录音
        requests.post(f"{API_BASE}/recording/start")
        time.sleep(1)
        
        # 取消
        response = requests.post(f"{API_BASE}/recording/cancel")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertTrue(data['success'])
    
    def test_get_recordings_list(self):
        """测试获取录音列表"""
        response = requests.get(f"{API_BASE}/recordings?limit=5")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('recordings', data)
        print(f"✓ 录音数量: {data['count']}")


def run_api_tests():
    """运行API测试"""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestAPIEndpoints)
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    print("=" * 60)
    print("  Life Coach API 测试")
    print("=" * 60)
    print()
    print("⚠️  提示: 请确保服务已启动")
    print("   命令: python main.py")
    print()
    
    success = run_api_tests()
    
    print()
    print("=" * 60)
    if success:
        print("✅ 所有API测试通过")
    else:
        print("❌ 部分API测试失败")
    print("=" * 60)
    
    sys.exit(0 if success else 1)
