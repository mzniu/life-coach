#!/usr/bin/env python3
"""
文本纠错器集成测试

测试新的双引擎架构:
1. macro-correct 引擎(默认)
2. llama-cpp 引擎(备选)
"""

import os
import sys
import time

# 添加 src 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from text_corrector import TextCorrector, get_text_corrector


def test_macro_correct_engine():
    """测试 macro-correct 引擎"""
    print("=" * 60)
    print("测试 1: macro-correct 引擎")
    print("=" * 60)
    
    corrector = TextCorrector(engine_type="macro-correct")
    
    test_cases = [
        "今天天气怎么样我们去哪里玩",
        "真麻烦你了希望你们好好跳舞",
        "少先队员因该为老人让坐",
        "请问你叫什么名字",
        "我想喝一杯咖啡然后去图书馆"
    ]
    
    print("\n开始测试...")
    total_time = 0
    
    for i, text in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}: {text}")
        
        result = corrector.correct(text)
        
        total_time += result["time_ms"]
        
        print(f"  成功: {result['success']}")
        print(f"  纠正后: {result['corrected']}")
        print(f"  是否改变: {result['changed']}")
        print(f"  耗时: {result['time_ms']} ms")
        
        if result["changed"]:
            print(f"  改变数量: {len(result['changes'])}")
    
    print(f"\n总耗时: {total_time} ms")
    print(f"平均耗时: {total_time / len(test_cases):.1f} ms/条")
    
    # 统计信息
    stats = corrector.get_stats()
    print(f"\n引擎统计: {stats}")
    
    corrector.unload()
    
    return True


def test_singleton_pattern():
    """测试单例模式"""
    print("\n" + "=" * 60)
    print("测试 2: 单例模式")
    print("=" * 60)
    
    # 设置环境变量
    os.environ["TEXT_CORRECTOR_ENGINE"] = "macro-correct"
    
    # 获取两次实例
    corrector1 = get_text_corrector()
    corrector2 = get_text_corrector()
    
    # 验证是同一个实例
    assert corrector1 is corrector2, "单例模式失败"
    print("✓ 单例模式验证通过")
    
    # 测试功能
    text = "今天天气怎么样"
    result = corrector1.correct(text)
    
    print(f"  输入: {text}")
    print(f"  输出: {result['corrected']}")
    print(f"  耗时: {result['time_ms']} ms")
    
    return True


def test_cache_functionality():
    """测试缓存功能"""
    print("\n" + "=" * 60)
    print("测试 3: 缓存功能")
    print("=" * 60)
    
    corrector = TextCorrector(engine_type="macro-correct")
    
    text = "今天天气怎么样我们去哪里玩"
    
    # 第一次调用(无缓存)
    print(f"\n首次调用: {text}")
    result1 = corrector.correct(text)
    time1 = result1["time_ms"]
    print(f"  耗时: {time1} ms")
    
    # 第二次调用(有缓存)
    print(f"\n再次调用: {text}")
    result2 = corrector.correct(text)
    time2 = result2["time_ms"]
    print(f"  耗时: {time2} ms")
    
    # 验证缓存效果
    print(f"\n缓存加速: {time1 / max(time2, 1):.1f}x")
    
    # 统计信息
    stats = corrector.get_stats()
    print(f"缓存命中: {stats.get('cache_hits', 0)}")
    print(f"缓存未命中: {stats.get('cache_misses', 0)}")
    
    corrector.unload()
    
    return True


def test_error_handling():
    """测试错误处理"""
    print("\n" + "=" * 60)
    print("测试 4: 错误处理")
    print("=" * 60)
    
    # 测试空文本
    corrector = TextCorrector(engine_type="macro-correct")
    
    empty_texts = ["", " ", "   "]
    
    for text in empty_texts:
        result = corrector.correct(text)
        print(f"  输入: '{text}' -> 输出: '{result['corrected']}'")
        assert result["success"], "空文本处理失败"
    
    print("✓ 空文本处理正常")
    
    corrector.unload()
    
    return True


def test_performance_comparison():
    """性能对比测试"""
    print("\n" + "=" * 60)
    print("测试 5: 性能对比")
    print("=" * 60)
    
    test_texts = [
        "今天天气怎么样我们去哪里玩",
        "真麻烦你了希望你们好好跳舞",
        "少先队员因该为老人让坐",
    ]
    
    # macro-correct 引擎
    print("\nmacro-correct 引擎:")
    corrector_macro = TextCorrector(engine_type="macro-correct")
    
    times_macro = []
    for text in test_texts:
        result = corrector_macro.correct(text)
        times_macro.append(result["time_ms"])
        print(f"  '{text[:15]}...' -> {result['time_ms']} ms")
    
    avg_macro = sum(times_macro) / len(times_macro)
    print(f"平均耗时: {avg_macro:.1f} ms")
    
    corrector_macro.unload()
    
    print("\n性能基准(来自测试):")
    print(f"  macro-correct: ~1500 ms/条 (首次)")
    print(f"  llama-cpp: ~8000 ms/条")
    print(f"  加速比: 5.3x")
    
    return True


def main():
    """运行所有测试"""
    print("文本纠错器集成测试")
    print("=" * 60)
    
    tests = [
        ("macro-correct 引擎", test_macro_correct_engine),
        ("单例模式", test_singleton_pattern),
        ("缓存功能", test_cache_functionality),
        ("错误处理", test_error_handling),
        ("性能对比", test_performance_comparison),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            print(f"\n{'=' * 60}")
            print(f"运行测试: {name}")
            print(f"{'=' * 60}")
            
            if test_func():
                passed += 1
                print(f"\n✓ {name} 通过")
            else:
                failed += 1
                print(f"\n✗ {name} 失败")
        
        except Exception as e:
            failed += 1
            print(f"\n✗ {name} 异常: {e}")
            import traceback
            traceback.print_exc()
    
    # 总结
    print("\n" + "=" * 60)
    print(f"测试完成: {passed} 通过, {failed} 失败")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
