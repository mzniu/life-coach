#!/usr/bin/env python3
"""
测试已部署的文本纠错器

通过 LifeCoach API 测试 macro-correct 引擎
"""

import requests
import time
import json

# 树莓派地址
PI_HOST = "192.168.1.28"
API_URL = f"http://{PI_HOST}:5000"

def test_corrector_api():
    """测试文本纠错 API"""
    print("=" * 60)
    print("测试已部署的文本纠错器 (macro-correct)")
    print("=" * 60)
    
    test_cases = [
        "今天天气怎么样我们去哪里玩",
        "真麻烦你了希望你们好好跳舞",
        "少先队员因该为老人让坐",
        "请问你叫什么名字",
        "我想喝一杯咖啡然后去图书馆"
    ]
    
    print(f"\nAPI: {API_URL}/api/correct_text\n")
    
    total_time = 0
    success_count = 0
    
    for i, text in enumerate(test_cases, 1):
        print(f"测试用例 {i}: {text}")
        
        try:
            start = time.time()
            response = requests.post(
                f"{API_URL}/api/correct_text",
                json={"text": text},
                timeout=30
            )
            elapsed = (time.time() - start) * 1000
            
            if response.status_code == 200:
                result = response.json()
                
                print(f"  ✓ 成功")
                print(f"  原文: {result['data']['original']}")
                print(f"  纠正: {result['data']['corrected']}")
                print(f"  改变: {result['data']['changed']}")
                print(f"  耗时: {result['data']['time_ms']} ms (含网络: {elapsed:.0f} ms)")
                
                if result['data']['changed']:
                    print(f"  改变数: {len(result['data']['changes'])}")
                
                total_time += result['data']['time_ms']
                success_count += 1
            else:
                print(f"  ✗ 失败: HTTP {response.status_code}")
                print(f"  {response.text}")
        
        except Exception as e:
            print(f"  ✗ 异常: {e}")
        
        print()
        time.sleep(0.5)
    
    if success_count > 0:
        print("=" * 60)
        print(f"测试完成: {success_count}/{len(test_cases)} 通过")
        print(f"平均耗时: {total_time / success_count:.1f} ms/条")
        print("=" * 60)
    
    return success_count == len(test_cases)


def test_corrector_stats():
    """获取纠错器统计信息"""
    print("\n" + "=" * 60)
    print("查询纠错器统计信息")
    print("=" * 60)
    
    try:
        response = requests.get(f"{API_URL}/api/correct_text/stats", timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            stats = result['data']
            
            print(f"\n引擎类型: {stats['engine']}")
            print(f"已加载: {stats['is_loaded']}")
            print(f"加载耗时: {stats['load_time_seconds']:.2f} 秒")
            print(f"处理次数: {stats['correction_count']}")
            print(f"缓存命中: {stats['cache_hits']}")
            print(f"缓存未命中: {stats['cache_misses']}")
            print(f"缓存大小: {stats['cache_size']}")
            
            return True
        else:
            print(f"✗ 失败: HTTP {response.status_code}")
            return False
    
    except Exception as e:
        print(f"✗ 异常: {e}")
        return False


def main():
    print("测试已部署的 macro-correct 纠错引擎")
    print(f"目标: {API_URL}")
    print("=" * 60)
    
    # 测试 API 可达性
    try:
        response = requests.get(f"{API_URL}/", timeout=5)
        if response.status_code == 200:
            print("✓ 服务可达")
        else:
            print(f"✗ 服务异常: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ 无法连接到服务: {e}")
        return False
    
    # 测试纠错功能
    test_passed = test_corrector_api()
    
    # 获取统计信息
    test_corrector_stats()
    
    return test_passed


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
